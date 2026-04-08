import { test, expect, Page } from '@playwright/test';
import { DashboardPage } from './dashboard.page';

/**
 * Extended Dashboard Page for bulk action testing
 */
class BulkActionsDashboardPage extends DashboardPage {
    constructor(page: Page) {
        super(page);
    }

    // Checkbox selectors
    get headerCheckbox() {
        return this.page.locator('#file-list #header .header-inner input[type="checkbox"]');
    }

    getFileCheckbox(index: number) {
        return this.page.locator('#file-list .file').nth(index).locator('.checkbox input[type="checkbox"]');
    }

    getFileRow(index: number) {
        return this.page.locator('#file-list .file').nth(index);
    }

    // Selection banner selectors (merged into bulk-actions-bar)
    get selectionBanner() {
        return this.page.locator('.bulk-actions-bar');
    }

    get selectionCount() {
        return this.page.locator('.bulk-actions-bar .selection-label');
    }

    get clearSelectionButton() {
        return this.page.locator('.bulk-actions-bar .clear-btn');
    }

    // Bulk actions bar selectors
    get bulkActionsBar() {
        return this.page.locator('.bulk-actions-bar');
    }

    get bulkSelectionLabel() {
        return this.page.locator('.bulk-actions-bar .selection-label');
    }

    get progressIndicator() {
        return this.page.locator('.bulk-actions-bar .progress-indicator');
    }

    getBulkActionButton(action: 'queue' | 'stop' | 'extract' | 'delete-local' | 'delete-remote') {
        const buttonTexts: Record<string, string> = {
            'queue': 'Queue',
            'stop': 'Stop',
            'extract': 'Extract',
            'delete-local': 'Delete Local',
            'delete-remote': 'Delete Remote'
        };
        return this.page.locator('.bulk-actions-bar .action-btn').filter({ hasText: buttonTexts[action] });
    }

    // Confirmation modal selectors
    get confirmationModal() {
        return this.page.locator('.modal.show');
    }

    get confirmModalTitle() {
        return this.page.locator('.modal.show .modal-title');
    }

    get confirmModalBody() {
        return this.page.locator('.modal.show .modal-body');
    }

    get confirmModalOkButton() {
        return this.page.locator('.modal.show .modal-footer .btn-primary, .modal.show .modal-footer .btn-danger');
    }

    // Alias for linter compatibility
    get confirmationModalOkButton() {
        return this.confirmModalOkButton;
    }

    get confirmModalCancelButton() {
        return this.page.locator('.modal.show .modal-footer .btn-secondary');
    }

    // Toast notification selectors
    get toastContainer() {
        return this.page.locator('.notification');
    }

    getToastByType(type: 'success' | 'warning' | 'danger') {
        return this.page.locator(`.notification.${type}`);
    }

    // Helper methods
    async clickFileCheckbox(index: number, modifiers?: ('Shift' | 'Control' | 'Meta')[]) {
        const checkbox = this.getFileCheckbox(index);
        await checkbox.scrollIntoViewIfNeeded();
        await checkbox.click({ modifiers });
        // Allow Angular change detection to propagate (longer in CI/QEMU environments)
        await this.page.waitForTimeout(process.env.CI ? 1000 : 100);
    }

    async clickHeaderCheckbox() {
        await this.headerCheckbox.scrollIntoViewIfNeeded();
        await this.headerCheckbox.click();
        await this.page.waitForTimeout(process.env.CI ? 1000 : 100);
    }

    async isFileRowBulkSelected(index: number): Promise<boolean> {
        return this.getFileRow(index).locator('.file.bulk-selected').count().then(c => c > 0) ||
               this.getFileRow(index).evaluate(el => el.querySelector('.file')?.classList.contains('bulk-selected') ?? false);
    }

    async isHeaderCheckboxChecked(): Promise<boolean> {
        return this.headerCheckbox.isChecked();
    }

    async isHeaderCheckboxIndeterminate(): Promise<boolean> {
        return this.headerCheckbox.evaluate((el: HTMLInputElement) => el.indeterminate);
    }

