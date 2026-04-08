# Copyright 2017, Inderpreet Singh, All rights reserved.

import hmac
import hashlib
import json
import unittest
from unittest.mock import MagicMock, patch

from web.handler.webhook import WebhookHandler


def _make_mock_config(webhook_secret: str = "") -> MagicMock:
    """Create a mock Config with the given webhook_secret."""
    mock_config = MagicMock()
    mock_config.general.webhook_secret = webhook_secret
    return mock_config


def _compute_hmac(secret: str, body: bytes) -> str:
    """Compute expected HMAC-SHA256 hex digest."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


class TestWebhookHandlerExtractSonarrTitle(unittest.TestCase):
    """Tests for _extract_sonarr_title static method."""

    def test_extracts_source_path_basename(self):
        body = {"episodeFile": {"sourcePath": "/downloads/Game.of.Thrones.S01E01-GROUP"}}
        result = WebhookHandler._extract_sonarr_title(body)
        self.assertEqual("Game.of.Thrones.S01E01-GROUP", result)

    def test_falls_back_to_release_title(self):
        body = {"release": {"releaseTitle": "Game.of.Thrones.S01E01-GROUP"}}
        result = WebhookHandler._extract_sonarr_title(body)
        self.assertEqual("Game.of.Thrones.S01E01-GROUP", result)

    def test_falls_back_to_series_title(self):
        body = {"series": {"title": "Game of Thrones"}}
        result = WebhookHandler._extract_sonarr_title(body)
        self.assertEqual("Game of Thrones", result)

    def test_prefers_source_path_over_release_title(self):
        body = {
            "episodeFile": {"sourcePath": "/downloads/FromSourcePath"},
            "release": {"releaseTitle": "FromRelease"}
        }
        result = WebhookHandler._extract_sonarr_title(body)
        self.assertEqual("FromSourcePath", result)

    def test_empty_body_returns_empty(self):
        result = WebhookHandler._extract_sonarr_title({})
        self.assertEqual("", result)


class TestWebhookHandlerExtractRadarrTitle(unittest.TestCase):
    """Tests for _extract_radarr_title static method."""

    def test_extracts_source_path_basename(self):
        body = {"movieFile": {"sourcePath": "/downloads/Inception.2010.1080p-GROUP"}}
        result = WebhookHandler._extract_radarr_title(body)
        self.assertEqual("Inception.2010.1080p-GROUP", result)

    def test_falls_back_to_release_title(self):
        body = {"release": {"releaseTitle": "Inception.2010.1080p-GROUP"}}
        result = WebhookHandler._extract_radarr_title(body)
        self.assertEqual("Inception.2010.1080p-GROUP", result)

    def test_falls_back_to_movie_title(self):
        body = {"movie": {"title": "Inception"}}
        result = WebhookHandler._extract_radarr_title(body)
        self.assertEqual("Inception", result)

    def test_empty_body_returns_empty(self):
        result = WebhookHandler._extract_radarr_title({})
        self.assertEqual("", result)


class TestWebhookHandlerRoutes(unittest.TestCase):
    """Tests for webhook handler routing and event processing."""

    def setUp(self):
        self.mock_webhook_manager = MagicMock()
        # Default config has empty webhook_secret (backward compat — no verification)
        self.handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config(""))

    @patch('web.handler.webhook.request')
    def test_sonarr_download_event_enqueues(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = {
            "eventType": "Download",
            "episodeFile": {"sourcePath": "/downloads/Test.File-GROUP"}
        }
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)
        self.mock_webhook_manager.enqueue_import.assert_called_once_with(
            "Sonarr", "Test.File-GROUP"
        )

    @patch('web.handler.webhook.request')
    def test_radarr_download_event_enqueues(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = {
            "eventType": "Download",
            "movieFile": {"sourcePath": "/downloads/Movie.2024-GROUP"}
        }
        response = self.handler._handle_webhook("Radarr", WebhookHandler._extract_radarr_title)
        self.assertEqual(200, response.status_code)
        self.mock_webhook_manager.enqueue_import.assert_called_once_with(
            "Radarr", "Movie.2024-GROUP"
        )

    @patch('web.handler.webhook.request')
    def test_test_event_returns_200_test_ok(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = {"eventType": "Test"}
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)
        self.assertIn("Test OK", response.body)
        self.mock_webhook_manager.enqueue_import.assert_not_called()

    @patch('web.handler.webhook.request')
    def test_grab_event_returns_200_ok(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = {"eventType": "Grab"}
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)
        self.mock_webhook_manager.enqueue_import.assert_not_called()

    @patch('web.handler.webhook.request')
    def test_rename_event_returns_200_ok(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = {"eventType": "Rename"}
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)
        self.mock_webhook_manager.enqueue_import.assert_not_called()

    @patch('web.handler.webhook.request')
    def test_empty_body_returns_400(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = None
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(400, response.status_code)
        self.assertIn("Empty body", response.body)

    @patch('web.handler.webhook.request')
    def test_invalid_json_returns_400(self, mock_request):
        mock_request.content_length = -1
        # Make request.json raise an exception when accessed
        type(mock_request).json = property(lambda self: (_ for _ in ()).throw(ValueError("bad json")))
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(400, response.status_code)
        self.assertIn("Invalid JSON", response.body)

    @patch('web.handler.webhook.request')
    def test_download_with_no_title_returns_200_no_enqueue(self, mock_request):
        mock_request.content_length = -1
        mock_request.json = {"eventType": "Download"}
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)
        self.mock_webhook_manager.enqueue_import.assert_not_called()

    def test_add_routes_registers_both_endpoints(self):
        mock_web_app = MagicMock()
        self.handler.add_routes(mock_web_app)
        calls = mock_web_app.add_post_handler.call_args_list
        paths = [c[0][0] for c in calls]
        self.assertIn("/server/webhook/sonarr", paths)
        self.assertIn("/server/webhook/radarr", paths)


class TestWebhookHandlerHmacVerification(unittest.TestCase):
    """Tests for HMAC signature verification on webhook requests."""

    def setUp(self):
        self.mock_webhook_manager = MagicMock()

    @patch('web.handler.webhook.request')
    def test_webhook_without_secret_config_accepts_all(self, mock_request):
        """When webhook_secret is empty, all requests pass regardless of headers."""
        handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config(""))
        mock_request.content_length = -1
        mock_request.json = {"eventType": "Test"}
        # No X-Webhook-Signature header needed
        mock_request.headers = {}
        mock_request.body.read.return_value = b'{"eventType": "Test"}'

        response = handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)

    @patch('web.handler.webhook.request')
    def test_webhook_with_secret_rejects_missing_signature(self, mock_request):
        """When webhook_secret is set and no signature header is sent, return 401."""
        handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config("testsecret"))
        body = b'{"eventType": "Test"}'
        mock_request.body.read.return_value = body
        mock_request.headers.get.return_value = ""  # No header

        response = handler._verify_hmac()
        self.assertIsNotNone(response)
        self.assertEqual(401, response.status_code)
        self.assertIn("signature", response.body.lower())

    @patch('web.handler.webhook.request')
    def test_webhook_with_secret_rejects_invalid_signature(self, mock_request):
        """When webhook_secret is set and signature is wrong, return 401."""
        handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config("testsecret"))
        body = b'{"eventType": "Test"}'
        mock_request.body.read.return_value = body
        mock_request.headers.get.return_value = "invalidsignature"

        response = handler._verify_hmac()
        self.assertIsNotNone(response)
        self.assertEqual(401, response.status_code)
        self.assertIn("invalid", response.body.lower())

    @patch('web.handler.webhook.request')
    def test_webhook_with_secret_accepts_valid_signature(self, mock_request):
        """When webhook_secret is set and HMAC signature is correct, return None (success)."""
        secret = "testsecret"
        handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config(secret))
        body = b'{"eventType": "Test"}'
        correct_sig = _compute_hmac(secret, body)

        mock_request.body.read.return_value = body
        mock_request.headers.get.return_value = correct_sig

        response = handler._verify_hmac()
        self.assertIsNone(response)  # None means success

    @patch('web.handler.webhook.request')
    def test_full_request_with_valid_signature_succeeds(self, mock_request):
        """End-to-end: valid signature + valid body returns 200."""
        secret = "testsecret"
        handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config(secret))
        body_dict = {"eventType": "Test"}
        body_bytes = json.dumps(body_dict).encode("utf-8")
        correct_sig = _compute_hmac(secret, body_bytes)

        mock_request.content_length = -1
        mock_request.body.read.return_value = body_bytes
        mock_request.headers.get.return_value = correct_sig
        mock_request.json = body_dict

        response = handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)

    @patch('web.handler.webhook.request')
    def test_full_request_with_invalid_signature_returns_401(self, mock_request):
        """End-to-end: invalid signature returns 401 regardless of body content."""
        secret = "testsecret"
        handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config(secret))
        body_bytes = b'{"eventType": "Download"}'

        mock_request.content_length = -1
        mock_request.body.read.return_value = body_bytes
        mock_request.headers.get.return_value = "wrongsignature"

        response = handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(401, response.status_code)


class TestWebhookPayloadSizeLimit(unittest.TestCase):
    """Tests for webhook payload size enforcement (WHOOK-01)."""

    def setUp(self):
        self.mock_webhook_manager = MagicMock()
        self.handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config(""))

    @patch('web.handler.webhook.request')
    def test_oversized_payload_returns_413(self, mock_request):
        """Payloads over 1MB must return 413 without reading the body."""
        mock_request.content_length = 2_000_000  # 2 MB
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(413, response.status_code)
        self.assertIn("Payload too large", response.body)
        mock_request.body.read.assert_not_called()

    @patch('web.handler.webhook.request')
    def test_payload_at_limit_is_accepted(self, mock_request):
        """Payloads at exactly 1MB (the limit) must be accepted."""
        mock_request.content_length = 1_048_576  # exactly 1 MB
        mock_request.json = {"eventType": "Test"}
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)

    @patch('web.handler.webhook.request')
    def test_payload_under_limit_is_accepted(self, mock_request):
        """Payloads under 1MB must be processed normally."""
        mock_request.content_length = 500
        mock_request.json = {"eventType": "Test"}
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)

    @patch('web.handler.webhook.request')
    def test_missing_content_length_is_accepted(self, mock_request):
        """Missing Content-Length header (-1 from Bottle) must be accepted (graceful degradation)."""
        mock_request.content_length = -1
        mock_request.json = {"eventType": "Test"}
        response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
        self.assertEqual(200, response.status_code)
