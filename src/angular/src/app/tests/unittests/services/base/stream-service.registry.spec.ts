import {discardPeriodicTasks, fakeAsync, TestBed, tick} from "@angular/core/testing";

import {createMockEventSource, MockEventSource} from "../../../mocks/mock-event-source";
import {LoggerService} from "../../../../services/utils/logger.service";
import {
    EventSourceFactory, IStreamService, StreamDispatchService, StreamServiceRegistry
} from "../../../../services/base/stream-service.registry";
import {ModelFileService} from "../../../../services/files/model-file.service";
import {ServerStatusService} from "../../../../services/server/server-status.service";
import {ConnectedService} from "../../../../services/utils/connected.service";
import {LogService} from "../../../../services/logs/log.service";


class MockStreamService implements IStreamService {
    eventList: [string, string][] = [];
    connectedSeq: boolean[] = [];

    getEventNames(): string[] {
        throw new Error("Method not implemented.");
    }

    notifyConnected(): void {
        this.connectedSeq.push(true);
    }

    notifyDisconnected(): void {
        this.connectedSeq.push(false);
    }

    notifyEvent(eventName: string, data: string): void {
        this.eventList.push([eventName, data]);
    }
}


describe("Testing stream dispatch service", () => {
    let dispatchService: StreamDispatchService;

    let mockEventSource: MockEventSource;
    let mockService1: MockStreamService;
    let mockService2: MockStreamService;

    beforeEach(fakeAsync(() => {
        TestBed.configureTestingModule({
            providers: [
                LoggerService,
                StreamDispatchService
            ]
        });

        spyOn(EventSourceFactory, "createEventSource").and.callFake(
            (url: string) => {
                mockEventSource = createMockEventSource(url);
                return mockEventSource as unknown as EventSource;
            }
        );
        mockService1 = new MockStreamService();
        mockService2 = new MockStreamService();
        spyOn(mockService1, "getEventNames").and.returnValue(["event1a", "event1b"]);
        spyOn(mockService2, "getEventNames").and.returnValue(["event2a", "event2b"]);

        dispatchService = TestBed.inject(StreamDispatchService);

        dispatchService.registerService(mockService1);
        dispatchService.registerService(mockService2);
        dispatchService.onInit();
        tick();
        discardPeriodicTasks();
    }));

    it("should create an instance", () => {
        expect(dispatchService).toBeDefined();
    });

    it("should construct an event source with correct url", fakeAsync(() => {
        expect(mockEventSource.url).toBe("/server/stream");
        discardPeriodicTasks();
    }));

    it("should register all events with the event source", fakeAsync(() => {
        // 4 service events + 1 heartbeat "ping" event = 5 listeners
        expect(mockEventSource.addEventListener).toHaveBeenCalledTimes(5);
        expect(mockEventSource.listeners.size).toBe(5);
        expect(mockEventSource.listeners.has("event1a")).toBe(true);
        expect(mockEventSource.listeners.has("event1b")).toBe(true);
        expect(mockEventSource.listeners.has("event2a")).toBe(true);
        expect(mockEventSource.listeners.has("event2b")).toBe(true);
        expect(mockEventSource.listeners.has("ping")).toBe(true);
        discardPeriodicTasks();
    }));

    it("should set an error handler on the event source", fakeAsync(() => {
        expect(mockEventSource.onerror).toBeDefined();
        discardPeriodicTasks();
    }));

    it("should forward name and data correctly", fakeAsync(() => {
        mockEventSource.listeners.get("event1a")!(<MessageEvent>{data: "data1a"});
        tick();
        expect(mockService1.eventList).toEqual([
            ["event1a", "data1a"]
        ]);
        expect(mockService2.eventList).toEqual([]);

        mockEventSource.listeners.get("event1b")!(<MessageEvent>{data: "data1b"});
        tick();
        expect(mockService1.eventList).toEqual([
            ["event1a", "data1a"], ["event1b", "data1b"]
        ]);
        expect(mockService2.eventList).toEqual([]);

        mockEventSource.listeners.get("event2a")!(<MessageEvent>{data: "data2a"});
        tick();
        expect(mockService1.eventList).toEqual([
            ["event1a", "data1a"], ["event1b", "data1b"]
        ]);
        expect(mockService2.eventList).toEqual([
            ["event2a", "data2a"]
        ]);

        mockEventSource.listeners.get("event2b")!(<MessageEvent>{data: "data2b"});
        tick();
        expect(mockService1.eventList).toEqual([
            ["event1a", "data1a"], ["event1b", "data1b"]
        ]);
        expect(mockService2.eventList).toEqual([
            ["event2a", "data2a"], ["event2b", "data2b"]
        ]);

        mockEventSource.listeners.get("event1b")!(<MessageEvent>{data: "data1bbb"});
        tick();
        expect(mockService1.eventList).toEqual([
            ["event1a", "data1a"], ["event1b", "data1b"], ["event1b", "data1bbb"]
        ]);
        expect(mockService2.eventList).toEqual([
            ["event2a", "data2a"], ["event2b", "data2b"]
        ]);
        discardPeriodicTasks();
    }));

    it("should log a warning when receiving an unregistered event name", fakeAsync(() => {
        const loggerService = TestBed.inject(LoggerService);
        // warn is a getter returning a function; use spyOnProperty to intercept the getter
        // and return a jasmine spy so we can assert it was called
        const warnFn = jasmine.createSpy("warnFn");
        spyOnProperty(loggerService, "warn", "get").and.returnValue(warnFn);

        // Remove the service mapping for event1a AFTER the EventSource listener was created.
        // This simulates the guard path: the event arrives but no service is mapped.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (dispatchService as any)._eventNameToServiceMap.delete("event1a");

        // Fire the event via the existing listener — it will reach the next handler
        // but find no mapped service, triggering the warn path
        mockEventSource.listeners.get("event1a")!(<MessageEvent>{data: "data-orphan"});
        tick();

        // The warn guard should have been hit
        expect(warnFn).toHaveBeenCalled();

        // The event should NOT have been dispatched to any service
        expect(mockService1.eventList).toEqual([]);

        // Verify stream still works for other events
        mockEventSource.listeners.get("event2a")!(<MessageEvent>{data: "data2a"});
        tick();
        expect(mockService2.eventList).toEqual([["event2a", "data2a"]]);
        discardPeriodicTasks();
    }));

    it("should call connect on open", fakeAsync(() => {
        mockEventSource.onopen!(new Event("connected"));
        tick();
        expect(mockService1.connectedSeq).toEqual([true]);
        expect(mockService2.connectedSeq).toEqual([true]);
        discardPeriodicTasks();
    }));

    it("should call disconnect on error", fakeAsync(() => {
        mockEventSource.onerror!(new Event("bad event"));
        tick();
        expect(mockService1.connectedSeq).toEqual([false]);
        expect(mockService2.connectedSeq).toEqual([false]);
        tick(4000);
        discardPeriodicTasks();
    }));

    it("should send events after reconnect", fakeAsync(() => {
        mockEventSource.onopen!(new Event("connected"));
        tick();
        mockEventSource.onerror!(new Event("bad event"));
        tick(4000);
        mockEventSource.onopen!(new Event("connected"));
        tick();
        mockEventSource.listeners.get("event1a")!(<MessageEvent>{data: "data1a"});
        tick();
        expect(mockService1.eventList).toEqual([
            ["event1a", "data1a"]
        ]);
        expect(mockService2.eventList).toEqual([]);
        mockEventSource.listeners.get("event2b")!(<MessageEvent>{data: "data2b"});
        tick();
        expect(mockService1.eventList).toEqual([["event1a", "data1a"]]);
        expect(mockService2.eventList).toEqual([["event2b", "data2b"]]);
        discardPeriodicTasks();
    }));
});



