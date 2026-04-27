# Phase 91: E2E Test Fixes & Platform - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 8 (7 modified + 1 new)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/e2e/tests/autoqueue.page.ts` | page-object | request-response | `src/e2e/tests/dashboard.page.ts` | exact |
| `src/e2e/tests/settings-error.spec.ts` | test-spec | request-response | `src/e2e/tests/dashboard.page.spec.ts` | exact |
| `src/e2e/tests/dashboard.page.spec.ts` | test-spec | request-response | `src/e2e/tests/dashboard.page.spec.ts` | self |
| `src/e2e/tests/dashboard.page.ts` | page-object | request-response | `src/e2e/tests/settings.page.ts` | exact |
| `src/e2e/tests/fixtures/seed-state.ts` | utility/fixture | request-response | `src/e2e/tests/fixtures/csp-listener.ts` | role-match |
| `src/e2e/tests/fixtures/helpers.ts` | utility | transform | `src/e2e/tests/fixtures/seed-state.ts` | role-match |
| `src/e2e/playwright.config.ts` | config | — | `src/e2e/playwright.config.ts` | self |
| `src/e2e/tests/fixtures/csp-listener.ts` | fixture/middleware | event-driven | `src/e2e/tests/fixtures/csp-listener.ts` | self |

---

## Pattern Assignments

### `src/e2e/tests/autoqueue.page.ts` (page-object, request-response)

**Fixes:** E2EFIX-01 (innerHTML→innerText at line 28), E2EFIX-05 (:has-text() at line 35)

**Analog:** `src/e2e/tests/app.ts` (innerText pattern), `src/e2e/tests/dashboard.page.ts` (filter({ hasText }) pattern)

---

**E2EFIX-01 — Bug location** (`autoqueue.page.ts` lines 26-29):
```typescript
async getPatterns(): Promise<string[]> {
    const elements = await this.page.locator('.pattern-section .pattern-chip .pattern-chip-text').all();
    return Promise.all(elements.map(elm => elm.innerHTML()));  // BUG: returns HTML markup
}
```

**Correct pattern from** `src/e2e/tests/app.ts` lines 14-17:
```typescript
async getNavLinks(): Promise<string[]> {
    const items = await this.page.locator('#top-nav .nav-link').all();
    return Promise.all(items.map(item => item.innerText()));  // CORRECT: rendered text
}
```

**Fix:** Change `elm.innerHTML()` → `elm.innerText()` at line 28.

---

**E2EFIX-05 — Bug location** (`autoqueue.page.ts` line 35):
```typescript
await this.page.locator(`.pattern-section .pattern-chip-text:has-text("${pattern}")`).waitFor({ state: 'visible' });
// BUG: deprecated :has-text() pseudo-class
```

**Correct pattern from** `src/e2e/tests/dashboard.page.ts` lines 160-162:
```typescript
async waitForFileStatus(name: string, label: string, timeout: number = 10_000): Promise<void> {
    await this.getStatusBadge(name).filter({ hasText: label }).waitFor({ timeout });
}
```

**Fix:** Replace the `:has-text()` locator with `.filter({ hasText })`:
```typescript
await this.page.locator('.pattern-section .pattern-chip-text')
    .filter({ hasText: pattern })
    .waitFor({ state: 'visible' });
```

---

### `src/e2e/tests/settings-error.spec.ts` (test-spec, request-response)

**Fix:** E2EFIX-02 (beforeEach ordering — API call fires before `navigateTo()`)

**Analog:** `src/e2e/tests/dashboard.page.spec.ts`

**Bug location** (`settings-error.spec.ts` lines 7-10):
```typescript
test.beforeEach(async ({ page }) => {
    settingsPage = new SettingsPage(page);
    await settingsPage.disableSonarr();  // BUG: API call before navigation
});
```

**Correct pattern from** `src/e2e/tests/dashboard.page.spec.ts` lines 14-17 (beforeEach navigate-first):
```typescript
test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateTo();  // CORRECT: navigation first
});
```

**Fix:** Add `await settingsPage.navigateTo()` before the `disableSonarr()` call:
```typescript
test.beforeEach(async ({ page }) => {
    settingsPage = new SettingsPage(page);
    await settingsPage.navigateTo();     // navigate first
    await settingsPage.disableSonarr(); // API call after page is ready
});
```

---

### `src/e2e/tests/dashboard.page.spec.ts` (test-spec, request-response)

**Fixes:** E2EFIX-03 (waitForTimeout at line 255), E2EFIX-04 (beforeAll CSP bypass at lines 121 and 375), E2EFIX-06 (missing response assertions at lines 272 and 302), PLAT-02 (arm64 sort — locale fix in config is primary remedy)

**Analog:** `src/e2e/tests/settings.page.ts` (response-checking pattern)

