import { Page, Locator } from '@playwright/test';
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
        // Wait for the transfer table container first (distinguishes "page not loaded" from "no data")
        await this.page.locator('.transfer-table').waitFor({ state: 'visible', timeout: 30000 });
        // Then wait for at least one row to render
        await this.page.locator('.transfer-table tbody app-transfer-row').first()
            .waitFor({ state: 'visible', timeout: 30000 });
    }

    async waitForAtLeastFileCount(count: number, timeout: number = 10000) {
        await this.page.waitForFunction(
            (expectedCount: number) => {
                const rows = document.querySelectorAll('.transfer-table tbody app-transfer-row');
                return rows.length >= expectedCount &&
                    [...rows].every(r => r.querySelector('td.cell-name .file-name')?.textContent?.trim());
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

    getRowCheckbox(fileName: string): Locator {
        const row = this.page.locator('.transfer-table tbody app-transfer-row', {
            has: this.page.locator('td.cell-name .file-name', { hasText: new RegExp(`^${this._escapeRegex(fileName)}$`) })
        });
        return row.locator('td.cell-checkbox input.ss-checkbox');
    }

    getHeaderCheckbox(): Locator {
        return this.page.locator('.transfer-table thead th.col-checkbox input.ss-checkbox');
    }

    getActionBar(): Locator {
        return this.page.locator('app-bulk-actions-bar .bulk-actions-bar');
    }

    getActionButton(name: 'Queue' | 'Stop' | 'Extract' | 'Delete Local' | 'Delete Remote'): Locator {
        return this.page.locator('app-bulk-actions-bar').getByRole('button', { name, exact: true });
    }

    getSegmentButton(name: 'All' | 'Active' | 'Done' | 'Errors'): Locator {
        return this.page.locator('.segment-filters').getByRole('button', { name, exact: true });
    }

    getSubButton(name: 'Pending' | 'Syncing' | 'Queued' | 'Extracting' | 'Downloaded' | 'Extracted' | 'Failed' | 'Deleted'): Locator {
        return this.page.locator('.segment-filters button.btn-sub').getByText(name, { exact: true });
    }

    async selectFileByName(fileName: string): Promise<void> {
        await this.getRowCheckbox(fileName).click();
    }

    async clearSelectionViaBar(): Promise<void> {
        const clearBtn = this.page.locator('app-bulk-actions-bar button.clear-btn');
        if (await clearBtn.isVisible()) {
            await clearBtn.click();
        }
    }

    private _escapeRegex(s: string): string {
        return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
}
