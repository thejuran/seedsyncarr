import {Component} from "@angular/core";

import {FileOptionsComponent} from "./file-options.component";
import {FileListComponent} from "./file-list.component";
import {StatsStripComponent} from "./stats-strip.component";

@Component({
    selector: "app-files-page",
    templateUrl: "./files-page.component.html",
    styleUrls: ["./files-page.component.scss"],
    standalone: true,
    imports: [StatsStripComponent, FileOptionsComponent, FileListComponent]
})
export class FilesPageComponent {
}
