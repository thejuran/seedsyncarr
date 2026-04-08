/**
 * Represents an in-progress action on a single file row.
 * Used by FileComponent to disable buttons and show spinners
 * while an action is being processed.
 */
export enum FileAction {
    QUEUE,
    STOP,
    EXTRACT,
    DELETE_LOCAL,
    DELETE_REMOTE
}
