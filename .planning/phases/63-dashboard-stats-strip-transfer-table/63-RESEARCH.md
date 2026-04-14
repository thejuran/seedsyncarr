# Phase 63: Dashboard — Stats Strip & Transfer Table — Research

**Researched:** 2026-04-14
**Domain:** Angular 21 + Bootstrap 5.3 + SCSS — dashboard UI components
**Confidence:** HIGH

## Summary

Phase 63 redesigns the existing `/dashboard` route (currently `FilesPageComponent` + `FileOptionsComponent` + `FileListComponent`) to deliver the Triggarr-style layout shown in the AIDesigner artifact. The work splits into two distinct visual zones: (1) a 4-card stats strip at the top of the page, and (2) a transfer table with search, segmented filters, status badges, animated progress bars, and a pagination footer.

The existing codebase already owns the full data model for files (`ViewFile`, `ViewFileService`) and the server/connection status stream. The stats card data — storage free space, download speed, active/queued counts — is **not present in the current backend API** exposed through the SSE stream. The current `ServerStatus` model only carries `server.up`, `errorMessage`, and scan timestamps. The REQUIREMENTS.md out-of-scope table explicitly states "New backend API endpoints — UI redesign only — use existing data from current API." This is the most important constraint to resolve: stats cards must derive from existing observable data sources or show derived/computed values from `ViewFileService`.

The transfer table UI is a visual redesign of the existing file list. The underlying service architecture (SSE stream → `ModelFileService` → `ViewFileService`) and filtering/sort services are already in place and working. The plan's primary task is to render the same data in the new Triggarr table layout — columns for Status badge, Progress bar, Bandwidth, ETA — and add pagination (not yet implemented).

**Primary recommendation:** Introduce a `DashboardStatsService` that derives all four stat card values from `ViewFileService.files` (active count, queued count, total transfer speed) plus placeholder/mock values for storage (since real disk stats are not in the current API). Redesign `FilesPageComponent` to host the stats strip + table layout. Replace the current card-row `app-file` with a true `<table>` row component for the new Triggarr table style. Add client-side pagination as a pure presentation layer on top of the existing filtered files observable.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Stats strip displays 4 metric cards in responsive grid | Bootstrap `row + col-*` or CSS grid; compute from ViewFileService |
| DASH-02 | Remote Storage card shows free space with progress bar | No backend source; derive placeholder or compute from file sizes; Bootstrap progress component |
| DASH-03 | Local Storage card shows free space with progress bar | Same as DASH-02; use local file sizes from ViewFile.localSize |
| DASH-04 | Download Speed card shows current speed with peak stat | Derived from sum of ViewFile.downloadingSpeed for all DOWNLOADING files |
| DASH-05 | Active Tasks card shows running count with DL/Queued badges | Count DOWNLOADING + QUEUED status files from ViewFileService |
| DASH-06 | Transfer table has search/filter input with magnifying glass icon | Existing ngModel binding to ViewFileOptionsService; add Font Awesome search icon |
| DASH-07 | Transfer table has segmented filter buttons (All/Active/Errors) | New "Active" and "Errors" compound filters mapping to existing StatusFilterCriteria |
| DASH-08 | File rows display status badges (Syncing/Queued/Synced/Failed) with semantic colors | Existing badge system; map new labels: Downloading→Syncing, Downloaded→Synced, Stopped→Failed |
| DASH-09 | File rows show animated striped progress bars with percentage | CSS @keyframes stripe animation; Bootstrap progress or custom SCSS |
| DASH-10 | File rows display bandwidth and ETA columns | ViewFile.downloadingSpeed + eta already in model; add as table columns |
| DASH-11 | Transfer table has pagination footer with page controls | Client-side pagination — slice the filteredFiles list by page; pure component state |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new packages needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @angular/core | ^21.2.8 | Signals, components, OnPush CD | Project standard [VERIFIED: package.json] |
| @angular/common | ^21.2.8 | AsyncPipe, DatePipe | Project standard [VERIFIED: package.json] |
| bootstrap | ^5.3.3 | Grid, progress, badge, pagination utilities | Project standard [VERIFIED: package.json] |
| rxjs | ^7.5.0 | Observables for ViewFileService stream | Project standard [VERIFIED: package.json] |
| immutable | ^5.1.5 | Immutable.List for files collection | Project standard [VERIFIED: package.json] |

