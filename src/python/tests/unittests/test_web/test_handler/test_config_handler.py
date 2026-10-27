import ast
import ipaddress
import json
import re
import socket
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch
from urllib.parse import urlparse

import requests
from urllib3.util import parse_url

from common import Config, ConfigError
from web.handler.config import ConfigHandler


# Locked refusal strings (D-07) -- literals, not imported from config.py, so
# these tests pin the exact wording rather than drift silently with the
# implementation.
LOOPBACK_MSG = "Loopback addresses are only allowed on port 8989 (Sonarr) or 7878 (Radarr)"
LINK_LOCAL_MSG = "URL points to a link-local or cloud-metadata address, which is not allowed"
UNSPECIFIED_MSG = "URL points to an unspecified address (0.0.0.0 or ::), which is not allowed"
MULTICAST_MSG = "URL points to a multicast address, which is not allowed"
RESERVED_MSG = "URL points to a reserved IP address, which is not allowed"
UNCHECKABLE_MSG = "URL resolves to an address that could not be checked, which is not allowed"
BAD_PORT_MSG = "Invalid URL: invalid port"
BAD_URL_MSG = "Invalid URL"

# Locked refusal strings (D-11/D-14, 125-04) -- same convention: literals
# pinned here, not imported from config.py.
BAD_CHARS_MSG = "Invalid URL: it contains a space, backslash or other character that is not allowed"
CREDENTIALS_MSG = "Invalid URL: a user name or password in the URL is not allowed"
QUERY_MSG = "Invalid URL: a query string or fragment (? or #) is not allowed"
BAD_HOSTNAME_MSG = "Invalid URL: malformed hostname"
UNRESOLVABLE_MSG = "Cannot resolve hostname"


def _resolve_all(mock_socket, *ips):
    """Stub getaddrinfo so the hostname resolves to one or more addresses."""
    mock_socket.getaddrinfo.return_value = [
        (None, None, None, None, (ip, 0)) for ip in ips
    ]
    mock_socket.gaierror = socket.gaierror


class TestConfigHandlerGet(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.handler = ConfigHandler(self.mock_config, MagicMock())

    @patch('web.handler.config.SerializeConfig')
    def test_get_returns_200(self, mock_serialize_cls):
        mock_serialize_cls.config.return_value = '{"test":"data"}'
        response = self.handler._ConfigHandler__handle_get_config()
        self.assertEqual(200, response.status_code)

    @patch('web.handler.config.SerializeConfig')
    def test_get_body_is_serialized_config(self, mock_serialize_cls):
        mock_serialize_cls.config.return_value = '{"test":"data"}'
        response = self.handler._ConfigHandler__handle_get_config()
        self.assertEqual('{"test":"data"}', response.body)


class TestConfigHandlerSet(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_context = MagicMock()
        self.handler = ConfigHandler(self.mock_config, self.mock_context)

    def test_constructor_creates_child_logger(self):
        self.mock_context.logger.getChild.assert_called_once_with("ConfigHandler")

    def test_set_valid_returns_200(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "lftp", "key": "remote_address", "value": "192.168.1.1"}
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(200, response.status_code)

    def test_set_calls_set_property(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "lftp", "key": "remote_address", "value": "192.168.1.1"}
            self.handler._ConfigHandler__handle_set_config()
        mock_inner.set_property.assert_called_once_with("remote_address", "192.168.1.1")

    def test_set_missing_section_returns_404(self):
        self.mock_config.has_section.return_value = False
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "nosection", "key": "key", "value": "value"}
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(404, response.status_code)
        self.assertIn("no section", response.body.lower())

    def test_set_missing_key_returns_404(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = False
        self.mock_config.nosection = mock_inner
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "nosection", "key": "badkey", "value": "value"}
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(404, response.status_code)
        self.assertIn("no option", response.body.lower())

    def test_set_config_error_returns_400(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        mock_inner.set_property.side_effect = ConfigError("Invalid")
        self.mock_config.lftp = mock_inner
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "lftp", "key": "remote_address", "value": "bad"}
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(400, response.status_code)

    def test_set_raw_value_with_spaces_through_body(self):
        # Replaces test_set_url_decodes_value: value with spaces arrives verbatim in
        # body — no URL decode step (D-04). set_property receives the raw value.
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "lftp", "key": "remote_path", "value": "/path/with spaces"}
            self.handler._ConfigHandler__handle_set_config()
        mock_inner.set_property.assert_called_once_with("remote_path", "/path/with spaces")

    def test_set_raw_value_with_slashes_through_body(self):
        # Replaces test_set_value_with_slashes: slashes in body arrive at set_property
        # verbatim — no encoding/decoding dance (D-04).
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "lftp", "key": "remote_path", "value": "/remote/path/to/dir"}
            self.handler._ConfigHandler__handle_set_config()
        mock_inner.set_property.assert_called_once_with("remote_path", "/remote/path/to/dir")

    def test_set_none_body_returns_400(self):
        # D-07: wrong/absent content-type → bottle.request.json returns None → 400
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = None
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(400, response.status_code)

    def test_set_non_dict_body_returns_400(self):
        # D-07: valid JSON but not a dict (e.g. JSON array) → 400
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = ["not", "a", "dict"]
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(400, response.status_code)

    def test_set_non_string_section_returns_400(self):
        # FINDING 1: non-string section (e.g. list) must return 400, NEVER 500.
        # Proves the isinstance guard fires BEFORE has_section/getattr — a truthy
        # non-string reaching has_section (which expects str) would raise TypeError → 500.
        self.mock_config.has_section = MagicMock()
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": ["general"], "key": "debug", "value": "True"}
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(400, response.status_code)
        # Assert the unsafe config lookup was never reached
        self.mock_config.has_section.assert_not_called()

    def test_set_non_string_key_returns_400(self):
        # FINDING 1: non-string key (e.g. dict) must return 400, NEVER 500.
        # Proves the isinstance guard fires BEFORE any config lookup.
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        self.mock_config.general = mock_inner
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "general", "key": {"x": 1}, "value": "True"}
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(400, response.status_code)
        # The has_section check for section="general" is reached (section IS a valid str),
        # but has_property must NOT be reached (key is non-string — isinstance guard fires)
        mock_inner.has_property.assert_not_called()


