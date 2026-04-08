import {ComponentFixture, TestBed, fakeAsync, tick} from "@angular/core/testing";
import {SimpleChange} from "@angular/core";

import {FileComponent, FileAction} from "../../../../pages/files/file.component";
import {FileSelectionService} from "../../../../services/files/file-selection.service";
import {ConfirmModalService} from "../../../../services/utils/confirm-modal.service";
import {ViewFile} from "../../../../services/files/view-file";
import {ViewFileOptions} from "../../../../services/files/view-file-options";


describe("FileComponent", () => {
    let component: FileComponent;
    let fixture: ComponentFixture<FileComponent>;
    let fileSelectionService: FileSelectionService;
    let mockConfirmModalService: jasmine.SpyObj<ConfirmModalService>;

    // Test file
    const testFile = new ViewFile({
        name: "test-file.mkv",
        isQueueable: true,
        isStoppable: false,
        isExtractable: true,
        isArchive: true,
        isLocallyDeletable: true,
        isRemotelyDeletable: true
    });

    const testOptions = new ViewFileOptions({});

    beforeEach(async () => {
        mockConfirmModalService = jasmine.createSpyObj("ConfirmModalService", ["confirm"]);
        mockConfirmModalService.confirm.and.returnValue(Promise.resolve(true));

        await TestBed.configureTestingModule({
            imports: [FileComponent],
            providers: [
                FileSelectionService,
                {provide: ConfirmModalService, useValue: mockConfirmModalService}
            ]
        })
        // Override template to simplify testing - focus on component logic
        .overrideTemplate(FileComponent, `
            <div #fileElement>
                <input type="checkbox" [checked]="isSelected()" (click)="onCheckboxClick($event)">
                {{ file?.name }}
            </div>
        `)
        .compileComponents();

        fileSelectionService = TestBed.inject(FileSelectionService);
        fixture = TestBed.createComponent(FileComponent);
        component = fixture.componentInstance;
        component.file = testFile;
        component.options = testOptions;
        fixture.detectChanges();
    });

    // =========================================================================
    // Signal-Based Selection Tests
    // =========================================================================

    describe("Signal-based selection (isSelected computed)", () => {
        it("should return false when file is not selected", () => {
            expect(component.isSelected()).toBe(false);
        });

        it("should return true when file is selected", () => {
            fileSelectionService.select(testFile.name!);
            expect(component.isSelected()).toBe(true);
        });

        it("should update when selection changes", () => {
            expect(component.isSelected()).toBe(false);

            fileSelectionService.select(testFile.name!);
            expect(component.isSelected()).toBe(true);

            fileSelectionService.deselect(testFile.name!);
            expect(component.isSelected()).toBe(false);
        });

        it("should return false when file is undefined", () => {
            component.file = undefined as unknown as ViewFile;
            expect(component.isSelected()).toBe(false);
        });

        it("should handle selection of different file", () => {
            fileSelectionService.select("other-file.mkv");
            expect(component.isSelected()).toBe(false);
        });

        it("should handle bulk selection correctly", () => {
            fileSelectionService.selectMultiple(["file1", testFile.name!, "file3"]);
            expect(component.isSelected()).toBe(true);
        });

        it("should handle clear selection", () => {
            fileSelectionService.select(testFile.name!);
            expect(component.isSelected()).toBe(true);

            fileSelectionService.clearSelection();
            expect(component.isSelected()).toBe(false);
        });
    });

    // =========================================================================
    // Checkbox Click Handler Tests
    // =========================================================================

    describe("Checkbox click handler (onCheckboxClick)", () => {
        it("should emit checkboxToggle with file and shiftKey=false on normal click", () => {
            spyOn(component.checkboxToggle, "emit");

            const event = new MouseEvent("click", {shiftKey: false});
            component.onCheckboxClick(event);

            expect(component.checkboxToggle.emit).toHaveBeenCalledWith({
                file: testFile,
                shiftKey: false
            });
        });

        it("should emit checkboxToggle with shiftKey=true on shift+click", () => {
            spyOn(component.checkboxToggle, "emit");

            const event = new MouseEvent("click", {shiftKey: true});
            component.onCheckboxClick(event);

            expect(component.checkboxToggle.emit).toHaveBeenCalledWith({
                file: testFile,
                shiftKey: true
            });
        });

        it("should stop event propagation", () => {
            const event = new MouseEvent("click");
            spyOn(event, "stopPropagation");

            component.onCheckboxClick(event);

            expect(event.stopPropagation).toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Lifecycle Tests
    // =========================================================================

    describe("Lifecycle hooks", () => {
        it("should set viewInitialized flag in ngAfterViewInit", () => {
            // Create a fresh component to test lifecycle
            const newFixture = TestBed.createComponent(FileComponent);
            const newComponent = newFixture.componentInstance;
            newComponent.file = testFile;
            newComponent.options = testOptions;

            // Before ngAfterViewInit, viewInitialized should be false
            expect((newComponent as unknown as {viewInitialized: boolean}).viewInitialized).toBe(false);

            // Trigger lifecycle
            newFixture.detectChanges();

            // After ngAfterViewInit, viewInitialized should be true
            expect((newComponent as unknown as {viewInitialized: boolean}).viewInitialized).toBe(true);
        });

        it("should reset activeAction on status change in ngOnChanges", () => {
            component.activeAction = FileAction.QUEUE;

            const oldFile = new ViewFile({name: "test", status: ViewFile.Status.QUEUED});
            const newFile = new ViewFile({name: "test", status: ViewFile.Status.DOWNLOADING});

            component.ngOnChanges({
                file: new SimpleChange(oldFile, newFile, false)
            });

            expect(component.activeAction).toBeNull();
        });

        it("should not reset activeAction when status unchanged", () => {
            component.activeAction = FileAction.QUEUE;

            const oldFile = new ViewFile({name: "test", status: ViewFile.Status.QUEUED});
            const newFile = new ViewFile({name: "test", status: ViewFile.Status.QUEUED});

            component.ngOnChanges({
                file: new SimpleChange(oldFile, newFile, false)
            });

            expect(component.activeAction).toBe(FileAction.QUEUE);
        });

        it("should handle null previousValue in ngOnChanges", () => {
            component.activeAction = FileAction.QUEUE;

            const newFile = new ViewFile({name: "test", status: ViewFile.Status.QUEUED});

            // Should not throw
            component.ngOnChanges({
                file: new SimpleChange(null, newFile, true)
            });

            // Active action should remain unchanged when oldFile is null
            expect(component.activeAction).toBe(FileAction.QUEUE);
        });
    });

    // =========================================================================
    // Action Eligibility Tests
    // =========================================================================

    describe("Action eligibility methods", () => {
        it("should return true for isQueueable when file is queueable and no active action", () => {
            component.file = new ViewFile({name: "test", isQueueable: true});
            component.activeAction = null;
            expect(component.isQueueable()).toBe(true);
        });

        it("should return false for isQueueable when action is active", () => {
            component.file = new ViewFile({name: "test", isQueueable: true});
            component.activeAction = FileAction.QUEUE;
            expect(component.isQueueable()).toBe(false);
        });

        it("should return true for isStoppable when file is stoppable", () => {
            component.file = new ViewFile({name: "test", isStoppable: true});
            component.activeAction = null;
            expect(component.isStoppable()).toBe(true);
        });

        it("should return true for isExtractable when file is extractable AND is archive", () => {
            component.file = new ViewFile({name: "test", isExtractable: true, isArchive: true});
            component.activeAction = null;
            expect(component.isExtractable()).toBe(true);
        });

        it("should return false for isExtractable when file is extractable but NOT archive", () => {
            component.file = new ViewFile({name: "test", isExtractable: true, isArchive: false});
            component.activeAction = null;
            expect(component.isExtractable()).toBe(false);
        });

        it("should return true for isLocallyDeletable when file is locally deletable", () => {
            component.file = new ViewFile({name: "test", isLocallyDeletable: true});
            component.activeAction = null;
            expect(component.isLocallyDeletable()).toBe(true);
        });

        it("should return true for isRemotelyDeletable when file is remotely deletable", () => {
            component.file = new ViewFile({name: "test", isRemotelyDeletable: true});
            component.activeAction = null;
            expect(component.isRemotelyDeletable()).toBe(true);
        });
    });

    // =========================================================================
    // Action Handler Tests
    // =========================================================================

    describe("Action handlers", () => {
        it("should set activeAction and emit queueEvent on onQueue", () => {
            spyOn(component.queueEvent, "emit");

            component.onQueue(testFile);

            expect(component.activeAction).toBe(FileAction.QUEUE);
            expect(component.queueEvent.emit).toHaveBeenCalledWith(testFile);
        });

        it("should set activeAction and emit stopEvent on onStop", () => {
            // Set up stoppable file for this test
            const stoppableFile = new ViewFile({name: "stoppable-file.mkv", isStoppable: true});
            component.file = stoppableFile;
            spyOn(component.stopEvent, "emit");

            component.onStop(stoppableFile);

            expect(component.activeAction).toBe(FileAction.STOP);
            expect(component.stopEvent.emit).toHaveBeenCalledWith(stoppableFile);
        });

        it("should set activeAction and emit extractEvent on onExtract", () => {
            spyOn(component.extractEvent, "emit");

            component.onExtract(testFile);

            expect(component.activeAction).toBe(FileAction.EXTRACT);
            expect(component.extractEvent.emit).toHaveBeenCalledWith(testFile);
        });

        it("should show confirmation modal for onDeleteLocal", fakeAsync(() => {
            spyOn(component.deleteLocalEvent, "emit");

            component.onDeleteLocal(testFile);
            tick();

            expect(mockConfirmModalService.confirm).toHaveBeenCalled();
            expect(component.activeAction).toBe(FileAction.DELETE_LOCAL);
            expect(component.deleteLocalEvent.emit).toHaveBeenCalledWith(testFile);
        }));

        it("should not emit deleteLocalEvent when confirmation cancelled", fakeAsync(() => {
            mockConfirmModalService.confirm.and.returnValue(Promise.resolve(false));
            spyOn(component.deleteLocalEvent, "emit");

            component.onDeleteLocal(testFile);
            tick();

            expect(mockConfirmModalService.confirm).toHaveBeenCalled();
            expect(component.activeAction).toBeNull();
            expect(component.deleteLocalEvent.emit).not.toHaveBeenCalled();
        }));

        it("should show confirmation modal for onDeleteRemote", fakeAsync(() => {
            spyOn(component.deleteRemoteEvent, "emit");

            component.onDeleteRemote(testFile);
            tick();

            expect(mockConfirmModalService.confirm).toHaveBeenCalled();
            expect(component.activeAction).toBe(FileAction.DELETE_REMOTE);
            expect(component.deleteRemoteEvent.emit).toHaveBeenCalledWith(testFile);
        }));

        it("should not emit deleteRemoteEvent when confirmation cancelled", fakeAsync(() => {
            mockConfirmModalService.confirm.and.returnValue(Promise.resolve(false));
            spyOn(component.deleteRemoteEvent, "emit");

            component.onDeleteRemote(testFile);
            tick();

            expect(mockConfirmModalService.confirm).toHaveBeenCalled();
            expect(component.activeAction).toBeNull();
            expect(component.deleteRemoteEvent.emit).not.toHaveBeenCalled();
        }));
    });

    // =========================================================================
    // ViewChild and Scroll Tests
    // =========================================================================

    describe("Scroll into view behavior", () => {
        it("should not attempt scroll before view initialized", () => {
            const newFixture = TestBed.createComponent(FileComponent);
            const newComponent = newFixture.componentInstance;
            newComponent.file = testFile;
            newComponent.options = testOptions;

            // Select the file before view is initialized
            fileSelectionService.select(testFile.name!);

            // Trigger ngOnChanges manually before ngAfterViewInit
            const oldFile = new ViewFile({name: "test", status: ViewFile.Status.DEFAULT});
            const newFile = new ViewFile({name: "test", status: ViewFile.Status.QUEUED, isSelected: true});

            // This should not throw even though fileElement may not be ready
            expect(() => {
                newComponent.ngOnChanges({
                    file: new SimpleChange(oldFile, newFile, false)
                });
            }).not.toThrow();
        });
    });

    // =========================================================================
    // Edge Cases
    // =========================================================================

    describe("Edge cases", () => {
        it("should handle rapid selection/deselection", () => {
            for (let i = 0; i < 100; i++) {
                fileSelectionService.select(testFile.name!);
                expect(component.isSelected()).toBe(true);
                fileSelectionService.deselect(testFile.name!);
                expect(component.isSelected()).toBe(false);
            }
        });

        it("should handle file with special characters in name", () => {
            component.file = new ViewFile({name: "file with spaces & special (chars).mkv"});
            fileSelectionService.select("file with spaces & special (chars).mkv");
            expect(component.isSelected()).toBe(true);
        });

        it("should handle empty file name", () => {
            component.file = new ViewFile({name: ""});
            fileSelectionService.select("");
            expect(component.isSelected()).toBe(true);
        });
    });
});
