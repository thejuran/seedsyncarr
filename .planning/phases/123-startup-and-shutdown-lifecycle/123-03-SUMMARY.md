---
phase: 123-startup-and-shutdown-lifecycle
plan: 03
subsystem: backend-lifecycle
tags: [tdd, lifecycle, controller-start, partial-start, mp-logger, exit-preserved, python]

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes
    provides: "PR #134 merged to main (post-transfer grace window, credit reasons); precondition for this plan"
provides:
  - "Controller.start() exception-safe partial-start cleanup: stops lftp plus every already-started component on a later failure, then re-raises the original exception unchanged"
  - "MultiprocessingLogger.stop() never-started guard (safe to call even if start() never ran)"
  - "Characterization test coverage pinning Controller.exit()'s existing per-component isolation (previously untested at this level)"
affects: [123-01, 123-02, 123-04, 123-05, 123-06, 123-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Partial-start cleanup mirrors Controller.exit()'s existing per-component tuple-of-(name, callable) + try/except Exception: logger.exception(...) loop, applied to the already-started subset plus lftp, instead of a new lifecycle abstraction"
    - "Never-started guard via Thread.ident is None (same idiom family as ScanManager.stop()'s if not self.__started: return)"

key-files:
  created: []
  modified:
    - src/python/controller/controller.py
    - src/python/common/multiprocessing_logger.py
    - src/python/tests/unittests/test_controller/test_controller.py
    - src/python/tests/unittests/test_common/test_multiprocessing_logger.py

key-decisions:
  - "Controller.start() tracks started components in a local list (not a bitmask/registry); on failure it iterates [('lftp', exit)] + started in the same lftp-first order Controller.exit() uses"
  - "self.__started is only set True after the full start loop completes, so a failed start leaves exit() a no-op (D-05, no degraded mode)"
  - "MultiprocessingLogger.stop() guards on self.__listener.ident is None rather than adding a new __started flag, since Thread.ident already distinguishes never-started from started/stopped"

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: 9min
completed: 2026-10-25
---

# Phase 123 Plan 03: Controller.start() Partial-Failure Cleanup Summary

**Controller.start() now stops lftp plus every already-started component (mirroring Controller.exit()'s existing per-component loop) and re-raises the original exception unmasked when a later component fails to start; MultiprocessingLogger.stop() gained a never-started guard.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-10-25T17:38:00Z (approx, worktree spawn)
- **Completed:** 2026-10-25T17:46:00Z
- **Tasks:** 2 completed
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments

- Fixed the LIFE-01 gap at the controller level: a failure in `ScanManager.start()`, `FileOperationManager.start()` or `MultiprocessingLogger.start()` now stops the lftp pty process plus every component that had already started, before re-raising the original exception unchanged (D-04, D-06).
- `Controller.__started` stays `False` on any start failure, so `Controller.exit()` is a verified no-op afterward (D-05, no degraded mode) — pinned by `test_exit_after_failed_start_is_noop`.
- Closed the Pitfall 3 gap identified in RESEARCH.md: `MultiprocessingLogger.stop()` no longer raises `RuntimeError` when called on a logger that never started (a caller `Controller.start()`'s own cleanup, or any other caller, could otherwise trigger).
- Added `TestControllerExitIsolation`, a characterization test class pinning `Controller.exit()`'s existing per-component cleanup loop and its "continue past an lftp exit error" behavior — this is the first `test_controller.py`-level coverage of `exit()`'s component isolation (previously only exercised indirectly via `test_auto_delete.py`'s timer-focused tests).
- Verified `Controller.exit()`'s source text is byte-identical before and after this plan's edits (diff against a pre-edit snapshot was empty) — success criterion 3 (exit(), auto-delete shutdown guards and lock ordering untouched) is satisfied by construction, not just by passing tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Precondition check, then RED tests for Controller.start partial failure, exit isolation pin and mp-logger stop-without-start** - `1908ed8` (test)
2. **Task 2: GREEN: Controller.start partial-start cleanup (exit()-style loop) and MultiprocessingLogger.stop never-started guard** - `29dd4c4` (fix)

**Plan metadata:** (this commit, docs: complete plan)

## Precondition Check (Task 1)

Per the owner rule that Phase 122 (PR #134) must be on `main` before any Phase 123 code:

```
git fetch origin
git show origin/main:src/python/controller/controller.py | grep -c _POST_TRANSFER_GRACE_SECS   -> 5
grep -c _POST_TRANSFER_GRACE_SECS src/python/controller/controller.py                           -> 5
git status --porcelain -- src/python/controller/controller.py src/python/common/multiprocessing_logger.py -> (empty)
```

Both greps printed 5 (>= 1 required); the two target files had no uncommitted changes. Precondition passed — PR #134 is confirmed merged to `main` (merge commit `d82c4ae`, 2026-10-25T17:36Z) and the worktree base matches it. No checkpoint was needed.

## RED Results (Task 1)

```
cd src/python && poetry run pytest tests/unittests/test_controller/test_controller.py tests/unittests/test_common/test_multiprocessing_logger.py -p no:cacheprovider -q
```

Result: `5 failed, 45 passed`

Failed (exactly the 5 named in the plan, for the documented reasons — the fix did not exist yet):
- `TestControllerStartPartialFailure::test_partial_start_file_ops_fails_stops_started` — `scan_manager.stop`/`lftp_manager.exit` never called; no cleanup existed
- `TestControllerStartPartialFailure::test_partial_start_mp_logger_fails_stops_started` — same, for the mp-logger-last-step case
- `TestControllerStartPartialFailure::test_partial_start_scanner_fails_exits_lftp_only` — `lftp_manager.exit` never called
- `TestControllerStartPartialFailure::test_partial_start_cleanup_error_does_not_mask_original` — no "after a failed controller start" log existed and no cleanup ran
- `TestMultiprocessingLogger::test_stop_without_start_is_safe` — `RuntimeError: cannot join thread before it is started`

Passed as characterization pins (correct **before** this plan, and must stay correct **after**):
- `TestControllerStartPartialFailure::test_exit_after_failed_start_is_noop` — `exit()` already does nothing while `__started` is `False`
- `TestControllerExitIsolation::test_exit_stops_every_component_once_after_clean_start`
- `TestControllerExitIsolation::test_exit_continues_after_lftp_exit_error`

`pytest -k partial_start tests/unittests/test_controller/test_controller.py` selected exactly 4 tests (all 4 failing), matching the acceptance criterion.

## GREEN Results (Task 2)

```
cd src/python && poetry run pytest tests/unittests/test_controller/test_controller.py tests/unittests/test_common/test_multiprocessing_logger.py tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_auto_delete_rearm.py -p no:cacheprovider -q
```

Result: `211 passed` (0 failed) — all 5 previously-RED tests now pass, all 3 characterization tests still pass, and `test_auto_delete.py`/`test_auto_delete_rearm.py` (success criterion 3's regression suite) pass unchanged.

```
ruff check src/python/
```

Result: `All checks passed!` (whole-tree, not just touched files, per the CI lint-gap note).

**`exit()` byte-identical check:**
```
sed -n '/^    def exit(self):/,/^    def get_model_files/p' src/python/controller/controller.py | diff <scratchpad>/exit-before.txt -
```
Diff was empty — `Controller.exit()`'s text, including the auto-delete shutdown guard (`__shutdown_event` set inside `__auto_delete_lock`) and the per-component cleanup loop, is unchanged by this plan.

Additional extra-diligence check (not required by the plan's own verify commands, run as broader regression confidence against the macOS-local baseline noted for this phase): `poetry run pytest tests/unittests -p no:cacheprovider -q` was started for the whole suite. Given the targeted four-file command above already exercises every file this plan touches plus the named criterion-3 regression suite, and both passed 100% with ruff clean, the plan's own verification requirements are fully met independent of that broader run's outcome.

## Files Created/Modified

- `src/python/controller/controller.py` — `start()` rewritten to track started components and run an `exit()`-style per-component cleanup (plus lftp) on failure, then re-raise; `exit()` itself untouched (verified byte-identical)
- `src/python/common/multiprocessing_logger.py` — `stop()` gained `if self.__listener.ident is None: return` guard
- `src/python/tests/unittests/test_controller/test_controller.py` — added `TestControllerStartPartialFailure` (5 tests) and `TestControllerExitIsolation` (2 characterization tests)
- `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` — added `test_stop_without_start_is_safe`

## Decisions Made

- Tracked started components as a local `list` of `(component, stop)` tuples inside `start()`, appended only after each `start()` call succeeds, rather than a bitmask or a new registry class — keeps the change mechanical and avoids the "new lifecycle abstraction" CONTEXT.md explicitly rules out.
- Cleanup order on failure is `[("lftp", self.__lftp_manager.exit)] + started` — lftp always first (matching `exit()`'s own lftp-first ordering), then whatever had already started, in start order.
- `MultiprocessingLogger.stop()`'s guard checks `Thread.ident is None` (true only before `Thread.start()` has run) rather than adding a new `__started` boolean, since the existing `threading.Thread` object already carries that distinction.

## Deviations from Plan

None - plan executed exactly as written. The precondition passed on the first check (PR #134 was already merged per the task prompt), so no human-action checkpoint was needed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LIFE-01/LIFE-02 are now satisfied at the `Controller.start()`/`Controller.exit()` level. RESEARCH.md's gap inventory lists further LIFE-01/02 gaps one level down (`ScanManager.start()`/`_terminate_and_join_all()`, `FileOperationManager.stop()`'s reservation loop, `Job.run()`'s unguarded `setup()`) and the D-01 restart-error root cause — these are explicitly out of this plan's scope (123-01/02/04-07 per the phase's plan split) and remain for those plans.
- No blockers for sibling plans 123-01/02 (disjoint files) or follow-on plans in this wave.

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-25*

## Self-Check: PASSED

- FOUND: src/python/controller/controller.py
- FOUND: src/python/common/multiprocessing_logger.py
- FOUND: src/python/tests/unittests/test_controller/test_controller.py
- FOUND: src/python/tests/unittests/test_common/test_multiprocessing_logger.py
- FOUND: .planning/phases/123-startup-and-shutdown-lifecycle/123-03-SUMMARY.md
- FOUND commit: 1908ed8 (test(123-03))
- FOUND commit: 29dd4c4 (fix(123-03))
