import {Injectable, OnDestroy} from "@angular/core";
import {Observable, ReplaySubject, Subject} from "rxjs";

import {BaseStreamService} from "../base/base-stream.service";
import {LogRecord} from "./log-record";
import {LoggerService} from "../utils/logger.service";


// Maximum number of log records to buffer in the ReplaySubject
// This prevents unbounded memory growth for long-running sessions
const MAX_LOG_BUFFER_SIZE = 5000;


@Injectable()
export class LogService extends BaseStreamService implements OnDestroy {
    private destroy$ = new Subject<void>();

    // Buffer up to MAX_LOG_BUFFER_SIZE logs for replay when component re-subscribes
    private _logs: ReplaySubject<LogRecord> = new ReplaySubject(MAX_LOG_BUFFER_SIZE);

    // Track if we've ever received logs (persists across component navigation)
    private _hasReceivedLogs = false;

    private _logger: LoggerService;

    constructor(logger: LoggerService) {
        super();
        this._logger = logger;
        this.registerEventName("log-record");
    }

    /**
     * Whether any logs have been received since the app started.
     * This persists across component navigation.
     */
    get hasReceivedLogs(): boolean {
        return this._hasReceivedLogs;
    }

    /**
     * Logs is a hot observable with replay buffer
     * @returns {Observable<LogRecord>}
     */
    get logs(): Observable<LogRecord> {
        return this._logs.asObservable();
    }

    protected onEvent(eventName: string, data: string): void {
        try {
            this._hasReceivedLogs = true;
            this._logs.next(LogRecord.fromJson(JSON.parse(data)));
        } catch (error) {
            this._logger.error("Failed to parse log event:", error);
        }
    }

    protected onConnected(): void {
        // nothing to do
    }

    protected onDisconnected(): void {
        // nothing to do
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }
}
