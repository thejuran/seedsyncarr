from unittest.mock import patch

from tests.integration.test_web.test_web_app import BaseTestWebApp


class TestWebhookIntegration(BaseTestWebApp):
    """
    Integration tests for webhook routes through the Bottle web layer.

    These tests verify that HTTP POST requests to /server/webhook/sonarr and
    /server/webhook/radarr are correctly routed through Bottle to
    WebhookHandler, which dispatches to webhook_manager.enqueue_import.

    The webhook_manager is a MagicMock injected as the 4th arg to WebAppBuilder
    in BaseTestWebApp.setUp. Access via name-mangled attribute:
    self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager
    """

    @property
    def _webhook_manager_mock(self):
        """Access the name-mangled webhook_manager MagicMock."""
        return self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager

    def test_sonarr_download_enqueues_via_web_layer(self):
        body = {
            "eventType": "Download",
            "episodeFile": {"sourcePath": "/downloads/Show.S01E01-GROUP"}
        }
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_called_once_with(
            "Sonarr", "Show.S01E01-GROUP"
        )

    def test_radarr_download_enqueues_via_web_layer(self):
        body = {
            "eventType": "Download",
            "movieFile": {"sourcePath": "/downloads/Movie.2024-GROUP"}
        }
        resp = self.test_app.post_json("/server/webhook/radarr", body)
        self.assertEqual(200, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_called_once_with(
            "Radarr", "Movie.2024-GROUP"
        )

    def test_sonarr_test_event_returns_200_without_enqueue(self):
        body = {"eventType": "Test"}
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_not_called()

    def test_sonarr_grab_event_returns_200_without_enqueue(self):
        body = {"eventType": "Grab"}
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_not_called()

    def test_radarr_test_event_returns_200_without_enqueue(self):
        body = {"eventType": "Test"}
        resp = self.test_app.post_json("/server/webhook/radarr", body)
        self.assertEqual(200, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_not_called()


class TestWebhookFailClosed(BaseTestWebApp):
    """Integration tests for BUG-02: webhook_require_secret fail-closed behavior."""

    def _set_require_secret(self, require_secret: bool, webhook_secret: str = ""):
        """Helper to configure require_secret flag on the real Config object."""
        self.context.config.general.webhook_require_secret = require_secret
        self.context.config.general.webhook_secret = webhook_secret

    def test_require_secret_off_no_secret_returns_200(self):
        """Default behavior (require_secret=False, no secret) -> 200 (COMPAT)."""
        self._set_require_secret(False, "")
        body = {"eventType": "Test"}
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)

    def test_require_secret_on_no_secret_returns_503(self):
        """require_secret=True + no secret -> 503 before body parse (BUG-02)."""
        self._set_require_secret(True, "")
        body = {"eventType": "Test"}
        resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)
        self.assertEqual(503, resp.status_int)

    def test_require_secret_on_with_secret_runs_hmac(self):
        """require_secret=True + secret configured -> HMAC path runs (returns 401 on missing sig)."""
        self._set_require_secret(True, "configured-secret")
        body = {"eventType": "Test"}
        # No X-Webhook-Signature header -> HMAC rejects with 401 (not 503)
        resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)
        self.assertEqual(401, resp.status_int)

    @patch("web.rate_limit.time")
    def test_503_precedes_429_when_window_exhausted(self, mock_time):
        """BLOCKER 2: 503 fires before 429 even when the rate-limit window is exhausted.

        Sends 61 fail-closed requests: every response must be 503 (never 429),
        proving the outer guard runs ahead of the rate-limit counter (D-05, T-101-06).
        """
        mock_time.time.return_value = 1000.0
        self._set_require_secret(True, "")
        body = {"eventType": "Test"}
        for i in range(61):
            resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)
            self.assertEqual(503, resp.status_int,
                             msg=f"Request {i+1}/61: expected 503 but got {resp.status_int}")


class TestWebhookRateLimit(BaseTestWebApp):
    """Integration tests for SEC-03: rate-limited webhook routes."""

    @patch("web.rate_limit.time")
    def test_sonarr_61st_request_returns_429(self, mock_time):
        """61st request to sonarr route returns 429 (within same window)."""
        mock_time.time.return_value = 1000.0
        self.context.config.general.webhook_require_secret = False
        self.context.config.general.webhook_secret = ""
        body = {"eventType": "Test"}
        for _ in range(60):
            resp = self.test_app.post_json("/server/webhook/sonarr", body)
            self.assertEqual(200, resp.status_int)
        resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)
        self.assertEqual(429, resp.status_int)

    @patch("web.rate_limit.time")
    def test_sonarr_and_radarr_counters_are_independent(self, mock_time):
        """Exhaust sonarr budget — radarr still accepts requests (D-09, independent closures)."""
        mock_time.time.return_value = 1000.0
        self.context.config.general.webhook_require_secret = False
        self.context.config.general.webhook_secret = ""
        body = {"eventType": "Test"}
        for _ in range(60):
            self.test_app.post_json("/server/webhook/sonarr", body)
        # radarr has an independent counter — should still be under limit
        resp = self.test_app.post_json("/server/webhook/radarr", body)
        self.assertEqual(200, resp.status_int)
