import { defineConfig, devices } from '@playwright/test';

// The token spec sets general.api_token on the shared myapp container at
// runtime and the API cannot unset it (config/set rejects an empty value).
// It must run strictly last, after every no-token spec.
const TOKEN_SPEC = /auth-token\.spec\.ts/;

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
    locale: 'en-US',  // Force deterministic ICU locale; prevents arm64/amd64 sort divergence
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      testIgnore: TOKEN_SPEC,
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--no-sandbox', '--disable-dev-shm-usage']
        }
      },
    },
    {
      // DO NOT set use.extraHTTPHeaders here — it would add Authorization to
      // every browser request, including the api.github.com request, and
      // mask the bug this project exists to catch.
      name: 'chromium-token',
      testMatch: TOKEN_SPEC,
      dependencies: ['chromium'],
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
