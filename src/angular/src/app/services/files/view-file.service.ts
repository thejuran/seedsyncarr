import {Injectable, OnDestroy} from "@angular/core";
import {Observable, BehaviorSubject, Subject} from "rxjs";
import {takeUntil} from "rxjs/operators";

import * as Immutable from "immutable";

import {LoggerService} from "../utils/logger.service";
import {ModelFile} from "./model-file";
import {ModelFileService} from "./model-file.service";
import {ViewFile} from "./view-file";
import {MOCK_MODEL_FILES} from "./mock-model-files";
import {StreamServiceRegistry} from "../base/stream-service.registry";
import {FileSelectionService} from "./file-selection.service";


/**
 * Interface defining filtering criteria for view files
 */
export interface ViewFileFilterCriteria {
    meetsCriteria(viewFile: ViewFile): boolean;
}


/**
 * Interface for sorting view files
 */
export type ViewFileComparator = (a: ViewFile, b: ViewFile) => number;


/**
 * ViewFileService class provides the store of view files.
 * It implements the observable service pattern to push updates
 * as they become available.
 *
 * The view model needs to be ordered and have fast lookup/update.
 * Unfortunately, there exists no immutable SortedMap structure.
 * This class stores the following data structures:
 *    1. files: List(ViewFile)
 *              ViewFiles sorted in the display order
 *    2. indices: Map(name, index)
 *                Maps name to its index in sortedList
 * The runtime complexity of operations is:
 *    1. Update w/o state change:
 *          O(1) to find index and update the sorted list
 *    2. Updates w/ state change:
 *          O(1) to find index and update the sorted list
 *          O(n log n) to sort list (might be faster since
 *                     list is mostly sorted already??)
 *          O(n) to update indexMap
 *    3. Add:
 *          O(1) to add to list
 *          O(n log n) to sort list (might be faster since
 *                     list is mostly sorted already??)
 *          O(n) to update indexMap
 *    4. Remove:
 *          O(n) to remove from sorted list
 *          O(n) to update indexMap
 *
 * Filtering:
 *      This service also supports providing a filtered list of view files.
 *      The strategy of using pipes to filter at the component level is not
 *      recommended by Angular: https://angular.io/guide/pipes#appendix-no
 *      -filterpipe-or-orderbypipe
 *      Instead, we provide a separate filtered observer.
 *      Filtering is controlled via a single filter criteria. Advanced filters
 *      need to be built outside the service (see ViewFileFilterService)
 */
@Injectable()
export class ViewFileService implements OnDestroy {

    private readonly USE_MOCK_MODEL = false;
    private destroy$ = new Subject<void>();

    private modelFileService: ModelFileService;

    private _files: Immutable.List<ViewFile> = Immutable.List([]);
    private _filesSubject: BehaviorSubject<Immutable.List<ViewFile>> = new BehaviorSubject(this._files);
    private _filteredFilesSubject: BehaviorSubject<Immutable.List<ViewFile>> = new BehaviorSubject(this._files);
    private _indices: Map<string, number> = new Map<string, number>();

    private _prevModelFiles: Immutable.Map<string, ModelFile> = Immutable.Map<string, ModelFile>();

    private _filterCriteria: ViewFileFilterCriteria | null = null;
    private _sortComparator: ViewFileComparator | null = null;

