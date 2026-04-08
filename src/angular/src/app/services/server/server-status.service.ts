import {Injectable, OnDestroy} from "@angular/core";
import {Observable, BehaviorSubject, Subject} from "rxjs";

import {Localization} from "../../common/localization";
import {ServerStatus, ServerStatusJson} from "./server-status";
import {BaseStreamService} from "../base/base-stream.service";
import {LoggerService} from "../utils/logger.service";


@Injectable()
export class ServerStatusService extends BaseStreamService implements OnDestroy {
    private destroy$ = new Subject<void>();

    private _status: BehaviorSubject<ServerStatus> =
        new BehaviorSubject(new ServerStatus({
            server: {
                up: false,
                errorMessage: Localization.Notification.STATUS_CONNECTION_WAITING
            }
        }));

    constructor(private _logger: LoggerService) {
        super();
        this.registerEventName("status");
    }

    get status(): Observable<ServerStatus> {
        return this._status.asObservable();
    }

    protected onEvent(eventName: string, data: string): void {
        this.parseStatus(data);
    }

    protected onConnected(): void {
        // nothing to do
    }

    protected onDisconnected(): void {
        // Notify the clients
        this._status.next(new ServerStatus({
            server: {
                up: false,
                errorMessage: Localization.Error.SERVER_DISCONNECTED
            }
        }));
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    /**
     * Parse an event and notify subscribers
     * @param {string} data
     */
    private parseStatus(data: string): void {
        try {
            const statusJson: ServerStatusJson = JSON.parse(data);
            const status = ServerStatus.fromJson(statusJson);
            this._status.next(status);
        } catch (error) {
            this._logger.error("Failed to parse status event:", error);
        }
    }
}
