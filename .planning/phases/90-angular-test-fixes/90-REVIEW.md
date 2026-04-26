---
phase: 90-angular-test-fixes
reviewed: 2026-04-26T01:38:54Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts
  - src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts
  - src/angular/src/app/tests/unittests/services/files/file-selection.service.spec.ts
  - src/angular/src/app/tests/unittests/services/files/view-file-filter.service.spec.ts
  - src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts
  - src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts
  - src/angular/src/app/tests/unittests/services/utils/notification.service.spec.ts
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 90: Code Review Report

**Reviewed:** 2026-04-26T01:38:54Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Seven Angular unit test files were reviewed at standard depth. The test suites are well-structured with comprehensive coverage across component rendering, service state management, HTTP interactions, and observable/signal-based reactivity. Tests properly use Angular TestBed, fakeAsync/tick, and HttpTestingController patterns.

One warning was found: incorrect inline comments in a test that could mislead future maintainers. Three informational items were identified: a large block of commented-out test code, a potentially misleading RED-target label on a test that should pass with current production code, and an empty subclass used as a test shim.

Overall quality is high. No security or correctness bugs were found in the test logic itself.

## Warnings

### WR-01: Stale comments misidentify EXTRACTING and EXTRACTED state transitions as "DELETED"

**File:** `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts:197-203`
**Issue:** Two consecutive state-transition comments on lines 197 and 203 both read `// Next state - DELETED`, but the code actually sets `ModelFile.State.EXTRACTING` (line 198) and `ModelFile.State.EXTRACTED` (line 203). This directly contradicts the `expectedStates` array at lines 139-140 which correctly lists `ViewFile.Status.EXTRACTING` and `ViewFile.Status.EXTRACTED` for indices 6 and 7. A developer trusting the comments during debugging or modification could introduce a real logic error.
**Fix:**
```typescript
// Line 197: change from
// Next state - DELETED
// to
// Next state - EXTRACTING

// Line 203: change from
// Next state - DELETED
// to
// Next state - EXTRACTED
```

## Info

### IN-01: Large commented-out test block (55 lines)

**File:** `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts:456-510`
**Issue:** A full test case (`should sort view files by status then name`) is commented out with `//`. It spans 55 lines and uses `any` types. The test appears to be superseded by the separate sort tests starting at line 827. Dead commented-out code increases cognitive load and makes maintenance harder.
**Fix:** Remove the commented-out block entirely. If the sort-by-status-then-name behavior is important, the active sort tests at lines 827-945 already cover sorting behavior. If this specific ordering needs coverage, write a fresh test without the `any` types.

### IN-02: Potentially misleading RED-target comment on passing test

**File:** `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts:1022-1057`
**Issue:** The block comment at lines 1002-1021 and the test name on line 1023 describe this as a "RED target" -- a test that is expected to fail. However, cross-referencing the production code in `view-file.service.ts` line 348, the `isQueueable` predicate is: `status === ViewFile.Status.DELETED || ([...DEFAULT, STOPPED...].includes(status) && remoteSize > 0)`. The `DELETED` branch evaluates `true` via short-circuit regardless of `remoteSize`, meaning this test should pass with the current code. If the fix described in the comment (Wave 2, D-02) has already been applied, the RED label is now stale and misleading. If the test is genuinely still red, the issue is elsewhere.
**Fix:** If the test passes, update the test name and surrounding comments to remove the "(RED target)" label and "Wave 1 commits these red" narrative. The characterization history can be preserved in git log or planning docs rather than inline comments that become inaccurate.

### IN-03: Empty subclass used as test shim

**File:** `src/angular/src/app/tests/unittests/services/utils/notification.service.spec.ts:9-11`
**Issue:** `TestNotificationService` extends `NotificationService` without adding any members or overrides. It is used as the DI provider for the test. While this works fine, it adds a layer of indirection with no purpose. If the original class has constructor constraints that require a subclass shim, a comment explaining why would be helpful.
**Fix:** If `NotificationService` can be injected directly (it appears to be a standard injectable), simplify the provider to use the class itself. Otherwise, add a brief comment explaining why the subclass exists.

---

_Reviewed: 2026-04-26T01:38:54Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
