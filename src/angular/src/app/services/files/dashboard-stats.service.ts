import {Injectable, OnDestroy} from "@angular/core";
import {Observable, BehaviorSubject, Subject, combineLatest} from "rxjs";
import {takeUntil} from "rxjs/operators";

import {ViewFileService} from "./view-file.service";
import {ViewFile} from "./view-file";
import {ServerStatusService} from "../server/server-status.service";


/**
 * Stats derived from the file list and server status for the dashboard stats strip.
 */
export interface DashboardStats {
    downloadingCount: number;
    queuedCount: number;
    totalSpeedBps: number;
    peakSpeedBps: number;
    remoteTrackedBytes: number;
    localTrackedBytes: number;
    totalTrackedBytes: number;
    remoteCapacityTotal: number | null;
    remoteCapacityUsed: number | null;
    localCapacityTotal: number | null;
    localCapacityUsed: number | null;
}

const ZERO_STATS: DashboardStats = {
    downloadingCount: 0,
    queuedCount: 0,
    totalSpeedBps: 0,
    peakSpeedBps: 0,
    remoteTrackedBytes: 0,
    localTrackedBytes: 0,
    totalTrackedBytes: 0,
    remoteCapacityTotal: null,
    remoteCapacityUsed: null,
    localCapacityTotal: null,
    localCapacityUsed: null,
};


/**
 * DashboardStatsService derives dashboard metric card data
 * from the existing ViewFileService file list observable and the
 * ServerStatusService status observable via combineLatest.
 * Capacity fields flow from the status stream; counts/speeds flow from the file list.
 */
@Injectable()
export class DashboardStatsService implements OnDestroy {

    private destroy$ = new Subject<void>();
    private _peakSpeed = 0;
    private _stats$ = new BehaviorSubject<DashboardStats>(ZERO_STATS);

    constructor(
        private viewFileService: ViewFileService,
        private serverStatusService: ServerStatusService,
    ) {
        combineLatest([
            this.viewFileService.files,
            this.serverStatusService.status,
        ])
            .pipe(takeUntil(this.destroy$))
            .subscribe(([files, status]) => {
                const downloading = files.filter(f => f.status === ViewFile.Status.DOWNLOADING).toList();
                const queued = files.filter(f => f.status === ViewFile.Status.QUEUED).toList();

                const totalSpeed = downloading.reduce(
                    (sum, f) => sum + (f.downloadingSpeed ?? 0), 0
                );
                // Reset peak only when no files are actively downloading (not on transient stalls)
                if (downloading.size === 0) {
                    this._peakSpeed = 0;
                } else {
                    this._peakSpeed = Math.max(this._peakSpeed, totalSpeed);
                }

                const remoteTrackedBytes = files.reduce(
                    (sum, f) => sum + (f.remoteSize ?? 0), 0
                );
                const localTrackedBytes = files.reduce(
                    (sum, f) => sum + (f.localSize ?? 0), 0
                );

                this._stats$.next({
                    downloadingCount: downloading.size,
                    queuedCount: queued.size,
                    totalSpeedBps: totalSpeed,
                    peakSpeedBps: this._peakSpeed,
                    remoteTrackedBytes,
                    localTrackedBytes,
                    totalTrackedBytes: remoteTrackedBytes + localTrackedBytes,
                    remoteCapacityTotal: status.storage.remoteTotal,
                    remoteCapacityUsed: status.storage.remoteUsed,
                    localCapacityTotal: status.storage.localTotal,
                    localCapacityUsed: status.storage.localUsed,
                });
            });
    }

    get stats$(): Observable<DashboardStats> {
        return this._stats$.asObservable();
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }
}
