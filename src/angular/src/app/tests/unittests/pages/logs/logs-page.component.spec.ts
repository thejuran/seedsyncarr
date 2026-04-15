import {BehaviorSubject, Observable, Subject} from "rxjs";
import {ComponentFixture, fakeAsync, TestBed, tick} from "@angular/core/testing";
import {FormsModule} from "@angular/forms";
import {NgClass} from "@angular/common";

import {LogsPageComponent} from "../../../../pages/logs/logs-page.component";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";
import {LogRecord} from "../../../../services/logs/log-record";

// Inline template (avoids html/scss loader issues in karma — established pattern)
const LOGS_PAGE_TEMPLATE = `
<div class="logs-toolbar">
  <div class="toolbar-left">
    <div class="level-filter-group">
      @for (lvl of LEVEL_FILTERS; track lvl) {
        <button class="level-btn" [class.level-btn--active]="activeLevel === lvl" (click)="setLevel(lvl)">{{ lvl }}</button>
      }
    </div>
    <div class="search-field">
      <input type="text" class="search-input" [ngModel]="searchInput" (ngModelChange)="searchInput = $event; onSearchInput($event)">
    </div>
  </div>
  <div class="toolbar-right">
    <button class="action-btn" [class.action-btn--active]="autoScroll" (click)="toggleAutoScroll()">Auto-scroll</button>
    <button class="action-btn action-btn--clear" (click)="clearLogs()">Clear</button>
    <button class="action-btn action-btn--export" (click)="exportLogs()">Export .log</button>
  </div>
</div>
<div class="terminal-container">
  <div #terminalViewport class="terminal-viewport" (scroll)="onTerminalScroll($event)">
    @for (entry of filteredLogs; track entry) {
      <div class="log-row" [ngClass]="levelRowClass(entry.level)">
        <div class="log-gutter">{{ $index + 1 }}</div>
        <div class="log-ts">{{ formatTimestamp(entry.time) }}</div>
        <div class="log-level" [ngClass]="levelClass(entry.level)">{{ levelLabel(entry.level) }}</div>
        <div class="log-msg">{{ entry.message }}</div>
      </div>
    }
  </div>
</div>
<div class="status-bar">
  <div class="status-bar__left">
    <span class="status-dot" [class.status-dot--connected]="isConnected" [class.status-dot--disconnected]="!isConnected"></span>
    @if (isConnected) {
      <span>Connected to active seedbox daemon</span>
    } @else {
      <span>Disconnected</span>
    }
  </div>
  <div class="status-bar__right">
    <span>{{ allLogs.length }} logs indexed</span>
    <span class="status-bar__timestamp">LAST UPDATED: {{ formatLastUpdated() }}</span>
  </div>
</div>
`;


class MockLogService {
    private _logs$ = new Subject<LogRecord>();

    get logs(): Observable<LogRecord> {
        return this._logs$.asObservable();
    }

    emit(record: LogRecord): void {
        this._logs$.next(record);
    }
}

class MockConnectedService {
    private _connected$ = new BehaviorSubject<boolean>(false);

    get connected(): Observable<boolean> {
        return this._connected$.asObservable();
    }

    setConnected(val: boolean): void {
        this._connected$.next(val);
    }
}

class MockStreamServiceRegistry {
    logService = new MockLogService();
    connectedService = new MockConnectedService();
}

function makeRecord(level: LogRecord.Level, message: string, time?: Date): LogRecord {
    return new LogRecord({
        time: time ?? new Date(2026, 3, 14, 14, 2, 11, 450),
        level,
        loggerName: "test.logger",
        message,
        exceptionTraceback: "",
    });
}


