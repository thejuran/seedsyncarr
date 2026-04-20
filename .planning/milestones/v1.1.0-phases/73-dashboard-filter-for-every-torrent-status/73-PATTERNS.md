# Phase 73: Dashboard filter for every torrent status - Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 6 (4 modified, 2 modified-with-additions)
**Analogs found:** 6 / 6 (all in-file or sibling-file analogs)

## Summary

This phase EXTENDS the existing drill-down segment-filter pattern in `TransferTableComponent`. Every modification has an exact in-file analog (Active/Errors segment branch, sub-button markup, segmentedFiles$ switch, sub-status filter test) **except** the URL query-param hydration + write-back, for which **no codebase analog exists** (Router.navigate with queryParamsHandling and ActivatedRoute.queryParamMap are not used anywhere in the codebase today). The planner should follow the design doc + Angular API contract for that one new pattern, and copy verbatim from the existing Active/Errors code for everything else.

The "port AIDesigner HTML identically" memory rule (`feedback_design_spec_rigor.md`) applies: every new button must reuse the existing `.btn-segment` / `.btn-sub` SCSS classes verbatim — no per-instance overrides, no token substitutions.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/angular/src/app/pages/files/transfer-table.component.ts` | component (controller of filter state) | event-driven + request-response | self (existing Active/Errors branches) | exact in-file |
| `src/angular/src/app/pages/files/transfer-table.component.html` | template | event-driven | self (existing Active/Errors blocks) | exact in-file |
| `src/angular/src/app/pages/files/transfer-table.component.scss` | styles | n/a (verify only) | self (existing `.btn-segment`/`.btn-sub`) | exact (no new tokens) |
| `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` | unit test | n/a | self (existing per-status sub-status test cases) | exact in-file |
| `src/e2e/tests/dashboard.page.ts` | e2e page object | locator-only | self (existing `getActionButton` / `getActionBar` locator pattern) | exact in-file |
| `src/e2e/tests/dashboard.page.spec.ts` | e2e spec | request-response | self (existing Phase 72 tests) | exact in-file |

## Pattern Assignments

### `src/angular/src/app/pages/files/transfer-table.component.ts` (component, event-driven)

**Analog:** itself (Active and Errors branches are the template for Done; Active sub-buttons are the template for the new Pending case).

#### Pattern 1 — Extend `activeSegment` union (existing line 28)

**Current** (`transfer-table.component.ts:28`):
```typescript
activeSegment: "all" | "active" | "errors" = "all";
```

**Target shape (per CONTEXT.md D-04):** Add `"done"` to both the field annotation, the `filterState$` BehaviorSubject generic at lines 53-57, and the `onSegmentChange` parameter type at line 158.

**Existing BehaviorSubject** (`transfer-table.component.ts:53-57`):
```typescript
private filterState$ = new BehaviorSubject<{
    segment: "all" | "active" | "errors";
    subStatus: ViewFile.Status | null;
    page: number;
}>({segment: "all", subStatus: null, page: 1});
```

#### Pattern 2 — Add Done branch to `segmentedFiles$` switch (analog: lines 79-91)

**Existing Active branch** (`transfer-table.component.ts:79-85`):
```typescript
if (state.segment === "active") {
    return files.filter(f =>
        f.status === ViewFile.Status.DOWNLOADING ||
        f.status === ViewFile.Status.QUEUED ||
        f.status === ViewFile.Status.EXTRACTING
    ).toList();
}
```

**Existing Errors branch** (`transfer-table.component.ts:86-91`):
```typescript
if (state.segment === "errors") {
    return files.filter(f =>
        f.status === ViewFile.Status.STOPPED ||
        f.status === ViewFile.Status.DELETED
    ).toList();
}
```

**Pattern to apply** — insert a Done branch with the same structure (per D-06 the group-OR is `DOWNLOADED ∪ EXTRACTED`):
```typescript
if (state.segment === "done") {
    return files.filter(f =>
        f.status === ViewFile.Status.DOWNLOADED ||
        f.status === ViewFile.Status.EXTRACTED
    ).toList();
}
```

Add the new Active branch member (Pending = `ViewFile.Status.DEFAULT`) into the existing Active filter:
```typescript
if (state.segment === "active") {
    return files.filter(f =>
        f.status === ViewFile.Status.DEFAULT ||      // NEW (Pending)
        f.status === ViewFile.Status.DOWNLOADING ||
        f.status === ViewFile.Status.QUEUED ||
        f.status === ViewFile.Status.EXTRACTING
    ).toList();
}
```

> NOTE: The sub-status code path at line 76 (`if (state.subStatus != null && state.segment !== "all")`) already filters to a single `ViewFile.Status` regardless of which parent segment is active, so it works for `subStatus = DEFAULT/DOWNLOADED/EXTRACTED` with **zero changes** once the parent branches accept `'done'` and the template emits the correct sub-status.

#### Pattern 3 — `onSegmentChange` already handles N segments (analog: lines 158-172)

**Existing** (`transfer-table.component.ts:158-172`):
```typescript
onSegmentChange(segment: "all" | "active" | "errors"): void {
    if (segment !== "all" && this.activeSegment === segment) {
        // Second click on same expandable parent — collapse to All
        this.activeSegment = "all";
        this.activeSubStatus = null;
        this.currentPage = 1;
        this.filterState$.next({segment: "all", subStatus: null, page: 1});
    } else {
        this.activeSegment = segment;
        this.activeSubStatus = null;
        this.currentPage = 1;
        this.filterState$.next({segment, subStatus: null, page: 1});
    }
    this.fileSelectionService.clearSelection();
}
```

**Pattern to apply:** **Only the parameter union changes** — extend to `"all" | "active" | "done" | "errors"`. The body works for any expandable segment; the design spec's state-transition table (and CONTEXT D-08) explicitly require Done to behave identically to Active/Errors. **No body changes required**.

#### Pattern 4 — URL query-param hydration on init (NEW PATTERN — no codebase analog)

**No existing analog.** A search of the entire `src/angular` tree returned zero hits for `Router.navigate`, `queryParamsHandling`, or `ActivatedRoute.queryParamMap`. The closest prior art is `AppComponent:36` which injects `Router` and listens to `router.events`, but does not navigate or read query params:

`pages/main/app.component.ts:36-50` (DI shape only — for reference):
```typescript
constructor(private router: Router, ...) { ... }

