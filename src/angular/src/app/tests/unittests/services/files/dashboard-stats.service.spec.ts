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


describe("Testing dashboard stats service", () => {
    let statsService: DashboardStatsService;
    let mockModelService: MockModelFileService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                DashboardStatsService,
                ViewFileService,
                LoggerService,
                ConnectedService,
                FileSelectionService,
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
});
