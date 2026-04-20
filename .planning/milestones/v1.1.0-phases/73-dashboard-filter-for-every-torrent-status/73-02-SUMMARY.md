---
phase: 73-dashboard-filter-for-every-torrent-status
plan: 02
subsystem: ui
tags: [angular, template, segment-filter, transfer-table, design-spec]

# Dependency graph
requires:
  - plan: 73-01
    provides: "activeSegment union widened to include 'done'; segmentedFiles$ Done branch; ViewFileStatus.DEFAULT in Active branch"
provides:
  - "Done parent button rendered between Active and Errors in .segment-filters"
  - "Done expand block with Downloaded (ViewFileStatus.DOWNLOADED) and Extracted (ViewFileStatus.EXTRACTED) subs"
  - "Pending sub-button (ViewFileStatus.DEFAULT) as first sub under Active expand block"
affects: [73-03, 73-04, 73-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Done parent button: byte-identical shape to Errors parent, substituting 'errors' -> 'done' and labels"
    - "Done sub-buttons: byte-identical shape to Failed/Deleted subs, substituting status enum values and labels"
    - "Pending sub-button: byte-identical shape to Syncing sub, substituting DOWNLOADING -> DEFAULT and label"

key-files:
  created: []
  modified:
    - src/angular/src/app/pages/files/transfer-table.component.html

key-decisions:
  - "Done block inserted between Active expand block closing brace and Errors parent comment (lines 66-95 in pre-edit file) per D-04 visual order"
  - "Pending inserted immediately after segment-divider and before Syncing button per D-05 (first/left-most sub under Active)"
  - "All new markup reuses existing SCSS classes verbatim per D-15 and feedback_design_spec_rigor.md — no new classes, no inline styles"

# Metrics
duration: 10min
completed: 2026-04-19
---

# Phase 73 Plan 02: Transfer Table Template — Done Segment + Pending Sub

**Added Done parent button + expand block and Pending sub-button to transfer-table.component.html, reusing all existing SCSS classes byte-for-byte**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-04-19T23:39Z
- **Tasks:** 2 (committed together — same file, edits inseparable at git level)
- **Files modified:** 1

## Accomplishments

- Inserted Done parent button (`onSegmentChange('done')`) with chevron toggle between Active expand block and Errors parent button (D-04 visual order: All, Active, Done, Errors)
- Inserted Done expand block (`@if (activeSegment === 'done')`) containing two sub-buttons: Downloaded (`ViewFileStatus.DOWNLOADED`) and Extracted (`ViewFileStatus.EXTRACTED`) — (D-03, D-06)
- Inserted Pending sub-button (`ViewFileStatus.DEFAULT`) as the first sub-button inside the Active expand block, immediately after the `<div class="segment-divider"></div>` and before Syncing (D-03, D-05)
- Active sub-button order is now: Pending, Syncing, Queued, Extracting (workflow-order per CONTEXT "Claude's Discretion")
- Zero new SCSS classes introduced; all new buttons reuse `.btn-segment`, `.btn-segment--parent-active`, `.btn-segment--parent-expanded`, `.btn-sub`, `.accent-dot`, `.segment-divider` verbatim (D-15)
- Mobile responsive behavior inherited — `.segment-filters` already hides below 768px (D-14); no new media queries

## Task Commits

1. **Tasks 1+2: Done segment block + Pending sub** - `51a0c7a` (feat)
   - Both tasks touched the same file; applied and committed together

## Files Created/Modified

- `src/angular/src/app/pages/files/transfer-table.component.html` — 39 lines inserted:
  - Lines 66-95 (post-edit): Done parent button + Done expand block (Downloaded, Extracted subs)
  - Lines 40-47 (post-edit): Pending sub-button inserted before Syncing in Active expand block

## Exact Line Ranges Where New Markup Was Inserted

**Done parent button + expand block** (inserted between what was line 64 and line 66 in the pre-edit file):
- Post-edit lines 74-103: `<!-- Done: expandable parent -->` through closing `}` of `@if (activeSegment === 'done')`

**Pending sub-button** (inserted between what was line 39 `<div class="segment-divider"></div>` and line 40 `<button ... DOWNLOADING>` in the pre-edit file):
- Post-edit lines 40-47: Pending `<button type="button" class="btn-sub" ...>` through `</button>`

## Visual DOM Order Verified

`grep -nE "onSegmentChange\('(active|done|errors)'\)" transfer-table.component.html` output:
- line 31: `onSegmentChange('active')`
- line 78: `onSegmentChange('done')`
- line 109: `onSegmentChange('errors')`

Order is correct: Active (31) < Done (78) < Errors (109).

## Sub-button Order Under Active Verified

Post-edit sub-button labels in file order: Pending (line 46), Syncing (line 54), Queued (line 62), Extracting (line 70).

## Confirmation: No New SCSS Classes

All `class="..."` attributes in the file use only these class names:
- `.btn-segment`, `.btn-segment--parent-active`, `.btn-segment--parent-expanded`
- `.btn-sub`, `.segment-divider`, `.accent-dot`
- `.ph-bold`, `.ph-caret-down`, `.ph-caret-up`
- Pre-existing card/table/pagination classes unchanged

No new class names were introduced.

## Build Verification

`cd src/angular && npx ng build --configuration=development` — exit 0. SCSS warnings (lighten() deprecations) are pre-existing and unrelated to this plan.

## Decisions Made

- Committed both tasks in a single git commit because both edits target the same file and were applied sequentially before any intermediate commit opportunity existed
- Indentation matched surrounding 8-space context for Done parent/expand block and 10-space context for Pending sub inside Active @if block

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria passed on first attempt.

## Known Stubs

None. All new buttons are fully wired to existing TypeScript methods (`onSegmentChange`, `onSubStatusChange`) with correct enum values. No placeholder content.

## Threat Flags

None. Template-only HTML changes mirror existing trusted patterns. All new attributes are static class bindings, static event handlers, and static text labels per T-73-02-01 / T-73-02-02 (accepted in plan's threat model).

## Next Phase Readiness

- Plan 03 (URL persistence) can safely add 'done' to the validated segment set and wire query-param hydration/write-back — the template already emits `onSegmentChange('done')` and `onSubStatusChange(ViewFileStatus.DEFAULT/DOWNLOADED/EXTRACTED)`
- Plan 04 (unit tests) can assert against the new buttons and sub-status filter behavior
- No blockers

---
*Phase: 73-dashboard-filter-for-every-torrent-status*
*Completed: 2026-04-19*
