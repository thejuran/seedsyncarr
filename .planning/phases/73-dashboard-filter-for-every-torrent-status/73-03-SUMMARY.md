---
phase: 73-dashboard-filter-for-every-torrent-status
plan: 03
subsystem: ui
tags: [angular, router, query-params, persistence, transfer-table, activated-route]

# Dependency graph
requires:
  - phase: 73-dashboard-filter-for-every-torrent-status
    plan: 01
    provides: "Widened activeSegment union + Done branch in segmentedFiles$"
provides:
  - "ngOnInit URL hydration: reads ?segment= and ?sub= via ActivatedRoute.snapshot.queryParamMap, validates, hydrates activeSegment+activeSubStatus before first filterState$ subscription"
  - "_writeFilterToUrl helper: Router.navigate([], {merge, replaceUrl:true}) called from onSegmentChange(1x) and onSubStatusChange(2x)"
  - "Silent fallback: invalid segment coerces to 'all'; sub not belonging to segment silently drops to null (D-11)"
affects: [73-04, 73-05]

# Tech tracking
tech-stack:
  added:
    - "Router (from @angular/router) — first navigate() usage in TransferTableComponent"
    - "ActivatedRoute (from @angular/router) — first queryParamMap snapshot read in this component"
  patterns:
    - "URL hydration on init via snapshot.queryParamMap.get() — NEW pattern, no prior codebase analog"
    - "Filter write-back via Router.navigate([], {relativeTo, queryParamsHandling:'merge', replaceUrl:true}) — NEW pattern"
    - "Per-segment sub-status validation tables (Set<string>) with silent fallback"

key-files:
  created: []
  modified:
    - src/angular/src/app/pages/files/transfer-table.component.ts

key-decisions:
  - "Used Router constructor injection (not inject()) to stay consistent with existing service injection style in the constructor"
  - "replaceUrl: true chosen to prevent filter clicks from bloating browser history — browser back/forward as filter undo deferred to follow-up phase (CONTEXT line 133)"
  - "Literal ViewFile.Status enum-string values used in URL (?sub=downloaded, ?sub=default) — zero mapping layer per CONTEXT discretion guidance"
  - "ngOnInit emits filterState$.next() only when state is non-default — avoids a redundant emit since BehaviorSubject is already initialised to {segment:all, subStatus:null, page:1}"
  - "Both params set to null (not omitted) when segment=all, relying on merge semantics to clear them from the URL"

# Metrics
duration: 12min
completed: 2026-04-19
---

# Phase 73 Plan 03: URL Query-Parameter Persistence Summary

**Added URL query-parameter persistence to TransferTableComponent: ngOnInit hydrates activeSegment+activeSubStatus from ?segment=/?sub= with silent fallback validation, and _writeFilterToUrl writes state back via Router.navigate with merge semantics on every filter change**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-04-19
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `OnInit` to the `@angular/core` import; implemented `TransferTableComponent implements OnInit`
- Added `Router` and `ActivatedRoute` imports from `@angular/router`; injected both via constructor params
- Added `VALID_SEGMENTS` (`Set<string>` of `{"all","active","done","errors"}`) and `VALID_SUBS_PER_SEGMENT` (per-segment `Set<string>` of `ViewFile.Status` literal strings) as private readonly fields (lines 62–79)
- Implemented `ngOnInit()` (line 181): reads `snapshot.queryParamMap.get("segment")` and `"sub"` once, validates against the allow-lists, silently falls back invalid segment to `"all"` and invalid/mismatched sub to `null` per D-11, then emits `filterState$.next()` only when state is non-default
- Added `_writeFilterToUrl()` private helper (line 363): clears both params when `segment=all`, otherwise sets `segment=<value>&sub=<statusOrNull>` — uses `Router.navigate([], {relativeTo, queryParamsHandling:"merge", replaceUrl:true})`
- Wired `_writeFilterToUrl()` at end of `onSegmentChange` (line 228) — 1 call site
- Wired `_writeFilterToUrl()` on both return paths of `onSubStatusChange` (lines 241, 252) — 2 call sites
- tsc exits 0 after both tasks

## Task Commits

1. **Task 1: Inject Router+ActivatedRoute and add ngOnInit URL hydration** — `3d1fbbe`
2. **Task 2: Add _writeFilterToUrl helper and wire into change handlers** — `67241f1`

