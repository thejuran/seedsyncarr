# Changelog

All notable changes to SeedSyncarr are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.2.2] - 2026-05-05

### Fixed

- Failed remote, local, or active scans are ignored when feeding the model builder, preventing transient scan failures from clearing visible transfer state.
- Scanner dead-process detection now avoids false error reports during shutdown, terminates scanner subprocesses after unexpected failures, and surfaces a clear controller error without internal diagnostic details.

## [1.2.1] - 2026-04-29

### Changed

- Updated development dependencies including Angular npm packages, PostCSS, Ruff, and PyInstaller.

### Fixed

- Repaired E2E CI SSH-key mounting for current GitHub Actions/Node runner behavior.
- Restored E2E setup completeness by supplying required remote password and rate-limit fixture values.
- Fixed E2E remote filesystem permissions for the SSH user and remote scan directory.
- Scoped compose builds to test services, forced the default buildx builder for compose steps, and resolved Python test build/lint failures.

## [1.2.0] - 2026-04-28

### Added

- Sliding-window rate limiting for mutable HTTP endpoints, with unit coverage for controller, config, and status handlers.
- Additional backend coverage for SSE streaming, webhooks, `DeleteRemoteProcess`, `ActiveScanner`, and scanner/process edge cases.
- Logs and Settings E2E specs plus page-object helpers for the web UI.
- Docker E2E validation scripts for compose schema, status parsing, setup patterns, and run-time environment checks.

### Changed

- Migrated Angular HTTP tests to the modern `provideHttpClient` / `provideHttpClientTesting` APIs.
- Refactored Python test helpers and controller fixtures to reduce duplication and make integration tests clearer.
- Documented Python test architecture tradeoffs and known coverage gaps.

### Fixed

- Fixed Python test defects around false coverage, temporary-file leaks, bare file handles, logger handler leaks, swallowed thread assertions, and busy-wait CPU spin.
- Fixed Angular test issues around fakeAsync cleanup, subscription teardown, optional assertion guards, and stale comments.
- Fixed E2E flakiness around Playwright selectors, API response waiting, arm64 sort determinism, Docker health checks, and shell-script failure handling.

### Security

- Hardened GitHub Actions CI with least-privilege permissions, SHA-pinned actions, safer expression quoting, and stricter shell behavior.
- Hardened E2E Docker SSH flows with ephemeral keys, non-root `sshd`, password-auth removal, and clearer key-generation failure handling.
- Tightened Semgrep rules for JavaScript NoSQL-injection and XSS eval patterns, reducing false positives while preserving signal.

## [1.1.2] - 2026-04-23

### Fixed

- Bulk-actions bar now sticks to the bottom of the viewport instead of rendering inline below the table, making it visible without scrolling.

## [1.1.1] - 2026-04-22

### Added

- Optional encryption at rest for config secrets (API token, webhook secret, Sonarr/Radarr API keys, remote password). Enable via `[Encryption]` section in config; a keyfile is generated on first enable with restrictive permissions.
- pip install support (`pip install seedsyncarr`) as an alternative to Docker.

### Changed

- Phosphor Icons self-hosted via npm instead of unpkg CDN — eliminates external script dependency and CSP violations.
- Removed Google Fonts (Inter, JetBrains Mono) — restored system font stack for zero external font dependencies.
- Replaced Debian package distribution with pip install.

### Fixed

- Bulk-actions bar now shows "Re-Queue from Remote" when the selection includes deleted files, matching the single-file behavior.
- Auto-delete for multi-file packs waits until every child file is confirmed as imported before deleting, preventing premature deletion when an import is silently rejected.
- E2E tests no longer fail due to CSP violations from external CDN resources.

### Security

- Updated `basic-ftp` transitive dependency to 5.3.0+ to close a denial-of-service advisory (GHSA-rp42-5vxx-qpwr).

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

[1.2.2]: https://github.com/thejuran/seedsyncarr/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/thejuran/seedsyncarr/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/thejuran/seedsyncarr/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/thejuran/seedsyncarr/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/thejuran/seedsyncarr/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/thejuran/seedsyncarr/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/thejuran/seedsyncarr/releases/tag/v1.0.0
