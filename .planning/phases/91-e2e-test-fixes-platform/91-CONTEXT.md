# Phase 91: E2E Test Fixes & Platform - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 7 specific E2E test quality defects (innerHTML vs innerText, beforeEach ordering, waitForTimeout removal, CSP fixture bypass, deprecated :has-text() selector, missing HTTP response checks, duplicated _escapeRegex helper) and 2 platform issues (CSP violation detection enforcement, arm64 Unicode sort failures).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User elected to skip discussion — all implementation decisions are at Claude's discretion. Requirements are fully specified in REQUIREMENTS.md (E2EFIX-01 through E2EFIX-07, PLAT-01, PLAT-02) with exact file locations and bug descriptions. No ambiguity in what needs fixing.

Key areas left to Claude:

- **D-01:** innerHTML→innerText fix for E2EFIX-01 — `autoqueue.page.ts:28` uses `elm.innerHTML()` for text content; switch to `elm.innerText()` to match other page objects (settings.page.ts already uses innerText)
- **D-02:** beforeEach ordering for E2EFIX-02 — `settings-error.spec.ts` calls `disableSonarr()` API before `navigateTo()`; determine correct order and whether navigation is needed before API setup calls
- **D-03:** waitForTimeout replacement for E2EFIX-03 — `dashboard.page.spec.ts:255` has `waitForTimeout(500)`; replace with Playwright auto-waiting or explicit wait condition
- **D-04:** CSP fixture bypass for E2EFIX-04 — `dashboard.page.spec.ts` beforeAll seed helpers may bypass CSP fixture context; determine how to ensure CSP enforcement covers seed operations
- **D-05:** :has-text() migration for E2EFIX-05 — `autoqueue.page.ts:35` uses deprecated `:has-text()` pseudo-class; replace with `locator.filter({ hasText })` pattern
- **D-06:** HTTP response checking for E2EFIX-06 — dashboard spec rate-limit config calls lack response status assertions; add appropriate checks
- **D-07:** _escapeRegex deduplication for E2EFIX-07 — currently private in `dashboard.page.ts:168`; decide whether to extract to App base class, standalone utility, or Playwright test helper
- **D-08:** CSP enforcement scope for PLAT-01 — CSP listener fixture already exists (`src/e2e/tests/fixtures/csp-listener.ts`) with `securitypolicyviolation` event handler and console listener; determine whether all specs should import it and how to handle beforeAll seed contexts
- **D-09:** arm64 Unicode sort for PLAT-02 — dashboard E2E specs fail on arm64 due to locale-dependent collation; choose between locale-aware assertions, platform-conditional expected values, or sort-agnostic test design

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — E2EFIX-01 through E2EFIX-07 and PLAT-01/PLAT-02 requirement definitions with file locations and bug descriptions

### Affected E2E Files
- `src/e2e/tests/autoqueue.page.ts` — E2EFIX-01 (innerHTML at line 28), E2EFIX-05 (:has-text at line 35)
- `src/e2e/tests/settings-error.spec.ts` — E2EFIX-02 (beforeEach ordering — API calls before navigateTo)
- `src/e2e/tests/dashboard.page.spec.ts` — E2EFIX-03 (waitForTimeout at line 255), E2EFIX-04 (beforeAll seed bypass), E2EFIX-06 (missing response checks), PLAT-02 (arm64 sort)
- `src/e2e/tests/dashboard.page.ts` — E2EFIX-07 (_escapeRegex at line 168)

### CSP Infrastructure
- `src/e2e/tests/fixtures/csp-listener.ts` — Existing CSP violation fixture (securitypolicyviolation event + console listener); PLAT-01 extends this

### Page Objects (reference for patterns)
- `src/e2e/tests/app.ts` — Base App class (innerText usage at lines 16, 20)
- `src/e2e/tests/settings.page.ts` — Settings page object (innerText usage at line 50)
- `src/e2e/tests/dashboard.page.ts` — Dashboard page object (hasText pattern at lines 55, 82)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **CSP listener fixture** (`fixtures/csp-listener.ts`): Full implementation exists — exposes `cspViolations` array, catches both `securitypolicyviolation` events and console CSP errors, fails test if violations detected (unless `allowViolations: true`). Most specs already import from this fixture.
- **App base class** (`app.ts`): Uses `innerText()` consistently — good pattern for E2EFIX-01 fix
- **dashboard.page.ts `_escapeRegex`**: Private method used in 2 locator calls — candidate for extraction to shared utility

### Established Patterns
- Page Object Model: all specs use page objects extending App base class
- CSP fixture re-export: specs import `{ test, expect }` from `./fixtures/csp-listener` instead of `@playwright/test`
- `locator.filter({ hasText })` pattern already used in dashboard.page.ts (lines 55, 82) — migration target for :has-text()
- Playwright auto-waiting via `waitFor({ state: 'visible' })` used extensively — model for waitForTimeout replacement
- `test.beforeAll` used for seed state setup in dashboard specs (lines 121, 375)

### Integration Points
- All fixes must pass `make run-tests-e2e` on both amd64 and arm64
- 37 existing E2E specs (7 spec files)
- E2E tests run against Docker compose stack (`http://myapp:8800`)
- Seed state helpers in `src/e2e/tests/fixtures/seed-state.ts`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for all fixes.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- **Migrate /server/config/set to POST-body** (score 0.9) — out of scope, explicitly deferred to future milestone (API-01)
- **Add CSP violation detection** (score 0.6) — already in scope as PLAT-01
- **Fix arm64 Unicode sort** (score 0.6) — already in scope as PLAT-02
- **Tighten Semgrep rules** (score 0.4) — belongs to Phase 96 (TOOL-01/TOOL-02)
- **Rate limiting** (score 0.3) — belongs to Phase 96 (RATE-01 through RATE-04)
- **webob/cgi upstream** (score 0.2) — blocked on upstream, out of scope

</deferred>

---

*Phase: 91-e2e-test-fixes-platform*
*Context gathered: 2026-04-27*
