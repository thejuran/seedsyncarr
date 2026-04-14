import {Component} from "@angular/core";

import {StatsStripComponent} from "./stats-strip.component";
import {TransferTableComponent} from "./transfer-table.component";

@Component({
    selector: "app-files-page",
    templateUrl: "./files-page.component.html",
    styleUrls: ["./files-page.component.scss"],
    standalone: true,
    imports: [StatsStripComponent, TransferTableComponent]
})
export class FilesPageComponent {
}
