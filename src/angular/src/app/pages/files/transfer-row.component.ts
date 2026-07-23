import {Component, Input, ChangeDetectionStrategy, EventEmitter, Output, inject, computed, HostBinding} from "@angular/core";
import {DecimalPipe} from "@angular/common";

import {FileSizePipe} from "../../common/file-size.pipe";
import {EtaPipe} from "../../common/eta.pipe";
import {ViewFile} from "../../services/files/view-file";
import {ClickStopPropagationDirective} from "../../common/click-stop-propagation.directive";
import {FileSelectionService} from "../../services/files/file-selection.service";


@Component({
    selector: "app-transfer-row",
    templateUrl: "./transfer-row.component.html",
    styleUrls: ["./transfer-row.component.scss"],
    standalone: true,
    imports: [FileSizePipe, EtaPipe, DecimalPipe, ClickStopPropagationDirective],
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class TransferRowComponent {

    public readonly ViewFile = ViewFile;
    @Input({ required: true }) file!: ViewFile;

    private selectionService = inject(FileSelectionService);

    readonly isSelected = computed(() => {
        const selected = this.selectionService.selectedFiles();
        return this.file?.name != null ? selected.has(this.file.name) : false;
    });

    @Output() checkboxToggle = new EventEmitter<{file: ViewFile, shiftKey: boolean}>();

    @HostBinding("attr.role") readonly hostRole = "row";

    @HostBinding("class.row-selected")
    get isRowSelected(): boolean { return this.isSelected(); }

    @HostBinding("attr.aria-label")
    get hostAriaLabel(): string {
        const base = `${this.file?.name ?? ""}, ${(this.badgeLabel || "").toLowerCase()}`;
        return this.isSelected() ? `${base}, selected` : base;
    }

    onCheckboxClick(event: MouseEvent): void {
        event.stopPropagation();
        this.checkboxToggle.emit({file: this.file, shiftKey: event.shiftKey});
    }

    private static readonly BADGE_LABELS: Record<ViewFile.Status, string> = {
        [ViewFile.Status.DOWNLOADING]: "Syncing",
        [ViewFile.Status.QUEUED]: "Queued",
        [ViewFile.Status.DOWNLOADED]: "Synced",
        [ViewFile.Status.STOPPED]: "Failed",
        [ViewFile.Status.EXTRACTING]: "Extracting",
        [ViewFile.Status.EXTRACTED]: "Extracted",
        [ViewFile.Status.DEFAULT]: "\u2014",
        [ViewFile.Status.DELETED]: "Deleted",
    };

    private static readonly BADGE_CLASSES: Record<ViewFile.Status, string> = {
        [ViewFile.Status.DOWNLOADING]: "badge bg-warning text-dark",
        [ViewFile.Status.QUEUED]: "badge bg-secondary",
        [ViewFile.Status.DOWNLOADED]: "badge bg-success",
        [ViewFile.Status.STOPPED]: "badge bg-danger",
        [ViewFile.Status.EXTRACTING]: "badge bg-info",
        [ViewFile.Status.EXTRACTED]: "badge bg-info",
        [ViewFile.Status.DEFAULT]: "badge bg-dark",
        [ViewFile.Status.DELETED]: "badge bg-danger",
    };

    /**
     * A DELETED file that still exists remotely but has no local content is a
     * "skipped" file: SeedSyncarr is intentionally not re-downloading it (it
     * was synced and then moved/removed locally, e.g. by a Sonarr/Radarr
     * import). This state silently blocked a re-grabbed release in the
     * 2026-07-23 incident, so it gets a distinct warning badge instead of
     * being indistinguishable from a plain deleted file.
     */
    get isSkippedRemote(): boolean {
        return this.file.status === ViewFile.Status.DELETED &&
            this.file.remoteSize != null && this.file.remoteSize > 0 &&
            (this.file.localSize == null || this.file.localSize === 0);
    }

    get badgeLabel(): string {
        if (this.isSkippedRemote) { return "Skipped (remote)"; }
        const status = this.file.status ?? ViewFile.Status.DEFAULT;
        return TransferRowComponent.BADGE_LABELS[status] ?? "\u2014";
    }

    get badgeClass(): string {
        if (this.isSkippedRemote) { return "badge bg-warning text-dark"; }
        const status = this.file.status ?? ViewFile.Status.DEFAULT;
        return TransferRowComponent.BADGE_CLASSES[status] ?? "badge bg-dark";
    }

    get isDownloading(): boolean {
        return this.file.status === ViewFile.Status.DOWNLOADING;
    }
}
