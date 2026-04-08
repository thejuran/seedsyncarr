# Tests for Bearer token authentication middleware (R001-R005, R008)

import logging
import unittest
from unittest.mock import MagicMock

from webtest import TestApp

from web.web_app import WebApp


def _make_web_app(api_token: str = "") -> WebApp:
    """Create a minimal WebApp with auth configured."""
    mock_context = MagicMock()
    mock_context.logger = logging.getLogger("test_auth")
    mock_context.args.html_path = "/tmp"
    mock_context.status = MagicMock()

    mock_controller = MagicMock()

    mock_config = MagicMock()
    mock_config.general.api_token = api_token

    app = WebApp(context=mock_context, controller=mock_controller, config=mock_config)

    # Add test endpoints
    @app.route("/server/test/endpoint")
    def _test_endpoint():
        return "ok"

    @app.route("/server/config/get")
    def _config_get():
        return "config"

    @app.post("/server/command/restart")
    def _restart():
        return "restarted"

    @app.route("/server/stream")
    def _stream():
        return "stream"

    @app.post("/server/webhook/sonarr")
    def _webhook_sonarr():
        return "webhook"

    @app.post("/server/webhook/radarr")
    def _webhook_radarr():
        return "webhook-radarr"

    @app.route("/test/non-server")
    def _non_server():
        return "non-server"

    @app.route("/dashboard")
    def _dashboard():
        return "dashboard"

    return app


class TestAuthMiddlewareWithToken(unittest.TestCase):
    """Tests for auth hook when api_token IS configured (R001, R008)."""

    def setUp(self):
        self.token = "test-secret-token-value"
        self.app = _make_web_app(api_token=self.token)
        self.client = TestApp(self.app)

    def test_server_endpoint_without_token_returns_401(self):
        """R001: /server/* without token → 401."""
        response = self.client.get("/server/test/endpoint", expect_errors=True)
        self.assertEqual(401, response.status_int)

    def test_server_endpoint_with_correct_token_returns_200(self):
        """R001: /server/* with valid Bearer token → 200."""
        response = self.client.get(
            "/server/test/endpoint",
            headers={"Authorization": "Bearer " + self.token}
        )
        self.assertEqual(200, response.status_int)
        self.assertEqual("ok", response.text)

    def test_server_endpoint_with_wrong_token_returns_401(self):
        """R008: Wrong token → 401 (timing-safe comparison)."""
        response = self.client.get(
            "/server/test/endpoint",
            headers={"Authorization": "Bearer wrong-token"},
            expect_errors=True
        )
        self.assertEqual(401, response.status_int)

    def test_malformed_auth_header_returns_401(self):
        """Malformed Authorization header → 401."""
        response = self.client.get(
            "/server/test/endpoint",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
            expect_errors=True
        )
        self.assertEqual(401, response.status_int)

    def test_empty_auth_header_returns_401(self):
        response = self.client.get(
            "/server/test/endpoint",
            headers={"Authorization": ""},
            expect_errors=True
        )
        self.assertEqual(401, response.status_int)

    def test_config_get_requires_auth(self):
        """Config endpoint is protected."""
        response = self.client.get("/server/config/get", expect_errors=True)
        self.assertEqual(401, response.status_int)

    def test_config_get_with_token_succeeds(self):
        response = self.client.get(
            "/server/config/get",
            headers={"Authorization": "Bearer " + self.token}
        )
        self.assertEqual(200, response.status_int)

    def test_post_endpoint_requires_auth(self):
        """POST endpoints are also protected."""
        response = self.client.post("/server/command/restart", expect_errors=True)
        self.assertEqual(401, response.status_int)

    def test_post_endpoint_with_token_succeeds(self):
        response = self.client.post(
            "/server/command/restart",
            headers={"Authorization": "Bearer " + self.token}
        )
        self.assertEqual(200, response.status_int)


class TestAuthMiddlewareExemptions(unittest.TestCase):
    """Tests for SSE and webhook exemptions (R003, R004)."""

    def setUp(self):
        self.token = "test-secret-token-value"
        self.app = _make_web_app(api_token=self.token)
        self.client = TestApp(self.app)

    def test_sse_stream_exempt_from_auth(self):
        """R003: /server/stream is exempt — EventSource can't send headers."""
        response = self.client.get("/server/stream")
        self.assertEqual(200, response.status_int)

    def test_webhook_sonarr_exempt_from_auth(self):
        """R004: /server/webhook/* exempt — uses HMAC auth."""
        response = self.client.post("/server/webhook/sonarr")
        self.assertEqual(200, response.status_int)

    def test_webhook_radarr_exempt_from_auth(self):
        """R004: /server/webhook/radarr also exempt."""
        response = self.client.post("/server/webhook/radarr")
        self.assertEqual(200, response.status_int)


class TestAuthMiddlewareNoToken(unittest.TestCase):
    """Tests for backward compatibility when no token configured (R005)."""

    def setUp(self):
        self.app = _make_web_app(api_token="")
        self.client = TestApp(self.app)

    def test_server_endpoint_allowed_without_token_config(self):
        """R005: Empty api_token → all requests pass through."""
        response = self.client.get("/server/test/endpoint")
        self.assertEqual(200, response.status_int)
        self.assertEqual("ok", response.text)

    def test_config_get_allowed_without_token_config(self):
        response = self.client.get("/server/config/get")
        self.assertEqual(200, response.status_int)

    def test_post_allowed_without_token_config(self):
        response = self.client.post("/server/command/restart")
        self.assertEqual(200, response.status_int)


class TestAuthMiddlewareNonServerPaths(unittest.TestCase):
    """Tests that non-/server/ paths are never blocked."""

    def setUp(self):
        self.token = "test-secret-token-value"
        self.app = _make_web_app(api_token=self.token)
        self.client = TestApp(self.app)

    def test_non_server_path_not_blocked(self):
        """Non-/server/ paths should not be affected by auth."""
        response = self.client.get("/test/non-server")
        self.assertEqual(200, response.status_int)

    def test_dashboard_not_blocked(self):
        """Frontend routes should not be blocked."""
        response = self.client.get("/dashboard")
        self.assertEqual(200, response.status_int)


class TestAuthRequestFlag(unittest.TestCase):
    """Tests that request.auth_valid flag is set correctly for downstream handlers."""

    def setUp(self):
        self.token = "test-secret-token-value"
        self.auth_valid_values = []

        app = _make_web_app(api_token=self.token)

        # Override test endpoint to capture auth_valid
        captured = self.auth_valid_values

        @app.route("/server/test/capture-auth")
        def _capture():
            import bottle
            captured.append(getattr(bottle.request, 'auth_valid', None))
            return "ok"

        self.app = app
        self.client = TestApp(app)

    def test_auth_valid_true_on_success(self):
        self.client.get(
            "/server/test/capture-auth",
            headers={"Authorization": "Bearer " + self.token}
        )
        self.assertEqual([True], self.auth_valid_values)

    def test_auth_valid_true_on_no_token_config(self):
        # Rebuild with no token
        self.auth_valid_values.clear()
        app = _make_web_app(api_token="")
        captured = self.auth_valid_values

        @app.route("/server/test/capture-auth")
        def _capture():
            import bottle
            captured.append(getattr(bottle.request, 'auth_valid', None))
            return "ok"

        client = TestApp(app)
        client.get("/server/test/capture-auth")
        self.assertEqual([True], self.auth_valid_values)
