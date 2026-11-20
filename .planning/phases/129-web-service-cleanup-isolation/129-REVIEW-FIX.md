---
phase: 129-web-service-cleanup-isolation
fixed_at: 2026-11-20T04:20:00Z
review_path: .planning/phases/129-web-service-cleanup-isolation/129-REVIEW.md
iteration: 1
fix_scope: WR-01, IN-01 only
findings_in_scope: 2
fixed: 2
skipped: 0
rejected: 0
status: all_fixed
---

# Phase 129: Code Review Fix Report

**Fixed at:** 2026-11-20T04:20:00Z
**Source review:** .planning/phases/129-web-service-cleanup-isolation/129-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (WR-01, IN-01, as directed by the orchestrator)
- Fixed: 2
- Skipped: 0
- Rejected: 0

Out of scope by instruction and left untouched: IN-02, IN-03, IN-04, SA-01, SA-02.

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

## Verification

Run from `src/python`:
- `pytest tests/unittests/test_web tests/integration/test_web -q -p no:cacheprovider`: 562 passed, 95 subtests passed.
- `ruff check .`: All checks passed.
- The three new WR-01 tests passed in 3 consecutive runs.

---

_Fixed: 2026-11-20T04:20:00Z_
_Fixer: Claude (bm-code-fixer)_
_Iteration: 1_
