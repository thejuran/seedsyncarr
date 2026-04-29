# Phase 90: Angular Test Fixes - Research

**Researched:** 2026-04-25
**Domain:** Angular 21 / Karma-Jasmine unit test quality
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — user skipped discussion.

### Claude's Discretion
- D-01: Subscription teardown strategy for ANGFIX-03/04/05/06 — afterEach unsubscribe, per-test teardown, or DestroyRef pattern across 4 affected spec files
- D-02: fakeAsync cleanup scope for ANGFIX-01 — whether to add `discardPeriodicTasks()` only to the specific spec named or audit all 23 fakeAsync-using specs
- D-03: Optional chaining guard approach for ANGFIX-07 — `expect(result).toBeDefined()` before each chained assertion vs restructuring variable declarations
- D-04: Double-cast fix for ANGFIX-02 — use `ViewFileFilterCriteria | undefined` type annotation instead of `undefined as unknown as ViewFileFilterCriteria`
- D-05: EventEmitter leak + non-null assertion fix for ANGFIX-06 — cleanup pattern for transfer-row.component.spec.ts

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANGFIX-01 | Add `discardPeriodicTasks()` for never-completing observable in fakeAsync zone (ANG-10) | stream-service.registry.spec.ts calls `onInit()` in `beforeEach`, which starts a `setInterval` via `startTimeoutChecker()`. All 10 fakeAsync tests in that file leave this periodic task running. |
| ANGFIX-02 | Fix double-cast hiding nullable type — use `ViewFileFilterCriteria \| undefined` (ANG-04) | Line 30 of view-file-filter.service.spec.ts: `filterCriteria = undefined as unknown as ViewFileFilterCriteria`. Fix: declare as `ViewFileFilterCriteria \| undefined` and add null-guard before `meetsCriteria` assertions, or use `!` where test flow guarantees assignment. |
| ANGFIX-03 | Fix `view-file.service.spec.ts` missing subscription teardown (BUG-09) | 21 `.subscribe()` calls, zero afterEach/unsubscribe. Pattern: assign to local `sub` var inside each test, call `sub.unsubscribe()` at end. Matches transfer-table.component.spec.ts precedent. |
| ANGFIX-04 | Fix subscription leaks in `notification.service.spec.ts` — 7 occurrences (ANG-01) | 7 `.subscribe()` calls, zero afterEach/unsubscribe. Same per-test teardown pattern as ANGFIX-03. |
| ANGFIX-05 | Fix signal-derived observable subscription leaks in `file-selection.service.spec.ts` (ANG-02) | 4 `.subscribe()` calls on `selectedFiles$`, `selectedCount$`, `hasSelection$` observables (lines 267, 291, 314, 365). These are backed by `toObservable()` from Angular signals. Per-test unsubscribe is appropriate; `TestBed.flushEffects()` already used in these tests. |
| ANGFIX-06 | Fix EventEmitter leak + non-null assertion in `transfer-row.component.spec.ts` (ANG-03) | 2 `.subscribe()` calls on `component.checkboxToggle` (lines 198, 210) with no teardown. Emission variable accessed with `!` non-null assertion after optional subscribe. Fix: capture subscription, unsubscribe at end of each test body. |
| ANGFIX-07 | Add `expect(result).toBeDefined()` guards where optional chaining masks test gaps (ANG-05) | bulk-command.service.spec.ts has 31 instances of `result?.` optional chaining. One test (line 57) already has `expect(result).toBeDefined()` before chained assertions — this is the required pattern for all others. |
</phase_requirements>

---

## Summary

Phase 90 fixes 7 specific test quality defects in the Angular spec suite. The defects fall into four categories: (1) a pending `setInterval` left running in `fakeAsync` zones, (2) a type-erasure double-cast hiding nullable state, (3) subscription leaks in four spec files, and (4) optional chaining masking silent test gaps in the bulk-command service spec.

All affected files have been read directly from the codebase. Every finding below is `[VERIFIED]` against the source files — no assumptions needed for the implementation work.

