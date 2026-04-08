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
        await this.page.request.get(
            'http://myapp:8800/server/config/set/sonarr/enabled/true'
        );
    }

    async setSonarrUrl(url: string): Promise<void> {
        await this.page.request.get(
            `http://myapp:8800/server/config/set/sonarr/sonarr_url/${encodeURIComponent(url)}`
        );
    }

    async setSonarrApiKey(key: string): Promise<void> {
        await this.page.request.get(
            `http://myapp:8800/server/config/set/sonarr/sonarr_api_key/${encodeURIComponent(key)}`
        );
    }

    async clickTestSonarrConnection(): Promise<void> {
        const sonarrFieldset = this.page.locator('fieldset').filter({ has: this.page.locator('text=Sonarr URL') });
        await sonarrFieldset.locator('button:has-text("Test Connection")').click();
    }

    async getSonarrTestResult(): Promise<{ text: string; isDanger: boolean }> {
        const sonarrFieldset = this.page.locator('fieldset').filter({ has: this.page.locator('text=Sonarr URL') });
        const result = sonarrFieldset.locator('.test-result');
        await result.waitFor({ state: 'visible', timeout: 15000 });
        const text = await result.innerText();
        const isDanger = await result.evaluate(el => el.classList.contains('text-danger'));
        return { text, isDanger };
    }

    async disableSonarr(): Promise<void> {
        await this.page.request.get(
            'http://myapp:8800/server/config/set/sonarr/enabled/false'
        );
    }
}