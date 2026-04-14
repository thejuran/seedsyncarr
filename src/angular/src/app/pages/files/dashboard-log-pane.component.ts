import {Component, ChangeDetectionStrategy, ChangeDetectorRef, DestroyRef, inject, OnInit} from "@angular/core";
import {DatePipe, NgClass} from "@angular/common";
import {RouterLink} from "@angular/router";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {debounceTime, scan} from "rxjs/operators";

import {StreamServiceRegistry} from "../../services/base/stream-service.registry";
import {LogService} from "../../services/logs/log.service";
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
    readonly logService: LogService;

    private destroyRef = inject(DestroyRef);

    constructor(
        streamRegistry: StreamServiceRegistry,
        private cdr: ChangeDetectorRef
    ) {
        this.logService = streamRegistry.logService;
    }

    ngOnInit(): void {
        this.logService.logs
            .pipe(
                takeUntilDestroyed(this.destroyRef),
                scan((acc: LogRecord[], record) => {
                    const next = [...acc, record];
                    return next.length > MAX_PANE_ENTRIES ? next.slice(-MAX_PANE_ENTRIES) : next;
                }, []),
                debounceTime(0)
            )
            .subscribe(entries => {
                this.entries = entries;
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

        void navigator.clipboard.writeText(text).catch(err => {
            console.warn("Failed to copy logs to clipboard:", err);
        });
    }
}
