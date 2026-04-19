---
phase: 73-dashboard-filter-for-every-torrent-status
verified: 2026-04-19T00:00:00Z
status: human_needed
score: 27/27 must-haves verified (automated)
re_verification: false
human_verification:
  - test: "Run the full Playwright e2e suite: cd /Users/julianamacbook/seedsyncarr && make run-tests-e2e (requires docker-compose stack: myapp + chrome + remote)"
    expected: "All 10 dashboard.page.spec.ts tests pass, including the 3 new tests: 'should expand Done segment to reveal Downloaded and Extracted subs', 'should reveal Pending sub under Active', 'should persist Done filter via URL query param (D-09)'. Full dashboard suite: 10/10 green."
    why_human: "The e2e suite requires a docker-compose stack (Angular app + Chromium + remote SSH). This session cannot spin up containers. tsc exits 0 and all locator selectors are structurally verified against the post-Plan-02 template, but browser interaction and actual URL round-trip require the running stack."
---

# Phase 73: Dashboard Filter for Every Torrent Status — Verification Report

**Phase Goal:** Extend the dashboard transfer-table segment filter so every operationally-meaningful ViewFile.Status (DEFAULT, DOWNLOADED, EXTRACTED) is reachable as a filter sub-button under a new Done parent + Pending sub under Active, and persist active filter state via URL query params with silent fallback on invalid values.

