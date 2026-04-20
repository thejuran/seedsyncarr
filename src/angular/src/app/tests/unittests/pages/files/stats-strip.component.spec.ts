import {ComponentFixture, fakeAsync, TestBed, tick} from "@angular/core/testing";
import {BehaviorSubject, Observable} from "rxjs";

import {StatsStripComponent} from "../../../../pages/files/stats-strip.component";
import {DashboardStats, DashboardStatsService} from "../../../../services/files/dashboard-stats.service";

// Inline copy of the real template for test rendering (avoids html/scss loader issues in karma)
const STATS_STRIP_TEMPLATE = `
@if (stats$ | async; as stats) {
<div class="stats-strip">
  <div class="stat-card">
    <div class="stat-watermark"><i class="fa fa-cloud"></i></div>
    <div class="stat-header">
      <i class="fa fa-cloud stat-icon stat-icon--amber"></i>
      <span class="stat-label">Remote Storage</span>
    </div>
    @if (stats.remoteCapacityTotal !== null && stats.remoteCapacityUsed !== null && stats.remoteCapacityTotal > 0) {
      <div class="stat-value-row">
        <span class="stat-value">{{ (stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) | number:'1.0-0' }}%</span>
        <span class="stat-unit">of {{ stats.remoteCapacityTotal | fileSize:2 }}</span>
      </div>
      <div class="stat-progress-wrap">
        <div class="stat-progress-track">
          <div class="stat-progress-fill"
               [class.stat-progress-fill--amber]="(stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) < 80"
               [class.stat-progress-fill--warning]="(stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) >= 80 && (stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) < 95"
               [class.stat-progress-fill--danger]="(stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) >= 95"
               [style.width.%]="stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100">
          </div>
        </div>
      </div>
      <div class="stat-sub">{{ stats.remoteCapacityUsed | fileSize:2 }} used</div>
    } @else {
      <div class="stat-value-row">
        <span class="stat-value">{{ stats.remoteTrackedBytes | fileSize:2:'value' }}</span>
        <span class="stat-unit">{{ stats.remoteTrackedBytes | fileSize:2:'unit' }} Tracked</span>
      </div>
      <div class="stat-progress-wrap">
        <div class="stat-progress-track">
          <div class="stat-progress-fill stat-progress-fill--amber"
               [style.width.%]="stats.totalTrackedBytes > 0 ? (stats.remoteTrackedBytes / stats.totalTrackedBytes * 100) : 0">
          </div>
        </div>
      </div>
    }
  </div>
  <div class="stat-card">
    <div class="stat-watermark"><i class="fa fa-database"></i></div>
    <div class="stat-header">
      <i class="fa fa-database stat-icon stat-icon--amber"></i>
      <span class="stat-label">Local Storage</span>
    </div>
    @if (stats.localCapacityTotal !== null && stats.localCapacityUsed !== null && stats.localCapacityTotal > 0) {
      <div class="stat-value-row">
        <span class="stat-value">{{ (stats.localCapacityUsed / stats.localCapacityTotal * 100) | number:'1.0-0' }}%</span>
        <span class="stat-unit">of {{ stats.localCapacityTotal | fileSize:2 }}</span>
      </div>
      <div class="stat-progress-wrap">
        <div class="stat-progress-track">
          <div class="stat-progress-fill"
               [class.stat-progress-fill--secondary]="(stats.localCapacityUsed / stats.localCapacityTotal * 100) < 80"
               [class.stat-progress-fill--warning]="(stats.localCapacityUsed / stats.localCapacityTotal * 100) >= 80 && (stats.localCapacityUsed / stats.localCapacityTotal * 100) < 95"
               [class.stat-progress-fill--danger]="(stats.localCapacityUsed / stats.localCapacityTotal * 100) >= 95"
               [style.width.%]="stats.localCapacityUsed / stats.localCapacityTotal * 100">
          </div>
        </div>
      </div>
      <div class="stat-sub">{{ stats.localCapacityUsed | fileSize:2 }} used</div>
    } @else {
      <div class="stat-value-row">
        <span class="stat-value">{{ stats.localTrackedBytes | fileSize:2:'value' }}</span>
        <span class="stat-unit">{{ stats.localTrackedBytes | fileSize:2:'unit' }} Tracked</span>
      </div>
      <div class="stat-progress-wrap">
        <div class="stat-progress-track">
          <div class="stat-progress-fill stat-progress-fill--secondary"
               [style.width.%]="stats.totalTrackedBytes > 0 ? (stats.localTrackedBytes / stats.totalTrackedBytes * 100) : 0">
          </div>
        </div>
      </div>
    }
  </div>
  <div class="stat-card">
    <div class="stat-watermark"><i class="fa fa-arrow-down"></i></div>
    <div class="stat-header">
      <i class="fa fa-arrow-down stat-icon stat-icon--success"></i>
      <span class="stat-label">Download Speed</span>
    </div>
    <div class="stat-value-row">
      <span class="stat-value">{{ stats.totalSpeedBps | fileSize:1:'value' }}</span>
      <span class="stat-unit">{{ stats.totalSpeedBps | fileSize:1:'unit' }}/s</span>
    </div>
    <div class="stat-sub">Peak: {{ stats.peakSpeedBps | fileSize:1 }}/s</div>
  </div>
  <div class="stat-card">
    <div class="stat-watermark"><i class="fa fa-tasks"></i></div>
    <div class="stat-header">
      <i class="fa fa-tasks stat-icon stat-icon--secondary"></i>
      <span class="stat-label">Active Tasks</span>
    </div>
    <div class="stat-value-row">
      <span class="stat-value">{{ stats.downloadingCount + stats.queuedCount }}</span>
      <span class="stat-unit">Running</span>
    </div>
    <div class="stat-badges">
      <span class="badge badge-dl">{{ stats.downloadingCount }} DL</span>
      <span class="badge badge-queued">{{ stats.queuedCount }} Queued</span>
    </div>
  </div>
</div>
}
`;


