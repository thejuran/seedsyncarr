# Phase 85: E2E Test Audit - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 14 (7 spec files + 5 page objects + 2 fixtures)
**Analogs found:** 14 / 14 (all files are existing — audit phase, no new files)

---

## File Classification

Phase 85 is a read-only staleness audit. No new files are created. All files listed below are existing files
being audited for stale/redundant coverage. Classification is provided for planner reference when
authoring plan actions that reference these files.

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/e2e/tests/app.spec.ts` | test (smoke) | request-response | `src/e2e/tests/about.page.spec.ts` | exact |
| `src/e2e/tests/about.page.spec.ts` | test (smoke) | request-response | `src/e2e/tests/app.spec.ts` | exact |
| `src/e2e/tests/settings.page.spec.ts` | test (smoke) | request-response | `src/e2e/tests/about.page.spec.ts` | exact |
| `src/e2e/tests/settings-error.spec.ts` | test (stateful) | request-response + API | `src/e2e/tests/autoqueue.page.spec.ts` | role-match |
| `src/e2e/tests/autoqueue.page.spec.ts` | test (CRUD) | request-response + CRUD | `src/e2e/tests/dashboard.page.spec.ts` | role-match |
| `src/e2e/tests/csp-canary.spec.ts` | test (security canary) | event-driven | none (unique pattern) | no-analog |
| `src/e2e/tests/dashboard.page.spec.ts` | test (UAT) | request-response + state-seeding | `src/e2e/tests/autoqueue.page.spec.ts` | role-match |
| `src/e2e/tests/app.ts` | page-object (base) | request-response | `src/e2e/tests/about.page.ts` | exact |
| `src/e2e/tests/about.page.ts` | page-object | request-response | `src/e2e/tests/settings.page.ts` | exact |
| `src/e2e/tests/autoqueue.page.ts` | page-object (CRUD) | request-response + CRUD | `src/e2e/tests/dashboard.page.ts` | role-match |
| `src/e2e/tests/settings.page.ts` | page-object (API) | request-response + API | `src/e2e/tests/autoqueue.page.ts` | role-match |
| `src/e2e/tests/dashboard.page.ts` | page-object (complex) | request-response + state | `src/e2e/tests/autoqueue.page.ts` | role-match |
| `src/e2e/tests/fixtures/csp-listener.ts` | fixture (extend) | event-driven | none (unique pattern) | no-analog |
| `src/e2e/tests/fixtures/seed-state.ts` | fixture (state-seeding) | CRUD + polling | none (unique pattern) | no-analog |

---

## Pattern Assignments

### `src/e2e/tests/app.spec.ts` (test, smoke, request-response)

**Analog:** `src/e2e/tests/about.page.spec.ts`
**Audit verdict:** KEEP ALL (3 tests) — not stale, not redundant

**Imports pattern** (lines 1-2):
```typescript
import { test, expect } from './fixtures/csp-listener';
import { App } from './app';
```

**Structure pattern** (lines 4-32): `test.describe` with `test.beforeEach` navigating via page object:
```typescript
test.describe('Testing top-level app', () => {
    test.beforeEach(async ({ page }) => {
        const app = new App(page);
        await app.navigateTo();
    });

    test('should have right title', async ({ page }) => {
        const app = new App(page);
        const title = await app.getTitle();
        expect(title).toBe('SeedSyncarr');
    });
});
```

**Nav link assertion pattern** (lines 16-25):
```typescript
test('should have all the nav links', async ({ page }) => {
    const app = new App(page);
    const items = await app.getNavLinks();
    expect(items).toEqual([
        'Dashboard',
        'Settings',
        'Logs',
        'About',
    ]);
});
```

---

### `src/e2e/tests/about.page.spec.ts` (test, smoke, request-response)

**Analog:** `src/e2e/tests/app.spec.ts`
**Audit verdict:** KEEP ALL (2 tests) — not stale, not redundant

**Imports pattern** (lines 1-2):
```typescript
import { test, expect } from './fixtures/csp-listener';
import { AboutPage } from './about.page';
```

**Regex assertion pattern** (lines 16-20):
```typescript
test('should have the right version', async ({ page }) => {
    const aboutPage = new AboutPage(page);
    const version = await aboutPage.getVersion();
    expect(version).toMatch(/^v\d+\.\d+\.\d+$/);
});
```

---

### `src/e2e/tests/settings.page.spec.ts` (test, smoke, request-response)

**Analog:** `src/e2e/tests/about.page.spec.ts`
**Audit verdict:** KEEP (1 test) — see Open Question 2; `should have Settings nav link active` also
appears in `autoqueue.page.spec.ts` but D-01 staleness criteria does not cover duplicated
assertions against live code; conservative audit keeps both.

**Full file** (lines 1-15):
```typescript
import { test, expect } from './fixtures/csp-listener';
import { SettingsPage } from './settings.page';

