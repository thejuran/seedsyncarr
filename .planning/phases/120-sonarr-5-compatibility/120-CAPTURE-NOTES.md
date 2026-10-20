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

## D-14 decision (Task 2 checkpoint, 2026-10-20)

Option chosen: **owner-adds-indexer-or-content**. The owner's words: "Choose other content first. The
compatibility test doesn't need that specific episode or private-tracker ratio usage. Prefer content you're
authorized to download, available through the sandbox Sonarr workflow. Tear down the temporary sink and
notification."

- The proposed candidate (Hacks S04E01, TorrentDay) is **rejected**. No private-tracker grab is made, from
  TorrentDay, Darkpeers, Luminarr or any other private indexer.
- The grab must use content the owner is authorized to download, through the normal sandbox Sonarr-v5 workflow
  (an indexer or content the owner supplies or chooses). Plan 05 waits for that choice before Task 3.

## Teardown at Task 2 (owner-adds-indexer-or-content)

Capture dir (raw captures kept on the NAS per D-13, mode `drwx------`):
`/volume1/docker/v5test/results/son5-capture-20261020-151815`

The sonarr-v5 version before teardown was **5.0.0.2701**. Teardown run (`bash "$D/teardown.sh"`):

```
RESTORED sonarr_url ok
DELUGE per-torrent mode, no client change (no L0 baseline recorded)
DELETED notification http=200
RESTORED notifications count=1 son5-capture-present=0
NOTIF_URLS_OK
REMOVED sink
CHECK sonarr_url=http://sonarr-v5:8989
SANDBOX_RESTORED ok
exit=0
```

The "no L0 baseline recorded" line means `D` was set but not exported in that `ssh` shell, so `teardown.sh` did
not read `state.env`. Cleanup by name (the notification and the sink) does not depend on `state.env`. I reran
the teardown idempotently with the directory passed as an argument (`bash "$D/teardown.sh" "$D"`):

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

Independent read-back after teardown:
- `son5-webhook-sink` containers (`ps -a`): 0
- sonarr-v5 notifications: only `id=1 name=Seedsyncarr`, with its URL on `http://seedsyncarr-test:8800/`.
  `son5-capture` (id 3) is gone.
- `seedsyncarr-test` `sonarr_url=http://sonarr-v5:8989`
- Deluge client id=1: enabled, `tvCategory=tv-v5test`, and `downloadDirectory` equals the recorded
  `DELUGE_DOWNLOAD_DIR_L0` (compared on the NAS without printing it)
- The sonarr-v5 version after teardown was still **5.0.0.2701** (D-07). The queue is empty and no grab was made.

### Resume requirements (before Task 3)

Teardown removed Task 1's L3 setup. On resume, re-create it before Task 3:
1. Make a new capture dir (or reuse the one above), `chmod 700` it and its `sink/` subdir, then copy
   `120-teardown.sh` → `$D/teardown.sh`. Always **export** `D`, or pass `"$D"` as an argument, when you run teardown.
2. Re-check the rig (L0): sonarr-v5 version 5.0.0.2701, notification count 1, Deluge `downloadDirectory` L0
   recorded in `state.env`.
3. Re-start `son5-webhook-sink` (same digest image, `--user 1026:100`, `docker_default`, `--label wud.watch=false
   --restart no`) and re-create notification `son5-capture` (onDownload/onUpgrade). Record the new `NID` in
   `state.env` and re-confirm `NOTIF_URLS_OK`.
4. Use only the authorized content or indexer the owner supplies. L1 does not need to be rerun unless the
   sonarr-v5 version changed.

## D-14 decision revised (2026-10-20, owner)

