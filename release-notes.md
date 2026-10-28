SeedSyncarr 1.8.0 is a reliability release: it fixes a second credential-exposure issue alongside the Test Connection URL fix, and repairs three smaller startup, shutdown and browser-tab issues found during testing. Everyone running 1.7.6 should update. Existing config and state files load unchanged; no new settings are required.

### What changed in 1.8.0

- **A crafted URL could redirect Test Connection** — a specially crafted Sonarr/Radarr URL could trick Test Connection into reaching a different address than the one shown, because the check and the connection library could read a backslash differently. Test Connection now checks the exact URL it connects to, and also now refuses multicast addresses, deprecated IPv6 site-local addresses, and a handful of cloud-metadata addresses the previous check missed.
- **The app token was sent to GitHub** — versions 1.0.0 through 1.7.6 sent your configured API token to GitHub's update-check request on every page load. GitHub rejected it, and no other destination ever received it. 1.8.0 sends the token only to SeedSyncarr's own API — which also means the update-availability notice now works correctly if you have a token configured (GitHub's rejection had been silently hiding it).
- **Test Connection now accepts LAN and Docker addresses** — Sonarr/Radarr Test Connection accepts local network addresses and Docker container names (for example `http://sonarr:8989`), not just addresses it previously allowed; `localhost` and other loopback addresses are accepted only on port 8989 or 7878. Malformed or ambiguous URLs (spaces, backslashes, a username/password in the URL, a query string, etc.) are refused with a specific reason.
- **Webhook test events now appear in the log, and a dropped hold is labeled correctly** — testing a webhook from Sonarr/Radarr now shows up in the application log, and a completion hold that is dropped without a release is now logged as "dropped" instead of "cleared".
- **Startup and shutdown clean up correctly** — if startup fails partway through, the parts that already started are shut down cleanly; one part failing to shut down no longer stops the rest from shutting down.
- **Backgrounded browser tabs catch back up** — a slow or backgrounded browser tab now catches up to the current state instead of falling further behind, with bounded memory use.

**Do this after updating:**

1. If you use Sonarr or Radarr integration, press **Test** for each connection in Settings — you can now enter a container name (for example `http://sonarr:8989`) if that's easier than an IP address.
2. Only if you have an API token configured: rotating it is a cheap precaution, not required.

Nothing else is required.

### Should you update?

Yes, from any version. The security fixes and the reliability fixes in this release apply to everyone, regardless of which version you're currently running.

### Before you upgrade

Make a copy of your settings and state first, so you can go back to 1.7.6 if you need to.

1. **Stop SeedSyncarr** (`docker compose stop seedsyncarr`, or your platform's Stop button) and wait until it has fully stopped.
2. **Copy three files** from your config folder (the folder you mount at `/config`): `settings.cfg`, `controller.persist` and `autoqueue.persist`. Copying them with a `.pre-1.8.0` suffix works well (for example `settings.cfg.pre-1.8.0`). Check the copies are not empty.
3. **Change the image tag to 1.8.0 and start SeedSyncarr**, recreating the container.
4. **If you use Sonarr or Radarr integration, check both are turned on and reachable** (Settings → the Test button for each). An unreachable app makes its downloads wait.

### If you need to roll back

1. **Stop SeedSyncarr** and wait until it has fully stopped.
2. **Put the copied files back** in your config folder under their original names (`settings.cfg`, `controller.persist`, `autoqueue.persist`).
3. **Make sure auto-delete is off in the restored settings.** Open the restored `settings.cfg`, find the `[AutoDelete]` section, and make sure its line reads `enabled = False`. (If there is no `[AutoDelete]` section, auto-delete is already off.)
4. **Change the image tag back to `ghcr.io/thejuran/seedsyncarr:1.7.6`** (or exactly the image you ran before) and start SeedSyncarr.
5. **Keep auto-delete off** until you have checked imports in the app.

No data conversion is needed — 1.8.0 did not change the settings or state file formats, so 1.7.6 reads them unchanged. Percent signs (`%`) in a saved password, key or token are handled the same way on 1.7.6 as on 1.8.0, so there is no extra step for those.

Rolling back brings back the two security issues fixed in 1.8.0: the Test Connection URL handling issue and the API token being sent to GitHub's update check.

If you saved a Sonarr/Radarr address as a Docker container name on 1.8.0, Test Connection on 1.7.6 will refuse it with a "private/reserved IP address" message — syncing itself is unaffected, since Test Connection's check isn't used by the actual transfer path. Switch to the LAN IP address if you need the Test button to work on 1.7.6.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
