import unittest
from unittest.mock import MagicMock


from common import Job


class DummyError(Exception):
    pass


class DummyFailingJob(Job):
    def setup(self):
        self.cleanup_run = False

    def execute(self):
        raise DummyError()

    def cleanup(self):
        self.cleanup_run = True


class TestJob(unittest.TestCase):
    def test_exception_propagates(self):
        context = MagicMock()
        job = DummyFailingJob("DummyFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        with self.assertRaises(DummyError):
            job.propagate_exception()

    def test_cleanup_executes_on_execute_error(self):
        context = MagicMock()
        job = DummyFailingJob("DummyFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertTrue(job.cleanup_run)
