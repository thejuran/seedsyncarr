import {Component, ChangeDetectionStrategy, DestroyRef, inject} from "@angular/core";
import {AsyncPipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Observable, BehaviorSubject, combineLatest} from "rxjs";
import {distinctUntilChanged, map} from "rxjs/operators";

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
    nameFilter = "";
    currentPage = 1;
    readonly pageSize = 15;

    pagedFiles$: Observable<ViewFile[]>;
    totalPages$: Observable<number>;
    totalCount$: Observable<number>;

    private filterState$ = new BehaviorSubject<{segment: "all" | "active" | "errors", page: number}>({segment: "all", page: 1});
    private destroyRef = inject(DestroyRef);

    constructor(
        private viewFileService: ViewFileService,
        private viewFileOptionsService: ViewFileOptionsService,
    ) {
        // Derive segmented files from filteredFiles + segment (distinctUntilChanged avoids re-filtering on page-only changes)
        const segmentedFiles$ = combineLatest([
            this.viewFileService.filteredFiles,
            this.filterState$.pipe(
                map(s => s.segment),
                distinctUntilChanged()
            )
        ]).pipe(
            map(([files, segment]) => {
                if (segment === "all") { return files; }
                if (segment === "active") {
                    return files.filter(f =>
                        f.status === ViewFile.Status.DOWNLOADING ||
                        f.status === ViewFile.Status.QUEUED ||
                        f.status === ViewFile.Status.EXTRACTING
                    ).toList();
                }
                // errors
                return files.filter(f =>
                    f.status === ViewFile.Status.STOPPED ||
                    f.status === ViewFile.Status.DELETED
                ).toList();
            })
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
    }

    onSearchInput(value: string): void {
        this.nameFilter = value;
        this.viewFileOptionsService.setNameFilter(value);
    }

    onSegmentChange(segment: "all" | "active" | "errors"): void {
        this.activeSegment = segment;
        this.currentPage = 1;
        this.filterState$.next({segment, page: 1});
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
