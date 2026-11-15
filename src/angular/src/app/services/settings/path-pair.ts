/**
 * A remote-to-local directory mapping, as returned by /server/pathpairs
 */
export interface PathPair {
    id: string;
    name: string;
    remote_path: string;
    local_path: string;
    enabled: boolean;
    auto_queue: boolean;
}

/**
 * The fields a client can set when creating or updating a path pair
 */
export interface PathPairInput {
    name: string;
    remote_path: string;
    local_path: string;
    enabled?: boolean;
    auto_queue?: boolean;
}

/**
 * Id of the pair migrated from the single remote/local path of the Lftp settings.
 * Its paths are owned by those settings and cannot be changed through the pair.
 */
export const LEGACY_PATH_PAIR_ID = "default";
