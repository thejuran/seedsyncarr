declare function spyOn<T, K extends keyof T>(
    object: T, method: K
): jasmine.Spy<T[K] extends (...args: infer A) => infer R ? (...args: A) => R : never>;

// Mock EventSource for testing - uses partial implementation to avoid strict type conflicts
export class MockEventSource {
    // EventSource constants
    readonly CONNECTING = 0;
    readonly OPEN = 1;
    readonly CLOSED = 2;

    // EventSource properties
    url: string;
    readyState = 0;
    withCredentials = false;
    onopen: ((ev: Event) => void) | null = null;
    onerror: ((ev: Event) => void) | null = null;
    onmessage: ((ev: MessageEvent) => void) | null = null;

    // Storage for event listeners - public for test access
    listeners: Map<string, EventListener> = new Map();

    constructor(url: string) {
        this.url = url;
    }

    addEventListener(
        type: string,
        listener: EventListenerOrEventListenerObject | null,
        _options?: boolean | AddEventListenerOptions
    ): void {
        if (listener && typeof listener === "function") {
            this.listeners.set(type, listener as EventListener);
        }
    }

    removeEventListener(
        type: string,
        _listener?: EventListenerOrEventListenerObject | null,
        _options?: boolean | EventListenerOptions
    ): void {
        this.listeners.delete(type);
    }

    dispatchEvent(_event: Event): boolean {
        return true;
    }

    close(): void {
        // Mock implementation - intentionally empty
    }
}

export function createMockEventSource(url: string): MockEventSource {
    const mockEventSource = new MockEventSource(url);
    spyOn(mockEventSource, "addEventListener").and.callThrough();
    spyOn(mockEventSource, "close").and.callThrough();
    return mockEventSource;
}
