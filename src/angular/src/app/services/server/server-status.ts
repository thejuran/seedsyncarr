import {Record} from "immutable";

/**
 * ServerStatus immutable
 */
interface IServerStatus {
    server: {
        up: boolean;
        errorMessage: string;
    };

    controller: {
        latestLocalScanTime: Date | null;
        latestRemoteScanTime: Date | null;
        latestRemoteScanFailed: boolean;
        latestRemoteScanError: string;
    };

    storage: {
        localTotal: number | null;
        localUsed: number | null;
        remoteTotal: number | null;
        remoteUsed: number | null;
    };
}
const DefaultServerStatus: IServerStatus = {
    server: {
        up: false,
        errorMessage: ""
    },
    controller: {
        latestLocalScanTime: null,
        latestRemoteScanTime: null,
        latestRemoteScanFailed: false,
        latestRemoteScanError: ""
    },
    storage: {
        localTotal: null,
        localUsed: null,
        remoteTotal: null,
        remoteUsed: null
    }
};
const ServerStatusRecord = Record(DefaultServerStatus);
export class ServerStatus extends ServerStatusRecord implements IServerStatus {
    server!: {
        up: boolean;
        errorMessage: string;
    };

    controller!: {
        latestLocalScanTime: Date | null;
        latestRemoteScanTime: Date | null;
        latestRemoteScanFailed: boolean;
        latestRemoteScanError: string;
    };

    storage!: {
        localTotal: number | null;
        localUsed: number | null;
        remoteTotal: number | null;
        remoteUsed: number | null;
    };

    constructor(props: Partial<IServerStatus>) {
        super(props);
    }
}


export namespace ServerStatus {
    export function fromJson(json: ServerStatusJson): ServerStatus {
        let latestLocalScanTime: Date | null = null;
        if (json.controller.latest_local_scan_time != null) {
            // str -> number, then sec -> ms
            latestLocalScanTime = new Date(1000 * +json.controller.latest_local_scan_time);
        }

        let latestRemoteScanTime: Date | null = null;
        if (json.controller.latest_remote_scan_time != null) {
            // str -> number, then sec -> ms
            latestRemoteScanTime = new Date(1000 * +json.controller.latest_remote_scan_time);
        }

        return new ServerStatus({
            server: {
                up: json.server.up,
                errorMessage: json.server.error_msg
            },
            controller: {
                latestLocalScanTime: latestLocalScanTime,
                latestRemoteScanTime: latestRemoteScanTime,
                latestRemoteScanFailed: json.controller.latest_remote_scan_failed,
                latestRemoteScanError: json.controller.latest_remote_scan_error
            },
            storage: {
                localTotal: json.storage?.local_total ?? null,
                localUsed: json.storage?.local_used ?? null,
                remoteTotal: json.storage?.remote_total ?? null,
                remoteUsed: json.storage?.remote_used ?? null
            }
        });
    }
}

/**
 * ServerStatus as serialized by the backend.
 * Note: naming convention matches that used in JSON
 */
export interface ServerStatusJson {
    server: {
        up: boolean;
        error_msg: string;
    };

    controller: {
        latest_local_scan_time: string;
        latest_remote_scan_time: string;
        latest_remote_scan_failed: boolean;
        latest_remote_scan_error: string;
    };

    storage?: {
        local_total: number | null;
        local_used: number | null;
        remote_total: number | null;
        remote_used: number | null;
    };
}
