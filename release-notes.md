A security release. Every time SeedSyncarr 1.0.0 through 1.7.5 started, it printed your settings — including your seedbox password, your Sonarr and Radarr API keys, and your webhook secret and API token — to the container log (what `docker logs` shows). These were readable as plain text unless you had turned on settings encryption. In addition, a configuration error (for example a password containing a `%` sign) could write an error report that included credentials to the application log files under `/config/log`. Anyone who could read those logs could read those credentials. After you update: recreate the container (a restart is not enough — the old container's log stays until the container is removed), rotate those credentials, delete or review the application log files under `/config/log`, and review anywhere your container or application logs were forwarded or backed up. The steps are under "Do this after updating" below.

Existing config and state files load unchanged; no new settings are required.

### What changed in 1.7.6

- **Startup no longer prints your settings** — the container log now shows a single line, `Config ready at /config/settings.cfg`, and nothing from the file.
- **Debug logging hides every secret setting** — when debug logging prints the configuration, every password, key, secret and token is shown as `***REDACTED***`, including any secret setting added in future.
- **A setting containing `%` saves correctly** — before, saving a password or other value with a `%` in it failed, the error (which included the value) was written to the log, and the restart after changing settings stopped. Such values now save and load unchanged.
- **A damaged settings file stops the app instead of being replaced** — if `settings.cfg` can't be read (for example a hand-edited value with a stray `%`), SeedSyncarr now stops with a one-line `Fatal:` message that names the setting but not its value, and leaves the file as it is. Fix the file and start again. Before, it could print the value and replace your settings with defaults.

**Do this after updating:**

1. **Recreate the container**, not just restart it — for example `docker compose up -d --force-recreate seedsyncarr`, or remove the container and create it again. The old container's log, with your credentials in it, is kept until the container is removed.
2. **Rotate your seedbox password and your Sonarr and Radarr API keys**, then enter the new ones in SeedSyncarr Settings.
3. **If you set a webhook secret or API token, rotate those too**, and update the webhook connection in Sonarr/Radarr with the new secret.
4. **Delete or review the application log files under `/config/log`**.
5. **Review any forwarded or backed-up copies of your container or application logs** (log collectors, monitoring tools, backups) and remove the old entries.

### Also in this release if you're upgrading from 1.7.4 (from 1.7.5)

1.7.6 includes everything from 1.7.5. If you are coming from 1.7.4 or earlier, these 1.7.5 changes are new to you as well:

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

Yes, from any version — this is a security fix. If you are coming from 1.7.4 or earlier and use Sonarr or Radarr integration, expect some items to show as Waiting until Sonarr/Radarr report their downloads complete — that is the 1.7.5 fix working. Upgrading takes a few minutes of downtime for the backup step below.

### Before you upgrade

Make a copy of your settings and state first, so you can go back to 1.7.4 if you need to.

1. **Stop SeedSyncarr** (`docker compose stop seedsyncarr`, or your platform's Stop button) and wait until it has fully stopped.
2. **Copy three files** from your config folder (the folder you mount at `/config`): `settings.cfg`, `controller.persist` and `autoqueue.persist`. Copying them with a `.pre-1.7.6` suffix works well (for example `settings.cfg.pre-1.7.6`). Check the copies are not empty.
3. **Change the image tag to 1.7.6 and start SeedSyncarr**, recreating the container (see "Do this after updating" above).
4. **If you use Sonarr or Radarr integration, check both are turned on and reachable** (Settings → the Test button for each). An unreachable app makes its downloads wait.

### If you need to roll back

**Rolling back to 1.7.5 or any earlier version brings back the printing of your settings to the container log on every start.** If you roll back after rotating your credentials, rotate again once you are back on 1.7.6 or later.

**Before rolling back, remove any `%` from secrets you saved on 1.7.6.** 1.7.6 can save a password, key or token that contains `%`; older versions read it but fail the next time they save settings, and that error includes the value. Change any such secret to one without `%` first, or keep `%` out of your secrets until you are back on 1.7.6 or later.

1. **Stop SeedSyncarr** and wait until it has fully stopped.
2. **Put the copied files back** in your config folder under their original names (`settings.cfg`, `controller.persist`, `autoqueue.persist`).
3. **Make sure auto-delete is off in the restored settings.** Open the restored `settings.cfg`, find the `[AutoDelete]` section, and make sure its line reads `enabled = False`. (If there is no `[AutoDelete]` section, auto-delete is already off.) Your copy was made while auto-delete may have been on, and this stops the older version from deleting anything as soon as it starts.
4. **Change the image tag back to `ghcr.io/thejuran/seedsyncarr:1.7.4`** (or exactly the image you ran before) and start SeedSyncarr. Note that 1.7.4 does not wait for Sonarr/Radarr to confirm a download is complete.
5. **Keep auto-delete off** until you have checked in the app that every download you expect to be imported shows as imported. The older version doesn't know about early episode imports that 1.7.5 and later recorded, and could delete those downloads too early.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
