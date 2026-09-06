A hotfix for a bug that v1.7.1 introduced: the moment a download finished, SeedSyncarr could immediately start downloading it again. If you imported the finished file into Sonarr or Radarr in that window, the import was ignored, a duplicate copy was pulled from the seedbox, and the original was never cleaned up.

Existing config files load unchanged; the new setting applies its default automatically.

### What changed for you

- **Finished downloads stay finished** — the app now waits for a fresh look at the local folder before deciding a file needs re-syncing, so a transfer that just completed is recognised as complete instead of being mistaken for a stranded partial. Imports that follow are recorded and cleaned up as intended.
- **The v1.7.1 guarantee still holds** — a genuinely half-finished copy on disk is still picked up and completed automatically; it just starts about 30 seconds later than before.
- **Tunable if you want it** — a new `local_stability_seconds` setting controls the wait (0 turns the gate off entirely).

### Should you update?

Yes, if you are on v1.7.1. Until you do, every completed download risks being re-downloaded in full, and the import that follows may be ignored.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
