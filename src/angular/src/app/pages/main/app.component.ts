import {AfterViewInit, Component, ElementRef, HostListener, OnInit, OnDestroy, ViewChild} from "@angular/core";
import {AsyncPipe} from "@angular/common";
import {NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet} from "@angular/router";

import {Observable, Subject} from "rxjs";
import {takeUntil} from "rxjs/operators";
import {ROUTE_INFOS} from "../../routes";

declare function require(moduleName: string): { version: string };
const { version: appVersion } = require("../../../../package.json");

import * as Immutable from "immutable";
import {DomService} from "../../services/utils/dom.service";
import {ToastService, Toast} from "../../services/utils/toast.service";
import {StreamServiceRegistry} from "../../services/base/stream-service.registry";
import {Notification} from "../../services/utils/notification";
import {NotificationService} from "../../services/utils/notification.service";
import {HeaderComponent} from "./header.component";

@Component({
    selector: "app-root",
    templateUrl: "./app.component.html",
    styleUrls: ["./app.component.scss"],
    standalone: true,
    imports: [RouterOutlet, RouterLink, RouterLinkActive, HeaderComponent, AsyncPipe]
})
export class AppComponent implements OnInit, AfterViewInit, OnDestroy {
    @ViewChild("topHeader", {static: false}) topHeader!: ElementRef;

    routeInfos = ROUTE_INFOS;
    version: string = appVersion;
    toasts: Toast[] = [];
    connected$!: Observable<boolean>;
    notifications$!: Observable<Immutable.List<Notification>>;
    bellOpen = false;

    private destroy$ = new Subject<void>();
    private _resizeObserver!: ResizeObserver;

    constructor(private router: Router,
                private _domService: DomService,
                private _toastService: ToastService,
                private _streamServiceRegistry: StreamServiceRegistry,
                private _notificationService: NotificationService) {
        this.connected$ = this._streamServiceRegistry.connectedService.connected;
        this.notifications$ = this._notificationService.notifications;
    }

    ngOnInit(): void {
        // Scroll to top on route changes
        this.router.events.pipe(takeUntil(this.destroy$)).subscribe((evt) => {
            if (!(evt instanceof NavigationEnd)) {
                return;
            }
            window.scrollTo(0, 0);
        });

        // Subscribe to toast notifications
        this._toastService.toasts$.pipe(takeUntil(this.destroy$)).subscribe(toast => {
            this.toasts.push(toast);
            if (toast.autohide) {
                setTimeout(() => {
                    const index = this.toasts.findIndex(t => t.id === toast.id);
                    if (index >= 0) {
                        this.toasts.splice(index, 1);
                    }
                }, toast.delay);
            }
        });
    }

    ngAfterViewInit(): void {
        this._resizeObserver = new ResizeObserver(() => {
            this._domService.setHeaderHeight(this.topHeader.nativeElement.clientHeight);
        });
        this._resizeObserver.observe(this.topHeader.nativeElement);
    }

    ngOnDestroy(): void {
        this._resizeObserver?.disconnect();
        this.destroy$.next();
        this.destroy$.complete();
    }

    dismissToast(toast: Toast): void {
        const index = this.toasts.findIndex(t => t.id === toast.id);
        if (index >= 0) {
            this.toasts.splice(index, 1);
        }
    }

    toggleBell(event: Event): void {
        event.stopPropagation();
        this.bellOpen = !this.bellOpen;
    }

    @HostListener('document:click')
    closeBell(): void {
        this.bellOpen = false;
    }

    dismissNotification(notif: Notification): void {
        this._notificationService.hide(notif);
    }

    title = "app";
}
