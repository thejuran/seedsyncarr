# Changelog

All notable changes to SeedSyncarr are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.7.0] - 2026-08-27

A reliability release closing the August incident cluster: releases that were
downloaded, imported, and deliberately deleted kept re-downloading from the
seedbox at every app restart; an auto-delete triggered by a Sonarr import
deleted a directory SeedSyncarr never owned; the ActiveScanner logged one
warning per second for entire transfers; and a wedged lftp could freeze the
whole app for hours — invisibly, because the container's log driver had
silently stopped recording. The root cause was one state-model gap with five
faces: completed transfers frequently never reached the persisted `downloaded`
list, and everything dangerous keyed off that list being right. Downloaded
tracking is now evidence-based and self-healing, destructive actions require
it, and existing persist files migrate themselves on first start with no
manual step.

### Fixed

- Fixed deleted releases re-downloading at every restart (incidents
  2026-08-22 and 2026-08-27). Completed-transfer tracking was edge-triggered:
  a release was only committed to the `downloaded` list if a model rebuild
  happened to observe the moment it finished, which restarts, duplicate lftp
  jobs, and fast import-then-delete sequences routinely prevented. Releases
  stuck in `imported`-but-not-`downloaded` were re-queued en masse seconds
  after every app restart (verified in production logs: nine releases queued
  in one millisecond after a restart). The commit is now level-triggered —
  every model build records any complete or imported release — and existing
  persist files self-heal on the first build after upgrade.
- Fixed auto-delete acting on directories SeedSyncarr never downloaded
  (incident 2026-08-21: a Sonarr import from an unrelated application's
  directory under the staging root deleted that entire directory). Webhook
  imports are only recorded — and auto-delete only armed — for releases with
  download evidence: already tracked as downloaded, or a complete local copy
  of a release that exists on the seedbox. Auto-delete additionally refuses
  outright to delete anything not in the downloaded list.
- Fixed the delete/re-queue race: auto-queue commands now re-check the
  stopped/downloaded guards at execution time, so a Delete Local landing
  between an auto-queue decision and its execution wins instead of being
  overwritten. Auto-queue commands also no longer clear the stopped flag.
- Fixed ActiveScanner logging "Path does not exist" once per second for the
  entire duration of every temp-file download (~172k lines/day measured).
  The active scanner now resolves `.lftp` temp names like the local scanner
  always has, and any genuinely missing path warns once then backs off to
  debug until it resolves.
- Fixed a wedged lftp freezing the app for hours. Every controller cycle
  called lftp status with a 180-second timeout; with lftp stuck, commands
  drained at minutes per cycle and the web worker pool exhausted (port
  accepted connections then reset). A circuit breaker now detects a stalled
  status call (>30s) and backs off polling for 60s, keeping the app
  responsive while lftp recovers.
- Fixed e2e seed fixture to poll for the "Skipped (remote)" badge after a
  local delete instead of racing the model update.

### Changed

- Delete Local is now a durable decision: a locally deleted release shows the
  amber "Skipped (remote)" badge and will not re-download while its seedbox
  copy remains. To deliberately re-download, press Queue — an explicit user
  Queue now clears the release's tracking and starts a fresh lifecycle.
  (Sonarr/Radarr re-grabs are unaffected: the 24-hour re-grab detection from
  1.6.0 still clears tracking automatically.)
- Logs are now written to rotating files under `/config/log` in addition to
  stdout. During the August incidents, Synology's container log driver had
  silently dropped all output for five days after hitting its size cap,
  leaving the incidents undiagnosable; file logs survive independent of the
  container log driver while `docker logs` keeps working.
- CI pins ruff to the version in poetry.lock (an unpinned install pulled the
  new ruff 0.16 release, whose changed defaults failed the whole tree with
  926 errors unrelated to the change under test).

### Security

- Sanitized remote-scanner-derived file names in the two new downloaded-list
  log calls (CWE-117 log injection), keeping the codebase-wide convention.
- Resolved all 22 open Dependabot alerts across pip and npm, including:
  cryptography 48.0.1 → 50.0.1 (2 high), pymdown-extensions → 11.0.2 (high +
  medium), webob → 1.8.11, fast-uri → 3.1.6 (high), postcss → 8.5.26 (high +
  medium), socket.io-parser → 4.2.7 (high), ip-address → 10.5.0 (high + 2
  medium), @angular/common → 22.1.3 (high), hono → 4.13.3 and
  @hono/node-server → 1.19.17 (4 medium/low), and removal of undici (1 high,
  4 medium). Also setuptools → 83.0.0 (moderate) and assorted dev-dependency
  updates (pytest, testfixtures, mkdocs-material, puppeteer, ruff 0.15.22).

