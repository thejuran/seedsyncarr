import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import bottle  # noqa: F401  (imported so the bottle.run patch target resolves)

from web.web_app_job import WebAppJob


APP_STOP_ERROR_MSG = "Error stopping web app during web service cleanup"
SERVER_STOP_ERROR_MSG = "Error stopping web server during web service cleanup"
THREAD_JOIN_ERROR_MSG = "Error joining web server thread during web service cleanup"
STUCK_WARNING_MSG = "Web server did not stop within 5.0 seconds; continuing shutdown"


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

    def test_join_timeout_constant_below_docker_grace(self):
        """WEB-02: the join bound is 5 s, below Docker's 10 s stop grace."""
        self.assertEqual(WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS, 5.0)
        self.assertLess(WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS, 10.0)