class TestConfigHandlerTestSonarrConnection(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.config.sonarr.enabled = False
        self.config.sonarr.sonarr_url = "http://sonarr.example.com:8989"
        self.config.sonarr.sonarr_api_key = "testapikey123"
        self.handler = ConfigHandler(self.config, MagicMock())

    def test_sonarr_missing_url_returns_error(self):
        self.config.sonarr.sonarr_url = ""
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Sonarr URL is required", body["error"])

    def test_sonarr_missing_api_key_returns_error(self):
        self.config.sonarr.sonarr_api_key = ""
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Sonarr API key is required", body["error"])

    @patch('web.handler.config.socket')
    def test_sonarr_rejects_ftp_scheme(self, mock_socket):
        self.config.sonarr.sonarr_url = "ftp://sonarr.local/"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertIn("Only http and https", body["error"])

    @patch('web.handler.config.socket')
    def test_sonarr_rejects_file_scheme(self, mock_socket):
        self.config.sonarr.sonarr_url = "file:///etc/passwd"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertIn("Only http and https", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_accepts_loopback_on_default_port(self, mock_socket, mock_requests):
        # D-02: loopback is allowed on Sonarr's own default port.
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://sonarr.local:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])
        mock_requests.get.assert_called_once()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_accepts_public_ip(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://sonarr.example.com:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_success_returns_version(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])
        self.assertEqual("4.0.2", body["version"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_401_returns_invalid_key(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Invalid API key", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_connection_error(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_requests.get.side_effect = requests.ConnectionError("Connection refused")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertIn("Connection refused", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_timeout(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_requests.get.side_effect = requests.Timeout("Connection timed out")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Connection timed out", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_accepts_loopback_on_radarr_port(self, mock_socket, mock_requests):
        # D-02: either allowed port is accepted on either service's test.
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://localhost:7878"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_accepts_lan_ip_and_reports_version(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("192.168.1.20", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://192.168.1.20:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual({"success": True, "version": "4.0.2"}, body)

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_rejects_cloud_metadata_without_request(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("169.254.169.254", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://169.254.169.254"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual({"success": False, "error": LINK_LOCAL_MSG}, body)
        self.assertEqual(200, response.status_code)
        self.assertNotIn("testapikey123", response.body)
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_invalid_port_returns_json_error(self, mock_socket, mock_requests):
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://sonarr.local:99999"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual(200, response.status_code)
        self.assertEqual(BAD_PORT_MSG, body["error"])
        mock_socket.getaddrinfo.assert_not_called()
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_redirect_to_metadata_is_not_followed(self, mock_socket, mock_requests):
        # D-05 lock: uses a public address (already allowed before and after
        # this phase) so the test exercises redirect handling unchanged by
        # the LAN classifier rewrite, not the classifier itself.
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://8.8.8.8:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertTrue(body["error"].startswith("URL redirects to "))
        self.assertTrue(body["error"].endswith("Update the URL to the final destination."))
        mock_requests.get.assert_called_once()
        _, kwargs = mock_requests.get.call_args
        self.assertIs(False, kwargs["allow_redirects"])

    # --- D-11 (CR-01): parser-differential payloads make no request ---

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_backslash_loopback_payload_makes_no_request(self, mock_socket, mock_requests):
        # urlparse sees host 8.8.8.8 (public); requests/urllib3 would connect
        # to 127.0.0.1:6390. Stubbing getaddrinfo to the public address shows
        # the pre-fix guard would allow this and make the request.
        _resolve_all(mock_socket, "8.8.8.8")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = r"http://127.0.0.1:6390\@8.8.8.8:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"success": False, "error": BAD_CHARS_MSG}, body)
        mock_socket.getaddrinfo.assert_not_called()
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_backslash_metadata_payload_makes_no_request(self, mock_socket, mock_requests):
        # urlparse sees host "sonarr" (a LAN container name, allowed since
        # Phase 125-01); requests/urllib3 would connect to 169.254.169.254.
        _resolve_all(mock_socket, "172.19.0.6")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = r"http://169.254.169.254\@sonarr:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"success": False, "error": BAD_CHARS_MSG}, body)
        mock_socket.getaddrinfo.assert_not_called()
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_backslash_redis_payload_makes_no_request(self, mock_socket, mock_requests):
        # urlparse sees host "sonarr"; requests/urllib3 would connect to
        # 127.0.0.1:6379 (a typical Redis port).
        _resolve_all(mock_socket, "172.19.0.6")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = r"http://127.0.0.1:6379\@sonarr:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"success": False, "error": BAD_CHARS_MSG}, body)
        mock_socket.getaddrinfo.assert_not_called()
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_userinfo_payload_makes_no_request(self, mock_socket, mock_requests):
        _resolve_all(mock_socket, "127.0.0.1")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://a@127.0.0.1:6379"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"success": False, "error": CREDENTIALS_MSG}, body)
        mock_socket.getaddrinfo.assert_not_called()
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_malformed_hostname_returns_json_error(self, mock_socket, mock_requests):
        _resolve_all(mock_socket, "8.8.8.8")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://a..b:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"success": False, "error": BAD_HOSTNAME_MSG}, body)
        mock_socket.getaddrinfo.assert_not_called()
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_trims_whitespace_and_requests_exact_validated_url(self, mock_socket, mock_requests):
        # IN-01: the string requested must equal the string validated.
        _resolve_all(mock_socket, "192.168.1.20")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "  http://192.168.1.20:8989/  "
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])
        mock_requests.get.assert_called_once_with(
            "http://192.168.1.20:8989/api/v3/system/status",
            headers={"X-Api-Key": "testapikey123"},
            timeout=10,
            allow_redirects=False
        )

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_validated_url_equals_requested_url(self, mock_socket, mock_requests):
        _resolve_all(mock_socket, "192.168.1.20")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "  http://192.168.1.20:8989/  "
        with patch.object(ConfigHandler, "_validate_url", wraps=ConfigHandler._validate_url) as mock_validate:
            self.handler._ConfigHandler__handle_test_sonarr_connection()
        validated_url = mock_validate.call_args[0][0]
        requested_url = mock_requests.get.call_args[0][0]
        self.assertEqual(validated_url + "/api/v3/system/status", requested_url)

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_rejects_aws_ipv6_metadata_without_request(self, mock_socket, mock_requests):
        # D-12: fd00:ec2::254 is inside the allowed fc00::/7 ULA range but is
        # AWS's IPv6 instance-metadata endpoint.
        _resolve_all(mock_socket, "fd00:ec2::254")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://metadata.example:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertEqual({"success": False, "error": LINK_LOCAL_MSG}, body)
        mock_requests.get.assert_not_called()

    @patch('requests.adapters.HTTPAdapter.send')
    @patch('web.handler.config.socket')
    def test_sonarr_backslash_payload_never_reaches_transport(self, mock_socket, mock_send):
        # Leaves the real `requests`/urllib3 module in place so this proves
        # the guard, not a mock of requests.get, stops the backslash payload
        # before anything is actually sent on the wire.
        _resolve_all(mock_socket, "8.8.8.8")
        self.config.sonarr.sonarr_url = r"http://127.0.0.1:6390\@8.8.8.8:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        mock_send.assert_not_called()


class TestConfigHandlerTestRadarrConnection(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.config.radarr.enabled = False
        self.config.radarr.radarr_url = "http://localhost:7878"
        self.config.radarr.radarr_api_key = "testapikey123"
        self.handler = ConfigHandler(self.config, MagicMock())

    def test_radarr_missing_url_returns_error(self):
        self.config.radarr.radarr_url = ""
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Radarr URL is required", body["error"])

    def test_radarr_missing_api_key_returns_error(self):
        self.config.radarr.radarr_api_key = ""
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Radarr API key is required", body["error"])

    @patch('web.handler.config.socket')
    def test_radarr_rejects_ftp_scheme(self, mock_socket):
        self.config.radarr.radarr_url = "ftp://radarr.local/"
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertIn("Only http and https", body["error"])

    @patch('web.handler.config.socket')
    def test_radarr_rejects_file_scheme(self, mock_socket):
        self.config.radarr.radarr_url = "file:///etc/passwd"
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertIn("Only http and https", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_accepts_loopback_on_default_port(self, mock_socket, mock_requests):
        # D-02: loopback is allowed on Radarr's own default port.
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "5.0.0"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.radarr.radarr_url = "http://radarr.local:7878"
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])
        mock_requests.get.assert_called_once()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_accepts_public_ip(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "5.0.0"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.radarr.radarr_url = "http://radarr.example.com:7878"
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_success_returns_version(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "5.0.0"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])
        self.assertEqual("5.0.0", body["version"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_401_returns_invalid_key(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Invalid API key", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_connection_error(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_requests.get.side_effect = requests.ConnectionError("Connection refused")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertIn("Connection refused", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_timeout(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_requests.get.side_effect = requests.Timeout("Connection timed out")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("Connection timed out", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_strips_trailing_slash(self, mock_socket, mock_requests):
        self.config.radarr.radarr_url = "http://radarr.example.com:7878/"
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "5.0.0"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout

        self.handler._ConfigHandler__handle_test_radarr_connection()
        mock_requests.get.assert_called_once_with(
            "http://radarr.example.com:7878/api/v3/system/status",
            headers={"X-Api-Key": "testapikey123"},
            timeout=10,
            allow_redirects=False
        )

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_config_key_whitespace_stripped_before_header(self, mock_socket, mock_requests):
        """CR-01: leading/trailing whitespace around a stored key is
        stripped before the X-Api-Key header is built."""
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://sonarr.example.com:8989"
        self.config.sonarr.sonarr_api_key = "  testapikey123\t"

        self.handler._ConfigHandler__handle_test_sonarr_connection()
        mock_requests.get.assert_called_once_with(
            "http://sonarr.example.com:8989/api/v3/system/status",
            headers={"X-Api-Key": "testapikey123"},
            timeout=10,
            allow_redirects=False
        )

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_generic_exception_does_not_leak_details(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_requests.get.side_effect = RuntimeError("internal details here")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertEqual("An unexpected error occurred", body["error"])
        self.assertNotIn("internal details", body["error"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_rejects_loopback_on_other_port_without_request(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.radarr.radarr_url = "http://localhost:9090"
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertEqual({"success": False, "error": LOOPBACK_MSG}, body)
        self.assertEqual(200, response.status_code)
        self.assertNotIn("testapikey123", response.body)
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_redirect_is_not_followed(self, mock_socket, mock_requests):
        # D-05 lock: uses a public address (already allowed before and after
        # this phase) so the test exercises redirect handling unchanged by
        # the LAN classifier rewrite, not the classifier itself.
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 307
        mock_response.headers = {"Location": "/login"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.radarr.radarr_url = "http://8.8.8.8:7878"
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertTrue(body["error"].startswith("URL redirects to "))
        self.assertTrue(body["error"].endswith("Update the URL to the final destination."))
        mock_requests.get.assert_called_once()
        _, kwargs = mock_requests.get.call_args
        self.assertIs(False, kwargs["allow_redirects"])

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_radarr_backslash_loopback_payload_makes_no_request(self, mock_socket, mock_requests):
        # D-11 (CR-01): same parser-differential payload via the Radarr path.
        _resolve_all(mock_socket, "8.8.8.8")
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.radarr.radarr_url = r"http://127.0.0.1:6390\@8.8.8.8:8989"
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"success": False, "error": BAD_CHARS_MSG}, body)
        mock_socket.getaddrinfo.assert_not_called()
        mock_requests.get.assert_not_called()


class TestConfigHandlerRateLimit(unittest.TestCase):
    """Rate limit integration tests for config endpoints."""

    @patch('web.rate_limit.time')
    def test_set_config_rate_limited_at_60_per_60s(self, mock_time):
        """config/set should reject requests after 60 within 60s."""
        from web.rate_limit import rate_limit

        mock_time.time.return_value = 1000.0

        mock_config = MagicMock()
        handler = ConfigHandler(mock_config, MagicMock())
        # Mock config to accept any set operation
        mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        mock_config.lftp = mock_inner

        rate_limited = rate_limit(max_requests=60, window_seconds=60.0, logger=MagicMock())(
            handler._ConfigHandler__handle_set_config
        )

        # Handler now takes no path params — mock bottle.request.json per call (Pitfall 6)
        # First 60 should succeed
        for i in range(60):
            with patch('web.handler.config.bottle') as mock_bottle:
                mock_bottle.request.json = {"section": "lftp", "key": "key{}".format(i), "value": "val"}
                response = rate_limited()
            self.assertNotEqual(429, response.status_code)

        # 61st should be rate limited
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "lftp", "key": "extra", "value": "val"}
            response = rate_limited()
        self.assertEqual(429, response.status_code)
        body = json.loads(response.body)
        self.assertIn("Rate limit", body["error"])

    @patch('web.rate_limit.time')
    def test_test_connection_rate_limited_at_5_per_60s(self, mock_time):
        """test-connection endpoints should reject after 5 within 60s."""
        mock_time.time.return_value = 1000.0
        from web.rate_limit import rate_limit
        from common import Config

        config = Config()
        config.sonarr.enabled = False
        config.sonarr.sonarr_url = "http://sonarr.example.com:8989"
        config.sonarr.sonarr_api_key = "testapikey123"
        handler = ConfigHandler(config, MagicMock())

        rate_limited = rate_limit(max_requests=5, window_seconds=60.0, logger=MagicMock())(
            handler._ConfigHandler__handle_test_sonarr_connection
        )

        # First 5 should proceed (may fail due to connection, but not 429)
        for i in range(5):
            with patch('web.handler.config.requests.get', side_effect=requests.ConnectionError("test")):
                with patch('web.handler.config.socket') as mock_socket:
                    mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
                    mock_socket.gaierror = __import__('socket').gaierror
                    response = rate_limited()
            self.assertNotEqual(429, response.status_code)

        # 6th should be rate limited regardless of connection
        response = rate_limited()
        self.assertEqual(429, response.status_code)


class TestParserDifferentialGuard(unittest.TestCase):
    """D-11 (CR-01, WR-02, D-14): _validate_url must refuse any URL that
    urllib.parse and urllib3 (what requests actually connects to) could
    read differently, before any resolution is attempted, and must refuse
    userinfo, query/fragment, percent-encoded-host, non-ASCII-host and
    malformed-hostname forms up front as well.
    """

    # --- CR-01 direct: the two review payloads ---

    @patch('web.handler.config.socket')
    def test_rejects_backslash_userinfo_loopback_payload(self, mock_socket):
        _resolve_all(mock_socket, "8.8.8.8")
        result = ConfigHandler._validate_url(r"http://127.0.0.1:6390\@8.8.8.8:8989")
        self.assertEqual(BAD_CHARS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_backslash_userinfo_metadata_payload(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url(r"http://169.254.169.254\@sonarr:8989")
        self.assertEqual(BAD_CHARS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    # --- userinfo / query / percent-in-host ---

    @patch('web.handler.config.socket')
    def test_rejects_userinfo_with_username(self, mock_socket):
        _resolve_all(mock_socket, "127.0.0.1")
        result = ConfigHandler._validate_url("http://a@127.0.0.1:6379")
        self.assertEqual(CREDENTIALS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_userinfo_empty_colon(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://:@sonarr:8989")
        self.assertEqual(CREDENTIALS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_query_string(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://sonarr:8989?x=1")
        self.assertEqual(QUERY_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_fragment(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://sonarr:8989#f")
        self.assertEqual(QUERY_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_percent_in_host(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://sonarr%2e:8989")
        self.assertEqual(BAD_URL_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    # --- characters: whitespace, control, non-ASCII (D-14) ---

    @patch('web.handler.config.socket')
    def test_rejects_tab_in_host(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://son\tarr:8989")
        self.assertEqual(BAD_CHARS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_trailing_space(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://sonarr:8989 ")
        self.assertEqual(BAD_CHARS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_trailing_newline(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://sonarr:8989\n")
        self.assertEqual(BAD_CHARS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_leading_space(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url(" http://sonarr:8989")
        self.assertEqual(BAD_CHARS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_non_ascii_host(self, mock_socket):
        # D-14: non-ASCII (internationalised) host names are refused;
        # users enter the xn-- (punycode) form instead.
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://ü.example:8989")
        self.assertEqual(BAD_CHARS_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_accepts_punycode_host(self, mock_socket):
        # D-14: the documented xn-- workaround is proven to work.
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://xn--tda.example:8989")
        self.assertIsNone(result)

    # --- parser-agreement lock: urlparse and urllib3.parse_url agree ---

    @patch('web.handler.config.socket')
    def test_parser_agreement_matches_for_allowed_hosts(self, mock_socket):
        _resolve_all(mock_socket, "172.19.0.6")
        urls = [
            "http://sonarr-v5:8989",
            "http://[fd00::1]:8989",
            "HTTP://Sonarr-V5:8989",
            "https://sonarr.example.com/base",
            "http://my_sonarr:8989",
            "http://192.168.1.20:8989",
        ]
        for url in urls:
            with self.subTest(url=url):
                parsed = urlparse(url)
                u3 = parse_url(url)
                u3_host = (u3.host or "").strip("[]").lower()
                self.assertEqual((parsed.scheme or "").lower(), (u3.scheme or "").lower())
                self.assertEqual(parsed.hostname, u3_host)
                self.assertEqual(parsed.port, u3.port)
                result = ConfigHandler._validate_url(url)
                self.assertIsNone(result)

    # --- WR-02: malformed hostnames, defence-in-depth getaddrinfo errors ---

    @patch('web.handler.config.socket')
    def test_rejects_consecutive_dots_hostname(self, mock_socket):
        _resolve_all(mock_socket, "8.8.8.8")
        result = ConfigHandler._validate_url("http://a..b:8989")
        self.assertEqual(BAD_HOSTNAME_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_dot_only_hostname(self, mock_socket):
        _resolve_all(mock_socket, "8.8.8.8")
        result = ConfigHandler._validate_url("http://.:8989")
        self.assertEqual(BAD_HOSTNAME_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_64_char_label_hostname(self, mock_socket):
        _resolve_all(mock_socket, "8.8.8.8")
        label = "a" * 64
        result = ConfigHandler._validate_url("http://{}.example:8989".format(label))
        self.assertEqual(BAD_HOSTNAME_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_getaddrinfo_unicode_error_returns_cannot_resolve(self, mock_socket):
        mock_socket.getaddrinfo.side_effect = UnicodeError("label empty or too long")
        mock_socket.gaierror = socket.gaierror
        result = ConfigHandler._validate_url("http://host.example:8989")
        self.assertEqual(UNRESOLVABLE_MSG, result)

    @patch('web.handler.config.socket')
    def test_getaddrinfo_value_error_returns_cannot_resolve(self, mock_socket):
        mock_socket.getaddrinfo.side_effect = ValueError("bad host")
        mock_socket.gaierror = socket.gaierror
        result = ConfigHandler._validate_url("http://host.example:8989")
        self.assertEqual(UNRESOLVABLE_MSG, result)


class TestValidateUrl(unittest.TestCase):
    """Full-path coverage for the SSRF guard ConfigHandler._validate_url.

    LAN-01/LAN-02 (Phase 125) replace the single "private or loopback or
    reserved or link-local" check with an explicit allow/refuse classifier:
    named private ranges, CGNAT/Tailscale and public addresses are allowed
    (D-01); loopback is allowed only on Sonarr/Radarr's own default ports,
    8989 or 7878 (D-02); link-local/cloud-metadata, unspecified, multicast,
    other reserved ranges (including IPv4-mapped/compatible/NAT64 bypass
    notations), and loopback on any other port stay refused with a
    category-specific message (D-03). Each case calls _validate_url directly
    with web.handler.config.socket patched (no bottle stack, no real DNS).
    The IP under test is supplied via socket.getaddrinfo's return value at
    addr_info[4][0]. Every resolving test re-assigns
    mock_socket.gaierror = socket.gaierror so the real
    `except socket.gaierror` clause in config.py keeps catching.
    """

    # --- D-01: named private ranges, CGNAT/Tailscale, public -- allowed ---

    @patch('web.handler.config.socket')
    def test_accepts_ipv4_private_10(self, mock_socket):
        _resolve_all(mock_socket, "10.0.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_ipv4_private_192_168(self, mock_socket):
        _resolve_all(mock_socket, "192.168.1.50")
        result = ConfigHandler._validate_url("http://host.example:8989/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_ipv4_private_172_16(self, mock_socket):
        _resolve_all(mock_socket, "172.16.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_ipv4_private_172_31_upper_edge(self, mock_socket):
        _resolve_all(mock_socket, "172.31.255.254")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_ipv6_unique_local(self, mock_socket):
        _resolve_all(mock_socket, "fc00::1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_ipv6_unique_local_fd(self, mock_socket):
        _resolve_all(mock_socket, "fd12:3456::1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_ipv6_mapped_private_ipv4(self, mock_socket):
        _resolve_all(mock_socket, "::ffff:10.0.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_container_name_resolving_to_docker_bridge(self, mock_socket):
        # The Phase 120 D-02 motivating case: a Docker container name
        # resolves to the bridge network's private address (LAN-01).
        _resolve_all(mock_socket, "172.19.0.6")
        result = ConfigHandler._validate_url("http://sonarr-v5:8989")
        self.assertIsNone(result)
        mock_socket.getaddrinfo.assert_called_once_with("sonarr-v5", None)

    @patch('web.handler.config.socket')
    def test_accepts_cgnat_tailscale_range(self, mock_socket):
        _resolve_all(mock_socket, "100.64.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

        _resolve_all(mock_socket, "100.127.255.254")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_public_just_outside_172_16_block(self, mock_socket):
        _resolve_all(mock_socket, "172.32.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_ACCEPTS_ipv6_mapped_PUBLIC_ipv4(self, mock_socket):
        # PROVES the guard does unmap-AND-recheck, not a blanket block of all
        # IPv4-mapped addresses: ::ffff:8.8.8.8 unmaps to the PUBLIC 8.8.8.8.
        _resolve_all(mock_socket, "::ffff:8.8.8.8")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_public_ip(self, mock_socket):
        _resolve_all(mock_socket, "8.8.8.8")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    # --- D-02: loopback, allowed only on Sonarr/Radarr's own ports ---

    @patch('web.handler.config.socket')
    def test_accepts_loopback_on_sonarr_port(self, mock_socket):
        _resolve_all(mock_socket, "127.0.0.1")
        result = ConfigHandler._validate_url("http://localhost:8989")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_loopback_on_radarr_port(self, mock_socket):
        _resolve_all(mock_socket, "127.0.0.1")
        result = ConfigHandler._validate_url("http://localhost:7878/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_loopback_127_range_on_sonarr_port(self, mock_socket):
        _resolve_all(mock_socket, "127.0.1.1")
        result = ConfigHandler._validate_url("http://localhost:8989")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_ipv6_loopback_on_sonarr_port(self, mock_socket):
        _resolve_all(mock_socket, "::1")
        result = ConfigHandler._validate_url("http://[::1]:8989/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_ipv6_mapped_loopback_on_radarr_port(self, mock_socket):
        _resolve_all(mock_socket, "::ffff:127.0.0.1")
        result = ConfigHandler._validate_url("http://localhost:7878")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_https_loopback_on_sonarr_port(self, mock_socket):
        _resolve_all(mock_socket, "127.0.0.1")
        result = ConfigHandler._validate_url("https://localhost:8989")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_loopback_without_port(self, mock_socket):
        _resolve_all(mock_socket, "127.0.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LOOPBACK_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_loopback_without_port(self, mock_socket):
        _resolve_all(mock_socket, "::1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LOOPBACK_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_mapped_loopback_ipv4_without_port(self, mock_socket):
        _resolve_all(mock_socket, "::ffff:127.0.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LOOPBACK_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_loopback_on_other_port(self, mock_socket):
        _resolve_all(mock_socket, "127.0.0.1")
        result = ConfigHandler._validate_url("http://localhost:8080/")
        self.assertEqual(LOOPBACK_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_loopback_https_default_port(self, mock_socket):
        _resolve_all(mock_socket, "127.0.0.1")
        result = ConfigHandler._validate_url("https://localhost/")
        self.assertEqual(LOOPBACK_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_mapped_loopback_on_other_port(self, mock_socket):
        _resolve_all(mock_socket, "::ffff:127.0.0.1")
        result = ConfigHandler._validate_url("http://host.example:22/")
        self.assertEqual(LOOPBACK_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_mixed_resolution_with_loopback_on_wrong_port(self, mock_socket):
        _resolve_all(mock_socket, "192.168.1.10", "127.0.0.1")
        result = ConfigHandler._validate_url("http://host.example:8080/")
        self.assertEqual(LOOPBACK_MSG, result)

    # --- D-03: link-local / cloud metadata ---

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_link_local(self, mock_socket):
        _resolve_all(mock_socket, "169.254.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_link_local(self, mock_socket):
        _resolve_all(mock_socket, "fe80::1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_mapped_link_local_ipv4(self, mock_socket):
        _resolve_all(mock_socket, "::ffff:169.254.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_cloud_metadata(self, mock_socket):
        _resolve_all(mock_socket, "169.254.169.254")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_mapped_cloud_metadata(self, mock_socket):
        _resolve_all(mock_socket, "::ffff:169.254.169.254")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    # --- D-03: unspecified ---

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_unspecified(self, mock_socket):
        _resolve_all(mock_socket, "0.0.0.0")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(UNSPECIFIED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_unspecified(self, mock_socket):
        _resolve_all(mock_socket, "::")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(UNSPECIFIED_MSG, result)

    # --- D-03: multicast (previously an unguarded gap) ---

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_multicast(self, mock_socket):
        _resolve_all(mock_socket, "224.0.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(MULTICAST_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_multicast_ssdp(self, mock_socket):
        _resolve_all(mock_socket, "239.255.255.250")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(MULTICAST_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_multicast(self, mock_socket):
        _resolve_all(mock_socket, "ff02::1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(MULTICAST_MSG, result)

    # --- D-03: other reserved ranges ---

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_documentation_range(self, mock_socket):
        _resolve_all(mock_socket, "192.0.2.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_class_e(self, mock_socket):
        _resolve_all(mock_socket, "240.0.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_limited_broadcast(self, mock_socket):
        _resolve_all(mock_socket, "255.255.255.255")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_deprecated_site_local(self, mock_socket):
        # Orchestrator decision 1 (125-RESEARCH.md Open Question 1): fec0::/10
        # is deprecated IPv6 site-local, treated as D-03's "other reserved".
        _resolve_all(mock_socket, "fec0::1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_compatible_loopback_bypass_on_allowed_port(self, mock_socket):
        # Orchestrator decision 2: ::127.0.0.1 is deprecated IPv4-compatible
        # notation embedding 127.0.0.1 that reports is_loopback=False,
        # is_global=True AND is_reserved=True in stdlib -- the "not
        # is_reserved" guard must catch it even on an allowed port (bypass).
        _resolve_all(mock_socket, "::127.0.0.1")
        result = ConfigHandler._validate_url("http://host.example:8989/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_nat64_embedded_loopback_bypass_on_allowed_port(self, mock_socket):
        # NAT64 well-known prefix embedding 127.0.0.1 in the low 32 bits --
        # same bypass shape as ::127.0.0.1, same guard closes it.
        _resolve_all(mock_socket, "64:ff9b::7f00:1")
        result = ConfigHandler._validate_url("http://host.example:8989/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_nat64_embedded_metadata(self, mock_socket):
        # 64:ff9b::a9fe:a9fe embeds 169.254.169.254 (cloud metadata) in NAT64
        # notation.
        _resolve_all(mock_socket, "64:ff9b::a9fe:a9fe")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    # --- WR-03: IPv6 transition forms, refused by explicit named ranges
    # rather than interpreter is_global/is_reserved tables (gh-113171) ---

    @patch('web.handler.config.socket')
    def test_rejects_6to4_embedded_loopback(self, mock_socket):
        # 2002:7f00:1:: is the 6to4 (2002::/16) encoding of 127.0.0.1.
        _resolve_all(mock_socket, "2002:7f00:1::")
        result = ConfigHandler._validate_url("http://host.example:8989/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_6to4_embedded_metadata(self, mock_socket):
        # 2002:a9fe:a9fe:: is the 6to4 encoding of 169.254.169.254.
        _resolve_all(mock_socket, "2002:a9fe:a9fe::")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_teredo(self, mock_socket):
        _resolve_all(mock_socket, "2001:0:4136:e378:8000:63bf:3fff:fdd2")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_nat64_local_use_embedded_metadata(self, mock_socket):
        # 64:ff9b:1::/48 is the NAT64 local-use prefix.
        _resolve_all(mock_socket, "64:ff9b:1::a9fe:a9fe")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_siit_embedded_metadata(self, mock_socket):
        # ::ffff:0:a.b.c.d (SIIT, ::ffff:0:0:0/96) is distinct from the
        # IPv4-mapped ::ffff:a.b.c.d form unmapped earlier in the function.
        _resolve_all(mock_socket, "::ffff:0:a9fe:a9fe")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(RESERVED_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_ipv6_transition_forms_on_simulated_old_interpreter_tables(self, mock_socket):
        # gh-113171 changed is_global/is_reserved for these prefixes across
        # CPython patch releases. Simulate an interpreter where these forms
        # report is_global=True, is_reserved=False, is_private=False -- the
        # explicit _REFUSED_NETWORKS entries must still refuse them,
        # independent of the interpreter's ipaddress tables.
        addresses = [
            "2002:7f00:1::",
            "2002:a9fe:a9fe::",
            "2001:0:4136:e378:8000:63bf:3fff:fdd2",
            "64:ff9b::7f00:1",
            "64:ff9b:1::7f00:1",
            "::7f00:1",
            "::ffff:0:7f00:1",
        ]
        with patch.object(ipaddress.IPv6Address, "is_global", new_callable=PropertyMock, return_value=True), \
                patch.object(ipaddress.IPv6Address, "is_reserved", new_callable=PropertyMock, return_value=False), \
                patch.object(ipaddress.IPv6Address, "is_private", new_callable=PropertyMock, return_value=False):
            for addr in addresses:
                with self.subTest(addr=addr):
                    _resolve_all(mock_socket, addr)
                    result = ConfigHandler._validate_url("http://host.example:8989/")
                    self.assertEqual(RESERVED_MSG, result)

            # ::1 is classified by is_loopback, which is untouched by the
            # patches above, so it stays allowed on its allowed port.
            _resolve_all(mock_socket, "::1")
            result = ConfigHandler._validate_url("http://host.example:8989/")
            self.assertIsNone(result)

    # --- D-12: cloud-metadata addresses inside otherwise-allowed ranges ---

    @patch('web.handler.config.socket')
    def test_rejects_aws_ipv6_metadata(self, mock_socket):
        # fd00:ec2::254 is AWS's IPv6 instance-metadata endpoint, inside the
        # otherwise-allowed fc00::/7 ULA range.
        _resolve_all(mock_socket, "fd00:ec2::254")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_alibaba_metadata(self, mock_socket):
        # 100.100.100.200 is Alibaba Cloud ECS metadata, inside the
        # otherwise-allowed 100.64.0.0/10 CGNAT/Tailscale range.
        _resolve_all(mock_socket, "100.100.100.200")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_alibaba_metadata_ipv6_mapped(self, mock_socket):
        _resolve_all(mock_socket, "::ffff:100.100.100.200")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    @patch('web.handler.config.socket')
    def test_accepts_ula_neighbor_of_aws_metadata(self, mock_socket):
        _resolve_all(mock_socket, "fd00::10")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_fd00_ec2_neighbor(self, mock_socket):
        _resolve_all(mock_socket, "fd00:ec2::253")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_tailscale_magicdns(self, mock_socket):
        # 100.100.100.100 is Tailscale's MagicDNS address -- must not regress.
        _resolve_all(mock_socket, "100.100.100.100")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_alibaba_metadata_neighbor(self, mock_socket):
        _resolve_all(mock_socket, "100.100.100.201")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    @patch('web.handler.config.socket')
    def test_accepts_cgnat_address(self, mock_socket):
        _resolve_all(mock_socket, "100.64.0.1")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    # --- D-04: mixed resolution -- any refused address refuses the URL ---

    @patch('web.handler.config.socket')
    def test_rejects_multi_address_when_any_refused(self, mock_socket):
        _resolve_all(mock_socket, "8.8.8.8", "169.254.169.254")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(LINK_LOCAL_MSG, result)

    @patch('web.handler.config.socket')
    def test_accepts_multi_address_when_all_allowed(self, mock_socket):
        _resolve_all(mock_socket, "192.168.1.10", "fd00::10")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIsNone(result)

    # --- unparseable / empty resolution -- fail closed ---

    @patch('web.handler.config.socket')
    def test_rejects_unparseable_resolved_address(self, mock_socket):
        # Today this is silently skipped (bare `except ValueError: pass`);
        # D-04 requires it to fail closed instead.
        _resolve_all(mock_socket, "not-an-ip")
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual(UNCHECKABLE_MSG, result)

    @patch('web.handler.config.socket')
    def test_rejects_empty_resolution(self, mock_socket):
        mock_socket.getaddrinfo.return_value = []
        mock_socket.gaierror = socket.gaierror
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual("Cannot resolve hostname", result)

    # --- unresolved hostname ---

    @patch('web.handler.config.socket')
    def test_unresolved_hostname(self, mock_socket):
        mock_socket.getaddrinfo.side_effect = socket.gaierror("name resolution failed")
        mock_socket.gaierror = socket.gaierror
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertEqual("Cannot resolve hostname", result)

    # --- malformed port / URL -- rejected before any socket call (Pitfall 1) ---

    @patch('web.handler.config.socket')
    def test_rejects_non_numeric_port(self, mock_socket):
        result = ConfigHandler._validate_url("http://host.example:abc/")
        self.assertEqual(BAD_PORT_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    @patch('web.handler.config.socket')
    def test_rejects_out_of_range_port(self, mock_socket):
        result = ConfigHandler._validate_url("http://host.example:99999/")
        self.assertEqual(BAD_PORT_MSG, result)
        mock_socket.getaddrinfo.assert_not_called()

    def test_rejects_malformed_ipv6_url(self):
        result = ConfigHandler._validate_url("http://[::1/")
        self.assertEqual(BAD_URL_MSG, result)

    # --- early returns: no socket call ---

    def test_rejects_ftp_scheme(self):
        result = ConfigHandler._validate_url("ftp://host.example/")
        self.assertEqual("Only http and https URLs are allowed", result)

    def test_rejects_no_hostname(self):
        result = ConfigHandler._validate_url("http:///path")
        self.assertEqual("Invalid URL: no hostname", result)

    # --- D-07: refusal messages never mention "private" or echo the host ---

    @patch('web.handler.config.socket')
    def test_refusal_messages_never_mention_private_or_echo_host(self, mock_socket):
        refused_single_addresses = [
            "169.254.169.254", "::ffff:169.254.169.254",
            "0.0.0.0", "::",
            "224.0.0.1", "239.255.255.250", "ff02::1",
            "192.0.2.1", "240.0.0.1", "255.255.255.255",
            "fec0::1", "::127.0.0.1", "64:ff9b::7f00:1", "64:ff9b::a9fe:a9fe",
            "127.0.0.1", "not-an-ip",
        ]
        for ip in refused_single_addresses:
            with self.subTest(ip=ip):
                _resolve_all(mock_socket, ip)
                result = ConfigHandler._validate_url("http://secret-host.example:8080/")
                self.assertIsNotNone(result)
                self.assertNotIn("private", result)
                self.assertNotIn("secret-host", result)


class TestLanRelaxationScope(unittest.TestCase):
    """D-06: the relaxed LAN guard must stay reachable from exactly one
    production call site, and no other outbound-HTTP module may bypass it."""

    @staticmethod
    def _src_root() -> Path:
        # .../src/python/tests/unittests/test_web/test_handler/test_config_handler.py
        return Path(__file__).resolve().parents[4]

    _EXCLUDED_DIR_NAMES = frozenset({
        "venv", "build", "dist", "site", "htmlcov", "node_modules", "__pycache__",
    })

    @classmethod
    def _production_py_files(cls):
        # IN-02: skip tests/, hidden directories (e.g. .venv) and known
        # non-production output directories, so an in-project venv or build
        # artifact never causes a false scope-test failure.
        root = cls._src_root()
        for path in root.rglob("*.py"):
            parts = path.relative_to(root).parts
            if parts[0] == "tests":
                continue
            dir_parts = parts[:-1]
            if any(part.startswith(".") or part in cls._EXCLUDED_DIR_NAMES for part in dir_parts):
                continue
            yield path

    def test_validate_url_only_called_from_test_arr_connection(self):
        config_py = self._src_root() / "web" / "handler" / "config.py"
        tree = ast.parse(config_py.read_text())

        callers = []
        call_count = 0

        class _Visitor(ast.NodeVisitor):
            def __init__(self):
                self._stack = []

            def visit_FunctionDef(self, node):
                self._stack.append(node.name)
                self.generic_visit(node)
                self._stack.pop()

            def visit_Call(self, node):
                nonlocal call_count
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "_validate_url":
                    call_count += 1
                    if self._stack:
                        callers.append(self._stack[-1])
                self.generic_visit(node)

        _Visitor().visit(tree)
        self.assertEqual({"_test_arr_connection"}, set(callers))
        self.assertEqual(1, call_count)

    def test_validate_url_not_referenced_outside_config_handler(self):
        root = self._src_root()
        matches = {
            path.relative_to(root).as_posix()
            for path in self._production_py_files()
            if "_validate_url" in path.read_text()
        }
        self.assertEqual({"web/handler/config.py"}, matches)

    def test_outbound_http_modules_are_known(self):
        # IN-02: widened to catch indented imports and modules beyond
        # `requests` (urllib3, urllib.request, http.client, aiohttp, httpx).
        root = self._src_root()
        pattern = re.compile(
            r"^\s*(?:import|from)\s+(?:requests|urllib3|urllib\.request|http\.client|aiohttp|httpx)\b",
            re.M,
        )
        matches = {
            path.relative_to(root).as_posix()
            for path in self._production_py_files()
            if pattern.search(path.read_text())
        }
        self.assertEqual({"web/handler/config.py", "controller/arr_queue.py"}, matches)

        arr_queue = root / "controller" / "arr_queue.py"
        self.assertNotIn("_validate_url", arr_queue.read_text())
