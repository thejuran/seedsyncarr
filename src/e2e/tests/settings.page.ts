import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class SettingsPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
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
}