ngOnInit(): void {
    this.router.events.pipe(takeUntil(this.destroy$)).subscribe(...);
}
```

**Pattern the planner must establish (per CONTEXT D-09 / D-10 / D-11):**

1. Add `Router` and `ActivatedRoute` to the constructor params (or use `inject()` to match the existing `inject(DestroyRef)` pattern at line 59).
2. Implement `OnInit` (analog: `DashboardLogPaneComponent` at `dashboard-log-pane.component.ts:21,35`).
3. **Hydrate before the first `filterState$.next()`.** The current constructor does not call `.next()` after the BehaviorSubject is constructed (line 57 sets the initial value `{segment: "all", subStatus: null, page: 1}`); the first emission to subscribers happens when the template subscribes via `async`. So the constructor stays mostly unchanged, but `ngOnInit` must read query params and call `filterState$.next(...)` synchronously before the view first subscribes. Use the snapshot:
   ```typescript
   const segParam = this.route.snapshot.queryParamMap.get("segment");
   const subParam = this.route.snapshot.queryParamMap.get("sub");
   ```
4. **Validation** (D-11): If `segment` is not in `{"all","active","done","errors"}`, fall back silently to `"all"` (no toast, no console warn). If `sub` is not a value of `ViewFile.Status`, OR the sub doesn't belong to the named segment (e.g. `?segment=active&sub=stopped`), fall back to the parent segment with no sub. The valid sub-per-segment map matches the segmentedFiles$ branches:
   - `active` → `{DEFAULT, DOWNLOADING, QUEUED, EXTRACTING}`
   - `done`   → `{DOWNLOADED, EXTRACTED}`
   - `errors` → `{STOPPED, DELETED}`
5. After validation, set `this.activeSegment` + `this.activeSubStatus` and call `this.filterState$.next({segment, subStatus, page: 1})`.

#### Pattern 5 — URL query-param write-back on change (NEW PATTERN — no codebase analog)

**Pattern the planner must establish (per CONTEXT D-09 / D-10):**

Add a private helper called from the end of `onSegmentChange` and `onSubStatusChange`:
```typescript
private _writeFilterToUrl(): void {
    const queryParams: {segment?: string | null; sub?: string | null} = {};
    if (this.activeSegment === "all") {
        // Clear both — do not pollute URL with default state
        queryParams.segment = null;
        queryParams.sub = null;
    } else {
        queryParams.segment = this.activeSegment;
        queryParams.sub = this.activeSubStatus ?? null;  // null clears the param under merge
    }
    this.router.navigate([], {
        relativeTo: this.route,
        queryParams,
        queryParamsHandling: "merge",
        replaceUrl: true,   // recommended — filter clicks shouldn't bloat history
    });
}
```

> **Discretionary note (CONTEXT "Claude's Discretion"):** Use the literal `ViewFile.Status` enum-string for `sub` (e.g. `?sub=downloading`, `?sub=default`). This matches the enum values at `view-file.ts:90-100` and adds zero mapping layer.

> **`replaceUrl: true`** is a recommendation, not a CONTEXT decision. CONTEXT did not lock history behavior. If the planner wants browser-back-as-undo, drop `replaceUrl`. CONTEXT defers "Browser back/forward as filter navigation" to a follow-up phase (line 133), which suggests `replaceUrl: true` for this phase to avoid accidentally shipping that behavior half-finished.

#### Pattern 6 — Selection-clear and page-reset still inherited (D-12, D-13)

The existing `onSegmentChange` line 171 (`this.fileSelectionService.clearSelection()`), `onSubStatusChange` line 183 + 193, and `combineLatest` flow at lines 134-139 are unchanged. **No code change needed** for selection/page resets — `'done'` inherits both for free. This is locked-in carry-forward from Phase 72 D-04.

---

### `src/angular/src/app/pages/files/transfer-table.component.html` (template, event-driven)

**Analog:** existing Active/Errors blocks at `transfer-table.component.html:28-95`.

#### Pattern 1 — Done parent button + expand block (analog: Errors lines 67-95)

**Existing Errors parent button** (`transfer-table.component.html:67-75`):
```html
<button type="button" class="btn-segment"
        [class.btn-segment--parent-active]="activeSegment === 'errors' && activeSubStatus === null"
        [class.btn-segment--parent-expanded]="activeSegment === 'errors' && activeSubStatus !== null"
        (click)="onSegmentChange('errors')">
  Errors
  <i class="ph-bold"
     [class.ph-caret-down]="activeSegment !== 'errors'"
     [class.ph-caret-up]="activeSegment === 'errors'"></i>
