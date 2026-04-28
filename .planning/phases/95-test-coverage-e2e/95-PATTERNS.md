# Phase 95: Test Coverage -- E2E - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 4 (3 new, 1 extended)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/e2e/tests/logs.page.ts` | page-object | request-response | `src/e2e/tests/about.page.ts` | exact |
| `src/e2e/tests/logs.page.spec.ts` | test | event-driven (SSE) | `src/e2e/tests/about.page.spec.ts` | role-match |
| `src/e2e/tests/settings-fields.spec.ts` | test | request-response + CRUD | `src/e2e/tests/settings-error.spec.ts` | exact |
| `src/e2e/tests/settings.page.ts` (extend) | page-object | CRUD | `src/e2e/tests/settings.page.ts` (self) | self |

---

## Pattern Assignments

### `src/e2e/tests/logs.page.ts` (page-object, request-response)

**Analog:** `src/e2e/tests/about.page.ts`

**Imports pattern** (lines 1-4):
```typescript
import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';
```

**Class + constructor + navigateTo pattern** (lines 5-14):
```typescript
export class AboutPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.ABOUT);
    }
```

**Locator method pattern** (lines 14-19):
```typescript
    async getVersion(): Promise<string> {
        const text = await this.page.locator('.version-badge').textContent() || '';
        const match = text.match(/Version\s+([\d.]+)/);
        return match ? `v${match[1]}` : '';
    }
```

**Locator return pattern** (`src/e2e/tests/dashboard.page.ts` lines 54-58, 61-62):
```typescript
    getRowCheckbox(fileName: string): Locator {
        const row = this.page.locator('.transfer-table tbody app-transfer-row', {
            has: this.page.locator('td.cell-name .file-name', { hasText: new RegExp(`^${escapeRegex(fileName)}$`) })
        });
        return row.locator('td.cell-checkbox input.ss-checkbox');
    }

    getHeaderCheckbox(): Locator {
        return this.page.locator('.transfer-table thead th.col-checkbox input.ss-checkbox');
    }
```

**Key locators for LogsPage** (verified from `logs-page.component.html` via RESEARCH.md):
- Level filter buttons: `.level-filter-group .level-btn` (5 buttons)
- Search input: `.search-input`
- Auto-scroll button: `.action-btn` filtered by `hasText: 'Auto-scroll'`
- Clear button: `.action-btn--clear`
- Export button: `.action-btn--export`
- Log rows: `.log-row` (inside `.terminal-content`)
- Status bar: `.status-bar`
- Log count: `.status-bar__right`
- Connection dot: `.status-dot`

**filter({ hasText }) pattern** (`src/e2e/tests/autoqueue.page.ts` lines 36-38):
```typescript
        await this.page.locator('.pattern-section .pattern-chip-text')
            .filter({ hasText: new RegExp(`^${escapeRegex(pattern)}$`) })
            .waitFor({ state: 'visible' });
```

**waitFor pattern for async content** (`src/e2e/tests/dashboard.page.ts` lines 19-24):
```typescript
    async navigateTo() {
        await this.page.goto(Paths.DASHBOARD);
        await this.page.locator('.transfer-table').waitFor({ state: 'visible', timeout: 30000 });
        await this.page.locator('.transfer-table tbody app-transfer-row').first()
            .waitFor({ state: 'visible', timeout: 30000 });
    }
```

---

### `src/e2e/tests/logs.page.spec.ts` (test, event-driven/SSE + structural-smoke)

**Analog:** `src/e2e/tests/about.page.spec.ts`

**Import pattern** (line 1-2):
```typescript
import { test, expect } from './fixtures/csp-listener';
import { AboutPage } from './about.page';
```
Note: Replace `AboutPage` with `LogsPage`. Never import from `@playwright/test` directly.

**describe + beforeEach pattern** (lines 4-9):
```typescript
test.describe('Testing about page', () => {
    test.beforeEach(async ({ page }) => {
        const aboutPage = new AboutPage(page);
        await aboutPage.navigateTo();
    });
```

**Structural probe test pattern** (lines 10-14):
```typescript
    test('should have About nav link active', async ({ page }) => {
        const aboutPage = new AboutPage(page);
        const activeLink = await aboutPage.getActiveNavLink();
        expect(activeLink).toBe('About');
    });
```

**afterEach cleanup pattern** (`src/e2e/tests/settings-error.spec.ts` lines 13-15):
```typescript
    test.afterEach(async () => {
        await settingsPage.disableSonarr().catch(() => {});
    });
```
Apply `.catch(() => {})` on any afterEach async call that hits the server — prevents teardown errors masking test results.

**SSE delivery assertion pattern** (RESEARCH.md — wait for outcome, not time):
```typescript
    // Wait for at least 1 log row to appear — Playwright auto-waits handle SSE latency
    await expect(logsPage.getLogRows().first()).toBeVisible({ timeout: 10000 });
    // OR for count-based assertion:
    await expect(logsPage.getLogRows()).toHaveCount(1, { timeout: 10000 });
```

