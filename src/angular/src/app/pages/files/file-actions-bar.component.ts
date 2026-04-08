import {Component, Input, Output, EventEmitter, ChangeDetectionStrategy} from "@angular/core";
import {ViewFile} from "../../services/files/view-file";

/**
 * Actions bar for a single selected file.
 * Displayed outside the virtual scroll viewport for fixed row heights.
 */
@Component({
    selector: "app-file-actions-bar",
    templateUrl: "./file-actions-bar.component.html",
    styleUrls: ["./file-actions-bar.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,

})
export class FileActionsBarComponent {
    @Input() file: ViewFile | null = null;
    @Input() activeAction: string | null = null;

    @Output() queueEvent = new EventEmitter<ViewFile>();
    @Output() stopEvent = new EventEmitter<ViewFile>();
    @Output() extractEvent = new EventEmitter<ViewFile>();
    @Output() deleteLocalEvent = new EventEmitter<ViewFile>();
    @Output() deleteRemoteEvent = new EventEmitter<ViewFile>();

    isQueueable(): boolean {
        return this.file != null && !!this.file.isQueueable;
    }

    isStoppable(): boolean {
        return this.file != null && !!this.file.isStoppable;
    }

    isExtractable(): boolean {
        return this.file != null && !!this.file.isExtractable && !!this.file.isArchive;
    }

    isLocallyDeletable(): boolean {
        return this.file != null && !!this.file.isLocallyDeletable;
    }

    isRemotelyDeletable(): boolean {
        return this.file != null && !!this.file.isRemotelyDeletable;
    }

    onQueue(): void {
        if (this.file && this.isQueueable()) {
            this.queueEvent.emit(this.file);
        }
    }

    onStop(): void {
        if (this.file && this.isStoppable()) {
            this.stopEvent.emit(this.file);
        }
    }

    onExtract(): void {
        if (this.file && this.isExtractable()) {
            this.extractEvent.emit(this.file);
        }
    }

    onDeleteLocal(): void {
        if (this.file && this.isLocallyDeletable()) {
            this.deleteLocalEvent.emit(this.file);
        }
    }

    onDeleteRemote(): void {
        if (this.file && this.isRemotelyDeletable()) {
            this.deleteRemoteEvent.emit(this.file);
        }
    }
}
