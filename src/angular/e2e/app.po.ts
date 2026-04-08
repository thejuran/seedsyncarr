import { Page } from '@playwright/test';

export class AppPage {
  constructor(private page: Page) {}

  async navigateTo() {
    await this.page.goto('/');
  }

  async getTitle() {
    return this.page.title();
  }
}
