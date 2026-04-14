import {ComponentFixture, TestBed} from "@angular/core/testing";
import {RouterModule} from "@angular/router";
import {BehaviorSubject} from "rxjs";

import {AppComponent} from "../../../../pages/main/app.component";
import {DomService} from "../../../../services/utils/dom.service";
import {ToastService} from "../../../../services/utils/toast.service";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";
import {ConnectedService} from "../../../../services/utils/connected.service";
import {NotificationService} from "../../../../services/utils/notification.service";


describe("AppComponent", () => {
    let component: AppComponent;
    let fixture: ComponentFixture<AppComponent>;
    let connectedSubject: BehaviorSubject<boolean>;
    let mockStreamServiceRegistry: jasmine.SpyObj<StreamServiceRegistry>;
    let mockConnectedService: jasmine.SpyObj<ConnectedService>;
    let mockNotificationService: jasmine.SpyObj<NotificationService>;
    let mockDomService: jasmine.SpyObj<DomService>;

    beforeEach(async () => {
        connectedSubject = new BehaviorSubject<boolean>(false);

        mockConnectedService = jasmine.createSpyObj("ConnectedService", [], {
            connected: connectedSubject.asObservable()
        });

        mockStreamServiceRegistry = jasmine.createSpyObj("StreamServiceRegistry", [], {
            connectedService: mockConnectedService
        });

        mockNotificationService = jasmine.createSpyObj("NotificationService", ["show", "hide"], {
            notifications: new BehaviorSubject([]).asObservable()
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
                  @let connected = connected$ | async;
                  <div class="connection-badge"
                       [class.connected]="connected"
                       [class.disconnected]="!connected">
                    <span class="status-dot"></span>
                    <span class="status-text">{{ connected ? 'Connection Stable' : 'Disconnected' }}</span>
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

        it("should show 'Connection Stable' when server is connected", () => {
            connectedSubject.next(true);
            fixture.detectChanges();

            const badge = fixture.nativeElement.querySelector(".connection-badge");
            expect(badge).toBeTruthy();
            expect(badge.classList.contains("connected")).toBeTrue();
            expect(badge.classList.contains("disconnected")).toBeFalse();

            const statusText = fixture.nativeElement.querySelector(".status-text");
            expect(statusText.textContent.trim()).toBe("Connection Stable");
        });

        it("should render status dot element", () => {
            const dot = fixture.nativeElement.querySelector(".status-dot");
            expect(dot).toBeTruthy();
        });
    });
});