describe("LogsPageComponent", () => {
    let component: LogsPageComponent;
    let fixture: ComponentFixture<LogsPageComponent>;
    let mockRegistry: MockStreamServiceRegistry;

    beforeEach(async () => {
        mockRegistry = new MockStreamServiceRegistry();

        await TestBed.configureTestingModule({
            imports: [LogsPageComponent, NgClass, FormsModule],
            providers: [
                {provide: StreamServiceRegistry, useValue: mockRegistry}
            ]
        })
        .overrideTemplate(LogsPageComponent, LOGS_PAGE_TEMPLATE)
        .compileComponents();

        fixture = TestBed.createComponent(LogsPageComponent);
        component = fixture.componentInstance;
    });

    // Test 1: creates
    it("should create", () => {
        expect(component).toBeDefined();
    });

    // Test 2: accumulates logs
    it("should accumulate log records in allLogs", fakeAsync(() => {
        fixture.detectChanges();
        mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "msg1"));
        tick();
        expect(component.allLogs.length).toBe(1);
    }));

    // Test 3: caps at 5000
    it("should cap allLogs at 5000 entries", fakeAsync(() => {
        fixture.detectChanges();
        for (let i = 0; i < 5005; i++) {
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, `msg-${i}`));
        }
        tick();
        expect(component.allLogs.length).toBe(5000);
        expect(component.allLogs[0].message).toBe("msg-5");
    }));

    // Tests 4-8: level filtering (LOGS-01)
    describe("level filtering (LOGS-01)", () => {
        beforeEach(fakeAsync(() => {
            fixture.detectChanges();
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.DEBUG, "debug-msg"));
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "info-msg"));
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.WARNING, "warn-msg"));
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.ERROR, "error-msg"));
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.CRITICAL, "crit-msg"));
            tick();
        }));

        it("ALL returns all entries", () => {
            component.setLevel("ALL");
            expect(component.filteredLogs.length).toBe(5);
        });

        it("INFO returns only INFO entries", () => {
            component.setLevel("INFO");
            expect(component.filteredLogs.length).toBe(1);
            expect(component.filteredLogs[0].message).toBe("info-msg");
        });

        it("WARN returns only WARNING entries", () => {
            component.setLevel("WARN");
            expect(component.filteredLogs.length).toBe(1);
            expect(component.filteredLogs[0].message).toBe("warn-msg");
        });

        it("ERROR returns ERROR + CRITICAL entries", () => {
            component.setLevel("ERROR");
            expect(component.filteredLogs.length).toBe(2);
            expect(component.filteredLogs.map(r => r.message)).toEqual(["error-msg", "crit-msg"]);
        });

        it("DEBUG returns only DEBUG entries", () => {
            component.setLevel("DEBUG");
            expect(component.filteredLogs.length).toBe(1);
            expect(component.filteredLogs[0].message).toBe("debug-msg");
        });
    });

    // Tests 9-10: regex search (LOGS-02)
    describe("regex search (LOGS-02)", () => {
        beforeEach(fakeAsync(() => {
            fixture.detectChanges();
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "file download started"));
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "connection established"));
            tick();
        }));

        it("filters by regex match on message", fakeAsync(() => {
            // Directly set searchQuery (bypassing debounce for unit test)
            component.searchQuery = "download";
            component.setLevel("ALL");
            expect(component.filteredLogs.length).toBe(1);
            expect(component.filteredLogs[0].message).toContain("download");
        }));

        it("invalid regex does not throw", fakeAsync(() => {
            component.searchQuery = "(invalid[";
            component.setLevel("ALL");
            expect(component.filteredLogs.length).toBe(2);
        }));
    });

    // Tests 11-12: clear (LOGS-03)
    describe("clearLogs (LOGS-03)", () => {
        it("empties allLogs array and resets search fields through debounce", fakeAsync(() => {
            fixture.detectChanges();
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "msg"));
            tick();
            expect(component.allLogs.length).toBe(1);
            component.searchInput = "foo";
            component.searchQuery = "foo";
            component.clearLogs();
            expect(component.allLogs.length).toBe(0);
            expect(component.searchInput).toBe("");
            expect(component.searchQuery).toBe("");
            // Flush debounce to verify searchQuery$ pipeline emission resolves cleanly
            tick(200);
            expect(component.searchQuery).toBe("");
        }));

        it("resets scan accumulator so new logs start fresh", fakeAsync(() => {
            fixture.detectChanges();
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "before-clear"));
            tick();
            expect(component.allLogs.length).toBe(1);
            component.clearLogs();
            expect(component.allLogs.length).toBe(0);
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "after-clear"));
            tick();
            expect(component.allLogs.length).toBe(1);
            expect(component.allLogs[0].message).toBe("after-clear");
        }));
    });

    // Test 13: export (LOGS-03)
    it("exportLogs creates a download with correct href and filename", fakeAsync(() => {
        fixture.detectChanges();
        const time = new Date(2026, 3, 14, 14, 2, 11);
        mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "export-test", time));
        tick();

        const createSpy = spyOn(URL, "createObjectURL").and.returnValue("blob:test");
        spyOn(URL, "revokeObjectURL");
        const fakeAnchor = document.createElement("a");
        const clickSpy = spyOn(fakeAnchor, "click");
        const origCreate = document.createElement.bind(document);
        spyOn(document, "createElement").and.callFake((tag: string) =>
            tag === "a" ? fakeAnchor : origCreate(tag));

        component.exportLogs();
        expect(createSpy).toHaveBeenCalledTimes(1);
        expect(clickSpy).toHaveBeenCalledTimes(1);
        expect(fakeAnchor.href).toContain("blob:test");
        expect(fakeAnchor.download).toMatch(/^seedsyncarr-logs-.*\.log$/);
    }));

    // Test: export sanitizes newlines in messages
    it("exportLogs sanitizes newlines in log messages", async () => {
        fixture.detectChanges();
        // Manually set allLogs with a newline-containing message
        component.allLogs = [makeRecord(LogRecord.Level.INFO, "line1\ninjected line")];
        component.setLevel("ALL");

        let capturedBlob: Blob | null = null;
        spyOn(URL, "createObjectURL").and.callFake((blob: Blob) => {
            capturedBlob = blob;
            return "blob:test";
        });
        spyOn(URL, "revokeObjectURL");
        const fakeAnchor = document.createElement("a");
        spyOn(fakeAnchor, "click");
        const origCreate = document.createElement.bind(document);
        spyOn(document, "createElement").and.callFake((tag: string) =>
            tag === "a" ? fakeAnchor : origCreate(tag));

        component.exportLogs();
        expect(capturedBlob).toBeTruthy();
        if (!capturedBlob) {return;}
        const content = await (capturedBlob as Blob).text();
        // Each individual log line should be free of embedded newlines
        const lines = content.split("\n");
        lines.forEach(line => expect(line).not.toMatch(/[\r\n]/));
        expect(content).toContain("line1 injected line");
    });

    // Test 14: connection status (LOGS-04)
    it("isConnected updates from ConnectedService", fakeAsync(() => {
        fixture.detectChanges();
        expect(component.isConnected).toBeFalse();
        mockRegistry.connectedService.setConnected(true);
        tick();
        expect(component.isConnected).toBeTrue();
    }));

    // Test 15: lastUpdated set on log arrival (LOGS-04)
    it("lastUpdated is set when log entries arrive", fakeAsync(() => {
        fixture.detectChanges();
        expect(component.lastUpdated).toBeNull();
        mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "msg"));
        tick();
        expect(component.lastUpdated).toBeTruthy();
        expect(component.lastUpdated instanceof Date).toBeTrue();
    }));

    // Test 16: formatLastUpdated (LOGS-04)
    describe("formatLastUpdated", () => {
        it("returns placeholder when no updates", () => {
            expect(component.formatLastUpdated()).toBe("--:--:-- --");
        });

        it("formats in HH:MM:SS AM/PM", () => {
            component.lastUpdated = new Date(2026, 3, 14, 14, 30, 45);
            expect(component.formatLastUpdated()).toBe("2:30:45 PM");
        });

        it("handles midnight correctly", () => {
            component.lastUpdated = new Date(2026, 3, 14, 0, 5, 9);
            expect(component.formatLastUpdated()).toBe("12:05:09 AM");
        });
    });

    // Test 17: levelLabel (full coverage)
    describe("levelLabel", () => {
        it("returns DEBUG for DEBUG", () => {
            expect(component.levelLabel(LogRecord.Level.DEBUG)).toBe("DEBUG");
        });
        it("returns INFO for INFO", () => {
            expect(component.levelLabel(LogRecord.Level.INFO)).toBe("INFO");
        });
        it("returns WARN for WARNING", () => {
            expect(component.levelLabel(LogRecord.Level.WARNING)).toBe("WARN");
        });
        it("returns ERROR for ERROR", () => {
            expect(component.levelLabel(LogRecord.Level.ERROR)).toBe("ERROR");
        });
        it("returns CRIT for CRITICAL", () => {
            expect(component.levelLabel(LogRecord.Level.CRITICAL)).toBe("CRIT");
        });
    });

    // Test: levelClass
    describe("levelClass", () => {
        it("returns log-level--info for INFO", () => {
            expect(component.levelClass(LogRecord.Level.INFO)).toBe("log-level--info");
        });
        it("returns log-level--warn for WARNING", () => {
            expect(component.levelClass(LogRecord.Level.WARNING)).toBe("log-level--warn");
        });
        it("returns log-level--debug for DEBUG", () => {
            expect(component.levelClass(LogRecord.Level.DEBUG)).toBe("log-level--debug");
        });
        it("returns log-level--error-badge for ERROR", () => {
            expect(component.levelClass(LogRecord.Level.ERROR)).toBe("log-level--error-badge");
        });
        it("returns log-level--error-badge for CRITICAL", () => {
            expect(component.levelClass(LogRecord.Level.CRITICAL)).toBe("log-level--error-badge");
        });
    });

    // Test: levelRowClass
    describe("levelRowClass", () => {
        it("returns log-row--error for ERROR", () => {
            expect(component.levelRowClass(LogRecord.Level.ERROR)).toBe("log-row--error");
        });
        it("returns log-row--error for CRITICAL", () => {
            expect(component.levelRowClass(LogRecord.Level.CRITICAL)).toBe("log-row--error");
        });
        it("returns log-row--warn for WARNING", () => {
            expect(component.levelRowClass(LogRecord.Level.WARNING)).toBe("log-row--warn");
        });
        it("returns empty string for INFO", () => {
            expect(component.levelRowClass(LogRecord.Level.INFO)).toBe("");
        });
        it("returns empty string for DEBUG", () => {
            expect(component.levelRowClass(LogRecord.Level.DEBUG)).toBe("");
        });
    });

    // Test: toggleAutoScroll
    describe("toggleAutoScroll", () => {
        it("toggles autoScroll from true to false", () => {
            component.autoScroll = true;
            component.toggleAutoScroll();
            expect(component.autoScroll).toBeFalse();
        });

        it("toggles autoScroll from false to true", () => {
            component.autoScroll = false;
            component.toggleAutoScroll();
            expect(component.autoScroll).toBeTrue();
        });
    });

    // Test: onTerminalScroll
    describe("onTerminalScroll", () => {
        it("disables autoScroll when scrolled away from bottom", () => {
            component.autoScroll = true;
            const mockEvent = {
                target: { scrollHeight: 1000, scrollTop: 500, clientHeight: 400 }
            } as unknown as Event;
            component.onTerminalScroll(mockEvent);
            expect(component.autoScroll).toBeFalse();
        });

        it("does not re-enable autoScroll when scrolled to bottom", () => {
            component.autoScroll = false;
            const mockEvent = {
                target: { scrollHeight: 1000, scrollTop: 595, clientHeight: 400 }
            } as unknown as Event;
            component.onTerminalScroll(mockEvent);
            expect(component.autoScroll).toBeFalse();
        });

        it("handles null event target gracefully", () => {
            const mockEvent = { target: null } as unknown as Event;
            expect(() => component.onTerminalScroll(mockEvent)).not.toThrow();
        });
    });

    // Test 18: formatTimestamp
    it("formatTimestamp returns HH:MM:SS.mmm", () => {
        const d = new Date(2026, 3, 14, 9, 5, 3, 42);
        expect(component.formatTimestamp(d)).toBe("09:05:03.042");
    });
});
