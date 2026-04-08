import {
    Component, Input, Output, ChangeDetectionStrategy,
    EventEmitter, OnChanges, SimpleChanges, ViewChild, ElementRef,
    inject, computed, AfterViewInit, HostBinding
} from "@angular/core";
import { DatePipe } from "@angular/common";

import {CapitalizePipe} from "../../common/capitalize.pipe";
import {EtaPipe} from "../../common/eta.pipe";
import {FileSizePipe} from "../../common/file-size.pipe";
import {ClickStopPropagationDirective} from "../../common/click-stop-propagation.directive";
import {ViewFile} from "../../services/files/view-file";
import {FileAction} from "../../services/files/file-action";
import {Localization} from "../../common/localization";
import {ViewFileOptions} from "../../services/files/view-file-options";
import {ConfirmModalService} from "../../services/utils/confirm-modal.service";
import {FileSelectionService} from "../../services/files/file-selection.service";

/**
 * FileComponent displays a single file row in the file list.
 *
 * Session 16: Signal-Based Selection Architecture
 * - Injects FileSelectionService directly instead of receiving selection via @Input
 * - Uses computed() signal to derive selection state from the service
 * - This eliminates cascading checkbox updates on select-all:
 *   - Old: Parent emits new Set → ALL components re-render via @Input change
 *   - New: Service signal updates → Only THIS component's computed() re-evaluates
 * - Angular's signal change detection only marks components whose computed values changed
 */
