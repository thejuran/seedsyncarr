import {TestBed, fakeAsync, tick} from "@angular/core/testing";
import {HttpClientTestingModule, HttpTestingController} from "@angular/common/http/testing";

import {BulkCommandService, BulkAction, BulkActionResult, BulkActionResponse} from "../../../../services/server/bulk-command.service";
import {LoggerService} from "../../../../services/utils/logger.service";

describe("BulkCommandService", () => {
    let service: BulkCommandService;
    let httpMock: HttpTestingController;
    let mockLogger: jasmine.SpyObj<LoggerService>;

    beforeEach(() => {
        mockLogger = jasmine.createSpyObj("LoggerService", ["debug", "info", "error"]);

        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                BulkCommandService,
                {provide: LoggerService, useValue: mockLogger}
            ]
        });

        service = TestBed.inject(BulkCommandService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    describe("executeBulkAction", () => {
        const testActions: BulkAction[] = ["queue", "stop", "extract", "delete_local", "delete_remote"];

        testActions.forEach(action => {
            it(`should send POST request with ${action} action`, fakeAsync(() => {
                const files = ["file1.txt", "file2.txt"];
                let result: BulkActionResult | undefined;

                service.executeBulkAction(action, files).subscribe(r => result = r);

                const req = httpMock.expectOne("/server/command/bulk");
                expect(req.request.method).toBe("POST");
                expect(req.request.body).toEqual({action, files});

                req.flush({
                    results: [
                        {file: "file1.txt", success: true},
                        {file: "file2.txt", success: true}
                    ],
                    summary: {total: 2, succeeded: 2, failed: 0}
                } as BulkActionResponse);

                tick();

                expect(result).toBeDefined();
                expect(result?.success).toBeTrue();
                expect(result?.allSucceeded).toBeTrue();
                expect(result?.response?.summary.succeeded).toBe(2);
            }));
        });

        it("should handle successful response with all files succeeded", fakeAsync(() => {
            const files = ["file1.txt", "file2.txt", "file3.txt"];
            let result: BulkActionResult | undefined;

            service.executeBulkAction("queue", files).subscribe(r => result = r);

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush({
                results: [
                    {file: "file1.txt", success: true},
                    {file: "file2.txt", success: true},
                    {file: "file3.txt", success: true}
                ],
                summary: {total: 3, succeeded: 3, failed: 0}
            });

            tick();

            expect(result?.success).toBeTrue();
            expect(result?.allSucceeded).toBeTrue();
            expect(result?.hasPartialFailure).toBeFalse();
            expect(result?.response?.summary.total).toBe(3);
            expect(result?.response?.summary.succeeded).toBe(3);
            expect(result?.response?.summary.failed).toBe(0);
        }));

        it("should handle partial failure response", fakeAsync(() => {
            const files = ["file1.txt", "file2.txt", "file3.txt"];
            let result: BulkActionResult | undefined;

            service.executeBulkAction("queue", files).subscribe(r => result = r);

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush({
                results: [
                    {file: "file1.txt", success: true},
                    {file: "file2.txt", success: false, error: "File not found", error_code: 404},
                    {file: "file3.txt", success: true}
                ],
                summary: {total: 3, succeeded: 2, failed: 1}
            });

            tick();

            expect(result?.success).toBeTrue();
            expect(result?.allSucceeded).toBeFalse();
            expect(result?.hasPartialFailure).toBeTrue();
            expect(result?.response?.summary.total).toBe(3);
            expect(result?.response?.summary.succeeded).toBe(2);
            expect(result?.response?.summary.failed).toBe(1);

            // Check individual file results
            const failedFile = result?.response?.results.find(r => r.file === "file2.txt");
            expect(failedFile?.success).toBeFalse();
            expect(failedFile?.error).toBe("File not found");
            expect(failedFile?.error_code).toBe(404);
        }));

        it("should handle all files failed response", fakeAsync(() => {
            const files = ["file1.txt", "file2.txt"];
            let result: BulkActionResult | undefined;

            service.executeBulkAction("queue", files).subscribe(r => result = r);

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush({
                results: [
                    {file: "file1.txt", success: false, error: "Error 1", error_code: 500},
                    {file: "file2.txt", success: false, error: "Error 2", error_code: 500}
                ],
                summary: {total: 2, succeeded: 0, failed: 2}
            });

            tick();

            expect(result?.success).toBeTrue(); // Request succeeded, but operations failed
            expect(result?.allSucceeded).toBeFalse();
            expect(result?.hasPartialFailure).toBeTrue(); // failed > 0
            expect(result?.response?.summary.succeeded).toBe(0);
            expect(result?.response?.summary.failed).toBe(2);
        }));

        it("should handle HTTP 400 error with JSON error body", fakeAsync(() => {
            const files = ["file1.txt"];
            let result: BulkActionResult | undefined;

            service.executeBulkAction("queue", files).subscribe(r => result = r);

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush(
                {error: "Invalid action 'invalid'. Valid actions: queue, stop, extract, delete_local, delete_remote"},
                {status: 400, statusText: "Bad Request"}
            );

            tick();

            expect(result?.success).toBeFalse();
            expect(result?.response).toBeNull();
            expect(result?.errorMessage).toContain("Invalid action");
        }));

        it("should handle HTTP 400 error with invalid files array", fakeAsync(() => {
            const files = ["file1.txt"];
            let result: BulkActionResult | undefined;

            service.executeBulkAction("queue", files).subscribe(r => result = r);

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush(
                {error: "files array is required and must not be empty"},
                {status: 400, statusText: "Bad Request"}
            );

            tick();

            expect(result?.success).toBeFalse();
            expect(result?.errorMessage).toContain("files array is required");
        }));

        it("should handle network error", fakeAsync(() => {
            const files = ["file1.txt"];
            let result: BulkActionResult | undefined;

            service.executeBulkAction("queue", files).subscribe(r => result = r);

            const req = httpMock.expectOne("/server/command/bulk");
            req.error(new ProgressEvent("error"));

            tick();

            expect(result?.success).toBeFalse();
            expect(result?.response).toBeNull();
            expect(result?.errorMessage).toBeDefined();
        }));

        it("should handle string error response", fakeAsync(() => {
            const files = ["file1.txt"];
            let result: BulkActionResult | undefined;

            service.executeBulkAction("queue", files).subscribe(r => result = r);

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush(
                "Internal server error",
                {status: 500, statusText: "Internal Server Error"}
            );

            tick();

            expect(result?.success).toBeFalse();
            expect(result?.errorMessage).toBe("Internal server error");
        }));

        it("should log debug info on successful response", fakeAsync(() => {
            const files = ["file1.txt"];

            service.executeBulkAction("queue", files).subscribe();

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush({
                results: [{file: "file1.txt", success: true}],
                summary: {total: 1, succeeded: 1, failed: 0}
            });

            tick();

            expect(mockLogger.debug).toHaveBeenCalledWith(
                "%s bulk response: %O",
                "/server/command/bulk",
                jasmine.any(Object)
            );
        }));

        it("should log debug info on error response", fakeAsync(() => {
            const files = ["file1.txt"];

            service.executeBulkAction("queue", files).subscribe();

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush({error: "Test error"}, {status: 400, statusText: "Bad Request"});

            tick();

            expect(mockLogger.debug).toHaveBeenCalledWith(
                "%s error: %O",
                "/server/command/bulk",
                jasmine.any(Object)
            );
        }));

        it("should share replay for multiple subscribers", fakeAsync(() => {
            const files = ["file1.txt"];
            const results: BulkActionResult[] = [];

            const observable = service.executeBulkAction("queue", files);

            observable.subscribe(r => results.push(r));
            observable.subscribe(r => results.push(r));

            const req = httpMock.expectOne("/server/command/bulk");
            req.flush({
                results: [{file: "file1.txt", success: true}],
                summary: {total: 1, succeeded: 1, failed: 0}
            });

            tick();

            // Both subscribers should get the same result
            expect(results.length).toBe(2);
            expect(results[0]).toBe(results[1]);
        }));
    });

    describe("BulkActionResult", () => {
        it("should report allSucceeded true when failed is 0", () => {
            const result = new BulkActionResult(true, {
                results: [],
                summary: {total: 5, succeeded: 5, failed: 0}
            }, null);

            expect(result.allSucceeded).toBeTrue();
            expect(result.hasPartialFailure).toBeFalse();
        });

        it("should report hasPartialFailure true when failed > 0", () => {
            const result = new BulkActionResult(true, {
                results: [],
                summary: {total: 5, succeeded: 3, failed: 2}
            }, null);

            expect(result.allSucceeded).toBeFalse();
            expect(result.hasPartialFailure).toBeTrue();
        });

        it("should report allSucceeded false on failed request", () => {
            const result = new BulkActionResult(false, null, "Error message");

            expect(result.allSucceeded).toBeFalse();
            expect(result.hasPartialFailure).toBeFalse();
        });
    });
});
