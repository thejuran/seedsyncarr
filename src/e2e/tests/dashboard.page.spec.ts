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
            { name: 'áßç déÀ.mp4', status: '', size: '840 KB' },
            { name: 'clients.jpg', status: '', size: '36.5 KB' },
            { name: 'crispycat', status: '', size: '1.53 MB' },
            { name: 'documentation.png', status: '', size: '8.88 KB' },
            { name: 'goose', status: '', size: '2.78 MB' },
            { name: 'illusion.jpg', status: '', size: '81.5 KB' },
            { name: 'joke', status: '', size: '168 KB' },
            { name: 'testing.gif', status: '', size: '8.95 MB' },
            { name: 'üæÒ', status: '', size: '70.8 KB' },
        ];
        await dashboardPage.waitForAtLeastFileCount(golden.length);
        const files = await dashboardPage.getFiles();
        expect(files).toEqual(golden);
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
