import { test, expect } from '@playwright/test';
import { DashboardPage, FileInfo } from './dashboard.page';

const TEST_FILE = 'clients.jpg';

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
