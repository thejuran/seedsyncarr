import {ComponentFixture, TestBed} from "@angular/core/testing";
import {SimpleChange, SimpleChanges} from "@angular/core";
import {List} from "immutable";

import {BulkActionsBarComponent, BulkActionCounts} from "../../../../pages/files/bulk-actions-bar.component";
import {ViewFile} from "../../../../services/files/view-file";


describe("BulkActionsBarComponent", () => {
    let component: BulkActionsBarComponent;
    let fixture: ComponentFixture<BulkActionsBarComponent>;

    // Test files with different action eligibility flags
    const testFiles = List([
        new ViewFile({
            name: "file1",
            isQueueable: true,
            isStoppable: false,
            isExtractable: false,
            isLocallyDeletable: false,
            isRemotelyDeletable: true
        }),
        new ViewFile({
            name: "file2",
            isQueueable: true,
            isStoppable: false,
            isExtractable: true,
            isArchive: true,  // Required for extraction
            isLocallyDeletable: true,
            isRemotelyDeletable: true
        }),
        new ViewFile({
            name: "file3",
            isQueueable: false,
            isStoppable: true,
            isExtractable: false,
            isLocallyDeletable: false,
            isRemotelyDeletable: false
        }),
        new ViewFile({
            name: "file4",
            isQueueable: false,
            isStoppable: true,
            isExtractable: true,
            isArchive: true,  // Required for extraction
            isLocallyDeletable: true,
            isRemotelyDeletable: false
        }),
        new ViewFile({
            name: "file5",
            isQueueable: true,
            isStoppable: false,
            isExtractable: true,
            isArchive: true,  // Required for extraction
            isLocallyDeletable: true,
            isRemotelyDeletable: true
        })
    ]);

    /**
     * Helper to set inputs and trigger ngOnChanges for proper cache update.
     */
    function setInputsAndDetectChanges(visibleFiles: List<ViewFile>, selectedFiles: Set<string>): void {
        const changes: SimpleChanges = {};
        if (component.visibleFiles !== visibleFiles) {
            changes["visibleFiles"] = new SimpleChange(component.visibleFiles, visibleFiles, false);
            component.visibleFiles = visibleFiles;
        }
        if (component.selectedFiles !== selectedFiles) {
            changes["selectedFiles"] = new SimpleChange(component.selectedFiles, selectedFiles, false);
            component.selectedFiles = selectedFiles;
        }
        if (Object.keys(changes).length > 0) {
            component.ngOnChanges(changes);
        }
        fixture.detectChanges();
    }

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [BulkActionsBarComponent]
        }).compileComponents();

        fixture = TestBed.createComponent(BulkActionsBarComponent);
        component = fixture.componentInstance;
        setInputsAndDetectChanges(testFiles, new Set());
    });

    // =========================================================================
    // Visibility Tests
    // =========================================================================

    describe("Visibility", () => {
        it("should not show bar when no files are selected", () => {
            setInputsAndDetectChanges(testFiles, new Set());
            expect(component.hasSelection).toBe(false);
        });

        it("should show bar when files are selected", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file1", "file2"]));
            expect(component.hasSelection).toBe(true);
        });

        it("should return correct selected count", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file1", "file2", "file3"]));
            expect(component.selectedCount).toBe(3);
        });
    });

    // =========================================================================
    // Action Counts Tests
    // =========================================================================

    describe("Action counts", () => {
        it("should calculate correct counts for selected files", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file1", "file2", "file3", "file4", "file5"]));
            const counts: BulkActionCounts = component.actionCounts;

            // file1, file2, file5 are queueable (3)
            expect(counts.queueable).toBe(3);
            // file3, file4 are stoppable (2)
            expect(counts.stoppable).toBe(2);
            // file2, file4, file5 are extractable (3)
            expect(counts.extractable).toBe(3);
            // file2, file4, file5 are locally deletable (3)
            expect(counts.locallyDeletable).toBe(3);
            // file1, file2, file5 are remotely deletable (3)
            expect(counts.remotelyDeletable).toBe(3);
        });

        it("should calculate counts only for selected files", () => {
            // Only select file1 and file3
            setInputsAndDetectChanges(testFiles, new Set(["file1", "file3"]));
            const counts: BulkActionCounts = component.actionCounts;

            // file1 is queueable
            expect(counts.queueable).toBe(1);
            // file3 is stoppable
            expect(counts.stoppable).toBe(1);
            // Neither is extractable
            expect(counts.extractable).toBe(0);
            // Neither is locally deletable
            expect(counts.locallyDeletable).toBe(0);
            // file1 is remotely deletable
            expect(counts.remotelyDeletable).toBe(1);
        });

        it("should return zero counts when no files selected", () => {
            setInputsAndDetectChanges(testFiles, new Set());
            const counts: BulkActionCounts = component.actionCounts;

            expect(counts.queueable).toBe(0);
            expect(counts.stoppable).toBe(0);
            expect(counts.extractable).toBe(0);
            expect(counts.locallyDeletable).toBe(0);
            expect(counts.remotelyDeletable).toBe(0);
        });

        it("should ignore selected files not in visible files", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file1", "nonexistent"]));
            const counts: BulkActionCounts = component.actionCounts;

            // Only file1 should be counted
            expect(counts.queueable).toBe(1);
            expect(counts.remotelyDeletable).toBe(1);
        });
    });

    // =========================================================================
    // File Getters Tests
    // =========================================================================

    describe("File getters", () => {
        beforeEach(() => {
            setInputsAndDetectChanges(testFiles, new Set(["file1", "file2", "file3", "file4", "file5"]));
        });

        it("should return queueable file names", () => {
            const files = component.queueableFiles;
            expect(files).toContain("file1");
            expect(files).toContain("file2");
            expect(files).toContain("file5");
            expect(files.length).toBe(3);
        });

        it("should return stoppable file names", () => {
            const files = component.stoppableFiles;
            expect(files).toContain("file3");
            expect(files).toContain("file4");
            expect(files.length).toBe(2);
        });

        it("should return extractable file names", () => {
            const files = component.extractableFiles;
            expect(files).toContain("file2");
            expect(files).toContain("file4");
            expect(files).toContain("file5");
            expect(files.length).toBe(3);
        });

        it("should return locally deletable file names", () => {
            const files = component.locallyDeletableFiles;
            expect(files).toContain("file2");
            expect(files).toContain("file4");
            expect(files).toContain("file5");
            expect(files.length).toBe(3);
        });

        it("should return remotely deletable file names", () => {
            const files = component.remotelyDeletableFiles;
            expect(files).toContain("file1");
            expect(files).toContain("file2");
            expect(files).toContain("file5");
            expect(files.length).toBe(3);
        });
    });

    // =========================================================================
    // Click Handler Tests
    // =========================================================================

    describe("Click handlers", () => {
        beforeEach(() => {
            setInputsAndDetectChanges(testFiles, new Set(["file1", "file2", "file5"]));
        });

        it("should emit clearSelection on Clear click", () => {
            spyOn(component.clearSelection, "emit");

            component.onClearClick();

            expect(component.clearSelection.emit).toHaveBeenCalled();
        });

        it("should emit queueAction with queueable files on Queue click", () => {
            spyOn(component.queueAction, "emit");

            component.onQueueClick();

            expect(component.queueAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["file1", "file2", "file5"])
            );
        });

        it("should not emit queueAction when no queueable files", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file3", "file4"]));
            spyOn(component.queueAction, "emit");

            component.onQueueClick();

            expect(component.queueAction.emit).not.toHaveBeenCalled();
        });

        it("should emit stopAction with stoppable files on Stop click", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file3", "file4"]));
            spyOn(component.stopAction, "emit");

            component.onStopClick();

            expect(component.stopAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["file3", "file4"])
            );
        });

        it("should not emit stopAction when no stoppable files", () => {
            spyOn(component.stopAction, "emit");

            component.onStopClick();

            expect(component.stopAction.emit).not.toHaveBeenCalled();
        });

        it("should emit extractAction with extractable files on Extract click", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file2", "file4", "file5"]));
            spyOn(component.extractAction, "emit");

            component.onExtractClick();

            expect(component.extractAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["file2", "file4", "file5"])
            );
        });

        it("should not emit extractAction when no extractable files", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file1", "file3"]));
            spyOn(component.extractAction, "emit");

            component.onExtractClick();

            expect(component.extractAction.emit).not.toHaveBeenCalled();
        });

        it("should emit deleteLocalAction with locally deletable files on Delete Local click", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file2", "file4", "file5"]));
            spyOn(component.deleteLocalAction, "emit");

            component.onDeleteLocalClick();

            expect(component.deleteLocalAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["file2", "file4", "file5"])
            );
        });

        it("should not emit deleteLocalAction when no locally deletable files", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file1", "file3"]));
            spyOn(component.deleteLocalAction, "emit");

            component.onDeleteLocalClick();

            expect(component.deleteLocalAction.emit).not.toHaveBeenCalled();
        });

        it("should emit deleteRemoteAction with remotely deletable files on Delete Remote click", () => {
            spyOn(component.deleteRemoteAction, "emit");

            component.onDeleteRemoteClick();

            expect(component.deleteRemoteAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["file1", "file2", "file5"])
            );
        });

        it("should not emit deleteRemoteAction when no remotely deletable files", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file3", "file4"]));
            spyOn(component.deleteRemoteAction, "emit");

            component.onDeleteRemoteClick();

            expect(component.deleteRemoteAction.emit).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Edge Case Tests
    // =========================================================================

    describe("Edge cases", () => {
        it("should handle empty visible files list", () => {
            setInputsAndDetectChanges(List(), new Set(["file1"]));

            expect(component.selectedViewFiles).toEqual([]);
            expect(component.actionCounts.queueable).toBe(0);
        });

        it("should handle single file selection", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file1"]));
            const counts = component.actionCounts;

            expect(counts.queueable).toBe(1);
            expect(counts.stoppable).toBe(0);
            expect(counts.extractable).toBe(0);
            expect(counts.locallyDeletable).toBe(0);
            expect(counts.remotelyDeletable).toBe(1);
        });

        it("should return selected view files correctly", () => {
            setInputsAndDetectChanges(testFiles, new Set(["file2", "file4"]));

            const selectedViewFiles = component.selectedViewFiles;

            expect(selectedViewFiles.length).toBe(2);
            expect(selectedViewFiles.map(f => f.name)).toContain("file2");
            expect(selectedViewFiles.map(f => f.name)).toContain("file4");
        });
    });

    // =========================================================================
    // FIX-01 DELETED Union Regression (D-09 coverage)
    // =========================================================================

    describe("FIX-01 DELETED union regression (D-09 coverage)", () => {
        it("All-DELETED union: Queue + Delete Remote enabled; Stop/Extract/DeleteLocal disabled (FIX-01 D-09 case 1)", () => {
            const makeDeleted = (name: string): ViewFile => new ViewFile({
                name,
                status: ViewFile.Status.DELETED,
                remoteSize: 1000,
                localSize: 0,
                isQueueable: true,
                isStoppable: false,
                isExtractable: false,
                isArchive: false,
                isLocallyDeletable: false,
                isRemotelyDeletable: true,
            });
            const d1 = makeDeleted("deleted-1.mkv");
            const d2 = makeDeleted("deleted-2.mkv");
            const d3 = makeDeleted("deleted-3.mkv");
            const visible = List([d1, d2, d3]);
            const selected = new Set<string>([
                "deleted-1.mkv", "deleted-2.mkv", "deleted-3.mkv",
            ]);

            setInputsAndDetectChanges(visible, selected);

            expect(component.actionCounts.queueable).toBe(3);
            expect(component.actionCounts.stoppable).toBe(0);
            expect(component.actionCounts.extractable).toBe(0);
            expect(component.actionCounts.locallyDeletable).toBe(0);
            expect(component.actionCounts.remotelyDeletable).toBe(3);

            spyOn(component.queueAction, "emit");
            spyOn(component.stopAction, "emit");
            spyOn(component.extractAction, "emit");
            spyOn(component.deleteLocalAction, "emit");
            spyOn(component.deleteRemoteAction, "emit");

            component.onQueueClick();
            expect(component.queueAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["deleted-1.mkv", "deleted-2.mkv", "deleted-3.mkv"])
            );
            expect((component.queueAction.emit as jasmine.Spy).calls.mostRecent().args[0].length)
                .toBe(3);

            component.onDeleteRemoteClick();
            expect(component.deleteRemoteAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["deleted-1.mkv", "deleted-2.mkv", "deleted-3.mkv"])
            );

            component.onStopClick();
            expect(component.stopAction.emit).not.toHaveBeenCalled();

            component.onExtractClick();
            expect(component.extractAction.emit).not.toHaveBeenCalled();

            component.onDeleteLocalClick();
            expect(component.deleteLocalAction.emit).not.toHaveBeenCalled();
        });

        it("DELETED + DOWNLOADING union: Queue (1) + Stop (1) + DeleteRemote (2); Extract/DeleteLocal disabled (FIX-01 D-09 case 2)", () => {
            const del = new ViewFile({
                name: "del.mkv",
                status: ViewFile.Status.DELETED,
                remoteSize: 1000,
                localSize: 0,
                isQueueable: true,
                isStoppable: false,
                isExtractable: false,
                isArchive: false,
                isLocallyDeletable: false,
                isRemotelyDeletable: true,
            });
            const dl = new ViewFile({
                name: "dl.mkv",
                status: ViewFile.Status.DOWNLOADING,
                remoteSize: 2000,
                localSize: 500,
                isQueueable: false,
                isStoppable: true,
                isExtractable: false,
                isArchive: false,
                isLocallyDeletable: false,
                isRemotelyDeletable: true,
            });
            const visible = List([del, dl]);
            const selected = new Set<string>(["del.mkv", "dl.mkv"]);

            setInputsAndDetectChanges(visible, selected);

            expect(component.actionCounts.queueable).toBe(1);
            expect(component.actionCounts.stoppable).toBe(1);
            expect(component.actionCounts.extractable).toBe(0);
            expect(component.actionCounts.locallyDeletable).toBe(0);
            expect(component.actionCounts.remotelyDeletable).toBe(2);

            spyOn(component.queueAction, "emit");
            spyOn(component.stopAction, "emit");
            spyOn(component.extractAction, "emit");
            spyOn(component.deleteLocalAction, "emit");
            spyOn(component.deleteRemoteAction, "emit");

            component.onQueueClick();
            expect(component.queueAction.emit).toHaveBeenCalledWith(["del.mkv"]);

            component.onStopClick();
            expect(component.stopAction.emit).toHaveBeenCalledWith(["dl.mkv"]);

            component.onDeleteRemoteClick();
            expect(component.deleteRemoteAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["del.mkv", "dl.mkv"])
            );
            expect((component.deleteRemoteAction.emit as jasmine.Spy).calls.mostRecent().args[0].length)
                .toBe(2);

            component.onExtractClick();
            expect(component.extractAction.emit).not.toHaveBeenCalled();

            component.onDeleteLocalClick();
            expect(component.deleteLocalAction.emit).not.toHaveBeenCalled();
        });

        it("DELETED + DOWNLOADED + STOPPED union: Queue (2), Extract (1), DeleteLocal (2), DeleteRemote (3); Stop disabled (FIX-01 D-09 case 3)", () => {
            const del = new ViewFile({
                name: "del.mkv",
                status: ViewFile.Status.DELETED,
                remoteSize: 1000,
                localSize: 0,
                isQueueable: true,
                isStoppable: false,
                isExtractable: false,
                isArchive: false,
                isLocallyDeletable: false,
                isRemotelyDeletable: true,
            });
            const dled = new ViewFile({
                name: "dled.rar",
                status: ViewFile.Status.DOWNLOADED,
                remoteSize: 3000,
                localSize: 3000,
                isQueueable: false,
                isStoppable: false,
                isExtractable: true,
                isArchive: true,
                isLocallyDeletable: true,
                isRemotelyDeletable: true,
            });
            const stp = new ViewFile({
                name: "stp.mkv",
                status: ViewFile.Status.STOPPED,
                remoteSize: 4000,
                localSize: 2000,
                isQueueable: true,
                isStoppable: false,
                isExtractable: false,
                isArchive: false,
                isLocallyDeletable: true,
                isRemotelyDeletable: true,
            });
            const visible = List([del, dled, stp]);
            const selected = new Set<string>(["del.mkv", "dled.rar", "stp.mkv"]);

            setInputsAndDetectChanges(visible, selected);

            expect(component.actionCounts.queueable).toBe(2);
            expect(component.actionCounts.stoppable).toBe(0);
            expect(component.actionCounts.extractable).toBe(1);
            expect(component.actionCounts.locallyDeletable).toBe(2);
            expect(component.actionCounts.remotelyDeletable).toBe(3);

            spyOn(component.queueAction, "emit");
            spyOn(component.stopAction, "emit");
            spyOn(component.extractAction, "emit");
            spyOn(component.deleteLocalAction, "emit");
            spyOn(component.deleteRemoteAction, "emit");

            component.onQueueClick();
            expect(component.queueAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["del.mkv", "stp.mkv"])
            );
            expect((component.queueAction.emit as jasmine.Spy).calls.mostRecent().args[0].length)
                .toBe(2);

            component.onExtractClick();
            expect(component.extractAction.emit).toHaveBeenCalledWith(["dled.rar"]);

            component.onDeleteLocalClick();
            expect(component.deleteLocalAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["dled.rar", "stp.mkv"])
            );
            expect((component.deleteLocalAction.emit as jasmine.Spy).calls.mostRecent().args[0].length)
                .toBe(2);

            component.onDeleteRemoteClick();
            expect(component.deleteRemoteAction.emit).toHaveBeenCalledWith(
                jasmine.arrayContaining(["del.mkv", "dled.rar", "stp.mkv"])
            );
            expect((component.deleteRemoteAction.emit as jasmine.Spy).calls.mostRecent().args[0].length)
                .toBe(3);

            component.onStopClick();
            expect(component.stopAction.emit).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Variant B DOM Contract Tests
    // =========================================================================

    describe("Variant B DOM contract", () => {
        /**
         * Helper for DOM tests: uses componentRef.setInput() which properly
         * marks an OnPush component as dirty before detectChanges().
         */
        function setInputsForDOM(visibleFiles: List<ViewFile>, selectedFiles: Set<string>): void {
            fixture.componentRef.setInput("visibleFiles", visibleFiles);
            fixture.componentRef.setInput("selectedFiles", selectedFiles);
            component.ngOnChanges({
                visibleFiles: new SimpleChange(component.visibleFiles, visibleFiles, false),
                selectedFiles: new SimpleChange(component.selectedFiles, selectedFiles, false)
            });
            fixture.detectChanges();
        }

        it("renders exactly 5 action buttons in order Queue, Stop, Extract, Delete Local, Delete Remote", () => {
            setInputsForDOM(testFiles, new Set(["file1", "file2"]));
            const buttons = fixture.nativeElement.querySelectorAll("button.action-btn");
            expect(buttons.length).toBe(5);

            const expectedLabels = ["Queue", "Stop", "Extract", "Delete Local", "Delete Remote"];
            buttons.forEach((btn: HTMLButtonElement, idx: number) => {
                const text = btn.textContent!.replace(/\s+/g, " ").trim();
                expect(text).toContain(expectedLabels[idx]);
            });
        });

        it("renders the vertical divider between Extract and Delete Local", () => {
            setInputsForDOM(testFiles, new Set(["file1", "file2"]));
            const actionsChildren = fixture.nativeElement.querySelectorAll(".actions > *");
            // Find Extract button index among children (skipping progress-indicator which is @if-hidden)
            let extractIdx = -1;
            actionsChildren.forEach((el: Element, idx: number) => {
                if (el.tagName === "BUTTON" && el.textContent!.replace(/\s+/g, " ").trim().includes("Extract")) {
                    extractIdx = idx;
                }
            });
            expect(extractIdx).toBeGreaterThan(-1);
            const dividerEl = actionsChildren[extractIdx + 1];
            expect(dividerEl.classList.contains("btn-divider")).toBe(true);
        });

        it("renders selection label as 'N selected' with no 'file/files' suffix", () => {
            setInputsForDOM(testFiles, new Set(["file1"]));
            const label1 = fixture.nativeElement.querySelector(".selection-label").textContent.trim();
            expect(label1).toBe("1 selected");
            expect(/\bfile(s)?\b/.test(label1)).toBe(false);

            setInputsForDOM(testFiles, new Set(["file1", "file2"]));
            const label2 = fixture.nativeElement.querySelector(".selection-label").textContent.trim();
            expect(label2).toBe("2 selected");
            expect(/\bfile(s)?\b/.test(label2)).toBe(false);
        });

        it("does NOT render button labels with a parenthesized count suffix", () => {
            setInputsForDOM(testFiles, new Set(["file1", "file2"]));
            const buttons = fixture.nativeElement.querySelectorAll("button.action-btn");
            buttons.forEach((btn: HTMLButtonElement) => {
                expect(/\(\d+\)/.test(btn.textContent!)).toBe(false);
            });
        });
    });

    // =========================================================================
    // Performance Tests
    // =========================================================================

    describe("Performance with large file counts", () => {
        it("should compute action counts efficiently with 500 files", () => {
            // Create 500 files with mixed action eligibility
            const largeFileList: ViewFile[] = [];
            for (let i = 0; i < 500; i++) {
                largeFileList.push(new ViewFile({
                    name: `file${i}`,
                    isQueueable: i % 2 === 0,
                    isStoppable: i % 3 === 0,
                    isExtractable: i % 4 === 0,
                    isLocallyDeletable: i % 5 === 0,
                    isRemotelyDeletable: i % 6 === 0
                }));
            }

            // Select all 500 files
            const allFileNames = new Set(largeFileList.map(f => f.name!));

            // Measure computation time
            const start = performance.now();
            setInputsAndDetectChanges(List(largeFileList), allFileNames);
            const elapsed = performance.now() - start;

            // Should complete in under 50ms
            expect(elapsed).toBeLessThan(50);

            // Verify counts are computed correctly
            expect(component.actionCounts.queueable).toBe(250); // 0, 2, 4, ...
            expect(component.actionCounts.stoppable).toBe(167); // 0, 3, 6, ...
        });

        it("should handle multiple getter accesses without recomputation", () => {
            // Create 100 files
            const files: ViewFile[] = [];
            for (let i = 0; i < 100; i++) {
                files.push(new ViewFile({
                    name: `file${i}`,
                    isQueueable: true,
                    isStoppable: true,
                    isExtractable: true,
                    isLocallyDeletable: true,
                    isRemotelyDeletable: true
                }));
            }
            const allFileNames = new Set(files.map(f => f.name!));
            setInputsAndDetectChanges(List(files), allFileNames);

            // Access all getters multiple times
            const start = performance.now();
            for (let i = 0; i < 100; i++) {
                // These should all return cached values - void used to suppress unused expression lint
                void component.actionCounts;
                void component.queueableFiles;
                void component.stoppableFiles;
                void component.extractableFiles;
                void component.locallyDeletableFiles;
                void component.remotelyDeletableFiles;
                void component.selectedViewFiles;
            }
            const elapsed = performance.now() - start;

            // 700 getter accesses should complete in under 10ms (cached)
            expect(elapsed).toBeLessThan(10);
        });

        it("should only recompute when inputs change", () => {
            // Create 100 files
            const files: ViewFile[] = [];
            for (let i = 0; i < 100; i++) {
                files.push(new ViewFile({
                    name: `file${i}`,
                    isQueueable: true
                }));
            }
            const filesList = List(files);
            const selectedFiles = new Set(files.map(f => f.name!));
            setInputsAndDetectChanges(filesList, selectedFiles);

            const initialCounts = component.actionCounts;

            // Simulate no input changes (just trigger ngOnChanges with operationInProgress)
            component.operationInProgress = true;
            component.ngOnChanges({
                operationInProgress: {
                    previousValue: false,
                    currentValue: true,
                    firstChange: false,
                    isFirstChange: () => false
                }
            });

            // Should still return the same cached counts
            expect(component.actionCounts).toBe(initialCounts);
        });
    });
});
