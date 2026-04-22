import {Record} from "immutable";

/**
 * View file
 * Represents the View Model
 */
interface IViewFile {
    name: string | null;
    isDir: boolean | null;
    localSize: number | null;
    remoteSize: number | null;
    percentDownloaded: number | null;
    status: ViewFile.Status | null;
    downloadingSpeed: number | null;
    eta: number | null;
    fullPath: string | null;
    isArchive: boolean | null;  // corresponds to is_extractable in ModelFile
    isSelected: boolean | null;
    isQueueable: boolean | null;
    isStoppable: boolean | null;
    // whether file can be queued for extraction (independent of isArchive)
    isExtractable: boolean | null;
    isLocallyDeletable: boolean | null;
    isRemotelyDeletable: boolean | null;
    // timestamps
    localCreatedTimestamp: Date | null;
    localModifiedTimestamp: Date | null;
    remoteCreatedTimestamp: Date | null;
    remoteModifiedTimestamp: Date | null;
    importStatus: ViewFile.ImportStatus | null;
}

// Boiler plate code to set up an immutable class
const DefaultViewFile: IViewFile = {
    name: null,
    isDir: null,
    localSize: null,
    remoteSize: null,
    percentDownloaded: null,
    status: null,
    downloadingSpeed: null,
    eta: null,
    fullPath: null,
    isArchive: null,
    isSelected: null,
    isQueueable: null,
    isStoppable: null,
    isExtractable: null,
    isLocallyDeletable: null,
    isRemotelyDeletable: null,
    localCreatedTimestamp: null,
    localModifiedTimestamp: null,
    remoteCreatedTimestamp: null,
    remoteModifiedTimestamp: null,
    importStatus: null
};
const ViewFileRecord = Record(DefaultViewFile);

/**
 * Immutable class that implements the interface
 */
export class ViewFile extends ViewFileRecord implements IViewFile {
    name!: string | null;
    isDir!: boolean | null;
    localSize!: number | null;
    remoteSize!: number | null;
    percentDownloaded!: number | null;
    status!: ViewFile.Status | null;
    downloadingSpeed!: number | null;
    eta!: number | null;
    fullPath!: string | null;
    isArchive!: boolean | null;
    isSelected!: boolean | null;
    isQueueable!: boolean | null;
    isStoppable!: boolean | null;
    isExtractable!: boolean | null;
    isLocallyDeletable!: boolean | null;
    isRemotelyDeletable!: boolean | null;
    localCreatedTimestamp!: Date | null;
    localModifiedTimestamp!: Date | null;
    remoteCreatedTimestamp!: Date | null;
    remoteModifiedTimestamp!: Date | null;
    importStatus!: ViewFile.ImportStatus | null;

    constructor(props: Partial<ViewFile>) {
        super(props);
    }
}

export namespace ViewFile {
    export enum Status {
        DEFAULT         = "default",
        QUEUED          = "queued",
        DOWNLOADING     = "downloading",
        DOWNLOADED      = "downloaded",
        STOPPED         = "stopped",
        DELETED         = "deleted",
        EXTRACTING      = "extracting",
        EXTRACTED       = "extracted"
    }

    export enum ImportStatus {
        NONE                = "none",
        IMPORTED            = "imported"
    }
}
