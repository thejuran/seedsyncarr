import {Injectable} from "@angular/core";
import {HttpClient, HttpErrorResponse} from "@angular/common/http";
import {Observable} from "rxjs";
import {shareReplay} from "rxjs/operators";

import {LoggerService} from "../utils/logger.service";

/**
 * Bulk action types supported by the API.
 */
export type BulkAction = "queue" | "stop" | "extract" | "delete_local" | "delete_remote";

/**
 * Result for a single file in a bulk operation.
 */
export interface BulkFileResult {
    file: string;
    success: boolean;
    error?: string;
    error_code?: number;
}

/**
 * Summary of a bulk operation.
 */
export interface BulkSummary {
    total: number;
    succeeded: number;
    failed: number;
}

/**
 * Complete response from bulk action endpoint.
 */
export interface BulkActionResponse {
    results: BulkFileResult[];
    summary: BulkSummary;
}

/**
 * Error response from bulk action endpoint.
 */
export interface BulkErrorResponse {
    error: string;
}

/**
 * Result wrapper for bulk action execution.
 */
export class BulkActionResult {
    readonly success: boolean;
    readonly response: BulkActionResponse | null;
    readonly errorMessage: string | null;
    readonly errorStatus: number | null;

    constructor(
        success: boolean,
        response: BulkActionResponse | null,
        errorMessage: string | null,
        errorStatus: number | null = null
    ) {
        this.success = success;
        this.response = response;
        this.errorMessage = errorMessage;
        this.errorStatus = errorStatus;
    }

    /**
     * Check if the bulk operation had partial failures.
     */
    get hasPartialFailure(): boolean {
        return this.success && (this.response?.summary.failed ?? 0) > 0;
    }

    /**
     * Check if all operations succeeded.
     */
    get allSucceeded(): boolean {
        return this.success && this.response?.summary.failed === 0;
    }

    /**
     * True when the failure looks transient (network error, 429, 5xx)
     * and the caller should preserve selection so the user can retry.
     */
    get isTransientFailure(): boolean {
        if (this.success) { return false; }
        const s = this.errorStatus;
        return s === null || s === 0 || s === 429 || (s !== null && s >= 500);
    }
}

/**
 * BulkCommandService handles sending bulk commands to the backend server.
 * This service makes POST requests to /server/command/bulk for bulk file operations.
 */
@Injectable({
    providedIn: "root"
})
export class BulkCommandService {
    private readonly BULK_URL = "/server/command/bulk";

    constructor(
        private _logger: LoggerService,
        private _http: HttpClient
    ) {}

    /**
     * Execute a bulk action on multiple files.
     * @param action The action to perform
     * @param files Array of file names to operate on
     * @returns Observable that emits BulkActionResult
     */
    public executeBulkAction(action: BulkAction, files: string[]): Observable<BulkActionResult> {
        return new Observable<BulkActionResult>(observer => {
            const body = {action, files};

            const sub = this._http.post<BulkActionResponse | BulkErrorResponse>(this.BULK_URL, body)
                .subscribe({
                    next: (data) => {
                        this._logger.debug("%s bulk response: %O", this.BULK_URL, data);

                        // Check if it's an error response (shouldn't happen with 200 but be safe)
                        if ("error" in data) {
                            observer.next(new BulkActionResult(false, null, data.error, null));
                        } else {
                            observer.next(new BulkActionResult(true, data, null));
                        }
                    },
                    error: (err: HttpErrorResponse) => {
                        this._logger.debug("%s error: %O", this.BULK_URL, err);

                        let errorMessage: string;
                        if (err.error instanceof Event) {
                            errorMessage = err.error.type;
                        } else if (typeof err.error === "object" && err.error?.error) {
                            // JSON error response from backend
                            errorMessage = err.error.error;
                        } else if (typeof err.error === "string") {
                            errorMessage = err.error;
                        } else {
                            errorMessage = err.message || "Unknown error";
                        }

                        // err.status is 0 for network failures, otherwise the HTTP status.
                        observer.next(new BulkActionResult(false, null, errorMessage, err.status ?? null));
                    }
                });

            return () => sub.unsubscribe();
        }).pipe(shareReplay(1));
    }
}
