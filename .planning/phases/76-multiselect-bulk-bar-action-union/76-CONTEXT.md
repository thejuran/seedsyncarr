# Phase 76: Multiselect Bulk-Bar Action Union - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Bug fix. Restore correct union-of-applicable-actions behavior in the dashboard
bulk-actions bar so that any selection including one or more DELETED files
exposes every action that applies to at least one selected row — most
importantly, "Re-Queue from Remote" (i.e. the Queue action dispatched against
a DELETED row). Inapplicable actions remain disabled on a per-button basis;
dispatch filters to eligible rows only. Regression from v1.1.0 (FIX-01).

**Out of scope:** adding new actions, relabeling existing actions, visual
redesign of the bar, per-row checkbox disabling, new E2E specs (that's
Phase 77), adding count badges like "Queue (1/3)" to buttons.

</domain>

<decisions>
## Implementation Decisions

### Bug-hunt Approach

- **D-01:** Planner's Wave 1 task is **characterization** — write a failing
  unit test that captures the exact current-behavior gap. Target scenarios:
  (a) a single selection of one DELETED file with `remoteSize > 0`, and
  (b) a mixed selection containing at least one DELETED file alongside
  non-deleted rows. The test must assert that `Queue` is enabled
  (`actionCounts.queueable >= 1`) and that `onQueueClick()` emits the
  deleted row's name.
- **D-02:** The fix follows from the red test. Root cause is unknown at
  context-gathering time — the current code (`BulkActionsBarComponent`,
  `ViewFile.service.ts` eligibility flags) **appears** to already implement
  union semantics on paper. Planner's characterization task is the discovery
  step. Possible root causes to investigate (non-exhaustive):
    1. `remoteSize === 0` on the user's repro rows, silently zeroing both
       `isQueueable` and `isRemotelyDeletable` despite DELETED status.
    2. A selection pruning / stale-selection path that drops DELETED
       filenames before the bar sees them.
    3. An `ngOnChanges`-cache miss where `visibleFiles` and `selectedFiles`
       update on separate ticks, leaving `_cachedSelectedViewFiles` empty
       between them.
    4. A `visibleFiles` mismatch — the bar's intersection filter
       (`visibleFiles ∩ selectedFiles`) drops rows that are selected but
       not in the current paged list.
- **D-03:** Fix scope is minimal. Whatever the single root cause is, the
  change should be the smallest edit that makes the characterization test
  pass without regressing the existing 489+ Angular specs. No refactors,
  no new services, no API changes.

### Union Contract (Unchanged From Phase 72)

- **D-04:** The spec is: a button is **enabled** iff at least one row in
  the current selection is eligible for that action (`actionCounts.X >= 1`).
  When clicked, it dispatches only to eligible rows; non-eligible rows in
  the selection are unaffected. This is the existing contract in
  `BulkActionsBarComponent.ngOnChanges` + `onXClick()` methods, and it
  is correct — Phase 76 must preserve it.
- **D-05:** Eligibility source of truth is the five `ViewFile.isX` flags
  computed in `ViewFileService.createViewFile()` (lines 348–369). These
  flags are the contract between model state and the bar. If the fix
  requires changing eligibility semantics (e.g., DELETED + `remoteSize === 0`
  edge case), the change lands there, not in the bar.

### No UI String or Visual Changes

- **D-06:** "Re-Queue from Remote" is **descriptive shorthand** for what the
  Queue action already does when dispatched against a DELETED row. The
  button label stays literally `Queue`. No tooltip change, no dynamic label,
  no second button. The phase 72 Variant-B visuals (D-07 through D-12 of
  Phase 72 CONTEXT) are locked.
- **D-07:** No per-row checkbox disabling. No count badges on buttons. No
  icon changes. The bar's DOM and SCSS are frozen modulo whatever minimal
  fix the bug requires.

### Per-row Dispatch & Selection Lifecycle (Unchanged)

