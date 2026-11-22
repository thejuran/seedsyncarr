SeedSyncarr 1.8.1 is a small patch release with two fixes. Existing config and state files load unchanged; no configuration changes are needed.

### What changed in 1.8.1

- **API keys with stray spaces now work** — a Sonarr or Radarr API key saved with spaces or tabs around it, for example from copy-paste, now works for saving, Test Connection and queue checks alike. A missing or malformed key holds downloads safely instead of being sent.
- **Stopping or restarting no longer hangs** — stopping or restarting SeedSyncarr no longer hangs or leaves the web server half-stopped, and one part of the web service failing to stop no longer prevents the rest from stopping.

### Should you update?

Yes if you use Sonarr or Radarr integration, or if you have seen a slow or stuck stop or restart. The update is safe for everyone.

### Before you upgrade

Make a copy of your settings and state first, so you can go back to 1.8.0 if you need to.

1. **Stop SeedSyncarr** (`docker compose stop seedsyncarr`, or your platform's Stop button) and wait until it has fully stopped.
2. **Copy three files** from your config folder (the folder you mount at `/config`): `settings.cfg`, `controller.persist` and `autoqueue.persist`. Copying them with a `.pre-1.8.1` suffix works well (for example `settings.cfg.pre-1.8.1`). Check the copies are not empty.
3. **Change the image tag to 1.8.1 and start SeedSyncarr**, recreating the container.
4. **If you use Sonarr or Radarr integration, check both are turned on and reachable** (Settings → the Test button for each). An unreachable app makes its downloads wait.

### If you need to roll back

1. **Stop SeedSyncarr** and wait until it has fully stopped.
2. **Put the copied files back** in your config folder under their original names (`settings.cfg`, `controller.persist`, `autoqueue.persist`).
3. **Make sure auto-delete is off in the restored settings.** Open the restored `settings.cfg`, find the `[AutoDelete]` section, and make sure its line reads `enabled = False`. (If there is no `[AutoDelete]` section, auto-delete is already off.)
4. **Change the image tag back to `ghcr.io/thejuran/seedsyncarr:1.8.0`** (or exactly the image you ran before; if you pin by digest, 1.8.0 is `sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`) and start SeedSyncarr.
5. **Keep auto-delete off** until you have checked imports in the app.

No data conversion is needed — 1.8.1 did not change the settings or state file formats, so 1.8.0 reads them unchanged, including API keys saved by 1.8.1. Percent signs (`%`) in a saved password, key or token are handled the same way on 1.8.0 as on 1.8.1, so there is no extra step for those.

Rolling back brings back only the two issues fixed in 1.8.1: an API key with stray spaces can be rejected by Sonarr or Radarr again, and a stop or restart can hang again. The security fixes from 1.8.0 remain in place.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
