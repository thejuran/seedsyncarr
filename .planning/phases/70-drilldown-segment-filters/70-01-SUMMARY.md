---
phase: 70-drilldown-segment-filters
plan: 01
subsystem: angular-frontend
tags: [ui, filters, drill-down, segment-control]
dependency_graph:
  requires: []
  provides: [drill-down-segment-filter, sub-status-filtering]
  affects: [transfer-table-component]
tech_stack:
  added: []
  patterns: [toggle-collapse-parent, sub-status-reactive-filter, BEM-modifier-classes]
key_files:
  created: []
  modified:
    - src/angular/src/app/pages/files/transfer-table.component.ts
    - src/angular/src/app/pages/files/transfer-table.component.html
    - src/angular/src/app/pages/files/transfer-table.component.scss
decisions:
  - "Used BEM-style modifier classes (btn-segment--parent-active, btn-segment--parent-expanded) instead of .active to avoid pointer-events:none blocking collapse clicks"
  - "Removed inner distinctUntilChanged pipe so sub-status changes propagate through combineLatest"
metrics:
  duration: 3m
  completed: 2026-04-15T20:30:02Z
  tasks: 2/2
  files: 3
---

# Phase 70 Plan 01: Drill-down Segment Filter Summary

Inline expandable sub-status drill-down for Active (Syncing/Queued/Extracting) and Errors (Failed/Deleted) with toggle-collapse, chevron rotation, and amber accent dot -- pixel-exact port from AIDesigner mockup.

## Task Results

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Add drill-down state, toggle-collapse logic, and sub-status filtering | 4eec1e5 | activeSubStatus field, ViewFileStatus alias, widened filterState$ BehaviorSubject, updated segmentedFiles$ pipeline with subStatus-first check, toggle-collapse onSegmentChange, onSubStatusChange method |
| 2 | Replace segment filter template with drill-down HTML and add SCSS classes | 9142124 | Full drill-down template with @if blocks, chevron icons (ph-caret-down/up), segment-divider, btn-sub buttons, accent-dot; updated pill container (border-radius 6px, rgba border, inset box-shadow); all new SCSS modifier classes |

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **BEM modifiers over .active class for parent buttons** - Active and Errors parent buttons use `btn-segment--parent-active` and `btn-segment--parent-expanded` classes instead of the existing `.active` class, which carries `pointer-events: none` and would block collapse clicks.

2. **Removed inner distinctUntilChanged** - The previous `filterState$.pipe(map(s => s.segment), distinctUntilChanged())` suppressed sub-status changes since it only emitted on segment changes. Replaced with direct `filterState$` subscription so sub-status changes propagate.

## Self-Check: PASSED
