import { test, expect } from '@playwright/test';
import { AboutPage } from './about.page';

test.describe('Testing about page', () => {
    test.beforeEach(async ({ page }) => {
        const aboutPage = new AboutPage(page);
        await aboutPage.navigateTo();
    });

    test('should have About nav link active', async ({ page }) => {
        const aboutPage = new AboutPage(page);
        const activeLink = await aboutPage.getActiveNavLink();
        expect(activeLink).toBe('About');
    });

    test('should have the right version', async ({ page }) => {
        const aboutPage = new AboutPage(page);
        const version = await aboutPage.getVersion();
        expect(version).toBe('v1.0.0');
    });
});
