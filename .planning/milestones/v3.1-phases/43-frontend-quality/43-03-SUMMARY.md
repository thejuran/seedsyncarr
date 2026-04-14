---
phase: 43-frontend-quality
plan: 03
subsystem: ui
tags: [angular, rxjs, sse, autoqueue, change-detection, memory-leak, subscription]

# Dependency graph
requires:
  - phase: 43-frontend-quality-02
    provides: Prior frontend quality fixes in phase 43
provides:
  - Correct post-request index resolution in AutoQueueService.remove()
  - Timer cleanup on StreamDispatchService destroy (interval + reconnect timer + EventSource)
  - Single async pipe subscription for file-options template options
affects: [file-options, autoqueue, stream-dispatch]

# Tech tracking
tech-stack:
  added: []
  patterns: [fresh-state-in-subscribe-callback, OnDestroy-timer-cleanup, local-snapshot-for-OnPush-template]

key-files:
  created: []
  modified:
    - src/angular/src/app/services/autoqueue/autoqueue.service.ts
    - src/angular/src/app/services/base/stream-service.registry.ts
    - src/angular/src/app/pages/files/file-options.component.ts
    - src/angular/src/app/pages/files/file-options.component.html

key-decisions:
  - "[FE-04]: AutoQueueService.remove re-reads patterns state inside subscribe callback: finalIndex from patterns.findIndex (fresh) not currentPatterns.findIndex (stale) — prevents corrupting list if patterns changed during HTTP request"
  - "[FE-05]: StreamDispatchService.ngOnDestroy clears setInterval timeout checker, cancels stored setTimeout reconnect timer, and closes EventSource — _reconnectTimer field added to track setTimeout handle"
  - "[FE-06]: FileOptionsComponent.latestOptions replaces options: Observable<ViewFileOptions> — subscription in ngOnInit feeds single property with detectChanges() for OnPush compatibility, eliminating 16 async pipe subscriptions"

patterns-established:
  - "Fresh state in subscribe callback: read BehaviorSubject.getValue() inside the callback, not before the request, to avoid stale closures after concurrent state changes"
  - "OnDestroy timer cleanup: store setInterval and setTimeout handles as class fields; clear and null both in ngOnDestroy"
  - "Local snapshot for OnPush template: subscribe once in ngOnInit, write to public property, call detectChanges() — avoids N async pipes for the same observable"

requirements-completed: [FE-04, FE-05, FE-06]

# Metrics
duration: 3min
completed: 2026-02-24
---

# Phase 43 Plan 03: Frontend Quality Bug Fixes Summary

**Stale-index fix in AutoQueueService.remove, timer cleanup on StreamDispatchService destroy, and 16-to-1 async pipe consolidation in FileOptionsComponent**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-24T02:21:30Z
- **Completed:** 2026-02-24T02:24:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- AutoQueueService.remove now reads fresh `_patterns` state inside the subscribe callback for both the list and the index — eliminating the stale `currentPatterns` snapshot that could corrupt the list if patterns changed concurrently during an HTTP request; added `finalIndex >= 0` guard for already-removed edge case
- StreamDispatchService implements OnDestroy: `ngOnDestroy` clears the `setInterval` timeout checker, cancels the stored `_reconnectTimer` (both `reconnectDueToTimeout` and error-path `setTimeout` calls now stored in the field), and closes any live `EventSource`
- FileOptionsComponent.`latestOptions` public property replaces 16 separate `(options | async)` pipe subscriptions — one ngOnInit subscription feeds the property with `detectChanges()` for OnPush; `headerHeight | async` (different observable) unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix AutoQueueService.remove stale index and StreamDispatchService timer cleanup** - `7631bfb` (fix)
2. **Task 2: Consolidate file-options async pipe subscriptions into single observable** - `03ee46c` (refactor)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `src/angular/src/app/services/autoqueue/autoqueue.service.ts` - Fixed stale `currentPatterns.findIndex` in remove() subscribe callback; now uses `patterns.findIndex` (fresh state) with `finalIndex >= 0` guard
- `src/angular/src/app/services/base/stream-service.registry.ts` - Added `OnDestroy` import, `implements OnDestroy`, `_reconnectTimer` field, `ngOnDestroy()` method; stored both setTimeout calls in `_reconnectTimer`
- `src/angular/src/app/pages/files/file-options.component.ts` - Replaced `options: Observable<ViewFileOptions>` with `latestOptions: ViewFileOptions = null`; updated ngOnInit subscription to write property + `detectChanges()`; removed constructor `options` assignment and private `_latestOptions` field
- `src/angular/src/app/pages/files/file-options.component.html` - Replaced all 16 `(options | async)?.` with `latestOptions?.` (zero-cost property access)

## Decisions Made

- Fresh state in subscribe callback: `currentPatterns` (captured before request) cannot be used for post-response index resolution — only `this._patterns.getValue()` inside the callback gives correct state
- `_reconnectTimer` field pattern: both setTimeout code paths (timeout-detected reconnect and error-handler reconnect) must use the same stored handle to allow single-point cleanup in ngOnDestroy
- `latestOptions` on component class: writing to a single property from one subscription is more predictable than N async pipe subscriptions under OnPush change detection — `detectChanges()` replaces the implicit triggering that async pipe provided

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three FE requirements (FE-04, FE-05, FE-06) complete
- All 387 Angular unit tests pass
- Phase 43 plan 03 complete; ready for next plan in phase 43 or phase completion

---
*Phase: 43-frontend-quality*
*Completed: 2026-02-24*
