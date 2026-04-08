import {fakeAsync, TestBed, tick} from "@angular/core/testing";

import {ServerStatusService} from "../../../../services/server/server-status.service";
import {LoggerService} from "../../../../services/utils/logger.service";
import {ServerStatus, ServerStatusJson} from "../../../../services/server/server-status";


describe("Testing server status service", () => {
    let serverStatusService: ServerStatusService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                LoggerService,
                ServerStatusService
            ]
        });

        serverStatusService = TestBed.inject(ServerStatusService);
    });

    it("should create an instance", () => {
        expect(serverStatusService).toBeDefined();
    });

    it("should register all events with the event source", () => {
        expect(serverStatusService.getEventNames()).toEqual(
            ["status"]
        );
    });

    it("should send correct status on event", fakeAsync(() => {
        let count = 0;
        let latestStatus: ServerStatus = null!;
        serverStatusService.status.subscribe({
            next: status => {
                count++;
                latestStatus = status;
            }
        });

        // Initial status
        tick();
        expect(count).toBe(1);
        expect(latestStatus.server.up).toBe(false);

        // New status
        const statusJson: ServerStatusJson = {
            server: {
                up: true,
                error_msg: null as unknown as string
            },
            controller: {
                latest_local_scan_time: null as unknown as string,
                latest_remote_scan_time: null as unknown as string,
                latest_remote_scan_failed: null as unknown as boolean,
                latest_remote_scan_error: null as unknown as string
            }
        };
        serverStatusService.notifyEvent("status", JSON.stringify(statusJson));
        tick();
        expect(count).toBe(2);
        expect(latestStatus.server.up).toBe(true);

        // Status update
        statusJson.server.up = false;
        statusJson.server.error_msg = "uh oh spaghettios";
        serverStatusService.notifyEvent("status", JSON.stringify(statusJson));
        tick();
        expect(count).toBe(3);
        expect(latestStatus.server.up).toBe(false);
        expect(latestStatus.server.errorMessage).toBe("uh oh spaghettios");
    }));

    it("should send correct status on disconnect", fakeAsync(() => {
        // Initial status
        const statusJson: ServerStatusJson = {
            server: {
                up: true,
                error_msg: null as unknown as string
            },
            controller: {
                latest_local_scan_time: null as unknown as string,
                latest_remote_scan_time: null as unknown as string,
                latest_remote_scan_failed: null as unknown as boolean,
                latest_remote_scan_error: null as unknown as string
            }
        };
        serverStatusService.notifyEvent("status", JSON.stringify(statusJson));

        let count = 0;
        let latestStatus: ServerStatus = null!;
        serverStatusService.status.subscribe({
            next: status => {
                count++;
                latestStatus = status;
            }
        });

        tick();
        expect(count).toBe(1);

        // Error
        serverStatusService.notifyDisconnected();
        tick();
        expect(count).toBe(2);
        expect(latestStatus.server.up).toBe(false);
    }));

    it("should not crash on malformed JSON in status event", fakeAsync(() => {
        let count = 0;
        let latestStatus: ServerStatus = null!;
        serverStatusService.status.subscribe({
            next: status => {
                count++;
                latestStatus = status;
            }
        });
        tick();
        expect(count).toBe(1);
        const initialStatus = latestStatus;

        // Malformed JSON should not throw
        expect(() => {
            serverStatusService.notifyEvent("status", "not valid json {{{");
            tick();
        }).not.toThrow();

        // Status should be unchanged
        expect(count).toBe(1);
        expect(latestStatus).toBe(initialStatus);

        // Subsequent valid events should still work
        const validStatusJson: ServerStatusJson = {
            server: {
                up: true,
                error_msg: null as unknown as string
            },
            controller: {
                latest_local_scan_time: null as unknown as string,
                latest_remote_scan_time: null as unknown as string,
                latest_remote_scan_failed: null as unknown as boolean,
                latest_remote_scan_error: null as unknown as string
            }
        };
        serverStatusService.notifyEvent("status", JSON.stringify(validStatusJson));
        tick();
        expect(count).toBe(2);
        expect(latestStatus.server.up).toBe(true);
    }));

});
