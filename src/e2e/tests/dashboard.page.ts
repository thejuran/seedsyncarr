import { Page } from '@playwright/test';
import { Paths } from '../urls';
import { App } from './app';

export interface FileInfo {
    name: string;
    status: string;
    size: string;
}

export interface FileActionButtonState {
    title: string;
    isEnabled: boolean;
}

export class DashboardPage extends App {
    constructor(page: Page) {
        super(page);
    }

    async navigateTo() {
        await this.page.goto(Paths.DASHBOARD);
        // Wait for the files list to show up (files are inside virtual scroll viewport)
        await this.page.locator('#file-list .file').first().waitFor({ state: 'visible', timeout: 30000 });
    }

    async waitForAtLeastFileCount(count: number, timeout: number = 10000) {
        // Wait for at least `count` files to be rendered in the viewport.
        // Uses >= because virtual scrolling may render more than expected.
        await this.page.waitForFunction(
            (expectedCount) => {
                const files = document.querySelectorAll('#file-list .file');
                return files.length >= expectedCount;
            },
            count,
            { timeout }
        );
    }

    async getFiles(): Promise<FileInfo[]> {
        const fileElements = await this.page.locator('#file-list .file').all();
        const files: FileInfo[] = [];

        for (const elm of fileElements) {
            // File name is in a flat <span class="name">
            const name = (await elm.locator('.name').textContent() || '').trim();
            // Status is in a <span class="status-badge badge-X">
            const statusText = (await elm.locator('.status-badge').textContent() || '').trim();
            // "Default" badge means no meaningful status — normalize to empty string for compatibility
            const status = statusText.toLowerCase() === 'default' ? '' : statusText;
            // Size is in <span class="size"> inside .meta-right
            const size = (await elm.locator('.meta-right .size').textContent() || '').trim();
            files.push({ name, status, size });
        }

        return files;
    }

    async selectFile(index: number) {
        await this.page.locator('#file-list .file').nth(index).click();
        // Allow Angular change detection to propagate (longer in CI/QEMU environments)
        await this.page.waitForTimeout(process.env.CI ? 500 : 100);
    }

    /**
     * Check if the file actions bar is visible for a selected file.
     * Actions are now shown in the external file-actions-bar component instead of inline.
     */
    async isFileActionsVisible(index: number): Promise<boolean> {
        // Get the file name at the given index
        const file = this.page.locator('#file-list .file').nth(index);
        const fileName = await file.locator('.name').textContent();

        // Check if the file-actions-bar shows this file's name
        const actionsBar = this.page.locator('app-file-actions-bar .file-actions-bar');
        const isVisible = await actionsBar.isVisible();
        if (!isVisible) {
            return false;
        }

        const barFileName = await actionsBar.locator('.name-text').textContent();
        return barFileName?.trim() === fileName?.trim();
    }

    /**
     * Get the file name at a given index.
     * Updated for flat-row layout where name is in a <span class="name">.
     */
    async getFileName(index: number): Promise<string> {
        const file = this.page.locator('#file-list .file').nth(index);
        return (await file.locator('.name').textContent() || '').trim();
    }

    /**
     * Get action button states from the external file-actions-bar.
     * Note: The file must be selected first for actions to appear.
     */
    async getFileActions(index: number): Promise<FileActionButtonState[]> {
        // Make sure the file is selected first
        await this.selectFile(index);

        // Wait for actions bar to be visible
        const actionsBar = this.page.locator('app-file-actions-bar .file-actions-bar');
        await actionsBar.waitFor({ state: 'visible', timeout: 5000 });

        const buttons = await actionsBar.locator('.actions button').all();
        const actions: FileActionButtonState[] = [];

        for (const button of buttons) {
            const title = (await button.textContent() || '').trim();
            const disabled = await button.isDisabled();
            actions.push({
                title,
                isEnabled: !disabled
            });
        }

        return actions;
    }
}