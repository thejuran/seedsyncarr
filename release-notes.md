A safety patch. It closes three ways SeedSyncarr could lose or damage data: crediting a Sonarr/Radarr import to the wrong download, mistaking a momentary hiccup in the seedbox connection for "nothing is downloading", and corrupting its own saved settings and state when a save failed partway. It also carries the extraction and auto-delete fixes that were written up as 1.7.3 but never shipped.

Existing config and state files load unchanged; no new settings are required.

### What changed for you

- **Imports go to the right download** — when a file name reported by Sonarr or Radarr matches more than one release, SeedSyncarr now rejects the import and logs a warning naming the candidates, instead of guessing. Nothing is recorded as imported and nothing is deleted for it.
- **A blip in the seedbox connection no longer looks like "finished"** — while SeedSyncarr briefly can't get download status from the seedbox, active downloads keep their Downloading/Queued state. Nothing is marked downloaded, re-queued, deleted or extracted on that cycle, and nothing is treated as finished based on a failed check.
- **Stop can report an error instead of a false success** — if you press Stop while SeedSyncarr briefly can't get download status from the seedbox, you now see the message "Lftp error", nothing is marked stopped, and you can retry once status recovers. Before, Stop could say it had succeeded while the download kept going.
- **Saved settings and state survive a failed save** — settings and state files are now written to a temporary file next to the original and swapped in only when complete, so a crash or full disk mid-save leaves the previous good copy in place instead of an empty file that resets your settings on the next start.
- **Extraction output is never half-visible to Sonarr/Radarr** — archives are unpacked into a hidden staging folder and moved into place only once complete, so an import can no longer pick up a partly-extracted file.
- **Auto-delete retries instead of giving up** — a cleanup that had to wait (for example, because extraction was still running) is now retried automatically for about two hours instead of being silently abandoned.

### Should you update?

Yes, from any 1.7.x release. Compared with v1.7.2, the last published release, every change above is a fix; the Stop change is the only difference in behavior you may notice. Upgrading takes a few minutes of downtime for the backup step below.

### Before you upgrade

Make a copy of your settings and state first, so you can go back to 1.7.2 if you need to.

1. **Stop SeedSyncarr** (`docker compose stop seedsyncarr`, or your platform's Stop button) and wait until it has fully stopped. Older versions can wipe a state file if they are cut off in the middle of saving it, so copy the files only once the app is stopped.
2. **Copy three files** from your config folder (the folder you mount at `/config`): `settings.cfg`, `controller.persist` and `autoqueue.persist`. Copying them with a `.pre-1.7.4` suffix works well (for example `settings.cfg.pre-1.7.4`). Check the copies are not empty.
3. **Change the image tag to 1.7.4 and start SeedSyncarr.**

### If you need to roll back

1. **Stop SeedSyncarr** and wait until it has fully stopped.
2. **Put the copied files back** in your config folder under their original names (`settings.cfg`, `controller.persist`, `autoqueue.persist`).
3. **Make sure auto-delete is off in the restored settings.** Open the restored `settings.cfg`, find the `[AutoDelete]` section, and make sure its line reads `enabled = False`. (If there is no `[AutoDelete]` section, auto-delete is already off.) Your copy was made while auto-delete may have been on, and this stops the older version from deleting anything as soon as it starts.
4. **Change the image tag back to the version you ran before** — for most people `ghcr.io/thejuran/seedsyncarr:1.7.2` — and start SeedSyncarr. If you had pinned a different image, go back to exactly that one.
5. **Keep auto-delete off** until you have checked in the app that every download you expect to be imported shows as imported. The older version doesn't know about imports that 1.7.4 refused to match, and could delete those downloads too early.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
