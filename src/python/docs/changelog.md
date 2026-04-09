# Changelog

All notable changes to SeedSyncarr are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

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

[1.0.0]: https://github.com/thejuran/seedsyncarr/releases/tag/v1.0.0
