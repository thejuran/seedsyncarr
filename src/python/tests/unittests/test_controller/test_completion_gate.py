import time
import unittest
from typing import Dict, List, Optional, Set
from unittest.mock import MagicMock, patch

from controller.arr_queue import (
    FETCH_DONE,
    FETCH_IDLE,
    FETCH_OVERRUN,
    FETCH_PENDING,
    ArrQueueClient,
    ArrTarget,
    FetchOutcome,
    QueueRecord,
)
from controller.completion_gate import REASON_LABELS, CompletionGate, Verdict
from tests.unittests.test_controller.test_arr_queue import (  # noqa: F401 (TrickleHandler re-exported)
    TrickleHandler,
    settle,
    start_trickle_server,
    stop_trickle_server,
)


ROOT = "Obsession.2025.1080p.WEB.H264-CiNEPHiLES.mkv"
SIZE = 55477377022
T0 = 1000.0


# ---------------------------------------------------------------------------
# Scaffolding (FakeArrClient is reused by the CommandProcessor gate tests)
# ---------------------------------------------------------------------------

class FakeArrClient:
    """
    Scriptable stand-in for ArrQueueClient with the same non-blocking
    start_fetch / poll / abandon / in_flight contract.

    responses: what the next completed fetch for a code returns (missing → None).
    stalled: codes whose polls stay FETCH_PENDING.
    overrun_next: codes whose next poll reports FETCH_OVERRUN once.
    refuse_start: codes for which start_fetch returns None.
    """

    def __init__(self, targets: Optional[List[ArrTarget]] = None):
        self.targets: List[ArrTarget] = list(targets or [])
        self.responses: Dict[str, Optional[List[QueueRecord]]] = {}
        self.stalled: Set[str] = set()
        self.overrun_next: Set[str] = set()
        self.refuse_start: Set[str] = set()
        self.start_calls: Dict[str, int] = {}
        self.abandon_calls: List[str] = []
        self.in_flight_codes: Set[str] = set()
        self.pending: Dict[str, int] = {}
        self._seq = 0

    def enabled_targets(self) -> List[ArrTarget]:
        return list(self.targets)

    def start_fetch(self, target: ArrTarget) -> Optional[int]:
        code = target.code
        self.start_calls[code] = self.start_calls.get(code, 0) + 1
        if code in self.refuse_start:
            return None
        self._seq += 1
        self.pending[code] = self._seq
        return self._seq

    def poll(self, code: str) -> FetchOutcome:
        fid = self.pending.get(code)
        if fid is None:
            return FetchOutcome(FETCH_IDLE, None, None)
        if code in self.overrun_next:
            self.overrun_next.discard(code)
            del self.pending[code]
            return FetchOutcome(FETCH_OVERRUN, fid, None)
        if code in self.stalled:
            return FetchOutcome(FETCH_PENDING, fid, None)
        del self.pending[code]
        records = self.responses.get(code)
        return FetchOutcome(FETCH_DONE, fid, list(records) if records is not None else None)

    def abandon(self, code: str) -> bool:
        self.abandon_calls.append(code)
        return self.pending.pop(code, None) is not None

    def in_flight(self, code: str) -> bool:
        return code in self.in_flight_codes


class FakeClock:
    def __init__(self, now: float = T0):
        self.now = now


def _target(code: str, url: str = "http://h", key: str = "k") -> ArrTarget:
    return ArrTarget(code.capitalize(), code, url, key)


def _rec(basename, download_id, status, sizeleft, valid=True, defect=None) -> QueueRecord:
    return QueueRecord(basename, download_id, status, sizeleft, valid, defect)


def _done(download_id="ABC", basename=ROOT) -> QueueRecord:
    return _rec(basename, download_id, "completed", 0)


def _downloading(download_id="XYZ", basename=ROOT, sizeleft=800430078) -> QueueRecord:
    return _rec(basename, download_id, "downloading", sizeleft)


def _decide(gate: CompletionGate, candidates) -> Dict[str, Verdict]:
    """Two consecutive controller cycles at the same time: start, then apply."""
    gate.evaluate(candidates)
    return gate.evaluate(candidates)


def _fmt(call) -> str:
    args = call[0]
    if not args:
        return ""
    try:
        return args[0] % tuple(args[1:]) if len(args) > 1 else str(args[0])
    except (TypeError, ValueError):
        return " ".join(str(a) for a in args)


HOLD = Verdict.hold


class GateTestBase(unittest.TestCase):
    CODES = ("sonarr", "radarr")

    def setUp(self):
        self.clock = FakeClock()
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        self.client = FakeArrClient([_target(c) for c in self.CODES])
        self.client.responses = {c: [] for c in self.CODES}
        self.gate = CompletionGate(self.context, self.client, clock=lambda: self.clock.now)

    def at(self, seconds: float):
        self.clock.now = T0 + seconds

    def info(self) -> List[str]:
        return [_fmt(c) for c in self.logger.info.call_args_list]

    def debug(self) -> List[str]:
        return [_fmt(c) for c in self.logger.debug.call_args_list]

    def prove_root(self, code="radarr"):
        self.client.responses[code] = [_done("ABC")]
        verdict = _decide(self.gate, {ROOT: SIZE})[ROOT]
        self.assertEqual(Verdict.proven(), verdict)
        return verdict


class SonarrOnlyBase(GateTestBase):
    CODES = ("sonarr",)


class RadarrOnlyBase(GateTestBase):
    CODES = ("radarr",)


# ---------------------------------------------------------------------------
# Verdict matrix
# ---------------------------------------------------------------------------

