# Phase 77: Deferred Playwright E2E (Phases 72 + 73) - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 3 (1 new, 2 modified)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/e2e/tests/fixtures/seed-state.ts` (NEW) | fixture (module-scoped seed helpers) | request-response (HTTP command dispatch) | `src/e2e/tests/settings.page.ts` (`enableSonarr`, `setSonarrUrl` — same `page.request.*` + ok-check + error-throw convention) | role-match (fixture vs page-object, but same HTTP call shape) |
| `src/e2e/tests/dashboard.page.ts` (MODIFIED) | page-object | request-response (DOM query/action) | self (existing methods at lines 53-93) + `src/e2e/tests/autoqueue.page.ts` (`waitForPatternsToLoad` polling pattern) | exact (extending the same file) |
| `src/e2e/tests/dashboard.page.spec.ts` (MODIFIED) | spec | event-driven (Playwright test runner) | self (existing 11 tests) + `src/e2e/tests/settings-error.spec.ts` (shared `let` + `beforeEach` pattern) | exact (extending the same file) |

## Pattern Assignments

### `src/e2e/tests/fixtures/seed-state.ts` (NEW, fixture, request-response)

**Closest analog:** `src/e2e/tests/settings.page.ts` — uses `page.request.*` against `/server/*` endpoints with ok-check + error-throw. Only file in the repo that HTTP-drives the backend from a Playwright test.

**Import pattern** (mirror `settings.page.ts:1` for Playwright types; fixture is not a class so import only `Page`):
```typescript
// settings.page.ts line 1 — import Page type only
import { Page } from '@playwright/test';
```

For seed-state.ts, use `type`-only import since no runtime reference to Page:
```typescript
import type { Page } from '@playwright/test';
```

**HTTP call + error-throw pattern** (copy from `settings.page.ts` lines 14-21):
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

**Transposition for Phase 77** — seed helpers are top-level `export async function` (not methods), take `page: Page` as first arg, and use `post`/`delete` verbs matching the 5 backend endpoints listed at `controller.py:66-72`:
```typescript
export async function queueFile(page: Page, name: string): Promise<void> {
    const res = await page.request.post(`/server/command/queue/${encodeURIComponent(name)}`);
    if (!res.ok()) {
        throw new Error(`queueFile(${name}) failed: ${res.status()} ${await res.text()}`);
    }
}
```

**URL encoding pattern** (copy from `settings.page.ts` lines 25, 34):
```typescript
`/server/config/set/sonarr/sonarr_url/${encodeURIComponent(url)}`
```
All seed helpers must wrap `name` in `encodeURIComponent` — harness uses Unicode filenames (`áßç déÀ.mp4`, `üæÒ`).

**Status-polling pattern** (copy DOM locator shape from `dashboard.page.ts` lines 53-58):
```typescript
getRowCheckbox(fileName: string): Locator {
    const row = this.page.locator('.transfer-table tbody app-transfer-row', {
        has: this.page.locator('td.cell-name .file-name', { hasText: new RegExp(`^${this._escapeRegex(fileName)}$`) })
    });
    return row.locator('td.cell-checkbox input.ss-checkbox');
}
```
Seed helper's internal `waitForBadge(page, name, label, timeout)` reuses this `has:` chaining, swapping the final `.cell-checkbox input` target for `td.cell-status .status-badge` + `.filter({ hasText: label }).waitFor({ timeout })`.

**Typed exports shape** — seed module exports a `SeedTarget` union, a `SeedPlanItem` interface, and top-level async functions (not a class). This diverges from the page-object convention (which uses classes); justified because there is no DOM state and no `this.page` to retain between calls — the `Page` is passed explicitly to each call.

---

### `src/e2e/tests/dashboard.page.ts` (MODIFIED, page-object, request-response)

**Closest analog:** self — extending the existing class. 9 new methods follow the exact style of the 9 existing ones at lines 53-93.

