# Phase 70: Drilldown Segment Filters — Pattern Map

**Mapped:** 2026-04-15
**Files analyzed:** 4 (3 source files + 1 spec file)
**Analogs found:** 4 / 4 (all self-referential — modifications to existing files)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/angular/src/app/pages/files/transfer-table.component.ts` | component (stateful controller) | event-driven + reactive (BehaviorSubject/combineLatest) | itself (current implementation) | exact — additive changes only |
| `src/angular/src/app/pages/files/transfer-table.component.html` | template | request-response (user click -> @if render) | itself (current implementation) | exact — additive @if blocks |
| `src/angular/src/app/pages/files/transfer-table.component.scss` | styles | — | itself (current `.btn-segment` block) | exact — new modifier classes alongside existing |
| `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` | test | — | itself (current spec) | exact — update existing + add cases |

All four files are modifications. There are no net-new files. The analog for every file is itself — the change is purely additive within the established patterns.

---

## Pattern Assignments

### `transfer-table.component.ts` (component, event-driven + reactive)

**Analog:** `src/angular/src/app/pages/files/transfer-table.component.ts` (current state)

**Imports pattern** (lines 1-12 — no changes needed):
```typescript
import {Component, ChangeDetectionStrategy, DestroyRef, inject} from "@angular/core";
import {AsyncPipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Observable, BehaviorSubject, Subject, combineLatest} from "rxjs";
import {debounceTime, distinctUntilChanged, map} from "rxjs/operators";