---

**E2EFIX-03 — Bug location** (`dashboard.page.spec.ts` lines 251-255):
```typescript
await page.request.post(`/server/command/stop/${encodeURIComponent('testing.gif')}`);
// Wait briefly for any stop to propagate before proceeding.
await page.waitForTimeout(500);  // BUG: fixed sleep
```

**Fix:** Remove `waitForTimeout(500)`. The Queue button assertion at line 277 provides Playwright auto-wait synchronization:
```typescript
await page.request.post(`/server/command/stop/${encodeURIComponent('testing.gif')}`);
// (no wait — the getActionButton('Queue').toBeEnabled() assertion at line 277
//  provides implicit synchronization via Playwright auto-wait)
```

---

**E2EFIX-04 — Bug location** (`dashboard.page.spec.ts` lines 121-133 and 375-387):
```typescript
test.beforeAll(async ({ browser }) => {
    test.setTimeout(120_000);
    const ctx = await browser.newContext();  // BUG: raw context bypasses CSP fixture
    const page = await ctx.newPage();
    const dash = new DashboardPage(page);
    await dash.navigateTo();
    await seedMultiple(page, [...]);
    await ctx.close();
});
```

**Fix (accepted limitation with documentation comment):**
```typescript
test.beforeAll(async ({ browser }) => {
    test.setTimeout(120_000);
    // CSP monitoring intentionally absent: raw context used for seed-state API calls only.
    // The fixture's page override applies only to per-test pages. Seed operations make HTTP
    // requests and poll badge DOM — they do not introduce new script sources; violations here
    // would indicate infrastructure issues, not app CSP regressions.
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    // ... rest unchanged
});
```

---

**E2EFIX-06 — Bug locations** (`dashboard.page.spec.ts` lines 272 and 302):
```typescript
await page.request.get('/server/config/set/lftp/rate_limit/100');  // BUG: no response check
// ...
await page.request.get('/server/config/set/lftp/rate_limit/0');    // BUG: no response check
```

**Correct pattern from** `src/e2e/tests/settings.page.ts` lines 14-20:
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

**Also from** `src/e2e/tests/fixtures/seed-state.ts` lines 48-60 (`expectOk` helper with POST/DELETE/GET):
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

**Fix:** Assign response and check `.ok()`:
```typescript
const throttleResp = await page.request.get('/server/config/set/lftp/rate_limit/100');
if (!throttleResp.ok()) throw new Error(`rate_limit set failed: ${throttleResp.status()}`);
// ... (in finally block)
const restoreResp = await page.request.get('/server/config/set/lftp/rate_limit/0');
if (!restoreResp.ok()) throw new Error(`rate_limit restore failed: ${restoreResp.status()}`);
```

---

### `src/e2e/tests/dashboard.page.ts` (page-object, request-response)

**Fix:** E2EFIX-07 (_escapeRegex private method at line 168 — extract to shared helpers.ts)

**Bug location** (`dashboard.page.ts` lines 168-170):
```typescript
private _escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
```

**Usage sites in same file** (lines 55 and 82):
```typescript
getRowCheckbox(fileName: string): Locator {
    const row = this.page.locator('.transfer-table tbody app-transfer-row', {
        has: this.page.locator('td.cell-name .file-name', { hasText: new RegExp(`^${this._escapeRegex(fileName)}$`) })
    });
    // ...
}
```

**Fix:** Remove private method, import from new `./helpers`:
```typescript
import { escapeRegex } from './helpers';
// Change: this._escapeRegex(fileName) → escapeRegex(fileName)  (two sites: lines 55 and 82)
```

---

### `src/e2e/tests/fixtures/seed-state.ts` (utility/fixture, request-response)

**Fix:** E2EFIX-07 (module-local `escapeRegex` at line 44 — replace with import from shared helpers.ts)

**Bug location** (`seed-state.ts` lines 44-46):
```typescript
function escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
```

**Fix:** Remove function definition, add import:
```typescript
import { escapeRegex } from './helpers';
// Remove lines 44-46 (the local function definition)
// Existing usages of escapeRegex(name) at lines 68-70 continue to work unchanged
```

---

### `src/e2e/tests/helpers.ts` (NEW utility, transform)

**Fix:** E2EFIX-07 — create shared utility file with `escapeRegex`

**Pattern source:** Both `dashboard.page.ts:168` and `seed-state.ts:44` contain the identical implementation.

**Import style from** `src/e2e/tests/fixtures/seed-state.ts` lines 1-2:
```typescript
import type { Page } from '@playwright/test';
```

**New file content:**
```typescript
/**
 * Escape special regex characters in a string so it can be used as a literal
 * pattern inside `new RegExp(...)`.
 *
 * Extracted from dashboard.page.ts and fixtures/seed-state.ts (E2EFIX-07).
 */
export function escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
```