**API-set trigger for SSE** (RESEARCH.md — trigger a backend change to produce a log entry):
```typescript
    // Trigger log entry via a config change before navigating to logs page
    const response = await page.request.get('/server/config/set/general/debug/false');
    // Do NOT assert response for this trigger (it's a fallback — organic logs are acceptable per D-05)
```

**DOM-state assertion instead of scroll-position** (RESEARCH.md — assert CSS class, not pixels):
```typescript
    // D-02: auto-scroll verified as DOM state only
    await expect(logsPage.getAutoScrollButton()).toHaveClass(/action-btn--active/);
```

---

### `src/e2e/tests/settings-fields.spec.ts` (test, CRUD + request-response)

**Analog:** `src/e2e/tests/settings-error.spec.ts`

**Full file structure pattern** (all lines 1-30):
```typescript
import { test, expect } from './fixtures/csp-listener';
import { SettingsPage } from './settings.page';

test.describe('Settings page error states', () => {
    let settingsPage: SettingsPage;

    test.beforeEach(async ({ page }) => {
        settingsPage = new SettingsPage(page);
        await settingsPage.navigateTo();
        await settingsPage.disableSonarr();
    });

    test.afterEach(async () => {
        await settingsPage.disableSonarr().catch(() => {});
    });

    test('should show error when Sonarr connection fails', async ({ page }) => {
        await settingsPage.enableSonarr();
        await settingsPage.setSonarrUrl('http://nonexistent.invalid:8989');
        await settingsPage.setSonarrApiKey('fake-api-key-for-testing');

        await settingsPage.navigateTo();

        await settingsPage.clickTestSonarrConnection();

        const result = await settingsPage.getSonarrTestResult();
        expect(result.isDanger).toBe(true);
        expect(result.text.length).toBeGreaterThan(0);
    });
});
```

**"Changes Saved" confirmation assertion** (RESEARCH.md critical detail — D-09):
```typescript
    // Assert floating save bar after fill + debounce resolves (5s covers 1s debounce + round-trip)
    await expect(page.locator('.floating-save-bar'))
        .toContainText('Changes Saved', { timeout: 5000 });
```

**API-set → reload → verify pattern** (`src/e2e/tests/settings-error.spec.ts` lines 19-23 + autoqueue reload pattern):
```typescript
    // API-set pattern (D-11): set value via API, reload, verify UI shows value
    await settingsPage.setSomeField('value');
    await settingsPage.navigateTo();  // reload the page
    // then assert input value or visible text
```

**UI-to-UI round-trip pattern** (RESEARCH.md D-10 + autoqueue.page.spec.ts lines 61-66 for reload+wait):
```typescript
    // D-10: fill via UI → wait for "Changes Saved" → click "Save Settings" → wait reconnect → reload → verify
    await settingsPage.fillServerAddress('192.168.1.100');
    await expect(page.locator('.floating-save-bar'))
        .toContainText('Changes Saved', { timeout: 5000 });
    await settingsPage.clickSaveSettings();
    // Wait for SSE reconnect (btn-save-settings re-enables when commandsEnabled is true)
    await expect(page.locator('.btn-save-settings')).toBeEnabled({ timeout: 15000 });
    await settingsPage.navigateTo();
    expect(await settingsPage.getServerAddress()).toBe('192.168.1.100');
```

---

### `src/e2e/tests/settings.page.ts` (extend in-place, CRUD)

**Analog:** `src/e2e/tests/settings.page.ts` (self — existing methods to copy pattern from)

**Existing API-set method pattern** (lines 14-21):
```typescript
    async enableSonarr(): Promise<void> {
        const response = await this.page.request.get(
            '/server/config/set/sonarr/enabled/true'
        );
        if (!response.ok()) {
            throw new Error(`enableSonarr failed: ${response.status()} ${response.statusText()}`);
        }
    }
```

**URL-encoded value pattern** (lines 23-30):
```typescript
    async setSonarrUrl(url: string): Promise<void> {
        const response = await this.page.request.get(
            `/server/config/set/sonarr/sonarr_url/${encodeURIComponent(url)}`
        );
        if (!response.ok()) {
            throw new Error(`setSonarrUrl failed: ${response.status()} ${response.statusText()}`);
        }
    }
```

**Locator with filter pattern** (lines 42-44):
```typescript
    async clickTestSonarrConnection(): Promise<void> {
        const sonarrFieldset = this.page.locator('fieldset').filter({ has: this.page.getByText('Sonarr URL') });
        await sonarrFieldset.getByRole('button', { name: 'Test Connection' }).click();
    }
```

