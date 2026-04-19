import {ComponentFixture, fakeAsync, TestBed, tick} from "@angular/core/testing";
import {BehaviorSubject, Observable, of} from "rxjs";

import * as Immutable from "immutable";

import {TransferTableComponent} from "../../../../pages/files/transfer-table.component";
import {ViewFileService} from "../../../../services/files/view-file.service";
import {ViewFileOptionsService} from "../../../../services/files/view-file-options.service";
import {ViewFile} from "../../../../services/files/view-file";
import {ViewFileOptions} from "../../../../services/files/view-file-options";
import {FileSelectionService} from "../../../../services/files/file-selection.service";
import {BulkActionDispatcher} from "../../../../services/files/bulk-action-dispatcher.service";
import {BulkCommandService, BulkActionResult} from "../../../../services/server/bulk-command.service";
import {ConfirmModalService} from "../../../../services/utils/confirm-modal.service";
import {NotificationService} from "../../../../services/utils/notification.service";
import {Localization} from "../../../../common/localization";


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
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.DOWNLOADING"
              (click)="onSubStatusChange(ViewFileStatus.DOWNLOADING)">Syncing</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.QUEUED"
              (click)="onSubStatusChange(ViewFileStatus.QUEUED)">Queued</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.EXTRACTING"
              (click)="onSubStatusChange(ViewFileStatus.EXTRACTING)">Extracting</button>
    }
    <button class="btn-segment"
            [class.btn-segment--parent-active]="activeSegment === 'errors' && activeSubStatus === null"
            [class.btn-segment--parent-expanded]="activeSegment === 'errors' && activeSubStatus !== null"
            (click)="onSegmentChange('errors')">Errors</button>
    @if (activeSegment === 'errors') {
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.STOPPED"
              (click)="onSubStatusChange(ViewFileStatus.STOPPED)">Failed</button>
      <button class="btn-sub" [class.active]="activeSubStatus === ViewFileStatus.DELETED"
              (click)="onSubStatusChange(ViewFileStatus.DELETED)">Deleted</button>
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

    pushOptions(options: ViewFileOptions): void {
        this._options$.next(options);
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
    let selectionService: FileSelectionService;
    let dispatcher: BulkActionDispatcher;
    let bulkCommandMock: {executeBulkAction: jasmine.Spy};
    let confirmModalMock: {confirm: jasmine.Spy};
    let notificationMock: {show: jasmine.Spy; hide: jasmine.Spy};

    beforeEach(async () => {
        mockFileService = new MockViewFileService();
        mockOptionsService = new MockViewFileOptionsService();

        const defaultResult = new BulkActionResult(true, {
            results: [],
            summary: {total: 0, succeeded: 0, failed: 0}
        } as any, null);
        bulkCommandMock = {
            executeBulkAction: jasmine.createSpy("executeBulkAction").and.returnValue(of(defaultResult))
        };
        confirmModalMock = {
            confirm: jasmine.createSpy("confirm").and.returnValue(Promise.resolve(true))
        };
        notificationMock = {
            show: jasmine.createSpy("show"),
            hide: jasmine.createSpy("hide")
        };

        await TestBed.configureTestingModule({
            imports: [TransferTableComponent],
            providers: [
                {provide: ViewFileService, useValue: mockFileService},
                {provide: ViewFileOptionsService, useValue: mockOptionsService},
                {provide: BulkCommandService, useValue: bulkCommandMock},
                {provide: ConfirmModalService, useValue: confirmModalMock},
                {provide: NotificationService, useValue: notificationMock}
            ]
        })
        .overrideTemplate(TransferTableComponent, TEST_TEMPLATE)
        .compileComponents();

        fixture = TestBed.createComponent(TransferTableComponent);
        component = fixture.componentInstance;
        selectionService = TestBed.inject(FileSelectionService);
        dispatcher = TestBed.inject(BulkActionDispatcher);
        selectionService.clearSelection();
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
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

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
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

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
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

        expect(pagedFiles.length).toBe(15); // First page

        let totalPages = 0;
        const totalSub = component.totalPages$.subscribe(t => totalPages = t);
        tick();
        totalSub.unsubscribe();

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
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

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

    // --- Sub-status defaults ---

    it("should have default activeSubStatus of null", () => {
        expect(component.activeSubStatus).toBeNull();
    });

    // --- Sub-status filtering (one test per status) ---

    it("should filter to DOWNLOADING only when Syncing sub-status selected", fakeAsync(() => {
        const files = [
            makeFile("dl-1", ViewFile.Status.DOWNLOADING),
            makeFile("queued-1", ViewFile.Status.QUEUED),
            makeFile("extract-1", ViewFile.Status.EXTRACTING),
        ];
        mockFileService.pushFiles(files);
        tick();

        component.onSegmentChange("active");
        component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

        expect(pagedFiles.length).toBe(1);
        expect(pagedFiles[0].name).toBe("dl-1");
    }));

    it("should filter to QUEUED only when Queued sub-status selected", fakeAsync(() => {
        const files = [
            makeFile("dl-1", ViewFile.Status.DOWNLOADING),
            makeFile("queued-1", ViewFile.Status.QUEUED),
            makeFile("extract-1", ViewFile.Status.EXTRACTING),
        ];
        mockFileService.pushFiles(files);
        tick();

        component.onSegmentChange("active");
        component.onSubStatusChange(ViewFile.Status.QUEUED);
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

        expect(pagedFiles.length).toBe(1);
        expect(pagedFiles[0].name).toBe("queued-1");
    }));

    it("should filter to EXTRACTING only when Extracting sub-status selected", fakeAsync(() => {
        const files = [
            makeFile("dl-1", ViewFile.Status.DOWNLOADING),
            makeFile("queued-1", ViewFile.Status.QUEUED),
            makeFile("extract-1", ViewFile.Status.EXTRACTING),
        ];
        mockFileService.pushFiles(files);
        tick();

        component.onSegmentChange("active");
        component.onSubStatusChange(ViewFile.Status.EXTRACTING);
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

        expect(pagedFiles.length).toBe(1);
        expect(pagedFiles[0].name).toBe("extract-1");
    }));

    it("should filter to STOPPED only when Failed sub-status selected", fakeAsync(() => {
        const files = [
            makeFile("stopped-1", ViewFile.Status.STOPPED),
            makeFile("deleted-1", ViewFile.Status.DELETED),
            makeFile("dl-1", ViewFile.Status.DOWNLOADING),
        ];
        mockFileService.pushFiles(files);
        tick();

        component.onSegmentChange("errors");
        component.onSubStatusChange(ViewFile.Status.STOPPED);
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

        expect(pagedFiles.length).toBe(1);
        expect(pagedFiles[0].name).toBe("stopped-1");
    }));

    it("should filter to DELETED only when Deleted sub-status selected", fakeAsync(() => {
        const files = [
            makeFile("stopped-1", ViewFile.Status.STOPPED),
            makeFile("deleted-1", ViewFile.Status.DELETED),
            makeFile("dl-1", ViewFile.Status.DOWNLOADING),
        ];
        mockFileService.pushFiles(files);
        tick();

        component.onSegmentChange("errors");
        component.onSubStatusChange(ViewFile.Status.DELETED);
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

        expect(pagedFiles.length).toBe(1);
        expect(pagedFiles[0].name).toBe("deleted-1");
    }));

    // --- Sub-status switching and state management ---

    it("should switch sub-status within same segment", fakeAsync(() => {
        const files = [
            makeFile("dl-1", ViewFile.Status.DOWNLOADING),
            makeFile("queued-1", ViewFile.Status.QUEUED),
        ];
        mockFileService.pushFiles(files);
        tick();

        component.onSegmentChange("active");
        component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
        tick();

        component.onSubStatusChange(ViewFile.Status.QUEUED);
        fixture.detectChanges();
        tick();

        let pagedFiles: ViewFile[] = [];
        const sub = component.pagedFiles$.subscribe(f => pagedFiles = f);
        tick();
        sub.unsubscribe();

        expect(pagedFiles.length).toBe(1);
        expect(pagedFiles[0].name).toBe("queued-1");
        expect(component.activeSubStatus).toBe(ViewFile.Status.QUEUED);
    }));

    it("should clear subStatus when switching parent segment", fakeAsync(() => {
        component.onSegmentChange("active");
        component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
        expect(component.activeSubStatus).toBe(ViewFile.Status.DOWNLOADING);

        component.onSegmentChange("errors");
        expect(component.activeSegment).toBe("errors");
        expect(component.activeSubStatus).toBeNull();
    }));

    it("should clear subStatus and collapse to All when clicking expanded parent", () => {
        component.onSegmentChange("active");
        component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
        expect(component.activeSubStatus).toBe(ViewFile.Status.DOWNLOADING);

        component.onSegmentChange("active"); // second click — collapse
        expect(component.activeSegment).toBe("all");
        expect(component.activeSubStatus).toBeNull();
    });

    it("should reset page to 1 on sub-status change", () => {
        component.currentPage = 3;
        component.onSegmentChange("active");
        component.onSubStatusChange(ViewFile.Status.DOWNLOADING);
        expect(component.currentPage).toBe(1);
    });

    // --- 72-04: Selection-clearing hooks (D-04) ---

    describe("selection clearing (D-04)", () => {
        it("clears selection on segment change", () => {
            selectionService.setSelection(["alpha", "beta"]);
            expect(selectionService.getSelectedCount()).toBe(2);

            component.onSegmentChange("active");

            expect(selectionService.getSelectedCount()).toBe(0);
        });

        it("clears selection on sub-status change", () => {
            component.onSegmentChange("active");
            selectionService.setSelection(["alpha", "beta"]);
            expect(selectionService.getSelectedCount()).toBe(2);

            component.onSubStatusChange(ViewFile.Status.DOWNLOADING);

            expect(selectionService.getSelectedCount()).toBe(0);
        });

        it("clears selection on goToPage", () => {
            selectionService.setSelection(["alpha", "beta"]);
            expect(selectionService.getSelectedCount()).toBe(2);

            component.goToPage(2);

            expect(selectionService.getSelectedCount()).toBe(0);
        });

        it("clears selection when filter options change (viewFileOptionsService.options emits)", fakeAsync(() => {
            component.currentPage = 3;
            selectionService.setSelection(["alpha", "beta"]);
            expect(selectionService.getSelectedCount()).toBe(2);

            mockOptionsService.pushOptions(new ViewFileOptions({nameFilter: "changed"}));
            tick();

            expect(selectionService.getSelectedCount()).toBe(0);
            expect(component.currentPage).toBe(1);
        }));

        it("also resets the shift-click anchor in the service on clear", () => {
            selectionService.setLastClicked("alpha");
            selectionService.setSelection(["alpha"]);

            component.onSegmentChange("active");

            expect(selectionService.getLastClicked()).toBeNull();
        });
    });

    // --- 72-04: Esc key handler (D-05) ---

    describe("Esc key handler (D-05)", () => {
        it("clears selection when Escape pressed and target is body", () => {
            selectionService.setSelection(["alpha"]);
            const event = new KeyboardEvent("keydown", {key: "Escape"});
            Object.defineProperty(event, "target", {value: document.body});

            component.onKeyDown(event);

            expect(selectionService.getSelectedCount()).toBe(0);
        });

        it("does NOT clear selection when Escape pressed while focus in an <input>", () => {
            selectionService.setSelection(["alpha"]);
            const input = document.createElement("input");
            const event = new KeyboardEvent("keydown", {key: "Escape"});
            Object.defineProperty(event, "target", {value: input});

            component.onKeyDown(event);

            expect(selectionService.getSelectedCount()).toBe(1);
        });
    });

    // --- 72-04: Header checkbox (D-02) ---

    describe("header checkbox state + click (D-02)", () => {
        it("onHeaderCheckboxClick selects all paged files when none selected", () => {
            const a = makeFile("a", ViewFile.Status.DOWNLOADED);
            const b = makeFile("b", ViewFile.Status.DOWNLOADED);
            (component as any)._currentPagedFiles = Immutable.List([a, b]);
            selectionService.clearSelection();

            component.onHeaderCheckboxClick();

            expect(selectionService.getSelectedFiles()).toEqual(new Set(["a", "b"]));
        });

        it("onHeaderCheckboxClick clears selection when all paged files already selected", () => {
            const a = makeFile("a", ViewFile.Status.DOWNLOADED);
            const b = makeFile("b", ViewFile.Status.DOWNLOADED);
            (component as any)._currentPagedFiles = Immutable.List([a, b]);
            selectionService.setSelection(["a", "b"]);

            component.onHeaderCheckboxClick();

            expect(selectionService.getSelectedCount()).toBe(0);
        });
    });

    // --- 72-04: Shift-click range selection (D-03) ---

    describe("shift-click range selection (D-03)", () => {
        let a: ViewFile;
        let b: ViewFile;
        let c: ViewFile;
        let d: ViewFile;

        beforeEach(() => {
            a = makeFile("a", ViewFile.Status.DOWNLOADED);
            b = makeFile("b", ViewFile.Status.DOWNLOADED);
            c = makeFile("c", ViewFile.Status.DOWNLOADED);
            d = makeFile("d", ViewFile.Status.DOWNLOADED);
            (component as any)._currentPagedFiles = Immutable.List([a, b, c, d]);
        });

        it("selects single file on first click (no prior anchor)", () => {
            component.onCheckboxToggle({file: b, shiftKey: false});

            expect(selectionService.getSelectedFiles()).toEqual(new Set(["b"]));
            expect(selectionService.getLastClicked()).toBe("b");
        });

        it("selects range between anchor and target on shift-click", () => {
            component.onCheckboxToggle({file: a, shiftKey: false});
            component.onCheckboxToggle({file: c, shiftKey: true});

            expect(selectionService.getSelectedFiles()).toEqual(new Set(["a", "b", "c"]));
        });

        it("falls back to single toggle when anchor is not in the current paged list", () => {
            selectionService.setLastClicked("nonexistent");

            component.onCheckboxToggle({file: b, shiftKey: true});

            expect(selectionService.getSelectedFiles()).toEqual(new Set(["b"]));
            expect(selectionService.getLastClicked()).toBe("b");
        });
    });

    // --- 72-04: Bulk action dispatch (D-16, D-17) ---

    describe("bulk action dispatch (D-16)", () => {
        it("onBulkQueue calls BulkCommandService.executeBulkAction with 'queue'", () => {
            component.onBulkQueue(["a"]);
            expect(bulkCommandMock.executeBulkAction).toHaveBeenCalledWith("queue", ["a"]);
        });

        it("onBulkStop calls executeBulkAction with 'stop'", () => {
            component.onBulkStop(["a"]);
            expect(bulkCommandMock.executeBulkAction).toHaveBeenCalledWith("stop", ["a"]);
        });

        it("onBulkExtract calls executeBulkAction with 'extract'", () => {
            component.onBulkExtract(["a"]);
            expect(bulkCommandMock.executeBulkAction).toHaveBeenCalledWith("extract", ["a"]);
        });

        it("onBulkDeleteLocal shows confirm modal with skipCount and calls executeBulkAction on confirm", async () => {
            selectionService.setSelection(["a", "b", "c"]);

            await component.onBulkDeleteLocal(["a", "b"]);

            expect(confirmModalMock.confirm).toHaveBeenCalled();
            const firstArg = confirmModalMock.confirm.calls.mostRecent().args[0];
            expect(firstArg.title).toBe(Localization.Modal.BULK_DELETE_LOCAL_TITLE);
            expect(firstArg.skipCount).toBe(1);
            expect(firstArg.okBtn).toBe("Delete");
            expect(bulkCommandMock.executeBulkAction).toHaveBeenCalledWith("delete_local", ["a", "b"]);
        });

        it("onBulkDeleteLocal does NOT call executeBulkAction if user cancels", async () => {
            confirmModalMock.confirm.and.returnValue(Promise.resolve(false));

            await component.onBulkDeleteLocal(["a", "b"]);

            expect(bulkCommandMock.executeBulkAction).not.toHaveBeenCalled();
        });

        it("onBulkDeleteRemote calls executeBulkAction with 'delete_remote' on confirm", async () => {
            await component.onBulkDeleteRemote(["a", "b"]);

            const firstArg = confirmModalMock.confirm.calls.mostRecent().args[0];
            expect(firstArg.title).toBe(Localization.Modal.BULK_DELETE_REMOTE_TITLE);
            expect(bulkCommandMock.executeBulkAction).toHaveBeenCalledWith("delete_remote", ["a", "b"]);
        });

        it("clears selection after successful bulk action", fakeAsync(() => {
            selectionService.setSelection(["a"]);
            component.onBulkQueue(["a"]);
            tick();

            expect(selectionService.getSelectedCount()).toBe(0);
        }));
    });

    // --- New: dispatcher concurrency gate + transient error handling ---

    describe("bulk dispatch concurrency + error handling", () => {
        it("ignores a second dispatch while the first is still in flight", () => {
            // Hold the first response — never emit, never complete.
            const pending = new Observable<BulkActionResult>(() => { /* never emits */ });
            bulkCommandMock.executeBulkAction.and.returnValue(pending);

            component.onBulkQueue(["a"]);
            expect(bulkCommandMock.executeBulkAction).toHaveBeenCalledTimes(1);
            expect(dispatcher.inProgress()).toBe(true);

            component.onBulkQueue(["b"]);
            expect(bulkCommandMock.executeBulkAction).toHaveBeenCalledTimes(1);
        });

        it("preserves selection on transient failure (HTTP 500) so user can retry", fakeAsync(() => {
            selectionService.setSelection(["a", "b"]);

            const transientFailure = new BulkActionResult(false, null, "Internal Server Error", 500);
            bulkCommandMock.executeBulkAction.and.returnValue(of(transientFailure));

            component.onBulkQueue(["a", "b"]);
            tick();

            expect(selectionService.getSelectedCount()).toBe(2);
            expect(notificationMock.show).toHaveBeenCalled();
            expect(dispatcher.inProgress()).toBe(false);
        }));

        it("preserves selection on network failure (status=0)", fakeAsync(() => {
            selectionService.setSelection(["a"]);

            const networkFailure = new BulkActionResult(false, null, "Network error", 0);
            bulkCommandMock.executeBulkAction.and.returnValue(of(networkFailure));

            component.onBulkQueue(["a"]);
            tick();

            expect(selectionService.getSelectedCount()).toBe(1);
        }));

        it("clears selection on permanent failure (HTTP 400)", fakeAsync(() => {
            selectionService.setSelection(["a", "b"]);

            const permanentFailure = new BulkActionResult(false, null, "Bad Request", 400);
            bulkCommandMock.executeBulkAction.and.returnValue(of(permanentFailure));

            component.onBulkQueue(["a", "b"]);
            tick();

            expect(selectionService.getSelectedCount()).toBe(0);
            expect(notificationMock.show).toHaveBeenCalled();
        }));

        it("releases the concurrency gate after a failure completes", fakeAsync(() => {
            const permanentFailure = new BulkActionResult(false, null, "Bad Request", 400);
            bulkCommandMock.executeBulkAction.and.returnValue(of(permanentFailure));

            component.onBulkQueue(["a"]);
            tick();

            expect(dispatcher.inProgress()).toBe(false);
        }));

        it("exposes bulkOperationInProgress as a computed mirroring the dispatcher signal", () => {
            expect(component.bulkOperationInProgress()).toBe(false);
        });
    });
});
