# Phase 72: Restore dashboard file selection and action bar - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Restore per-file selection state and the 5-action control surface (Queue / Stop / Extract / Delete Local / Delete Remote) on the dashboard transfer table, which were dropped in the v1.1.0 Triggarr-style redesign (phases 62–71). Ship the selection+action flow with functional parity to the pre-redesign behavior, visually integrated into the redesigned dashboard using AIDesigner Variant B (card-internal action bar).

**Out of scope:** adding new actions, redesigning the table layout, filter/segment changes (Phase 73), storage tile changes (Phase 74), re-adding any actions beyond the original 5.

</domain>

<decisions>
## Implementation Decisions

### Selection model
- **D-01:** Multi-select via checkboxes (not single-select by row click).
- **D-02:** Header "select all visible" checkbox — selects all rows on the current page only (not all pages in the filter).
- **D-03:** Shift-click range-select — `onCheckboxClick` emits `{file, shiftKey}` and the selection service extends the range from last-clicked to target.
- **D-04:** Clear selection on any page change, filter change, or segment change. Selection is tied to what's currently visible.
- **D-05:** Keyboard: `Esc` clears selection. No arrow-key row navigation.
- **D-06:** Selected-row visual treatment: checkbox checked + amber left-border accent (3px) + ~4% amber-wash background on the row (`rgba(212, 165, 116, 0.04)`), per Variant B.

### Action bar placement and visuals
- **D-07:** Action bar is **card-internal** — sits inside the transfer-table card, directly above the pagination footer. Not a viewport-floating bar.
- **D-08:** Bar has an amber top divider (`border-t border-brand-amber/30`) separating it from table rows, on a slightly lighter forest background (`#252e23`).
- **D-09:** Bar appears only when 1+ files are selected. When 0 selected, only pagination is visible in the card footer.
- **D-10:** Bar content layout: left side shows `2 selected` label (amber) + `Clear` text link; right side shows 5 action buttons in order Queue · Stop · Extract · | · Delete Local · Delete Remote (vertical divider between Extract and Delete Local).
- **D-11:** Queue is the amber-filled primary button (`bg-brand-amber text-moss-base`). Stop / Delete Local / Delete Remote are outline with red text (`border-status-red/40 text-status-red`). Extract is neutral outline (`border-moss-border text-ui-muted` when disabled).
- **D-12:** Buttons disable based on eligibility counts against the current selection — e.g. if 0 of N selected files are extractable, Extract is dimmed + `cursor-not-allowed`. Preserves the M007 eligibility-counting contract from `BulkActionsBarComponent`.

### Component strategy
- **D-13:** **Adapt the orphaned `BulkActionsBarComponent`** (cheapest path). Reuse its existing eligibility logic, count caching in `ngOnChanges`, 5 event emitters, and Set-based `@Input selectedFiles`. Rename to reflect it now handles 1..N selection; rewrite SCSS to match Variant B exactly.
- **D-14:** Existing `bulk-actions-bar.component.spec.ts` remains the contract for counts/eligibility; update only what the SCSS/rename change forces.
- **D-15:** Selection state lives in **the existing `FileSelectionService`** (signal-based, from M007). Wire `TransferRowComponent` checkbox click to `selectionService.toggle(file, shiftKey)`. Wire page/filter/segment resets in `TransferTableComponent` to call `selectionService.clear()` alongside the existing `goToPage(1)` on filter option change.
- **D-16:** Action event handlers in `TransferTableComponent` dispatch via existing `ViewFileService` action APIs (the same ones `FileComponent` used to call). No new backend endpoints.
- **D-17:** Delete Local and Delete Remote use the existing `ConfirmModalService` modal. For bulk deletes, the modal body shows the count and a short preview list of file names (truncate if > N).

