# Phase 95: Test Coverage -- E2E - Research

**Researched:** 2026-04-28
**Domain:** Playwright E2E testing — Angular app, Page Object Model, SSE-backed pages
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Logs Page Test Scope (COVER-02)**
- D-01: Use structural smoke approach — verify page load, all toolbar elements present (5 level filter buttons, search input, auto-scroll/clear/export buttons), at least 1 log row renders, and status bar text visible. Consistent with the shallow structural probe pattern used by `about.page.spec.ts` and `settings.page.spec.ts`.
- D-02: Auto-scroll verified as DOM state only (button has `action-btn--active` class on load). Do NOT test scroll position mechanics — fragile in CI against viewport size variations.
- D-03: Do NOT test level filter clicks, search debounce, clear, or export download at E2E level. These are fully covered by Angular unit tests. E2E proves the component mounts in the real stack and receives SSE data.

**SSE Log Delivery (COVER-02)**
- D-04: Use API-triggered logs — dispatch a command (e.g., stop on an already-stopped file, or a config change) that produces a predictable INFO-level log entry. This tests the real SSE pipeline.
- D-05: Organic logs from the running harness are acceptable as a fallback for the page-load smoke assertion (status bar log count > 0), but should not be the primary mechanism for asserting specific log line rendering.
- D-06: Do NOT use `page.route()` interception or test-only injection endpoints.

**Settings Test Scope (COVER-03)**
- D-07: Use representative sample — cover 1 field per conceptual group exercising a distinct input type: text field (Server Address), checkbox toggle (SSH key auth), interval field (Discovery polling). ~6-8 tests total.
- D-08: Skip Radarr card. Skip API & Security token reveal/copy. Skip AutoQueue patterns (already covered by `autoqueue.page.spec.ts`).
- D-09: Assert the floating save bar's "Changes Saved" confirmation as the E2E-verifiable proof that the `onSetConfig → /server/config/set → config update → floating bar` round-trip works.

**Config Persistence Verification (COVER-03)**
- D-10: Use hybrid approach — one UI-to-UI round-trip test (fill via UI → click "Save Settings" → wait for SSE reconnect → reload page → verify value retained).
- D-11: Remaining fields use the cheaper API-set → reload → verify UI pattern (matching `settings.page.ts` `page.request.get('/server/config/set/...')` convention).
- D-12: Each test's `afterEach` must restore original config values to prevent cross-test pollution. Follow the pattern in `settings-error.spec.ts` which uses `disableSonarr().catch(() => {})` for cleanup.

### Claude's Discretion

No discretion areas specified — open to standard approaches following the established Page Object Model and structural probe patterns.

### Deferred Ideas (OUT OF SCOPE)

- Migrate /server/config/set to POST-body (API-01)
- Add CSP violation detection (already complete, PLAT-01, Phase 91)
- Fix arm64 Unicode sort (already complete, PLAT-02, Phase 91)
- webob/cgi upstream (blocked on upstream)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COVER-02 | Add Logs page E2E coverage — page object + specs for load, render, auto-scroll | Logs page DOM structure fully mapped; SSE trigger strategy via config change API identified; auto-scroll via `action-btn--active` CSS class verified in template |
| COVER-03 | Add Settings form fields E2E coverage — remote host, encryption toggle, save/persist | OptionComponent 1s debounce documented; floating save bar "Changes Saved" trigger path confirmed; API-set pattern from `settings.page.ts` confirmed; config section/key names verified in `options-list.ts` |
</phase_requirements>

---

## Summary

Phase 95 adds Playwright E2E specs for two pages currently lacking coverage: the Logs page (COVER-02) and the Settings form fields (COVER-03). Both pages are live Angular components consuming real backend SSE data when run against the Docker compose stack.

The Logs page component (`LogsPageComponent`) receives log records via `LogService`, which subscribes to SSE events named `"log-record"`. The component accumulates records in a scan accumulator with debounce(0), renders them as `.log-row` elements inside `.terminal-viewport`, and shows connection state and a log count in a `.status-bar`. Auto-scroll is tracked as `autoScroll: boolean` which maps to the CSS class `action-btn--active` on the toolbar button — this is a reliable DOM-state assertion that avoids fragile scroll-position checks.