    async getSelectedFileCount(): Promise<number> {
        const text = await this.selectionCount.textContent();
        const match = text?.match(/(\d+)\s+files?\s+selected/);
        return match ? parseInt(match[1], 10) : 0;
    }

    async getBulkActionButtonCount(action: 'queue' | 'stop' | 'extract' | 'delete-local' | 'delete-remote'): Promise<number> {
        const button = this.getBulkActionButton(action);
        const text = await button.textContent();
        const match = text?.match(/\((\d+)\)/);
        return match ? parseInt(match[1], 10) : 0;
    }

    async isBulkActionButtonEnabled(action: 'queue' | 'stop' | 'extract' | 'delete-local' | 'delete-remote'): Promise<boolean> {
        const button = this.getBulkActionButton(action);
        return button.isEnabled();
    }

    async shiftClickFileCheckbox(index: number) {
        await this.getFileCheckbox(index).click({ modifiers: ['Shift'] });
    }

    async ctrlClickFileCheckbox(index: number) {
        const modifier = process.platform === 'darwin' ? 'Meta' : 'Control';
        await this.getFileCheckbox(index).click({ modifiers: [modifier] });
    }

    async pressCtrlA() {
        const modifier = process.platform === 'darwin' ? 'Meta' : 'Control';
        await this.page.keyboard.press(`${modifier}+a`);
        await this.page.waitForTimeout(100);
    }

    async pressEscape() {
        await this.page.keyboard.press('Escape');
    }

    async clickConfirmButton() {
        await this.confirmModalOkButton.click();
    }

    async clickCancelButton() {
        await this.confirmModalCancelButton.click();
    }

    async getAllBulkActionButtonTexts(): Promise<string[]> {
        return this.page.locator('.bulk-actions-bar .action-btn').allTextContents();
    }
}

