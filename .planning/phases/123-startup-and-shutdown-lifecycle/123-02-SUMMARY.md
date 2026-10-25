---
phase: 123-startup-and-shutdown-lifecycle
plan: 02
subsystem: backend-process-lifecycle
tags: [python, multiprocessing, lifecycle, scan-manager, file-operation-manager]

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes
    provides: PR #134 merged to main (precondition for all Phase 123 code changes)
provides:
  - "ScanManager.start() cleans up already-started scanner processes when a later start() raises, then re-raises the original exception unchanged"
  - "ScanManager._terminate_and_join() isolates each process's terminate()/join() so one raising call never skips the rest"
  - "FileOperationManager.stop() isolates each wrapper's reservation.release() so one raising release never skips the rest or the extract-process stop"
affects: [123-04 (ControllerJob/health-check shutdown-awareness builds on this ScanManager shape)]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Per-component try/except Exception: logger.exception(...) cleanup loop (mirrors Controller.exit()'s existing tuple-of-(name, callable) pattern), applied one level down inside ScanManager and FileOperationManager"]

key-files:
  created: []
  modified:
    - src/python/controller/scan_manager.py
    - src/python/controller/file_operation_manager.py
    - src/python/tests/unittests/test_controller/test_scan_manager.py
    - src/python/tests/unittests/test_controller/test_file_operation_manager.py

key-decisions:
  - "Precondition gate (PR #134 on origin/main) checked live via git fetch + grep before any edit, per the plan's owner rule"
  - "A process whose terminate() raises is deliberately not joined (D-04/discretion: no unbounded join on a process that may still be running)"

patterns-established:
  - "Partial-start cleanup: track a local list of (name, process) tuples that succeeded; on failure, clean up only that subset via the same fault-isolated helper used for full-stop, then bare `raise` to preserve the original exception (D-06)"

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: ~20min
completed: 2026-10-25
---

# Phase 123 Plan 02: ScanManager / FileOperationManager Partial-Start and Cleanup Isolation Summary

**ScanManager.start() now stops already-started scanner processes on a later failure, and both ScanManager and FileOperationManager isolate per-process/per-reservation cleanup so one failing step never skips the rest**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-10-25T17:43:19Z
- **Tasks:** 2 (Task 1 RED, Task 2 GREEN)
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments

- `ScanManager.start()` tracks which of the three scanner processes (active, local, remote) actually started; if the 2nd or 3rd `.start()` raises, only the already-started processes are terminated and joined before the original exception propagates unchanged (LIFE-01). The never-started processes are left untouched, and `__started` stays `False` so a later `stop()` is still a no-op (D-05: no degraded mode).
- A new private helper `ScanManager._terminate_and_join(processes)` fault-isolates each process's `terminate()` and `join()`: one process's `terminate()` or `join()` raising is logged via `logger.exception` and does not skip the others (LIFE-02). A process whose `terminate()` raised is not joined, since it may still be running and `join()` has no bound. `_terminate_and_join_all()` now calls this helper with the same active/local/remote order and keeps its existing debug log lines unchanged.
- `FileOperationManager.stop()`'s reservation-release loop now wraps each wrapper's `reservation.release()` in its own `try/except Exception: self.logger.exception(...)`, so one wrapper's failing release no longer skips releasing the remaining reservations or stopping the extract process (LIFE-02). The sanitized root name is preserved in both the success debug line and the new error line (no new log-injection surface).
- `_check_process_health()`, the `stop()` never-started guard, and the existing start order (active, local, remote) are all unchanged, as the plan requires.

## Task Commits

1. **Task 1: Precondition check, then RED tests for ScanManager partial start and cleanup isolation, and FileOperationManager stop isolation** - `cbf6dcd` (test)
2. **Task 2: GREEN: track started scanner processes, fault-isolate terminate/join and reservation release** - `04eac94` (fix)

_No refactor commit was needed; the GREEN implementation matched the planned shape without further cleanup._

## Precondition Check (Task 1)

Run before any edit, per the plan's owner rule (Phase 122 / PR #134 must be on main before any Phase 123 code):

```
$ git fetch origin
$ git show origin/main:src/python/controller/controller.py | grep -c _POST_TRANSFER_GRACE_SECS
5
$ grep -c _POST_TRANSFER_GRACE_SECS src/python/controller/controller.py
5
$ git status --porcelain -- src/python/controller/scan_manager.py src/python/controller/file_operation_manager.py
(empty)
```

Both greps printed 5 (>= 1) and the porcelain status was empty, so the precondition passed and Task 1 proceeded. (PR #134 merged to main at 2026-10-25T17:36Z, merge commit `d82c4ae`, confirmed present on `origin/main` after the fetch.)

## RED Result (Task 1)

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_file_operation_manager.py -p no:cacheprovider -q`

Result: **6 failed, 43 passed.**

Failed (as specified by the plan), with reasons observed:
- `test_partial_start_third_process_fails_stops_started` — failed because `start()` did not terminate/join the already-started active and local processes.
- `test_partial_start_second_process_fails_stops_started` — same reason, one level earlier.
- `test_partial_start_cleanup_error_does_not_mask_original` — failed because no cleanup ran at all (nothing to mask yet) and `logger.exception` was never called.
- `test_cleanup_isolation_terminate_error_continues` — failed because `manager.stop()` raised (today's `_terminate_and_join_all()` has no per-process isolation).
- `test_cleanup_isolation_join_error_continues` — failed for the same reason, on the join phase.
- `test_stop_cleanup_isolation_release_error_continues` — failed because `manager.stop()` raised on the first wrapper's `reservation.release()`, never reaching the second wrapper's release or the extract-process stop.

Passed as the plan's characterization test: `test_partial_start_first_process_fails_touches_nothing` passed unmodified (today's code already does nothing when the very first process's `start()` raises, since nothing had started yet).

Selector counts confirmed via `--collect-only`:
- `-k partial_start` → 4/49 tests collected (matches plan)
- `-k cleanup_isolation` → 3/49 tests collected (matches plan)

## GREEN Result (Task 2)

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_file_operation_manager.py -p no:cacheprovider -q`

Result: **49 passed, 0 failed.**

Whole-tree ruff: `ruff check src/python/` → `All checks passed!`

Acceptance-criteria greps:
```
$ grep -c "after a failed scanner start" src/python/controller/scan_manager.py
1
$ grep -c "Error releasing root reservation for" src/python/controller/file_operation_manager.py
1
$ grep -c "Scanner process(es) died unexpectedly" src/python/controller/scan_manager.py
1
$ git diff HEAD~1 -- src/python/controller | grep "^+" | grep -c "sleep("
0
```
All match the plan's expected values; the health-check error message is untouched and no new sleep was introduced.

## Files Created/Modified

- `src/python/controller/scan_manager.py` — `start()` now tracks started processes and cleans up the already-started subset on a later failure; new `_terminate_and_join()` helper fault-isolates terminate/join; `_terminate_and_join_all()` now delegates to it.
- `src/python/controller/file_operation_manager.py` — `stop()`'s reservation-release loop now fault-isolates each wrapper's `release()` call.
- `src/python/tests/unittests/test_controller/test_scan_manager.py` — 6 new tests covering partial-start cleanup and per-process cleanup isolation.
- `src/python/tests/unittests/test_controller/test_file_operation_manager.py` — 1 new test covering per-wrapper reservation-release isolation on `stop()`.

## Decisions Made

- Precondition gate verified live (git fetch + grep + porcelain status) exactly as the plan specifies, rather than assumed from context, since the orchestrator's objective explicitly called out that PR #134 should now be merged.
- Followed the plan's exact fix shape (tuple-of-`(name, callable)` try/except loop mirroring `Controller.exit()`) with no new class, registry, or lifecycle abstraction, per CONTEXT.md's discretion note.
- A process whose `terminate()` raises is deliberately excluded from the join phase (documented in a comment in `_terminate_and_join`), matching the plan's explicit instruction to avoid an unbounded `join()` on a process that may still be running.

## Deviations from Plan

None - plan executed exactly as written. No Rule 1/2/3/4 auto-fixes were needed; the RED tests failed for exactly the reasons the plan predicted, and the GREEN implementation matched the plan's prescribed shape on the first pass.

## Issues Encountered

- The worktree's branch HEAD was at the PR #134 merge commit directly (not based on `ad1543d`, the phase-123 branch tip recorded in STATE.md) when this agent started. Per the mandatory `<worktree_branch_check>` step, the worktree was reset (`git reset --hard ad1543de711273725ca83093fce5a12f3fd8e975`) before any file was read or edited. `origin/main` already contained the PR #134 merge after `git fetch origin`, so the Task 1 precondition passed as expected without further action.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LIFE-01 and LIFE-02 are now closed at the `ScanManager`/`FileOperationManager` level, one tier below `Controller.exit()`'s already-correct per-component loop.
- Plan 123-04 (per RESEARCH.md's Open Question 1 / shutdown-aware health check) can build directly on this `ScanManager` shape without further changes here; `_check_process_health()` was deliberately left untouched.
- No blockers for subsequent Phase 123 plans in this wave.

## Self-Check: PASSED

- FOUND: .planning/phases/123-startup-and-shutdown-lifecycle/123-02-SUMMARY.md
- FOUND: src/python/controller/scan_manager.py
- FOUND: src/python/controller/file_operation_manager.py
- FOUND: cbf6dcd (test commit)
- FOUND: 04eac94 (fix commit)
- FOUND: 9dc261c (docs/summary commit)

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-25*
