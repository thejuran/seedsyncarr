import { test, expect } from './fixtures/csp-listener';

test.use({ allowViolations: true });

test.describe('CSP violation canary', () => {
    test('Seeded inline-script injection fires a CSP violation', async ({ page, cspViolations }) => {
        await page.addInitScript(() => {
            document.addEventListener('DOMContentLoaded', () => {
                const el = document.createElement('script');
                el.textContent = 'window.__canaryRan = true;';
                document.body.appendChild(el);
            });
        });

        await page.goto('/');

        await expect.poll(() => cspViolations.length).toBeGreaterThan(0);

        const sawScriptSrc = cspViolations.some((v) =>
            (v.source === 'event' && v.violatedDirective?.startsWith('script-src')) ||
            (v.source === 'console' && v.text?.includes('script-src'))
        );
        expect(sawScriptSrc).toBe(true);
    });
});
