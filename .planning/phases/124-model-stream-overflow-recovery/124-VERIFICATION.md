---
phase: 124-model-stream-overflow-recovery
verified: 2026-10-27T11:12:09Z
status: gaps_found
score: 9/9 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
gaps:
  - truth: "The resync gate's comment states it 'must run strictly before get_next_event() so the first value after a drop is never a stale backlog event' (stream_model.py:86)"
    status: partial
    severity: minor
    reason: "Code review WR-01 (124-REVIEW.md): the dropped-count check (line 88) and the dequeue (line 105) are two separate, unlocked reads. A producer can drop an event in that narrow window, in which case get_next_event() returns the event immediately after the gap instead of the resync. The code's own next call sees the new drop and resyncs, so the browser tab still converges within one more get_value() cycle -- final convergence (the roadmap's actual success criterion) is unaffected. Independently confirmed: no test in this phase exercises a concurrent producer racing the handler thread (all convergence tests flood synchronously before draining), so this narrow window is real but untested and the comment overstates a per-call guarantee that the implementation does not provide."
    artifacts:
      - path: "src/python/web/handler/stream_model.py"
        issue: "Comment at line 86 claims an invariant ('the first value after a drop is never a stale backlog event') that the check-then-dequeue code below it does not actually enforce under a concurrent producer"
    missing:
      - "Either re-check get_dropped_count() after get_next_event() and discard/resync on a post-dequeue mismatch (124-REVIEW.md's suggested fix), or correct the comment to say the gate is best-effort per-call and convergence is guaranteed on the next call, not this one"
  - truth: "(D-05) A test proves at most one snapshot is ever pending"
    status: partial
    severity: minor
    reason: "Code review WR-02 (124-REVIEW.md): test_resync_pending_state_is_bounded's final assertion (assertIsNone(self.handler.initial_model_files)) checks the already-None initial-model slot from setUp, not the resync-pending state -- it would still pass if _resync_pending were replaced by a growing list. The 'one pending' property is genuinely proven, but by a different test (test_multiple_drops_coalesce_into_one_resync's resync_model_files.assert_called_once()), not by the test whose name and docstring claim to prove it."
    artifacts:
      - path: "src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py"
        issue: "test_resync_pending_state_is_bounded (lines ~210-223) asserts an unrelated attribute instead of self.handler._resync_pending or resync_model_files.assert_called_once()"
    missing:
      - "Replace or add the assertion: assertIs(False, self.handler._resync_pending) and/or self.mock_controller.resync_model_files.assert_called_once()"
  - truth: "REQUIREMENTS.md reflects STRM-01/STRM-02 as complete once the phase closes (the pattern Phase 123 followed with its phase-gate doc commit)"
    status: failed
    severity: minor
    reason: "REQUIREMENTS.md still shows '- [ ] STRM-01' / '- [ ] STRM-02' and traceability status 'Pending' for both, even though ROADMAP.md marks Phase 124 '[x] ... completed 2026-10-27' and all 3 plans are done. No docs commit in this phase's range (2ed7078..HEAD) touches REQUIREMENTS.md, unlike Phase 123 (commit bf73322 'docs(123-05): complete phase gate plan' flipped LIFE-01/LIFE-02 to [x]/Complete). This is a documentation sync gap, not a functional gap -- the underlying work is verified done."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Lines 27-28 checkboxes unchecked; traceability table lines 77-78 show 'Pending' for STRM-01 and STRM-02"
    missing:
      - "Mark STRM-01 and STRM-02 as [x] and 'Complete' in REQUIREMENTS.md as part of closing out this phase (orchestrator/finalize step)"
human_verification: []
---

# Phase 124: Model-Stream Overflow Recovery Verification Report

**Phase Goal:** A slow SSE client that loses incremental model events converges back to the server's current state without unbounded buffering
**Requirements:** STRM-01, STRM-02
**Verified:** 2026-10-27T11:12:09Z
**Status:** gaps_found (three minor, non-blocking gaps; routes to backlog per `has_blocking_gaps: false`)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