test.describe('Testing settings page', () => {
    test.beforeEach(async ({ page }) => {
        const settingsPage = new SettingsPage(page);
        await settingsPage.navigateTo();
    });

    test('should have Settings nav link active', async ({ page }) => {
        const settingsPage = new SettingsPage(page);
        const activeLink = await settingsPage.getActiveNavLink();
        expect(activeLink).toBe('Settings');
    });
});
```

---

### `src/e2e/tests/settings-error.spec.ts` (test, stateful, request-response + API)

**Analog:** `src/e2e/tests/autoqueue.page.spec.ts`
**Audit verdict:** KEEP (1 test) — unique error-state coverage; no other spec tests Sonarr connection failure

**Imports + lifecycle pattern** (lines 1-14):
```typescript
import { test, expect } from './fixtures/csp-listener';
import { SettingsPage } from './settings.page';

test.describe('Settings page error states', () => {
    let settingsPage: SettingsPage;

    test.beforeEach(async ({ page }) => {
        settingsPage = new SettingsPage(page);
        await settingsPage.disableSonarr();
    });

    test.afterEach(async () => {
        await settingsPage.disableSonarr().catch(() => {});
    });
```

**Key pattern: `test.afterEach` teardown with `.catch(() => {})` swallowing teardown failures** (line 13):
```typescript
    test.afterEach(async () => {
        await settingsPage.disableSonarr().catch(() => {});
    });
```

**API-then-navigate pattern** (lines 16-27):
```typescript
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
```

---

### `src/e2e/tests/autoqueue.page.spec.ts` (test, CRUD, request-response + CRUD)

**Analog:** `src/e2e/tests/settings-error.spec.ts`
**Audit verdict:** KEEP ALL (3 tests) WITH CAVEAT — selectors live; `btn-pattern-add` may be disabled
in CI harness because `autoqueue/enabled` is not set by `setup_seedsyncarr.sh` (Pitfall 1)

**Imports + beforeEach isolation pattern** (lines 1-10):
```typescript
import { test, expect } from './fixtures/csp-listener';
import { AutoQueuePage } from './autoqueue.page';

test.describe('Testing autoqueue patterns in settings', () => {
    test.beforeEach(async ({ page }) => {
        const autoQueuePage = new AutoQueuePage(page);
        await autoQueuePage.navigateTo();
        // Clean up any existing patterns to ensure test isolation
        await autoQueuePage.removeAllPatterns();
    });
```

**CRUD sequence pattern** (lines 18-48): add → assert order → remove-by-index → assert remaining.

**Page reload + wait pattern** (lines 50-66):
```typescript
    test('should list existing patterns in alphabetical order', async ({ page }) => {
        // ...add patterns...
        await autoQueuePage.navigateTo();
        await autoQueuePage.waitForPatternsToLoad(4);
        expect(await autoQueuePage.getPatterns()).toEqual([...]);
    });
```

---

### `src/e2e/tests/csp-canary.spec.ts` (test, security canary, event-driven)

**Analog:** None — unique pattern (no other spec uses `test.use({ allowViolations: true })`)
**Audit verdict:** KEEP MANDATORY (1 test) — verifies the `csp-listener` fixture itself works; removal
would eliminate CSP violation guard verification for all other specs

**Critical pattern: `test.use({ allowViolations: true })`** (lines 1-3):
```typescript
import { test, expect } from './fixtures/csp-listener';

test.use({ allowViolations: true });
```

**CSP violation polling pattern** (lines 12-23):
```typescript
        await page.addInitScript(() => {
            document.addEventListener('DOMContentLoaded', () => {
                const el = document.createElement('script');
                el.src = 'https://evil.example.com/pwned.js';
                document.body.appendChild(el);
            });
        });

        await page.goto('/');

        await expect.poll(() => cspViolations.length).toBeGreaterThan(0);

        const sawScriptSrc = cspViolations.some((v) =>
            (v.source === 'event' && v.violatedDirective?.startsWith('script-src')) ||
            (v.source === 'console' && v.text?.includes('script-src'))
        );
        expect(sawScriptSrc).toBe(true);
```

---

### `src/e2e/tests/dashboard.page.spec.ts` (test, UAT, request-response + state-seeding)

**Analog:** `src/e2e/tests/autoqueue.page.spec.ts`
**Audit verdict:** KEEP ALL (26 tests) MANDATORY — core E2E UAT coverage; all selectors live

**Imports pattern** (lines 1-3):
```typescript
import { test, expect } from './fixtures/csp-listener';
import { DashboardPage, FileInfo } from './dashboard.page';
import { seedMultiple, seedStatus } from './fixtures/seed-state';
```

**`test.describe.serial` + `test.beforeAll` seeding pattern** (lines 118-138):
```typescript
test.describe.serial('UAT-01: selection and bulk bar', () => {
    let dashboardPage: DashboardPage;

    test.beforeAll(async ({ browser }) => {
        test.setTimeout(120_000);
        const ctx = await browser.newContext();
        const page = await ctx.newPage();
        const dash = new DashboardPage(page);
        await dash.navigateTo();
        await seedMultiple(page, [
            { file: DELETED_FILE, target: 'DELETED' },
            { file: DOWNLOADED_FILE, target: 'DOWNLOADED' },
            { file: STOPPED_FILE, target: 'STOPPED' },
        ]);
        await ctx.close();
    });

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });
```

**`toBeDisabled()` assertion pattern for Extract button** (per MEMORY: Extract disabled in e2e — assert `toBeDisabled`, do not click):
```typescript
    await expect(dashboardPage.getActionButton('Extract')).toBeDisabled();
```

**URL sub= param assertion** (per MEMORY: URL sub= params use enum values, not display labels):
```typescript
    await expect(page).toHaveURL(/[?&]sub=downloading(&|$)/);   // not "Syncing"
    await expect(page).toHaveURL(/[?&]sub=stopped(&|$)/);       // not "Failed"
```

---

## Page Object Pattern Assignments

### `src/e2e/tests/app.ts` (page-object, base class)

**Full file** (lines 1-22):
```typescript
import { Page } from '@playwright/test';

export class App {
    constructor(protected page: Page) {}

    async navigateTo() {
        await this.page.goto('/');
    }

    async getTitle(): Promise<string> {
        return this.page.title();
    }

    async getNavLinks(): Promise<string[]> {
        const items = await this.page.locator('#top-nav .nav-link').all();
        return Promise.all(items.map(item => item.innerText()));
    }

    async getActiveNavLink(): Promise<string> {
        return this.page.locator('#top-nav .nav-link.active').innerText();
    }
}
```

**Key:** `protected page: Page` — all subclasses extend `App` and call `super(page)`.

---

### `src/e2e/tests/about.page.ts` (page-object, simple subclass)

**Full file** (lines 1-20):
```typescript
import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class AboutPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.ABOUT);
    }

    async getVersion(): Promise<string> {
        const text = await this.page.locator('.version-badge').textContent() || '';
        const match = text.match(/Version\s+([\d.]+)/);
        return match ? `v${match[1]}` : '';
    }
}
```

**Pattern:** Extend `App`, override `navigateTo()` with `Paths.*` constant, add page-specific methods.

---

### `src/e2e/tests/autoqueue.page.ts` (page-object, CRUD)

**Imports + navigateTo with waitFor** (lines 1-14):
```typescript
import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class AutoQueuePage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.SETTINGS);
        await this.page.locator('.pattern-section').waitFor({ state: 'visible' });
    }
