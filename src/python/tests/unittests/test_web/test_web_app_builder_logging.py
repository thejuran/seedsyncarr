"""
LOG-01 regressions: webhook/controller/config handler log lines must reach
the app's "seedsyncarr" logger tree (via WebAppBuilder's real construction),
not a detached module-level logger.
"""
import logging
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

from web.handler.config import ConfigHandler
from web.handler.webhook import WebhookHandler
from web.web_app_builder import WebAppBuilder


class TestWebAppBuilderLogging(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)

        self.context = MagicMock()
        self.context.logger = logging.getLogger("seedsyncarr")
        self.context.config.lftp.local_path = self.tmp_dir
        self.context.config.general.webhook_secret = ""
        self.context.config.general.webhook_require_secret = False

        self.builder = WebAppBuilder(self.context, MagicMock(), MagicMock(), MagicMock())

    @patch('web.handler.webhook.request')
    def test_webhook_test_event_logged_under_app_logger(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = {"eventType": "Test"}

        with self.assertLogs("seedsyncarr", level="INFO") as captured:
            response = self.builder.webhook_handler._handle_webhook(
                "Sonarr", WebhookHandler._extract_sonarr_title
            )

        self.assertEqual(200, response.status_code)
        matching = [
            r for r in captured.records
            if r.getMessage() == "Sonarr webhook test event received"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("seedsyncarr.WebhookHandler", matching[0].name)

    @patch('web.handler.webhook.request')
    def test_radarr_webhook_test_event_logged_under_app_logger(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = {"eventType": "Test"}

        with self.assertLogs("seedsyncarr", level="INFO") as captured:
            response = self.builder.webhook_handler._handle_webhook(
                "Radarr", WebhookHandler._extract_radarr_title
            )

        self.assertEqual(200, response.status_code)
        matching = [
            r for r in captured.records
            if r.getMessage() == "Radarr webhook test event received"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("seedsyncarr.WebhookHandler", matching[0].name)

    def test_controller_traversal_warning_under_app_logger(self):
        with self.assertLogs("seedsyncarr", level="WARNING") as captured:
            response = self.builder.controller_handler._check_path_safe("../../etc/passwd")

        self.assertIsNotNone(response)
        self.assertEqual(400, response.status_code)
        matching = [
            r for r in captured.records
            if r.getMessage().startswith("Rejected path traversal attempt for")
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("seedsyncarr.ControllerHandler", matching[0].name)

    @patch('web.handler.config.requests')
    def test_config_unexpected_error_logged_without_api_key(self, mock_requests):
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        mock_requests.get.side_effect = RuntimeError("boom")
        api_key = "test-api-key-122-PIN"

        with patch.object(ConfigHandler, "_validate_url", return_value=None):
            with self.assertLogs("seedsyncarr", level="ERROR") as captured:
                response = self.builder.config_handler._test_arr_connection(
                    "Sonarr", "http://203.0.113.10:8989", api_key
                )

        self.assertIn("An unexpected error occurred", response.body)

        matching = [r for r in captured.records if r.name == "seedsyncarr.ConfigHandler"]
        self.assertEqual(1, len(matching))
        self.assertEqual(
            "Unexpected error testing Sonarr connection", matching[0].getMessage()
        )

        # D-14: the formatted record, including the traceback, must never
        # surface the API key (it travels only via the X-Api-Key header).
        formatted = logging.Formatter().format(matching[0])
        self.assertNotIn(api_key, formatted)


if __name__ == "__main__":
    unittest.main()