**Verified:** 2026-04-19
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `activeSegment` accepts `'done'` as a valid type at all annotated sites | ✓ VERIFIED | `"all" \| "active" \| "done" \| "errors"` present at field (line 29), BehaviorSubject generic (line 55), `onSegmentChange` param (line 214). |
| 2 | `filterState$` BehaviorSubject generic includes `'done'` in segment union | ✓ VERIFIED | Line 55: `segment: "all" \| "active" \| "done" \| "errors"` |
| 3 | `onSegmentChange` accepts `'done'` and uses collapse-on-second-click semantics (D-08) | ✓ VERIFIED | Method signature (line 214) accepts `'done'`; body unchanged — condition `segment !== "all" && this.activeSegment === segment` covers `'done'` without modification |
| 4 | `segmentedFiles$` returns DOWNLOADED ∪ EXTRACTED when segment=`'done'` with no sub (D-06) | ✓ VERIFIED | Lines 108-113: `if (state.segment === "done") { return files.filter(f => f.status === ViewFile.Status.DOWNLOADED \|\| f.status === ViewFile.Status.EXTRACTED).toList(); }` |
| 5 | `segmentedFiles$` returns DEFAULT ∪ DOWNLOADING ∪ QUEUED ∪ EXTRACTING when segment=`'active'` with no sub (D-05) | ✓ VERIFIED | Lines 100-107: Active branch includes `ViewFile.Status.DEFAULT` as first clause |
| 6 | Sub-status code path at line 97 still works for any ViewFile.Status (unchanged) | ✓ VERIFIED | Line 97-99: `if (state.subStatus != null && state.segment !== "all") { return files.filter(f => f.status === state.subStatus).toList(); }` — unmodified |
| 7 | Done parent button renders between Active expand block and Errors parent in `.segment-filters` | ✓ VERIFIED | HTML lines 74-103: `<!-- Done: expandable parent -->` block between Active `}` and `<!-- Errors: expandable parent -->` |
| 8 | Done parent click triggers `onSegmentChange('done')` and toggles chevron | ✓ VERIFIED | Line 78: `(click)="onSegmentChange('done')"` with `ph-caret-down`/`ph-caret-up` conditional classes at lines 81-82 |
| 9 | When `activeSegment === 'done'`, expand block reveals Downloaded and Extracted sub-buttons | ✓ VERIFIED | Lines 85-103: `@if (activeSegment === 'done')` block contains two `btn-sub` buttons bound to `ViewFileStatus.DOWNLOADED` and `ViewFileStatus.EXTRACTED` |
| 10 | Active expand block reveals Pending as first sub (workflow order: Pending, Syncing, Queued, Extracting) | ✓ VERIFIED | Lines 38-72: Pending button (DEFAULT) at lines 40-47, before Syncing at lines 48-55 |
| 11 | All new sub-buttons use existing `.btn-sub` class verbatim — no new SCSS classes (D-15) | ✓ VERIFIED | All new buttons use `class="btn-sub"` only; no inline styles; no new class names introduced |
| 12 | Pending/Downloaded/Extracted sub-buttons show `.accent-dot` when their status matches `activeSubStatus` | ✓ VERIFIED | Each new sub has `@if (activeSubStatus === ViewFileStatus.DEFAULT/DOWNLOADED/EXTRACTED) { <span class="accent-dot"></span> }` |
| 13 | On init, URL `?segment=done` hydrates `activeSegment='done'` before first `filterState$` observation (D-09) | ✓ VERIFIED | `ngOnInit()` lines 181-207 reads `snapshot.queryParamMap.get("segment")`, validates, and calls `filterState$.next()` synchronously |
| 14 | On init, `?segment=done&sub=downloaded` hydrates both `activeSegment='done'` and `activeSubStatus=DOWNLOADED` | ✓ VERIFIED | `ngOnInit` per-segment validation tables (lines 62-78) allow `"downloaded"` under `done` segment |
| 15 | On init, invalid `?segment=garbage` silently falls back to `'all'` — no console.error, no toast (D-11) | ✓ VERIFIED | Lines 186-189: `VALID_SEGMENTS.has(segParam)` guard; no `console.*` or notification call in `ngOnInit` |
| 16 | On init, `?segment=active&sub=stopped` — segment hydrated, sub silently dropped to null (D-11) | ✓ VERIFIED | `VALID_SUBS_PER_SEGMENT["active"]` does not contain `"stopped"`; sub coerces to `null` |
| 17 | `onSegmentChange` writes `{segment: <value>, sub: null}` to URL via `Router.navigate` with `queryParamsHandling: 'merge'` (D-10) | ✓ VERIFIED | `_writeFilterToUrl()` at line 363, called from `onSegmentChange` at line 228; `queryParamsHandling: "merge"` at line 375 |
| 18 | `onSegmentChange('all')` writes `{segment: null, sub: null}` clearing both params | ✓ VERIFIED | `_writeFilterToUrl()` sets `queryParams = {segment: null, sub: null}` when `activeSegment === "all"` (lines 364-371) |
| 19 | `onSubStatusChange` writes `{segment: <current>, sub: <statusEnumString>}` on both return paths | ✓ VERIFIED | `_writeFilterToUrl()` called at lines 241 and 252 (both branches of `onSubStatusChange`) |
| 20 | `Router.navigate` uses `relativeTo: this.route` and `[]` commands — no path manipulation possible (D-10 security) | ✓ VERIFIED | Lines 372-377: `this.router.navigate([], { relativeTo: this.route, ..., replaceUrl: true })` |
| 21 | Page navigation and search do NOT write to URL (D-11) | ✓ VERIFIED | `goToPage`, `onPrevPage`, `onNextPage`, `onSearchInput` do not call `_writeFilterToUrl()` |
| 22 | Unit TestBed provides Router and ActivatedRoute mocks; 17 new tests cover Done branch, Pending sub, URL hydration/write-back, D-12 carry-forward | ✓ VERIFIED | spec.ts lines 136-142 (mocks), 166-176 (providers), 208-214 (4-button assertion), 502-627 (filter logic), 954-1053 (URL persistence describe — 11 tests); total 566 tests, +17 from baseline 549 |
| 23 | `DashboardPage.getSegmentButton(name)` locator scoped to `.segment-filters` resolves All/Active/Done/Errors | ✓ VERIFIED | `dashboard.page.ts` lines 72-74: `this.page.locator('.segment-filters').getByRole('button', { name, exact: true })` |
| 24 | `DashboardPage.getSubButton(name)` locator resolves all 8 sub-button labels by visible text | ✓ VERIFIED | `dashboard.page.ts` lines 76-78: `this.page.locator('.segment-filters button.btn-sub').getByText(name, { exact: true })` |
| 25 | E2e test: clicking Done parent reveals Downloaded and Extracted subs | ✓ VERIFIED (structural) | `dashboard.page.spec.ts` lines 77-85: assertions wired to correct locators and production template selectors. Runtime: see human verification. |
| 26 | E2e test: clicking Active parent reveals Pending sub | ✓ VERIFIED (structural) | `dashboard.page.spec.ts` lines 87-93. Runtime: see human verification. |
| 27 | E2e test: clicking Done parent updates URL to contain `?segment=done` (D-09 round-trip) | ✓ VERIFIED (structural) | `dashboard.page.spec.ts` lines 95-99: `expect(page).toHaveURL(/[?&]segment=done(&\|$)/)`. Runtime: see human verification. |

