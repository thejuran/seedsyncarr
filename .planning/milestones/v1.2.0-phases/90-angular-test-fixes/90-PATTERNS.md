# Phase 90: Angular Test Fixes - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 6 modified spec files
**Analogs found:** 6 / 6

---

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` | test | event-driven | self (edit in place) | exact |
| `src/angular/src/app/tests/unittests/services/files/view-file-filter.service.spec.ts` | test | CRUD | self (edit in place) | exact |
| `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts` | test | CRUD | `transfer-table.component.spec.ts` | role-match |
| `src/angular/src/app/tests/unittests/services/utils/notification.service.spec.ts` | test | event-driven | `transfer-table.component.spec.ts` | role-match |
| `src/angular/src/app/tests/unittests/services/files/file-selection.service.spec.ts` | test | event-driven | `transfer-table.component.spec.ts` | role-match |
| `src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts` | test | event-driven | `transfer-table.component.spec.ts` | exact |
| `src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts` | test | request-response | self (existing guard pattern at line 57 to propagate) | exact |

---

## Pattern Assignments

### ANGFIX-01: `stream-service.registry.spec.ts` — fakeAsync zone cleanup

**Fix:** Add `discardPeriodicTasks()` at the end of every `fakeAsync` block (1 `beforeEach` + 10 `it` bodies).

**Root cause location** (lines 43–68): `beforeEach(fakeAsync(...))` calls `dispatchService.onInit()` at line 66, which starts a `setInterval` via `startTimeoutChecker()`. Every fakeAsync block that exits without discarding it leaves the zone dirty.

**Import change** (line 1 — current):
```typescript
import {fakeAsync, TestBed, tick} from "@angular/core/testing";
```

**Import change** (after fix):
```typescript
import {fakeAsync, TestBed, tick, discardPeriodicTasks} from "@angular/core/testing";
```

**beforeEach pattern** (lines 43–68 — after fix):
```typescript
beforeEach(fakeAsync(() => {
    // ... all existing setup ...
    dispatchService.onInit();
    tick();
    discardPeriodicTasks();  // ADD: discard setInterval from startTimeoutChecker()
}));
```

**it() pattern** (representative — e.g. lines 74–87 — after fix):
```typescript
it("should construct an event source with correct url", fakeAsync(() => {
    expect(mockEventSource.url).toBe("/server/stream");
    discardPeriodicTasks();  // ADD: at end of every fakeAsync it() body
}));
```

**Scope:** Only `stream-service.registry.spec.ts`. The `setInterval` originates from `StreamDispatchService.onInit()`, which is called in no other spec file. The other 13 fakeAsync spec files do not instantiate `StreamDispatchService`.

---

### ANGFIX-02: `view-file-filter.service.spec.ts` — double-cast fix

**Fix:** Change the `filterCriteria` variable declaration from a lying type to a truthful union type, remove the double-cast reset, and add `!` non-null assertions at usage sites.

**Current state** (lines 18 and 30):
```typescript
let filterCriteria: ViewFileFilterCriteria;          // line 18 — declared as non-nullable
// ...
filterCriteria = undefined as unknown as ViewFileFilterCriteria;  // line 30 — double-cast reset
```

**After fix** (lines 18 and 30):
```typescript
let filterCriteria: ViewFileFilterCriteria | undefined;   // truthful union type
// ...
filterCriteria = undefined;  // plain reset, no cast needed
```

**Usage site pattern** — wherever `filterCriteria.meetsCriteria(...)` is called after a `tick()` that guarantees population (lines 96–116, 96–136, 143–153, 202–249, 260–279):
```typescript
// Before:
expect(filterCriteria.meetsCriteria(new ViewFile({name: "tofu"}))).toBe(true);

// After:
expect(filterCriteria!.meetsCriteria(new ViewFile({name: "tofu"}))).toBe(true);
```

The `!` is safe because in every test that calls `meetsCriteria`, `tick()` has already fired the options spy which populates `filterCriteria` via `spyOn(viewFileService, "setFilterCriteria").and.callFake(value => filterCriteria = value)`.

---

### ANGFIX-03: `view-file.service.spec.ts` — subscription teardown

**Gold-standard analog:** `transfer-table.component.spec.ts` lines 255–262:
```typescript
let pagedFiles: ViewFile[] = [];
const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
tick();
sub.unsubscribe();
```

**Pattern to apply to all 21 subscribe calls across 16 test bodies:**

```typescript
// Single-subscription test (current — no teardown):
it("should forward an empty model by default", fakeAsync(() => {
    let count = 0;
    viewService.files.subscribe({
        next: list => {
            expect(list.size).toBe(0);
            count++;
        }
    });
    tick();
    expect(count).toBe(1);
}));

