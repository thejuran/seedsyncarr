# Phase 69: E2E Selector Update - Pattern Map

**Mapped:** 2026-04-15
**Files analyzed:** 2 modified files
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/e2e/tests/dashboard.page.ts` | page-object | request-response | `src/e2e/tests/autoqueue.page.ts` | exact (page-object, DOM enumeration) |
| `src/e2e/tests/dashboard.page.spec.ts` | test | request-response | `src/e2e/tests/autoqueue.page.spec.ts` | role-match (spec with golden data) |
| `src/e2e/tests/bulk-actions.spec.ts` | test | request-response | N/A — bulk-selection UI absent from dashboard route | no analog (retire/skip) |

---

## Pattern Assignments

### `src/e2e/tests/dashboard.page.ts` (page-object, request-response)

**Analog:** `src/e2e/tests/autoqueue.page.ts`

The autoqueue page object is the closest current analog because it uses:
- `waitFor({ state: 'visible' })` in `navigateTo()` (not a bare goto)
- `waitForFunction` with `document.querySelectorAll` for count polling
- `.all()` + `for...of` loop to enumerate DOM elements
- `.count()` for list length
- Named CSS class selectors (`.pattern-section .pattern-chip`) rather than IDs

**Imports pattern** (`src/e2e/tests/autoqueue.page.ts` lines 1-3):
```typescript
import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';
```

**Class skeleton pattern** (`src/e2e/tests/autoqueue.page.ts` lines 5-9):
```typescript
export class AutoQueuePage extends App {
    constructor(page: Page) {
        super(page);
    }
```

**navigateTo() with explicit waitFor pattern** (`src/e2e/tests/autoqueue.page.ts` lines 11-15):
```typescript
async navigateTo() {
    await this.page.goto(Paths.SETTINGS);
    // Wait for the settings page to load with the AutoQueue pattern section
    await this.page.locator('.pattern-section').waitFor({ state: 'visible' });
}
```
Apply to dashboard: replace `.pattern-section` with `.transfer-table tbody app-transfer-row` and add `first()` + `timeout: 30000`.

**waitForFunction count-polling pattern** (`src/e2e/tests/autoqueue.page.ts` lines 17-24):
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
Apply to dashboard: replace selector with `.transfer-table tbody app-transfer-row`, rename method `waitForAtLeastFileCount`, keep `>=` comparison and `{ timeout }` parameter.

**Row enumeration with .all() + loop pattern** (`src/e2e/tests/autoqueue.page.ts` lines 26-29):
```typescript
async getPatterns(): Promise<string[]> {
    const elements = await this.page.locator('.pattern-section .pattern-chip .pattern-chip-text').all();
    return Promise.all(elements.map(elm => elm.innerHTML()));
}
```
Apply to dashboard `getFiles()`: use `.all()` to enumerate `app-transfer-row`, then for each row read child locators for `.file-name`, `.status-badge`, `td.cell-size`. Use `textContent()` (not `innerHTML()`), `.trim()`, and em-dash normalization.

**New selectors to use in dashboard.page.ts rewrite** (source: RESEARCH.md verified against transfer-table.component.html and transfer-row.component.html):

```typescript
// navigateTo — wait for first row
await this.page.locator('.transfer-table tbody app-transfer-row').first()
    .waitFor({ state: 'visible', timeout: 30000 });

// waitForAtLeastFileCount — count rows
document.querySelectorAll('.transfer-table tbody app-transfer-row').length >= expectedCount

// getFiles — enumerate rows and read cells
const rowElements = await this.page.locator('.transfer-table tbody app-transfer-row').all();
// per row:
const name    = (await row.locator('td.cell-name .file-name').textContent() || '').trim();
const statusText = (await row.locator('td.cell-status .status-badge').textContent() || '').trim();
const status  = statusText === '\u2014' ? '' : statusText;  // em-dash DEFAULT → ''
const size    = (await row.locator('td.cell-size').textContent() || '').trim();

// getFileName — single row name
const name = (await this.page.locator('.transfer-table tbody app-transfer-row')
    .nth(index).locator('td.cell-name .file-name').textContent() || '').trim();
```

**Methods to REMOVE** (no analog in new markup — these DOM structures no longer exist):
- `selectFile(index)` — no per-row click produces a visible actions bar
- `isFileActionsVisible(index)` — `app-file-actions-bar` not in `files-page.component.html`
- `getFileActions(index)` — same reason
- `FileActionButtonState` interface — unused after above removals

---

### `src/e2e/tests/dashboard.page.spec.ts` (test, request-response)

**Analog:** `src/e2e/tests/autoqueue.page.spec.ts` (for structure) and current `dashboard.page.spec.ts` (for test intent)

**Test structure pattern** (`src/e2e/tests/dashboard.page.spec.ts` lines 1-10):
```typescript
import { test, expect } from '@playwright/test';
import { DashboardPage, FileInfo } from './dashboard.page';

test.describe('Testing dashboard page', () => {
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });
```
Keep this structure unchanged — it is already correct.

**Test to keep unchanged:**
```typescript
// src/e2e/tests/dashboard.page.spec.ts lines 12-16
test('should have Dashboard nav link active', async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    const activeLink = await dashboardPage.getActiveNavLink();
    expect(activeLink).toBe('Dashboard');
});
```
This test uses `App.getActiveNavLink()` which targets `#top-nav .nav-link.active` — unchanged nav markup, test stays valid.

