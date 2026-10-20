"""Sonarr 5 Test Connection compatibility (SON5-01).

Feeds the recorded Sonarr 5 ``GET /api/v3/system/status`` body to the real
``ConfigHandler`` Test Connection path. The expected version always comes from
the fixture manifest (``fixtures.tested_version()``), never from a literal, so the
tests hold unchanged when the fixture is replaced by a newer capture (D-01, D-08).

The LAN-guard test records a known limitation rather than a fix: a Sonarr
reached by docker-network container name resolves to a private address, which
the SSRF guard rejects before Sonarr is contacted. Relaxing that guard is
deferred to the Reliability milestone (D-02).
"""
import json
import re
import socket
import unittest
from unittest.mock import MagicMock, patch

import requests

from common import Config
from web.handler.config import ConfigHandler
from tests.unittests.test_sonarr5 import fixtures
from tests.unittests.test_sonarr5.fixtures import fixture_bytes, fixture_json

_STATUS = "system_status.json"
# Shared address space (RFC 6598) example address, not a real host.
_CGNAT_EXAMPLE_IP = "100.64.0.1"


def _resolve_to(mock_socket, ip: str):
    mock_socket.getaddrinfo.return_value = [(None, None, None, None, (ip, 0))]
    mock_socket.gaierror = socket.gaierror


def _bind_request_errors(mock_requests):
    mock_requests.ConnectionError = requests.ConnectionError
    mock_requests.Timeout = requests.Timeout


class TestSonarr5SystemStatus(unittest.TestCase):
    def setUp(self):
        # Fresh handler per test so the Test Connection rate limiter never trips.
        self.config = Config()
        self.config.sonarr.enabled = False
        self.config.sonarr.sonarr_url = "http://sonarr.example.invalid:8989"
        self.config.sonarr.sonarr_api_key = "testapikey123"
        self.handler = ConfigHandler(self.config)

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr5_status_fixture_returns_success_with_recorded_version(self, mock_socket, mock_requests):
        _resolve_to(mock_socket, "8.8.8.8")
        _bind_request_errors(mock_requests)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = lambda: json.loads(fixture_bytes(_STATUS))
        mock_requests.get.return_value = mock_response

        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)

        self.assertEqual({"success": True, "version": fixtures.tested_version()}, body)
        self.assertTrue(body["version"].startswith("5."))
        mock_requests.get.assert_called_once()
        args, kwargs = mock_requests.get.call_args
        self.assertTrue(args[0].endswith("/api/v3/system/status"))
        self.assertEqual({"X-Api-Key": self.config.sonarr.sonarr_api_key}, kwargs["headers"])
        self.assertEqual(10, kwargs["timeout"])
        self.assertIs(False, kwargs["allow_redirects"])

    def test_fixture_version_matches_manifest(self):
        self.assertEqual(fixtures.tested_version(), fixture_json(_STATUS)["version"])
        self.assertIsNotNone(re.fullmatch(r"5\.\d+\.\d+\.\d+", fixtures.tested_version()))

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_docker_network_url_rejected_by_lan_guard_known_limitation(self, mock_socket, mock_requests):
        """Known limitation (D-02, deferred to Reliability item 5).

        A Sonarr addressed by docker-network container name resolves to a
        private bridge address. The SSRF guard rejects it before any request is
        made. This documents current behavior; it is not a fix.
        """
        _resolve_to(mock_socket, "172.19.0.6")
        _bind_request_errors(mock_requests)
        self.config.sonarr.sonarr_url = "http://sonarr-v5:8989"

        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)

        self.assertFalse(body["success"])
        self.assertIn("private", body["error"])
        mock_requests.get.assert_not_called()

    @patch('web.handler.config.socket')
    def test_cgnat_address_passes_url_validation(self, mock_socket):
        _resolve_to(mock_socket, _CGNAT_EXAMPLE_IP)
        self.assertIsNone(ConfigHandler._validate_url("http://{}:8990".format(_CGNAT_EXAMPLE_IP)))

    def test_status_fixture_extra_keys_are_present_and_harmless(self):
        status = fixture_json(_STATUS)
        self.assertEqual("Sonarr", status["appName"])
        self.assertIn("branch", status)


if __name__ == "__main__":
    unittest.main()
