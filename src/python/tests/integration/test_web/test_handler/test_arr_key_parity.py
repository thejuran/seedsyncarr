"""
Cross-path parity for the Sonarr/Radarr API key.

Save (POST /server/config/set), Test Connection (ConfigHandler._test_arr_connection)
and the queue check (ArrQueueClient) all read or write the same real Config here.

Parity contract: parity is claimed for string input only. For a raw key that is
a non-empty string, the three paths give the same accept/reject verdict as
is_valid_arr_api_key(normalize_arr_api_key(raw)), and an accepted key is sent
as the same trimmed value everywhere. Null, empty and non-string input is
handled by each path's own boundary guard and is covered by its own test, not
by the parity table.
"""
import json
import logging
import socket
from unittest.mock import MagicMock, patch

import requests

from controller.arr_queue import ArrQueueClient
from tests.integration.test_web.test_web_app import BaseTestWebApp
from tests.unittests.test_common.test_arr_api_key import RULE_CASES
from tests.unittests.test_controller.test_arr_queue import settle, _response, _bind_exceptions
from web.handler.config import ConfigHandler


K = "abcDEF123-parity"
GOOD_KEY = "goodKEY1"
SONARR_URL = "http://sonarr.internal.example:8989"
RADARR_URL = "http://radarr.internal.example:7878"

ARRS = {
    "sonarr": ("Sonarr", "sonarr_api_key", "sonarr_url", SONARR_URL),
    "radarr": ("Radarr", "radarr_api_key", "radarr_url", RADARR_URL),
}


def _sent_key(mock_requests) -> str:
    """X-Api-Key header of the single outbound request made through the mock."""
    mock_requests.get.assert_called_once()
    return mock_requests.get.call_args[1]["headers"]["X-Api-Key"]


def _wire_test_connection(mock_requests, mock_socket):
    """Let a valid key reach the request and come back as a 200 with a version."""
    mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
    mock_socket.gaierror = socket.gaierror
    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {"version": "4.0.2"}
    mock_requests.get.return_value = ok
    mock_requests.ConnectionError = requests.ConnectionError
    mock_requests.Timeout = requests.Timeout


def _wire_queue(mock_requests):
    """Mocked arr answers the queue request with an empty queue."""
    _bind_exceptions(mock_requests)
    mock_requests.get.return_value = _response(200, [b"[]"])


