Post-redesign cleanup and hardening — encryption at rest for config secrets, pip install support, self-hosted icons, two bug fixes, and a security dependency update.

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

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
