---
phase: 73
slug: dashboard-filter-for-every-torrent-status
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-19
---

# Phase 73 — Validation Strategy

> Per-phase validation contract. Reconstructed retroactively from artifacts (State B); no pre-execution Wave-0 stubs needed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Angular unit framework** | Karma + Jasmine |
| **Angular unit config** | `src/angular/karma.conf.js`, `src/angular/angular.json` (`test` builder) |
| **Angular quick run** | `cd src/angular && npx tsc --noEmit -p tsconfig.json` (compile-time checks, ~5s) |
| **Angular full suite** | `make run-tests-angular` (dockerized Karma/Jasmine — 566 specs) |
| **E2E framework** | Playwright |
| **E2E config** | `src/e2e/playwright.config.ts` |
| **E2E compile check** | `cd src/e2e && npx tsc --noEmit` (~3s) |
| **E2E full suite** | `make run-tests-e2e` (requires docker-compose: myapp + chrome + remote SSH) |
| **Spec files touched** | `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` (1096 lines, 84 specs), `src/e2e/tests/dashboard.page.spec.ts` (111 lines, 11 tests), `src/e2e/tests/dashboard.page.ts` (94 lines, page object) |

---

## Sampling Rate

- **After every task commit:** `cd src/angular && npx tsc --noEmit` (or `cd src/e2e && npx tsc --noEmit` for e2e-touching tasks)
- **After every plan wave:** `make run-tests-angular` (unit) and `make run-tests-e2e` (e2e, infra permitting)
- **Before `/gsd-verify-work`:** Full Angular suite green; e2e suite green if infra available
- **Max feedback latency:** ~5s (tsc), ~60–120s (dockerized unit), ~3–5min (e2e stack)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command / Test | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|--------------------------|-------------|--------|
| 73-01-01 | 01 | 1 | D-04, D-07 | T-73-01-01 | Segment type union widened to accept `'done'` at 3 annotation sites | compile | `cd src/angular && npx tsc --noEmit -p tsconfig.json` exits 0 | ✅ | ✅ green |
| 73-01-02 | 01 | 1 | D-05, D-06 | T-73-01-02 | `segmentedFiles$` returns DEFAULT-bearing Active set and DOWNLOADED∪EXTRACTED Done set | unit | spec `it("should filter to DOWNLOADED ∪ EXTRACTED when 'done' segment selected with no sub")` (line 504); `it("should include DEFAULT (Pending) in 'active' segment results")` (line 528) | ✅ | ✅ green |
| 73-02-01 | 02 | 1 | D-03, D-04, D-14, D-15 | T-73-02-01, T-73-02-02 | Done parent + expand block inserted between Active and Errors using existing SCSS classes only | build + unit | `ng build --configuration=development` exits 0; spec `it("should render 4 parent segment filter buttons in order All, Active, Done, Errors")` (line 208) | ✅ | ✅ green |
| 73-02-02 | 02 | 1 | D-05, D-15 | T-73-02-01 | Pending sub-button added as first sub under Active expand block | unit | spec `it("should filter to DEFAULT only when Pending sub-status selected under Active")` (line 552) | ✅ | ✅ green |
| 73-03-01 | 03 | 2 | D-09, D-11 | T-73-03-01, T-73-03-02 | `ngOnInit` hydrates `activeSegment`/`activeSubStatus` from validated URL params | unit | URL persistence describe `hydrates activeSegment='done' from ?segment=done` (line 973); `falls back silently to 'all' when ?segment value is invalid (D-11)` (line 991); `drops sub silently when sub doesn't belong to the named segment (D-11)` (line 998) | ✅ | ✅ green |
| 73-03-02 | 03 | 2 | D-09, D-10 | T-73-03-03 | `_writeFilterToUrl` calls `Router.navigate([], {relativeTo, queryParamsHandling:"merge", replaceUrl:true})` | unit | `writes ?segment=done&sub=null on onSegmentChange('done')` (line 1051); `writes ?segment=done&sub=downloaded on subsequent onSubStatusChange(DOWNLOADED)` (line 1062); `clears both params on onSegmentChange('all')` (line 1072) | ✅ | ✅ green |
| 73-03-03 | 03 | 2 | D-11 | T-73-03-01, T-73-03-02 | Page and search changes do NOT persist to URL | unit | `does NOT call router.navigate when goToPage is invoked` (line 1083); `does NOT call router.navigate when onSearchInput is invoked` (line 1089) | ✅ | ✅ green |
| 73-03-04 | 03 | 2 | D-11 | T-73-03-01 | URL self-sanitizes when hydrated from invalid params | unit | `sanitizes URL to default when ?segment is invalid` (line 1013); `sanitizes URL by dropping sub when sub is invalid for the segment` (line 1020); `sanitizes URL by dropping orphan sub when no segment is given` (line 1027) | ✅ | ✅ green |
| 73-04-01 | 04 | 2 | D-04, D-09 | T-73-04-02 | TestBed provides Router + ActivatedRoute mocks; TEST_TEMPLATE updated; mock map cleared between tests | unit | providers at spec:166-176 inject Router/ActivatedRoute; `beforeEach` clears `mockQueryParamMap` (spec:144-146) | ✅ | ✅ green |
| 73-04-02 | 04 | 2 | D-01, D-05, D-06, D-12, D-13 | — | 17 new unit specs cover Done branch, Pending sub, URL round-trip, D-12 carry-forward, D-13 page-reset | unit | filter-logic specs (lines 504-627); URL-persistence describe (lines 956-1091); `clears file selection when 'done' segment selected (D-12 carry-forward)` (line 620); `reset page to 1 on sub-status change` (line 677) | ✅ | ✅ green |
| 73-05-01 | 05 | 3 | D-01, D-03, D-04 | T-73-05-01 | `getSegmentButton` + `getSubButton` locator methods scoped to `.segment-filters` | compile | `cd src/e2e && npx tsc --noEmit` exits 0; locator shape verified by grep (`this.page.locator('.segment-filters')` present at dashboard.page.ts:73,77) | ✅ | ✅ green |
| 73-05-02 | 05 | 3 | D-01, D-09 | T-73-05-02 | 4 Playwright tests: Done expand, Pending reveal, URL round-trip, sanitize on invalid | e2e | `should expand Done segment to reveal Downloaded and Extracted subs` (spec:77); `should reveal Pending sub under Active` (spec:87); `should persist Done filter via URL query param (D-09)` (spec:95); `should silently fall back to All and sanitize URL when ?segment= is invalid (D-11)` (spec:101) | ✅ | ✅ green (structural) / ⚠️ runtime CI-gated |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky / CI-gated*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 stubs created because:
- Karma/Jasmine already configured for the Angular app (`angular.json`, `karma.conf.js`)
- Playwright already configured for e2e (`src/e2e/playwright.config.ts`)
- TestBed scaffolding for `TransferTableComponent` already existed from prior phases — Plan 04 extended it with Router/ActivatedRoute mocks rather than bootstrapping fresh

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Playwright dashboard suite runtime execution | D-01, D-03, D-04, D-09, D-11 | The Playwright suite requires a docker-compose stack (Angular app + Chromium + remote SSH) that cannot be started from inside a Claude session. Structural verification (tsc + locator-shape grep + template diff) confirms wiring is correct; the final runtime confirmation is CI's job. | `make run-tests-e2e` with docker-compose available. Expect 11/11 dashboard tests green, including the 4 new tests at `dashboard.page.spec.ts:77,87,95,101`. Accepted by HUMAN-UAT (commit `6e1fea1`, runtime deferred to CI). |

