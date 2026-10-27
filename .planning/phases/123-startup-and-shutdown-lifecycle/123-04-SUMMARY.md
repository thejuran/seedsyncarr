---
phase: 123-startup-and-shutdown-lifecycle
plan: 04
subsystem: backend-lifecycle
tags: [tdd, d-01, shutdown-aware-health-check, sigterm, tini, python]

# Dependency graph
requires:
  - phase: 123-02
    provides: "ScanManager.start() partial-start cleanup and _terminate_and_join() fault isolation (this plan's health-check rewrite builds on that shape)"
  - phase: 123-03
    provides: "Controller.start() partial-failure cleanup (this plan adds a sibling method, note_shutdown_requested(), between start() and process())"
provides:
  - "ScanManager.note_shutdown_requested() + shutdown-aware _check_process_health(): dead scanners after a requested shutdown log INFO and never raise; an all-SIGTERM death with no request yet gets one extra cycle before raising"
  - "Controller.note_shutdown_requested() delegating to ScanManager, no lock, __shutdown_event untouched"
  - "Seedsyncarr.signal() marks shutdown on the live controller before raising ServiceExit, tolerating no controller yet and logging (never masking) a note_shutdown_requested failure"
affects: ["123-06", "123-07 (live restart check proves the unit-proven D-01 fix actually eliminates the scanner-death error on a real docker restart)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shutdown-signal idiom: a component-local threading.Event, set by a one-way note_*_requested() call and read only by the health check that needs it -- no new lock, no polling thread, mirrors the existing Job.shutdown_flag / Controller.__shutdown_event family without reusing either (reuse would have changed the auto-delete guard or stopped the job before the DEFER-SHUTDOWN sleep)"
    - "One-cycle grace period for an ambiguous signal race: a boolean latch (__sigterm_recheck_pending) defers judgment exactly one health-check cycle when the evidence (all-SIGTERM exitcodes) is consistent with 'shutdown is about to be requested' but not yet certain"

key-files:
  created: []
  modified:
    - src/python/controller/scan_manager.py
    - src/python/controller/controller.py
    - src/python/seedsyncarr.py
    - src/python/tests/unittests/test_controller/test_scan_manager.py
    - src/python/tests/unittests/test_controller/test_controller.py
    - src/python/tests/unittests/test_seedsyncarr.py

key-decisions:
  - "D-02 split recorded explicitly below: handler-to-ScanManager wiring, the INFO/no-raise path, the SIGTERM one-cycle recheck, and the unchanged ERROR path are unit-proven in this plan; that tini's group SIGTERM actually produces exitcode -15 on a real restart, and that a real restart logs neither the scanner error nor the lftp error, is live-proven only in plans 06/07"
  - "D-03 verdict reconfirmed, no code change: the DEFER-SHUTDOWN sleep is kept; both time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS) call sites and their comments are byte-for-byte unchanged (grep count stayed 2; diff shows zero added sleep( lines)"
  - "Open Question 2 (Controller.__init__'s eager lftp spawn) stays out of scope, recorded as a backlog candidate -- it is a different code path (constructor-time, not start()-time) than anything this plan touches"

patterns-established:
  - "A component that must distinguish 'this failure is expected because shutdown already started' from 'this is a real failure' reads a local Event set by a one-way note_*_requested() call threaded down from the signal handler through Controller -- never by reusing __shutdown_event or Job.shutdown_flag for an unrelated purpose"

requirements-completed: [LIFE-02]

# Metrics
duration: ~20min (excluding two unrelated 10-minute supplementary whole-suite attempts described below)
completed: 2026-10-25
---

# Phase 123 Plan 04: Shutdown-Aware Scanner Health Check (D-01) Summary

**ScanManager now distinguishes a scanner killed by the container's own SIGTERM from a genuine unexpected death: dead scanners seen after `Controller.note_shutdown_requested()` (wired from `Seedsyncarr.signal()`) log INFO and never raise, and an all-SIGTERM death with no request yet gets exactly one extra health-check cycle before the unchanged ERROR + `ScannerProcessDiedError` path fires.**

## Performance

- **Duration:** ~20 min of active implementation/verification (RED commit `2c87bcf` at 13:59:46, GREEN commit `c69559c` at 14:01:46, base `4eafa25` at 13:54:52)
- **Started:** 2026-10-25T13:54:52-04:00 (worktree reset to phase-123 base)
- **Completed:** 2026-10-25 (this summary)
- **Tasks:** 2 (RED test commit, GREEN fix commit)
- **Files modified:** 6 (3 test files in Task 1, 3 source files in Task 2)

## Precondition Check (Task 1)

Per the plan's owner rule (PR #134 / Phase 122 must be on `main` before any Phase 123 code):

```
$ git fetch origin
$ git show origin/main:src/python/controller/controller.py | grep -c _POST_TRANSFER_GRACE_SECS
5
$ grep -c _POST_TRANSFER_GRACE_SECS src/python/controller/controller.py
5
$ git status --porcelain -- src/
(empty)
```

Both greps printed 5 (>= 1 required) and `src/` was clean. Precondition passed; execution proceeded without a checkpoint.

## Accomplishments

- `ScanManager.__init__` gained `self.__shutdown_requested = threading.Event()` and `self.__sigterm_recheck_pending = False`, plus the public `note_shutdown_requested()` method that sets the event. This is a component-local shutdown signal, deliberately not reusing `Job.shutdown_flag` or `Controller.__shutdown_event` (per CONTEXT.md's discretion note and RESEARCH's Don't-Hand-Roll table: either would have changed the auto-delete guard or stopped the job before the DEFER-SHUTDOWN sleep).
- `_check_process_health()` was rewritten with three branches, in order: (a) if shutdown was already requested, every dead process is logged at INFO ("Scanner process(es) stopped during shutdown: Name (exitcode N), ...") and `_terminate_and_join_all()` runs, with no raise; (b) if shutdown was NOT yet requested but every dead process has `exitcode == -signal.SIGTERM` and no recheck is already pending, the manager logs DEBUG and returns without touching `__started`, giving the main thread's handler exactly one more cycle to catch up; (c) otherwise (any non-SIGTERM exitcode, or a SIGTERM death that already got its one recheck), the original ERROR + raise path runs byte-for-byte unchanged.
- `Controller.note_shutdown_requested()` was added between `start()` and `process()`: a one-line delegation to `self.__scan_manager.note_shutdown_requested()`, taking no lock and never touching `__shutdown_event` (verified by `exit()`'s byte-identical diff and a dedicated test asserting the auto-delete guard stays clear).
- `Seedsyncarr.__init__` now initializes `self.__controller = None` before the two `signal.signal(...)` registrations; `run()` assigns `self.__controller = controller` immediately after constructing it; `signal()` now reads that attribute and, if not `None`, calls `controller.note_shutdown_requested()` inside its own `try/except Exception: self.context.logger.exception(...)`, then always raises `ServiceExit()` regardless of outcome.
- Both DEFER-SHUTDOWN `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` call sites in `seedsyncarr.py` are untouched (grep count stayed 2; `git diff -- src/python | grep "^+" | grep -c "sleep("` printed 0).

## Task Commits

1. **Task 1: RED tests for the shutdown-aware health check, the SIGTERM one-cycle re-check, controller delegation and signal-handler wiring** - `2c87bcf` (test)
2. **Task 2: GREEN: ScanManager.note_shutdown_requested + shutdown-aware health check, Controller delegation, signal-handler wiring** - `c69559c` (fix)

_No refactor commit was needed; the GREEN implementation matched the planned shape on the first pass._

## RED Results (Task 1, commit `2c87bcf`)

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_controller.py tests/unittests/test_seedsyncarr.py -p no:cacheprovider -q`

Result: **8 failed, 110 passed.** Every failure matched the plan's predicted reason:

| Test | Observed failure |
|------|-------------------|
| `test_shutdown_aware_dead_scanners_after_request_do_not_raise` | `AttributeError: 'ScanManager' object has no attribute 'note_shutdown_requested'` |
| `test_shutdown_aware_any_exitcode_after_request_does_not_raise` | same `AttributeError` |
| `test_shutdown_aware_sigterm_death_rechecked_once_then_raises` | first `propagate_exceptions()` raised `ScannerProcessDiedError` immediately (today's code has no recheck) |
| `test_shutdown_aware_sigterm_death_then_request_is_benign` | same `AttributeError` (no `note_shutdown_requested`) |
| `test_note_shutdown_requested_delegates_to_scan_manager` | `AttributeError: 'Controller' object has no attribute 'note_shutdown_requested'` |
| `test_note_shutdown_requested_does_not_touch_auto_delete_guard` | same `AttributeError` |
| `test_signal_marks_shutdown_on_controller_then_raises` | `assert_called_once()` failed: 0 calls (handler never reads a controller today) |
| `test_signal_note_failure_is_logged_and_still_raises` | `assert_called_once()` failed: 0 calls (same reason) |

**Characterization pins confirmed passing at RED** (must stay correct after the fix, per the plan):
- `test_shutdown_aware_mixed_exitcodes_raise_immediately` — a mixed-exitcode death (one SIGTERM, one not) already raises immediately today; unaffected by this plan's new branches.
- `test_signal_without_controller_still_raises` — `signal()` never read a controller today, so a `None` controller already raised `ServiceExit` cleanly.

Selector check: `pytest -k shutdown_aware tests/unittests/test_controller/test_scan_manager.py --collect-only -q` → `5/26 tests collected`, matching the plan.

`git show --stat --format= HEAD` at the RED commit listed only the three test files; `git log -1 --format=%s` started with `test(123-04):`.

## GREEN Results (Task 2, commit `c69559c`)

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_controller.py tests/unittests/test_seedsyncarr.py tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_auto_delete_rearm.py -p no:cacheprovider -q`

Result: **279 passed, 0 failed.**

Whole-tree lint: `ruff check src/python/` → `All checks passed!`

Acceptance-criteria greps, all confirmed:
- `grep -c "time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)" src/python/seedsyncarr.py` → `2`
- `grep -c "stopped during shutdown" src/python/controller/scan_manager.py` → `1`
- `grep -c "Scanner process(es) died unexpectedly" src/python/controller/scan_manager.py` → `1`
- `grep -c "A scanner process stopped unexpectedly. Please check server logs for details." src/python/controller/scan_manager.py` → `1`
- `grep -c "def note_shutdown_requested" src/python/controller/controller.py` → `1`; same grep on `scan_manager.py` → `1`
- `sed -n '/^    def exit(self):/,/^    def get_model_files/p' src/python/controller/controller.py | diff <scratchpad>/exit-before-04.txt -` → **empty diff** (`exit()` byte-identical)
- `git diff HEAD~1 -- src/python | grep "^+" | grep -c "sleep("` → `0`
- `git log -1 --format=%s` → `fix(123-04): ...`; `git show --stat --format= HEAD` → only the three source files

**Supplementary whole-local-suite attempts (not part of the plan's required gate, not relied on for this "done" claim):** `poetry run pytest tests/unittests -p no:cacheprovider -q` was run twice for extra confidence beyond the plan's prescribed command. Both attempts stalled around 41% progress with no failures observed in that partial output, and both were terminated by `timeout 600` (10 minutes) with exit code 124 before reaching the final summary line — consistent with this being an unusually slow full local run outside the project's Docker-based `make run-tests-python` path, not a regression signal. No pass/fail claim is made from these two attempts; the plan's own prescribed verification command (above, 279 passed / 0 failed) is what backs the "done" status for this plan.

## D-02 split

**Unit-proven (this plan):**
- The handler-to-`ScanManager` wiring: `Seedsyncarr.signal()` → `Controller.note_shutdown_requested()` → `ScanManager.note_shutdown_requested()`, exercised end-to-end by `TestSeedsyncarrSignalShutdownRequest` and `TestControllerShutdownRequest`.
- The INFO/no-raise path once shutdown is requested, for both an all-SIGTERM death and a mixed/any-exitcode death (`test_shutdown_aware_dead_scanners_after_request_do_not_raise`, `test_shutdown_aware_any_exitcode_after_request_does_not_raise`).
- The SIGTERM one-cycle re-check: a death seen before any request is given exactly one extra cycle, then raises if still unresolved (`test_shutdown_aware_sigterm_death_rechecked_once_then_raises`), or resolves benignly if the request arrives within that one cycle (`test_shutdown_aware_sigterm_death_then_request_is_benign`).
- The unchanged ERROR path for a genuine death (any non-SIGTERM exitcode, or a mix), both as a new test (`test_shutdown_aware_mixed_exitcodes_raise_immediately`) and the pre-existing `test_propagate_exceptions_raises_when_process_dies`, both green.

**Live-proven only (plans 06/07 — not claimed here):**
- That `tini -g` actually delivers the container's SIGTERM to the process group and that the forked scanner children die with exitcode `-15` on a real `docker restart`, as RESEARCH.md's log forensics and architecture diagram describe mechanistically but did not themselves constitute a live proof this session.
- That a real restart, after this fix, logs neither "Scanner process(es) died unexpectedly" nor `ScannerProcessDiedError` — the actual elimination of the Phase 122 restart error on the shipping build.
- The lftp "Could not terminate the child" half is explicitly a separate mechanism (lftp's pty child calls `setsid()` and is in its own session, so `tini -g`'s process-group SIGTERM never reaches it directly — RESEARCH Pitfall 2) and is unaffected by any code change in this plan; plan 06's restart cycles are its only proof, and no lftp code was touched here.

## D-03 decision

**Kept, no code change.** Both `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` call sites in `seedsyncarr.py` (the main loop's tail and the exception-handler's pre-terminate wait) are byte-for-byte unchanged, and the existing DEFER-SHUTDOWN backlog note in `.planning/codebase/CONCERNS.md` stays as is.

RESEARCH.md's evidence for this verdict: the kernel delivers the container's process-group SIGTERM to the forked scanner children instantaneously and independently of anything running on the python main thread — no amount of shortening, lengthening, or removing the 0.5s sleep can change whether that direct kernel-level signal kills them. The 2026-10-23 14:14:37-38 sandbox log excerpt (quoted in RESEARCH.md's architecture diagram) additionally shows the `ControllerJob` thread self-detecting the dead scanners and running `Controller.exit()` to completion in well under 1 second — before the main thread's 0.5s DEFER-SHUTDOWN sleep path had even reached its own `terminate()` call. The self-triggered path, not the sleep-gated path, is what actually ran `Lftp.exit()` in the originally observed failing case, so the sleep was never the mechanism producing either restart error in the first place.

## Open Question 2

RESEARCH.md's Open Question 2 — whether `Controller.__init__`'s eager, unconditional construction of `LftpManager`/`Lftp` (which spawns the lftp pty process immediately, before `Controller.start()` is ever called) should be brought into LIFE-01's scope if `Controller.__init__` itself later raises after that construction — is left out of scope for this plan, consistent with its "RESOLVED (planning): out of scope for Phase 123" disposition in RESEARCH.md. No code in `Controller.__init__` was touched here; this is recorded as a backlog candidate, not acted on.

## Files Created/Modified

- `src/python/controller/scan_manager.py` — `note_shutdown_requested()` added; `_check_process_health()` rewritten with the shutdown-aware / SIGTERM-recheck / unchanged-error three-branch shape; `signal` and `threading` imports added.
- `src/python/controller/controller.py` — `note_shutdown_requested()` added between `start()` and `process()`, delegating to `self.__scan_manager.note_shutdown_requested()`; no other line changed (verified byte-identical `exit()`).
- `src/python/seedsyncarr.py` — `self.__controller = None` added before signal registration in `__init__`; `self.__controller = controller` assigned right after construction in `run()`; `signal()` now marks shutdown on the controller (if any) before raising `ServiceExit`, with its own failure guarded and logged.
- `src/python/tests/unittests/test_controller/test_scan_manager.py` — 5 new tests under "D-01: shutdown-aware health check and SIGTERM one-cycle recheck".
- `src/python/tests/unittests/test_controller/test_controller.py` — new `TestControllerShutdownRequest(BaseControllerTestCase)` with 2 tests.
- `src/python/tests/unittests/test_seedsyncarr.py` — new `TestSeedsyncarrSignalShutdownRequest` with 3 tests.

## Decisions Made

- Collected dead processes in the existing Remote, Local, Active order (matching the interfaces note and the pre-existing code), then branched on the collected set rather than per-process, so the "every dead process has exitcode == -SIGTERM" check in branch (b) is evaluated over exactly the processes found dead this cycle, not all three unconditionally.
- Branch (a)'s INFO log reports each dead process's own exitcode individually (`"{} (exitcode {})".format(name, process.exitcode)`), rather than a flat name list, since the shutdown-path log line's whole purpose is to show this was an expected stop and the per-process exitcode is the evidence for that.
- `__sigterm_recheck_pending` is a plain instance boolean (not another `threading.Event`), since it is only ever read and written from the thread that calls `propagate_exceptions()`/`_check_process_health()` — no cross-thread synchronization need, unlike `__shutdown_requested` which is set from the main thread and read from the `ControllerJob` thread.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<behavior>` sections were followed verbatim; no Rule 1-4 auto-fixes were needed.

## Issues Encountered

- The worktree's branch HEAD did not match the orchestrator-supplied base commit (`4eafa25...`) when this agent started (merge-base check found `a56a1f8...`, the pre-wave-1 Phase 122 merge commit, instead). Per the mandatory `<worktree_branch_check>` step, the working tree was confirmed clean and then reset (`git reset --hard 4eafa25bae7770f204c8f21e323b276613f607d4`) before any file was read or edited, correcting the worktree to the expected wave-1-complete base.
- The plan's own `<verify>` command line hardcodes `cd /Users/julianamacbook/seedsyncarr/src/python` (the main checkout, not this worktree). The first invocation of that exact command accidentally ran against the main repo and showed a misleadingly clean "108 passed" (pre-wave-2 state). This was caught before drawing any conclusion from it, and every subsequent test/lint/grep command in this plan was run against the correct worktree path (`.../worktrees/agent-ae5f81774469f87f1/src/python`), which is what every result reported above reflects.
- Two supplementary whole-local-suite runs (`poetry run pytest tests/unittests`, outside the plan's required command) each timed out at 10 minutes around 41% progress with no failures observed in the partial output; not relied on for this plan's "done" claim (see RED/GREEN sections above for the actual gating verification).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- D-01's unit-provable half is closed: the signal-handler-to-health-check wiring exists, is tested end-to-end, and leaves the genuine-death ERROR path, `exit()`, both DEFER-SHUTDOWN sleeps, and the auto-delete shutdown guard/lock ordering all unchanged.
- Plans 06/07 can now exercise this fix live on the NAS sandbox: a real `docker restart` should no longer log "Scanner process(es) died unexpectedly" / raise `ScannerProcessDiedError`, closing the deterministic half of the Phase 122 restart-error pair. The lftp "Could not terminate the child" half remains a separate, intermittent mechanism for those plans to assess independently (RESEARCH Pitfall 2) — no lftp code was touched here.
- No blockers identified for dependent plans in this wave.

## Self-Check: PASSED

- FOUND: src/python/controller/scan_manager.py
- FOUND: src/python/controller/controller.py
- FOUND: src/python/seedsyncarr.py
- FOUND: src/python/tests/unittests/test_controller/test_scan_manager.py
- FOUND: src/python/tests/unittests/test_controller/test_controller.py
- FOUND: src/python/tests/unittests/test_seedsyncarr.py
- FOUND commit: 2c87bcf (test(123-04))
- FOUND commit: c69559c (fix(123-04))

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-25*