### No New Packages Required
All needed primitives exist in the installed stack. The design artifact uses Tailwind + Phosphor Icons but the project out-of-scope table explicitly forbids Tailwind and external icon fonts beyond Font Awesome 4.7. All Tailwind utility classes must be translated to Bootstrap 5 + custom SCSS. All Phosphor Icons must be replaced with Font Awesome 4.7 equivalents.

**Installation:** No new packages to install.

## Architecture Patterns

### Recommended Project Structure Changes

The stats strip and transfer table redesign lives entirely inside the existing `files` page directory. No new route is needed.

```
src/angular/src/app/
├── pages/
│   └── files/
│       ├── files-page.component.html      # NEW: stats strip + table shell layout
│       ├── files-page.component.ts        # MODIFY: inject DashboardStatsService
│       ├── files-page.component.scss      # NEW: page-level layout SCSS
│       ├── stats-strip.component.html     # NEW: 4-card stat strip
│       ├── stats-strip.component.ts       # NEW: subscribes to DashboardStatsService
│       ├── stats-strip.component.scss     # NEW: card styles
│       ├── transfer-table.component.html  # NEW: table with search/filter/pagination
│       ├── transfer-table.component.ts    # NEW: owns pagination state + filter dispatch
│       ├── transfer-table.component.scss  # NEW: table SCSS
│       ├── transfer-row.component.html    # NEW: single table row
│       ├── transfer-row.component.ts      # NEW: replaces file.component for table view
│       └── transfer-row.component.scss    # NEW: row-level SCSS
└── services/
    └── files/
        └── dashboard-stats.service.ts     # NEW: derives stats from ViewFileService
```

**Existing files to preserve unchanged:** `file.component.*`, `file-options.component.*`, `file-list.component.*`, `bulk-actions-bar.component.*`, `file-actions-bar.component.*`. These are still used by the detail/action patterns; the new transfer table is a parallel view layer.

**Alternative simpler approach:** Extend `files-page.component` to host both the stats strip and an enhanced `file-list` with pagination. This avoids creating many new component files but makes each file larger. Given the scope of 11 requirements and the Triggarr table redesign, separate components are cleaner.

### Pattern 1: Stats Derived from ViewFileService

**What:** A `DashboardStatsService` subscribes to `ViewFileService.files` and emits a typed stats object.
**When to use:** When stats data can be computed from the existing file model (active count, speed, queued count).

```typescript
// Source: [ASSUMED — derived pattern from existing ViewFileService usage in codebase]
export interface DashboardStats {
  downloadingCount: number;
  queuedCount: number;
  totalSpeedBps: number;
  peakSpeedBps: number;
  // Storage placeholder: not available from API
  remoteFreeBytes: number | null;
  localFreeBytes: number | null;
  remoteTotalBytes: number | null;
  localTotalBytes: number | null;
}

@Injectable()
export class DashboardStatsService implements OnDestroy {
  private destroy$ = new Subject<void>();
  private _stats$ = new BehaviorSubject<DashboardStats>(/* zero state */);
  private _peakSpeed = 0;

  constructor(private viewFileService: ViewFileService) {
    this.viewFileService.files.pipe(takeUntil(this.destroy$)).subscribe(files => {
      const downloading = files.filter(f => f.status === ViewFile.Status.DOWNLOADING);
      const queued = files.filter(f => f.status === ViewFile.Status.QUEUED);
      const totalSpeed = downloading.reduce((sum, f) => sum + (f.downloadingSpeed ?? 0), 0);
      if (totalSpeed > this._peakSpeed) { this._peakSpeed = totalSpeed; }
      this._stats$.next({
        downloadingCount: downloading.size,
        queuedCount: queued.size,
        totalSpeedBps: totalSpeed,
        peakSpeedBps: this._peakSpeed,
        remoteFreeBytes: null,   // not in current API
        localFreeBytes: null,    // not in current API
        remoteTotalBytes: null,
        localTotalBytes: null,
      });
    });
  }

  get stats$(): Observable<DashboardStats> { return this._stats$.asObservable(); }
  ngOnDestroy() { /* cleanup */ }
}
```

