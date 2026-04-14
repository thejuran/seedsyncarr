<!-- generated-by: gsd-doc-writer -->
# Configuration

Seedsyncarr is configured through a single INI-format file, `settings.cfg`, stored in the config directory specified at startup via the `-c` flag. On first run, a default `settings.cfg` is automatically created with placeholder values. The application will refuse to start the sync controller until all required placeholder values are replaced.

---

## Config File Format

The config file uses standard INI format with named sections. On Docker, the file is located at `/config/settings.cfg`. On a direct install, it lives in the directory passed to `-c`.

```ini
[General]
debug = False
verbose = False
webhook_secret =
api_token =
allowed_hostname =

[Lftp]
remote_address = <replace me>
remote_username = <replace me>
remote_password = <replace me>
remote_port = 22
remote_path = <replace me>
local_path = <replace me>
remote_path_to_scan_script = /tmp
use_ssh_key = False
num_max_parallel_downloads = 2
num_max_parallel_files_per_download = 4
num_max_connections_per_root_file = 4
num_max_connections_per_dir_file = 4
num_max_total_connections = 16
use_temp_file = False

[Controller]
interval_ms_remote_scan = 30000
interval_ms_local_scan = 10000
interval_ms_downloading_scan = 1000
extract_path = /tmp
use_local_path_as_extract_path = True
max_tracked_files = 10000

[Web]
port = 8800

[AutoQueue]
enabled = True
patterns_only = False
auto_extract = True

[Sonarr]
enabled = False
sonarr_url =
sonarr_api_key =

[Radarr]
enabled = False
radarr_url =
radarr_api_key =

[AutoDelete]
enabled = False
dry_run = False
delay_seconds = 60
```

---

## Required vs Optional Settings

Settings marked **Required** contain the placeholder value `<replace me>` by default. The application detects these placeholders at startup and will not begin syncing until they are replaced with real values. Settings can be changed at runtime through the web UI at `http://<host>:8800/settings` or via the config API.

### [General]

| Setting | Required | Default | Description |
|---|---|---|---|
| `debug` | Optional | `False` | Enable verbose debug logging. |
| `verbose` | Optional | `False` | Enable extra verbose output. |
| `webhook_secret` | Optional | _(empty)_ | HMAC-SHA256 secret for verifying incoming webhook signatures. When empty, webhook signature verification is skipped and any caller can trigger a webhook. |
| `api_token` | Optional | _(empty)_ | Bearer token required on all `/server/*` API requests. When empty, the API accepts all requests without authentication. A warning is emitted at startup when this is not set. |
| `allowed_hostname` | Optional | _(empty)_ | Hostname the web server will accept in the HTTP `Host` header. When empty, any hostname is accepted (required for Docker environments with dynamic hostnames). When set, only `localhost`, `127.0.0.1`, `[::1]`, and this value are allowed. |

### [Lftp]

| Setting | Required | Default | Description |
|---|---|---|---|
| `remote_address` | **Required** | — | Hostname or IP address of the remote server. |
| `remote_username` | **Required** | — | SSH/SFTP username on the remote server. |
| `remote_password` | **Required** | — | Password for the remote user. Ignored when `use_ssh_key` is `True`. |
| `remote_port` | Optional | `22` | SSH port on the remote server. Must be a positive integer. |
| `remote_path` | **Required** | — | Absolute path on the remote server to scan for files. |
| `local_path` | **Required** | `/downloads/` (Docker) | Absolute local path where files are downloaded. The Docker image pre-fills this with `/downloads/`. |
| `remote_path_to_scan_script` | Optional | `/tmp` | Path on the remote server where the scan helper script is uploaded before execution. |
| `use_ssh_key` | Optional | `False` | Use SSH key authentication instead of password. The key must already be present in the SSH config for the running user. |
| `num_max_parallel_downloads` | Optional | `2` | Maximum number of files or directories to download concurrently. Must be ≥ 1. |
| `num_max_parallel_files_per_download` | Optional | `4` | Maximum number of files within a single directory download to transfer in parallel. Must be ≥ 1. |
| `num_max_connections_per_root_file` | Optional | `4` | Maximum LFTP connections per top-level file transfer. Must be ≥ 1. |
| `num_max_connections_per_dir_file` | Optional | `4` | Maximum LFTP connections per file inside a directory transfer. Must be ≥ 1. |
| `num_max_total_connections` | Optional | `16` | Hard cap on total simultaneous LFTP connections. `0` means unlimited. |
| `use_temp_file` | Optional | `False` | Download files to a `.lftp` temporary name and rename on completion. |

### [Controller]

| Setting | Required | Default | Description |
|---|---|---|---|
| `interval_ms_remote_scan` | Optional | `30000` | How often (in ms) to scan the remote server for new files. |
| `interval_ms_local_scan` | Optional | `10000` | How often (in ms) to scan the local download directory. |
| `interval_ms_downloading_scan` | Optional | `1000` | How often (in ms) to poll active transfers for progress updates. |
| `extract_path` | Optional | `/tmp` | Directory where archives are extracted. Overridden when `use_local_path_as_extract_path` is `True`. |
| `use_local_path_as_extract_path` | Optional | `True` | When `True`, archives are extracted into the same directory as the download (`local_path`). |
| `max_tracked_files` | Optional | `10000` | Maximum number of file entries tracked in the controller's state. Must be ≥ 1. |

### [Web]

| Setting | Required | Default | Description |
|---|---|---|---|
| `port` | Optional | `8800` | TCP port the web server listens on. Must be a positive integer. |

### [AutoQueue]

