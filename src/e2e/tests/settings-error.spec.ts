import { test, expect } from './fixtures/csp-listener';
import { SettingsPage } from './settings.page';

test.describe('Settings page error states', () => {
    let settingsPage: SettingsPage;

    test.beforeEach(async ({ page }) => {
        settingsPage = new SettingsPage(page);
        await settingsPage.navigateTo();
        await settingsPage.disableSonarr();
    });

    test.afterEach(async () => {
        await settingsPage.disableSonarr().catch((e) => {
            console.warn('[afterEach] disableSonarr cleanup failed (non-fatal):', e);
        });
    });

    test('should show error when Sonarr connection fails', async () => {
        await settingsPage.enableSonarr();
        await settingsPage.setSonarrUrl('http://nonexistent.invalid:8989');
        // NOTE: value appears in access logs — use synthetic strings only
        await settingsPage.setSonarrApiKey('test-FAKE-not-real-0000');

        await settingsPage.navigateTo();

        await settingsPage.clickTestSonarrConnection();

        const result = await settingsPage.getSonarrTestResult();
        expect(result.isDanger).toBe(true);
        expect(result.text.length).toBeGreaterThan(0);
    });
});
