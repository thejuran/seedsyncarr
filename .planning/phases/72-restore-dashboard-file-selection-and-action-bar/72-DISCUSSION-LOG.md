# Phase 72: Restore dashboard file selection and action bar - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 72-restore-dashboard-file-selection-and-action-bar
**Areas discussed:** Selection model, Action surface placement, Component strategy, Wrap-up scope

---

## Selection model

### Q1: How should users pick files for actions on the dashboard?

| Option | Description | Selected |
|--------|-------------|----------|
| Single-select (click row) | One row at a time, click replaces, click-again deselects. | |
| Multi-select (checkboxes) | Checkbox per row, shift-click range, action bar with counts. | ✓ |
| Both — click=single, checkbox=multi | Click for single-file, checkboxes for bulk. | |

**User's choice:** Multi-select (checkboxes)

### Q2: Should selection survive page / filter / sort changes?

| Option | Description | Selected |
|--------|-------------|----------|
| Clear on any filter/page/segment change | Selection tied to what's visible; all changes reset. | ✓ |
| Persist across page changes, clear on filter/segment | Middle ground. | |
| Persist everywhere until explicit deselect | Sticky selection; user Escapes / click-away. | |

**User's choice:** Clear on any filter/page/segment change

### Q3: Where do keyboard shortcuts land?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: Esc to deselect, click to select | Click-driven baseline. | ✓ |
| Full: arrows to move, Enter to act, Esc to clear | Full keyboard nav over rows. | |
| No keyboard — click only | Drop Esc. | |

**User's choice:** Minimal: Esc to deselect, click to select

### Q4: Table header "select all visible" checkbox?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — selects all rows on current page | Standard table pattern. | ✓ |
| Yes — selects across all pages in current filter | More powerful but risky. | |
| No header checkbox — per-row only | Simpler, safer, tedious. | |

**User's choice:** Yes — selects all rows on current page

### Q5: Shift-click range-select?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — shift-click extends from last-clicked to target | FileComponent already had this pattern. | ✓ |
| No — individual clicks only | Each checkbox toggles independently. | |

**User's choice:** Yes

### Q6: Visual treatment when a row is selected?

| Option | Description | Selected |
|--------|-------------|----------|
| Checkbox only (no row highlight) | Keeps rows visually calm. | |
| Checkbox + subtle row background tint | Obvious at a glance; stays within palette. | ✓ |
| Checkbox + left-border accent | Echoes v3.0 status-based border pattern. | |

**User's choice:** Checkbox + subtle row background tint
**Notes:** Final Variant B implements both checkbox + amber-wash background AND amber left-border accent together.

---

## Action surface placement

Flow changed mid-discussion: user redirected UI decisions to AIDesigner MCP instead of text-mocked options.

**Process:**
1. Dispatched two parallel `mcp__aidesigner__generate_design` calls showing the whole dashboard with different action-bar placements.
2. Variant A: floating bar fixed to viewport bottom, amber top-border glow.
3. Variant B: action bar contained inside the transfer-table card, above pagination.
4. Both saved to `.planning/phases/72-.../variant-A-floating-bar.html` and `variant-B-card-internal-bar.html` and opened in browser for comparison.

**User's choice:** Variant B (card-internal bar)

**Notes:** User specifically preferred the bar feeling native to the table card rather than floating chrome over the log pane. Variant B becomes the identical-port design target (per design-spec rigor memory rule).

---

## Component strategy

### Q1: How should the action bar be built in Angular?

| Option | Description | Selected |
|--------|-------------|----------|
| Adapt orphaned BulkActionsBarComponent | Reuse counts/eligibility/emitters, restyle SCSS. | ✓ |
| Write a new TransferActionsBarComponent from scratch | Clean signal-based standalone, fresh SCSS. | |
| Inline the bar into TransferTableComponent | No separate component. | |

**User's choice:** Adapt orphaned BulkActionsBarComponent (user requested pros/cons comparison table before answering; chose "cheapest path" after review)

### Q2: Where does selection state live?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse FileSelectionService signal | Already exists from M007, signal-based, unit-tested. | ✓ |
| Local state in TransferTableComponent | Private Set, simpler wiring. | |
| New SelectionStore signal-based service | Dedicated service, duplicates infra. | |

**User's choice:** Reuse FileSelectionService signal

### Q3: Delete Local / Delete Remote confirmation UX?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep ConfirmModalService modal | Matches FileComponent pattern, already wired. | ✓ |
| Toast with Undo window | Faster UX, requires backend undo-queue. | |
| Inline two-step confirm (button morphs) | Snappy, easy to misclick. | |

**User's choice:** Keep ConfirmModalService modal

---

## Wrap-up scope

### Q1: Which truly-obsolete orphans get deleted in this phase?

| Option | Description | Selected |
|--------|-------------|----------|
| file-actions-bar.component.* | Single-file variant, superseded. | ✓ |
| file-list.component.* + file.component.* | Old list wrapper + per-row with inline actions. | ✓ |
| file-options.component.* | Per-row dropdown, unused. | ✓ |
| Keep orphans, defer cleanup | Smaller diff, delayed cleanup. | |

**User's choice:** All three orphan groups to be deleted in this phase.

### Q2: What happens to the 5 skipped E2E tests?

| Option | Description | Selected |
|--------|-------------|----------|
| Unskip + update selectors in this phase | Restore the 5 originals against new DOM. | ✓ |
| Unskip + expand with bulk-specific tests | Restore + add multi-select coverage. | |
| Leave skipped, file a follow-up E2E phase | Ship UI only, defer E2E. | |

**User's choice:** Unskip + update selectors in this phase

---

## Claude's Discretion

- Exact class names and file renames during BulkActionsBar adaptation.
- Precise SCSS token mapping from Variant B Tailwind to project's `@use` SCSS system (must be literal hex per design-spec rigor memory).
- Bulk delete modal body formatting and preview list truncation threshold.
- Whether to migrate ConfirmModalService call sites to async/await or keep existing .then() pattern.

## Deferred Ideas

- Toast-with-Undo delete pattern (rejected — backend undo-queue not worth building).
- Arrow-key row nav / Enter-to-act (rejected for this phase).
- "Select all across all pages in filter" (rejected — destructive risk on unseen rows).
- Expanded E2E coverage for multi-select behaviors (select-all header, shift-click range, eligibility disable) — file a follow-up if regressions surface.
