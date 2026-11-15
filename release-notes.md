SeedSyncarr 1.9.0 adds multiple path pairs: one install can now sync several remote directories, each into its own local directory. This is the setup for an rTorrent seedbox that sorts finished downloads into per-label folders (for example one for Sonarr and one for Radarr). Existing config and state files load unchanged; no new settings are required, and with a single path SeedSyncarr behaves exactly as before.

### What changed in 1.9.0

- **Path pairs** — add remote-to-local directory pairs under Settings → Path Pairs. Each pair has a name, an enabled switch and an AutoQueue switch, and runs its own transfers and scans. Changes apply after a restart. See [Path Pairs](https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/docs/CONFIGURATION.md#path-pairs) for details and an rTorrent per-label example.
- **Your current path becomes the Default pair** — on first start the existing remote and local paths become one pair named Default, which keeps its existing state file, so nothing is re-scanned or re-queued.
- **The file list shows which pair a file is in** — when more than one pair has files, the list gets a Pair column and a pair filter. The same file name in two pairs appears as two rows that you can select and act on separately.
- **Duplicate names across pairs are handled safely** — Sonarr and Radarr do not say which pair they imported from, so an import whose file name exists in more than one pair is logged as ambiguous and nothing is credited or auto-deleted for it.
- **Commands name their pair** — queue, stop, extract and delete act on the pair of the file you picked. A command for a pair that is not active is refused instead of being sent to another pair.

**Do this after updating:**

Nothing is required. To use the feature, open Settings → Path Pairs, add a pair, and restart SeedSyncarr.

### Should you update?

Only if you want more than one remote-to-local directory pair. With a single path nothing changes in how SeedSyncarr behaves.

### Before you upgrade

Make a copy of your settings and state first, so you can go back to 1.8.0 if you need to.

1. **Stop SeedSyncarr** (`docker compose stop seedsyncarr`, or your platform's Stop button) and wait until it has fully stopped.
2. **Copy three files** from your config folder (the folder you mount at `/config`): `settings.cfg`, `controller.persist` and `autoqueue.persist`. Copying them with a `.pre-1.9.0` suffix works well (for example `settings.cfg.pre-1.9.0`). Check the copies are not empty.
3. **Change the image tag to 1.9.0 and start SeedSyncarr**, recreating the container.

### If you need to roll back

1. **Stop SeedSyncarr** and wait until it has fully stopped.
2. **Put the copied files back** in your config folder under their original names (`settings.cfg`, `controller.persist`, `autoqueue.persist`).
3. **Change the image tag back to `ghcr.io/thejuran/seedsyncarr:1.8.0`** (or exactly the image you ran before) and start SeedSyncarr.

1.8.0 ignores `path_pairs.json` and the extra `controller.<pair id>.persist` files and keeps syncing the Default pair, so no data conversion is needed. Pairs you added after upgrading are not synced on 1.8.0, and their downloaded files stay where they are.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