- **D-08:** Current behavior stands: `BulkActionDispatcher._dispatch()`
  sends the filtered list of eligible filenames to the backend; on success,
  selection is cleared; on transient failure, selection is preserved for
  retry. Planner does NOT modify this flow. Partial-success toast already
  formats as "succeeded / failed" via `Localization.Bulk.PARTIAL_*`.

### Unit Test Coverage

- **D-09:** New unit tests land in
  `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts`
  (and/or `view-file.service.spec.ts` if the fix moves to eligibility flags).
  The three representative mixed selections required by phase success
  criteria #4 are, at minimum:
    1. **All-DELETED** — N>=1 DELETED rows, all with `remoteSize > 0`;
       Queue must be enabled; Delete Remote must be enabled; other three
       disabled.
    2. **DELETED + DOWNLOADING** — one of each; Queue enabled (1),
       Stop enabled (1), Delete Remote enabled (1), Extract disabled,
       Delete Local disabled.
    3. **DELETED + DOWNLOADED + STOPPED** — mixed states; union must show
       Queue (DELETED + STOPPED), Extract (DOWNLOADED), Delete Local
       (DOWNLOADED + STOPPED), Delete Remote (all three); Stop disabled.
- **D-10:** The characterization test from D-01 stays in the suite as a
  regression guard — it is the anchor that proves the bug is fixed and
  stays fixed.

### E2E Deferred to Phase 77

- **D-11:** Phase 76 ships the fix + unit tests only. Playwright specs
  covering the FIX-01 behavior are written in Phase 77 (UAT-01 scope). The
  ROADMAP dependency "Phase 77 depends on Phase 76" is honored: 76 lands
  first, 77's specs reference the already-fixed behavior.

### Claude's Discretion

- Exact root cause (see D-02 candidate list) — discovery job for planner.
- Whether the fix lands in `BulkActionsBarComponent`, `ViewFileService.
  createViewFile()`, the `FileSelectionService`, or the `TransferTable` wiring.
- Whether `isQueueable`/`isRemotelyDeletable` predicates need edge-case
  adjustment for DELETED rows where `remoteSize === 0` (e.g., when a
  deleted+rotated-out file should be un-selectable vs. just un-queueable).
- Exact test naming and file layout. The existing
  `bulk-actions-bar.component.spec.ts` has ~400 lines of precedent — match
  its style.
- Whether to add a fourth mixed case beyond the three required by D-09
  (e.g., DEFAULT + EXTRACTED + DELETED to exercise the full 5-button matrix).

### Folded Todos

_None — `gsd-sdk query todo.match-phase 76` returned zero matches. Pending
todos in the project inbox (test warnings, CSP detection, encryption,
rate limiting) are owned by other v1.1.1 phases._

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement + prior phase context
- `.planning/REQUIREMENTS.md` §FIX-01 — the milestone requirement this
  phase satisfies (v1.1.0 regression).
- `.planning/ROADMAP.md` §"Phase 76: Multiselect Bulk-Bar Action Union" —
  goal, success criteria, dependency note for Phase 77.
- `.planning/milestones/v1.1.0-phases/72-restore-dashboard-file-selection-and-action-bar/72-CONTEXT.md`
  — Phase 72's decisions on the bar component (D-13 adapt
  `BulkActionsBarComponent`, D-07 card-internal placement, Variant-B
  visuals). Phase 76 preserves all of it.
- `.planning/milestones/v1.1.0-phases/72-restore-dashboard-file-selection-and-action-bar/72-05-PLAN.md`
  (and 72-01 through 72-04) — the plans that built the current bar.
  Useful to understand the component's current wiring.

### Code artifacts to investigate / fix
- `src/angular/src/app/pages/files/bulk-actions-bar.component.ts` — the
  component that decides per-action enablement and filters dispatch. The
  `_recomputeCachedValues()` method (lines 86–132) is where union semantics
  live today; inspect whether the intersection with `visibleFiles`
  (line 88–90) is the failure point.
