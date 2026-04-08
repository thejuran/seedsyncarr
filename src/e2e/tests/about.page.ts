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
        return this.page.locator('#version').textContent() || '';
    }
}