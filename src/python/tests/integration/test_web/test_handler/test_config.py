import json

from tests.integration.test_web.test_web_app import BaseTestWebApp


class TestConfigHandler(BaseTestWebApp):
    def test_get(self):
        self.context.config.general.debug = True
        self.context.config.lftp.remote_path = "/remote/server/path"
        self.context.config.controller.interval_ms_local_scan = 5678
        self.context.config.web.port = 8080
        resp = self.test_app.get("/server/config/get")
        self.assertEqual(200, resp.status_int)
        json_dict = json.loads(str(resp.html))
        self.assertEqual(True, json_dict["general"]["debug"])
        # No api_token configured → auth_valid=True → config is unredacted (CONF-04)
        self.assertEqual("/remote/server/path", json_dict["lftp"]["remote_path"])
        self.assertEqual(5678, json_dict["controller"]["interval_ms_local_scan"])
        self.assertEqual(8080, json_dict["web"]["port"])

    def test_get_secret_fields_always_blank(self):
        """SEC-02: webhook_secret and api_token always serialize as "" in GET response."""
        self.context.config.general.webhook_secret = "super-secret-value"
        self.context.config.general.api_token = "super-token-value"
        # Provide the Bearer token so the auth middleware allows the request.
        # This exercises the authenticated path (auth_valid=True) — exactly the path
        # D-10 changes (previously returned the real value, now always returns "").
        resp = self.test_app.get(
            "/server/config/get",
            headers={"Authorization": "Bearer super-token-value"}
        )
        self.assertEqual(200, resp.status_int)
        json_dict = json.loads(str(resp.html))
        self.assertEqual("", json_dict["general"]["webhook_secret"])
        self.assertEqual("", json_dict["general"]["api_token"])
        # Values must not appear anywhere in the response body
        self.assertNotIn("super-secret-value", str(resp.html))
        self.assertNotIn("super-token-value", str(resp.html))

    def test_set_good(self):
        self.assertEqual(None, self.context.config.general.debug)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "general", "key": "debug", "value": "True"}
        )
        self.assertEqual(200, resp.status_int)
        self.assertEqual(True, self.context.config.general.debug)

        self.assertEqual(None, self.context.config.lftp.remote_path)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "lftp", "key": "remote_path", "value": "/path/to/somewhere"}
        )
        self.assertEqual(200, resp.status_int)
        # CFG-04: value persists verbatim via unchanged Config.set_property path (no decode)
        self.assertEqual("/path/to/somewhere", self.context.config.lftp.remote_path)

        self.assertEqual(None, self.context.config.controller.interval_ms_local_scan)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "controller", "key": "interval_ms_local_scan", "value": "5678"}
        )
        self.assertEqual(200, resp.status_int)
        self.assertEqual(5678, self.context.config.controller.interval_ms_local_scan)

        self.assertEqual(None, self.context.config.web.port)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "web", "key": "port", "value": "8080"}
        )
        self.assertEqual(200, resp.status_int)
        self.assertEqual(8080, self.context.config.web.port)

    def test_set_good_slash_value_persists_verbatim(self):
        # D-04: value with slashes arrives in body and reaches set_property verbatim (no decode)
        self.assertEqual(None, self.context.config.lftp.remote_path)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "lftp", "key": "remote_path", "value": "/home/remoteuser/files"}
        )
        self.assertEqual(200, resp.status_int)
        self.assertEqual("/home/remoteuser/files", self.context.config.lftp.remote_path)

    def test_set_missing_section(self):
        self.assertFalse(self.context.config.has_section("bad_section"))
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "bad_section", "key": "option", "value": "value"},
            expect_errors=True
        )
        self.assertEqual(404, resp.status_int)
        self.assertEqual("There is no section 'bad_section' in config", str(resp.html))
        self.assertFalse(self.context.config.has_section("bad_section"))

    def test_set_missing_option(self):
        self.assertFalse(self.context.config.general.has_property("bad_option"))
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "general", "key": "bad_option", "value": "value"},
            expect_errors=True
        )
        self.assertEqual(404, resp.status_int)
        self.assertEqual("Section 'general' in config has no option 'bad_option'", str(resp.html))
        self.assertFalse(self.context.config.general.has_property("bad_option"))

    def test_set_bad_value(self):
        # boolean
        self.assertEqual(None, self.context.config.general.debug)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "general", "key": "debug", "value": "cat"},
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)
        self.assertEqual("Bad config: General.debug (cat) must be a boolean value", str(resp.html))
        self.assertEqual(None, self.context.config.general.debug)

        # positive int
        self.assertEqual(None, self.context.config.controller.interval_ms_local_scan)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "controller", "key": "interval_ms_local_scan", "value": "-1"},
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)
        self.assertEqual(
            "Bad config: Controller.interval_ms_local_scan (-1) must be greater than 0",
            str(resp.html)
        )
        self.assertEqual(None, self.context.config.controller.interval_ms_local_scan)

    def test_set_whitespace_value(self):
        # Whitespace-only value still surfaces ConfigError → 400 (D-05 preserved)
        self.assertEqual(None, self.context.config.lftp.remote_path)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "lftp", "key": "remote_path", "value": "  "},
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)
        self.assertEqual("Bad config: Lftp.remote_path is empty", str(resp.html))
        self.assertEqual(None, self.context.config.lftp.remote_path)

    def test_set_empty_value(self):
        # D-06: empty value is now 400 (was 404 under GET route-miss; intentional
        # contract refinement — empty value is a body-validation failure, not a route miss)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "lftp", "key": "remote_path", "value": ""},
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)

    def test_set_malformed_body_wrong_content_type(self):
        # D-07: wrong content-type → bottle.request.json returns None → handler guard → 400
        resp = self.test_app.post(
            "/server/config/set",
            params="not-json",
            content_type="text/plain",
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)

    def test_set_invalid_json_correct_content_type(self):
        # D-07 / FINDING 3: malformed JSON WITH Content-Type: application/json →
        # bottle's own HTTPError(400, 'Invalid JSON') fires before the handler runs.
        # No handler code services this path — this test pins that bottle's 400 is
        # the D-07 contract for malformed-JSON-with-correct-content-type.
        resp = self.test_app.post(
            "/server/config/set",
            params="{bad json",
            content_type="application/json",
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)

    def test_set_missing_required_field(self):
        # D-07: absent required field (no 'value') → 400 (malformed, distinct from unknown section)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "general", "key": "debug"},
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)

    def test_set_non_string_section(self):
        # FINDING 1: non-string section must return 400, NEVER 500 (no TypeError/DoS).
        # A list would reach has_section() which expects str → TypeError → 500 if unguarded.
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": ["general"], "key": "debug", "value": "True"},
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)
        self.assertNotEqual(500, resp.status_int)

    def test_set_non_string_key(self):
        # FINDING 1: non-string key must return 400, NEVER 500 (no TypeError/DoS).
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "general", "key": {"x": 1}, "value": "True"},
            expect_errors=True
        )
        self.assertEqual(400, resp.status_int)
        self.assertNotEqual(500, resp.status_int)

    def test_old_value_bearing_path_returns_404(self):
        # D-02 / FINDING 2: the OLD value-bearing path is unregistered → GET returns
        # exactly 404. (405 would mean a value-bearing route shape still exists under
        # another method — the CFG-02 failure mode. Assert 404 strictly, not 405.)
        resp = self.test_app.get(
            "/server/config/set/general/debug/True",
            expect_errors=True
        )
        self.assertEqual(404, resp.status_int)
        # POST to the value-bearing path is NOT the new contract (must not 200)
        resp_post = self.test_app.post_json(
            "/server/config/set/general/debug/True",
            {"value": "True"},
            expect_errors=True
        )
        self.assertNotEqual(200, resp_post.status_int)

    def test_bare_path_get_returns_non_200(self):
        # D-02 / FINDING 2: the NEW bare path is POST-only — GET does not succeed.
        # NOTE: In this WebApp, a GET to /server/config/set is intercepted by the
        # catch-all static file route (self.route("/<file_path:path>")) before bottle
        # can issue a 405 Method Not Allowed. The static handler returns 404 (file not
        # found) — not 405. Either way the credential-leaking GET path is gone.
        # Assert: GET does NOT return 200 (route is not accessible via GET).
        resp = self.test_app.get("/server/config/set", expect_errors=True)
        self.assertNotEqual(200, resp.status_int)
