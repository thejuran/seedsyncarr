import {Component} from "@angular/core";

import {FileOptionsComponent} from "./file-options.component";
import {FileListComponent} from "./file-list.component";

@Component({
    selector: "app-files-page",
    templateUrl: "./files-page.component.html",
    standalone: true,
    imports: [FileOptionsComponent, FileListComponent]
})
export class FilesPageComponent {
}
