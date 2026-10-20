# Phase 120 — Sonarr 5 Live Capture Notes (Plan 05)

**Sandbox:** `seedsyncarr-test` (localhost:8801) against `sonarr-v5` (localhost:8990) on the NAS.
**Date:** 2026-10-20 (NAS host clock, -0500; seedsyncarr-test app log clock = host clock + 1h).

## Hygiene

These notes contain no secret values. The sandbox Sonarr key was read into a shell variable from
`/volume1/docker/v5test/sonarr/config.xml` only and was never printed. The production Sonarr,
Radarr and SeedSyncarr config files were not read. The Prowlarr key was read into a variable only for one
read-only `GET /api/v1/indexer` (privacy classification) and never printed. The NAS Tailscale
address appears as `<nas-tailscale-ip>`, docker-network client addresses as `<docker-ip>`, and
seedbox home paths as `~/...`. Image digests are truncated to 12 hex characters. Command output was
limited to status words, counts, HTTP codes, versions, field names and directory or release names.
Raw captures stay on the NAS in the capture directory (mode 0700, files 0600) until Plan 06
sanitizes them and deletes the directory (D-13).

## Capture directories

| Attempt | Path (NAS) | Outcome |
|---------|-----------|---------|
| 1 | `/volume1/docker/v5test/results/son5-capture-20261020-151245` | Failed at the L3 Test-event assertion; the trap tore down the sandbox (see "Teardown after Task 1 failure") |
| 2 | `/volume1/docker/v5test/results/son5-capture-20261020-151815` | Success (current `D`) |

Permission note: `results/` carries an inherited Synology ACL, so `mkdir` under `umask 077` still
produced `drwxrwxrwx+`. Each capture dir and its `sink/` subdir were `chmod 700`'d immediately after
creation. That strips the inherited ACL (`drwx------`, no `+`), and files created afterwards are `0600`.

## Teardown probe (pre-create)

`120-teardown.sh` was copied to `$D/teardown.sh` (0700) and run before any resource existed (attempt 1 dir,
15:12; repeated on the attempt 2 dir, 15:18, with identical output):

```
RESTORED sonarr_url ok
DELUGE per-torrent mode, no client change (no L0 baseline recorded)
RESTORED notifications count=1 son5-capture-present=0
NOTIF_URLS_OK
REMOVED sink (absent)
CHECK sonarr_url=http://sonarr-v5:8989
SANDBOX_RESTORED ok
exit=0
```

## Staged script contract

`$D/run-L1L3.sh` (0700, run as `ssh nas` then `bash "$D/run-L1L3.sh"`) begins:

```
#!/usr/bin/env bash
export D=<capture dir>
OK=0
trap '[ "$OK" = 1 ] || bash "$D/teardown.sh"' EXIT INT TERM HUP
```

and sets `OK=1` as its final statement. `D` is exported so `teardown.sh` picks it up from the environment.

## Rig (L0) — attempt 2, 15:18:19

- `system/status.version` = **5.0.0.2701**, branch `develop`, runtime .NET 10.0.13
- `sonarr-v5`: image id `8b59d172e9b4`, config `linuxserver/sonarr:develop`, RepoDigest `linuxserver/sonarr@sha256:096c4c08d947…`
- `seedsyncarr-test`: image id `5b801f8397d6`, config `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a…`
- Notifications: count 1. `id=1 name=Seedsyncarr impl=Webhook url=http://seedsyncarr-test:8800/server/webhook/sonarr onDownload=true onUpgrade=true onImportComplete=false`. It points at the sandbox, never at prod `seedsyncarr:`.
- Download clients: count 1 (Deluge, `id=1`). Field names: `host,port,useSsl,urlBase,password,tvCategory,tvImportedCategory,recentTvPriority,olderTvPriority,addPaused,downloadDirectory,completedDirectory`. Values: `downloadDirectory=~/v5test-incomplete`, `completedDirectory=~/v5test`, `tvCategory=tv-v5test`.
- `seedsyncarr-test` `sonarr_url=http://sonarr-v5:8989` (baseline)
- `$D/state.env` (0600): `SINK_NAME=son5-webhook-sink`, `DELUGE_CLIENT_ID=1`, `DELUGE_DOWNLOAD_DIR_L0=<the downloadDirectory value>`, `NID=3`

