---
phase: 84-angular-test-audit
plan: 01
subsystem: testing
tags: [angular, karma, jasmine, coverage, audit, staleness]

# Dependency graph
requires:
  - phase: 83-python-test-audit
    provides: "Zero-removal Python staleness audit pattern (D-01 criteria, D-05 inventory format)"
provides:
  - "Zero-removal staleness audit result for Angular unit test suite (40 spec files)"
  - "Coverage baseline: Statements 83.34%, Branches 69.01%, Functions 79.73%, Lines 84.21%"
  - "Verified all 40 spec files exercise live production components/services"
  - "Verified all 7 mock files are actively imported (zero orphans)"
  - "ng test green: 599/599 tests passing"
affects: [84-02-ci-noise-cleanup, 85-e2e-test-audit, 86-coverage-verification]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - ".planning/phases/84-angular-test-audit/84-01-SUMMARY.md"
  modified: []

key-decisions:
  - "Zero stale Angular tests found -- all 40 spec files import production code that exists on disk"
  - "Coverage baseline captured locally via ChromeHeadless (not Docker): Statements 83.34%, Branches 69.01%, Functions 79.73%, Lines 84.21%"
  - "Two previously stale specs (file.component.spec.ts, file-list.component.spec.ts) were already removed in commit 103ace3 during Phase 72"
  - "All 7 mocks in tests/mocks/ have active importers (zero orphans per D-05)"

patterns-established: []

requirements-completed: [NG-01, NG-02, NG-03]

# Metrics
duration: 22min
completed: 2026-04-24
---

# Phase 84 Plan 01: Angular Test Staleness Audit and Coverage Baseline Summary

**Independent staleness audit of 40 Angular spec files confirms zero stale tests; ng test green 599/599; coverage baseline Statements 83.34% / Branches 69.01% / Functions 79.73% / Lines 84.21%**

## Performance

- **Duration:** 22 min
- **Started:** 2026-04-24T19:00:00Z
- **Completed:** 2026-04-24T19:22:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Independently verified all 40 Angular spec files import production components, services, or models that exist on disk (zero stale per D-01)
- Confirmed all 7 mock files in `src/angular/src/app/tests/mocks/` are actively imported by remaining spec files (zero orphans per D-05)
- Ran full Angular test suite: 599/599 tests pass with zero failures (NG-02/NG-03)
- Captured pre-migration coverage baseline: Statements 83.34%, Branches 69.01%, Functions 79.73%, Lines 84.21% (D-09)
- Documented zero-removal inventory (D-06) confirming no spec removals needed at this stage

## Task Commits

Each task was committed atomically:

1. **Task 1: Execute staleness audit, run test suite, capture coverage baseline, and document results** - (docs: audit result — SUMMARY.md only, no production code changes)

## Removal Inventory (D-06)

| Spec File Path | Test Count Removed | Reason |
|----------------|-------------------|--------|
| *(none)* | 0 | All 40 spec files verified LIVE against production modules |

**Total tests removed:** 0
**Total files deleted:** 0

**Historical note:** `file.component.spec.ts` and `file-list.component.spec.ts` were the two stale spec files that tested `FileComponent` and `FileListComponent` (deleted during the v1.1.0 redesign in Phase 72). Both were already removed in commit `103ace3`. They no longer exist. [VERIFIED: git log --diff-filter=D, 84-RESEARCH.md]

## Coverage Baseline (D-09)

Coverage captured via: `node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false --code-coverage`

Environment: local macOS, ChromeHeadless (Chrome.app), Angular 21.2.9 / Karma 6.4.4

| Metric | Value | Raw Count |
|--------|-------|-----------|
| Statements | **83.34%** | 1682 / 2018 |
| Branches | **69.01%** | 461 / 668 |
| Functions | **79.73%** | 421 / 528 |
| Lines | **84.21%** | 1622 / 1926 |

**Test suite result:** 599 / 599 SUCCESS (0 failures, 0 pending)

Note: Coverage collected with `text-summary` reporter added temporarily to karma.conf.js for baseline capture, then reverted. No permanent changes to karma.conf.js — `git diff HEAD -- src/angular/karma.conf.js` confirms zero diff.

## Verification Evidence

### NG-01: Import Cross-Check (All 40 Spec Files)

**Method:** For each of the 40 spec files, extracted all relative import paths (`./` and `../`) using `grep -oP` on import statements, resolved each path relative to the spec file's directory, and verified the target `.ts` file exists on disk.

**Result table:**

