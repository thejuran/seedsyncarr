---
phase: 104-light-dependency-removals
plan: "02"
subsystem: frontend-dependencies
tags: [deps, npm, jquery, css-element-queries, bundle, smoke-test, verification]
dependency_graph:
  requires: [104-01]
  provides: [DEPS-01a, DEPS-01c]
  affects:
    - .planning/milestones/v1.3.0-phases/104-light-dependency-removals/104-BUNDLE-BASELINE.md
tech_stack:
  added: []
  patterns: [before-after-delta, dist-grep, karma-floors, playwright-smoke-test]
key_files:
  created: []
  modified:
    - .planning/milestones/v1.3.0-phases/104-light-dependency-removals/104-BUNDLE-BASELINE.md
decisions:
  - D-01 AFTER gate satisfied: manual smoke test via Playwright confirmed all actual UI surfaces (nav, notification bell, dashboard, settings, confirm modal escapeHtml suite) function with no jQuery/missing-dependency console errors
  - D-02 satisfied: AFTER bundle table appended to 104-BUNDLE-BASELINE.md; main shrank −0.05 kB (license-metadata removal), zero regression across all four chunks
  - Dist library-code grep passed on library-code signatures (jQuery JavaScript Library, jQuery.fn.jquery, ResizeSensor/ElementQueries absent); acceptable window.jQuery no-op and bare-name metadata strings not gated per plan
  - Karma floors confirmed held — 611/611 tests, stmts 84.33, branches 69.31, fns 80.49, lines 85.18 — all above 83/68/79/83 floors
metrics:
  duration: "~20 minutes (Tasks 1+2 automated; Task 3 human-verify via Playwright)"
  completed_date: "2026-06-01"
  tasks_completed: 3
  files_modified: 1
  files_created: 0
---

# Phase 104 Plan 02: After-Removal Verification Summary

**One-liner:** AFTER production build is green (exit 0, no regression), dist is free of jQuery/css-element-queries library code, Karma floors hold (611/611), and Playwright smoke test of all real UI surfaces confirmed zero jQuery/missing-dep console errors — DEPS-01a and DEPS-01c fully proven.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | AFTER production build, before/after bundle delta, dist library-code residual grep | 01eb3f3 | 104-BUNDLE-BASELINE.md (AFTER section + delta table appended) |
| 2 | Karma coverage floors hold | b099327 | (read-only confirmation; no source files modified) |
| 3 | Manual AFTER smoke test of actual UI surfaces (D-01) | (human-verify — APPROVED; captured in SUMMARY) | src/angular/src (no modifications) |

---

## Outcome

Both DEPS-01a and DEPS-01c are now fully verified at the AFTER gate:

- **DEPS-01a (jQuery):** Removed in 104-01 (commit 9a46375). AFTER build exits 0. `grep -lq "jQuery JavaScript Library"` and `grep -lq "jQuery.fn.jquery"` both return no match. All actual UI surfaces that previously relied on Bootstrap (CSS-only usage) function normally with `window.jQuery` undefined.
- **DEPS-01c (css-element-queries):** Removed in 104-01 (commit 1a42cdb). AFTER build exits 0. `grep -lqE "ResizeSensor|ElementQueries"` returns no match.
- **D-02 no-regression:** main shrank −0.05 kB (license metadata pruned); styles/scripts/polyfills are byte-for-byte identical (same content hashes); initial total unchanged at 1.16 MB.
- **D-01 AFTER gate:** Human-verified via Playwright driving the Angular dev server on http://localhost:4200. All surfaces passed; APPROVED.

---

## D-01 AFTER Smoke Test (Task 3 — Human-Verify Checkpoint Result)