## Files Created/Modified

- `src/angular/src/app/pages/files/transfer-table.component.ts` — 71 net lines added (51 Task 1, 20 Task 2)

## Exact Line Ranges (after both tasks)

| Addition | Lines |
|----------|-------|
| `import {Router, ActivatedRoute}` | 5 |
| `implements OnInit` on class declaration | 27 |
| `VALID_SEGMENTS` field | 62 |
| `VALID_SUBS_PER_SEGMENT` field | 63–79 |
| `Router` + `ActivatedRoute` constructor params | 85–86 |
| `ngOnInit(): void` method | 181–207 |
| `this._writeFilterToUrl()` in `onSegmentChange` | 228 |
| `this._writeFilterToUrl()` in `onSubStatusChange` (deselect path) | 241 |
| `this._writeFilterToUrl()` in `onSubStatusChange` (select path) | 252 |
| `_writeFilterToUrl(): void` helper | 363–378 |

## Validated Allow-List Shape

**Segments:** `{"all", "active", "done", "errors"}` — any other value (including `null`) silently coerces to `"all"`

**Per-segment sub-status sets** (literal `ViewFile.Status` enum strings):
- `active` → `{DEFAULT, DOWNLOADING, QUEUED, EXTRACTING}`
- `done` → `{DOWNLOADED, EXTRACTED}`
- `errors` → `{STOPPED, DELETED}`

A sub value present in the URL but not in the named segment's set silently drops to `null` (e.g., `?segment=active&sub=stopped` resolves to `activeSegment="active", activeSubStatus=null`).

## D-11 Confirmation: Page and Search Not Persisted

- `goToPage`, `onPrevPage`, `onNextPage` do NOT call `_writeFilterToUrl` — page state is session-only
- `onSearchInput` does NOT call `_writeFilterToUrl` — name filter is session-only
- Verified: `awk '/goToPage\(page: number\)/,/^    \}$/' ... | grep -c '_writeFilterToUrl'` returns `0`
- Verified: `awk '/onSearchInput\(value: string\)/,/^    \}$/' ... | grep -c '_writeFilterToUrl'` returns `0`

## replaceUrl: true Rationale

`replaceUrl: true` prevents filter clicks from pushing new entries onto the browser history stack. CONTEXT.md (line 133) explicitly defers "Browser back/forward as filter navigation" to a follow-up phase. Using `replaceUrl: true` avoids accidentally shipping that behavior half-finished while still persisting the URL for direct links and page reload.

## Note: Plan 04 Must Provide Router + ActivatedRoute Mocks

`transfer-table.component.spec.ts` uses `TestBed` to construct `TransferTableComponent`. Now that the component has `Router` and `ActivatedRoute` as constructor dependencies, the spec's `TestBed.configureTestingModule` must add providers for both:

```typescript
const mockQueryParamMap: { [k: string]: string | null } = {};
const mockActivatedRoute = {
    snapshot: {
        queryParamMap: { get: (k: string) => mockQueryParamMap[k] ?? null }
    }
};
const mockRouter = { navigate: jasmine.createSpy("navigate") };

// In providers:
{provide: ActivatedRoute, useValue: mockActivatedRoute},
{provide: Router, useValue: mockRouter},
```

Without these providers, the existing spec will fail at component construction. Plan 04 is designated to add these mocks and the new URL hydration + write-back test cases.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all URL read/write paths are fully wired.

## Threat Flags

No new network endpoints, auth paths, or trust boundary changes beyond what was declared in the plan's `<threat_model>`. All three STRIDE mitigations (T-73-03-01, T-73-03-02, T-73-03-03) are implemented as specified:
- `VALID_SEGMENTS` allow-list enforces T-73-03-01
- `VALID_SUBS_PER_SEGMENT` per-segment allow-list enforces T-73-03-02
- `navigate([], {relativeTo: this.route})` with empty commands array enforces T-73-03-03

## Self-Check: PASSED

- `src/angular/src/app/pages/files/transfer-table.component.ts` — exists, 379 lines
- Commit `3d1fbbe` — exists (Task 1)
- Commit `67241f1` — exists (Task 2)
- tsc exits 0 on main repo
- All acceptance criteria verified via grep

---
*Phase: 73-dashboard-filter-for-every-torrent-status*
*Completed: 2026-04-19*
