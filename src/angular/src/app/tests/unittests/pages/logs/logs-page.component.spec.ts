import {BehaviorSubject, Subject} from "rxjs";
import {ComponentFixture, fakeAsync, TestBed, tick} from "@angular/core/testing";
import {FormsModule} from "@angular/forms";
import {DatePipe, NgClass} from "@angular/common";

import {LogsPageComponent} from "../../../../pages/logs/logs-page.component";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";
import {LogRecord} from "../../../../services/logs/log-record";

// Inline template (avoids html/scss loader issues in karma — established pattern)
const LOGS_PAGE_TEMPLATE = `
<div class="logs-toolbar">
  <div class="toolbar-left">
    <div class="level-filter-group">
      @for (lvl of ['ALL', 'INFO', 'WARN', 'ERROR', 'DEBUG']; track lvl) {
        <button class="level-btn" [class.level-btn--active]="activeLevel === lvl" (click)="setLevel($any(lvl))">{{ lvl }}</button>
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
    @for (entry of filteredLogs; track $index) {
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
    hasReceivedLogs = false;

    get logs() {
        return this._logs$.asObservable();
    }

    emit(record: LogRecord): void {
        this._logs$.next(record);
    }
}

class MockConnectedService {
    private _connected$ = new BehaviorSubject<boolean>(false);

    get connected() {
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
            imports: [LogsPageComponent, DatePipe, NgClass, FormsModule],
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
            component.setLevel('ALL');
            expect(component.filteredLogs.length).toBe(5);
        });

        it("INFO returns only INFO entries", () => {
            component.setLevel('INFO');
            expect(component.filteredLogs.length).toBe(1);
            expect(component.filteredLogs[0].message).toBe("info-msg");
        });

        it("WARN returns only WARNING entries", () => {
            component.setLevel('WARN');
            expect(component.filteredLogs.length).toBe(1);
            expect(component.filteredLogs[0].message).toBe("warn-msg");
        });

        it("ERROR returns ERROR + CRITICAL entries", () => {
            component.setLevel('ERROR');
            expect(component.filteredLogs.length).toBe(2);
            expect(component.filteredLogs.map(r => r.message)).toEqual(["error-msg", "crit-msg"]);
        });

        it("DEBUG returns only DEBUG entries", () => {
            component.setLevel('DEBUG');
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
            (component as any).searchQuery = "download";
            expect(component.filteredLogs.length).toBe(1);
            expect(component.filteredLogs[0].message).toContain("download");
        }));

        it("invalid regex does not throw", fakeAsync(() => {
            (component as any).searchQuery = "(invalid[";
            expect(() => component.filteredLogs).not.toThrow();
            // Should return all results when regex is invalid
            expect(component.filteredLogs.length).toBe(2);
        }));
    });

    // Tests 11-12: clear (LOGS-03)
    describe("clearLogs (LOGS-03)", () => {
        it("empties allLogs array", fakeAsync(() => {
            fixture.detectChanges();
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "msg"));
            tick();
            expect(component.allLogs.length).toBe(1);
            component.clearLogs();
            expect(component.allLogs.length).toBe(0);
        }));

        it("does not call LogService methods", fakeAsync(() => {
            fixture.detectChanges();
            const logSvc = mockRegistry.logService;
            const emitSpy = spyOn(logSvc, "emit");
            component.clearLogs();
            expect(emitSpy).not.toHaveBeenCalled();
        }));
    });

    // Test 13: export (LOGS-03)
    it("exportLogs creates a download with filtered entries", fakeAsync(() => {
        fixture.detectChanges();
        const time = new Date(2026, 3, 14, 14, 2, 11);
        mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "export-test", time));
        tick();

        const createSpy = spyOn(URL, "createObjectURL").and.returnValue("blob:test");
        const revokeSpy = spyOn(URL, "revokeObjectURL");
        const clickSpy = jasmine.createSpy("click");
        spyOn(document, "createElement").and.returnValue({
            set href(v: string) {},
            set download(v: string) {},
            click: clickSpy
        } as any);

        component.exportLogs();
        expect(createSpy).toHaveBeenCalledTimes(1);
        expect(clickSpy).toHaveBeenCalledTimes(1);
        expect(revokeSpy).toHaveBeenCalledTimes(1);
    }));

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

    // Test 17: levelLabel
    describe("levelLabel", () => {
        it("returns WARN for WARNING", () => {
            expect(component.levelLabel(LogRecord.Level.WARNING)).toBe("WARN");
        });
        it("returns CRIT for CRITICAL", () => {
            expect(component.levelLabel(LogRecord.Level.CRITICAL)).toBe("CRIT");
        });
    });

    // Test 18: formatTimestamp
    it("formatTimestamp returns HH:MM:SS.mmm", () => {
        const d = new Date(2026, 3, 14, 9, 5, 3, 42);
        expect(component.formatTimestamp(d)).toBe("09:05:03.042");
    });
});