    constructor(private _logger: LoggerService,
                private _streamServiceRegistry: StreamServiceRegistry,
                private _fileSelectionService: FileSelectionService) {
        this.modelFileService = _streamServiceRegistry.modelFileService;
        const _viewFileService = this;

        if (!this.USE_MOCK_MODEL) {
            this.modelFileService.files
                .pipe(takeUntil(this.destroy$))
                .subscribe({
                    next: modelFiles => {
                        const t0 = performance.now();
                        _viewFileService.buildViewFromModelFiles(modelFiles);
                        const t1 = performance.now();
                        this._logger.debug("ViewFile creation took", (t1 - t0).toFixed(0), "ms");
                    }
                });
        } else {
            // For layout/style testing
            this.buildViewFromModelFiles(MOCK_MODEL_FILES);
        }
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    private buildViewFromModelFiles(modelFiles: Immutable.Map<string, ModelFile>): void {
        this._logger.debug("Received next model files");

        // Diff the previous domain model with the current domain model, then apply
        // those changes to the view model
        // This is a roughly O(2N) operation on every update, so won't scale well
        // But should be fine for small models
        // A more scalable solution would be to subscribe to domain model updates
        let newViewFiles = this._files;

        const addedNames: string[] = [];
        const removedNames: string[] = [];
        const updatedNames: string[] = [];
        // Loop through old model to find deletions
        this._prevModelFiles.keySeq().forEach(
            name => {
                if (!modelFiles.has(name)) { removedNames.push(name); }
            }
        );
        // Loop through new model to find additions and updates
        modelFiles.keySeq().forEach(
            name => {
                if (!this._prevModelFiles.has(name)) {
                    addedNames.push(name);
                } else if (!Immutable.is(modelFiles.get(name), this._prevModelFiles.get(name))) {
                    updatedNames.push(name);
                }
            }
        );

        let reSort = false;
        let updateIndices = false;
        // Do the updates first before indices change (re-sort may be required)
        updatedNames.forEach(
            name => {
                const index = this._indices.get(name)!;
                const oldViewFile = newViewFiles.get(index) as ViewFile;
                const newViewFile = ViewFileService.createViewFile(modelFiles.get(name)!, !!oldViewFile.isSelected);
                newViewFiles = newViewFiles.set(index, newViewFile);
                if (this._sortComparator != null && this._sortComparator(oldViewFile, newViewFile) !== 0) {
                    reSort = true;
                }
            }
        );
        // Do the adds (requires re-sort)
        addedNames.forEach(
            name => {
                reSort = true;
                const viewFile = ViewFileService.createViewFile(modelFiles.get(name)!);
                newViewFiles = newViewFiles.push(viewFile);
                this._indices.set(name, newViewFiles.size - 1);
            }
        );
        // Do the removes (no re-sort required)
        removedNames.forEach(
            name => {
                updateIndices = true;
                const index = newViewFiles.findIndex(value => value.name === name);
                newViewFiles = newViewFiles.remove(index);
                this._indices.delete(name);
            }
        );

        if (reSort && this._sortComparator != null) {
            this._logger.debug("Re-sorting view files");
            newViewFiles = newViewFiles.sort(this._sortComparator).toList();
        }
        if (updateIndices || reSort) {
            this._indices.clear();
            newViewFiles.forEach(
                (value, index) => this._indices.set(value.name!, index!)
            );
        }

        this._files = newViewFiles;
        this.pushViewFiles();
        this._prevModelFiles = modelFiles;
        this._logger.debug("New view model: %O", this._files.toJS());
    }

    get files(): Observable<Immutable.List<ViewFile>> {
        return this._filesSubject.asObservable();
    }

    get filteredFiles(): Observable<Immutable.List<ViewFile>> {
        return this._filteredFilesSubject.asObservable();
    }

    /**
     * Set a file to be in selected state
     * @param {ViewFile} file
     */
    public setSelected(file: ViewFile): void {
        // Find the selected file, if any
        // Note: we can optimize this by storing an additional
        //       state that tracks the selected file
        //       but that would duplicate state and can introduce
        //       bugs, so we just search instead
        let viewFiles = this._files;
        const unSelectIndex = viewFiles.findIndex(value => !!value.isSelected);

        // Unset the previously selected file, if any
        if (unSelectIndex >= 0) {
            let unSelectViewFile = viewFiles.get(unSelectIndex)!;

            // Do nothing if file is already selected
            if (unSelectViewFile.name === file.name) { return; }

            unSelectViewFile = new ViewFile(unSelectViewFile.set("isSelected", false));
            viewFiles = viewFiles.set(unSelectIndex, unSelectViewFile);
        }

        // Set the new selected file
        if (this._indices.has(file.name!)) {
            const index = this._indices.get(file.name!)!;
            let viewFile = viewFiles.get(index) as ViewFile;
            viewFile = new ViewFile(viewFile.set("isSelected", true));
            viewFiles = viewFiles.set(index, viewFile);
        } else {
            this._logger.error("Can't find file to select: " + file.name);
        }

        // Send update
        this._files = viewFiles;
        this.pushViewFiles();
    }

    /**
     * Un-select the currently selected file
     */
    public unsetSelected(): void {
        // Unset the previously selected file, if any
        let viewFiles = this._files;
        const unSelectIndex = viewFiles.findIndex(value => !!value.isSelected);

        // Unset the previously selected file, if any
        if (unSelectIndex >= 0) {
            let unSelectViewFile = viewFiles.get(unSelectIndex)!;

            unSelectViewFile = new ViewFile(unSelectViewFile.set("isSelected", false));
            viewFiles = viewFiles.set(unSelectIndex, unSelectViewFile);

            // Send update
            this._files = viewFiles;
            this.pushViewFiles();
        }
    }

    /**
     * Set a new filter criteria.
     * Clears bulk file selection when filter changes.
     * @param {ViewFileFilterCriteria} criteria
     */
    public setFilterCriteria(criteria: ViewFileFilterCriteria | null): void {
        this._filterCriteria = criteria;
        this._fileSelectionService.clearSelection();
        this.pushViewFiles();
    }

    /**
     * Sets a new comparator.
     * Clears bulk file selection when sort changes.
     * @param {ViewFileComparator} comparator
     */
    public setComparator(comparator: ViewFileComparator | null): void {
        this._sortComparator = comparator;
        this._fileSelectionService.clearSelection();

        // Re-sort and regenerate index cache
        this._logger.debug("Re-sorting view files");
        let newViewFiles = this._files;
        if (this._sortComparator != null) {
            newViewFiles = newViewFiles.sort(this._sortComparator).toList();
        }
        this._files = newViewFiles;
        this._indices.clear();
        newViewFiles.forEach(
            (value, index) => this._indices.set(value.name!, index!)
        );

        this.pushViewFiles();
    }

    private static createViewFile(modelFile: ModelFile, isSelected: boolean = false): ViewFile {
        // Use zero for unknown sizes
        let localSize: number = modelFile.local_size;
        if (localSize == null) {
            localSize = 0;
        }
        let remoteSize: number = modelFile.remote_size;
        if (remoteSize == null) {
            remoteSize = 0;
        }
        const percentDownloaded: number = remoteSize > 0
            ? Math.trunc(100.0 * localSize / remoteSize)
            : 100;

        // Translate the status
        let status = null;
        switch (modelFile.state) {
            case ModelFile.State.DEFAULT: {
                if (localSize > 0 && remoteSize > 0) {
                    status = ViewFile.Status.STOPPED;
                } else {
                    status = ViewFile.Status.DEFAULT;
                }
                break;
            }
            case ModelFile.State.QUEUED: {
                status = ViewFile.Status.QUEUED;
                break;
            }
            case ModelFile.State.DOWNLOADING: {
                status = ViewFile.Status.DOWNLOADING;
                break;
            }
            case ModelFile.State.DOWNLOADED: {
                status = ViewFile.Status.DOWNLOADED;
                break;
            }
            case ModelFile.State.DELETED: {
                status = ViewFile.Status.DELETED;
                break;
            }
            case ModelFile.State.EXTRACTING: {
                status = ViewFile.Status.EXTRACTING;
                break;
            }
            case ModelFile.State.EXTRACTED: {
                status = ViewFile.Status.EXTRACTED;
                break;
            }
        }

        const isQueueable: boolean = status === ViewFile.Status.DELETED
                                    || ([ViewFile.Status.DEFAULT,
                                         ViewFile.Status.STOPPED].includes(status)
                                        && remoteSize > 0);
        const isStoppable: boolean = [ViewFile.Status.QUEUED,
                                    ViewFile.Status.DOWNLOADING].includes(status);
        const isExtractable: boolean = [ViewFile.Status.DEFAULT,
                                    ViewFile.Status.STOPPED,
                                    ViewFile.Status.DOWNLOADED,
                                    ViewFile.Status.EXTRACTED].includes(status)
                                    && localSize > 0;
        const isLocallyDeletable: boolean = [ViewFile.Status.DEFAULT,
                                    ViewFile.Status.STOPPED,
                                    ViewFile.Status.DOWNLOADED,
                                    ViewFile.Status.EXTRACTED].includes(status)
                                    && localSize > 0;
        const isRemotelyDeletable: boolean = status === ViewFile.Status.DELETED
                                    || ([ViewFile.Status.DEFAULT,
                                         ViewFile.Status.STOPPED,
                                         ViewFile.Status.DOWNLOADED,
                                         ViewFile.Status.EXTRACTED].includes(status)
                                        && remoteSize > 0);

        return new ViewFile({
            name: modelFile.name,
            isDir: modelFile.is_dir,
            localSize: localSize,
            remoteSize: remoteSize,
            percentDownloaded: percentDownloaded,
            status: status,
            downloadingSpeed: modelFile.downloading_speed,
            eta: modelFile.eta,
            fullPath: modelFile.full_path,
            isArchive: modelFile.is_extractable,
            isSelected: isSelected,
            isQueueable: isQueueable,
            isStoppable: isStoppable,
            isExtractable: isExtractable,
            isLocallyDeletable: isLocallyDeletable,
            isRemotelyDeletable: isRemotelyDeletable,
            localCreatedTimestamp: modelFile.local_created_timestamp,
            localModifiedTimestamp: modelFile.local_modified_timestamp,
            remoteCreatedTimestamp: modelFile.remote_created_timestamp,
            remoteModifiedTimestamp: modelFile.remote_modified_timestamp,
            importStatus: ViewFileService.mapImportStatus(modelFile.import_status)
        });
    }

    private static mapImportStatus(status: ModelFile.ImportStatus): ViewFile.ImportStatus {
        switch (status) {
            case ModelFile.ImportStatus.IMPORTED:
                return ViewFile.ImportStatus.IMPORTED;
            default:
                return ViewFile.ImportStatus.NONE;
        }
    }

    private pushViewFiles(): void {
        // Unfiltered files
        this._filesSubject.next(this._files);

        // Filtered files
        let filteredFiles = this._files;
        if (this._filterCriteria != null) {
            const criteria = this._filterCriteria;
            filteredFiles = Immutable.List<ViewFile>(
                this._files.filter(f => criteria.meetsCriteria(f))
            );
        }
        this._filteredFilesSubject.next(filteredFiles);
    }
}