All truths below were checked against the actual source diff (`git diff 2ed7078..HEAD`), the actual test files (collected and run, not just read), and — for the RED-before-GREEN claim — independently reproduced by checking out a pre-fix commit into a disposable git worktree and running the real test suite against it, not by trusting SUMMARY.md narration.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1 — Overflow reproduced at the model-stream boundary with a recorded, repeatable test, before any fix | VERIFIED | `test_stream_model_overflow.py::TestModelStreamOverflowReproduction::test_stalled_listener_overflow_diverges_from_server_model` — real `Controller`/`Model`/`__model_lock`, real `WebResponseModelListener`, 1501 events (1 remove + 1500 adds) against maxsize 1000. Ran it directly: PASSED. Commit `003a26b`/`c7e33ae` (both `test(124-01)`) land before any production file is touched (`git diff --name-only` for 124-01 touches only `src/python/tests/`). |
| 2 | SC2 — If an existing recovery guarantee is found, record it and close with no code change | N/A (condition not met, correctly) | 124-01-SUMMARY.md records `dropped=501`, `queue=1000`, `missing=500 files (file-0000..file-0499)`, `ghost.txt present` — i.e. divergence, not convergence. Verdict line is exactly `Verdict: no existing recovery guarantee for the model stream; proceed to STRM-02 fix (124-02, 124-03).` Independently confirmed by running the reproduction test (above): client model diverges from server. |
| 3 | SC3 — After overflow the slow client's model matches the server's current state, demonstrated by a test that fails before and passes after | VERIFIED | Ran the exact convergence suite (unit + integration) against commit `3411e50` (both RED commits landed, GREEN fix `52da527` not yet applied) in a disposable worktree: **10 of 10 expected tests FAILED** (`TestModelStreamConvergence` x4, `TestModelStreamHandlerResync` x5 excluding the one no-drop test, `test_stalled_consumer_converges_after_overflow`), 22 others passed, matching 124-03-SUMMARY's claimed RED output exactly. Ran the same suite at `HEAD`: all 10 now PASS, confirmed by `assertEqual(server_snapshot(controller.get_model_files()), client.files)` for both the real-`Controller` unit test and the real-WSGI-generator/real-`SerializeModel` integration test. |
| 4 | SC4 — Buffering stays bounded under a stalled consumer; producer atomicity alone is not accepted; no event-bus redesign | VERIFIED | `test_queue_never_exceeds_maxsize_under_sustained_stall` (5000 puts into maxsize=1000, asserted after every put) passes. `StreamQueue.put()` is byte-for-byte unchanged (`git diff HEAD~1 -- src/python/web/utils.py` around `def put` shows no change; confirmed by reading the file). The fix is a resync gate in `ModelStreamHandler.get_value()` plus `Controller.resync_model_files()` — no new event bus, no pub/sub layer; `controller/` still has zero imports from `web/` (`grep -rnE "^(from|import) web" src/python/controller/` → empty). |

**Score:** 4/4 roadmap success criteria verified.

### Plan-Level Must-Haves

