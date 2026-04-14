import {Component, ChangeDetectionStrategy} from "@angular/core";
import {AsyncPipe} from "@angular/common";

import {DashboardStatsService} from "../../services/files/dashboard-stats.service";
import {FileSizePipe} from "../../common/file-size.pipe";


@Component({
    selector: "app-stats-strip",
    templateUrl: "./stats-strip.component.html",
    styleUrls: ["./stats-strip.component.scss"],
    standalone: true,
    imports: [AsyncPipe, FileSizePipe],
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class StatsStripComponent {
    stats$ = this.dashboardStatsService.stats$;

    constructor(private dashboardStatsService: DashboardStatsService) {}
}
