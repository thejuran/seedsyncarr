import logging
import os
import socket
import subprocess
import sys
import textwrap
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import bottle

from web.web_app_job import MyWSGIHandler, MyWSGIRefServer, WebAppJob


APP_STOP_ERROR_MSG = "Error stopping web app during web service cleanup"
SERVER_STOP_ERROR_MSG = "Error stopping web server during web service cleanup"
THREAD_JOIN_ERROR_MSG = "Error joining web server thread during web service cleanup"
STUCK_WARNING_MSG = "Web server did not stop within 5.0 seconds; continuing shutdown"
STOP_DEFERRED_MSG = "Web server not started yet; stop deferred to startup"
NEVER_STARTED_MSG = "Web server never started; nothing to stop"

# Pool size of the real server in the stuck-requests test and the number of
# requests held open in it, so that every worker is stuck and none is idle.
# Five is the smallest pool paste accepts with its default options.
STUCK_WORKER_COUNT = 5

LOGGER = logging.getLogger("test_web_app_job")

# Child process for the process-exit test: starts a real web server on a
# daemon thread and ends without stopping it, as when server.stop() failed or
# never ran. The interpreter must still exit by itself.
NEVER_STOPPED_SERVER_SCRIPT = textwrap.dedent("""
    import logging
    import sys
    import threading
    import time

    import bottle

    from web.web_app_job import MyWSGIRefServer

    srv = MyWSGIRefServer(logging.getLogger("child"), host="127.0.0.1", port=0)
    thread = threading.Thread(target=bottle.run,
                              kwargs={"app": bottle.Bottle(), "server": srv, "quiet": True},
                              daemon=True)
    thread.start()
    deadline = time.monotonic() + 10.0
    while srv.server is None:
        if time.monotonic() > deadline:
            sys.exit(2)
        time.sleep(0.01)
""")


def _joins_in_time(thread):
    """Model a thread that is alive until it is joined."""
    thread.is_alive.return_value = True

    def _join(timeout=None):
        thread.is_alive.return_value = False

    thread.join.side_effect = _join