</button>
```

**Existing Errors expand block** (`transfer-table.component.html:77-95`):
```html
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
```

**Pattern to apply (per D-04: order is Active, Done, Errors):** Insert the Done parent button + expand block **between** the Active expand block (ends line 64) and the Errors parent button (starts line 67). Mirror Errors verbatim, substituting `'errors'` → `'done'`, label `Errors` → `Done`, and the two subs → `DOWNLOADED` (label "Downloaded") and `EXTRACTED` (label "Extracted").

#### Pattern 2 — Pending sub-button under Active (analog: Syncing button at lines 40-47)

**Existing Syncing sub-button** (`transfer-table.component.html:40-47`):
```html
<button type="button" class="btn-sub"
        [class.active]="activeSubStatus === ViewFileStatus.DOWNLOADING"
        (click)="onSubStatusChange(ViewFileStatus.DOWNLOADING)">
  @if (activeSubStatus === ViewFileStatus.DOWNLOADING) {
    <span class="accent-dot"></span>
  }
  Syncing
</button>
```

**Pattern to apply (per CONTEXT D-05 + "Claude's Discretion" recommendation: Pending = first sub, left-most):** Insert a new sub-button **immediately after the `<div class="segment-divider"></div>` at line 39 and before the existing Syncing button at line 40**. Reuse the markup verbatim, substituting `DOWNLOADING` → `DEFAULT` and `Syncing` → `Pending`:
```html
<button type="button" class="btn-sub"
        [class.active]="activeSubStatus === ViewFileStatus.DEFAULT"
        (click)="onSubStatusChange(ViewFileStatus.DEFAULT)">
  @if (activeSubStatus === ViewFileStatus.DEFAULT) {
    <span class="accent-dot"></span>
  }
  Pending
