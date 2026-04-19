import {ComponentFixture, TestBed} from "@angular/core/testing";

import {TransferRowComponent} from "../../../../pages/files/transfer-row.component";
import {ViewFile} from "../../../../services/files/view-file";
import {FileSelectionService} from "../../../../services/files/file-selection.service";


// Simplified template for unit testing — mirrors key structural elements
const TEST_TEMPLATE = `
<td class="cell-checkbox" appClickStopPropagation>
  <input type="checkbox" class="ss-checkbox"
         [checked]="isSelected()"
         (click)="onCheckboxClick($event)"
         [attr.aria-label]="'Select ' + file.name" />
</td>
<td class="cell-name">{{ file.name }}</td>
<td class="cell-status"><span [class]="badgeClass">{{ badgeLabel }}</span></td>
<td class="cell-progress">
  @if (file.percentDownloaded != null && file.percentDownloaded < 100) {
    <div class="progress-wrap">
      <div class="progress-bar progress-bar-striped progress-bar-animated"
           [class.bg-warning]="isDownloading"
           [style.width.%]="file.percentDownloaded"></div>
      <span class="progress-pct">{{ file.percentDownloaded }}%</span>
    </div>
  }
</td>
<td class="cell-speed">
  @if (isDownloading && file.downloadingSpeed) {
    {{ file.downloadingSpeed }}
  }
</td>
<td class="cell-eta">
  @if (isDownloading && file.eta) {
    {{ file.eta }}
  }
</td>
<td class="cell-size">{{ file.remoteSize }}</td>
`;