describe("Testing stream service registry", () => {
    let registry: StreamServiceRegistry;

    let mockDispatch: jasmine.SpyObj<StreamDispatchService>;

    let mockModelFileService: jasmine.Spy;
    let mockServerStatusService: jasmine.Spy;
    let mockConnectedService: jasmine.Spy;
    let mockLogService: jasmine.Spy;

    let registered: unknown[];

    beforeEach(() => {
        registered = [];

        mockDispatch = jasmine.createSpyObj("mockDispatch", ["registerService"]);
        mockDispatch.registerService.and.callFake((value: IStreamService): IStreamService => { registered.push(value); return value; });

        mockModelFileService = jasmine.createSpy("mockModelFileService");
        mockServerStatusService = jasmine.createSpy("mockServerStatusService");
        mockConnectedService = jasmine.createSpy("mockConnectedService");
        mockLogService = jasmine.createSpy("mockLogService");

        TestBed.configureTestingModule({
            providers: [
                StreamServiceRegistry,
                LoggerService,
                {provide: StreamDispatchService, useValue: mockDispatch},
                {provide: ModelFileService, useValue: mockModelFileService},
                {provide: ServerStatusService, useValue: mockServerStatusService},
                {provide: ConnectedService, useValue: mockConnectedService},
                {provide: LogService, useValue: mockLogService}
            ]
        });

        registry = TestBed.inject(StreamServiceRegistry);
    });

    it("should create an instance", () => {
        expect(registry).toBeDefined();
    });

    it("should register model file service", () => {
        expect(registered.includes(mockModelFileService)).toBe(true);
    });

    it("should register server status service", () => {
        expect(registered.includes(mockServerStatusService)).toBe(true);
    });

    it("should register connected service", () => {
        expect(registered.includes(mockConnectedService)).toBe(true);
    });

    it("should register log service", () => {
        expect(registered.includes(mockLogService)).toBe(true);
    });
});
