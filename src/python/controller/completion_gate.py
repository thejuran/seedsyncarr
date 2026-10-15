"""
Completion gate: decides from Sonarr/Radarr queue evidence whether a remote
root has finished downloading before any transfer of it may start.

A root is PROVEN only when exactly one downloadId group of queue records has
basename(outputPath) equal to the root name (exact, case-sensitive) and every
record of that group is well-formed with status "completed" and sizeleft 0.
Anything else holds the root with a reason code: an arr that has not given a
usable answer, ambiguous identity, an incomplete or unverifiable download, or
no matching queue entry. Elapsed time never grants completion.

Thread model: every method runs on the controller thread and returns without
waiting on any arr. Queue fetches run on the client's worker threads; their
results are applied by a later evaluate() call through client.poll. A hold
caused only by a first (or forced, post-invalidation) fetch that is still in
flight is provisional: it is returned to the caller but not registered in
`holds` and not logged at INFO.
"""

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, NamedTuple, Optional, Tuple

from common import Context, sanitize_log_value

from .arr_queue import (
    FETCH_DONE,
    FETCH_IDLE,
    FETCH_OVERRUN,
    ArrQueueClient,
    ArrTarget,
    QueueRecord,
)


REASON_LABELS: Dict[str, str] = {
    "sonarr_unavailable": "Sonarr unavailable",
    "radarr_unavailable": "Radarr unavailable",
    "ambiguous_match": "Ambiguous match",
    "still_downloading": "Still downloading",
    "no_queue_entry": "No matching queue entry",
}

_FRESH = "fresh"
_STALE = "stale"
_PENDING = "pending"
_UNAVAILABLE = "unavailable"

_ConfigKey = Tuple[Tuple[str, str, str], ...]


@dataclass(frozen=True)
class Verdict:
    """
    required: the gate applies (at least one arr enabled).
    proven: completion is proven. held == required and not proven.

    Constructors: Verdict.not_required(), Verdict.proven(), Verdict.hold(code).
    The `proven` constructor shares its name with the field; it is attached
    after the class body so the dataclass does not mistake it for the field's
    default (instances still read the boolean field).
    """
    required: bool
    proven: bool
    reason: Optional[str]

    @property
    def held(self) -> bool:
        return self.required and not self.proven

    @staticmethod
    def not_required() -> "Verdict":
        return Verdict(required=False, proven=False, reason=None)

    @staticmethod
    def hold(reason_code: str) -> "Verdict":
        return Verdict(required=True, proven=False, reason=reason_code)


def _proven_verdict() -> Verdict:
    return Verdict(required=True, proven=True, reason=None)


setattr(Verdict, "proven", staticmethod(_proven_verdict))


class _Proof(NamedTuple):
    download_id: str
    remote_size: Optional[int]
    config_key: _ConfigKey
    epoch: int


class _PendingFetch(NamedTuple):
    fetch_id: int
    epoch: int


