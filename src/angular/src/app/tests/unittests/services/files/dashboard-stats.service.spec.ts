import {fakeAsync, TestBed, tick} from "@angular/core/testing";

import * as Immutable from "immutable";

import {DashboardStatsService, DashboardStats} from "../../../../services/files/dashboard-stats.service";
import {ViewFileService} from "../../../../services/files/view-file.service";
import {LoggerService} from "../../../../services/utils/logger.service";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";
import {MockStreamServiceRegistry} from "../../../mocks/mock-stream-service.registry";
import {ConnectedService} from "../../../../services/utils/connected.service";
import {MockModelFileService} from "../../../mocks/mock-model-file.service";
import {ModelFile} from "../../../../services/files/model-file";
import {FileSelectionService} from "../../../../services/files/file-selection.service";
import {BehaviorSubject} from "rxjs";
import {ServerStatusService} from "../../../../services/server/server-status.service";
import {ServerStatus} from "../../../../services/server/server-status";


class MockServerStatusService implements Pick<ServerStatusService, "status"> {
    _status$ = new BehaviorSubject<ServerStatus>(new ServerStatus({}));
    get status() {
        return this._status$.asObservable();
    }
    pushStatus(storage: {localTotal: number | null; localUsed: number | null; remoteTotal: number | null; remoteUsed: number | null}) {
        // Carry server/controller forward so a future DashboardStatsService dependency
        // on either block doesn't get silently reset to defaults by this test helper.
        const current = this._status$.getValue();
        this._status$.next(new ServerStatus({server: current.server, controller: current.controller, storage}));
    }
}