**Existing Locator-returning helper pattern** (lines 53-58, 60-62, 64-66, 68-70, 72-74, 76-78) — new `getStatusBadge`, `getEmptyRow`, `getToast`, `getClearSelectionLink` must match this shape:
```typescript
getRowCheckbox(fileName: string): Locator {
    const row = this.page.locator('.transfer-table tbody app-transfer-row', {
        has: this.page.locator('td.cell-name .file-name', { hasText: new RegExp(`^${this._escapeRegex(fileName)}$`) })
    });
    return row.locator('td.cell-checkbox input.ss-checkbox');
}

getHeaderCheckbox(): Locator {
    return this.page.locator('.transfer-table thead th.col-checkbox input.ss-checkbox');
}

getActionBar(): Locator {
    return this.page.locator('app-bulk-actions-bar .bulk-actions-bar');
}

getActionButton(name: 'Queue' | 'Stop' | 'Extract' | 'Delete Local' | 'Delete Remote'): Locator {
    return this.page.locator('app-bulk-actions-bar').getByRole('button', { name, exact: true });
}

getSegmentButton(name: 'All' | 'Active' | 'Done' | 'Errors'): Locator {
    return this.page.locator('.segment-filters').getByRole('button', { name, exact: true });
}

getSubButton(name: 'Pending' | 'Syncing' | 'Queued' | 'Extracting' | 'Downloaded' | 'Extracted' | 'Failed' | 'Deleted'): Locator {
    return this.page.locator('.segment-filters button.btn-sub').getByText(name, { exact: true });
}
```

Conventions extracted from above:
- Literal-string-union types for bounded enum args (`'Queue' | 'Stop' | ...`), not plain `string`.
- Prefer `getByRole('button', { name, exact: true })` when the element is semantic; fall back to CSS class selectors (`button.btn-sub`) only when needed for disambiguation.
- Return `Locator` (no `Promise`) for pure element accessors; return `Promise<T>` only for methods that perform actions or read text.

**Existing action method pattern** (lines 80-89):
```typescript
async selectFileByName(fileName: string): Promise<void> {
    await this.getRowCheckbox(fileName).click();
}

async clearSelectionViaBar(): Promise<void> {
    const clearBtn = this.page.locator('app-bulk-actions-bar button.clear-btn');
    if (await clearBtn.isVisible()) {
        await clearBtn.click();
    }
}
```
Conventions: thin wrappers over existing Locator accessors; use `isVisible()` guards for idempotent operations (new `shiftClickFile`, `clickHeaderCheckbox`, `clickConfirmModalConfirm` follow this shape).

**Private regex-escape helper** (lines 91-93) — reuse for new `getStatusBadge(fileName)`:
```typescript
private _escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
```

**Polling pattern** (lines 25-35) — closest analog for new `waitForFileStatus`:
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
Note: `waitForFunction` is the established pattern for bulk DOM polling. For single-row status polling, prefer the simpler `locator.filter({ hasText }).waitFor({ timeout })` (per RESEARCH.md Pattern 2) — same timeout semantics, less code, no need to escape to `document.querySelectorAll`.

Also see `src/e2e/tests/autoqueue.page.ts` lines 16-24 for a second `waitForFunction` precedent with a named timeout default of 5000 — Phase 77 helpers should default to `10_000` (matches the CI `expect.timeout`).

**Method-naming conventions extracted from the existing class:**
- `getX()` — returns `Locator` (no await needed at call site)
- `getX(): Promise<T>` — returns value (e.g., `getFiles`, `getActiveNavLink`)
- `waitForX()` — polling / status transitions
- `clickX()` / `selectX()` / `clearX()` — imperative action wrappers
- `shiftClickFile`, `clickHeaderCheckbox`, `clickConfirmModalConfirm` follow `clickX` / `selectX` nomenclature.

---

### `src/e2e/tests/dashboard.page.spec.ts` (MODIFIED, spec, event-driven)

**Closest analog:** self — 11 existing tests at lines 6-111 establish the describe/beforeEach/test shape. `src/e2e/tests/settings-error.spec.ts` is the best analog for the `let dashboardPage` + `beforeEach` + `afterEach` cleanup shape used for stateful tests.

**Imports pattern** (lines 1-2):
```typescript
import { test, expect } from '@playwright/test';
import { DashboardPage, FileInfo } from './dashboard.page';
```
New imports for Phase 77 will add:
```typescript
import { seedMultiple } from './fixtures/seed-state';
```

**Top-level describe + shared instance pattern** (lines 6-12):
```typescript
test.describe('Testing dashboard page', () => {
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });
```

**Nested describe option** — existing file has one top-level describe. Phase 77's new UAT-01 and UAT-02 blocks can either sit as **sibling top-level describes** (recommended — cleaner for `beforeAll` scoping) or as **nested inner describes** (tighter grouping but shared-state semantics get muddier). Prefer siblings because each new describe needs its own `beforeAll` seed flow; a nested inner describe inherits the outer `beforeEach`'s non-seeded navigation which may race the seed.