class CompletionGate:
    """
    Snapshot cache, capped backoff, strong-identity match, verdicts and the
    hold registry.

    A proof authorizes transfers for ONE download identity within ONE root
    lifecycle under ONE integration configuration. It is consumed on transfer
    submission and dropped on lifecycle reset or root removal via invalidate().
    Live queue evidence is always evaluated first; any matching record that
    does not prove the root drops the cached proof.

    Invalidation fences the name per target on request-start epochs: after
    invalidate(name), each enabled arr is stale for the name until a fetch
    STARTED after the invalidation has completed. A stale arr can neither
    prove the name nor be stood in for by the absence cache, so neither a
    retained snapshot nor a delayed response to an earlier request can
    recreate the proof. A fresh arr's strong proof releases the name on its
    own even while another arr is unavailable, stale or pending (D-17).

    Configuration identity is (code, url, key fingerprint) per enabled arr;
    any change clears every cache, fence, epoch and backoff and abandons
    in-flight fetches.
    """

    REFRESH_INTERVAL_SECS = 30.0
    BACKOFF_STEPS_SECS = (30.0, 60.0, 120.0, 240.0, 300.0)

    def __init__(self, context: Context, client: ArrQueueClient,
                 clock: Callable[[], float] = time.monotonic):
        self.logger = context.logger.getChild("CompletionGate")
        self._client = client
        self._clock = clock
        # code -> list snapshot; None = last fetch failed/overrun/refused; absent = never completed
        self._snapshots: Dict[str, Optional[List[QueueRecord]]] = {}
        self._epoch: Dict[str, int] = {}
        self._snapshot_epoch: Dict[str, int] = {}
        self._fences: Dict[str, Dict[str, int]] = {}
        self._pending_fetch: Dict[str, _PendingFetch] = {}
        self._next_fetch_at: Dict[str, float] = {}
        self._backoff_index: Dict[str, int] = {}
        self._in_backoff: Dict[str, bool] = {}
        self._config_key: Optional[_ConfigKey] = None
        self._holds: Dict[str, str] = {}
        self._proofs: Dict[str, _Proof] = {}

    # ------------------------------------------------------------------ public

    @property
    def holds(self) -> Dict[str, str]:
        """Copy of name -> reason code for current, non-provisional holds."""
        return dict(self._holds)

    def label(self, reason_code: str) -> str:
        return REASON_LABELS.get(reason_code, reason_code)

    def evaluate(self, candidates: Mapping[str, Optional[int]]) -> Dict[str, Verdict]:
        """
        Decide every candidate (name -> remote size). Never blocks: applies
        completed fetch results, starts at most one fetch per arr, then decides
        from completed snapshots. Names no longer candidates leave the registry.
        """
        return self._run(candidates, prune=True)

    def verdict(self, name: str, remote_size: Optional[int]) -> Verdict:
        """
        Decide a single name with the same non-blocking guarantee as evaluate().
        Holds of other names are left untouched (this is not a full cycle).
        """
        return self._run({name: remote_size}, prune=False)[name]

    def invalidate(self, name: str, cause: str) -> bool:
        """
        Drop the cached proof for `name` and fence it: every enabled arr is
        stale for the name until a fetch started after this call completes.
        Returns True if a proof existed.
        """
        existed = self._proofs.pop(name, None) is not None
        targets = self._client.enabled_targets()
        for t in targets:
            self._epoch[t.code] = self._epoch.get(t.code, 0) + 1
        self._fences[name] = {t.code: self._epoch[t.code] for t in targets}
        self.logger.debug("Completion proof dropped for '%s': %s",
                          sanitize_log_value(name), sanitize_log_value(cause))
        return existed

    def invalidate_all(self, cause: str) -> int:
        """Drop every cached proof. Returns how many were dropped."""
        count = len(self._proofs)
        self._proofs.clear()
        self.logger.debug("Completion proofs dropped (%d): %s", count, sanitize_log_value(cause))
        return count

    # ---------------------------------------------------------------- internal

    def _run(self, candidates: Mapping[str, Optional[int]], prune: bool) -> Dict[str, Verdict]:
        now = self._clock()

        # (1) Integration configuration identity.
        targets = self._client.enabled_targets()
        key: _ConfigKey = tuple(t.identity for t in targets)
        if self._config_key is not None and key != self._config_key:
            self._reset_integration_state()
        self._config_key = key

        # (2) No arr enabled: the gate does not apply (D-16).
        if not targets:
            verdicts = {name: Verdict.not_required() for name in candidates}
            for name in list(self._holds):
                if prune or name in candidates:
                    self._clear_hold(name)
            return verdicts

        # (3) Apply completed results (always, even with no candidates).
        for t in targets:
            self._apply_outcome(t, now)

        # (4) Start fetches: at most one per arr per call, only when needed.
        if candidates:
            for t in targets:
                if self._should_start(t.code, candidates, now):
                    fid = self._client.start_fetch(t)
                    if fid is None:
                        self._record_failure(t, now)
                    else:
                        self._pending_fetch[t.code] = _PendingFetch(fid, self._epoch.get(t.code, 0))

        # (5)-(7) Decide each name, lift fences, update the registry.
        verdicts: Dict[str, Verdict] = {}
        for name, remote_size in candidates.items():
            verdict, provisional = self._decide(name, remote_size, targets, key)
            self._maybe_lift_fence(name, targets)
            self._record(name, verdict, provisional, targets)
            verdicts[name] = verdict

        if prune:
            for name in list(self._holds):
                if name not in candidates:
                    self._clear_hold(name)
        return verdicts

    def _reset_integration_state(self):
        self.invalidate_all("integration configuration changed")
        for code in list(self._pending_fetch):
            self._client.abandon(code)
        self._snapshots.clear()
        self._epoch.clear()
        self._snapshot_epoch.clear()
        self._fences.clear()
        self._pending_fetch.clear()
        self._next_fetch_at.clear()
        self._backoff_index.clear()
        self._in_backoff.clear()

    def _apply_outcome(self, target: ArrTarget, now: float):
        code = target.code
        outcome = self._client.poll(code)
        pending = self._pending_fetch.get(code)
        if outcome.state == FETCH_DONE:
            if pending is None or outcome.fetch_id != pending.fetch_id:
                self.logger.debug("%s: ignoring result for superseded fetch", target.label)
                return
            del self._pending_fetch[code]
            if outcome.records is None:
                self._record_failure(target, now)
                return
            self._snapshots[code] = list(outcome.records)
            self._snapshot_epoch[code] = pending.epoch
            self._backoff_index[code] = 0
            self._in_backoff[code] = False
            self._next_fetch_at[code] = now + self.REFRESH_INTERVAL_SECS
        elif outcome.state == FETCH_OVERRUN:
            self._pending_fetch.pop(code, None)
            self._record_failure(target, now)
        elif outcome.state == FETCH_IDLE and pending is not None:
            # The client no longer tracks our fetch (abandoned): never wait on it.
            del self._pending_fetch[code]
            self._record_failure(target, now)

    def _record_failure(self, target: ArrTarget, now: float):
        code = target.code
        self._snapshots[code] = None
        self._in_backoff[code] = True
        idx = self._backoff_index.get(code, 0)
        delay = self.BACKOFF_STEPS_SECS[min(idx, len(self.BACKOFF_STEPS_SECS) - 1)]
        self._next_fetch_at[code] = now + delay
        self._backoff_index[code] = idx + 1
        suffix = " (fetch still in flight)" if self._client.in_flight(code) else ""
        self.logger.debug("%s queue unavailable; next attempt in %.0f s%s", target.label, delay, suffix)

    def _should_start(self, code: str, candidates: Mapping[str, Optional[int]], now: float) -> bool:
        if code in self._pending_fetch:
            return False
        if self._next_fetch_at.get(code, float("-inf")) <= now:
            return True
        if self._in_backoff.get(code, False):
            return False  # a fence bypasses the refresh interval, never the failure backoff
        snapshot_epoch = self._snapshot_epoch.get(code, -1)
        return any(snapshot_epoch < self._fences[name].get(code, 0)
                   for name in candidates if name in self._fences)

    def _is_fresh(self, name: str, code: str) -> bool:
        if not isinstance(self._snapshots.get(code), list):
            return False
        fence = self._fences.get(name)
        if fence is None:
            return True
        return self._snapshot_epoch.get(code, -1) >= fence.get(code, 0)

    def _is_pending(self, code: str) -> bool:
        return code in self._pending_fetch

    def _classify(self, name: str, code: str) -> str:
        if self._is_fresh(name, code):
            return _FRESH
        if code in self._snapshots and self._snapshots[code] is None:
            return _UNAVAILABLE
        if self._is_pending(code):
            return _PENDING
        if code in self._snapshots:
            return _STALE
        return _UNAVAILABLE

    def _unavailable(self, name: str, code: str) -> Tuple[Verdict, bool]:
        """Hold for an arr that has not given a usable answer; provisional while its fetch is pending."""
        return Verdict.hold(code + "_unavailable"), self._classify(name, code) == _PENDING

    def _decide(self, name: str, remote_size: Optional[int], targets: List[ArrTarget],
                key: _ConfigKey) -> Tuple[Verdict, bool]:
        codes = [t.code for t in targets]

        # Every matching record from every list snapshot, fresh or stale, valid or not.
        matching: List[Tuple[str, QueueRecord]] = []
        for code in codes:
            snapshot = self._snapshots.get(code)
            if isinstance(snapshot, list):
                for rec in snapshot:
                    if rec.basename is not None and rec.basename == name:
                        matching.append((code, rec))

        if matching:
            verdict, provisional = self._decide_from_records(name, remote_size, codes, key, matching)
            if not verdict.proven:
                # Contradicting live evidence overrides any cached proof.
                self._proofs.pop(name, None)
            return verdict, provisional

        # No matching record anywhere: the absence cache needs every arr fresh.
        all_fresh = all(self._is_fresh(name, code) for code in codes)
        proof = self._proofs.get(name)
        if (proof is not None and all_fresh and proof.remote_size == remote_size
                and proof.config_key == key):
            return Verdict.proven(), False
        for code in codes:
            if not self._is_fresh(name, code):
                return self._unavailable(name, code)
        return Verdict.hold("no_queue_entry"), False

    def _decide_from_records(self, name: str, remote_size: Optional[int], codes: List[str],
                             key: _ConfigKey, matching: List[Tuple[str, QueueRecord]]) -> Tuple[Verdict, bool]:
        groups: Dict[str, List[Tuple[str, QueueRecord]]] = {}
        unidentified = False
        for code, rec in matching:
            if rec.download_id is None:
                unidentified = True
            else:
                groups.setdefault(rec.download_id.upper(), []).append((code, rec))
        if unidentified or len(groups) > 1:
            return Verdict.hold("ambiguous_match"), False

        members = next(iter(groups.values()))
        complete = all(rec.valid and rec.status is not None and rec.status.lower() == "completed"
                       and rec.sizeleft == 0 for _, rec in members)
        if not complete:
            return Verdict.hold("still_downloading"), False

        contributing = {code for code, _ in members}
        for code in codes:
            if code in contributing and not self._is_fresh(name, code):
                # Pre-invalidation evidence cannot prove; the forced refresh will replace it.
                return self._unavailable(name, code)

        self._proofs[name] = _Proof(
            download_id=members[0][1].download_id,
            remote_size=remote_size,
            config_key=key,
            epoch=min(self._snapshot_epoch.get(code, 0) for code in contributing),
        )
        return Verdict.proven(), False

    def _maybe_lift_fence(self, name: str, targets: List[ArrTarget]):
        fence = self._fences.get(name)
        if fence is None:
            return
        if all(self._snapshot_epoch.get(t.code, -1) >= fence.get(t.code, 0) for t in targets):
            self._fences.pop(name)

    def _record(self, name: str, verdict: Verdict, provisional: bool, targets: List[ArrTarget]):
        safe = sanitize_log_value(name)
        if verdict.held and provisional:
            self.logger.debug("Completion check awaiting %s response for '%s' (provisional hold)",
                              self.label(verdict.reason), safe)
            return
        previous = self._holds.get(name)
        if not verdict.held:
            if previous is not None:
                self._clear_hold(name)
            return
        if previous is None:
            self.logger.info("Completion hold for '%s': %s", safe, self.label(verdict.reason))
        elif previous != verdict.reason:
            self.logger.info("Completion hold reason changed for '%s': %s -> %s",
                             safe, self.label(previous), self.label(verdict.reason))
        else:
            self.logger.debug("Completion hold unchanged for '%s': %s", safe, self.label(verdict.reason))
        self._holds[name] = verdict.reason

    def _clear_hold(self, name: str):
        if self._holds.pop(name, None) is not None:
            self.logger.info("Completion hold cleared for '%s'", sanitize_log_value(name))
