import * as Immutable from "immutable";

import {ServerStatus, ServerStatusJson} from "../../../../services/server/server-status";


describe("Testing log record initialization", () => {
    let baseJson: ServerStatusJson;
    let baseStatus: ServerStatus;

    beforeEach(() => {
        baseJson = {
            server: {
                up: true,
                error_msg: "An error message"
            },
            controller: {
                latest_local_scan_time: "1514776875.9439101",
                latest_remote_scan_time: "1524743857.3456243",
                latest_remote_scan_failed: true,
                latest_remote_scan_error: "message failure reason"
            },
            storage: {
                local_total: 500_000_000_000,
                local_used: 100_000_000_000,
                remote_total: 2_000_000_000_000,
                remote_used: 1_300_000_000_000
            }
        };
        baseStatus = ServerStatus.fromJson(baseJson);
    });

    it("should be immutable", () => {
        expect(baseStatus instanceof Immutable.Record).toBe(true);
    });

    it("should correctly initialize server up", () => {
        expect(baseStatus.server.up).toBe(true);
    });

    it("should correctly initialize server error message", () => {
        expect(baseStatus.server.errorMessage).toBe("An error message");
    });

    it("should correctly initialize controller latest local scan time", () => {
        expect(baseStatus.controller.latestLocalScanTime).toEqual(new Date(1514776875943));
        // Allow null
        baseJson.controller.latest_local_scan_time = null as unknown as string;
        const newStatus = ServerStatus.fromJson(baseJson);
        expect(newStatus.controller.latestLocalScanTime).toBeNull();
    });

    it("should correctly initialize controller latest remote scan time", () => {
        expect(baseStatus.controller.latestRemoteScanTime).toEqual(new Date(1524743857345));
        // Allow null
        baseJson.controller.latest_remote_scan_time = null as unknown as string;
        const newStatus = ServerStatus.fromJson(baseJson);
        expect(newStatus.controller.latestRemoteScanTime).toBeNull();
    });

    it("should correctly initialize controller failure", () => {
        expect(baseStatus.controller.latestRemoteScanFailed).toBe(true);
    });

    it("should correctly initialize controller error", () => {
        expect(baseStatus.controller.latestRemoteScanError).toBe("message failure reason");
    });

    it("should correctly initialize storage localTotal", () => {
        expect(baseStatus.storage.localTotal).toBe(500_000_000_000);
        baseJson.storage!.local_total = null;
        const newStatus = ServerStatus.fromJson(baseJson);
        expect(newStatus.storage.localTotal).toBeNull();
    });

    it("should correctly initialize storage localUsed", () => {
        expect(baseStatus.storage.localUsed).toBe(100_000_000_000);
        baseJson.storage!.local_used = null;
        const newStatus = ServerStatus.fromJson(baseJson);
        expect(newStatus.storage.localUsed).toBeNull();
    });

    it("should correctly initialize storage remoteTotal", () => {
        expect(baseStatus.storage.remoteTotal).toBe(2_000_000_000_000);
        baseJson.storage!.remote_total = null;
        const newStatus = ServerStatus.fromJson(baseJson);
        expect(newStatus.storage.remoteTotal).toBeNull();
    });

    it("should correctly initialize storage remoteUsed", () => {
        expect(baseStatus.storage.remoteUsed).toBe(1_300_000_000_000);
        baseJson.storage!.remote_used = null;
        const newStatus = ServerStatus.fromJson(baseJson);
        expect(newStatus.storage.remoteUsed).toBeNull();
    });

    it("should default storage to all-null when backend omits the key (deploy-skew)", () => {
        const legacyJson: ServerStatusJson = {
            server: {up: true, error_msg: ""},
            controller: {
                latest_local_scan_time: "1514776875.9439101",
                latest_remote_scan_time: "1524743857.3456243",
                latest_remote_scan_failed: false,
                latest_remote_scan_error: ""
            }
            // storage key intentionally omitted
        };
        const status = ServerStatus.fromJson(legacyJson);
        expect(status.storage.localTotal).toBeNull();
        expect(status.storage.localUsed).toBeNull();
        expect(status.storage.remoteTotal).toBeNull();
        expect(status.storage.remoteUsed).toBeNull();
    });

    it("should default storage to all-null in the Default record (cold-load per D-14)", () => {
        const empty = new ServerStatus({});
        expect(empty.storage.localTotal).toBeNull();
        expect(empty.storage.localUsed).toBeNull();
        expect(empty.storage.remoteTotal).toBeNull();
        expect(empty.storage.remoteUsed).toBeNull();
    });
});
