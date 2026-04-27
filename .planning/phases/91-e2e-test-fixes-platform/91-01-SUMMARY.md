---
phase: 91-e2e-test-fixes-platform
plan: "01"
subsystem: e2e
tags: [e2e, playwright, refactor, api-fix]
dependency_graph:
  requires: []
  provides: [shared-helpers-ts, correct-playwright-apis]
  affects: [src/e2e/tests/autoqueue.page.ts, src/e2e/tests/dashboard.page.ts, src/e2e/tests/fixtures/seed-state.ts]
tech_stack:
  added: []
  patterns: [shared-utility-extraction, playwright-filter-hasText, innerText-over-innerHTML]
key_files:
  created:
    - src/e2e/tests/helpers.ts
  modified:
    - src/e2e/tests/autoqueue.page.ts
    - src/e2e/tests/dashboard.page.ts
    - src/e2e/tests/fixtures/seed-state.ts
decisions:
  - "helpers.ts lives under src/e2e/tests/ (excluded from Angular build) — no production bundle risk"
  - "escapeRegex signature unchanged during extraction — zero call-site churn beyond replacing this._escapeRegex"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
---

# Phase 91 Plan 01: E2E Page Object API Fixes Summary

**One-liner:** Fixed innerHTML→innerText and :has-text()→filter({hasText}) in AutoQueue page object, and extracted duplicated escapeRegex to a single shared helpers.ts.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create shared helpers.ts and deduplicate escapeRegex (E2EFIX-07) | e9e79f7 | helpers.ts (created), dashboard.page.ts, seed-state.ts |
| 2 | Fix innerHTML and :has-text() in AutoQueue page object (E2EFIX-01, E2EFIX-05) | 8287ed1 | autoqueue.page.ts |

## What Was Built

### Task 1 — Shared escapeRegex utility (E2EFIX-07)

Created `src/e2e/tests/helpers.ts` with a single exported `escapeRegex` function. Removed the private `_escapeRegex` method from `dashboard.page.ts` and the module-local `escapeRegex` function from `fixtures/seed-state.ts`. Both files now import from the shared module. The function signature is identical so all existing call sites work unchanged.

### Task 2 — AutoQueue page object API fixes (E2EFIX-01, E2EFIX-05)

- **E2EFIX-01:** `getPatterns()` changed from `elm.innerHTML()` to `elm.innerText()`. The old call returned raw HTML markup (e.g. entities and tags); `innerText()` returns the visible text content that assertions compare against.
- **E2EFIX-05:** `addPattern()` replaced `:has-text("${pattern}")` CSS pseudo-class with `.filter({ hasText: pattern })`. The pseudo-class is deprecated in Playwright and emits warnings; the `filter()` API is the supported replacement.

## Verification

All plan verification steps passed:

1. `cd src/e2e && npx tsc --noEmit` — exits 0 (no TypeScript errors)
2. `grep -r 'innerHTML()' src/e2e/tests/autoqueue.page.ts` — no matches
3. `grep -r ':has-text(' src/e2e/tests/autoqueue.page.ts` — no matches
4. `grep -r '_escapeRegex' src/e2e/tests/` — no matches
5. `grep -c 'function escapeRegex' src/e2e/tests/helpers.ts` — returns 1
6. `grep -c 'function escapeRegex' src/e2e/tests/fixtures/seed-state.ts` — returns 0

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. `helpers.ts` is under `src/e2e/tests/` which is a separate npm project excluded from the Angular production bundle. No new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- `src/e2e/tests/helpers.ts` — exists (created in this plan)
- `src/e2e/tests/autoqueue.page.ts` — modified, contains `elm.innerText()` and `.filter({ hasText: pattern })`
- `src/e2e/tests/dashboard.page.ts` — modified, imports `escapeRegex` from `./helpers`, no `_escapeRegex`
- `src/e2e/tests/fixtures/seed-state.ts` — modified, imports `escapeRegex` from `../helpers`, no local definition
- Commit e9e79f7 — exists (Task 1)
- Commit 8287ed1 — exists (Task 2)
