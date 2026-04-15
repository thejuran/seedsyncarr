import {ComponentFixture, fakeAsync, TestBed, tick} from "@angular/core/testing";
import {DatePipe, NgClass} from "@angular/common";
import {RouterModule} from "@angular/router";
import {Observable, Subject} from "rxjs";

import {DashboardLogPaneComponent} from "../../../../pages/files/dashboard-log-pane.component";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";
import {LogRecord} from "../../../../services/logs/log-record";

// Inline copy of the real template (avoids html/scss loader issues in karma)
const LOG_PANE_TEMPLATE = `
<section class="log-pane">
  <div class="log-pane__header">
    <span class="log-pane__title">
      <i class="fa fa-terminal"></i> System Event Log
    </span>
    <div class="log-pane__actions">
      <button class="log-pane__action-btn" (click)="copyLogs()" title="Copy logs">
        <i class="fa fa-copy"></i>
      </button>
      <a class="log-pane__action-btn" routerLink="/logs" title="Expand logs">
        <i class="fa fa-expand"></i>
      </a>
    </div>
  </div>
  <div class="log-pane__body">
    @if (!logService.hasReceivedLogs) {
      <div class="log-pane__spinner">
        <i class="fa fa-circle-o-notch fa-spin"></i>
      </div>
    }
    @for (entry of entries; track $index) {
      <div class="log-entry"
           [class.log-entry--error]="entry.level === LogRecord.Level.ERROR || entry.level === LogRecord.Level.CRITICAL">
        <span class="log-entry__ts">{{ entry.time | date:'HH:mm:ss.SSS' }}</span>
        <span class="log-entry__badge"
              [ngClass]="{
                'log-entry__badge--info': entry.level === LogRecord.Level.INFO || entry.level === LogRecord.Level.DEBUG,
                'log-entry__badge--warn': entry.level === LogRecord.Level.WARNING,
                'log-entry__badge--error': entry.level === LogRecord.Level.ERROR || entry.level === LogRecord.Level.CRITICAL
              }">{{ levelBadge(entry.level) }}</span>
        <span class="log-entry__msg">{{ entry.message }}</span>
      </div>
    }
  </div>
</section>
`;


class MockLogService {
    private _logs$ = new Subject<LogRecord>();
    hasReceivedLogs = false;

    get logs(): Observable<LogRecord> {
        return this._logs$.asObservable();
    }

    emit(record: LogRecord): void {
        this._logs$.next(record);
    }
}

class MockStreamServiceRegistry {
    logService = new MockLogService();
}

function makeRecord(level: LogRecord.Level, message: string, time?: Date): LogRecord {
    return new LogRecord({
        time: time ?? new Date(2026, 3, 14, 14, 2, 11, 450),
        level,
        loggerName: "test",
        message,
        exceptionTraceback: "",
    });
}


