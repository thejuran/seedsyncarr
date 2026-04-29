---
phase: 90-angular-test-fixes
plan: 01
subsystem: testing
tags: [angular, jasmine, fakeAsync, discardPeriodicTasks, typescript, karma]

# Dependency graph
requires:
  - phase: 86-test-audit
    provides: Angular test baseline (599 tests passing)
provides:
  - fakeAsync zone cleanup in stream-service.registry.spec.ts (no pending timer warnings)
  - Truthful nullable type for filterCriteria in view-file-filter.service.spec.ts
  - toBeDefined guards in bulk-command.service.spec.ts preventing silent false passes
affects: [90-angular-test-fixes]

# Tech tracking
tech-stack:
  added: []
  patterns: [discardPeriodicTasks in fakeAsync zones with setInterval, union types over double-cast for nullable test variables, toBeDefined guards before optional chaining assertions]

key-files:
  created: []
  modified:
    - src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts
    - src/angular/src/app/tests/unittests/services/files/view-file-filter.service.spec.ts
    - src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts

key-decisions:
  - "Plan listed 9 fakeAsync it() blocks but file has 8; added discardPeriodicTasks to all 8 actual fakeAsync it blocks"

patterns-established:
  - "discardPeriodicTasks(): call at end of every fakeAsync block that inherits periodic timers from beforeEach"
  - "Union type | undefined: prefer over double-cast (as unknown as T) for nullable test variables"
  - "toBeDefined guard: add expect(result).toBeDefined() before any result?.property assertions"

requirements-completed: [ANGFIX-01, ANGFIX-02, ANGFIX-07]

# Metrics
duration: 3min
completed: 2026-04-25
---

# Phase 90 Plan 01: Angular Test Fixes - Zone Cleanup, Type Safety, and Assertion Guards

**discardPeriodicTasks in 10 fakeAsync blocks, union type replacing double-cast, and 7 toBeDefined guards across 3 Angular spec files**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-25T21:55:34Z
- **Completed:** 2026-04-25T21:59:32Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Eliminated pending timer warnings in stream-service.registry.spec.ts by adding discardPeriodicTasks() to 1 beforeEach + 8 fakeAsync it() blocks
- Replaced unsafe double-cast (undefined as unknown as ViewFileFilterCriteria) with truthful union type (ViewFileFilterCriteria | undefined) and non-null assertions at 40 call sites
- Added expect(result).toBeDefined() guards to 7 test blocks in bulk-command.service.spec.ts that relied on optional chaining (result?.) which silently passes when result is undefined
- All 599 Angular tests pass with zero timer warnings and zero TypeScript compilation errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add discardPeriodicTasks() to stream-service.registry.spec.ts** - `4be045d` (fix)
2. **Task 2: Fix double-cast and add toBeDefined guards** - `4e92875` (fix)

## Files Created/Modified
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` - Added discardPeriodicTasks import and 9 call sites (1 beforeEach + 8 it blocks) to clean up setInterval from onInit()
- `src/angular/src/app/tests/unittests/services/files/view-file-filter.service.spec.ts` - Changed filterCriteria type to union, removed double-cast, added ! non-null assertion to 40 meetsCriteria() calls
- `src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts` - Added 7 expect(result).toBeDefined() guards before optional chaining assertions

## Decisions Made
- Plan counted 9 fakeAsync it() blocks but the file contains exactly 8. Added discardPeriodicTasks to all 8 actual fakeAsync it() blocks (10 total grep hits: 1 import + 1 beforeEach + 8 it blocks, not 11 as plan predicted). This is a plan enumeration error, not a code deviation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected fakeAsync it() block count from plan's 9 to actual 8**
- **Found during:** Task 1 (stream-service.registry.spec.ts)
- **Issue:** Plan stated 9 fakeAsync it() blocks but the file only has 8. The plan's acceptance criteria expected grep -c of 11 (1+1+9) but correct count is 10 (1+1+8).
- **Fix:** Added discardPeriodicTasks to all 8 actual fakeAsync it() blocks. Result: 10 grep hits instead of plan's predicted 11.
- **Files modified:** stream-service.registry.spec.ts
- **Verification:** All 14 tests in file pass, zero timer warnings
- **Committed in:** 4be045d

---

**Total deviations:** 1 auto-fixed (1 plan miscount correction)
**Impact on plan:** Trivial -- plan over-counted by 1, all actual fakeAsync blocks are covered.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 3 spec files fixed and verified
- 599/599 Angular tests passing
- Ready for plan 02 (remaining Angular test quality fixes)

## Self-Check: PASSED

All 3 modified files exist. Both task commits (4be045d, 4e92875) verified in git log.

---
*Phase: 90-angular-test-fixes*
*Completed: 2026-04-25*