class _RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class TestArrKeyParity(BaseTestWebApp):
    def setUp(self):
        super().setUp()
        config = self.context.config
        config.sonarr.enabled = True
        config.sonarr.sonarr_url = SONARR_URL
        config.radarr.enabled = True
        config.radarr.radarr_url = RADARR_URL
        self.handler = ConfigHandler(config, self.context)
        self.client = ArrQueueClient(self.context)

    def tearDown(self):
        for code in ("sonarr", "radarr"):
            settle(self.client, code)
        super().tearDown()

    # -- helpers -----------------------------------------------------------

    def _save(self, code: str, value):
        _label, key_prop, _url_prop, _url = ARRS[code]
        return self.test_app.post_json(
            "/server/config/set",
            {"section": code, "key": key_prop, "value": value},
            expect_errors=True,
        )

    def _stored(self, code: str):
        _label, key_prop, _url_prop, _url = ARRS[code]
        return getattr(getattr(self.context.config, code), key_prop)

    def _store(self, code: str, value):
        _label, key_prop, _url_prop, _url = ARRS[code]
        setattr(getattr(self.context.config, code), key_prop, value)

    def _target(self, code: str):
        targets = [t for t in self.client.enabled_targets() if t.code == code]
        self.assertEqual(1, len(targets))
        return targets[0]

    def _test_connection(self, code: str, raw_key):
        """Run Test Connection against a mocked arr; return (body, mock_requests)."""
        label, _key_prop, url_prop, _url = ARRS[code]
        url = getattr(getattr(self.context.config, code), url_prop)
        with patch("web.handler.config.requests") as mock_requests, \
                patch("web.handler.config.socket") as mock_socket:
            _wire_test_connection(mock_requests, mock_socket)
            response = self.handler._test_arr_connection(label, url, raw_key)
        return json.loads(response.body), mock_requests

    def _queue_check(self, code: str):
        """Run one queue check on the stored key; return (fetch_id, outcome, mock_requests)."""
        with patch("controller.arr_queue.requests") as mock_requests:
            _wire_queue(mock_requests)
            fetch_id = self.client.start_fetch(self._target(code))
            settled = settle(self.client, code)
            outcome = self.client.poll(code) if fetch_id is not None else None
        self.assertTrue(settled)
        return fetch_id, outcome, mock_requests

    def _assert_queue_sent(self, code: str, expected_key: str):
        fetch_id, outcome, mock_requests = self._queue_check(code)
        self.assertIsNotNone(fetch_id)
        self.assertEqual([], outcome.records)
        self.assertEqual(expected_key, _sent_key(mock_requests))

    def _assert_test_connection_sent(self, code: str, raw_key, expected_key: str):
        body, mock_requests = self._test_connection(code, raw_key)
        self.assertIs(True, body["success"])
        self.assertEqual("4.0.2", body["version"])
        self.assertEqual(expected_key, _sent_key(mock_requests))

    def _padded_key_through_all_paths(self, code: str):
        label, key_prop, _url_prop, _url = ARRS[code]
        resp = self._save(code, "\t" + K + "  ")
        self.assertEqual(200, resp.status_int)
        self.assertEqual("{}.{} updated".format(code, key_prop), resp.text)
        stored = self._stored(code)
        self.assertEqual(K, stored)

        self._assert_test_connection_sent(code, stored, K)

        self.assertEqual(K, self._target(code).api_key)
        self._assert_queue_sent(code, K)

    # -- tests -------------------------------------------------------------

    def test_padded_key_saved_then_same_key_on_all_three_paths(self):
        self._padded_key_through_all_paths("sonarr")

    def test_padded_key_saved_then_same_key_on_all_three_paths_radarr(self):
        self._padded_key_through_all_paths("radarr")

    def test_padded_key_in_live_config_agrees_between_test_connection_and_queue(self):
        # A padded key placed in the live config without going through Save.
        self._store("sonarr", "  " + K + "\n")
        self._assert_test_connection_sent("sonarr", self._stored("sonarr"), K)
        self._assert_queue_sent("sonarr", K)

    def test_rule_table_verdicts_agree_on_all_three_paths(self):
        rows = [row for row in RULE_CASES if isinstance(row[0], str) and row[0] != ""]
        self.assertEqual(15, len(rows))
        for raw, normalized, valid in rows:
            with self.subTest(raw=repr(raw)):
                # (a) Save
                self._store("sonarr", GOOD_KEY)
                resp = self._save("sonarr", raw)
                if valid:
                    self.assertEqual(200, resp.status_int)
                    self.assertEqual(normalized, self._stored("sonarr"))
                else:
                    self.assertEqual(400, resp.status_int)
                    self.assertEqual(GOOD_KEY, self._stored("sonarr"))
                    if normalized == "":
                        self.assertEqual("Invalid request body", resp.text)
                    else:
                        self.assertEqual("Sonarr API key contains invalid characters", resp.text)

                # (b) Test Connection
                body, mock_requests = self._test_connection("sonarr", raw)
                if valid:
                    self.assertIs(True, body["success"])
                    self.assertEqual(normalized, _sent_key(mock_requests))
                else:
                    self.assertIs(False, body["success"])
                    if normalized == "":
                        self.assertEqual("Sonarr API key is required", body["error"])
                    else:
                        self.assertEqual("Sonarr API key contains invalid characters", body["error"])
                    mock_requests.get.assert_not_called()

                # (c) Queue check on the same raw value placed in the live config
                self._store("sonarr", raw)
                fetch_id, outcome, mock_requests = self._queue_check("sonarr")
                if valid:
                    self.assertIsNotNone(fetch_id)
                    self.assertEqual([], outcome.records)
                    self.assertEqual(normalized, _sent_key(mock_requests))
                else:
                    self.assertIsNone(fetch_id)
                    mock_requests.get.assert_not_called()

    def test_boundary_specific_inputs_are_handled_by_each_path(self):
        # Save: the empty-value guard runs before the key rule.
        for value in (None, ""):
            with self.subTest(save=repr(value)):
                self._store("sonarr", GOOD_KEY)
                resp = self._save("sonarr", value)
                self.assertEqual(400, resp.status_int)
                self.assertEqual("Invalid request body", resp.text)
                self.assertEqual(GOOD_KEY, self._stored("sonarr"))

        # Save turns a number into text before applying the rule.
        self._store("sonarr", GOOD_KEY)
        resp = self._save("sonarr", 12345)
        self.assertEqual(200, resp.status_int)
        self.assertEqual("sonarr.sonarr_api_key updated", resp.text)
        self.assertEqual("12345", self._stored("sonarr"))

        # Test Connection: a null or empty key is reported as required.
        for value in (None, ""):
            with self.subTest(test_connection=repr(value)):
                body, mock_requests = self._test_connection("sonarr", value)
                self.assertIs(False, body["success"])
                self.assertEqual("Sonarr API key is required", body["error"])
                mock_requests.get.assert_not_called()

        # Queue: null, empty and non-string keys are skipped.
        for value in (None, "", 123):
            with self.subTest(queue=repr(value)):
                self._store("sonarr", value)
                self.assertEqual("", self._target("sonarr").api_key)
                fetch_id, _outcome, mock_requests = self._queue_check("sonarr")
                self.assertIsNone(fetch_id)
                mock_requests.get.assert_not_called()

    def test_no_key_material_in_parity_logs_or_responses(self):
        recorder = _RecordingHandler()
        root = logging.getLogger()
        root.addHandler(recorder)
        self.addCleanup(root.removeHandler, recorder)

        bodies = []
        resp = self._save("sonarr", "  LEAKPROBE-" + K + "  ")
        self.assertEqual(200, resp.status_int)
        bodies.append(resp.text)
        saved = self._stored("sonarr")

        resp = self._save("sonarr", "LEAKPROBE inner space")
        self.assertEqual(400, resp.status_int)
        bodies.append(resp.text)

        # Skipped queue check on an invalid key placed in the live config.
        self._store("sonarr", "LEAKPROBE inner space")
        fetch_id, _outcome, mock_requests = self._queue_check("sonarr")
        self.assertIsNone(fetch_id)
        mock_requests.get.assert_not_called()

        # Successful queue check on the saved key.
        self._store("sonarr", saved)
        self._assert_queue_sent("sonarr", "LEAKPROBE-" + K)

        self.assertTrue(recorder.messages, "expected the parity run to log something")
        for message in recorder.messages:
            self.assertNotIn("LEAKPROBE", message)
        for body in bodies:
            self.assertNotIn("LEAKPROBE", body)