The fixes are surgical: no production code changes, no new dependencies, no TestBed restructuring. Each fix is a localized edit to one spec file. The confirmed test command is `cd src/angular && ng test --watch=false`.

**Primary recommendation:** Use per-test `const sub = ...; ...; sub.unsubscribe()` teardown for all subscription leaks (matching the existing `transfer-table.component.spec.ts` pattern already in the codebase). Add `discardPeriodicTasks()` at the end of every fakeAsync test body in `stream-service.registry.spec.ts` (the only spec that calls `onInit()`). Change the double-cast to `ViewFileFilterCriteria | undefined`. Add `expect(result).toBeDefined()` before every `result?.` assertion block in `bulk-command.service.spec.ts`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Subscription teardown | Test layer | — | Spec files own their own cleanup; production observables are not changed |
| fakeAsync zone hygiene | Test layer | — | `discardPeriodicTasks()` is a test-only API; production `setInterval` stays |
| Type correctness (ANGFIX-02) | Test layer | — | Only the test's local variable declaration is wrong; no production type changes |
| Optional-chain test guards | Test layer | — | Strengthening test assertions; `BulkActionResult` interface unchanged |

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| @angular/core/testing | 21.2.x | `fakeAsync`, `tick`, `discardPeriodicTasks`, `flush`, `TestBed.flushEffects` | `[VERIFIED: package.json]` |
| jasmine-core | 6.2.0 | `expect`, `toBeDefined`, `describe`, `it`, `beforeEach`, `afterEach` | `[VERIFIED: package.json]` |
| karma | 6.4.4 | Test runner: `ng test --watch=false` | `[VERIFIED: package.json]` |

**No new packages to install.** All APIs used are already in the existing test infrastructure.

---

## Architecture Patterns

### System Architecture Diagram

```
ng test --watch=false
    └─► Karma runner
            └─► Jasmine test executor
                    ├─► stream-service.registry.spec.ts
                    │       └─► beforeEach: onInit() starts setInterval (ANGFIX-01 source)
                    │           fakeAsync tests exit with pending periodic task
                    │           FIX: discardPeriodicTasks() at end of each fakeAsync test
                    │
                    ├─► view-file-filter.service.spec.ts
                    │       └─► filterCriteria = undefined as unknown as ViewFileFilterCriteria
                    │           FIX: declare as ViewFileFilterCriteria | undefined (ANGFIX-02)
                    │
                    ├─► view-file.service.spec.ts (ANGFIX-03)
                    ├─► notification.service.spec.ts (ANGFIX-04)
                    ├─► file-selection.service.spec.ts (ANGFIX-05)
                    └─► transfer-row.component.spec.ts (ANGFIX-06)
                            └─► .subscribe() calls without teardown
                                FIX: per-test const sub = ...; sub.unsubscribe()
                    └─► bulk-command.service.spec.ts (ANGFIX-07)
                            └─► result?.property — silent pass if result is undefined
                                FIX: expect(result).toBeDefined() before chained assertions
```

### Recommended Project Structure
No structural changes. All edits are in-place within existing spec files.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Discard periodic timers in fakeAsync | Custom interval cleanup helper | `discardPeriodicTasks()` from `@angular/core/testing` | Built-in API; already imported in all fakeAsync files |
| Observable teardown in tests | Custom cleanup service | Per-test `sub.unsubscribe()` | Simplest, zero-overhead, matches existing codebase pattern |
| Null-safe test assertions | Custom guard wrapper | `expect(result).toBeDefined()` | Standard Jasmine; one line per test block |

---

## Detailed Findings by Requirement

### ANGFIX-01: fakeAsync zone cleanup — stream-service.registry.spec.ts

