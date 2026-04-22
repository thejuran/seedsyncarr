# Phase 76: Multiselect Bulk-Bar Action Union - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 4 modified + 1-2 test (mixed)
**Analogs found:** 4 / 4 (all fix sites have in-file precedent; tests have sibling precedent)

## Scope Note

This is a **bug-fix phase**. No new files are created. All fix sites are
modifications to existing files, and every fix-site analog IS the file itself
(in-place edit). The only "new" code lands as **new `it(...)` cases inside
the existing `bulk-actions-bar.component.spec.ts`** (and optionally
`view-file.service.spec.ts` if D-02 candidate root cause #1 is the winner).
Per D-02, root cause is unknown at mapping time; this PATTERNS.md enumerates
the per-candidate analog for each possible fix site so the planner can
reference the right one once Wave-1 characterization resolves the root cause.

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `src/angular/src/app/pages/files/bulk-actions-bar.component.ts` | component | request-response (Input / OnChanges / EventEmitter) | *self* — `_recomputeCachedValues` at lines 86-132 | in-place |
| `src/angular/src/app/pages/files/bulk-actions-bar.component.html` | template | declarative binding | *self* — disable bindings lines 16-41 | in-place |
| `src/angular/src/app/services/files/view-file.service.ts` | service | transform (ModelFile → ViewFile) | *self* — `createViewFile` at lines 297-394; eligibility predicates at 348-369 | in-place |
| `src/angular/src/app/services/files/file-selection.service.ts` | service | state (signal-based) | *self* — `pruneSelection` at lines 213-228 | in-place (unlikely fix site) |
| `src/angular/src/app/pages/files/transfer-table.component.ts` | component | event-driven / rxjs | *self* — `pagedFilesList$` wiring at lines 134, 137-139 | in-place (unlikely fix site) |
| `src/angular/src/app/pages/files/transfer-table.component.html` | template | declarative binding | *self* — bar wiring lines 174-184 | in-place (unlikely fix site) |
| **NEW** cases in `.../tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` | test | jasmine unit | *self* — existing `Action counts` + `Click handlers` blocks at lines 114-331 | exact-precedent |
| **NEW** cases in `.../tests/unittests/services/files/view-file.service.spec.ts` (conditional) | test | jasmine unit (fakeAsync) | *self* — `isQueueable` test at lines 271-329; `isRemotelyDeletable` test at lines 633-680 | exact-precedent |

## Pattern Assignments

### `bulk-actions-bar.component.ts` (component, request-response)

**Analog:** self (lines 86-132 — `_recomputeCachedValues`). Any fix at this
site MUST preserve OnPush + the single-pass loop + the five parallel
`*Files` caches. The suspicion in D-02 candidate #4 is that the
`visibleFiles.filter(...).toArray()` intersection at lines 88-90 is the
failure point when `selectedFiles` names are not in `visibleFiles`.

**Intersection pattern to inspect / modify** (lines 86-91):
```typescript
private _recomputeCachedValues(): void {
    // Compute selected view files once
    this._cachedSelectedViewFiles = this.visibleFiles
        .filter(f => f.name != null && this.selectedFiles.has(f.name))
        .toArray();
```

**Single-pass eligibility loop** (lines 99-117) — preserve structure if fix
is additive:
```typescript
for (const file of this._cachedSelectedViewFiles) {
    if (!file.name) { continue; }
    if (file.isQueueable) {
        queueable.push(file.name);
    }
    if (file.isStoppable) {
        stoppable.push(file.name);
    }
    // Match single-file logic: isExtractable AND isArchive
    if (file.isExtractable && file.isArchive) {
        extractable.push(file.name);
    }
    if (file.isLocallyDeletable) {
        locallyDeletable.push(file.name);
    }
    if (file.isRemotelyDeletable) {
        remotelyDeletable.push(file.name);
    }
}
```

**`ngOnChanges` gate** (lines 74-79) — preserve; any new cache-triggering
input must be added here:
```typescript
ngOnChanges(changes: SimpleChanges): void {
    // Only recompute if visibleFiles or selectedFiles changed
    if (changes["visibleFiles"] || changes["selectedFiles"]) {
        this._recomputeCachedValues();
    }
}
```

**Click emit pattern** (lines 237-242) — preserve verbatim; dispatch is
already per-action filtered:
```typescript
onQueueClick(): void {
    const files = this.queueableFiles;
    if (files.length > 0) {
        this.queueAction.emit(files);
    }
}
```

---

### `bulk-actions-bar.component.html` (template, declarative binding)

**Analog:** self (lines 1-44). Disable gate is `actionCounts.X === 0 ||
operationInProgress`. Visibility gate is `@if (hasSelection)`. No label
changes permitted (D-06).

**Disable-binding pattern** (line 17) — the contract that actionCounts > 0
enables the button:
```html
<button type="button" class="action-btn action-queue"
        [disabled]="actionCounts.queueable === 0 || operationInProgress"
        (click)="onQueueClick()">
  <i class="fa fa-play" aria-hidden="true"></i><span>Queue</span>
</button>
```

**Visibility gate** (line 1):
```html
@if (hasSelection) {
  <div class="bulk-actions-bar">
```

Per CONTEXT user symptom ("bar doesn't show at all"), if the bar fails to
render with DELETED rows selected, inspect whether `hasSelection` is
somehow false — but that is a pure `selectedFiles.size > 0` check, which
should be DELETED-agnostic.

---

### `view-file.service.ts` §`createViewFile` (service, transform)

**Analog:** self (lines 297-394). The five eligibility flags are D-05's
"source of truth." If the fix lives here, it is narrow: adjust one
predicate for the DELETED + `remoteSize === 0` edge case (D-02 candidate
root cause #1).

**Current `isQueueable`** (lines 348-351) — DELETED IS in the set, but is
gated by `remoteSize > 0`:
```typescript
const isQueueable: boolean = [ViewFile.Status.DEFAULT,
                            ViewFile.Status.STOPPED,
                            ViewFile.Status.DELETED].includes(status)
                            && remoteSize > 0;
```

**Current `isRemotelyDeletable`** (lines 364-369) — same pattern:
```typescript
const isRemotelyDeletable: boolean = [ViewFile.Status.DEFAULT,
                            ViewFile.Status.STOPPED,
                            ViewFile.Status.DOWNLOADED,
                            ViewFile.Status.EXTRACTED,
                            ViewFile.Status.DELETED].includes(status)
                            && remoteSize > 0;
```

**If the fix is here:** edit the `&& remoteSize > 0` clause for the DELETED
branch only. The minimal-diff change per D-03 is a ternary or a dedicated
branch, never a wholesale refactor.

**Size-normalization precedent** (lines 298-306) — zero defaults are
already in place; a DELETED file with a null `remote_size` will already
have `remoteSize === 0`, which is precisely the symptom D-02 #1 calls out:
```typescript
// Use zero for unknown sizes
let localSize: number = modelFile.local_size;
if (localSize == null) {
    localSize = 0;
}
let remoteSize: number = modelFile.remote_size;
if (remoteSize == null) {
    remoteSize = 0;
}
```

---

### `file-selection.service.ts` (service, state — signal-based)

**Analog:** self (lines 213-228 — `pruneSelection`). Per CONTEXT
"Existing Code Insights", `pruneSelection` "is not called outside tests."
A fix here is unlikely but possible if D-02 candidate #2 turns out to be
the root cause (a stale-selection path drops DELETED filenames).

**Current `pruneSelection`** (lines 213-228) — signal-based mutation with
operation-lock guard:
```typescript
pruneSelection(existingFileNames: Set<string>): void {
    // Skip pruning during bulk operations to prevent race conditions
    if (this._operationInProgress()) {
        return;
    }

    const currentSet = this.selectedFiles();
    const toRemove = Array.from(currentSet).filter(f => !existingFileNames.has(f));
    if (toRemove.length > 0) {
        this.selectedFiles.update(set => {
            const newSet = new Set(set);
            toRemove.forEach(f => newSet.delete(f));
            return newSet;
        });
    }
}
```

**Immutable mutation idiom** (lines 115-122) — if any new selection
mutator is added, follow this pattern (new Set per update, not in-place):
```typescript
select(fileName: string): void {
    if (!this.selectedFiles().has(fileName)) {
        this.selectedFiles.update(set => {
            const newSet = new Set(set);
            newSet.add(fileName);
            return newSet;
        });
    }
}
```

---

### `transfer-table.component.ts` (component, event-driven / rxjs)

**Analog:** self (lines 117-140). If D-02 candidate #3 or #4 wins — a
`visibleFiles`/`selectedFiles` update-tick mismatch — the fix may land
in the observable wiring.

**Current `pagedFilesList$` derivation** (line 134):
```typescript
this.pagedFilesList$ = this.pagedFiles$.pipe(map(arr => List(arr)), shareReplay(1));
this.selectedFiles$ = this.fileSelectionService.selectedFiles$;
```

**Current `_currentPagedFiles` mirror** (lines 137-139) — used by
`onHeaderCheckboxClick` and `onCheckboxToggle`:
```typescript
this.pagedFilesList$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(files => {
    this._currentPagedFiles = files;
});
```

**Subscription cleanup idiom** (line 137, 156, 167) — `takeUntilDestroyed
(this.destroyRef)`. Any new subscription MUST use this.

**`shareReplay(1)` pattern** (lines 115, 134) — ensures subscribers at bar
mount time get the current paged list without a re-subscription cost.
Preserve.

---

### `transfer-table.component.html` (template, declarative binding)

**Analog:** self (lines 174-184). The bar's two data inputs are
`pagedFilesList$` and `selectedFiles$` with `??` fallbacks.

**Bar wiring** (lines 174-184) — if fix requires a different
`visibleFiles` source (e.g., unpaged segmented list), the edit lands here:
```html
<app-bulk-actions-bar
    [visibleFiles]="(pagedFilesList$ | async) ?? emptySetList"
    [selectedFiles]="(selectedFiles$ | async) ?? emptySet"
    [operationInProgress]="bulkOperationInProgress()"
    (clearSelection)="onClearSelection()"
    (queueAction)="onBulkQueue($event)"
    (stopAction)="onBulkStop($event)"
    (extractAction)="onBulkExtract($event)"
    (deleteLocalAction)="onBulkDeleteLocal($event)"
    (deleteRemoteAction)="onBulkDeleteRemote($event)">
</app-bulk-actions-bar>
```

**CAUTION:** If the fix changes the `visibleFiles` source away from
`pagedFilesList$`, the `_recomputeCachedValues` intersection becomes a
no-op (selection is already a subset of the expanded list), which may
mask other bugs. Per D-03 "minimal edit," this is almost certainly NOT
the right fix site; document in PLAN.md why it was eliminated.

---

### NEW test cases in `bulk-actions-bar.component.spec.ts`

**Analog:** self — the existing spec is the template for all Phase 76
additions. Planner MUST match its style (D-09 Claude's Discretion note).

#### Reusable harness — `setInputsAndDetectChanges` (lines 63-77)

This is the **verbatim precedent** for Wave-1 characterization. All new
`it(...)` cases in Phase 76 use this helper.

```typescript
/**
 * Helper to set inputs and trigger ngOnChanges for proper cache update.
 */
function setInputsAndDetectChanges(visibleFiles: List<ViewFile>, selectedFiles: Set<string>): void {
    const changes: SimpleChanges = {};
    if (component.visibleFiles !== visibleFiles) {
        changes["visibleFiles"] = new SimpleChange(component.visibleFiles, visibleFiles, false);
        component.visibleFiles = visibleFiles;
    }
    if (component.selectedFiles !== selectedFiles) {
        changes["selectedFiles"] = new SimpleChange(component.selectedFiles, selectedFiles, false);
        component.selectedFiles = selectedFiles;
    }
    if (Object.keys(changes).length > 0) {
        component.ngOnChanges(changes);
    }
    fixture.detectChanges();
}
```

#### Reusable harness — DOM-aware variant `setInputsForDOM` (lines 375-384)

Use this instead of `setInputsAndDetectChanges` when the test needs to
assert on rendered button state (disabled attribute, visibility, etc.).
Required for any Phase 76 case that asserts the bar renders (symptom from
CONTEXT: "the bar doesn't show at all").

```typescript
function setInputsForDOM(visibleFiles: List<ViewFile>, selectedFiles: Set<string>): void {
    fixture.componentRef.setInput("visibleFiles", visibleFiles);
    fixture.componentRef.setInput("selectedFiles", selectedFiles);
    component.ngOnChanges({
        visibleFiles: new SimpleChange(component.visibleFiles, visibleFiles, false),
        selectedFiles: new SimpleChange(component.selectedFiles, selectedFiles, false)
    });
    fixture.detectChanges();
}
```

#### Fixture-construction precedent (lines 14-58)

New Phase 76 fixtures MUST set `isQueueable`/`isRemotelyDeletable` flags
directly on `ViewFile` rather than relying on `ViewFileService.
createViewFile()` — the bar's unit test is a pure-consumer test, not an
integration test. For DELETED characterization, also set `status:
ViewFile.Status.DELETED` and `remoteSize: <positive integer>` explicitly
so downstream assertions can tie symptom to status.

```typescript
new ViewFile({
    name: "file1",
    isQueueable: true,
    isStoppable: false,
    isExtractable: false,
    isLocallyDeletable: false,
    isRemotelyDeletable: true
}),
```

#### Mixed-selection "count + emit" precedent (lines 131-146 + 254-262)

This is the **precedent for D-09 tests**. New tests mirror this exact
shape: (a) set inputs via harness, (b) assert counts, (c) spy on emitter,
(d) call click handler, (e) assert emit-with-filtered-array. Quoting the
existing mixed-selection count-check (lines 131-146) and the matching
click-handler shape (lines 254-262):

Count assertion pattern (lines 131-146):
```typescript
it("should calculate counts only for selected files", () => {
    // Only select file1 and file3
    setInputsAndDetectChanges(testFiles, new Set(["file1", "file3"]));
    const counts: BulkActionCounts = component.actionCounts;

    // file1 is queueable
    expect(counts.queueable).toBe(1);
    // file3 is stoppable
    expect(counts.stoppable).toBe(1);
    // Neither is extractable
    expect(counts.extractable).toBe(0);
    // Neither is locally deletable
    expect(counts.locallyDeletable).toBe(0);
    // file1 is remotely deletable
    expect(counts.remotelyDeletable).toBe(1);
});
```

Emit-filtering pattern (lines 254-262):
```typescript
it("should emit stopAction with stoppable files on Stop click", () => {
    setInputsAndDetectChanges(testFiles, new Set(["file3", "file4"]));
    spyOn(component.stopAction, "emit");

    component.onStopClick();

    expect(component.stopAction.emit).toHaveBeenCalledWith(
        jasmine.arrayContaining(["file3", "file4"])
    );
});
```

#### Describe-block organization precedent

The existing file is organized as:
- `describe("Visibility", ...)` — lines 93-108
- `describe("Action counts", ...)` — lines 114-167
- `describe("File getters", ...)` — lines 173-216
- `describe("Click handlers", ...)` — lines 222-331
- `describe("Edge cases", ...)` — lines 337-365
- `describe("Variant B DOM contract", ...)` — lines 371-432
- `describe("Performance with large file counts", ...)` — lines 438-532

D-09 Phase 76 cases fit naturally into a **new** `describe("DELETED
union regression (FIX-01)", ...)` block appended after "Edge cases" and
before "Variant B DOM contract" — or, if the planner prefers, as new
`it(...)` cases inside "Action counts" + "Click handlers". Either
placement matches the existing style.

---

### NEW test cases in `view-file.service.spec.ts` (conditional)

**Conditional:** only add tests here if the fix lands in
`createViewFile` eligibility flags (D-02 candidate root cause #1).

**Analog:** self — test vector table idiom at lines 271-329 (`isQueueable`)
and 633-680 (`isRemotelyDeletable`) is the exact precedent. Existing
fixtures already cover the DELETED branch; any Phase 76 extension is
adding a vector for the edge case the fix targets.

**Test-vector pattern** (lines 271-329):
```typescript
it("should should correctly set ViewFile isQueueable", fakeAsync(() => {
    // Test and expected result vectors
    // test - [ModelFile.State, local size, remote size]
    // result - [isQueueable, ViewFile.Status]
    const testVectors: TestVector[] = [
        // Default remote file is queueable
        [[ModelFile.State.DEFAULT, null as unknown as number, 100], [true, ViewFile.Status.DEFAULT]],
        // ...
        // Deleted file is queueable
        [[ModelFile.State.DELETED, null as unknown as number, 100], [true, ViewFile.Status.DELETED]],
        // ...
    ];

    let count = -1;
    viewService.files.subscribe({
        next: list => {
            // Ignore first
            if(count >= 0) {
                expect(list.size).toBe(1);
                const file = list.get(0)!;
                const resultVector = testVectors[count][1];
                expect(file!.isQueueable).toBe(resultVector[0]);
                expect(file!.status).toBe(resultVector[1]);
            }
            count++;
        }
    });
    tick();
    expect(count).toBe(0);

    // Send over the test vectors
    for(const vector of testVectors) {
        const testVector = vector[0];
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: testVector[0],
            local_size: testVector[1] ?? undefined,
            remote_size: testVector[2] ?? undefined,
        }));
        mockModelService._files.next(model);
        tick();
    }
    expect(count).toBe(testVectors.length);
}));
```

**`TestVector` alias** (line 17):
```typescript
type TestVector = [[ModelFile.State, number | null | undefined, number | null | undefined], [boolean, ViewFile.Status]];
```

**TestBed setup** (lines 25-40) — reuse verbatim; do not add new
providers:
```typescript
beforeEach(() => {
    TestBed.configureTestingModule({
        providers: [
            ViewFileService,
            LoggerService,
            ConnectedService,
            FileSelectionService,
            {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
        ]
    });

    viewService = TestBed.inject(ViewFileService);
    fileSelectionService = TestBed.inject(FileSelectionService);
    const mockRegistry: MockStreamServiceRegistry = TestBed.inject(StreamServiceRegistry) as unknown as MockStreamServiceRegistry;
    mockModelService = mockRegistry.modelFileService;
});
```

---

## Shared Patterns

### Angular OnPush + @Input/ngOnChanges cache

**Source:** `bulk-actions-bar.component.ts` (lines 29-37 + 74-79)
**Apply to:** The bar itself. Any fix MUST preserve OnPush; adding a new
subscription path in the bar is out of scope per D-03 "no refactors."

```typescript
@Component({
    selector: "app-bulk-actions-bar",
    templateUrl: "./bulk-actions-bar.component.html",
    styleUrls: ["./bulk-actions-bar.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
})
```

### Signal-based selection state

**Source:** `file-selection.service.ts` (lines 36-53)
**Apply to:** Any new selection mutator (unlikely this phase). Immutable
Set + `signal.update()` + `toObservable()` bridge for legacy subscribers.

```typescript
readonly selectedFiles = signal<Set<string>>(new Set());
readonly selectedCount = computed(() => this.selectedFiles().size);
readonly hasSelection = computed(() => this.selectedFiles().size > 0);
readonly selectedFiles$ = toObservable(this.selectedFiles);
```

### Eligibility-flag computation idiom

**Source:** `view-file.service.ts` §`createViewFile` (lines 348-369)
**Apply to:** Any fix landing in `createViewFile`. Pattern is
`[...Status].includes(status) && <size predicate>`. Preserve this shape
to minimize diff surface.

### Immutable List intersection

**Source:** `bulk-actions-bar.component.ts` (lines 88-90)
**Apply to:** The bar's `_recomputeCachedValues`. `List<ViewFile>.filter
(...).toArray()` is the O(n) intersection idiom used throughout. If the
fix requires a different intersection (e.g., walk selection, look up in
file-name→ViewFile map), the planner MUST document why the current shape
is wrong. Default assumption: preserve.

### `takeUntilDestroyed(destroyRef)` cleanup

**Source:** `transfer-table.component.ts` (lines 87, 137, 156, 167)
**Apply to:** Any new rxjs subscription. No exceptions.

### Test fixture — direct `ViewFile` construction

**Source:** `bulk-actions-bar.component.spec.ts` (lines 14-58)
**Apply to:** All Phase 76 `bulk-actions-bar` spec additions. Construct
`ViewFile` with the five eligibility flags set directly — do NOT route
through `createViewFile`. This keeps the unit test a pure consumer test.
Exception: D-09 mixed cases may additionally set `status` + `remoteSize`
to make the linkage to the FIX-01 repro self-documenting, even though
the bar does not read those fields.

### Test fixture — `fakeAsync` + test-vector table

**Source:** `view-file.service.spec.ts` (lines 271-329, 633-680)
**Apply to:** Any Phase 76 addition to `view-file.service.spec.ts`.
Append a vector row to an existing `testVectors` table rather than
writing a new `it(...)` block, UNLESS the new assertion is structurally
different (e.g., asserts against a new flag not currently in the table).

---

## No Analog Found

**None.** Every fix-site candidate for Phase 76 has an existing file that
is itself the closest analog (in-place edit). Every test addition has a
sibling `it(...)` in the same file that demonstrates the required shape.

## Metadata

**Analog search scope:**
- `src/angular/src/app/pages/files/` (5 .ts, 5 .html, 5 .scss)
- `src/angular/src/app/services/files/` (~10 .ts)
- `src/angular/src/app/tests/unittests/pages/files/` (5 .spec.ts)
- `src/angular/src/app/tests/unittests/services/files/` (9 .spec.ts)

**Files scanned:** ~35 (directly read: 7)
**Files read fully:**
- `bulk-actions-bar.component.ts`
- `bulk-actions-bar.component.html`
- `view-file.service.ts`
- `file-selection.service.ts`
- `transfer-table.component.ts`
- `bulk-actions-bar.component.spec.ts`
- `view-file.ts`

**Files targeted-read (offset/limit):**
- `transfer-table.component.html` (lines 160-199)
- `view-file.service.spec.ts` (lines 1-130, 265-345, 625-680)

**Pattern extraction date:** 2026-04-20