</button>
```

> **Per `feedback_design_spec_rigor.md`:** Do NOT add new SCSS classes, do NOT change the markup shape, do NOT introduce per-instance style attributes. The new Pending sub must be byte-identical in attribute set to the existing sub-buttons (only label + enum value change).

---

### `src/angular/src/app/pages/files/transfer-table.component.scss` (styles, verify only)

**Analog:** the existing `.btn-segment`, `.btn-segment--parent-active`, `.btn-segment--parent-expanded`, `.btn-sub`, `.btn-sub.active`, `.accent-dot`, `.segment-divider` rules at `transfer-table.component.scss:141-244`.

**Pattern to apply:** **No code changes.** Verify after the template change that:
- The new Done parent renders identically to Errors (same paddings, same hover state, same chevron behavior).
- The new Pending / Downloaded / Extracted subs render identically to Syncing / Queued / Extracting / Failed / Deleted (same dimmer text, same `.active` amber treatment, same `.accent-dot` glow).

The existing rule at `transfer-table.component.scss:127-139` already hides `.segment-filters` below 768px (CONTEXT D-14), so the new Done parent and all 4 new sub-buttons inherit the mobile-hidden behavior with **zero new media queries**.

---

### `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` (unit test)

**Analog:** the existing per-status sub-status test block at lines 358-473 (one `it()` per status, identical shape).

#### Pattern 1 — Add 4 new sub-status filter tests (analog: lines 360-381)

**Existing per-status test** (`transfer-table.component.spec.ts:360-381`):
```typescript
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
    const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
    tick();
    sub.unsubscribe();

    expect(pagedFiles.length).toBe(1);
    expect(pagedFiles[0].name).toBe("dl-1");
}));
```

**Pattern to apply:** Mirror this `it()` 4 times for the new statuses:
- `DEFAULT` (Pending) under `active`
- `DOWNLOADED` under `done`
- `EXTRACTED` under `done`
- (Optional sanity) Done parent group-OR — `onSegmentChange("done")` with no sub-status returns `DOWNLOADED ∪ EXTRACTED` (analog: existing "should filter to active statuses" at line 213 and "should filter to error statuses" at line 238).

#### Pattern 2 — Update segment count assertion (existing line 182)

**Existing** (`transfer-table.component.spec.ts:182-188`):
```typescript
it("should render 3 parent segment filter buttons", () => {
    const buttons = fixture.nativeElement.querySelectorAll(".btn-segment");
    expect(buttons.length).toBe(3);
    expect(buttons[0].textContent).toContain("All");
    expect(buttons[1].textContent).toContain("Active");
    expect(buttons[2].textContent).toContain("Errors");
});
```

**Pattern to apply:** Bump count to 4 and add `Done` between Active and Errors. Also update the `TEST_TEMPLATE` constant at lines 20-69 to add the Done parent + expand block + the new Pending sub-button (mirror the existing Active/Errors entries verbatim).

#### Pattern 3 — Add URL hydration + write-back tests (NEW PATTERN — no in-file analog)

**No exact analog.** The closest is the existing TestBed setup at lines 142-153 (where the planner will need to add `ActivatedRoute` and `Router` providers). Mocking shape:

```typescript
// Mocks (place near top of describe)
const mockQueryParamMap: { [k: string]: string | null } = {};
const mockActivatedRoute = {
    snapshot: {
        queryParamMap: { get: (k: string) => mockQueryParamMap[k] ?? null }
    }
};
const mockRouter = { navigate: jasmine.createSpy("navigate") };

