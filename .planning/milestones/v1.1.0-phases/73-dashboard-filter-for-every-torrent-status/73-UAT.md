---
status: complete
phase: 73-dashboard-filter-for-every-torrent-status
source: [73-01-SUMMARY.md, 73-02-SUMMARY.md, 73-03-SUMMARY.md, 73-04-SUMMARY.md, 73-05-SUMMARY.md]
started: 2026-04-20T00:00:00Z
updated: 2026-04-20T00:00:00Z
resolution: accepted-structural
---

## Current Test

[testing complete]

## Tests

### 1. Done parent button visible between Active and Errors
expected: Segment filter row shows four parents in order — All · Active · Done · Errors. Done sits between Active and Errors.
result: pass
evidence: `transfer-table.component.html` renders four `button.btn-segment` in DOM order: All (L23) → Active (L28) → Done (L75) → Errors (L106).

### 2. Active expand reveals Pending sub (first position, workflow order)
expected: Clicking Active expands a sub-row with four buttons in this left-to-right order — Pending · Syncing · Queued · Extracting. Pending is the new leftmost sub.
result: pass
evidence: `@if (activeSegment === 'active')` block (L38-72) renders four `button.btn-sub` in order — Pending=DEFAULT (L40-47), Syncing=DOWNLOADING (L48-55), Queued=QUEUED (L56-63), Extracting=EXTRACTING (L64-71).

### 3. Done expand reveals Downloaded and Extracted subs
expected: Clicking Done expands a sub-row with two buttons — Downloaded · Extracted. Both visible; no other subs appear under Done.
result: pass
evidence: `@if (activeSegment === 'done')` block (L85-103) contains exactly two `button.btn-sub` — Downloaded=DOWNLOADED (L87-94), Extracted=EXTRACTED (L95-102).

### 4. Pending sub filters to DEFAULT (pre-download) files only
expected: With Active expanded, clicking Pending shows only files in the DEFAULT state. Files currently downloading, queued, or extracting are hidden.
result: pass
evidence: HTML L42 `(click)="onSubStatusChange(ViewFileStatus.DEFAULT)"` sets `subStatus=DEFAULT`; `segmentedFiles$` pipeline (TS L106-108) takes the `subStatus != null` branch and returns `files.filter(f => f.status === state.subStatus)` — narrows to DEFAULT only.

### 5. Done (no sub) shows Downloaded + Extracted files together
expected: Clicking Done without a sub selected shows both DOWNLOADED and EXTRACTED files intermixed. No active/errored files appear.
result: pass
evidence: `SEGMENT_STATUSES["done"] = [DOWNLOADED, EXTRACTED]` (TS L35-38). With `subStatus=null` and `segment="done"`, pipeline (TS L109-112) filters files to `allowed.includes(f.status)` — exactly DOWNLOADED ∪ EXTRACTED.

### 6. Downloaded sub filters to DOWNLOADED only
expected: With Done expanded, clicking Downloaded narrows the list to only files with status DOWNLOADED. Extracted files are hidden.
result: pass
evidence: HTML L89 `(click)="onSubStatusChange(ViewFileStatus.DOWNLOADED)"` sets `subStatus=DOWNLOADED`; same sub-branch filter as test 4 narrows to DOWNLOADED only.

### 7. URL persists filter — ?segment=done after clicking Done
expected: Clicking Done updates URL to `?segment=done`. Clicking Downloaded extends it to `?segment=done&sub=downloaded`. Clicking All clears both params.
result: pass
evidence: `onSegmentChange` (TS L229) and both paths of `onSubStatusChange` (TS L241, L252) call `_writeFilterToUrl()`. Helper (TS L363+) sets `queryParams={segment:null,sub:null}` when `activeSegment==="all"`, else `{segment:<seg>,sub:<sub>}`, merged via `router.navigate([], {queryParamsHandling:"merge", replaceUrl:true})`.

### 8. URL hydration — reloading with ?segment=done&sub=downloaded lands on Downloaded
expected: Opening `/dashboard?segment=done&sub=downloaded` shows Done expanded and Downloaded sub active. File list matches test 6 without a user click.
result: pass
evidence: `ngOnInit` reads `snapshot.queryParamMap.get("segment"|"sub")`, validates against `isSegment()` and `SEGMENT_STATUSES[segment]`, then (TS L195-200) sets `activeSegment`, `activeSubStatus`, and emits `filterState$.next({segment,subStatus,page:1})` before first render. Plan-04 test `URL persistence → hydrates segment+sub on init` asserts this end-to-end.

### 9. Invalid URL params silently fall back (no error toast)
expected: `/dashboard?segment=garbage` lands on All with no error toast/console dialog; garbage param removed from URL. `/dashboard?segment=active&sub=stopped` lands on Active with no sub.
result: pass
evidence: `segmentInvalid = segParam != null && !isSegment(segParam)` (TS L180); `segment` coerces to `"all"` when invalid. For `sub`, `SEGMENT_STATUSES[segment].includes(subParam)` gate drops mismatches to `null`. No `notification.show`/`console.error` call in `ngOnInit`. `if (segmentInvalid || subInvalid) { this._writeFilterToUrl(); }` (TS L204-206) rewrites URL to sanitized state. Plan-04 `notificationMock.show` NOT-called assertion locks this in.

### 10. Page navigation and search do NOT persist to URL
expected: Pagination clicks and search typing leave URL query params untouched. No `?page=` or `?search=` ever appears.
result: pass
evidence: `goToPage` (TS L379-383) only emits `filterState$.next(...)` and `clearSelection()` — no `_writeFilterToUrl()` call. `onSearchInput` (TS L212-215) only drives `searchInput$.next(value)` — no `_writeFilterToUrl()` call. Same for `onPrevPage`/`onNextPage`.

### 11. Selection clears when segment changes (D-12 carry-forward)
expected: Tick one or more file checkboxes, click a different segment parent. All checkboxes clear and the multi-action bar disappears.
result: pass
evidence: `onSegmentChange` (TS L228) calls `this.fileSelectionService.clearSelection()` on every invocation, regardless of whether it's a new segment or a collapse-to-all. `onSubStatusChange` does the same on both return paths (TS L243, L257). Plan-04 test `should clear file selection when 'done' segment selected` asserts this via `selectionService.getSelectedCount()`.

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
