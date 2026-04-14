import {ChangeDetectorRef} from "@angular/core";
import {ComponentFixture, TestBed} from "@angular/core/testing";
import {BehaviorSubject} from "rxjs";

import * as Immutable from "immutable";

import {NotificationBellComponent} from "../../../../pages/main/notification-bell.component";
import {NotificationService} from "../../../../services/utils/notification.service";
import {Notification} from "../../../../services/utils/notification";


describe("NotificationBellComponent", () => {
    let component: NotificationBellComponent;
    let fixture: ComponentFixture<NotificationBellComponent>;
    let notificationsSubject: BehaviorSubject<Immutable.List<Notification>>;
    let mockNotificationService: jasmine.SpyObj<NotificationService>;

    beforeEach(async () => {
        notificationsSubject = new BehaviorSubject<Immutable.List<Notification>>(Immutable.List([]));

        mockNotificationService = jasmine.createSpyObj("NotificationService", ["show", "hide"], {
            notifications: notificationsSubject.asObservable()
        });

        await TestBed.configureTestingModule({
            imports: [NotificationBellComponent],
            providers: [
                {provide: NotificationService, useValue: mockNotificationService}
            ]
        })
        .overrideTemplate(NotificationBellComponent, `
            @let notifs = notifications$ | async;
            <div class="bell-wrapper">
              <button class="bell-btn" aria-label="Notifications" (click)="toggleBell()">
                <i class="fa fa-bell"></i>
                @if (notifs?.size > 0) {
                  <span class="bell-badge-dot"></span>
                }
              </button>
              @if (bellOpen) {
                <div class="bell-dropdown">
                  <div class="bell-dropdown-header">
                    <span class="bell-dropdown-title">Notifications</span>
                  </div>
                  <div class="bell-dropdown-body">
                    @if (notifs?.size === 0) {
                      <div class="bell-empty">No notifications</div>
                    } @else {
                      @for (notif of notifs; track $index) {
                        <div class="bell-notif" [attr.data-level]="notif.level">
                          <span class="bell-notif-text">{{ notif.text }}</span>
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
        `)
        .compileComponents();

        fixture = TestBed.createComponent(NotificationBellComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
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
            component.toggleBell();
            expect(component.bellOpen).toBeTrue();

            component.toggleBell();
            expect(component.bellOpen).toBeFalse();
        });

        it("should show dropdown when bell is open", () => {
            component.toggleBell();
            expect(component.bellOpen).toBeTrue();

            // markForCheck + detectChanges via ChangeDetectorRef avoids NG0100
            // when nested @if conditionals are first created inside a newly
            // stamped @if (bellOpen) block
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

        it("should close bell on outside document click via closeBell", () => {
            component.bellOpen = true;

            // Simulate a click outside the component
            const outsideEvent = new MouseEvent("click");
            Object.defineProperty(outsideEvent, "target", {value: document.body});
            component.closeBell(outsideEvent);

            expect(component.bellOpen).toBeFalse();
        });

        it("should not close bell when click is inside the component", () => {
            component.bellOpen = true;

            // Simulate a click inside the component
            const insideEvent = new MouseEvent("click");
            Object.defineProperty(insideEvent, "target", {value: fixture.nativeElement});
            component.closeBell(insideEvent);

            expect(component.bellOpen).toBeTrue();
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
            component.toggleBell();
            fixture.detectChanges();

            const notifText = fixture.nativeElement.querySelector(".bell-notif-text");
            expect(notifText).toBeTruthy();
            expect(notifText.textContent).toContain("Server is down");
        });

        it("should show empty message when no notifications and bell is open", () => {
            notificationsSubject.next(Immutable.List([]));
            component.toggleBell();
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
            component.toggleBell();
            fixture.detectChanges();

            const dismissBtns = fixture.nativeElement.querySelectorAll(".bell-notif-dismiss");
            expect(dismissBtns.length).toBe(1);
        });
    });
});
