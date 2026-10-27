import unittest
from unittest.mock import MagicMock

from web.web_app_job import WebAppJob


class TestWebAppJobCleanup(unittest.TestCase):
    def test_cleanup_without_setup_does_not_raise(self):
        web_app = MagicMock()
        job = WebAppJob(context=MagicMock(), web_app=web_app)
        job.cleanup()
        web_app.stop.assert_called_once()