class TestVerdictMatrix(GateTestBase):
    def test_no_arr_enabled_is_not_required(self):
        self.client.targets = []
        verdicts = _decide(self.gate, {ROOT: SIZE, "Other": 1})
        self.assertEqual(Verdict.not_required(), verdicts[ROOT])
        self.assertFalse(verdicts[ROOT].required)
        self.assertFalse(verdicts[ROOT].held)
        self.assertEqual({}, self.client.start_calls)
        self.assertEqual({}, self.gate.holds)

    def test_obsession_replay_downloading_holds_still_downloading(self):
        """
        Obsession replay, step 1: the remote file had already reached its full
        size (55,477,377,022 B, preallocated) while Radarr still reported
        800,430,078 B (~800 MB) left. A size plateau must never start a copy.
        """
        self.client.responses["radarr"] = [
            _rec(ROOT, "ABC", "downloading", 800430078)
        ]
        verdict = _decide(self.gate, {ROOT: SIZE})[ROOT]
        self.assertEqual(HOLD("still_downloading"), verdict)
        self.assertTrue(verdict.held)
        self.assertEqual({ROOT: "still_downloading"}, self.gate.holds)

    def test_obsession_replay_completed_proves(self):
        """Obsession replay, step 2: the same record at completed / sizeleft 0 proves."""
        self.client.responses["radarr"] = [_rec(ROOT, "ABC", "downloading", 800430078)]
        _decide(self.gate, {ROOT: SIZE})
        self.client.responses["radarr"] = [_rec(ROOT, "ABC", "completed", 0)]
        self.at(31)
        verdict = _decide(self.gate, {ROOT: SIZE})[ROOT]
        self.assertTrue(verdict.proven)
        self.assertFalse(verdict.held)
        self.assertEqual({}, self.gate.holds)

    def test_completed_status_is_case_insensitive(self):
        self.client.responses["radarr"] = [_rec(ROOT, "ABC", "Completed", 0)]
        self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_zero_candidates_no_queue_entry(self):
        self.client.responses = {"sonarr": [_done("Q", "Other.mkv")], "radarr": []}
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_two_download_ids_across_arrs_ambiguous(self):
        self.client.responses = {"sonarr": [_done("USENET1")], "radarr": [_done("TORRENT1")]}
        self.assertEqual(HOLD("ambiguous_match"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_download_id_grouping_is_case_insensitive(self):
        self.client.responses = {"sonarr": [_done("abc")], "radarr": [_done("ABC")]}
        self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_sonarr_per_episode_same_download_id_completed_proves(self):
        season = "Show.S01.1080p.WEB-GRP"
        self.client.responses["sonarr"] = [_done("SEASON", season) for _ in range(3)]
        self.assertEqual(Verdict.proven(), _decide(self.gate, {season: 10})[season])

    def test_sonarr_per_episode_one_downloading_still_downloading(self):
        season = "Show.S01.1080p.WEB-GRP"
        self.client.responses["sonarr"] = [
            _done("SEASON", season), _downloading("SEASON", season, 10), _done("SEASON", season)
        ]
        self.assertEqual(HOLD("still_downloading"), _decide(self.gate, {season: 10})[season])

    def test_output_path_basename_compare_is_case_sensitive(self):
        self.client.responses["radarr"] = [_done("ABC", ROOT.lower())]
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_records_without_output_path_never_match(self):
        self.client.responses["radarr"] = [_done("ABC", None), _rec(None, None, "delay", 1, False,
                                                                     "missing_download_id")]
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_title_never_used_for_matching(self):
        # The queue record's title may equal the root, but only basename(outputPath) matches.
        self.client.responses["radarr"] = [_done("ABC", "Obsession.2025.REPACK.mkv")]
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_d17_sonarr_unavailable_radarr_proves(self):
        self.client.responses = {"sonarr": None, "radarr": [_done("ABC")]}
        self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_d17_sonarr_unavailable_radarr_no_candidate_holds(self):
        self.client.responses = {"sonarr": None, "radarr": []}
        self.assertEqual(HOLD("sonarr_unavailable"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_both_unavailable_holds_first_enabled(self):
        self.client.responses = {"sonarr": None, "radarr": None}
        self.assertEqual(HOLD("sonarr_unavailable"), _decide(self.gate, {ROOT: SIZE})[ROOT])


class TestRadarrOnly(RadarrOnlyBase):
    def test_radarr_only_unavailable(self):
        self.client.responses = {"radarr": None}
        self.assertEqual(HOLD("radarr_unavailable"), _decide(self.gate, {ROOT: SIZE})[ROOT])


# ---------------------------------------------------------------------------
# Non-blocking scheduling and provisional holds
# ---------------------------------------------------------------------------

class TestNonBlockingScheduling(GateTestBase):
    def test_evaluate_never_blocks_on_pending_fetch(self):
        """
        Job.execute must return relatively quickly. A design that joined each
        fetch could stall the single controller thread ~40 s with two stalled
        arrs; evaluate() must decide from completed snapshots and return.
        """
        self.client.stalled = {"sonarr", "radarr"}
        names = {ROOT: SIZE, "B": 1, "C": 2}
        t = time.monotonic()
        verdicts = self.gate.evaluate(names)
        self.assertLess(time.monotonic() - t, 0.1)
        for name in names:
            self.assertEqual(HOLD("sonarr_unavailable"), verdicts[name])
        self.assertEqual({}, self.gate.holds)
        self.logger.info.assert_not_called()
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.client.start_calls)

        self.at(1)
        verdicts = self.gate.evaluate(names)
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.client.start_calls)
        self.assertEqual(HOLD("sonarr_unavailable"), verdicts[ROOT])
        self.assertEqual({}, self.gate.holds)
        self.logger.info.assert_not_called()

    def test_pending_result_applied_on_later_evaluate(self):
        self.client.responses = {"sonarr": [], "radarr": [_done("ABC")]}
        self.client.stalled = {"radarr"}
        self.gate.evaluate({ROOT: SIZE})
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertEqual(HOLD("radarr_unavailable"), verdict)
        self.assertEqual({}, self.gate.holds)
        self.client.stalled = set()
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertEqual(Verdict.proven(), verdict)
        self.assertEqual({}, self.gate.holds)
        self.assertFalse(any("hold" in line.lower() for line in self.info()))

    def test_verdict_is_nonblocking_and_returns_provisional_hold_for_fenced_pending_target(self):
        """
        The USER re-queue sequence: after submission invalidates the proof, the
        next verdict starts a forced refresh and answers at once with a
        provisional hold (428), then succeeds on the next click.
        """
        self.prove_root("radarr")
        self.at(0.5)
        self.gate.invalidate(ROOT, "transfer submitted")
        self.at(1)
        t = time.monotonic()
        verdict = self.gate.verdict(ROOT, SIZE)
        self.assertLess(time.monotonic() - t, 0.1)
        self.assertEqual({"sonarr": 2, "radarr": 2}, self.client.start_calls)
        self.assertTrue(verdict.held)
        # The proving record came from Radarr, whose forced refresh is pending.
        self.assertEqual(HOLD("radarr_unavailable"), verdict)
        self.assertEqual({}, self.gate.holds)
        self.assertEqual(Verdict.proven(), self.gate.verdict(ROOT, SIZE))


class TestNonBlockingScheduling1Arr(SonarrOnlyBase):
    def test_overrun_pending_fetch_becomes_unavailable_hold_with_backoff(self):
        self.gate.evaluate({ROOT: SIZE})
        self.client.overrun_next = {"sonarr"}
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertIsNone(self.gate._snapshots["sonarr"])
        self.assertTrue(self.gate._in_backoff["sonarr"])
        self.assertEqual(T0 + 30, self.gate._next_fetch_at["sonarr"])
        self.assertEqual(HOLD("sonarr_unavailable"), verdict)
        self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)
        self.assertEqual(1, len(self.info()))

        self.at(10)
        self.gate.evaluate({ROOT: SIZE})
        self.assertEqual(1, self.client.start_calls["sonarr"])

        self.at(31)
        self.client.refuse_start = {"sonarr"}
        self.gate.evaluate({ROOT: SIZE})
        self.assertEqual(2, self.client.start_calls["sonarr"])
        self.assertEqual(2, self.gate._backoff_index["sonarr"])
        self.assertEqual(T0 + 31 + 60, self.gate._next_fetch_at["sonarr"])
        self.assertEqual(1, len(self.info()))

        self.at(91)
        self.client.refuse_start = set()
        self.client.responses["sonarr"] = [_done("ABC")]
        verdict = _decide(self.gate, {ROOT: SIZE})[ROOT]
        self.assertEqual(Verdict.proven(), verdict)
        self.assertEqual(0, self.gate._backoff_index["sonarr"])
        self.assertFalse(self.gate._in_backoff["sonarr"])
        self.assertEqual({}, self.gate.holds)
        self.assertEqual(1, sum(1 for line in self.info() if "hold cleared" in line))

    def test_pending_retry_after_failure_keeps_regular_unavailable_hold(self):
        self.client.responses["sonarr"] = None
        _decide(self.gate, {ROOT: SIZE})
        self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)
        self.assertEqual(1, len(self.info()))
        self.at(31)
        self.client.stalled = {"sonarr"}
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertEqual(2, self.client.start_calls["sonarr"])
        self.assertEqual(HOLD("sonarr_unavailable"), verdict)
        self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)
        self.assertEqual(1, len(self.info()))

    def test_periodic_refresh_in_flight_keeps_deciding_from_fresh_snapshot(self):
        self.prove_root("sonarr")
        self.at(31)
        self.client.stalled = {"sonarr"}
        self.assertEqual(Verdict.proven(), self.gate.evaluate({ROOT: SIZE})[ROOT])
        self.assertEqual(2, self.client.start_calls["sonarr"])
        self.at(52)
        self.client.overrun_next = {"sonarr"}
        self.assertEqual(HOLD("sonarr_unavailable"), self.gate.evaluate({ROOT: SIZE})[ROOT])
        self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)
        self.client.stalled = set()
        self.at(82)
        self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.assertEqual({}, self.gate.holds)

    def test_url_change_abandons_in_flight_fetch_and_never_applies_its_result(self):
        for refuse in (False, True):
            with self.subTest(refuse=refuse):
                self.setUp()
                self.client.targets = [_target("sonarr", url="http://a")]
                self.client.responses["sonarr"] = [_done("ABC")]
                self.client.stalled = {"sonarr"}
                self.gate.evaluate({ROOT: SIZE})
                self.assertIn("sonarr", self.gate._pending_fetch)

                self.at(10)
                self.client.targets = [_target("sonarr", url="http://b")]
                if refuse:
                    self.client.refuse_start = {"sonarr"}
                    self.client.in_flight_codes = {"sonarr"}
                verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
                self.assertEqual(["sonarr"], self.client.abandon_calls)
                self.assertEqual(2, self.client.start_calls["sonarr"])
                self.assertEqual({}, self.gate._fences)
                self.assertEqual(HOLD("sonarr_unavailable"), verdict)
                if refuse:
                    self.assertIsNone(self.gate._snapshots["sonarr"])
                    self.assertNotIn("sonarr", self.gate._pending_fetch)
                    self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)
                    self.assertTrue(any("in flight" in line for line in self.debug()))
                else:
                    self.assertNotIn("sonarr", self.gate._snapshots)
                    self.assertIn("sonarr", self.gate._pending_fetch)
                    self.assertEqual({}, self.gate.holds)
                    # Still pending: nothing from url A was applied.
                    self.gate.evaluate({ROOT: SIZE})
                    self.assertNotIn("sonarr", self.gate._snapshots)
                    self.client.stalled = set()
                    self.client.responses["sonarr"] = []
                    self.assertEqual(HOLD("no_queue_entry"), self.gate.evaluate({ROOT: SIZE})[ROOT])


