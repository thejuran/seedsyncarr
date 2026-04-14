import {ComponentFixture, fakeAsync, TestBed, tick} from "@angular/core/testing";
import {BehaviorSubject} from "rxjs";

import {StatsStripComponent} from "../../../../pages/files/stats-strip.component";
import {DashboardStats, DashboardStatsService} from "../../../../services/files/dashboard-stats.service";

// Inline copy of the real template for test rendering (avoids html/scss loader issues in karma)
const STATS_STRIP_TEMPLATE = `
@if (stats$ | async; as stats) {
<div class="stats-strip row g-3 mb-4">
  <div class="col-12 col-sm-6 col-lg-3">
    <div class="stat-card">
      <div class="stat-header">
        <i class="fa fa-cloud stat-icon"></i>
        <span class="stat-label">Remote Storage</span>
      </div>
      <div class="stat-value">{{ stats.remoteTrackedBytes }}</div>
      <div class="stat-sub">tracked usage</div>
      <div class="progress stat-progress mt-2" style="height: 4px;">
        <div class="progress-bar bg-warning" role="progressbar"
             [style.width.%]="stats.totalTrackedBytes > 0 ? (stats.remoteTrackedBytes / stats.totalTrackedBytes * 100) : 0"></div>
      </div>
    </div>
  </div>
  <div class="col-12 col-sm-6 col-lg-3">
    <div class="stat-card">
      <div class="stat-header">
        <i class="fa fa-database stat-icon"></i>
        <span class="stat-label">Local Storage</span>
      </div>
      <div class="stat-value">{{ stats.localTrackedBytes }}</div>
      <div class="stat-sub">tracked usage</div>
      <div class="progress stat-progress mt-2" style="height: 4px;">
        <div class="progress-bar bg-info" role="progressbar"
             [style.width.%]="stats.totalTrackedBytes > 0 ? (stats.localTrackedBytes / stats.totalTrackedBytes * 100) : 0"></div>
      </div>
    </div>
  </div>
  <div class="col-12 col-sm-6 col-lg-3">
    <div class="stat-card">
      <div class="stat-header">
        <i class="fa fa-arrow-down stat-icon"></i>
        <span class="stat-label">Download Speed</span>
      </div>
      <div class="stat-value">{{ stats.totalSpeedBps }}/s</div>
      <div class="stat-sub">peak: {{ stats.peakSpeedBps }}/s</div>
    </div>
  </div>
  <div class="col-12 col-sm-6 col-lg-3">
    <div class="stat-card">
      <div class="stat-header">
        <i class="fa fa-tasks stat-icon"></i>
        <span class="stat-label">Active Tasks</span>
      </div>
      <div class="stat-value">{{ stats.downloadingCount + stats.queuedCount }}</div>
      <div class="stat-badges">
        <span class="badge bg-warning text-dark">{{ stats.downloadingCount }} DL</span>
        <span class="badge bg-secondary">{{ stats.queuedCount }} Queued</span>
      </div>
    </div>
  </div>
</div>
}
`;


class MockDashboardStatsService {
    private _stats$ = new BehaviorSubject<DashboardStats>({
        downloadingCount: 0,
        queuedCount: 0,
        totalSpeedBps: 0,
        peakSpeedBps: 0,
        remoteTrackedBytes: 0,
        localTrackedBytes: 0,
        totalTrackedBytes: 0,
    });

    get stats$() {
        return this._stats$.asObservable();
    }

    pushStats(stats: DashboardStats): void {
        this._stats$.next(stats);
    }
}


describe("StatsStripComponent", () => {
    let component: StatsStripComponent;
    let fixture: ComponentFixture<StatsStripComponent>;
    let mockStatsService: MockDashboardStatsService;

    beforeEach(async () => {
        mockStatsService = new MockDashboardStatsService();

        await TestBed.configureTestingModule({
            imports: [StatsStripComponent],
            providers: [
                {provide: DashboardStatsService, useValue: mockStatsService}
            ]
        })
        .overrideTemplate(StatsStripComponent, STATS_STRIP_TEMPLATE)
        .compileComponents();

        fixture = TestBed.createComponent(StatsStripComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("should create", () => {
        expect(component).toBeDefined();
    });

    it("should render 4 stat cards", () => {
        const cards = fixture.nativeElement.querySelectorAll(".stat-card");
        expect(cards.length).toBe(4);
    });

    it("should render Remote Storage card with cloud icon", () => {
        const el: HTMLElement = fixture.nativeElement;
        const icon = el.querySelector(".fa-cloud");
        expect(icon).toBeTruthy();
        const label = icon!.closest(".stat-header")!.querySelector(".stat-label");
        expect(label!.textContent).toContain("Remote Storage");
    });

    it("should render Local Storage card with database icon", () => {
        const el: HTMLElement = fixture.nativeElement;
        const icon = el.querySelector(".fa-database");
        expect(icon).toBeTruthy();
        const label = icon!.closest(".stat-header")!.querySelector(".stat-label");
        expect(label!.textContent).toContain("Local Storage");
    });

    it("should render Download Speed card with arrow-down icon", () => {
        const el: HTMLElement = fixture.nativeElement;
        const icon = el.querySelector(".fa-arrow-down");
        expect(icon).toBeTruthy();
        const label = icon!.closest(".stat-header")!.querySelector(".stat-label");
        expect(label!.textContent).toContain("Download Speed");
    });

    it("should render Active Tasks card with tasks icon", () => {
        const el: HTMLElement = fixture.nativeElement;
        const icon = el.querySelector(".fa-tasks");
        expect(icon).toBeTruthy();
        const label = icon!.closest(".stat-header")!.querySelector(".stat-label");
        expect(label!.textContent).toContain("Active Tasks");
    });

    it("should render two progress bars for storage cards", () => {
        const bars = fixture.nativeElement.querySelectorAll(".progress-bar");
        expect(bars.length).toBe(2);
    });

    it("should display DL and Queued badges in Active Tasks card", fakeAsync(() => {
        mockStatsService.pushStats({
            downloadingCount: 3,
            queuedCount: 5,
            totalSpeedBps: 0,
            peakSpeedBps: 0,
            remoteTrackedBytes: 0,
            localTrackedBytes: 0,
            totalTrackedBytes: 0,
        });
        fixture.detectChanges();
        tick();

        const badges = fixture.nativeElement.querySelectorAll(".stat-badges .badge");
        expect(badges.length).toBe(2);
        expect(badges[0].textContent).toContain("3 DL");
        expect(badges[1].textContent).toContain("5 Queued");
    }));

    it("should display peak speed in Download Speed card", fakeAsync(() => {
        mockStatsService.pushStats({
            downloadingCount: 1,
            queuedCount: 0,
            totalSpeedBps: 1000,
            peakSpeedBps: 5000,
            remoteTrackedBytes: 0,
            localTrackedBytes: 0,
            totalTrackedBytes: 0,
        });
        fixture.detectChanges();
        tick();

        const el: HTMLElement = fixture.nativeElement;
        const speedCard = el.querySelector(".fa-arrow-down")!.closest(".stat-card")!;
        const sub = speedCard.querySelector(".stat-sub");
        expect(sub!.textContent).toContain("peak");
    }));
});
