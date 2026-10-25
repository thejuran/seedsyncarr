"""
LOG-01 regressions: webhook/controller/config handler log lines must reach
the app's "seedsyncarr" logger tree (via WebAppBuilder's real construction),
not a detached module-level logger.

122-14 adds CR-01 (an Arr API key must never reach the persisted app log or
the UI log stream, even via a real requests.exceptions.InvalidHeader) and
WR-01 (the status endpoint's rate-limit warning must reach the app logger
too) regressions.
"""
import json
import logging
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

from web.handler.config import ConfigHandler
from web.handler.webhook import WebhookHandler
from web.serialize import SerializeLogRecord
from web.web_app_builder import WebAppBuilder


class _CapturingHandler(logging.Handler):
    """Captures every record regardless of level, so a test can prove nothing
    was logged in addition to asserting what was logged (CR-01)."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


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
            "Unexpected error testing Sonarr connection (RuntimeError)",
            matching[0].getMessage()
        )
        self.assertIsNone(matching[0].exc_info)

        # D-14: the formatted record, including the traceback, must never
        # surface the API key (it travels only via the X-Api-Key header).
        formatted = logging.Formatter().format(matching[0])
        self.assertNotIn(api_key, formatted)

    def test_config_key_with_newline_never_reaches_requests_or_log(self):
        """CR-01: a stored key with an embedded newline must be rejected
        before it ever reaches `requests` (which would otherwise raise a
        real InvalidHeader whose message embeds the raw key), and nothing
        under the app logger tree may contain any part of the key."""
        key = "SSA122LEAK" + "\n" + "PROBE122"

        capturing_handler = _CapturingHandler()
        app_logger = logging.getLogger("seedsyncarr")
        app_logger.addHandler(capturing_handler)
        try:
            with patch.object(ConfigHandler, "_validate_url", return_value=None):
                response = self.builder.config_handler._test_arr_connection(
                    "Sonarr", "http://203.0.113.10:8989", key
                )
        finally:
            app_logger.removeHandler(capturing_handler)

        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Sonarr API key contains invalid characters", body["error"])

        self.assertNotIn("SSA122LEAK", response.body)
        self.assertNotIn("PROBE122", response.body)

        for record in capturing_handler.records:
            formatted = logging.Formatter().format(record)
            self.assertNotIn("SSA122LEAK", formatted)
            self.assertNotIn("PROBE122", formatted)
            serialized = SerializeLogRecord().record(record)
            self.assertNotIn("SSA122LEAK", serialized)
            self.assertNotIn("PROBE122", serialized)

    def test_config_unexpected_error_with_real_invalid_header_logs_type_only(self):
        """CR-01: a real requests.exceptions.InvalidHeader (whose message
        embeds the key) must be logged as its type only, never its message
        or traceback, in either output path (plain Formatter or the SSE
        serializer)."""
        key = "SSA122validKEY0123456789abcdef01"
        invalid_header = requests.exceptions.InvalidHeader(
            "Invalid leading whitespace, reserved character(s), or return "
            "character(s) in header value: '" + key + "'"
        )

        with patch('web.handler.config.requests.get', side_effect=invalid_header):
            with patch.object(ConfigHandler, "_validate_url", return_value=None):
                with self.assertLogs("seedsyncarr", level="ERROR") as captured:
                    response = self.builder.config_handler._test_arr_connection(
                        "Sonarr", "http://203.0.113.10:8989", key
                    )

        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("An unexpected error occurred", body["error"])

        matching = [r for r in captured.records if r.name == "seedsyncarr.ConfigHandler"]
        self.assertEqual(1, len(matching))
        self.assertEqual(
            "Unexpected error testing Sonarr connection (InvalidHeader)",
            matching[0].getMessage()
        )
        self.assertIsNone(matching[0].exc_info)

        formatted = logging.Formatter().format(matching[0])
        self.assertNotIn(key, formatted)
        serialized = SerializeLogRecord().record(matching[0])
        self.assertNotIn(key, serialized)

    @patch('web.handler.status.SerializeStatusJson')
    @patch('web.rate_limit.time')
    def test_status_rate_limit_warning_under_app_logger(self, mock_time, mock_serialize):
        """WR-01: the status endpoint's rate-limit warning must reach the
        app logger (seedsyncarr.StatusHandler), not a detached module
        logger."""
        mock_time.time.return_value = 1000.0
        mock_serialize.status.return_value = '{"server":{"up":true}}'

        web_app = MagicMock()
        self.builder.status_handler.add_routes(web_app)

        wrapped = None
        for call_args in web_app.add_handler.call_args_list:
            args, _kwargs = call_args
            if args and args[0] == "/server/status":
                wrapped = args[1]
                break
        self.assertIsNotNone(wrapped, "no handler registered for /server/status")

        for _ in range(60):
            response = wrapped()
            self.assertNotEqual(429, response.status_code)

        with self.assertLogs("seedsyncarr", level="WARNING") as captured:
            response = wrapped()

        self.assertEqual(429, response.status_code)
        matching = [
            r for r in captured.records
            if r.name == "seedsyncarr.StatusHandler"
            and r.getMessage().startswith("Rate limit exceeded for")
        ]
        self.assertEqual(1, len(matching))


if __name__ == "__main__":
    unittest.main()
