import {Injectable} from "@angular/core";
import {Subject, Observable} from "rxjs";

export interface Toast {
    id: number;
    message: string;
    type: "success" | "info" | "warning" | "danger";
    autohide: boolean;
    delay: number;  // milliseconds
}

/**
 * ToastService manages ephemeral toast notifications.
 * Toasts are emitted via a Subject and consumed by the app component's
 * toast container. Unlike NotificationService (persistent alerts in header),
 * toasts are transient and auto-dismiss.
 */
@Injectable({providedIn: "root"})
export class ToastService {
    private _toasts$ = new Subject<Toast>();
    private _nextId = 0;

    get toasts$(): Observable<Toast> {
        return this._toasts$.asObservable();
    }

    show(toast: Partial<Toast> & {message: string}): void {
        const id = this._nextId++;
        this._toasts$.next({
            ...toast,
            id,
            type: toast.type ?? "info",
            autohide: toast.autohide ?? true,
            delay: toast.delay ?? 5000,
        });
    }

    success(message: string): void {
        this.show({message, type: "success"});
    }

    info(message: string): void {
        this.show({message, type: "info"});
    }

    warning(message: string): void {
        this.show({message, type: "warning"});
    }

    danger(message: string): void {
        this.show({message, type: "danger"});
    }
}
