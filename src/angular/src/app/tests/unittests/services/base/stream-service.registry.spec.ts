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

    it("should create an instance", fakeAsync(() => {
        expect(dispatchService).toBeDefined();
        discardPeriodicTasks();
    }));

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

    describe("heartbeat-vs-timeout race", () => {
        it("heartbeat after timeout boundary re-arms _lastEventTime and prevents spurious reconnect", fakeAsync(() => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (dispatchService as any).startTimeoutChecker();
            // Seed _lastEventTime via onopen so checkConnectionTimeout doesn't bail
            // at the _lastEventTime === 0 guard (line 125)
            mockEventSource.onopen!(new Event("connected"));
            tick();

            // Advance 30001ms: interval checks fire at T=5000..30000.
            // At T=30000, elapsed==30000 which is NOT > 30000 (strict), so no reconnect.
            tick(30001);

            // Fire heartbeat AFTER the 30s boundary but BEFORE the next checker tick.
            // No tick() between this and the subsequent tick(5000) — same fakeAsync frame.
            // This re-arms _lastEventTime to ~30001ms (registry.ts line 204).
            mockEventSource.listeners.get("ping")!(new Event("ping"));

            // Advance to next interval boundary (T=35000ms).
            // elapsed = 35000 - 30001 = 4999ms < 30000ms → NO reconnect.
            tick(5000);

            // No spurious reconnect and no double subscription
            expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(1);
            // Services must NOT have received a false disconnect
            expect(mockService1.connectedSeq).not.toContain(false);
            expect(mockService2.connectedSeq).not.toContain(false);
            discardPeriodicTasks();
        }));

        it("without heartbeat, timeout fires and reconnect occurs (positive control)", fakeAsync(() => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (dispatchService as any).startTimeoutChecker();
            // Seed _lastEventTime so checkConnectionTimeout doesn't bail at the guard
            mockEventSource.onopen!(new Event("connected"));
            tick();

            // Advance 35001ms: at T=35000 elapsed=35000 > 30000 (strict) →
            // reconnectDueToTimeout() fires: closes source, notifies disconnect,
            // sets _lastEventTime=0, schedules setTimeout at STREAM_RETRY_INTERVAL_MS=3000.
            tick(35001);

            // Timeout triggered: disconnect must have been notified
            expect(mockService1.connectedSeq).toContain(false);
            // Reconnect timer is pending but has not yet fired
            expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(1);

            // Advance past STREAM_RETRY_INTERVAL_MS=3000ms → createSseObserver fires →
            // createEventSource called a 2nd time
            tick(3001);
            expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(2);
            discardPeriodicTasks();
        }));
    });

    describe("BUG-04 same-tick reconnect collision", () => {
        it("BUG-04: stale onerror after idle-timeout close does not double-notify disconnect or double-reconnect",
            fakeAsync(() => {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (dispatchService as any).startTimeoutChecker();
                // Seed _lastEventTime via onopen so checkConnectionTimeout doesn't bail
                // at the _lastEventTime === 0 guard; this also pushes one true into connectedSeq
                mockEventSource.onopen!(new Event("connected"));
                tick();

                // Advance past timeout boundary: elapsed 35001 > 30000 (strict) →
                // reconnectDueToTimeout() fires: closes _currentEventSource, notifies
                // disconnect ONCE, schedules the 3000ms retry timer.
                tick(35001);

                // One timeout-path disconnect must have been delivered
                const falsesAfterTimeout = mockService1.connectedSeq.filter(v => v === false).length;
                expect(falsesAfterTimeout).toBe(1);

                // Simulate the now-closed EventSource firing onerror (some browsers/proxies
                // do this on .close()). The mockEventSource.close() is a no-op that does NOT
                // clear .onerror, so this call reaches observer.error() on the subscription.
                //
                // RED DISCRIMINATOR: Before the BUG-04 fix, _currentSubscription is still live
                // here, so observer.error() triggers the error handler which pushes a SECOND
                // false into connectedSeq → count becomes 2.
                // After the fix, reconnectDueToTimeout() unsubscribes _currentSubscription
                // before scheduling the retry, so observer.error() hits a closed subscriber
                // and the error callback never runs → count stays 1.
                mockEventSource.onerror!(new Event("error"));
                tick();

                // RED ASSERTION (discriminator): exactly ONE disconnect notification total.
                // Before the fix this is 2 (stale subscription error handler ran, pushed a
                // second false). After the unsubscribe fix it is 1 (torn-down subscription's
                // error callback never fires).
                expect(mockService1.connectedSeq.filter(v => v === false).length).toBe(1);
                // Mirror for mockService2 — same invariant
                expect(mockService2.connectedSeq.filter(v => v === false).length).toBe(1);

                // Flush the retry timer → exactly one reconnect fires → createSseObserver
                // called once more.
                tick(3001);

                // GREEN-INVARIANT GUARD: createEventSource is called exactly twice — initial
                // (1) + exactly one reconnect (2). Both reconnect paths clear-and-re-arm the
                // single _reconnectTimer, so this count is 2 on BOTH sides of the fix; it
                // confirms no double reconnect but is NOT the RED discriminator.
                expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(2);
                discardPeriodicTasks();
            }));
    });
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