class TestRealClientNonBlocking(unittest.TestCase):
    """Gate driven by a real ArrQueueClient against a trickling local socket."""

    def setUp(self):
        self.server, self.port, self.stop_event, self.connections = start_trickle_server()
        self.deadline_patch = patch.object(ArrQueueClient, "FETCH_DEADLINE_SECS", 1.0)
        self.deadline_patch.start()
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        url = "http://127.0.0.1:{}".format(self.port)
        cfg = self.context.config
        cfg.sonarr.enabled = True
        cfg.sonarr.sonarr_url = url
        cfg.sonarr.sonarr_api_key = "k"
        cfg.radarr.enabled = True
        cfg.radarr.radarr_url = url
        cfg.radarr.radarr_api_key = "k"
        self.client = ArrQueueClient(self.context)
        self.gate = CompletionGate(self.context, self.client)

    def tearDown(self):
        stop_trickle_server(self.server)
        for code in ("sonarr", "radarr"):
            settle(self.client, code, timeout=5.0)
        self.deadline_patch.stop()

    def test_real_client_evaluate_returns_fast_with_both_arrs_stalled(self):
        t = time.monotonic()
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertLess(time.monotonic() - t, 0.1)
        self.assertEqual(HOLD("sonarr_unavailable"), verdict)
        self.assertTrue(self.client.in_flight("sonarr"))
        self.assertTrue(self.client.in_flight("radarr"))

    def test_two_stalled_targets_do_not_block_controller(self):
        t = time.monotonic()
        for _ in range(10):
            self.gate.evaluate({ROOT: SIZE})
        self.assertLess(time.monotonic() - t, 1.0)
        self.assertEqual({}, self.gate.holds)

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            t = time.monotonic()
            self.gate.evaluate({ROOT: SIZE})
            self.assertLess(time.monotonic() - t, 0.1)
            if not self.gate._pending_fetch:
                break
            time.sleep(0.05)
        self.assertEqual({}, self.gate._pending_fetch)
        self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)
        info = [_fmt(c) for c in self.logger.info.call_args_list]
        self.assertEqual(1, len(info))
        self.assertTrue(self.client.in_flight("sonarr"))
        self.assertTrue(self.client.in_flight("radarr"))