```

**`waitForFunction` poll pattern** (lines 16-24):
```typescript
    async waitForPatternsToLoad(expectedCount: number) {
        if (expectedCount > 0) {
            await this.page.waitForFunction(
                (expected) => document.querySelectorAll('.pattern-section .pattern-chip').length >= expected,
                expectedCount,
                { timeout: 5000 }
            );
        }
    }
```

**Remove-by-index + waitForFunction count-change pattern** (lines 38-45):
```typescript
    async removePattern(index: number) {
        const countBefore = await this.page.locator('.pattern-section .pattern-chip').count();
        await this.page.locator('.pattern-section .pattern-chip').nth(index).locator('.pattern-chip-remove').click();
        await this.page.waitForFunction(
            (expected) => document.querySelectorAll('.pattern-section .pattern-chip').length === expected,
            countBefore - 1
        );
    }
```

---

### `src/e2e/tests/settings.page.ts` (page-object, HTTP API via `page.request`)

**`page.request.get` with error-throw pattern** (lines 14-22):
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

**`fieldset` + `filter({ has: getByText(...) })` scoped locator pattern** (lines 42-48):
```typescript
    async clickTestSonarrConnection(): Promise<void> {
        const sonarrFieldset = this.page.locator('fieldset').filter({ has: this.page.getByText('Sonarr URL') });
        await sonarrFieldset.getByRole('button', { name: 'Test Connection' }).click();
    }

    async getSonarrTestResult(): Promise<{ text: string; isDanger: boolean }> {
        const sonarrFieldset = this.page.locator('fieldset').filter({ has: this.page.getByText('Sonarr URL') });
        const result = sonarrFieldset.locator('.test-result');
        await result.waitFor({ state: 'visible', timeout: 15000 });
        const text = await result.innerText();
        const isDanger = await result.evaluate(el => el.classList.contains('text-danger'));
        return { text, isDanger };
    }
