import hashlib
import hmac
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import requests

from controller.arr_queue import (
    FETCH_DONE,
    FETCH_IDLE,
    FETCH_OVERRUN,
    FETCH_PENDING,
    ArrQueueClient,
    ArrTarget,
    QueueRecord,
)


API_KEY = "s3cr3t-api-key-0123456789abcdef"
SONARR_URL = "http://sonarr.internal.example:8989/"
RADARR_URL = "http://radarr.internal.example:7878"
MIB = 1024 * 1024


# ---------------------------------------------------------------------------
# Real-socket helpers (module level: reused by the CompletionGate tests and by
# the CommandProcessor tests that exercise the gate against a stalled arr).
# ---------------------------------------------------------------------------

class TrickleHandler(BaseHTTPRequestHandler):
    """
    Answers every GET with a 200 whose Content-Length (4 x 64 KiB) is never
    satisfied: one byte is written every 0.2 s, which keeps the client's 10 s
    read-inactivity timeout from firing while urllib3 stays blocked waiting for
    a full 64 KiB chunk. Once the server's stop event is set the handler stops
    trickling and closes the connection; requests arriving after that get an
    immediate empty JSON list.
    """

    def do_GET(self):  # noqa: N802 (http.server naming)
        server = self.server
        server.connections.append(self.path)
        if server.stop_event.is_set():
            body = b"[]"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(4 * ArrQueueClient.CHUNK_BYTES))
        self.end_headers()
        for _ in range(300):
            try:
                self.wfile.write(b"[")
                self.wfile.flush()
            except OSError:
                return
            if server.stop_event.wait(0.2):
                return

    def log_message(self, format, *args):  # noqa: A002 - silence the handler
        pass


