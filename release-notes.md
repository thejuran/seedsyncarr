A reliability release driven by a cluster of real incidents: releases you deleted kept coming back, an auto-delete removed a folder that wasn't SeedSyncarr's to touch, and one bad afternoon the app froze for five hours with nothing in the logs to show why. All of it traced to a single gap — the app frequently failed to record that a download had finished, and every safety decision depended on that record being right.

Existing config and persist files load unchanged; the tracking state repairs itself automatically on first start.

### What changed for you

- **Deleting a local copy finally makes it stay deleted** — Previously there was no way to delete a downloaded release and have it stay gone: as long as the copy remained on the seedbox, the app would re-download it at the next restart (one 33 GB remux re-downloaded within an hour of being deleted). Deleted releases now show the amber "Skipped (remote)" badge and stay put. Want it back? Press Queue — that's now an explicit "download this fresh" instruction.
- **Auto-delete can no longer touch what SeedSyncarr didn't download** — A Sonarr import from a folder belonging to a different app used to be able to trick auto-delete into wiping that entire folder. Auto-delete now demands proof the app itself downloaded a release before deleting anything, and imports without that evidence are logged and ignored.
- **A stuck transfer no longer takes the whole app down** — When lftp wedged, every screen of the app went dead for hours while downloads sat frozen. The app now detects the stall, works around it, and stays responsive while the transfer layer recovers.
- **Logs that survive** — The Synology container log had silently stopped recording for five days, which is why the incidents above were so hard to diagnose. Logs are now also written to rotating files in your config folder, so the next question of "what happened last Tuesday" has an answer.
- **A much quieter log** — The scanner used to write a warning every single second for every in-progress download (about 172,000 lines a day). That noise is gone.
- **Security updates** — All 22 open dependency alerts resolved, including high-severity updates to the encryption library and several web components.

### Should you update?

Yes. If you have ever deleted a release and watched it come back, or found the app frozen with an empty log, this release removes both failure modes at the root — and until you update, every app restart can still re-download previously deleted releases.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
