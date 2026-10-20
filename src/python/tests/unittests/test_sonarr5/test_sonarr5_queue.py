"""SON5-02: Sonarr 5 queue/details replay through the real client and gate.

The committed queue fixtures are fed to ``ArrQueueClient`` as raw byte chunks
(exactly what Sonarr 5 sent), and the resulting records drive the real
``CompletionGate``. The tracked download is identified by the manifest's
``queue_target_download_id`` and the Sonarr build is the one recorded in the
manifest, so no root name or id is hardcoded here.
"""
import json
import os
import unittest
from typing import Dict, List
from unittest.mock import MagicMock, patch

import requests

from controller.arr_queue import FETCH_DONE, ArrQueueClient, ArrTarget, QueueRecord
from controller.completion_gate import CompletionGate, Verdict
from tests.unittests.test_controller.test_arr_queue import (
    API_KEY,
    FakeClock,
    _bind_exceptions,
    _response,
    settle,
)
from tests.unittests.test_sonarr5.fixtures import (
    fixture_bytes,
    fixture_json,
    queue_target_download_id,
)


SONARR_URL = "http://sonarr.example.invalid:8989/"
INCOMPLETE = "queue_details_incomplete.json"
COMPLETE = "queue_details_complete.json"
CHUNK = 4096


def _chunks(raw: bytes) -> List[bytes]:
    return [raw[i:i + CHUNK] for i in range(0, len(raw), CHUNK)]


def _serve(mock_requests, raw: bytes, status: int = 200):
    """Answer the next queue/details GET with ``raw`` split into byte chunks."""
    _bind_exceptions(mock_requests)
    mock_requests.get.side_effect = None
    mock_requests.get.return_value = _response(status, _chunks(raw))


def _target_record(fixture_name: str) -> dict:
    """The record tracking the manifest's target download in ``fixture_name``."""
    matches = [r for r in fixture_json(fixture_name) if r.get("downloadId") == queue_target_download_id()]
    if len(matches) != 1:
        raise AssertionError(f"{fixture_name}: expected 1 target record, found {len(matches)}")
    return matches[0]


_UNRELATED_DOWNLOAD_ID = "F" * 40
_UNRELATED_ROOT = "Other.Show.S01E01.1080p.WEB.h264-OTHER"


def _unrelated_record(fixture_name: str) -> dict:
    """A completed record for another download, derived from the captured target record.

    The live capture queue held only the tracked download, so the unrelated record is
    the captured record with a different downloadId and output root; every other field
    keeps the exact shape Sonarr 5 sent.
    """
    record = dict(_target_record(fixture_name))
    parent = os.path.dirname(record["outputPath"].rstrip("/\\"))
    record.update(
        downloadId=_UNRELATED_DOWNLOAD_ID,
        outputPath="{}/{}".format(parent, _UNRELATED_ROOT),
        title=_UNRELATED_ROOT,
        status="completed",
        sizeleft=0,
    )
    return record


def _root_of(record: dict) -> str:
    return os.path.basename(record["outputPath"].rstrip("/\\"))


def _decide(gate: CompletionGate, client: ArrQueueClient, candidates) -> Dict[str, Verdict]:
    """Start a fetch, let the worker finish, then apply the snapshot."""
    gate.evaluate(candidates)
    assert settle(client, "sonarr")
    return gate.evaluate(candidates)