class TestWebAppJobCleanup(unittest.TestCase):
    def _setup_job(self):
        web_app = MagicMock()
        job = WebAppJob(context=MagicMock(), web_app=web_app)
        job.setup()
        return job, web_app

    def _assert_nothing_logged(self, job):
        job.logger.exception.assert_not_called()
        job.logger.warning.assert_not_called()

    def test_cleanup_without_setup_does_not_raise(self):
        """WEB-02: cleanup() before setup() stops the app only and logs nothing."""
        web_app = MagicMock()
        job = WebAppJob(context=MagicMock(), web_app=web_app)
        job.cleanup()  # must not raise
        web_app.stop.assert_called_once()
        job.logger.exception.assert_not_called()
        job.logger.warning.assert_not_called()

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_app_stop_failure_still_stops_server_and_joins(self, mock_server_cls, mock_thread_cls):
        """WEB-01: a failing app.stop() still stops the server and joins the thread."""
        server = mock_server_cls.return_value
        thread = mock_thread_cls.return_value
        _joins_in_time(thread)
        job, web_app = self._setup_job()
        web_app.stop.side_effect = RuntimeError("app stop failed")

        job.cleanup()  # must not raise

        server.stop.assert_called_once()
        thread.join.assert_called_once_with(timeout=WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)
        job.logger.exception.assert_called_once()
        self.assertEqual(job.logger.exception.call_args[0][0], APP_STOP_ERROR_MSG)
        job.logger.warning.assert_not_called()

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_server_stop_failure_still_joins_thread(self, mock_server_cls, mock_thread_cls):
        """WEB-01: a failing server.stop() still joins the thread."""
        server = mock_server_cls.return_value
        thread = mock_thread_cls.return_value
        _joins_in_time(thread)
        job, web_app = self._setup_job()
        server.stop.side_effect = RuntimeError("server stop failed")

        job.cleanup()  # must not raise

        web_app.stop.assert_called_once()
        thread.join.assert_called_once_with(timeout=WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)
        job.logger.exception.assert_called_once()
        self.assertEqual(job.logger.exception.call_args[0][0], SERVER_STOP_ERROR_MSG)
        job.logger.warning.assert_not_called()

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_join_failure_is_logged_and_cleanup_returns(self, mock_server_cls, mock_thread_cls):
        """WEB-01: a failing join is logged and cleanup() returns."""
        server = mock_server_cls.return_value
        thread = mock_thread_cls.return_value
        thread.is_alive.return_value = True
        thread.join.side_effect = RuntimeError("join failed")
        job, web_app = self._setup_job()

        job.cleanup()  # must not raise

        web_app.stop.assert_called_once()
        server.stop.assert_called_once()
        job.logger.exception.assert_called_once()
        self.assertEqual(job.logger.exception.call_args[0][0], THREAD_JOIN_ERROR_MSG)
        job.logger.warning.assert_not_called()

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_all_steps_fail_all_attempted_and_logged(self, mock_server_cls, mock_thread_cls):
        """WEB-01: when every step fails, all are attempted and logged in order."""
        server = mock_server_cls.return_value
        thread = mock_thread_cls.return_value
        thread.is_alive.return_value = True
        job, web_app = self._setup_job()
        web_app.stop.side_effect = RuntimeError("app stop failed")
        server.stop.side_effect = RuntimeError("server stop failed")
        thread.join.side_effect = RuntimeError("join failed")

        job.cleanup()  # must not raise

        web_app.stop.assert_called_once()
        server.stop.assert_called_once()
        thread.join.assert_called_once()
        messages = [c[0][0] for c in job.logger.exception.call_args_list]
        self.assertEqual(messages, [APP_STOP_ERROR_MSG, SERVER_STOP_ERROR_MSG, THREAD_JOIN_ERROR_MSG])

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_server_not_created_skips_server_and_join(self, mock_server_cls, mock_thread_cls):
        """WEB-02: when the server constructor raised in setup, cleanup skips server and join."""
        mock_server_cls.side_effect = RuntimeError("server create failed")
        web_app = MagicMock()
        job = WebAppJob(context=MagicMock(), web_app=web_app)
        with self.assertRaises(RuntimeError):
            job.setup()

        job.cleanup()  # must not raise

        web_app.stop.assert_called_once()
        mock_thread_cls.assert_not_called()
        self._assert_nothing_logged(job)

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_thread_not_started_skips_join(self, mock_server_cls, mock_thread_cls):
        """WEB-02: when Thread.start() raised in setup, cleanup stops the server and skips the join."""
        server = mock_server_cls.return_value
        thread = mock_thread_cls.return_value
        thread.start.side_effect = RuntimeError("can't start new thread")
        thread.is_alive.return_value = False
        web_app = MagicMock()
        job = WebAppJob(context=MagicMock(), web_app=web_app)
        with self.assertRaises(RuntimeError):
            job.setup()

        job.cleanup()  # must not raise

        web_app.stop.assert_called_once()
        server.stop.assert_called_once()
        thread.join.assert_not_called()
        self._assert_nothing_logged(job)

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_thread_already_finished_skips_join(self, mock_server_cls, mock_thread_cls):
        """WEB-02: a server thread that already finished is not joined."""
        thread = mock_thread_cls.return_value
        thread.is_alive.return_value = False
        job, _ = self._setup_job()

        job.cleanup()  # must not raise

        thread.join.assert_not_called()
        self._assert_nothing_logged(job)

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_clean_shutdown_joins_with_timeout_and_logs_nothing(self, mock_server_cls, mock_thread_cls):
        """WEB-02: a clean shutdown joins with the bounded timeout and logs nothing."""
        thread = mock_thread_cls.return_value
        _joins_in_time(thread)
        job, _ = self._setup_job()

        job.cleanup()  # must not raise

        thread.join.assert_called_once_with(timeout=WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)
        self._assert_nothing_logged(job)

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_stuck_thread_logs_warning_and_returns(self, mock_server_cls, mock_thread_cls):
        """WEB-02: a server thread still alive after the bounded join is warned about."""
        thread = mock_thread_cls.return_value
        thread.is_alive.return_value = True
        job, _ = self._setup_job()

        job.cleanup()  # must not raise

        thread.join.assert_called_once_with(timeout=WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)
        job.logger.warning.assert_called_once()
        self.assertEqual(job.logger.warning.call_args[0][0], STUCK_WARNING_MSG)
        job.logger.exception.assert_not_called()

    def test_stuck_real_thread_returns_within_bound(self):
        """WEB-02: a real stuck server thread does not hold cleanup past the bound."""
        release = threading.Event()
        real_threads = []

        def _make_thread(*args, **kwargs):
            t = threading.Thread(*args, **kwargs)
            real_threads.append(t)
            return t

        def _stuck_run(**kwargs):
            release.wait(5.0)

        def _teardown():
            release.set()
            for t in real_threads:
                if t.ident is not None:
                    t.join(5.0)
            for t in real_threads:
                self.assertFalse(t.is_alive())

        self.addCleanup(_teardown)

        with patch("web.web_app_job.MyWSGIRefServer"), \
                patch("web.web_app_job.Thread", side_effect=_make_thread) as mock_thread_cls, \
                patch("web.web_app_job.bottle.run", side_effect=_stuck_run), \
                patch.object(WebAppJob, "_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS", 0.05):
            job, _ = self._setup_job()
            t = time.monotonic()
            job.cleanup()  # must not raise
            elapsed = time.monotonic() - t

        self.assertLess(elapsed, 1.0)
        job.logger.warning.assert_called_once()
        self.assertIn("did not stop within 0.05 seconds", job.logger.warning.call_args[0][0])
        self.assertIs(mock_thread_cls.call_args.kwargs["daemon"], True)

    @patch("web.web_app_job.Thread")
    @patch("web.web_app_job.MyWSGIRefServer")
    def test_server_thread_created_as_daemon(self, mock_server_cls, mock_thread_cls):
        """WEB-02: the web-server thread is a daemon so it cannot hold the interpreter open."""
        self._setup_job()
        self.assertIs(mock_thread_cls.call_args.kwargs.get("daemon"), True)

    def test_join_timeout_constant_pinned_at_5s(self):
        """WEB-02: pins the join bound at 5 s.

        The value is budgeted against docker's 10 s stop grace (see the
        constant's comment). Changing it must be a deliberate edit here too.
        """
        self.assertEqual(WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS, 5.0)


