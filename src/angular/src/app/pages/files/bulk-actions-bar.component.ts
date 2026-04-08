import {Component, Input, Output, EventEmitter, ChangeDetectionStrategy, OnChanges, SimpleChanges} from "@angular/core";
import {List} from "immutable";

import {ViewFile} from "../../services/files/view-file";

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
    private _cachedQueueableFiles: string[] = [];
    private _cachedStoppableFiles: string[] = [];
    private _cachedExtractableFiles: string[] = [];
    private _cachedLocallyDeletableFiles: string[] = [];
    private _cachedRemotelyDeletableFiles: string[] = [];

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
            .filter(f => f.name != null && this.selectedFiles.has(f.name))
            .toArray();

        // Compute action-specific lists in a single pass
        const queueable: string[] = [];
        const stoppable: string[] = [];
        const extractable: string[] = [];
        const locallyDeletable: string[] = [];
        const remotelyDeletable: string[] = [];

        for (const file of this._cachedSelectedViewFiles) {
            if (!file.name) { continue; }
            if (file.isQueueable) {
                queueable.push(file.name);
            }
            if (file.isStoppable) {
                stoppable.push(file.name);
            }
            // Match single-file logic: isExtractable AND isArchive
            if (file.isExtractable && file.isArchive) {
                extractable.push(file.name);
            }
            if (file.isLocallyDeletable) {
                locallyDeletable.push(file.name);
            }
            if (file.isRemotelyDeletable) {
                remotelyDeletable.push(file.name);
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
    @Output() queueAction = new EventEmitter<string[]>();

    /**
     * Emitted when user clicks Stop button.
     * Passes array of file names that are stoppable.
     */
    @Output() stopAction = new EventEmitter<string[]>();

    /**
     * Emitted when user clicks Extract button.
     * Passes array of file names that are extractable.
     */
    @Output() extractAction = new EventEmitter<string[]>();

    /**
     * Emitted when user clicks Delete Local button.
     * Passes array of file names that are locally deletable.
     */
    @Output() deleteLocalAction = new EventEmitter<string[]>();

    /**
     * Emitted when user clicks Delete Remote button.
     * Passes array of file names that are remotely deletable.
     */
    @Output() deleteRemoteAction = new EventEmitter<string[]>();

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
    get queueableFiles(): string[] {
        return this._cachedQueueableFiles;
    }

    /**
     * Get files that are stoppable (cached).
     */
    get stoppableFiles(): string[] {
        return this._cachedStoppableFiles;
    }

    /**
     * Get files that are extractable (cached).
     */
    get extractableFiles(): string[] {
        return this._cachedExtractableFiles;
    }

    /**
     * Get files that are locally deletable (cached).
     */
    get locallyDeletableFiles(): string[] {
        return this._cachedLocallyDeletableFiles;
    }

    /**
     * Get files that are remotely deletable (cached).
     */
    get remotelyDeletableFiles(): string[] {
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
