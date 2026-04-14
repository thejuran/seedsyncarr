export class Localization {
    static Error = class {
        public static readonly SERVER_DISCONNECTED = "Lost connection to the SeedSyncarr service.";
    };

    static Notification = class {
        public static readonly CONFIG_RESTART = "Restart the app to apply new settings.";
        public static readonly CONFIG_VALUE_BLANK =
            (section: string, option: string): string => `Setting ${section}.${option} cannot be blank.`;

        public static readonly AUTOQUEUE_PATTERN_EMPTY = "Cannot add an empty autoqueue pattern.";

        public static readonly STATUS_CONNECTION_WAITING = "Waiting for SeedSyncarr service to respond...";
        public static readonly STATUS_REMOTE_SCAN_WAITING = "Waiting for remote server to respond...";
        public static readonly STATUS_REMOTE_SERVER_ERROR = (error: string): string =>
            `Lost connection to remote server. Retrying automatically.${error ? " " + error : ""}`;

        public static readonly NEW_VERSION_AVAILABLE = (url: string): string =>
            `A new version of SeedSyncarr is available! Visit ${url} to grab the latest version.`;
    };

    static Modal = class {
        public static readonly DELETE_LOCAL_TITLE = "Delete Local File";
        public static readonly DELETE_LOCAL_MESSAGE =
            (name: string): string => `Are you sure you want to delete "${name}" from the local server?`;

        public static readonly DELETE_REMOTE_TITLE = "Delete Remote File";
        public static readonly DELETE_REMOTE_MESSAGE =
            (name: string): string => `Are you sure you want to delete "${name}" from the remote server?`;

        // Bulk action confirmations
        public static readonly BULK_DELETE_LOCAL_TITLE = "Delete Local Files";
        public static readonly BULK_DELETE_LOCAL_MESSAGE =
            (count: number): string => {
                const plural = count === 1 ? "" : "s";
                return `Are you sure you want to delete ${count} file${plural} from the local server?`;
            };

        public static readonly BULK_DELETE_REMOTE_TITLE = "Delete Remote Files";
        public static readonly BULK_DELETE_REMOTE_MESSAGE =
            (count: number): string => {
                const plural = count === 1 ? "" : "s";
                return `Are you sure you want to delete ${count} file${plural} ` +
                    `from the remote server? This cannot be undone.`;
            };
    };

    static Bulk = class {
        // Success messages
        public static readonly SUCCESS_QUEUED = (count: number): string =>
            `Queued ${count} file${count === 1 ? "" : "s"} successfully`;
        public static readonly SUCCESS_STOPPED = (count: number): string =>
            `Stopped ${count} file${count === 1 ? "" : "s"} successfully`;
        public static readonly SUCCESS_EXTRACTED = (count: number): string =>
            `Extracted ${count} file${count === 1 ? "" : "s"} successfully`;
        public static readonly SUCCESS_DELETED_LOCAL = (count: number): string =>
            `Deleted ${count} local file${count === 1 ? "" : "s"} successfully`;
        public static readonly SUCCESS_DELETED_REMOTE = (count: number): string =>
            `Deleted ${count} remote file${count === 1 ? "" : "s"} successfully`;

        // Partial failure messages
        public static readonly PARTIAL_QUEUED = (succeeded: number, failed: number): string =>
            `Queued ${succeeded} file${succeeded === 1 ? "" : "s"}. ${failed} failed.`;
        public static readonly PARTIAL_STOPPED = (succeeded: number, failed: number): string =>
            `Stopped ${succeeded} file${succeeded === 1 ? "" : "s"}. ${failed} failed.`;
        public static readonly PARTIAL_EXTRACTED = (succeeded: number, failed: number): string =>
            `Extracted ${succeeded} file${succeeded === 1 ? "" : "s"}. ${failed} failed.`;
        public static readonly PARTIAL_DELETED_LOCAL = (succeeded: number, failed: number): string =>
            `Deleted ${succeeded} local file${succeeded === 1 ? "" : "s"}. ${failed} failed.`;
        public static readonly PARTIAL_DELETED_REMOTE = (succeeded: number, failed: number): string =>
            `Deleted ${succeeded} remote file${succeeded === 1 ? "" : "s"}. ${failed} failed.`;

        // Error messages
        public static readonly ERROR = (message: string): string =>
            `Bulk action failed: ${message}`;
        public static readonly ERROR_RETRY = (message: string): string =>
            `${message} Please re-select files and try again.`;
    };

    static Log = class {
        public static readonly CONNECTED = "Connected to service";
        public static readonly DISCONNECTED = "Lost connection to service";
    };
}
