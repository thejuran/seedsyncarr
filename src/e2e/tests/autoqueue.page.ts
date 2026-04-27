import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';
import { escapeRegex } from './helpers';

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
                (expected) => document.querySelectorAll('.pattern-section .pattern-chip').length >= expected,
                expectedCount,
                { timeout: 5000 }
            );
        }
    }

    async getPatterns(): Promise<string[]> {
        const elements = await this.page.locator('.pattern-section .pattern-chip .pattern-chip-text').all();
        return Promise.all(elements.map(elm => elm.innerText()));
    }

    async addPattern(pattern: string) {
        await this.page.locator('.pattern-add input').fill(pattern);
        await this.page.locator('.pattern-add .btn-pattern-add').click();
        // Wait for the pattern to appear in the list
        await this.page.locator('.pattern-section .pattern-chip-text')
            .filter({ hasText: new RegExp(`^${escapeRegex(pattern)}$`) })
            .waitFor({ state: 'visible' });
    }

    async removePattern(index: number) {
        const countBefore = await this.page.locator('.pattern-section .pattern-chip').count();
        await this.page.locator('.pattern-section .pattern-chip').nth(index).locator('.pattern-chip-remove').click();
        await this.page.waitForFunction(
            (expected) => document.querySelectorAll('.pattern-section .pattern-chip').length === expected,
            countBefore - 1
        );
    }

    async removeAllPatterns() {
        while ((await this.page.locator('.pattern-section .pattern-chip').count()) > 0) {
            await this.removePattern(0);
        }
    }
}
