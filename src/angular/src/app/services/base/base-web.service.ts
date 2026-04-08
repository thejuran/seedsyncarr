import {Injectable, OnDestroy} from "@angular/core";
import {Subject} from "rxjs";
import {takeUntil} from "rxjs/operators";

import {StreamServiceRegistry} from "./stream-service.registry";
import {ConnectedService} from "../utils/connected.service";


/**
 * BaseWebService provides utility to be notified when connection to
 * the backend server is lost and regained. Non-streaming web services
 * can use these notifications to re-issue get requests.
 */
@Injectable()
export abstract class BaseWebService implements OnDestroy {
    /**
     * Subject for cleanup - child classes can use this with takeUntil() for their subscriptions
     */
    protected destroy$ = new Subject<void>();
    private _connectedService: ConnectedService;

    /**
     * Call this method to finish initialization
     */
    public onInit(): void {
        this._connectedService.connected.pipe(
            takeUntil(this.destroy$)
        ).subscribe({
            next: connected => {
                if(connected) {
                    this.onConnected();
                } else {
                    this.onDisconnected();
                }
            }
        });
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    constructor(_streamServiceProvider: StreamServiceRegistry) {
        this._connectedService = _streamServiceProvider.connectedService;
    }


    /**
     * Callback for connected
     */
    protected abstract onConnected(): void;

    /**
     * Callback for disconnected
     */
    protected abstract onDisconnected(): void;
}
