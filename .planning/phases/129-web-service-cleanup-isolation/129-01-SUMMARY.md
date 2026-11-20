---
phase: 129-web-service-cleanup-isolation
plan: 01
subsystem: web
tags: [shutdown, cleanup, threading, tdd]
requires: []
provides:
  - "WebAppJob.cleanup() with three isolated steps, applicability guards and a bounded join"
  - "WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS = 5.0"
  - "daemon web-server thread"
affects:
  - "129-02 (MyWSGIRefServer.stop made immediate; extends the constant's comment with the whole web-cleanup budget)"
tech-stack:
  added: []
  patterns:
    - "per-step try/except + logger.exception (Controller.exit style)"
    - "class-level timeout constant patchable by tests (ScanManager style)"
key-files:
  created: []
  modified:
    - src/python/web/web_app_job.py
    - src/python/tests/unittests/test_web/test_web_app_job.py
decisions:
  - "The thread join runs even when server.stop() failed (D-06): the timeout makes the wait safe"
  - "is_alive() guards the join, so an unstarted or finished thread is skipped silently (D-03)"
metrics:
  duration: "~2 min wall clock (measured 83 s between start and end timestamps)"
  completed: 2026-11-20
  tasks: 2
  files: 2
---

# Phase 129 Plan 01: Isolated, Bounded WebAppJob Cleanup Summary

`WebAppJob.cleanup()` now runs app stop, server stop and a 5-second bounded thread join as three independent try/except steps that log each failure and never raise, and the web-server thread is a daemon.

## RED (commit 982e4518)

Added 12 tests to `TestWebAppJobCleanup` (13 total with the extended `test_cleanup_without_setup_does_not_raise`), four pinned message literals, and behaviour-modelled thread liveness (no `is_alive.side_effect` lists, no name-mangled attribute access).

Failing run on the pre-change code: `11 failed, 2 passed`.

| Test | Failure reason on pre-change code |
|------|-----------------------------------|
| test_app_stop_failure_still_stops_server_and_joins | `RuntimeError: app stop failed` escaped `cleanup()` |
| test_server_stop_failure_still_joins_thread | `RuntimeError: server stop failed` escaped `cleanup()` |
| test_join_failure_is_logged_and_cleanup_returns | `RuntimeError: join failed` escaped `cleanup()` |
| test_all_steps_fail_all_attempted_and_logged | `RuntimeError: app stop failed` escaped `cleanup()` |
| test_clean_shutdown_joins_with_timeout_and_logs_nothing | `AttributeError: type object 'WebAppJob' has no attribute '_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS'` |
| test_stuck_thread_logs_warning_and_returns | `AttributeError` for `_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS` |
| test_stuck_real_thread_returns_within_bound | `AttributeError: <class 'web.web_app_job.WebAppJob'> does not have the attribute '_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS'` (patch.object) |
| test_join_timeout_constant_below_docker_grace | `AttributeError` for `_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS` |
| test_server_thread_created_as_daemon | `AssertionError: None is not True` (no `daemon` kwarg) |
| test_thread_not_started_skips_join | `AssertionError: Expected 'join' to not have been called. Called 1 times. Calls: [call()].` |
| test_thread_already_finished_skips_join | `AssertionError: Expected 'join' to not have been called. Called 1 times. Calls: [call()].` |

Lock tests green before the change: `test_cleanup_without_setup_does_not_raise`, `test_server_not_created_skips_server_and_join`.

Verbatim app.stop failure (fail-before evidence for REL-07), from `pytest -k app_stop_failure` run alone:

```
E               RuntimeError: app stop failed
1 failed, 12 deselected, 3 warnings in 0.12s
```

The plan's `red()` verify helper passed for all four selectors (each run alone: expected text present, `1 failed`, no import or collection error), and the lock selector reported `2 passed, 11 deselected`. Whole-tree `ruff check src/python/`: `All checks passed!`.

## GREEN (commit 84c450f9)

In `src/python/web/web_app_job.py`, `WebAppJob` only:
- Added `_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS = 5.0` with a comment stating it limits this one wait and must stay below Docker's 10 s grace (no claim about the final state save, no whole-cleanup budget yet).
- `setup()`: `daemon=True` on the existing `Thread(...)` call.
- `cleanup()`: three blocks; app stop always attempted; server stop only if the server exists; join only if the thread exists and `is_alive()`, with `join(timeout=...)` and a WARNING `Web server did not stop within 5.0 seconds; continuing shutdown` if still alive. Each block logs its fixed message via `logger.exception`.

Observed results:
- `pytest tests/unittests/test_web/test_web_app_job.py`: `13 passed`
- `pytest tests/unittests/test_web`: `485 passed, 54 subtests passed`
- `ruff check src/python/`: `All checks passed!`
- Acceptance greps: constant 1, daemon=True 1, logger.exception 3, bounded join 1, `.join()` 0, logger.warning 1; test file has 0 `_WebAppJob__` and 0 `is_alive.side_effect = [`.
- `git diff HEAD~1 HEAD --stat` over tests, seedsyncarr.py, common, web_app.py: empty.

## REFACTOR

None needed.

## Commits

- 982e4518 test(129-01): add failing tests for web service cleanup isolation
- 84c450f9 feat(129-01): isolate web service cleanup steps and bound the server thread join

## Notes for the owner

- Until plan 129-02 lands, stopping the app in the brief moment before the web server has finished starting is logged as an error instead of being skipped quietly. Plan 129-02 closes that, and both plans ship in the same pull request.
- After this plan the wait for the web server is limited to 5 seconds, but the step just before it (telling the web server to stop) can still take about half a second for each browser request that is stuck. Plan 129-02 makes that step immediate, so the 5-second limit on the web server's share of shutdown is only complete once both plans are in. This is a limit on the web server's share of shutdown, not a guarantee that the final state save finishes inside Docker's 10 seconds.

## Deviations from Plan

None - plan executed exactly as written.

Process note: the worktree started at 74b7a6e4 rather than the expected base dc0aa172, so it was reset to dc0aa172 per the branch check before any work. REQUIREMENTS.md was not updated here: WEB-02's full bound depends on plan 129-02, so marking requirements is left to the orchestrator after the wave.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/python/web/web_app_job.py, src/python/tests/unittests/test_web/test_web_app_job.py
- FOUND commits: 982e4518, 84c450f9