// After fix — assign to sub, unsubscribe last:
it("should forward an empty model by default", fakeAsync(() => {
    let count = 0;
    const sub = viewService.files.subscribe({
        next: list => {
            expect(list.size).toBe(0);
            count++;
        }
    });
    tick();
    expect(count).toBe(1);
    sub.unsubscribe();  // ADD: always last, after all assertions
}));
```

**Ordering rule** (from RESEARCH.md Pitfall 3): `sub.unsubscribe()` goes after all `expect(...)` assertions, as the very last statement in the test body.

---

### ANGFIX-04: `notification.service.spec.ts` — subscription teardown

**Gold-standard analog:** Same transfer-table pattern. 7 subscribe calls across 7 `it()` blocks, all inside `fakeAsync`. No `afterEach` changes needed.

**Current pattern** (representative — lines 37–47):
```typescript
let actualCount = 0;
notificationService.notifications.subscribe({
    next: list => {
        expect(list.size).toBe(1);
        expect(Immutable.is(expectedNotification, list.get(0))).toBe(true);
        actualCount++;
    }
});
tick();
expect(actualCount).toBe(1);
```

**After fix:**
```typescript
let actualCount = 0;
const sub = notificationService.notifications.subscribe({
    next: list => {
        expect(list.size).toBe(1);
        expect(Immutable.is(expectedNotification, list.get(0))).toBe(true);
        actualCount++;
    }
});
tick();
expect(actualCount).toBe(1);
sub.unsubscribe();  // ADD
```

**Note:** Test at lines 82–86 subscribes and then calls `notificationService.show(expectedNotification)` and `tick()` after subscription. `sub.unsubscribe()` goes after the final `expect(actualCount).toBe(1)`.

---

### ANGFIX-05: `file-selection.service.spec.ts` — signal-observable subscription teardown

**Context:** 4 subscribe calls on signal-derived observables (`selectedFiles$`, `selectedCount$`, `hasSelection$`). These tests are NOT `fakeAsync` — they use `TestBed.flushEffects()` instead. No `tick()` is present.

**Current pattern** (lines 264–286):
```typescript
it("should emit on selectedFiles$ when selection changes", () => {
    const emissions: Set<string>[] = [];
    service.selectedFiles$.subscribe(files => {
        emissions.push(files);
    });
    TestBed.flushEffects();
    // ... assertions ...
    service.deselect("file1");
    TestBed.flushEffects();
    expect(emissions.length).toBe(3);
    expect(emissions[2].size).toBe(0);
});
```

**After fix:**
```typescript
it("should emit on selectedFiles$ when selection changes", () => {
    const emissions: Set<string>[] = [];
    const sub = service.selectedFiles$.subscribe(files => {
        emissions.push(files);
    });
    TestBed.flushEffects();
    // ... assertions ...
    service.deselect("file1");
    TestBed.flushEffects();
    expect(emissions.length).toBe(3);
    expect(emissions[2].size).toBe(0);
    sub.unsubscribe();  // ADD: after final assertion
});
```

Apply same pattern to lines 288–309 (`selectedCount$`), 311–332 (`hasSelection$`), and 362–378 (second `selectedFiles$` occurrence).

---

### ANGFIX-06: `transfer-row.component.spec.ts` — EventEmitter subscription teardown + non-null assertion

**Current state** (lines 195–216):
```typescript
it("emits checkboxToggle with shiftKey=false on plain click", () => {
    setFile(ViewFile.Status.DEFAULT, {name: "gamma.mkv"});
    let emission: {file: ViewFile, shiftKey: boolean} | null = null;
    component.checkboxToggle.subscribe(e => emission = e);   // no teardown

    component.onCheckboxClick(new MouseEvent("click", {shiftKey: false}));

    expect(emission).not.toBeNull();
    expect(emission!.file).toBe(component.file);    // non-null assertion safe here
    expect(emission!.shiftKey).toBe(false);
});
```

**After fix:**
```typescript
it("emits checkboxToggle with shiftKey=false on plain click", () => {
    setFile(ViewFile.Status.DEFAULT, {name: "gamma.mkv"});
    let emission: {file: ViewFile, shiftKey: boolean} | null = null;
    const sub = component.checkboxToggle.subscribe(e => emission = e);  // ADD const sub

    component.onCheckboxClick(new MouseEvent("click", {shiftKey: false}));

    expect(emission).not.toBeNull();
    expect(emission!.file).toBe(component.file);
    expect(emission!.shiftKey).toBe(false);
    sub.unsubscribe();  // ADD: after assertions, only unsubscribe the subscription — never call .complete() on the EventEmitter
});
```

**Critical rule** (from RESEARCH.md Pitfall 5): Do NOT call `component.checkboxToggle.complete()`. `EventEmitter` extends `Subject` — completing it would break subsequent tests. Only `.unsubscribe()` on the `sub` object.

Apply to both test bodies at lines 195–205 and 207–216.

---

### ANGFIX-07: `bulk-command.service.spec.ts` — `toBeDefined` guards before optional chaining

**Existing correct pattern** (lines 56–60 — the template to copy):
```typescript
tick();

