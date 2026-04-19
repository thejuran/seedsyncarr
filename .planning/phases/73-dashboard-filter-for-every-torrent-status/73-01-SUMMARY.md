---
phase: 73-dashboard-filter-for-every-torrent-status
plan: 01
subsystem: ui
tags: [angular, filter, segment-filter, transfer-table, type-union, rxjs, behaviorsubject]

# Dependency graph
requires:
  - phase: 72-restore-dashboard-file-selection-and-action-bar
    provides: fileSelectionService.clearSelection wiring in onSegmentChange/onSubStatusChange (D-12 carry-forward)
provides:
  - "Widened activeSegment union: \"all\" | \"active\" | \"done\" | \"errors\" at all 3 type sites"
  - "Done branch in segmentedFiles$: returns DOWNLOADED || EXTRACTED when segment === 'done'"
  - "Active branch extended: DEFAULT (Pending) added as first OR clause"
  - "Type contract + filter logic foundation consumed by Plan 02 (template) and Plan 03 (URL persistence)"
affects: [73-02, 73-03, 73-04, 73-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Segment union extension: add new literal to all 3 type-annotated sites (field, BehaviorSubject generic, method param)"
    - "segmentedFiles$ branch-OR pattern: Active → Done → Errors in visual button order"

key-files:
  created: []
  modified:
    - src/angular/src/app/pages/files/transfer-table.component.ts

key-decisions:
  - "Done branch added between Active and Errors branches to mirror visual left-to-right button order (D-04)"
  - "DEFAULT (Pending) inserted as first OR clause in Active branch, matching workflow left-to-right order (D-05)"
  - "onSegmentChange body unchanged — existing collapse-on-second-click logic handles 'done' without modification (D-08)"

patterns-established:
  - "Segment branch order in segmentedFiles$: Active (DEFAULT|DOWNLOADING|QUEUED|EXTRACTING) -> Done (DOWNLOADED|EXTRACTED) -> Errors (STOPPED|DELETED)"

requirements-completed: [D-01, D-04, D-05, D-06, D-07, D-08, D-13]

# Metrics
duration: 8min
completed: 2026-04-19
---

# Phase 73 Plan 01: Segment Filter Type Foundation Summary

**Widened activeSegment union to `"all" | "active" | "done" | "errors"` and extended segmentedFiles$ with a Done branch (DOWNLOADED | EXTRACTED) and DEFAULT (Pending) in the Active branch**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-19T~21:50Z
- **Completed:** 2026-04-19T~21:58Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Widened the `activeSegment` string literal union at all 3 type-annotated sites (field declaration, BehaviorSubject generic, `onSegmentChange` parameter)
- Added Done branch in `segmentedFiles$` returning `DOWNLOADED || EXTRACTED` (D-06 group-OR semantics)
- Extended Active branch to include `DEFAULT` (Pending) as first OR clause (D-05)
- Branch order in file: Active → Done → Errors — mirrors the visual button order from D-04
- Zero changes to `onSegmentChange` body (D-08 compliance), Errors branch, or sub-status code path

## Task Commits

1. **Task 1: Widen activeSegment type union** - `90789c6` (feat)
2. **Task 2: Add Done branch + DEFAULT to Active** - `41e1c68` (feat)

## Files Created/Modified
- `src/angular/src/app/pages/files/transfer-table.component.ts` — Union widened at 3 sites; Done branch inserted; Active branch extended with DEFAULT

## Decisions Made
- Placed `"done"` between `"active"` and `"errors"` in the union to mirror the visual left-to-right button order specified in D-04
- `DEFAULT` inserted as first (leftmost) OR clause in Active branch per the "Pending → Queued → Syncing → Extracting" workflow-order recommendation in CONTEXT.md
- Did not modify `onSegmentChange` body — the existing collapse-on-second-click logic at line 159 works for any non-"all" segment value, satisfying D-08

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `npx tsc` in the worktree environment fails with "Cannot find type definition file for 'jasmine'" because the worktree has no local `node_modules/`. This is a pre-existing environment issue, not a regression: the same tsc invocation on the main repo (`/Users/julianamacbook/seedsyncarr/src/angular`) passes cleanly (exit 0). No `transfer-table.component.ts` errors were emitted.

## Exact Lines Changed

**Task 1 (union widening):**
- Line 28: `activeSegment: "all" | "active" | "errors"` → `"all" | "active" | "done" | "errors"`
- Lines 53-57: `BehaviorSubject<{segment: "all" | "active" | "errors"; ...}>` → `"all" | "active" | "done" | "errors"`
- Line 158: `onSegmentChange(segment: "all" | "active" | "errors")` → `"all" | "active" | "done" | "errors"`

**Task 2 (filter logic):**
- Lines 79-85: Active branch — added `f.status === ViewFile.Status.DEFAULT ||` as first OR clause
- Lines 87-93 (new): Done branch inserted between Active and Errors:
  ```typescript
  if (state.segment === "done") {
      return files.filter(f =>
          f.status === ViewFile.Status.DOWNLOADED ||
          f.status === ViewFile.Status.EXTRACTED
      ).toList();
  }
  ```

## Branch order in segmentedFiles$ after change

Active (line 79) → Done (line 87) → Errors (line 93) → fallthrough `return files.toList()`

## Confirmation: onSegmentChange body unchanged (D-08)

The body of `onSegmentChange` between the signature and closing `}` is byte-identical to the prior version. Only the parameter type changed from `"all" | "active" | "errors"` to `"all" | "active" | "done" | "errors"`.

## Note on existing spec at line 213

The existing spec test "should filter to active statuses" (spec line 213) asserts the Active branch returns specific files. Now that `DEFAULT` is included in the Active branch, if the test data includes a `DEFAULT` file that wasn't expected, the assertion count may fail. Plan 04 is designated to reconcile spec assertions. No spec changes are made in this plan.

## Next Phase Readiness
- Type contract established — Plan 02 (template) can safely call `onSegmentChange("done")` and emit `ViewFile.Status.DEFAULT/DOWNLOADED/EXTRACTED` from sub-buttons
- Plan 03 (URL persistence) can safely add `"done"` to the validated segment set
- No blockers

---
*Phase: 73-dashboard-filter-for-every-torrent-status*
*Completed: 2026-04-19*
