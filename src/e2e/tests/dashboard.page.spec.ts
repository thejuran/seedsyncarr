import { test, expect } from '@playwright/test';
import { DashboardPage, FileInfo } from './dashboard.page';

test.describe('Testing dashboard page', () => {
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });

    test('should have Dashboard nav link active', async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        const activeLink = await dashboardPage.getActiveNavLink();
        expect(activeLink).toBe('Dashboard');
    });

    test('should have a list of files', async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        const golden: FileInfo[] = [
            { name: 'áßç déÀ.mp4', status: '', size: '0% — 0 B of 840 KB' },
            { name: 'clients.jpg', status: '', size: '0% — 0 B of 36.5 KB' },
            { name: 'crispycat', status: '', size: '0% — 0 B of 1.53 MB' },
            { name: 'documentation.png', status: '', size: '0% — 0 B of 8.88 KB' },
            { name: 'goose', status: '', size: '0% — 0 B of 2.78 MB' },
            { name: 'illusion.jpg', status: '', size: '0% — 0 B of 81.5 KB' },
            { name: 'joke', status: '', size: '0% — 0 B of 168 KB' },
            { name: 'testing.gif', status: '', size: '0% — 0 B of 8.95 MB' },
            { name: 'üæÒ', status: '', size: '0% — 0 B of 70.8 KB' },
        ];
        // Wait for all files to load (incremental loading sends files one at a time)
        await dashboardPage.waitForAtLeastFileCount(golden.length);
        const files = await dashboardPage.getFiles();
        expect(files).toEqual(golden);
    });

    test('should show and hide action buttons on select', async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        // Wait for at least 2 files to load (we access index 1)
        await dashboardPage.waitForAtLeastFileCount(2);
        const actionsBar = page.locator('app-file-actions-bar .file-actions-bar');
        await expect(actionsBar).not.toBeVisible();
        await dashboardPage.selectFile(1);
        await expect(actionsBar).toBeVisible();
        // Extra delay before re-click to deselect (arm64/QEMU timing)
        await page.waitForTimeout(process.env.CI ? 500 : 100);
        await dashboardPage.selectFile(1);
        await expect(actionsBar).not.toBeVisible({ timeout: 5000 });
    });

    test('should show action buttons for most recent file selected', async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        // Wait for at least 3 files to load (we access index 1 and 2)
        await dashboardPage.waitForAtLeastFileCount(3);
        expect(await dashboardPage.isFileActionsVisible(1)).toBe(false);
        expect(await dashboardPage.isFileActionsVisible(2)).toBe(false);
        await dashboardPage.selectFile(1);
        expect(await dashboardPage.isFileActionsVisible(1)).toBe(true);
        expect(await dashboardPage.isFileActionsVisible(2)).toBe(false);
        await dashboardPage.selectFile(2);
        expect(await dashboardPage.isFileActionsVisible(1)).toBe(false);
        expect(await dashboardPage.isFileActionsVisible(2)).toBe(true);
        await dashboardPage.selectFile(2);
        expect(await dashboardPage.isFileActionsVisible(1)).toBe(false);
        expect(await dashboardPage.isFileActionsVisible(2)).toBe(false);
    });

    test('should have all the action buttons', async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        // Wait for at least 2 files to load (we access index 1)
        await dashboardPage.waitForAtLeastFileCount(2);
        const states = await dashboardPage.getFileActions(1);
        expect(states.length).toBe(5);
        expect(states[0].title).toBe('Queue');
        expect(states[1].title).toBe('Stop');
        expect(states[2].title).toBe('Extract');
        expect(states[3].title).toBe('Delete Local');
        expect(states[4].title).toBe('Delete Remote');
    });

    test('should have Queue action enabled for Default state', async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        // Wait for at least 2 files to load (we access index 1)
        await dashboardPage.waitForAtLeastFileCount(2);
        const files = await dashboardPage.getFiles();
        expect(files[1].status).toBe('');
        const states = await dashboardPage.getFileActions(1);
        expect(states[0].title).toBe('Queue');
        expect(states[0].isEnabled).toBe(true);
    });

    test('should have Stop action disabled for Default state', async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        // Wait for at least 2 files to load (we access index 1)
        await dashboardPage.waitForAtLeastFileCount(2);
        const files = await dashboardPage.getFiles();
        expect(files[1].status).toBe('');
        const states = await dashboardPage.getFileActions(1);
        expect(states[1].title).toBe('Stop');
        expect(states[1].isEnabled).toBe(false);
    });
});