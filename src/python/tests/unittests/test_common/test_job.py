import unittest
from unittest.mock import MagicMock


from common import Job


class DummyError(Exception):
    pass


class DummyCleanupError(Exception):
    pass


class DummyFailingJob(Job):
    def setup(self):
        self.cleanup_run = False

    def execute(self):
        raise DummyError()

    def cleanup(self):
        self.cleanup_run = True


class DummySetupFailingJob(Job):
    def __init__(self, name, context):
        super().__init__(name, context)
        self.execute_calls = 0
        self.cleanup_run = False
        self.cleanup_calls = 0

    def setup(self):
        raise DummyError()

    def execute(self):
        self.execute_calls += 1

    def cleanup(self):
        self.cleanup_run = True
        self.cleanup_calls += 1


class DummySetupAndCleanupFailingJob(Job):
    def __init__(self, name, context):
        super().__init__(name, context)
        self.execute_calls = 0
        self.cleanup_calls = 0

    def setup(self):
        raise DummyError()

    def execute(self):
        self.execute_calls += 1

    def cleanup(self):
        self.cleanup_calls += 1
        raise DummyCleanupError()


class DummyCleanupFailingJob(Job):
    def __init__(self, name, context):
        super().__init__(name, context)
        self.execute_calls = 0
        self.cleanup_calls = 0

    def setup(self):
        pass

    def execute(self):
        self.execute_calls += 1

    def cleanup(self):
        self.cleanup_calls += 1
        raise DummyCleanupError()


class DummyCleanJob(Job):
    def __init__(self, name, context):
        super().__init__(name, context)

    def setup(self):
        pass

    def execute(self):
        pass

    def cleanup(self):
        pass


class TestJob(unittest.TestCase):
    def test_exception_propagates(self):
        context = MagicMock()
        job = DummyFailingJob("DummyFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        with self.assertRaises(DummyError):
            job.propagate_exception()

    def test_cleanup_executes_on_execute_error(self):
        context = MagicMock()
        job = DummyFailingJob("DummyFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        self.assertTrue(job.cleanup_run)

    def test_setup_exception_propagates(self):
        context = MagicMock()
        job = DummySetupFailingJob("DummySetupFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        with self.assertRaises(DummyError):
            job.propagate_exception()
        self.assertEqual(0, job.execute_calls)

    def test_cleanup_executes_on_setup_error(self):
        context = MagicMock()
        job = DummySetupFailingJob("DummySetupFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        self.assertTrue(job.cleanup_run)
        self.assertEqual(1, job.cleanup_calls)

    def test_setup_error_sets_shutdown_flag(self):
        context = MagicMock()
        job = DummySetupFailingJob("DummySetupFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        self.assertTrue(job.shutdown_flag.is_set())

    def test_setup_error_not_masked_by_cleanup_error(self):
        context = MagicMock()
        context.logger = MagicMock()
        job = DummySetupAndCleanupFailingJob("DummySetupAndCleanupFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        with self.assertRaises(DummyError):
            job.propagate_exception()
        cleanup_logged = any(
            "cleanup" in str(call.args[0]).lower()
            for call in job.logger.exception.call_args_list
        )
        self.assertTrue(cleanup_logged, "Expected logger.exception to be called with a message mentioning 'cleanup'")

    def test_cleanup_error_surfaces_on_clean_run(self):
        context = MagicMock()
        context.logger = MagicMock()
        job = DummyCleanupFailingJob("DummyCleanupFailingJob", context)
        job.start()
        job.terminate()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        with self.assertRaises(DummyCleanupError):
            job.propagate_exception()

    def test_clean_run_has_no_exception(self):
        context = MagicMock()
        context.logger = MagicMock()
        job = DummyCleanJob("DummyCleanJob", context)
        job.start()
        job.terminate()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        self.assertIsNone(job.propagate_exception())