### Wrap-up scope
- **D-18:** Delete these truly-obsolete components in this phase: `file-actions-bar.component.*`, `file-list.component.*`, `file.component.*`, `file-options.component.*`. (`bulk-actions-bar.component.*` stays — it's what we're adapting.)
- **D-19:** Unskip and update the 5 E2E tests in `src/e2e/tests/dashboard.page.spec.ts:38-56` to match the new DOM (checkbox column, card-internal action bar). Update the `dashboard.page` page-object selectors accordingly. No new E2E tests beyond restoring the originals.

### Claude's Discretion
- Exact class names and file renames during the `BulkActionsBar` adaptation (`TransferActionsBar` vs keeping `BulkActionsBar` — downstream planner may choose whichever reduces diff churn).
- Precise SCSS token mapping from AIDesigner Variant B's Tailwind classes to the project's `@use` SCSS system (port literal hex values per the design-spec rigor memory).
- Bulk delete modal body formatting (exact truncation threshold for the preview list).
- Whether to migrate `ConfirmModalService` call sites to `async/await` or keep the existing `.then()` pattern from `FileComponent`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design contract (Variant B — the identical port target)
- `.planning/phases/72-restore-dashboard-file-selection-and-action-bar/variant-B-card-internal-bar.html` — Full dashboard mockup with card-internal action bar, checkbox column, selected-row styling, and all 5 action buttons with eligibility-disabled states. Every hex value, padding, font-size, border-radius, and class in this file is the port target (per user's "port AIDesigner HTML identically" rule in memory).

### Upstream todo that defined the phase
- `.planning/todos/completed/2026-04-19-restore-dashboard-file-selection-and-action-bar.md` — Original problem statement, list of 5 dropped actions, file inventory of orphaned components, and the "Option 1 — Restore" confirmation.

### Code artifacts to reuse / adapt
- `src/angular/src/app/pages/files/bulk-actions-bar.component.ts` — Source component to adapt (eligibility counts, 5 emitters, Set<string> selection input).
- `src/angular/src/app/pages/files/bulk-actions-bar.component.html` — Template to rewrite against Variant B's bar markup.
- `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` — Existing test contract for count and eligibility logic; keep as regression anchor.
- `src/angular/src/app/services/files/file-selection.service.ts` — Signal-based selection service to reuse (from M007).
- `src/angular/src/app/services/utils/confirm-modal.service.ts` — Existing modal service for Delete Local / Delete Remote confirmations (call pattern already used by `FileComponent`).
- `src/angular/src/app/pages/files/transfer-table.component.ts` — Wire-up site for selection clearing in the `combineLatest` filter/page reset flow (already has `goToPage(1)` hook at line 95-98).
- `src/angular/src/app/pages/files/transfer-row.component.ts` — Row component to add checkbox column and click-to-toggle behavior.
- `src/angular/src/app/pages/files/transfer-row.component.html` — Template to add the leading checkbox cell (and selected-row left-border / amber-wash styling).
- `src/angular/src/app/pages/files/files-page.component.html` — Layout site (the card hosting the action bar).

### Tests to restore
- `src/e2e/tests/dashboard.page.spec.ts:38-56` — 5 `.skip()`'d tests to unskip and update: show/hide actions on select, show actions for most recent selected, all action buttons present, Queue enabled for Default, Stop disabled for Default.
- `src/e2e/tests/dashboard.page.ts` — Page object whose selectors need to be updated to the new DOM (checkbox column in transfer-table, card-internal action bar).

### Palette tokens (port literally per design-spec rigor memory)
- Forest base: `#1a201a` · Forest surface: `#222a20` · Forest border: `#2d3a2d` · Forest terminal: `#111511` · Action bar band: `#252e23`
- UI text primary: `#e8ebe6` · secondary: `#9ca39a` · muted: `#6b736a`
- Brand amber: `#d4a574` · amber wash: `rgba(212, 165, 116, 0.04)`
- Status green: `#7fb069` · red: `#c97d7d` · blue: `#7896b0`

### Project-level rules
- `/Users/julianamacbook/.claude/projects/-Users-julianamacbook-seedsyncarr/memory/feedback_design_spec_rigor.md` — "Port AIDesigner HTML identically, no approximations." Applies to every Variant B value.
- `.planning/PROJECT.md` — Constraints (dark-only, Deep Moss + Amber palette, no SVG icons, text-only UI — Variant B uses Phosphor icons in small roles, map to equivalent Font Awesome 4.7 glyphs per memory).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`BulkActionsBarComponent`** — Full 5-action eligibility+count logic, cached via `ngOnChanges`. Adapt SCSS + tweak template for Variant B.
- **`FileSelectionService`** — Signal-based (`selectedFiles` signal), already supports toggle/shift-click/clear. Drop-in.
- **`ConfirmModalService`** — Existing modal for delete confirmations; pattern demonstrated in `FileComponent:149-162`.
- **`ViewFileService`** — Existing action dispatch API (queue/stop/extract/delete-local/delete-remote), unchanged from pre-redesign.
- **`TransferTableComponent.filterState$`** — Already has a `combineLatest` flow that resets page to 1 on filter option change (line 95-98); hook selection clearing into the same flow.

### Established Patterns
- **Signal-based row state** (M007) — `computed()` signals in row components for selection state. `TransferRow` should follow `FileComponent:95-101` pattern: inject `FileSelectionService`, `readonly isSelected = computed(() => this.selectionService.selectedFiles().has(this.file.name))`.
- **`takeUntilDestroyed(destroyRef)`** — Uniform subscription cleanup in standalone components (already used in `TransferTableComponent`).
- **OnPush change detection** — All dashboard components use `ChangeDetectionStrategy.OnPush`.
- **`ClickStopPropagationDirective`** — Used on checkbox clicks in `FileComponent:onCheckboxClick` to prevent row-click handlers. Apply to `TransferRow` checkbox.

### Integration Points
- **`files-page.component.html`** — Currently renders `<app-stats-strip>`, `<app-transfer-table>`, `<app-dashboard-log-pane>`. The action bar lives INSIDE the transfer-table card, not in files-page — no change here.
- **`TransferTableComponent` template** — Add checkbox column to `<thead>` (select-all) and `<tbody>` via `TransferRow`; insert the adapted action bar as a conditional block between the table and the pagination footer (i.e., in the card's footer region).
- **`TransferRowComponent`** — Add leading `<td>` with checkbox + apply selected-row classes (`row-selected` or equivalent SCSS class) via `@HostBinding` on the computed `isSelected` signal.
- **E2E page object** — `dashboard.page.ts` selectors for row, checkbox, and each action button need to match Variant B's DOM structure.

</code_context>

<specifics>
## Specific Ideas

- User specifically chose Variant B over Variant A because the action bar should feel "native to the table card," not floating chrome over the log pane.
- Both Variant B and Variant A demonstrated eligibility-count disabling (Extract dimmed because only 1 of 2 selected files is extractable; Delete Remote dimmed because 0 of 2 are remotely-deletable) — this stays as the interaction contract.
- The amber-wash + amber-left-border selected-row treatment was chosen over "checkbox only" — it must be obvious at a glance which rows will be acted on.

</specifics>

<deferred>
## Deferred Ideas

- Toast-with-Undo pattern for deletes (considered, rejected in favor of the existing `ConfirmModalService` modal — would require undo-queue plumbing on the backend).
- Arrow-key row navigation and Enter-to-act (considered, rejected in favor of click+Esc only for this phase).
- "Select all across all pages in filter" (rejected — too risky for destructive actions on unseen rows).
- New E2E tests for multi-select behaviors beyond the original 5 (select-all header, shift-click range, eligibility-count disabling) — file a follow-up phase if regressions surface.

</deferred>

---

*Phase: 72-restore-dashboard-file-selection-and-action-bar*
*Context gathered: 2026-04-19*
