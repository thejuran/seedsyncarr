# Changelog

All notable changes to SeedSyncarr are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.1.0] - 2026-04-20

### Added

- Per-file selection and shift-range select with a bulk-actions bar for Queue, Stop, Extract, Delete Local, and Delete Remote operations on multiple files.
- Dashboard filter with URL persistence: filter transfers by status with state preserved in the browser URL for sharing and page reloads.
- Storage capacity tiles on the dashboard showing local disk and seedbox usage with warning and danger color thresholds.
- New navigation bar with live connection status indicator and notification panel.

### Changed

- Transfer table redesigned with search, pagination, status badges, and progress bars.
- Settings page reorganized into card sections with toggle switches and inline AutoQueue pattern management.
- Logs page updated with full-viewport terminal view, log-level filter buttons, and regex search.
- About page updated with version badge and system information table.
- Color theme unified consistently across all pages.

## [1.0.0] - 2026-04-08

### Added

- LFTP-based file synchronization from remote seedbox to local server
- Web UI for monitoring and controlling transfers with real-time status via SSE
- Sonarr and Radarr webhook integration for automated media imports with auto-delete
- AutoQueue with pattern-based file selection
- Automatic file extraction after sync completes
- Docker images for amd64 and arm64
- Dark mode UI with Deep Moss and Amber palette
- API token authentication (Bearer tokens)
- Security hardening: HMAC webhooks, CSP, DNS rebinding prevention, credential redaction

[1.1.0]: https://github.com/thejuran/seedsyncarr/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/thejuran/seedsyncarr/releases/tag/v1.0.0