### Pattern 2: Storage Cards with Null-Safe Progress Bars

Since `remoteFreeBytes` and `localFreeBytes` are null (no API source), the storage cards must degrade gracefully. The plan must choose one of two approaches:

**Option A — Show "N/A":** Render "—" in the value slot and a disabled/empty progress bar when data is null.
**Option B — Derive from file sizes:** Remote storage can approximate used space as the sum of all `ViewFile.remoteSize` values; local as sum of `ViewFile.localSize`. These are not "free space" but "total tracked usage" — still meaningful, but labeling must be accurate.

**Recommendation:** Option B for the progress bar (show tracked usage percentage relative to total tracked sizes), with "tracked usage" as the label sub-stat. This gives live data without adding a backend endpoint. [ASSUMED — no authoritative source for what is most useful; planner should confirm with user if needed]

### Pattern 3: Client-Side Pagination

**What:** Pure presentation state inside `TransferTableComponent`. No service changes needed.
**When to use:** The full filtered files list comes from `ViewFileService.filteredFiles`. Pagination slices it.

```typescript
// Source: [ASSUMED — standard Angular pagination pattern]
// In TransferTableComponent:
pageSize = 10;
currentPage = 1;

get pagedFiles(): ViewFile[] {
  const start = (this.currentPage - 1) * this.pageSize;
  return this.visibleFiles.slice(start, start + this.pageSize);
}

get totalPages(): number {
  return Math.ceil(this.visibleFiles.length / this.pageSize);
}
```

When filter changes (via `ViewFileOptionsService`), reset `currentPage = 1`.

### Pattern 4: All/Active/Errors Segmented Filter

The existing filter bar uses individual status pills (Downloading, Queued, Downloaded, etc.). The Triggarr design uses 3 compound filters: **All**, **Active**, **Errors**.

Mapping to existing `StatusFilterCriteria`:
- **All** → `selectedStatusFilter = null` (clears filter)
- **Active** → custom: show files where `status === DOWNLOADING || status === QUEUED || status === EXTRACTING`
- **Errors** → custom: show files where `status === STOPPED || status === DELETED`

The existing `ViewFileFilterService` uses a single `ViewFileFilterCriteria` interface. A new `CompoundStatusFilterCriteria` implementing `ViewFileFilterCriteria` can handle the Active/Errors compound cases without changing the service.

```typescript
// Source: [VERIFIED: view-file-filter.service.ts — existing pattern]
class CompoundStatusFilterCriteria implements ViewFileFilterCriteria {
  constructor(private statuses: ViewFile.Status[]) {}
  meetsCriteria(f: ViewFile): boolean {
    return this.statuses.includes(f.status!);
  }
}
```

### Pattern 5: Animated Striped Progress Bar (SCSS)

The AIDesigner artifact uses Tailwind's `progress-striped` CSS animation. Must be translated to Bootstrap 5 progress + custom SCSS:

```scss
// Source: [VERIFIED: design.html keyframes, translated to Bootstrap/SCSS]
// In transfer-row.component.scss or _common.scss

@keyframes progress-stripe {
  0%   { background-position: 20px 0; }
  100% { background-position: 0 0; }
}

.progress-bar-striped-animated {
  background-image: linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.15) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 255, 255, 0.15) 75%,
    transparent 75%,
    transparent
  );
  background-size: 20px 20px;
  animation: progress-stripe 1s linear infinite;
}
```

Bootstrap 5 also ships `.progress-bar-striped` and `.progress-bar-animated` classes that do this natively. [VERIFIED: styles.scss imports bootstrap/scss/progress]

### Pattern 6: Status Badge Label Mapping

The AIDesigner design uses different badge labels than the current `ViewFile.Status` enum values. The plan must define a label mapping:

