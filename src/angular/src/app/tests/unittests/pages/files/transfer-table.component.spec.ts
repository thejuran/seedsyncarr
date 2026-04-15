import {ComponentFixture, fakeAsync, TestBed, tick} from "@angular/core/testing";
import {BehaviorSubject, Observable} from "rxjs";

import * as Immutable from "immutable";

import {TransferTableComponent} from "../../../../pages/files/transfer-table.component";
import {ViewFileService} from "../../../../services/files/view-file.service";
import {ViewFileOptionsService} from "../../../../services/files/view-file-options.service";
import {ViewFile} from "../../../../services/files/view-file";
import {ViewFileOptions} from "../../../../services/files/view-file-options";


// Simplified template for unit testing — mirrors key structural elements
const TEST_TEMPLATE = `
<div class="table-header">
  <div class="search-box">
    <i class="fa fa-search search-icon"></i>
    <input type="search" class="search-input" [value]="nameFilter" (input)="onSearchInput($any($event.target).value)">
  </div>
  <div class="segment-filters">
    <button class="btn-segment" [class.active]="activeSegment === 'all'" (click)="onSegmentChange('all')">All</button>
    <button class="btn-segment"
            [class.btn-segment--parent-active]="activeSegment === 'active' && activeSubStatus === null"
            [class.btn-segment--parent-expanded]="activeSegment === 'active' && activeSubStatus !== null"
            (click)="onSegmentChange('active')">Active</button>
    @if (activeSegment === 'active') {
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.DOWNLOADING" (click)="onSubStatusChange(ViewFileStatus.DOWNLOADING)">Syncing</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.QUEUED" (click)="onSubStatusChange(ViewFileStatus.QUEUED)">Queued</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.EXTRACTING" (click)="onSubStatusChange(ViewFileStatus.EXTRACTING)">Extracting</button>
    }
    <button class="btn-segment"
            [class.btn-segment--parent-active]="activeSegment === 'errors' && activeSubStatus === null"
            [class.btn-segment--parent-expanded]="activeSegment === 'errors' && activeSubStatus !== null"
            (click)="onSegmentChange('errors')">Errors</button>
    @if (activeSegment === 'errors') {
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.STOPPED" (click)="onSubStatusChange(ViewFileStatus.STOPPED)">Failed</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.DELETED" (click)="onSubStatusChange(ViewFileStatus.DELETED)">Deleted</button>
    }
  </div>
</div>
@if ({paged: pagedFiles$ | async, totalPages: totalPages$ | async, totalCount: totalCount$ | async}; as vm) {
<table class="transfer-table">
  <thead><tr>
    <th>Name</th><th>Status</th><th>Progress</th><th>Speed</th><th>ETA</th><th>Size</th>
  </tr></thead>
  <tbody>
    @for (file of (vm.paged ?? []); track file.name) {
      <tr class="file-row">{{ file.name }}</tr>
    }
  </tbody>
</table>
<div class="pagination-footer">
  <span class="page-info">Page {{ currentPage }} of {{ vm.totalPages }} ({{ vm.totalCount }} files)</span>
  <button class="prev-btn" [disabled]="currentPage <= 1" (click)="onPrevPage()">Prev</button>
  <button class="next-btn" [disabled]="currentPage >= (vm.totalPages ?? 1)" (click)="onNextPage(vm.totalPages ?? 1)">Next</button>
</div>
}
`;


class MockViewFileService {
    private _filteredFiles$ = new BehaviorSubject<Immutable.List<ViewFile>>(Immutable.List([]));

    get filteredFiles(): Observable<Immutable.List<ViewFile>> {
        return this._filteredFiles$.asObservable();
    }

    pushFiles(files: ViewFile[]): void {
        this._filteredFiles$.next(Immutable.List(files));
    }
}

class MockViewFileOptionsService {
    private _options$ = new BehaviorSubject<ViewFileOptions>(new ViewFileOptions({}));

    get options(): Observable<ViewFileOptions> {
        return this._options$.asObservable();
    }

    setNameFilter = jasmine.createSpy("setNameFilter");
    setSelectedStatusFilter = jasmine.createSpy("setSelectedStatusFilter");
}


function makeFile(name: string, status: ViewFile.Status, opts: Partial<ViewFile> = {}): ViewFile {
    return new ViewFile({
        name,
        status,
        remoteSize: 1000,
        localSize: 500,
        percentDownloaded: 50,
        ...opts
    });
}


