import {Component, ChangeDetectionStrategy, DestroyRef, inject} from "@angular/core";
import {AsyncPipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Observable, BehaviorSubject, Subject, combineLatest} from "rxjs";
import {debounceTime, distinctUntilChanged, map, shareReplay} from "rxjs/operators";

import {ViewFileService} from "../../services/files/view-file.service";
import {ViewFileOptionsService} from "../../services/files/view-file-options.service";
import {ViewFile} from "../../services/files/view-file";
import {TransferRowComponent} from "./transfer-row.component";


@Component({
    selector: "app-transfer-table",
    templateUrl: "./transfer-table.component.html",
    styleUrls: ["./transfer-table.component.scss"],
    standalone: true,
    imports: [AsyncPipe, FormsModule, TransferRowComponent],
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
                if (state.subStatus != null) {
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
                return files;
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

        // Reset page when filter options change
        this.viewFileOptionsService.options
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(() => {
                this.goToPage(1);
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
    }

    onSubStatusChange(status: ViewFile.Status): void {
        if (this.activeSubStatus === status) {
            // Second click — deselect, show full parent segment
            this.activeSubStatus = null;
            this.currentPage = 1;
            this.filterState$.next({ segment: this.activeSegment, subStatus: null, page: 1 });
            return;
        }
        this.activeSubStatus = status;
        this.currentPage = 1;
        this.filterState$.next({
            segment: this.activeSegment,
            subStatus: status,
            page: 1
        });
    }

    goToPage(page: number): void {
        this.currentPage = page;
        this.filterState$.next({...this.filterState$.value, page});
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

    getPageNumbers(totalPages: number): number[] {
        return Array.from({length: totalPages}, (_, i) => i + 1);
    }

    trackByName(index: number, file: ViewFile): string {
        return file.name ?? `__row_${index}`;
    }
}