---

## Requirement Coverage Summary

| D-Item | Description | Automated Coverage | Evidence |
|--------|-------------|---------------------|----------|
| D-01 | 3 new filterable statuses (DEFAULT, DOWNLOADED, EXTRACTED) | ✅ | unit specs 528, 552, 575, 598; e2e 77, 87 |
| D-03 | Labels Pending / Downloaded / Extracted | ✅ | HTML grep + e2e `getByText` (77, 87) |
| D-04 | Done sibling of Active/Errors; order All/Active/Done/Errors | ✅ | unit 208; e2e getSegmentButton union |
| D-05 | Pending under Active, left-most sub | ✅ | unit 528, 552; e2e 87 |
| D-06 | Done parent = DOWNLOADED ∪ EXTRACTED | ✅ | unit 504 |
| D-07 | Preserve `activeSegment` + `activeSubStatus` state shape | ✅ | tsc compile-time; unit 193, 381 |
| D-08 | Done collapse-on-second-click identical to Active/Errors | ✅ | unit 667 |
| D-09 | URL persistence (hydrate on init, write on change) | ✅ | unit 956-1091 (URL describe); e2e 95 |
| D-10 | `Router.navigate` with `queryParamsHandling: "merge"` | ✅ | unit 1051, 1062 (assert merge handling) |
| D-11 | Silent fallback on invalid URL params; page/search not persisted | ✅ | unit 991, 998, 1005, 1013-1039, 1083, 1089; e2e 101 |
| D-12 | Clear file selection on filter change (Phase 72 carry-forward) | ✅ | unit 620, 686-727 |
| D-13 | Reset page to 1 on filter change | ✅ | unit 677; structural grep of `this.currentPage = 1` in onSegmentChange / onSubStatusChange |
| D-14 | Mobile: no new SCSS media queries | ✅ | structural grep (no new classes introduced) |
| D-15 | Reuse `.btn-segment`, `.btn-sub`, `.accent-dot`, `.segment-divider` verbatim | ✅ | Plan 02 SUMMARY class-name grep verified |

**14/14 D-items have automated verification.** No orphans. D-02 deferred by CONTEXT (WAITING_FOR_IMPORT, not in phase scope).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands or structural coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] No Wave 0 gaps (existing infrastructure sufficient)
- [x] No watch-mode flags in any command
- [x] Feedback latency < 5s for tsc, < 2min for full unit suite
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-04-19