import {ViewFileService} from "../../services/files/view-file.service";
import {ViewFileOptionsService} from "../../services/files/view-file-options.service";
import {ViewFile} from "../../services/files/view-file";
import {TransferRowComponent} from "./transfer-row.component";
```

**Existing state field pattern** (lines 24-27 — extend, do not replace):
```typescript
activeSegment: "all" | "active" | "errors" = "all";
nameFilter = "";
currentPage = 1;
readonly pageSize = 15;
```

ADD after `activeSegment`:
```typescript
activeSubStatus: ViewFile.Status | null = null;
readonly ViewFileStatus = ViewFile.Status;   // exposes namespace enum to template
```

**BehaviorSubject widening pattern** (line 33 — widen type + initial value):

Current (line 33):
```typescript
private filterState$ = new BehaviorSubject<{segment: "all" | "active" | "errors", page: number}>({segment: "all", page: 1});
```

Replace with:
```typescript
private filterState$ = new BehaviorSubject<{
    segment: "all" | "active" | "errors";
    subStatus: ViewFile.Status | null;
    page: number;
}>({ segment: "all", subStatus: null, page: 1 });
```

**segmentedFiles$ pipeline pattern** (lines 42-64 — replace map body + remove inner distinctUntilChanged):

Current (lines 42-64):
```typescript
const segmentedFiles$ = combineLatest([
    this.viewFileService.filteredFiles,
    this.filterState$.pipe(
        map(s => s.segment),
        distinctUntilChanged()
    )
]).pipe(
    map(([files, segment]) => {
        if (segment === "all") { return files; }
        if (segment === "active") {
            return files.filter(f =>
                f.status === ViewFile.Status.DOWNLOADING ||
                f.status === ViewFile.Status.QUEUED ||
                f.status === ViewFile.Status.EXTRACTING
            ).toList();
        }
        // errors
        return files.filter(f =>
            f.status === ViewFile.Status.STOPPED ||
            f.status === ViewFile.Status.DELETED
        ).toList();
    })
);
```

Replace with (removes inner `distinctUntilChanged` so sub-status changes are not suppressed; adds subStatus check as first branch):
```typescript
const segmentedFiles$ = combineLatest([
    this.viewFileService.filteredFiles,
    this.filterState$
]).pipe(
    map(([files, state]) => {
        if (state.subStatus != null) {
            return files.filter(f => f.status === state.subStatus).toList();
        }
        if (state.segment === "active") {
            return files.filter(f =>
                f.status === ViewFile.Status.DOWNLOADING ||
                f.status === ViewFile.Status.QUEUED ||
                f.status === ViewFile.Status.EXTRACTING
            ).toList();
        }
        if (state.segment === "errors") {
            return files.filter(f =>
                f.status === ViewFile.Status.STOPPED ||
                f.status === ViewFile.Status.DELETED
            ).toList();
        }
        return files;
    })
);
```

Note: `pagedFiles$` (line 67) uses `this.filterState$` directly and reads `state.page` only — it compiles without change once the BehaviorSubject type is widened.

**onSegmentChange pattern** (lines 106-110 — replace body with toggle-collapse logic):

Current (lines 106-110):
```typescript
onSegmentChange(segment: "all" | "active" | "errors"): void {
    this.activeSegment = segment;
    this.currentPage = 1;
    this.filterState$.next({segment, page: 1});
}
```

Replace with:
```typescript
onSegmentChange(segment: "all" | "active" | "errors"): void {
    if (segment !== "all" && this.activeSegment === segment) {
        // Second click on same expandable parent — collapse to All
        this.activeSegment = "all";
        this.activeSubStatus = null;
        this.currentPage = 1;
        this.filterState$.next({ segment: "all", subStatus: null, page: 1 });
    } else {
        this.activeSegment = segment;
        this.activeSubStatus = null;
        this.currentPage = 1;
        this.filterState$.next({ segment, subStatus: null, page: 1 });
    }
}
```

**New method — onSubStatusChange** (add after `onSegmentChange`):
```typescript
onSubStatusChange(status: ViewFile.Status): void {
    this.activeSubStatus = status;
    this.currentPage = 1;
    this.filterState$.next({
        segment: this.activeSegment,
        subStatus: status,
        page: 1
    });
}
```

**goToPage pattern** (line 112-115 — update spread to include subStatus):

Current (lines 112-115):
```typescript
goToPage(page: number): void {
    this.currentPage = page;
    this.filterState$.next({...this.filterState$.value, page});
}
```

No change needed — spread operator `...this.filterState$.value` already carries `subStatus` forward once the type is widened.

---

### `transfer-table.component.html` (template, request-response)

**Analog:** `src/angular/src/app/pages/files/transfer-table.component.html` (current state)

**Existing @if / @for control flow pattern** (lines 48-56 and 64-67 — copy this style for new @if blocks):
```html
@for (file of (vm.paged ?? []); track trackByName($index, file)) {
  <app-transfer-row [file]="file"></app-transfer-row>
} @empty {
  <tr class="empty-row">
    <td colspan="6" class="text-center text-muted py-4">
      No files match the current filter
    </td>
  </tr>
}
```
```html
@if ((vm.totalCount ?? 0) === 0) {
  No files to display
} @else {
  Showing {{ ... }}
}
```

**Segment filter block to replace** (lines 20-30):

Current:
```html
<div class="segment-filters" role="group" aria-label="File status filter">
  <button type="button" class="btn-segment"
          [class.active]="activeSegment === 'all'"
          (click)="onSegmentChange('all')">All</button>
  <button type="button" class="btn-segment"
          [class.active]="activeSegment === 'active'"
          (click)="onSegmentChange('active')">Active</button>
  <button type="button" class="btn-segment"
          [class.active]="activeSegment === 'errors'"
          (click)="onSegmentChange('errors')">Errors</button>
