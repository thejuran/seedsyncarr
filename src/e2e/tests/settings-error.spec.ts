import { test, expect } from '@playwright/test';
import { SettingsPage } from './settings.page';

test.describe('Settings page error states', () => {
    let settingsPage: SettingsPage;

    test.beforeEach(async ({ page }) => {
        settingsPage = new SettingsPage(page);
    });

    test.afterEach(async () => {
        await settingsPage.disableSonarr();
    });

    test('should show error when Sonarr connection fails', async ({ page }) => {
        await settingsPage.enableSonarr();
        await settingsPage.setSonarrUrl('http://nonexistent.invalid:8989');
        await settingsPage.setSonarrApiKey('fake-api-key-for-testing');

        await settingsPage.navigateTo();

        await settingsPage.clickTestSonarrConnection();

        const result = await settingsPage.getSonarrTestResult();
        expect(result.isDanger).toBe(true);
        expect(result.text.length).toBeGreaterThan(0);
    });
});
