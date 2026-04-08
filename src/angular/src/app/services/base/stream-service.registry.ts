import {Injectable, NgZone, OnDestroy} from "@angular/core";
import {Observable} from "rxjs";

import {ModelFileService} from "../files/model-file.service";
import {ServerStatusService} from "../server/server-status.service";
import {LoggerService} from "../utils/logger.service";
import {ConnectedService} from "../utils/connected.service";
import {LogService} from "../logs/log.service";


export class EventSourceFactory {
    static createEventSource(url: string): EventSource {
        return new EventSource(url);
    }
}


export interface IStreamService {
    /**
     * Returns the event names supported by this stream service
     * @returns {string[]}
     */
    getEventNames(): string[];

    /**
     * Notifies the stream service that it is now connected
     */
    notifyConnected(): void;

    /**
     * Notifies the stream service that it is now disconnected
     */
    notifyDisconnected(): void;

    /**
     * Notifies the stream service of an event
     * @param {string} eventName
     * @param {string} data
     */
    notifyEvent(eventName: string, data: string): void;
}


/**
 * StreamDispatchService is the top-level service that connects to
 * the multiplexed SSE stream. It listens for SSE events and dispatches
 * them to whichever IStreamService that requested them.
 *
 * Includes idle connection detection: if no events (including heartbeat pings)
 * are received within the timeout period, the connection is proactively
 * closed and reconnected. This handles cases where the connection becomes
 * stale (e.g., proxy/firewall closes it) without triggering an error event.
 */
@Injectable()
export class StreamDispatchService implements OnDestroy {
    private readonly STREAM_URL = "/server/stream";

    private readonly STREAM_RETRY_INTERVAL_MS = 3000;

    // Heartbeat event name - sent by server every 15 seconds
    private readonly HEARTBEAT_EVENT = "ping";

    // Connection timeout: if no events received within this period, reconnect.
    // Set to 30 seconds (2x the server's 15-second heartbeat interval) to allow
    // for some network jitter while still detecting stale connections promptly.
    private readonly CONNECTION_TIMEOUT_MS = 30000;

    // How often to check for connection timeout
    private readonly TIMEOUT_CHECK_INTERVAL_MS = 5000;

    private _eventNameToServiceMap: Map<string, IStreamService> = new Map();
    private _services: IStreamService[] = [];

    // Track last event time for idle detection
    private _lastEventTime = 0;
    private _timeoutCheckInterval: ReturnType<typeof setInterval> | null = null;
    private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private _currentEventSource: EventSource | null = null;
    private _currentSubscription: { unsubscribe(): void } | null = null;

    constructor(private _logger: LoggerService,
                private _zone: NgZone) {
    }

    /**
     * Call this method to finish initialization
     */
    public onInit(): void {
        this.createSseObserver();
        this.startTimeoutChecker();
    }

    ngOnDestroy(): void {
        if (this._timeoutCheckInterval) {
            clearInterval(this._timeoutCheckInterval);
            this._timeoutCheckInterval = null;
        }
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
        if (this._currentEventSource) {
            this._currentEventSource.close();
            this._currentEventSource = null;
        }
    }

    /**
     * Start periodic timeout checking
     */
    private startTimeoutChecker(): void {
        if (this._timeoutCheckInterval) {
            clearInterval(this._timeoutCheckInterval);
        }

        this._timeoutCheckInterval = setInterval(() => {
            this.checkConnectionTimeout();
        }, this.TIMEOUT_CHECK_INTERVAL_MS);
    }

    /**
     * Check if the connection has timed out due to inactivity
     */
    private checkConnectionTimeout(): void {
        if (this._lastEventTime === 0) {
            // No events received yet, connection is still initializing
            return;
        }

        const elapsed = Date.now() - this._lastEventTime;
        if (elapsed > this.CONNECTION_TIMEOUT_MS) {
            this._logger.warn(
                `No events received for ${elapsed}ms, reconnecting due to idle timeout`
            );
            this.reconnectDueToTimeout();
        }
    }