## L1 — SON5-01 Test Connection (attempt 2, 15:18:19 – 15:19:22)

- version before L1: **5.0.0.2701**
- Container-name URL (`http://sonarr-v5:8989`): `testconn-containername` result **success=false**, error `"URL resolves to a private/reserved IP address"` (mentions "private": true). This is the known LAN/private-address limitation (D-02, Reliability item 5). It is **not** a Sonarr 5 failure and does not trigger SON5-05.
- Tailscale URL: `POST /server/config/set` sonarr_url=`http://<nas-tailscale-ip>:8990` returned http=200. `testconn-tailscale` result **success=true version=5.0.0.2701**. The Tailscale-IP count inside `testconn-tailscale.json` = 0.
- Inline restore: `POST /server/config/set` back to `http://sonarr-v5:8989` returned http=200. The read-back printed `RESTORED sonarr_url ok`.
- Settled 60 s (gate reset, Pitfall 6).
- version after L1: **5.0.0.2701** (15:19:22), unchanged, so no rerun was needed. The raw `system/status` body was saved as `$D/system_status.json`.
- Attempt 1 (15:15) produced the identical L1 results.

## L3 setup (attempt 2, 15:19:22 – 15:19:58)

- Sink image: the sandbox's own image by digest, `ghcr.io/thejuran/seedsyncarr@sha256:da6196e0e89a…`. The `:1.7.6` tag is not present locally; only the digest ref exists. `python3 --version` = Python 3.11.17.
- Sink: `son5-webhook-sink`, network `docker_default`, `--label wud.watch=false --restart no`, `--user 1026:100` (so captured bodies are owned by the NAS user, 0600), `/sink` = `$D/sink`. In-network `/healthz` returned **ok**.
- `POST notification` "son5-capture" returned http=201, **id=3** (attempt 1 had created id=2, which its teardown deleted). Re-GET:
  - `id=1 name=Seedsyncarr url=http://seedsyncarr-test:8800/server/webhook/sonarr onDownload=true onUpgrade=true onGrab=false onImportComplete=false`
  - `id=3 name=son5-capture url=http://son5-webhook-sink:8080/ onDownload=true onUpgrade=true onGrab=false onImportComplete=false`
  - `NOTIF_URLS_OK` (exactly 2 connections, none on `seedsyncarr:8800` / `//seedsyncarr/` / `//seedsyncarr:`)
- Creating the notification triggered Sonarr's validation Test POST to the sink (first sink body, `eventType=Test`, 20:19:53Z).
- **Test event to Seedsyncarr** (15:19:53): `POST notification/test` returned http=200. Window evidence in `$D/log-L3-test.txt`:
  ```
  2026-10-20 16:19:53,363 - INFO - web_access (MainProcess/worker 29) - <docker-ip> - - [20/Oct/2026:16:19:53 -0400] "POST /server/webhook/sonarr HTTP/1.1" 200 7 "-" "Sonarr/5.0.0.2701 (alpine 3.24.2)"
  ```
  The response was 200 with the 7-byte body (`Test OK`). In the window: `import enqueued` = 0, `Recorded webhook import` = 0. The app-log line `Sonarr webhook test event received` was **not** emitted (count 0); see the observability finding below.
- **Test event to son5-capture** (15:19:55): http=200. The sink wrote `20261020T201955862607Z-0002.json` with `eventType=Test`, copied to `$D/webhook_test.json` (0600). Top-level keys: `applicationUrl,episodes,eventType,instanceName,series`. Sink meta `user_agent=Sonarr/5.0.0.2701 (alpine 3.24.2)`.
- version after L3 setup: **5.0.0.2701** (15:19:58), unchanged.

### Observability finding (pre-existing, not Sonarr-5-caused)

`src/python/web/handler/webhook.py` logs through `logging.getLogger(__name__)`
(`web.handler.webhook`). That logger is outside the app's configured `seedsyncarr` logger, so its INFO lines
(`<source> webhook test event received`, and any other handler INFO line) reach no handler. The sandbox log has
0 such lines in its whole history. Controller-side lines (`webhook import enqueued`, `Recorded webhook import`)
are logged normally. Test-event acceptance is therefore proven from the access log (200, 7-byte `Test OK`,
`Sonarr/5.0.0.2701` user agent) plus zero import lines in the window. Logged in `deferred-items.md`.

