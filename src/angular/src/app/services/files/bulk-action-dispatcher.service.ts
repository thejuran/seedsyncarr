import {DestroyRef, Injectable, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";

import {Localization} from "../../common/localization";
import {
    BulkAction, BulkActionOptions, BulkActionResult, BulkCommandService
} from "../server/bulk-command.service";
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
// Per-file error code the backend returns when a queue request needs the
// user's explicit confirmation because download completion is unverified.
const ERROR_CODE_NEEDS_CONFIRMATION = 428;

interface DispatchOptions {
    // Called after the result is handled and the concurrency gate is released.
    onResult?: (result: BulkActionResult) => void;
    // Forwarded to BulkCommandService for this single request.
    requestOptions?: BulkActionOptions;
    // Suppress the partial-failure toast when every failure needs confirmation
    // (the confirm modal is shown instead).
    quietOnConfirmationOnly?: boolean;
}


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
        this._dispatch("queue", fileNames, BulkActionDispatcher.QUEUE_MESSAGES, {
            quietOnConfirmationOnly: true,
            onResult: (result) => {
                // The confirm flow handles its own outcome; nothing to await here.
                void this._offerReleaseForUnverified(result);
            }
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

    private static readonly QUEUE_MESSAGES: BulkActionMessages = {
        successMsg: Localization.Bulk.SUCCESS_QUEUED,
        partialMsg: Localization.Bulk.PARTIAL_QUEUED
    };

    /**
     * Files whose queue request failed only because download completion could
     * not be verified get a single explicit confirmation. On OK they are
     * re-queued once with releaseUnverified; the approval is not remembered,
     * and the re-queue never prompts again.
     */
    private async _offerReleaseForUnverified(result: BulkActionResult): Promise<void> {
        const files = BulkActionDispatcher._filesNeedingConfirmation(result);
        if (files.length === 0) {
            return;
        }
        const confirmed = await this._confirmModalService.confirm({
            title: Localization.Modal.RELEASE_UNVERIFIED_TITLE,
            body: Localization.Modal.RELEASE_UNVERIFIED_MESSAGE + this._buildPreviewSuffix(files),
            okBtn: "Release",
            okBtnClass: "btn btn-outline-danger"
        });
        if (confirmed) {
            this._dispatch("queue", files, BulkActionDispatcher.QUEUE_MESSAGES, {
                requestOptions: {releaseUnverified: true}
            });
        }
    }

    private static _filesNeedingConfirmation(result: BulkActionResult): string[] {
        return (result.response?.results ?? [])
            .filter(r => !r.success && r.error_code === ERROR_CODE_NEEDS_CONFIRMATION)
            .map(r => r.file);
    }

    private _dispatch(
        action: BulkAction,
        fileNames: string[],
        messages: BulkActionMessages,
        options: DispatchOptions = {}
    ): void {
        // Concurrency gate: ignore subsequent dispatches until the current one resolves.
        if (this._inProgress()) {
            return;
        }
        this._inProgress.set(true);
        this._fileSelectionService.beginOperation();

        const request$ = options.requestOptions
            ? this._bulkCommandService.executeBulkAction(action, fileNames, options.requestOptions)
            : this._bulkCommandService.executeBulkAction(action, fileNames);
        request$.pipe(
            takeUntilDestroyed(this._destroyRef)
        ).subscribe({
            next: (result: BulkActionResult) => {
                this._inProgress.set(false);
                this._fileSelectionService.endOperation();
                this._handleBulkResult(result, messages, options.quietOnConfirmationOnly ?? false);

                // Preserve selection on transient failures so the user can retry without
                // re-selecting. BulkCommandService emits all failures through `next`
                // (never `error`), so this is the single place that decides retention.
                const shouldPreserveSelection = !result.success && result.isTransientFailure;
                if (!shouldPreserveSelection) {
                    this._fileSelectionService.clearSelection();
                }

                options.onResult?.(result);
            }
            // No `error` callback: BulkCommandService catches HttpErrorResponse and
            // surfaces it via `next(BulkActionResult(success=false, errorStatus=...))`.
        });
    }

    private _handleBulkResult(
        result: BulkActionResult,
        messages: BulkActionMessages,
        quietOnConfirmationOnly: boolean
    ): void {
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
            const failures = result.response.results.filter(r => !r.success);
            const onlyNeedsConfirmation = failures.length > 0 &&
                failures.every(r => r.error_code === ERROR_CODE_NEEDS_CONFIRMATION);
            if (quietOnConfirmationOnly && onlyNeedsConfirmation) {
                return;
            }
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
