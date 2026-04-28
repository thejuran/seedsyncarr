import { Page, Locator } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class SettingsPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo(): Promise<void> {
        await this.page.goto(Paths.SETTINGS);
    }

    async enableSonarr(): Promise<void> {
        const response = await this.page.request.get(
            '/server/config/set/sonarr/enabled/true'
        );
        if (!response.ok()) {
            throw new Error(`enableSonarr failed: ${response.status()} ${response.statusText()}`);
        }
    }

    async setSonarrUrl(url: string): Promise<void> {
        const response = await this.page.request.get(
            `/server/config/set/sonarr/sonarr_url/${encodeURIComponent(url)}`
        );
        if (!response.ok()) {
            throw new Error(`setSonarrUrl failed: ${response.status()} ${response.statusText()}`);
        }
    }

    // NOTE: the key value appears as a plain path segment in server access logs
    // because the backend config/set endpoint is GET-only. Always pass obviously-synthetic
    // strings (e.g. 'test-FAKE-not-real-0000') — never realistic-looking credentials.
    async setSonarrApiKey(key: string): Promise<void> {
        const response = await this.page.request.get(
            `/server/config/set/sonarr/sonarr_api_key/${encodeURIComponent(key)}`
        );
        if (!response.ok()) {
            throw new Error(`setSonarrApiKey failed: ${response.status()} ${response.statusText()}`);
        }
    }

    async clickTestSonarrConnection(): Promise<void> {
        const sonarrFieldset = this.page.locator('fieldset').filter({ has: this.page.getByText('Sonarr URL') });
        await sonarrFieldset.getByRole('button', { name: 'Test Connection' }).click();
    }

    async getSonarrTestResult(): Promise<{ text: string; isDanger: boolean }> {
        const sonarrFieldset = this.page.locator('fieldset').filter({ has: this.page.getByText('Sonarr URL') });
        const result = sonarrFieldset.locator('.test-result');
        await result.waitFor({ state: 'visible', timeout: 15000 });
        const text = await result.innerText();
        const isDanger = await result.evaluate(el => el.classList.contains('text-danger'));
        return { text, isDanger };
    }

    async disableSonarr(): Promise<void> {
        const response = await this.page.request.get(
            '/server/config/set/sonarr/enabled/false'
        );
        if (!response.ok()) {
            throw new Error(`disableSonarr failed: ${response.status()} ${response.statusText()}`);
        }
    }

    // --- Config API methods (API-set pattern per D-11) ---

    async setRemoteAddress(address: string): Promise<void> {
        const response = await this.page.request.get(
            `/server/config/set/lftp/remote_address/${encodeURIComponent(address)}`
        );
        if (!response.ok()) {
            throw new Error(`setRemoteAddress failed: ${response.status()} ${response.statusText()}`);
        }
    }

    async setUseSshKey(enabled: boolean): Promise<void> {
        const response = await this.page.request.get(
            `/server/config/set/lftp/use_ssh_key/${encodeURIComponent(String(enabled))}`
        );
        if (!response.ok()) {
            throw new Error(`setUseSshKey failed: ${response.status()} ${response.statusText()}`);
        }
    }

    async setRemoteScanInterval(ms: string): Promise<void> {
        const response = await this.page.request.get(
            `/server/config/set/controller/interval_ms_remote_scan/${encodeURIComponent(ms)}`
        );
        if (!response.ok()) {
            throw new Error(`setRemoteScanInterval failed: ${response.status()} ${response.statusText()}`);
        }
    }

    // --- UI locator methods ---

    getServerAddressInput(): Locator {
        // Server Address is the first app-option with label 'Server Address' in the Remote Server card
        return this.page.locator('app-option').filter({ hasText: 'Server Address' }).locator('input[type="text"]');
    }

    getSshKeyCheckbox(): Locator {
        // SSH key auth checkbox in the Remote Server card
        return this.page.locator('app-option').filter({ hasText: 'password-less key-based' }).locator('input[type="checkbox"]');
    }

    getRemoteScanIntervalInput(): Locator {
        // Remote Scan Interval in the File Discovery Polling card
        return this.page.locator('app-option').filter({ hasText: 'Remote Scan Interval' }).locator('input[type="text"]');
    }

    getFloatingSaveBar(): Locator {
        return this.page.locator('.floating-save-bar');
    }

    // --- UI interaction methods ---

    async fillServerAddress(address: string): Promise<void> {
        await this.getServerAddressInput().fill(address);
    }

    async getServerAddressValue(): Promise<string> {
        return this.getServerAddressInput().inputValue();
    }

    async getSshKeyChecked(): Promise<boolean> {
        return this.getSshKeyCheckbox().isChecked();
    }

    async getRemoteScanIntervalValue(): Promise<string> {
        return this.getRemoteScanIntervalInput().inputValue();
    }
}