// In TestBed.providers
{provide: ActivatedRoute, useValue: mockActivatedRoute},
{provide: Router, useValue: mockRouter},
```

**Suggested test cases (per CONTEXT D-09 / D-11):**
- Hydrates `activeSegment = "done"` from `?segment=done`
- Hydrates `activeSubStatus = DOWNLOADED` from `?segment=done&sub=downloaded`
- Falls back to `"all"` for invalid segment (`?segment=garbage`)
- Falls back to parent segment with no sub when sub doesn't belong to segment (`?segment=active&sub=stopped`)
- Calls `router.navigate` with `{queryParams: {segment: "done", sub: null}, queryParamsHandling: "merge"}` on `onSegmentChange("done")`
- Calls `router.navigate` with `{queryParams: {segment: "done", sub: "downloaded"}, ...}` on subsequent `onSubStatusChange(DOWNLOADED)`
- Calls `router.navigate` with `{queryParams: {segment: null, sub: null}, ...}` on `onSegmentChange("all")` (clears params)

#### Pattern 4 — Selection-clear and page-reset already covered (D-12, D-13)

The existing `selection clearing (D-04)` describe block at lines 532-581 already covers `onSegmentChange` and `onSubStatusChange`. **No new tests needed** — the existing tests will pass for `'done'` once the type union is widened. Optionally add one test that calls `component.onSegmentChange("done")` and asserts `selectionService.getSelectedCount() === 0` to lock in coverage explicitly.

---

### `src/e2e/tests/dashboard.page.ts` (e2e page object, locator-only)

**Analog:** existing `getActionButton` and `getActionBar` locators at `dashboard.page.ts:64-70`.

**Existing** (`dashboard.page.ts:64-70`):
```typescript
getActionBar(): Locator {
    return this.page.locator('app-bulk-actions-bar .bulk-actions-bar');
}

getActionButton(name: 'Queue' | 'Stop' | 'Extract' | 'Delete Local' | 'Delete Remote'): Locator {
    return this.page.locator('app-bulk-actions-bar').getByRole('button', { name, exact: true });
}
```

**Pattern to apply:** Add two parallel methods scoped to `.segment-filters` (the container at `transfer-table.component.html:20`):

```typescript
getSegmentButton(name: 'All' | 'Active' | 'Done' | 'Errors'): Locator {
    return this.page.locator('.segment-filters').getByRole('button', { name, exact: true });
}

getSubButton(name: 'Pending' | 'Syncing' | 'Queued' | 'Extracting' | 'Downloaded' | 'Extracted' | 'Failed' | 'Deleted'): Locator {
    return this.page.locator('.segment-filters button.btn-sub').getByText(name, { exact: true });
}
```

> **Note:** the `getByText` (not `getByRole({name})`) for sub-buttons avoids accidentally matching the `.accent-dot`'s aria. Sub-buttons contain a `<span class="accent-dot">` + label text node; `getByText` selects on the visible label.

---

### `src/e2e/tests/dashboard.page.spec.ts` (e2e spec, request-response)

**Analog:** existing tests in `dashboard.page.spec.ts` that exercise the action bar (lines 39-47 for show/hide, lines 57-65 for "all the action buttons").

**Existing show/hide pattern** (`dashboard.page.spec.ts:39-47`):
```typescript
test('should show and hide action buttons on select', async () => {
    await expect(dashboardPage.getActionBar()).not.toBeVisible();

    await dashboardPage.selectFileByName(TEST_FILE);
    await expect(dashboardPage.getActionBar()).toBeVisible();

    await dashboardPage.selectFileByName(TEST_FILE);
    await expect(dashboardPage.getActionBar()).not.toBeVisible();
});
```

**Pattern to apply:** Add a small set of new tests using the new selectors. CONTEXT does not specify exact E2E coverage — keep it minimal and parity-focused with the existing Phase 72 tests:

```typescript
test('should expand Done segment to reveal Downloaded and Extracted subs', async () => {
    await expect(dashboardPage.getSubButton('Downloaded')).not.toBeVisible();
    await dashboardPage.getSegmentButton('Done').click();
    await expect(dashboardPage.getSubButton('Downloaded')).toBeVisible();
    await expect(dashboardPage.getSubButton('Extracted')).toBeVisible();
});

test('should reveal Pending sub under Active', async () => {
    await dashboardPage.getSegmentButton('Active').click();
    await expect(dashboardPage.getSubButton('Pending')).toBeVisible();
});