# ---------------------------------------------------------------------------
# Mixed valid / malformed matching records
# ---------------------------------------------------------------------------

class TestMalformedRecords(GateTestBase):
    def test_malformed_sibling_missing_download_id_holds_ambiguous(self):
        self.client.responses["radarr"] = [
            _done("ABC"), _rec(ROOT, None, "completed", 0, False, "missing_download_id")
        ]
        self.assertEqual(HOLD("ambiguous_match"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_malformed_sibling_bad_sizeleft_holds_still_downloading(self):
        for bad in (_rec(ROOT, "ABC", "completed", None, False, "bad_sizeleft"),
                    _rec(ROOT, "ABC", None, 0, False, "bad_status")):
            with self.subTest(defect=bad.defect):
                self.setUp()
                self.client.responses["radarr"] = [_done("ABC"), bad]
                self.assertEqual(HOLD("still_downloading"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_malformed_record_in_other_arr_still_holds(self):
        self.client.responses = {
            "sonarr": [_rec(ROOT, "XYZ", "completed", None, False, "bad_sizeleft")],
            "radarr": [_done("ABC")],
        }
        self.assertEqual(HOLD("ambiguous_match"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_only_malformed_records_hold_not_proven_not_no_queue_entry(self):
        cases = [
            (_rec(ROOT, None, "completed", 0, False, "missing_download_id"), "ambiguous_match"),
            (_rec(ROOT, "ABC", "completed", None, False, "bad_sizeleft"), "still_downloading"),
            (_rec(ROOT, "ABC", None, 0, False, "bad_status"), "still_downloading"),
        ]
        for record, reason in cases:
            with self.subTest(defect=record.defect):
                self.setUp()
                self.client.responses["radarr"] = [record]
                self.assertEqual(HOLD(reason), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_malformed_record_for_a_different_root_is_irrelevant(self):
        self.client.responses["radarr"] = [
            _done("ABC"), _rec("Other.mkv", None, None, None, False, "missing_download_id")
        ]
        self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])


# ---------------------------------------------------------------------------
# Proof cache scoped to identity + lifecycle, request-epoch fences
# ---------------------------------------------------------------------------

class TestProofCache(GateTestBase):
    def test_cached_proof_survives_record_leaving_queue_after_import(self):
        self.prove_root("radarr")
        self.client.responses["radarr"] = []
        self.at(31)
        self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.at(62)
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE + 1})[ROOT])

    def test_same_name_same_size_regrab_overrides_cached_proof(self):
        """
        A same-name re-grab whose client preallocates the file at the original
        size looks identical by name and remote size; the live queue record of
        the new download must win over the cached proof and drop it.
        """
        self.prove_root("radarr")
        self.at(31)
        self.client.responses["radarr"] = [_downloading("XYZ", sizeleft=1000)]
        self.assertEqual(HOLD("still_downloading"), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.assertNotIn(ROOT, self.gate._proofs)
        self.at(62)
        self.client.responses["radarr"] = []
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_cached_proof_not_used_while_any_enabled_arr_unavailable(self):
        self.prove_root("radarr")
        self.at(31)
        self.client.responses = {"sonarr": None, "radarr": []}
        self.assertEqual(HOLD("sonarr_unavailable"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_cached_proof_dropped_by_invalid_matching_record(self):
        self.prove_root("radarr")
        self.at(31)
        self.client.responses["radarr"] = [_rec(ROOT, "ABC", "completed", None, False, "bad_sizeleft")]
        self.assertTrue(_decide(self.gate, {ROOT: SIZE})[ROOT].held)
        self.assertNotIn(ROOT, self.gate._proofs)
        self.at(62)
        self.client.responses["radarr"] = []
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_invalidate_drops_proof_and_returns_bool(self):
        self.prove_root("radarr")
        self.assertTrue(self.gate.invalidate(ROOT, "transfer submitted"))
        self.assertFalse(self.gate.invalidate(ROOT, "transfer submitted"))
        self.client.responses["radarr"] = []
        self.at(1)
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.assertTrue(any("Completion proof dropped" in line for line in self.debug()))

    def test_invalidate_then_verdict_before_refresh_deadline_requires_fresh_fetch(self):
        """
        Between a submission's invalidate() and the 30 s refresh deadline the
        completed record is still in the retained snapshot. A verdict taken in
        that window must not recreate PROVEN from it: a same-name replacement
        grab would otherwise pass the renewed start gate.
        """
        variants = {
            "b": ({"sonarr": [], "radarr": [_downloading("XYZ", sizeleft=5)]}, HOLD("still_downloading")),
            "c": ({"sonarr": None, "radarr": None}, HOLD("sonarr_unavailable")),
            "d": ({"sonarr": [], "radarr": [_done("ABC")]}, Verdict.proven()),
        }
        for label, (responses, expected) in variants.items():
            with self.subTest(variant=label):
                self.setUp()
                self.prove_root("radarr")
                self.at(5)
                self.gate.invalidate(ROOT, "transfer submitted")
                self.at(10)
                self.client.responses = responses
                first = self.gate.evaluate({ROOT: SIZE})[ROOT]
                self.assertEqual({"sonarr": 2, "radarr": 2}, self.client.start_calls)
                self.assertFalse(first.proven)
                self.assertNotIn(ROOT, self.gate.holds)
                self.assertEqual(expected, self.gate.evaluate({ROOT: SIZE})[ROOT])

    def test_fresh_proof_from_responding_arr_after_invalidation_while_other_unavailable(self):
        """
        D-17: an unavailable service causes a hold only when no other configured
        service provides sufficient completion evidence. Submit → invalidate →
        interrupted transfer → retry must re-prove from a fresh Radarr answer
        while Sonarr is still down.
        """
        variants = {
            "radarr_proves": ({"sonarr": None, "radarr": [_done("ABC")]}, Verdict.proven()),
            "radarr_fails": ({"sonarr": None, "radarr": None}, HOLD("sonarr_unavailable")),
            "sonarr_contradicts": ({"sonarr": [_done("OTHER")], "radarr": [_done("ABC")]},
                                   HOLD("ambiguous_match")),
        }
        for label, (responses, expected) in variants.items():
            with self.subTest(variant=label):
                self.setUp()
                self.client.responses = {"sonarr": None, "radarr": [_done("ABC")]}
                self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])
                self.assertEqual(0, self.gate._snapshot_epoch["radarr"])
                self.assertNotIn("sonarr", self.gate._snapshot_epoch)
                self.at(1)
                self.gate.invalidate(ROOT, "transfer submitted")
                self.assertEqual({"sonarr": 1, "radarr": 1}, self.gate._fences[ROOT])
                self.at(31)
                self.client.responses = responses
                self.assertEqual(expected, _decide(self.gate, {ROOT: SIZE})[ROOT])
                if expected.proven:
                    self.assertEqual("ABC", self.gate._proofs[ROOT].download_id)
                    self.assertEqual(1, self.gate._snapshot_epoch["radarr"])

    def test_stale_pre_invalidation_snapshot_never_proves(self):
        self.prove_root("radarr")
        self.at(1)
        self.gate.invalidate(ROOT, "lifecycle reset")
        self.at(2)
        self.client.responses = {"sonarr": [], "radarr": None}
        self.assertEqual(HOLD("radarr_unavailable"), _decide(self.gate, {ROOT: SIZE})[ROOT])

        # White-box: a retained completed record from a pre-fence request.
        self.gate._snapshots["radarr"] = [_done("ABC")]
        self.assertLess(self.gate._snapshot_epoch["radarr"], self.gate._fences[ROOT]["radarr"])
        self.assertNotIn("radarr", self.gate._pending_fetch)
        self.at(3)
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertEqual(HOLD("radarr_unavailable"), verdict)
        self.assertNotIn(ROOT, self.gate._proofs)

    def test_fenced_name_never_proven_from_absence_cache(self):
        self.prove_root("radarr")
        self.at(1)
        self.gate.invalidate(ROOT, "transfer submitted")
        self.client.responses = {"sonarr": [], "radarr": []}
        self.at(2)
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])

    def test_fence_blocks_absence_cache_while_target_in_backoff(self):
        self.prove_root("radarr")
        self.at(1)
        self.gate.invalidate(ROOT, "transfer submitted")
        self.client.responses = {"sonarr": None, "radarr": []}
        self.at(2)
        self.assertEqual(HOLD("sonarr_unavailable"), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.assertEqual(2, self.client.start_calls["sonarr"])
        self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)
        for t in (10, 20, 31):
            self.at(t)
            self.assertEqual(HOLD("sonarr_unavailable"), self.gate.evaluate({ROOT: SIZE})[ROOT])
        # The fence never starts a fetch inside Sonarr's backoff window.
        self.assertEqual(2, self.client.start_calls["sonarr"])
        self.client.responses["sonarr"] = []
        self.at(32)
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.assertEqual(3, self.client.start_calls["sonarr"])
        self.assertNotIn(ROOT, self.gate._fences)

    def test_enabled_target_change_drops_all_proofs(self):
        self.client.targets = [_target("sonarr")]
        self.client.responses = {"sonarr": [_done("ABC")], "radarr": []}
        self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.client.targets = [_target("sonarr"), _target("radarr")]
        self.client.responses["sonarr"] = []
        self.at(5)
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertNotIn(ROOT, self.gate._proofs)
        self.assertFalse(verdict.proven)
        self.assertEqual(HOLD("no_queue_entry"), self.gate.evaluate({ROOT: SIZE})[ROOT])
        self.assertEqual(1, sum(1 for line in self.debug() if "configuration changed" in line))

    def test_proof_is_recorded_with_download_id(self):
        self.prove_root("radarr")
        proof = self.gate._proofs[ROOT]
        self.assertEqual("ABC", proof.download_id)
        self.assertEqual(SIZE, proof.remote_size)
        self.assertEqual(0, proof.epoch)
        self.assertEqual(tuple(t.identity for t in self.client.targets), proof.config_key)

    def test_snapshot_epoch_is_stamped_from_request_start(self):
        self.assertEqual({}, self.gate._epoch)
        self.client.stalled = {"sonarr"}
        self.gate.evaluate({ROOT: SIZE})          # both started at epoch 0
        self.gate.invalidate(ROOT, "lifecycle reset")
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.gate._epoch)
        self.gate.evaluate({ROOT: SIZE})          # radarr lands with its start epoch 0
        self.assertEqual(0, self.gate._snapshot_epoch["radarr"])
        self.assertNotIn("sonarr", self.gate._snapshot_epoch)
        self.client.stalled = set()
        self.gate.evaluate({ROOT: SIZE})          # sonarr lands (0); radarr's fenced refresh lands (1)
        self.assertEqual(0, self.gate._snapshot_epoch["sonarr"])
        self.assertEqual(1, self.gate._snapshot_epoch["radarr"])
        self.gate.evaluate({ROOT: SIZE})          # sonarr's fenced refresh started at 1
        self.assertEqual(1, self.gate._snapshot_epoch["sonarr"])

        self.client.responses["radarr"] = None
        self.at(31)
        _decide(self.gate, {ROOT: SIZE})
        self.assertIsNone(self.gate._snapshots["radarr"])
        self.assertEqual(1, self.gate._snapshot_epoch["radarr"])
        self.at(62)
        self.gate.evaluate({ROOT: SIZE})          # sonarr refresh starts
        self.client.overrun_next = {"sonarr"}
        self.gate.evaluate({ROOT: SIZE})
        self.assertIsNone(self.gate._snapshots["sonarr"])
        self.assertEqual(1, self.gate._snapshot_epoch["sonarr"])
        self.client.refuse_start = {"sonarr", "radarr"}
        self.at(200)
        self.gate.evaluate({ROOT: SIZE})
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.gate._snapshot_epoch)

    def test_invalidate_bumps_only_enabled_target_epochs(self):
        self.client.targets = [_target("sonarr")]
        self.gate.invalidate(ROOT, "lifecycle reset")
        self.assertEqual({"sonarr": 1}, self.gate._epoch)
        self.assertEqual({"sonarr": 1}, self.gate._fences[ROOT])

    def test_fence_is_per_name_and_lifts_after_refresh(self):
        self.client.responses = {"sonarr": [_done("A1", "A"), _done("B1", "B")], "radarr": []}
        verdicts = _decide(self.gate, {"A": 1, "B": 2})
        self.assertTrue(verdicts["A"].proven and verdicts["B"].proven)
        self.at(1)
        self.gate.invalidate("A", "transfer submitted")
        self.at(2)
        verdicts = self.gate.evaluate({"A": 1, "B": 2})
        self.assertEqual({"sonarr": 2, "radarr": 2}, self.client.start_calls)
        self.assertEqual(Verdict.proven(), verdicts["B"])
        self.assertTrue(verdicts["A"].held)
        self.assertNotIn("A", self.gate.holds)
        verdicts = self.gate.evaluate({"A": 1, "B": 2})
        self.assertEqual(Verdict.proven(), verdicts["A"])
        self.assertNotIn("A", self.gate._fences)
        self.at(12)
        self.gate.evaluate({"A": 1, "B": 2})
        self.assertEqual({"sonarr": 2, "radarr": 2}, self.client.start_calls)