```

---

### `src/e2e/tests/dashboard.page.ts` (page-object, complex)

**`has:` scoped locator pattern for row-scoped operations** (lines 53-58):
```typescript
    getRowCheckbox(fileName: string): Locator {
        const row = this.page.locator('.transfer-table tbody app-transfer-row', {
            has: this.page.locator('td.cell-name .file-name', { hasText: new RegExp(`^${this._escapeRegex(fileName)}$`) })
        });
        return row.locator('td.cell-checkbox input.ss-checkbox');
    }
```

**`getActionButton` by `getByRole('button', { name, exact: true })`** (lines 68-70):
```typescript
    getActionButton(name: 'Queue' | 'Stop' | 'Extract' | 'Delete Local' | 'Delete Remote'): Locator {
        return this.page.locator('app-bulk-actions-bar').getByRole('button', { name, exact: true });
    }
```

**`waitForFunction` for DOM count** (lines 25-35):
```typescript
    async waitForAtLeastFileCount(count: number, timeout: number = 10000) {
        await this.page.waitForFunction(
            (expectedCount: number) => {
                const rows = document.querySelectorAll('.transfer-table tbody app-transfer-row');
                return rows.length >= expectedCount &&
                    [...rows].every(r => r.querySelector('td.cell-name .file-name')?.textContent?.trim());
            },
            count,
            { timeout }
        );
    }
```

**`getSelectedCount` via checked checkboxes (not bar visibility)** (lines 155-158):
```typescript
        return await this.page
            .locator('.transfer-table tbody app-transfer-row td.cell-checkbox input.ss-checkbox:checked')
            .count();
```

---

## Fixture Pattern Assignments

### `src/e2e/tests/fixtures/csp-listener.ts` (fixture, event-driven)

**No analog — unique pattern.** This is the base fixture all specs import instead of `@playwright/test`.

**`base.extend<Fixtures>` pattern** (lines 19-68):
```typescript
export const test = base.extend<Fixtures>({
    allowViolations: [false, { option: true }],

    cspViolations: async ({}, use) => {
        await use([]);
    },

    page: async ({ page, cspViolations, allowViolations }, use) => {
        // ...setup: exposeFunction + addInitScript + page.on('console')...
        await use(page);

        if (!allowViolations) {
            expect(cspViolations, 'CSP violations detected').toEqual([]);
        }
    },
});

