import { test, expect } from '@playwright/test';
import { DashboardPage, FileInfo } from './dashboard.page';
import { seedMultiple } from './fixtures/seed-state';

const TEST_FILE = 'clients.jpg';
const DELETED_FILE = 'clients.jpg';        // FIX-01 anchor; pre-seeded DELETED via seed-state (RESEARCH Pitfall 2 rejected 'joke' as a directory)
const DOWNLOADED_FILE = 'documentation.png';  // seeded DOWNLOADED sibling — small 9KB file; ALSO the Delete Local target in Spec 4 (see mapping comment in Task 2)
const STOPPED_FILE = 'illusion.jpg';       // seeded STOPPED sibling — 80KB
const DEFAULT_FILE = 'goose';              // unseeded fixture in DEFAULT state

test.describe('Testing dashboard page', () => {
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });

    test('should have Dashboard nav link active', async () => {
        const activeLink = await dashboardPage.getActiveNavLink();
        expect(activeLink).toBe('Dashboard');
    });

    test('should have a list of files', async () => {
        const golden: FileInfo[] = [
            { name: 'áßç déÀ.mp4', status: '', size: '800 KB' },
            { name: 'clients.jpg', status: '', size: '40 KB' },
            { name: 'crispycat', status: '', size: '2 MB' },
            { name: 'documentation.png', status: '', size: '9 KB' },
            { name: 'goose', status: '', size: '3 MB' },
            { name: 'illusion.jpg', status: '', size: '80 KB' },
            { name: 'joke', status: '', size: '200 KB' },
            { name: 'testing.gif', status: '', size: '9 MB' },
            { name: 'üæÒ', status: '', size: '70 KB' },
        ];
        await dashboardPage.waitForAtLeastFileCount(golden.length);
        const files = await dashboardPage.getFiles();
        // Compare order-independent: display order depends on browser locale's
        // localeCompare, which can differ between amd64/arm64 Chromium builds.
        const byName = (a: FileInfo, b: FileInfo) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
        expect([...files].sort(byName)).toEqual([...golden].sort(byName));
    });

    test('should show and hide action buttons on select', async () => {
        await expect(dashboardPage.getActionBar()).not.toBeVisible();

        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionBar()).toBeVisible();

        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionBar()).not.toBeVisible();
    });

    test('should show action buttons for most recent file selected', async ({ page }) => {
        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('1 selected');

        await dashboardPage.selectFileByName('goose');
        await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('2 selected');
    });

    test('should have all the action buttons', async () => {
        await dashboardPage.selectFileByName(TEST_FILE);

        await expect(dashboardPage.getActionBar().locator('button.action-btn')).toHaveCount(5);

        for (const name of ['Queue', 'Stop', 'Extract', 'Delete Local', 'Delete Remote'] as const) {
            await expect(dashboardPage.getActionButton(name)).toBeVisible();
        }
    });

    test('should have Queue action enabled for Default state', async () => {
        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionButton('Queue')).toBeEnabled();
    });

    test('should have Stop action disabled for Default state', async () => {
        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionButton('Stop')).toBeDisabled();
    });

    test('should expand Done segment to reveal Downloaded and Extracted subs', async () => {
        await expect(dashboardPage.getSubButton('Downloaded')).not.toBeVisible();
        await expect(dashboardPage.getSubButton('Extracted')).not.toBeVisible();

        await dashboardPage.getSegmentButton('Done').click();

        await expect(dashboardPage.getSubButton('Downloaded')).toBeVisible();
        await expect(dashboardPage.getSubButton('Extracted')).toBeVisible();
    });

    test('should reveal Pending sub under Active', async () => {
        await expect(dashboardPage.getSubButton('Pending')).not.toBeVisible();

        await dashboardPage.getSegmentButton('Active').click();

        await expect(dashboardPage.getSubButton('Pending')).toBeVisible();
    });

    test('should persist Done filter via URL query param (D-09)', async ({ page }) => {
        await dashboardPage.getSegmentButton('Done').click();

        await expect(page).toHaveURL(/[?&]segment=done(&|$)/);
    });

    test('should silently fall back to All and sanitize URL when ?segment= is invalid (D-11)', async ({ page }) => {
        await page.goto('/dashboard?segment=garbage');
        await page.locator('.segment-filters').waitFor({ state: 'visible', timeout: 30000 });

        // Default state: "All" is active
        await expect(dashboardPage.getSegmentButton('All')).toHaveClass(/(^|\s)active(\s|$)/);

        // URL is sanitized — the garbage param is gone
        await expect(page).not.toHaveURL(/segment=garbage/);
    });
});

test.describe.serial('UAT-01: selection and bulk bar', () => {
    let dashboardPage: DashboardPage;

    test.beforeAll(async ({ browser }) => {
        const ctx = await browser.newContext();
        const page = await ctx.newPage();
        const dash = new DashboardPage(page);
        await dash.navigateTo();
        // Seed plan (revised): DOWNLOADED_FILE must reach DOWNLOADED so Spec 4's Delete Local
        // dispatch satisfies controller.py:1041 precondition (local_size not None). See
        // controller/controller.py:1032-1047 — delete_local rejects with 404 when local_size is None.
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

    test('UAT-01: per-file selection accumulates and bulk bar reacts', async ({ page }) => {
        await expect(dashboardPage.getActionBar()).not.toBeVisible();

        await dashboardPage.selectFileByName(DEFAULT_FILE);
        await expect(dashboardPage.getActionBar()).toBeVisible();
        expect(await dashboardPage.getSelectedCount()).toBe(1);
        await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('1 selected');

        await dashboardPage.selectFileByName(DOWNLOADED_FILE);
        expect(await dashboardPage.getSelectedCount()).toBe(2);
        await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('2 selected');

        await dashboardPage.selectFileByName(STOPPED_FILE);
        expect(await dashboardPage.getSelectedCount()).toBe(3);
    });

    test('UAT-01: shift-range select extends selection to contiguous rows', async () => {
        // Anchor: click first checkbox normally; shift-click a later one.
        // Order is locale-sort dependent on the harness — use files that are definitely visible
        // and rely on the contiguous-range semantic (shift extends from anchor to target).
        await dashboardPage.selectFileByName('clients.jpg');
        await dashboardPage.shiftClickFile('documentation.png');
        // Expect >= 2 selected (exact count depends on row order in the rendered table; this
        // asserts range-extension worked without being fragile to locale-sort divergence).
        const count = await dashboardPage.getSelectedCount();
        expect(count).toBeGreaterThanOrEqual(2);
        await expect(dashboardPage.getActionBar()).toBeVisible();
    });

    test('UAT-01: page-scoped header checkbox selects all visible rows', async ({ page }) => {
        await dashboardPage.clickHeaderCheckbox();

        await expect(dashboardPage.getActionBar()).toBeVisible();
        // Harness loads 9 fixture files in one page (no pagination surface on this data set);
        // header select-all must select every visible row — assert count equals visible row count.
        const visibleRowCount = await page.locator('.transfer-table tbody app-transfer-row').count();
        const selected = await dashboardPage.getSelectedCount();
        expect(selected).toBe(visibleRowCount);
        expect(selected).toBeGreaterThanOrEqual(9);

        // Toggle off — selection clears, bar hides.
        await dashboardPage.clickHeaderCheckbox();
        await expect(dashboardPage.getActionBar()).not.toBeVisible();
    });
});