expect(result).toBeDefined();          // guard already present
expect(result?.success).toBeTrue();
expect(result?.allSucceeded).toBeTrue();
expect(result?.response?.summary.succeeded).toBe(2);
```

**Current broken pattern** (representative — lines 80–88):
```typescript
tick();

// NO guard — if result is undefined, all assertions silently pass
expect(result?.success).toBeTrue();
expect(result?.allSucceeded).toBeTrue();
expect(result?.hasPartialFailure).toBeFalse();
```

**After fix:**
```typescript
tick();

expect(result).toBeDefined();          // ADD this line before first result?. assertion
expect(result?.success).toBeTrue();
expect(result?.allSucceeded).toBeTrue();
expect(result?.hasPartialFailure).toBeFalse();
```

**7 test blocks needing this guard** (all inside the `executeBulkAction` describe block):
1. "should handle successful response with all files succeeded" — add guard after `tick()` at ~line 80
2. "should handle partial failure response" — add guard after `tick()` at ~line 108
3. "should handle all files failed response" — add guard after `tick()` at ~line 138
4. "should handle HTTP 400 error with JSON error body" — add guard after `tick()` at ~line 160
5. "should handle HTTP 400 error with invalid files array" — add guard after `tick()` at ~line 177
6. "should handle network error" — add guard after `tick()` at ~line 193
7. "should handle string error response" — add guard after `tick()` at ~line 211

The `testActions.forEach` block (lines 37–61) already has `expect(result).toBeDefined()` on line 57 — do not modify it.

---

## Shared Patterns

### Pattern A: Per-test subscription teardown
**Source:** `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` lines 255–262, 279–281, 298–300, 305–307
**Apply to:** ANGFIX-03, ANGFIX-04, ANGFIX-05, ANGFIX-06

```typescript
// Gold standard from transfer-table.component.spec.ts (lines 255-262):
let pagedFiles: ViewFile[] = [];
const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
tick();
sub.unsubscribe();

// Multiple subscriptions in one test (lines 304-309):
const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
tick();
sub.unsubscribe();

let totalPages = 0;
const totalSub = component.totalPages$.subscribe(t => totalPages = t);
tick();
totalSub.unsubscribe();
```

**Rules:**
- Always name: `const sub = ...subscribe(...)` (or `sub1`, `sub2` for multiples)
- Never use `afterEach` — per-test is the project standard
- Always place `sub.unsubscribe()` after the last `expect(...)` in the test body
- For `EventEmitter` subscriptions: only unsubscribe `sub`, never call `.complete()` on the emitter

### Pattern B: fakeAsync zone discard
**Source:** Angular `@angular/core/testing` API (already imported in all fakeAsync files)
**Apply to:** ANGFIX-01 (`stream-service.registry.spec.ts` only)

```typescript
import {fakeAsync, TestBed, tick, discardPeriodicTasks} from "@angular/core/testing";

// At the end of every fakeAsync block body (beforeEach and it):
discardPeriodicTasks();
```

### Pattern C: Union type instead of double-cast
**Source:** `view-file-filter.service.spec.ts` line 18/30 (the bad pattern to replace)
**Apply to:** ANGFIX-02

```typescript
// Replace:  let x: T;  /  x = undefined as unknown as T;
// With:     let x: T | undefined;  /  x = undefined;
// At usage: x!.method()  (safe when test flow guarantees assignment before use)
```

### Pattern D: toBeDefined guard before optional chaining
**Source:** `bulk-command.service.spec.ts` lines 57–60 (existing correct pattern)
**Apply to:** ANGFIX-07

```typescript
// After tick(), before any result?. assertions:
expect(result).toBeDefined();
```

---

## No Analog Found

None. All 7 fixes have verified patterns in the existing codebase.

---

## Metadata

**Analog search scope:** `src/angular/src/app/tests/unittests/`
**Files scanned:** 8 spec files read directly; 1 production file (`stream-service.registry.ts`) referenced for root-cause verification
**Pattern extraction date:** 2026-04-25
