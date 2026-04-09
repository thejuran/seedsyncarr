# Configuration Reference

SeedSyncarr stores its configuration in `~/.seedsyncarr/settings.cfg` (INI format). All settings are editable through the web UI under **Settings**.

## [General]

| Field | Type | Description |
|-------|------|-------------|
| `debug` | bool | Enable debug logging |
| `verbose` | bool | Enable verbose logging |
| `webhook_secret` | string | HMAC-SHA256 secret for webhook signature verification. Leave empty to disable verification. |
| `api_token` | string | Bearer token for API authentication. Leave empty to disable token auth (backward compatible). |
| `allowed_hostname` | string | Restrict requests to this Host header value. Leave empty to allow any hostname (recommended for Docker). |

## [Lftp]

| Field | Type | Description |
|-------|------|-------------|
| `remote_address` | string | SSH hostname or IP of your seedbox |
| `remote_username` | string | SSH username |
| `remote_password` | string | SSH password |
| `remote_port` | int | SSH port (must be > 0) |
| `remote_path` | string | Path on the seedbox to sync from |
| `local_path` | string | Local path to sync files to |
| `remote_path_to_scan_script` | string | Path to the remote scan script |
| `use_ssh_key` | bool | Use SSH key authentication instead of password |
| `num_max_parallel_downloads` | int | Maximum concurrent LFTP downloads (must be > 0) |
| `num_max_parallel_files_per_download` | int | Maximum parallel files per download session (must be > 0) |
| `num_max_connections_per_root_file` | int | LFTP connections per root-level file (must be > 0) |
| `num_max_connections_per_dir_file` | int | LFTP connections per directory-level file (must be > 0) |
| `num_max_total_connections` | int | Total maximum LFTP connections. Set to 0 for unlimited. |
| `use_temp_file` | bool | Use `.lftp` temporary files during download |

## [Controller]

| Field | Type | Description |
|-------|------|-------------|
| `interval_ms_remote_scan` | int | Interval in milliseconds between remote directory scans (must be > 0) |
| `interval_ms_local_scan` | int | Interval in milliseconds between local directory scans (must be > 0) |
| `interval_ms_downloading_scan` | int | Interval in milliseconds between download progress scans (must be > 0) |
| `extract_path` | string | Path where downloaded archives are extracted |
| `use_local_path_as_extract_path` | bool | Use `local_path` as the extraction destination instead of `extract_path` |
| `max_tracked_files` | int | Maximum number of files tracked in memory (must be > 0) |

## [Web]

| Field | Type | Description |
|-------|------|-------------|
| `port` | int | HTTP port for the web dashboard (default: 8800, must be > 0) |

## [AutoQueue]

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Enable automatic queuing of new remote files |
| `patterns_only` | bool | Only auto-queue files matching configured patterns |
| `auto_extract` | bool | Automatically extract archives after download |

## [Sonarr]

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Enable Sonarr integration |
| `sonarr_url` | string | Sonarr base URL (e.g., `http://sonarr:8989`) |
| `sonarr_api_key` | string | Sonarr API key (found in Sonarr under Settings > General) |

## [Radarr]

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Enable Radarr integration |
| `radarr_url` | string | Radarr base URL (e.g., `http://radarr:7878`) |
| `radarr_api_key` | string | Radarr API key (found in Radarr under Settings > General) |

## [AutoDelete]

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Enable automatic deletion of seedbox files after successful import |
| `dry_run` | bool | Log which files would be deleted without actually deleting them |
| `delay_seconds` | int | Seconds to wait after import before deleting (must be > 0) |