class TestProofCacheSonarrOnly(SonarrOnlyBase):
    def test_response_from_fetch_started_before_invalidation_never_satisfies_fence(self):
        """
        A periodic refresh starts, then a same-name lifecycle reset invalidates
        the root, then the delayed response for the earlier download arrives.
        That response describes the old download; it must stay stale and may
        never authorize copying the replacement that is still downloading.
        """
        for variant in ("a", "b"):
            with self.subTest(variant=variant):
                self.setUp()
                self.prove_root("sonarr")
                self.at(31)
                self.client.stalled = {"sonarr"}
                self.gate.evaluate({ROOT: SIZE})
                self.assertEqual(2, self.client.start_calls["sonarr"])
                self.at(32)
                self.gate.invalidate(ROOT, "lifecycle reset")
                self.at(33)
                self.client.stalled = set()
                verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
                self.assertEqual(HOLD("sonarr_unavailable"), verdict)
                self.assertNotIn(ROOT, self.gate.holds)
                self.assertNotIn(ROOT, self.gate._proofs)
                self.assertEqual(0, self.gate._snapshot_epoch["sonarr"])
                self.assertEqual(1, self.gate._fences[ROOT]["sonarr"])
                self.assertEqual(3, self.client.start_calls["sonarr"])
                if variant == "a":
                    self.client.responses["sonarr"] = [_downloading("XYZ", sizeleft=10)]
                    self.assertEqual(HOLD("still_downloading"), self.gate.evaluate({ROOT: SIZE})[ROOT])
                else:
                    self.assertEqual(Verdict.proven(), self.gate.evaluate({ROOT: SIZE})[ROOT])
                    self.assertNotIn(ROOT, self.gate._fences)

    def test_url_change_same_service_clears_snapshots_and_backoff(self):
        # Variant 1: URL switch right after a proof.
        self.client.targets = [_target("sonarr", url="http://a")]
        self.prove_root("sonarr")
        self.at(10)
        self.client.targets = [_target("sonarr", url="http://b")]
        self.client.responses["sonarr"] = []
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertEqual(2, self.client.start_calls["sonarr"])
        self.assertNotIn(ROOT, self.gate._proofs)
        self.assertNotIn("sonarr", self.gate._snapshots)
        self.assertEqual({}, self.gate._fences)
        self.assertEqual({}, self.gate._epoch)
        self.assertEqual({}, self.gate._snapshot_epoch)
        self.assertFalse(verdict.proven)
        self.assertEqual(HOLD("no_queue_entry"), self.gate.evaluate({ROOT: SIZE})[ROOT])

        # Variant 2: URL A failing in a 300 s backoff; switch to URL B fetches at once.
        self.setUp()
        self.client.targets = [_target("sonarr", url="http://a")]
        self.client.responses["sonarr"] = None
        for t in (0, 30, 90, 210, 450):
            self.at(t)
            _decide(self.gate, {ROOT: SIZE})
        self.assertEqual(5, self.gate._backoff_index["sonarr"])
        self.assertEqual(T0 + 450 + 300, self.gate._next_fetch_at["sonarr"])
        self.at(460)
        self.client.targets = [_target("sonarr", url="http://b")]
        self.client.responses["sonarr"] = []
        self.gate.evaluate({ROOT: SIZE})
        self.assertEqual(6, self.client.start_calls["sonarr"])
        self.assertEqual(0, self.gate._backoff_index.get("sonarr", 0))
        self.assertEqual(HOLD("no_queue_entry"), self.gate.evaluate({ROOT: SIZE})[ROOT])

        # Variant 3: same URL, api key rotated → identical reset.
        self.setUp()
        self.client.targets = [_target("sonarr", key="old")]
        self.prove_root("sonarr")
        self.at(5)
        self.client.targets = [_target("sonarr", key="new")]
        self.client.responses["sonarr"] = []
        self.gate.evaluate({ROOT: SIZE})
        self.assertEqual(2, self.client.start_calls["sonarr"])
        self.assertNotIn(ROOT, self.gate._proofs)
        self.assertEqual(HOLD("no_queue_entry"), self.gate.evaluate({ROOT: SIZE})[ROOT])