The Settings page (`SettingsPageComponent`) binds to `ConfigService.config` (an observable) and calls `onSetConfig(section, key, value)` on any field change. `onSetConfig` calls `/server/config/set/<section>/<key>/<value>` immediately, and on success calls `onSaveComplete()` which sets `saveConfirmed = true` for 2500ms — rendering "Changes Saved" in the floating save bar. Critically, `OptionComponent` has a **1000ms debounce** before emitting `changeEvent`, meaning tests that `fill()` a text input must wait for this debounce to fire before expecting `saveConfirmed` to appear. The "Save Settings" button triggers `onCommandRestart()` (a server restart), not the initial config persistence — config is already written when `onSetConfig` succeeds.

**Primary recommendation:** Create `logs.page.ts` + `logs.page.spec.ts` for COVER-02, and extend `settings.page.ts` + create `settings-fields.spec.ts` for COVER-03. All files follow the established Page Object Model with CSP fixture imports and `afterEach` cleanup.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Logs page structural smoke | Browser/Client | — | DOM assertions against rendered Angular component |
| SSE log delivery proof | API/Backend + Browser/Client | — | Real pipeline from backend → SSE → Angular service → DOM |
| Auto-scroll DOM state | Browser/Client | — | CSS class on button; no scroll position measurement |
| Settings field value rendering | Browser/Client | API/Backend | Angular binds config observable to input values loaded from `/server/config/get` |
| Config persistence round-trip | API/Backend | Browser/Client | `onSetConfig` → `/server/config/set` → disk write; UI reload proves disk read |
| Floating save bar confirmation | Browser/Client | — | `saveConfirmed` flag set in Angular after API returns 200 |
| Test cleanup/restore | API/Backend | — | `page.request.get('/server/config/set/...')` API calls in `afterEach` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@playwright/test` | `^1.48.0` (locked in package.json; latest published: 1.59.1) | E2E browser automation + assertions | Project's chosen E2E framework; all existing specs use it |
| TypeScript | `^5.3.0` | Type-safe test code | Project's E2E language |

[VERIFIED: npm registry — `npm view @playwright/test version` returned 1.59.1]

### No New Dependencies

This phase adds test files only. No new packages are required — the existing `src/e2e/package.json` already declares all needed dependencies.

---

## Architecture Patterns

### Page Object Model

All E2E specs in this project follow the POM pattern:

```
src/e2e/tests/
├── app.ts                     # Base App class
├── logs.page.ts               # NEW — LogsPage extends App
├── logs.page.spec.ts          # NEW — COVER-02 specs
├── settings.page.ts           # EXTEND — add field/save/confirm methods
├── settings-fields.spec.ts    # NEW — COVER-03 specs
└── fixtures/
    └── csp-listener.ts        # import { test, expect } from here — REQUIRED
