---
phase: 84-angular-test-audit
reviewed: 2026-04-24T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/angular/src/app/tests/unittests/services/autoqueue/autoqueue.service.spec.ts
  - src/angular/src/app/tests/unittests/services/files/model-file.service.spec.ts
  - src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts
  - src/angular/src/app/tests/unittests/services/server/server-command.service.spec.ts
  - src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts
  - src/angular/src/app/tests/unittests/services/utils/rest.service.spec.ts
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 84: Code Review Report

**Reviewed:** 2026-04-24T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

These six spec files were migrated from the deprecated `HttpClientTestingModule` to the
`provideHttpClient()` / `provideHttpClientTesting()` functional API. The migration is
structurally correct across all files: the old `imports` array entries have been replaced
with the two provider functions placed at the top of the `providers` array, and
`HttpTestingController` is still obtained via `TestBed.inject`. The HTTP mocking
mechanics work the same way under both APIs, and no test logic was broken in transit.

Three warnings identify reliability hazards that could cause tests to pass silently when
assertions are never reached. Three info items flag minor quality issues.

---

## Warnings

### WR-01: `afterEach(httpMock.verify())` missing in `autoqueue.service.spec.ts`

**File:** `src/angular/src/app/tests/unittests/services/autoqueue/autoqueue.service.spec.ts`
**Lines:** 20-465 (suite level)

**Issue:** `httpMock.verify()` is called manually at the end of every individual test that
uses HTTP, but there is no `afterEach(() => httpMock.verify())` guard. Any test that exits
early (for example, an unexpected exception before reaching `httpMock.verify()`) will
silently leave unexpected HTTP requests open and not fail the test. The pattern is also
brittle: adding a new test that omits the manual `verify()` call will go unnoticed.

By contrast, `bulk-command.service.spec.ts` (line 29-31) correctly uses `afterEach` for
this, which is the preferred pattern.

**Fix:** Add an `afterEach` at the describe-block level:

```typescript
afterEach(() => {
    httpMock.verify();
});
```

Then remove the per-test `httpMock.verify()` calls to avoid the redundant double-verify
(it works but is noisy on failures).

---

### WR-02: `afterEach(httpMock.verify())` missing in `config.service.spec.ts`

**File:** `src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts`
**Lines:** 21-342 (suite level)

**Issue:** Same structural problem as WR-01. `httpMock.verify()` is called inline in each
test, but there is no `afterEach` safety net. The suite is larger (14 tests) than the
autoqueue suite, making the manual discipline harder to maintain.

**Fix:**

```typescript
afterEach(() => {
    httpMock.verify();
});
```

---

### WR-03: `afterEach(httpMock.verify())` missing in `server-command.service.spec.ts`

**File:** `src/angular/src/app/tests/unittests/services/server/server-command.service.spec.ts`
**Lines:** 13-64 (suite level)

**Issue:** Only one HTTP-exercising test exists today ("should send a POST restart command",
line 47), and `httpMock.verify()` is called inline (line 62). If additional tests are
added later without a verify call, unexpected pending requests will go undetected.

**Fix:**

```typescript
afterEach(() => {
    httpMock.verify();
});
```

---

## Info

### IN-01: `BulkActionResult` constructor called without `errorStatus` argument in spec

**File:** `src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts`
**Lines:** 279-303

**Issue:** The unit tests for `BulkActionResult` (the `describe("BulkActionResult", ...)` block)
construct instances with three arguments: `(success, response, errorMessage)`. The
production class signature is `(success, response, errorMessage, errorStatus = null)`.
The fourth parameter has a default, so this compiles and runs correctly today. However, if
the test ever needs to exercise `isTransientFailure` (which depends on `errorStatus`), the
tests will need updating. The omission also means `isTransientFailure` is not covered by
this spec at all.

**Fix:** Either add coverage for `isTransientFailure`, or document explicitly that it is
tested elsewhere. Example:

```typescript
it("should treat network error (status 0) as transient", () => {
    const result = new BulkActionResult(false, null, "Network error", 0);
    expect(result.isTransientFailure).toBeTrue();
});

it("should treat 5xx as transient", () => {
    const result = new BulkActionResult(false, null, "Server error", 503);
    expect(result.isTransientFailure).toBeTrue();
});

it("should treat 4xx as non-transient", () => {
    const result = new BulkActionResult(false, null, "Bad request", 400);
    expect(result.isTransientFailure).toBeFalse();
});
```

---

### IN-02: `model-file.service.spec.ts` has no `afterEach(httpMock.verify())`  and `httpMock` is injected but never called with `verify()`

**File:** `src/angular/src/app/tests/unittests/services/files/model-file.service.spec.ts`
**Lines:** 33-36

**Issue:** `httpMock` is injected in `beforeEach` (line 33), which is correct. However,
most tests in this file operate via `notifyEvent` / `notifyConnected` / `notifyDisconnected`
rather than through the `HttpTestingController`, and there is no `afterEach(httpMock.verify())`
call. The tests that do use HTTP (`queue`, `stop`, `extract`, `deleteLocal`, `deleteRemote`)
each call `httpMock.verify()` individually (lines 387, 467, 546, 625, 704), but the tests
that do not issue HTTP requests are never verified. If a future change causes a test to
inadvertently trigger an HTTP call, it will not be caught.

**Fix:** Add `afterEach(() => httpMock.verify())` at the describe-block level so all tests
are uniformly covered.

---

### IN-03: `rest.service.spec.ts` imports `fakeAsync` but does not use it as a zone wrapper

**File:** `src/angular/src/app/tests/unittests/services/utils/rest.service.spec.ts`
**Line:** 1

**Issue:** `fakeAsync` is imported at line 1 but the tests call `httpMock.expectOne().flush()`
synchronously within a regular `it(...)` block — they are not wrapped in `fakeAsync(() => ...)`.
Flushing an `HttpTestingController` response is synchronous in the new `provideHttpClientTesting`
API (as it was with `HttpClientTestingModule`), so the tests work correctly. The unused import
is a leftover from migration scaffolding.

**Fix:** Remove `fakeAsync` from the import on line 1:

```typescript
// Before
import {fakeAsync, TestBed} from "@angular/core/testing";

// After
import {TestBed} from "@angular/core/testing";
```

---

_Reviewed: 2026-04-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
