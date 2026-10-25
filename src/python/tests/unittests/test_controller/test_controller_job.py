import unittest
from unittest.mock import MagicMock

from common import AppError
from controller import ControllerJob
from controller.controller import ControllerError


class TestControllerJob(unittest.TestCase):
    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.mock_controller = MagicMock()
        self.mock_auto_queue = MagicMock()
        self.job = ControllerJob(
            context=self.mock_context,
            controller=self.mock_controller,
            auto_queue=self.mock_auto_queue
        )

    def test_setup_starts_controller(self):
        self.job.setup()
        self.mock_controller.start.assert_called_once()

    def test_execute_processes_controller(self):
        self.job.execute()
        self.mock_controller.process.assert_called_once()

    def test_execute_processes_auto_queue(self):
        self.job.execute()
        self.mock_auto_queue.process.assert_called_once()

    def test_execute_calls_controller_before_auto_queue(self):
        call_order = []
        self.mock_controller.process.side_effect = lambda: call_order.append('controller')
        self.mock_auto_queue.process.side_effect = lambda: call_order.append('auto_queue')
        self.job.execute()
        self.assertEqual(['controller', 'auto_queue'], call_order)

    def test_cleanup_exits_controller(self):
        self.job.cleanup()
        self.mock_controller.exit.assert_called_once()

    def test_setup_apperror_propagates_unchanged(self):
        app_error = AppError("controller start failed")
        self.mock_controller.start.side_effect = app_error
        with self.assertRaises(AppError) as cm:
            self.job.setup()
        self.assertIs(app_error, cm.exception)

    def test_setup_non_apperror_wrapped_in_controller_error(self):
        os_error = OSError("fork failed")
        self.mock_controller.start.side_effect = os_error
        with self.assertRaises(ControllerError) as cm:
            self.job.setup()
        err = cm.exception
        self.assertEqual(
            "Controller failed to start. Please check server logs for details.",
            str(err)
        )
        self.assertIs(os_error, err.__cause__)
        self.assertNotIn("fork failed", str(err))

    def test_setup_failure_thread_runs_cleanup_and_surfaces(self):
        self.mock_controller.start.side_effect = OSError("fork failed")
        job = ControllerJob(
            context=self.mock_context,
            controller=self.mock_controller,
            auto_queue=self.mock_auto_queue
        )
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        self.mock_controller.exit.assert_called_once()
        self.mock_controller.process.assert_not_called()
        with self.assertRaises(ControllerError):
            job.propagate_exception()
