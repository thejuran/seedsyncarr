---
phase: 90-angular-test-fixes
plan: 02
subsystem: angular-tests
tags: [angular, testing, subscription-leak, teardown]
dependency_graph:
  requires: []
  provides: [ANGFIX-03, ANGFIX-04, ANGFIX-05, ANGFIX-06]
  affects:
    - src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts
    - src/angular/src/app/tests/unittests/services/utils/notification.service.spec.ts
    - src/angular/src/app/tests/unittests/services/files/file-selection.service.spec.ts
    - src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts
tech_stack:
  added: []
  patterns: [per-test-subscription-teardown]
key_files:
  created: []
  modified:
    - src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts
    - src/angular/src/app/tests/unittests/services/utils/notification.service.spec.ts
    - src/angular/src/app/tests/unittests/services/files/file-selection.service.spec.ts
    - src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts
decisions: []
metrics:
  duration: 6m 26s
  completed: 2026-04-25T22:02:13Z
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
  tests_passed: 599
---

# Phase 90 Plan 02: Angular Subscription Leak Fixes Summary

Per-test subscription teardown added to 33 subscribe calls across 4 Angular spec files, matching the transfer-table.component.spec.ts gold-standard pattern (`const sub = ...; sub.unsubscribe()`).

## Task Summary

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Add subscription teardown to view-file.service.spec.ts and notification.service.spec.ts | 9ac7de5 | 20 teardowns in view-file, 7 in notification |
| 2 | Add subscription teardown to file-selection.service.spec.ts and transfer-row.component.spec.ts | 5dddfe5 | 4 teardowns in file-selection, 2 in transfer-row |

## Changes Made

### ANGFIX-03: view-file.service.spec.ts (20 subscribe calls)
- Added `const sub = ` prefix to all 20 `.subscribe()` calls across 20 test bodies
- Added `sub.unsubscribe()` as the last statement after final `expect()` in each test
- Covers: files observable (16 tests), filteredFiles observable (3 tests), FIX-01 regression tests (2 tests, nested in describe block)

### ANGFIX-04: notification.service.spec.ts (7 subscribe calls)
- Added `const sub = ` prefix to all 7 `.subscribe()` calls across 7 test bodies
- Added `sub.unsubscribe()` as the last statement after final `expect()` in each test
- Covers: show, hide, idempotent show/hide, level sort, timestamp sort, combined sort

### ANGFIX-05: file-selection.service.spec.ts (4 subscribe calls)
- Added `const sub = ` prefix to all 4 `.subscribe()` calls on signal-derived observables
- Added `sub.unsubscribe()` as the last statement after final `expect()` in each test
- Covers: selectedFiles$, selectedCount$, hasSelection$, no-change-no-emit

### ANGFIX-06: transfer-row.component.spec.ts (2 subscribe calls)
- Added `const sub = ` prefix to both EventEmitter `.subscribe()` calls
- Added `sub.unsubscribe()` as the last statement after final `expect()` in each test
- No `.complete()` called on EventEmitter (per D-05 constraint)
- Covers: checkboxToggle with shiftKey=false, checkboxToggle with shiftKey=true

## Verification

- `ng test --watch=false` for view-file.service.spec.ts + notification.service.spec.ts: 31/31 SUCCESS
- `ng test --watch=false` for file-selection.service.spec.ts + transfer-row.component.spec.ts: 80/80 SUCCESS
- Full Angular test suite: 599/599 SUCCESS
- grep counts: view-file 20, notification 7, file-selection 4, transfer-row 2 (total 33 `sub.unsubscribe()`)
- Zero bare `.subscribe()` without `const sub =` in modified files (excluding comments)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- [x] src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts: FOUND
- [x] src/angular/src/app/tests/unittests/services/utils/notification.service.spec.ts: FOUND
- [x] src/angular/src/app/tests/unittests/services/files/file-selection.service.spec.ts: FOUND
- [x] src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts: FOUND
- [x] Commit 9ac7de5: FOUND
- [x] Commit 5dddfe5: FOUND