</div>
```

Replace with drill-down version (preserves All button with existing `.active` class; Active and Errors get new modifier classes only — never the `active` class — so `pointer-events: none` on `.btn-segment.active` does not block collapse clicks):
```html
<div class="segment-filters" role="group" aria-label="File status filter">

  <!-- All: terminal button, keeps existing active class -->
  <button type="button" class="btn-segment"
          [class.active]="activeSegment === 'all'"
          (click)="onSegmentChange('all')">All</button>

  <!-- Active: expandable parent -->
  <button type="button" class="btn-segment"
          [class.btn-segment--parent-active]="activeSegment === 'active' && activeSubStatus === null"
          [class.btn-segment--parent-expanded]="activeSegment === 'active' && activeSubStatus !== null"
          (click)="onSegmentChange('active')">
    Active
    <i class="ph-bold"
       [class.ph-caret-down]="activeSegment !== 'active'"
       [class.ph-caret-up]="activeSegment === 'active'"></i>
  </button>

  @if (activeSegment === 'active') {
    <div class="segment-divider"></div>
    <button type="button" class="btn-sub"
            [class.active]="activeSubStatus === ViewFileStatus.DOWNLOADING"
            (click)="onSubStatusChange(ViewFileStatus.DOWNLOADING)">
      @if (activeSubStatus === ViewFileStatus.DOWNLOADING) {
        <span class="accent-dot"></span>
      }
      Syncing
    </button>
    <button type="button" class="btn-sub"
            [class.active]="activeSubStatus === ViewFileStatus.QUEUED"
            (click)="onSubStatusChange(ViewFileStatus.QUEUED)">
      @if (activeSubStatus === ViewFileStatus.QUEUED) {
        <span class="accent-dot"></span>
      }
      Queued
    </button>
    <button type="button" class="btn-sub"
            [class.active]="activeSubStatus === ViewFileStatus.EXTRACTING"
            (click)="onSubStatusChange(ViewFileStatus.EXTRACTING)">
      @if (activeSubStatus === ViewFileStatus.EXTRACTING) {
        <span class="accent-dot"></span>
      }
      Extracting
    </button>
  }

  <!-- Errors: expandable parent -->
  <button type="button" class="btn-segment"
          [class.btn-segment--parent-active]="activeSegment === 'errors' && activeSubStatus === null"
          [class.btn-segment--parent-expanded]="activeSegment === 'errors' && activeSubStatus !== null"
          (click)="onSegmentChange('errors')">
    Errors
    <i class="ph-bold"
       [class.ph-caret-down]="activeSegment !== 'errors'"
       [class.ph-caret-up]="activeSegment === 'errors'"></i>
  </button>

  @if (activeSegment === 'errors') {
    <div class="segment-divider"></div>
    <button type="button" class="btn-sub"
            [class.active]="activeSubStatus === ViewFileStatus.STOPPED"
            (click)="onSubStatusChange(ViewFileStatus.STOPPED)">
      @if (activeSubStatus === ViewFileStatus.STOPPED) {
        <span class="accent-dot"></span>
      }
      Failed
    </button>
    <button type="button" class="btn-sub"
            [class.active]="activeSubStatus === ViewFileStatus.DELETED"
            (click)="onSubStatusChange(ViewFileStatus.DELETED)">
      @if (activeSubStatus === ViewFileStatus.DELETED) {
        <span class="accent-dot"></span>
      }
      Deleted
    </button>
  }

</div>
```

---

### `transfer-table.component.scss` (styles)

**Analog:** `src/angular/src/app/pages/files/transfer-table.component.scss` (current state)

**Existing `.btn-segment` block pattern** (lines 138-161 — DO NOT modify; new classes are additions):
```scss
.btn-segment {
  background: transparent;
  border: none;
  color: #9aaa8a;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: #293326;
    color: #e0e8d6;
  }

  &.active {
    background: #222a20;
    border: 1px solid #3e4a38;
    color: #e0e8d6;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    pointer-events: none;    // <-- All button only; Active/Errors never get .active
  }
}
```

**Existing `.segment-filters` rule** (lines 126-136 — update border-radius from 4px to 6px per mockup):
```scss
.segment-filters {
  display: none;
  background: #151a14;
  border: 1px solid rgba(62, 74, 56, 0.3);   // spec uses opacity 0.3 on pill border
  border-radius: 6px;                         // mockup value overrides spec 4px per project convention
  padding: 2px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.4);

  @media (min-width: 768px) {
    display: flex;
    align-items: center;                      // needed to vertically center sub-buttons with parents
  }
}
```

**New classes to append after `.btn-segment` block** (add in the Segment Filters section):
```scss
// Expanded parent — sub-status IS selected: lighter bg, transparent border, amber chevron
.btn-segment--parent-expanded {
  background: rgba(34, 42, 32, 0.6);
  border: 1px solid transparent;
  color: #e0e8d6;
}

// Expanded parent — no sub-selection: full active treatment + chevron up (same visual as All active, but pointer-events remain enabled)
.btn-segment--parent-active {
  background: #222a20;
  border: 1px solid #3e4a38;
  color: #e0e8d6;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
}