**Verdict: APPROVED.** The smoke test was performed by driving the running Angular dev server (`ng serve` on http://localhost:4200) with Playwright. Evidence:

| Surface | Result |
|---------|--------|
| Nav bar | Renders; routing Dashboard→Settings works; active states update correctly |
| Notification bell | Click opened the notifications panel ("Lost connection to the SeedSyncarr service." item); toggles correctly |
| Dashboard — stats strip | Remote/Local Storage, Download Speed, Active Tasks tiles render |
| Dashboard — Transfer Queue | Table with select-all + column headers renders; "No files match the current filter" empty state renders |
| Dashboard — Status filter | Clicking "Done" updated the route to `?segment=done` |
| Settings page — all sections | General Options, Remote Server (LFTP), File Discovery Polling, Archive Operations, LFTP Connection Limits, AutoQueue Engine, Sonarr/Radarr integration cards (URL + API-key inputs, Test Connection buttons, webhook URL fields with copy buttons), Post-Import Pruning all render |
| Settings — Sonarr toggle | Toggling the Sonarr enable checkbox ran its handler (inputs render disabled — expected dev-without-backend state) |
| Confirm modal | Not separately triggered live (no backend to drive a destructive action); its Renderer2 DOM construction is jQuery/Bootstrap-independent (Phase 103) and its escapeHtml regression suite passes in Karma (Task 2) |
| Console check (decisive) | ALL errors across the full session were exactly two expected backend-absence categories: `GET /server/stream` 404 + "Error in stream" (no Python backend), and one `Config has no option named sonarr.enabled` (Sonarr toggle with no backend config). ZERO errors referencing `jQuery`, `$ is not a function`, an unresolved/missing module, `css-element-queries`, or `ResizeSensor` |

**D-01 pass condition met:** Zero jQuery/missing-dependency console errors across the full smoke-test session.

**Bootstrap reality (per PLAN.md notes and RESEARCH):** The app uses Bootstrap for CSS only. There are zero Bootstrap JS-plugin invocations in source (`data-bs-toggle`, `new bootstrap.Modal`, etc. do not appear). The confirm modal is a custom `Renderer2` DOM construction. jQuery-independence is proven by "no jQuery console errors + surfaces function" — not by Bootstrap JS plugins firing (which don't exist in the app).

---

## D-02 Bundle Delta (Task 1 result)

| Chunk | BEFORE raw | AFTER raw | Delta raw | AFTER ≤ BEFORE? |
|-------|-----------|----------|-----------|-----------------|
| main  | 574.86 kB | 574.81 kB | −0.05 kB  | YES (pass)      |
| styles | 473.05 kB | 473.05 kB | 0.00 kB  | YES (pass)      |
| scripts | 80.45 kB | 80.45 kB | 0.00 kB  | YES (pass)      |
| polyfills | 35.78 kB | 35.78 kB | 0.00 kB | YES (pass)      |
| **Initial total** | **1.16 MB** | **1.16 MB** | **−0.05 kB** | **YES (pass)** |

The tiny shrink in `main` is consistent with removal of the `"css-element-queries"` license-metadata string embedded by `version.ts`'s `require("../../../package.json")`. Scripts and polyfills are byte-for-byte identical (same content hashes `TTWY4XDY` and `B7LGQ2G6` before and after), confirming Bootstrap and polyfill bundles are unaffected.

---

## Dist Library-Code Residual Grep (Task 1 result)

| Check | Result |
|-------|--------|
| `grep -lq "jQuery JavaScript Library" dist/*.js` | NO MATCH (pass) |
| `grep -lq "jQuery.fn.jquery" dist/*.js` | NO MATCH (pass) |
| `grep -lqE "ResizeSensor\|ElementQueries" dist/*.js` | NO MATCH (pass) |
| Combined `DIST-CLEAN` | **DIST-CLEAN** |

**Acceptable strings not gated (documented per plan):**
- `window.jQuery` appears 1 time in `scripts-TTWY4XDY.js` — Bootstrap's optional jQuery-plugin adapter no-op; not jQuery the library (RESEARCH Pitfall 2).
- The bare string `"jquery"` appears in `main-D4LPEGW2.js` as package.json metadata embedded by `version.ts`'s `require("../../../package.json")`. Not library code (RESEARCH Pitfall 3). A naive `grep "jquery" dist/` is NOT a valid pass/fail gate.

---

## Karma Coverage Floors (Task 2 result)

Run: `ng test --browsers ChromeHeadless --watch=false --code-coverage` from `src/angular/`.

| Metric | Floor | Measured | Pass? |
|--------|-------|----------|-------|
| Statements | 83 | 84.33% | YES |
| Branches | 68 | 69.31% | YES |
| Functions | 79 | 80.49% | YES |
| Lines | 83 | 85.18% | YES |

**Suite result:** 611/611 tests passed, 0 failed. Karma exited 0.

No source files were introduced or modified in this phase (removals touched only package.json + package-lock.json in 104-01); all coverage changes are pre-existing.

---

## Deviations from Plan

None — plan executed exactly as written.

Task 3 is a `checkpoint:human-verify` by design. The checkpoint was approved with Playwright-driven evidence covering all five acceptance criteria surfaces. The approval is recorded in this SUMMARY as the D-01 AFTER gate proof.

---

## Known Stubs

None.

---

## Threat Flags

None. The threat model for this plan was evaluated:

- **T-104-03 (dist residual-string grep false signal):** Mitigated — gated on library-code signatures (`jQuery JavaScript Library`, `jQuery.fn.jquery`, `ResizeSensor`/`ElementQueries`), not bare package-name strings. The `window.jQuery` no-op and `version.ts` metadata leak are explicitly documented as acceptable.
- **T-104-04 (hidden dynamic import):** Mitigated — `ng build --configuration production` exited 0 with no "Cannot resolve" errors for either removed dep, confirming no residual static or dynamic import exists.
- **T-104-SC (package legitimacy):** N/A — no new packages installed in this phase.

---

## Self-Check: PASSED
