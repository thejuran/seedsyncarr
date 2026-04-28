import { test, expect } from './fixtures/csp-listener';
import { LogsPage } from './logs.page';

test.describe('Testing logs page', () => {
    let logsPage: LogsPage;

    test.beforeEach(async ({ page }) => {
        logsPage = new LogsPage(page);
        await logsPage.navigateTo();
    });

    test('should have Logs nav link active', async ({ page }) => {
        const activeLink = await logsPage.getActiveNavLink();
        expect(activeLink).toBe('Logs');
    });

    test('should display all 5 level filter buttons', async () => {
        // D-01: verify all toolbar elements present
        const buttons = logsPage.getLevelButtons();
        await expect(buttons).toHaveCount(5);
        // Verify exact labels: ALL, INFO, WARN, ERROR, DEBUG
        await expect(buttons.nth(0)).toHaveText('ALL');
        await expect(buttons.nth(1)).toHaveText('INFO');
        await expect(buttons.nth(2)).toHaveText('WARN');
        await expect(buttons.nth(3)).toHaveText('ERROR');
        await expect(buttons.nth(4)).toHaveText('DEBUG');
    });

    test('should display search input', async () => {
        // D-01: search input present
        await expect(logsPage.getSearchInput()).toBeVisible();
    });

    test('should have auto-scroll active on load', async () => {
        // D-02: auto-scroll verified as DOM state only (class check, not scroll position)
        const btn = logsPage.getAutoScrollButton();
        await expect(btn).toBeVisible();
        await expect(btn).toHaveClass(/action-btn--active/);
    });

    test('should display clear and export buttons', async () => {
        // D-01: toolbar action buttons present
        await expect(logsPage.getClearButton()).toBeVisible();
        await expect(logsPage.getExportButton()).toBeVisible();
    });

    test('should render at least one log row from SSE', async () => {
        // D-04/D-05: Organic logs from the running harness are acceptable
        // for the page-load smoke assertion. The Docker compose stack
        // produces INFO-level log entries during scan cycles.
        // Wait with generous timeout for SSE delivery.
        // NOTE: this test does not run in stub/offline mode — the Docker compose
        // stack must be running with active scan cycles for logs to appear.
        await expect(logsPage.getLogRows().first()).toBeVisible({ timeout: 15000 });
    });

    test('should display status bar with log count', async () => {
        // D-01: status bar text visible
        await expect(logsPage.getStatusBar()).toBeVisible();
        // Wait for the status bar right section to show a log count.
        // In sequential execution the prior test already waited for the first log row,
        // so we wait on the status text directly rather than duplicating the row wait.
        await expect(logsPage.getStatusBarRight()).toContainText('logs indexed', { timeout: 15000 });
    });
});
