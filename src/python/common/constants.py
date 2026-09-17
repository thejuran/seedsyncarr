class Constants:
    """
    POD class to hold shared constants
    """
    SERVICE_NAME = "seedsyncarr"
    MAIN_THREAD_SLEEP_INTERVAL_IN_SECS = 0.5
    MAX_LOG_SIZE_IN_BYTES = 10*1024*1024  # 10 MB
    LOG_BACKUP_COUNT = 10
    WEB_ACCESS_LOG_NAME = 'web_access'
    MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS = 30
    JSON_PRETTY_PRINT_INDENT = 4
    LFTP_TEMP_FILE_SUFFIX = ".lftp"
    # Staging directory that archives are unpacked into before their output is
    # moved into the release folder (incident 2026-09-16: Radarr imported a
    # 6 GB partial of a 38.5 GB mkv that unrar was still writing in place).
    # Lives at the extract ROOT as a sibling of the release folders, never
    # inside one, so *arr completed-download handling never sees it. Shared by
    # ExtractDispatch (writer) and LocalScanner (exclusion) so both agree.
    EXTRACT_STAGING_DIR_NAME = ".seedsyncarr-extracting"
