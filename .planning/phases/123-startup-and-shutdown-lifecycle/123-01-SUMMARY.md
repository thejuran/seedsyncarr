---
phase: 123-startup-and-shutdown-lifecycle
plan: 01
subsystem: backend-lifecycle
tags: [python, threading, job-thread, controller, exception-propagation, tdd]

# Dependency graph
requires: []
provides:
  - "Job.run() wraps setup() the same way execute() is wrapped: a setup() failure sets exc_info, sets shutdown_flag, and still runs cleanup() exactly once"
  - "Job.run()'s cleanup() call is itself guarded: a cleanup failure is logged and only populates exc_info when no earlier setup/execute failure already claimed it (D-06)"
  - "ControllerJob.setup() re-raises AppError unchanged but wraps any other exception in ControllerError chained from the original, routing non-AppError startup failures into the existing RECOV-01 except-AppError path (D-04, D-05)"
  - "WebAppJob.cleanup() is safe to call after a setup() that raised before assigning the server/server thread"
affects: ["123-02", "123-03", "123-04"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "setup()/cleanup() exception wrapping in Job.run() mirrors the pre-existing execute() except-block shape (capture exc_info, logger.exception, set shutdown_flag)"
    - "Non-AppError startup failures wrapped in a domain-specific AppError subclass chained via `raise ... from exc`, keeping the original exception as __cause__ for server-log-only detail while the UI sees a fixed generic message"

key-files:
  created:
    - src/python/tests/unittests/test_web/test_web_app_job.py
  modified:
    - src/python/common/job.py
    - src/python/controller/controller_job.py
    - src/python/web/web_app_job.py
    - src/python/tests/unittests/test_common/test_job.py
    - src/python/tests/unittests/test_controller/test_controller_job.py

key-decisions:
  - "cleanup() exceptions never overwrite an existing exc_info (D-06): the guard is `if self.exc_info is None: self.exc_info = sys.exc_info()`, applied only in the cleanup except-block"
  - "ControllerJob.setup() distinguishes AppError (re-raised unchanged) from everything else (wrapped in ControllerError with a fixed message, original as __cause__) so RECOV-01's existing `except AppError` main-loop path handles both without further changes"

patterns-established:
  - "Job subclasses relying on setup()-assigned state (e.g. WebAppJob's server/server thread) must None-guard cleanup() now that cleanup() runs even when setup() raised partway through"

requirements-completed: [LIFE-01]

# Metrics
duration: ~15min
completed: 2026-10-25
---

# Phase 123 Plan 01: Job Setup-Failure Surfacing Summary

**`Job.run()` now wraps `setup()` the same way it already wrapped `execute()`, so a `ControllerJob.setup()` failure (a `Controller.start()` exception) runs cleanup exactly once and surfaces through `propagate_exception()` into the existing RECOV-01 bounded auto-restart instead of killing the thread silently.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-10-25 (session start, after base reset to `ad1543d`)
- **Completed:** 2026-10-25T17:50:02Z
- **Tasks:** 2 (RED test commit, GREEN fix commit)
- **Files modified:** 6 (3 test files touched/created in Task 1, 3 source files in Task 2)

## Precondition Check (Task 1)

Per the plan's owner rule (Phase 122 / PR #134 must be on `main` before any Phase 123 code):

```
$ git fetch origin
$ git show origin/main:src/python/controller/controller.py | grep -c _POST_TRANSFER_GRACE_SECS
5
$ grep -c _POST_TRANSFER_GRACE_SECS src/python/controller/controller.py
5
$ git status --porcelain -- src/
(empty)
```

Both greps printed 5 (≥1) and `src/` was clean — the precondition passed, confirming HEAD was cut from a `main` that already contains Phase 122 (PR #134, merged as `d82c4ae`). Execution proceeded without a checkpoint.

## Accomplishments

- `Job.run()`'s `setup()` call is now wrapped in `try/except Exception`, mirroring the existing `execute()` except-block: `exc_info` is captured, `logger.exception("Caught exception in setup for ...")` is logged, and `shutdown_flag` is set — so the existing `while not shutdown_flag.is_set()` loop is skipped and the existing single `cleanup()` call site is reached exactly once either way.
- `Job.run()`'s `cleanup()` call is now also guarded: a cleanup exception is logged (`"Caught exception in cleanup for ..."`), and only populates `exc_info` when it is still `None` — an earlier setup/execute failure is never masked (D-06), while a cleanup failure on an otherwise-clean run now surfaces instead of dying silently inside the thread.
- `ControllerJob.setup()` re-raises an `AppError` from `Controller.start()` unchanged, but wraps any other exception in `ControllerError("Controller failed to start. Please check server logs for details.") from exc` — the original is `__cause__`, logged in full (with traceback) by `Job.run()`'s setup except-block, while the web UI only ever sees the fixed generic message (`server.error_msg`).
- `WebAppJob.cleanup()` now None-guards `self.__server.stop()` and `self.__server_thread.join()`, since `cleanup()` is reachable after a `setup()` that raised before those were assigned (a previously-latent gap now exercised by the shared `Job.run()` fix).

## Task Commits

1. **Task 1: Precondition check, then RED tests for setup-failure surfacing, D-06 cleanup guard, ControllerJob routing, WebAppJob cleanup** - `647eef0` (test)
2. **Task 2: GREEN: wrap setup() and guard cleanup() in Job.run, route ControllerJob startup failures to AppError, None-guard WebAppJob.cleanup** - `277257f` (fix)

_No plan-metadata commit yet — STATE.md/ROADMAP.md are owned by the orchestrator per this run's instructions; this plan's own metadata commit (SUMMARY.md) follows this report._

## Files Created/Modified

- `src/python/common/job.py` - `Job.run()` wraps `setup()` and `cleanup()` in `try/except Exception`, each mirroring the existing `execute()` except-block shape; `setup()`'s abstract docstring updated to document the new contract
- `src/python/controller/controller_job.py` - `setup()` catches `Controller.start()` failures, re-raising `AppError` unchanged and wrapping anything else in `ControllerError(...) from exc`
- `src/python/web/web_app_job.py` - `cleanup()` None-guards `self.__server`/`self.__server_thread` before calling `.stop()`/`.join()`
- `src/python/tests/unittests/test_common/test_job.py` - `DummyCleanupError`, `DummySetupFailingJob`, `DummySetupAndCleanupFailingJob`, `DummyCleanupFailingJob`, `DummyCleanJob`; 6 new `TestJob` methods
- `src/python/tests/unittests/test_controller/test_controller_job.py` - 3 new `TestControllerJob` methods (AppError passthrough, non-AppError wrapping, real-thread setup-failure-to-cleanup-to-propagate path)
- `src/python/tests/unittests/test_web/test_web_app_job.py` (new) - `TestWebAppJobCleanup.test_cleanup_without_setup_does_not_raise`

## RED Results (Task 1, commit `647eef0`)

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_common/test_job.py tests/unittests/test_controller/test_controller_job.py tests/unittests/test_web/test_web_app_job.py -p no:cacheprovider -q`

Result: **8 failed, 9 passed.** Every failure matched the plan's documented reason, none were ImportError/fixture errors:

| Test | Observed failure |
|------|-------------------|
| `test_setup_exception_propagates` | `AssertionError: DummyError not raised` (propagate raised nothing) |
| `test_cleanup_executes_on_setup_error` | `AssertionError: False is not true` (`cleanup_run` stayed `False`) |
| `test_setup_error_sets_shutdown_flag` | `AssertionError: False is not true` |
| `test_setup_error_not_masked_by_cleanup_error` | `AssertionError: DummyError not raised` |
| `test_cleanup_error_surfaces_on_clean_run` | `AssertionError: DummyCleanupError not raised` |
| `test_setup_non_apperror_wrapped_in_controller_error` | `OSError: fork failed` raised directly (ControllerError expected) |
| `test_setup_failure_thread_runs_cleanup_and_surfaces` | `AssertionError: Expected 'exit' to have been called once. Called 0 times.` |
| `test_cleanup_without_setup_does_not_raise` | `AttributeError: 'NoneType' object has no attribute 'stop'` |

Passed (as expected): `test_clean_run_has_no_exception`, `test_setup_apperror_propagates_unchanged`, and all 7 pre-existing tests across the three files.

## GREEN Results (Task 2, commit `277257f`)

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_common/test_job.py tests/unittests/test_controller/test_controller_job.py tests/unittests/test_web/test_web_app_job.py -p no:cacheprovider -q`

Result: **17 passed, 0 failed.**

Whole-tree lint: `ruff check src/python/` → `All checks passed!`

Acceptance-criteria greps, all confirmed:
- `grep -c "Caught exception in setup for" src/python/common/job.py` → `1`
- `grep -c "Caught exception in cleanup for" src/python/common/job.py` → `1`
- `grep -c "self.cleanup()" src/python/common/job.py` → `1` (single cleanup call site)
- `grep -c "Controller failed to start. Please check server logs for details." src/python/controller/controller_job.py` → `1`
- `grep -c "from exc" src/python/controller/controller_job.py` → `1`
- `grep -c "is not None" src/python/web/web_app_job.py` → `2`
- `git diff HEAD~1 -- src/python/common/job.py | grep "^[-+]" | grep -c "sleep"` → `0` (no new sleep)
- `git log -1 --format=%s` → `fix(123-01): ...`; `git show --stat --format= HEAD` → only the three source files

Broader regression check (beyond the plan's required command, run as extra confidence): the full quick-run command from RESEARCH.md (`test_job.py`, `test_scan_manager.py`, `test_controller.py`, `test_controller_job.py`, `test_file_operation_manager.py`, `test_auto_delete.py`, and `test_web/`) — **578 passed, 0 failed.** A whole-tree run (`tests/unittests`) was also attempted for extra confidence beyond the plan's prescribed gate; it was interrupted partway (46% complete, 0 failures observed up to that point) to avoid resource contention with a concurrently-running sibling worktree agent executing the same suite, and is not relied on for any pass/fail claim in this summary — the plan's prescribed gates (targeted 3-file command + whole-tree ruff) are what back the "done" claim above.

## Decisions Made

- The cleanup-exception guard in `Job.run()` uses `if self.exc_info is None: self.exc_info = sys.exc_info()` rather than always overwriting — this is the literal D-06 requirement (never mask an earlier setup/execute failure) applied at the one new risk point the plan's fix introduces.
- `ControllerJob.setup()`'s `except AppError: raise` comes before the catch-all `except Exception as exc:` so `AppError` instances (including its own subclasses like `ControllerError` itself, were one ever raised by `Controller.start()`) pass through unchanged, matching D-04/D-05 exactly as specified.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<behavior>` sections were followed verbatim; no Rule 1-4 auto-fixes were needed beyond what the plan already specified.

## Issues Encountered

None blocking. One self-inflicted minor cleanup: while drafting `test_job.py`'s `test_clean_run_has_no_exception`, an initial draft left a stray unused `DummyCleanupFailingJob.__new__(...)` line and an inline nested test class; this was caught and fixed before running any test (moved `DummyCleanJob` to module level alongside the other Dummy* fixtures, matching the file's existing style) — not a deviation from the plan, just an in-progress authoring correction.

## Behaviour notes

A `WebAppJob.setup()` failure now also surfaces through `propagate_exception()` (previously the web thread died silently, since `Job.run()` never reached `cleanup()` after an uncaught `setup()` exception). This is practically unreachable today (RESEARCH.md Assumption A3 — no currently-reachable statement in `MyWSGIRefServer.__init__`/`Thread.__init__` realistically raises before `self.__server`/`self.__server_thread` are assigned), and when it does happen it now uses the exact same main-loop path a `WebAppJob.execute()` failure already takes (both are plain `Exception`, not `AppError`, so both would currently escape `propagate_exception()`'s caller to the outer `except Exception` in `seedsyncarr.py`'s `main()` — this plan did not change that routing for `WebAppJob`, only made its `setup()` failures reach `propagate_exception()` at all, consistent with `execute()`'s pre-existing behavior).

## Known Stubs

None.

## Threat Flags

None — all new/changed surface (exception wrapping in `Job.run()`, `ControllerJob.setup()`, `WebAppJob.cleanup()`) is covered by this plan's own `<threat_model>` (T-123-01..04), already addressed by the implementation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LIFE-01's "the failure still surfaces" half is closed for the `Job`/`ControllerJob` layer: a `Controller.start()` failure now cleans up (`Controller.exit()` called once) and surfaces through `propagate_exception()` into the existing RECOV-01 bounded auto-restart.
- Plans 02/03 (per this plan's `<objective>`) can now rely on `ControllerJob.setup()` failures being visible to the main loop when they add partial-start cleanup inside `Controller`/`ScanManager` — without this plan's fix, no such cleanup would ever have been followed by a visible failure (RESEARCH Pitfall 1).
- No blockers identified for dependent plans in this wave.

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-25*