| Setting | Required | Default | Description |
|---|---|---|---|
| `enabled` | Optional | `True` | Automatically queue all newly detected remote files for download. |
| `patterns_only` | Optional | `False` | When `True`, only auto-queue files matching a configured pattern list. |
| `auto_extract` | Optional | `True` | Automatically extract archives after download completes. |

### [Sonarr]

| Setting | Required | Default | Description |
|---|---|---|---|
| `enabled` | Optional | `False` | Enable Sonarr integration. |
| `sonarr_url` | Optional | _(empty)_ | Base URL of the Sonarr instance. <!-- VERIFY: production Sonarr instance URL --> |
| `sonarr_api_key` | Optional | _(empty)_ | Sonarr API key. Redacted in API responses. |

### [Radarr]

| Setting | Required | Default | Description |
|---|---|---|---|
| `enabled` | Optional | `False` | Enable Radarr integration. |
| `radarr_url` | Optional | _(empty)_ | Base URL of the Radarr instance. <!-- VERIFY: production Radarr instance URL --> |
| `radarr_api_key` | Optional | _(empty)_ | Radarr API key. Redacted in API responses. |

### [AutoDelete]

| Setting | Required | Default | Description |
|---|---|---|---|
| `enabled` | Optional | `False` | Automatically delete files from the remote server after a successful download. |
| `dry_run` | Optional | `False` | When `True`, log what would be deleted without actually deleting. |
| `delay_seconds` | Optional | `60` | Seconds to wait after a download completes before deleting the remote file. Must be ≥ 1. |

---

## CLI Arguments

The following flags are passed to `seedsyncarr` (or `python seedsyncarr.py`) at startup and are separate from `settings.cfg`:

| Flag | Required | Description |
|---|---|---|
| `-c`, `--config_dir` | **Required** | Path to the directory containing `settings.cfg` and state persist files. Falls back to `~/.seedsync` if that directory exists. |
| `--logdir` | Optional | Directory for rotating log files. When omitted, logs are written to stdout. |
| `-d`, `--debug` | Optional | Enable debug logging. Equivalent to setting `general.debug = True` in the config file. |
| `--exit` | Optional | Exit immediately on any error instead of staying up in a degraded state. |
| `--html` | Required (unfrozen) | Path to the compiled Angular web UI directory. Pre-set in the Docker image at `/app/html`. |
| `--scanfs` | Required (unfrozen) | Path to the `scanfs` binary. Pre-set in the Docker image at `/app/scanfs`. |

---

## Defaults

| Setting | Default value | Where set |
|---|---|---|
| `general.debug` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `general.verbose` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `general.webhook_secret` | _(empty string)_ | `seedsyncarr.py` `_create_default_config()` |
| `general.api_token` | _(empty string)_ | `seedsyncarr.py` `_create_default_config()` |
| `general.allowed_hostname` | _(empty string)_ | `seedsyncarr.py` `_create_default_config()` |
| `lftp.remote_port` | `22` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.remote_path_to_scan_script` | `/tmp` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.use_ssh_key` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.num_max_parallel_downloads` | `2` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.num_max_parallel_files_per_download` | `4` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.num_max_connections_per_root_file` | `4` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.num_max_connections_per_dir_file` | `4` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.num_max_total_connections` | `16` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.use_temp_file` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `lftp.local_path` | `/downloads/` (Docker image only) | `setup_default_config.sh` |
| `controller.interval_ms_remote_scan` | `30000` | `seedsyncarr.py` `_create_default_config()` |
| `controller.interval_ms_local_scan` | `10000` | `seedsyncarr.py` `_create_default_config()` |
| `controller.interval_ms_downloading_scan` | `1000` | `seedsyncarr.py` `_create_default_config()` |
| `controller.extract_path` | `/tmp` | `seedsyncarr.py` `_create_default_config()` |
| `controller.use_local_path_as_extract_path` | `True` | `seedsyncarr.py` `_create_default_config()` |
| `controller.max_tracked_files` | `10000` | `seedsyncarr.py` `_create_default_config()` |
| `web.port` | `8800` | `seedsyncarr.py` `_create_default_config()` |
| `autoqueue.enabled` | `True` | `seedsyncarr.py` `_create_default_config()` |
| `autoqueue.patterns_only` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `autoqueue.auto_extract` | `True` | `seedsyncarr.py` `_create_default_config()` |
| `sonarr.enabled` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `radarr.enabled` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `autodelete.enabled` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `autodelete.dry_run` | `False` | `seedsyncarr.py` `_create_default_config()` |
| `autodelete.delay_seconds` | `60` | `seedsyncarr.py` `_create_default_config()` |

---

## Per-Environment Overrides

There are no separate per-environment config files. The single `settings.cfg` file is used in all environments. Environment-specific values (e.g., different remote servers for staging vs production) must be set directly in the config file for each deployment.

When running via Docker, the staging compose file (`src/docker/stage/docker-image/compose.yml`) accepts two environment variables that control which image is pulled:

| Variable | Description |
|---|---|
| `STAGING_REGISTRY` | Docker registry path for the image under test. <!-- VERIFY: actual registry value --> |
| `STAGING_VERSION` | Image tag/version to deploy. <!-- VERIFY: actual version tag format --> |

---

## Persist State Files

Alongside `settings.cfg`, Seedsyncarr writes two state files to the same config directory. These are managed automatically and do not require manual editing.

| File | Description |
|---|---|
| `controller.persist` | Tracks the state of all known remote and local files. Backed up automatically if corrupted. |
| `autoqueue.persist` | Tracks auto-queue pattern state. Backed up automatically if corrupted. |

Log files are written to the directory specified by `--logdir`, with a 10 MB rotating size limit and 10 backup files kept per log (`seedsyncarr.log`, `web_access.log`).