| Spec File | Target Production File | Status |
|-----------|----------------------|--------|
| `pages/about/about-page.component.spec.ts` | `about-page.component.ts` | LIVE |
| `pages/settings/option.component.spec.ts` | `option.component.ts` | LIVE |
| `pages/settings/settings-page.component.spec.ts` | `settings-page.component.ts` | LIVE |
| `tests/unittests/common/is-selected.pipe.spec.ts` | `common/is-selected.pipe.ts` | LIVE |
| `tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` | `pages/files/bulk-actions-bar.component.ts` | LIVE |
| `tests/unittests/pages/files/dashboard-log-pane.component.spec.ts` | `pages/files/dashboard-log-pane.component.ts` | LIVE |
| `tests/unittests/pages/files/stats-strip.component.spec.ts` | `pages/files/stats-strip.component.ts` | LIVE |
| `tests/unittests/pages/files/transfer-row.component.spec.ts` | `pages/files/transfer-row.component.ts` | LIVE |
| `tests/unittests/pages/files/transfer-table.component.spec.ts` | `pages/files/transfer-table.component.ts` | LIVE |
| `tests/unittests/pages/logs/logs-page.component.spec.ts` | `pages/logs/logs-page.component.ts` | LIVE |
| `tests/unittests/pages/main/app.component.spec.ts` | `pages/main/app.component.ts` | LIVE |
| `tests/unittests/pages/main/notification-bell.component.spec.ts` | `pages/main/notification-bell.component.ts` | LIVE |
| `tests/unittests/services/autoqueue/autoqueue.service.spec.ts` | `services/autoqueue/autoqueue.service.ts` | LIVE |
| `tests/unittests/services/base/base-stream.service.spec.ts` | `services/base/base-stream.service.ts` | LIVE |
| `tests/unittests/services/base/base-web.service.spec.ts` | `services/base/base-web.service.ts` | LIVE |
| `tests/unittests/services/base/stream-service.registry.spec.ts` | `services/base/stream-service.registry.ts` | LIVE |
| `tests/unittests/services/files/bulk-action-dispatcher.service.spec.ts` | `services/files/bulk-action-dispatcher.service.ts` | LIVE |
| `tests/unittests/services/files/dashboard-stats.service.spec.ts` | `services/files/dashboard-stats.service.ts` | LIVE |
| `tests/unittests/services/files/file-selection.service.spec.ts` | `services/files/file-selection.service.ts` | LIVE |
| `tests/unittests/services/files/model-file.service.spec.ts` | `services/files/model-file.service.ts` | LIVE |
| `tests/unittests/services/files/model-file.spec.ts` | `services/files/model-file.ts` | LIVE |
| `tests/unittests/services/files/view-file-filter.service.spec.ts` | `services/files/view-file-filter.service.ts` | LIVE |
| `tests/unittests/services/files/view-file-options.service.spec.ts` | `services/files/view-file-options.service.ts` | LIVE |
| `tests/unittests/services/files/view-file-sort.service.spec.ts` | `services/files/view-file-sort.service.ts` | LIVE |
| `tests/unittests/services/files/view-file.service.spec.ts` | `services/files/view-file.service.ts` | LIVE |
| `tests/unittests/services/logs/log-record.spec.ts` | `services/logs/log-record.ts` | LIVE |
| `tests/unittests/services/logs/log.service.spec.ts` | `services/logs/log.service.ts` | LIVE |
| `tests/unittests/services/server/bulk-command.service.spec.ts` | `services/server/bulk-command.service.ts` | LIVE |
| `tests/unittests/services/server/server-command.service.spec.ts` | `services/server/server-command.service.ts` | LIVE |
| `tests/unittests/services/server/server-status.service.spec.ts` | `services/server/server-status.service.ts` | LIVE |
| `tests/unittests/services/server/server-status.spec.ts` | `services/server/server-status.ts` | LIVE |
| `tests/unittests/services/settings/config.service.spec.ts` | `services/settings/config.service.ts` | LIVE |
| `tests/unittests/services/settings/config.spec.ts` | `services/settings/config.ts` | LIVE |
| `tests/unittests/services/utils/auth.interceptor.spec.ts` | `services/utils/auth.interceptor.ts` | LIVE |
| `tests/unittests/services/utils/confirm-modal.service.spec.ts` | `services/utils/confirm-modal.service.ts` | LIVE |
| `tests/unittests/services/utils/connected.service.spec.ts` | `services/utils/connected.service.ts` | LIVE |
| `tests/unittests/services/utils/dom.service.spec.ts` | `services/utils/dom.service.ts` | LIVE |
| `tests/unittests/services/utils/notification.service.spec.ts` | `services/utils/notification.service.ts` | LIVE |
| `tests/unittests/services/utils/rest.service.spec.ts` | `services/utils/rest.service.ts` | LIVE |
| `tests/unittests/services/utils/version-check.service.spec.ts` | `services/utils/version-check.service.ts` | LIVE |

**Verdict:** 40 LIVE, 0 STALE. Zero stale tests by D-01 definition.

### NG-02: Zero Test Files Deleted

No spec files were deleted in this plan. The removal inventory table above documents zero removals.

Previous removals (pre-existing, not in this plan): `file.component.spec.ts` and `file-list.component.spec.ts` removed in commit `103ace3` during Phase 72 (v1.1.0 UI redesign). Both tested `FileComponent` and `FileListComponent` which were deleted and replaced with `TransferRowComponent` and `TransferTableComponent`. The replacement components already have live specs (`transfer-row.component.spec.ts`, `transfer-table.component.spec.ts`).

### NG-03: ng test Exit Green

