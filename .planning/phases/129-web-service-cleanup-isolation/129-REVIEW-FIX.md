---
phase: 129-web-service-cleanup-isolation
fixed_at: 2026-11-20T04:26:00Z
review_path: .planning/phases/129-web-service-cleanup-isolation/129-REVIEW.md
iteration: 2
fix_scope: WR-01, IN-01 (iteration 1); IN-02, IN-03, IN-04 (iteration 2)
findings_in_scope: 5
fixed: 5
skipped: 0
rejected: 0
status: all_fixed
---

# Phase 129: Code Review Fix Report

**Fixed at:** 2026-11-20T04:20:00Z (iteration 1), 2026-11-20T04:26:00Z (iteration 2)
**Source review:** .planning/phases/129-web-service-cleanup-isolation/129-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 5 (WR-01 and IN-01 in iteration 1; IN-02, IN-03 and IN-04 in iteration 2, as directed by the orchestrator)
- Fixed: 5
- Skipped: 0
- Rejected: 0

Set-aside items (owner rulings, no code change):
- **SA-01** (paste force-kills and replaces hung workers on the orphaned server thread): accepted as is by the owner on 2026-11-20.
- **SA-02** (port-bind failure at startup leaves the job running without a web UI): deferred to the backlog by the owner on 2026-11-20.

## Fixed Issues

### WR-01: stop() can race paste's serve loop and kill the server thread with an uncaught ValueError

**Files modified:** `src/python/web/web_app_job.py`, `src/python/tests/unittests/test_web/test_web_app_job.py`
**Commit:** 6db9a12b
**Status:** fixed: requires human verification (logic change in error handling)
**Applied fix:** `MyWSGIRefServer.run()` wraps `server.serve_forever()` in `try/except (OSError, ValueError)`. When the error happens after a stop was requested, `run()` logs at debug level and returns normally. Otherwise it re-raises. The check reads the adapter's own `__stop_requested` flag under the existing lock, not paste's `server.running`. `stop()` sets that flag before it clears `running` and closes the socket, so the flag is the authoritative signal and mocks can't fake it.

Tests were written first and confirmed failing before the fix:
- `test_socket_error_after_stop_ends_run_cleanly`: covers both ValueError and OSError. The fake `serve_forever` calls `srv.stop()` and then raises, and `run()` must return cleanly. This failed before the fix.
- `test_socket_error_without_stop_propagates`: covers both ValueError and OSError. With no stop requested, the error must propagate. This already passed before the fix and guards against over-swallowing.
- `test_real_server_stop_racing_serve_loop_exits_cleanly`: uses a real paste server whose `handle_request` is wrapped so that its first call runs `srv.stop()` before delegating. This reproduces the race deterministically. Before the fix the server thread died with `ValueError('Invalid file descriptor: -1')`, the reviewer's exact error. After the fix the thread exits with no exception.

### IN-01: Duplicated rationale comment on the join-timeout constant

**Files modified:** `src/python/web/web_app_job.py`
**Commit:** 238c9382
**Applied fix:** Merged the two comment paragraphs into one. It covers the budget breakdown (app flag, socket close, bounded join), why the bound stays under docker's 10 s grace, and why the value is a class attribute (so tests can patch it).

### IN-02: Stop-before-start still binds the port and builds a full thread pool

**Files modified:** `src/python/web/web_app_job.py`, `src/python/tests/unittests/test_web/test_web_app_job.py`
**Commit:** 83171bd5
**Status:** fixed: requires human verification (startup/stop ordering change)
**Applied fix:** `run()` now checks `__stop_requested` under the existing lock before it calls `httpserver.serve()`. If a stop was already requested, it logs "Web server stop requested before startup; not starting" at debug level and returns, so the port is never bound and no worker pool starts. The check after publication is unchanged, so a stop that arrives during construction is still honoured (`test_stop_during_server_construction_closes_instead_of_serving` still passes). The class docstring now describes both cases.

Tests were updated first and confirmed failing before the fix:
- `test_stop_before_run_closes_instead_of_serving` became `test_stop_before_run_never_constructs_server`. It asserts that `httpserver.serve` is never called and that `srv.server` stays None.
- `test_real_server_stop_before_start_never_serves` became `test_real_server_stop_before_start_never_binds`. It wraps paste's real `serve` in a spy and asserts the spy is never called and `srv.server` stays None. Binding only happens inside `serve`, so this proves the port was never bound. It replaces the old `assertIsNotNone(srv.server)` and the probe of a released ephemeral port.

### IN-03: Misleading "stop deferred to startup" debug log when run() already failed

**Files modified:** `src/python/web/web_app_job.py`, `src/python/tests/unittests/test_web/test_web_app_job.py`
**Commit:** cbf80a11
**Status:** fixed: requires human verification (new state flag read under the lock)
**Applied fix:** A new `__ended_without_server` flag is set under the lock in a `try/finally` around the pre-start check and server construction. It is set only when no server was built: either the stop came first, or `httpserver.serve()` raised (for example, port in use). It is not set when construction succeeds, so a `stop()` that lands between construction and publication still logs the deferred message, which is correct for that window. `stop()` reads the flag together with `self.server`. If there is no server and run() has ended, it logs "Web server never started; nothing to stop". Otherwise it keeps "Web server not started yet; stop deferred to startup".

Tests:
- `test_stop_after_failed_startup_logs_never_started`: `serve` raises `OSError(98)`, then `stop()` must log the never-started message and not the deferred one. This failed before the fix.
- `test_stop_before_run_logs_deferred`: a guard showing that a stop before any run() still logs the deferred message. It passed both before and after the fix.

### IN-04: Test-suite nits: tautological constant test and an ephemeral-port assumption

**Files modified:** `src/python/tests/unittests/test_web/test_web_app_job.py`
**Commit:** 0a19522c
**Applied fix:** Dropped the redundant `assertLess(..., 10.0)`. Renamed `test_join_timeout_constant_below_docker_grace` to `test_join_timeout_constant_pinned_at_5s`, with a docstring saying it pins the value and pointing to the budget rationale on the constant. The ephemeral-port half of this finding was resolved in the IN-02 commit: the stop-before-start test now asserts adapter state (the real constructor is never called and `srv.server` is None) and no longer connects to a released port.

## Verification

Iteration 2, run from `src/python`:
- `pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider`, three runs in a row: 27 passed, 4 subtests passed each (2.67 s, 2.36 s, 2.29 s).
- `pytest tests/unittests/test_web tests/integration/test_web -q -p no:cacheprovider`: 564 passed, 95 subtests passed.
- `ruff check .`: All checks passed.

Iteration 1: 562 passed, 95 subtests passed. Ruff was clean. The three WR-01 tests passed in 3 consecutive runs.

---

_Fixed: 2026-11-20T04:26:00Z_
_Fixer: Claude (bm-code-fixer)_
_Iteration: 2_