Note: No `@playwright/test` import needed — this is a pure utility with no Playwright dependency.

---

### `src/e2e/playwright.config.ts` (config)

**Fix:** PLAT-02 — add `locale: 'en-US'` to force deterministic ICU collation on arm64 Chromium

**Bug location** (`playwright.config.ts` lines 18-22):
```typescript
use: {
    baseURL: process.env.APP_BASE_URL || 'http://myapp:8800',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
},
```

**Fix:**
```typescript
use: {
    baseURL: process.env.APP_BASE_URL || 'http://myapp:8800',
    locale: 'en-US',  // Force deterministic ICU locale; prevents arm64/amd64 sort divergence
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
},
```

---

### `src/e2e/tests/fixtures/csp-listener.ts` (fixture/middleware, event-driven)

**Fix:** PLAT-01 — no code changes to the fixture itself. The beforeAll CSP bypass (E2EFIX-04) is addressed by documentation comments in `dashboard.page.spec.ts`. The fixture is already complete and all 7 spec files already import from it.

**Reference — full fixture pattern** (`csp-listener.ts` lines 19-71):
```typescript
export const test = base.extend<Fixtures>({
    allowViolations: [false, { option: true }],

    cspViolations: async ({}, use) => {
        await use([]);
    },

    page: async ({ page, cspViolations, allowViolations }, use) => {
        await page.exposeFunction('__reportCspViolation', (v: unknown) => { /* ... */ });
        await page.addInitScript(() => {
            document.addEventListener('securitypolicyviolation', (e) => {
                // @ts-expect-error — exposed function on window at runtime
                window.__reportCspViolation({ ... });
            });
        });
        page.on('console', (msg) => {
            if (msg.type() === 'error' &&
                msg.text().includes('violates the following Content Security Policy directive')) {
                cspViolations.push({ source: 'console', text: msg.text() });
            }
        });
        await use(page);
        if (!allowViolations) {
            expect(cspViolations, 'CSP violations detected').toEqual([]);
        }
    },
});
export { expect };
```

---

## Shared Patterns

### Response-checking for `page.request.*` calls
**Source:** `src/e2e/tests/settings.page.ts` lines 14-20
**Apply to:** All `page.request.get/post` API calls in `dashboard.page.spec.ts` (E2EFIX-06) and anywhere an API failure should abort the test
```typescript
const response = await this.page.request.get('/server/config/set/...');
if (!response.ok()) {
    throw new Error(`<methodName> failed: ${response.status()} ${response.statusText()}`);
}
```

### `filter({ hasText })` for text-content locator filtering
**Source:** `src/e2e/tests/dashboard.page.ts` lines 160-162 and `src/e2e/tests/fixtures/seed-state.ts` lines 66-72
**Apply to:** Any locator that currently uses `:has-text()` pseudo-class (E2EFIX-05)
```typescript
// Page object pattern (dashboard.page.ts):
await this.getStatusBadge(name).filter({ hasText: label }).waitFor({ timeout });

// Constructor pattern (seed-state.ts):
const row = page.locator('.transfer-table tbody app-transfer-row', {
    has: page.locator('td.cell-name .file-name', {
        hasText: new RegExp(`^${escapeRegex(name)}$`),
    }),
});
await row.locator('td.cell-status .status-badge').filter({ hasText: label }).waitFor({ timeout });
```

### `innerText()` for visible text content
**Source:** `src/e2e/tests/app.ts` lines 14-17, `src/e2e/tests/settings.page.ts` line 50
**Apply to:** Any `elm.innerHTML()` call used for text content assertions (E2EFIX-01)
```typescript
// app.ts (model):
return Promise.all(items.map(item => item.innerText()));

// settings.page.ts (single element):
const text = await result.innerText();
```

### CSP fixture import convention
**Source:** `src/e2e/tests/settings-error.spec.ts` line 1, `src/e2e/tests/dashboard.page.spec.ts` line 1
**Apply to:** All spec files (already applied — no changes needed for PLAT-01)
```typescript
import { test, expect } from './fixtures/csp-listener';
```

### `beforeEach` navigate-first ordering
**Source:** `src/e2e/tests/dashboard.page.spec.ts` lines 14-17
**Apply to:** `settings-error.spec.ts` beforeEach (E2EFIX-02)
```typescript
test.beforeEach(async ({ page }) => {
    pageObject = new PageClass(page);
    await pageObject.navigateTo();  // always first
    // then any API state setup
});
```

---

## No Analog Found

All files have close analogs in the codebase. No files require falling back to RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `src/e2e/tests/`, `src/e2e/tests/fixtures/`, `src/e2e/playwright.config.ts`
**Files scanned:** 8 source files read in full
**Pattern extraction date:** 2026-04-27
