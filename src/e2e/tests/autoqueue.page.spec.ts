import { test, expect } from './fixtures/csp-listener';
import { AutoQueuePage } from './autoqueue.page';

test.describe('Testing autoqueue patterns in settings', () => {
    test.beforeEach(async ({ page }) => {
        const autoQueuePage = new AutoQueuePage(page);
        await autoQueuePage.navigateTo();
        // Clean up any existing patterns to ensure test isolation
        await autoQueuePage.removeAllPatterns();
    });

    test('should have Settings nav link active', async ({ page }) => {
        const autoQueuePage = new AutoQueuePage(page);
        const activeLink = await autoQueuePage.getActiveNavLink();
        expect(activeLink).toBe('Settings');
    });

    test('should add and remove patterns', async ({ page }) => {
        const autoQueuePage = new AutoQueuePage(page);

        // start with an empty list
        expect(await autoQueuePage.getPatterns()).toEqual([]);

        // add some patterns, and expect them in added order
        await autoQueuePage.addPattern('APattern');
        await autoQueuePage.addPattern('CPattern');
        await autoQueuePage.addPattern('DPattern');
        await autoQueuePage.addPattern('BPattern');
        expect(await autoQueuePage.getPatterns()).toEqual([
            'APattern', 'CPattern', 'DPattern', 'BPattern'
        ]);

        // remove patterns one by one
        await autoQueuePage.removePattern(2);
        expect(await autoQueuePage.getPatterns()).toEqual([
            'APattern', 'CPattern', 'BPattern'
        ]);
        await autoQueuePage.removePattern(0);
        expect(await autoQueuePage.getPatterns()).toEqual([
            'CPattern', 'BPattern'
        ]);
        await autoQueuePage.removePattern(1);
        expect(await autoQueuePage.getPatterns()).toEqual([
            'CPattern'
        ]);
        await autoQueuePage.removePattern(0);
        expect(await autoQueuePage.getPatterns()).toEqual([]);
    });

    test('should list existing patterns in alphabetical order', async ({ page }) => {
        const autoQueuePage = new AutoQueuePage(page);

        // start with an empty list
        expect(await autoQueuePage.getPatterns()).toEqual([]);

        // add some patterns, and expect them in added order
        await autoQueuePage.addPattern('APattern');
        await autoQueuePage.addPattern('CPattern');
        await autoQueuePage.addPattern('DPattern');
        await autoQueuePage.addPattern('BPattern');

        // reload the page
        await autoQueuePage.navigateTo();

        // Wait for patterns to load from server after page reload
        await autoQueuePage.waitForPatternsToLoad(4);

        // patterns should be in alphabetical order
        expect(await autoQueuePage.getPatterns()).toEqual([
            'APattern', 'BPattern', 'CPattern', 'DPattern'
        ]);

        // remove all patterns
        await autoQueuePage.removeAllPatterns();
        expect(await autoQueuePage.getPatterns()).toEqual([]);
    });
});