// Thin vertical separator between parent and child sub-buttons
.segment-divider {
  width: 1px;
  height: 14px;
  background: rgba(62, 74, 56, 0.6);
  flex-shrink: 0;
}

// Sub-button base style
.btn-sub {
  background: transparent;
  border: 1px solid transparent;
  color: #7d8c6d;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  gap: 6px;

  &:hover {
    color: #e0e8d6;
    background: rgba(34, 42, 32, 0.4);
  }

  &.active {
    background: #222a20;
    border: 1px solid #3e4a38;
    color: #c49a4a;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
  }
}

// Amber accent dot with glow — rendered only inside active sub-button via @if in template
.accent-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c49a4a;
  box-shadow: 0 0 6px 1px rgba(196, 154, 74, 0.3);
  flex-shrink: 0;
}
```

---

### `transfer-table.component.spec.ts` (test)

**Analog:** `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` (current state)

**Test setup pattern** (lines 82-105 — keep verbatim; only TEST_TEMPLATE and individual `it` blocks change):
```typescript
describe("TransferTableComponent", () => {
    let component: TransferTableComponent;
    let fixture: ComponentFixture<TransferTableComponent>;
    let mockFileService: MockViewFileService;
    let mockOptionsService: MockViewFileOptionsService;

    beforeEach(async () => {
        mockFileService = new MockViewFileService();
        mockOptionsService = new MockViewFileOptionsService();

        await TestBed.configureTestingModule({
            imports: [TransferTableComponent],
            providers: [
                {provide: ViewFileService, useValue: mockFileService},
                {provide: ViewFileOptionsService, useValue: mockOptionsService}
            ]
        })
        .overrideTemplate(TransferTableComponent, TEST_TEMPLATE)
        .compileComponents();

        fixture = TestBed.createComponent(TransferTableComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });
```

**makeFile helper pattern** (lines 70-79 — keep verbatim, reuse for all new test cases):
```typescript
function makeFile(name: string, status: ViewFile.Status, opts: Partial<ViewFile> = {}): ViewFile {
    return new ViewFile({
        name,
        status,
        remoteSize: 1000,
        localSize: 500,
        percentDownloaded: 50,
        ...opts
    });
}
```

**fakeAsync + tick + subscribe pattern** (lines 152-174 — copy for all new filter tests):
```typescript
it("should filter to active statuses when 'active' segment selected", fakeAsync(() => {
    const files = [
        makeFile("dl-1", ViewFile.Status.DOWNLOADING),
        // ...
    ];
    mockFileService.pushFiles(files);
    tick();

    component.onSegmentChange("active");
    fixture.detectChanges();
    tick();

    let pagedFiles: ViewFile[] = [];
    component.pagedFiles$.subscribe(f => pagedFiles = f);
    tick();

    expect(pagedFiles.length).toBe(3);
    expect(pagedFiles.map(f => f.name)).toEqual(jasmine.arrayContaining([...]));
}));
```

**TEST_TEMPLATE update** — add sub-button structure so new component fields compile in the test template. Replace the current `<div class="segment-filters">` block in `TEST_TEMPLATE` (lines 21-24) with:
```typescript
const TEST_TEMPLATE = `
<div class="table-header">
  <div class="segment-filters">
    <button class="btn-segment" [class.active]="activeSegment === 'all'" (click)="onSegmentChange('all')">All</button>
    <button class="btn-segment"
            [class.btn-segment--parent-active]="activeSegment === 'active' && activeSubStatus === null"
            [class.btn-segment--parent-expanded]="activeSegment === 'active' && activeSubStatus !== null"
            (click)="onSegmentChange('active')">Active</button>
    @if (activeSegment === 'active') {
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.DOWNLOADING" (click)="onSubStatusChange(ViewFileStatus.DOWNLOADING)">Syncing</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.QUEUED" (click)="onSubStatusChange(ViewFileStatus.QUEUED)">Queued</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.EXTRACTING" (click)="onSubStatusChange(ViewFileStatus.EXTRACTING)">Extracting</button>
    }
    <button class="btn-segment"
            [class.btn-segment--parent-active]="activeSegment === 'errors' && activeSubStatus === null"
            [class.btn-segment--parent-expanded]="activeSegment === 'errors' && activeSubStatus !== null"
            (click)="onSegmentChange('errors')">Errors</button>
    @if (activeSegment === 'errors') {
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.STOPPED" (click)="onSubStatusChange(ViewFileStatus.STOPPED)">Failed</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.DELETED" (click)="onSubStatusChange(ViewFileStatus.DELETED)">Deleted</button>
    }
  </div>
</div>
// ... rest of template unchanged
`;
```

**Tests to update:**

`"should render 3 segment filter buttons"` (lines 126-132) — assertion count and selector must widen. Replace with:
```typescript
it("should render 3 parent segment filter buttons", () => {
    const buttons = fixture.nativeElement.querySelectorAll(".btn-segment");
    expect(buttons.length).toBe(3);
    expect(buttons[0].textContent).toContain("All");
    expect(buttons[1].textContent).toContain("Active");
    expect(buttons[2].textContent).toContain("Errors");
});
```

`"should set activeSegment when segment button clicked"` (lines 141-150) — add toggle-collapse assertion. Replace with:
```typescript
it("should set activeSegment when segment button clicked", () => {
    component.onSegmentChange("active");
    expect(component.activeSegment).toBe("active");

    // Second click on same segment collapses to all
    component.onSegmentChange("active");
    expect(component.activeSegment).toBe("all");
    expect(component.activeSubStatus).toBeNull();

    component.onSegmentChange("errors");
    expect(component.activeSegment).toBe("errors");

    component.onSegmentChange("all");
    expect(component.activeSegment).toBe("all");
});
```

**New test cases to add** (follow the fakeAsync + tick + subscribe pattern from existing filter tests):

```typescript
it("should have default activeSubStatus of null", () => {
    expect(component.activeSubStatus).toBeNull();
});

it("should filter to DOWNLOADING only when Syncing sub-status selected", fakeAsync(() => {
    const files = [
        makeFile("dl-1", ViewFile.Status.DOWNLOADING),
        makeFile("queued-1", ViewFile.Status.QUEUED),
        makeFile("extract-1", ViewFile.Status.EXTRACTING),
    ];
    mockFileService.pushFiles(files);
    tick();

    component.onSegmentChange("active");
    component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
    fixture.detectChanges();
    tick();

    let pagedFiles: ViewFile[] = [];
    component.pagedFiles$.subscribe(f => pagedFiles = f);
    tick();

    expect(pagedFiles.length).toBe(1);
    expect(pagedFiles[0].name).toBe("dl-1");
}));

it("should filter to QUEUED only when Queued sub-status selected", fakeAsync(() => { /* same pattern */ }));
it("should filter to EXTRACTING only when Extracting sub-status selected", fakeAsync(() => { /* same pattern */ }));
it("should filter to STOPPED only when Failed sub-status selected", fakeAsync(() => { /* same pattern */ }));
it("should filter to DELETED only when Deleted sub-status selected", fakeAsync(() => { /* same pattern */ }));

it("should switch sub-status within same segment", fakeAsync(() => {
    const files = [
        makeFile("dl-1", ViewFile.Status.DOWNLOADING),
        makeFile("queued-1", ViewFile.Status.QUEUED),
    ];
    mockFileService.pushFiles(files);
    tick();

    component.onSegmentChange("active");
    component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
    tick();

    component.onSubStatusChange(ViewFile.Status.QUEUED);
    fixture.detectChanges();
    tick();

    let pagedFiles: ViewFile[] = [];
    component.pagedFiles$.subscribe(f => pagedFiles = f);
    tick();

    expect(pagedFiles.length).toBe(1);
    expect(pagedFiles[0].name).toBe("queued-1");
    expect(component.activeSubStatus).toBe(ViewFile.Status.QUEUED);
}));

it("should clear subStatus when switching parent segment", fakeAsync(() => {
    component.onSegmentChange("active");
    component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
    expect(component.activeSubStatus).toBe(ViewFile.Status.DOWNLOADING);

    component.onSegmentChange("errors");
    expect(component.activeSegment).toBe("errors");
    expect(component.activeSubStatus).toBeNull();
}));

it("should clear subStatus and collapse to All when clicking expanded parent", () => {
    component.onSegmentChange("active");
    component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
    expect(component.activeSubStatus).toBe(ViewFile.Status.DOWNLOADING);

    component.onSegmentChange("active"); // second click — collapse
    expect(component.activeSegment).toBe("all");
    expect(component.activeSubStatus).toBeNull();
});

it("should reset page to 1 on sub-status change", () => {
    component.currentPage = 3;
    component.onSegmentChange("active");
    component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
    expect(component.currentPage).toBe(1);
});
```

---

## Shared Patterns

### Reactive state emission (BehaviorSubject)
**Source:** `transfer-table.component.ts` lines 33, 109, 112-115
**Apply to:** Every state mutation (onSegmentChange, onSubStatusChange, goToPage)

The invariant: every handler that changes filter state MUST call `this.filterState$.next({...})` with the full object shape `{ segment, subStatus, page }`. Never mutate component fields without a matching `.next()` call. The pipeline is driven entirely by `filterState$` emissions.

```typescript
// Pattern: always emit full state object, always reset page on filter change
this.filterState$.next({ segment: this.activeSegment, subStatus: status, page: 1 });
```

### @if control flow (Angular 17+)
**Source:** `transfer-table.component.html` lines 48-56, 64-67
**Apply to:** All conditional sub-button rendering blocks

Use `@if` / `@else` / `@for` / `@empty` syntax exclusively. Do not use `*ngIf` or `*ngFor` directives — the template already uses the new control flow syntax and mixing is not permitted.

### Token reuse
**Source:** `transfer-table.component.scss` — all existing color values
**Apply to:** All new SCSS classes

All color values for new classes are already present in the existing SCSS file. Do not introduce new tokens. Exact reuse:
- `#222a20` — active bg (`.transfer-card`, `.btn-segment.active`, `.btn-page.active`)
- `#3e4a38` — border color (throughout)
- `#e0e8d6` — primary text (throughout)
- `#9aaa8a` — muted text (`.card-subtitle`, `.btn-segment`)
- `#7d8c6d` — sub-muted (new `.btn-sub` base color — slightly dimmer than `#9aaa8a`)
- `#c49a4a` — amber accent (`.search-input:focus` border/shadow)
- `#151a14` — deep bg (`.segment-filters`, `.search-input`)
- `0.15s ease` — transition (`.btn-segment`, `.btn-page`, `.search-icon`)

---

## No Analog Found

None. All files are modifications of existing files.

---

## Critical Anti-Patterns (from codebase inspection)

| Risk | Evidence in codebase | Guard |
|------|---------------------|-------|
| `pointer-events: none` blocks collapse click | `.btn-segment.active { pointer-events: none }` at scss line 159 | Active/Errors parent buttons must never receive `[class.active]` binding — use `btn-segment--parent-active` and `btn-segment--parent-expanded` only |
| `distinctUntilChanged` on segment-only drops sub-status changes | `filterState$.pipe(map(s => s.segment), distinctUntilChanged())` at ts lines 44-47 | Remove inner `.pipe(map(s => s.segment), distinctUntilChanged())` and pass full `filterState$` to `combineLatest` |
| Namespace enum inaccessible in template | `ViewFile.Status` is a TS namespace enum, not a direct export | Add `readonly ViewFileStatus = ViewFile.Status;` as class field; reference `ViewFileStatus.DOWNLOADING` in template |
| BehaviorSubject initial value mismatch | Current initial value `{segment: "all", page: 1}` lacks `subStatus` | Update to `{segment: "all", subStatus: null, page: 1}` together with the type annotation |
| `border` on `.btn-segment` base conflicts with modifier classes | `.btn-segment { border: none }` at scss line 141 | New modifier classes set `border: 1px solid ...` which overrides `border: none` — correct, no fix needed |

---

## Metadata

**Analog search scope:** `src/angular/src/app/pages/files/`, `src/angular/src/app/tests/unittests/pages/files/`, `src/angular/src/app/services/files/`
**Files scanned:** 5 source files read directly
**Pattern extraction date:** 2026-04-15
