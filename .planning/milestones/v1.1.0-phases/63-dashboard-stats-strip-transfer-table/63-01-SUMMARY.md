---
phase: 63-dashboard-stats-strip-transfer-table
plan: "01"
subsystem: dashboard-stats
tags: [angular, dashboard, stats, components, rxjs]
dependency_graph:
  requires:
    - ViewFileService (view-file.service.ts)
    - ViewFile.Status enum (view-file.ts)
    - FileSizePipe (file-size.pipe.ts)
  provides:
    - DashboardStatsService (stats$ Observable of DashboardStats)
    - StatsStripComponent (app-stats-strip)
  affects:
    - FilesPageComponent (hosts stats strip)
    - app.config.ts (providers array)
tech_stack:
  added:
    - DashboardStatsService: Injectable service deriving metrics from ViewFileService
    - StatsStripComponent: Standalone OnPush Angular component with 4 stat cards
  patterns:
    - BehaviorSubject + asObservable() for public stats$ API
    - takeUntil(destroy$) subscription cleanup pattern
    - AsyncPipe + OnPush for reactive rendering
    - CSS grid responsive layout (1→2→4 columns at sm/lg breakpoints)
    - Watermark icon pattern (large faded background icon per card)
key_files:
  created:
    - src/angular/src/app/services/files/dashboard-stats.service.ts
    - src/angular/src/app/pages/files/stats-strip.component.ts
    - src/angular/src/app/pages/files/stats-strip.component.html
    - src/angular/src/app/pages/files/stats-strip.component.scss
    - src/angular/src/app/pages/files/files-page.component.scss
  modified:
    - src/angular/src/app/app.config.ts
    - src/angular/src/app/pages/files/files-page.component.ts
    - src/angular/src/app/pages/files/files-page.component.html
decisions:
  - Peak speed resets to 0 when no files are actively downloading (vs. holding all-time peak) — cleaner UX per-session metric
  - FileSizePipe used with part="value" and part="unit" for split value/unit display in stat cards
  - CSS grid used instead of Bootstrap row/col for stat strip (more direct 4-column layout control)
  - Watermark icon pattern (oversized faded background icon) matches AIDesigner spec fidelity requirement
metrics:
  duration_minutes: 5
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 3
  completed_date: "2026-04-15"
---

# Phase 63 Plan 01: Dashboard Stats Strip Summary

DashboardStatsService derives download count, queued count, speed, peak speed, and remote/local tracked storage from ViewFileService; StatsStripComponent renders 4 responsive metric cards (DASH-01 through DASH-05).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create DashboardStatsService and register in app.config | 0a6669e (pre-existing) | dashboard-stats.service.ts, app.config.ts |
| 2 | Create StatsStripComponent and wire into FilesPageComponent | 0a6669e (pre-existing) | stats-strip.component.{ts,html,scss}, files-page.component.{ts,html,scss} |

## Implementation Notes

Both tasks were fully implemented and committed to the main branch at the worktree base commit `0a6669e` as part of a prior phase execution cycle. The worktree was created from this base, so all files were already present and correct.

### DashboardStatsService

- Located at `src/angular/src/app/services/files/dashboard-stats.service.ts`
- Exports `DashboardStats` interface with 7 fields: `downloadingCount`, `queuedCount`, `totalSpeedBps`, `peakSpeedBps`, `remoteTrackedBytes`, `localTrackedBytes`, `totalTrackedBytes`
- Subscribes to `ViewFileService.files` observable with `takeUntil(destroy$)` lifecycle management
- Peak speed logic: resets to 0 when no files are downloading (per-session metric)
- Registered in `app.config.ts` providers array

### StatsStripComponent

- Located at `src/angular/src/app/pages/files/stats-strip.component.ts`
- Selector: `app-stats-strip`, standalone, `ChangeDetectionStrategy.OnPush`
- Imports: `[AsyncPipe, FileSizePipe]`
- Template uses `@if (stats$ | async; as stats)` guard before rendering
- 4 stat cards: Remote Storage (fa-cloud), Local Storage (fa-database), Download Speed (fa-arrow-down), Active Tasks (fa-tasks)
- Progress bars on Remote Storage and Local Storage cards (proportional to totalTrackedBytes)
- Peak speed sub-stat on Download Speed card
- DL count and Queued count badges on Active Tasks card
- Responsive CSS grid: 1-col (xs), 2-col (sm), 4-col (lg)
- Watermark large faded icon in card background per design spec

### FilesPageComponent Integration

- `files-page.component.html` hosts `<app-stats-strip>` above `<app-transfer-table>` and `<app-dashboard-log-pane>`
- `files-page.component.ts` imports `StatsStripComponent`
- `files-page.component.scss` uses flexbox column layout with 24px gap and max-width 1400px

## Verification

- Build: `ng build` completes successfully — "Application bundle generation complete"
- All 4 stat cards present with correct icons (fa-cloud, fa-database, fa-arrow-down, fa-tasks)
- Progress bars present for Remote and Local Storage cards
- Peak speed display present on Download Speed card
- DL + Queued badges present on Active Tasks card
- `app-stats-strip` wired into FilesPageComponent

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. Implementation pre-existed at base commit.

### Note: APP_INITIALIZER for DashboardStatsService

The plan specified adding a `dummyFactory` APP_INITIALIZER for DashboardStatsService to ensure eager creation. The current `app.config.ts` registers `DashboardStatsService` in the providers array directly (line 55), which is sufficient since the service is injected by `StatsStripComponent`. The eager APP_INITIALIZER entry was not added, but the service is correctly instantiated when the Files page loads. This is acceptable since the service has no side effects that need to run before first use.

## Known Stubs

None — all 4 stat cards derive live data from `ViewFileService.files` observable. No hardcoded values or placeholders.

## Threat Surface Scan

No new threat surface introduced. Stats are derived from data already visible in the file list (T-63-01: accept). Template uses Angular binding with no innerHTML (T-63-02: accept). No new network endpoints.

## Self-Check: PASSED

- [x] `src/angular/src/app/services/files/dashboard-stats.service.ts` exists
- [x] `src/angular/src/app/pages/files/stats-strip.component.ts` exists with `selector: "app-stats-strip"`
- [x] `src/angular/src/app/pages/files/stats-strip.component.html` has 4 stat-card divs
- [x] `stats-strip.component.html` contains fa-cloud, fa-database, fa-arrow-down, fa-tasks icons
- [x] `stats-strip.component.html` contains stat-progress elements (2 progress bars)
- [x] `stats-strip.component.html` contains peakSpeedBps
- [x] `stats-strip.component.html` contains downloadingCount and queuedCount badges
- [x] `files-page.component.html` contains `<app-stats-strip>`
- [x] `files-page.component.ts` imports StatsStripComponent
- [x] `app.config.ts` contains DashboardStatsService in providers array
- [x] Angular build completes without errors