**Root cause:** `[VERIFIED: codebase read]`
- `StreamDispatchService.onInit()` calls `startTimeoutChecker()` which runs `setInterval(..., 5000)` (TIMEOUT_CHECK_INTERVAL_MS).
- `stream-service.registry.spec.ts` calls `dispatchService.onInit()` inside `beforeEach(fakeAsync(...))` at line 66.
- All 10 `fakeAsync` test bodies in this file exit without discarding the periodic interval, leaving it in the fake zone.
- Angular's `fakeAsync` zone throws "1 timer(s) still in the queue" if periodic tasks are pending when the zone exits.

**Fix:** `[VERIFIED: Angular docs pattern]`
```typescript
// Import at top
import {fakeAsync, TestBed, tick, discardPeriodicTasks} from "@angular/core/testing";

// At end of each fakeAsync test body in stream-service.registry.spec.ts:
discardPeriodicTasks();
```

**Scope decision (D-02):** The `setInterval` originates from `StreamDispatchService.onInit()`, which is ONLY called in `stream-service.registry.spec.ts`. The other 13 fakeAsync spec files do not instantiate `StreamDispatchService` or call `onInit()`. Therefore `discardPeriodicTasks()` is only needed in `stream-service.registry.spec.ts`. The `beforeEach` itself is `fakeAsync` — it also needs `discardPeriodicTasks()` at its end.

**Count:** 1 `beforeEach(fakeAsync(...))` + 10 `it(..., fakeAsync(...))` = 11 locations in `stream-service.registry.spec.ts`.

---

### ANGFIX-02: Double-cast fix — view-file-filter.service.spec.ts

**Root cause:** `[VERIFIED: codebase read, line 30]`
```typescript
filterCriteria = undefined as unknown as ViewFileFilterCriteria;  // Reset before each test
```
The double-cast `undefined as unknown as ViewFileFilterCriteria` tells TypeScript the variable holds a valid `ViewFileFilterCriteria` when it actually holds `undefined`. If a test accessing `filterCriteria.meetsCriteria(...)` runs before the service populates the variable, TypeScript won't warn and the test will throw at runtime rather than fail with a clear assertion error.

**Fix (D-04):** Change the local variable declaration type:
```typescript
// Before (line 17-ish area):
let filterCriteria: ViewFileFilterCriteria;

// After:
let filterCriteria: ViewFileFilterCriteria | undefined;

// And the reset at line 30:
filterCriteria = undefined;  // No cast needed
```
Where the test code calls `filterCriteria.meetsCriteria(...)`, TypeScript will now require a null-guard or non-null assertion. Since each test that uses `filterCriteria` has already called `tick()` which populates it via the `setFilterCriteria` spy, using `filterCriteria!.meetsCriteria(...)` is safe and correct.

---

### ANGFIX-03/04/05/06: Subscription teardown strategy (D-01)

**Decision:** Per-test `sub.unsubscribe()` at end of each test body. `[VERIFIED: transfer-table.component.spec.ts precedent]`

**Rationale:** The existing codebase already uses this pattern in `transfer-table.component.spec.ts` (lines 258, 281, 300, 307, 328, etc.). An `afterEach` approach is more abstract but would require adding a shared `let sub` variable per `describe` block and conditionally calling unsubscribe — adding indirection for no benefit. `DestroyRef` is for production code, not spec teardown.

**Pattern:**
```typescript
// Per test with a single subscription:
it("should emit on selectedFiles$ when selection changes", () => {
    const emissions: Set<string>[] = [];
    const sub = service.selectedFiles$.subscribe(files => {
        emissions.push(files);
    });
    TestBed.flushEffects();
    // ... assertions ...
    sub.unsubscribe();
});
```

**For tests with multiple subscriptions (transfer-table precedent):**
```typescript
const sub1 = service.someObs$.subscribe(...);
const sub2 = service.anotherObs$.subscribe(...);
// ... assertions ...
sub1.unsubscribe();
sub2.unsubscribe();
```

#### ANGFIX-03: view-file.service.spec.ts

