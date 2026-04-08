import {Injectable, OnDestroy} from "@angular/core";
import {Observable, BehaviorSubject, Subject} from "rxjs";

import {BaseStreamService} from "../base/base-stream.service";


/**
 * ConnectedService exposes the connection status to clients
 * as an Observable
 */
@Injectable()
export class ConnectedService extends BaseStreamService implements OnDestroy {
    private destroy$ = new Subject<void>();

    // For clients
    private _connectedSubject: BehaviorSubject<boolean> = new BehaviorSubject(false);

    constructor() {
        super();
        // No events to register
    }

    get connected(): Observable<boolean> {
        return this._connectedSubject.asObservable();
    }

    protected onEvent(_eventName: string, _data: string): void {
        // Nothing to do
    }

    protected onConnected(): void {
        if(this._connectedSubject.getValue() === false) {
            this._connectedSubject.next(true);
        }
    }

    protected onDisconnected(): void {
        if(this._connectedSubject.getValue() === true) {
            this._connectedSubject.next(false);
        }
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }
}