| # | Must-have | Status | Evidence |
|---|-----------|--------|----------|
| 5 | (D-01) Reproduction: real Controller/Model/lock, stalled listener, 1501 events, dropped=501, queued=1000 | VERIFIED | Ran directly; matches exactly (see SC1 row). |
| 6 | (D-06) Status stream self-healing evidence, no code change | VERIFIED | `TestStatusStreamSelfHealingEvidence::test_overflowed_status_listener_still_delivers_latest_snapshot` — 1200 `notify()` calls, `dropped==200`, last of 1000 drained events `is` the final snapshot. Ran directly: PASSED. `git log --oneline -- src/python/web/handler/stream_status.py src/python/web/handler/stream_log.py src/angular \| grep -c '124-'` → `0`. |
| 7 | (D-07) Stall-capable SSE harness `open_sse_stream()` | VERIFIED | `tests/helpers/wsgi_stream.py` has exactly 1 `def open_sse_stream` (returns un-iterated body); used by the real integration convergence test (`test_stalled_consumer_converges_after_overflow`), which PASSED when run. |
| 8 | `StreamQueue.clear()` exists, discards backlog, leaves `dropped_count` unchanged, works empty, allows `put()` after | VERIFIED | `web/utils.py:74-84`, `def clear(self) -> None`; `test_clear_discards_backlog`/`test_clear_does_not_affect_dropped_count`/`test_clear_on_empty_queue`/`test_put_after_clear` all PASSED when run directly. |
| 9 | (D-03) `Controller.resync_model_files(discard_backlog)` runs the callback and takes the snapshot in one `__model_lock` acquisition; blocks on a held lock; works with a real listener; does not add/remove listeners; propagates exceptions and releases the lock | VERIFIED | `controller.py:532-541`; `with self.__model_lock: discard_backlog(); return self.__get_model_files()`, no try/except. All 6 `TestResyncModelFiles` tests (real `threading.Thread` + real `Lock`, real `WebResponseModelListener`) read and run directly: PASSED. `grep -rnE "^(from\|import) web" src/python/controller/` → empty (controller/ still imports nothing from web/). |
| 10 | (D-02) `ModelStreamHandler.get_value()` sends a fresh `model-init` on the same connection after a drop, via `resync_model_files` | VERIFIED | `stream_model.py:81-102`: dropped-count delta sets `_resync_pending`; when pending, calls `self.controller.resync_model_files(self._discard_backlog)` and returns `self.serialize.model(files)`. `grep -c "self.controller.resync_model_files(self._discard_backlog)"` → 1. |
| 11 | (D-07b) Real-Controller unit convergence + real-WSGI-generator integration convergence, both RED before the fix and GREEN after | VERIFIED | Independently reproduced RED at commit `3411e50` (10 failed) and GREEN at `HEAD` (all pass) — see SC3 row. Both RED commits (`a169f57`, `3411e50`) precede the GREEN commit (`52da527`) in `git log --oneline`. |
| 12 | (D-04) Coalesced pending-resync state is a single bool, never a list; any number of drops before delivery fold into one resync | VERIFIED (property proven; one test's assertion is weak — see Gap 2) | `_resync_pending: bool` in `__init__` (no list/collection anywhere in the class). `test_multiple_drops_coalesce_into_one_resync` (three overflow bursts → `resync_model_files.assert_called_once()`) PASSED directly. `test_drop_during_resync_is_absorbed` (a drop landing inside the lock during discard is absorbed, no second resync) PASSED directly. |
| 13 | (D-05) Bounded buffering at the handler: queue `<= maxsize` during stall; empty after resync | VERIFIED | `test_resync_pending_state_is_bounded`'s queue-size assertions and `test_stalled_tab_converges_to_server_model_after_overflow`'s `assertLessEqual(get_queue_size(), get_maxsize())` both PASSED directly. |
| 14 | (D-08) Resync warning rate-limited by resync count (1, 101, ... log; 2-100 don't), counts only, no file names | VERIFIED | `stream_model.py:94-101`: `if self._resync_count % 100 == 1: self.logger.warning(...)` with only integer counts interpolated. `test_resync_warning_rate_limited_by_resync_count` (101 cycles → exactly 2 log records) PASSED directly. |
| 15 | Normal (no-drop) behavior unchanged; `resync_model_files` never called without a drop | VERIFIED | `test_no_resync_without_drops` PASSED directly; full pre-existing `test_web`/`test_controller`/integration suites (1335 tests) pass with 0 failures. |

**Score:** 9/9 distinct STRM-01/STRM-02 technical must-haves verified (rows 5-15 collapse to 9 unique capability claims; two carry a non-blocking documentation/assertion-quality caveat recorded as Gap 1/Gap 2 below).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/python/tests/helpers/model_stream_client.py` | `ModelStreamClient`, `parse_sse_events`, `server_snapshot`, `apply_all` | VERIFIED | `grep -E "class ModelStreamClient\|def parse_sse_events\|def server_snapshot\|def apply_all"` → 4 matches. Mirrors the frontend's 4 `parseEvent` rules exactly (read and confirmed against the plan's spec). |
| `src/python/tests/helpers/wsgi_stream.py` | `open_sse_stream`, `collect_sse_chunks` unchanged | VERIFIED | Both present, 1 each. |
| `src/python/tests/unittests/test_web/test_handler/test_stream_model_overflow.py` | `TestModelStreamOverflowReproduction`, `TestModelStreamConvergence`, `TestStatusStreamSelfHealingEvidence` | VERIFIED | All 3 classes present; 6 tests, all PASS when run directly. |
| `src/python/web/utils.py` | `StreamQueue.clear()`, `put()` unchanged | VERIFIED | `def clear(self) -> None` present; `put()` byte-identical to pre-phase version. |
| `src/python/controller/controller.py` | `resync_model_files(discard_backlog)` | VERIFIED | Exact signature match via grep; zero web imports. |
| `src/python/tests/unittests/test_controller/test_controller_unit.py` | `TestResyncModelFiles` (6 tests) | VERIFIED | Present, all 6 PASS when run directly (real lock, real thread, real listener). |
| `src/python/web/handler/stream_model.py` | Resync gate in `get_value()` | VERIFIED | Gate precedes `get_next_event()` by line order (88 < 105); wired to `resync_model_files`. |
| `src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py` | `TestModelStreamHandlerResync` (6 tests) | VERIFIED | Present, all 6 PASS when run directly. |
| `src/python/tests/integration/test_web/test_handler/test_stream_model.py` | `test_stalled_consumer_converges_after_overflow` | VERIFIED | Present, PASSES directly through the real WSGI generator and real `SerializeModel`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `stream_model.py ModelStreamHandler.get_value` | `controller.py Controller.resync_model_files` | `self.controller.resync_model_files(self._discard_backlog)` | WIRED | `grep -c` → 1; exercised by `TestModelStreamHandlerResync` (mocked Controller, call asserted) and by `TestModelStreamConvergence`/the integration test (real/mock Controller actually invoked and the resulting model-init actually sent). |
| `ModelStreamHandler._discard_backlog` | `WebResponseModelListener.clear` + `get_dropped_count` | runs inside `resync_model_files`'s `__model_lock` | WIRED | `_discard_backlog` body calls `self.model_listener.clear()` then rebaselines `self._last_seen_dropped`; proven atomic by `test_resync_with_real_listener_discards_backlog_and_keeps_later_events` and `test_drop_during_resync_is_absorbed`. |
| `Controller.resync_model_files` | `self.__model_lock` | `with self.__model_lock: discard_backlog(); return self.__get_model_files()` | WIRED | Confirmed by reading the method body and by `test_discard_runs_while_model_lock_held` / `test_resync_blocks_until_model_lock_released` (real thread blocks on the held lock, completes after release, result reflects only pre-release mutations). |

### Data-Flow Trace (Level 4)

Not applicable in the usual UI-rendering sense — this phase is server-side stream state, not a rendered component. The equivalent trace (server model → wire event → client reducer) is exactly what the convergence tests assert end-to-end: `Controller.get_model_files()` (real DB-equivalent source of truth, the in-memory `Model`) → `SerializeModel().model()/update_event()` (real serialization, exercised through the real WSGI generator in the integration test) → `ModelStreamClient` (a faithful mirror of the production Angular reducer) → `assertEqual(server_snapshot(...), client.files)`. No hardcoded/static data anywhere in this path; traced and confirmed FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| STRM-01 reproduction reproduces independently | `poetry run pytest .../test_stream_model_overflow.py::TestModelStreamOverflowReproduction -v` | 1 passed | PASS |
| Full targeted suite (unit+integration, this phase's files + dependents) | `poetry run pytest tests/unittests/test_web/ tests/unittests/test_controller/ tests/integration/test_web/test_handler/test_stream_model.py -q` (excluding the two documented macOS-only hangs) | 1335 passed | PASS |
| Whole-tree lint | `ruff check src/python/` | All checks passed! | PASS |
| No web import from controller/ | `grep -rnE "^(from\|import) web" src/python/controller/` | empty | PASS |
| Full local suite + coverage gate | `poetry run pytest --cov ... -q` (with the same documented local-only exclusions) | 1873 passed, coverage 89.99% (gate 88%) | PASS |
| Docker CI-equivalent suite | `make run-tests-python` | `1986 passed, 62 skipped ... exited with code 0` | PASS (ran live, not reused from SUMMARY) |
| RED reproduction (pre-fix) | checked out `3411e50` into a disposable worktree, ran the same convergence suite | 10 failed (exactly the expected set), 22 passed | PASS (confirms "fails before") |
| Known macOS-local-only hangs | `tests/unittests/test_controller/test_extract/test_extract_process.py`, `.../test_scan/test_scanner_process.py` run locally | 6 failed / 3 failed+3 errored respectively | Excluded locally as directed; both pass in Docker (confirmed above, both appear PASSED in the `make run-tests-python` log) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention applies to this phase (web-server unit/integration test fix, not a migration/tooling phase); no probes declared in any PLAN/SUMMARY. Skipped.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| STRM-01 | 124-01 | Overflow reproduced; existing-guarantee path recorded if found | SATISFIED (code) / NOT YET REFLECTED in REQUIREMENTS.md | Reproduction test runs and passes; verdict recorded in 124-01-SUMMARY.md. REQUIREMENTS.md still shows `[ ]`/"Pending" — see Gap 3. |
| STRM-02 | 124-02, 124-03 | Convergence with bounded buffering; producer atomicity alone not accepted | SATISFIED (code) / NOT YET REFLECTED in REQUIREMENTS.md | Convergence proven RED-before-GREEN at unit and integration level (independently reproduced); bounded buffering proven at queue and handler level. REQUIREMENTS.md still shows `[ ]`/"Pending" — see Gap 3. |

No orphaned requirements: PLAN frontmatter across 124-01/02/03 declares exactly `{STRM-01, STRM-02}`, and REQUIREMENTS.md's "Model-Stream Overflow" section maps exactly those two IDs to Phase 124 — full coverage both directions.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers, no empty stub implementations (`return None`/`return {}`/`=> {}`), and no hardcoded-empty-data patterns were found in any file this phase modified (`stream_model.py`, `utils.py`, `controller.py`, and the 5 test files). The only findings are the two code-review warnings already surfaced above (WR-01, WR-02), reflected as Gap 1 and Gap 2.

### Human Verification Required

None. This phase's goal (server-side stream convergence under a stalled SSE consumer) is fully verifiable by automated test and direct code inspection; D-07 explicitly scoped this phase to automated tests only, with no NAS sandbox session required (web-server-only change, no transfer/import/delete path touched) — consistent with the phase's own decision record.

### Gaps Summary

Three gaps found, **all minor and non-blocking** (`has_blocking_gaps: false`):

1. **WR-01 (comment overstatement, not a convergence failure):** the resync gate's dropped-count check and its dequeue are two separate unlocked reads, so a drop that lands in that exact window can let one post-gap event through before the very next `get_value()` call resyncs. Final convergence — the actual roadmap success criterion — is not affected (confirmed by tracing the next-call behavior); only the code comment's stronger per-call claim is inaccurate. Code review itself rated this a non-blocking warning.
2. **WR-02 (weak test assertion):** `test_resync_pending_state_is_bounded`'s closing assertion checks an unrelated attribute. The property it's meant to prove (at most one pending resync) is still genuinely proven by a sibling test, so no functional gap — just a test that doesn't document what it claims to.
3. **REQUIREMENTS.md not yet updated:** STRM-01/STRM-02 remain `[ ]`/"Pending" in `.planning/REQUIREMENTS.md` despite ROADMAP.md correctly marking Phase 124 complete and all underlying work being verified. Prior phases (e.g. 123) closed this gap with an explicit phase-gate docs commit; 124 has no equivalent commit. Purely a documentation-sync item for phase closure, not a code gap.

None of the three block the phase goal: the model-stream overflow recovery mechanism is implemented, tested with real locks/threads/WSGI generator, proven to fail before and pass after the fix, bounded, and scoped exactly as the roadmap and REQUIREMENTS specify. Recommend routing all three to backlog (`/bm:add-backlog`) rather than a follow-up phase, with gap 3 resolved as part of this phase's own closure docs rather than a new backlog item.

---

*Verified: 2026-10-27T11:12:09Z*
*Verifier: Claude (bm-verifier)*