describe("TransferTableComponent", () => {
    let component: TransferTableComponent;
    let fixture: ComponentFixture<TransferTableComponent>;
    let mockFileService: MockViewFileService;
    let mockOptionsService: MockViewFileOptionsService;

    beforeEach(async () => {
        mockFileService = new MockViewFileService();
        mockOptionsService = new MockViewFileOptionsService();

        await TestBed.configureTestingModule({
            imports: [TransferTableComponent],
            providers: [
                {provide: ViewFileService, useValue: mockFileService},
                {provide: ViewFileOptionsService, useValue: mockOptionsService}
            ]
        })
        .overrideTemplate(TransferTableComponent, TEST_TEMPLATE)
        .compileComponents();

        fixture = TestBed.createComponent(TransferTableComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("should create", () => {
        expect(component).toBeDefined();
    });

    it("should have default activeSegment of 'all'", () => {
        expect(component.activeSegment).toBe("all");
    });

    it("should have pageSize of 15", () => {
        expect(component.pageSize).toBe(15);
    });

    it("should render search input with magnifying glass icon", () => {
        const icon = fixture.nativeElement.querySelector(".fa-search");
        expect(icon).toBeTruthy();
        const input = fixture.nativeElement.querySelector(".search-input");
        expect(input).toBeTruthy();
    });

    it("should render 3 parent segment filter buttons", () => {
        const buttons = fixture.nativeElement.querySelectorAll(".btn-segment");
        expect(buttons.length).toBe(3);
        expect(buttons[0].textContent).toContain("All");
        expect(buttons[1].textContent).toContain("Active");
        expect(buttons[2].textContent).toContain("Errors");
    });

    it("should call viewFileOptionsService.setNameFilter on search input", fakeAsync(() => {
        component.onSearchInput("test query");
        expect(component.nameFilter).toBe("test query");
        tick(300);
        expect(mockOptionsService.setNameFilter).toHaveBeenCalledWith("test query");
    }));

    it("should set activeSegment when segment button clicked", () => {
        component.onSegmentChange("active");
        expect(component.activeSegment).toBe("active");

        // Second click on same segment collapses to all
        component.onSegmentChange("active");
        expect(component.activeSegment).toBe("all");
        expect(component.activeSubStatus).toBeNull();

        component.onSegmentChange("errors");
        expect(component.activeSegment).toBe("errors");

        component.onSegmentChange("all");
        expect(component.activeSegment).toBe("all");
    });

    it("should filter to active statuses when 'active' segment selected", fakeAsync(() => {
        const files = [
            makeFile("dl-1", ViewFile.Status.DOWNLOADING),
            makeFile("queued-1", ViewFile.Status.QUEUED),
            makeFile("done-1", ViewFile.Status.DOWNLOADED),
            makeFile("extract-1", ViewFile.Status.EXTRACTING),
            makeFile("stopped-1", ViewFile.Status.STOPPED),
        ];
        mockFileService.pushFiles(files);
        tick();

        component.onSegmentChange("active");
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();

        // Active = DOWNLOADING + QUEUED + EXTRACTING
        expect(pagedFiles.length).toBe(3);
        expect(pagedFiles.map(f => f.name)).toEqual(jasmine.arrayContaining(["dl-1", "queued-1", "extract-1"]));
    }));

    it("should filter to error statuses when 'errors' segment selected", fakeAsync(() => {
        const files = [
            makeFile("dl-1", ViewFile.Status.DOWNLOADING),
            makeFile("stopped-1", ViewFile.Status.STOPPED),
            makeFile("deleted-1", ViewFile.Status.DELETED),
        ];
        mockFileService.pushFiles(files);
        tick();

        component.onSegmentChange("errors");
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();

        // Errors = STOPPED + DELETED
        expect(pagedFiles.length).toBe(2);
        expect(pagedFiles.map(f => f.name)).toEqual(jasmine.arrayContaining(["stopped-1", "deleted-1"]));
    }));

    it("should paginate files with pageSize 15", fakeAsync(() => {
        const files = Array.from({length: 20}, (_, i) =>
            makeFile(`file-${i}`, ViewFile.Status.DOWNLOADED)
        );
        mockFileService.pushFiles(files);
        tick();
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();

        expect(pagedFiles.length).toBe(15); // First page

        let totalPages = 0;
        component.totalPages$.subscribe(t => totalPages = t);
        tick();

        expect(totalPages).toBe(2); // 20 / 15 = 2 pages
    }));

    it("should navigate to next page", fakeAsync(() => {
        const files = Array.from({length: 20}, (_, i) =>
            makeFile(`file-${i}`, ViewFile.Status.DOWNLOADED)
        );
        mockFileService.pushFiles(files);
        tick();

        component.onNextPage(2);
        fixture.detectChanges();
        tick();

        expect(component.currentPage).toBe(2);

        let pagedFiles: ViewFile[] = [];
        component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();

        expect(pagedFiles.length).toBe(5); // Remaining 5 files
    }));

    it("should navigate to previous page", fakeAsync(() => {
        const files = Array.from({length: 20}, (_, i) =>
            makeFile(`file-${i}`, ViewFile.Status.DOWNLOADED)
        );
        mockFileService.pushFiles(files);
        tick();

        component.goToPage(2);
        tick();
        expect(component.currentPage).toBe(2);

        component.onPrevPage();
        tick();
        expect(component.currentPage).toBe(1);
    }));

    it("should not navigate before page 1", () => {
        expect(component.currentPage).toBe(1);
        component.onPrevPage();
        expect(component.currentPage).toBe(1);
    });

    it("should not navigate past last page", fakeAsync(() => {
        const files = Array.from({length: 10}, (_, i) =>
            makeFile(`file-${i}`, ViewFile.Status.DOWNLOADED)
        );
        mockFileService.pushFiles(files);
        tick();

        component.onNextPage(1); // totalPages = 1
        expect(component.currentPage).toBe(1);
    }));

    it("should render pagination footer", fakeAsync(() => {
        const files = [makeFile("file-1", ViewFile.Status.DOWNLOADED)];
        mockFileService.pushFiles(files);
        tick();
        fixture.detectChanges();
        tick();

        const footer = fixture.nativeElement.querySelector(".pagination-footer");
        expect(footer).toBeTruthy();
        const info = fixture.nativeElement.querySelector(".page-info");
        expect(info!.textContent).toContain("Page 1");
    }));
});