describe("Testing dashboard stats service", () => {
    let statsService: DashboardStatsService;
    let mockModelService: MockModelFileService;
    let mockServerStatus: MockServerStatusService;

    beforeEach(() => {
        mockServerStatus = new MockServerStatusService();
        TestBed.configureTestingModule({
            providers: [
                DashboardStatsService,
                ViewFileService,
                LoggerService,
                ConnectedService,
                FileSelectionService,
                {provide: ServerStatusService, useValue: mockServerStatus},
                {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
            ]
        });

        statsService = TestBed.inject(DashboardStatsService);
        const mockRegistry: MockStreamServiceRegistry = TestBed.inject(StreamServiceRegistry) as unknown as MockStreamServiceRegistry;
        mockModelService = mockRegistry.modelFileService;
    });

    it("should create an instance", () => {
        expect(statsService).toBeDefined();
    });

    it("should emit zero stats by default", fakeAsync(() => {
        let latestStats: DashboardStats | null = null;

        statsService.stats$.subscribe(stats => {
            latestStats = stats;
        });
        tick();

        expect(latestStats).toBeDefined();
        expect(latestStats!.downloadingCount).toBe(0);
        expect(latestStats!.queuedCount).toBe(0);
        expect(latestStats!.totalSpeedBps).toBe(0);
        expect(latestStats!.peakSpeedBps).toBe(0);
        expect(latestStats!.remoteTrackedBytes).toBe(0);
        expect(latestStats!.localTrackedBytes).toBe(0);
        expect(latestStats!.totalTrackedBytes).toBe(0);
        expect(latestStats!.remoteCapacityTotal).toBeNull();
        expect(latestStats!.remoteCapacityUsed).toBeNull();
        expect(latestStats!.localCapacityTotal).toBeNull();
        expect(latestStats!.localCapacityUsed).toBeNull();
    }));

    it("should count downloading files", fakeAsync(() => {
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 1000,
            local_size: 500,
            downloading_speed: 100
        }));
        model = model.set("b", new ModelFile({
            name: "b",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 2000,
            local_size: 1000,
            downloading_speed: 200
        }));
        mockModelService._files.next(model);
        tick();

        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => {
            latestStats = stats;
        });
        tick();

        expect(latestStats!.downloadingCount).toBe(2);
    }));

    it("should count queued files", fakeAsync(() => {
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.QUEUED,
            remote_size: 1000,
            local_size: 0
        }));
        model = model.set("b", new ModelFile({
            name: "b",
            state: ModelFile.State.QUEUED,
            remote_size: 2000,
            local_size: 0
        }));
        model = model.set("c", new ModelFile({
            name: "c",
            state: ModelFile.State.DOWNLOADED,
            remote_size: 3000,
            local_size: 3000
        }));
        mockModelService._files.next(model);
        tick();

        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => {
            latestStats = stats;
        });
        tick();

        expect(latestStats!.queuedCount).toBe(2);
        expect(latestStats!.downloadingCount).toBe(0);
    }));

    it("should compute total download speed from downloading files", fakeAsync(() => {
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 1000,
            local_size: 500,
            downloading_speed: 150
        }));
        model = model.set("b", new ModelFile({
            name: "b",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 2000,
            local_size: 1000,
            downloading_speed: 250
        }));
        mockModelService._files.next(model);
        tick();

        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => {
            latestStats = stats;
        });
        tick();

        expect(latestStats!.totalSpeedBps).toBe(400);
    }));

    it("should track peak speed across updates", fakeAsync(() => {
        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => {
            latestStats = stats;
        });
        tick();

        // First update: speed is 400
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 1000,
            local_size: 500,
            downloading_speed: 400
        }));
        mockModelService._files.next(model);
        tick();

        expect(latestStats!.totalSpeedBps).toBe(400);
        expect(latestStats!.peakSpeedBps).toBe(400);

        // Second update: speed drops to 100
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 1000,
            local_size: 600,
            downloading_speed: 100
        }));
        mockModelService._files.next(model);
        tick();

        expect(latestStats!.totalSpeedBps).toBe(100);
        expect(latestStats!.peakSpeedBps).toBe(400); // Peak should remain 400
    }));

    it("should compute remote and local tracked bytes from all files", fakeAsync(() => {
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADED,
            remote_size: 5000,
            local_size: 5000
        }));
        model = model.set("b", new ModelFile({
            name: "b",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 3000,
            local_size: 1000,
            downloading_speed: 100
        }));
        mockModelService._files.next(model);
        tick();

        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => {
            latestStats = stats;
        });
        tick();

        expect(latestStats!.remoteTrackedBytes).toBe(8000);
        expect(latestStats!.localTrackedBytes).toBe(6000);
        expect(latestStats!.totalTrackedBytes).toBe(14000);
    }));

    it("should reset peak speed when all downloads stop", fakeAsync(() => {
        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => {
            latestStats = stats;
        });
        tick();

        // First: active download at speed 500
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 1000,
            local_size: 500,
            downloading_speed: 500
        }));
        mockModelService._files.next(model);
        tick();

        expect(latestStats!.peakSpeedBps).toBe(500);

        // Second: download finishes — totalSpeed becomes 0
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADED,
            remote_size: 1000,
            local_size: 1000,
            downloading_speed: 0
        }));
        mockModelService._files.next(model);
        tick();

        expect(latestStats!.peakSpeedBps).toBe(0);
    }));

    it("should handle zero sizes gracefully", fakeAsync(() => {
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DEFAULT,
            remote_size: 0,
            local_size: 0
        }));
        mockModelService._files.next(model);
        tick();

        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => {
            latestStats = stats;
        });
        tick();

        expect(latestStats!.remoteTrackedBytes).toBe(0);
        expect(latestStats!.localTrackedBytes).toBe(0);
        expect(latestStats!.totalTrackedBytes).toBe(0);
    }));

    it("should surface capacity from status stream when backend emits values", fakeAsync(() => {
        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => { latestStats = stats; });
        tick();

        mockServerStatus.pushStatus({
            localTotal: 500_000_000_000,
            localUsed: 100_000_000_000,
            remoteTotal: 2_000_000_000_000,
            remoteUsed: 1_300_000_000_000,
        });
        tick();

        expect(latestStats!.remoteCapacityTotal).toBe(2_000_000_000_000);
        expect(latestStats!.remoteCapacityUsed).toBe(1_300_000_000_000);
        expect(latestStats!.localCapacityTotal).toBe(500_000_000_000);
        expect(latestStats!.localCapacityUsed).toBe(100_000_000_000);
    }));

    it("should keep per-tile capacity independent (remote null, local populated)", fakeAsync(() => {
        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => { latestStats = stats; });
        tick();

        mockServerStatus.pushStatus({
            localTotal: 500_000_000_000,
            localUsed: 100_000_000_000,
            remoteTotal: null,
            remoteUsed: null,
        });
        tick();

        expect(latestStats!.localCapacityTotal).toBe(500_000_000_000);
        expect(latestStats!.remoteCapacityTotal).toBeNull();
        expect(latestStats!.remoteCapacityUsed).toBeNull();
    }));

    it("should preserve capacity when file list re-emits (combineLatest retention)", fakeAsync(() => {
        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => { latestStats = stats; });
        tick();

        // First: status delivers capacity.
        mockServerStatus.pushStatus({
            localTotal: 500, localUsed: 100,
            remoteTotal: 2000, remoteUsed: 1300,
        });
        tick();

        // Then: a file-list update arrives (no status change).
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 100,
            local_size: 50,
            downloading_speed: 10,
        }));
        mockModelService._files.next(model);
        tick();

        // Capacity must be preserved from the prior status emission.
        expect(latestStats!.remoteCapacityTotal).toBe(2000);
        expect(latestStats!.localCapacityTotal).toBe(500);
        // And file-derived fields reflect the new file.
        expect(latestStats!.downloadingCount).toBe(1);
        expect(latestStats!.remoteTrackedBytes).toBe(100);
    }));

    it("should preserve file-derived counts when status re-emits (combineLatest retention)", fakeAsync(() => {
        let latestStats: DashboardStats | null = null;
        statsService.stats$.subscribe(stats => { latestStats = stats; });
        tick();

        // First: a file-list update.
        let model = Immutable.Map<string, ModelFile>();
        model = model.set("a", new ModelFile({
            name: "a",
            state: ModelFile.State.DOWNLOADING,
            remote_size: 1000,
            local_size: 500,
            downloading_speed: 100,
        }));
        mockModelService._files.next(model);
        tick();

        // Then: a status update arrives (no file change).
        mockServerStatus.pushStatus({
            localTotal: 500_000_000_000, localUsed: 100_000_000_000,
            remoteTotal: 2_000_000_000_000, remoteUsed: 1_300_000_000_000,
        });
        tick();

        // File-derived fields preserved.
        expect(latestStats!.downloadingCount).toBe(1);
        expect(latestStats!.remoteTrackedBytes).toBe(1000);
        // Capacity updated.
        expect(latestStats!.remoteCapacityTotal).toBe(2_000_000_000_000);
    }));
});