class TestPreInvalidationBothArrs(GateTestBase):
    def test_pre_invalidation_response_with_post_invalidation_absence_still_holds(self):
        self.prove_root("sonarr")
        self.at(31)
        self.client.stalled = {"sonarr"}
        _decide(self.gate, {ROOT: SIZE})          # both refreshes start; radarr lands (epoch 0)
        self.at(32)
        self.gate.invalidate(ROOT, "lifecycle reset")
        self.at(33)
        self.client.stalled = set()
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]   # sonarr's old record lands stale
        self.assertEqual(HOLD("sonarr_unavailable"), verdict)
        self.client.stalled = {"sonarr"}
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]   # radarr fresh & empty; sonarr pending
        self.assertEqual(1, self.gate._snapshot_epoch["radarr"])
        self.assertEqual(HOLD("sonarr_unavailable"), verdict)
        self.assertNotIn(ROOT, self.gate.holds)
        self.assertNotIn(ROOT, self.gate._proofs)


# ---------------------------------------------------------------------------
# Backoff / fetch sharing
# ---------------------------------------------------------------------------

class TestBackoffAndSharing(GateTestBase):
    def test_one_fetch_per_arr_per_cycle_shared_across_names(self):
        names = {"N{}".format(i): i for i in range(5)}
        self.gate.evaluate(names)
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.client.start_calls)
        self.gate.evaluate(names)
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.client.start_calls)
        self.at(10)
        self.gate.evaluate(names)
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.client.start_calls)
        self.at(31)
        self.gate.evaluate(names)
        self.assertEqual({"sonarr": 2, "radarr": 2}, self.client.start_calls)

    def test_evaluate_without_candidates_polls_but_starts_nothing(self):
        self.client.responses["radarr"] = [_done("ABC")]
        self.gate.evaluate({ROOT: SIZE})
        self.gate.evaluate({})
        self.assertIn("radarr", self.gate._snapshots)
        self.assertEqual(Verdict.proven(), self.gate.evaluate({ROOT: SIZE})[ROOT])
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.client.start_calls)
        self.at(100)
        self.assertEqual({}, self.gate.evaluate({}))
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.client.start_calls)

    def test_cached_snapshot_used_between_refreshes(self):
        self.prove_root("radarr")
        self.client.responses["radarr"] = []
        self.at(10)
        self.assertEqual(Verdict.proven(), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.assertEqual({"sonarr": 1, "radarr": 1}, self.client.start_calls)


class TestBackoffSonarrOnly(SonarrOnlyBase):
    def test_backoff_ladder_caps_at_300_and_resets_on_success(self):
        self.client.responses["sonarr"] = None
        t = 0.0
        expected_steps = [30, 60, 120, 240, 300, 300]
        for step in expected_steps:
            self.at(t)
            _decide(self.gate, {ROOT: SIZE})
            self.assertEqual(T0 + t + step, self.gate._next_fetch_at["sonarr"])
            calls = self.client.start_calls["sonarr"]
            self.at(t + step - 1)
            self.gate.evaluate({ROOT: SIZE})
            self.assertEqual(calls, self.client.start_calls["sonarr"])
            t += step
        self.assertEqual(6, self.client.start_calls["sonarr"])
        self.client.responses["sonarr"] = []
        self.at(t)
        self.assertEqual(HOLD("no_queue_entry"), _decide(self.gate, {ROOT: SIZE})[ROOT])
        self.assertEqual(0, self.gate._backoff_index["sonarr"])
        self.assertEqual(T0 + t + CompletionGate.REFRESH_INTERVAL_SECS, self.gate._next_fetch_at["sonarr"])

    def test_refused_start_counts_as_failure(self):
        self.client.refuse_start = {"sonarr"}
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertEqual(1, self.client.start_calls["sonarr"])
        self.assertIsNone(self.gate._snapshots["sonarr"])
        self.assertEqual(T0 + 30, self.gate._next_fetch_at["sonarr"])
        self.assertEqual(HOLD("sonarr_unavailable"), verdict)
        self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)

    def test_failure_debug_mentions_in_flight(self):
        self.gate.evaluate({ROOT: SIZE})
        self.client.overrun_next = {"sonarr"}
        self.client.in_flight_codes = {"sonarr"}
        self.gate.evaluate({ROOT: SIZE})
        self.assertTrue(any("in flight" in line for line in self.debug()))

    def test_idle_while_pending_is_treated_as_failure(self):
        self.gate.evaluate({ROOT: SIZE})
        self.client.pending.clear()    # the client lost/abandoned the fetch
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertNotIn("sonarr", self.gate._pending_fetch)
        self.assertEqual(HOLD("sonarr_unavailable"), verdict)
        self.assertEqual({ROOT: "sonarr_unavailable"}, self.gate.holds)


