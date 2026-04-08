import {TestBed} from "@angular/core/testing";

import {FileSelectionService} from "../../../../services/files/file-selection.service";
import {ViewFile} from "../../../../services/files/view-file";


describe("Testing file selection service", () => {
    let service: FileSelectionService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [FileSelectionService]
        });
        service = TestBed.inject(FileSelectionService);
    });

    // =========================================================================
    // Basic Selection Tests
    // =========================================================================

    it("should create an instance", () => {
        expect(service).toBeDefined();
    });

    it("should start with no selections", () => {
        expect(service.getSelectedCount()).toBe(0);
        expect(service.getSelectedFiles().size).toBe(0);
    });

    it("should select a file", () => {
        service.select("file1");

        expect(service.isSelected("file1")).toBe(true);
        expect(service.getSelectedCount()).toBe(1);
        expect(service.getSelectedFiles().has("file1")).toBe(true);
    });

    it("should not duplicate selection", () => {
        service.select("file1");
        service.select("file1");

        expect(service.getSelectedCount()).toBe(1);
    });

    it("should deselect a file", () => {
        service.select("file1");
        service.select("file2");

        service.deselect("file1");

        expect(service.isSelected("file1")).toBe(false);
        expect(service.isSelected("file2")).toBe(true);
        expect(service.getSelectedCount()).toBe(1);
    });

    it("should handle deselecting non-selected file", () => {
        service.deselect("nonexistent");

        expect(service.getSelectedCount()).toBe(0);
    });

    it("should toggle selection on", () => {
        service.toggle("file1");

        expect(service.isSelected("file1")).toBe(true);
    });

    it("should toggle selection off", () => {
        service.select("file1");
        service.toggle("file1");

        expect(service.isSelected("file1")).toBe(false);
    });

    it("should select multiple files", () => {
        service.selectMultiple(["file1", "file2", "file3"]);

        expect(service.getSelectedCount()).toBe(3);
        expect(service.isSelected("file1")).toBe(true);
        expect(service.isSelected("file2")).toBe(true);
        expect(service.isSelected("file3")).toBe(true);
    });

    it("should not duplicate when selecting multiple", () => {
        service.select("file1");
        service.selectMultiple(["file1", "file2"]);

        expect(service.getSelectedCount()).toBe(2);
    });

    // =========================================================================
    // Select All Tests
    // =========================================================================

    it("should select all visible files", () => {
        const files = [
            new ViewFile({name: "file1"}),
            new ViewFile({name: "file2"}),
            new ViewFile({name: "file3"})
        ];

        service.selectAllVisible(files);

        expect(service.getSelectedCount()).toBe(3);
        expect(service.isSelected("file1")).toBe(true);
        expect(service.isSelected("file2")).toBe(true);
        expect(service.isSelected("file3")).toBe(true);
    });

    // =========================================================================
    // Clear Selection Tests
    // =========================================================================

    it("should clear all selections", () => {
        service.selectMultiple(["file1", "file2", "file3"]);

        service.clearSelection();

        expect(service.getSelectedCount()).toBe(0);
        expect(service.isSelected("file1")).toBe(false);
    });

    // =========================================================================
    // Set Selection Tests
    // =========================================================================

    it("should replace selection with setSelection", () => {
        service.selectMultiple(["file1", "file2"]);

        service.setSelection(["file3", "file4"]);

        expect(service.getSelectedCount()).toBe(2);
        expect(service.isSelected("file1")).toBe(false);
        expect(service.isSelected("file2")).toBe(false);
        expect(service.isSelected("file3")).toBe(true);
        expect(service.isSelected("file4")).toBe(true);
    });

    it("should select range (for shift+click)", () => {
        service.select("file1");

        service.selectRange(["file2", "file3", "file4"]);

        expect(service.getSelectedCount()).toBe(3);
        expect(service.isSelected("file1")).toBe(false);  // Previous cleared
        expect(service.isSelected("file2")).toBe(true);
        expect(service.isSelected("file3")).toBe(true);
        expect(service.isSelected("file4")).toBe(true);
    });

    // =========================================================================
    // Prune Selection Tests
    // =========================================================================

    it("should prune non-existent files from selection", () => {
        service.selectMultiple(["file1", "file2", "file3"]);

        service.pruneSelection(new Set(["file1", "file3"]));

        expect(service.getSelectedCount()).toBe(2);
        expect(service.isSelected("file1")).toBe(true);
        expect(service.isSelected("file2")).toBe(false);  // Pruned
        expect(service.isSelected("file3")).toBe(true);
    });

    // =========================================================================
    // Signal Tests (Session 16)
    // =========================================================================

    describe("Signal-based state", () => {
        it("should expose selectedFiles as a signal", () => {
            expect(service.selectedFiles).toBeDefined();
            // Read signal value
            expect(service.selectedFiles().size).toBe(0);
        });

        it("should expose computed selectedCount signal", () => {
            expect(service.selectedCount).toBeDefined();
            expect(service.selectedCount()).toBe(0);

            service.selectMultiple(["file1", "file2", "file3"]);
            expect(service.selectedCount()).toBe(3);
        });

        it("should expose computed hasSelection signal", () => {
            expect(service.hasSelection).toBeDefined();
            expect(service.hasSelection()).toBe(false);

            service.select("file1");
            expect(service.hasSelection()).toBe(true);

            service.clearSelection();
            expect(service.hasSelection()).toBe(false);
        });

        it("should update signal value when selecting", () => {
            service.select("file1");
            expect(service.selectedFiles().has("file1")).toBe(true);

            service.select("file2");
            expect(service.selectedFiles().has("file2")).toBe(true);
        });

        it("should update signal value when deselecting", () => {
            service.selectMultiple(["file1", "file2"]);
            service.deselect("file1");

            expect(service.selectedFiles().has("file1")).toBe(false);
            expect(service.selectedFiles().has("file2")).toBe(true);
        });

        it("should update signal value when clearing", () => {
            service.selectMultiple(["file1", "file2", "file3"]);
            service.clearSelection();

            expect(service.selectedFiles().size).toBe(0);
        });
    });

    // =========================================================================
    // Observable Tests (backwards compatibility)
    // Note: toObservable() uses Angular's effect system internally, which requires
    // TestBed.flushEffects() to trigger emissions in tests.
    // =========================================================================

    it("should emit on selectedFiles$ when selection changes", () => {
        const emissions: Set<string>[] = [];

        service.selectedFiles$.subscribe(files => {
            emissions.push(files);
        });

        // Flush effects to get initial emission
        TestBed.flushEffects();
        expect(emissions.length).toBe(1);
        expect(emissions[0].size).toBe(0);

        service.select("file1");
        TestBed.flushEffects();
        expect(emissions.length).toBe(2);
        expect(emissions[1].size).toBe(1);
        expect(emissions[1].has("file1")).toBe(true);

        service.deselect("file1");
        TestBed.flushEffects();
        expect(emissions.length).toBe(3);
        expect(emissions[2].size).toBe(0);
    });

    it("should emit on selectedCount$ when selection changes", () => {
        const emissions: number[] = [];

        service.selectedCount$.subscribe(count => {
            emissions.push(count);
        });

        // Flush effects to get initial emission
        TestBed.flushEffects();
        expect(emissions.length).toBe(1);
        expect(emissions[0]).toBe(0);

        service.selectMultiple(["file1", "file2"]);
        TestBed.flushEffects();
        expect(emissions.length).toBe(2);
        expect(emissions[1]).toBe(2);

        service.clearSelection();
        TestBed.flushEffects();
        expect(emissions.length).toBe(3);
        expect(emissions[2]).toBe(0);
    });

    it("should emit on hasSelection$ when selection changes", () => {
        const emissions: boolean[] = [];

        service.hasSelection$.subscribe(has => {
            emissions.push(has);
        });

        // Flush effects to get initial emission
        TestBed.flushEffects();
        expect(emissions.length).toBe(1);
        expect(emissions[0]).toBe(false);

        service.select("file1");
        TestBed.flushEffects();
        expect(emissions.length).toBe(2);
        expect(emissions[1]).toBe(true);

        service.clearSelection();
        TestBed.flushEffects();
        expect(emissions.length).toBe(3);
        expect(emissions[2]).toBe(false);
    });

    // =========================================================================
    // Edge Cases
    // =========================================================================

    it("should return new Set from getSelectedFiles to prevent mutation", () => {
        service.select("file1");

        const files1 = service.getSelectedFiles();
        const files2 = service.getSelectedFiles();

        expect(files1).not.toBe(files2);  // Different objects
        expect(files1).toEqual(files2);   // Same content
    });

    it("should handle empty array in selectMultiple", () => {
        service.select("file1");
        service.selectMultiple([]);

        expect(service.getSelectedCount()).toBe(1);
    });

    it("should handle empty array in selectAllVisible", () => {
        service.select("file1");
        service.selectAllVisible([]);

        expect(service.getSelectedCount()).toBe(1);
    });

    it("should not emit when no actual change occurs", () => {
        let emissionCount = 0;

        service.selectedFiles$.subscribe(() => {
            emissionCount++;
        });

        // Flush effects to get initial emission
        TestBed.flushEffects();
        expect(emissionCount).toBe(1);

        // Try to deselect non-existent file - should not emit
        service.deselect("nonexistent");
        TestBed.flushEffects();

        expect(emissionCount).toBe(1);  // Still 1
    });

    // =========================================================================
    // Performance Tests
    // =========================================================================

    describe("Performance with large file counts", () => {

        it("should select 500 files efficiently (under 50ms)", () => {
            const files: ViewFile[] = [];
            for (let i = 0; i < 500; i++) {
                files.push(new ViewFile({name: `file${i}`}));
            }

            const start = performance.now();
            service.selectAllVisible(files);
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(500);
            expect(elapsed).toBeLessThan(50);
        });

        it("should toggle selection efficiently with 500 files selected", () => {
            // Select 500 files first
            const files: ViewFile[] = [];
            for (let i = 0; i < 500; i++) {
                files.push(new ViewFile({name: `file${i}`}));
            }
            service.selectAllVisible(files);

            // Measure toggle performance
            const start = performance.now();
            service.toggle("file250");
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(499);
            expect(elapsed).toBeLessThan(10);
        });

        it("should clear 500 selections efficiently", () => {
            // Select 500 files first
            const files: ViewFile[] = [];
            for (let i = 0; i < 500; i++) {
                files.push(new ViewFile({name: `file${i}`}));
            }
            service.selectAllVisible(files);

            // Measure clear performance
            const start = performance.now();
            service.clearSelection();
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(0);
            expect(elapsed).toBeLessThan(10);
        });

        it("should handle rapid toggle cycles without memory leaks", () => {
            const files: ViewFile[] = [];
            for (let i = 0; i < 100; i++) {
                files.push(new ViewFile({name: `file${i}`}));
            }

            // Rapid select/clear cycles
            for (let cycle = 0; cycle < 100; cycle++) {
                service.selectAllVisible(files);
                service.clearSelection();
            }

            expect(service.getSelectedCount()).toBe(0);
        });

        it("should handle isSelected lookup efficiently with 500 files", () => {
            // Select 500 files first
            const fileNames: string[] = [];
            for (let i = 0; i < 500; i++) {
                fileNames.push(`file${i}`);
            }
            service.selectMultiple(fileNames);

            // Measure lookup performance (1000 lookups)
            const start = performance.now();
            for (let i = 0; i < 1000; i++) {
                service.isSelected(`file${i % 500}`);
            }
            const elapsed = performance.now() - start;

            // 1000 lookups should complete in under 10ms
            expect(elapsed).toBeLessThan(10);
        });

        it("should prune 500 selections efficiently", () => {
            // Select 500 files
            const fileNames: string[] = [];
            for (let i = 0; i < 500; i++) {
                fileNames.push(`file${i}`);
            }
            service.selectMultiple(fileNames);

            // Create a set with only 250 files (simulating half deleted)
            const remainingFiles = new Set<string>();
            for (let i = 0; i < 250; i++) {
                remainingFiles.add(`file${i}`);
            }

            // Measure prune performance
            const start = performance.now();
            service.pruneSelection(remainingFiles);
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(250);
            expect(elapsed).toBeLessThan(20);
        });

        it("should handle range selection with 500 files efficiently", () => {
            // Create range of 500 file names
            const fileNames: string[] = [];
            for (let i = 0; i < 500; i++) {
                fileNames.push(`file${i}`);
            }

            // Measure range selection performance
            const start = performance.now();
            service.selectRange(fileNames);
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(500);
            expect(elapsed).toBeLessThan(50);
        });
    });

    // =========================================================================
    // Large Scale Tests (1000+ files)
    // =========================================================================

    describe("Large scale selection (1000+ files)", () => {

        it("should select 1000 files efficiently", () => {
            const files: ViewFile[] = [];
            for (let i = 0; i < 1000; i++) {
                files.push(new ViewFile({name: `file${i}`}));
            }

            const start = performance.now();
            service.selectAllVisible(files);
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(1000);
            expect(elapsed).toBeLessThan(100);
        });

        it("should select 5000 files efficiently", () => {
            const files: ViewFile[] = [];
            for (let i = 0; i < 5000; i++) {
                files.push(new ViewFile({name: `file${i}`}));
            }

            const start = performance.now();
            service.selectAllVisible(files);
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(5000);
            expect(elapsed).toBeLessThan(500);
        });

        it("should clear 5000 selections efficiently", () => {
            // Select 5000 files
            const files: ViewFile[] = [];
            for (let i = 0; i < 5000; i++) {
                files.push(new ViewFile({name: `file${i}`}));
            }
            service.selectAllVisible(files);

            const start = performance.now();
            service.clearSelection();
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(0);
            expect(elapsed).toBeLessThan(50);
        });

        it("should handle isSelected lookup efficiently with 5000 files", () => {
            const fileNames: string[] = [];
            for (let i = 0; i < 5000; i++) {
                fileNames.push(`file${i}`);
            }
            service.selectMultiple(fileNames);

            // Measure 5000 lookups
            const start = performance.now();
            for (let i = 0; i < 5000; i++) {
                service.isSelected(`file${i}`);
            }
            const elapsed = performance.now() - start;

            // 5000 lookups should complete in under 50ms (O(1) per lookup)
            expect(elapsed).toBeLessThan(50);
        });

        it("should prune 5000 selections efficiently", () => {
            const fileNames: string[] = [];
            for (let i = 0; i < 5000; i++) {
                fileNames.push(`file${i}`);
            }
            service.selectMultiple(fileNames);

            // Keep only 2500 files
            const remainingFiles = new Set<string>();
            for (let i = 0; i < 2500; i++) {
                remainingFiles.add(`file${i}`);
            }

            const start = performance.now();
            service.pruneSelection(remainingFiles);
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(2500);
            expect(elapsed).toBeLessThan(100);
        });
    });

    // =========================================================================
    // Memory and GC Behavior Tests
    // =========================================================================

    describe("Memory and garbage collection behavior", () => {

        it("should not retain references to old selection sets after clear", () => {
            // Select some files
            service.selectMultiple(["file1", "file2", "file3"]);
            const oldSet = service.getSelectedFiles();

            // Clear selection
            service.clearSelection();
            const newSet = service.getSelectedFiles();

            // Old set should still have its values (it's a copy)
            expect(oldSet.size).toBe(3);
            // New set should be empty
            expect(newSet.size).toBe(0);
            // They should be different objects
            expect(oldSet).not.toBe(newSet);
        });

        it("should create new Set objects on each signal update to support immutability", () => {
            const set1 = service.selectedFiles();

            service.select("file1");
            const set2 = service.selectedFiles();

            service.select("file2");
            const set3 = service.selectedFiles();

            // All sets should be different objects
            expect(set1).not.toBe(set2);
            expect(set2).not.toBe(set3);
        });

        it("should survive 1000 rapid select/clear cycles without issues", () => {
            const files: ViewFile[] = [];
            for (let i = 0; i < 100; i++) {
                files.push(new ViewFile({name: `file${i}`}));
            }

            const start = performance.now();
            for (let cycle = 0; cycle < 1000; cycle++) {
                service.selectAllVisible(files);
                service.clearSelection();
            }
            const elapsed = performance.now() - start;

            expect(service.getSelectedCount()).toBe(0);
            // 1000 cycles should complete in under 2 seconds
            expect(elapsed).toBeLessThan(2000);
        });

        it("should handle repeated large selections without accumulating memory", () => {
            // This test verifies that selections are properly cleared
            // and don't accumulate across multiple select/clear cycles

            for (let round = 0; round < 10; round++) {
                const files: ViewFile[] = [];
                for (let i = 0; i < 1000; i++) {
                    files.push(new ViewFile({name: `round${round}_file${i}`}));
                }
                service.selectAllVisible(files);
                expect(service.getSelectedCount()).toBe(1000);
                service.clearSelection();
                expect(service.getSelectedCount()).toBe(0);
            }

            // After all rounds, selection should be empty
            expect(service.getSelectedCount()).toBe(0);
        });
    });

    // =========================================================================
    // Serialization Tests (for future persistence)
    // =========================================================================

    describe("Selection state serialization", () => {

        it("should be able to export selection state as array", () => {
            service.selectMultiple(["file1", "file2", "file3"]);

            // Get selected files as array (serializable)
            const selectedArray = Array.from(service.getSelectedFiles());

            expect(selectedArray).toContain("file1");
            expect(selectedArray).toContain("file2");
            expect(selectedArray).toContain("file3");
            expect(selectedArray.length).toBe(3);
        });

        it("should be able to restore selection from array", () => {
            const savedSelection = ["file1", "file2", "file3"];

            // Restore selection
            service.setSelection(savedSelection);

            expect(service.getSelectedCount()).toBe(3);
            expect(service.isSelected("file1")).toBe(true);
            expect(service.isSelected("file2")).toBe(true);
            expect(service.isSelected("file3")).toBe(true);
        });
    });

    // =========================================================================
    // Operation Lock Tests (Session 18 - Race Condition Prevention)
    // =========================================================================

    describe("Operation lock for race condition prevention", () => {

        it("should expose operationInProgress as a readonly signal", () => {
            expect(service.operationInProgress).toBeDefined();
            expect(service.operationInProgress()).toBe(false);
        });

        it("should set operationInProgress to true when beginOperation is called", () => {
            service.beginOperation();

            expect(service.operationInProgress()).toBe(true);
        });

        it("should set operationInProgress to false when endOperation is called", () => {
            service.beginOperation();
            service.endOperation();

            expect(service.operationInProgress()).toBe(false);
        });

        it("should skip pruneSelection when operation is in progress", () => {
            // Select some files
            service.selectMultiple(["file1", "file2", "file3"]);
            expect(service.getSelectedCount()).toBe(3);

            // Start an operation
            service.beginOperation();

            // Try to prune (simulating file list update during bulk operation)
            // Only file1 "exists" - file2 and file3 would normally be pruned
            service.pruneSelection(new Set(["file1"]));

            // Selection should be unchanged because operation is in progress
            expect(service.getSelectedCount()).toBe(3);
            expect(service.isSelected("file1")).toBe(true);
            expect(service.isSelected("file2")).toBe(true);
            expect(service.isSelected("file3")).toBe(true);
        });

        it("should allow pruneSelection after operation ends", () => {
            // Select some files
            service.selectMultiple(["file1", "file2", "file3"]);

            // Start and end an operation
            service.beginOperation();
            service.endOperation();

            // Now prune should work
            service.pruneSelection(new Set(["file1"]));

            expect(service.getSelectedCount()).toBe(1);
            expect(service.isSelected("file1")).toBe(true);
            expect(service.isSelected("file2")).toBe(false);
            expect(service.isSelected("file3")).toBe(false);
        });

        it("should handle multiple begin/end cycles correctly", () => {
            service.selectMultiple(["file1", "file2"]);

            // First cycle
            service.beginOperation();
            expect(service.operationInProgress()).toBe(true);
            service.pruneSelection(new Set(["file1"])); // Should be skipped
            expect(service.getSelectedCount()).toBe(2);
            service.endOperation();
            expect(service.operationInProgress()).toBe(false);

            // Second cycle
            service.beginOperation();
            expect(service.operationInProgress()).toBe(true);
            service.pruneSelection(new Set(["file1"])); // Should be skipped
            expect(service.getSelectedCount()).toBe(2);
            service.endOperation();
            expect(service.operationInProgress()).toBe(false);

            // Now prune should work
            service.pruneSelection(new Set(["file1"]));
            expect(service.getSelectedCount()).toBe(1);
        });

        it("should not block other selection operations during operation", () => {
            service.beginOperation();

            // These should still work
            service.select("file1");
            expect(service.isSelected("file1")).toBe(true);

            service.deselect("file1");
            expect(service.isSelected("file1")).toBe(false);

            service.selectMultiple(["file2", "file3"]);
            expect(service.getSelectedCount()).toBe(2);

            service.clearSelection();
            expect(service.getSelectedCount()).toBe(0);

            service.endOperation();
        });
    });
});