**Finding:** `[VERIFIED: codebase read]`
- 21 `.subscribe()` calls across 16 test bodies.
- Many tests subscribe to `viewService.files` or `viewService.filteredFiles` inside `fakeAsync` blocks.
- The subscriptions are currently let to leak because `fakeAsync` zones close synchronously after `tick()` — the subscription stays open but becomes garbage-collectible only if nothing else holds a reference.
- In Karma with Jasmine, leaking subscriptions across tests can cause cross-test contamination where a late emission from a prior test's observable fires into a subsequent test.

**Count:** 21 subscribe calls across 16 `it()` blocks. Each gets `const sub = ...; sub.unsubscribe()` treatment.

#### ANGFIX-04: notification.service.spec.ts

**Finding:** `[VERIFIED: codebase read]`
- 7 `.subscribe()` calls on `notificationService.notifications`.
- All 7 are inside `fakeAsync` blocks.
- No `afterEach`, no cleanup.

**Count:** 7 subscribe calls in 7 `it()` blocks.

#### ANGFIX-05: file-selection.service.spec.ts

**Finding:** `[VERIFIED: codebase read]`
- 4 `.subscribe()` calls on signal-derived observables: `selectedFiles$` (lines 267, 365), `selectedCount$` (line 291), `hasSelection$` (line 314).
- These observables are created via `toObservable()` which uses Angular's effect system. `TestBed.flushEffects()` is already called in these tests.
- The 4 tests with subscriptions are NOT inside `fakeAsync` — they use synchronous `TestBed.flushEffects()` instead.
- Teardown: `sub.unsubscribe()` at the end of each test body, after the final assertion.

**Count:** 4 subscribe calls in 4 `it()` blocks.

#### ANGFIX-06: transfer-row.component.spec.ts

**Finding:** `[VERIFIED: codebase read]`
- 2 `.subscribe()` calls on `component.checkboxToggle` EventEmitter (lines 198, 210).
- `component.checkboxToggle` is `new EventEmitter<{file: ViewFile, shiftKey: boolean}>()` in the production component.
- After subscribe, `emission` is accessed via non-null assertion `emission!.file` and `emission!.shiftKey`.
- These tests are NOT `fakeAsync` — they're synchronous.
- Fix: `const sub = component.checkboxToggle.subscribe(e => emission = e); ...; sub.unsubscribe();`

**Count:** 2 subscribe calls in 2 `it()` blocks.

---

### ANGFIX-07: Optional chaining guards — bulk-command.service.spec.ts