**waitFor on result element** (lines 46-53):
```typescript
    async getSonarrTestResult(): Promise<{ text: string; isDanger: boolean }> {
        const sonarrFieldset = this.page.locator('fieldset').filter({ has: this.page.getByText('Sonarr URL') });
        const result = sonarrFieldset.locator('.test-result');
        await result.waitFor({ state: 'visible', timeout: 15000 });
        const text = await result.innerText();
        const isDanger = await result.evaluate(el => el.classList.contains('text-danger'));
        return { text, isDanger };
    }
```

**New methods to add — verified config section/key pairs** (from RESEARCH.md, sourced from `options-list.ts`):
- `lftp/remote_address` — Server Address (text)
- `lftp/use_ssh_key` — SSH key auth (boolean/checkbox, values `true`/`false`)
- `controller/interval_ms_remote_scan` — Discovery polling interval (text/number)
- `lftp/remote_username` — Remote Username (text)
- `lftp/remote_port` — Remote Port (text/number)

---

## Shared Patterns

### CSP Fixture Import (mandatory for all new spec files)

**Source:** `src/e2e/tests/fixtures/csp-listener.ts` + confirmed in `about.page.spec.ts` line 1, `settings-error.spec.ts` line 1, `autoqueue.page.spec.ts` line 1, `app.spec.ts` line 1

**Apply to:** Every new `.spec.ts` file — `logs.page.spec.ts` and `settings-fields.spec.ts`

```typescript
import { test, expect } from './fixtures/csp-listener';
```

Never use:
```typescript
import { test, expect } from '@playwright/test'; // WRONG — bypasses CSP detection
```

### beforeEach Navigation

**Source:** `src/e2e/tests/about.page.spec.ts` lines 5-8, `src/e2e/tests/settings-error.spec.ts` lines 7-10

**Apply to:** All new spec files

```typescript
    test.beforeEach(async ({ page }) => {
        const xPage = new XPage(page);
        await xPage.navigateTo();
    });
```

Do NOT use `beforeAll` — it bypasses the CSP fixture (E2EFIX-04, Phase 91).

### afterEach Cleanup with .catch(() => {})

**Source:** `src/e2e/tests/settings-error.spec.ts` lines 13-15

**Apply to:** All tests that modify config state (all COVER-03 tests)

```typescript
    test.afterEach(async () => {
        await settingsPage.restoreOriginalValue().catch(() => {});
    });
```

The `.catch(() => {})` is mandatory — teardown may run after a server restart (D-10) and the server may not be immediately available.

### API-Set Config Request

**Source:** `src/e2e/tests/settings.page.ts` lines 14-21

**Apply to:** All SettingsPage setup/teardown methods and new config-set methods

```typescript
    async setConfigValue(section: string, key: string, value: string): Promise<void> {
        const response = await this.page.request.get(
            `/server/config/set/${section}/${key}/${encodeURIComponent(value)}`
        );
        if (!response.ok()) {
            throw new Error(`setConfigValue failed: ${response.status()} ${response.statusText()}`);
        }
    }
```

Always check `response.ok()` and throw with status details — silent failures lead to confusing test errors (Pitfall 5 from RESEARCH.md).

### Outcome-Based Waiting (no waitForTimeout)

**Source:** RESEARCH.md "State of the Art" + `src/e2e/tests/dashboard.page.ts` lines 19-24, `src/e2e/tests/autoqueue.page.ts` lines 36-38

**Apply to:** All async assertions in both new spec files

```typescript
// Correct — wait for observable outcome:
await expect(locator).toBeVisible({ timeout: 10000 });
await expect(locator).toContainText('Changes Saved', { timeout: 5000 });
await locator.waitFor({ state: 'visible', timeout: 15000 });

// WRONG — forbidden since E2EFIX-03 (Phase 91):
await page.waitForTimeout(500);
```

### Page Object Extends App

**Source:** `src/e2e/tests/about.page.ts` lines 5-8, `src/e2e/tests/settings.page.ts` lines 5-8

**Apply to:** `logs.page.ts` (new page object)

```typescript
export class LogsPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.LOGS);
    }
```

### filter({ hasText }) for Text-Matched Locators

**Source:** `src/e2e/tests/settings.page.ts` line 42, `src/e2e/tests/autoqueue.page.ts` line 36

**Apply to:** `logs.page.ts` auto-scroll button locator

```typescript
    getAutoScrollButton() {
        return this.page.locator('.action-btn').filter({ hasText: 'Auto-scroll' });
    }
```

Do NOT use deprecated `:has-text()` pseudo-class (E2EFIX-05, Phase 91).

---

## No Analog Found

All 4 files have strong analogs in the codebase. No files require fallback to RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `src/e2e/tests/` (all files enumerated)
**Files scanned:** 10 (app.ts, app.spec.ts, about.page.ts, about.page.spec.ts, settings.page.ts, settings.page.spec.ts, settings-error.spec.ts, autoqueue.page.ts, autoqueue.page.spec.ts, dashboard.page.ts) + fixtures/csp-listener.ts, helpers.ts, playwright.config.ts, urls.ts
**Pattern extraction date:** 2026-04-28