```

### Page Object Base Class

```typescript
// Source: src/e2e/tests/app.ts [VERIFIED: read directly]
export class App {
    constructor(protected page: Page) {}
    async navigateTo() { await this.page.goto('/'); }
    async getNavLinks(): Promise<string[]> { ... }
    async getActiveNavLink(): Promise<string> { ... }
}
```

All page objects extend `App` and override `navigateTo()` to use `Paths.*` constants from `src/e2e/urls.ts`.

### CSP Fixture Import (MANDATORY)

All spec files MUST import `test` and `expect` from the CSP fixture, never from `@playwright/test` directly:

```typescript
// Source: src/e2e/tests/about.page.spec.ts [VERIFIED: read directly]
import { test, expect } from './fixtures/csp-listener';
```

### API-Set Config Pattern

Used for both test setup and `afterEach` cleanup:

```typescript
// Source: src/e2e/tests/settings.page.ts [VERIFIED: read directly]
const response = await this.page.request.get(
    '/server/config/set/sonarr/enabled/true'
);
if (!response.ok()) {
    throw new Error(`enableSonarr failed: ${response.status()} ${response.statusText()}`);
}
```

Config section/key pairs confirmed in `options-list.ts` [VERIFIED]:
- Text: `lftp/remote_address`, `lftp/remote_username`, `lftp/remote_port`
- Checkbox: `lftp/use_ssh_key`, `general/debug`
- Interval (Text): `controller/interval_ms_remote_scan`, `controller/interval_ms_local_scan`

Values in URL path must be `encodeURIComponent()`-encoded for non-alphanumeric values (existing convention from `setSonarrUrl`).

### afterEach Cleanup Pattern

```typescript
// Source: src/e2e/tests/settings-error.spec.ts [VERIFIED: read directly]
test.afterEach(async () => {
    await settingsPage.disableSonarr().catch(() => {});
});
```

The `.catch(() => {})` prevents test suite failures when cleanup itself encounters an error.

### Structural Probe Pattern (shallow)

```typescript
// Source: src/e2e/tests/about.page.spec.ts [VERIFIED: read directly]
test('should have About nav link active', async ({ page }) => {
    const aboutPage = new AboutPage(page);
    const activeLink = await aboutPage.getActiveNavLink();
    expect(activeLink).toBe('About');
});
```

For the Logs page, structural probes verify toolbar buttons are visible, `.log-row` count >= 1, and status bar text is present — not interactivity.

### Recommended Project Structure (new files only)

```
src/e2e/tests/
├── logs.page.ts               # LogsPage page object
├── logs.page.spec.ts          # COVER-02 specs (structural smoke + SSE delivery)
└── settings-fields.spec.ts    # COVER-03 specs (field types + save round-trip)
```

`settings.page.ts` is extended in-place, not replaced.

---

## Critical Implementation Details

### 1. OptionComponent 1000ms Debounce

**Source:** `src/angular/src/app/pages/settings/option.component.ts` [VERIFIED: read directly]

`OptionComponent` debounces all `changeEvent` emissions by **1000ms**. This means:

- After `page.fill()` on a text input, the test MUST wait at least 1s before the Angular `onSetConfig` fires
- The "Changes Saved" state (`saveConfirmed`) is visible for 2500ms after `onSetConfig` completes
- Use `await expect(page.locator('.floating-save-bar')).toContainText('Changes Saved', { timeout: 5000 })` to wait for the confirmation

Checkbox toggles also go through this debounce (the `[ngModel]` binding in `option.component.html` routes through the same `newValue` subject).

### 2. "Save Settings" vs. Config Persistence

**Source:** `src/angular/src/app/pages/settings/settings-page.component.ts` [VERIFIED: read directly]

- Config is **persisted** on each `onSetConfig` call (the API call to `/server/config/set`)
- The **"Save Settings" button** calls `onCommandRestart()` which triggers a server restart — it does NOT trigger persistence
- `saveConfirmed` is set by `onSaveComplete()` called from the `onSetConfig` success path — NOT from the Save Settings button click

For COVER-03 D-09 (assert "Changes Saved" as E2E-verifiable proof): assert `.floating-save-bar` contains text "Changes Saved" BEFORE clicking Save Settings. The confirmation fires immediately when the config API call returns 200.

For the full round-trip test (D-10): fill field → wait for "Changes Saved" (proves API succeeded) → click "Save Settings" → wait for page reconnect (SSE reconnect after restart) → reload → verify field value.

### 3. Logs Page: SSE Trigger via Config Change

**Source:** CONTEXT.md D-04 + controller.py line ~1075 [VERIFIED: code read]

The controller logs an INFO entry at `controller.py:1075` when it receives a command from the queue:
```python
self.logger.info("Received command {} for file {}".format(str(command.action), command.filename))
```

A simpler, more reliable approach for E2E: trigger a config change via `page.request.get('/server/config/set/general/debug/false')` (or true→false toggle). This causes `onSetConfig` in the Angular app itself to fire, which produces a log entry via the configured Python logger at the backend. The resulting log row will appear in `.log-row` within the terminal viewport.

Alternatively, relying on **organic logs** (the harness starts services that log INFO entries during scan cycles) is viable for the page-load smoke assertion per D-05.

### 4. Logs Page DOM Structure

**Source:** `logs-page.component.html` [VERIFIED: read directly]

Key locators for the Logs page page object:

| Element | Selector | Notes |
|---------|----------|-------|
| Level filter buttons | `.level-filter-group .level-btn` | 5 buttons: ALL, INFO, WARN, ERROR, DEBUG |
| Active level button | `.level-btn.level-btn--active` | Currently active level |
| Search input | `.search-input` | `input[type=text]` with placeholder |
| Auto-scroll button | `.action-btn` (filter by text 'Auto-scroll') | Has `action-btn--active` class when on |
| Clear button | `.action-btn--clear` | |
| Export button | `.action-btn--export` | |
| Log rows | `.log-row` | Inside `.terminal-content` |
| Status bar | `.status-bar` | Contains `.status-bar__left` and `.status-bar__right` |
| Log count | `.status-bar__right` | Contains text "X logs indexed" |
| Connection status | `.status-dot` | Has `status-dot--connected` or `status-dot--disconnected` |

### 5. Settings Page: Floating Save Bar

**Source:** `settings-page.component.html` [VERIFIED: read directly]

```html
<div class="floating-save-bar">
  <div class="floating-save-inner">
    <!-- saveConfirmed == true -->
    <span class="save-status-label">Changes Saved</span>
    <!-- saveConfirmed == false -->
    <span class="save-status-label">Unsaved Changes</span>
    
    <button class="btn-save-settings" [disabled]="!commandsEnabled">
      Save Settings
    </button>
  </div>