**Score:** 27/27 automated truths verified. 3 e2e truths verified structurally; runtime verification is the single outstanding human item.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/angular/src/app/pages/files/transfer-table.component.ts` | Widened union + Done branch + Pending in Active + ngOnInit URL hydration + `_writeFilterToUrl` | ✓ VERIFIED | 379 lines; all changes confirmed by direct read. |
| `src/angular/src/app/pages/files/transfer-table.component.html` | Done parent button + Done expand block + Pending sub-button | ✓ VERIFIED | 213 lines; DOM order Active(31) < Done(78) < Errors(109); all new buttons use existing SCSS classes. |
| `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` | Updated TestBed mocks + TEST_TEMPLATE + 17 new tests | ✓ VERIFIED | 1055 lines; Router/ActivatedRoute providers at lines 174-175; 4-button assertion at line 208; filter-logic tests 504-627; URL persistence describe 956-1053. |
| `src/e2e/tests/dashboard.page.ts` | `getSegmentButton` and `getSubButton` locator methods | ✓ VERIFIED | Lines 72-78; both methods present with exhaustive name unions. |
| `src/e2e/tests/dashboard.page.spec.ts` | 3 new Playwright tests for Done expand, Pending reveal, URL round-trip | ✓ VERIFIED (structural) | Lines 77-99; tests appended correctly inside the existing describe block. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `activeSegment` field | `filterState$` BehaviorSubject | `onSegmentChange` calls `filterState$.next()` | ✓ WIRED | Lines 220, 225 — both branches of `onSegmentChange` write `filterState$.next()` |
| `filterState$` | `segmentedFiles$` | `combineLatest` in constructor | ✓ WIRED | Line 89-95: `combineLatest([this.viewFileService.filteredFiles, this.filterState$.pipe(...)])` |
| `Done parent button` | `onSegmentChange` | `(click)="onSegmentChange('done')"` | ✓ WIRED | HTML line 78 |
| `Done sub-buttons` | `onSubStatusChange` | `(click)="onSubStatusChange(ViewFileStatus.DOWNLOADED/EXTRACTED)"` | ✓ WIRED | HTML lines 89-102 |
| `Pending sub-button` | `onSubStatusChange` | `(click)="onSubStatusChange(ViewFileStatus.DEFAULT)"` | ✓ WIRED | HTML line 42 |
| `ngOnInit` | `ActivatedRoute.snapshot.queryParamMap` | `this.route.snapshot.queryParamMap.get("segment"/"sub")` | ✓ WIRED | Lines 182-183 |
| `onSegmentChange / onSubStatusChange` | `Router.navigate` | `_writeFilterToUrl()` helper | ✓ WIRED | Lines 228, 241, 252 → `_writeFilterToUrl()` at line 363 |
| URL-supplied segment/sub values | Validated enum allow-lists | `VALID_SEGMENTS` and `VALID_SUBS_PER_SEGMENT` | ✓ WIRED | Lines 62-78 (allow-lists); lines 186-198 (validation logic) |
| `DashboardPage.getSegmentButton` | `.segment-filters` parent buttons | `page.locator('.segment-filters').getByRole('button', { name, exact: true })` | ✓ WIRED | dashboard.page.ts line 73 |
| `DashboardPage.getSubButton` | `.segment-filters button.btn-sub` | `page.locator('.segment-filters button.btn-sub').getByText(name, { exact: true })` | ✓ WIRED | dashboard.page.ts line 77 |

---

### Data-Flow Trace (Level 4)

The core filter pipeline is: `ViewFileService.filteredFiles` → `segmentedFiles$` → `pagedFiles$` → template `async` pipe.

| Component | Data Variable | Source | Produces Real Data | Status |
|-----------|--------------|--------|-------------------|--------|
| `segmentedFiles$` Done branch | `files` from `ViewFileService.filteredFiles` | `combineLatest` at line 89 — `this.viewFileService.filteredFiles` | Yes — service streams real file list; filter is a pure `Immutable.List.filter()` | ✓ FLOWING |
| `filterState$` | `{segment, subStatus, page}` | `onSegmentChange`/`onSubStatusChange` write `filterState$.next(...)` + `ngOnInit` hydrates from URL | Yes — state driven by user interaction and URL params | ✓ FLOWING |
| `ngOnInit` hydration | `activeSegment`, `activeSubStatus` | `ActivatedRoute.snapshot.queryParamMap` validated against `VALID_SEGMENTS`/`VALID_SUBS_PER_SEGMENT` | Yes — reads real URL params; null/invalid silently degrade | ✓ FLOWING |
| `_writeFilterToUrl` write-back | `queryParams` | `this.activeSegment` / `this.activeSubStatus` (typed; bounded by union and ViewFile.Status) | Yes — writes real component state to URL | ✓ FLOWING |

No hollow props, no hardcoded empty returns, no static stubs detected.

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — the Angular app requires a running server + browser to test behavioral outputs. Unit tests (Karma/Jasmine, 566 passing per 73-04 SUMMARY) provide programmatic coverage. The only runnable isolated artifact is `ng build`, which the SUMMARY documents as passing (`ng build --configuration development` exits 0 for Plans 02 and 03).

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| D-01 | 01, 02, 04, 05 | Add 3 new filterable statuses: DEFAULT, DOWNLOADED, EXTRACTED | ✓ SATISFIED | Active branch +DEFAULT; Done branch (DOWNLOADED∪EXTRACTED); unit tests for each; e2e locators for all 3 labels |
| D-03 | 02, 05 | Labels: DEFAULT→Pending, DOWNLOADED→Downloaded, EXTRACTED→Extracted | ✓ SATISFIED | HTML line 46 "Pending", lines 93/101 "Downloaded"/"Extracted"; e2e `getByText` selectors use exact labels |
| D-04 | 01, 02, 04 | Done parent as sibling of Active/Errors; layout All/Active/Done/Errors | ✓ SATISFIED | HTML DOM order Active(31)<Done(78)<Errors(109); 4-button unit assertion; `getSegmentButton` union |
| D-05 | 01, 02, 04 | Pending lives under Active, left-most sub | ✓ SATISFIED | HTML Pending before Syncing (lines 40-47 vs 48-55); Active branch includes DEFAULT |
| D-06 | 01, 04 | Done parent (no sub) = DOWNLOADED ∪ EXTRACTED | ✓ SATISFIED | `.ts` lines 108-113; unit test "should filter to DOWNLOADED ∪ EXTRACTED" |
| D-07 | 01 | Preserve state shape `activeSegment: union + activeSubStatus: ViewFile.Status\|null` | ✓ SATISFIED | Field types unchanged structurally; union widened to include `'done'` |
| D-08 | 01 | Done state transitions identical to Active/Errors (collapse-on-second-click) | ✓ SATISFIED | `onSegmentChange` body unmodified; condition `segment !== "all" && this.activeSegment === segment` covers `'done'` |
| D-09 | 03, 04, 05 | Persist via URL `?segment=&sub=`; on init hydrate; on change write | ✓ SATISFIED | `ngOnInit` + `_writeFilterToUrl`; unit tests (6 hydration + 5 write-back); e2e URL round-trip test (structural) |
| D-10 | 03, 04 | `Router.navigate` with `queryParamsHandling: 'merge'` | ✓ SATISFIED | `_writeFilterToUrl()` line 375; `relativeTo: this.route` line 373; unit test asserts `queryParamsHandling === "merge"` |
| D-11 | 03, 04 | Silent fallback: invalid segment→`'all'`; mismatched sub→`null`; page/search NOT persisted | ✓ SATISFIED | `VALID_SEGMENTS`/`VALID_SUBS_PER_SEGMENT` guards; no console/notification in `ngOnInit`; `notificationMock.show` not-called assertions pass; `goToPage`/`onSearchInput` do not call `_writeFilterToUrl` |
| D-12 | 04 | Filter changes continue to clear file selection (carry-forward from Phase 72 D-04) | ✓ SATISFIED | `fileSelectionService.clearSelection()` called in `onSegmentChange` (line 227) and both paths of `onSubStatusChange` (lines 240, 251); unit test "should clear file selection when 'done' segment selected" |
| D-13 | 01 | Filter changes continue to reset page to 1 (inherited via existing combineLatest flow) | ✓ SATISFIED | `this.currentPage = 1; this.filterState$.next({..., page: 1})` in both branches of `onSegmentChange` and both paths of `onSubStatusChange` |
| D-14 | 02 | Mobile: new buttons inherit `.segment-filters` hidden-below-768px rule — no new media queries | ✓ SATISFIED | No new SCSS classes introduced (confirmed by Plan 02 SUMMARY); all new buttons are inside `.segment-filters` |
| D-15 | 02 | Reuse `.btn-segment`, `.btn-sub`, `.accent-dot`, `.segment-divider` verbatim | ✓ SATISFIED | All new buttons confirmed to use only existing class names; Plan 02 SUMMARY explicitly confirms no new class names |

**All 14 D-item requirements satisfied.** No orphaned requirements (D-02 is explicitly deferred by CONTEXT.md — WAITING_FOR_IMPORT skipped; this is not a requirement of this phase).

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| (none) | — | — | — |

Scanned `transfer-table.component.ts`, `transfer-table.component.html`, `transfer-table.component.spec.ts`, `dashboard.page.ts`, `dashboard.page.spec.ts` for TODO/FIXME/placeholder/`return null`/`return []`/stub patterns. None found in the new code added by this phase. All new branches return real filtered data. All new buttons are fully wired to existing TypeScript methods with concrete enum values.

---

### Human Verification Required

### 1. E2E Suite — Full Playwright Dashboard Test Run

**Test:** `cd /Users/julianamacbook/seedsyncarr && make run-tests-e2e`

Then confirm the dashboard suite (10 tests) is green:
- `should expand Done segment to reveal Downloaded and Extracted subs` — click Done parent, assert Downloaded/Extracted become visible
- `should reveal Pending sub under Active` — click Active parent, assert Pending becomes visible
- `should persist Done filter via URL query param (D-09)` — click Done parent, assert `page.url()` matches `/[?&]segment=done(&|$)/`
- All 7 existing Phase 72 dashboard tests continue to pass (selection-clearing, action-bar, file list)

**Expected:** All 10 tests pass (exit 0).

**Why human:** The Playwright suite requires a docker-compose stack (`myapp` serving Angular on the configured port, `chrome` running Chromium, `remote` SSH as documented in `src/e2e/README.md`). This session cannot spin up containers. All locator selectors (`getSegmentButton`, `getSubButton`, `toHaveURL`) are verified against the post-Plan-02 template via `tsc --noEmit` (exit 0) and direct file inspection, but clicking real buttons in a real browser requires the running stack. The structural wiring is complete and correct; the e2e tests are the runtime confidence check.

---

### Gaps Summary

No gaps. All 27 automated must-haves verified. The single outstanding item is the runtime e2e suite, which is CI-gated by design (documented in Plan 05 SUMMARY and the phase verification notes). The phase goal is structurally achieved; runtime confirmation is the expected final step for any UI feature in this project.

---

_Verified: 2026-04-19_
_Verifier: Claude (gsd-verifier)_
