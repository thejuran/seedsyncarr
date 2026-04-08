import {IsSelectedPipe} from "../../../common/is-selected.pipe";


describe("IsSelectedPipe", () => {
    let pipe: IsSelectedPipe;

    beforeEach(() => {
        pipe = new IsSelectedPipe();
    });

    it("should create an instance", () => {
        expect(pipe).toBeTruthy();
    });

    it("should return true for selected file", () => {
        const selectedFiles = new Set(["file1", "file2", "file3"]);
        expect(pipe.transform("file1", selectedFiles)).toBe(true);
        expect(pipe.transform("file2", selectedFiles)).toBe(true);
        expect(pipe.transform("file3", selectedFiles)).toBe(true);
    });

    it("should return false for non-selected file", () => {
        const selectedFiles = new Set(["file1", "file2"]);
        expect(pipe.transform("file3", selectedFiles)).toBe(false);
        expect(pipe.transform("file4", selectedFiles)).toBe(false);
    });

    it("should return false for empty selection set", () => {
        const selectedFiles = new Set<string>();
        expect(pipe.transform("file1", selectedFiles)).toBe(false);
    });

    it("should return false for null fileName", () => {
        const selectedFiles = new Set(["file1"]);
        expect(pipe.transform(null as unknown as string, selectedFiles)).toBe(false);
    });

    it("should return false for undefined fileName", () => {
        const selectedFiles = new Set(["file1"]);
        expect(pipe.transform(undefined as unknown as string, selectedFiles)).toBe(false);
    });

    it("should return false for null selectedFiles", () => {
        expect(pipe.transform("file1", null as unknown as Set<string>)).toBe(false);
    });

    it("should return false for undefined selectedFiles", () => {
        expect(pipe.transform("file1", undefined as unknown as Set<string>)).toBe(false);
    });

    // =========================================================================
    // Performance Tests
    // =========================================================================

    describe("Performance", () => {
        it("should handle large selection set efficiently", () => {
            // Create a set with 10000 files
            const selectedFiles = new Set<string>();
            for (let i = 0; i < 10000; i++) {
                selectedFiles.add(`file${i}`);
            }

            // Perform 10000 lookups
            const start = performance.now();
            for (let i = 0; i < 10000; i++) {
                pipe.transform(`file${i}`, selectedFiles);
            }
            const elapsed = performance.now() - start;

            // 10000 lookups should complete in under 10ms (Set.has is O(1))
            expect(elapsed).toBeLessThan(10);
        });

        it("should be efficient for repeated lookups on same file", () => {
            const selectedFiles = new Set(["file1", "file2", "file3"]);

            // Perform 10000 lookups on the same file
            const start = performance.now();
            for (let i = 0; i < 10000; i++) {
                pipe.transform("file1", selectedFiles);
            }
            const elapsed = performance.now() - start;

            // Should complete in under 5ms
            expect(elapsed).toBeLessThan(5);
        });
    });
});