describe("DashboardLogPaneComponent", () => {
    let component: DashboardLogPaneComponent;
    let fixture: ComponentFixture<DashboardLogPaneComponent>;
    let mockRegistry: MockStreamServiceRegistry;

    beforeEach(async () => {
        mockRegistry = new MockStreamServiceRegistry();

        await TestBed.configureTestingModule({
            imports: [DashboardLogPaneComponent, DatePipe, NgClass, RouterModule.forRoot([])],
            providers: [
                {provide: StreamServiceRegistry, useValue: mockRegistry}
            ]
        })
        .overrideTemplate(DashboardLogPaneComponent, LOG_PANE_TEMPLATE)
        .compileComponents();

        fixture = TestBed.createComponent(DashboardLogPaneComponent);
        component = fixture.componentInstance;
    });

    it("should create", () => {
        expect(component).toBeDefined();
    });

    it("should start with empty entries array", () => {
        expect(component.entries).toEqual([]);
        expect(component.entries.length).toBe(0);
    });

    it("should add a log record to entries when LogService emits", fakeAsync(() => {
        fixture.detectChanges(); // triggers ngOnInit
        const record = makeRecord(LogRecord.Level.INFO, "Test message");
        mockRegistry.logService.emit(record);
        tick();

        expect(component.entries.length).toBe(1);
        expect(component.entries[0].message).toBe("Test message");
    }));

    it("should cap entries at 50, discarding oldest", fakeAsync(() => {
        fixture.detectChanges();
        for (let i = 0; i < 55; i++) {
            mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, `msg-${i}`));
        }
        tick();

        expect(component.entries.length).toBe(50);
        // First 5 should be discarded; entries[0] should be msg-5
        expect(component.entries[0].message).toBe("msg-5");
        expect(component.entries[49].message).toBe("msg-54");
    }));

    describe("levelBadge()", () => {
        it("should return [DEBUG] for DEBUG level", () => {
            expect(component.levelBadge(LogRecord.Level.DEBUG)).toBe("[DEBUG]");
        });

        it("should return [INFO] for INFO level", () => {
            expect(component.levelBadge(LogRecord.Level.INFO)).toBe("[INFO]");
        });

        it("should return [WARN] for WARNING level", () => {
            expect(component.levelBadge(LogRecord.Level.WARNING)).toBe("[WARN]");
        });

        it("should return [ERR!] for ERROR level", () => {
            expect(component.levelBadge(LogRecord.Level.ERROR)).toBe("[ERR!]");
        });

        it("should return [CRIT] for CRITICAL level", () => {
            expect(component.levelBadge(LogRecord.Level.CRITICAL)).toBe("[CRIT]");
        });
    });

    it("should render timestamp, badge, and message for each entry", fakeAsync(() => {
        mockRegistry.logService.hasReceivedLogs = true;
        fixture.detectChanges();

        mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "Hello world"));
        tick();
        fixture.detectChanges();

        const entries = fixture.nativeElement.querySelectorAll(".log-entry");
        expect(entries.length).toBe(1);

        const ts = entries[0].querySelector(".log-entry__ts");
        expect(ts).toBeTruthy();
        // Timestamp should match HH:mm:ss.SSS format
        expect(ts!.textContent!.trim()).toMatch(/\d{2}:\d{2}:\d{2}\.\d{3}/);

        const badge = entries[0].querySelector(".log-entry__badge");
        expect(badge).toBeTruthy();
        expect(badge!.textContent!.trim()).toBe("[INFO]");

        const msg = entries[0].querySelector(".log-entry__msg");
        expect(msg).toBeTruthy();
        expect(msg!.textContent!.trim()).toBe("Hello world");
    }));

    it("should apply correct CSS class for INFO entries", fakeAsync(() => {
        mockRegistry.logService.hasReceivedLogs = true;
        fixture.detectChanges();
        mockRegistry.logService.emit(makeRecord(LogRecord.Level.INFO, "info msg"));
        tick();
        fixture.detectChanges();

        const badge = fixture.nativeElement.querySelector(".log-entry__badge");
        expect(badge!.classList.contains("log-entry__badge--info")).toBeTrue();
    }));

    it("should apply correct CSS class for WARNING entries", fakeAsync(() => {
        mockRegistry.logService.hasReceivedLogs = true;
        fixture.detectChanges();
        mockRegistry.logService.emit(makeRecord(LogRecord.Level.WARNING, "warn msg"));
        tick();
        fixture.detectChanges();

        const badge = fixture.nativeElement.querySelector(".log-entry__badge");
        expect(badge!.classList.contains("log-entry__badge--warn")).toBeTrue();
    }));

    it("should apply correct CSS class for ERROR entries", fakeAsync(() => {
        mockRegistry.logService.hasReceivedLogs = true;
        fixture.detectChanges();
        mockRegistry.logService.emit(makeRecord(LogRecord.Level.ERROR, "error msg"));
        tick();
        fixture.detectChanges();

        const badge = fixture.nativeElement.querySelector(".log-entry__badge");
        expect(badge!.classList.contains("log-entry__badge--error")).toBeTrue();
    }));

    it("should show spinner when hasReceivedLogs is false", fakeAsync(() => {
        mockRegistry.logService.hasReceivedLogs = false;
        fixture.detectChanges();
        tick();

        const spinner = fixture.nativeElement.querySelector(".log-pane__spinner");
        expect(spinner).toBeTruthy();
    }));

    it("should hide spinner when hasReceivedLogs is true", fakeAsync(() => {
        mockRegistry.logService.hasReceivedLogs = true;
        fixture.detectChanges();
        tick();

        const spinner = fixture.nativeElement.querySelector(".log-pane__spinner");
        expect(spinner).toBeFalsy();
    }));

    it("should call navigator.clipboard.writeText when copyLogs is called", fakeAsync(() => {
        fixture.detectChanges();
        const record = makeRecord(LogRecord.Level.INFO, "Test copy", new Date(2026, 3, 14, 14, 2, 11, 450));
        mockRegistry.logService.emit(record);
        tick();

        const clipboardSpy = spyOn(navigator.clipboard, "writeText").and.returnValue(Promise.resolve());
        component.copyLogs();

        expect(clipboardSpy).toHaveBeenCalledTimes(1);
        const arg = clipboardSpy.calls.first().args[0];
        expect(arg).toContain("[INFO]");
        expect(arg).toContain("Test copy");
    }));
});
