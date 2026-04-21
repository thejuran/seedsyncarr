import { test as base, expect, type Page } from '@playwright/test';

export interface CspViolation {
    source: 'console' | 'event';
    blockedURI?: string;
    violatedDirective?: string;
    originalPolicy?: string;
    sourceFile?: string;
    lineNumber?: number;
    sample?: string;
    text?: string;
}

type Fixtures = {
    cspViolations: CspViolation[];
    allowViolations: boolean;
};

export const test = base.extend<Fixtures>({
    allowViolations: [false, { option: true }],

    cspViolations: async ({}, use) => {
        await use([]);
    },

    page: async ({ page, cspViolations, allowViolations }, use) => {
        await page.exposeFunction('__reportCspViolation', (v: CspViolation) => {
            cspViolations.push({ ...v, source: 'event' });
        });

        await page.addInitScript(() => {
            document.addEventListener('securitypolicyviolation', (e) => {
                // @ts-ignore — exposed function on window at runtime
                window.__reportCspViolation({
                    blockedURI: e.blockedURI,
                    violatedDirective: e.violatedDirective,
                    originalPolicy: e.originalPolicy,
                    sourceFile: e.sourceFile,
                    lineNumber: e.lineNumber,
                    sample: e.sample,
                });
            });
        });

        page.on('console', (msg) => {
            const text = msg.text();
            if (msg.type() === 'error' &&
                text.includes('violates the following Content Security Policy directive')) {
                cspViolations.push({ source: 'console', text });
            }
        });

        await use(page);

        if (!allowViolations) {
            expect(cspViolations, 'CSP violations detected').toEqual([]);
        }
    },
});

export { expect };
