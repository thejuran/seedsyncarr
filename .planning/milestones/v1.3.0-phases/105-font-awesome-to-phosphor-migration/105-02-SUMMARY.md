---
phase: 105-font-awesome-to-phosphor-migration
plan: 02
subsystem: angular-ui
tags: [icon-migration, font-awesome, phosphor, css-animation, unit-specs, karma]
dependency_graph:
  requires: [105-01]
  provides: [DEPS-01b-files-cluster, ph-spin-css-rule]
  affects: [dashboard-log-pane, stats-strip, transfer-row, transfer-table, bulk-actions-bar]
tech_stack:
  added: []
  patterns: [PATTERN-A-static-ph-idiom, PATTERN-F1-scss-selector-rename, PATTERN-F6-ph-spin-keyframes]
key_files:
  created: []
  modified:
    - src/angular/src/app/pages/files/dashboard-log-pane.component.html
    - src/angular/src/app/pages/files/dashboard-log-pane.component.scss
    - src/angular/src/app/pages/files/stats-strip.component.html
    - src/angular/src/app/pages/files/transfer-row.component.html
    - src/angular/src/app/pages/files/transfer-table.component.html
    - src/angular/src/app/pages/files/bulk-actions-bar.component.html
    - src/angular/src/app/tests/unittests/pages/files/dashboard-log-pane.component.spec.ts
    - src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts
    - src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts
decisions:
  - "Q4 applied as ph-file-zip (user substitution from proposed ph-file-archive) per 105-MAPPING-SIGNOFF.md DECISION line"
  - "ph-spin keyframes scoped to dashboard-log-pane.component.scss (not global styles.scss) — only one spinner exists"
  - "ph-prohibit used for Delete Remote overlay (not ph-ban — ph-ban does not exist in Phosphor 2.1.2)"
metrics:
  duration: "~20 minutes"
  completed: "2026-06-01"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 9
  karma_results: "611/611 PASS — stmts 84.33% / branches 69.31% / fns 80.49% / lines 85.18%"
---

# Phase 105 Plan 02: Files Cluster FA→Phosphor Migration Summary

**One-liner:** Migrated all Font Awesome icons in the `files/` component cluster (5 templates + 1 SCSS) to Phosphor classes, added the net-new `@keyframes ph-spin` / `.ph-spin` CSS rule that preserves spinner animation after the FA dep drop in 105-04, and faithfully updated 3 unit specs; 611/611 Karma tests pass with coverage floors held.

---

## What Was Built

### Task 1: Files-cluster template migration + ph-spin CSS prereq (commit 5c1b519)

Migrated all `fa fa-*` icon classes across 5 templates and augmented the SCSS:

**dashboard-log-pane.component.html** (4 changes):
- L4: `fa fa-terminal` → `ph ph-terminal`
- L8: `fa fa-copy` → `ph ph-copy`
- L11: `fa fa-expand` → `ph ph-arrows-out`
- L18: `fa fa-circle-o-notch fa-spin` → `ph ph-circle-notch ph-spin` (Q5)

**dashboard-log-pane.component.scss** (2 changes):
- L38: `.fa-terminal` → `.ph-terminal` (PATTERN F1 — preserves amber terminal-icon color)
- Appended `@keyframes ph-spin` + `.ph-spin { animation: ph-spin 1s linear infinite; display: inline-block; }` at end of file (PATTERN F6 — required before FA dep drop in 105-04)

**stats-strip.component.html** (8 changes — both watermark + stat-icon instances each):
- L5,7: `fa fa-cloud` → `ph ph-cloud`
- L46,48: `fa fa-database` → `ph ph-database`
- L87,89: `fa fa-arrow-down` → `ph ph-arrow-down`
- L101,103: `fa fa-tasks` → `ph ph-list-checks`

**transfer-row.component.html** (1 change):
- L18: `fa fa-arrow-down` → `ph ph-arrow-down`

**transfer-table.component.html** (1 change, line 13 only):
- `fa fa-search search-icon` → `ph ph-magnifying-glass search-icon`
- Existing `ph-bold` caret toggle blocks left untouched (D-02)

**bulk-actions-bar.component.html** (6 changes):
- L19: `fa fa-play` → `ph ph-play`
- L24: `fa fa-stop` → `ph ph-stop`
- L29: `fa fa-file-archive-o` → `ph ph-file-zip` (Q4 SIGNOFF — user chose ph-file-zip, NOT ph-file-archive)
- L35: `fa fa-trash` → `ph ph-trash`
- L40: `fa fa-cloud` → `ph ph-cloud` (cloud icon)
- L40: `fa fa-ban action-overlay` → `ph ph-prohibit action-overlay` (corrected per Pitfall 4 — ph-ban does not exist)

**Verify result:** `FILES-CLUSTER-MIGRATED` (zero FA residuals, all key patterns confirmed)

---

### Task 2: 3 spec files faithfully updated + Karma green (commit e15a1d3)

Per D-03 (faithful update — no loosening to library-agnostic assertions):

**dashboard-log-pane.component.spec.ts** — LOG_PANE_TEMPLATE inline:
- fa-terminal → ph-terminal, fa-copy → ph-copy, fa-expand → ph-arrows-out, fa-circle-o-notch fa-spin → ph-circle-notch ph-spin
- (No fa-* querySelector assertions in this spec — spinner test uses `.log-pane__spinner`)

**stats-strip.component.spec.ts** — STATS_STRIP_TEMPLATE inline + 5 DOM assertions:
- Template: all 8 fa-* instances migrated to ph equivalents (cloud/database/arrow-down/list-checks)
- L182: `.stat-icon.fa-cloud` → `.stat-icon.ph-cloud`
- L190: `.stat-icon.fa-database` → `.stat-icon.ph-database`
- L198: `.stat-icon.fa-arrow-down` → `.stat-icon.ph-arrow-down`
- L206: `.stat-icon.fa-tasks` → `.stat-icon.ph-list-checks`
- L242: `.stat-icon.fa-arrow-down` → `.stat-icon.ph-arrow-down` (peak-speed test)

**transfer-table.component.spec.ts** — TEST_TEMPLATE + 1 DOM assertion:
- Template L25: `fa fa-search search-icon` → `ph ph-magnifying-glass search-icon`
- L202: `querySelector(".fa-search")` → `querySelector(".ph-magnifying-glass")`

**Karma results:** 611/611 PASS
- Statements: 84.33% (floor 83% — held)
- Branches: 69.31% (floor 68% — held)
- Functions: 80.49% (floor 79% — held)
- Lines: 85.18% (floor 83% — held)

---

## Deviations from Plan

None — plan executed exactly as written. Q4 `ph-file-zip` applied per the signed-off DECISION line (105-MAPPING-SIGNOFF.md). All per-file edit line numbers matched the plan's annotations.

---

## Known Stubs

None. All 5 templates render live data from services; no hardcoded placeholder values introduced.

---

## Threat Flags

No new threat surface introduced. Icon-class CSS swap on static `<i>` elements — no auth, no user input, no injection sink. The added `.ph-spin` rule is a pure CSS keyframe animation with no scripting. All changes are compile-time constants.

---

## Self-Check: PASSED

All 9 source files exist on disk. Both task commits (5c1b519, e15a1d3) confirmed in git log. SUMMARY.md written at expected path. 611/611 Karma tests passing with all four coverage floors held or risen.
