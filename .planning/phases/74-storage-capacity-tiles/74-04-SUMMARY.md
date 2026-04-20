---
phase: 74-storage-capacity-tiles
plan: 04
subsystem: ui
tags: [angular, template, scss, capacity, threshold, design-system]

requires:
  - phase: 74-03
    provides: DashboardStats four nullable *Capacity* fields + combineLatest pipeline
provides:
  - Capacity-mode template branches on Remote and Local Storage tiles
  - Threshold-driven progress-bar color shifts (amber/secondary < 80%, warning >= 80%, danger >= 95%)
  - --warning and --danger SCSS modifiers using Bootstrap semantic tokens
  - DecimalPipe wired into the standalone component for integer percentage formatting
  - 12 new component tests covering capacity render, fallback, thresholds, per-tile independence
affects: []

tech-stack:
  added: []
  patterns:
    - "@if/@else capacity branches with three-part divide-by-zero guard"
    - "Threshold class bindings: [class.X]=expr pattern with strict >= comparisons"

key-files:
  created: []
  modified:
    - src/angular/src/app/pages/files/stats-strip.component.html
    - src/angular/src/app/pages/files/stats-strip.component.scss
    - src/angular/src/app/pages/files/stats-strip.component.ts
    - src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts

key-decisions:
  - "Inline test template mirrors the real template exactly to keep karma loader-issue workaround in place"
  - "Three-part @if guard (total !== null && used !== null && total > 0) defensively covers divide-by-zero"
  - "Bootstrap semantic tokens via var(--bs-warning, #ffc107) / var(--bs-danger, #dc3545) — no new SCSS variables"
  - "Local tile keeps --secondary as below-80% base (matches existing tile identity)"

patterns-established:
  - "Capacity / fallback dual-mode rendering with per-tile independence handled at the @if level (no shared computed flag)"

requirements-completed: []

duration: ~25min
completed: 2026-04-20
---

# Phase 74-04: Capacity-Tile UI Summary

**Remote and Local Storage tiles now render the locked capacity design (XX% / of X.XX TB / progress bar / X.XX GB used) when SSE delivers capacity data, with strict 80%/95% threshold color shifts. Falls back verbatim to existing tracked-bytes layout when capacity is null.**

## Performance

- **Duration:** ~25 min (Tasks 1-3 inline + visual verification + screenshots)
- **Tasks:** 3 implementation + 2 user checkpoints (Task 0 pre-flight, Task 4 visual verification)
- **Files modified:** 4
- **Tests:** 21 SUCCESS (12 new capacity tests + 9 existing tile tests)

## Accomplishments
- `.stat-progress-fill--warning` and `.stat-progress-fill--danger` SCSS modifiers added (Bootstrap semantic tokens)
- `DecimalPipe` added to `StatsStripComponent.imports`
- Remote tile template: `@if (stats.remoteCapacityTotal !== null && stats.remoteCapacityUsed !== null && stats.remoteCapacityTotal > 0)` capacity branch + `@else` verbatim tracked-bytes fallback
- Local tile template: same shape with `localCapacity*` fields
- Capacity layout renders: integer percent + `of {total}` + progress bar + `{used} used` sub-line
- Threshold class bindings: amber/secondary base when `< 80%`, `--warning` when `>= 80 && < 95`, `--danger` when `>= 95`
- Inline test template updated to mirror real template's @if/@else structure
- `makeStats()` test helper for concise stat construction
- 12 new tests: fallback both-tiles, Remote/Local capacity mode, per-tile independence in both directions, integer percent rounding, 79/80/94/95 threshold boundaries, Local secondary base, danger uniformity, progress-fill width binding
- Existing icon-selector tests scoped to `.stat-icon` to skip the new `.stat-watermark` icons

## Task Commits

1. **Task 1: SCSS modifiers + DecimalPipe import** — `1075dda` (feat)
2. **Task 2: Capacity-mode template port** — `4c29687` (feat)
3. **Task 3: Spec test extensions + helper + selector scoping** — `b390607` (test)

## Files Created/Modified
- `src/angular/src/app/pages/files/stats-strip.component.html` — full rewrite adding @if/@else capacity branches to Remote and Local tiles; Download Speed and Active Tasks tiles unchanged
- `src/angular/src/app/pages/files/stats-strip.component.scss` — added `--warning` and `--danger` modifiers under `.stat-progress-fill`
- `src/angular/src/app/pages/files/stats-strip.component.ts` — added `DecimalPipe` to imports
- `src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts` — updated inline template, added `makeStats` helper, added 12 tests, scoped icon selectors to `.stat-icon`

## Decisions Made
- Stayed with the inline test template (mirroring the real one) rather than refactoring to use the real `templateUrl` directly — preserves the existing karma-friendly approach
- Three-part `@if` guard (`total !== null && used !== null && total > 0`) for defense against backend emitting `total: 0`
- Did not extract the percentage expression into a component field — inline keeps the diff minimal and the template self-contained, matching CONTEXT.md's discretion note

## Visual Verification (Task 4)
Dev server spun up at `http://localhost:4200`. Three states verified via injection of synthetic capacity values into the running component:

- **Fallback mode**: both Remote and Local tiles show `0 B Tracked` (verbatim existing layout) — confirms D-14 cold-load behavior
- **Capacity mode (normal)**: Remote at `65%` of `1.8 TB` with `1.2 TB used` and amber progress bar; Local at `24%` of `470 GB` with `110 GB used` and olive (secondary) progress bar — confirms D-01..D-07 layout and per-tile color identity
- **Threshold mode**: Remote at `85%` showing warning (yellow) bar; Local at `97%` showing danger (red) bar — confirms D-09/D-10/D-11 strict threshold transitions

User approved the rendered output as matching the locked design spec.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test regression] Existing icon-selector tests broke after watermark icons were added to template**
- **Found during:** Task 3 verification
- **Issue:** The new template adds `<i class="fa fa-cloud">` watermark icons in addition to the existing `<i class="fa fa-cloud stat-icon">` header icons. Tests that did `el.querySelector(".fa-cloud")` matched the watermark first (which has no `.stat-header` ancestor), then failed at `.closest(".stat-header")`.
- **Fix:** Scoped the icon selectors to `.stat-icon.fa-X` so they match only the header icons.
- **Files modified:** `src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts`
- **Committed in:** `b390607` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 selector scoping)
**Impact on plan:** Necessary for test correctness; no scope creep.

## Issues Encountered
- Visual verification required injecting capacity values via `cmp.stats$ = newSubject.asObservable()` (replacing the observable reference) because pushing to `_stats$.next()` did not trigger AsyncPipe re-render in OnPush mode when called from the dev console. This is a verification-only workaround; the real backend SSE path drives the original BehaviorSubject correctly.
- Pre-existing gsd-executor agent dispatch failure (same as Plan 74-02): both worktree-isolated and sequential agent invocations returned "I need Bash access" with one tool use. Falling back to inline orchestrator execution restored progress.

## User Setup Required
None.

## Next Phase Readiness
- Phase 74 is now end-to-end deliverable: backend StorageStatus + scanner df collection + `>1%` gate + frontend DTO + combineLatest + capacity-mode template with threshold colors
- When the backend is restarted against a real seedbox, the dashboard will automatically transition from fallback to capacity mode as the first SSE status payload with non-null storage values arrives
- No follow-up work; phase ready for verification + roadmap completion

---
*Phase: 74-storage-capacity-tiles*
*Completed: 2026-04-20*
