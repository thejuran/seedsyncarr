import {AfterViewInit, Component, ElementRef, OnInit, OnDestroy, ViewChild} from "@angular/core";
import {AsyncPipe, NgClass} from "@angular/common";
import {NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet} from "@angular/router";

import {Observable, Subject} from "rxjs";
import {takeUntil} from "rxjs/operators";
import {ROUTE_INFOS} from "../../routes";

import {APP_VERSION} from "../../common/version";

import {DomService} from "../../services/utils/dom.service";
import {ToastService, Toast} from "../../services/utils/toast.service";
import {StreamServiceRegistry} from "../../services/base/stream-service.registry";
import {HeaderComponent} from "./header.component";
import {NotificationBellComponent} from "./notification-bell.component";

@Component({
    selector: "app-root",
    templateUrl: "./app.component.html",
    styleUrls: ["./app.component.scss"],
    standalone: true,
    imports: [RouterOutlet, RouterLink, RouterLinkActive, HeaderComponent, AsyncPipe, NgClass, NotificationBellComponent]
})
export class AppComponent implements OnInit, AfterViewInit, OnDestroy {
    @ViewChild("topHeader", {static: false}) topHeader!: ElementRef;

    routeInfos = ROUTE_INFOS;
    readonly version: string = APP_VERSION;
    toasts: Toast[] = [];
    connected$: Observable<boolean>;

    private destroy$ = new Subject<void>();
    private _resizeObserver!: ResizeObserver;
    private _toastTimerMap = new Map<number, ReturnType<typeof setTimeout>>();

    constructor(private router: Router,
                private _domService: DomService,
                private _toastService: ToastService,
                private _streamServiceRegistry: StreamServiceRegistry) {
        this.connected$ = this._streamServiceRegistry.connectedService.connected;
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
                const handle = setTimeout(() => {
                    const toastIdx = this.toasts.findIndex(t => t.id === toast.id);
                    if (toastIdx >= 0) { this.toasts.splice(toastIdx, 1); }
                    this._toastTimerMap.delete(toast.id);
                }, toast.delay);
                this._toastTimerMap.set(toast.id, handle);
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
        this._toastTimerMap.forEach(timer => clearTimeout(timer));
        this._resizeObserver?.disconnect();
        this.destroy$.next();
        this.destroy$.complete();
    }

    dismissToast(toast: Toast): void {
        const timer = this._toastTimerMap.get(toast.id);
        if (timer) {
            clearTimeout(timer);
            this._toastTimerMap.delete(toast.id);
        }
        const index = this.toasts.findIndex(t => t.id === toast.id);
        if (index >= 0) {
            this.toasts.splice(index, 1);
        }
    }

    private static readonly NAV_ICONS: Record<string, string> = {
        dashboard: "fa-th-large",
        settings: "fa-cog",
        logs: "fa-terminal",
        about: "fa-info-circle"
    };

    navIcon(path: string): string {
        return AppComponent.NAV_ICONS[path] ?? "fa-circle";
    }

    title = "app";
}
