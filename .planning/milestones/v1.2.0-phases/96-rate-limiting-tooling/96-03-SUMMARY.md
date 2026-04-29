---
phase: 96-rate-limiting-tooling
plan: "03"
subsystem: web-handlers
tags: [rate-limiting, bottle, decorator, config-handler, status-handler, controller-handler, python]

requires:
  - "rate_limit(max_requests, window_seconds) decorator factory from Plan 01"
provides:
  - "Rate-limited /server/config/set at 60 req/60s (D-01 high tier)"
  - "Rate-limited /server/config/sonarr/test-connection at 5 req/60s (D-01 low tier)"
  - "Rate-limited /server/config/radarr/test-connection at 5 req/60s (D-01 low tier)"
  - "Rate-limited /server/status at 60 req/60s (D-01 high tier)"
  - "Rate-limited /server/command/bulk at 10 req/60s (D-03 preserved)"
  - "Elimination of inline _check_bulk_rate_limit() from ControllerHandler (D-05)"
affects: []

tech-stack:
  added: []
  patterns:
    - "rate_limit(N, W) applied at add_routes() time — each call creates an independent closure"
    - "Decorator wraps handler before registration; rate limit enforced at routing layer, not method body"

key-files:
  created: []
  modified:
    - src/python/web/handler/config.py
    - src/python/web/handler/status.py
    - src/python/web/handler/controller.py
    - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py
    - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
    - src/python/tests/unittests/test_web/test_handler/test_status_handler.py

key-decisions:
  - "rate_limit() applied at add_routes() registration, not as a class-level decorator — preserves independent closures per handler instance"
  - "Lock import removed from controller.py since _bulk_rate_lock no longer needed"
  - "TestControllerHandlerRateLimit extracted into its own class (approach A from plan) with _rate_limited_bulk wrapper in setUp — avoids contaminating TestControllerHandlerBulkCommand tests with rate limit state"
  - "test_test_connection_rate_limited_at_5_per_60s uses real Config() (not MagicMock) to avoid MagicMock propagating as URL string to urlparse"

requirements-completed: [RATE-02, RATE-03, RATE-04]

duration: 8min
completed: "2026-04-28"
---

# Phase 96 Plan 03: Apply rate_limit Decorator to All HTTP Endpoints Summary

**rate_limit decorator applied to all mutable/pollable endpoints (config/set at 60/60s, test-connection at 5/60s, /server/status at 60/60s, bulk at 10/60s preserved); ControllerHandler inline rate limit logic eliminated per D-05**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-28T22:58Z
- **Completed:** 2026-04-28T23:04Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Applied `rate_limit` decorator to `config/set` (60/60s), `sonarr/test-connection` (5/60s), `radarr/test-connection` (5/60s), and `/server/status` (60/60s) — all per D-01 thresholds
- Refactored `ControllerHandler` to use decorator at `add_routes()` for bulk endpoint (10/60s per D-03), eliminating `_check_bulk_rate_limit()`, `_BULK_RATE_LIMIT`, `_BULK_RATE_WINDOW`, `_bulk_request_times`, `_bulk_rate_lock` (D-05)
- `Lock` import removed from controller.py as no longer needed
- `TestControllerHandlerRateLimit` class created using decorator approach (A) — fresh rate-limited wrapper in setUp
- `TestConfigHandlerRateLimit` class added covering 60/60s for config/set and 5/60s for test-connection
- `TestStatusHandlerRateLimit` class added covering 60/60s for /server/status
- All 1224 Python tests pass (151 handler tests + full suite), zero regressions

## Task Commits

1. **Task 1: ConfigHandler + StatusHandler** - `e8e8fed` (feat)
2. **Task 2: ControllerHandler refactor + all test updates** - `6e66d6a` (feat)

## Files Created/Modified

- `src/python/web/handler/config.py` — Added `from web.rate_limit import rate_limit`; `add_routes` wraps set at 60/60s, both test-connections at 5/60s; `/server/config/get` unwrapped (read-only)
- `src/python/web/handler/status.py` — Added `from web.rate_limit import rate_limit`; `add_routes` wraps `/server/status` at 60/60s
- `src/python/web/handler/controller.py` — Added decorator import; removed `_BULK_RATE_LIMIT`, `_BULK_RATE_WINDOW`, `_bulk_request_times`, `_bulk_rate_lock`, `_check_bulk_rate_limit()`; bulk wrapped at 10/60s in `add_routes`; `Lock` removed from threading import
- `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` — Added `from web.rate_limit import rate_limit`; new `TestControllerHandlerRateLimit` class with decorator-based tests using numeric literals (10, 60.0); removed `ControllerHandler._bulk_request_times = []` resets from `setUp` methods
- `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` — Added `TestConfigHandlerRateLimit` class with 2 tests
- `src/python/tests/unittests/test_web/test_handler/test_status_handler.py` — Added `import json`; added `TestStatusHandlerRateLimit` class with 1 test

## Decisions Made

- Each `rate_limit(...)` call in `add_routes()` creates an independent closure — per D-01, endpoints have separate counters that do not share state
- `_call_bulk_handler` in `TestControllerHandlerBulkCommand` still calls `__handle_bulk_command` directly (bypassing the decorator) — this is correct for the bulk validation/behavior tests; the rate limit behavior is tested in the separate `TestControllerHandlerRateLimit` class
- `test_test_connection_rate_limited_at_5_per_60s` uses real `Config()` with concrete URL and api_key values — MagicMock URL caused `TypeError` in `urlparse` during socket validation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MagicMock propagating as URL string in test_connection rate limit test**
- **Found during:** Task 2 (first Docker test run)
- **Issue:** `test_test_connection_rate_limited_at_5_per_60s` used `MagicMock()` for config; `mock_config.sonarr.sonarr_url` returned a MagicMock object, causing `TypeError: '>' not supported between instances of 'MagicMock' and 'int'` inside `urlparse`
- **Fix:** Replaced `MagicMock()` config with `real Config()` object with concrete `sonarr_url` and `sonarr_api_key` strings; patched `socket` module to mock DNS resolution; patched `requests.get` to raise `ConnectionError`
- **Files modified:** `src/python/tests/unittests/test_web/test_handler/test_config_handler.py`
- **Commit:** 6e66d6a

## Known Stubs

None.

## Threat Flags

All threat mitigations in the plan's STRIDE register are now implemented:
- T-96-07: config/test-connection at 5 req/60s — DoS prevention on expensive outbound HTTP
- T-96-08: config/set at 60 req/60s — tampering prevention while allowing settings form saves
- T-96-09: /server/status at 60 req/60s — aggressive polling prevention
- T-96-10: /server/command/bulk preserved at 10 req/60s via decorator

No new threat surface introduced beyond what the plan documents.

## Self-Check: PASSED

- FOUND: src/python/web/handler/config.py
- FOUND: src/python/web/handler/status.py
- FOUND: src/python/web/handler/controller.py
- FOUND: src/python/tests/unittests/test_web/test_handler/test_controller_handler.py
- FOUND: src/python/tests/unittests/test_web/test_handler/test_config_handler.py
- FOUND: src/python/tests/unittests/test_web/test_handler/test_status_handler.py
- FOUND: Task 1 commit e8e8fed
- FOUND: Task 2 commit 6e66d6a
- Grep check: controller.py contains 0 occurrences of old inline rate limit patterns
- Grep check: config.py has 3 rate_limit() calls, status.py has 1, controller.py has 1
- Full suite: 1224 passed, 62 skipped, 0 failures

---
*Phase: 96-rate-limiting-tooling*
*Completed: 2026-04-28*
