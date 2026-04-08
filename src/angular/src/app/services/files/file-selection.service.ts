import {Injectable, signal, computed} from "@angular/core";
import {toObservable} from "@angular/core/rxjs-interop";
import {Observable} from "rxjs";
import {map} from "rxjs/operators";

import {ViewFile} from "./view-file";

/**
 * FileSelectionService manages bulk file selection state using Angular signals.
 *
 * This service is separate from the single-file selection in ViewFileService
 * (which controls the details panel). This service manages checkbox-based
 * multi-file selection for bulk actions.
 *
 * Selection state:
 * - Selected files are tracked by name in a Set<string>
 *
 * Angular Signals Architecture (Session 16):
 * - Uses signals for fine-grained reactivity
 * - FileComponent uses computed() to derive its own selection state
 * - Only components whose selection actually changed will re-render
 * - Eliminates cascading checkbox effect on select-all
 *
 * Thread Safety (Session 18):
 * - operationInProgress signal prevents race conditions during bulk operations
 * - pruneSelection() is skipped while bulk operations are in progress
 * - Prevents selection state corruption when file list updates mid-operation
 */
@Injectable({
    providedIn: "root"
})
export class FileSelectionService {

    // Signal-based selection state (replaces BehaviorSubject)
    // Each mutation creates a new Set for immutability
    readonly selectedFiles = signal<Set<string>>(new Set());

    // Flag indicating a bulk operation is in progress
    // When true, pruneSelection() will be skipped to prevent race conditions
    private readonly _operationInProgress = signal<boolean>(false);
    readonly operationInProgress = this._operationInProgress.asReadonly();

    // Computed signals for derived state
    readonly selectedCount = computed(() => this.selectedFiles().size);
    readonly hasSelection = computed(() => this.selectedFiles().size > 0);

    // Observable for backwards compatibility with existing subscribers
    // Uses toObservable() to convert signal to RxJS observable
    readonly selectedFiles$ = toObservable(this.selectedFiles);

    constructor() {
        // Intentionally empty - signals initialized inline
    }

    // =========================================================================
    // Selection State Observables (for backwards compatibility)
    // =========================================================================

    /**
     * Observable of the selected file count.
     */
    get selectedCount$(): Observable<number> {
        return this.selectedFiles$.pipe(
            map(files => files.size)
        );
    }

    /**
     * Observable indicating if any files are selected.
     */
    get hasSelection$(): Observable<boolean> {
        return this.selectedFiles$.pipe(
            map(files => files.size > 0)
        );
    }

    // =========================================================================
    // Selection State Getters (synchronous)
    // =========================================================================

    /**
     * Get the current set of selected file names.
     */
    getSelectedFiles(): Set<string> {
        return new Set(this.selectedFiles());
    }

    /**
     * Get the current number of selected files.
     */
    getSelectedCount(): number {
        return this.selectedFiles().size;
    }

    /**
     * Check if a file is currently selected.
     * @param fileName The name of the file to check
     */
    isSelected(fileName: string): boolean {
        return this.selectedFiles().has(fileName);
    }

    // =========================================================================
    // Selection Modification Methods
    // =========================================================================

    /**
     * Select a single file.
     * @param fileName The name of the file to select
     */
    select(fileName: string): void {
        if (!this.selectedFiles().has(fileName)) {
            this.selectedFiles.update(set => {
                const newSet = new Set(set);
                newSet.add(fileName);
                return newSet;
            });
        }
    }

    /**
     * Deselect a single file.
     * @param fileName The name of the file to deselect
     */
    deselect(fileName: string): void {
        if (this.selectedFiles().has(fileName)) {
            this.selectedFiles.update(set => {
                const newSet = new Set(set);
                newSet.delete(fileName);
                return newSet;
            });
        }
    }

    /**
     * Toggle selection state of a file.
     * @param fileName The name of the file to toggle
     */
    toggle(fileName: string): void {
        if (this.selectedFiles().has(fileName)) {
            this.deselect(fileName);
        } else {
            this.select(fileName);
        }
    }

    /**
     * Select multiple files at once.
     * @param fileNames Array of file names to select
     */
    selectMultiple(fileNames: string[]): void {
        const currentSet = this.selectedFiles();
        const filesToAdd = fileNames.filter(f => !currentSet.has(f));
        if (filesToAdd.length > 0) {
            this.selectedFiles.update(set => {
                const newSet = new Set(set);
                filesToAdd.forEach(f => newSet.add(f));
                return newSet;
            });
        }
    }

    /**
     * Select all visible files (those currently in the filtered view).
     * @param visibleFiles List of currently visible ViewFiles
     */
    selectAllVisible(visibleFiles: ViewFile[]): void {
        const fileNames = visibleFiles.map(f => f.name).filter((n): n is string => n != null);
        this.selectMultiple(fileNames);
    }

    /**
     * Clear all selections and reset to initial state.
     */
    clearSelection(): void {
        if (this.selectedFiles().size > 0) {
            this.selectedFiles.set(new Set());
        }
    }

    /**
     * Replace the current selection with a new set of files.
     * @param fileNames Array of file names that should be selected
     */
    setSelection(fileNames: string[]): void {
        this.selectedFiles.set(new Set(fileNames));
    }

    /**
     * Select a range of files (for shift+click).
     * Replaces current selection with the range.
     * @param fileNames Array of file names in the range
     */
    selectRange(fileNames: string[]): void {
        this.setSelection(fileNames);
    }

    /**
     * Remove files from selection that no longer exist.
     * Called when the file list updates to clean up stale selections.
     *
     * NOTE: This method is skipped while a bulk operation is in progress
     * to prevent race conditions where the file list updates mid-operation.
     *
     * @param existingFileNames Set of file names that currently exist
     */
    pruneSelection(existingFileNames: Set<string>): void {
        // Skip pruning during bulk operations to prevent race conditions
        if (this._operationInProgress()) {
            return;
        }

        const currentSet = this.selectedFiles();
        const toRemove = Array.from(currentSet).filter(f => !existingFileNames.has(f));
        if (toRemove.length > 0) {
            this.selectedFiles.update(set => {
                const newSet = new Set(set);
                toRemove.forEach(f => newSet.delete(f));
                return newSet;
            });
        }
    }

    // =========================================================================
    // Bulk Operation Lock Methods
    // =========================================================================

    /**
     * Mark the start of a bulk operation.
     * While in progress, pruneSelection() will be skipped to prevent race conditions.
     */
    beginOperation(): void {
        this._operationInProgress.set(true);
    }

    /**
     * Mark the end of a bulk operation.
     * Allows pruneSelection() to run again on subsequent file list updates.
     */
    endOperation(): void {
        this._operationInProgress.set(false);
    }
}
