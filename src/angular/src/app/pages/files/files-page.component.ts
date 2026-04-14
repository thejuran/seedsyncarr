import {Component} from "@angular/core";

import {DashboardLogPaneComponent} from "./dashboard-log-pane.component";
import {StatsStripComponent} from "./stats-strip.component";
import {TransferTableComponent} from "./transfer-table.component";

@Component({
    selector: "app-files-page",
    templateUrl: "./files-page.component.html",
    styleUrls: ["./files-page.component.scss"],
    standalone: true,
    imports: [StatsStripComponent, TransferTableComponent, DashboardLogPaneComponent]
})
export class FilesPageComponent {
}
