import {Component, Input, ChangeDetectionStrategy} from "@angular/core";

import {FileSizePipe} from "../../common/file-size.pipe";
import {EtaPipe} from "../../common/eta.pipe";
import {ViewFile} from "../../services/files/view-file";


@Component({
    selector: "app-transfer-row",
    templateUrl: "./transfer-row.component.html",
    styleUrls: ["./transfer-row.component.scss"],
    standalone: true,
    imports: [FileSizePipe, EtaPipe],
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class TransferRowComponent {

    @Input({ required: true }) file!: ViewFile;

    private static readonly BADGE_LABELS: Record<string, string> = {
        [ViewFile.Status.DOWNLOADING]: "Syncing",
        [ViewFile.Status.QUEUED]: "Queued",
        [ViewFile.Status.DOWNLOADED]: "Synced",
        [ViewFile.Status.STOPPED]: "Failed",
        [ViewFile.Status.EXTRACTING]: "Extracting",
        [ViewFile.Status.EXTRACTED]: "Extracted",
        [ViewFile.Status.DEFAULT]: "\u2014",
        [ViewFile.Status.DELETED]: "Deleted",
    };

    private static readonly BADGE_CLASSES: Record<string, string> = {
        [ViewFile.Status.DOWNLOADING]: "badge bg-warning text-dark",
        [ViewFile.Status.QUEUED]: "badge bg-secondary",
        [ViewFile.Status.DOWNLOADED]: "badge bg-success",
        [ViewFile.Status.STOPPED]: "badge bg-danger",
        [ViewFile.Status.EXTRACTING]: "badge bg-info",
        [ViewFile.Status.EXTRACTED]: "badge bg-info",
        [ViewFile.Status.DEFAULT]: "badge bg-dark",
        [ViewFile.Status.DELETED]: "badge bg-danger",
    };

    get badgeLabel(): string {
        return TransferRowComponent.BADGE_LABELS[this.file.status ?? ""] ?? "\u2014";
    }

    get badgeClass(): string {
        return TransferRowComponent.BADGE_CLASSES[this.file.status ?? ""] ?? "badge bg-dark";
    }

    get isDownloading(): boolean {
        return this.file.status === ViewFile.Status.DOWNLOADING;
    }
}
