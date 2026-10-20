"""Sonarr 5 webhook compatibility (SON5-03).

Drives the recorded Sonarr 5 webhook bodies (fixture manifest build:
``fixtures.tested_version()``) through two layers:

* the real Bottle web layer, posting the raw fixture bytes so HMAC verification
  runs over exactly what Sonarr 5 sends;
* a real ``WebhookManager`` with decoy model entries, proving the Download event
  marks exactly one file and that ambiguous names are still rejected.

File and directory names are derived from the fixture, never written as
literals, so these tests hold unchanged when the fixtures are replaced by newer
captures.
"""
import hashlib
import hmac
import json
import os
import re
import unittest
from unittest.mock import MagicMock

from controller.webhook_manager import WebhookManager
from tests.integration.test_web.test_web_app import BaseTestWebApp
from tests.unittests.test_sonarr5 import fixtures
from tests.unittests.test_sonarr5.fixtures import fixture_bytes, fixture_json

_ROUTE = "/server/webhook/sonarr"
_TEST_EVENT = "webhook_test.json"
_DOWNLOAD_EVENT = "webhook_download.json"
_PROVENANCE = "eventType=Download, episodeFile.sourcePath"
_SECRET = "sonarr5-test-secret"


def _compute_hmac(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _download_source_path() -> str:
    return fixture_json(_DOWNLOAD_EVENT)["episodeFile"]["sourcePath"]


def _child_and_root():
    """Return (child file basename, root directory name) from the Download fixture."""
    source_path = _download_source_path()
    return os.path.basename(source_path), os.path.basename(os.path.dirname(source_path))


def _next_episode_name(name: str) -> str:
    """Return ``name`` with its SxxEyy episode number bumped (a sibling episode)."""
    def bump(match):
        number = match.group(2)
        return match.group(1) + str(int(number) + 1).zfill(len(number))
    sibling = re.sub(r"([Ss]\d+[Ee])(\d+)", bump, name, count=1)
    if sibling == name:
        stem, ext = os.path.splitext(name)
        sibling = stem + ".sibling" + ext
    return sibling


def _lookup(*entries):
    """Build the process() lookup from (basename, path, root) triples."""
    result = {}
    for basename, path, root in entries:
        result.setdefault(basename.lower(), {})[path] = root
    return result


class TestSonarr5WebhookWebLayer(BaseTestWebApp):
    @property
    def _webhook_manager_mock(self):
        return self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager

    def _post(self, raw: bytes, headers=None, expect_errors=False):
        return self.test_app.post(
            _ROUTE,
            params=raw,
            content_type="application/json",
            headers=headers or {},
            expect_errors=expect_errors,
        )

    def _require_secret(self):
        self.context.config.general.webhook_secret = _SECRET
        self.context.config.general.webhook_require_secret = True

    def test_fixture_build_is_sonarr5(self):
        self.assertTrue(fixtures.tested_version().startswith("5."))

    def test_test_event_returns_test_ok_without_enqueue(self):
        resp = self._post(fixture_bytes(_TEST_EVENT))
        self.assertEqual(200, resp.status_int)
        self.assertEqual("Test OK", resp.text)
        self._webhook_manager_mock.enqueue_import.assert_not_called()

    def test_download_event_enqueues_source_path_basename_once(self):
        resp = self._post(fixture_bytes(_DOWNLOAD_EVENT))
        self.assertEqual(200, resp.status_int)
        self.assertEqual("OK", resp.text)
        self._webhook_manager_mock.enqueue_import.assert_called_once_with(
            "Sonarr", os.path.basename(_download_source_path()), provenance=_PROVENANCE
        )

    def test_signed_raw_download_body_is_accepted(self):
        self._require_secret()
        raw = fixture_bytes(_DOWNLOAD_EVENT)
        resp = self._post(raw, headers={"X-Webhook-Signature": _compute_hmac(_SECRET, raw)})
        self.assertEqual(200, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_called_once_with(
            "Sonarr", os.path.basename(_download_source_path()), provenance=_PROVENANCE
        )

    def test_unsigned_download_body_is_rejected(self):
        self._require_secret()
        resp = self._post(fixture_bytes(_DOWNLOAD_EVENT), expect_errors=True)
        self.assertEqual(401, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_not_called()

    def test_signature_over_reserialized_json_is_rejected(self):
        """The signature must cover the exact bytes Sonarr 5 sent, not a re-encoding."""
        self._require_secret()
        raw = fixture_bytes(_DOWNLOAD_EVENT)
        reserialized = json.dumps(json.loads(raw)).encode("utf-8")
        self.assertNotEqual(raw, reserialized)
        resp = self._post(
            raw,
            headers={"X-Webhook-Signature": _compute_hmac(_SECRET, reserialized)},
            expect_errors=True,
        )
        self.assertEqual(401, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_not_called()


class TestSonarr5WebhookExactFile(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()
        self.manager = WebhookManager(self.context)
        self.child, self.root = _child_and_root()

    def _decoy_name(self, suffix: str) -> str:
        stem, ext = os.path.splitext(self.child)
        return stem + suffix + ext

    def test_download_marks_exactly_one_file_among_decoys(self):
        sibling = _next_episode_name(self.child)
        self.assertNotEqual(self.child, sibling)
        other_root = self.root + "-OTHERGROUP"
        near_identical = self._decoy_name("-OTHERGROUP")
        name_to_paths = _lookup(
            (self.root, self.root, self.root),
            (self.child, "{}/{}".format(self.root, self.child), self.root),
            (sibling, "{}/{}".format(self.root, sibling), self.root),
            (other_root, other_root, other_root),
            (near_identical, "{}/{}".format(other_root, near_identical), other_root),
            ("Unrelated.Release", "Unrelated.Release", "Unrelated.Release"),
            ("unrelated.mkv", "Unrelated.Release/unrelated.mkv", "Unrelated.Release"),
        )
        self.manager.enqueue_import("Sonarr", self.child)
        self.assertEqual([(self.root, self.child)], self.manager.process(name_to_paths))

    def test_same_basename_under_two_roots_is_rejected(self):
        other_root = self.root + "-OTHERGROUP"
        name_to_paths = _lookup(
            (self.child, "{}/{}".format(self.root, self.child), self.root),
            (self.child, "{}/{}".format(other_root, self.child), other_root),
        )
        self.manager.enqueue_import("Sonarr", self.child)
        self.assertEqual([], self.manager.process(name_to_paths))


if __name__ == "__main__":
    unittest.main()
