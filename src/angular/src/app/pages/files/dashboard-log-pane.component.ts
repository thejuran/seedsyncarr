import {Component, ChangeDetectionStrategy, ChangeDetectorRef, DestroyRef, inject, OnInit} from "@angular/core";
import {DatePipe, NgClass} from "@angular/common";
import {RouterLink} from "@angular/router";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";

import {StreamServiceRegistry} from "../../services/base/stream-service.registry";
import {LogRecord} from "../../services/logs/log-record";

const MAX_PANE_ENTRIES = 50;

@Component({
    selector: "app-dashboard-log-pane",
    templateUrl: "./dashboard-log-pane.component.html",
    styleUrls: ["./dashboard-log-pane.component.scss"],
    standalone: true,
    imports: [DatePipe, NgClass, RouterLink],
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardLogPaneComponent implements OnInit {
    public readonly LogRecord = LogRecord;
    entries: LogRecord[] = [];

    private destroyRef = inject(DestroyRef);

    constructor(
        public streamRegistry: StreamServiceRegistry,
        private cdr: ChangeDetectorRef
    ) {}

    ngOnInit(): void {
        this.streamRegistry.logService.logs
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(record => {
                this.entries.push(record);
                if (this.entries.length > MAX_PANE_ENTRIES) {
                    this.entries.shift();
                }
                this.cdr.markForCheck();
            });
    }

    levelBadge(level: LogRecord.Level): string {
        switch (level) {
            case LogRecord.Level.DEBUG:    return "[DEBUG]";
            case LogRecord.Level.INFO:     return "[INFO]";
            case LogRecord.Level.WARNING:  return "[WARN]";
            case LogRecord.Level.ERROR:    return "[ERR!]";
            case LogRecord.Level.CRITICAL: return "[CRIT]";
            default:                       return `[${level}]`;
        }
    }

    copyLogs(): void {
        const text = this.entries.map(e => {
            const d = e.time;
            const hh = String(d.getHours()).padStart(2, "0");
            const mm = String(d.getMinutes()).padStart(2, "0");
            const ss = String(d.getSeconds()).padStart(2, "0");
            const ms = String(d.getMilliseconds()).padStart(3, "0");
            return `${hh}:${mm}:${ss}.${ms} ${this.levelBadge(e.level)} ${e.message}`;
        }).join("\n");

        try {
            navigator.clipboard.writeText(text);
        } catch (err) {
            console.warn("Failed to copy logs to clipboard:", err);
        }
    }
}