def start_trickle_server() -> Tuple[ThreadingHTTPServer, int, threading.Event, List]:
    """Start a TrickleHandler server on 127.0.0.1 at an ephemeral port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), TrickleHandler)
    # Handler threads are daemons and stop on their own once stop_event is set;
    # server_close() must not join them (teardown waits are bounded elsewhere).
    server.block_on_close = False
    server.stop_event = threading.Event()
    server.connections = []
    port = server.server_address[1]
    thread = threading.Thread(name="TrickleServer", target=server.serve_forever,
                              kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    return server, port, server.stop_event, server.connections


def stop_trickle_server(server: ThreadingHTTPServer):
    server.stop_event.set()
    server.shutdown()
    server.server_close()


def settle(client: ArrQueueClient, code: str, timeout: float = 5.0) -> bool:
    """Test-only: wait (bounded) until no worker for `code` is alive."""
    deadline = time.monotonic() + timeout
    while client.in_flight(code):
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class FakeClock:
    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


def _record(output_path="/data/torrents/Show.S01E01.mkv", download_id="ABC123",
            status="completed", sizeleft=0, **extra):
    rec = {
        "id": 1,
        "title": "Some Title",
        "size": 1000,
        "trackedDownloadState": "importPending",
        "protocol": "torrent",
    }
    if output_path is not None:
        rec["outputPath"] = output_path
    if download_id is not None:
        rec["downloadId"] = download_id
    if status is not None:
        rec["status"] = status
    if sizeleft is not None:
        rec["sizeleft"] = sizeleft
    rec.update(extra)
    return rec


def _response(status=200, chunks=None):
    resp = MagicMock()
    resp.status_code = status
    resp.iter_content.side_effect = lambda chunk_size=None: iter(chunks or [])
    return resp


def _json_chunks(payload, parts=2) -> List[bytes]:
    raw = json.dumps(payload).encode("utf-8")
    step = max(1, len(raw) // parts)
    return [raw[i:i + step] for i in range(0, len(raw), step)]


def _bind_exceptions(mock_requests):
    mock_requests.RequestException = requests.RequestException
    mock_requests.ConnectionError = requests.ConnectionError
    mock_requests.Timeout = requests.Timeout


def _log_text(logger) -> str:
    return " ".join(repr(c) for c in logger.mock_calls)


def _calls(logger, level) -> List[str]:
    out = []
    for c in getattr(logger, level).call_args_list:
        args = c[0]
        if not args:
            continue
        try:
            out.append(args[0] % tuple(args[1:]) if len(args) > 1 else str(args[0]))
        except (TypeError, ValueError):
            out.append(" ".join(str(a) for a in args))
    return out


class BaseArrQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        cfg = self.context.config
        cfg.sonarr.enabled = True
        cfg.sonarr.sonarr_url = SONARR_URL
        cfg.sonarr.sonarr_api_key = API_KEY
        cfg.radarr.enabled = False
        cfg.radarr.radarr_url = RADARR_URL
        cfg.radarr.radarr_api_key = API_KEY
        self.clock = FakeClock()
        self.client = ArrQueueClient(self.context, clock=self.clock)
        self.sonarr = ArrTarget("Sonarr", "sonarr", SONARR_URL, API_KEY)

    def tearDown(self):
        for code in ("sonarr", "radarr"):
            settle(self.client, code)

    def _fetch(self, mock_requests, response=None, side_effect=None) -> Tuple[int, object]:
        _bind_exceptions(mock_requests)
        if side_effect is not None:
            mock_requests.get.side_effect = side_effect
        else:
            mock_requests.get.return_value = response
        fid = self.client.start_fetch(self.sonarr)
        self.assertIsNotNone(fid)
        self.assertTrue(settle(self.client, "sonarr"))
        return fid, self.client.poll("sonarr")


class TestArrQueueTargets(BaseArrQueueTestCase):
    def test_enabled_targets_sonarr_first_and_only_enabled(self):
        targets = self.client.enabled_targets()
        self.assertEqual(["sonarr"], [t.code for t in targets])
        self.assertEqual("Sonarr", targets[0].label)
        self.assertEqual(API_KEY, targets[0].api_key)

        self.context.config.radarr.enabled = True
        self.assertEqual(["sonarr", "radarr"], [t.code for t in self.client.enabled_targets()])

        self.context.config.sonarr.enabled = False
        self.context.config.radarr.enabled = False
        self.assertEqual([], self.client.enabled_targets())

    def test_enabled_target_with_blank_url_is_still_enabled(self):
        self.context.config.sonarr.sonarr_url = None
        self.context.config.sonarr.sonarr_api_key = None
        targets = self.client.enabled_targets()
        self.assertEqual(1, len(targets))
        self.assertEqual("", targets[0].url)
        self.assertEqual("", targets[0].api_key)

    def test_target_identity_fingerprints_key_and_normalizes_url(self):
        t = ArrTarget("Sonarr", "sonarr", "http://h:8989/", "k")
        from controller import arr_queue
        expected = hmac.new(arr_queue._FINGERPRINT_SECRET, b"k", hashlib.sha256).hexdigest()[:16]
        self.assertEqual(("sonarr", "http://h:8989", expected), t.identity)
        # Stable within the process, so key-rotation detection works.
        self.assertEqual(t.identity, ArrTarget("Sonarr", "sonarr", "http://h:8989", "k").identity)
        other = ArrTarget("Sonarr", "sonarr", "http://h:8989/", "k2")
        self.assertNotEqual(t.identity, other.identity)
        self.assertNotIn("k", t.identity)
        identity = ArrTarget("Sonarr", "sonarr", "http://h", API_KEY).identity
        self.assertFalse(any(API_KEY in part for part in identity))


@patch("controller.arr_queue.requests")
class TestArrQueueFetch(BaseArrQueueTestCase):
    def test_start_fetch_then_poll_returns_records_on_200_list(self, mock_requests):
        payload = [
            _record("/data/torrents/Show.S01E01.mkv", "ABC123", "completed", 0, id=1),
            _record("/data/torrents/Other.Release/", "DEF456", "downloading", 512, id=2),
        ]
        resp = _response(200, _json_chunks(payload, 2))
        _bind_exceptions(mock_requests)
        mock_requests.get.return_value = resp

        t = time.monotonic()
        fid = self.client.start_fetch(self.sonarr)
        self.assertLess(time.monotonic() - t, 0.05)
        self.assertIsInstance(fid, int)
        self.assertTrue(settle(self.client, "sonarr"))
        outcome = self.client.poll("sonarr")

        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertEqual(fid, outcome.fetch_id)
        self.assertEqual(
            [
                QueueRecord("Show.S01E01.mkv", "ABC123", "completed", 0, True, None),
                QueueRecord("Other.Release", "DEF456", "downloading", 512, True, None),
            ],
            outcome.records,
        )
        self.assertEqual(FETCH_IDLE, self.client.poll("sonarr").state)
        mock_requests.get.assert_called_once_with(
            "http://sonarr.internal.example:8989/api/v3/queue/details",
            headers={"X-Api-Key": API_KEY},
            timeout=(3.05, 10),
            allow_redirects=False,
            stream=True,
        )
        resp.iter_content.assert_called_once_with(chunk_size=ArrQueueClient.CHUNK_BYTES)
        resp.close.assert_called_once_with()
        self.assertFalse(self.client.in_flight("sonarr"))

    def test_poll_before_completion_is_pending_and_nonblocking(self, mock_requests):
        _bind_exceptions(mock_requests)
        release = threading.Event()
        resp = _response(200, [b"[]"])

        def blocking_get(*args, **kwargs):
            release.wait(5.0)
            return resp

        mock_requests.get.side_effect = blocking_get
        fid = self.client.start_fetch(self.sonarr)
        t = time.monotonic()
        outcome = self.client.poll("sonarr")
        self.assertLess(time.monotonic() - t, 0.05)
        self.assertEqual(FETCH_PENDING, outcome.state)
        self.assertEqual(fid, outcome.fetch_id)
        self.assertIsNone(outcome.records)
        self.assertTrue(self.client.in_flight("sonarr"))

        release.set()
        self.assertTrue(settle(self.client, "sonarr"))
        outcome = self.client.poll("sonarr")
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertEqual(fid, outcome.fetch_id)
        self.assertEqual([], outcome.records)

    def test_poll_recovers_result_posted_between_pop_and_liveness_check(self, mock_requests):
        """A worker that posts and exits just after poll()'s first pop keeps its good snapshot."""
        _bind_exceptions(mock_requests)
        mock_requests.get.return_value = _response(200, _json_chunks([_record()], 1))
        fid = self.client.start_fetch(self.sonarr)
        self.assertTrue(settle(self.client, "sonarr"))

        class FirstPopMisses(dict):
            """Simulates the post landing after poll()'s first pop: that pop sees nothing."""
            missed = False

            def pop(self, key, default=None):
                if not self.missed:
                    self.missed = True
                    return default
                return super().pop(key, default)

        self.client._ArrQueueClient__results = FirstPopMisses(self.client._ArrQueueClient__results)
        outcome = self.client.poll("sonarr")

        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertEqual(fid, outcome.fetch_id)
        self.assertEqual([QueueRecord("Show.S01E01.mkv", "ABC123", "completed", 0, True, None)],
                         outcome.records)
        self.assertFalse(any("ended without a result" in m for m in _calls(self.logger, "warning")))
        self.assertEqual(FETCH_IDLE, self.client.poll("sonarr").state)

    def test_poll_without_fetch_is_idle(self, mock_requests):
        outcome = self.client.poll("sonarr")
        self.assertEqual(FETCH_IDLE, outcome.state)
        self.assertIsNone(outcome.fetch_id)
        self.assertIsNone(outcome.records)

    def test_fetch_unavailable_on_non_200(self, mock_requests):
        resp = _response(503, [b"oops"])
        _, outcome = self._fetch(mock_requests, response=resp)
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        warnings = _calls(self.logger, "warning")
        self.assertEqual(1, len(warnings))
        self.assertIn("Sonarr", warnings[0])
        self.assertIn("503", warnings[0])
        resp.close.assert_called_once_with()

    def test_fetch_unavailable_on_connection_error(self, mock_requests):
        _, outcome = self._fetch(mock_requests, side_effect=requests.ConnectionError("refused " + API_KEY))
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        warnings = _calls(self.logger, "warning")
        self.assertEqual(1, len(warnings))
        self.assertIn("ConnectionError", warnings[0])
        self.assertIn("Sonarr", warnings[0])

    def test_fetch_unavailable_on_timeout(self, mock_requests):
        _, outcome = self._fetch(mock_requests, side_effect=requests.Timeout("slow"))
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        warnings = _calls(self.logger, "warning")
        self.assertEqual(1, len(warnings))
        self.assertIn("Timeout", warnings[0])

    def test_fetch_unavailable_on_invalid_json(self, mock_requests):
        resp = _response(200, [b"{not json"])
        _, outcome = self._fetch(mock_requests, response=resp)
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        self.assertEqual(1, len(_calls(self.logger, "warning")))
        resp.close.assert_called_once_with()

    def test_fetch_unavailable_on_non_list_payload(self, mock_requests):
        resp = _response(200, _json_chunks({"records": []}))
        _, outcome = self._fetch(mock_requests, response=resp)
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        self.assertEqual(1, len(_calls(self.logger, "warning")))
        resp.close.assert_called_once_with()

    def test_fetch_unexpected_exception_in_worker_posts_unavailable(self, mock_requests):
        _, outcome = self._fetch(mock_requests, side_effect=RuntimeError("boom"))
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        warnings = _calls(self.logger, "warning")
        self.assertEqual(1, len(warnings))
        self.assertIn("RuntimeError", warnings[0])
        self.logger.exception.assert_not_called()

    def test_fetch_oversized_chunked_response_aborts_at_cap(self, mock_requests):
        pulled = []

        def endless(chunk_size=None):
            while True:
                pulled.append(1)
                yield b"x" * MIB

        resp = MagicMock()
        resp.status_code = 200
        resp.iter_content.side_effect = endless
        with patch("controller.arr_queue.json.loads") as mock_loads:
            _, outcome = self._fetch(mock_requests, response=resp)
            mock_loads.assert_not_called()
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        self.assertLessEqual(len(pulled), ArrQueueClient.MAX_RESPONSE_BYTES // MIB + 1)
        warnings = _calls(self.logger, "warning")
        self.assertEqual(1, len(warnings))
        self.assertIn("exceeded", warnings[0])
        self.assertIn("Sonarr", warnings[0])
        resp.close.assert_called_once_with()

    def test_fetch_slow_trickle_exceeds_deadline_worker_side(self, mock_requests):
        pulled = []
        clock = self.clock

        def trickle(chunk_size=None):
            for _ in range(100):
                pulled.append(1)
                clock.now += 6.0
                yield b"["

        resp = MagicMock()
        resp.status_code = 200
        resp.iter_content.side_effect = trickle
        _, outcome = self._fetch(mock_requests, response=resp)
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        self.assertLess(len(pulled), 10)
        warnings = _calls(self.logger, "warning")
        self.assertEqual(1, len(warnings))
        self.assertIn("deadline", warnings[0])
        resp.close.assert_called_once_with()

    def test_fetch_deadline_covers_connect_phase(self, mock_requests):
        resp = _response(200, [b"[]"])
        clock = self.clock

        def slow_connect(*args, **kwargs):
            clock.now += 21.0
            return resp

        _, outcome = self._fetch(mock_requests, side_effect=slow_connect)
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertIsNone(outcome.records)
        warnings = _calls(self.logger, "warning")
        self.assertEqual(1, len(warnings))
        self.assertIn("deadline", warnings[0])
        resp.close.assert_called_once_with()

    def test_abandon_discards_outstanding_fetch_result(self, mock_requests):
        _bind_exceptions(mock_requests)
        release = threading.Event()
        resp = _response(200, [b"[]"])

        def blocking_get(*args, **kwargs):
            release.wait(5.0)
            return resp

        mock_requests.get.side_effect = blocking_get
        fid = self.client.start_fetch(self.sonarr)
        self.assertTrue(self.client.abandon("sonarr"))
        self.assertEqual(FETCH_IDLE, self.client.poll("sonarr").state)
        self.assertTrue(self.client.in_flight("sonarr"))

        release.set()
        self.assertTrue(settle(self.client, "sonarr"))
        self.assertEqual(FETCH_IDLE, self.client.poll("sonarr").state)
        debug = " ".join(_calls(self.logger, "debug"))
        self.assertIn("discarded late queue result", debug)
        self.assertFalse(self.client.abandon("sonarr"))

        mock_requests.get.side_effect = None
        mock_requests.get.return_value = _response(200, [b"[]"])
        fid2 = self.client.start_fetch(self.sonarr)
        self.assertNotEqual(fid, fid2)
        self.assertTrue(settle(self.client, "sonarr"))
        outcome = self.client.poll("sonarr")
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertEqual(fid2, outcome.fetch_id)

    def test_abandon_without_fetch_returns_false(self, mock_requests):
        self.assertFalse(self.client.abandon("sonarr"))

    def test_fetch_preserves_malformed_records_as_invalid(self, mock_requests):
        base = "/data/torrents/Obsession.2025.1080p.WEB.H264-CiNEPHiLES.mkv"
        payload = [
            _record(base, "ABC", "completed", 0),
            _record(base, None, "completed", 0),
            _record(base, "ABC", "completed", "n/a"),
            _record(base, "ABC", 7, 0),
            _record(base, "ABC", "completed", None, sizeLeft=0),
        ]
        resp = _response(200, _json_chunks(payload, 3))
        _, outcome = self._fetch(mock_requests, response=resp)
        self.assertEqual(FETCH_DONE, outcome.state)
        recs = outcome.records
        self.assertEqual(5, len(recs))
        name = "Obsession.2025.1080p.WEB.H264-CiNEPHiLES.mkv"
        self.assertEqual(QueueRecord(name, "ABC", "completed", 0, True, None), recs[0])
        self.assertEqual(QueueRecord(name, None, "completed", 0, False, "missing_download_id"), recs[1])
        self.assertEqual(QueueRecord(name, "ABC", "completed", None, False, "bad_sizeleft"), recs[2])
        self.assertEqual(QueueRecord(name, "ABC", None, 0, False, "bad_status"), recs[3])
        self.assertEqual(QueueRecord(name, "ABC", "completed", 0, True, None), recs[4])
        self.assertEqual([], _calls(self.logger, "warning"))
        debug = _calls(self.logger, "debug")
        self.assertEqual(3, sum(1 for d in debug if "defect" in d))
        self.assertTrue(any("missing_download_id" in d and name in d for d in debug))

    def test_fetch_boolean_sizeleft_and_empty_download_id_are_invalid(self, mock_requests):
        payload = [_record("/x/A.mkv", "", "completed", 0), _record("/x/A.mkv", "ABC", "completed", False)]
        _, outcome = self._fetch(mock_requests, response=_response(200, _json_chunks(payload)))
        self.assertEqual("missing_download_id", outcome.records[0].defect)
        self.assertEqual("bad_sizeleft", outcome.records[1].defect)
        self.assertIsNone(outcome.records[1].sizeleft)

    def test_fetch_normalizes_output_path_separators(self, mock_requests):
        payload = [
            _record("C:\\downloads\\Release.Name\\", "A1"),
            _record("/data/Release.Two//", "A2"),
            _record("Plain.mkv", "A3"),
        ]
        _, outcome = self._fetch(mock_requests, response=_response(200, _json_chunks(payload)))
        self.assertEqual(["Release.Name", "Release.Two", "Plain.mkv"], [r.basename for r in outcome.records])

    def test_fetch_pending_release_without_output_path_is_unattributable_not_invalid(self, mock_requests):
        payload = [
            _record(None, "ABC", "delay", 100),
            _record("", "DEF", "queued", 100),
            _record(None, None, "queued", 100),
        ]
        _, outcome = self._fetch(mock_requests, response=_response(200, _json_chunks(payload)))
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertEqual(3, len(outcome.records))
        self.assertIsNone(outcome.records[0].basename)
        self.assertTrue(outcome.records[0].valid)
        self.assertIsNone(outcome.records[1].basename)
        self.assertTrue(outcome.records[1].valid)
        self.assertFalse(outcome.records[2].valid)
        self.assertEqual("missing_download_id", outcome.records[2].defect)

    def test_fetch_rejects_snapshot_on_unattributable_malformed_record(self, mock_requests):
        for bad in ("not-a-dict", 42, None, _record(123, "ABC")):
            with self.subTest(bad=bad):
                self.logger.reset_mock()
                payload = [_record("/data/A.mkv", "ABC"), bad]
                _, outcome = self._fetch(mock_requests, response=_response(200, _json_chunks(payload)))
                self.assertEqual(FETCH_DONE, outcome.state)
                self.assertIsNone(outcome.records)
                warnings = _calls(self.logger, "warning")
                self.assertEqual(1, len(warnings))
                self.assertIn("Sonarr queue snapshot rejected: unparseable record", warnings[0])

    def test_start_fetch_rejects_non_http_url(self, mock_requests):
        _bind_exceptions(mock_requests)
        before = threading.active_count()
        fid = self.client.start_fetch(ArrTarget("Sonarr", "sonarr", "ftp://x", API_KEY))
        self.assertIsNone(fid)
        self.assertEqual(before, threading.active_count())
        self.assertFalse(self.client.in_flight("sonarr"))
        mock_requests.get.assert_not_called()
        self.assertEqual(1, len(_calls(self.logger, "warning")))
        self.assertEqual(FETCH_IDLE, self.client.poll("sonarr").state)

    def test_start_fetch_rejects_blank_url(self, mock_requests):
        _bind_exceptions(mock_requests)
        self.assertIsNone(self.client.start_fetch(ArrTarget("Sonarr", "sonarr", "", "")))
        mock_requests.get.assert_not_called()

    def test_no_secret_in_logs(self, mock_requests):
        fingerprint = self.sonarr.identity[2]
        scenarios = [
            dict(response=_response(401, [b"denied " + API_KEY.encode()])),
            dict(side_effect=requests.ConnectionError("conn to " + SONARR_URL + " key " + API_KEY)),
            dict(side_effect=requests.Timeout(API_KEY)),
            dict(side_effect=ValueError(API_KEY)),
            dict(response=_response(200, [b"{bad " + API_KEY.encode()])),
            dict(response=_response(200, _json_chunks({"k": API_KEY}))),
            dict(response=_response(200, _json_chunks([_record("/a/B.mkv", None), "junk"]))),
            dict(response=_response(200, _json_chunks([_record("/a/B.mkv", None)]))),
        ]
        for kwargs in scenarios:
            self._fetch(mock_requests, **kwargs)

        # cap
        resp = MagicMock()
        resp.status_code = 200
        resp.iter_content.side_effect = lambda chunk_size=None: iter([b"x" * MIB] * 10)
        self._fetch(mock_requests, response=resp)

        # deadline + overrun + abandon + still-in-flight + discarded late result
        release = threading.Event()
        clock = self.clock

        def stalled_get(*args, **kwargs):
            release.wait(5.0)
            return _response(200, [b"[]"])

        mock_requests.get.side_effect = stalled_get
        self.client.start_fetch(self.sonarr)
        clock.now += 25.0
        self.assertEqual(FETCH_OVERRUN, self.client.poll("sonarr").state)
        self.assertIsNone(self.client.start_fetch(self.sonarr))
        release.set()
        settle(self.client, "sonarr")
        self.client.poll("sonarr")
        mock_requests.get.side_effect = stalled_get
        release.clear()
        self.client.start_fetch(self.sonarr)
        self.client.abandon("sonarr")
        release.set()
        settle(self.client, "sonarr")
        self.client.poll("sonarr")
        self.client.start_fetch(ArrTarget("Sonarr", "sonarr", "gopher://" + API_KEY, API_KEY))

        text = _log_text(self.logger)
        self.assertGreater(len(self.logger.mock_calls), 10)
        self.assertNotIn(API_KEY, text)
        self.assertNotIn(fingerprint, text)
        self.assertNotIn(SONARR_URL.rstrip("/"), text)
        self.assertNotIn("sonarr.internal.example", text)
        self.assertNotIn("X-Api-Key", text)


class TestArrQueueRealSocket(unittest.TestCase):
    """
    Transport-level tests against a real local HTTP server.

    urllib3's HTTPResponse.stream on a non-chunked (Content-Length) body blocks
    until `amt` bytes have been read or the connection closes, so a server that
    trickles one byte at a time keeps the read alive past any between-chunk
    deadline check. Job.execute must "return relatively quickly", so the
    controller thread must never wait on such a read.
    """

    def setUp(self):
        self.server, self.port, self.stop_event, self.connections = start_trickle_server()
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        self.deadline_patch = patch.object(ArrQueueClient, "FETCH_DEADLINE_SECS", 1.0)
        self.deadline_patch.start()
        self.client = ArrQueueClient(self.context)
        self.url = "http://127.0.0.1:{}".format(self.port)

    def tearDown(self):
        stop_trickle_server(self.server)
        for code in ("sonarr", "radarr"):
            settle(self.client, code, timeout=5.0)
        self.deadline_patch.stop()

    def _poll_until_overrun(self, code, fid, t0):
        outcomes = []
        while time.monotonic() - t0 < 5.0:
            t = time.monotonic()
            outcome = self.client.poll(code)
            self.assertLess(time.monotonic() - t, 0.1)
            outcomes.append(outcome)
            if outcome.state == FETCH_OVERRUN:
                break
            time.sleep(0.05)
        self.assertEqual(FETCH_OVERRUN, outcomes[-1].state)
        self.assertEqual(fid, outcomes[-1].fetch_id)
        self.assertTrue(all(o.state == FETCH_PENDING for o in outcomes[:-1]))
        return outcomes

    def test_poll_reports_overrun_without_blocking_real_socket(self):
        """
        The worker is blocked inside urllib3 waiting for a 64 KiB chunk that the
        trickling Content-Length body never fills; start_fetch and every poll
        must still return in well under 100 ms (Job.execute contract).
        """
        target = ArrTarget("Sonarr", "sonarr", self.url, "k")
        t0 = time.monotonic()
        fid = self.client.start_fetch(target)
        self.assertLess(time.monotonic() - t0, 0.1)
        self.assertIsNotNone(fid)

        self._poll_until_overrun("sonarr", fid, t0)
        elapsed = time.monotonic() - t0
        self.assertGreaterEqual(elapsed, 1.0)
        self.assertLess(elapsed, 2.0)

        self.assertEqual(FETCH_IDLE, self.client.poll("sonarr").state)
        self.assertTrue(self.client.in_flight("sonarr"))
        warnings = _calls(self.logger, "warning")
        self.assertEqual(1, sum(1 for w in warnings if "deadline" in w))

        stop_trickle_server(self.server)
        self.assertTrue(settle(self.client, "sonarr", timeout=5.0))
        self.assertEqual(FETCH_IDLE, self.client.poll("sonarr").state)
        debug = " ".join(_calls(self.logger, "debug"))
        self.assertIn("discarded late queue result", debug)

    def test_start_fetch_refused_while_prior_worker_alive_and_late_result_discarded(self):
        target = ArrTarget("Sonarr", "sonarr", self.url, "k")
        outcomes = []
        t0 = time.monotonic()
        fid = self.client.start_fetch(target)
        outcomes.extend(self._poll_until_overrun("sonarr", fid, t0))
        self.assertEqual(1, len(self.connections))

        before = threading.active_count()
        t = time.monotonic()
        self.assertIsNone(self.client.start_fetch(target))
        self.assertLess(time.monotonic() - t, 0.05)
        self.assertEqual(before, threading.active_count())
        self.assertTrue(self.client.in_flight("sonarr"))
        logged = " ".join(_calls(self.logger, "debug") + _calls(self.logger, "warning"))
        self.assertIn("still in flight", logged)
        time.sleep(0.1)
        self.assertEqual(1, len(self.connections))

        other = ArrTarget("Radarr", "radarr", self.url, "k")
        rid = self.client.start_fetch(other)
        self.assertIsNotNone(rid)
        deadline = time.monotonic() + 2.0
        while len(self.connections) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(2, len(self.connections))

        self.stop_event.set()
        self.assertTrue(settle(self.client, "sonarr", timeout=5.0))
        outcomes.append(self.client.poll("sonarr"))

        fid3 = self.client.start_fetch(target)
        self.assertIsNotNone(fid3)
        self.assertNotEqual(fid, fid3)
        self.assertTrue(settle(self.client, "sonarr", timeout=5.0))
        final = self.client.poll("sonarr")
        outcomes.append(final)
        self.assertEqual(FETCH_DONE, final.state)
        self.assertEqual(fid3, final.fetch_id)
        self.assertEqual([], final.records)
        self.assertEqual(3, len(self.connections))
        self.assertFalse(any(o.state == FETCH_DONE and o.fetch_id == fid for o in outcomes))


if __name__ == "__main__":
    unittest.main()