- `src/angular/src/app/pages/files/bulk-actions-bar.component.html` —
  template with the five buttons and their `actionCounts.X === 0` disable
  bindings. Verify `@if (hasSelection)` is not the wrong gate for any
  deleted-only scenario.
- `src/angular/src/app/services/files/view-file.service.ts` §`createViewFile`
  (lines 321–394) — where the five eligibility flags (`isQueueable`,
  `isStoppable`, `isExtractable`, `isLocallyDeletable`, `isRemotelyDeletable`)
  are computed from status + remoteSize + localSize. If DELETED behavior
  is wrong, it may be wrong here.
- `src/angular/src/app/pages/files/transfer-table.component.ts` —
  `BulkActionsBar` wiring (line 174–184 of the `.html`); `visibleFiles`
  binds to `pagedFilesList$`. Verify the intersection path under page
  transitions.
- `src/angular/src/app/pages/files/transfer-table.component.html` §lines
  174–184 — the template site that passes `visibleFiles` and `selectedFiles`
  into the bar.
- `src/angular/src/app/services/files/file-selection.service.ts` — signal-
  based selection. `pruneSelection()` exists but is not called outside
  tests; verify nothing else silently drops DELETED filenames.
- `src/angular/src/app/services/files/bulk-action-dispatcher.service.ts` —
  dispatch path. Unchanged, but referenced for the partial-success toast
  flow (Localization.Bulk.PARTIAL_*).

### Existing test files to extend
- `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts`
  — ~400 lines, existing contract for counts + eligibility + emit
  filtering. The three mixed-selection cases in D-09 land here.
- `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts`
  (if it exists) — candidate home for any eligibility-flag regression
  tests if the fix moves there.

### Project-level rules
- `.planning/PROJECT.md` — Constraints (dark-only, Deep Moss + Amber
  palette, no visual redesign for this phase). Key Decisions table
  already records the bulk-bar visual contract.
- `/Users/julianamacbook/.claude/projects/-Users-julianamacbook-seedsyncarr/memory/feedback_design_spec_rigor.md`
  — "Port AIDesigner HTML identically." Applies *if* visual changes are
  ever required (they are not for Phase 76).

### Victim status enum
- `src/angular/src/app/services/files/view-file.ts` §`ViewFile.Status` —
  the seven statuses: DEFAULT, DOWNLOADING, QUEUED, DOWNLOADED, EXTRACTING,
  EXTRACTED, STOPPED, DELETED. Test fixtures must cover the DELETED branch
  explicitly.

### Dispatch / backend flow (read-only reference)
- `src/angular/src/app/services/server/bulk-command.service.ts` — backend
  HTTP dispatcher. Phase 76 does not modify this.
- `src/angular/src/app/common/localization.ts` §`Bulk.PARTIAL_*` — partial-
  success toast strings. Unchanged.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`BulkActionsBarComponent`** already implements the union contract on
  paper: `_recomputeCachedValues` iterates the selection once, building
  five per-action filename lists; `actionCounts.X === 0` is the disable
  predicate. If this IS the fix site, the change is likely a small tweak
  to the intersection filter on lines 88–90.
- **`ViewFile.isQueueable`** today is `status ∈ {DEFAULT, STOPPED, DELETED}
  && remoteSize > 0` — DELETED is already in the queueable set. This
  matters for the characterization test: choose fixtures with
  `remoteSize > 0` explicitly.
- **`ViewFile.isRemotelyDeletable`** today is `status ∈ {DEFAULT, STOPPED,
  DOWNLOADED, EXTRACTED, DELETED} && remoteSize > 0` — also DELETED-aware.
- **Existing spec harness**
  (`bulk-actions-bar.component.spec.ts` helper `setInputsAndDetectChanges`)
  — reuse for D-09 test scenarios. Minimal scaffolding cost.
