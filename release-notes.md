A safety release. It stops SeedSyncarr from copying a download that is still being written on the seedbox, so Sonarr or Radarr can no longer import a file that is cut short. It also makes sure season-pack episodes imported early are remembered so cleanup finishes, carries two safety fixes held over from 1.7.4, and makes the PyPI package installable again.

Existing config and state files load unchanged; no new settings are required.

### What changed for you

- **A download still in progress on the seedbox is no longer copied early** — when Sonarr or Radarr integration is turned on, SeedSyncarr now asks Sonarr/Radarr whether the download has finished before it starts copying. Before, a file that was still growing on the seedbox could be copied too soon and imported short.
- **Turning on Sonarr or Radarr integration now controls every automatic transfer** — once either integration is on, anything Sonarr/Radarr can't vouch for waits, including items the other app manages. If you use both apps, turn on both integrations and make sure SeedSyncarr can reach them; if only one is on, the other app's downloads will wait with "No matching queue entry".
- **Items that can't be checked show as Waiting, with a reason** — "Sonarr unavailable", "Radarr unavailable", "Ambiguous match", "Still downloading" or "No matching queue entry". SeedSyncarr keeps checking on its own and starts the transfer as soon as the download is confirmed complete. It never gives up and copies anyway just because time has passed.
- **You can still release a waiting item by hand** — pressing Queue on a waiting item asks: "Completion could not be verified. Transfer and release this item anyway?" Your answer applies to that one transfer only; if the item is queued again later, it is checked again. (If you call the API directly, the single-file queue command now answers `428` for such an item unless you add `release_unverified=true`.)
- **Unfinished copies are always hidden** — files are now always written under a temporary `.lftp` name until the copy is complete, so Sonarr/Radarr can never import a half-copied file. The "Rename unfinished/downloading files" setting is gone; if your `settings.cfg` still has the `use_temp_file` line, it is accepted and ignored.
- **Season-pack episodes imported early are remembered** — when Sonarr imports an episode while the rest of the pack is still copying, that import is now saved straight away (it survives a restart), so automatic cleanup can finish once the whole pack is copied and every episode is imported. A notice from Sonarr about the whole pack folder that arrives while the pack is still copying is ignored to stay safe; that pack may need to be cleaned up by hand.
- **Auto-delete and queueing can no longer collide** — a cleanup can't start while a transfer of the same item is being started, and re-queueing an item cancels any cleanup that was scheduled for the earlier attempt.
- **A slow reply from the seedbox connection can't be mistaken for the next answer** — after a command times out, SeedSyncarr now resynchronizes its connection before using it again.
- **PyPI installs work again** — the Python package is fixed and checked on every build.
- **Dependency updates** — cryptography 50.0.2 and pytz 2026.5, plus a build-only update to source-map-js.

**Limitation:** with both Sonarr and Radarr integrations turned off, SeedSyncarr keeps the previous behaviour — it waits for a file's size to stop changing — and **cannot prove the seedbox download finished**. Turning off the integration in SeedSyncarr also doesn't stop another app from watching your download folder. If Sonarr or Radarr imports from your local download folder, turn on the matching integration.

**One-time cleanup:** downloads that already got stuck before this update — shown as Done but never cleaned up — won't clean themselves up. Check that they were imported, then delete them locally once by hand. With temporary files now always on, Delete Local also leaves behind a stopped, partly copied `<name>.lftp` file; remove that by hand too.

### Should you update?

Yes, from any 1.7.x release. If you use Sonarr or Radarr integration, expect some items to show as Waiting until Sonarr/Radarr report their downloads complete — that is the fix working. Upgrading takes a few minutes of downtime for the backup step below.

### Before you upgrade

Make a copy of your settings and state first, so you can go back to 1.7.4 if you need to.

1. **Stop SeedSyncarr** (`docker compose stop seedsyncarr`, or your platform's Stop button) and wait until it has fully stopped.
2. **Copy three files** from your config folder (the folder you mount at `/config`): `settings.cfg`, `controller.persist` and `autoqueue.persist`. Copying them with a `.pre-1.7.5` suffix works well (for example `settings.cfg.pre-1.7.5`). Check the copies are not empty.
3. **Change the image tag to 1.7.5 and start SeedSyncarr.**
4. **If you use Sonarr or Radarr integration, check both are turned on and reachable** (Settings → the Test button for each). An unreachable app makes its downloads wait.

### If you need to roll back

1. **Stop SeedSyncarr** and wait until it has fully stopped.
2. **Put the copied files back** in your config folder under their original names (`settings.cfg`, `controller.persist`, `autoqueue.persist`).
3. **Make sure auto-delete is off in the restored settings.** Open the restored `settings.cfg`, find the `[AutoDelete]` section, and make sure its line reads `enabled = False`. (If there is no `[AutoDelete]` section, auto-delete is already off.) Your copy was made while auto-delete may have been on, and this stops the older version from deleting anything as soon as it starts.
4. **Change the image tag back to `ghcr.io/thejuran/seedsyncarr:1.7.4`** (or exactly the image you ran before) and start SeedSyncarr. Note that 1.7.4 does not wait for Sonarr/Radarr to confirm a download is complete.
5. **Keep auto-delete off** until you have checked in the app that every download you expect to be imported shows as imported. The older version doesn't know about early episode imports that 1.7.5 recorded, and could delete those downloads too early.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