**Finding:** `[VERIFIED: codebase read]`
- `result` is declared as `BulkActionResult | undefined` at the top of each test.
- 31 instances of `result?.property` optional chaining.
- If `result` is `undefined` (observable never emitted, tick() didn't advance enough, etc.), every `result?.property` assertion silently passes by evaluating to `undefined` — Jasmine's `toBeTrue()` on `undefined` would be a false pass.
- One test (lines 57-60) already has the correct pattern: `expect(result).toBeDefined()` before the chained assertions.
- 8 test blocks lack this guard.

**Fix (D-03):** Add `expect(result).toBeDefined();` as the first assertion after `tick()` in each test block. No need to restructure variable declarations.

**Test blocks that need guards:** `[VERIFIED: codebase read]`
1. Lines 64-88: "should handle successful response with all files succeeded"
2. Lines 90-120: "should handle partial failure response"
3. Lines 122-144: "should handle all files failed response"
4. Lines 146-163: "should handle HTTP 400 error with JSON error body"
5. Lines 165-181: "should handle HTTP 400 error with invalid files array"
6. Lines 183-197: "should handle network error"
7. Lines 199-215: "should handle string error response"

(The `testActions.forEach` tests at lines 37-61 already have `expect(result).toBeDefined()` on line 57.)

---

## Common Pitfalls

### Pitfall 1: Forgetting the beforeEach fakeAsync for ANGFIX-01
**What goes wrong:** Only adding `discardPeriodicTasks()` to `it(...)` blocks but forgetting `beforeEach(fakeAsync(...))` at line 43 — the beforeEach also calls `onInit()` and `tick()` leaving the interval in the zone.
**How to avoid:** Add `discardPeriodicTasks()` before closing brace of `beforeEach(fakeAsync(...))` at line 67 as well.

### Pitfall 2: Using afterEach instead of per-test unsubscribe for mixed fakeAsync/non-fakeAsync specs
**What goes wrong:** Some tests in `view-file.service.spec.ts` are `fakeAsync`, others (like "should clear bulk selection when filter criteria changes") are also `fakeAsync` but the subscription isn't to an async stream. A shared `afterEach` variable would need careful typing.
**How to avoid:** Per-test teardown is always safe and is already the project pattern.

### Pitfall 3: Ordering unsubscribe before assertions in view-file tests
**What goes wrong:** Calling `sub.unsubscribe()` before the final `expect(count).toBe(N)` assertion means if the count is wrong, unsubscribe has already occurred, making debug harder.
**How to avoid:** Place `sub.unsubscribe()` after all assertions, at the very end of the test body.

### Pitfall 4: filterCriteria non-null assertion in ANGFIX-02
**What goes wrong:** After changing the type to `ViewFileFilterCriteria | undefined`, TypeScript will flag `filterCriteria.meetsCriteria(...)` as a compile error. Must add `!` or a null-check.
**How to avoid:** Use `filterCriteria!.meetsCriteria(...)` since by the point of use, `tick()` has already populated it via the spy.

### Pitfall 5: Double-unsubscribe on EventEmitter in ANGFIX-06
**What goes wrong:** `EventEmitter` extends `Subject` — calling `complete()` on it would break subsequent tests. Do not call `.complete()`, only `.unsubscribe()` on the subscription object.
**How to avoid:** `const sub = component.checkboxToggle.subscribe(...); ...; sub.unsubscribe();` — only the subscription is unsubscribed, not the emitter itself.

---

## Code Examples

### fakeAsync zone cleanup (ANGFIX-01)
```typescript
// Source: [VERIFIED: Angular @angular/core/testing API]
import {fakeAsync, TestBed, tick, discardPeriodicTasks} from "@angular/core/testing";

beforeEach(fakeAsync(() => {
    // ... setup ...
    dispatchService.onInit();
    tick();
    discardPeriodicTasks();  // ADD: discard the setInterval from startTimeoutChecker()
}));

it("should forward name and data correctly", fakeAsync(() => {
    // ... test body ...
    tick();
    discardPeriodicTasks();  // ADD: at end of every fakeAsync it() body
}));
```

### Per-test subscription teardown (ANGFIX-03/04/05/06)
```typescript
// Source: [VERIFIED: transfer-table.component.spec.ts lines 255-264, existing codebase pattern]
it("should show notification", fakeAsync(() => {
    const expectedNotification = new Notification({level: Notification.Level.DANGER, text: "danger"});
    notificationService.show(expectedNotification);

    let actualCount = 0;
    const sub = notificationService.notifications.subscribe({
        next: list => {
            expect(list.size).toBe(1);
            actualCount++;
        }
    });

    tick();
    expect(actualCount).toBe(1);
    sub.unsubscribe();  // ADD
}));
```

### Double-cast fix (ANGFIX-02)
```typescript
// Source: [VERIFIED: codebase read, view-file-filter.service.spec.ts line 30]
// BEFORE:
let filterCriteria: ViewFileFilterCriteria;
// ...
filterCriteria = undefined as unknown as ViewFileFilterCriteria;

// AFTER:
let filterCriteria: ViewFileFilterCriteria | undefined;
// ...
filterCriteria = undefined;  // plain reset, no cast

// At usage sites, add ! since tick() guarantees assignment:
expect(filterCriteria!.meetsCriteria(new ViewFile({name: "tofu"}))).toBe(true);
```

### toBeDefined guard (ANGFIX-07)
```typescript
// Source: [VERIFIED: bulk-command.service.spec.ts lines 57-60, existing pattern to propagate]
tick();

expect(result).toBeDefined();          // ADD this guard
expect(result?.success).toBeTrue();
expect(result?.allSucceeded).toBeTrue();
expect(result?.response?.summary.succeeded).toBe(2);
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `undefined as unknown as T` | `T \| undefined` type declaration | TypeScript catches null-dereference at compile time |
| Leaked subscriptions in tests | Per-test `sub.unsubscribe()` | Prevents cross-test emission contamination |
| No `discardPeriodicTasks()` | `discardPeriodicTasks()` at fakeAsync exit | Eliminates "N timer(s) still in the queue" zone warnings |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Karma 6.4.4 + Jasmine 6.2.0 |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `cd src/angular && ng test --watch=false --include="**/stream-service.registry.spec.ts"` |
| Full suite command | `cd src/angular && ng test --watch=false` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANGFIX-01 | No pending timer warnings from fakeAsync zones | unit | `ng test --watch=false` | Yes |
| ANGFIX-02 | No double-cast hiding nullable type | unit (TypeScript compile) | `ng test --watch=false` | Yes |
| ANGFIX-03 | view-file.service.spec.ts has teardown | unit | `ng test --watch=false` | Yes |
| ANGFIX-04 | notification.service.spec.ts has teardown | unit | `ng test --watch=false` | Yes |
| ANGFIX-05 | file-selection.service.spec.ts has teardown | unit | `ng test --watch=false` | Yes |
| ANGFIX-06 | transfer-row.component.spec.ts has teardown | unit | `ng test --watch=false` | Yes |
| ANGFIX-07 | toBeDefined guards before optional chaining | unit | `ng test --watch=false` | Yes |

### Sampling Rate
- **Per task commit:** `cd src/angular && ng test --watch=false` (full suite, 599 tests)
- **Per wave merge:** Full suite green
- **Phase gate:** Full suite green with zero subscription leak warnings before `/gsd-verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. No new test files needed. All work is edits to existing spec files.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | `ng test` | Yes | Darwin host | — |
| Angular CLI | `ng test --watch=false` | Yes (local) | 21.2.x | `npx ng test` |
| Karma/Chrome | Test runner | Yes | Karma 6.4.4 | — |

---

## Assumptions Log

No assumed claims — all findings in this research are `[VERIFIED]` against codebase reads.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims were verified by direct codebase inspection. No user confirmation needed.**

---

## Open Questions

None. All 7 requirements have clear, verified fixes with no ambiguity.

---

## Sources

### Primary (HIGH confidence — verified by direct codebase read)
- `src/angular/src/app/services/base/stream-service.registry.ts` — `setInterval` in `startTimeoutChecker()`, `onInit()` entry point
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` — 10 fakeAsync tests, `beforeEach` calls `onInit()`
- `src/angular/src/app/tests/unittests/services/files/view-file-filter.service.spec.ts` — line 30 double-cast
- `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts` — 21 subscribe calls, 0 teardown
- `src/angular/src/app/tests/unittests/services/utils/notification.service.spec.ts` — 7 subscribe calls, 0 teardown
- `src/angular/src/app/tests/unittests/services/files/file-selection.service.spec.ts` — 4 signal-observable subscribe calls, 0 teardown
- `src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts` — 2 EventEmitter subscribe calls, 0 teardown
- `src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts` — 31 optional chaining assertions, only 1 test has `toBeDefined` guard
- `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` — existing per-test `sub.unsubscribe()` pattern (gold standard)
- `src/angular/package.json` — Angular 21.2.x, Karma 6.4.4, Jasmine 6.2.0

---

## Metadata

**Confidence breakdown:**
- Subscription leak locations: HIGH — verified by direct file read and grep counts
- fakeAsync periodic task source: HIGH — traced from spec → `onInit()` → `startTimeoutChecker()` → `setInterval`
- Teardown pattern choice: HIGH — exact pattern exists in transfer-table.component.spec.ts
- Optional chaining gap analysis: HIGH — count verified by grep, one existing guard identified
- Double-cast root cause: HIGH — line 30 read directly

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (stable domain — Angular test APIs don't change between patch releases)