| ViewFile.Status | Current Badge | New Triggarr Badge | Color |
|----------------|--------------|-------------------|-------|
| DOWNLOADING | "Downloading" | "Syncing" | amber ($warning) |
| QUEUED | "Queued" | "Queued" | muted sage |
| DOWNLOADED | "Downloaded" | "Synced" | green ($success) |
| STOPPED | "Stopped" | "Failed" | red ($danger) |
| EXTRACTING | "Extracting" | "Extracting" | blue ($info) |
| EXTRACTED | "Extracted" | "Extracted" | blue ($info) |
| DEFAULT | "Default" | (hidden or "—") | muted |

This mapping belongs in `TransferRowComponent` as a static lookup — same pattern as existing `BADGE_CLASSES` in `file.component.ts`. [VERIFIED: file.component.ts lines 41-55]

### Anti-Patterns to Avoid

- **Calling `ng build` to validate** — use `ng lint` and unit tests instead; full builds take >30s.
- **Modifying `ViewFileService` internals** — the service is stable and well-tested. New UI features should be additive (new derived services, new filter criteria classes).
- **Using Tailwind utilities directly** — project forbids Tailwind. All Tailwind classes from design.html must map to Bootstrap equivalents or custom SCSS vars.
- **Adding Phosphor Icons** — project uses Font Awesome 4.7. Map all `ph-*` icons to `fa-*` equivalents (e.g., `ph-magnifying-glass` → `fa-search`, `ph-cloud` → `fa-cloud`, `ph-database` → `fa-database`).
- **Duplicating filter logic** — the existing `ViewFileFilterService` + `ViewFileOptionsService` pipeline handles filtering. New segmented buttons should dispatch through `ViewFileOptionsService.setSelectedStatusFilter()` — do not build a parallel filter state.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Animated striped progress | Custom CSS animation from scratch | Bootstrap `.progress-bar-striped.progress-bar-animated` | Already imported in styles.scss |
| Responsive 4-col grid | Custom flexbox grid | Bootstrap `row + col-sm-6 col-lg-3` | Handles all breakpoints consistently |
| Search debounce | Manual `setTimeout` in component | RxJS `debounceTime` via `Subject + pipe` | Already pattern used in codebase |
| File size formatting | Custom pipe | Existing `FileSizePipe` | Already tested and in use |
| ETA formatting | Custom logic | Existing `EtaPipe` | Already tested and in use |
| Date formatting | Custom | Angular `DatePipe` | Already imported in file.component.ts |

## Common Pitfalls

### Pitfall 1: Storage Cards Have No Real Data Source
**What goes wrong:** Designer adds "1.8 TB Free" for Remote Storage and "2.4 TB Free" for Local Storage — but those fields don't exist anywhere in the current SSE/API stream.
**Why it happens:** The AIDesigner artifact uses static placeholder data. REQUIREMENTS.md explicitly bans new backend endpoints.
**How to avoid:** For DASH-02/DASH-03, show derived "tracked usage" data (sum of remote/local file sizes) and label it accurately. Or show a placeholder with "—" for free space. Either way, the implementation must NOT wait for a backend change.
**Warning signs:** If a plan task says "add new API endpoint for disk stats" — that's out of scope.

### Pitfall 2: Breaking the Existing Filter Pipeline
**What goes wrong:** The new All/Active/Errors segmented buttons bypass `ViewFileOptionsService` and maintain their own filter state, causing conflicts with the existing search box.
**Why it happens:** Temptation to simplify the new component by not wiring to the existing service.
**How to avoid:** All filter interactions — including the new segmented buttons — must go through `ViewFileOptionsService.setSelectedStatusFilter()`. The search input already uses `onFilterByName()` in `FileOptionsComponent`. The new table header's search input should do the same.
**Warning signs:** Component maintains `private filteredFiles: ViewFile[]` that is not sourced from `ViewFileService.filteredFiles`.

### Pitfall 3: Pagination Not Resetting on Filter Change
**What goes wrong:** User is on page 3, applies "Active" filter, sees "No results" because page 3 doesn't exist with fewer items.
**Why it happens:** `currentPage` state is not linked to filter changes.
**How to avoid:** Subscribe to `ViewFileOptionsService.options` changes in `TransferTableComponent` and reset `currentPage = 1` whenever filter or search changes.

