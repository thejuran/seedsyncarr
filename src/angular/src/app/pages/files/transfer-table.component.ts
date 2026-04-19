import {Component, ChangeDetectionStrategy, ChangeDetectorRef, DestroyRef, HostListener, inject} from "@angular/core";
import {AsyncPipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Observable, BehaviorSubject, Subject, combineLatest} from "rxjs";
import {debounceTime, distinctUntilChanged, map, shareReplay} from "rxjs/operators";
import {List} from "immutable";

import {ViewFileService} from "../../services/files/view-file.service";
import {ViewFileOptionsService} from "../../services/files/view-file-options.service";
import {ViewFile} from "../../services/files/view-file";
import {FileSelectionService} from "../../services/files/file-selection.service";
import {BulkCommandService, BulkAction, BulkActionResult} from "../../services/server/bulk-command.service";
import {ConfirmModalService} from "../../services/utils/confirm-modal.service";
import {NotificationService} from "../../services/utils/notification.service";
import {Notification} from "../../services/utils/notification";
import {Localization} from "../../common/localization";
import {TransferRowComponent} from "./transfer-row.component";
import {BulkActionsBarComponent} from "./bulk-actions-bar.component";


@Component({
    selector: "app-transfer-table",
    templateUrl: "./transfer-table.component.html",
    styleUrls: ["./transfer-table.component.scss"],
    standalone: true,
    imports: [AsyncPipe, FormsModule, TransferRowComponent, BulkActionsBarComponent],
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class TransferTableComponent {

    activeSegment: "all" | "active" | "errors" = "all";
    activeSubStatus: ViewFile.Status | null = null;
    readonly ViewFileStatus = ViewFile.Status;
    nameFilter = "";
    currentPage = 1;
    readonly pageSize = 15;

    pagedFiles$: Observable<ViewFile[]>;
    totalPages$: Observable<number>;
    totalCount$: Observable<number>;

    pagedFilesList$!: Observable<List<ViewFile>>;
    selectedFiles$!: Observable<Set<string>>;
    headerCheckboxState$!: Observable<"none" | "some" | "all">;
    bulkOperationInProgress = false;

    // Template fallback constants for the `?? ...` defaults on the BulkActionsBar bindings.
    public readonly emptySet = new Set<string>();
    public readonly emptySetList = List<ViewFile>();

    private _lastClickedFileName: string | null = null;
    private _currentPagedFiles: List<ViewFile> = List();

    private filterState$ = new BehaviorSubject<{
        segment: "all" | "active" | "errors";
        subStatus: ViewFile.Status | null;
        page: number;
    }>({ segment: "all", subStatus: null, page: 1 });
    private searchInput$ = new Subject<string>();
    private destroyRef = inject(DestroyRef);

    constructor(
        private viewFileService: ViewFileService,
        private viewFileOptionsService: ViewFileOptionsService,
        public fileSelectionService: FileSelectionService,
        private bulkCommandService: BulkCommandService,
        private confirmModalService: ConfirmModalService,
        private notificationService: NotificationService,
        private _cdr: ChangeDetectorRef,
    ) {
        // Derive segmented files from filteredFiles + filter state (segment + optional sub-status)
        const segmentedFiles$ = combineLatest([
            this.viewFileService.filteredFiles,
            this.filterState$.pipe(
                map(s => ({ segment: s.segment, subStatus: s.subStatus })),
                distinctUntilChanged((a, b) => a.segment === b.segment && a.subStatus === b.subStatus)
            )
        ]).pipe(
            map(([files, state]) => {
                if (state.subStatus != null && state.segment !== "all") {
                    return files.filter(f => f.status === state.subStatus).toList();
                }
                if (state.segment === "active") {
                    return files.filter(f =>
                        f.status === ViewFile.Status.DOWNLOADING ||
                        f.status === ViewFile.Status.QUEUED ||
                        f.status === ViewFile.Status.EXTRACTING
                    ).toList();
                }
                if (state.segment === "errors") {
                    return files.filter(f =>
                        f.status === ViewFile.Status.STOPPED ||
                        f.status === ViewFile.Status.DELETED
                    ).toList();
                }
                return files.toList();
            }),
            shareReplay(1)
        );

        // Paged files derived from segmented + page
        this.pagedFiles$ = combineLatest([segmentedFiles$, this.filterState$]).pipe(
            map(([files, state]) => {
                const start = (state.page - 1) * this.pageSize;
                return files.slice(start, start + this.pageSize).toArray();
            })
        );

        this.totalPages$ = segmentedFiles$.pipe(
            map(files => Math.max(1, Math.ceil(files.size / this.pageSize)))
        );

        this.totalCount$ = segmentedFiles$.pipe(
            map(files => files.size)
        );

        this.pagedFilesList$ = this.pagedFiles$.pipe(map(arr => List(arr)), shareReplay(1));
        this.selectedFiles$ = this.fileSelectionService.selectedFiles$;

        this.pagedFilesList$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(files => {
            this._currentPagedFiles = files;
        });

        this.headerCheckboxState$ = combineLatest([
            this.pagedFilesList$,
            this.fileSelectionService.selectedFiles$
        ]).pipe(
            map(([files, selectedFiles]) => {
                if (files.size === 0 || selectedFiles.size === 0) { return "none" as const; }
                const visibleSelectedCount = files.filter(f => f.name != null && selectedFiles.has(f.name)).size;
                if (visibleSelectedCount === 0) { return "none" as const; }
                if (visibleSelectedCount === files.size) { return "all" as const; }
                return "some" as const;
            })
        );

        // Reset page and clear selection when filter options change (D-04)
        this.viewFileOptionsService.options
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(() => {
                this.goToPage(1);
                this.fileSelectionService.clearSelection();
                this._lastClickedFileName = null;
            });

        // Debounce search input to avoid expensive recalculations per keystroke
        this.searchInput$
            .pipe(
                debounceTime(300),
                distinctUntilChanged(),
                takeUntilDestroyed(this.destroyRef)
            )
            .subscribe(value => {
                this.viewFileOptionsService.setNameFilter(value);
            });
    }

    onSearchInput(value: string): void {
        this.nameFilter = value;
        this.searchInput$.next(value);
    }

    onSegmentChange(segment: "all" | "active" | "errors"): void {
        if (segment !== "all" && this.activeSegment === segment) {
            // Second click on same expandable parent — collapse to All
            this.activeSegment = "all";
            this.activeSubStatus = null;
            this.currentPage = 1;
            this.filterState$.next({ segment: "all", subStatus: null, page: 1 });
        } else {
            this.activeSegment = segment;
            this.activeSubStatus = null;
            this.currentPage = 1;
            this.filterState$.next({ segment, subStatus: null, page: 1 });
        }
        this.fileSelectionService.clearSelection();
        this._lastClickedFileName = null;
    }

    onSubStatusChange(status: ViewFile.Status): void {
        if (this.activeSegment === "all") {
            return;
        }
        if (this.activeSubStatus === status) {
            // Second click — deselect, show full parent segment
            this.activeSubStatus = null;
            this.currentPage = 1;
            this.filterState$.next({ segment: this.activeSegment, subStatus: null, page: 1 });
            this.fileSelectionService.clearSelection();
            this._lastClickedFileName = null;
            return;
        }
        this.activeSubStatus = status;
        this.currentPage = 1;
        this.filterState$.next({
            segment: this.activeSegment,
            subStatus: status,
            page: 1
        });
        this.fileSelectionService.clearSelection();
        this._lastClickedFileName = null;
    }

    goToPage(page: number): void {
        this.currentPage = page;
        this.filterState$.next({...this.filterState$.value, page});
        this.fileSelectionService.clearSelection();
        this._lastClickedFileName = null;
    }

    onPrevPage(): void {
        if (this.currentPage > 1) {
            this.goToPage(this.currentPage - 1);
        }
    }

    onNextPage(totalPages: number): void {
        if (this.currentPage < totalPages) {
            this.goToPage(this.currentPage + 1);
        }
    }

    private _cachedPageNumbers: number[] = [1];
    private _cachedTotalPages = 1;

    getPageNumbers(totalPages: number): number[] {
        if (totalPages !== this._cachedTotalPages) {
            this._cachedTotalPages = totalPages;
            this._cachedPageNumbers = Array.from({length: totalPages}, (_, i) => i + 1);
        }
        return this._cachedPageNumbers;
    }

    trackByName(index: number, file: ViewFile): string {
        return file.name ?? `__row_${index}`;
    }

    @HostListener("document:keydown", ["$event"])
    onKeyDown(event: KeyboardEvent): void {
        if (event.key === "Escape" && !this._isInputElement(event.target)) {
            this.fileSelectionService.clearSelection();
            this._lastClickedFileName = null;
        }
    }

    private _isInputElement(target: EventTarget | null): boolean {
        if (!target) { return false; }
        const tag = (target as HTMLElement).tagName?.toLowerCase();
        return tag === "input" || tag === "textarea" || tag === "select";
    }

    onCheckboxToggle(event: {file: ViewFile, shiftKey: boolean}): void {
        if (event.shiftKey && this._lastClickedFileName !== null) {
            const lastIndex = this._currentPagedFiles.findIndex(f => f.name === this._lastClickedFileName);
            const currentIndex = this._currentPagedFiles.findIndex(f => f.name === event.file.name);
            if (lastIndex !== -1 && currentIndex !== -1) {
                const start = Math.min(lastIndex, currentIndex);
                const end = Math.max(lastIndex, currentIndex);
                const rangeNames: string[] = [];
                for (let i = start; i <= end; i++) {
                    const file = this._currentPagedFiles.get(i);
                    if (file?.name) { rangeNames.push(file.name); }
                }
                this.fileSelectionService.setSelection(rangeNames);
            } else {
                this.fileSelectionService.toggle(event.file.name!);
                this._lastClickedFileName = event.file.name ?? null;
            }
        } else {
            this.fileSelectionService.toggle(event.file.name!);
            this._lastClickedFileName = event.file.name ?? null;
        }
    }

    onHeaderCheckboxClick(): void {
        const selectedFiles = this.fileSelectionService.getSelectedFiles();
        const files = this._currentPagedFiles;
        const visibleSelectedCount = files.filter(f => f.name != null && selectedFiles.has(f.name)).size;
        if (visibleSelectedCount === files.size && files.size > 0) {
            this.fileSelectionService.clearSelection();
            this._lastClickedFileName = null;
        } else {
            this.fileSelectionService.selectAllVisible(files.toArray());
        }
    }

    onClearSelection(): void {
        this.fileSelectionService.clearSelection();
        this._lastClickedFileName = null;
    }

    onBulkQueue(fileNames: string[]): void {
        this._executeBulkAction("queue", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_QUEUED,
            partialMsg: Localization.Bulk.PARTIAL_QUEUED
        });
    }

    onBulkStop(fileNames: string[]): void {
        this._executeBulkAction("stop", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_STOPPED,
            partialMsg: Localization.Bulk.PARTIAL_STOPPED
        });
    }

    onBulkExtract(fileNames: string[]): void {
        this._executeBulkAction("extract", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_EXTRACTED,
            partialMsg: Localization.Bulk.PARTIAL_EXTRACTED
        });
    }

    async onBulkDeleteLocal(fileNames: string[]): Promise<void> {
        const skipCount = this.fileSelectionService.getSelectedFiles().size - fileNames.length;
        const body = Localization.Modal.BULK_DELETE_LOCAL_MESSAGE(fileNames.length)
                     + this._buildPreviewSuffix(fileNames);
        const confirmed = await this.confirmModalService.confirm({
            title: Localization.Modal.BULK_DELETE_LOCAL_TITLE,
            body,
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

    async onBulkDeleteRemote(fileNames: string[]): Promise<void> {
        const skipCount = this.fileSelectionService.getSelectedFiles().size - fileNames.length;
        const body = Localization.Modal.BULK_DELETE_REMOTE_MESSAGE(fileNames.length)
                     + this._buildPreviewSuffix(fileNames);
        const confirmed = await this.confirmModalService.confirm({
            title: Localization.Modal.BULK_DELETE_REMOTE_TITLE,
            body,
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

    private _buildPreviewSuffix(fileNames: string[]): string {
        if (fileNames.length === 0) { return ""; }
        const PREVIEW_LIMIT = 5;
        if (fileNames.length <= PREVIEW_LIMIT) {
            return "\n\n" + fileNames.join("\n");
        }
        return "\n\n" + fileNames.slice(0, PREVIEW_LIMIT).join("\n")
               + "\n… and " + (fileNames.length - PREVIEW_LIMIT) + " more";
    }

    private _executeBulkAction(
        action: BulkAction,
        fileNames: string[],
        messages: {
            successMsg: (count: number) => string;
            partialMsg: (succeeded: number, failed: number) => string;
        }
    ): void {
        this.fileSelectionService.beginOperation();
        this.bulkOperationInProgress = true;
        this._cdr.markForCheck();

        this.bulkCommandService.executeBulkAction(action, fileNames).pipe(
            takeUntilDestroyed(this.destroyRef)
        ).subscribe({
            next: (result: BulkActionResult) => {
                this.bulkOperationInProgress = false;
                this._cdr.markForCheck();
                this.fileSelectionService.endOperation();
                this._handleBulkResult(result, messages);
                this.fileSelectionService.clearSelection();
                this._lastClickedFileName = null;
            },
            error: (err) => {
                this.bulkOperationInProgress = false;
                this._cdr.markForCheck();
                this.fileSelectionService.endOperation();
                const isTransient = !err.status || err.status === 429 || err.status >= 500;
                if (isTransient) {
                    this._showNotification(
                        Notification.Level.DANGER,
                        Localization.Bulk.ERROR_RETRY("Request failed. Selection preserved for retry.")
                    );
                } else {
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

    private _handleBulkResult(
        result: BulkActionResult,
        messages: {
            successMsg: (count: number) => string;
            partialMsg: (succeeded: number, failed: number) => string;
        }
    ): void {
        if (!result.success) {
            this._showNotification(
                Notification.Level.DANGER,
                Localization.Bulk.ERROR(result.errorMessage || "Unknown error")
            );
        } else if (result.allSucceeded && result.response) {
            this._showNotification(
                Notification.Level.SUCCESS,
                messages.successMsg(result.response.summary.succeeded)
            );
        } else if (result.response) {
            this._showNotification(
                Notification.Level.WARNING,
                messages.partialMsg(result.response.summary.succeeded, result.response.summary.failed)
            );
        }
    }

    private _showNotification(level: Notification.Level, text: string): void {
        const notification = new Notification({ level, text, dismissible: true });
        this.notificationService.show(notification);
        if (level === Notification.Level.SUCCESS || level === Notification.Level.WARNING) {
            setTimeout(() => { this.notificationService.hide(notification); }, 5000);
        }
    }
}