    /**
     * Proactively close and reconnect when idle timeout is detected
     */
    private reconnectDueToTimeout(): void {
        // Close the current EventSource if it exists
        if (this._currentEventSource) {
            this._currentEventSource.close();
            this._currentEventSource = null;
        }

        // Reset last event time to prevent immediate re-trigger
        this._lastEventTime = 0;

        // Notify all services of disconnection
        for (const service of this._services) {
            this._zone.run(() => {
                service.notifyDisconnected();
            });
        }

        // Reconnect after a short delay
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
        }
        this._reconnectTimer = setTimeout(() => { this.createSseObserver(); }, this.STREAM_RETRY_INTERVAL_MS);
    }

    /**
     * Register an IStreamService with the dispatch
     * @param {IStreamService} service
     * @returns {IStreamService}
     */
    public registerService(service: IStreamService): IStreamService {
        for(const eventName of service.getEventNames()) {
            this._eventNameToServiceMap.set(eventName, service);
        }
        this._services.push(service);
        return service;
    }

    private createSseObserver(): void {
        // Tear down previous subscription to prevent stale event delivery
        this._currentSubscription?.unsubscribe();
        this._currentSubscription = null;

        const observable = new Observable<{ event: string; data: string }>(observer => {
            const eventSource = EventSourceFactory.createEventSource(this.STREAM_URL);

            // Store reference for proactive close on timeout
            this._currentEventSource = eventSource;

            // Listen for registered service events
            for (const eventName of Array.from(this._eventNameToServiceMap.keys())) {
                eventSource.addEventListener(eventName, event => {
                    // Update last event time for timeout detection
                    this._lastEventTime = Date.now();
                    observer.next({
                        "event": eventName,
                        "data": (<MessageEvent>event).data
                    });
                });
            }

            // Listen for heartbeat ping events (not dispatched to services, just for keepalive)
            eventSource.addEventListener(this.HEARTBEAT_EVENT, () => {
                this._lastEventTime = Date.now();
                // Heartbeat events are not dispatched to services - they're only
                // used to keep the connection alive and detect timeouts
            });

            eventSource.onopen = (_event): void => {
                this._logger.info("Connected to server stream");

                // Initialize last event time on connection
                this._lastEventTime = Date.now();

                // Notify all services of connection
                for (const service of this._services) {
                    this._zone.run(() => {
                        service.notifyConnected();
                    });
                }
            };

            eventSource.onerror = (x): void => observer.error(x);

            return (): void => {
                eventSource.close();
                this._currentEventSource = null;
            };
        });
        this._currentSubscription = observable.subscribe({
            next: (x: { event: string; data: string }) => {
                const eventName = x.event;
                const eventData = x.data;
                const service = this._eventNameToServiceMap.get(eventName);
                if (service) {
                    this._zone.run(() => {
                        service.notifyEvent(eventName, eventData);
                    });
                } else {
                    this._logger.warn("Received unknown SSE event:", eventName);
                }
            },
            error: err => {
                this._logger.error("Error in stream: %O", err);

                // Clear the EventSource reference
                this._currentEventSource = null;

                // Notify all services of disconnection
                for (const service of this._services) {
                    this._zone.run(() => {
                        service.notifyDisconnected();
                    });
                }

                if (this._reconnectTimer) {
                    clearTimeout(this._reconnectTimer);
                }
                this._reconnectTimer = setTimeout(() => { this.createSseObserver(); }, this.STREAM_RETRY_INTERVAL_MS);
            }
        });
    }
}


/**
 * StreamServiceRegistry is responsible for initializing all
 * Stream Services. All services created by the registry
 * will be connected to a single stream via the DispatchService
 */
@Injectable()
export class StreamServiceRegistry {

    constructor(private _dispatch: StreamDispatchService,
                private _modelFileService: ModelFileService,
                private _serverStatusService: ServerStatusService,
                private _connectedService: ConnectedService,
                private _logService: LogService) {
        // Register all services
        _dispatch.registerService(_connectedService);
        _dispatch.registerService(_serverStatusService);
        _dispatch.registerService(_modelFileService);
        _dispatch.registerService(_logService);
    }

    /**
     * Call this method to finish initialization
     */
    public onInit(): void {
        this._dispatch.onInit();
    }

    get modelFileService(): ModelFileService { return this._modelFileService; }
    get serverStatusService(): ServerStatusService { return this._serverStatusService; }
    get connectedService(): ConnectedService { return this._connectedService; }
    get logService(): LogService { return this._logService; }
}

/**
 * StreamServiceRegistry factory and provider
 */
export const streamServiceRegistryFactory = (
        _dispatch: StreamDispatchService,
        _modelFileService: ModelFileService,
        _serverStatusService: ServerStatusService,
        _connectedService: ConnectedService,
        _logService: LogService
): StreamServiceRegistry => {
    const streamServiceRegistry = new StreamServiceRegistry(
        _dispatch,
        _modelFileService,
        _serverStatusService,
        _connectedService,
        _logService
    );
    streamServiceRegistry.onInit();
    return streamServiceRegistry;
};

export const StreamServiceRegistryProvider = {
    provide: StreamServiceRegistry,
    useFactory: streamServiceRegistryFactory,
    deps: [
        StreamDispatchService,
        ModelFileService,
        ServerStatusService,
        ConnectedService,
        LogService
    ]
};