### Pitfall 4: OnPush Change Detection with Pagination State
**What goes wrong:** Page number changes but the template doesn't update because the component uses `ChangeDetectionStrategy.OnPush`.
**Why it happens:** Pagination is component state mutation (not observable), so OnPush won't detect it automatically.
**How to avoid:** Either use `ChangeDetectorRef.markForCheck()` on page changes, or use a `BehaviorSubject<number>` for `currentPage` and derive `pagedFiles$` as an observable.

### Pitfall 5: Overwriting Existing file.component Template
**What goes wrong:** Developer modifies `file.component.html` to match the new table row design, breaking the detail panel / actions bar / bulk selection.
**Why it happens:** `file.component` appears to be the row — natural to edit it.
**How to avoid:** Create a NEW `transfer-row.component` for the Triggarr table view. Keep `file.component` intact for now. The `file-list.component` and action bars depend on it; removing them is out of scope for Phase 63.

### Pitfall 6: Font Awesome Icon Gaps
**What goes wrong:** Icon names from the design artifact (`ph-magnifying-glass`, `ph-cloud`, `ph-hard-drives`) don't exist in Font Awesome 4.7.
**Why it happens:** Design uses Phosphor Icons; project uses FA 4.7.
**How to avoid:** Use this mapping table:
| Phosphor | Font Awesome 4.7 |
|----------|-----------------|
| `ph-magnifying-glass` | `fa-search` |
| `ph-cloud` | `fa-cloud` |
| `ph-database` | `fa-database` |
| `ph-arrow-down-right` | `fa-arrow-down` |
| `ph-list-numbers` | `fa-tasks` |
| `ph-clock-clockwise` | `fa-clock-o` |
| `ph-check` | `fa-check` |
| `ph-warning-circle` | `fa-exclamation-circle` |
| `ph-arrow-down` (animate) | `fa-arrow-down` |

## Code Examples

Verified patterns from the codebase:

### Bootstrap Progress Bar (striped + animated)
```html
<!-- Source: Bootstrap 5.3 — already imported in styles.scss -->
<div class="progress" style="height: 6px;">
  <div class="progress-bar progress-bar-striped progress-bar-animated bg-warning"
       role="progressbar"
       [style.width.%]="file.percentDownloaded ?? 0"
       [attr.aria-valuenow]="file.percentDownloaded ?? 0"
       aria-valuemin="0"
       aria-valuemax="100">
  </div>
</div>
```

### Stat Card (Bootstrap grid + custom SCSS)
```html
<!-- Source: [ASSUMED — Bootstrap col pattern aligned with design.html structure] -->
<div class="row g-3 mb-4">
  <div class="col-12 col-sm-6 col-lg-3">
    <div class="stat-card">
      <div class="stat-label"><i class="fa fa-cloud"></i> Remote Storage</div>
      <div class="stat-value">{{ remoteTrackedUsage | fileSize:2 }} <span class="stat-unit">tracked</span></div>
      <div class="progress stat-progress mt-2">
        <div class="progress-bar bg-warning" [style.width.%]="remoteUsagePct"></div>
      </div>
    </div>
  </div>
</div>
```

### Segmented Filter Buttons (Bootstrap btn-group)
```html
<!-- Source: [VERIFIED: Bootstrap 5.3 btn-group pattern, styles.scss imports button-group] -->
<div class="btn-group btn-group-sm filter-segment" role="group">
  <button type="button" class="btn"
    [class.active]="activeFilter === 'all'"
    (click)="onSetFilter('all')">All</button>
  <button type="button" class="btn"
    [class.active]="activeFilter === 'active'"
    (click)="onSetFilter('active')">Active</button>
  <button type="button" class="btn"
    [class.active]="activeFilter === 'errors'"
    (click)="onSetFilter('errors')">Errors</button>
</div>
```

