import { test, expect } from './fixtures/csp-listener';
import { SettingsPage } from './settings.page';

test.describe('Settings page form fields', () => {
    let settingsPage: SettingsPage;
    // Store original values for afterEach restoration
    let originalAddress: string;
    let originalSshKey: boolean;
    let originalScanInterval: string;

    test.beforeEach(async ({ page }) => {
        settingsPage = new SettingsPage(page);
        await settingsPage.navigateTo();
        // Capture original values before each test modifies them
        originalAddress = await settingsPage.getServerAddressValue();
        originalSshKey = await settingsPage.getSshKeyChecked();
        originalScanInterval = await settingsPage.getRemoteScanIntervalValue();
    });

    test.afterEach(async () => {
        // D-12: restore original config values to prevent cross-test pollution
        // Use .catch(() => {}) per settings-error.spec.ts pattern
        await settingsPage.setRemoteAddress(originalAddress).catch(() => {});
        await settingsPage.setUseSshKey(originalSshKey).catch(() => {});
        await settingsPage.setRemoteScanInterval(originalScanInterval).catch(() => {});
    });

    // --- Text field: Server Address (D-07, D-11) ---

    test('should display Server Address field with current value', async () => {
        // D-07: representative sample -- text field
        const input = settingsPage.getServerAddressInput();
        await expect(input).toBeVisible();
        // Field should have some value (may be empty string in test harness)
        const value = await settingsPage.getServerAddressValue();
        expect(typeof value).toBe('string');
    });

    test('should persist Server Address via API-set and reload', async () => {
        // D-11: API-set -> reload -> verify UI pattern
        const testAddress = 'e2e-test-host.example.com';
        await settingsPage.setRemoteAddress(testAddress);
        await settingsPage.navigateTo();
        const displayed = await settingsPage.getServerAddressValue();
        expect(displayed).toBe(testAddress);
    });

    // --- Checkbox: SSH key auth (D-07, D-11) ---

    test('should display SSH key auth checkbox', async () => {
        // D-07: representative sample -- checkbox toggle
        const checkbox = settingsPage.getSshKeyCheckbox();
        await expect(checkbox).toBeVisible();
    });

    test('should persist SSH key auth toggle via API-set and reload', async () => {
        // D-11: API-set -> reload -> verify UI pattern
        const currentValue = await settingsPage.getSshKeyChecked();
        const newValue = !currentValue;
        await settingsPage.setUseSshKey(newValue);
        await settingsPage.navigateTo();
        const displayed = await settingsPage.getSshKeyChecked();
        expect(displayed).toBe(newValue);
    });

    // --- Interval field: Remote Scan Interval (D-07, D-11) ---

    test('should display Remote Scan Interval field', async () => {
        // D-07: representative sample -- interval/text field
        const input = settingsPage.getRemoteScanIntervalInput();
        await expect(input).toBeVisible();
    });

    test('should persist Remote Scan Interval via API-set and reload', async () => {
        // D-11: API-set -> reload -> verify UI pattern
        const testInterval = '45000';
        await settingsPage.setRemoteScanInterval(testInterval);
        await settingsPage.navigateTo();
        const displayed = await settingsPage.getRemoteScanIntervalValue();
        expect(displayed).toBe(testInterval);
    });

    // --- Floating save bar confirmation (D-09, D-10) ---

    test('should show Changes Saved after UI field edit', async () => {
        // D-09: Assert floating save bar "Changes Saved" as E2E-verifiable proof
        // of the onSetConfig -> /server/config/set -> config update -> floating bar round-trip
        // D-10: UI-to-UI round-trip -- fill via UI, wait for confirmation
        const testAddress = 'e2e-roundtrip-test.example.com';
        await settingsPage.fillServerAddress(testAddress);
        // OptionComponent has a 1000ms debounce. The "Changes Saved" text appears
        // after debounce fires + API call completes. 5s timeout covers both.
        await expect(settingsPage.getFloatingSaveBar())
            .toContainText('Changes Saved', { timeout: 5000 });
    });

    test('should persist value after UI edit and page reload', async () => {
        // D-10: Full UI-to-UI round-trip -- fill -> save confirmation -> reload -> verify
        const testAddress = 'e2e-persist-test.example.com';
        await settingsPage.fillServerAddress(testAddress);
        // Wait for "Changes Saved" to confirm API persistence succeeded
        await expect(settingsPage.getFloatingSaveBar())
            .toContainText('Changes Saved', { timeout: 5000 });
        // Reload page and verify value was persisted to disk
        await settingsPage.navigateTo();
        const displayed = await settingsPage.getServerAddressValue();
        expect(displayed).toBe(testAddress);
    });
});