After hearing the ratio cost and the hit-and-run risk, the owner said: "yes go ahead with Hacks S04E01".
D-14 is now **grab-private**: grab **Hacks S04E01 1080p HEVC x265-MeGusta** (about 359 MB) from **TorrentDay**
through sandbox sonarr-v5 (`POST release {guid, indexerId}`, so Sonarr's queue tracks it). This replaces the
earlier "Choose other content first" answer (owner-adds-indexer-or-content, above). Only this episode is
approved. S04E02 from the same group and tracker is the only pre-approved alternate; if S04E01 is gone, stop
and ask.

Added owner requirement, **keep seeding**: the torrent must never be removed from Deluge. That rules out
removing or deleting the torrent or its data, `removeFromClient`, and queue DELETE, at any point including
teardown, so there is no hit-and-run on TorrentDay.

## Teardown fix before resume (Step 0)

Bug found at Task 2: `teardown.sh` only knew the capture dir from env `D`. Run as `bash "$D/teardown.sh"`
without exporting `D`, it skipped the Deluge check and still printed `SANDBOX_RESTORED ok`. Fixed in commit
`ea8c85c`:
- `D` defaults to the script's own directory, since it is copied into the capture dir.
- These now FAIL (`SANDBOX_RESTORED FAIL deluge`, exit 1): a missing `state.env`; `MODE=A` without
  `DELUGE_DOWNLOAD_DIR_L0`; and `MODE=B` without `DELUGE_CLIENT_ID` or `downloadclient-orig.json`.
- The script never touches a torrent.

Proven on the NAS from a scratch dir, with `D` unset each time:
- no `state.env`: FAIL deluge, exit=1
- `MODE=B` without the saved JSON: FAIL deluge, exit=1
- a valid `state.env`: `DELUGE per-torrent mode, no client change (downloadDirectory matches L0: yes)`,
  `SANDBOX_RESTORED ok`, exit=0

The scratch dir was then removed.

## Resume attempt 3 (capture dir `/volume1/docker/v5test/results/son5-capture-20261020-163945`)

The dir and `sink/` are `drwx------`. The staged files are `teardown.sh` (fixed copy), `dlib.sh` (shared
helpers), `l0.sh`, `probe.sh`, `run-L3setup.sh`, `run-L2.sh`, `streamhold.py`, `s02.sh` and `tstat.sh`.

### L0 (15:39)
- `system/status.version` = **5.0.0.2701**. Image ids are unchanged: sonarr-v5 `8b59d172e9b4`,
  seedsyncarr-test `5b801f8397d6`.
- Notifications: count 1 (`Seedsyncarr` → `http://seedsyncarr-test:8800/server/webhook/sonarr`).
- Deluge client id 1: `enable=true removeCompletedDownloads=false removeFailedDownloads=false`,
  `downloadDirectory=~/v5test-incomplete`, `completedDirectory=~/v5test`, `tvCategory=tv-v5test`,
  `useSsl=true`, `urlBase=/deluge`. The Sonarr API returns the Deluge password field **masked**.
- TorrentDay (Prowlarr) on sonarr-v5: `seedCriteria.seedRatio` and `seedTime` are empty, so Sonarr sets no
  stop ratio on the torrent.
- seedsyncarr-test: `sonarr_url=http://sonarr-v5:8989`. AutoDelete is `enabled=true dry_run=false delay=300`;
  it deletes only the local NAS copy, never the seedbox data. Remote stability is 90 s; the remote scan runs
  every 30 s.
- The queue is empty. `state.env` keys are `SINK_NAME DELUGE_CLIENT_ID DELUGE_DOWNLOAD_DIR_L0`.
- Teardown probe (pre-create), run **without** `D` exported (this exercises the fix): `RESTORED sonarr_url ok`,
  `DELUGE per-torrent mode, no client change (downloadDirectory matches L0: yes)`,
  `RESTORED notifications count=1 son5-capture-present=0`, `NOTIF_URLS_OK`, `REMOVED sink (absent)`,
  `SANDBOX_RESTORED ok`, exit=0.

### MODE A probe (read-only)
The Deluge password is read from the sandbox Sonarr DB (`/volume1/docker/v5test/sonarr/sonarr.db`, read-only
SQLite, into a variable, never printed), because the API masks it. Results: `DELUGE_AUTH http=200 result=true`,
`DELUGE_WEB_CONNECTED true`. Label `tv-v5test` has 11 torrents. No existing S04E01 or S04E02 torrent.

### L3 setup (15:41, `run-L3setup.sh`, failure-only trap → teardown)
- Version before: 5.0.0.2701. Sink `son5-webhook-sink` uses the same digest image, `--user 1026:100`; `SINK_HEALTHZ ok`.
- `NOTIF_CREATE http=201 id=4` (NID=4 in `state.env`). Connections: id 1 `Seedsyncarr` →
  `seedsyncarr-test:8800`; id 4 `son5-capture` → `http://son5-webhook-sink:8080/` (onDownload/onUpgrade true,
  onGrab false). `NOTIF_URLS_OK`.
- Test → Seedsyncarr at 15:41:46, http=200. Access log
  `2026-10-20 16:41:46,615 ... <docker-ip> ... "POST /server/webhook/sonarr HTTP/1.1" 200 7 "-" "Sonarr/5.0.0.2701 (alpine 3.24.2)"`;
  import lines in the window = 0.
- Test → son5-capture at 15:41:54, http=200. The sink wrote `20261020T204154668414Z-0002.json`, copied to
  `webhook_test.json` (eventType Test; keys `applicationUrl,episodes,eventType,instanceName,series`;
  `user_agent=Sonarr/5.0.0.2701 (alpine 3.24.2)`).
- Version after: 5.0.0.2701. `L3SETUP_OK`.

### Task 3 run (`run-L2.sh`, detached with nohup; `trap 'bash "$D/teardown.sh"' EXIT INT TERM HUP`)
- `V_BEFORE 5.0.0.2701` at 15:44:20. `MODE=A` was appended before any Deluge action.
- Candidate: `Hacks S04E01 1080p HEVC x265-MeGusta`, 359 MB, 18 seeders, TorrentDay (Prowlarr), rejected=false.
  Episode id 28 (series 1, hasFile=false).
- **`GRAB http=200` at 15:44:28** (NAS host time) via `POST release {guid, indexerId}`. This is the only grab
  made in this plan.
- `TORRENT_SEEN` in Deluge at 15:44:29, progress 16%. On the capture torrent only:
  `core.set_torrent_options` set `stop_at_ratio=false remove_at_ratio=false max_download_speed=256` (error null),
  so Deluge never auto-pauses or removes it at a ratio. `core.move_storage` to `completedDirectory` (error null),
  result true at 15:44:31, state Downloading, progress 32%. The speed cap keeps a real "downloading" window
  open on a fast seedbox.
- From 15:45 the Sonarr queue showed the target as `downloading` with `sizeleft` falling (256,671,744 →
  172,474,368), and the root appeared in the seedsyncarr-test model (`default`, remote size 374,536,741).
- **Blocker (environmental):** the seedbox refused SSH on port 22 from the NAS starting 15:45 host time
  (`Connection refused`; Deluge Web on 443 stayed reachable). seedsyncarr-test reported
  `latest_remote_scan_failed: true`, so the 90 s remote-stability window could not advance and the root never
  reached the completion gate. With the torrent due to finish in about 12 min, the window would have been lost.
- At about 15:50 the speed cap was cut to 4 KiB/s (the torrent stays in Downloading, not paused). `run-L2.sh`
  was then stopped with SIGKILL, so its trap did not run (see the trap flaw below).
  `CAPTURE_STATUS=FAILED` and `CAPTURE_NOTE=seedbox-ssh-refused-run-killed` were appended to `state.env`.
  Teardown was run by hand:
  ```
  RESTORED sonarr_url ok
  DELUGE per-torrent mode, no client change (downloadDirectory matches L0: yes)
  DELETED notification http=200
  RESTORED notifications count=1 son5-capture-present=0
  NOTIF_URLS_OK
  REMOVED sink
  CHECK sonarr_url=http://sonarr-v5:8989
  SANDBOX_RESTORED ok
  exit=0
  ```
- Trap flaw found: `trap 'bash "$D/teardown.sh"' EXIT INT TERM HUP` does not exit on INT/TERM/HUP, so after a
  signal the trap tears down and then the script keeps looping. Future staged scripts should use
  `trap 'exit 130' INT TERM HUP; trap 'bash "$D/teardown.sh"' EXIT`.
- Seedbox SSH recovered at 15:55:47 (tcp/22 open; `latest_remote_scan_failed: false` at 15:56:16).

### SON5-02 milestone 1 captured after recovery (read-only, 15:57)
Once scans recovered, the gate evaluated the root. Saved without touching the torrent:
- `queue_details_incomplete.json` (15:57:14): `Hacks.S04E01.1080p.HEVC.x265-MeGusta`, `status=downloading`,
  `trackedDownloadState=downloading`, `sizeleft=165052416`, output basename = the root.
- `log-L2-incomplete.txt`:
  ```
  2026-10-20 16:55:50,109 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta': Still downloading
  ```
- `stream-L2-incomplete.txt`: `root=Hacks.S04E01.1080p.HEVC.x265-MeGusta hold_reason=still_downloading`
  (2 string `hold_reason` values in the stream).
- The sink and `son5-capture` notification were **not** live at that moment (torn down at 15:50), so the
  Download webhook for this torrent cannot be captured until they are re-created **before** it completes.

### Owner update (coordinator, about 15:56): use the owner-added Hacks S02 download instead
Read-only findings (`s02.sh`, 15:56:50; no torrent touched):
- sonarr-v5 `queue/details`: 1 record (S04E01 only). `queue?includeUnknownSeriesItems=true`: total 1 (S04E01
  only). **The S02 download is not in sonarr-v5's queue.**
- Deluge (read-only status), Hacks S02 torrents:
  - `Hacks 2021 S02 1080p BluRay x265 HEVC 10bit AAC 5 1-Vyndros`: label **`tv-v4test`**, Seeding, 100%,
    about 6,012 MB, save dir `v4test`, added about 6 min earlier. This is the owner's new torrent: wrong
    category for sonarr-v5 and already complete.
  - `Hacks S02 1080p BluRay x264-BRAVERY`: label `tv-v5test`, Seeding, 100%, about 24,099 MB, added about 21 h
    earlier (imported on 2026-10-19).
- sonarr-v5 Hacks episode files: S1 10 (SDTV), **S2 8 of 8 (Bluray-1080p)**, S3 9. S2 episodes monitored: 0.
- seedsyncarr-test model: `Hacks S02 1080p BluRay x264-BRAVERY` is `deleted` (auto-deleted locally on
  2026-10-19). The Vyndros root is not in the model; it sits under `v4test`, which seedsyncarr-test does not scan.
- S04E01 at 15:56:50: Downloading, 56%, `max_download_speed=4`, `stop_at_ratio=false`,
  `remove_at_ratio=false`, save dir `v5test`.

Re-check at 15:58:22, after the owner said the S02 torrent is in `tv-v5test` (read-only):
- Every Hacks torrent in Deluge, in any label: S01 XviD-AFG, the S02 BRAVERY pack and S03E01–E09 BRAVERY are all
  in `tv-v5test`, 100%, Seeding, added 4 h or more earlier. S04E01 MeGusta is in `tv-v5test`, Downloading, 56%,
  added 13 min earlier. **The Vyndros S02 pack is in `tv-v4test`**, 100%, Seeding, added 8 min earlier.
- No torrent was added to `tv-v5test` in the last 2 h other than S04E01.
- sonarr-v5 `queue?includeUnknownSeriesItems=true`: total 1 (S04E01, `downloading`, `sizeleft=164757504`).

### Teardown read-back (fresh session, 15:57)
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
`son5-webhook-sink` containers (`ps -a`): 0. Raw files are 0600 and include 76 `queue-<epoch>.json` snapshots,
`queue_details_incomplete.json`, `log-L2-incomplete.txt`, `stream-L2-incomplete.txt`, `webhook_test.json`,
`log-L3-test.txt`, `grab.json`, `releases-summary.json` (title/size/seeders/indexer only) and `run-L2.out`.

## Owner decision: resume-s04e01 = lift-cap-and-capture (2026-10-20)

The owner chose option 1 and approved one change only: removing the per-torrent download speed cap on the
S04E01 torrent. The torrent is not removed or paused, stop/remove-at-ratio stay off, and it keeps seeding.
The S02 pack is not used: it is not in sonarr-v5's queue, it is in label `tv-v4test`, and Sonarr already has
all 8 S02 files.

### Re-baseline (16:00, same capture dir, so the incomplete evidence stays alongside)
`l0.sh`: version **5.0.0.2701**, image ids unchanged, notifications count 1 (`Seedsyncarr` → seedsyncarr-test),
Deluge client unchanged (`downloadDirectory=~/v5test-incomplete`, `removeCompletedDownloads=false`),
`sonarr_url=http://sonarr-v5:8989`, queue total 1 (S04E01). Teardown probe: `SANDBOX_RESTORED ok`, exit=0.

### L3 setup re-created (16:01, `run-L3setup.sh` with the fixed trap)
`trap 'exit 130' INT TERM HUP` + `trap '[ "$OK" = 1 ] || bash "$D/teardown.sh"' EXIT`. `SINK_HEALTHZ ok`;
`NOTIF_CREATE http=201 id=5` (NID=5); `NOTIF_URLS_OK` (id 1 → seedsyncarr-test, id 5 → son5-webhook-sink).
Test → Seedsyncarr http=200 (access log `200 7` from `Sonarr/5.0.0.2701 (alpine 3.24.2)`, import lines 0);
Test → sink http=200 (eventType Test, `webhook_test.json` refreshed). Version before/after: 5.0.0.2701.

### Completion capture (`run-M2.sh`, detached; `trap 'exit 130' INT TERM HUP` + `trap 'bash "$D/teardown.sh"' EXIT`)
The monitor attaches to the existing `CAPTURE_TORRENT_ID` and makes no grab. The cap was lifted only after the
monitor started.
- `V_BEFORE 5.0.0.2701` at 16:01:31; pre-lift snapshot of the same downloadId: `status=downloading sizeleft=164118528`.
- **`CAP_LIFTED max_download_speed=-1 error=null` at 16:01:32**, leaving Downloading 56.6%, `stop_at_ratio=false`,
  `remove_at_ratio=false`. The pre-cap value was not recorded before the first cap; -1 (unlimited) is
  Deluge's default, and Sonarr sets no speed limit.
- `HOLD_CLEARED` seen at 16:01:51 (host time).
- **M2 COMPLETE at 16:02:22**: `queue_details_complete.json` has the same downloadId with `status=completed`,
  `sizeleft=0`, `trackedDownloadState=importPending`, `trackedDownloadStatus=warning` (Sonarr is waiting
  for the file to land on the NAS).
- **M3 WEBHOOK at 16:05:24**: sink `20261020T210521790007Z-0003.json` → `webhook_download.json`, eventType
  `Download`, `isUpgrade=false`, `user_agent=Sonarr/5.0.0.2701 (alpine 3.24.2)`,
  child `Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv`. Keys:
  `applicationUrl,customFormatInfo,downloadClient,downloadClientType,downloadId,episodeFile,episodes,eventType,instanceName,isUpgrade,release,series`.
- **`IMPORT_LINES single=1 total=1 mine=1`**.
- `DELUGE_FINAL` state **Seeding**, progress 100, `stop_at_ratio=false`, `remove_at_ratio=false`,
  `max_download_speed=-1`, label `tv-v5test`.
- `V_AFTER 5.0.0.2701` at 16:05:31 (equal, D-07). **`CAPTURE_STATUS=COMPLETE`**. 119 queue snapshots in total.

Log evidence (app clock = host + 1h), from `log-L2-incomplete.txt`, `log-L2-complete.txt` and `log-L3-import.txt`:
```
2026-10-20 16:55:50,109 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta': Still downloading
2026-10-20 17:01:49,817 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold cleared for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'
2026-10-20 17:03:20,525 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta': Still downloading
2026-10-20 17:03:21,095 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold cleared for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'
2026-10-20 17:03:21,096 - INFO - seedsyncarr.AutoQueue (MainProcess/ControllerJob) - Auto queueing 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'
2026-10-20 17:03:21,597 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Received command Action.QUEUE for file Hacks.S04E01.1080p.HEVC.x265-MeGusta
2026-10-20 17:05:21,785 - INFO - seedsyncarr.WebhookManager (MainProcess/worker 3) - Sonarr webhook import enqueued: 'Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv' (eventType=Download, episodeFile.sourcePath)
2026-10-20 17:05:22,069 - INFO - seedsyncarr.WebhookManager (MainProcess/ControllerJob) - Sonarr import detected: 'Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv' (matched SeedSyncarr file 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'; eventType=Download, episodeFile.sourcePath)
2026-10-20 17:05:22,069 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Recorded webhook import: 'Hacks.S04E01.1080p.HEVC.x265-MeGusta' (child: 'Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv')
```
Observation for Plan 06 (not a Sonarr 5 failure): the 17:01:49 "cleared" came while Sonarr still reported
`downloading`. When the cap lifted, the remote size changed, the root left the stability sweep, and the gate
dropped the hold of a root that is no longer a candidate. The actual completion release is the
17:03:20 → 17:03:21 hold → cleared → `Auto queueing` sequence, after Sonarr reported `completed` at 17:02:22
app time. That second hold lasted 0.6 s, because the gate re-held on a queue view older than the completion.

Live negatives were not run: there is no seedbox shell for a probe file, and breaking the key or URL would
corrupt the evidence. CI (Plan 04) is authoritative for the missing-entry, API-error and unrelated-download
negatives.

### Teardown at Task 3 (COMPLETE)
From the monitor's EXIT trap, at 16:05:31:
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
Fresh-session read-back:
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
Plan verify on the NAS: `CAPTURE_STATUS=COMPLETE`, sink containers 0, `PAIR_OK 1`, `WEBHOOK_OK`.
`queue_details_incomplete.json` (1154 B), `queue_details_complete.json` (1367 B) and
`webhook_download.json` (3306 B) are all mode 600. The sonarr-v5 queue total is now 0.

### Kept seeding (owner requirement)
- Deluge: `Hacks.S04E01.1080p.HEVC.x265-MeGusta`, label `tv-v5test`, **Seeding**, 100%, stop/remove-at-ratio
  off. The seeding data is on the seedbox at `~/v5test/Hacks.S04E01.1080p.HEVC.x265-MeGusta`.
- Nothing removed it: there was no remove, pause, queue DELETE or `removeFromClient`, and sonarr-v5 has
  `removeCompletedDownloads=false`.
- NAS: the imported episode is at `/volume1/data/v5test/media/tv/Hacks/Season 4/Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv`
  (sonarr-v5 `/data/media/tv/...`, HDTV-1080p, 356,287,747 B, 2 links). The seedsyncarr-test staging copy in
  `/volume1/data/v5test/torrents/` is auto-deleted 300 s after import; this affects the NAS copy only.

### Deviations (this plan)
1. **Password source**: the Sonarr API masks the Deluge password, so MODE A reads it from the sandbox Sonarr DB
   (`/volume1/docker/v5test/sonarr/sonarr.db`, read-only, into a variable, never printed).
2. **Per-torrent speed cap and ratio options**: on the capture torrent only, `stop_at_ratio=false` and
   `remove_at_ratio=false` were set to protect seeding. A temporary `max_download_speed` cap (256, then
   4 KiB/s while the seedbox SSH was down) kept the incomplete window open. The cap was removed at 16:01:32
   with owner approval.
3. **Trap fix**: the plan's `trap 'bash "$D/teardown.sh"' EXIT INT TERM HUP` does not exit on a signal.
   Scripts now use `trap 'exit 130' INT TERM HUP` plus an EXIT trap. The first `run-L2.sh` was stopped with
   SIGKILL, and teardown was run by hand.
4. **Teardown hardening** (`ea8c85c`): the capture dir defaults to the script's own location, and missing Deluge
   state now FAILs.
5. **Incomplete milestone captured outside `run-L2.sh`**: it was saved read-only at 15:57 after the seedbox SSH
   recovered, so the sink was not live then. The pair is still the same downloadId (`PAIR_OK 1`).

## Early "Completion hold cleared" at 17:01:49 (app clock): evidence-based account

Sources: read-only. The sandbox app log, the 5 s `queue-<epoch>.json` snapshots, the NAS staging dir and
`src/python/controller/completion_gate.py` / `auto_queue.py`. No live changes. The model stream was **not**
captured between 17:01:49 and 17:03:20 (the monitor did not poll it), so the stream state for that interval
is unknown. The last stream reading, at 16:57 host, was `default` / `still_downloading`.

**What logged.** Every INFO line from 17:00:00 to 17:04:09 app clock, excluding memory stats:
```
17:01:49,817 Completion hold cleared for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'
17:03:20,525 Completion hold for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta': Still downloading
17:03:21,095 Completion hold cleared for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'
17:03:21,096 Auto queueing 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'
17:03:21,597 Received command Action.QUEUE for file Hacks.S04E01.1080p.HEVC.x265-MeGusta
17:03:22,029 ActiveScanner: Path does not exist: /downloads/Hacks.S04E01.1080p.HEVC.x265-MeGusta
```
Nothing else in that window: no `Auto queueing`, no QUEUE command, no transfer line and no reason-change line.

**Sonarr queue/details** (same downloadId, host clock):
- 16:01:31 to 16:02:17: `status=downloading`, `trackedDownloadState=downloading`, `trackedDownloadStatus=ok`,
  and `sizeleft=164118528` unchanged across all 10 snapshots. Sonarr's queue view lagged its own client
  refresh.
- From 16:02:22: `status=completed`, `sizeleft=0`, `importPending`, `warning`.
- So at the clear (16:01:49 host), the nearest snapshot (16:01:46 / 16:01:51) said `downloading` with
  `sizeleft=164118528`.

**Was anything transferred between 17:01:49 and 17:03:20?** No.
- No `Auto queueing` or `Action.QUEUE` line exists before 17:03:21.
- At 17:03:22 the local active scanner reported the local root path did not exist yet.
- The staging dir mtime is 16:03:51 host, after the 16:03:21 queue.
- The child-file mtimes in the staging copy (mkv 16:01:36, nfo 16:01:35 host) are the seedbox mtimes
  preserved by the transfer, not copy times. They show the seedbox file was last written at 16:01:36, about
  4 s after the cap lifted. Deluge had in fact finished before 16:01:49, but Sonarr's queue still said
  `downloading` until 16:02:22.

**Why the hold cleared.** The gate code path:
1. `AutoQueue.process` (`auto_queue.py`) passes the gate only *sweep survivors*: DEFAULT roots whose remote
   size has been stable for `remote_stability_seconds` (90) on the successful-scan clock. A size change
   resets that window (`__update_remote_size_history`).
2. When the cap lifted, the download finished and the remote scan saw a new size for the root. The root
   stopped being a stability candidate and was not in `gate_candidates` for that cycle.
3. `CompletionGate._run(..., prune=True)` ends with `for name in list(self._holds): if name not in candidates:
   self._clear_hold(name)`. `_clear_hold` logs `Completion hold cleared for '<root>'`, the same message used
   when a hold is released on proof. The 17:01:49 line is this **prune** (the root left the candidate set),
   not a "not held" verdict. No verdict was produced for the root in that cycle, and AutoQueue queues only
   survivors whose verdict in the *same* cycle is not held.
4. While there were no candidates, `_run` started no fetches (step 4 runs only `if candidates`). The gate's
   last Sonarr snapshot therefore stayed at "downloading".
5. At 17:03:20 the size had been stable for 90 s, and the root re-entered the candidates. `_decide`
   evaluated it from that stale "downloading" snapshot and **re-held it** (`Still downloading`), and a fetch
   started. 0.57 s later the fresh snapshot (`completed`, `sizeleft=0`) was applied. The verdict became not
   held, `_record` cleared the hold, and the same cycle queued it (17:03:21).

**Verdict.**
- **Not a safety gap.** The prune-clear only removes the registry entry. It cannot queue anything, because
  queueing needs the root to be a sweep survivor with a not-held verdict computed in the same cycle, from the
  gate's arr snapshot. When the root came back, the gate re-held it on the stale snapshot rather than
  releasing it. The only release came from a snapshot showing `completed`, `sizeleft=0`.
- A premature transfer of an incomplete file **cannot** happen through this path. It would need the gate's
  own snapshot to report completion.
- **Version-independent.** It is gate-internal (stability sweep plus registry prune) and would happen the
  same way against Sonarr 4 or Radarr. It is not Sonarr-5-specific and does not trigger SON5-05.
- **Observability defect (pre-existing).** One log message, `Completion hold cleared`, covers both "dropped
  from candidates" and "released on proof". That makes a non-release look like a release. Logged to
  `deferred-items.md` as a candidate wording fix, for example `Completion hold dropped for '<root>' (no
  longer a queue candidate)`.
- This supersedes the shorter "Observation for Plan 06" paragraph above. Its mechanism (prune on leaving
  the sweep, then a re-hold on an older queue view) is confirmed. The new evidence is that the Deluge
  download had in fact completed at about 16:01:36 host, while Sonarr's queue still said `downloading`
  until 16:02:22.
