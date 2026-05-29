Security and maintenance update for SeedSyncarr.

This release clears a high-severity advisory in a transitive Angular test-toolchain dependency (`tmp`) and refreshes development tooling and Angular framework dependencies. The vulnerable package is not present in the published Docker runtime, but the lockfile has been updated so the advisory is resolved.

No configuration changes or migrations are required.

### Security

- Updated `tmp` to 0.2.7 to address GHSA-ph9p-34f9-6g65 / CVE-2026-44705 (path traversal via unsanitized prefix/postfix).

### Changed

- Updated Angular framework and CLI to 21.2.14, along with TypeScript ESLint 8.60.0 and Sass 1.100.0.
- Updated development tooling: Puppeteer 25.1.0, Ruff 0.15.14, and testfixtures 12.0.0.


**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