class _BlockingWebApp(bottle.Bottle):
    """A servable web app whose /block route holds its worker until released."""

    def __init__(self, entered: threading.Semaphore, release: threading.Event):
        super().__init__()
        self._entered = entered
        self._release = release
        self.route("/block", callback=self._block)

    def _block(self):
        self._entered.release()
        self._release.wait(30.0)
        return "released"

    def stop(self):
        pass

    def process(self):
        pass


def _make_server_thread(srv: MyWSGIRefServer) -> threading.Thread:
    """Build (but do not start) a daemon thread that runs a real adapter."""
    return threading.Thread(target=bottle.run,
                            kwargs={"app": bottle.Bottle(), "server": srv, "quiet": True},
                            daemon=True)


class TestMyWSGIRefServer(unittest.TestCase):
    def _new_mock_logged_server(self):
        logger = MagicMock()
        srv = MyWSGIRefServer(logger, host="127.0.0.1", port=0)
        return srv, logger

    def _patch_httpserver(self):
        patcher = patch("web.web_app_job.httpserver")
        mock_httpserver = patcher.start()
        self.addCleanup(patcher.stop)
        return mock_httpserver

    def _wait_for_server(self, srv: MyWSGIRefServer):
        deadline = time.monotonic() + 5.0
        while srv.server is None:
            if time.monotonic() > deadline:
                self.fail("web server was not created within 5 s")
            time.sleep(0.01)

    def _stop_quietly(self, srv: MyWSGIRefServer):
        # Teardown must never add an error next to a test failure.
        if srv.server is not None:
            try:
                srv.stop()
            except Exception:
                LOGGER.debug("teardown stop() failed", exc_info=True)

    def _register_real_server_teardown(self, srv: MyWSGIRefServer, thread: threading.Thread):
        # One function: cleanups run last-registered-first.
        def _teardown():
            self._stop_quietly(srv)
            if thread.ident is not None:
                thread.join(5.0)
                self.assertFalse(thread.is_alive())

        self.addCleanup(_teardown)

    def _register_barrier_teardown(self, release: threading.Event, thread: threading.Thread):
        # One function: cleanups run last-registered-first, so a separate
        # release cleanup would run after the join and stall a failed run.
        def _teardown():
            release.set()
            if thread.ident is not None:
                thread.join(5.0)
            self.assertFalse(thread.is_alive())

        self.addCleanup(_teardown)

    def test_stop_before_run_never_constructs_server(self):
        """WEB-02: stop() before run() is a quiet no-op and run() then never builds the server."""
        srv, logger = self._new_mock_logged_server()
        mock_httpserver = self._patch_httpserver()

        srv.stop()  # must not raise
        srv.run(MagicMock())

        # No server means no bound port and no worker pool.
        mock_httpserver.serve.assert_not_called()
        self.assertIsNone(srv.server)
        logger.exception.assert_not_called()
        logger.error.assert_not_called()

    def test_stop_before_run_logs_deferred(self):
        """WEB-02: stop() before run() has started reports the stop as deferred to startup."""
        srv, logger = self._new_mock_logged_server()

        srv.stop()

        logger.debug.assert_called_with(STOP_DEFERRED_MSG)

    def test_stop_after_failed_startup_logs_never_started(self):
        """WEB-02: stop() after run() failed to build the server does not claim a startup is pending."""
        srv, logger = self._new_mock_logged_server()
        mock_httpserver = self._patch_httpserver()
        mock_httpserver.serve.side_effect = OSError(98, "Address already in use")

        with self.assertRaises(OSError):
            srv.run(MagicMock())
        srv.stop()  # must not raise

        self.assertIsNone(srv.server)
        logger.debug.assert_called_with(NEVER_STARTED_MSG)
        debug_messages = [c.args[0] for c in logger.debug.call_args_list]
        self.assertNotIn(STOP_DEFERRED_MSG, debug_messages)

    def test_run_serves_with_daemon_threads(self):
        """WEB-02: run() asks paste for daemon worker threads and serves."""
        srv, _ = self._new_mock_logged_server()
        mock_httpserver = self._patch_httpserver()

        srv.run(MagicMock())

        mock_httpserver.serve.assert_called_once()
        kwargs = mock_httpserver.serve.call_args.kwargs
        self.assertIs(kwargs.get("daemon_threads"), True, "daemon_threads=True not passed to httpserver.serve")
        self.assertIs(kwargs.get("start_loop"), False)
        self.assertIs(kwargs.get("handler"), MyWSGIHandler)
        server = mock_httpserver.serve.return_value
        server.serve_forever.assert_called_once()
        server.server_close.assert_not_called()

    def test_stop_after_run_closes_server(self):
        """WEB-02: stop() on a running server only clears the running flag and closes the socket."""
        srv, _ = self._new_mock_logged_server()
        mock_httpserver = self._patch_httpserver()
        server = mock_httpserver.serve.return_value
        server.running = True

        srv.run(MagicMock())
        srv.stop()

        # The job thread must never run paste's worker-pool teardown.
        server.server_close.assert_not_called()
        server.thread_pool.shutdown.assert_not_called()
        self.assertIs(server.running, False)
        server.socket.close.assert_called_once()

    def test_stop_during_server_construction_closes_instead_of_serving(self):
        """WEB-02: a stop() while httpserver.serve is still constructing the server is honoured."""
        srv, logger = self._new_mock_logged_server()
        in_serve = threading.Event()
        release_serve = threading.Event()
        server = MagicMock()

        def _serve(*args, **kwargs):
            in_serve.set()
            release_serve.wait(5.0)
            return server

        mock_httpserver = self._patch_httpserver()
        mock_httpserver.serve.side_effect = _serve
        thread = threading.Thread(target=srv.run, args=(MagicMock(),), daemon=True)
        self._register_barrier_teardown(release_serve, thread)
        thread.start()

        self.assertTrue(in_serve.wait(5.0))
        self.assertIsNone(srv.server)
        srv.stop()  # must not raise
        release_serve.set()
        thread.join(5.0)
        self.assertFalse(thread.is_alive())

        server.server_close.assert_called_once()
        server.serve_forever.assert_not_called()
        logger.exception.assert_not_called()
        logger.error.assert_not_called()

    def test_stop_right_after_publication_ends_serve_loop(self):
        """WEB-02: a stop() right after the server is published ends the loop via flag and socket."""
        srv, _ = self._new_mock_logged_server()
        at_loop = threading.Event()
        release_loop = threading.Event()
        server = MagicMock()
        server.running = True

        def _serve_forever():
            at_loop.set()
            release_loop.wait(5.0)

        server.serve_forever.side_effect = _serve_forever
        mock_httpserver = self._patch_httpserver()
        mock_httpserver.serve.return_value = server
        thread = threading.Thread(target=srv.run, args=(MagicMock(),), daemon=True)
        self._register_barrier_teardown(release_loop, thread)
        thread.start()

        self.assertTrue(at_loop.wait(5.0))
        srv.stop()

        server.server_close.assert_not_called()
        self.assertIs(server.running, False)
        server.socket.close.assert_called_once()
        release_loop.set()
        thread.join(5.0)
        self.assertFalse(thread.is_alive())

    def test_socket_error_after_stop_ends_run_cleanly(self):
        """WEB-02: a socket error from the serve loop after stop() is a normal exit."""
        for error in (ValueError("Invalid file descriptor: -1"), OSError(9, "Bad file descriptor")):
            with self.subTest(error=type(error).__name__):
                srv, logger = self._new_mock_logged_server()
                server = MagicMock()
                server.running = True

                def _serve_forever():
                    # stop() closes the socket between the loop's running
                    # check and the next accept, as on the real server.
                    srv.stop()
                    raise error

                server.serve_forever.side_effect = _serve_forever
                with patch("web.web_app_job.httpserver") as mock_httpserver:
                    mock_httpserver.serve.return_value = server
                    srv.run(MagicMock())  # must not raise

                server.serve_forever.assert_called_once()
                logger.exception.assert_not_called()
                logger.error.assert_not_called()

    def test_socket_error_without_stop_propagates(self):
        """WEB-02: a socket error from the serve loop without a stop() is not swallowed."""
        for error in (ValueError("Invalid file descriptor: -1"), OSError(9, "Bad file descriptor")):
            with self.subTest(error=type(error).__name__):
                srv, _ = self._new_mock_logged_server()
                server = MagicMock()
                server.running = True
                server.serve_forever.side_effect = error
                with patch("web.web_app_job.httpserver") as mock_httpserver:
                    mock_httpserver.serve.return_value = server
                    with self.assertRaises(type(error)):
                        srv.run(MagicMock())

    def test_real_server_stop_racing_serve_loop_exits_cleanly(self):
        """WEB-02: stop() closing the socket just before handle_request() does not kill the server thread."""
        from paste import httpserver as paste_httpserver
        real_serve = paste_httpserver.serve
        srv = MyWSGIRefServer(LOGGER, host="127.0.0.1", port=0)
        raced = threading.Event()
        errors = []

        def _serve(*args, **kwargs):
            server = real_serve(*args, **kwargs)
            real_handle_request = server.handle_request

            def _handle_request():
                # The loop has passed its running check; stop() lands now.
                if not raced.is_set():
                    raced.set()
                    srv.stop()
                return real_handle_request()

            server.handle_request = _handle_request
            return server

        def _run():
            try:
                bottle.run(app=bottle.Bottle(), server=srv, quiet=True)
            except BaseException as e:
                errors.append(e)

        thread = threading.Thread(target=_run, daemon=True)
        self._register_real_server_teardown(srv, thread)
        with patch("web.web_app_job.httpserver.serve", side_effect=_serve):
            thread.start()
            thread.join(5.0)

        self.assertFalse(thread.is_alive())
        self.assertTrue(raced.is_set(), "the race was not exercised")
        self.assertEqual(errors, [])

    def test_real_server_stop_frees_port(self):
        """WEB-02: a real server stops through stop(), its thread ends and the port is free."""
        srv = MyWSGIRefServer(LOGGER, host="127.0.0.1", port=0)
        thread = _make_server_thread(srv)
        self._register_real_server_teardown(srv, thread)
        thread.start()
        self._wait_for_server(srv)
        port = srv.server.server_address[1]

        srv.stop()
        thread.join(3.0)
        self.assertFalse(thread.is_alive())

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
        finally:
            sock.close()

    def test_real_server_stop_before_start_never_binds(self):
        """WEB-02: a real server stopped before its thread starts never binds the port or serves."""
        from paste import httpserver as paste_httpserver
        srv = MyWSGIRefServer(LOGGER, host="127.0.0.1", port=0)
        thread = _make_server_thread(srv)
        self._register_real_server_teardown(srv, thread)

        srv.stop()
        # Spy on the real constructor: binding happens only inside it, so an
        # uncalled spy proves the port was never bound, without probing a
        # released ephemeral port that another process could take.
        with patch("web.web_app_job.httpserver.serve", wraps=paste_httpserver.serve) as serve_spy:
            thread.start()
            thread.join(3.0)

        self.assertFalse(thread.is_alive())
        serve_spy.assert_not_called()
        self.assertIsNone(srv.server)

    def test_cleanup_returns_within_bound_with_stuck_requests(self):
        """WEB-02: with every worker stuck in a request, WebAppJob.cleanup() stays within the bound."""
        entered = threading.Semaphore(0)
        release = threading.Event()
        adapters = []
        real_threads = []
        clients = []

        # Registered first so it is undone last, after the server has wound down.
        exit_patcher = patch("os._exit")
        mock_exit = exit_patcher.start()
        self.addCleanup(exit_patcher.stop)

        def _make_adapter(logger, host, port):
            srv = MyWSGIRefServer(logger, host="127.0.0.1", port=0,
                                  threadpool_workers=STUCK_WORKER_COUNT)
            adapters.append(srv)
            return srv

        def _make_thread(*args, **kwargs):
            t = threading.Thread(*args, **kwargs)
            real_threads.append(t)
            return t

        def _teardown():
            release.set()
            for c in clients:
                c.close()
            for srv in adapters:
                self._stop_quietly(srv)
            for t in real_threads:
                if t.ident is not None:
                    t.join(10.0)
            for t in real_threads:
                self.assertFalse(t.is_alive())

        self.addCleanup(_teardown)

        context = MagicMock()
        context.args.debug = False
        app = _BlockingWebApp(entered, release)
        job = WebAppJob(context=context, web_app=app)

        with patch("web.web_app_job.MyWSGIRefServer", side_effect=_make_adapter), \
                patch("web.web_app_job.Thread", side_effect=_make_thread), \
                patch.object(WebAppJob, "_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS", 0.2):
            job.setup()
            adapter = adapters[0]
            self._wait_for_server(adapter)
            port = adapter.server.server_address[1]
            for _ in range(STUCK_WORKER_COUNT):
                c = socket.create_connection(("127.0.0.1", port), timeout=5)
                clients.append(c)
                c.sendall(b"GET /block HTTP/1.0\r\n\r\n")
            # Entry barrier: every handler must have reported in before cleanup.
            for _ in range(STUCK_WORKER_COUNT):
                self.assertTrue(entered.acquire(timeout=5.0), "request did not reach the handler")

            server = adapter.server
            self.assertEqual(len(server.thread_pool.workers), STUCK_WORKER_COUNT,
                             "the pool must be fully blocked before cleanup")
            self.assertEqual(server.thread_pool.idle_workers, [],
                             "the pool must be fully blocked before cleanup")

            t = time.monotonic()
            job.cleanup()  # must not raise
            elapsed = time.monotonic() - t

        self.assertLess(elapsed, 1.5, "cleanup exceeded the shutdown bound: {:.2f}s".format(elapsed))
        job.logger.warning.assert_called_once()
        self.assertIn("did not stop within 0.2 seconds", job.logger.warning.call_args[0][0])
        job.logger.exception.assert_not_called()
        mock_exit.assert_not_called()

    def test_process_exits_when_web_server_never_stopped(self):
        """WEB-02: a process whose web server was never stopped still exits by itself."""
        src_python_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))
        try:
            proc = subprocess.run([sys.executable, "-c", NEVER_STOPPED_SERVER_SCRIPT],
                                  cwd=src_python_dir, capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            self.fail("process did not exit: web server threads kept the interpreter alive")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
