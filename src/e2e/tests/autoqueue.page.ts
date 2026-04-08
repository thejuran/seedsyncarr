import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class AutoQueuePage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.SETTINGS);
        // Wait for the settings page to load with the AutoQueue pattern section
        await this.page.locator('.pattern-section').waitFor({ state: 'visible' });
    }

    async waitForPatternsToLoad(expectedCount: number) {
        if (expectedCount > 0) {
            await this.page.waitForFunction(
                (expected) => document.querySelectorAll('.pattern-section .pattern-row').length >= expected,
                expectedCount,
                { timeout: 5000 }
            );
        }
    }

    async getPatterns(): Promise<string[]> {
        const elements = await this.page.locator('.pattern-section .pattern-row .pattern-text').all();
        return Promise.all(elements.map(elm => elm.innerHTML()));
    }

    async addPattern(pattern: string) {
        await this.page.locator('.pattern-add input').fill(pattern);
        await this.page.locator('.pattern-add .pattern-add-btn').click();
        // Wait for the pattern to appear in the list
        await this.page.locator(`.pattern-section .pattern-text:has-text("${pattern}")`).waitFor({ state: 'visible' });
    }

    async removePattern(index: number) {
        const countBefore = await this.page.locator('.pattern-section .pattern-row').count();
        await this.page.locator('.pattern-section .pattern-row').nth(index).locator('.pattern-remove-btn').click();
        await this.page.waitForFunction(
            (expected) => document.querySelectorAll('.pattern-section .pattern-row').length === expected,
            countBefore - 1
        );
    }

    async removeAllPatterns() {
        while ((await this.page.locator('.pattern-section .pattern-row').count()) > 0) {
            await this.removePattern(0);
        }
    }
}
