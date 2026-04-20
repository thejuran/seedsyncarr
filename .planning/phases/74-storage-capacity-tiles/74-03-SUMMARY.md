---
phase: 74-storage-capacity-tiles
plan: 03
subsystem: ui
tags: [angular, rxjs, dto, combinelatest, sse, immutable]

requires:
  - phase: 74-01
    provides: backend storage block on SSE status stream (snake_case JSON)
provides:
  - ServerStatus DTO storage block (camelCase, snake→camel mapping, deploy-skew safe)
  - DashboardStats four nullable *Capacity* fields (null defaults per D-14)
  - DashboardStatsService combineLatest pipeline merging files$ + status$ (D-15 per-tile independence)
affects: [74-04, future dashboard components consuming capacity]

tech-stack:
  added: []
  patterns:
    - rxjs combineLatest for cross-stream merge with retention semantics
    - optional-chaining + ?? null for backward-compatible JSON parsing

key-files:
  created: []
  modified:
    - src/angular/src/app/services/server/server-status.ts
    - src/angular/src/app/services/files/dashboard-stats.service.ts
    - src/angular/src/app/tests/unittests/services/server/server-status.spec.ts
    - src/angular/src/app/tests/unittests/services/files/dashboard-stats.service.spec.ts
    - src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts

key-decisions:
  - "ServerStatusJson.storage typed as optional (storage?:) to survive backend deploy skew"
  - "ZERO_STATS capacity fields are literal null (NOT 0) per D-14 cold-load fallback rule"
  - "combineLatest seeded by ServerStatusService BehaviorSubject — initial subscription fires immediately with null storage"
  - "Cross-file mock fix in stats-strip.component.spec.ts is owned by this plan (the widener), not deferred to 74-04"

patterns-established:
  - "Snake→camel JSON mapping: json.section?.snake_field ?? null inside fromJson"
  - "Per-tile fallback independence via direct field-by-field assignment from a single status snapshot"

requirements-completed: []

duration: ~10min
completed: 2026-04-20
---

# Phase 74-03: Frontend DTO + DashboardStats Merge Summary

**ServerStatus DTO storage block + DashboardStats four nullable capacity fields wired through DashboardStatsService via combineLatest(files$, status$).**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files modified:** 5
- **Tests:** 35 SUCCESS (4 new combineLatest tests, 6 new storage DTO tests, 25 baseline)

## Accomplishments
- `IServerStatus.storage` block (camelCase) + `DefaultServerStatus.storage` all-null + `ServerStatus` class field
- `ServerStatusJson.storage` optional + `ServerStatus.fromJson` snake→camel with `?.` + `?? null` fallback (deploy-skew safe)
- `DashboardStats` widened with four `*Capacity*` fields (`number | null`)
- `ZERO_STATS` capacity fields literal `null` per D-14
- `DashboardStatsService` constructor rewired to `combineLatest([files, status])` with `takeUntil(destroy$)`
- 4 new combineLatest tests (capacity surfacing, per-tile independence, retention in both directions)
- 6 new ServerStatus storage tests (init per-field, null passthrough, missing-key deploy skew, default record cold-load)

## Task Commits

1. **Task 1 RED: ServerStatus storage block tests** — `0aa039c` (test)
2. **Task 1 GREEN: ServerStatus DTO storage block** — `1e6faf0` (feat)
3. **Task 2 RED: DashboardStats capacity + combineLatest tests** — `4d5e8de` (test)
4. **Task 2 GREEN: DashboardStats widening + combineLatest pipeline** — `9f58d39` (feat)
5. **Cross-file fix: stats-strip mock null capacity fields** — `f4acdb9` (fix)

## Files Created/Modified
- `src/angular/src/app/services/server/server-status.ts` — IServerStatus.storage, DefaultServerStatus.storage, ServerStatus.storage class field, ServerStatusJson.storage?, fromJson snake→camel mapping
- `src/angular/src/app/services/files/dashboard-stats.service.ts` — DashboardStats widened, ZERO_STATS null capacities, constructor combineLatest pipeline, ServerStatusService injection
- `src/angular/src/app/tests/unittests/services/server/server-status.spec.ts` — 6 new tests (per-field init, null passthrough, deploy-skew default, cold-load default)
- `src/angular/src/app/tests/unittests/services/files/dashboard-stats.service.spec.ts` — 4 new tests (capacity surfacing, per-tile independence, retention in both directions); MockServerStatusService added; updated default-stats assertion
- `src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts` — Added four `null` capacity fields to three `DashboardStats` literals to unblock TS compile (Plan 74-04 will further modify this file)

## Decisions Made
- `ServerStatusJson.storage` typed optional (`storage?:`) so older backend payloads parse without TS error during rolling deploy
- `?.` + `?? null` in `fromJson` collapses three deploy-skew cases (missing key, present-with-null, present-with-number) into one expression
- Cross-file fix to `stats-strip.component.spec.ts` adopted from this plan (Rule 1: type regression from interface widening) rather than deferred to 74-04 — without it the entire Angular TS project fails to compile, blocking all test runs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Type regression] Mock in stats-strip.component.spec.ts breaks TS compile after DashboardStats widening**
- **Found during:** Task 2 verification (test run)
- **Issue:** `stats-strip.component.spec.ts` constructs three `DashboardStats` literals (one BehaviorSubject init + two `pushStats` calls) that omit the four new `*Capacity*` fields, causing TS2345 errors that block the entire Angular test project from compiling
- **Fix:** Added `remoteCapacityTotal: null, remoteCapacityUsed: null, localCapacityTotal: null, localCapacityUsed: null` to all three sites
- **Files modified:** `src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts`
- **Verification:** `npx ng test` against the three relevant spec files now reports 35 SUCCESS
- **Committed in:** `f4acdb9`

---

**Total deviations:** 1 auto-fixed (Rule 1 type regression from interface widening)
**Impact on plan:** Necessary for test correctness; no scope creep. Plan 74-04 will further modify the same file for capacity-tile UI tests.

## Issues Encountered
- The originally-spawned subagent paused mid-Task-2 reporting that a `PreToolUse:Edit` reminder appeared to block edits to `stats-strip.component.spec.ts`. Investigation showed the reminder is advisory-only — edits succeed despite the reminder. Orchestrator completed Task 2 GREEN commit, ran the cross-file fix, and verified the test suite directly.

## User Setup Required
None.

## Next Phase Readiness
- Plan 74-04 can now consume `stats.remoteCapacityTotal`, `stats.remoteCapacityUsed`, `stats.localCapacityTotal`, `stats.localCapacityUsed` directly from `DashboardStatsService.stats$`
- `null` capacity values enable the per-tile fallback branch in the template (D-14 / D-15)
- The `stats-strip.component.spec.ts` mock is compile-clean; 74-04 can extend it with capacity-tile assertions

---
*Phase: 74-storage-capacity-tiles*
*Completed: 2026-04-20*
