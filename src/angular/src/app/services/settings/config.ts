import {Record} from "immutable";

/**
 * Backend config
 * Note: Naming convention matches that used in the JSON
 */

/*
 * GENERAL
 */
interface IGeneral {
    debug: boolean;
}
const DefaultGeneral: IGeneral = {
    debug: false
};
const GeneralRecord = Record(DefaultGeneral);

/*
 * LFTP
 */
interface ILftp {
    remote_address: string;
    remote_username: string;
    remote_password: string;
    remote_port: number;
    remote_path: string;
    local_path: string;
    remote_path_to_scan_script: string;
    use_ssh_key: boolean;
    num_max_parallel_downloads: number;
    num_max_parallel_files_per_download: number;
    num_max_connections_per_root_file: number;
    num_max_connections_per_dir_file: number;
    num_max_total_connections: number;
    use_temp_file: boolean;
}
const DefaultLftp: ILftp = {
    remote_address: "",
    remote_username: "",
    remote_password: "",
    remote_port: 0,
    remote_path: "",
    local_path: "",
    remote_path_to_scan_script: "",
    use_ssh_key: false,
    num_max_parallel_downloads: 0,
    num_max_parallel_files_per_download: 0,
    num_max_connections_per_root_file: 0,
    num_max_connections_per_dir_file: 0,
    num_max_total_connections: 0,
    use_temp_file: false,
};
const LftpRecord = Record(DefaultLftp);

/*
 * CONTROLLER
 */
interface IController {
    interval_ms_remote_scan: number;
    interval_ms_local_scan: number;
    interval_ms_downloading_scan: number;
    extract_path: string;
    use_local_path_as_extract_path: boolean;
}
const DefaultController: IController = {
    interval_ms_remote_scan: 0,
    interval_ms_local_scan: 0,
    interval_ms_downloading_scan: 0,
    extract_path: "",
    use_local_path_as_extract_path: false,
};
const ControllerRecord = Record(DefaultController);

/*
 * WEB
 */
interface IWeb {
    port: number;
}
const DefaultWeb: IWeb = {
    port: 0
};
const WebRecord = Record(DefaultWeb);

/*
 * AUTOQUEUE
 */
interface IAutoQueue {
    enabled: boolean;
    patterns_only: boolean;
    auto_extract: boolean;
}
const DefaultAutoQueue: IAutoQueue = {
    enabled: false,
    patterns_only: false,
    auto_extract: false,
};
const AutoQueueRecord = Record(DefaultAutoQueue);

/*
 * SONARR
 */
interface ISonarr {
    enabled: boolean;
    sonarr_url: string;
    sonarr_api_key: string;
}
const DefaultSonarr: ISonarr = {
    enabled: false,
    sonarr_url: "",
    sonarr_api_key: "",
};
const SonarrRecord = Record(DefaultSonarr);

/*
 * RADARR
 */
interface IRadarr {
    enabled: boolean;
    radarr_url: string;
    radarr_api_key: string;
}
const DefaultRadarr: IRadarr = {
    enabled: false,
    radarr_url: "",
    radarr_api_key: "",
};
const RadarrRecord = Record(DefaultRadarr);

/*
 * AUTODELETE
 */
interface IAutoDelete {
    enabled: boolean;
    dry_run: boolean;
    delay_seconds: number;
}
const DefaultAutoDelete: IAutoDelete = {
    enabled: false,
    dry_run: false,
    delay_seconds: 0,
};
const AutoDeleteRecord = Record(DefaultAutoDelete);

/*
 * CONFIG
 */
export interface IConfig {
    general: IGeneral;
    lftp: ILftp;
    controller: IController;
    web: IWeb;
    autoqueue: IAutoQueue;
    sonarr: ISonarr;
    radarr: IRadarr;
    autodelete: IAutoDelete;
}
const DefaultConfig: IConfig = {
    general: DefaultGeneral,
    lftp: DefaultLftp,
    controller: DefaultController,
    web: DefaultWeb,
    autoqueue: DefaultAutoQueue,
    sonarr: DefaultSonarr,
    radarr: DefaultRadarr,
    autodelete: DefaultAutoDelete,
};
const ConfigRecord = Record(DefaultConfig);


export class Config extends ConfigRecord implements IConfig {
    general!: IGeneral;
    lftp!: ILftp;
    controller!: IController;
    web!: IWeb;
    autoqueue!: IAutoQueue;
    sonarr!: ISonarr;
    radarr!: IRadarr;
    autodelete!: IAutoDelete;

    constructor(props: Partial<IConfig>) {
        // Create immutable members
        super({
            general: GeneralRecord(props.general),
            lftp: LftpRecord(props.lftp),
            controller: ControllerRecord(props.controller),
            web: WebRecord(props.web),
            autoqueue: AutoQueueRecord(props.autoqueue),
            sonarr: props.sonarr ? SonarrRecord(props.sonarr) : SonarrRecord(DefaultSonarr),
            radarr: props.radarr ? RadarrRecord(props.radarr) : RadarrRecord(DefaultRadarr),
            autodelete: props.autodelete ? AutoDeleteRecord(props.autodelete) : AutoDeleteRecord(DefaultAutoDelete),
        });
    }
}