### Status Badge Lookup (existing pattern to replicate)
```typescript
// Source: [VERIFIED: file.component.ts lines 41-55]
private static readonly TRANSFER_BADGE_LABELS: Record<string, string> = {
  [ViewFile.Status.DOWNLOADING]: "Syncing",
  [ViewFile.Status.QUEUED]:      "Queued",
  [ViewFile.Status.DOWNLOADED]:  "Synced",
  [ViewFile.Status.STOPPED]:     "Failed",
  [ViewFile.Status.EXTRACTING]:  "Extracting",
  [ViewFile.Status.EXTRACTED]:   "Extracted",
  [ViewFile.Status.DEFAULT]:     "—",
  [ViewFile.Status.DELETED]:     "Deleted",
};
```

### Pagination Slice Pattern
```typescript
// Source: [ASSUMED — standard Angular pagination]
// In TransferTableComponent — async pipe compatible version
pagedFiles$: Observable<ViewFile[]>;

private pageSubject = new BehaviorSubject<number>(1);
readonly pageSize = 10;

constructor(private viewFileService: ViewFileService) {
  this.pagedFiles$ = combineLatest([
    this.viewFileService.filteredFiles,
    this.pageSubject
  ]).pipe(
    map(([files, page]) => {
      const start = (page - 1) * this.pageSize;
      return files.slice(start, start + this.pageSize).toArray();
    })
  );
}
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Custom keyframe animation for striped bars | Bootstrap `.progress-bar-striped.progress-bar-animated` | Already available; no new CSS needed |
| Single-file card/row component (`file.component`) | Separate table row component (`transfer-row.component`) | Cleaner separation, keeps existing component intact |

**Deprecated/outdated in design artifact:**
- Tailwind CSS classes: translate all to Bootstrap 5 + SCSS vars
- Phosphor Icons: replace with Font Awesome 4.7 equivalents

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Storage free space (remote/local) is not available in the current SSE API | Pitfall 1 / Stats Pattern | If the API does have disk stats on an undiscovered endpoint, the cards could show real data instead of derived values |
| A2 | `DashboardStatsService` should be a new injectable derived from `ViewFileService` | Architecture Pattern 1 | If the planner prefers inline logic in the component, the service layer is not strictly needed |
| A3 | Storage cards should show "tracked usage" derived from file sizes when real disk info is unavailable | Pattern 2 | If the preference is to show "—" instead, the progress bars become static/empty |
| A4 | Pagination page size of 10 is appropriate | Pattern 3 | Configurable if user prefers a different default |
| A5 | `transfer-row.component` should be a new standalone component, not a modification of `file.component` | Architecture Pattern | Could edit file.component to support both modes via @Input flag, but that increases coupling |

## Open Questions

1. **Remote/Local Storage Cards — what to show?**
   - What we know: `ViewFile` has `localSize` and `remoteSize` per file; no disk free-space data in current API
   - What's unclear: Whether to show aggregate tracked file sizes (as a proxy), or just "—" placeholders
   - Recommendation: Show aggregate tracked usage with "tracked" sub-label; plan should confirm with user if a specific presentation is preferred

2. **Existing `file-options.component` — keep or replace?**
   - What we know: `file-options` currently renders the status filter pills and sort options at the top of the files page
   - What's unclear: Phase 63 replaces these with the new table header (search + segmented All/Active/Errors). Should `file-options` be hidden, removed, or evolved?
   - Recommendation: The new `transfer-table.component` should own search + segmented filter in its header row. The `file-options` filter pills can be hidden or conditionally shown via CSS (not deleted — they're needed by Phase 64+ or may be desired by user). Confirm scope in plan.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Angular CLI | Build/serve | Yes | ^21.2.7 | — |
| Bootstrap 5.3 | Progress, grid, badges | Yes | ^5.3.3 | — |
| Font Awesome 4.7 | Icons | Yes | ^4.7.0 | — |
| RxJS | Observable composition | Yes | ^7.5.0 | — |
| Karma/Jasmine | Unit tests | Yes | ^6.x | — |
| Playwright | E2E tests | Yes | ^1.59.1 | — |

No missing dependencies.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Karma + Jasmine (unit), Playwright (E2E) |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `cd src/angular && ng test --watch=false --browsers=ChromeHeadless` |
| Full suite command | `cd src/angular && ng test --watch=false --browsers=ChromeHeadless` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | 4 stat cards rendered in responsive grid | Playwright smoke | `cd src/e2e && npx playwright test --grep "stats"` | No — Wave 0 |
| DASH-02 | Remote storage progress bar present | Playwright smoke | same | No — Wave 0 |
| DASH-03 | Local storage progress bar present | Playwright smoke | same | No — Wave 0 |
| DASH-04 | Download speed card shows speed value | Unit (DashboardStatsService) | `ng test --include="**/dashboard-stats*"` | No — Wave 0 |
| DASH-05 | Active tasks count computed correctly | Unit (DashboardStatsService) | same | No — Wave 0 |
| DASH-06 | Search input filters table rows | Playwright smoke | `npx playwright test --grep "filter"` | No — Wave 0 |
| DASH-07 | All/Active/Errors buttons narrow rows | Playwright smoke | same | No — Wave 0 |
| DASH-08 | Status badges render with semantic colors | Playwright visual / unit | `ng test --include="**/transfer-row*"` | No — Wave 0 |
| DASH-09 | Animated striped progress bars visible | Playwright smoke | `npx playwright test --grep "progress"` | No — Wave 0 |
| DASH-10 | Bandwidth + ETA columns present in rows | Unit (transfer-row) | `ng test --include="**/transfer-row*"` | No — Wave 0 |
| DASH-11 | Pagination footer updates displayed rows | Unit (transfer-table) | `ng test --include="**/transfer-table*"` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `cd src/angular && ng lint`
- **Per wave merge:** `cd src/angular && ng test --watch=false --browsers=ChromeHeadless`
- **Phase gate:** Full unit suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/angular/src/app/services/files/dashboard-stats.service.spec.ts` — covers DASH-04, DASH-05
- [ ] `src/angular/src/app/pages/files/transfer-row.component.spec.ts` — covers DASH-08, DASH-10
- [ ] `src/angular/src/app/pages/files/transfer-table.component.spec.ts` — covers DASH-11
- [ ] `src/e2e/tests/dashboard-stats.spec.ts` — smoke tests for DASH-01 through DASH-09