## D-14 inventory (attempt 2, 15:19:58 – 15:21:46)

Indexers on sonarr-v5. Class comes from Prowlarr `privacy`, matched by name; hosts only:

| Indexer | Implementation | Protocol | Search enabled | Host | Class |
|---------|----------------|----------|----------------|------|-------|
| Darkpeers (API) (Prowlarr) | Torznab | torrent | yes | prowlarr | private |
| Luminarr (API) (Prowlarr) | Torznab | torrent | yes | prowlarr | private |
| TorrentDay (Prowlarr) | Torznab | torrent | yes | prowlarr | private |
| DrunkenSlug (Prowlarr) | Newznab | usenet | no | prowlarr | private |
| Nzb.su (Prowlarr) | Newznab | usenet | no | prowlarr | private |
| NZBFinder (Prowlarr) | Newznab | usenet | no | prowlarr | private |
| NZBgeek (Prowlarr) | Newznab | usenet | no | prowlarr | private |
| NzbPlanet (Prowlarr) | Newznab | usenet | no | prowlarr | private |
| iPlayarr | Newznab | usenet | interactive only | gluetun-uk | n/a (usenet-style; no usenet client on sonarr-v5) |

Torrent search indexers: 3. Public: 0. The only download client is Deluge (torrent).

Sandbox series: `Hacks (2021)` unmonitored, files 27/47; `That Mitchell and Webb Look (2006)` unmonitored,
files 0/84. `wanted/missing` total = 0 (both series unmonitored). Queue empty.

Release searches (read-only; only title, size, seeders and indexer kept in `$D/candidates.json`; no guid or magnet):
- That Mitchell and Webb Look S1E1, S1E2 and the season-1 pack: **0 torrent releases**.
- Hacks S4E1 / S4E2 (missing episodes of an existing sandbox series), best fits for 50–500 MB with ≥ 10 seeders:
  - **Hacks S04E01 1080p HEVC x265-MeGusta**: 359 MB, 18 seeders, TorrentDay (private), not rejected
  - Hacks S04E02 1080p HEVC x265-MeGusta: 346 MB, 18 seeders, TorrentDay (private), not rejected
  - Next best (fewer seeders): S04E01 720p HEVC x265-MeGusta, 290 MB, 6 seeders; Darkpeers S04E01 NORDiC 1080p, 638 MB, 5 seeders

INDEXER_CLASS=private-only

Proposed candidate (needs owner consent per D-14): **Hacks S04E01 1080p HEVC x265-MeGusta, 359 MB, 18 seeders,
TorrentDay (private)**, episode of an existing sandbox series (no `POST series` needed).

## Teardown after Task 1 failure

Attempt 1 (`son5-capture-20261020-151245`) exited 1 at `FAIL Seedsyncarr test event not logged`. The assertion
expected the handler's app-log line, which is never emitted (finding above). The trap ran `teardown.sh`:

```
RESTORED sonarr_url ok
DELUGE per-torrent mode, no client change (downloadDirectory matches L0: yes)
DELETED notification http=200
RESTORED notifications count=1 son5-capture-present=0
NOTIF_URLS_OK
REMOVED sink
CHECK sonarr_url=http://sonarr-v5:8989
SANDBOX_RESTORED ok
```

Fresh `ssh nas` session read-back (idempotent rerun, same dir):

```
RESTORED sonarr_url ok
DELUGE per-torrent mode, no client change (downloadDirectory matches L0: yes)
RESTORED notifications count=1 son5-capture-present=0
NOTIF_URLS_OK
REMOVED sink (absent)
CHECK sonarr_url=http://sonarr-v5:8989
SANDBOX_RESTORED ok
exit=0
```

Fix: the Test-event assertion now uses the access-log 200 / 7-byte `Test OK` line from `Sonarr/<build>`, and
requires zero `import enqueued` / `Recorded webhook import` lines in the window. Attempt 2 then ran from the top
in a new dir.

## State at end of Task 1

`son5-webhook-sink` running and notification `son5-capture` (id 3) live, as designed: this is the only success
exit that leaves them up. `seedsyncarr-test` `sonarr_url` = `http://sonarr-v5:8989`. No grab has been made.
The Deluge client is unchanged.
