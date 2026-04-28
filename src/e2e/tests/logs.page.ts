import { Page, Locator } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export class LogsPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.LOGS);
    }

    getLevelButtons(): Locator {
        return this.page.locator('.level-filter-group .level-btn');
    }

    getSearchInput(): Locator {
        return this.page.locator('.search-input');
    }

    getAutoScrollButton(): Locator {
        return this.page.locator('.action-btn').filter({ hasText: 'Auto-scroll' });
    }

    getClearButton(): Locator {
        return this.page.locator('.action-btn--clear');
    }

    getExportButton(): Locator {
        return this.page.locator('.action-btn--export');
    }

    getLogRows(): Locator {
        return this.page.locator('.log-row');
    }

    getStatusBar(): Locator {
        return this.page.locator('.status-bar');
    }

    getStatusBarRight(): Locator {
        return this.page.locator('.status-bar__right');
    }

}
