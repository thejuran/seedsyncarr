import {TestBed, fakeAsync, tick} from "@angular/core/testing";
import {Observable, of} from "rxjs";

import {BulkActionDispatcher} from "../../../../services/files/bulk-action-dispatcher.service";
import {FileSelectionService} from "../../../../services/files/file-selection.service";
import {BulkCommandService, BulkActionResult, BulkActionResponse, BulkFileResult} from "../../../../services/server/bulk-command.service";
import {ConfirmModalService} from "../../../../services/utils/confirm-modal.service";
import {NotificationService} from "../../../../services/utils/notification.service";
import {Notification} from "../../../../services/utils/notification";
import {Localization} from "../../../../common/localization";


function okResult(succeeded = 1, failed = 0): BulkActionResult {
    return new BulkActionResult(
        true,
        {results: [], summary: {total: succeeded + failed, succeeded, failed}} as BulkActionResponse,
        null
    );
}

function perFileResult(results: BulkFileResult[]): BulkActionResult {
    const failed = results.filter(r => !r.success).length;
    return new BulkActionResult(
        true,
        {results, summary: {total: results.length, succeeded: results.length - failed, failed}},
        null
    );
}

function failResult(message: string, status: number | null): BulkActionResult {
    return new BulkActionResult(false, null, message, status);
}


