---
phase: 91-e2e-test-fixes-platform
plan: "02"
subsystem: e2e-tests
tags: [e2e, playwright, test-quality, arm64, csp]
dependency_graph:
  requires: []
  provides: [E2EFIX-02, E2EFIX-03, E2EFIX-04, E2EFIX-06, PLAT-01, PLAT-02]
  affects: [src/e2e/tests/settings-error.spec.ts, src/e2e/tests/dashboard.page.spec.ts, src/e2e/playwright.config.ts]
tech_stack:
  added: []
  patterns: [navigate-before-api, playwright-auto-wait, response-ok-assertion, csp-bypass-documentation, icu-locale-config]
key_files:
  created: []
  modified:
    - src/e2e/tests/settings-error.spec.ts
    - src/e2e/tests/dashboard.page.spec.ts
    - src/e2e/playwright.config.ts
decisions:
  - "Use Playwright auto-wait on Queue button assertion instead of waitForTimeout(500) — eliminates fixed sleep, equivalent synchronization"
  - "Throw on non-OK rate_limit config responses — silent failures now abort the test with descriptive error messages"
  - "Document CSP bypass in beforeAll comments rather than changing fixture — seed operations are HTTP+DOM only, no new script sources"
  - "Set locale: 'en-US' at config level not per-project — applies globally to all Chromium runs, prevents arm64/amd64 ICU divergence"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-27"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase 91 Plan 02: E2E Spec Quality Fixes and arm64 Platform Config Summary

Fix 4 spec-level defects (beforeEach ordering, waitForTimeout removal, missing response assertions, CSP bypass documentation) and add arm64-safe locale config to playwright.config.ts.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix beforeEach ordering in settings-error.spec.ts (E2EFIX-02) | a22f852 | src/e2e/tests/settings-error.spec.ts |
| 2 | Fix waitForTimeout, response assertions, CSP comments in dashboard spec (E2EFIX-03, E2EFIX-04, E2EFIX-06, PLAT-01) | 873322d | src/e2e/tests/dashboard.page.spec.ts |
| 3 | Add locale to playwright.config.ts for arm64 Unicode sort (PLAT-02) | ff36b17 | src/e2e/playwright.config.ts |

## Changes Made

### Task 1 — settings-error.spec.ts beforeEach ordering (E2EFIX-02)

Added `await settingsPage.navigateTo()` between `new SettingsPage(page)` and `await settingsPage.disableSonarr()` in the `test.beforeEach` block. The API call `disableSonarr()` issues an HTTP request to the server; without a prior page navigation there is no authenticated session context established. The second `navigateTo()` in the test body (line 22) remains — that is an intentional re-navigate after enabling Sonarr and setting config values.

### Task 2 — dashboard.page.spec.ts four-part fix

**E2EFIX-03:** Removed `await page.waitForTimeout(500)` after the stop command. Replaced the old comment with an explanation that the Queue button `toBeEnabled()` assertion below already uses Playwright's built-in auto-wait (polls until actionable or timeout).

**E2EFIX-06:** Wrapped both `rate_limit` config GET calls with response variables and `if (!resp.ok()) throw` guards:
- `const throttleResp = await page.request.get('/server/config/set/lftp/rate_limit/100')` + error throw
- `const restoreResp = await page.request.get('/server/config/set/lftp/rate_limit/0')` + error throw in finally block

**E2EFIX-04 / PLAT-01:** Added the same 6-line CSP bypass documentation comment to both `test.beforeAll` blocks (UAT-01 and UAT-02), immediately after `test.setTimeout(120_000)`. Explains that `browser.newContext()` pages are not managed by the csp-listener fixture's `exposeFunction + addInitScript` page override; seed operations are HTTP requests and badge DOM polling only — no new script sources.

### Task 3 — playwright.config.ts locale (PLAT-02)

Added `locale: 'en-US'` to the `use` block between `baseURL` and `trace`. Forces Chromium to use en-US ICU collation regardless of host system locale, preventing localeCompare-based file ordering divergence between amd64 and arm64 Chromium builds.

## Verification Results

| Check | Result |
|-------|--------|
| `npx tsc --noEmit` exits 0 | PASS |
| No `waitForTimeout` in spec files | PASS |
| `grep -c 'CSP monitoring intentionally absent' dashboard.page.spec.ts` = 2 | PASS |
| `throttleResp.ok()` present in dashboard spec | PASS |
| `restoreResp.ok()` present in dashboard spec | PASS |
| `locale: 'en-US'` in playwright.config.ts | PASS |
| `navigateTo` count in settings-error.spec.ts >= 2 | PASS (2) |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. All changes are test-infrastructure only. The rate_limit config calls were already present (no new network surface introduced). The locale setting and CSP comments are documentation/config changes with no production impact.

## Self-Check: PASSED

All files verified present. All commits verified in git log.
