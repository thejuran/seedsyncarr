import logging
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

    # Bounds how long shutdown waits for the web-server thread. It must stay
    # well below docker's default 10 s stop grace so that time is left for
    # the shutdown work that follows (controller exit, final state save)
    # before docker escalates to SIGKILL. A class attribute rather than a
    # Constants entry so tests can patch it.
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
    Extend bottle's default server to support programatic stopping of server
    Copied from: https://stackoverflow.com/a/16056443
    """
    quiet = True  # disable logging to stdout

    def __init__(self, logger: logging.Logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger
        self.server = None

    @overrides(bottle.ServerAdapter)
    def run(self, handler):
        self.logger.debug("Starting web server")
        handler = TransLogger(handler, logger=self.logger, setup_console_handler=(not self.quiet))
        self.server = httpserver.serve(handler, host=self.host, port=str(self.port), start_loop=False,
                                       handler=MyWSGIHandler,
                                       **self.options)
        self.server.serve_forever()

    def stop(self):
        self.logger.debug("Stopping web server")
        self.server.server_close()