## Security Domain

No new authentication, session management, or API endpoints introduced. Phase 63 is purely presentational.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | Yes (search input) | Existing Angular template binding — no direct DOM manipulation; no injection risk |
| V6 Cryptography | No | — |

The search input uses Angular's `[(ngModel)]` two-way binding which sanitizes output by default. No raw `innerHTML` or DOM injection. [VERIFIED: file-options.component.html uses FormsModule ngModel]

## Sources

### Primary (HIGH confidence)
- `src/angular/src/app/pages/files/` — all existing component files read directly
- `src/angular/src/app/services/files/view-file.ts` — data model
- `src/angular/src/app/services/files/view-file.service.ts` — filtering and data flow
- `src/angular/src/app/common/_bootstrap-variables.scss` — palette tokens
- `src/angular/src/styles.scss` — Bootstrap imports confirmed
- `src/angular/package.json` — dependency versions confirmed
- `.aidesigner/runs/2026-04-14T03-20-41-363Z.../design.html` — visual spec artifact
- `.planning/REQUIREMENTS.md` — out-of-scope table (no new backend endpoints, no Tailwind, FA 4.7 only)

### Secondary (MEDIUM confidence)
- Bootstrap 5.3 progress docs — `.progress-bar-striped` and `.progress-bar-animated` classes [ASSUMED: in Bootstrap 5.3, known from training; verified indirectly by styles.scss importing `bootstrap/scss/progress`]

### Tertiary (LOW confidence)
- Storage card "tracked usage" derivation approach — [ASSUMED] no authoritative guidance in REQUIREMENTS.md for this edge case

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified from package.json and source files
- Architecture: HIGH — all patterns derived from existing codebase conventions
- Pitfalls: HIGH — data availability gap (DASH-02/03) verified by reading ServerStatus + ServerStatusService source
- Storage card data: LOW — approach is assumed; user confirmation may be needed

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable stack)