**beforeAll pattern** — no existing `beforeAll` in this file; closest precedent is `settings-error.spec.ts` which uses `beforeEach` + `afterEach` for stateful setup. New pattern for Phase 77:
```typescript
test.describe.serial('UAT-01: selection and bulk bar', () => {
    let dashboardPage: DashboardPage;

    test.beforeAll(async ({ browser }) => {
        const ctx = await browser.newContext();
        const page = await ctx.newPage();
        const dash = new DashboardPage(page);
        await dash.navigateTo();
        await seedMultiple(page, [
            { file: 'clients.jpg', target: 'DELETED' },
            { file: 'documentation.png', target: 'DOWNLOADED' },
            { file: 'illusion.jpg', target: 'STOPPED' },
        ]);
        await ctx.close();
    });

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });

    // ...15 new specs land here, destructive-last...
});
```
`test.describe.serial()` is the right primitive per RESEARCH.md A3: technically redundant given `workers: 1, fullyParallel: false` but makes destructive-last contract explicit.

**Test body patterns:**

1. **Visible/not-visible assertion** (lines 39-47) — reuse for bulk-bar visibility specs:
```typescript
test('should show and hide action buttons on select', async () => {
    await expect(dashboardPage.getActionBar()).not.toBeVisible();

    await dashboardPage.selectFileByName(TEST_FILE);
    await expect(dashboardPage.getActionBar()).toBeVisible();

    await dashboardPage.selectFileByName(TEST_FILE);
    await expect(dashboardPage.getActionBar()).not.toBeVisible();
});
```

2. **Text-assertion on selection-label** (lines 49-55) — reuse for multi-select count specs:
```typescript
test('should show action buttons for most recent file selected', async ({ page }) => {
    await dashboardPage.selectFileByName(TEST_FILE);
    await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('1 selected');

    await dashboardPage.selectFileByName('goose');
    await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('2 selected');
});
```

3. **Enabled/disabled button assertion** (lines 67-75) — reuse for FIX-01 union spec:
```typescript
test('should have Queue action enabled for Default state', async () => {
    await dashboardPage.selectFileByName(TEST_FILE);
    await expect(dashboardPage.getActionButton('Queue')).toBeEnabled();
});

test('should have Stop action disabled for Default state', async () => {
    await dashboardPage.selectFileByName(TEST_FILE);
    await expect(dashboardPage.getActionButton('Stop')).toBeDisabled();
});
```

4. **URL-assertion pattern** (line 98) — reuse verbatim for UAT-02 URL round-trip specs:
```typescript
await expect(page).toHaveURL(/[?&]segment=done(&|$)/);
```
For sub round-trip, pattern extends to `/[?&]segment=errors&sub=deleted(&|$)/`.

5. **URL fallback pattern** (lines 101-110) — reference for behavior NOT to duplicate (invalid-value case already covered):
```typescript
test('should silently fall back to All and sanitize URL when ?segment= is invalid (D-11)', async ({ page }) => {
    await page.goto('/dashboard?segment=garbage');
    await page.locator('.segment-filters').waitFor({ state: 'visible', timeout: 30000 });

    await expect(dashboardPage.getSegmentButton('All')).toHaveClass(/(^|\s)active(\s|$)/);
    await expect(page).not.toHaveURL(/segment=garbage/);
});
```

6. **Order-independent comparison pattern** (lines 33-36) — reuse for status-filter row-list assertions:
```typescript
const byName = (a: FileInfo, b: FileInfo) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
expect([...files].sort(byName)).toEqual([...golden].sort(byName));
```

7. **Shared constant at file top** (line 4):
```typescript
const TEST_FILE = 'clients.jpg';
```
Phase 77 may add a few more file-name constants (e.g., `const DELETED_FILE = 'clients.jpg';` for the FIX-01 fixture) for readability.

---

## Shared Patterns

### Playwright Page + request context
**Source:** `src/e2e/tests/settings.page.ts:15` and all other `page.request.*` call sites
**Apply to:** `src/e2e/tests/fixtures/seed-state.ts`
```typescript
const response = await this.page.request.get('/server/config/set/sonarr/enabled/true');
if (!response.ok()) {
    throw new Error(`enableSonarr failed: ${response.status()} ${response.statusText()}`);
}
```
**Key insight:** `page.request.*` carries no `Authorization` header and the harness backend accepts that (RESEARCH.md Open Question 1). No auth plumbing needed. `baseURL` from `playwright.config.ts:19` (`http://myapp:8800`) is prepended automatically to relative paths.

