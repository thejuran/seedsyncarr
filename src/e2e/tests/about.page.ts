import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class AboutPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.ABOUT);
    }

    async getVersion(): Promise<string> {
        const text = await this.page.locator('.version-badge').textContent() || '';
        // Extract version from "Version X.Y.Z (Stable)" format
        const match = text.match(/Version\s+([\d.]+)/);
        return match ? `v${match[1]}` : '';
    }
}