## [1.6.0] - 2026-07-23

A reliability release driven by a production incident: a completed seedbox
download was silently never synced, because tracking state left over from an
earlier download/import of the same release name permanently blacklisted it
from auto-queue while the failure was invisible in the dashboard. This release
fixes the root causes, makes *arr import detection strictly evidence-based,
and surfaces skipped files in the UI. Existing config and persist files load
unchanged; a new persist field (`absent_since`) is added automatically on the
next save, with no migration step.

### Fixed

- Fixed re-grabbed releases being silently blacklisted forever. Downloaded and
  imported tracking entries are keyed by file name and were kept indefinitely,
  so when Sonarr/Radarr re-grabbed a release that had been synced and imported
  months earlier, the re-appearing remote file was marked Deleted and
  auto-queue skipped it with no error. SeedSyncarr now records when a tracked
  file disappears from both the seedbox and local storage; if it re-appears
  remotely after more than 24 hours of absence, that is treated as a new
  lifecycle (a re-grab) and the stale tracking is cleared so the file syncs
  fresh. The 24-hour threshold prevents a transient empty remote scan from
  clearing tracking en masse (which would re-download still-seeding,
  already-imported files), and the absence clock only advances on successful
  remote scans, so a seedbox outage does not count toward it.
- Fixed interrupted downloads becoming permanently un-queueable. A file was
  marked "downloaded" as soon as its transfer started writing bytes; if the
  transfer was interrupted (app restart, lftp crash) and the partial file
  disappeared, the file was marked Deleted on the next model build and skipped
  by auto-queue forever. Only completed downloads are now tracked. Files that
  did complete and were then moved or deleted by external tools (e.g. a
  Sonarr/Radarr import) still never re-download.
- Fixed a webhook false-import vector. A Sonarr/Radarr "Download" event
  without a source file path fell back to the release title — which for a
  single-file release equals the tracked file name exactly — so such an event
  could mark a file imported (and arm auto-delete) without any real import.
  Import detection now requires `movieFile.sourcePath` /
  `episodeFile.sourcePath`; Download events without it are logged and ignored.
  The failure direction is safe: a missed import means no auto-delete, never a
  wrong one.
- Fixed the dashboard file list being able to freeze silently and render zero
  files: an error while processing a single model update killed the update
  subscription permanently. The view now recovers by rebuilding from the full
  model and keeps processing subsequent updates.
- Fixed the System Event Log spinner never resolving when no log lines arrive
  within the stream's short replay window. It now shows "No recent events"
  once the stream connects.

### Changed

- The initial file list is sent to the browser as a single snapshot event
  instead of one event per file. With hundreds of tracked files, the per-file
  burst forced the frontend through hundreds of re-sort/render cycles on page
  load and could starve the browser main thread.
- Files in the Deleted state that still exist on the seedbox with no local
  copy now show an amber "Skipped (remote)" badge instead of a red "Deleted"
  badge, making intentionally-skipped (and wrongly-stuck) files visible at a
  glance.
- Every webhook import decision is now logged with its provenance (event type
  and the payload field that produced the file name), and ignored webhook
  event types are logged at INFO, so any unexplained import mark can be traced
  to the exact webhook that caused it.

## [1.5.1] - 2026-07-06

A bug-fix release. It stops the container from slowly accumulating defunct
("zombie") child processes over time. Existing config files load unchanged with
no migration step.

### Fixed

- Fixed an accumulation of zombie (`<defunct>`) child processes. The application
  process ran as PID 1 inside the container, and a plain PID 1 does not receive
  the kernel's automatic reaping of children that exit or are reparented to it.
  Because the app spawns `ssh`/`scp` (remote scan) and `lftp` (downloads) on
  every scan cycle, exited children piled up as zombies — over a thousand were
  observed in long-running deployments, which would eventually exhaust the
  process table and prevent new processes from starting. The app is now launched
  under `tini` as the container's init, which reaps these children. Signal
  forwarding is preserved, so container stop/restart behaves exactly as before.
  This is a Docker-image change only; there are no application-code or config
  changes.

## [1.5.0] - 2026-06-22

