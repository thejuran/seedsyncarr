---
phase: 46-code-review-fixes
plan: 04
subsystem: ui
tags: [angular, typescript, sse, stream, logging, http]

# Dependency graph
requires:
  - phase: 43-frontend-stream-fixes
    provides: StreamDispatchService with _reconnectTimer field and ngOnDestroy cleanup
  - phase: 42-frontend-crash-fixes
    provides: Map.has() guard for unknown SSE events in StreamDispatchService
provides:
  - clearTimeout guard before both _reconnectTimer reassignment sites (CR-06)
  - Real unknown-event test exercising Map.get() guard path via spyOnProperty (CR-08)
  - LogService uses LoggerService.error instead of console.error (CR-09)
  - RestService shared handleSuccess/handleError helpers eliminating triplicated code (CR-11)
affects: [angular-streaming, frontend-services, code-review-fixes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "clearTimeout before setTimeout reassignment: prevents ghost timers on reconnect"
    - "spyOnProperty for getter-based LoggerService methods in Angular tests"
    - "Private helper factories (handleSuccess/handleError) returning closures for RxJS operators"

key-files:
  created: []
  modified:
    - src/angular/src/app/services/base/stream-service.registry.ts
    - src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts
    - src/angular/src/app/services/logs/log.service.ts
    - src/angular/src/app/services/utils/rest.service.ts

key-decisions:
  - "spyOnProperty for LoggerService.warn getter: spyOn cannot intercept getters directly; spyOnProperty captures the getter call and returns a jasmine.createSpy() function that the production code invokes"
  - "handleSuccess/handleError as factory methods: each returns a closure over url for logging, preserving exact behavior while eliminating three copies of identical map/catchError blocks"
  - "clearTimeout guard pattern: if (this._reconnectTimer) { clearTimeout(...); } before both setTimeout assignment sites in reconnectDueToTimeout() and error handler"

patterns-established:
  - "clearTimeout before _reconnectTimer: pattern applied at both assignment sites to prevent ghost timers"
  - "spyOnProperty for getter-returning-function: use spyOnProperty(obj, 'getter', 'get').and.returnValue(spy) instead of spyOn for LoggerService methods"

requirements-completed: [CR-06, CR-08, CR-09, CR-11]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 46 Plan 04: Code Review Fixes (CR-06/08/09/11) Summary

**Ghost-timer clearTimeout guards added to both reconnect sites; unknown-event test uses spyOnProperty; LogService injects LoggerService; RestService deduplicates map/catchError to shared private factories**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T03:47:04Z
- **Completed:** 2026-02-24T03:49:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- CR-06: Added `clearTimeout(this._reconnectTimer)` guard before both `setTimeout` assignments in `StreamDispatchService` — prevents accumulation of ghost reconnect timers when reconnect is triggered while one is already pending
- CR-08: Replaced inadequate unknown-event test with one that deletes a service mapping from `_eventNameToServiceMap` after setup, fires the orphaned event, and asserts via `spyOnProperty` that `warn` was called; stream continues working for other events
- CR-09: `LogService` now injects `LoggerService` and replaces `console.error(...)` with `this._logger.error(...)` for consistent logging across the Angular codebase
- CR-11: `RestService` extracts identical `map`/`catchError` blocks into `handleSuccess(url)` and `handleError(url)` private factory methods; all three HTTP methods (`sendRequest`, `post`, `delete`) call the shared helpers

## Task Commits

Each task was committed atomically:

1. **Task 1: Clear _reconnectTimer before reassignment and fix unknown-event test** - `d9ed3f9` (fix)
2. **Task 2: LogService uses LoggerService and RestService error helper extraction** - `b53fe7d` (fix)

## Files Created/Modified

- `src/angular/src/app/services/base/stream-service.registry.ts` - Added `clearTimeout` guard at both `_reconnectTimer` assignment sites (lines 160 and 255)
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` - Replaced trivial unknown-event test with Map.get() guard path test using `spyOnProperty`
- `src/angular/src/app/services/logs/log.service.ts` - Added `LoggerService` import and injection; replaced `console.error` with `this._logger.error`
- `src/angular/src/app/services/utils/rest.service.ts` - Extracted `handleSuccess(url)` and `handleError(url)` private helpers; removed triplicated inline map/catchError blocks

## Decisions Made

- **spyOnProperty for LoggerService getters:** `LoggerService.warn` (and `error`, `debug`, `info`) are getters returning bound console functions. `spyOn(logger, "warn")` intercepts the getter call but the returned function is the real `console.warn` — asserting `toHaveBeenCalled()` on the spy fails. The fix is `spyOnProperty(loggerService, "warn", "get").and.returnValue(jasmine.createSpy("warnFn"))` to intercept the getter and return a traceable function.
- **Factory method pattern for RxJS helpers:** `handleSuccess` and `handleError` take `url` as an argument and return a function. This is the correct pattern for reusable RxJS operator callbacks when they need to close over state (the URL for logging).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] spyOn replaced with spyOnProperty for LoggerService.warn getter**
- **Found during:** Task 1 (unknown-event test verification)
- **Issue:** The plan's test template used `spyOn(loggerService, "warn")` but `warn` is a getter on `LoggerService`'s prototype. `spyOn` intercepts the getter's property descriptor, making calls to the getter return the spy object itself rather than a function — so calling `this._logger.warn(...)` in production code fails to record a call on the spy
- **Fix:** Used `spyOnProperty(loggerService, "warn", "get").and.returnValue(jasmine.createSpy("warnFn"))` and asserted `expect(warnFn).toHaveBeenCalled()` on the inner spy
- **Files modified:** `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts`
- **Verification:** 394/394 tests pass after fix
- **Committed in:** d9ed3f9 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan-provided test code)
**Impact on plan:** Fix was essential for the test to correctly exercise the warn guard path. All other changes executed exactly as planned.

## Issues Encountered

None beyond the `spyOn`/`spyOnProperty` correction documented above.

## Next Phase Readiness

- 394/394 Angular unit tests pass
- Production build succeeds with no errors (warnings are pre-existing, unrelated)
- All four CR requirements satisfied; ready for remaining Phase 46 plans

---
*Phase: 46-code-review-fixes*
*Completed: 2026-02-24*
