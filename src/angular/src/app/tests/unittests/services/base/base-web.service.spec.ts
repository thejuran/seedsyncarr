import {TestBed} from "@angular/core/testing";
import {Injectable, OnDestroy} from "@angular/core";

import {BaseWebService} from "../../../../services/base/base-web.service";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";
import {MockStreamServiceRegistry} from "../../../mocks/mock-stream-service.registry";
import {LoggerService} from "../../../../services/utils/logger.service";
import {ConnectedService} from "../../../../services/utils/connected.service";


@Injectable()
class TestBaseWebService extends BaseWebService implements OnDestroy {
    public onConnected(): void {
        // Test stub - intentionally empty
    }

    public onDisconnected(): void {
        // Test stub - intentionally empty
    }

    override ngOnDestroy(): void {
        super.ngOnDestroy();
    }
}

describe("Testing base web service", () => {
    let baseWebService: TestBaseWebService;

    let mockRegistry: MockStreamServiceRegistry;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                TestBaseWebService,
                LoggerService,
                ConnectedService,
                {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
            ]
        });

        mockRegistry = TestBed.inject(StreamServiceRegistry) as unknown as MockStreamServiceRegistry;

        baseWebService = TestBed.inject(TestBaseWebService);
        spyOn(baseWebService, "onConnected");
        spyOn(baseWebService, "onDisconnected");

        // Initialize base web service
        baseWebService.onInit();
    });

    it("should create an instance", () => {
        expect(baseWebService).toBeDefined();
    });

    it("should forward the connected notification", () => {
        mockRegistry.connectedService.notifyConnected();
        expect(baseWebService.onConnected).toHaveBeenCalledTimes(1);
    });

    it("should forward the disconnected notification", () => {
        mockRegistry.connectedService.notifyDisconnected();
        expect(baseWebService.onDisconnected).toHaveBeenCalledTimes(1);
    });

    it("should stop receiving notifications after ngOnDestroy", () => {
        // Verify initial subscription works
        mockRegistry.connectedService.notifyConnected();
        expect(baseWebService.onConnected).toHaveBeenCalledTimes(1);

        // Record call counts before ngOnDestroy
        const connectedCallsBefore = (baseWebService.onConnected as jasmine.Spy).calls.count();
        const disconnectedCallsBefore = (baseWebService.onDisconnected as jasmine.Spy).calls.count();

        // Call ngOnDestroy to clean up
        baseWebService.ngOnDestroy();

        // Further notifications should not trigger callbacks
        mockRegistry.connectedService.notifyConnected();
        mockRegistry.connectedService.notifyDisconnected();

        // Verify no new calls were made after ngOnDestroy
        expect((baseWebService.onConnected as jasmine.Spy).calls.count()).toBe(connectedCallsBefore);
        expect((baseWebService.onDisconnected as jasmine.Spy).calls.count()).toBe(disconnectedCallsBefore);
    });

    it("should handle ngOnDestroy being called multiple times", () => {
        baseWebService.ngOnDestroy();
        expect(() => baseWebService.ngOnDestroy()).not.toThrow();
    });
});