</div>
```

Assert confirmation: `await expect(page.locator('.floating-save-bar')).toContainText('Changes Saved')`.

The `btn-save-settings` button is disabled when `commandsEnabled` is false (i.e., when SSE is disconnected). Tests using D-10 (UI round-trip with restart) must wait for reconnect before the Save Settings button becomes enabled again.

### 6. App Spec Confirms Nav Label for Logs

**Source:** `src/e2e/tests/app.spec.ts` [VERIFIED: read directly]

The nav labels are: `['Dashboard', 'Settings', 'Logs', 'About']`. The Logs page active nav link text is `'Logs'`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Waiting for SSE data to arrive | Custom polling loop | `locator.waitFor({ state: 'visible' })` / `expect(locator).toHaveCount(n, { timeout })` | Playwright's auto-waiting handles SSE latency correctly |
| Config cleanup | Custom REST client | `page.request.get('/server/config/set/...')` | Already established pattern in `settings.page.ts`; uses Playwright's own request context |
| Debounce wait after fill | `page.waitForTimeout(1100)` | `expect(floatingSaveBar).toContainText('Changes Saved', { timeout: 5000 })` | Wait for observable outcome, not arbitrary time — more robust and aligns with Playwright best practice |
| CSP violation detection | Custom console listener | `import { test, expect } from './fixtures/csp-listener'` | Already implemented in Phase 91; auto-detects and fails on violation |

**Key insight:** In this codebase, all timing waits should be expressed as "wait for this element state" not "sleep N ms". The 1000ms debounce and API round-trip latency are handled implicitly by waiting for the "Changes Saved" confirmation to appear.

---

## Common Pitfalls

### Pitfall 1: Importing test/expect from @playwright/test directly

**What goes wrong:** CSP violations go undetected; tests pass while silent CSP regressions exist.
**Why it happens:** Default Playwright test import bypasses the `csp-listener.ts` fixture.
**How to avoid:** Always `import { test, expect } from './fixtures/csp-listener'` in every new spec file.
**Warning signs:** Spec file opens with `from '@playwright/test'` instead of `from './fixtures/csp-listener'`.

### Pitfall 2: Not accounting for OptionComponent 1000ms debounce

**What goes wrong:** Test fills a text field, immediately asserts "Changes Saved" → assertion fails because the debounce hasn't fired yet.
**Why it happens:** The option component delays `changeEvent` emission by 1000ms after last keystroke.
**How to avoid:** After filling a text field, wait for the observable outcome: `expect(floatingSaveBar).toContainText('Changes Saved', { timeout: 5000 })`. The 5s timeout covers 1s debounce + network round-trip.
**Warning signs:** Using `page.waitForTimeout(500)` after fill — deprecated pattern, now forbidden (E2EFIX-03 removed this).

### Pitfall 3: asserting scroll position instead of DOM state for auto-scroll

**What goes wrong:** Test checks pixel scroll position → CI fails on different viewport sizes or when organic logs haven't populated yet.
**Why it happens:** `scrollTop` / `scrollHeight` values vary with viewport and content.
**How to avoid:** Assert only that the auto-scroll button has class `action-btn--active` (template sets this via `[class.action-btn--active]="autoScroll"`, and `autoScroll` defaults to `true`).
**Warning signs:** Test uses `page.evaluate(() => element.scrollTop)` or similar.

### Pitfall 4: afterEach cleanup not using `.catch(() => {})`

**What goes wrong:** Cleanup API call fails (e.g., service briefly unreachable after restart) → throws in afterEach → masks the actual test result with a teardown error.
**Why it happens:** Teardown runs after the server restart in D-10 tests; server may not be immediately available.
**How to avoid:** Follow `settings-error.spec.ts` pattern: `await page.request.get(...).catch(() => {})`. For SettingsPage methods called from afterEach, wrap in `.catch(() => {})`.
**Warning signs:** afterEach body has uncaught async calls without error handling.

### Pitfall 5: Testing config keys that don't exist or wrong section name

**What goes wrong:** `/server/config/set/wrongsection/key/value` returns 404 → test setup silently fails → field doesn't change → assertion fails with confusing message.
**Why it happens:** Section names in the API must match config object property names exactly.
**How to avoid:** Use only the verified pairs from `options-list.ts`: e.g., `lftp/remote_address`, `lftp/use_ssh_key`, `controller/interval_ms_remote_scan`. Check response with `.ok()` check as done in existing `SettingsPage` methods.
**Warning signs:** API call returns non-200 status; test setup doesn't check response status.

### Pitfall 6: Log row assertion without SSE data arriving

**What goes wrong:** Test navigates to Logs page and immediately asserts `.log-row` count >= 1 → 0 rows because SSE hasn't delivered any records yet.
**Why it happens:** `LogService` uses `ReplaySubject(5000)` but the Angular component's `scan` accumulator starts empty on each navigation. Real logs arrive asynchronously over SSE.
**How to avoid:** Either (a) trigger a config-change API call before navigation to pre-populate the SSE buffer, or (b) use `expect(page.locator('.log-row').first()).toBeVisible({ timeout: 10000 })` after navigation to wait for organic logs.
**Warning signs:** Asserting `.toHaveCount()` with no timeout on `.log-row` immediately after `navigateTo()`.

---

## Code Examples

### LogsPage Page Object (new file pattern)

```typescript
// Pattern derived from: src/e2e/tests/about.page.ts [VERIFIED: read directly]
import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class LogsPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.LOGS);
    }

    getLevelButtons() {
        return this.page.locator('.level-filter-group .level-btn');
    }

    getSearchInput() {
        return this.page.locator('.search-input');
    }

    getAutoScrollButton() {
        return this.page.locator('.action-btn').filter({ hasText: 'Auto-scroll' });
    }

    getClearButton() {
        return this.page.locator('.action-btn--clear');
    }

    getExportButton() {
        return this.page.locator('.action-btn--export');
    }

    getLogRows() {
        return this.page.locator('.log-row');
    }

    getStatusBar() {
        return this.page.locator('.status-bar');
    }
}
```

### SettingsPage Extension (new methods)

```typescript
// Extending src/e2e/tests/settings.page.ts [VERIFIED: read directly]
// Add to SettingsPage class:

async setServerAddress(address: string): Promise<void> {
    const response = await this.page.request.get(
        `/server/config/set/lftp/remote_address/${encodeURIComponent(address)}`
    );
    if (!response.ok()) {
        throw new Error(`setServerAddress failed: ${response.status()} ${response.statusText()}`);
    }
}

async getServerAddress(): Promise<string | null> {
    // Locator for the Server Address input (in Remote Server card, full-width grid-span-2)
    return this.page.locator(
        '.settings-card-body--grid-2col .grid-span-2 app-option input[type="text"]'
    ).first().inputValue();
}

async fillServerAddress(address: string): Promise<void> {
    await this.page.locator(
        '.settings-card-body--grid-2col .grid-span-2 app-option input[type="text"]'
    ).first().fill(address);
}

async waitForSaveConfirmed(): Promise<void> {
    await expect(this.page.locator('.floating-save-bar'))
        .toContainText('Changes Saved', { timeout: 5000 });
}

async clickSaveSettings(): Promise<void> {
    await this.page.locator('.btn-save-settings').click();
}
```

### SSE Trigger Pattern for Logs Tests

```typescript
// Trigger a backend log entry via config change (no test-only endpoints needed)
// Pattern from CONTEXT.md D-04 [ASSUMED: specific API call produces INFO log]
const response = await page.request.get('/server/config/set/general/debug/false');
// OR use any other valid config change that doesn't alter test state materially
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `waitForTimeout(500)` | `locator.waitFor()` / expect with timeout | E2EFIX-03 (Phase 91) | All timing waits must be outcome-based |
| `:has-text()` pseudo-class | `locator.filter({ hasText })` | E2EFIX-05 (Phase 91) | New specs must use filter API, not deprecated pseudo-class |
| `beforeAll` for seeding | `beforeEach` with navigate | E2EFIX-04 (Phase 91) | beforeAll bypasses CSP fixture; always use beforeEach |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A config-change API call (e.g., `/server/config/set/general/debug/false`) produces a visible INFO-level log entry in the SSE stream reliably enough to assert `.log-row` renders | Code Examples: SSE Trigger Pattern | If no log entry is produced by this specific call, the SSE delivery test needs a different trigger (e.g., stop command on a known file) |
| A2 | The auto-scroll button locator `.action-btn` filtered by `hasText: 'Auto-scroll'` is unique enough on the page | Code Examples: LogsPage | If other `.action-btn` elements contain the text substring "Auto-scroll", locator may be ambiguous — may need to scope to `.toolbar-right` |
| A3 | `lftp/remote_address` has a writable default value in the Docker test stack (not null/empty/placeholder) so API-set → reload → verify round-trip works | Settings patterns | If the field is null in the test config, the Angular `[disabled]="value == null"` binding may block interaction |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

