import logging
import threading
from threading import Thread

import bottle
from paste import httpserver
from paste.translogger import TransLogger

from .web_app import WebApp
from common import overrides, Job, Context

class WebAppJob(Job):
    """
    Web interface service
    """

    # Bounds how long shutdown waits for the web-server thread. In cleanup(),
    # app.stop() sets a flag, server.stop() closes the listening socket and
    # returns at once (paste's worker teardown runs on the server thread, not
    # here), and the join waits at most this many seconds. The web service's
    # share of shutdown is therefore about this bound, which stays well below
    # docker's default 10 s stop grace and leaves time for the shutdown work
    # that follows (controller exit, final state save) before docker
    # escalates to SIGKILL. A class attribute rather than a Constants entry
    # so tests can patch it.
    _SERVER_THREAD_JOIN_TIMEOUT_IN_SECS = 5.0

    def __init__(self, context: Context, web_app: WebApp):
        super().__init__(name=self.__class__.__name__, context=context)
        self.web_access_logger = context.web_access_logger
        self.__context = context
        self.__app = web_app
        self.__server = None
        self.__server_thread = None

    @overrides(Job)
    def setup(self):
        # Note: do not use requestlogger.WSGILogger as it breaks SSE
        self.__server = MyWSGIRefServer(self.web_access_logger,
                                        host="0.0.0.0",
                                        port=self.__context.config.web.port)
        # A server thread that outlives the bounded join in cleanup() must
        # not keep the interpreter alive at exit.
        self.__server_thread = Thread(target=bottle.run,
                                      kwargs={
                                          'app': self.__app,
                                          'server': self.__server,
                                          'debug': self.__context.args.debug
                                      },
                                      daemon=True)
        self.__server_thread.start()

    @overrides(Job)
    def execute(self):
        self.__app.process()

    @overrides(Job)
    def cleanup(self):
        # Each step runs independently: a failure in one never skips the
        # others. Job.run may call this after a setup() that raised partway,
        # so steps that do not apply are skipped silently.
        try:
            self.__app.stop()
        except Exception:
            self.logger.exception("Error stopping web app during web service cleanup")

        if self.__server is not None:
            try:
                self.__server.stop()
            except Exception:
                self.logger.exception("Error stopping web server during web service cleanup")

        # Unlike ScanManager._terminate_and_join, the wait runs even when
        # stopping the server failed: the timeout makes the wait safe, and it
        # gives the server a chance to finish on its own.
        thread = self.__server_thread
        try:
            # is_alive() skips a thread that was never started (join() on it
            # raises RuntimeError) and one that already finished.
            if thread is not None and thread.is_alive():
                thread.join(timeout=self._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)
                if thread.is_alive():
                    self.logger.warning("Web server did not stop within {} seconds; continuing shutdown"
                                        .format(self._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS))
        except Exception:
            self.logger.exception("Error joining web server thread during web service cleanup")

class MyWSGIHandler(httpserver.WSGIHandler):
    """
    This class is overridden to fix a bug in Paste http server
    """
    def wsgi_write_chunk(self, chunk):
        if type(chunk) is str:
            chunk = str.encode(chunk)
        super().wsgi_write_chunk(chunk)

class MyWSGIRefServer(bottle.ServerAdapter):
    """
    Extend bottle's default server to support programatic stopping of server.
    stop() may arrive before startup, in which case the server is never
    created, or during startup, in which case it is closed as soon as it is
    created and never serves. stop() returns
    immediately; the server thread finishes winding down on its own.
    Originally copied from: https://stackoverflow.com/a/16056443
    (the stop mechanism no longer follows that answer)
    """
    quiet = True  # disable logging to stdout

    def __init__(self, logger: logging.Logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger
        self.server = None
        # Serializes stop() (called from the job thread) against run() (the
        # server thread) storing self.server, so a stop that arrives during
        # startup is never lost. __ended_without_server lets stop() tell a
        # pending startup apart from a run() that ended without a server.
        self.__stop_requested = False
        self.__ended_without_server = False
        self.__lock = threading.Lock()

    @overrides(bottle.ServerAdapter)
    def run(self, handler):
        self.logger.debug("Starting web server")
        server = None
        try:
            handler = TransLogger(handler, logger=self.logger, setup_console_handler=(not self.quiet))
            # Fast path for a stop() that arrived before startup: never bind
            # the port or start the worker pool. A stop() during construction
            # is still caught by the check after publication below.
            with self.__lock:
                if self.__stop_requested:
                    self.logger.debug("Web server stop requested before startup; not starting")
                    return
            # paste's pool workers are non-daemon by default and would keep
            # the interpreter alive at exit when the server was not stopped
            # cleanly.
            server = httpserver.serve(handler, host=self.host, port=str(self.port), start_loop=False,
                                      handler=MyWSGIHandler,
                                      daemon_threads=True,
                                      **self.options)
        finally:
            if server is None:
                # run() is over without a server (stopped first, or
                # construction raised, e.g. port in use), so a later stop()
                # must not report a startup that will never happen.
                with self.__lock:
                    self.__ended_without_server = True
        with self.__lock:
            self.server = server
            stop_requested = self.__stop_requested
        if stop_requested:
            # stop() arrived during startup. Closing with paste's full
            # teardown is safe only here: nothing has been accepted yet, so
            # every worker is idle and the pool drains in milliseconds, and
            # this is the server thread, which cleanup() waits on for a
            # bounded time only. Without a serve loop nothing else would
            # drain the idle workers.
            server.server_close()
            return
        try:
            server.serve_forever()
        except (OSError, ValueError):
            # stop() closes the listening socket from the job thread, which
            # can land after paste's loop has checked its running flag but
            # before the next accept. handle_request() then fails on the
            # closed socket (ValueError: Invalid file descriptor: -1). paste
            # has already drained the pool in its finally block, so after a
            # requested stop this is a normal exit. Without a stop it is a
            # real failure and must propagate.
            with self.__lock:
                stop_requested = self.__stop_requested
            if not stop_requested:
                raise
            self.logger.debug("Web server loop ended after stop()")

    def stop(self):
        with self.__lock:
            self.__stop_requested = True
            server = self.server
            ended_without_server = self.__ended_without_server
        if server is None:
            if ended_without_server:
                self.logger.debug("Web server never started; nothing to stop")
            else:
                self.logger.debug("Web server not started yet; stop deferred to startup")
            return
        self.logger.debug("Stopping web server")
        # This is everything paste's server_close() does except the
        # worker-pool teardown. paste's own serve loop sees the flag within
        # about a second and drains the pool on the server thread. Calling
        # server_close() here would run that teardown on the job thread, where
        # it costs about half a second per stuck request before the bounded
        # join even starts and can enter paste's force-quit branch. Closing
        # the socket here frees the port for an immediate restart.
        server.running = False
        server.socket.close()
