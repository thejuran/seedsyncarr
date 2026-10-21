import { test, expect } from './fixtures/csp-listener';
import { AutoQueuePage } from './autoqueue.page';
import { Paths } from '../urls';

// NOTE: synthetic test fixture, not a secret; appears in the config/set
// response and access logs — use only this fake value.
const E2E_TOKEN = 'e2e-api-token-not-a-secret';
const AUTH = { Authorization: `Bearer ${E2E_TOKEN}` };

/**
 * Runs only in the 'chromium-token' Playwright project, after every other
 * test (SEC-02, D-12). general.api_token cannot be unset through the API
 * (config/set rejects an empty value), so this spec must run last.
 */
test.describe('API token configured (SEC-02)', () => {
    let githubHeaders: Record<string, string>[] = [];

    test.beforeEach(async ({ page, request }) => {
        githubHeaders = [];

        // Idempotent across CI retries: the server ignores the header when no
        // token is set yet, and accepts it when this token is already set.
        const res = await request.post('/server/config/set', {
            headers: AUTH,
            data: { section: 'general', key: 'api_token', value: E2E_TOKEN },
        });
        if (!res.ok()) {
            throw new Error(`api_token set failed: ${res.status()}`);
        }

        // Register before any navigation — the update check fires in an
        // APP_INITIALIZER at bootstrap.
        await page.route('https://api.github.com/**', async (route) => {
            githubHeaders.push(await route.request().allHeaders());
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                headers: { 'Access-Control-Allow-Origin': '*' },
                body: JSON.stringify({
                    tag_name: 'v99.0.0',
                    html_url: 'https://github.com/thejuran/seedsyncarr/releases/tag/v99.0.0',
                }),
            });
        });
    });

    test('rejects /server/ requests without the token', async ({ request }) => {
        const noAuth = await request.get('/server/config/get');
        expect(noAuth.status()).toBe(401);

        const withAuth = await request.get('/server/config/get', { headers: AUTH });
        expect(withAuth.status()).toBe(200);
    });

    test('sends the token to /server/* but never to api.github.com', async ({ page }) => {
        const ownReq = page.waitForRequest((r) => new URL(r.url()).pathname === '/server/config/get');
        const githubReq = page.waitForRequest((r) => r.url().startsWith('https://api.github.com/'));

        await page.goto(Paths.SETTINGS);

        // Positive control: proves the capture mechanism sees the header and
        // that the token really is configured.
        const own = await ownReq;
        expect((await own.allHeaders())['authorization']).toBe(`Bearer ${E2E_TOKEN}`);
        expect((await own.response())?.status()).toBe(200);

        // SEC-02 core assertion: the browser's request to api.github.com
        // never carries the app token.
        await githubReq;
        expect(githubHeaders.length).toBeGreaterThan(0);
        for (const headers of githubHeaders) {
            expect(headers['authorization']).toBeUndefined();
        }

        await expect(page.locator('meta[name="api-token"]')).toHaveAttribute('content', E2E_TOKEN);

        // D-07 demonstration: the stubbed newer release is readable because
        // the token no longer causes GitHub to return 401.
        await page.locator('.bell-btn').click();
        await expect(
            page.locator('.bell-notif-text').filter({ hasText: 'A new version of SeedSyncarr is available' })
        ).toBeVisible();
    });

    test('authenticated write flow works with the token', async ({ page }) => {
        const autoQueuePage = new AutoQueuePage(page);
        await autoQueuePage.navigateTo();
        await autoQueuePage.removeAllPatterns();

        const addResp = page.waitForResponse((r) => new URL(r.url()).pathname.startsWith('/server/autoqueue/add/'));
        await autoQueuePage.addPattern('e2e-token-pattern');
        const resp = await addResp;

        expect(resp.status()).toBe(200);
        expect((await resp.request().allHeaders())['authorization']).toBe(`Bearer ${E2E_TOKEN}`);
        expect(await autoQueuePage.getPatterns()).toEqual(['e2e-token-pattern']);

        await autoQueuePage.removeAllPatterns();
        expect(await autoQueuePage.getPatterns()).toEqual([]);
    });
});
