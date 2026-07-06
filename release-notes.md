A bug-fix release that stops the container from slowly piling up defunct ("zombie") child processes over time.

Existing config files (including encrypted ones) load unchanged, with no migration step.

### What changed for you

- **No more zombie process build-up** — Because of how the app started inside the container, the short-lived helper processes it launches on every scan (the `ssh`/`scp` used for remote scanning and the `lftp` used for downloads) were never cleaned up after they finished. They accumulated as harmless-looking but ever-growing "defunct" entries — over a thousand in long-running setups — which would eventually fill the process table and stop the container from starting anything new. Those helpers are now cleaned up as they exit. Stop and restart behave exactly as before.

### Should you update?

Yes — especially if your container runs for weeks at a time without a restart. This is a Docker-image-only fix with no config or behaviour changes, so updating is low-risk.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