### Locator-chain row lookup by filename
**Source:** `src/e2e/tests/dashboard.page.ts:53-58` (`getRowCheckbox`)
**Apply to:** New `getStatusBadge` helper on `DashboardPage`; internal `waitForBadge` in `seed-state.ts`
```typescript
const row = this.page.locator('.transfer-table tbody app-transfer-row', {
    has: this.page.locator('td.cell-name .file-name', {
        hasText: new RegExp(`^${this._escapeRegex(fileName)}$`)
    })
});
return row.locator('td.cell-checkbox input.ss-checkbox');
```
**Key insight:** Anchor-both-ends regex (`^...$`) prevents prefix collisions (e.g., `joke` vs `joke.png`). Always escape via `_escapeRegex` because harness fixtures include `.` and other regex metacharacters.

### URL-encoded path parameter
**Source:** `src/e2e/tests/settings.page.ts:25` — `encodeURIComponent(url)` inside a template literal
**Apply to:** Every seed endpoint URL in `seed-state.ts`
```typescript
`/server/config/set/sonarr/sonarr_url/${encodeURIComponent(url)}`
```

### Literal-string-union types over plain string
**Source:** `src/e2e/tests/dashboard.page.ts:68-77` (`getActionButton`, `getSegmentButton`, `getSubButton`)
**Apply to:** `SeedTarget` type in `seed-state.ts`; `variant` arg on new `getToast(variant?)` helper
```typescript
getActionButton(name: 'Queue' | 'Stop' | 'Extract' | 'Delete Local' | 'Delete Remote'): Locator { ... }
```
**Transposition:** `export type SeedTarget = 'DOWNLOADED' | 'STOPPED' | 'DELETED';`

### test.beforeEach instance-init
**Source:** `src/e2e/tests/dashboard.page.spec.ts:9-12` and `src/e2e/tests/settings-error.spec.ts:5-10`
**Apply to:** Both new UAT-01 and UAT-02 describe blocks
```typescript
let dashboardPage: DashboardPage;

test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateTo();
});
```
**Note on `settings-error.spec.ts:12-14`** — shows `afterEach` cleanup pattern for destructive tests, but Phase 77 explicitly rejects per-test cleanup (D-07); omit.

### expect(locator).toHaveText / toContainText
**Source:** `src/e2e/tests/dashboard.page.spec.ts:51, 54` (exact) and RESEARCH.md recommendation (partial for toasts)
**Apply to:**
- Selection-count: `toHaveText('2 selected')` (exact — stable format)
- Toast text: `toContainText('Queued')` (partial — `Localization.Bulk.SUCCESS_*` is count-dependent)

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | All three files have strong analogs — two are self-referential (extending same file), one mirrors the `page.request.*` shape from `settings.page.ts`. |

## Metadata

**Analog search scope:** `src/e2e/tests/` (all files: `app.ts`, `about.page.*`, `app.spec.ts`, `autoqueue.page.*`, `dashboard.page.*`, `settings-error.spec.ts`, `settings.page.*`), `src/e2e/playwright.config.ts`, `src/e2e/urls.ts`, `src/e2e/package.json`, `src/angular/src/app/pages/files/transfer-row.component.ts`
**Files scanned:** 12
**Pattern extraction date:** 2026-04-20

**Key observations:**
1. The `src/e2e/tests/fixtures/` directory does NOT yet exist — Wave 1 must `mkdir` before writing `seed-state.ts`.
2. `page.request.*` usage in `settings.page.ts` confirms no auth header needed — seed helpers carry no `Authorization` bearer.
3. `src/e2e/urls.ts` sits at `src/e2e/urls.ts` (not `src/e2e/tests/urls.ts`) — page objects import via `'../urls'` relative path. Seed-state module at `src/e2e/tests/fixtures/seed-state.ts` does not need `Paths` (uses absolute `/server/command/*` paths directly), so no import-path adjustment needed for the two-levels-up traversal.
4. Existing `DashboardPage` method order is: navigation → data-read → Locator accessors → action wrappers → private helpers. New methods should land in their corresponding section, not appended at the end.
5. No existing `test.beforeAll` in any spec file — Phase 77 introduces this primitive. `test.describe.serial()` is also new; both are standard Playwright APIs and do not require config changes.
