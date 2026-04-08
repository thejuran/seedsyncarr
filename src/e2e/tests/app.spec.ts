import { test, expect } from '@playwright/test';
import { App } from './app';

test.describe('Testing top-level app', () => {
    test.beforeEach(async ({ page }) => {
        const app = new App(page);
        await app.navigateTo();
    });

    test('should have right title', async ({ page }) => {
        const app = new App(page);
        const title = await app.getTitle();
        expect(title).toBe('SeedSyncarr');
    });

    test('should have all the nav links', async ({ page }) => {
        const app = new App(page);
        const items = await app.getNavLinks();
        expect(items).toEqual([
            'Dashboard',
            'Settings',
            'Logs',
            'About',
        ]);
    });

    test('should default to the dashboard page', async ({ page }) => {
        const app = new App(page);
        const activeLink = await app.getActiveNavLink();
        expect(activeLink).toBe('Dashboard');
    });
});
