import { test, expect } from '@playwright/test';
import { DashboardPage, FileInfo } from './dashboard.page';

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

    // v1.1.0: app-file-actions-bar removed from dashboard — transfer-table is read-only
    test.skip('should show and hide action buttons on select', async () => {
        // Skipped: app-file-actions-bar not rendered in v1.1.0 dashboard (files-page uses app-transfer-table)
    });

    test.skip('should show action buttons for most recent file selected', async () => {
        // Skipped: app-file-actions-bar not rendered in v1.1.0 dashboard
    });

    test.skip('should have all the action buttons', async () => {
        // Skipped: app-file-actions-bar not rendered in v1.1.0 dashboard
    });

    test.skip('should have Queue action enabled for Default state', async () => {
        // Skipped: app-file-actions-bar not rendered in v1.1.0 dashboard
    });

    test.skip('should have Stop action disabled for Default state', async () => {
        // Skipped: app-file-actions-bar not rendered in v1.1.0 dashboard
    });
});
