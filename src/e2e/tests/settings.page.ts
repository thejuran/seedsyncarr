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
}