describe("BulkActionDispatcher", () => {
    let dispatcher: BulkActionDispatcher;
    let selection: FileSelectionService;
    let bulkCommand: {executeBulkAction: jasmine.Spy};
    let confirmModal: {confirm: jasmine.Spy};
    let notification: {show: jasmine.Spy; hide: jasmine.Spy};

    beforeEach(() => {
        bulkCommand = {
            executeBulkAction: jasmine.createSpy("executeBulkAction").and.returnValue(of(okResult()))
        };
        confirmModal = {
            confirm: jasmine.createSpy("confirm").and.returnValue(Promise.resolve(true))
        };
        notification = {
            show: jasmine.createSpy("show"),
            hide: jasmine.createSpy("hide")
        };

        TestBed.configureTestingModule({
            providers: [
                {provide: BulkCommandService, useValue: bulkCommand},
                {provide: ConfirmModalService, useValue: confirmModal},
                {provide: NotificationService, useValue: notification}
            ]
        });

        dispatcher = TestBed.inject(BulkActionDispatcher);
        selection = TestBed.inject(FileSelectionService);
        selection.clearSelection();
    });

    describe("action routing", () => {
        it("dispatchQueue forwards 'queue' and its file list", () => {
            dispatcher.dispatchQueue(["a", "b"]);
            expect(bulkCommand.executeBulkAction).toHaveBeenCalledWith("queue", ["a", "b"]);
        });

        it("dispatchStop forwards 'stop'", () => {
            dispatcher.dispatchStop(["a"]);
            expect(bulkCommand.executeBulkAction).toHaveBeenCalledWith("stop", ["a"]);
        });

        it("dispatchExtract forwards 'extract'", () => {
            dispatcher.dispatchExtract(["a"]);
            expect(bulkCommand.executeBulkAction).toHaveBeenCalledWith("extract", ["a"]);
        });

        it("confirmAndDispatchDeleteLocal shows modal then dispatches on confirm", async () => {
            await dispatcher.confirmAndDispatchDeleteLocal(["a", "b"], /* selectedCount */ 3);

            expect(confirmModal.confirm).toHaveBeenCalled();
            const arg = confirmModal.confirm.calls.mostRecent().args[0];
            expect(arg.skipCount).toBe(1);
            expect(bulkCommand.executeBulkAction).toHaveBeenCalledWith("delete_local", ["a", "b"]);
        });

        it("confirmAndDispatchDeleteLocal skips dispatch when user cancels", async () => {
            confirmModal.confirm.and.returnValue(Promise.resolve(false));

            await dispatcher.confirmAndDispatchDeleteLocal(["a"], 1);

            expect(bulkCommand.executeBulkAction).not.toHaveBeenCalled();
        });

        it("confirmAndDispatchDeleteRemote passes the remote title", async () => {
            await dispatcher.confirmAndDispatchDeleteRemote(["a"], 1);

            const arg = confirmModal.confirm.calls.mostRecent().args[0];
            expect(arg.title).toContain("Remote");
        });

        it("confirmAndDispatchDelete* omits skipCount when all selected are eligible", async () => {
            await dispatcher.confirmAndDispatchDeleteLocal(["a", "b"], /* selectedCount */ 2);

            const arg = confirmModal.confirm.calls.mostRecent().args[0];
            expect(arg.skipCount).toBeUndefined();
        });
    });

    describe("concurrency gate", () => {
        it("inProgress starts false", () => {
            expect(dispatcher.inProgress()).toBe(false);
        });

        it("flips inProgress true while dispatch is in flight, back to false on completion", fakeAsync(() => {
            const pending = new Observable<BulkActionResult>(() => { /* never emits */ });
            bulkCommand.executeBulkAction.and.returnValue(pending);

            dispatcher.dispatchQueue(["a"]);
            expect(dispatcher.inProgress()).toBe(true);

            // Second attempt is gated
            dispatcher.dispatchQueue(["b"]);
            expect(bulkCommand.executeBulkAction).toHaveBeenCalledTimes(1);
        }));

        it("returns to !inProgress after a successful dispatch completes", fakeAsync(() => {
            dispatcher.dispatchQueue(["a"]);
            tick();
            expect(dispatcher.inProgress()).toBe(false);
        }));
    });

    describe("selection retention on failure", () => {
        it("preserves selection when errorStatus is a 5xx", fakeAsync(() => {
            selection.setSelection(["a", "b"]);
            bulkCommand.executeBulkAction.and.returnValue(of(failResult("Internal Server Error", 503)));

            dispatcher.dispatchQueue(["a", "b"]);
            tick();

            expect(selection.getSelectedCount()).toBe(2);
        }));

        it("preserves selection when errorStatus is 429 (rate limit)", fakeAsync(() => {
            selection.setSelection(["a"]);
            bulkCommand.executeBulkAction.and.returnValue(of(failResult("Too Many Requests", 429)));

            dispatcher.dispatchQueue(["a"]);
            tick();

            expect(selection.getSelectedCount()).toBe(1);
        }));

        it("preserves selection when errorStatus is 0 (network error)", fakeAsync(() => {
            selection.setSelection(["a"]);
            bulkCommand.executeBulkAction.and.returnValue(of(failResult("Network", 0)));

            dispatcher.dispatchQueue(["a"]);
            tick();

            expect(selection.getSelectedCount()).toBe(1);
        }));

        it("clears selection on permanent failure (HTTP 400)", fakeAsync(() => {
            selection.setSelection(["a", "b"]);
            bulkCommand.executeBulkAction.and.returnValue(of(failResult("Bad Request", 400)));

            dispatcher.dispatchQueue(["a", "b"]);
            tick();

            expect(selection.getSelectedCount()).toBe(0);
        }));

        it("clears selection on success", fakeAsync(() => {
            selection.setSelection(["a"]);
            bulkCommand.executeBulkAction.and.returnValue(of(okResult()));

            dispatcher.dispatchQueue(["a"]);
            tick();

            expect(selection.getSelectedCount()).toBe(0);
        }));
    });

    describe("notifications", () => {
        it("shows SUCCESS notification on all-succeeded response", fakeAsync(() => {
            bulkCommand.executeBulkAction.and.returnValue(of(okResult(3, 0)));

            dispatcher.dispatchQueue(["a", "b", "c"]);
            tick();

            expect(notification.show).toHaveBeenCalled();
            const shown = notification.show.calls.mostRecent().args[0];
            expect(shown.level).toBe(Notification.Level.SUCCESS);
        }));

        it("shows WARNING notification on partial failure", fakeAsync(() => {
            bulkCommand.executeBulkAction.and.returnValue(of(okResult(2, 1)));

            dispatcher.dispatchQueue(["a", "b", "c"]);
            tick();

            const shown = notification.show.calls.mostRecent().args[0];
            expect(shown.level).toBe(Notification.Level.WARNING);
        }));

        it("shows DANGER notification on failure", fakeAsync(() => {
            bulkCommand.executeBulkAction.and.returnValue(of(failResult("Bad Request", 400)));

            dispatcher.dispatchQueue(["a"]);
            tick();

            const shown = notification.show.calls.mostRecent().args[0];
            expect(shown.level).toBe(Notification.Level.DANGER);
        }));
    });

    describe("release of unverified transfers (428)", () => {
        const MIXED: BulkFileResult[] = [
            {file: "A", success: true},
            {file: "B", success: false, error: "Completion could not be verified: Still downloading", error_code: 428},
            {file: "C", success: false, error: "File 'C' not found", error_code: 404},
        ];

        it("asks for confirmation once with the verbatim message and the held files", fakeAsync(() => {
            bulkCommand.executeBulkAction.and.returnValues(of(perFileResult(MIXED)), of(okResult(1, 0)));

            dispatcher.dispatchQueue(["A", "B", "C"]);
            tick();

            expect(confirmModal.confirm).toHaveBeenCalledTimes(1);
            const arg = confirmModal.confirm.calls.mostRecent().args[0];
            expect(arg.title).toBe(Localization.Modal.RELEASE_UNVERIFIED_TITLE);
            expect(arg.body.startsWith(
                "Completion could not be verified. Transfer and release this item anyway?")).toBeTrue();
            expect(arg.body).toContain("B");
            expect(arg.body).not.toContain("C");
            expect(arg.okBtn).toBe("Release");
        }));

        it("re-sends queue with releaseUnverified for exactly the 428 files on confirm", fakeAsync(() => {
            bulkCommand.executeBulkAction.and.returnValues(of(perFileResult(MIXED)), of(okResult(1, 0)));

            dispatcher.dispatchQueue(["A", "B", "C"]);
            tick();

            expect(bulkCommand.executeBulkAction).toHaveBeenCalledTimes(2);
            expect(bulkCommand.executeBulkAction.calls.argsFor(0)).toEqual([jasmine.any(String), ["A", "B", "C"]]);
            expect(bulkCommand.executeBulkAction.calls.argsFor(1))
                .toEqual(["queue", ["B"], {releaseUnverified: true}]);
            expect(dispatcher.inProgress()).toBe(false);
        }));

        it("sends nothing more when the user cancels", fakeAsync(() => {
            confirmModal.confirm.and.returnValue(Promise.resolve(false));
            bulkCommand.executeBulkAction.and.returnValue(of(perFileResult(MIXED)));

            dispatcher.dispatchQueue(["A", "B", "C"]);
            tick();

            expect(confirmModal.confirm).toHaveBeenCalledTimes(1);
            expect(bulkCommand.executeBulkAction).toHaveBeenCalledTimes(1);
        }));

        it("never asks when no file needs confirmation", fakeAsync(() => {
            bulkCommand.executeBulkAction.and.returnValue(of(perFileResult([
                {file: "A", success: true},
                {file: "C", success: false, error: "not found", error_code: 404},
            ])));

            dispatcher.dispatchQueue(["A", "C"]);
            tick();

            expect(confirmModal.confirm).not.toHaveBeenCalled();
            expect(bulkCommand.executeBulkAction).toHaveBeenCalledTimes(1);
        }));

        it("does not ask again when the release attempt itself returns 428", fakeAsync(() => {
            const held = perFileResult([MIXED[1]]);
            bulkCommand.executeBulkAction.and.returnValues(of(held), of(held));

            dispatcher.dispatchQueue(["B"]);
            tick();

            expect(confirmModal.confirm).toHaveBeenCalledTimes(1);
            expect(bulkCommand.executeBulkAction).toHaveBeenCalledTimes(2);
        }));

        it("only offers release for queue, not other actions", fakeAsync(() => {
            bulkCommand.executeBulkAction.and.returnValue(of(perFileResult(MIXED)));

            dispatcher.dispatchStop(["A", "B", "C"]);
            tick();

            expect(confirmModal.confirm).not.toHaveBeenCalled();
        }));

        it("skips the partial-failure toast when every failure is a 428", fakeAsync(() => {
            confirmModal.confirm.and.returnValue(Promise.resolve(false));
            bulkCommand.executeBulkAction.and.returnValue(of(perFileResult([
                {file: "A", success: true},
                MIXED[1],
            ])));

            dispatcher.dispatchQueue(["A", "B"]);
            tick();

            expect(notification.show).not.toHaveBeenCalled();
            expect(confirmModal.confirm).toHaveBeenCalledTimes(1);
        }));

        it("still shows the partial-failure toast when a non-428 failure is present", fakeAsync(() => {
            confirmModal.confirm.and.returnValue(Promise.resolve(false));
            bulkCommand.executeBulkAction.and.returnValue(of(perFileResult(MIXED)));

            dispatcher.dispatchQueue(["A", "B", "C"]);
            tick();

            const shown = notification.show.calls.mostRecent().args[0];
            expect(shown.level).toBe(Notification.Level.WARNING);
        }));
    });

    describe("selection-lock contract", () => {
        it("holds the selection-service operation lock for the duration of a dispatch", fakeAsync(() => {
            const pending = new Observable<BulkActionResult>(() => { /* hang */ });
            bulkCommand.executeBulkAction.and.returnValue(pending);

            dispatcher.dispatchQueue(["a"]);
            expect(selection.operationInProgress()).toBe(true);
        }));

        it("releases the selection-service operation lock after success", fakeAsync(() => {
            dispatcher.dispatchQueue(["a"]);
            tick();
            expect(selection.operationInProgress()).toBe(false);
        }));

        it("releases the selection-service operation lock after failure", fakeAsync(() => {
            bulkCommand.executeBulkAction.and.returnValue(of(failResult("Bad Request", 400)));

            dispatcher.dispatchQueue(["a"]);
            tick();

            expect(selection.operationInProgress()).toBe(false);
        }));
    });
});