- **`FileSelectionService`** is pure state; no filter on status.
  `selectedFiles` is a plain `Set<string>` of filenames. DELETED rows
  are selectable today.

### Established Patterns
- **OnPush + Signals** — `TransferRowComponent` derives selection via a
  `computed()` signal; `BulkActionsBarComponent` uses `@Input` +
  `ngOnChanges` (no signals). Fix must match whichever component's style
  the edit lands in.
- **Set-based selection** — plain `Set<string>` of filenames; no
  wrapping in Immutable.js for this path (though the file list itself
  is `List<ViewFile>`).
- **`takeUntilDestroyed(destroyRef)`** — subscription cleanup idiom used
  throughout `TransferTableComponent`. If any new subscriptions are added,
  follow the pattern.
- **`ChangeDetectionStrategy.OnPush`** — every dashboard component.

### Integration Points
- **`TransferTableComponent` → `BulkActionsBar`** — binds `visibleFiles`
  to `pagedFilesList$` and `selectedFiles` to
  `fileSelectionService.selectedFiles$`. These are the two inputs the bar
  unions over. The page-transition `clearSelection` call
  (transfer-table.component.ts line 258) resets selection on every
  `goToPage`, so cross-page selection is impossible today.
- **Segment change clears selection** — `onSegmentChange` and
  `onSubStatusChange` both call `clearSelection()`. A user navigating
  from "all" to "errors → deleted" and selecting rows there IS a valid
  single-page repro for this phase.
- **Header select-all** — `onHeaderCheckboxClick` selects all visible
  (paged) rows, including DELETED. Good source of a worst-case
  fixture for D-09.

</code_context>

<specifics>
## Specific Ideas

- The user's stated symptom: "the bar doesn't show at all" for selections
  containing DELETED files, whether alone or mixed. Code analysis suggests
  the bar SHOULD render because `hasSelection` is purely `selectedFiles.size
  > 0`. This tension is exactly why D-01 mandates characterization first —
  do not assume; write the red test.
- "Re-Queue from Remote" in every FIX-01 discussion is descriptive: it
  means "Queue a DELETED-status file, which triggers re-download from
  remote because the file's localSize is 0." Planner should not search
  for a button with that literal label — none exists, and none is being
  added.
- The default landing segment is "all" — DELETED rows appear in "all" and
  in "errors → Deleted" sub-status. Both are valid repro surfaces.
- The bar is card-internal per Phase 72 D-07 — it does not float over the
  log pane. If the visual test is "the bar isn't visible," check that the
  user isn't scrolled past the transfer-table card before checking code.

</specifics>

<deferred>
## Deferred Ideas

- **Per-action count badges** (e.g., "Queue (2/5)") — considered, deferred.
  Additive visual change that the current spec does not require; would
  need an AIDesigner spec update.
- **Dynamic label swap** to "Re-Queue from Remote" when selection is all-
  DELETED — considered, rejected. No UI string changes in this phase.
- **Disabling row checkboxes when no action applies** — considered,
  rejected. Changes selection model semantics and contradicts the "union"
  principle (a row with no actions is still informationally selectable
  for future extension).
- **New E2E specs for FIX-01** — explicitly owned by Phase 77 (UAT-01).
  Phase 76 ships unit tests only.
- **Refactor `_recomputeCachedValues` to signals** — attractive but off-
  scope; `BulkActionsBarComponent` uses `@Input` + `ngOnChanges` today,
  keep it that way.
- **Backend changes to `BulkCommandService`** — none required. The union
  fix is client-side; the backend already accepts the five actions and
  returns per-file success/failure.

### Reviewed Todos (not folded)

_None — `gsd-sdk query todo.match-phase 76` returned zero matches. No
pending todos were reviewed for this phase._

</deferred>

---

*Phase: 76-multiselect-bulk-bar-action-union*
*Context gathered: 2026-04-20*
