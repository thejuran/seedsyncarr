import {ChangeDetectorRef} from "@angular/core";
import {ComponentFixture, TestBed} from "@angular/core/testing";
import {RouterModule} from "@angular/router";
import {BehaviorSubject} from "rxjs";

import * as Immutable from "immutable";

import {AppComponent} from "../../../../pages/main/app.component";
import {DomService} from "../../../../services/utils/dom.service";
import {ToastService} from "../../../../services/utils/toast.service";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";
import {ConnectedService} from "../../../../services/utils/connected.service";
import {NotificationService} from "../../../../services/utils/notification.service";
import {Notification} from "../../../../services/utils/notification";


describe("AppComponent", () => {
    let component: AppComponent;
    let fixture: ComponentFixture<AppComponent>;
    let connectedSubject: BehaviorSubject<boolean>;
    let notificationsSubject: BehaviorSubject<Immutable.List<Notification>>;
    let mockStreamServiceRegistry: jasmine.SpyObj<StreamServiceRegistry>;
    let mockConnectedService: jasmine.SpyObj<ConnectedService>;
    let mockNotificationService: jasmine.SpyObj<NotificationService>;
    let mockDomService: jasmine.SpyObj<DomService>;

    beforeEach(async () => {
        connectedSubject = new BehaviorSubject<boolean>(false);
        notificationsSubject = new BehaviorSubject<Immutable.List<Notification>>(Immutable.List([]));

        mockConnectedService = jasmine.createSpyObj("ConnectedService", [], {
            connected: connectedSubject.asObservable()
        });

        mockStreamServiceRegistry = jasmine.createSpyObj("StreamServiceRegistry", [], {
            connectedService: mockConnectedService
        });

        mockNotificationService = jasmine.createSpyObj("NotificationService", ["show", "hide"], {
            notifications: notificationsSubject.asObservable()
        });

        mockDomService = jasmine.createSpyObj("DomService", ["setHeaderHeight"]);

        await TestBed.configureTestingModule({
            imports: [
                AppComponent,
                RouterModule.forRoot([])
            ],
            providers: [
                {provide: StreamServiceRegistry, useValue: mockStreamServiceRegistry},
                {provide: NotificationService, useValue: mockNotificationService},
                {provide: DomService, useValue: mockDomService},
                ToastService
            ]
        })
        .overrideTemplate(AppComponent, `
            <div id="top-nav">
              <div class="nav-inner">
                <div class="nav-brand">
                  <span class="brand-text">SeedSync<span class="brand-arr">arr</span></span>
                </div>
                <div class="nav-links"></div>
                <div class="nav-right">
                  <div class="connection-badge"
                       [class.connected]="connected$ | async"
                       [class.disconnected]="!(connected$ | async)">
                    <span class="status-dot"></span>
                    <span class="status-text">{{ (connected$ | async) ? 'Connected' : 'Disconnected' }}</span>
                  </div>
                  <div class="bell-wrapper" (click)="toggleBell($event)">
                    <button class="bell-btn" aria-label="Notifications">
                      <i class="fa fa-bell"></i>
                      @if ((notifications$ | async)?.size > 0) {
                        <span class="bell-badge-dot"></span>
                      }
                    </button>
                    @if (bellOpen) {
                      <div class="bell-dropdown" (click)="$event.stopPropagation()">
                        <div class="bell-dropdown-header">
                          <span class="bell-dropdown-title">Notifications</span>
                        </div>
                        <div class="bell-dropdown-body">
                          @if ((notifications$ | async)?.size === 0) {
                            <div class="bell-empty">No notifications</div>
                          } @else {
                            @for (notif of notifications$ | async; track notif.timestamp) {
                              <div class="bell-notif" [attr.data-level]="notif.level">
                                <span class="bell-notif-text" [innerHTML]="notif.text"></span>
                                @if (notif.dismissible) {
                                  <button class="bell-notif-dismiss" (click)="dismissNotification(notif)">
                                    <i class="fa fa-times"></i>
                                  </button>
                                }
                              </div>
                            }
                          }
                        </div>
                      </div>
                    }
                  </div>
                </div>
              </div>
            </div>
            <div id="top-content">
              <div id="top-header"><div #topHeader></div></div>
              <router-outlet></router-outlet>
            </div>
        `)
        .compileComponents();

        fixture = TestBed.createComponent(AppComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    // =========================================================================
    // NAV-03: Connection Status Badge
    // =========================================================================

    describe("NAV-03: Connection status badge", () => {
        it("should expose connected$ observable from StreamServiceRegistry", () => {
            expect(component.connected$).toBeDefined();
        });

        it("should show 'Disconnected' when server is not connected", () => {
            connectedSubject.next(false);
            fixture.detectChanges();

            const badge = fixture.nativeElement.querySelector(".connection-badge");
            expect(badge).toBeTruthy();
            expect(badge.classList.contains("disconnected")).toBeTrue();
            expect(badge.classList.contains("connected")).toBeFalse();

            const statusText = fixture.nativeElement.querySelector(".status-text");
            expect(statusText.textContent.trim()).toBe("Disconnected");
        });

        it("should show 'Connected' when server is connected", () => {
            connectedSubject.next(true);
            fixture.detectChanges();

            const badge = fixture.nativeElement.querySelector(".connection-badge");
            expect(badge).toBeTruthy();
            expect(badge.classList.contains("connected")).toBeTrue();
            expect(badge.classList.contains("disconnected")).toBeFalse();

            const statusText = fixture.nativeElement.querySelector(".status-text");
            expect(statusText.textContent.trim()).toBe("Connected");
        });

        it("should render status dot element", () => {
            const dot = fixture.nativeElement.querySelector(".status-dot");
            expect(dot).toBeTruthy();
        });
    });

    // =========================================================================
    // NAV-04: Notification Bell
    // =========================================================================

    describe("NAV-04: Notification bell", () => {
        it("should expose notifications$ observable from NotificationService", () => {
            expect(component.notifications$).toBeDefined();
        });

        it("should start with bell closed", () => {
            expect(component.bellOpen).toBeFalse();
        });

        it("should not show badge dot when no notifications", () => {
            notificationsSubject.next(Immutable.List([]));
            fixture.detectChanges();

            const badgeDot = fixture.nativeElement.querySelector(".bell-badge-dot");
            expect(badgeDot).toBeFalsy();
        });

        it("should show badge dot when notifications are present", () => {
            const notif = new Notification({
                level: Notification.Level.DANGER,
                text: "Server error",
                dismissible: true
            });
            notificationsSubject.next(Immutable.List([notif]));
            fixture.detectChanges();

            const badgeDot = fixture.nativeElement.querySelector(".bell-badge-dot");
            expect(badgeDot).toBeTruthy();
        });

        it("should toggle bell open state on toggleBell", () => {
            const event = new Event("click");
            spyOn(event, "stopPropagation");

            component.toggleBell(event);
            expect(component.bellOpen).toBeTrue();
            expect(event.stopPropagation).toHaveBeenCalled();

            component.toggleBell(event);
            expect(component.bellOpen).toBeFalse();
        });

        it("should show dropdown when bell is open", () => {
            // Verify toggleBell sets the state correctly
            component.toggleBell(new Event("click"));
            expect(component.bellOpen).toBeTrue();

            // Use markForCheck + detectChanges to properly settle the @if conditional
            // and the async pipes created inside the newly rendered view
            const cdr = fixture.componentRef.injector.get(ChangeDetectorRef);
            cdr.markForCheck();
            cdr.detectChanges();

            const dropdown = fixture.nativeElement.querySelector(".bell-dropdown");
            expect(dropdown).toBeTruthy();
        });

        it("should hide dropdown when bell is closed", () => {
            component.bellOpen = false;
            fixture.detectChanges();

            const dropdown = fixture.nativeElement.querySelector(".bell-dropdown");
            expect(dropdown).toBeFalsy();
        });

        it("should close bell on document click via closeBell", () => {
            component.bellOpen = true;
            component.closeBell();
            expect(component.bellOpen).toBeFalse();
        });

        it("should call NotificationService.hide when dismissing notification", () => {
            const notif = new Notification({
                level: Notification.Level.WARNING,
                text: "Test warning",
                dismissible: true
            });

            component.dismissNotification(notif);
            expect(mockNotificationService.hide).toHaveBeenCalledWith(notif);
        });

        it("should show notification text in dropdown", () => {
            const notif = new Notification({
                level: Notification.Level.DANGER,
                text: "Server is down",
                dismissible: true
            });
            notificationsSubject.next(Immutable.List([notif]));
            component.toggleBell(new Event("click"));
            fixture.detectChanges();

            const notifText = fixture.nativeElement.querySelector(".bell-notif-text");
            expect(notifText).toBeTruthy();
            expect(notifText.textContent).toContain("Server is down");
        });

        it("should show empty message when no notifications and bell is open", () => {
            notificationsSubject.next(Immutable.List([]));
            component.toggleBell(new Event("click"));
            fixture.detectChanges();

            const emptyMsg = fixture.nativeElement.querySelector(".bell-empty");
            expect(emptyMsg).toBeTruthy();
            expect(emptyMsg.textContent).toContain("No notifications");
        });

        it("should show dismiss button only for dismissible notifications", () => {
            const notifDismissible = new Notification({
                level: Notification.Level.WARNING,
                text: "Can dismiss",
                dismissible: true
            });
            const notifFixed = new Notification({
                level: Notification.Level.DANGER,
                text: "Cannot dismiss",
                dismissible: false
            });
            notificationsSubject.next(Immutable.List([notifDismissible, notifFixed]));
            component.toggleBell(new Event("click"));
            fixture.detectChanges();

            const dismissBtns = fixture.nativeElement.querySelectorAll(".bell-notif-dismiss");
            expect(dismissBtns.length).toBe(1);
        });
    });
});