Command: `node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false`

Output (final lines):
```
Chrome Headless 147.0.0.0 (Mac OS 10.15.7): Executed 599 of 599 SUCCESS (1.049 secs / 0.994 secs)
TOTAL: 599 SUCCESS
```

**Exit code: 0**
**Failures: 0**

### D-05: Mock Orphan Check

Mocks directory: `src/angular/src/app/tests/mocks/` (7 files)

| Mock File | Imported By | Verdict |
|-----------|------------|---------|
| `mock-event-source.ts` | `base-stream.service.spec.ts`, `stream-service.registry.spec.ts` | LIVE |
| `mock-model-file.service.ts` | `dashboard-stats.service.spec.ts`, `view-file.service.spec.ts` | LIVE |
| `mock-rest.service.ts` | `version-check.service.spec.ts` | LIVE |
| `mock-storage.service.ts` | `view-file-options.service.spec.ts` | LIVE |
| `mock-stream-service.registry.ts` | `autoqueue.service.spec.ts`, `base-web.service.spec.ts`, `config.service.spec.ts`, `dashboard-stats.service.spec.ts`, `server-command.service.spec.ts`, `view-file.service.spec.ts` | LIVE |
| `mock-view-file-options.service.ts` | `view-file-filter.service.spec.ts`, `view-file-sort.service.spec.ts` | LIVE |
| `mock-view-file.service.ts` | `view-file-filter.service.spec.ts`, `view-file-sort.service.spec.ts` | LIVE |

**Verdict: Zero orphaned mocks.**

Note: The research document (84-RESEARCH.md) listed the mocks as being in `tests/unittests/mocks/` but the actual directory is `tests/mocks/`. The import cross-reference correctly resolved all mock imports to existing files.

## Requirements Addressed

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| NG-01 | Identify Angular test files/cases testing deleted components or superseded UI patterns | COMPLETE | Import cross-check of all 40 spec files: zero stale tests found (40 LIVE, 0 STALE) |
| NG-02 | Remove identified stale Angular tests without breaking the test suite | COMPLETE | Zero removals needed; no test files deleted; suite runs 599/599 green |
| NG-03 | Verify all remaining Angular tests pass | COMPLETE | `ng test --browsers ChromeHeadless --watch=false` exits 0: "TOTAL: 599 SUCCESS" |

## Files Created/Modified

- `.planning/phases/84-angular-test-audit/84-01-SUMMARY.md` — This audit summary with zero-removal inventory, coverage baseline, and verification evidence

## Decisions Made

None — followed plan as specified. The research finding of zero stale tests was independently confirmed by full import cross-reference.

## Deviations from Plan

None — plan executed exactly as written. The only transient change was adding `text-summary` reporter to karma.conf.js during Step 4 (coverage capture) and immediately reverting it. `git diff HEAD -- src/angular/karma.conf.js` confirms zero net diff.

## Issues Encountered

**Mock directory path mismatch:** The plan and 84-RESEARCH.md referenced mocks at `tests/unittests/mocks/` but the actual directory is `tests/mocks/`. The first orphan check attempt used the wrong path and returned no results. Fixed by using `find` to locate the actual mock files, then rerunning the check with the correct path `src/angular/src/app/tests/mocks/`. All 7 mock files were confirmed LIVE with correct paths.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Angular staleness audit complete with zero removals documented (D-06 inventory table)
- Coverage baseline recorded (D-09): Statements 83.34% / Branches 69.01% / Functions 79.73% / Lines 84.21%
- Ready for Plan 02 (CI noise cleanup): `HttpClientTestingModule` deprecation migration in 6 spec files (per D-07/D-08)
- The 6 files requiring `HttpClientTestingModule` → `provideHttpClient()` + `provideHttpClientTesting()` migration are: `autoqueue.service.spec.ts`, `bulk-command.service.spec.ts`, `config.service.spec.ts`, `model-file.service.spec.ts`, `rest.service.spec.ts`, `server-command.service.spec.ts`
- After Plan 02 completes, coverage "after" baseline should be captured and compared against these numbers (D-09 pair)

## Self-Check: PASSED

All claims verified:
- `84-01-SUMMARY.md` exists at `.planning/phases/84-angular-test-audit/84-01-SUMMARY.md`
- File contains "Removal Inventory" section with zero-removal table
- File contains "Coverage Baseline" section with Statements/Branches/Functions/Lines percentages
- File contains "NG-01" with import cross-check evidence for all 40 spec files
- File contains "NG-02" with evidence of zero test files deleted
- File contains "NG-03" with evidence of `ng test` exit green (599/599 SUCCESS)
- File contains "D-05" mock orphan check result (zero orphans, 7 mock files all LIVE)
- File contains "D-06" inventory table
- File contains "D-09" coverage baseline
- `ng test --browsers ChromeHeadless --watch=false` exited with 0 failures
- `git diff HEAD -- src/angular/karma.conf.js` confirms zero net changes to karma.conf.js

---
*Phase: 84-angular-test-audit*
*Completed: 2026-04-24*
