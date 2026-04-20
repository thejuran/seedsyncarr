---
phase: 72-restore-dashboard-file-selection-and-action-bar
plan: 04
status: complete
decisions: [D-02, D-03, D-04, D-05, D-09, D-10, D-11, D-12, D-15, D-16, D-17]
tasks_completed: 3
files_modified:
  - src/angular/src/app/pages/files/transfer-table.component.ts
  - src/angular/src/app/pages/files/transfer-table.component.html
  - src/angular/src/app/pages/files/transfer-table.component.scss
  - src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts
---

# 72-04 Summary — TransferTable selection orchestration + bulk actions

## What was built

TransferTableComponent is now the orchestration hub for dashboard file
selection. It injects FileSelectionService, BulkCommandService,
ConfirmModalService, NotificationService, and ChangeDetectorRef. The table
renders a page-scoped "select all visible" checkbox in the header, clears
selection on every page / segment / sub-status change, handles Esc-to-clear
(unless focus is in an input/textarea/select), resolves shift-click ranges
within the current paged list via a cached `_currentPagedFiles`, inserts
the adapted BulkActionsBarComponent card-internally above the pagination
footer, and dispatches all 5 bulk actions through the existing
BulkCommandService + ConfirmModalService infrastructure.

## Bar insertion point

The `<app-bulk-actions-bar>` element is positioned between the closing
`</div>` of the `<div class="transfer-table-wrap">` block and the
`<!-- Pagination Footer -->` comment, matching Variant B line 306 position.
The bar's own `@if (hasSelection)` guard from plan 01 ensures it renders
only when 1+ files are selected (D-09).

## Delete preview-list truncation threshold (D-17)

Threshold chosen: **5** (Claude's discretion).

- If `fileNames.length <= 5`: show all file names, one per line, appended
  as `"\n\n" + fileNames.join("\n")`.
- If `fileNames.length > 5`: show the first 5 followed by
  `"\n… and {N-5} more"`.

Implemented in `_buildPreviewSuffix()`. The suffix is concatenated onto
`Localization.Modal.BULK_DELETE_*_MESSAGE(count)` before passing to
`confirmModalService.confirm({body, …})`. ConfirmModalService's existing
`escapeHtml()` handles DOM-XSS mitigation on the concatenated string
(T-72-09).

## ConfirmModalService call style

`async/await` was chosen over `.then()` per D-17 Claude's discretion.
`onBulkDeleteLocal` and `onBulkDeleteRemote` are both `async` methods that
`await` the `confirm()` promise and only call `_executeBulkAction` if the
user confirmed.

## Selector contract for plan 05 (E2E Playwright)

Plan 05's dashboard page-object should target:

- Header checkbox: `.transfer-table thead th.col-checkbox input.ss-checkbox`
- Row checkbox: `app-transfer-row td.cell-checkbox input.ss-checkbox`
- Bulk-action bar container: `app-bulk-actions-bar`
- Selection label: `app-bulk-actions-bar .selection-label` (e.g. "3 selected")
- Clear link: `app-bulk-actions-bar button.clear-btn`
- Action buttons (5): `app-bulk-actions-bar button.action-btn` (in DOM
  order: Queue, Stop, Extract, Delete Local, Delete Remote)

## Backend endpoints

NO new backend endpoints were added. The implementation reuses the
existing `BulkCommandService.executeBulkAction(action, fileNames)`
infrastructure that routes to `/server/command/bulk` and returns a
`BulkActionResult` (D-16). No changes to any service file outside the
component.

## emptySet / emptySetList declaration ownership

Both fallback constants are declared ONCE each, in the class body of
`transfer-table.component.ts` (Task 1):

- `public readonly emptySet = new Set<string>();`
- `public readonly emptySetList = List<ViewFile>();`

Task 2 did NOT re-declare either; the template consumes them via `??`
defaults on `[selectedFiles]` and `[visibleFiles]`.

## Spec count delta

- Pre-Task-3: 26 specs
- Post-Task-3: 42 specs (16 new across 5 describe blocks: 3 selection-clear
  + 2 Esc + 2 header + 3 shift-click + 6 bulk dispatch)
- Result: 42/42 green

## Build / test verification

- `npx tsc --noEmit -p src/tsconfig.app.json` — exits 0
- `npx ng build --configuration=development` — exits 0 (only pre-existing
  `@import` deprecation warnings from styles.scss)
- `npx ng test --include='**/transfer-table.component.spec.ts' --watch=false --browsers=ChromeHeadless` — 42/42 SUCCESS

## Notes for downstream plans

- Plan 05 can now un-skip the 5 dashboard Playwright tests against the
  selectors listed above. The header checkbox uses the same
  `.ss-checkbox` class as row checkboxes; distinguish by ancestor
  (`th.col-checkbox` vs `td.cell-checkbox`) or by `aria-label`
  (`"Select all visible files"` vs `"Select {file.name}"`).
- The shift-click contract is page-scoped: range resolution operates on
  `_currentPagedFiles` only, so ranges never cross page boundaries — this
  matches D-02 + D-03 intent.
- Selection survives transient errors (HTTP 429 or 5xx) per the M007
  contract: `_executeBulkAction`'s error path preserves selection on
  transient failures and clears it on non-transient errors.
