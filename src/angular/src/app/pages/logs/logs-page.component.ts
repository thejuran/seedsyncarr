import {
    AfterContentChecked, AfterViewInit,
    ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, HostListener,
    OnDestroy, OnInit, TemplateRef, ViewChild, ViewContainerRef
} from "@angular/core";
import { DatePipe, AsyncPipe } from "@angular/common";

import {LogService} from "../../services/logs/log.service";
import {LogRecord} from "../../services/logs/log-record";
import {StreamServiceRegistry} from "../../services/base/stream-service.registry";
import {ConnectedService} from "../../services/utils/connected.service";
import {Localization} from "../../common/localization";
import {DomService} from "../../services/utils/dom.service";
import {Observable, Subject} from "rxjs";
import {takeUntil} from "rxjs/operators";

@Component({
    selector: "app-logs-page",
    templateUrl: "./logs-page.component.html",
    styleUrls: ["./logs-page.component.scss"],
    providers: [],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
    imports: [DatePipe, AsyncPipe]
})
export class LogsPageComponent implements OnInit, AfterViewInit, AfterContentChecked, OnDestroy {
    public readonly LogRecord = LogRecord;
    public readonly Localization = Localization;

    public headerHeight: Observable<number>;

    @ViewChild("templateRecord", {static: false}) templateRecord!: TemplateRef<unknown>;

    // Where to insert the cloned content
    @ViewChild("container", {static: false, read: ViewContainerRef}) container!: ViewContainerRef;

    @ViewChild("logHead", {static: false}) logHead!: ElementRef;
    @ViewChild("logTail", {static: false}) logTail!: ElementRef;

    public showScrollToTopButton = false;
    public showScrollToBottomButton = false;

    // Connection and log state
    public isConnected = false;

    private _logService: LogService;
    private _connectedService: ConnectedService;
    private _viewInitialized = false;
    private _destroy$ = new Subject<void>();

    constructor(private _elementRef: ElementRef,
                private _changeDetector: ChangeDetectorRef,
                private _streamRegistry: StreamServiceRegistry,
                private _domService: DomService) {
        this._logService = _streamRegistry.logService;
        this._connectedService = _streamRegistry.connectedService;
        this.headerHeight = this._domService.headerHeight;
    }

    /**
     * Check if we've received any logs (tracked in LogService to persist across navigation)
     */
    get hasReceivedLogs(): boolean {
        return this._logService.hasReceivedLogs;
    }

    ngOnInit(): void {
        // Subscribe to connection status (doesn't need ViewChild elements)
        this._connectedService.connected
            .pipe(takeUntil(this._destroy$))
            .subscribe({
                next: connected => {
                    this.isConnected = connected;
                    this._changeDetector.detectChanges();
                }
            });
    }

    ngAfterViewInit(): void {
        this._viewInitialized = true;

        // Subscribe to logs after view is initialized so ViewChild elements are available
        this._logService.logs
            .pipe(takeUntil(this._destroy$))
            .subscribe({
                next: record => {
                    this.insertRecord(record);
                }
            });
    }

    ngOnDestroy(): void {
        this._destroy$.next();
        this._destroy$.complete();
    }

    ngAfterContentChecked(): void {
        // Refresh button state when tabs is switched away and back
        // Only run after view is initialized (ViewChild elements are available)
        if (this._viewInitialized) {
            this.refreshScrollButtonVisibility();
        }
    }

    scrollToTop(): void {
        window.scrollTo(0, 0);
    }

    scrollToBottom(): void {
        window.scrollTo(0, document.body.scrollHeight);
    }

    @HostListener("window:scroll")
    checkScroll(): void {
        this.refreshScrollButtonVisibility();
    }

    private insertRecord(record: LogRecord): void {
        // Guard against ViewChild elements not being available
        if (!this.container || !this.templateRecord || !this.logTail) {
            return;
        }

        // Scroll down if the log is visible and already scrolled to the bottom
        const scrollToBottom = this._elementRef.nativeElement.offsetParent != null &&
            LogsPageComponent.isElementInViewport(this.logTail.nativeElement);
        this.container.createEmbeddedView(this.templateRecord, {record: record});
        this._changeDetector.detectChanges();

        if (scrollToBottom) {
            this.scrollToBottom();
        }
        this.refreshScrollButtonVisibility();
    }

    private refreshScrollButtonVisibility(): void {
        // Guard against ViewChild elements not being available
        if (!this.logHead || !this.logTail) {
            return;
        }

        // Show/hide the scroll buttons
        this.showScrollToTopButton = !LogsPageComponent.isElementInViewport(
            this.logHead.nativeElement
        );
        this.showScrollToBottomButton = !LogsPageComponent.isElementInViewport(
            this.logTail.nativeElement
        );
    }

    // Source: https://stackoverflow.com/a/7557433
    private static isElementInViewport(el: HTMLElement): boolean {
        const rect = el.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && /* or $(window).height() */
            rect.right <= (window.innerWidth || document.documentElement.clientWidth) /* or $(window).width() */
        );
    }
}