describe("TransferRowComponent", () => {
    let component: TransferRowComponent;
    let fixture: ComponentFixture<TransferRowComponent>;
    let selectionService: FileSelectionService;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [TransferRowComponent]
        })
        .overrideTemplate(TransferRowComponent, TEST_TEMPLATE)
        .compileComponents();

        fixture = TestBed.createComponent(TransferRowComponent);
        component = fixture.componentInstance;
        selectionService = TestBed.inject(FileSelectionService);
        selectionService.clearSelection();
    });

    function setFile(status: ViewFile.Status, opts: Partial<ViewFile> = {}): void {
        component.file = new ViewFile({
            name: "test-file.mkv",
            status,
            remoteSize: 5000,
            localSize: 2500,
            percentDownloaded: 50,
            downloadingSpeed: 1000,
            eta: 120,
            ...opts
        });
        fixture.detectChanges();
    }

    it("should create", () => {
        setFile(ViewFile.Status.DEFAULT);
        expect(component).toBeDefined();
    });

    // DASH-08: Badge labels
    it("should return 'Syncing' badge for DOWNLOADING status", () => {
        setFile(ViewFile.Status.DOWNLOADING);
        expect(component.badgeLabel).toBe("Syncing");
    });

    it("should return 'Queued' badge for QUEUED status", () => {
        setFile(ViewFile.Status.QUEUED);
        expect(component.badgeLabel).toBe("Queued");
    });

    it("should return 'Synced' badge for DOWNLOADED status", () => {
        setFile(ViewFile.Status.DOWNLOADED);
        expect(component.badgeLabel).toBe("Synced");
    });

    it("should return 'Failed' badge for STOPPED status", () => {
        setFile(ViewFile.Status.STOPPED);
        expect(component.badgeLabel).toBe("Failed");
    });

    it("should return 'Deleted' badge for DELETED status", () => {
        setFile(ViewFile.Status.DELETED);
        expect(component.badgeLabel).toBe("Deleted");
    });

    // DASH-08: Badge CSS classes with semantic colors
    it("should return warning badge class for DOWNLOADING", () => {
        setFile(ViewFile.Status.DOWNLOADING);
        expect(component.badgeClass).toContain("bg-warning");
    });

    it("should return success badge class for DOWNLOADED", () => {
        setFile(ViewFile.Status.DOWNLOADED);
        expect(component.badgeClass).toContain("bg-success");
    });

    it("should return danger badge class for STOPPED", () => {
        setFile(ViewFile.Status.STOPPED);
        expect(component.badgeClass).toContain("bg-danger");
    });

    it("should return secondary badge class for QUEUED", () => {
        setFile(ViewFile.Status.QUEUED);
        expect(component.badgeClass).toContain("bg-secondary");
    });

    // DASH-09: isDownloading getter
    it("should report isDownloading true for DOWNLOADING status", () => {
        setFile(ViewFile.Status.DOWNLOADING);
        expect(component.isDownloading).toBe(true);
    });

    it("should report isDownloading false for non-DOWNLOADING status", () => {
        setFile(ViewFile.Status.DOWNLOADED);
        expect(component.isDownloading).toBe(false);
    });

    // DASH-09: Progress bar rendering
    it("should render progress bar for downloading file", () => {
        setFile(ViewFile.Status.DOWNLOADING, {percentDownloaded: 45});
        const bar = fixture.nativeElement.querySelector(".progress-bar");
        expect(bar).toBeTruthy();
        const pct = fixture.nativeElement.querySelector(".progress-pct");
        expect(pct!.textContent).toContain("45");
    });

    // DASH-10: Speed and ETA rendering
    it("should render speed for downloading file", () => {
        setFile(ViewFile.Status.DOWNLOADING, {downloadingSpeed: 5000});
        const speed = fixture.nativeElement.querySelector(".cell-speed");
        expect(speed!.textContent!.trim()).toContain("5000");
    });

    it("should render ETA for downloading file", () => {
        setFile(ViewFile.Status.DOWNLOADING, {eta: 300});
        const eta = fixture.nativeElement.querySelector(".cell-eta");
        expect(eta!.textContent!.trim()).toContain("300");
    });

    it("should not render speed for non-downloading file", () => {
        setFile(ViewFile.Status.DOWNLOADED, {downloadingSpeed: 0});
        const speed = fixture.nativeElement.querySelector(".cell-speed");
        expect(speed!.textContent!.trim()).toBe("");
    });

    // DASH-10: Size column
    it("should render file size", () => {
        setFile(ViewFile.Status.DOWNLOADED, {remoteSize: 9999});
        const size = fixture.nativeElement.querySelector(".cell-size");
        expect(size!.textContent).toContain("9999");
    });

    describe("checkbox + selection signal", () => {
        it("reflects isSelected() = false when the service selection does not contain the file name", () => {
            setFile(ViewFile.Status.DEFAULT, {name: "alpha.mkv"});
            selectionService.clearSelection();
            fixture.detectChanges();

            expect(component.isSelected()).toBe(false);
            const checkbox = fixture.nativeElement.querySelector("input.ss-checkbox") as HTMLInputElement;
            expect(checkbox.checked).toBe(false);
            expect(fixture.debugElement.nativeElement.classList.contains("row-selected")).toBe(false);
        });

        it("reflects isSelected() = true + applies row-selected class when service selection contains the file name", () => {
            setFile(ViewFile.Status.DEFAULT, {name: "beta.mkv"});
            selectionService.select("beta.mkv");
            fixture.detectChanges();

            expect(component.isSelected()).toBe(true);
            const checkbox = fixture.nativeElement.querySelector("input.ss-checkbox") as HTMLInputElement;
            expect(checkbox.checked).toBe(true);
            expect(fixture.debugElement.nativeElement.classList.contains("row-selected")).toBe(true);
        });

        it("emits checkboxToggle with shiftKey=false on plain click", () => {
            setFile(ViewFile.Status.DEFAULT, {name: "gamma.mkv"});
            let emission: {file: ViewFile, shiftKey: boolean} | null = null;
            component.checkboxToggle.subscribe(e => emission = e);

            component.onCheckboxClick(new MouseEvent("click", {shiftKey: false}));

            expect(emission).not.toBeNull();
            expect(emission!.file).toBe(component.file);
            expect(emission!.shiftKey).toBe(false);
        });

        it("emits checkboxToggle with shiftKey=true on shift+click", () => {
            setFile(ViewFile.Status.DEFAULT, {name: "delta.mkv"});
            let emission: {file: ViewFile, shiftKey: boolean} | null = null;
            component.checkboxToggle.subscribe(e => emission = e);

            component.onCheckboxClick(new MouseEvent("click", {shiftKey: true}));

            expect(emission).not.toBeNull();
            expect(emission!.shiftKey).toBe(true);
        });

        it("host aria-label includes 'selected' suffix when selected", () => {
            setFile(ViewFile.Status.DEFAULT, {name: "epsilon.mkv"});
            selectionService.select("epsilon.mkv");
            fixture.detectChanges();

            const selectedLabel = fixture.debugElement.nativeElement.getAttribute("aria-label") as string;
            expect(selectedLabel.endsWith(", selected")).toBe(true);

            selectionService.clearSelection();
            fixture.detectChanges();

            const unselectedLabel = fixture.debugElement.nativeElement.getAttribute("aria-label") as string;
            expect(unselectedLabel.endsWith(", selected")).toBe(false);
        });
    });
});
