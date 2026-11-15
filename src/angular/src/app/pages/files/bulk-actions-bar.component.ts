import {Component, Input, Output, EventEmitter, ChangeDetectionStrategy, OnChanges, SimpleChanges} from "@angular/core";
import {List} from "immutable";

import {ViewFile} from "../../services/files/view-file";
import {BulkFile, toBulkFile} from "../../services/server/bulk-command.service";

/**
 * Action counts for bulk operations.
 */
export interface BulkActionCounts {
    queueable: number;
    stoppable: number;
    extractable: number;
    locallyDeletable: number;
    remotelyDeletable: number;
}

/**
 * Bulk actions bar component that displays when files are selected.
 *
 * Shows action buttons with counts indicating how many selected files
 * are eligible for each action. Buttons are disabled when count is 0.
 *
 * Button order: Queue, Stop, Extract, Delete Local, Delete Remote
 *
 * Performance optimization: Action counts and file lists are cached
 * and only recomputed when inputs change, avoiding repeated iteration
 * through the file list on each template access.
 */
@Component({
    selector: "app-bulk-actions-bar",
    templateUrl: "./bulk-actions-bar.component.html",
    styleUrls: ["./bulk-actions-bar.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,

})
export class BulkActionsBarComponent implements OnChanges {

    /**
     * The list of currently visible (filtered) files.
     */
    @Input() visibleFiles: List<ViewFile> = List();

    /**
     * The set of currently selected file names.
     */
    @Input() selectedFiles: Set<string> = new Set();

    /**
     * Whether a bulk operation is currently in progress.
     */
    @Input() operationInProgress = false;

    /**
     * Emitted when user clicks Clear button to clear selection.
     */
    @Output() clearSelection = new EventEmitter<void>();

    // Cached computed values - recomputed only on input changes
    private _cachedSelectedViewFiles: ViewFile[] = [];
    private _cachedActionCounts: BulkActionCounts = {
        queueable: 0,
        stoppable: 0,
        extractable: 0,
        locallyDeletable: 0,
        remotelyDeletable: 0
    };
    private _cachedQueueableFiles: BulkFile[] = [];
    private _cachedStoppableFiles: BulkFile[] = [];
    private _cachedExtractableFiles: BulkFile[] = [];
    private _cachedLocallyDeletableFiles: BulkFile[] = [];
    private _cachedRemotelyDeletableFiles: BulkFile[] = [];

    ngOnChanges(changes: SimpleChanges): void {
        // Only recompute if visibleFiles or selectedFiles changed
        if (changes["visibleFiles"] || changes["selectedFiles"]) {
            this._recomputeCachedValues();
        }
    }

    /**
     * Recompute all cached values from current inputs.
     * This is called once per input change, avoiding repeated computation
     * when multiple getters access the same underlying data.
     */
    private _recomputeCachedValues(): void {
        // Compute selected view files once
        this._cachedSelectedViewFiles = this.visibleFiles
            .filter(f => f.name != null && this.selectedFiles.has(f.key))
            .toArray();

        // Compute action-specific lists in a single pass
        const queueable: BulkFile[] = [];
        const stoppable: BulkFile[] = [];
        const extractable: BulkFile[] = [];
        const locallyDeletable: BulkFile[] = [];
        const remotelyDeletable: BulkFile[] = [];

        for (const file of this._cachedSelectedViewFiles) {
            if (!file.name) { continue; }
            if (file.isQueueable) {
                queueable.push(toBulkFile(file.name, file.pairId));
            }
            if (file.isStoppable) {
                stoppable.push(toBulkFile(file.name, file.pairId));
            }
            // Match single-file logic: isExtractable AND isArchive
            if (file.isExtractable && file.isArchive) {
                extractable.push(toBulkFile(file.name, file.pairId));
            }
            if (file.isLocallyDeletable) {
                locallyDeletable.push(toBulkFile(file.name, file.pairId));
            }
            if (file.isRemotelyDeletable) {
                remotelyDeletable.push(toBulkFile(file.name, file.pairId));
            }
        }

        this._cachedQueueableFiles = queueable;
        this._cachedStoppableFiles = stoppable;
        this._cachedExtractableFiles = extractable;
        this._cachedLocallyDeletableFiles = locallyDeletable;
        this._cachedRemotelyDeletableFiles = remotelyDeletable;

        this._cachedActionCounts = {
            queueable: queueable.length,
            stoppable: stoppable.length,
            extractable: extractable.length,
            locallyDeletable: locallyDeletable.length,
            remotelyDeletable: remotelyDeletable.length
        };
    }

    /**
     * Emitted when user clicks Queue button.
     * Passes array of file names that are queueable.
     */
    @Output() queueAction = new EventEmitter<BulkFile[]>();

    /**
     * Emitted when user clicks Stop button.
     * Passes array of file names that are stoppable.
     */
    @Output() stopAction = new EventEmitter<BulkFile[]>();

    /**
     * Emitted when user clicks Extract button.
     * Passes array of file names that are extractable.
     */
    @Output() extractAction = new EventEmitter<BulkFile[]>();

    /**
     * Emitted when user clicks Delete Local button.
     * Passes array of file names that are locally deletable.
     */
    @Output() deleteLocalAction = new EventEmitter<BulkFile[]>();

    /**
     * Emitted when user clicks Delete Remote button.
     * Passes array of file names that are remotely deletable.
     */
    @Output() deleteRemoteAction = new EventEmitter<BulkFile[]>();

    /**
     * Check if any files are selected (determines bar visibility).
     */
    get hasSelection(): boolean {
        return this.selectedFiles.size > 0;
    }

    /**
     * Get the count of selected files.
     */
    get selectedCount(): number {
        return this.selectedFiles.size;
    }

    /**
     * Get the list of selected ViewFile objects (cached).
     */
    get selectedViewFiles(): ViewFile[] {
        return this._cachedSelectedViewFiles;
    }

    /**
     * Get action counts for all selected files (cached).
     */
    get actionCounts(): BulkActionCounts {
        return this._cachedActionCounts;
    }

    /**
     * Get files that are queueable (cached).
     */
    get queueableFiles(): BulkFile[] {
        return this._cachedQueueableFiles;
    }

    /**
     * Get files that are stoppable (cached).
     */
    get stoppableFiles(): BulkFile[] {
        return this._cachedStoppableFiles;
    }

    /**
     * Get files that are extractable (cached).
     */
    get extractableFiles(): BulkFile[] {
        return this._cachedExtractableFiles;
    }

    /**
     * Get files that are locally deletable (cached).
     */
    get locallyDeletableFiles(): BulkFile[] {
        return this._cachedLocallyDeletableFiles;
    }

    /**
     * Get files that are remotely deletable (cached).
     */
    get remotelyDeletableFiles(): BulkFile[] {
        return this._cachedRemotelyDeletableFiles;
    }

    /**
     * Handle Clear button click.
     */
    onClearClick(): void {
        this.clearSelection.emit();
    }

    /**
     * Handle Queue button click.
     */
    onQueueClick(): void {
        const files = this.queueableFiles;
        if (files.length > 0) {
            this.queueAction.emit(files);
        }
    }

    /**
     * Handle Stop button click.
     */
    onStopClick(): void {
        const files = this.stoppableFiles;
        if (files.length > 0) {
            this.stopAction.emit(files);
        }
    }

    /**
     * Handle Extract button click.
     */
    onExtractClick(): void {
        const files = this.extractableFiles;
        if (files.length > 0) {
            this.extractAction.emit(files);
        }
    }

    /**
     * Handle Delete Local button click.
     */
    onDeleteLocalClick(): void {
        const files = this.locallyDeletableFiles;
        if (files.length > 0) {
            this.deleteLocalAction.emit(files);
        }
    }

    /**
     * Handle Delete Remote button click.
     */
    onDeleteRemoteClick(): void {
        const files = this.remotelyDeletableFiles;
        if (files.length > 0) {
            this.deleteRemoteAction.emit(files);
        }
    }
}
