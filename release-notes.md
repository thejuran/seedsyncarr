A hardening and polish release. The focus this time was closing the one place credentials could leak, making a few unsafe defaults visible instead of silent, and tightening up the documentation.

Existing config files (including encrypted ones) load unchanged, with no migration step.

### What changed for you

- **Credentials no longer travel in URLs** — Saving a setting now sends the value in a request body instead of the URL path. Previously, config values (including secrets) could show up in server access logs, browser history, and reverse-proxy logs. This is the one behavior change: the Settings page and setup tooling use the new path automatically, and your saved settings round-trip exactly as before.

### Safer defaults, no longer silent

- **Startup warnings for unsafe setups** — If the server is reachable on a non-loopback address with no API token set, or the webhook is reachable with no secret, you now get a clear warning at startup. Defaults are unchanged — the app just stops being quietly unsafe.
- **Visible delete failures** — If a local cleanup fails, it's now logged with context instead of being silently swallowed, so a failed delete leaves a trace you can find.
- **Loud legacy-config warning** — If startup falls back to the old `~/.seedsync` directory because the configured one is missing, you get a one-time heads-up instead of silently loading a pre-fork config.

### Under the hood

- **Reliable process startup** — Background process startup now serializes cleanly, so the full test suite passes under both process start methods (`fork` and `spawn`).
- **Progress display fix** — Extracted files no longer show a progress bar above 100%.

### Presentation

- Rebuilt the README, `SECURITY.md`, and the community-health files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`), and the repository license is now detected correctly. The security posture is stated plainly so you can see what's protected by default and what the opt-in knobs are for.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
