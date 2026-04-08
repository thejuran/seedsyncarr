import { test, expect } from '@playwright/test';
import { AppPage } from './app.po';

test.describe('SeedSyncarr App', () => {
  let appPage: AppPage;

  test.beforeEach(async ({ page }) => {
    appPage = new AppPage(page);
  });

  test('should have correct title', async ({ page }) => {
    appPage = new AppPage(page);
    await appPage.navigateTo();
    const title = await appPage.getTitle();
    expect(title).toBe('SeedSyncarr');
  });
});
