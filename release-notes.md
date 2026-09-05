A hotfix for one sharp-edged bug: if Sonarr or Radarr grabbed a release while the seedbox was still downloading it, SeedSyncarr could sync a half-written copy — and your library ended up with videos that play fine until they cut off before the end. It happened three times in the week after v1.7.0 shipped, and the app never went back to finish the job.

Existing config files load unchanged; the new setting applies its default automatically.

### What changed for you

- **No more truncated episodes and movies** — SeedSyncarr now waits until a release has stopped growing on the seedbox (90 seconds of stability by default) before starting the transfer, so it never grabs a torrent mid-write. And if a partial copy does end up on disk — a crash, a restart, a race — the app now notices on its own that the remote copy is bigger and finishes the download, no event or manual re-queue required.
- **The trade-off, stated plainly** — new downloads start about 90 seconds later than before. That minute and a half is what buys the guarantee that what lands in your library is complete.
- **Tunable if you want it** — a new `remote_stability_seconds` setting controls the wait (0 turns the gate off entirely).

### Should you update?

Yes. Until you do, any release grabbed while the seedbox is still downloading it can be imported into your library truncated — and nothing will ever come back to fix it.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
