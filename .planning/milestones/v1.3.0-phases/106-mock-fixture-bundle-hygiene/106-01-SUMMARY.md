---
phase: 106-mock-fixture-bundle-hygiene
plan: "01"
subsystem: ui
tags: [angular, environment, fileReplacements, bundle-hygiene, mock-fixture, tree-shaking]

# Dependency graph
requires:
  - phase: 105-font-awesome-to-phosphor-migration
    provides: Phase-105 AFTER bundle baseline (1.13 MB / 207.70 kB) used as BEFORE anchor and secondary sanity gate
provides:
  - useMockModel environment flag in dev (true) and prod (false) env files
  - angular.json second fileReplacements entry swapping mock-model-files.ts for empty prod stub in production
  - mock-model-files.ts relocated to tests/fixtures/ (dev-only fixture dir)
  - mock-model-files.prod.ts empty prod stub with identical MOCK_MODEL_FILES signature
  - screenshot-model-files.ts deleted (135-line dead file, zero importers)
  - 106-BUNDLE-BASELINE.md: TRUE Phase-106 before/after, dist absence proof, Karma floor record
  - environment.test.ts: test-specific env with useMockModel:false ensuring Karma suite sees service behavior
affects: [106-02, 106-03, future-plans-touching-view-file-service]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-layer mock exclusion: env flag (runtime) + fileReplacements (build-time) together guarantee mock data absent from prod"
    - "Per-config environment files: environment.ts (dev), environment.prod.ts (prod), environment.test.ts (test) with key-parallel shapes"
    - "Fixture files in tests/fixtures/ for dev-only data not shipped to production"

key-files:
  created:
    - src/angular/src/app/tests/fixtures/mock-model-files.prod.ts
    - src/angular/src/environments/environment.test.ts
    - .planning/milestones/v1.3.0-phases/106-mock-fixture-bundle-hygiene/106-BUNDLE-BASELINE.md
  modified:
    - src/angular/src/app/tests/fixtures/mock-model-files.ts (moved from services/files/ + import path fix)
    - src/angular/src/environments/environment.ts
    - src/angular/src/environments/environment.prod.ts
    - src/angular/src/app/services/files/view-file.service.ts
    - src/angular/angular.json
  deleted:
    - src/angular/src/app/services/files/mock-model-files.ts (relocated)
    - src/angular/src/app/services/files/screenshot-model-files.ts (dead code)

key-decisions:
  - "D-01: two-layer guarantee (env flag + second fileReplacements entry to prod stub)"
  - "D-02: useMockModel added to both env files (dev true / prod false); USE_MOCK_MODEL class field removed; service branches on environment.useMockModel"
  - "D-03: empty-map prod stub mock-model-files.prod.ts with identical MOCK_MODEL_FILES signature + angular.json second fileReplacements entry"
  - "D-04: screenshot-model-files.ts deleted outright (zero importers)"
  - "D-05: mock-model-files.ts relocated to src/app/tests/fixtures/ via git mv equivalent"
  - "environment.test.ts added (useMockModel:false) to prevent Karma tests from taking the mock branch during unit test runs"

patterns-established:
  - "Pattern: environment flag + fileReplacements for dev-only data — both are needed together for full prod exclusion"
  - "Pattern: environment.test.ts for Karma test environment with service-behavior flags set to false"

requirements-completed: [DEPS-02]

# Metrics
duration: 25min
completed: 2026-06-01
---

# Phase 106 Plan 01: Mock Fixture Bundle Hygiene Summary

**Mock-model fixture eliminated from production bundle via env flag + angular.json fileReplacements; dist absence proven by filename-literal grep; Karma 611/611 green, all floors hold**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-01T17:37:00Z
- **Completed:** 2026-06-01T17:46:00Z
- **Tasks:** 2 (+ 1 Rule-1 auto-fix folded into Task 1 commit chain)
- **Files modified:** 9 (3 created, 4 modified, 2 deleted)

## Accomplishments

- Removed 192-line mock dataset and 135-line dead file from production bundle via two-layer guarantee: `environment.useMockModel` flag (runtime) + angular.json `fileReplacements` swapping the fixture for an empty prod stub (build-time)
- Proved mock data absent: both distinctive filename literal greps (`A Really Cool Video About Cats`, `Super.Secret.Folder.With.A.Long.Name`) return ZERO matches in dist/; `MOCK_MODEL_FILES` symbol also completely tree-shaken
- AFTER bundle: 1.13 MB / 207.23 kB xfer — main chunk -4.87 kB raw vs. BEFORE; within Phase-105 baseline (207.70 kB)
- Karma 611/611 pass; floors stmts 84.33/83, branches 69.31/68, fns 80.49/79, lines 85.18/83 all clear

## Task Commits

1. **Task 1: Relocate fixture, add env flag, repoint service, add prod stub, extend fileReplacements, delete dead file** — `2ead438` (feat)
2. **Rule-1 fix: environment.test.ts + test fileReplacements + fixture import fix** — `7aa11d0` (fix)
3. **Task 2: AFTER prod build, bundle delta, dist absence grep, Karma floors** — `6186bed` (feat)