**Golden data test — update size format** (`src/e2e/tests/dashboard.page.spec.ts` lines 18-35):
```typescript
// OLD golden (broken — uses OLD size format "0% — 0 B of 840 KB")
{ name: 'áßç déÀ.mp4', status: '', size: '0% — 0 B of 840 KB' },

// NEW golden (FileSizePipe precision:1 from td.cell-size)
{ name: 'áßç déÀ.mp4', status: '', size: '840 KB' },
{ name: 'clients.jpg', status: '', size: '36.5 KB' },
{ name: 'crispycat', status: '', size: '1.53 MB' },
{ name: 'documentation.png', status: '', size: '8.88 KB' },
{ name: 'goose', status: '', size: '2.78 MB' },
{ name: 'illusion.jpg', status: '', size: '81.5 KB' },
{ name: 'joke', status: '', size: '168 KB' },
{ name: 'testing.gif', status: '', size: '8.95 MB' },
{ name: 'üæÒ', status: '', size: '70.8 KB' },
```
Note: Exact values must be confirmed at test-run time since `FileSizePipe` output depends on runtime precision.

**Tests to REMOVE or skip** (reference non-existent `app-file-actions-bar`):
- `'should show and hide action buttons on select'` (lines 37-49) — `app-file-actions-bar` not rendered
- `'should show action buttons for most recent file selected'` (lines 51-66) — same
- `'should have all the action buttons'` (lines 68-79) — same
- `'should have Queue action enabled for Default state'` (lines 81-90) — same
- `'should have Stop action disabled for Default state'` (lines 92-101) — same

**Preferred skip pattern** (copy from Playwright skip convention used in prior E2E fixes):
```typescript
test.skip('should show and hide action buttons on select', async ({ page }) => {
    // Skipped: app-file-actions-bar no longer rendered in v1.1.0 dashboard
    // See: files-page.component.html — only app-transfer-table is present
});
```

---

### `src/e2e/tests/bulk-actions.spec.ts` (test, request-response)

**No viable analog.** The bulk-selection UI (`app-file-list` with `.bulk-actions-bar`, header checkbox, per-row `.checkbox`) is not rendered at any route in v1.1.0. All selectors in this file are broken.

**Pattern to apply — mass test.skip** (retire in place):
```typescript
// Wrap entire describe block or mark each test:
test.skip('1.1 - clicking checkbox on single file row selects it', async () => {
    // Skipped: bulk-selection UI (app-file-list) not rendered on /dashboard in v1.1.0
    // app-transfer-table is a read-only table with no checkboxes
});
```
Alternative: add `test.skip` to the outer `test.describe` block which skips all contained tests:
```typescript
test.describe('Bulk File Actions', () => {
    test.skip(true, 'Bulk-selection UI (app-file-list) not rendered at /dashboard in v1.1.0');
    // ... rest of tests remain as documentation
```

---

## Shared Patterns

### Base Class (App) — unchanged
**Source:** `src/e2e/tests/app.ts` lines 1-22
**Apply to:** All page objects (no change needed)

```typescript
import { Page } from '@playwright/test';

export class App {
    constructor(protected page: Page) {}

    async getActiveNavLink(): Promise<string> {
        return this.page.locator('#top-nav .nav-link.active').innerText();
    }
}
```
`DashboardPage extends App` — keep as-is. `App.getActiveNavLink()` uses `#top-nav .nav-link.active` which is still valid.

### waitFor({ state: 'visible' }) — preferred wait pattern
**Source:** `src/e2e/tests/autoqueue.page.ts` line 14 and `src/e2e/tests/dashboard.page.ts` line 24
**Apply to:** `navigateTo()` in `dashboard.page.ts`

```typescript
await this.page.locator(selector).first().waitFor({ state: 'visible', timeout: 30000 });
```

### waitForFunction with querySelectorAll — preferred count-polling pattern
**Source:** `src/e2e/tests/autoqueue.page.ts` lines 18-24 and `src/e2e/tests/dashboard.page.ts` lines 30-37
**Apply to:** `waitForAtLeastFileCount()` in `dashboard.page.ts`

```typescript
await this.page.waitForFunction(
    (expectedCount) => {
        const rows = document.querySelectorAll('SELECTOR');
        return rows.length >= expectedCount;
    },
    count,
    { timeout }
);
```

### textContent() + trim() normalization — preferred text extraction
**Source:** `src/e2e/tests/dashboard.page.ts` lines 46-52 (existing pattern, retain in rewrite)
**Apply to:** `getFiles()` cell reads in `dashboard.page.ts`

```typescript
const value = (await elm.locator('SELECTOR').textContent() || '').trim();
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/e2e/tests/bulk-actions.spec.ts` | test | request-response | All selectors target `app-file-list` which is not rendered at any route in v1.1.0. No equivalent bulk-selection UI exists in the new markup to write analogs against. |

---

## Metadata

**Analog search scope:** `src/e2e/tests/`
**Files scanned:** 9 (app.ts, app.spec.ts, dashboard.page.ts, dashboard.page.spec.ts, bulk-actions.spec.ts, settings.page.ts, settings.page.spec.ts, about.page.ts, autoqueue.page.ts)
**Pattern extraction date:** 2026-04-15
