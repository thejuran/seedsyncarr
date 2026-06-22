A reliability and security-maintenance release. The remote scanner now recovers on its own from transient network blips instead of going dark until a manual restart, and every outstanding dependency advisory is cleared.

Existing config files (including encrypted ones) load unchanged, with no migration step.

### What changed for you

- **The scanner recovers from transient network blips on its own** — A scan that hit a momentary DNS/name-resolution hiccup (for example "could not resolve hostname" or a fleeting bad-hostname error) used to terminate the scanner, which could leave your file list frozen for a long time until you restarted the container by hand. Those transient failures are now retried in-scan with a short, bounded backoff, so the list keeps updating once the blip clears. A host that is genuinely wrong or persistently unreachable still surfaces the error to you as before once the retries are exhausted — so a real misconfiguration still stops and prompts.
- **The controller restarts itself after a fatal error** — If the controller dies from a permanent-class error, it now auto-restarts through the existing recovery path instead of staying down indefinitely. The restart is bounded, so an genuinely unrecoverable condition can't turn into a restart loop, and a restart you trigger from the UI doesn't eat into the automatic-recovery budget.

### Security

- **Cleared all open dependency advisories** — Merged the outstanding dependency updates and pulled the build-time `piscina` dependency up to a patched version, clearing all 8 open Dependabot alerts (3 high, 5 medium). The affected packages are build/dev tooling only — there are no changes to the running app's dependencies.

### Should you update?

Yes — especially if your seedbox connection ever has brief DNS or network hiccups, where this release keeps the scanner alive and recovering instead of silently freezing.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
