import { test, expect } from '@playwright/test';
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