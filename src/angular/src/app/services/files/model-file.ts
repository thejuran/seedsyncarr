import {Record, Set} from "immutable";

/**
 * JSON representation of a model file received from the backend
 * Used for type-safe JSON parsing before conversion to ModelFile
 * Note: Some fields are optional as they may not always be present in the JSON
 */
export interface ModelFileJson {
    name: string;
    is_dir: boolean;
    local_size: number;
    remote_size: number;
    state: string;
    downloading_speed: number;
    eta: number;
    full_path: string;
    is_extractable?: boolean | null;
    import_status?: string | null;
    local_created_timestamp?: number | null;
    local_modified_timestamp?: number | null;
    remote_created_timestamp?: number | null;
    remote_modified_timestamp?: number | null;
    children: ModelFileJson[];
}

/**
 * Model file received from the backend
 * Note: Naming convention matches that used in the JSON
 */
interface IModelFile {
    name: string;
    is_dir: boolean;
    local_size: number;
    remote_size: number;
    state: ModelFile.State;
    downloading_speed: number;
    eta: number;
    full_path: string;
    is_extractable: boolean;
    import_status: ModelFile.ImportStatus;
    local_created_timestamp: Date | null;
    local_modified_timestamp: Date | null;
    remote_created_timestamp: Date | null;
    remote_modified_timestamp: Date | null;
    children: Set<ModelFile>;
}

// Boiler plate code to set up an immutable class
const DefaultModelFile: IModelFile = {
    name: "",
    is_dir: false,
    local_size: 0,
    remote_size: 0,
    state: "default" as ModelFile.State,
    downloading_speed: 0,
    eta: 0,
    full_path: "",
    is_extractable: false,
    import_status: "none" as ModelFile.ImportStatus,
    local_created_timestamp: null,
    local_modified_timestamp: null,
    remote_created_timestamp: null,
    remote_modified_timestamp: null,
    children: Set<ModelFile>()
};
const ModelFileRecord = Record(DefaultModelFile);

/**
 * Immutable class that implements the interface
 * Pattern inspired by: http://blog.angular-university.io/angular-2-application
 *                      -architecture-building-flux-like-apps-using-redux-and
 *                      -immutable-js-js
 */
export class ModelFile extends ModelFileRecord implements IModelFile {
    name!: string;
    is_dir!: boolean;
    local_size!: number;
    remote_size!: number;
    state!: ModelFile.State;
    downloading_speed!: number;
    eta!: number;
    full_path!: string;
    is_extractable!: boolean;
    import_status!: ModelFile.ImportStatus;
    local_created_timestamp!: Date;
    local_modified_timestamp!: Date;
    remote_created_timestamp!: Date;
    remote_modified_timestamp!: Date;
    children!: Set<ModelFile>;

    constructor(props: Partial<ModelFile>) {
        super(props);
    }
}

// Additional types
export namespace ModelFile {
    export function fromJson(json: ModelFileJson): ModelFile {
        // Create immutable objects for children as well
        const children: ModelFile[] = [];
        for (const child of json.children) {
            children.push(ModelFile.fromJson(child));
        }

        // State mapping
        const state = ModelFile.State[json.state.toUpperCase() as keyof typeof ModelFile.State];

        // Timestamps
        const localCreatedTimestamp = json.local_created_timestamp != null
            ? new Date(1000 * json.local_created_timestamp)
            : null;
        const localModifiedTimestamp = json.local_modified_timestamp != null
            ? new Date(1000 * json.local_modified_timestamp)
            : null;
        const remoteCreatedTimestamp = json.remote_created_timestamp != null
            ? new Date(1000 * json.remote_created_timestamp)
            : null;
        const remoteModifiedTimestamp = json.remote_modified_timestamp != null
            ? new Date(1000 * json.remote_modified_timestamp)
            : null;

        // Import status mapping (with fallback for older backends)
        const importStatusStr = json.import_status || "none";
        const importStatus = ModelFile.ImportStatus[importStatusStr.toUpperCase() as keyof typeof ModelFile.ImportStatus]
            || ModelFile.ImportStatus.NONE;

        return new ModelFile({
            name: json.name,
            is_dir: json.is_dir,
            local_size: json.local_size,
            remote_size: json.remote_size,
            state: state,
            downloading_speed: json.downloading_speed,
            eta: json.eta,
            full_path: json.full_path,
            is_extractable: json.is_extractable != null ? json.is_extractable : false,
            import_status: importStatus,
            local_created_timestamp: localCreatedTimestamp ?? undefined,
            local_modified_timestamp: localModifiedTimestamp ?? undefined,
            remote_created_timestamp: remoteCreatedTimestamp ?? undefined,
            remote_modified_timestamp: remoteModifiedTimestamp ?? undefined,
            children: Set<ModelFile>(children)
        });
    }

    export enum State {
        DEFAULT = "default",
        QUEUED = "queued",
        DOWNLOADING = "downloading",
        DOWNLOADED = "downloaded",
        DELETED = "deleted",
        EXTRACTING = "extracting",
        EXTRACTED = "extracted"
    }

    export enum ImportStatus {
        NONE            = "none",
        IMPORTED        = "imported"
    }
}
