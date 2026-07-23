import hmac
import hashlib
import json
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from web.handler.webhook import WebhookHandler


def _make_mock_config(webhook_secret: str = "", webhook_require_secret: bool = False) -> MagicMock:
    """Create a mock Config with the given webhook_secret and webhook_require_secret."""
    mock_config = MagicMock()
    mock_config.general.webhook_secret = webhook_secret
    mock_config.general.webhook_require_secret = webhook_require_secret
    return mock_config


def _compute_hmac(secret: str, body: bytes) -> str:
    """Compute expected HMAC-SHA256 hex digest."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


class TestWebhookHandlerExtractSonarrTitle(unittest.TestCase):
    """Tests for _extract_sonarr_title static method.

    Only episodeFile.sourcePath is trusted. Regression (incident 2026-07-23):
    the old release.releaseTitle/series.title fallbacks could mark a file
    imported without a real import — for a single-file release the
    releaseTitle equals the file name exactly, so any Download-typed event
    lacking a sourcePath would false-positively arm auto-delete.
    """

    def test_extracts_source_path_basename(self):
        body = {"episodeFile": {"sourcePath": "/downloads/Game.of.Thrones.S01E01-GROUP"}}
        result, provenance = WebhookHandler._extract_sonarr_title(body)
        self.assertEqual("Game.of.Thrones.S01E01-GROUP", result)
        self.assertEqual("episodeFile.sourcePath", provenance)

    def test_release_title_alone_is_not_trusted(self):
        body = {"release": {"releaseTitle": "Game.of.Thrones.S01E01-GROUP.mkv"}}
        result, provenance = WebhookHandler._extract_sonarr_title(body)
        self.assertEqual("", result)
        self.assertEqual("", provenance)

    def test_series_title_alone_is_not_trusted(self):
        body = {"series": {"title": "Game of Thrones"}}
        result, _ = WebhookHandler._extract_sonarr_title(body)
        self.assertEqual("", result)

    def test_prefers_source_path_over_release_title(self):
        body = {
            "episodeFile": {"sourcePath": "/downloads/FromSourcePath"},
            "release": {"releaseTitle": "FromRelease"}
        }
        result, _ = WebhookHandler._extract_sonarr_title(body)
        self.assertEqual("FromSourcePath", result)

    def test_empty_body_returns_empty(self):
        result, provenance = WebhookHandler._extract_sonarr_title({})
        self.assertEqual("", result)
        self.assertEqual("", provenance)


class TestWebhookHandlerExtractRadarrTitle(unittest.TestCase):
    """Tests for _extract_radarr_title static method.

    Only movieFile.sourcePath is trusted; see TestWebhookHandlerExtractSonarrTitle
    docstring for the false-positive import regression this guards against.
    """

    def test_extracts_source_path_basename(self):
        body = {"movieFile": {"sourcePath": "/downloads/Inception.2010.1080p-GROUP"}}
        result, provenance = WebhookHandler._extract_radarr_title(body)
        self.assertEqual("Inception.2010.1080p-GROUP", result)
        self.assertEqual("movieFile.sourcePath", provenance)

    def test_release_title_alone_is_not_trusted(self):
        # Single-file release: releaseTitle equals the tracked file name
        # exactly. Trusting it would mark an import that never happened.
        body = {"release": {"releaseTitle": "Inception.2010.1080p-GROUP.mkv"}}
        result, provenance = WebhookHandler._extract_radarr_title(body)
        self.assertEqual("", result)
        self.assertEqual("", provenance)

    def test_movie_title_alone_is_not_trusted(self):
        body = {"movie": {"title": "Inception"}}
        result, _ = WebhookHandler._extract_radarr_title(body)
        self.assertEqual("", result)

    def test_empty_body_returns_empty(self):
        result, provenance = WebhookHandler._extract_radarr_title({})
        self.assertEqual("", result)
        self.assertEqual("", provenance)


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
            "Sonarr", "Test.File-GROUP",
            provenance="eventType=Download, episodeFile.sourcePath"
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
            "Radarr", "Movie.2024-GROUP",
            provenance="eventType=Download, movieFile.sourcePath"
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

    @patch('web.handler.webhook.request')
    def test_download_with_only_release_title_not_enqueued(self, mock_request):
        # Regression (incident 2026-07-23): a Download event without
        # movieFile.sourcePath must NOT mark an import via release.releaseTitle.
        # For a single-file release the releaseTitle equals the file name, so
        # the old fallback would false-positively mark the file imported and
        # arm auto-delete without any real *arr import.
        mock_request.content_length = -1
        mock_request.json = {
            "eventType": "Download",
            "release": {"releaseTitle": "Movie.2024.2160p-GROUP.mkv"}
        }
        response = self.handler._handle_webhook("Radarr", WebhookHandler._extract_radarr_title)
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


class TestWebhookFailClosedGuard(unittest.TestCase):
    """Unit tests for the BUG-02 fail-closed guard wrapper (_make_require_secret_guard).

    These verify the guard short-circuits to 503 BEFORE reading the body or calling the
    inner handler, mirroring the body-not-read proof pattern in TestWebhookPayloadSizeLimit.
    """

    def setUp(self):
        self.mock_webhook_manager = MagicMock()

    @patch('web.handler.webhook.request')
    def test_require_secret_on_no_secret_503_before_body_read(self, mock_request):
        """require_secret=True + no secret -> 503 + body not read + inner handler not called.

        Proves guard short-circuits before body parse (mirrors size-limit test line 274).
        The sentinel inner handler raises if called, proving the guard short-circuited.
        """
        handler = WebhookHandler(
            self.mock_webhook_manager,
            _make_mock_config(webhook_secret="", webhook_require_secret=True)
        )
        # Sentinel inner handler: raises if called, proving guard short-circuits
        sentinel_inner = MagicMock()
        guarded = handler._make_require_secret_guard(sentinel_inner)

        # Set up mock request to track body.read calls and json access
        mock_json = PropertyMock(side_effect=AssertionError("request.json should not be accessed"))
        type(mock_request).json = mock_json

        response = guarded()

        # (a) status 503
        self.assertEqual(503, response.status_code)
        # (b) inner handler NOT called — proves guard short-circuited
        sentinel_inner.assert_not_called()
        # (c) body.read NOT called — no body parse
        mock_request.body.read.assert_not_called()
        # (d) request.json NOT accessed
        mock_json.assert_not_called()

    @patch('web.handler.webhook.request')
    def test_require_secret_off_guard_calls_inner(self, mock_request):
        """require_secret=False + no secret -> guard passes through to inner handler (COMPAT)."""
        handler = WebhookHandler(
            self.mock_webhook_manager,
            _make_mock_config(webhook_secret="", webhook_require_secret=False)
        )
        inner_result = MagicMock()
        inner = MagicMock(return_value=inner_result)
        guarded = handler._make_require_secret_guard(inner)

        result = guarded()

        inner.assert_called_once()
        self.assertIs(inner_result, result)

    @patch('web.handler.webhook.request')
    def test_require_secret_on_with_secret_calls_inner(self, mock_request):
        """require_secret=True + secret configured -> guard passes through to inner handler."""
        handler = WebhookHandler(
            self.mock_webhook_manager,
            _make_mock_config(webhook_secret="configured-secret", webhook_require_secret=True)
        )
        inner_result = MagicMock()
        inner = MagicMock(return_value=inner_result)
        guarded = handler._make_require_secret_guard(inner)

        result = guarded()

        inner.assert_called_once()
        self.assertIs(inner_result, result)
