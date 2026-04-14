---
phase: 42-crash-prevention
plan: 02
subsystem: ui
tags: [angular, sse, rxjs, observable, error-handling, typescript]

# Dependency graph
requires: []
provides:
  - SSE dispatch guard against unknown event names (CRASH-04)
  - try/catch around JSON.parse in ModelFileService, ServerStatusService, LogService (CRASH-05)
  - Malformed JSON resilience tests for all three stream services
affects: [crash-prevention, sse, stream-services]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Map.has() guard before Map.get().method() to prevent undefined dereference in observable next handlers"
    - "try/catch wrapping JSON.parse in SSE stream service parse methods"

key-files:
  created: []
  modified:
    - src/angular/src/app/services/base/stream-service.registry.ts
    - src/angular/src/app/services/files/model-file.service.ts
    - src/angular/src/app/services/server/server-status.service.ts
    - src/angular/src/app/services/logs/log.service.ts
    - src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts
    - src/angular/src/app/tests/unittests/services/files/model-file.service.spec.ts
    - src/angular/src/app/tests/unittests/services/logs/log.service.spec.ts
    - src/angular/src/app/tests/unittests/services/server/server-status.service.spec.ts

key-decisions:
  - "Inject LoggerService into ServerStatusService for consistent error logging on malformed JSON"
  - "Use console.error in LogService for malformed JSON (no LoggerService dep to add) — avoids new dependency for defensive path"
  - "Guard .get(eventName) with .has() check rather than nullish coalescing — explicit warning log aids debugging"

patterns-established:
  - "Map.has() guard before Map.get().notifyEvent() in observable next handlers"
  - "try/catch wrapping entire parse method body, not just the JSON.parse line"

requirements-completed: [CRASH-04, CRASH-05]

# Metrics
duration: 3min
completed: 2026-02-24
---

# Phase 42 Plan 02: Angular SSE Crash Prevention Summary

**Hardened Angular SSE stream against unknown event names and malformed JSON: Map.has() guard in dispatch + try/catch in all three stream service parsers with 3 new resilience tests**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-24T02:03:33Z
- **Completed:** 2026-02-24T02:07:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Fixed CRASH-04: StreamDispatchService now checks `_eventNameToServiceMap.has(eventName)` before calling `.notifyEvent()` — unknown event names log a warning instead of crashing the subscription
- Fixed CRASH-05: All three SSE stream services (ModelFileService, ServerStatusService, LogService) wrap JSON.parse in try/catch — malformed JSON is logged and skipped, stream continues
- Added 3 new unit tests verifying malformed JSON resilience across all services
- All 385 Angular unit tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Guard SSE dispatch against unknown event names** - `e736b69` (fix)
2. **Task 2: Wrap JSON.parse in try/catch across all SSE stream services** - `a7122fc` (fix)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `src/angular/src/app/services/base/stream-service.registry.ts` - Added Map.has() guard before notifyEvent() call in observable next handler
- `src/angular/src/app/services/files/model-file.service.ts` - Wrapped entire parseEvent() body in try/catch
- `src/angular/src/app/services/server/server-status.service.ts` - Injected LoggerService, wrapped parseStatus() in try/catch
- `src/angular/src/app/services/logs/log.service.ts` - Wrapped onEvent() JSON.parse in try/catch with console.error
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` - Added test for stream resilience after known events
- `src/angular/src/app/tests/unittests/services/files/model-file.service.spec.ts` - Added malformed JSON resilience test
- `src/angular/src/app/tests/unittests/services/logs/log.service.spec.ts` - Added malformed JSON resilience test
- `src/angular/src/app/tests/unittests/services/server/server-status.service.spec.ts` - Added malformed JSON resilience test

## Decisions Made
- Injected LoggerService into ServerStatusService for consistent error logging — already provided in the test module
- Used `console.error` in LogService to avoid adding a new dependency for a defensive error path
- Guard uses explicit `if (service)` check with `_logger.warn` rather than silent ignore — aids debugging

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added LoggerService injection to ServerStatusService**
- **Found during:** Task 2 (server-status.service.ts fix)
- **Issue:** Plan noted ServerStatusService had no `_logger` and offered either injecting LoggerService or using console.error. Injecting LoggerService is consistent with ModelFileService pattern and the test module already provided LoggerService.
- **Fix:** Added `import {LoggerService}` and `constructor(private _logger: LoggerService)` to ServerStatusService
- **Files modified:** src/angular/src/app/services/server/server-status.service.ts
- **Verification:** All tests pass, including existing server-status.service.spec.ts tests
- **Committed in:** a7122fc (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (missing critical - no logger for error reporting)
**Impact on plan:** Necessary for consistent error visibility. LoggerService was already provided in test module so no test changes needed beyond the new resilience test.

## Issues Encountered
None — implementation was straightforward. LoggerService was already listed in test providers.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CRASH-04 and CRASH-05 requirements are satisfied
- Angular SSE stream is now resilient to both unknown event names and malformed JSON payloads
- Ready for remaining phases in 42-crash-prevention

---
*Phase: 42-crash-prevention*
*Completed: 2026-02-24*