function makeStats(overrides: Partial<DashboardStats> = {}): DashboardStats {
    return {
        downloadingCount: 0,
        queuedCount: 0,
        totalSpeedBps: 0,
        peakSpeedBps: 0,
        remoteTrackedBytes: 0,
        localTrackedBytes: 0,
        totalTrackedBytes: 0,
        remoteCapacityTotal: null,
        remoteCapacityUsed: null,
        localCapacityTotal: null,
        localCapacityUsed: null,
        ...overrides,
    };
}


class MockDashboardStatsService {
    private _stats$ = new BehaviorSubject<DashboardStats>(makeStats());

    get stats$(): Observable<DashboardStats> {
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
        // Scope to .stat-icon to skip the .stat-watermark icon (also has fa-cloud)
        const icon = el.querySelector(".stat-icon.fa-cloud");
        expect(icon).toBeTruthy();
        const label = icon!.closest(".stat-header")!.querySelector(".stat-label");
        expect(label!.textContent).toContain("Remote Storage");
    });

    it("should render Local Storage card with database icon", () => {
        const el: HTMLElement = fixture.nativeElement;
        const icon = el.querySelector(".stat-icon.fa-database");
        expect(icon).toBeTruthy();
        const label = icon!.closest(".stat-header")!.querySelector(".stat-label");
        expect(label!.textContent).toContain("Local Storage");
    });

    it("should render Download Speed card with arrow-down icon", () => {
        const el: HTMLElement = fixture.nativeElement;
        const icon = el.querySelector(".stat-icon.fa-arrow-down");
        expect(icon).toBeTruthy();
        const label = icon!.closest(".stat-header")!.querySelector(".stat-label");
        expect(label!.textContent).toContain("Download Speed");
    });

    it("should render Active Tasks card with tasks icon", () => {
        const el: HTMLElement = fixture.nativeElement;
        const icon = el.querySelector(".stat-icon.fa-tasks");
        expect(icon).toBeTruthy();
        const label = icon!.closest(".stat-header")!.querySelector(".stat-label");
        expect(label!.textContent).toContain("Active Tasks");
    });

    it("should render two progress fill bars for storage cards in fallback mode", () => {
        const bars = fixture.nativeElement.querySelectorAll(".stat-progress-fill");
        expect(bars.length).toBe(2);
    });

    it("should display DL and Queued badges in Active Tasks card", fakeAsync(() => {
        mockStatsService.pushStats(makeStats({
            downloadingCount: 3,
            queuedCount: 5,
        }));
        fixture.detectChanges();
        tick();

        const badges = fixture.nativeElement.querySelectorAll(".stat-badges .badge");
        expect(badges.length).toBe(2);
        expect(badges[0].textContent).toContain("3 DL");
        expect(badges[1].textContent).toContain("5 Queued");
    }));

    it("should display peak speed in Download Speed card", fakeAsync(() => {
        mockStatsService.pushStats(makeStats({
            downloadingCount: 1,
            totalSpeedBps: 1000,
            peakSpeedBps: 5000,
        }));
        fixture.detectChanges();
        tick();

        const el: HTMLElement = fixture.nativeElement;
        // Scope to .stat-icon to skip the .stat-watermark icon
        const speedCard = el.querySelector(".stat-icon.fa-arrow-down")!.closest(".stat-card")!;
        const sub = speedCard.querySelector(".stat-sub");
        expect(sub!.textContent).toContain("Peak");
    }));

    // ========================================================================
    // Phase 74-04: capacity-mode rendering, fallback, thresholds, independence
    // ========================================================================

    it("should render both tiles in fallback mode when capacity is null", () => {
        mockStatsService.pushStats(makeStats({
            remoteTrackedBytes: 1000,
            localTrackedBytes: 500,
            totalTrackedBytes: 1500,
        }));
        fixture.detectChanges();

        const text = (fixture.nativeElement as HTMLElement).textContent || "";
        expect(text).toContain("Tracked");
        expect(text).not.toContain("%");
        expect(text).not.toContain("used");
    });

    it("should render Remote tile in capacity mode when remoteCapacity fields are populated", () => {
        mockStatsService.pushStats(makeStats({
            remoteCapacityTotal: 1000,
            remoteCapacityUsed: 500,
        }));
        fixture.detectChanges();

        const cards = fixture.nativeElement.querySelectorAll(".stat-card");
        const remoteCard = cards[0] as HTMLElement;
        const remoteText = remoteCard.textContent || "";

        expect(remoteText).toContain("50%");
        expect(remoteText).toContain("of ");
        expect(remoteText).toContain("used");
    });

    it("should render Local tile fallback while Remote shows capacity (per-tile independence, D-15)", () => {
        mockStatsService.pushStats(makeStats({
            remoteCapacityTotal: 1000,
            remoteCapacityUsed: 500,
            remoteTrackedBytes: 999,
            localTrackedBytes: 200,
            totalTrackedBytes: 1199,
        }));
        fixture.detectChanges();

        const cards = fixture.nativeElement.querySelectorAll(".stat-card");
        const remoteCard = cards[0] as HTMLElement;
        const localCard = cards[1] as HTMLElement;

        expect((remoteCard.textContent || "")).toContain("50%");
        expect((localCard.textContent || "")).toContain("Tracked");
        expect((localCard.textContent || "")).not.toContain("%");
    });

    it("should render Remote fallback while Local shows capacity (per-tile independence, D-15)", () => {
        mockStatsService.pushStats(makeStats({
            localCapacityTotal: 1000,
            localCapacityUsed: 500,
            remoteTrackedBytes: 100,
            localTrackedBytes: 200,
            totalTrackedBytes: 300,
        }));
        fixture.detectChanges();

        const cards = fixture.nativeElement.querySelectorAll(".stat-card");
        const remoteCard = cards[0] as HTMLElement;
        const localCard = cards[1] as HTMLElement;

        expect((remoteCard.textContent || "")).toContain("Tracked");
        expect((localCard.textContent || "")).toContain("50%");
    });

    it("should render integer percentage (D-05): 65.3% -> '65%'", () => {
        mockStatsService.pushStats(makeStats({
            remoteCapacityTotal: 1000,
            remoteCapacityUsed: 653,
        }));
        fixture.detectChanges();

        const remoteCard = fixture.nativeElement.querySelectorAll(".stat-card")[0] as HTMLElement;
        const remoteText = remoteCard.textContent || "";
        expect(remoteText).toContain("65%");
        expect(remoteText).not.toContain("65.3%");
        expect(remoteText).not.toContain("65.0%");
    });

    it("should use amber fill at 79% (below warning threshold, D-09)", () => {
        mockStatsService.pushStats(makeStats({
            remoteCapacityTotal: 100,
            remoteCapacityUsed: 79,
        }));
        fixture.detectChanges();

        const fill = fixture.nativeElement.querySelectorAll(".stat-card")[0]
            .querySelector(".stat-progress-fill") as HTMLElement;
        expect(fill.classList.contains("stat-progress-fill--amber")).toBe(true);
        expect(fill.classList.contains("stat-progress-fill--warning")).toBe(false);
        expect(fill.classList.contains("stat-progress-fill--danger")).toBe(false);
    });

    it("should use warning fill at 80% boundary (D-09)", () => {
        mockStatsService.pushStats(makeStats({
            remoteCapacityTotal: 100,
            remoteCapacityUsed: 80,
        }));
        fixture.detectChanges();

        const fill = fixture.nativeElement.querySelectorAll(".stat-card")[0]
            .querySelector(".stat-progress-fill") as HTMLElement;
        expect(fill.classList.contains("stat-progress-fill--warning")).toBe(true);
        expect(fill.classList.contains("stat-progress-fill--amber")).toBe(false);
        expect(fill.classList.contains("stat-progress-fill--danger")).toBe(false);
    });

    it("should use warning fill at 94% (top of warning band, D-09)", () => {
        mockStatsService.pushStats(makeStats({
            remoteCapacityTotal: 100,
            remoteCapacityUsed: 94,
        }));
        fixture.detectChanges();

        const fill = fixture.nativeElement.querySelectorAll(".stat-card")[0]
            .querySelector(".stat-progress-fill") as HTMLElement;
        expect(fill.classList.contains("stat-progress-fill--warning")).toBe(true);
        expect(fill.classList.contains("stat-progress-fill--danger")).toBe(false);
    });

    it("should use danger fill at 95% boundary (D-09)", () => {
        mockStatsService.pushStats(makeStats({
            remoteCapacityTotal: 100,
            remoteCapacityUsed: 95,
        }));
        fixture.detectChanges();

        const fill = fixture.nativeElement.querySelectorAll(".stat-card")[0]
            .querySelector(".stat-progress-fill") as HTMLElement;
        expect(fill.classList.contains("stat-progress-fill--danger")).toBe(true);
        expect(fill.classList.contains("stat-progress-fill--warning")).toBe(false);
        expect(fill.classList.contains("stat-progress-fill--amber")).toBe(false);
    });

    it("should use secondary fill for Local tile in capacity mode below warning threshold", () => {
        mockStatsService.pushStats(makeStats({
            localCapacityTotal: 100,
            localCapacityUsed: 50,
        }));
        fixture.detectChanges();

        const fill = fixture.nativeElement.querySelectorAll(".stat-card")[1]
            .querySelector(".stat-progress-fill") as HTMLElement;
        expect(fill.classList.contains("stat-progress-fill--secondary")).toBe(true);
        expect(fill.classList.contains("stat-progress-fill--warning")).toBe(false);
    });

    it("should apply danger uniformly to Local tile capacity mode (D-10 color-family-agnostic)", () => {
        mockStatsService.pushStats(makeStats({
            localCapacityTotal: 100,
            localCapacityUsed: 97,
        }));
        fixture.detectChanges();

        const fill = fixture.nativeElement.querySelectorAll(".stat-card")[1]
            .querySelector(".stat-progress-fill") as HTMLElement;
        expect(fill.classList.contains("stat-progress-fill--danger")).toBe(true);
        expect(fill.classList.contains("stat-progress-fill--secondary")).toBe(false);
    });

    it("should set progress-fill width to used/total * 100", () => {
        mockStatsService.pushStats(makeStats({
            remoteCapacityTotal: 1000,
            remoteCapacityUsed: 750,
        }));
        fixture.detectChanges();

        const fill = fixture.nativeElement.querySelectorAll(".stat-card")[0]
            .querySelector(".stat-progress-fill") as HTMLElement;
        expect(fill.style.width).toBe("75%");
    });
});