## Files Created/Modified

- `src/angular/src/app/tests/fixtures/mock-model-files.ts` — relocated from services/files/; ModelFile import path updated to `../../services/files/model-file`
- `src/angular/src/app/tests/fixtures/mock-model-files.prod.ts` — empty prod stub: `MOCK_MODEL_FILES = Immutable.Map<string, ModelFile>()`
- `src/angular/src/environments/environment.ts` — added `useMockModel: true`
- `src/angular/src/environments/environment.prod.ts` — added `useMockModel: false`
- `src/angular/src/environments/environment.test.ts` — created: `useMockModel: false` for Karma test config
- `src/angular/src/app/services/files/view-file.service.ts` — removed `USE_MOCK_MODEL` class field; added `environment` import; branches on `environment.useMockModel`
- `src/angular/angular.json` — production `fileReplacements` now has 2 entries (env swap + fixture swap); test config has env.ts→env.test.ts swap
- `.planning/milestones/v1.3.0-phases/106-mock-fixture-bundle-hygiene/106-BUNDLE-BASELINE.md` — BEFORE/AFTER delta, dist absence proof, Karma floor record
- **Deleted:** `src/angular/src/app/services/files/screenshot-model-files.ts` (dead code, zero importers)

## Decisions Made

- D-01 through D-07 as specified in the plan — all implemented per CONTEXT.md
- Additional: `environment.test.ts` with `useMockModel: false` to keep Karma tests functioning correctly after the `useMockModel: true` dev flag was added (see Deviations)
- The test config's `fileReplacements` for environment (env.ts→env.test.ts) is distinct from the production fixture swap (mock-model-files→mock-model-files.prod.ts); dev/test still see the full populated fixture

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test suite broke when environment.useMockModel: true was added to environment.ts**

- **Found during:** Task 2 (Karma run)
- **Issue:** Adding `useMockModel: true` to `environment.ts` caused `ViewFileService` constructor to take the mock branch (`buildViewFromModelFiles(MOCK_MODEL_FILES)`) instead of subscribing to `modelFileService.files`. This broke 29 of 29 view-file service tests and 9 dashboard-stats service tests (total: 29 FAILED before fix).
- **Root cause:** The Karma test runner uses `environment.ts` (dev config), which now has `useMockModel: true`. Prior to this phase, the class field `USE_MOCK_MODEL = false` was hardcoded, so tests always hit the non-mock path regardless of environment.
- **Fix:** Created `src/environments/environment.test.ts` (key-parallel: production false, useMockModel false, logger DEBUG) and added a `fileReplacements` entry in the angular.json `test` config to swap `environment.ts` for `environment.test.ts`. This preserves the real populated fixture in test (no `mock-model-files.prod.ts` swap in test — as required by plan) while fixing the env flag for test correctness.
- **Files modified:** `src/angular/src/environments/environment.test.ts` (created), `src/angular/angular.json` (test config fileReplacements added)
- **Verification:** 611/611 tests pass; coverage floors all hold
- **Committed in:** `7aa11d0`

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug introduced by Task 1 env flag change)
**Impact on plan:** Necessary for test suite correctness. The plan's constraint "dev/test must see the real populated fixture" is preserved — the test env fix is about the environment flag (useMockModel), not the fixture swap. No scope creep.

## Issues Encountered

- `git mv` failed in the worktree context (fatal: renaming failed: No such file or directory — git mv resolves paths relative to the main repo's filesystem, not the worktree path). Resolved by using `git rm --cached` + `git add` + `cp` + `rm`, which git correctly records as a rename (RM status in index).
- Worktree has no `node_modules` directory. Resolved by symlinking `node_modules` from the main repo (`ln -sf /path/to/main/node_modules /path/to/worktree/node_modules`). The symlink is ignored by `.gitignore`.

## Known Stubs

None. The empty prod stub `mock-model-files.prod.ts` is intentional (not a UI-visible stub) — it is the prod replacement for the fixture and correctly exports an empty map.

## Threat Flags

None. This phase removes an information-disclosure surface (T-106-01 — dev mock dataset in prod bundle). Net attack surface decreases. No new trust boundaries introduced.

## User Setup Required

None — no external service configuration required. Plan 106-02 will smoke-test the dev mock toggle via browser UI (checkpoint).

## Next Phase Readiness

- Plan 106-02 (dev smoke test): the mechanism is in place — `useMockModel: true` in dev environment causes the app to render mock data on `ng serve`. The checkpoint in 106-02 confirms this works via browser visit and DOM inspection.
- All Karma tests pass (611/611); TypeScript compiles clean (tsc --noEmit exit 0).
- The `MOCK-ABSENT-FROM-PROD-DIST` gate is cleared; the Phase-105 bundle baseline is met.

---
*Phase: 106-mock-fixture-bundle-hygiene*
*Plan: 106-01*
*Completed: 2026-06-01*
