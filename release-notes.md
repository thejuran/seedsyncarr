A security-maintenance release. No behavior changes — it pulls in upstream patches for two flagged frontend build and runtime dependencies.

Existing config files (including encrypted ones) load unchanged, with no migration step.

### What changed for you

- **Patched a high-severity Angular issue** — Updated `@angular/core` to 22.0.1, which fixes a client-hydration vulnerability (DOM clobbering and response-cache poisoning) in the Angular runtime. There is no change to how the app behaves.
- **Cleared two build-time advisories** — Pinned `esbuild` to 0.28.1 to resolve two flagged build-tooling advisories. This affects only how the frontend is built, not the running app.

### Should you update?

Yes, if you run a build from source or want the patched runtime. The fixes are upstream dependency patches; nothing in SeedSyncarr's own behavior or configuration changes.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
