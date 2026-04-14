import {
    ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef,
    ElementRef, inject, OnInit, ViewChild
} from "@angular/core";
import {NgClass} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {debounceTime, distinctUntilChanged, scan} from "rxjs/operators";
import {Subject} from "rxjs";

import {StreamServiceRegistry} from "../../services/base/stream-service.registry";
import {LogService} from "../../services/logs/log.service";
import {LogRecord} from "../../services/logs/log-record";
import {ConnectedService} from "../../services/utils/connected.service";

export type LevelFilter = 'ALL' | 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';

const MAX_LOG_ENTRIES = 5000;

@Component({
    selector: "app-logs-page",
    templateUrl: "./logs-page.component.html",
    styleUrls: ["./logs-page.component.scss"],
    standalone: true,
    imports: [NgClass, FormsModule],
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class LogsPageComponent implements OnInit {
    public readonly LogRecord = LogRecord;

    allLogs: LogRecord[] = [];
    activeLevel: LevelFilter = 'ALL';
    searchInput = '';
    searchQuery = '';
    autoScroll = true;
    isConnected = false;
    lastUpdated: Date | null = null;

    private searchQuery$ = new Subject<string>();
    private destroyRef = inject(DestroyRef);

    @ViewChild('terminalViewport') terminalViewport!: ElementRef<HTMLDivElement>;

    private logService: LogService;
    private connectedService: ConnectedService;

    constructor(
        streamRegistry: StreamServiceRegistry,
        private cdr: ChangeDetectorRef
    ) {
        this.logService = streamRegistry.logService;
        this.connectedService = streamRegistry.connectedService;
    }

    ngOnInit(): void {
        // Accumulate log entries via scan (same pattern as DashboardLogPaneComponent)
        this.logService.logs
            .pipe(
                takeUntilDestroyed(this.destroyRef),
                scan((acc: LogRecord[], record) => {
                    const next = [...acc, record];
                    return next.length > MAX_LOG_ENTRIES ? next.slice(-MAX_LOG_ENTRIES) : next;
                }, []),
                debounceTime(0)
            )
            .subscribe(entries => {
                this.allLogs = entries;
                this.lastUpdated = new Date();
                this.cdr.markForCheck();
                if (this.autoScroll) {
                    setTimeout(() => this.scrollToBottom(), 0);
                }
            });

        // Connection status
        this.connectedService.connected
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(connected => {
                this.isConnected = connected;
                this.cdr.markForCheck();
            });

        // Debounced search
        this.searchQuery$
            .pipe(
                takeUntilDestroyed(this.destroyRef),
                debounceTime(200),
                distinctUntilChanged()
            )
            .subscribe(q => {
                this.searchQuery = q;
                this.cdr.markForCheck();
            });
    }

    get filteredLogs(): LogRecord[] {
        let result = this.allLogs;

        if (this.activeLevel !== 'ALL') {
            result = result.filter(r => this.matchesLevel(r.level));
        }

        if (this.searchQuery.trim()) {
            try {
                const rx = new RegExp(this.searchQuery, 'i');
                result = result.filter(r => rx.test(r.message) || rx.test(r.loggerName));
            } catch {
                // Invalid regex — show all results
            }
        }

        return result;
    }

    setLevel(level: LevelFilter): void {
        this.activeLevel = level;
        this.cdr.markForCheck();
    }

    onSearchInput(value: string): void {
        this.searchQuery$.next(value);
    }

    toggleAutoScroll(): void {
        this.autoScroll = !this.autoScroll;
        if (this.autoScroll) {
            this.scrollToBottom();
        }
        this.cdr.markForCheck();
    }

    onTerminalScroll(event: Event): void {
        const el = event.target as HTMLElement;
        const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 10;
        if (!isAtBottom && this.autoScroll) {
            this.autoScroll = false;
            this.cdr.markForCheck();
        }
    }

    clearLogs(): void {
        this.allLogs = [];
        this.searchInput = '';
        this.searchQuery = '';
        this.cdr.markForCheck();
    }

    exportLogs(): void {
        const lines = this.filteredLogs.map(e => {
            const d = e.time;
            const date = `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
            const time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
            return `${date} ${time} - ${e.level} - ${e.loggerName} - ${e.message}`;
        }).join('\n');

        const blob = new Blob([lines], {type: 'text/plain'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `seedsyncarr-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.log`;
        a.click();
        URL.revokeObjectURL(url);
    }

    formatTimestamp(date: Date): string {
        const hh = String(date.getHours()).padStart(2, '0');
        const mm = String(date.getMinutes()).padStart(2, '0');
        const ss = String(date.getSeconds()).padStart(2, '0');
        const ms = String(date.getMilliseconds()).padStart(3, '0');
        return `${hh}:${mm}:${ss}.${ms}`;
    }

    formatLastUpdated(): string {
        if (!this.lastUpdated) return '--:--:-- --';
        const h = this.lastUpdated.getHours();
        const ampm = h >= 12 ? 'PM' : 'AM';
        const h12 = h % 12 || 12;
        const mm = String(this.lastUpdated.getMinutes()).padStart(2, '0');
        const ss = String(this.lastUpdated.getSeconds()).padStart(2, '0');
        return `${h12}:${mm}:${ss} ${ampm}`;
    }

    levelLabel(level: LogRecord.Level): string {
        switch (level) {
            case LogRecord.Level.DEBUG:    return 'DEBUG';
            case LogRecord.Level.INFO:     return 'INFO';
            case LogRecord.Level.WARNING:  return 'WARN';
            case LogRecord.Level.ERROR:    return 'ERROR';
            case LogRecord.Level.CRITICAL: return 'CRIT';
            default:                       return level;
        }
    }

    levelRowClass(level: LogRecord.Level): string {
        switch (level) {
            case LogRecord.Level.ERROR:
            case LogRecord.Level.CRITICAL: return 'log-row--error';
            case LogRecord.Level.WARNING:  return 'log-row--warn';
            default:                       return '';
        }
    }

    levelClass(level: LogRecord.Level): string {
        switch (level) {
            case LogRecord.Level.INFO:     return 'log-level--info';
            case LogRecord.Level.WARNING:  return 'log-level--warn';
            case LogRecord.Level.DEBUG:    return 'log-level--debug';
            case LogRecord.Level.ERROR:
            case LogRecord.Level.CRITICAL: return 'log-level--error-badge';
            default:                       return '';
        }
    }

    private matchesLevel(level: LogRecord.Level): boolean {
        switch (this.activeLevel) {
            case 'INFO':  return level === LogRecord.Level.INFO;
            case 'WARN':  return level === LogRecord.Level.WARNING;
            case 'ERROR': return level === LogRecord.Level.ERROR || level === LogRecord.Level.CRITICAL;
            case 'DEBUG': return level === LogRecord.Level.DEBUG;
            default:      return true;
        }
    }

    private scrollToBottom(): void {
        const el = this.terminalViewport?.nativeElement;
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    }
}
