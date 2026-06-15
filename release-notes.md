A bug-fix and security-maintenance release. It fixes a startup hang that could leave a freshly deployed container unable to serve, and clears the remaining flagged dependency advisories.

Existing config files (including encrypted ones) load unchanged, with no migration step.

### What changed for you

- **Fixed a startup hang on fresh deploys** — On some Linux container setups the app could come up but never start serving, because the logger forced a multiprocessing mode that launched a helper process that hung during startup. The logger now uses the right mode for the platform, so the server starts reliably.

### Security

- **Patched cryptography** — Updated to a release that bundles patched OpenSSL (two high-severity advisories).
- **Patched Angular** — `@angular/common` and `@angular/compiler` updated to 22.0.1, resolving high-severity cache-poisoning and denial-of-service issues and a sanitization bypass.
- **Patched build tooling** — `vite` and `@babel/core` updated to clear the remaining build-time advisories. These affect only how the app is built, not the running app.

### Should you update?

Yes — especially if you run on Linux/Docker, where this release fixes the startup hang.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
