import {DestroyRef, Injectable, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";

import {Localization} from "../../common/localization";
import {BulkAction, BulkActionResult, BulkCommandService} from "../server/bulk-command.service";
import {ConfirmModalService} from "../utils/confirm-modal.service";
import {Notification} from "../utils/notification";
import {NotificationService} from "../utils/notification.service";
import {FileSelectionService} from "./file-selection.service";


export interface BulkActionMessages {
    successMsg: (count: number) => string;
    partialMsg: (succeeded: number, failed: number) => string;
}

const PREVIEW_LIMIT = 5;
const NOTIFICATION_DISMISS_MS = 5000;


/**
 * BulkActionDispatcher owns the end-to-end bulk-action flow:
 *   - Concurrency gate (`inProgress` signal) to prevent overlapping dispatches.
 *   - Delegation to BulkCommandService for the HTTP call.
 *   - Success/partial/failure notification formatting.
 *   - Selection preservation on transient failures (so the user can retry).
 *   - Confirm-modal flow for destructive actions (delete local / delete remote).
 *
 * Extracted from TransferTableComponent so the component can focus on view state
 * (filter/segment/pagination) and delegate dispatch concerns.
 */
@Injectable({providedIn: "root"})
export class BulkActionDispatcher {

    private readonly _inProgress = signal<boolean>(false);
    readonly inProgress = this._inProgress.asReadonly();

    private readonly _bulkCommandService = inject(BulkCommandService);
    private readonly _confirmModalService = inject(ConfirmModalService);
    private readonly _notificationService = inject(NotificationService);
    private readonly _fileSelectionService = inject(FileSelectionService);
    private readonly _destroyRef = inject(DestroyRef);

    dispatchQueue(fileNames: string[]): void {
        this._dispatch("queue", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_QUEUED,
            partialMsg: Localization.Bulk.PARTIAL_QUEUED
        });
    }

    dispatchStop(fileNames: string[]): void {
        this._dispatch("stop", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_STOPPED,
            partialMsg: Localization.Bulk.PARTIAL_STOPPED
        });
    }

    dispatchExtract(fileNames: string[]): void {
        this._dispatch("extract", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_EXTRACTED,
            partialMsg: Localization.Bulk.PARTIAL_EXTRACTED
        });
    }

    async confirmAndDispatchDeleteLocal(fileNames: string[], selectedCount: number): Promise<void> {
        const skipCount = selectedCount - fileNames.length;
        const body = Localization.Modal.BULK_DELETE_LOCAL_MESSAGE(fileNames.length)
                     + this._buildPreviewSuffix(fileNames);
        const confirmed = await this._confirmModalService.confirm({
            title: Localization.Modal.BULK_DELETE_LOCAL_TITLE,
            body,
            okBtn: "Delete",
            okBtnClass: "btn btn-outline-danger",
            skipCount: skipCount > 0 ? skipCount : undefined
        });
        if (confirmed) {
            this._dispatch("delete_local", fileNames, {
                successMsg: Localization.Bulk.SUCCESS_DELETED_LOCAL,
                partialMsg: Localization.Bulk.PARTIAL_DELETED_LOCAL
            });
        }
    }

    async confirmAndDispatchDeleteRemote(fileNames: string[], selectedCount: number): Promise<void> {
        const skipCount = selectedCount - fileNames.length;
        const body = Localization.Modal.BULK_DELETE_REMOTE_MESSAGE(fileNames.length)
                     + this._buildPreviewSuffix(fileNames);
        const confirmed = await this._confirmModalService.confirm({
            title: Localization.Modal.BULK_DELETE_REMOTE_TITLE,
            body,
            okBtn: "Delete",
            okBtnClass: "btn btn-danger",
            skipCount: skipCount > 0 ? skipCount : undefined
        });
        if (confirmed) {
            this._dispatch("delete_remote", fileNames, {
                successMsg: Localization.Bulk.SUCCESS_DELETED_REMOTE,
                partialMsg: Localization.Bulk.PARTIAL_DELETED_REMOTE
            });
        }
    }

    private _dispatch(
        action: BulkAction,
        fileNames: string[],
        messages: BulkActionMessages
    ): void {
        // Concurrency gate: ignore subsequent dispatches until the current one resolves.
        if (this._inProgress()) {
            return;
        }
        this._inProgress.set(true);
        this._fileSelectionService.beginOperation();

        this._bulkCommandService.executeBulkAction(action, fileNames).pipe(
            takeUntilDestroyed(this._destroyRef)
        ).subscribe({
            next: (result: BulkActionResult) => {
                this._inProgress.set(false);
                this._fileSelectionService.endOperation();
                this._handleBulkResult(result, messages);

                // Preserve selection on transient failures so the user can retry without
                // re-selecting. BulkCommandService emits all failures through `next`
                // (never `error`), so this is the single place that decides retention.
                const shouldPreserveSelection = !result.success && result.isTransientFailure;
                if (!shouldPreserveSelection) {
                    this._fileSelectionService.clearSelection();
                }
            }
            // No `error` callback: BulkCommandService catches HttpErrorResponse and
            // surfaces it via `next(BulkActionResult(success=false, errorStatus=...))`.
        });
    }

    private _handleBulkResult(result: BulkActionResult, messages: BulkActionMessages): void {
        if (!result.success) {
            const raw = result.errorMessage || "Unknown error";
            const text = result.isTransientFailure
                ? Localization.Bulk.ERROR_TRANSIENT(`Request failed: ${raw}.`)
                : Localization.Bulk.ERROR(raw);
            this._showNotification(Notification.Level.DANGER, text);
            return;
        }
        if (result.allSucceeded && result.response) {
            this._showNotification(
                Notification.Level.SUCCESS,
                messages.successMsg(result.response.summary.succeeded)
            );
        } else if (result.response) {
            this._showNotification(
                Notification.Level.WARNING,
                messages.partialMsg(result.response.summary.succeeded, result.response.summary.failed)
            );
        }
    }

    private _showNotification(level: Notification.Level, text: string): void {
        const notification = new Notification({level, text, dismissible: true});
        this._notificationService.show(notification);
        if (level === Notification.Level.SUCCESS || level === Notification.Level.WARNING) {
            setTimeout(() => { this._notificationService.hide(notification); }, NOTIFICATION_DISMISS_MS);
        }
    }

    private _buildPreviewSuffix(fileNames: string[]): string {
        if (fileNames.length === 0) { return ""; }
        if (fileNames.length <= PREVIEW_LIMIT) {
            return "\n\n" + fileNames.join("\n");
        }
        return "\n\n" + fileNames.slice(0, PREVIEW_LIMIT).join("\n")
               + "\n… and " + (fileNames.length - PREVIEW_LIMIT) + " more";
    }
}
