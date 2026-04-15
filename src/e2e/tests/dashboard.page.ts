import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export interface FileInfo {
    name: string;
    status: string;
    size: string;
}

export class DashboardPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.DASHBOARD);
        // Wait for the transfer table to render at least one row
        await this.page.locator('.transfer-table tbody app-transfer-row').first()
            .waitFor({ state: 'visible', timeout: 30000 });
    }

    async waitForAtLeastFileCount(count: number, timeout: number = 10000) {
        await this.page.waitForFunction(
            (expectedCount) => {
                const rows = document.querySelectorAll('.transfer-table tbody app-transfer-row');
                return rows.length >= expectedCount;
            },
            count,
            { timeout }
        );
    }

    async getFiles(): Promise<FileInfo[]> {
        const rowElements = await this.page.locator('.transfer-table tbody app-transfer-row').all();
        const files: FileInfo[] = [];

        for (const row of rowElements) {
            const name = (await row.locator('td.cell-name .file-name').textContent() || '').trim();
            const statusText = (await row.locator('td.cell-status .status-badge').textContent() || '').trim();
            // DEFAULT status renders as em dash; normalize to empty string for golden data
            const status = statusText === '\u2014' ? '' : statusText;
            const size = (await row.locator('td.cell-size').textContent() || '').trim();
            files.push({ name, status, size });
        }

        return files;
    }
}
