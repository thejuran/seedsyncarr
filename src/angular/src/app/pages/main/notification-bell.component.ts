import {Component, ElementRef, HostListener} from "@angular/core";
import {AsyncPipe} from "@angular/common";
import {Observable} from "rxjs";

import * as Immutable from "immutable";
import {Notification} from "../../services/utils/notification";
import {NotificationService} from "../../services/utils/notification.service";

@Component({
    selector: "app-notification-bell",
    templateUrl: "./notification-bell.component.html",
    styleUrls: ["./notification-bell.component.scss"],
    standalone: true,
    imports: [AsyncPipe]
})
export class NotificationBellComponent {
    notifications$: Observable<Immutable.List<Notification>>;
    bellOpen = false;

    constructor(
        private _elRef: ElementRef,
        private _notificationService: NotificationService
    ) {
        this.notifications$ = this._notificationService.notifications;
    }

    toggleBell(): void {
        this.bellOpen = !this.bellOpen;
    }

    @HostListener("document:click", ["$event"])
    closeBell(event: Event): void {
        const target = event.target as Node | null;
        if (target && this._elRef.nativeElement.contains(target)) {
            return;
        }
        this.bellOpen = false;
    }

    dismissNotification(notif: Notification): void {
        this._notificationService.hide(notif);
    }
}
