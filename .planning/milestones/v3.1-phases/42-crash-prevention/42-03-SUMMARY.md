---
phase: 42-crash-prevention
plan: 03
subsystem: api
tags: [python, bottle, http, threading, timeout, controller-handler]

# Dependency graph
requires:
  - phase: 42-crash-prevention
    provides: "Plan 01 and 02 added timeout to bulk endpoint and WebResponseActionCallback.wait()"
provides:
  - "Bounded 30-second timeout on all 5 individual action endpoint wait() calls"
  - "HTTP 504 Gateway Timeout response when individual action command times out"
affects: [42-crash-prevention, web-handler, controller-handler]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "completed = callback.wait(timeout=self._ACTION_TIMEOUT); if not completed: return HTTPResponse(body='Operation timed out', status=504)"

key-files:
  created: []
  modified:
    - src/python/web/handler/controller.py
    - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py

key-decisions:
  - "_ACTION_TIMEOUT = 30.0 on ControllerHandler class: 30s provides generous headroom for delete/extract while still bounding the wait; individual action endpoints mirror bulk endpoint's timeout pattern"
  - "HTTP 504 body is 'Operation timed out' (plain text, matches bulk endpoint's per-file timeout error message)"

patterns-established:
  - "Individual action timeout pattern: completed = callback.wait(timeout=self._ACTION_TIMEOUT); if not completed: return HTTPResponse(body='Operation timed out', status=504)"

requirements-completed: [CRASH-06]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 42 Plan 03: Bounded Timeouts on Individual Action Endpoints Summary

**All 5 individual action handler methods (queue, stop, extract, delete_local, delete_remote) now use a 30-second bounded timeout via _ACTION_TIMEOUT constant, returning HTTP 504 if the controller fails to respond**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-24T02:03:26Z
- **Completed:** 2026-02-24T02:05:06Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Added `_ACTION_TIMEOUT = 30.0` class constant to `ControllerHandler`
- Updated all 5 individual action handlers to use `completed = callback.wait(timeout=self._ACTION_TIMEOUT)` instead of unbounded `callback.wait()`
- Added `if not completed: return HTTPResponse(body="Operation timed out", status=504)` after each wait
- Added `test_action_timeout_returns_504` test (mocks stuck controller, patches timeout to 0.1s, verifies 504 response)
- Added `test_action_success_returns_200` test (mocks successful controller, verifies 200 response with file name in body)
- All 38 tests pass (36 pre-existing + 2 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add bounded timeout to individual action endpoint waits** - `05a0003` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/python/web/handler/controller.py` - Added `_ACTION_TIMEOUT = 30.0`; updated all 5 handlers with bounded timeout and 504 fallback
- `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` - Added `TestControllerHandlerSingleAction` class with 2 new tests

## Decisions Made
- `_ACTION_TIMEOUT = 30.0`: 30 seconds is generous for normal operations (complete in milliseconds) while bounding worst-case waits for delete/extract; matches the plan's recommendation
- Timeout body `"Operation timed out"` (plain text): consistent with the pattern in the bulk endpoint's per-file timeout error
- Placed `_ACTION_TIMEOUT` constant adjacent to the existing `_VALID_ACTIONS` and bulk timeout constants to group all timeout/rate-limit constants together

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CRASH-06 resolved: individual action endpoints are now bounded; no more indefinite thread blocking
- All controller handler tests pass
- Ready for the next plan in phase 42 (crash prevention)

---
*Phase: 42-crash-prevention*
*Completed: 2026-02-24*
