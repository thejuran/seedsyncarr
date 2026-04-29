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
