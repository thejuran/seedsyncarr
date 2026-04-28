# Phase 95: Test Coverage -- E2E - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Playwright E2E specs for the Logs page (COVER-02) and Settings form fields (COVER-03) — two pages that currently have minimal or no E2E coverage. Prove they render correctly and function in the live Docker compose stack.

</domain>

<decisions>
## Implementation Decisions

### Logs Page Test Scope (COVER-02)
- **D-01:** Use **structural smoke** approach — verify page load, all toolbar elements present (5 level filter buttons, search input, auto-scroll/clear/export buttons), at least 1 log row renders, and status bar text visible. Consistent with the shallow structural probe pattern used by `about.page.spec.ts` and `settings.page.spec.ts`.
- **D-02:** Auto-scroll verified as DOM state only (button has `action-btn--active` class on load). Do NOT test scroll position mechanics — fragile in CI against viewport size variations.
- **D-03:** Do NOT test level filter clicks, search debounce, clear, or export download at E2E level. These are fully covered by Angular unit tests. E2E proves the component mounts in the real stack and receives SSE data.

### SSE Log Delivery (COVER-02)
- **D-04:** Use **API-triggered logs** — dispatch a command (e.g., stop on an already-stopped file, or a config change) that produces a predictable INFO-level log entry at `controller.py:1075`. This tests the real SSE pipeline: `MultiprocessingLogger` → root logger → `LogStreamHandler` → SSE → `LogService.onEvent` → `.log-row` DOM nodes.
- **D-05:** Organic logs from the running harness are acceptable as a fallback for the page-load smoke assertion (status bar log count > 0), but should not be the primary mechanism for asserting specific log line rendering.
- **D-06:** Do NOT use `page.route()` interception (no precedent in codebase, skips real pipeline) or test-only injection endpoints (ships test code into production).

### Settings Test Scope (COVER-03)
- **D-07:** Use **representative sample** — cover 1 field per conceptual group that exercises a distinct input type: text field (e.g., Server Address), checkbox toggle (e.g., SSH key auth), interval field (e.g., Discovery polling). ~6-8 tests total.
- **D-08:** Skip Radarr card (structural mirror of Sonarr, which already has `settings-error.spec.ts`). Skip API & Security token reveal/copy (`navigator.clipboard` unreliable in headless Chromium). Skip AutoQueue patterns (already covered by `autoqueue.page.spec.ts`).
- **D-09:** Assert the floating save bar's "Changes Saved" confirmation as the E2E-verifiable proof that the `onSetConfig → /server/config/set → config update → floating bar` round-trip works.

### Config Persistence Verification (COVER-03)
- **D-10:** Use **hybrid approach** — one UI-to-UI round-trip test (fill a text field via UI → click "Save Settings" → wait for SSE reconnect → reload page → verify value retained) proves the full user flow including disk persistence via restart.
- **D-11:** Remaining fields use the cheaper **API-set → reload → verify UI** pattern (matching the existing `settings.page.ts` `page.request.get('/server/config/set/...')` convention from `settings-error.spec.ts`).
- **D-12:** Each test's `afterEach` must restore original config values to prevent cross-test pollution. Follow the pattern in `settings-error.spec.ts` which uses `disableSonarr().catch(() => {})` for cleanup.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — COVER-02 and COVER-03 requirement definitions with success criteria

### Logs Page (COVER-02)
- `src/angular/src/app/pages/logs/logs-page.component.ts` — LogsPageComponent (290 lines, SSE subscription, level filters, search, auto-scroll, clear, export)
- `src/angular/src/app/pages/logs/logs-page.component.html` — Template with toolbar, terminal viewport, status bar
- `src/angular/src/app/services/logs/log.service.ts` — LogService (SSE consumer, emits LogRecord stream)
- `src/angular/src/app/services/logs/log-record.ts` — LogRecord model with Level enum

### Settings Page (COVER-03)
- `src/angular/src/app/pages/settings/settings-page.component.ts` — SettingsPageComponent (config binding, onSetConfig, save/restart)
- `src/angular/src/app/pages/settings/settings-page.component.html` — Template with 8 cards, form fields, floating save bar
- `src/e2e/tests/settings.page.ts` — Existing page object (Sonarr config methods — extend, don't replace)
- `src/e2e/tests/settings.page.spec.ts` — Existing spec (1 test — nav link active)
- `src/e2e/tests/settings-error.spec.ts` — Existing Sonarr error spec (API-set pattern reference)

### E2E Infrastructure & Patterns
- `src/e2e/tests/app.ts` — Base App class (page object base, getNavLinks, getActiveNavLink)
- `src/e2e/tests/about.page.spec.ts` — Reference for shallow structural probe pattern
- `src/e2e/tests/fixtures/csp-listener.ts` — CSP violation fixture (all new specs must import `{ test, expect }` from here)
- `src/e2e/tests/helpers.ts` — Shared `escapeRegex` utility
- `src/e2e/urls.ts` — URL paths (Paths.LOGS, Paths.SETTINGS)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `App` base class (`app.ts`): `getActiveNavLink()`, `getNavLinks()` — reuse for Logs nav link assertion
- `SettingsPage` page object (`settings.page.ts`): Already has Sonarr config methods — extend with new methods for text field input, checkbox toggle, save button click, and save confirmation assertion
- CSP listener fixture: All specs must use `import { test, expect } from './fixtures/csp-listener'`
- `escapeRegex` helper (`helpers.ts`): Available if regex patterns needed in locators

### Established Patterns
- Page Object Model: all specs use page objects extending `App` base class
- Shallow structural probes for non-Dashboard pages: `about.page.spec.ts` (version text), `settings.page.spec.ts` (nav active)
- API-set config pattern: `page.request.get('/server/config/set/section/key/value')` for test setup/teardown
- `afterEach` cleanup with `.catch(() => {})` for teardown resilience
- `beforeEach` navigates to page before each test

### Integration Points
- New files: `logs.page.ts` (page object), `logs.page.spec.ts` (spec file)
- Extended: `settings.page.ts` (add methods for field input, save, confirmation)
- New file: `settings-fields.spec.ts` (or extend `settings.page.spec.ts` — planner decides naming)
- All specs run against Docker compose stack at `http://myapp:8800`
- Must pass `make run-tests-e2e` on both amd64 and arm64

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following the established Page Object Model and structural probe patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- **Migrate /server/config/set to POST-body** (score 0.6) — out of scope, explicitly deferred to future milestone (API-01)
- **Add CSP violation detection** (score 0.6) — already complete (PLAT-01, Phase 91)
- **Fix arm64 Unicode sort** (score 0.6) — already complete (PLAT-02, Phase 91)
- **webob/cgi upstream** (score 0.2) — blocked on upstream, out of scope

</deferred>

---

*Phase: 95-Test Coverage -- E2E*
*Context gathered: 2026-04-28*
