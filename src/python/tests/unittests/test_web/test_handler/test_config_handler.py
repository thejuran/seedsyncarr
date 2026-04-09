import json
import socket
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import requests

from common import Config, ConfigError
from web.handler.config import ConfigHandler


class TestConfigHandlerGet(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.handler = ConfigHandler(self.mock_config)

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
        self.handler = ConfigHandler(self.mock_config)

    def test_set_valid_returns_200(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        response = self.handler._ConfigHandler__handle_set_config("lftp", "remote_address", quote("192.168.1.1"))
        self.assertEqual(200, response.status_code)

    def test_set_calls_set_property(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        self.handler._ConfigHandler__handle_set_config("lftp", "remote_address", quote("192.168.1.1"))
        mock_inner.set_property.assert_called_once_with("remote_address", "192.168.1.1")

    def test_set_missing_section_returns_404(self):
        self.mock_config.has_section.return_value = False
        response = self.handler._ConfigHandler__handle_set_config("nosection", "key", quote("value"))
        self.assertEqual(404, response.status_code)
        self.assertIn("no section", response.body.lower())

    def test_set_missing_key_returns_404(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = False
        self.mock_config.nosection = mock_inner
        response = self.handler._ConfigHandler__handle_set_config("nosection", "badkey", quote("value"))
        self.assertEqual(404, response.status_code)
        self.assertIn("no option", response.body.lower())

    def test_set_config_error_returns_400(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        mock_inner.set_property.side_effect = ConfigError("Invalid")
        self.mock_config.lftp = mock_inner
        response = self.handler._ConfigHandler__handle_set_config("lftp", "remote_address", quote("bad"))
        self.assertEqual(400, response.status_code)

    def test_set_url_decodes_value(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        self.handler._ConfigHandler__handle_set_config("lftp", "remote_path", quote("/path/with spaces"))
        mock_inner.set_property.assert_called_once_with("remote_path", "/path/with spaces")

    def test_set_value_with_slashes(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        self.handler._ConfigHandler__handle_set_config("lftp", "remote_path", quote("/remote/path/to/dir"))
        mock_inner.set_property.assert_called_once_with("remote_path", "/remote/path/to/dir")


class TestConfigHandlerTestSonarrConnection(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.config.sonarr.enabled = False
        self.config.sonarr.sonarr_url = "http://sonarr.example.com:8989"
        self.config.sonarr.sonarr_api_key = "testapikey123"
        self.handler = ConfigHandler(self.config)

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

    @patch('web.handler.config.socket')
    def test_sonarr_rejects_private_ip(self, mock_socket):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        mock_socket.gaierror = socket.gaierror
        self.config.sonarr.sonarr_url = "http://sonarr.local:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertIn("private", body["error"])

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


class TestConfigHandlerTestRadarrConnection(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.config.radarr.enabled = False
        self.config.radarr.radarr_url = "http://localhost:7878"
        self.config.radarr.radarr_api_key = "testapikey123"
        self.handler = ConfigHandler(self.config)

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

    @patch('web.handler.config.socket')
    def test_radarr_rejects_private_ip(self, mock_socket):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        mock_socket.gaierror = socket.gaierror
        self.config.radarr.radarr_url = "http://radarr.local:7878"
        response = self.handler._ConfigHandler__handle_test_radarr_connection()
        body = json.loads(response.body)
        self.assertFalse(body["success"])
        self.assertIn("private", body["error"])

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
