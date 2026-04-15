---
phase: 63-dashboard-stats-strip-transfer-table
reviewed: 2026-04-14T12:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/angular/src/app/services/files/dashboard-stats.service.ts
  - src/angular/src/app/pages/files/stats-strip.component.ts
  - src/angular/src/app/pages/files/stats-strip.component.html
  - src/angular/src/app/pages/files/stats-strip.component.scss
  - src/angular/src/app/pages/files/transfer-table.component.ts
  - src/angular/src/app/pages/files/transfer-table.component.html
  - src/angular/src/app/pages/files/transfer-table.component.scss
  - src/angular/src/app/pages/files/transfer-row.component.ts
  - src/angular/src/app/pages/files/transfer-row.component.html
  - src/angular/src/app/pages/files/transfer-row.component.scss
  - src/angular/src/app/pages/files/files-page.component.ts
  - src/angular/src/app/pages/files/files-page.component.html
  - src/angular/src/app/pages/files/files-page.component.scss
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 63: Code Review Report

**Reviewed:** 2026-04-14T12:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

The dashboard stats strip and transfer table components are well-structured, using Angular standalone components with OnPush change detection, proper Immutable.js interop (`.size`, `.filter().toList()`, `.slice().toArray()`), and reactive state management via BehaviorSubjects and combineLatest. The code is clean and follows consistent patterns. Two warnings were found related to misleading UI labels and a missing `@Injectable` provider scope consideration. One info-level item was noted.

## Warnings

### WR-01: Misleading "Free" label on storage stat cards

**File:** `src/angular/src/app/pages/files/stats-strip.component.html:12-13`
**Issue:** The Remote Storage and Local Storage cards display the unit suffix "Free" (lines 12 and 31), but the values represent total tracked bytes on remote and local storage respectively -- not free/available space. There is no free-space metric available from the backend. This will confuse users into thinking they are seeing available disk space.
**Fix:** Change the label to something accurate, such as "Tracked" or remove the qualifier entirely:
```html
<!-- Line 12: change -->
<span class="stat-unit">{{ stats.remoteTrackedBytes | fileSize:2:'unit' }}</span>

<!-- Line 31: change -->
<span class="stat-unit">{{ stats.localTrackedBytes | fileSize:2:'unit' }}</span>
```

### WR-02: DashboardStatsService declared as @Injectable() without providedIn, but no module provides it

**File:** `src/angular/src/app/services/files/dashboard-stats.service.ts:38`
**Issue:** `DashboardStatsService` uses `@Injectable()` without `providedIn: 'root'` and is not included in the `providers` array of `FilesPageComponent` or `StatsStripComponent`. Unless it is provided by a parent module or route configuration (not visible in the reviewed files), injecting it into `StatsStripComponent` will throw a `NullInjectorError` at runtime.
**Fix:** Either add `providedIn: 'root'` to the decorator, or add the service to the providers of `FilesPageComponent` (so it is scoped to the page and destroyed with it, which is appropriate given the `OnDestroy` lifecycle):
```typescript
// Option A: root singleton
@Injectable({ providedIn: 'root' })
export class DashboardStatsService implements OnDestroy { ... }

// Option B: page-scoped (preferred, preserves OnDestroy semantics)
// In files-page.component.ts:
@Component({
    ...
    providers: [DashboardStatsService]
})
```

## Info

### IN-01: getPageNumbers creates a new array on every change detection cycle

**File:** `src/angular/src/app/pages/files/transfer-table.component.ts:117-119`
**Issue:** `getPageNumbers()` is called directly in the template (`transfer-table.component.html:70`), creating a new array on every change detection run. With OnPush this is limited to input/async changes, so it is not a correctness bug, but it is a pattern that can cause issues if change detection strategy changes.
**Fix:** Consider computing the page numbers array as part of the reactive pipeline (e.g., derive from `totalPages$` via `map`) and consuming it with `async` pipe in the template.

---

_Reviewed: 2026-04-14T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
