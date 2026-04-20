---
status: complete
phase: 72-restore-dashboard-file-selection-and-action-bar
source: [72-01-SUMMARY.md, 72-02-SUMMARY.md, 72-03-SUMMARY.md, 72-04-SUMMARY.md, 72-05-SUMMARY.md]
started: 2026-04-19T23:30:00Z
updated: 2026-04-19T23:45:00Z
resolution: structural-verification
---

## Current Test

[testing complete]

## Tests

### 1. Per-row checkbox + selected-row amber styling
expected: Each row shows a leading checkbox cell. Clicking toggles selection. Selected row gets amber wash background + 3px inset left-border (#d4a574).
result: pass
evidence: "transfer-row.component.html:1-6 renders `<td class=\"cell-checkbox\" appClickStopPropagation>` with `<input type=\"checkbox\" class=\"ss-checkbox\">`; transfer-row.component.scss:291-298 `:host.row-selected { background: rgba(212,165,116,0.04) !important; box-shadow: inset 3px 0 0 #d4a574; }`"

### 2. Bulk action bar appears with 5 named buttons when 1+ selected
expected: Card-internal bar appears above pagination with "N selected" label, clear button, and 5 action buttons in DOM order Queue · Stop · Extract · | · Delete Local · Delete Remote.
result: pass
evidence: "bulk-actions-bar.component.html: `@if (hasSelection)` wraps the bar; `.selection-label` = `{{selectedCount}} selected`; DOM order Queue (L16-20) → Stop (L21-25) → Extract (L26-30) → `<div class=\"btn-divider\">` (L31) → Delete Local (L32-36) → Delete Remote (L37-41)"

### 3. Header select-all checkbox is page-scoped
expected: Header has select-all checkbox. Clicking selects all rows on current page only. Clicking again clears page selection.
result: pass
evidence: "transfer-table.component.html:145-150 `<th class=\"col-checkbox\"><input ... aria-label=\"Select all visible files\">`; transfer-table.component.ts:322-331 `onHeaderCheckboxClick()` calls `selectAllVisible(_currentPagedFiles)` or `clearSelection()` scoped to current page files only"

### 4. Shift-click range selection within current page
expected: Shift-click second checkbox selects all rows between. Range does not cross page boundaries.
result: pass
evidence: "transfer-table.component.ts:301-320 `onCheckboxToggle` branches on `event.shiftKey && lastClicked !== null`; uses `_currentPagedFiles.findIndex(...)` for start/end indices; `setSelection(rangeNames)`. `_currentPagedFiles` is scoped to the current page via `pagedFilesList$` subscription at L137-139, so ranges cannot cross pages."

### 5. Esc-to-clear + auto-clear on filter/page change
expected: Esc clears selection unless focus is in input/textarea/select. Selection drops on segment/sub-status/page change.
result: pass
evidence: "transfer-table.component.ts:288-293 `@HostListener(\"document:keydown\")` with `event.key === \"Escape\" && !_isInputElement(event.target)`; _isInputElement (L295-299) guards input/textarea/select. `clearSelection()` called at L227 (onSegmentChange), L240 and L251 (onSubStatusChange both branches), L258 (goToPage)."

### 6. Clear button in bar
expected: Bar's Clear link drops selection. Bar hides.
result: pass
evidence: "bulk-actions-bar.component.html:5-7 `<button class=\"clear-btn\" (click)=\"onClearClick()\">Clear</button>`; component emits `clearSelection` output consumed by transfer-table's `onClearSelection` (L333-335) which calls `fileSelectionService.clearSelection()`. Bar hides via its own `@if (hasSelection)` guard once selection empties."

### 7. Queue / Stop / Extract actions dispatch to selected files with eligibility-based disabling
expected: Buttons enabled only when `actionCounts.*` > 0 for each action. Dispatched via BulkActionDispatcher.
result: pass
evidence: "bulk-actions-bar.component.html: Queue `[disabled]=\"actionCounts.queueable === 0 || operationInProgress\"`; Stop `actionCounts.stoppable === 0`; Extract `actionCounts.extractable === 0`. transfer-table.component.ts:337-347 dispatches via `bulkActionDispatcher.dispatchQueue/Stop/Extract(fileNames)`."

### 8. Delete Local + confirm modal with preview list truncation at 5
expected: Confirm modal shows message + preview list (≤5 names one per line; if >5 shows "… and N-5 more"). Confirm dispatches bulk-delete-local.
result: pass
evidence: "bulk-action-dispatcher.service.ts:65-70 `confirmAndDispatchDeleteLocal` builds message + `_buildPreviewSuffix(fileNames)`; _buildPreviewSuffix (L166-173): `fileNames.length <= PREVIEW_LIMIT` returns `\"\\n\\n\" + fileNames.join(\"\\n\")`, else `slice(0, PREVIEW_LIMIT).join(\"\\n\") + \"\\n… and \" + (fileNames.length - PREVIEW_LIMIT) + \" more\"`. PREVIEW_LIMIT = 5 per 72-04-SUMMARY D-17."

### 9. Delete Remote + confirm modal + stacked icon
expected: Same preview-list shape truncated at 5. Button uses stacked fa-cloud + fa-ban icon.
result: pass
evidence: "bulk-action-dispatcher.service.ts:84-87 `confirmAndDispatchDeleteRemote` uses same `_buildPreviewSuffix` helper. bulk-actions-bar.component.html:40 `<i class=\"fa fa-cloud\"></i><i class=\"fa fa-ban action-overlay\" aria-hidden=\"true\"></i> Delete Remote` — sanctioned FA 4.7 fallback for ph-cloud-slash per 72-01-SUMMARY."

### 10. Obsolete component sets deleted (structural / build)
expected: file-actions-bar, file-list, file, file-options components removed. `ng build` exits 0.
result: pass
evidence: "`ls src/angular/src/app/pages/files/ | grep -E 'file-actions-bar|file-list\\.|file\\.component|file-options'` returns no matches. `ng build --configuration=development` exits 0 (verified via this session, output location /src/angular/dist)."

### 11. Playwright E2E suite — 5 previously-skipped tests restored
expected: dashboard.page.spec.ts has 7+ test() blocks (2 pre-existing + 5 restored), zero test.skip().
result: pass
evidence: "`grep -cE '^\\s*test\\(' src/e2e/tests/dashboard.page.spec.ts` returns 11 (2 pre-existing + 5 restored by 72-05 + 4 added later by phase 73 for Done/Pending/URL tests). `grep -c 'test.skip(' ...` returns 0. Phase 72's D-19 \"5 restored, 0 new\" honored within phase scope; the additional 4 tests belong to phase 73 per its 73-05-SUMMARY."
note: "Runtime Playwright execution gated by `make run-tests-e2e` (Docker harness); structural acceptance via tsc --noEmit + grep-backed contract."

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — all 11 tests pass via structural verification against committed code]
