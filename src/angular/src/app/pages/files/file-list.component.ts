import {Component, ChangeDetectionStrategy, ChangeDetectorRef, HostListener, DestroyRef, inject} from "@angular/core";
import { AsyncPipe } from "@angular/common";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
// CDK virtual scroll temporarily disabled for E2E debugging
// import {CdkVirtualScrollViewport, CdkVirtualForOf} from "@angular/cdk/scrolling";
import {Observable, combineLatest} from "rxjs";
import {map} from "rxjs/operators";

import {List} from "immutable";

import {FileComponent} from "./file.component";
import {BulkActionsBarComponent} from "./bulk-actions-bar.component";
import {FileActionsBarComponent} from "./file-actions-bar.component";
import {ViewFileService} from "../../services/files/view-file.service";
import {ViewFile} from "../../services/files/view-file";
import {LoggerService} from "../../services/utils/logger.service";
import {ViewFileOptions} from "../../services/files/view-file-options";
import {ViewFileOptionsService} from "../../services/files/view-file-options.service";
import {FileSelectionService} from "../../services/files/file-selection.service";
import {BulkCommandService, BulkAction, BulkActionResult} from "../../services/server/bulk-command.service";
import {ConfirmModalService} from "../../services/utils/confirm-modal.service";
import {NotificationService} from "../../services/utils/notification.service";
import {Notification} from "../../services/utils/notification";
import {Localization} from "../../common/localization";
import {ToastService} from "../../services/utils/toast.service";
// Note: IsSelectedPipe removed in Session 16 - FileComponent now uses computed() signal

