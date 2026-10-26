---
phase: 123-startup-and-shutdown-lifecycle
plan: 08
subsystem: backend-lifecycle
tags: [tdd, gap-closure, gap-1, d-01, sigterm, scanner-health-check, monotonic-clock]

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "06"
    provides: "Live restart evidence (123-LIFE-EVIDENCE.md 'Sandbox re-pin') proving the 123-04 one-cycle SIGTERM grace loses the race against a 0.67-1.55 s main-thread handler latency"
provides:
  - "ScanManager clock-injected, time-bounded (10.0 s) SIGTERM grace in _check_process_health(), replacing the one-ControllerJob-cycle recheck"
  - "Deterministic fake-clock regression tests pinning the grace window, including literal replays of the live I1 (+1.55 s) and A2 (+0.67 s) handler-latency timings"
affects: ["123-10 (rejected-alternatives record for the evidence file)", "123-11/123-12 (live restart re-check that this fix actually eliminates the false ERROR on a real docker restart)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Clock injection for deterministic time-bounded tests: ScanManager.__init__(..., clock: Callable[[], float] = time.monotonic), matching the existing arr_queue.py / completion_gate.py pattern -- a module-level _FakeClock class (never a lambda bound to a name, ruff E731) with a mutable .now attribute stands in for time.monotonic in tests"
    - "Deadline-from-first-sighting: an Optional[float] timestamp set once when an ambiguous condition is first observed, read on every later check via (now - first_seen) < window, never reset until a fresh instance -- replaces a boolean one-shot recheck latch with a clock-measured window that is immune to how many intervening cycles run"

key-files:
  created: []
  modified:
    - src/python/controller/scan_manager.py
    - src/python/tests/unittests/test_controller/test_scan_manager.py

key-decisions:
  - "Chose a clock-injected, time-bounded grace window (10.0 s, docker's default stop timeout) over the rejected alternatives: (b) signal.pthread_sigmask blocking SIGTERM in worker threads was rejected because forked children inherit the forking thread's signal mask, which would break AppProcess.terminate() (relies on SIGTERM) and cannot cover threads created by libraries outside this code's control (web server, multiprocessing feeders, Timer threads); (c) having children handle SIGTERM themselves was rejected because it changes child-process semantics more widely than this gap needs"
  - "The grace deadline is measured from the FIRST sighting of an all-SIGTERM death and is never extended by a later SIGTERM death inside the same window (test_sigterm_grace_measured_from_first_sighting pins this)"
  - "Documented cost: a genuine SIGTERM-only death with no shutdown request now surfaces up to 10 s plus one ControllerJob cycle later than before this change; every other kind of death (OOM's SIGKILL, a non-zero exit, a mix that includes a non-SIGTERM code) still raises on the same check it is first seen, unchanged"
  - "D-02 split: the grace window, the replay of the measured 0.67 s and 1.55 s handler latencies, the bounded surfacing of a genuine SIGTERM-only death, and immediate raising for every other death are unit-proven here with a fake clock and no real processes or sleeps; that a real docker restart actually logs neither the false ERROR nor ScannerProcessDiedError is live-proven only in 123-11/123-12"

patterns-established:
  - "A deadline-from-first-sighting latch (Optional[float] timestamp, not a boolean) is the shape to reach for whenever a health check must give an ambiguous external event a bounded grace period measured against a real clock rather than a fixed number of poll cycles"

requirements-completed: [LIFE-02]

# Metrics
duration: ~20min
completed: 2026-10-26
---

# Phase 123 Plan 08: Clock-Bounded SIGTERM Scanner Grace (GAP-1) Summary

**ScanManager now decides "expected shutdown" vs. "genuine scanner death" on a 10.0 s monotonic-clock window measured from the first all-SIGTERM sighting, instead of a single ControllerJob cycle (0.5 s) -- closing the gap where the live main-thread SIGTERM handler ran 0.67-1.55 s after the scanners died and lost the old one-cycle race, producing the false "Scanner process(es) died unexpectedly" ERROR seen in 3 of 5 live restart cycles (123-06).**

## Performance

- **Duration:** ~20 min (RED commit `17387a6` at 2026-10-26T14:24:47-04:00, GREEN commit `1ffc601` at 2026-10-26T14:26:41-04:00; elapsed time also includes reading plan/context/gap-evidence files and running the verification suites before and after each commit)
- **Tasks:** 2 (RED test commit, GREEN fix commit)
- **Files modified:** 2 (1 test file in Task 1, 1 source file in Task 2)

## Accomplishments

- `ScanManager.__init__` gained `clock: Callable[[], float] = time.monotonic`, stored as `self.__clock`, following the exact clock-injection signature already used by `arr_queue.py` and `completion_gate.py`.
- Added the class constant `_SIGTERM_SHUTDOWN_GRACE_IN_SECS = 10.0` (docker's default stop timeout) and replaced the boolean `__sigterm_recheck_pending` one-shot latch with `__sigterm_first_seen: Optional[float]`, which records the clock reading when an all-SIGTERM death is first observed without a shutdown request.
- Rewrote the grace branch of `_check_process_health()`: on first sighting it logs DEBUG once and returns; on every subsequent check within `now - first_seen < 10.0` it returns silently (no per-cycle log spam); once the window elapses it falls through to the unchanged ERROR + `_terminate_and_join_all()` + `ScannerProcessDiedError` path. The shutdown-requested branch (INFO, no raise) and the final ERROR path are byte-identical to before.
- Rewrote the `_check_process_health()` docstring to explain the tini/SIG_DFL mechanism, the measured 0.67-1.55 s live handler latency, why the window is clock-based rather than cycle-based, why 10 s was chosen, and the documented detection-delay cost.
- Added 8 new fake-clock tests and modified 1 existing test (`test_shutdown_aware_sigterm_death_then_request_is_benign`, now constructed with the fake clock) under a renamed section comment (`# --- D-01 / GAP-1: shutdown-aware health check and time-bounded SIGTERM grace ---`). Deleted `test_shutdown_aware_sigterm_death_rechecked_once_then_raises`, whose one-cycle contract was the defect.
- No `sleep(` was added to product or test code. `controller.py` and `seedsyncarr.py` were not touched; both DEFER-SHUTDOWN sleep call sites remain untouched (out of this plan's scope, not re-verified here since no file touching them was modified).

## Task Commits

1. **Task 1 (RED): fake-clock tests for a time-bounded SIGTERM grace** - `17387a6` (test)
2. **Task 2 (GREEN): clock-injected 10 s SIGTERM grace in `_check_process_health()`** - `1ffc601` (fix)

_No refactor commit was needed; the GREEN implementation matched the planned shape on the first pass._

## RED Results (Task 1, commit `17387a6`)

Command: `cd src/python && timeout 300 poetry run pytest tests/unittests/test_controller/test_scan_manager.py -p no:cacheprovider -q`

Result: **9 failed, 24 passed.** Every failure was one of the new or modified GAP-1 tests; no pre-existing, untouched test failed:

| Test | Observed failure |
|------|-------------------|
| `test_sigterm_grace_defaults` | `AttributeError`/assertion failure: `ScanManager.__init__` has no `clock` parameter and no `_SIGTERM_SHUTDOWN_GRACE_IN_SECS` constant yet |
| `test_sigterm_death_not_reported_within_grace_across_many_cycles` | `TypeError: ScanManager.__init__() got an unexpected keyword argument 'clock'` |
| `test_sigterm_death_handler_late_1_55s_resolves_as_shutdown` | same `TypeError` |
| `test_sigterm_death_handler_late_0_67s_resolves_as_shutdown` | same `TypeError` |
| `test_sigterm_death_raises_when_grace_elapses` | same `TypeError` |
| `test_sigterm_grace_measured_from_first_sighting` | same `TypeError` |
| `test_sigterm_grace_then_non_sigterm_death_raises_immediately` | same `TypeError` |
| `test_nonzero_exit_raises_on_first_check` | same `TypeError` |
| `test_shutdown_aware_sigterm_death_then_request_is_benign` | same `TypeError` (modified to pass `clock=`) |

Acceptance-criteria checks, all confirmed:
- `grep -c "def test_shutdown_aware_sigterm_death_rechecked_once_then_raises"` -> `0`
- `grep -c` the four named new-test strings -> `4`
- `grep -c "sleep("` in the test file -> `0`
- `git log -1 --format=%s` -> `test(123-08): ...`; `git show --stat --format= HEAD` -> only `src/python/tests/unittests/test_controller/test_scan_manager.py`

## GREEN Results (Task 2, commit `1ffc601`)

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_controller_job.py tests/unittests/test_seedsyncarr.py -p no:cacheprovider -q`

Result: **133 passed, 0 failed.**

Whole-tree lint: `ruff check src/python/` -> `All checks passed!`

Acceptance-criteria greps, all confirmed:
- `grep -c "_SIGTERM_SHUTDOWN_GRACE_IN_SECS = 10.0" src/python/controller/scan_manager.py` -> `1`
- `grep -c "sigterm_recheck_pending" src/python/controller/scan_manager.py` -> `0`
- `grep -cF "clock: Callable[[], float] = time.monotonic" src/python/controller/scan_manager.py` -> `1`
- `grep -cF "Scanner process(es) died unexpectedly: {}" src/python/controller/scan_manager.py` -> `1`; `grep -cF "stopped during shutdown: {}" src/python/controller/scan_manager.py` -> `1` (log texts unchanged)
- `git diff HEAD~1 -- src/python/controller/scan_manager.py | grep "^+" | grep -c "sleep("` -> `0`
- `git diff HEAD~2 --name-only -- src/` -> exactly `src/python/controller/scan_manager.py` and `src/python/tests/unittests/test_controller/test_scan_manager.py`
- `git log -2 --format=%s` -> `fix(123-08): ...` on top of `test(123-08): ...`

A supplementary whole-local-suite run (`poetry run pytest tests/unittests`, outside the plan's required command) was also started; consistent with the known environment behavior documented in 123-04's summary (two prior attempts each stalled around 41% with no failures observed before timing out), this run did not reach completion within a practical wait and was terminated. It is not relied on for this plan's "done" claim -- the plan's own prescribed verification command (133 passed / 0 failed, above) is what backs this plan's completion.

## Approach Chosen and Rejected Alternatives

**Chosen:** a clock-injected, time-bounded SIGTERM grace window (10.0 s, matching docker's default stop timeout) measured from the first sighting of an all-SIGTERM death, independent of how many ControllerJob cycles elapse or how late the main thread's SIGTERM handler runs.

**Rejected (b): `signal.pthread_sigmask` blocking SIGTERM in worker threads.** Forked children inherit the forking thread's signal mask. The scanner processes are started from the `ControllerJob` thread, so blocking SIGTERM there would be inherited by the forked scanner children and would break `AppProcess.terminate()`, which relies on sending SIGTERM to those same children. It also cannot cover threads created by libraries outside this code's control (the web server, multiprocessing feeders, `Timer` threads), so it would not close the gap for those paths.

**Rejected (c): children handling SIGTERM themselves.** This changes child-process signal-handling semantics more broadly than this gap needs, and would not by itself fix the parent-side race this plan addresses (the parent still needs to distinguish an expected stop from a genuine death).

## Documented Detection-Delay Cost

A genuine SIGTERM-only death with no shutdown request now surfaces up to 10 s plus one ControllerJob cycle later than it did before this change (previously, one 0.5 s cycle). This is a deliberate trade: it bounds the false-positive ERROR to zero on any real `docker stop`/`docker restart` (the handler either runs inside the 10 s window, or docker SIGKILLs the container when the window ends), at the cost of a slower surfacing of a genuine, unsignaled scanner death into the existing bounded auto-restart (RECOV-01). Every other kind of death (SIGKILL/OOM's exitcode -9, a non-zero exit, or a mix that includes a non-SIGTERM code) is unaffected and still raises on the same check it is first seen -- this is pinned by `test_sigterm_grace_then_non_sigterm_death_raises_immediately` and `test_nonzero_exit_raises_on_first_check`.

## D-02 Split (unit-proven vs. live-proven)

**Unit-proven (this plan, with a fake clock and no real processes or sleeps):**
- The 10.0 s grace window itself, and that it is not reported (no ERROR, no `ScannerProcessDiedError`, no terminate/join) on any check within the window, across many intervening cycles (`test_sigterm_death_not_reported_within_grace_across_many_cycles`).
- The exact live I1 (+1.55 s) and A2 (+0.67 s) handler-latency timings from 123-LIFE-EVIDENCE.md, replayed as deterministic regression tests that resolve via the shutdown-aware INFO path once `note_shutdown_requested()` arrives inside the window.
- The bounded surfacing of a genuine SIGTERM-only death with no shutdown request: the first check at or after `first_seen + 10.0 s` raises the unchanged ERROR, terminates/joins once, and a further check makes no new terminate call.
- That the grace deadline is fixed at the first sighting and is not extended by a second scanner dying SIGTERM later inside the same window.
- That any non-SIGTERM death (a `-9` OOM kill, a non-zero exit, or a mix that includes a non-SIGTERM code), including one that appears while a SIGTERM grace window is already open, still raises on that same check, unchanged from before this plan.

**Live-proven only (123-11/123-12 -- not claimed here):**
- That a real `docker stop`/`docker restart` on the new build logs neither the false "Scanner process(es) died unexpectedly" ERROR nor raises `ScannerProcessDiedError`, across repeated cycles, closing the gap observed in 123-06's 3-of-5 FAIL result.
- That the 10 s window genuinely never collides with docker's own stop-timeout-then-SIGKILL behavior on the real NAS sandbox.

## Files Created/Modified

- `src/python/controller/scan_manager.py` -- `clock` parameter added to `__init__` (default `time.monotonic`); `_SIGTERM_SHUTDOWN_GRACE_IN_SECS = 10.0` class constant added; `__sigterm_recheck_pending` boolean replaced by `__sigterm_first_seen: Optional[float]`; `_check_process_health()`'s SIGTERM branch rewritten to a clock-measured deadline-from-first-sighting; docstring rewritten to document the mechanism, the measured latencies, the 10 s choice, and the detection-delay cost.
- `src/python/tests/unittests/test_controller/test_scan_manager.py` -- added `import inspect`, `import time`, and a module-level `_FakeClock` helper class; renamed the D-01 section comment; added 8 new tests, modified 1 existing test to use the fake clock, and deleted 1 test whose one-cycle contract was the defect.

## Decisions Made

See `key-decisions` in the frontmatter above (chosen approach vs. rejected alternatives, deadline-from-first-sighting semantics, documented detection-delay cost, D-02 split).

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<behavior>` sections were followed verbatim; no Rule 1-4 auto-fixes were needed.

## Issues Encountered

- The worktree's branch HEAD did not match the orchestrator-supplied base commit (`6d48023...`) when this agent started: `git merge-base HEAD 6d48023...` resolved to `a56a1f8...` (a Phase 122 pre-merge ancestor), and `6d48023` was confirmed NOT an ancestor of the worktree's starting HEAD (`d82c4ae`, PR #134's merge commit onto `main`). Per the mandatory `<worktree_branch_check>` step, the branch namespace was confirmed to be a valid per-agent branch first, then `git reset --hard 6d48023bcb5cf741d8d89cdcbfb1d01bdffe97e4` was run, correcting the worktree to the expected phase-123 gap-closure base before any plan file was read or edited.
- A supplementary whole-local-suite run (`poetry run pytest tests/unittests`, outside the plan's required verification command) was started for extra confidence beyond the plan's prescribed command; consistent with 123-04's documented experience in this environment, it did not finish in a practical wait and was terminated (the underlying process was killed) rather than left running. Not relied on for this plan's "done" claim -- the plan's own prescribed verification command (133 passed / 0 failed, reported above) is what backs this plan's completion.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GAP-1's unit-provable half is closed: the SIGTERM grace is now clock-bounded rather than cycle-bounded, with deterministic replays of both live handler-latency measurements (0.67 s and 1.55 s) from 123-06, and the genuine-death ERROR path, the shutdown-aware INFO path, and every other exitcode's immediate-raise behavior are all pinned as regressions.
- 123-10 can now record the rejected alternatives (pthread_sigmask, child SIGTERM handlers) in the phase evidence file, citing this plan's reasoning.
- 123-11/123-12 can now re-run the live `docker restart` cycles on a build containing this fix to confirm the false ERROR no longer fires on the real NAS sandbox, closing out GAP-1 as fully proven.
- No blockers identified for dependent plans in this wave.

## Self-Check: PASSED

- FOUND: src/python/controller/scan_manager.py
- FOUND: src/python/tests/unittests/test_controller/test_scan_manager.py
- FOUND commit: 17387a6 (test(123-08))
- FOUND commit: 1ffc601 (fix(123-08))

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*
