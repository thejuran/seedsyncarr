import {Component, ChangeDetectionStrategy, DestroyRef, inject} from "@angular/core";
import {AsyncPipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Observable, BehaviorSubject, combineLatest} from "rxjs";
import {map} from "rxjs/operators";

import {List} from "immutable";

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

    private segmentFilter$ = new BehaviorSubject<"all" | "active" | "errors">("all");
    private pageSubject = new BehaviorSubject<number>(1);
    private destroyRef = inject(DestroyRef);

    constructor(
        private viewFileService: ViewFileService,
        private viewFileOptionsService: ViewFileOptionsService,
    ) {
        // Derive segmented files from filteredFiles + segment filter
        const segmentedFiles$ = combineLatest([
            this.viewFileService.filteredFiles,
            this.segmentFilter$
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
        this.pagedFiles$ = combineLatest([segmentedFiles$, this.pageSubject]).pipe(
            map(([files, page]) => {
                const start = (page - 1) * this.pageSize;
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
        // Reset page before emitting segment to avoid stale-page intermediate slice
        this.currentPage = 1;
        this.pageSubject.next(1);
        this.segmentFilter$.next(segment);
    }

    goToPage(page: number): void {
        this.currentPage = page;
        this.pageSubject.next(page);
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