@Component({
    selector: "app-file-list",
    providers: [],
    templateUrl: "./file-list.component.html",
    styleUrls: ["./file-list.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
    imports: [
        AsyncPipe,
        FileComponent,
        BulkActionsBarComponent,
        FileActionsBarComponent
    ]
})
export class FileListComponent {
    // Inject DestroyRef for automatic subscription cleanup
    private destroyRef = inject(DestroyRef);

    public files: Observable<List<ViewFile>>;
    public identify = FileListComponent.identify;
    public readonly emptySet = new Set<string>();
    public options: Observable<ViewFileOptions>;

    // Header checkbox state: 'none', 'some', 'all'
    public headerCheckboxState$: Observable<"none" | "some" | "all">;

    // Track import status to detect transitions for toast notifications
    private _prevImportStatuses: Map<string, string> = new Map();
    private _firstEmission = true;

    // Selection state for banner
    public selectedFiles$: Observable<Set<string>>;

    // Single selected file for actions bar (detail panel selection)
    public selectedFile$!: Observable<ViewFile | null>;

    // Track last clicked file name for shift+click range selection (name-based for filter resilience)
    private _lastClickedFileName: string | null = null;
    // Cache of current files list for range selection (updated on each observable emission)
    private _currentFiles: List<ViewFile> = List();
    // Track whether a bulk operation is in progress (for UI feedback)
    public bulkOperationInProgress = false;

    constructor(private _logger: LoggerService,
                private viewFileService: ViewFileService,
                private viewFileOptionsService: ViewFileOptionsService,
                public fileSelectionService: FileSelectionService,
                private bulkCommandService: BulkCommandService,
                private confirmModalService: ConfirmModalService,
                private notificationService: NotificationService,
                private _toastService: ToastService,
                private _cdr: ChangeDetectorRef) {
        this.files = viewFileService.filteredFiles;
        this.options = this.viewFileOptionsService.options;

        // Selection state observable for banner
        this.selectedFiles$ = this.fileSelectionService.selectedFiles$;

        // Single selected file for actions bar (derived from files list)
        this.selectedFile$ = this.files.pipe(
            map(files => files.find(f => !!f.isSelected) || null)
        );

        // Keep a cached copy of files for range selection
        // Uses takeUntilDestroyed to automatically unsubscribe when component is destroyed
        this.files.pipe(
            takeUntilDestroyed(this.destroyRef)
        ).subscribe(files => {
            this._currentFiles = files;
            // Note: We intentionally do NOT reset _lastClickedFileName here.
            // The anchor persists even if the file is temporarily filtered out,
            // allowing shift+click to work correctly when the filter changes back.
        });

        // Calculate header checkbox state based on selection and visible files
        this.headerCheckboxState$ = combineLatest([
            this.files,
            this.fileSelectionService.selectedFiles$
        ]).pipe(
            map(([files, selectedFiles]) => {
                if (files.size === 0 || selectedFiles.size === 0) {
                    return "none";
                }
                const visibleSelectedCount = files.filter(f => f.name != null && selectedFiles.has(f.name)).size;
                if (visibleSelectedCount === 0) {
                    return "none";
                } else if (visibleSelectedCount === files.size) {
                    return "all";
                } else {
                    return "some";
                }
            })
        );

        // Subscribe to file updates to detect import status transitions
        this.viewFileService.files
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(files => {
                if (this._firstEmission) {
                    // First emission is initial load - record statuses without toasting
                    this._firstEmission = false;
                    files.forEach(file => {
                        if (file.importStatus) {
                            this._prevImportStatuses.set(file.name!, file.importStatus);
                        }
                    });
                    return;
                }

                // Check for new imports (only toast when we've seen the file before
                // with a non-IMPORTED status — files appearing for the first time
                // as IMPORTED are persisted from a previous session, not new events)
                files.forEach(file => {
                    const prevStatus = this._prevImportStatuses.get(file.name!);
                    if (file.importStatus === ViewFile.ImportStatus.IMPORTED &&
                        prevStatus !== undefined &&
                        prevStatus !== ViewFile.ImportStatus.IMPORTED) {
                        this._toastService.success("Sonarr/Radarr imported: " + file.name);
                    }
                    // Update tracked status
                    if (file.importStatus) {
                        this._prevImportStatuses.set(file.name!, file.importStatus);
                    }
                });

                // Clean up removed files
                const currentNames = new Set(files.map(f => f.name));
                for (const name of this._prevImportStatuses.keys()) {
                    if (!currentNames.has(name)) {
                        this._prevImportStatuses.delete(name);
                    }
                }
            });
    }

    // =========================================================================
    // Keyboard Shortcuts
    // =========================================================================

    /**
     * Handle Ctrl/Cmd+A to select all visible files.
     * Handle Escape to clear selection.
     */
    @HostListener("document:keydown", ["$event"])
    onKeyDown(event: KeyboardEvent): void {
        // Ctrl/Cmd+A: Select all visible files
        if ((event.ctrlKey || event.metaKey) && event.key === "a") {
            // Only handle if not in an input/textarea
            if (!this._isInputElement(event.target)) {
                event.preventDefault();
                this.fileSelectionService.selectAllVisible(this._currentFiles.toArray());
            }
        }

        // Escape: Clear selection
        if (event.key === "Escape") {
            if (!this._isInputElement(event.target)) {
                this.fileSelectionService.clearSelection();
                this._lastClickedFileName = null;
            }
        }

        // Arrow Down: move focus to next file row
        if (event.key === "ArrowDown") {
            if (!this._isInputElement(event.target)) {
                event.preventDefault();
                this._moveFocusToRow(1);
            }
        }

        // Arrow Up: move focus to previous file row
        if (event.key === "ArrowUp") {
            if (!this._isInputElement(event.target)) {
                event.preventDefault();
                this._moveFocusToRow(-1);
            }
        }

        // Enter/Space: select the focused file row (like clicking)
        if (event.key === "Enter" || event.key === " ") {
            if (!this._isInputElement(event.target)) {
                const focused = document.activeElement as HTMLElement;
                if (focused?.closest("app-file")) {
                    event.preventDefault();
                    focused.closest("app-file")?.querySelector<HTMLElement>(".file")?.click();
                }
            }
        }
    }

    /**
     * Move keyboard focus to the next/previous file row.
     * @param direction +1 for next row, -1 for previous row
     */
    private _moveFocusToRow(direction: number): void {
        const rows = Array.from(document.querySelectorAll<HTMLElement>("#file-list .file[role=\"row\"]"));
        if (rows.length === 0) {return;}

        const currentIndex = rows.findIndex(row => row === document.activeElement || row.contains(document.activeElement as Node));

        let nextIndex: number;
        if (currentIndex === -1) {
            // No row currently focused — focus the first (down) or last (up) row
            nextIndex = direction > 0 ? 0 : rows.length - 1;
        } else {
            nextIndex = currentIndex + direction;
        }

        // Clamp to bounds (do not wrap)
        if (nextIndex < 0 || nextIndex >= rows.length) {return;}

        rows[nextIndex].focus();
    }

    /**
     * Check if the event target is an input element where we shouldn't intercept shortcuts.
     */
    private _isInputElement(target: EventTarget | null): boolean {
        if (!target) {
            return false;
        }
        const tagName = (target as HTMLElement).tagName?.toLowerCase();
        return tagName === "input" || tagName === "textarea" || tagName === "select";
    }

    /**
     * Used for trackBy in ngFor
     * @param index
     * @param item
     */
    static identify(index: number, item: ViewFile): string {
        return item.name!;
    }

    onSelect(file: ViewFile): void {
        if (file.isSelected) {
            this.viewFileService.unsetSelected();
        } else {
            this.viewFileService.setSelected(file);
        }
    }

    onQueue(file: ViewFile): void {
        this.viewFileService.queue(file).pipe(
            takeUntilDestroyed(this.destroyRef)
        ).subscribe(data => {
            this._logger.info(data);
        });
    }

    onStop(file: ViewFile): void {
        this.viewFileService.stop(file).pipe(
            takeUntilDestroyed(this.destroyRef)
        ).subscribe(data => {
            this._logger.info(data);
        });
    }

    onExtract(file: ViewFile): void {
        this.viewFileService.extract(file).pipe(
            takeUntilDestroyed(this.destroyRef)
        ).subscribe(data => {
            this._logger.info(data);
        });
    }

    onDeleteLocal(file: ViewFile): void {
        this.viewFileService.deleteLocal(file).pipe(
            takeUntilDestroyed(this.destroyRef)
        ).subscribe(data => {
            this._logger.info(data);
        });
    }

    onDeleteRemote(file: ViewFile): void {
        this.viewFileService.deleteRemote(file).pipe(
            takeUntilDestroyed(this.destroyRef)
        ).subscribe(data => {
            this._logger.info(data);
        });
    }

    // =========================================================================
    // Bulk Selection Methods
    // =========================================================================

    /**
     * Handle header checkbox click.
     * If none or some selected: select all visible.
     * If all selected: deselect all.
     */
    onHeaderCheckboxClick(files: List<ViewFile>): void {
        const selectedFiles = this.fileSelectionService.getSelectedFiles();
        const visibleSelectedCount = files.filter(f => f.name != null && selectedFiles.has(f.name)).size;

        if (visibleSelectedCount === files.size && files.size > 0) {
            // All visible are selected - clear selection
            this.fileSelectionService.clearSelection();
        } else {
            // None or some selected - select all visible
            this.fileSelectionService.selectAllVisible(files.toArray());
        }
    }

    /**
     * Handle "Clear" from banner.
     */
    onClearSelection(): void {
        this.fileSelectionService.clearSelection();
        this._lastClickedFileName = null;
    }

    /**
     * Handle checkbox toggle with support for shift+click range selection.
     * Uses name-based anchor tracking so shift+click works correctly even
     * when filters change or virtual scrolling shifts the list.
     * @param event The event containing the file and shift key state
     */
    onCheckboxToggle(event: {file: ViewFile, shiftKey: boolean}): void {
        if (event.shiftKey && this._lastClickedFileName !== null) {
            // Shift+click: select range from anchor to current
            // Find both indices by name (handles filter/scroll changes)
            const lastIndex = this._currentFiles.findIndex(f => f.name === this._lastClickedFileName);
            const currentIndex = this._currentFiles.findIndex(f => f.name === event.file.name);

            if (lastIndex !== -1 && currentIndex !== -1) {
                // Both anchor and target are visible - select the range
                const start = Math.min(lastIndex, currentIndex);
                const end = Math.max(lastIndex, currentIndex);

                const rangeNames: string[] = [];
                for (let i = start; i <= end; i++) {
                    const file = this._currentFiles.get(i);
                    if (file?.name) {
                        rangeNames.push(file.name);
                    }
                }
                this.fileSelectionService.setSelection(rangeNames);
            } else {
                // Anchor no longer visible - just toggle the clicked file and set new anchor
                this.fileSelectionService.toggle(event.file.name!);
                this._lastClickedFileName = event.file.name;
            }
        } else {
            // Normal click: toggle the single file and update anchor
            this.fileSelectionService.toggle(event.file.name!);
            this._lastClickedFileName = event.file.name;
        }
    }

    // =========================================================================
    // Bulk Action Handlers
    // =========================================================================

    /**
     * Handle bulk Queue action.
     * @param fileNames Array of file names to queue
     */
    onBulkQueue(fileNames: string[]): void {
        this._logger.info(`Bulk queue requested for ${fileNames.length} files:`, fileNames);
        this._executeBulkAction("queue", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_QUEUED,
            partialMsg: Localization.Bulk.PARTIAL_QUEUED
        });
    }

    /**
     * Handle bulk Stop action.
     * @param fileNames Array of file names to stop
     */
    onBulkStop(fileNames: string[]): void {
        this._logger.info(`Bulk stop requested for ${fileNames.length} files:`, fileNames);
        this._executeBulkAction("stop", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_STOPPED,
            partialMsg: Localization.Bulk.PARTIAL_STOPPED
        });
    }

    /**
     * Handle bulk Extract action.
     * @param fileNames Array of file names to extract
     */
    onBulkExtract(fileNames: string[]): void {
        this._logger.info(`Bulk extract requested for ${fileNames.length} files:`, fileNames);
        this._executeBulkAction("extract", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_EXTRACTED,
            partialMsg: Localization.Bulk.PARTIAL_EXTRACTED
        });
    }

    /**
     * Handle bulk Delete Local action.
     * @param fileNames Array of file names to delete locally
     */
    async onBulkDeleteLocal(fileNames: string[]): Promise<void> {
        this._logger.info(`Bulk delete local requested for ${fileNames.length} files:`, fileNames);

        // Calculate skip count (selected files not eligible for this action)
        const skipCount = this.fileSelectionService.getSelectedFiles().size - fileNames.length;

        const confirmed = await this.confirmModalService.confirm({
            title: Localization.Modal.BULK_DELETE_LOCAL_TITLE,
            body: Localization.Modal.BULK_DELETE_LOCAL_MESSAGE(fileNames.length),
            okBtn: "Delete",
            okBtnClass: "btn btn-outline-danger",
            skipCount: skipCount > 0 ? skipCount : undefined
        });

        if (confirmed) {
            this._executeBulkAction("delete_local", fileNames, {
                successMsg: Localization.Bulk.SUCCESS_DELETED_LOCAL,
                partialMsg: Localization.Bulk.PARTIAL_DELETED_LOCAL
            });
        }
    }

    /**
     * Handle bulk Delete Remote action.
     * @param fileNames Array of file names to delete remotely
     */
    async onBulkDeleteRemote(fileNames: string[]): Promise<void> {
        this._logger.info(`Bulk delete remote requested for ${fileNames.length} files:`, fileNames);

        // Calculate skip count (selected files not eligible for this action)
        const skipCount = this.fileSelectionService.getSelectedFiles().size - fileNames.length;

        const confirmed = await this.confirmModalService.confirm({
            title: Localization.Modal.BULK_DELETE_REMOTE_TITLE,
            body: Localization.Modal.BULK_DELETE_REMOTE_MESSAGE(fileNames.length),
            okBtn: "Delete",
            okBtnClass: "btn btn-danger",
            skipCount: skipCount > 0 ? skipCount : undefined
        });

        if (confirmed) {
            this._executeBulkAction("delete_remote", fileNames, {
                successMsg: Localization.Bulk.SUCCESS_DELETED_REMOTE,
                partialMsg: Localization.Bulk.PARTIAL_DELETED_REMOTE
            });
        }
    }

    // =========================================================================
    // Private Helpers
    // =========================================================================

    /**
     * Execute a bulk action and handle the response with notifications.
     *
     * Uses beginOperation/endOperation to prevent race conditions with
     * pruneSelection() when the file list updates during the operation.
     */
    private _executeBulkAction(
        action: BulkAction,
        fileNames: string[],
        messages: {
            successMsg: (count: number) => string;
            partialMsg: (succeeded: number, failed: number) => string;
        }
    ): void {
        // Lock selection state to prevent pruneSelection race conditions
        this.fileSelectionService.beginOperation();

        // Show progress indicator for all bulk operations
        this.bulkOperationInProgress = true;
        this._cdr.markForCheck();

        this.bulkCommandService.executeBulkAction(action, fileNames).pipe(
            takeUntilDestroyed(this.destroyRef)
        ).subscribe({
            next: (result: BulkActionResult) => {
                this.bulkOperationInProgress = false;
                this._cdr.markForCheck();
                // Release the lock before clearing selection
                this.fileSelectionService.endOperation();
                this._handleBulkResult(result, messages);
                // Clear selection after action (even on partial failure)
                this.fileSelectionService.clearSelection();
                this._lastClickedFileName = null;
            },
            error: (err) => {
                this.bulkOperationInProgress = false;
                this._cdr.markForCheck();
                // Release the lock on error
                this.fileSelectionService.endOperation();
                this._logger.error("Bulk action error:", err);

                // Check if this is a transient error where retry makes sense
                // - Network errors (status 0)
                // - Rate limiting (status 429)
                // - Server errors (status >= 500)
                const isTransientError = !err.status || err.status === 429 || err.status >= 500;

                if (isTransientError) {
                    // Preserve selection for retry on transient errors
                    this._showNotification(
                        Notification.Level.DANGER,
                        Localization.Bulk.ERROR_RETRY("Request failed. Selection preserved for retry.")
                    );
                } else {
                    // Clear selection on validation errors (400) - user needs to fix something
                    this.fileSelectionService.clearSelection();
                    this._lastClickedFileName = null;
                    this._showNotification(
                        Notification.Level.DANGER,
                        Localization.Bulk.ERROR_RETRY("Request failed.")
                    );
                }
            }
        });
    }

    /**
     * Handle the result of a bulk action and show appropriate notification.
     */
    private _handleBulkResult(
        result: BulkActionResult,
        messages: {
            successMsg: (count: number) => string;
            partialMsg: (succeeded: number, failed: number) => string;
        }
    ): void {
        if (!result.success) {
            // Complete failure (request error)
            this._showNotification(
                Notification.Level.DANGER,
                Localization.Bulk.ERROR(result.errorMessage || "Unknown error")
            );
        } else if (result.allSucceeded && result.response) {
            // All succeeded
            this._showNotification(
                Notification.Level.SUCCESS,
                messages.successMsg(result.response.summary.succeeded)
            );
        } else if (result.response) {
            // Partial failure
            this._showNotification(
                Notification.Level.WARNING,
                messages.partialMsg(
                    result.response.summary.succeeded,
                    result.response.summary.failed
                )
            );
        }
    }

    /**
     * Show a notification to the user.
     */
    private _showNotification(level: Notification.Level, text: string): void {
        const notification = new Notification({
            level,
            text,
            dismissible: true
        });
        this.notificationService.show(notification);

        // Auto-dismiss success and warning notifications after a delay
        if (level === Notification.Level.SUCCESS || level === Notification.Level.WARNING) {
            setTimeout(() => {
                this.notificationService.hide(notification);
            }, 5000);
        }
    }

}