test('should persist Done filter via URL query param', async ({ page }) => {
    await dashboardPage.getSegmentButton('Done').click();
    await expect(page).toHaveURL(/[?&]segment=done\b/);
});
```

> **Selection-clearing carry-forward (CONTEXT D-12):** the existing Phase 72 selection tests at `dashboard.page.spec.ts:39-75` already cover that filter changes don't break selection. They will continue to pass for `'done'` with no edits because the existing TEST_FILE click path is independent of which segment is selected.

---

## Shared Patterns

### Pattern A — `ViewFileStatus` enum exposure (already applied)

**Source:** `transfer-table.component.ts:30` — `readonly ViewFileStatus = ViewFile.Status;`
**Apply to:** template references to enum values (already used by Syncing/Queued/Extracting/Failed/Deleted; the new Pending/Downloaded/Extracted just use the same `ViewFileStatus.DEFAULT/DOWNLOADED/EXTRACTED`).
**No code change needed** — the enum is already template-accessible.

### Pattern B — `inject()` for new DI dependencies (analog: `transfer-table.component.ts:59`)

**Existing:**
```typescript
private destroyRef = inject(DestroyRef);
```

**Apply to:** `Router` and `ActivatedRoute` if the planner prefers `inject()` over constructor params for the new query-param wiring. Either style is consistent with the file (constructor uses `private` params for services; `inject()` is used for `DestroyRef`).

### Pattern C — `feedback_design_spec_rigor.md` rule

**Source:** `/Users/julianamacbook/.claude/projects/-Users-julianamacbook-seedsyncarr/memory/feedback_design_spec_rigor.md` — "Port AIDesigner HTML identically, no approximations."
**Apply to:** every new HTML element. The new Done parent and the 4 new sub-buttons MUST reuse the existing class names verbatim. No new SCSS classes, no inline styles, no approximate token swaps.

### Pattern D — Selection cleared on filter change (Phase 72 D-04, locked carry-forward)

**Source:** `transfer-table.component.ts:171, 183, 193, 138`
**Apply to:** All branches of `onSegmentChange` and `onSubStatusChange`. **Already wired** — `'done'` inherits this for free, and the existing unit tests at lines 532-581 will continue to enforce it.

### Pattern E — Page reset on filter change (D-13, locked carry-forward)

**Source:** `transfer-table.component.ts:163, 168, 181, 187` (each filter mutator sets `this.currentPage = 1` and emits `{..., page: 1}`).
**Apply to:** Done segment + new sub-status changes — already inherited via the unchanged onSegmentChange / onSubStatusChange bodies.

---

## No Analog Found

| File / Pattern | Role | Data Flow | Reason |
|---|---|---|---|
| URL query-param hydration on init | component init | request-response | `ActivatedRoute.queryParamMap` is not used anywhere in `src/angular`. Planner must follow the design doc + Angular API contract directly. |
| URL query-param write-back via `Router.navigate` | event-driven | request-response | `Router.navigate` with `queryParamsHandling: 'merge'` is not used anywhere in `src/angular`. The only `Router` usage today is `AppComponent` listening to `router.events`. Planner must follow the Angular API contract directly. |

For both new patterns, the suggested implementation shapes above (`Pattern 4` and `Pattern 5` under `transfer-table.component.ts`) are derived from CONTEXT D-09 / D-10 / D-11 + Angular's documented `NavigationExtras.queryParamsHandling` contract.

---

## Metadata

**Analog search scope:**
- `src/angular/src/app/pages/files/` (component family)
- `src/angular/src/app/pages/main/` (Router DI prior art)
- `src/angular/src/app/tests/unittests/pages/files/` (unit-test scaffolding)
- `src/e2e/tests/` (page-object + spec analogs)
- `src/angular/src/app/services/files/view-file.ts` (status enum)
- Repo-wide grep for `Router.navigate`, `queryParamsHandling`, `ActivatedRoute`, `queryParamMap`

**Files scanned:** ~15 (transfer-table .ts/.html/.scss + spec, dashboard.page.ts + spec, view-file.ts, app.config.ts, app.component.ts, routes.ts, dashboard-log-pane.component.ts, bulk-actions-bar.component.spec.ts, files-page directory listing)

**Pattern extraction date:** 2026-04-19

**Phase:** 73-dashboard-filter-for-every-torrent-status