class Sonarr5QueueBase(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        cfg = self.context.config
        cfg.sonarr.enabled = True
        cfg.sonarr.sonarr_url = SONARR_URL
        cfg.sonarr.sonarr_api_key = API_KEY
        cfg.radarr.enabled = False
        self.clock = FakeClock()
        self.client = ArrQueueClient(self.context, clock=self.clock)
        self.gate = CompletionGate(self.context, self.client, clock=self.clock)
        self.sonarr = ArrTarget("Sonarr", "sonarr", SONARR_URL, API_KEY)
        self.target_root = _root_of(_target_record(INCOMPLETE))

    def tearDown(self):
        for code in ("sonarr", "radarr"):
            settle(self.client, code)

    def advance(self, seconds: float):
        self.clock.now += seconds


@patch("controller.arr_queue.requests")
class TestSonarr5QueueReplay(Sonarr5QueueBase):
    def test_sonarr5_queue_fixture_normalizes_with_lowercase_sizeleft(self, mock_requests):
        _serve(mock_requests, fixture_bytes(COMPLETE))
        self.assertIsNotNone(self.client.start_fetch(self.sonarr))
        self.assertTrue(settle(self.client, "sonarr"))
        outcome = self.client.poll("sonarr")

        self.assertEqual(FETCH_DONE, outcome.state)
        expected = [
            QueueRecord(_root_of(r), r["downloadId"], r["status"], r["sizeleft"], True, None)
            for r in fixture_json(COMPLETE)
        ]
        self.assertEqual(expected, outcome.records)
        target = [rec for rec in outcome.records if rec.download_id == queue_target_download_id()]
        self.assertEqual(1, len(target))
        self.assertEqual("completed", target[0].status.lower())
        self.assertEqual(0, target[0].sizeleft)

    def test_incomplete_fixture_holds_still_downloading(self, mock_requests):
        _serve(mock_requests, fixture_bytes(INCOMPLETE))
        record = _target_record(INCOMPLETE)
        self.assertNotEqual(0, record["sizeleft"])

        verdict = _decide(self.gate, self.client, {self.target_root: record["size"]})[self.target_root]

        self.assertTrue(verdict.held)
        self.assertFalse(verdict.proven)
        self.assertEqual("still_downloading", verdict.reason)
        self.assertEqual({self.target_root: "still_downloading"}, self.gate.holds)

    def test_same_download_complete_fixture_releases(self, mock_requests):
        incomplete = _target_record(INCOMPLETE)
        complete = _target_record(COMPLETE)
        # Both snapshots track the same download, captured in both states.
        self.assertEqual(queue_target_download_id(), incomplete["downloadId"])
        self.assertEqual(queue_target_download_id(), complete["downloadId"])
        self.assertEqual(_root_of(incomplete), _root_of(complete))
        candidates = {self.target_root: incomplete["size"]}

        _serve(mock_requests, fixture_bytes(INCOMPLETE))
        held = _decide(self.gate, self.client, candidates)[self.target_root]
        self.assertEqual("still_downloading", held.reason)

        _serve(mock_requests, fixture_bytes(COMPLETE))
        self.advance(CompletionGate.REFRESH_INTERVAL_SECS + 1)
        verdict = _decide(self.gate, self.client, candidates)[self.target_root]

        self.assertTrue(verdict.proven)
        self.assertFalse(verdict.held)
        self.assertEqual({}, self.gate.holds)

    def test_unrelated_root_never_released_by_other_download(self, mock_requests):
        _serve(mock_requests, fixture_bytes(COMPLETE))
        root = "Other.Root.S09E09-NOPE"

        verdict = _decide(self.gate, self.client, {root: 1000})[root]

        self.assertFalse(verdict.proven)
        self.assertTrue(verdict.held)
        self.assertEqual("no_queue_entry", verdict.reason)


@patch("controller.arr_queue.requests")
class TestSonarr5QueueNegatives(Sonarr5QueueBase):
    def _assert_held(self, verdict: Verdict, reason: str):
        self.assertFalse(verdict.proven)
        self.assertTrue(verdict.held)
        self.assertEqual(reason, verdict.reason)

    def test_http_500_holds_sonarr_unavailable_never_proves(self, mock_requests):
        _serve(mock_requests, b"", status=500)
        verdict = _decide(self.gate, self.client, {self.target_root: 1000})[self.target_root]
        self._assert_held(verdict, "sonarr_unavailable")
        self.assertEqual({self.target_root: "sonarr_unavailable"}, self.gate.holds)

    def test_connection_error_holds_sonarr_unavailable(self, mock_requests):
        _bind_exceptions(mock_requests)
        mock_requests.get.side_effect = requests.ConnectionError("boom")
        verdict = _decide(self.gate, self.client, {self.target_root: 1000})[self.target_root]
        self._assert_held(verdict, "sonarr_unavailable")

    def test_invalid_json_holds_sonarr_unavailable(self, mock_requests):
        truncated = fixture_bytes(COMPLETE)[:-7]
        with self.assertRaises(ValueError):
            json.loads(truncated)
        _serve(mock_requests, truncated)
        verdict = _decide(self.gate, self.client, {self.target_root: 1000})[self.target_root]
        self._assert_held(verdict, "sonarr_unavailable")

    def test_cached_proof_not_used_when_snapshot_becomes_unavailable(self, mock_requests):
        candidates = {self.target_root: 1000}
        _serve(mock_requests, fixture_bytes(COMPLETE))
        self.assertTrue(_decide(self.gate, self.client, candidates)[self.target_root].proven)

        self.advance(CompletionGate.REFRESH_INTERVAL_SECS + 1)
        _serve(mock_requests, b"", status=500)
        verdict = _decide(self.gate, self.client, candidates)[self.target_root]
        self._assert_held(verdict, "sonarr_unavailable")

    def test_mixed_snapshot_keeps_target_held(self, mock_requests):
        target = _target_record(INCOMPLETE)
        unrelated = _unrelated_record(COMPLETE)
        unrelated_root = _root_of(unrelated)
        self.assertNotEqual(self.target_root, unrelated_root)
        # This test serves a synthetic variant derived from the captured records: the incomplete
        # target next to another download that has already completed.
        raw = json.dumps([target, unrelated]).encode("utf-8")
        _serve(mock_requests, raw)

        verdicts = _decide(self.gate, self.client, {self.target_root: 1000, unrelated_root: 1000})

        self._assert_held(verdicts[self.target_root], "still_downloading")
        self.assertTrue(verdicts[unrelated_root].proven)
        self.assertEqual({self.target_root: "still_downloading"}, self.gate.holds)

    def test_season_pack_one_record_downloading_holds(self, mock_requests):
        done = dict(_target_record(COMPLETE), status="completed", sizeleft=0)
        downloading = dict(done, status="downloading", sizeleft=123456)
        # This test serves a synthetic variant derived from the captured record: two per-episode
        # rows of one download, one of them still downloading.
        raw = json.dumps([done, downloading]).encode("utf-8")
        _serve(mock_requests, raw)

        verdict = _decide(self.gate, self.client, {self.target_root: 1000})[self.target_root]

        self._assert_held(verdict, "still_downloading")

    def test_missing_queue_entry_holds(self, mock_requests):
        _serve(mock_requests, fixture_bytes(INCOMPLETE))
        root = "Probe.File.Not.In.Queue"
        verdict = _decide(self.gate, self.client, {root: 1000})[root]
        self._assert_held(verdict, "no_queue_entry")
        self.assertEqual({root: "no_queue_entry"}, self.gate.holds)