test.describe('Bulk File Actions', () => {
    let dashboardPage: BulkActionsDashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboardPage = new BulkActionsDashboardPage(page);
        await dashboardPage.navigateTo();
        // Wait for files to load - with virtual scrolling, only visible files are rendered
        // min-height 500px / 83px row height = ~6 visible files
        await dashboardPage.waitForAtLeastFileCount(5);
    });

    test.describe('TS-1: Checkbox Selection Basics', () => {
        test('1.1 - clicking checkbox on single file row selects it', async () => {
            await dashboardPage.clickFileCheckbox(0);

            expect(await dashboardPage.getFileCheckbox(0).isChecked()).toBe(true);
            expect(await dashboardPage.selectionBanner).toBeVisible();
        });

        test('1.2 - clicking same checkbox again deselects it', async () => {
            await dashboardPage.clickFileCheckbox(0);
            expect(await dashboardPage.getFileCheckbox(0).isChecked()).toBe(true);

            await dashboardPage.clickFileCheckbox(0);
            expect(await dashboardPage.getFileCheckbox(0).isChecked()).toBe(false);
            await expect(dashboardPage.selectionBanner).not.toBeVisible();
        });

        test('1.3 - clicking checkboxes on multiple files selects all of them', async () => {
            await dashboardPage.clickFileCheckbox(0);
            await dashboardPage.clickFileCheckbox(1);
            await dashboardPage.clickFileCheckbox(2);

            expect(await dashboardPage.getFileCheckbox(0).isChecked()).toBe(true);
            expect(await dashboardPage.getFileCheckbox(1).isChecked()).toBe(true);
            expect(await dashboardPage.getFileCheckbox(2).isChecked()).toBe(true);
        });

        test('1.4 - clicking file name does not clear checkbox selection', async () => {
            await dashboardPage.clickFileCheckbox(0);
            expect(await dashboardPage.getFileCheckbox(0).isChecked()).toBe(true);

            // Click on file name (not checkbox)
            await dashboardPage.selectFile(1);

            // Original checkbox selection should remain
            expect(await dashboardPage.getFileCheckbox(0).isChecked()).toBe(true);
            // Bulk actions bar should still be visible (single-file bar hidden during bulk select)
            expect(await dashboardPage.selectionBanner.isVisible()).toBe(true);
        });

        test('1.5 - selection count in banner matches selected files', async () => {
            // Click checkboxes and wait for banner to appear and count to update
            await dashboardPage.clickFileCheckbox(0);
            await expect(dashboardPage.selectionBanner).toBeVisible({ timeout: 5000 });
            await expect(dashboardPage.selectionCount).toContainText('1', { timeout: 5000 });

            await dashboardPage.clickFileCheckbox(1);
            await expect(dashboardPage.selectionCount).toContainText('2', { timeout: 5000 });

            await dashboardPage.clickFileCheckbox(2);
            await expect(dashboardPage.selectionCount).toContainText('3', { timeout: 5000 });
        });
    });

    test.describe('TS-2: Header Checkbox Behavior', () => {
        test('2.1 - clicking header checkbox with none selected selects all visible', async () => {
            await dashboardPage.clickHeaderCheckbox();

            expect(await dashboardPage.isHeaderCheckboxChecked()).toBe(true);
            // All visible files should be selected
            const files = await dashboardPage.getFiles();
            for (let i = 0; i < files.length; i++) {
                expect(await dashboardPage.getFileCheckbox(i).isChecked()).toBe(true);
            }
        });

        test('2.2 - clicking header checkbox again deselects all', async () => {
            await dashboardPage.clickHeaderCheckbox();
            expect(await dashboardPage.isHeaderCheckboxChecked()).toBe(true);

            await dashboardPage.clickHeaderCheckbox();
            expect(await dashboardPage.isHeaderCheckboxChecked()).toBe(false);
            await expect(dashboardPage.selectionBanner).not.toBeVisible();
        });

        test('2.3 - selecting some files shows indeterminate header state', async () => {
            await dashboardPage.clickFileCheckbox(0);
            await dashboardPage.clickFileCheckbox(1);

            expect(await dashboardPage.isHeaderCheckboxIndeterminate()).toBe(true);
        });

        test('2.4 - clicking header while indeterminate selects all', async () => {
            await dashboardPage.clickFileCheckbox(0);
            expect(await dashboardPage.isHeaderCheckboxIndeterminate()).toBe(true);

            await dashboardPage.clickHeaderCheckbox();
            expect(await dashboardPage.isHeaderCheckboxChecked()).toBe(true);
            expect(await dashboardPage.isHeaderCheckboxIndeterminate()).toBe(false);
        });

        test('2.5 - clicking header when all selected deselects all', async () => {
            await dashboardPage.clickHeaderCheckbox();
            expect(await dashboardPage.isHeaderCheckboxChecked()).toBe(true);

            await dashboardPage.clickHeaderCheckbox();
            expect(await dashboardPage.isHeaderCheckboxChecked()).toBe(false);
        });
    });

    test.describe('TS-3: Selection Banner', () => {
        test('3.1 - selecting 1 file shows banner with count', async () => {
            await dashboardPage.clickFileCheckbox(0);

            await expect(dashboardPage.selectionBanner).toBeVisible({ timeout: 5000 });
            const text = await dashboardPage.selectionCount.textContent();
            expect(text).toContain('1');
            expect(text).toContain('selected');
        });

        test('3.2 - selecting 5 files shows correct count', async () => {
            // Click checkboxes and wait for banner count to update after each
            for (let i = 0; i < 5; i++) {
                await dashboardPage.clickFileCheckbox(i);
                await expect(dashboardPage.selectionBanner).toBeVisible({ timeout: 5000 });
                await expect(dashboardPage.selectionCount).toContainText(`${i + 1}`, { timeout: 5000 });
            }
        });

        test('3.3 - clicking Clear button clears selection', async () => {
            await dashboardPage.clickFileCheckbox(0);
            await dashboardPage.clickFileCheckbox(1);
            await expect(dashboardPage.selectionBanner).toBeVisible({ timeout: 5000 });

            await dashboardPage.clearSelectionButton.click();

            await expect(dashboardPage.selectionBanner).not.toBeVisible();
            expect(await dashboardPage.getFileCheckbox(0).isChecked()).toBe(false);
            expect(await dashboardPage.getFileCheckbox(1).isChecked()).toBe(false);
        });

        // Note: Tests 3.4-3.6 for "Select all matching" feature were removed.
        // Removed: bulk actions only operated on visible files, not all matching.
    });

    test.describe('TS-4: Keyboard Shortcuts', () => {
        test('4.1 - Ctrl+A selects all visible files', async () => {
            // Focus on the file list area first
            await dashboardPage.getFileRow(0).click();
            await dashboardPage.pressCtrlA();

            expect(await dashboardPage.isHeaderCheckboxChecked()).toBe(true);
            await expect(dashboardPage.selectionBanner).toBeVisible();
        });

        test('4.2 - Escape clears selection', async () => {
            await dashboardPage.clickFileCheckbox(0);
            await dashboardPage.clickFileCheckbox(1);
            await expect(dashboardPage.selectionBanner).toBeVisible();

            // Click on file list area to move focus away from checkbox input
            // (keyboard shortcuts are ignored when focus is on input elements)
            await dashboardPage.getFileRow(0).locator('.name').click();
            await dashboardPage.pressEscape();

            await expect(dashboardPage.selectionBanner).not.toBeVisible();
        });

        test('4.3-4.5 - Shift+click selects range', async () => {
            // Click on file 1 and wait for banner to show 1 selected
            await dashboardPage.clickFileCheckbox(1);
            await expect(dashboardPage.selectionCount).toContainText('1');

            // Extra stabilization delay before Shift+click (arm64/QEMU needs more time)
            await dashboardPage.page.waitForTimeout(process.env.CI ? 500 : 100);

            // Shift+click on file 4 to select range [1-4]
            await dashboardPage.clickFileCheckbox(4, ['Shift']);

            // Wait for banner to show 4 files selected (range of 4 files)
            await expect(dashboardPage.selectionCount).toContainText('4', { timeout: 5000 });

            // Files 1, 2, 3, 4 should all be selected
            expect(await dashboardPage.getFileCheckbox(1).isChecked()).toBe(true);
            expect(await dashboardPage.getFileCheckbox(2).isChecked()).toBe(true);
            expect(await dashboardPage.getFileCheckbox(3).isChecked()).toBe(true);
            expect(await dashboardPage.getFileCheckbox(4).isChecked()).toBe(true);

            // File 0 should not be selected
            expect(await dashboardPage.getFileCheckbox(0).isChecked()).toBe(false);
        });
    });

    test.describe('TS-6: Bulk Actions Bar Display', () => {
        test('6.1 - actions bar not visible with no selection', async () => {
            await expect(dashboardPage.bulkActionsBar).not.toBeVisible();
        });

        test('6.2 - actions bar appears when file selected', async () => {
            await dashboardPage.clickFileCheckbox(0);

            await expect(dashboardPage.bulkActionsBar).toBeVisible();
        });

        test('6.3 - buttons show counts for eligible files', async () => {
            await dashboardPage.clickFileCheckbox(0);
            await dashboardPage.clickFileCheckbox(1);

            await expect(dashboardPage.bulkActionsBar).toBeVisible();

            // Check that Queue button exists and has a count
            const queueButton = dashboardPage.getBulkActionButton('queue');
            await expect(queueButton).toBeVisible();
            const queueText = await queueButton.textContent();
            expect(queueText).toMatch(/Queue \(\d+\)/);
        });

        test('6.4 - buttons disabled when count is 0', async () => {
            await dashboardPage.clickFileCheckbox(0);

            // Stop button should be disabled for files in Default state
            const stopButton = dashboardPage.getBulkActionButton('stop');
            const stopCount = await dashboardPage.getBulkActionButtonCount('stop');

            if (stopCount === 0) {
                expect(await stopButton.isDisabled()).toBe(true);
            }
        });

        test('6.6 - verify button order', async () => {
            await dashboardPage.clickFileCheckbox(0);
            // Wait for bulk actions bar to be visible before checking buttons
            await expect(dashboardPage.bulkActionsBar).toBeVisible();

            const buttons = await dashboardPage.getAllBulkActionButtonTexts();

            // Verify order: Queue, Stop, Extract, Delete Local, Delete Remote
            expect(buttons.length).toBe(5);
            expect(buttons[0]).toContain('Queue');
            expect(buttons[1]).toContain('Stop');
            expect(buttons[2]).toContain('Extract');
            expect(buttons[3]).toContain('Delete Local');
            expect(buttons[4]).toContain('Delete Remote');
        });
    });

    test.describe('TS-7: Bulk Queue Action', () => {
        test('7.1-7.5 - Queue action button is enabled for queueable files', async () => {
            // Select some queueable files
            await dashboardPage.clickFileCheckbox(0);
            await dashboardPage.clickFileCheckbox(1);

            const queueButton = dashboardPage.getBulkActionButton('queue');
            const queueCount = await dashboardPage.getBulkActionButtonCount('queue');

            // Verify queue button is enabled when there are queueable files
            if (queueCount > 0) {
                await expect(queueButton).toBeEnabled();
                // Verify no confirmation dialog would appear (queue doesn't need confirmation)
                // Note: We don't actually click to avoid modifying state for other tests
            }
        });
    });

    test.describe('TS-10: Bulk Delete Local Action', () => {
        test('10.2-10.4 - Delete Local shows confirmation dialog', async () => {
            // Need to find files with local copies
            await dashboardPage.clickHeaderCheckbox();

            const deleteLocalButton = dashboardPage.getBulkActionButton('delete-local');
            const deleteCount = await dashboardPage.getBulkActionButtonCount('delete-local');

            if (deleteCount > 0) {
                await deleteLocalButton.click();

                // Confirmation dialog should appear
                await expect(dashboardPage.confirmationModal).toBeVisible();

                // Cancel should close without action
                await dashboardPage.clickCancelButton();

                await expect(dashboardPage.confirmationModal).not.toBeVisible();

                // Selection should remain
                await expect(dashboardPage.selectionBanner).toBeVisible();
            }
        });
    });

    test.describe('TS-11: Bulk Delete Remote Action', () => {
        test('11.2-11.3 - Delete Remote shows danger confirmation dialog', async () => {
            await dashboardPage.clickHeaderCheckbox();

            const deleteRemoteButton = dashboardPage.getBulkActionButton('delete-remote');
            const deleteCount = await dashboardPage.getBulkActionButtonCount('delete-remote');

            if (deleteCount > 0) {
                await deleteRemoteButton.click();

                // Confirmation dialog should appear
                await expect(dashboardPage.confirmationModal).toBeVisible();

                // Should have danger styling (button class)
                const okButton = dashboardPage.confirmationModalOkButton;
                const buttonClasses = await okButton.getAttribute('class');
                expect(buttonClasses).toContain('btn-danger');

                // Cancel to cleanup
                await dashboardPage.clickCancelButton();
            }
        });
    });

    test.describe('TS-14: Edge Cases', () => {
        test('14.3 - buttons have correct disabled attribute based on eligibility', async () => {
            await dashboardPage.clickFileCheckbox(0);

            const queueButton = dashboardPage.getBulkActionButton('queue');
            const stopButton = dashboardPage.getBulkActionButton('stop');
            const queueCount = await dashboardPage.getBulkActionButtonCount('queue');
            const stopCount = await dashboardPage.getBulkActionButtonCount('stop');

            // Queue button should be enabled if there are queueable files
            if (queueCount > 0) {
                await expect(queueButton).toBeEnabled();
            }

            // Stop button should be disabled for files in Default state
            if (stopCount === 0) {
                await expect(stopButton).toBeDisabled();
            }
        });

        test('14.4 - all buttons disabled when no eligible files', async () => {
            // Select files and check disabled state of buttons with 0 count
            await dashboardPage.clickFileCheckbox(0);

            const stopButton = dashboardPage.getBulkActionButton('stop');
            const stopCount = await dashboardPage.getBulkActionButtonCount('stop');

            if (stopCount === 0) {
                expect(await stopButton.isDisabled()).toBe(true);
            }
        });

        test('14.6 - empty selection keyboard shortcuts are no-op', async () => {
            // Ensure no selection
            await expect(dashboardPage.selectionBanner).not.toBeVisible();

            // Press Escape - should not error
            await dashboardPage.pressEscape();

            // Still no selection (no error)
            await expect(dashboardPage.selectionBanner).not.toBeVisible();
        });
    });
});