---

## Open Questions

1. **Which API call reliably triggers a log entry for COVER-02?**
   - What we know: Controller logs INFO at `controller.py:1075` on receiving a command; config changes call Python logger via `onSetConfig` → API → config.set_property (no explicit log in the handler)
   - What's unclear: Whether a GET to `/server/config/set/...` itself generates a backend log entry, or whether a stop-command on a known file is needed
   - Recommendation: Planner should check controller.py handler for explicit `self.logger.info(...)` in `__handle_set_config`, or use the organic-logs fallback per D-05 for the page-load smoke test, and only use the API-trigger for the specific log-row assertion test

2. **Server Address field locator precision**
   - What we know: The Remote Server card uses `settings-card-body--grid-2col` with multiple `grid-span-2` divs for text fields
   - What's unclear: Whether scoping to `.grid-span-2 app-option input[type="text"]` is precise enough to target only Server Address without matching Local Directory or other full-width text fields
   - Recommendation: Use `page.getByLabel('Server Address')` or use `.settings-card-body--grid-2col .grid-span-2 app-option` first `.locator` in the template order — planner should verify by label text

---

## Environment Availability

Step 2.6: SKIPPED — this phase adds only test files; no new external tools or services are required beyond the Docker compose stack already validated in Phase 92.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Playwright `^1.48.0` |
| Config file | `src/e2e/playwright.config.ts` |
| Quick run command | `cd src/e2e && npx playwright test --grep "logs\|settings-fields"` |
| Full suite command | `make run-tests-e2e` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COVER-02 | Logs page loads and nav link is active | E2E smoke | `npx playwright test logs.page.spec.ts` | ❌ Wave 0 |
| COVER-02 | All 5 level filter buttons visible on load | E2E smoke | `npx playwright test logs.page.spec.ts` | ❌ Wave 0 |
| COVER-02 | Search input visible on load | E2E smoke | `npx playwright test logs.page.spec.ts` | ❌ Wave 0 |
| COVER-02 | Auto-scroll button visible + has active class on load | E2E smoke | `npx playwright test logs.page.spec.ts` | ❌ Wave 0 |
| COVER-02 | At least 1 log row renders (SSE delivery proof) | E2E integration | `npx playwright test logs.page.spec.ts` | ❌ Wave 0 |
| COVER-02 | Status bar text visible | E2E smoke | `npx playwright test logs.page.spec.ts` | ❌ Wave 0 |
| COVER-03 | Settings page loads and nav link is active | E2E smoke | `npx playwright test settings-fields.spec.ts` | ❌ Wave 0 |
| COVER-03 | Text field (Server Address) saves via "Changes Saved" confirmation | E2E integration | `npx playwright test settings-fields.spec.ts` | ❌ Wave 0 |
| COVER-03 | Checkbox toggle (SSH key auth) saves via "Changes Saved" confirmation | E2E integration | `npx playwright test settings-fields.spec.ts` | ❌ Wave 0 |
| COVER-03 | Interval field (Discovery polling) saves via API-set + reload + verify | E2E integration | `npx playwright test settings-fields.spec.ts` | ❌ Wave 0 |
| COVER-03 | UI-to-UI round-trip: fill → save → restart → reload → verify persisted | E2E integration | `npx playwright test settings-fields.spec.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd src/e2e && npx playwright test logs.page.spec.ts settings-fields.spec.ts`
- **Per wave merge:** `make run-tests-e2e`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/e2e/tests/logs.page.ts` — LogsPage page object (COVER-02)
- [ ] `src/e2e/tests/logs.page.spec.ts` — Logs E2E specs (COVER-02)
- [ ] `src/e2e/tests/settings-fields.spec.ts` — Settings field specs (COVER-03)
- [ ] Extension methods added to `src/e2e/tests/settings.page.ts` (COVER-03)

---

## Security Domain

No new security surfaces introduced. This phase adds test files only — no production code changes. The existing `/server/config/set` endpoint used for test setup is already in production.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no — test code only | N/A |

---

## Sources

### Primary (HIGH confidence)
- `src/e2e/tests/app.ts` — Base class API verified
- `src/e2e/tests/about.page.ts` + `about.page.spec.ts` — Structural probe pattern verified
- `src/e2e/tests/settings.page.ts` + `settings-error.spec.ts` — API-set pattern and afterEach cleanup verified
- `src/e2e/tests/fixtures/csp-listener.ts` — CSP fixture import requirement verified
- `src/e2e/playwright.config.ts` — Test runner config verified
- `src/e2e/urls.ts` — Paths.LOGS and Paths.SETTINGS verified
- `src/angular/.../logs-page.component.html` — All DOM selectors verified
- `src/angular/.../logs-page.component.ts` — Auto-scroll default (`autoScroll = true`) verified
- `src/angular/.../settings-page.component.ts` — `onSaveComplete()` and `saveConfirmed` lifecycle verified
- `src/angular/.../settings-page.component.html` — Floating save bar HTML structure verified
- `src/angular/.../option.component.ts` — 1000ms debounce verified
- `src/angular/.../options-list.ts` — All section/key pairs verified
- `src/python/web/handler/config.py` — `/server/config/set` endpoint signature verified

### Secondary (MEDIUM confidence)
- npm registry: `@playwright/test` latest version 1.59.1 [VERIFIED: npm view]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Playwright version and package.json locked; no new dependencies
- Architecture: HIGH — All page objects, DOM selectors, and component logic read directly from source
- Pitfalls: HIGH — All identified from direct source code reading (debounce timing, DOM structure, cleanup pattern)

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable — no framework migrations in progress)