@Component({
    selector: "app-file",
    providers: [],
    templateUrl: "./file.component.html",
    styleUrls: ["./file.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
    imports: [DatePipe, CapitalizePipe, EtaPipe, FileSizePipe, ClickStopPropagationDirective]
})
export class FileComponent implements OnChanges, AfterViewInit {
    // Badge class lookup — avoids string concatenation in template for defense-in-depth
    private static readonly BADGE_CLASSES: Record<string, string> = {
        [ViewFile.Status.DEFAULT]: "status-badge badge-default",
        [ViewFile.Status.QUEUED]: "status-badge badge-queued",
        [ViewFile.Status.DOWNLOADING]: "status-badge badge-downloading",
        [ViewFile.Status.DOWNLOADED]: "status-badge badge-downloaded",
        [ViewFile.Status.STOPPED]: "status-badge badge-stopped",
        [ViewFile.Status.DELETED]: "status-badge badge-deleted",
        [ViewFile.Status.EXTRACTING]: "status-badge badge-extracting",
        [ViewFile.Status.EXTRACTED]: "status-badge badge-extracted",
    };

    get statusBadgeClass(): string {
        const status = this.file?.status;
        return (status != null ? FileComponent.BADGE_CLASSES[status] : undefined) ?? "status-badge badge-default";
    }

    // Inject FileSelectionService for signal-based selection
    private selectionService = inject(FileSelectionService);

    // Make ViewFile optionType accessible from template
    ViewFile = ViewFile;

    // Entire div element
    @ViewChild("fileElement", {static: false}) fileElement!: ElementRef<HTMLDivElement>;

    @Input() file!: ViewFile;
    @Input() options!: ViewFileOptions;
    // Note: @Input() bulkSelected removed - now computed from FileSelectionService signal

    @Output() queueEvent = new EventEmitter<ViewFile>();
    @Output() stopEvent = new EventEmitter<ViewFile>();
    @Output() extractEvent = new EventEmitter<ViewFile>();
    @Output() deleteLocalEvent = new EventEmitter<ViewFile>();
    @Output() deleteRemoteEvent = new EventEmitter<ViewFile>();
    @Output() checkboxToggle = new EventEmitter<{file: ViewFile, shiftKey: boolean}>();

    // Indicates an active action on-going
    activeAction: FileAction | null = null;

    // Track whether view has been initialized (ViewChild availability)
    private viewInitialized = false;

    /**
     * Computed signal for selection state - fine-grained reactivity.
     * Only re-evaluates when THIS file's selection state changes.
     *
     * Why this fixes cascading checkboxes:
     * - Old: @Input bound to pipe output → every checkbox re-renders when Set changes
     * - New: computed() reads signal → Angular only marks dirty if computed value changed
     *
     * The key insight: when select-all runs, the selectedFiles signal updates once,
     * and each FileComponent's computed() independently checks "am I selected?".
     * Angular's signal-based change detection batches all DOM updates together.
     */
    readonly isSelected = computed(() => {
        // Access the selection signal - this creates a dependency
        const selected = this.selectionService.selectedFiles();
        // Check if this file is in the selection
        // Note: this.file may be undefined during initial render
        return this.file?.name != null ? selected.has(this.file.name) : false;
    });

    /**
     * Per-class @HostBindings for status-based classes on the host element.
     * Enables colored left border and glow animation via CSS targeting
     * :host.status-* and :host.downloading-active.
     *
     * Uses individual class bindings instead of @HostBinding('class') to
     * avoid overwriting parent-applied classes like [class.even-row].
     */
    @HostBinding("class.status-default") get isStatusDefault(): boolean { return this.file?.status === ViewFile.Status.DEFAULT; }
    @HostBinding("class.status-queued") get isStatusQueued(): boolean { return this.file?.status === ViewFile.Status.QUEUED; }
    @HostBinding("class.status-downloading") get isStatusDownloading(): boolean {
        return this.file?.status === ViewFile.Status.DOWNLOADING;
    }
    @HostBinding("class.status-downloaded") get isStatusDownloaded(): boolean { return this.file?.status === ViewFile.Status.DOWNLOADED; }
    @HostBinding("class.status-stopped") get isStatusStopped(): boolean { return this.file?.status === ViewFile.Status.STOPPED; }
    @HostBinding("class.status-deleted") get isStatusDeleted(): boolean { return this.file?.status === ViewFile.Status.DELETED; }
    @HostBinding("class.status-extracting") get isStatusExtracting(): boolean { return this.file?.status === ViewFile.Status.EXTRACTING; }
    @HostBinding("class.status-extracted") get isStatusExtracted(): boolean { return this.file?.status === ViewFile.Status.EXTRACTED; }
    @HostBinding("class.downloading-active") get isDownloadingActive(): boolean {
        return this.file?.status === ViewFile.Status.DOWNLOADING;
    }

    constructor(private confirmModal: ConfirmModalService) {}

    ngAfterViewInit(): void {
        this.viewInitialized = true;
    }

    ngOnChanges(changes: SimpleChanges): void {
        // Check for status changes
        const oldFile: ViewFile = changes.file?.previousValue;
        const newFile: ViewFile = changes.file?.currentValue;
        if (oldFile != null && newFile != null && oldFile.status !== newFile.status) {
            // Reset any active action
            this.activeAction = null;

            // Scroll into view if this file is selected and not already in viewport
            // Only access ViewChild after view has been initialized
            // Use the computed signal value instead of ViewFile.isSelected to ensure consistency
            if (this.viewInitialized && this.isSelected() && this.fileElement?.nativeElement &&
                !FileComponent.isElementInViewport(this.fileElement.nativeElement)) {
                this.fileElement.nativeElement.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        }
    }

    showDeleteConfirmation(title: string, message: string, callback: () => void): void {
        this.confirmModal.confirm({
            title: title,
            body: message,
            okBtn: "Delete",
            okBtnClass: "btn btn-danger",
            cancelBtn: "Cancel",
            cancelBtnClass: "btn btn-secondary"
        }).then((confirmed) => {
            if (confirmed) {
                callback();
            }
        });
    }

    isQueueable(): boolean {
        return this.activeAction == null && (this.file?.isQueueable ?? false);
    }

    isStoppable(): boolean {
        return this.activeAction == null && (this.file?.isStoppable ?? false);
    }

    isExtractable(): boolean {
        return this.activeAction == null && (this.file?.isExtractable ?? false) && (this.file?.isArchive ?? false);
    }

    isLocallyDeletable(): boolean {
        return this.activeAction == null && (this.file?.isLocallyDeletable ?? false);
    }

    isRemotelyDeletable(): boolean {
        return this.activeAction == null && (this.file?.isRemotelyDeletable ?? false);
    }

    onCheckboxClick(event: MouseEvent): void {
        event.stopPropagation();
        this.checkboxToggle.emit({file: this.file, shiftKey: event.shiftKey});
    }

    onQueue(file: ViewFile): void {
        if (!this.isQueueable()) {
            return;
        }
        this.activeAction = FileAction.QUEUE;
        // Pass to parent component
        this.queueEvent.emit(file);
    }

    onStop(file: ViewFile): void {
        if (!this.isStoppable()) {
            return;
        }
        this.activeAction = FileAction.STOP;
        // Pass to parent component
        this.stopEvent.emit(file);
    }

    onExtract(file: ViewFile): void {
        if (!this.isExtractable()) {
            return;
        }
        this.activeAction = FileAction.EXTRACT;
        // Pass to parent component
        this.extractEvent.emit(file);
    }

    onDeleteLocal(file: ViewFile): void {
        if (!this.isLocallyDeletable()) {
            return;
        }
        this.showDeleteConfirmation(
            Localization.Modal.DELETE_LOCAL_TITLE,
            Localization.Modal.DELETE_LOCAL_MESSAGE(file.name!),
            () => {
                this.activeAction = FileAction.DELETE_LOCAL;
                // Pass to parent component
                this.deleteLocalEvent.emit(file);
            }
        );
    }

    onDeleteRemote(file: ViewFile): void {
        if (!this.isRemotelyDeletable()) {
            return;
        }
        this.showDeleteConfirmation(
            Localization.Modal.DELETE_REMOTE_TITLE,
            Localization.Modal.DELETE_REMOTE_MESSAGE(file.name!),
            () => {
                this.activeAction = FileAction.DELETE_REMOTE;
                // Pass to parent component
                this.deleteRemoteEvent.emit(file);
            }
        );
    }

    // Source: https://stackoverflow.com/a/7557433
    private static isElementInViewport(el: HTMLElement): boolean {
        const rect = el.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && /* or $(window).height() */
            rect.right <= (window.innerWidth || document.documentElement.clientWidth) /* or $(window).width() */
        );
    }
}

// Re-export for backward compatibility with existing imports
export {FileAction} from "../../services/files/file-action";
