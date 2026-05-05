Scanner process health check hardening — failed scans no longer clear transfer state, and scanner shutdown/death handling is now explicit and clean.

### Fixed

- Failed remote, local, or active scans are ignored when feeding the model builder, preserving visible transfer state through transient scan failures.
- Scanner dead-process detection now avoids false error reports during shutdown and terminates scanner subprocesses after unexpected failures.
- User-facing scanner failure messages no longer expose internal diagnostic details.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