A reliability and security-maintenance release. It makes the remote scanner
recover automatically from transient network blips instead of going dark until
a manual restart, and clears every outstanding dependency advisory. Existing
config files load unchanged with no migration step.

### Added

- Automatic scanner recovery from transient remote name-resolution failures.
  A scan that hits a momentary DNS/SSH name-resolution error (for example
  `Could not resolve hostname` or a fleeting `Bad hostname`) is now retried
  in-scan with bounded, jittered backoff (a capped number of attempts, never an
  infinite loop) instead of terminating the scanner. The file list keeps
  updating once the blip clears. A genuinely wrong or persistently-unresolvable
  host still surfaces to the operator exactly as before once retries are
  exhausted, so real configuration mistakes still stop and prompt.
- Bounded controller auto-restart. If the controller dies from a
  permanent-class error it now auto-restarts through the existing service
  recovery path instead of staying down indefinitely, with the restart budget
  bounded so an unrecoverable condition cannot become a restart loop. UI-driven
  restarts do not consume the auto-recovery budget.

### Security

- Cleared all 8 open Dependabot alerts (3 high, 5 medium) by merging the
  outstanding dependency PRs and forcing the build-time `piscina` dependency to
  a patched version via an npm override. No runtime image changes — the affected
  packages are build/dev tooling only.

## [1.4.2] - 2026-06-15

A bug-fix and security-maintenance release. It fixes a startup hang that could
leave the container unable to serve after a fresh deploy, and clears the
remaining flagged dependency advisories. Existing config files load unchanged
with no migration step.

### Fixed

- Fixed a startup hang on Linux deployments. The multiprocessing logger forced
  the `spawn` start method, which launched a resource-tracker helper that
  re-execs the interpreter; on some container filesystems that step blocked
  indefinitely, so the web server never started and the container wedged during
  config setup. The logger now uses `fork` where available (Linux), falling
  back to the platform default elsewhere.

### Security

- Updated `cryptography` to 48.0.1, which ships patched OpenSSL in its wheels
  (resolves two high-severity Dependabot alerts).
- Updated `@angular/common` and `@angular/compiler` to 22.0.1, resolving
  high-severity cache-poisoning and date-formatting denial-of-service issues and
  a two-way-binding sanitization bypass.
- Updated the `vite` and `@babel/core` build dependencies to patched versions,
  clearing the remaining flagged build-time advisories.

## [1.4.1] - 2026-06-15

A security-maintenance release. No behavior changes — it pulls in upstream patches for two flagged frontend build/runtime dependencies. Existing config files load unchanged with no migration step.

### Security

- Updated `@angular/core` to 22.0.1, which patches a high-severity client-hydration issue (DOM clobbering and response-cache poisoning) in the Angular runtime (resolves Dependabot alert GHSA-rgjc-h3x7-9mwg).
- Pinned `esbuild` to 0.28.1 to clear two flagged build-time advisories (Dependabot alerts #20 and #21).

## [1.4.0] - 2026-06-03

A hardening and documentation release that closes the remaining public-facing rough edges and rebuilds the project's documentation surface. The one breaking change is the config-set endpoint moving from a GET path to a POST body so credentials no longer travel in URLs or server logs; on-disk config files (including encrypted ones) load unchanged with no migration step.

### Changed

- **Breaking:** Configuration values are now set via `POST /server/config/set` with a JSON body (`{section, key, value}`); the legacy `GET /server/config/set/{section}/{key}/{value}` path has been removed so credential values no longer appear as URL path segments in access logs, browser history, or reverse-proxy logs. The Angular settings page and the end-to-end setup use the new endpoint; saved settings round-trip unchanged.

### Added

- A prominent startup warning when the server binds to a non-loopback interface with no `api_token` configured, so an unauthenticated posture is no longer silent (default behavior unchanged).
- A prominent startup warning when the webhook endpoint is reachable with no `webhook_secret` set and `webhook_require_secret` off (default behavior unchanged).
- A one-time warning when startup falls back to the legacy `~/.seedsync` configuration directory because the configured directory is absent.

### Fixed

- Failures during local file deletion are now logged with context instead of being silently swallowed, so a failed cleanup leaves an observable signal in the logs.
- Background process startup now strips non-picklable thread objects from the subprocess state during serialization (via `__getstate__`), so `AppProcess` subclasses pickle cleanly and the full test suite passes under both `fork` and `spawn` start methods.

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
