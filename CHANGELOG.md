# Changelog

All notable changes to SeedSyncarr are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.4.0] - 2026-06-02

A launch-hardening release that closes the remaining public-facing rough edges and rebuilds the project's documentation surface. The one breaking change is the config-set endpoint moving from a GET path to a POST body so credentials no longer travel in URLs or server logs; on-disk config files (including encrypted ones) load unchanged with no migration step.

### Changed

- **Breaking:** Configuration values are now set via `POST /server/config/set` with a JSON body (`{section, key, value}`); the legacy `GET /server/config/set/{section}/{key}/{value}` path has been removed so credential values no longer appear as URL path segments in access logs, browser history, or reverse-proxy logs. The Angular settings page and the end-to-end setup use the new endpoint; saved settings round-trip unchanged.

### Added

- A prominent startup warning when the server binds to a non-loopback interface with no `api_token` configured, so an unauthenticated posture is no longer silent (default behavior unchanged).
- A prominent startup warning when the webhook endpoint is reachable with no `webhook_secret` set and `webhook_require_secret` off (default behavior unchanged).
- A one-time warning when startup falls back to the legacy `~/.seedsync` configuration directory because the configured directory is absent.

### Fixed

- Failures during local file deletion are now logged with context instead of being silently swallowed, so a failed cleanup leaves an observable signal in the logs.
- Background process startup now creates its queue and event from a spawn-compatible multiprocessing context, so the full test suite passes under both `fork` and `spawn` start methods.

### Documentation

- Rebuilt the README, `SECURITY.md`, and community-health files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`) and added a v1.4.0 release entry, following a cynical-reader teardown and an adversarial content pass over the drafts.
- Renamed `LICENSE.txt` to `LICENSE` so the repository license is detected correctly, and added run/tooling artifacts to `.gitignore`.

## [1.3.0] - 2026-06-02

A reliability and quality release delivered across four work streams (test coverage, known bugs + security, dependency cleanup, and a behavior-preserving backend refactor). No configuration changes or migrations are required; existing config files (including encrypted ones) load unchanged.

### Security

- The Sonarr/Radarr webhook can now be configured to reject unauthenticated calls when no secret is set (opt-in fail-closed, default behavior unchanged), and is rate-limited like other mutable endpoints.
- Remote- and user-supplied file names are sanitized for CR/LF and control characters before reaching log lines, closing a log-forging surface (CWE-117).
- The config API response no longer distinguishes set-vs-unset secret fields beyond the explicit boolean flag.
- The confirmation modal is now built structurally via `Renderer2` text nodes instead of an `innerHTML` sink, eliminating an XSS vector when rendering file names.

### Fixed

- Auto-delete timers are tracked and cancelled on controller shutdown, and a timer callback that fires during shutdown no-ops instead of acting against a half-torn-down model.
- The SSE stream registry no longer leaves an orphaned subscription when a reconnect fires in the same tick as a timeout.
- Background multiprocessing logging now creates its queue from a shared `spawn`-compatible context, fixing failures under `spawn`-mode process startup.

### Changed

- Removed three end-of-life frontend dependencies (jQuery 4, Font Awesome 4.7, and css-element-queries) and migrated all icons to Phosphor; the production bundle ships less code with no visual or behavioral change.
- Development-only mock fixtures are now fully excluded from the production bundle via Angular `fileReplacements`.
- Refactored several large backend components into smaller, single-responsibility pieces — declarative `Config` secret-field discovery, a shared single-action request-dispatch helper, and decomposition of the `Controller` class into focused collaborators. Behavior is unchanged.
- Closed eight test-coverage gaps and ratcheted CI coverage floors (Python and Angular) so regressions are caught earlier.

## [1.2.5] - 2026-05-28

### Security

- Updated `tmp` to 0.2.7 to address GHSA-ph9p-34f9-6g65 / CVE-2026-44705 (path traversal via unsanitized prefix/postfix). The vulnerable package was a transitive dependency of the Angular test toolchain only and is not present in the published Docker runtime, but the lockfile has been updated to clear the advisory.

### Changed

- Updated Angular framework and CLI to 21.2.14, along with `@typescript-eslint/*` 8.60.0 and `sass` 1.100.0.
- Updated development tooling: Puppeteer 25.1.0, Ruff 0.15.14, and `testfixtures` 12.0.0.

## [1.2.4] - 2026-05-20

### Changed

- Refreshed frontend and Python dependencies, including Angular 21.2.13 patch updates, `zone.js` 0.16.2, `requests` 2.34.2, and `patool` 4.0.5.
- Updated development tooling: Puppeteer 25, Playwright 1.60, TypeScript ESLint 8.59.4, ESLint 10.4, and Ruff 0.15.13.

## [1.2.3] - 2026-05-11

### Security

- Updated `urllib3` to 2.7.0 to address GHSA-mf9v-mfxr-j63j / CVE-2026-44432.

### Changed

- Refreshed frontend and Python runtime dependencies, including timezone data.
- Updated frontend build dependencies and resolved dependency advisory coverage in the web UI toolchain.
- Improved release validation so future published versions are checked against their release metadata before publishing.

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

[1.4.0]: https://github.com/thejuran/seedsyncarr/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/thejuran/seedsyncarr/compare/v1.2.5...v1.3.0
[1.2.3]: https://github.com/thejuran/seedsyncarr/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/thejuran/seedsyncarr/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/thejuran/seedsyncarr/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/thejuran/seedsyncarr/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/thejuran/seedsyncarr/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/thejuran/seedsyncarr/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/thejuran/seedsyncarr/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/thejuran/seedsyncarr/releases/tag/v1.0.0
