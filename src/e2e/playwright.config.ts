import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for SeedSyncarr e2e tests
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.ts',
  fullyParallel: false, // Run tests sequentially for predictable state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker for stateful tests
  reporter: [
    ['list'],
    ['html', { open: 'never' }]
  ],
  use: {
    baseURL: process.env.APP_BASE_URL || 'http://myapp:8800',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--no-sandbox', '--disable-dev-shm-usage']
        }
      },
    },
  ],
  timeout: 30000,
  expect: {
    timeout: process.env.CI ? 10000 : 5000
  },
});
