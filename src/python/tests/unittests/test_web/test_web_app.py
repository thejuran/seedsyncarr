import html as html_mod
import logging
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from webtest import TestApp

from web.web_app import WebApp

_TEST_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>SeedSyncarr</title>
</head>
<body>
    <app-root></app-root>
</body>
</html>
"""


def _make_minimal_web_app(html_path: str = "/tmp") -> WebApp:
    """
    Create a minimal WebApp instance suitable for unit testing.

    Sets up a fake context and controller so WebApp can be instantiated
    without real infrastructure.
    """
    mock_context = MagicMock()
    mock_context.logger = logging.getLogger("test_web_app")
    mock_context.args.html_path = html_path
    mock_context.status = MagicMock()

    mock_controller = MagicMock()

    return WebApp(context=mock_context, controller=mock_controller)


def _make_web_app_with_index(api_token: str = "", html_content: str = _TEST_INDEX_HTML):
    """Create a WebApp with a real index.html in a temp dir and config.
    Returns (app, tmp_dir_obj) — caller should call tmp_dir_obj.cleanup() or use
    the returned tmpdir.name path. The TemporaryDirectory auto-cleans on GC."""
    tmp_dir_obj = tempfile.TemporaryDirectory()
    tmpdir = tmp_dir_obj.name
    with open(os.path.join(tmpdir, "index.html"), "w") as f:
        f.write(html_content)

    mock_context = MagicMock()
    mock_context.logger = logging.getLogger("test_web_app")
    mock_context.args.html_path = tmpdir
    mock_context.status = MagicMock()

    mock_config = MagicMock()
    mock_config.general.api_token = api_token

    mock_controller = MagicMock()

    app = WebApp(context=mock_context, controller=mock_controller, config=mock_config)
    app.add_default_routes()
    return app, tmp_dir_obj


class TestWebAppSecurityHeaders(unittest.TestCase):
    """Tests that all API responses include required security headers."""

    def setUp(self):
        self.app = _make_minimal_web_app()
        # Add a simple test endpoint that returns 200
        @self.app.route("/test/ping")
        def _ping():
            return "pong"

        self.client = TestApp(self.app)

    def test_response_has_csp_header(self):
        """Content-Security-Policy header must be present on every response."""
        response = self.client.get("/test/ping")
        self.assertIn("Content-Security-Policy", response.headers)
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)

    def test_csp_header_contains_required_directives(self):
        """CSP header must include all required directives (R014).
        script-src/style-src use 'unsafe-inline' so Angular's autoCsp meta tag
        (hash-based) provides the actual inline restriction via dual-policy enforcement."""
        response = self.client.get("/test/ping")
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("font-src", csp)
        self.assertIn("connect-src", csp)
        self.assertIn("script-src 'self' 'unsafe-inline'", csp)
        self.assertIn("style-src 'self' 'unsafe-inline'", csp)
        self.assertIn("object-src 'none'", csp)

    def test_response_has_x_frame_options(self):
        """X-Frame-Options: DENY must be present on every response."""
        response = self.client.get("/test/ping")
        self.assertIn("X-Frame-Options", response.headers)
        self.assertEqual("DENY", response.headers["X-Frame-Options"])

    def test_response_has_x_content_type_options(self):
        """X-Content-Type-Options: nosniff must be present on every response."""
        response = self.client.get("/test/ping")
        self.assertIn("X-Content-Type-Options", response.headers)
        self.assertEqual("nosniff", response.headers["X-Content-Type-Options"])

    def test_security_headers_on_second_route(self):
        """Security headers must appear on responses from all routes, not just one."""
        @self.app.route("/test/other")
        def _other():
            return "other"

        client = TestApp(self.app)
        response = client.get("/test/other")
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("X-Frame-Options", response.headers)
        self.assertIn("X-Content-Type-Options", response.headers)

    def test_security_headers_on_post_route(self):
        """Security headers must appear on POST responses too."""
        @self.app.route("/test/post", method="POST")
        def _post():
            return "posted"

        client = TestApp(self.app)
        response = client.post("/test/post")
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("X-Frame-Options", response.headers)
        self.assertIn("X-Content-Type-Options", response.headers)


class TestWebAppMetaTagInjection(unittest.TestCase):
    """Tests for api-token meta tag injection in index.html (R007)."""

    def test_index_contains_meta_tag_with_token(self):
        """index.html should contain api-token meta tag with configured token."""
        app, _tmpd = _make_web_app_with_index(api_token="my-secret-token")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/")
        self.assertIn('<meta name="api-token" content="my-secret-token">', response.text)

    def test_index_meta_tag_empty_when_no_token(self):
        """Empty api_token should produce meta tag with empty content."""
        app, _tmpd = _make_web_app_with_index(api_token="")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/")
        self.assertIn('<meta name="api-token" content="">', response.text)

    def test_index_content_type_is_html(self):
        """Response Content-Type should be text/html."""
        app, _tmpd = _make_web_app_with_index(api_token="tok")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/")
        self.assertIn("text/html", response.content_type)

    def test_dashboard_route_serves_injected_index(self):
        """All Angular routes should serve the injected index.html."""
        app, _tmpd = _make_web_app_with_index(api_token="dashboard-tok")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/dashboard")
        self.assertIn('<meta name="api-token" content="dashboard-tok">', response.text)

    def test_settings_route_serves_injected_index(self):
        app, _tmpd = _make_web_app_with_index(api_token="settings-tok")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/settings")
        self.assertIn('<meta name="api-token" content="settings-tok">', response.text)

    def test_logs_route_serves_injected_index(self):
        app, _tmpd = _make_web_app_with_index(api_token="logs-tok")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/logs")
        self.assertIn('<meta name="api-token" content="logs-tok">', response.text)

    def test_about_route_serves_injected_index(self):
        app, _tmpd = _make_web_app_with_index(api_token="about-tok")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/about")
        self.assertIn('<meta name="api-token" content="about-tok">', response.text)

    def test_meta_tag_inserted_before_head_close(self):
        """Meta tag should appear before </head>."""
        app, _tmpd = _make_web_app_with_index(api_token="pos-test")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/")
        text = response.text
        meta_pos = text.find('<meta name="api-token"')
        head_close_pos = text.find("</head>")
        self.assertGreater(meta_pos, -1, "Meta tag not found")
        self.assertGreater(head_close_pos, -1, "</head> not found")
        self.assertLess(meta_pos, head_close_pos, "Meta tag should be before </head>")

    def test_original_html_preserved(self):
        """Original HTML structure should be preserved after injection."""
        app, _tmpd = _make_web_app_with_index(api_token="tok")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/")
        self.assertIn("<app-root>", response.text)
        self.assertIn("<title>SeedSyncarr</title>", response.text)

    def test_security_headers_on_index(self):
        """Security headers should still be present on index.html responses."""
        app, _tmpd = _make_web_app_with_index(api_token="tok")
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/")
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("X-Frame-Options", response.headers)

    def test_static_files_not_affected(self):
        """Static files other than index.html should be served normally."""
        app, _tmpd = _make_web_app_with_index(api_token="tok")
        self.addCleanup(_tmpd.cleanup)
        # Create a static CSS file
        with open(os.path.join(_tmpd.name, "styles.css"), "w") as f:
            f.write("body { color: red; }")
        client = TestApp(app)
        response = client.get("/styles.css")
        self.assertEqual("body { color: red; }", response.text)
        self.assertNotIn("api-token", response.text)

    def test_meta_tag_escapes_html_special_chars(self):
        """XSS prevention: HTML special characters in API token must be escaped in meta tag output."""
        xss_token = '<script>"alert(1)\'&'
        app, _tmpd = _make_web_app_with_index(api_token=xss_token)
        self.addCleanup(_tmpd.cleanup)
        client = TestApp(app)
        response = client.get("/")
        self.assertNotIn("<script>", response.text)
        escaped = html_mod.escape(xss_token, quote=True)
        self.assertIn('<meta name="api-token" content="{}">'.format(escaped), response.text)

    def test_missing_index_html_returns_404(self):
        """When index.html doesn't exist, return 404."""
        app = _make_minimal_web_app(html_path="/nonexistent/path")
        app.add_default_routes()
        client = TestApp(app)
        response = client.get("/", expect_errors=True)
        self.assertEqual(404, response.status_int)
