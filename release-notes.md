Security and maintenance update for SeedSyncarr.

This release updates the bundled Python HTTP dependency stack to address a high-severity urllib3 advisory affecting compressed streaming responses. SeedSyncarr does not appear to use the affected streaming paths directly, but published Docker/PyPI builds now include the patched dependency.

No configuration changes or migrations are required.

### Security

- Updated urllib3 to 2.7.0 to address GHSA-mf9v-mfxr-j63j / CVE-2026-44432.

### Changed

- Refreshed frontend and Python runtime dependencies, including timezone data.
- Updated frontend build dependencies and resolved dependency advisory coverage in the web UI toolchain.
- Improved release validation so future published versions are checked against their release metadata before publishing.


**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