export { expect };
```

**Critical rule:** All spec files import `{ test, expect }` from this fixture, never from `@playwright/test`
directly. Only `csp-canary.spec.ts` sets `test.use({ allowViolations: true })`.

---

### `src/e2e/tests/fixtures/seed-state.ts` (fixture, state-seeding, CRUD + polling)

**No analog — unique pattern.** State seeding via HTTP API calls through `page.request`.

**`expectOk` helper pattern** (lines 48-60):
```typescript
async function expectOk(page: Page, url: string, method: 'POST' | 'DELETE' | 'GET'): Promise<void> {
    let res;
    if (method === 'POST') {
        res = await page.request.post(url);
    } else if (method === 'DELETE') {
        res = await page.request.delete(url);
    } else {
        res = await page.request.get(url);
    }
    if (!res.ok()) {
        throw new Error(`Seed call ${method} ${url} failed: ${res.status()} ${await res.text()}`);
    }
}
```

**`waitForBadge` row-scoped polling** (lines 65-72):
```typescript
async function waitForBadge(page: Page, name: string, label: string, timeout = 30_000): Promise<void> {
    const row = page.locator('.transfer-table tbody app-transfer-row', {
        has: page.locator('td.cell-name .file-name', {
            hasText: new RegExp(`^${escapeRegex(name)}$`),
        }),
    });
    await row.locator('td.cell-status .status-badge').filter({ hasText: label }).waitFor({ timeout });
}
```

**`seedMultiple` sequential execution** (lines 150-155):
```typescript
export async function seedMultiple(page: Page, plan: SeedPlanItem[]): Promise<void> {
    // Sequential: harness runs workers: 1 and LFTP contention makes parallel unsafe.
    for (const item of plan) {
        await seedStatus(page, item.file, item.target);
    }
}
```

---

## Shared Patterns

### CSP Listener Import (ALL specs)
**Source:** `src/e2e/tests/fixtures/csp-listener.ts`
**Apply to:** Every `*.spec.ts` file
```typescript
import { test, expect } from './fixtures/csp-listener';
// Never: import { test, expect } from '@playwright/test';
```

### Page Object Inheritance (ALL page objects)
**Source:** `src/e2e/tests/app.ts` (base), `src/e2e/tests/about.page.ts` (simplest subclass)
**Apply to:** Every `*.page.ts` file
```typescript
import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class XxxPage extends App {
    constructor(page: Page) { super(page); }
    async navigateTo() { await this.page.goto(Paths.XXX); }
}
```

### Route Constants (ALL page objects)
**Source:** `src/e2e/urls.ts`
**Apply to:** All page objects that call `navigateTo()`
```typescript
export const Paths = {
  DASHBOARD: '/dashboard',
  SETTINGS: '/settings',
  ABOUT: '/about',
  LOGS: '/logs',
} as const;
```

### HTTP API via `page.request` (stateful page objects)
**Source:** `src/e2e/tests/settings.page.ts` lines 14-22
**Apply to:** Any page object that must configure server state before a test
```typescript
const response = await this.page.request.get('/server/config/set/section/key/value');
if (!response.ok()) {
    throw new Error(`operation failed: ${response.status()} ${response.statusText()}`);
}
```

### `encodeURIComponent` on URL parameters
**Source:** `src/e2e/tests/fixtures/seed-state.ts` lines 16-20
**Apply to:** Any `page.request` call where file names or values go into URLs
```typescript
const ENDPOINT = {
    queue: (n: string) => `/server/command/queue/${encodeURIComponent(n)}`,
};
```

### Playwright Config (shared infrastructure)
**Source:** `src/e2e/playwright.config.ts`
**Key constraints for all plan tasks:**
- `workers: 1` — tests run sequentially; no parallel state assumptions
- `fullyParallel: false` — test order within a file is preserved
- `retries: 2` in CI — flaky transitions get 2 retries; do not over-stabilize timeouts
- `timeout: 30000` — 30s per test; seed operations use `test.setTimeout(120_000)` in `beforeAll`
- `baseURL: process.env.APP_BASE_URL || 'http://myapp:8800'`

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/e2e/tests/fixtures/csp-listener.ts` | fixture | event-driven | No other Playwright fixture extension exists in the codebase; this IS the base pattern |
| `src/e2e/tests/fixtures/seed-state.ts` | fixture | CRUD + polling | No other state-seeding fixture exists; pattern is internal to this file |
| `src/e2e/tests/csp-canary.spec.ts` | test (security canary) | event-driven | Only spec that uses `test.use({ allowViolations: true })` |

---

## Key Audit Findings for Planner

| Finding | Implication for Plan |
|---------|---------------------|
| ZERO stale spec files (all 7 LIVE) | E2E-02 removal action produces zero removals; document as explicit decision |
| `autoqueue.page.spec.ts` may fail CI (Pitfall 1) | Plan must include CI harness run BEFORE declaring audit complete; document failure as pre-existing defect if observed |
| `settings.page.spec.ts` has 1 test duplicated in `autoqueue.page.spec.ts` | Conservative keep; plan may explicitly document as candidate for future removal |
| Logs page (`/logs`) has zero E2E coverage | Document as coverage gap; out of scope per audit mandate |
| E2E verification requires Docker + pre-built image | Plan verification task must use `make run-tests-e2e`, not `npx playwright test` locally |
| arm64 verification only runs on push to main | amd64 is the primary verification arch; arm64 verified automatically on next main push |

---

## Metadata

**Analog search scope:** `src/e2e/tests/`, `src/e2e/tests/fixtures/`, `src/e2e/`
**Files scanned:** 14 (all E2E spec, page object, fixture, and config files)
**Pattern extraction date:** 2026-04-24