# ---------------------------------------------------------------------------
# Transition logging and the hold registry
# ---------------------------------------------------------------------------

class TestHoldRegistry(GateTestBase):
    def test_hold_start_logged_once_with_sanitized_name_and_label(self):
        name = "Evil\nName.mkv"
        _decide(self.gate, {name: 1})
        info = self.info()
        self.assertEqual(1, len(info))
        self.assertIn("Evil\\nName.mkv", info[0])
        self.assertNotIn("\n", info[0])
        self.assertIn(REASON_LABELS["no_queue_entry"], info[0])
        self.at(31)
        _decide(self.gate, {name: 1})
        self.assertEqual(1, len(self.info()))

    def test_reason_change_logged_once(self):
        _decide(self.gate, {ROOT: SIZE})
        self.client.responses["radarr"] = [_downloading()]
        self.at(31)
        _decide(self.gate, {ROOT: SIZE})
        self.assertEqual({ROOT: "still_downloading"}, self.gate.holds)
        info = self.info()
        self.assertEqual(2, len(info))
        self.assertIn(REASON_LABELS["still_downloading"], info[1])
        self.at(62)
        _decide(self.gate, {ROOT: SIZE})
        self.assertEqual(2, len(self.info()))

    def test_hold_cleared_when_proven(self):
        _decide(self.gate, {ROOT: SIZE})
        self.client.responses["radarr"] = [_done()]
        self.at(31)
        _decide(self.gate, {ROOT: SIZE})
        self.assertEqual({}, self.gate.holds)
        self.assertEqual(1, sum(1 for line in self.info() if "hold cleared" in line))

    def test_hold_cleared_when_no_longer_candidate(self):
        _decide(self.gate, {ROOT: SIZE, "Other": 1})
        self.assertEqual({ROOT: "no_queue_entry", "Other": "no_queue_entry"}, self.gate.holds)
        self.gate.evaluate({"Other": 1})
        self.assertEqual({"Other": "no_queue_entry"}, self.gate.holds)
        self.assertEqual(1, sum(1 for line in self.info() if "hold cleared" in line))

    def test_holds_property_is_a_copy(self):
        _decide(self.gate, {ROOT: SIZE})
        holds = self.gate.holds
        holds.clear()
        self.assertEqual({ROOT: "no_queue_entry"}, self.gate.holds)

    def test_provisional_hold_never_touches_registry(self):
        _decide(self.gate, {ROOT: SIZE})
        self.assertEqual({ROOT: "no_queue_entry"}, self.gate.holds)
        self.at(1)
        self.gate.invalidate(ROOT, "transfer submitted")
        self.at(2)
        info_before = len(self.info())
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertEqual(HOLD("sonarr_unavailable"), verdict)
        self.assertEqual({ROOT: "no_queue_entry"}, self.gate.holds)
        self.assertEqual(info_before, len(self.info()))
        self.assertTrue(any("awaiting" in line for line in self.debug()))

    def test_verdict_does_not_clear_other_holds(self):
        _decide(self.gate, {ROOT: SIZE, "Other": 1})
        self.gate.verdict("Other", 1)
        self.assertEqual({ROOT: "no_queue_entry", "Other": "no_queue_entry"}, self.gate.holds)
        self.assertFalse(any("hold cleared" in line for line in self.info()))

    def test_label_lookup_and_invalidate_all(self):
        for code, label in REASON_LABELS.items():
            self.assertEqual(label, self.gate.label(code))
        self.assertEqual("No matching queue entry", self.gate.label("no_queue_entry"))
        self.client.responses["radarr"] = [_done("A1", "A"), _done("B1", "B")]
        _decide(self.gate, {"A": 1, "B": 2})
        self.assertEqual(2, self.gate.invalidate_all("test"))
        self.assertEqual({}, self.gate._proofs)

    def test_no_targets_clears_existing_holds(self):
        _decide(self.gate, {ROOT: SIZE})
        self.client.targets = []
        verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
        self.assertEqual(Verdict.not_required(), verdict)
        self.assertEqual({}, self.gate.holds)
        self.assertEqual(1, sum(1 for line in self.info() if "hold cleared" in line))


if __name__ == "__main__":
    unittest.main()
