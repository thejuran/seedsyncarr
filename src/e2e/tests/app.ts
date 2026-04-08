import { Page } from '@playwright/test';

export class App {
    constructor(protected page: Page) {}

    async navigateTo() {
        await this.page.goto('/');
    }

    async getTitle(): Promise<string> {
        return this.page.title();
    }

    async getNavLinks(): Promise<string[]> {
        const items = await this.page.locator('#top-nav .nav-link').all();
        return Promise.all(items.map(item => item.innerText()));
    }

    async getActiveNavLink(): Promise<string> {
        return this.page.locator('#top-nav .nav-link.active').innerText();
    }
}
