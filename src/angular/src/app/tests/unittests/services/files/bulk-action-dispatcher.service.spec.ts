import {TestBed, fakeAsync, tick} from "@angular/core/testing";
import {Observable, of} from "rxjs";

import {BulkActionDispatcher} from "../../../../services/files/bulk-action-dispatcher.service";
import {FileSelectionService} from "../../../../services/files/file-selection.service";
import {BulkCommandService, BulkActionResult} from "../../../../services/server/bulk-command.service";
import {ConfirmModalService} from "../../../../services/utils/confirm-modal.service";
import {NotificationService} from "../../../../services/utils/notification.service";
import {Notification} from "../../../../services/utils/notification";


function okResult(succeeded = 1, failed = 0): BulkActionResult {
    return new BulkActionResult(
        true,
        {results: [], summary: {total: succeeded + failed, succeeded, failed}} as any,
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
