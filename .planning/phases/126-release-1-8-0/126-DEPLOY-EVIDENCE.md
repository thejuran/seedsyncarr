# Phase 126 Plan 06: Production Deploy by Digest (REL-06, D-15/D-16/D-17)

Hygiene: only counts, digests, field names and status words are recorded below. No credential
value, settings.cfg excerpt, or secret appears anywhere in this file.

RELEASE_DIGEST=sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7
SMOKE_IMAGE_ID (126-05 sandbox)=sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309
ROLLBACK_IMAGE=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
TS (backup suffix)=20261028-1807

## Gate: owner go-ahead

Checked `126-SMOKE-EVIDENCE.md` §"Owner go-ahead (Plan 126-05 Task 3, 2026-10-28)" before any
NAS write: owner's reply, verbatim, is `"deploy"`. Production was confirmed still on
`:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` at the moment
that reply was recorded, and this plan is the one that performs the deploy. Gate: **PASS** —
proceed.

| Marker | Value |
|---|---|
| DEPLOY_START (preconditions) | `2026-10-28 18:07:57 -0500` |
| TS (backup suffix) | `20261028-1807` |
| STOP_TIME | `1793228896` = `2026-10-28 18:08:16 -0500` |
| UP_TIME | `1793229011` = `2026-10-28 18:10:11 -0500` |
| Downtime (STOP_TIME to UP_TIME, includes backups + two loader-check runs) | 115 s |
| First successful remote scan after deploy | `1793229041.9848` = `2026-10-28 18:10:41 -0500` (31 s after UP_TIME; no warm-up scanner error occurred) |
| Steady-state check (uptime 309 s) | `2026-10-28 18:15:20 -0500` |
| Production no-secrets check (1g) | between the steady-state check and the wud restore, same session |
| WUD_START_TIME | `1793229340` = `2026-10-28 18:15:40 -0500` |
| Post-wud re-fingerprint | `2026-10-28 18:18:55 -0500` (195 s after WUD_START_TIME) |
| Pre-deploy production container | `2feb4073db71` |
| Post-deploy production container | `34470550b27f` |

### 1a preconditions

```
$ sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}}'
exited
$ sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Id}} {{.Config.Image}} {{.Image}} {{.State.Status}} {{.State.StartedAt}}'
2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e sha256:5b801f8397d68bf9bb35eed0d4f882cae2ab24100e4d28be4006f8f028e0ef62 running 2026-10-23T07:04:18.591254939Z
```

Identical to the production fingerprint recorded in `126-SMOKE-EVIDENCE.md` at the end of Plan
05 — production was untouched between plans.

```
$ sudo /usr/local/bin/docker pull -q ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7
ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7
$ sudo /usr/local/bin/docker image inspect ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 --format '{{.Id}} {{json .RepoDigests}}'
sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309 ["ghcr.io/thejuran/seedsyncarr@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7"]
```

PRE_PULL_ID_MATCH: pulled `.Id` == SMOKE_IMAGE_ID (`sha256:12fba785...79309`) — **PASS**.

```
$ cd /volume1/docker && ls -i docker-compose.yml
101692302 docker-compose.yml
$ cp -p docker-compose.yml docker-compose.yml.pre-1.8.0-20261028-1807
$ ls -i docker-compose.yml docker-compose.yml.pre-1.8.0-20261028-1807
101692302 docker-compose.yml
101927299 docker-compose.yml.pre-1.8.0-20261028-1807
$ sha256sum docker-compose.yml.pre-1.8.0-20261028-1807
3245550284ff313de1d6061d9747ce0653a4237bb13446e30dc6dc3a6fc60a87  docker-compose.yml.pre-1.8.0-20261028-1807
```

### 1b stop and backups

```
STOP_TIME: 1793228896 Wed Oct 28 18:08:16 -05 2026
$ cd /volume1/docker && sudo /usr/local/bin/docker compose stop seedsyncarr
 Container seedsyncarr  Stopping
 Container seedsyncarr  Stopped
after stop (date +%s): 1793228908
$ sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.FinishedAt}}'
exited 0 false 2026-10-28T23:08:24.452860116Z
$ tail -8 /volume1/docker/seedsync/log/seedsyncarr.log   (app-log clock = host + 1h)
2026-10-28 19:08:20,869 - INFO - seedsyncarr (MainProcess/MainThread) - Caught signal SIGTERM
2026-10-28 19:08:20,869 - INFO - seedsyncarr (MainProcess/MainThread) - Exiting Seedsyncarr
2026-10-28 19:08:21,050 - ERROR - seedsyncarr.ScanManager (MainProcess/ControllerJob) - Scanner process(es) died unexpectedly: RemoteScanner, LocalScanner, ActiveScanner
... ScannerProcessDiedError traceback (known pre-existing shutdown race, logged on every stop since before 1.7.6 — see 119.1-REL04-EVIDENCE.md 1b, same traceback on a CLEAN_STOP) ...
2026-10-28 19:08:21,908 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Exited controller
2026-10-28 19:08:22,774 - INFO - seedsyncarr (MainProcess/MainThread) - Exited successfully
```

STOP_CLASS: **CLEAN_STOP** (ExitCode 0, OOMKilled false; SIGTERM-to-"Exited successfully"
duration 1.9 s, well under the 10 s grace; `Caught signal SIGTERM` through `Exited successfully`
present). The `ScannerProcessDiedError` lines are the same known shutdown-race traceback already
documented as expected on every stop (119.1-REL04-EVIDENCE.md), not a startup error or a FORCED_STOP
indicator.

```
$ cd /volume1/docker/seedsync && cp -p settings.cfg settings.cfg.pre-1.8.0-20261028-1807 && cp -p controller.persist controller.persist.pre-1.8.0-20261028-1807 && cp -p autoqueue.persist autoqueue.persist.pre-1.8.0-20261028-1807 && echo COPIES_OK
COPIES_OK
$ ls -l *.pre-1.8.0-20261028-1807
-rw------- 1 jule1651 users    22 Oct 28 18:08 autoqueue.persist.pre-1.8.0-20261028-1807
-rw------- 1 jule1651 users 26626 Oct 28 18:08 controller.persist.pre-1.8.0-20261028-1807
-rw------- 1 jule1651 users  1265 Oct 28 18:08 settings.cfg.pre-1.8.0-20261028-1807
test -s: no EMPTY line (all three non-zero)
$ sha256sum settings.cfg.pre-1.8.0-20261028-1807 controller.persist.pre-1.8.0-20261028-1807 autoqueue.persist.pre-1.8.0-20261028-1807 /volume1/docker/docker-compose.yml.pre-1.8.0-20261028-1807
065af6bf5cd1a8a2273a5e063f5ede49ba4885bdb56dbeeb83fce7944f4033ed  settings.cfg.pre-1.8.0-20261028-1807
ef9109b595b3b9a30e2cb9d5f9f77df5843c23d09ed3075b024dedbcda04a16a  controller.persist.pre-1.8.0-20261028-1807
53ba66394d6c25515c760efbcde45b4d0917b778b2b883bc1833618b53e6c4df  autoqueue.persist.pre-1.8.0-20261028-1807
3245550284ff313de1d6061d9747ce0653a4237bb13446e30dc6dc3a6fc60a87  /volume1/docker/docker-compose.yml.pre-1.8.0-20261028-1807
```

No NO-GO condition: `COPIES_OK` printed, all three backups non-empty, four sha256 sums recorded.

### 1c loader check (both images, read-only)

```
$ sha256sum parse_check.py   (NAS copy, /tmp/deploy180, 0700 dir)
920363ac3693d1528ece37114e870cf00cb8b75b718663bc2ef5d446b3f5dd53  parse_check.py
```

Matches the recorded value from 118-05 (`920363ac...5dd53`) exactly.

```
$ sudo /usr/local/bin/docker run --rm -i --read-only --network none --cap-drop ALL --user 1026:100 --entrypoint python3 -w /app/python -v /volume1/docker/seedsync:/c:ro ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e - settings.cfg.pre-1.8.0-20261028-1807 controller.persist.pre-1.8.0-20261028-1807 autoqueue.persist.pre-1.8.0-20261028-1807 < parse_check.py
PASS settings.cfg.pre-1.8.0-20261028-1807 loader=Config
AutoDelete.enabled=True
PASS controller.persist.pre-1.8.0-20261028-1807 loader=ControllerPersist
PASS autoqueue.persist.pre-1.8.0-20261028-1807 loader=AutoQueuePersist
PARSE_OK
EXIT=0
$ sudo /usr/local/bin/docker run --rm -i --read-only --network none --cap-drop ALL --user 1026:100 --entrypoint python3 -w /app/python -v /volume1/docker/seedsync:/c:ro ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 - settings.cfg.pre-1.8.0-20261028-1807 controller.persist.pre-1.8.0-20261028-1807 autoqueue.persist.pre-1.8.0-20261028-1807 < parse_check.py
PASS settings.cfg.pre-1.8.0-20261028-1807 loader=Config
AutoDelete.enabled=True
PASS controller.persist.pre-1.8.0-20261028-1807 loader=ControllerPersist
PASS autoqueue.persist.pre-1.8.0-20261028-1807 loader=AutoQueuePersist
PARSE_OK
EXIT=0
```

Both images: three `PASS` lines, `PARSE_OK`, `EXIT=0`. `AutoDelete.enabled=True` recorded in
both — this means a rollback restoring these backups would re-arm auto-delete, so rollback step
(iii) (force `enabled = False`) is **required**, not skippable, if a rollback is ever executed.
No LEAVE_STOPPED or NO-GO condition arose.

### 1d compose pin (inode-preserving write-through)

```
$ grep -c 'wud\.' docker-compose.yml.pre-1.8.0-20261028-1807
34
INODE before=101692302
$ sed 's|ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e|ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7|' docker-compose.yml > /tmp/dc180.new && cat /tmp/dc180.new > docker-compose.yml && rm /tmp/dc180.new
INODE after=101692302
$ diff docker-compose.yml.pre-1.8.0-20261028-1807 docker-compose.yml
140c140
<     image: ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
---
>     image: ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7
$ grep -c 'wud\.' docker-compose.yml
34
$ grep -c 'seedsyncarr:1.8.0@sha256' docker-compose.yml
1
$ grep -c 'seedsyncarr:dev' docker-compose.yml
0
$ grep -c 'seedsyncarr:latest' docker-compose.yml
0
```

INODE_MATCH: same inode (101692302) before and after — **PASS**. Exactly one line changed. wud
label count unchanged (34 == 34). No `:dev`, no `:latest`.

### 1e recreate and verify image

```
UP_TIME: 1793229011 Wed Oct 28 18:10:11 -05 2026
$ sudo /usr/local/bin/docker compose up -d seedsyncarr
 Container seedsyncarr  Recreate
 Container seedsyncarr  Recreated
 Container seedsyncarr  Starting
 Container seedsyncarr  Started
$ sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.State.Status}} {{.Image}} {{.Id}} {{.Config.Image}}'
running sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309 34470550b27f231b8acd67543e3336aaa4b3a131e2e099aaeb7408370d0dca39 ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7
$ sudo /usr/local/bin/docker image inspect sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309 --format '{{json .RepoDigests}}'
["ghcr.io/thejuran/seedsyncarr@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7"]
$ sudo /usr/local/bin/docker inspect seedsyncarr --format '{{json .Config.Labels}}'   (wud labels, excerpted)
"wud.tag.include":"^\\d+\\.\\d+\\.\\d+$"
"wud.watch.digest":"true"
```

IMAGE_ID_MATCH: running `.Image` (`sha256:12fba785...79309`) == SMOKE_IMAGE_ID — **PASS**.
RepoDigests of that image contains RELEASE_DIGEST exactly. wud labels preserved.
CONTAINER_RECREATED: `2feb4073db71` -> `34470550b27f` (confirmed also via the new container's
own `com.docker.compose.replace` label, which names the old container ID).

Startup log (`sudo /usr/local/bin/docker logs seedsyncarr`):

```
[entrypoint] GID 100 already exists as 'users'; using it for seedsyncarr
[entrypoint] Remapping seedsyncarr uid 1000 -> 1026
[entrypoint] Running config setup as uid 1026
Config ready at /config/settings.cfg (existing config kept)
[entrypoint] Starting seedsyncarr as uid 1026 gid 100
2026-10-28 19:10:41,309 - INFO - seedsyncarr (MainProcess/MainThread) - Debug mode is disabled.
2026-10-28 19:10:41,343 - INFO - seedsyncarr (MainProcess/MainThread) - Starting SeedSyncarr
2026-10-28 19:10:41,343 - INFO - seedsyncarr (MainProcess/MainThread) - Platform: x86_64
2026-10-28 19:10:41,343 - WARNING - ... [SECURITY] webhook_secret is not configured. ...
2026-10-28 19:10:41,343 - WARNING - ... [SECURITY] No API token configured. ...
2026-10-28 19:10:41,343 - WARNING - ... [SECURITY] Application is bound to 0.0.0.0 without an API token. ...
2026-10-28 19:10:41,962 - INFO - seedsyncarr.WebApp (MainProcess/MainThread) - Html path set to: /app/html
2026-10-28 19:10:42,044 - INFO - seedsyncarr.Controller.MemoryMonitor (MainProcess/ControllerJob) - Memory stats: process=50.2MB, downloaded_files=96, extracted_files=0, model_files=7, lftp_statuses=0
2026-10-28 19:10:44,081 - INFO - RemoteScanner.RemoteScanner (RemoteScanner/RemoteScanner) - Installing local:/app/scanfs to remote:/home/jules1651/.local/scanfs
```

The config loaded (`existing config kept`, no `Fatal: Bad config`), the controller started, and
`downloaded_files=96` matches the pre-deploy memory stat exactly (controller.persist carried
over intact).

### 1f recovery

```
$ curl -s http://localhost:8800/server/status | jq '{up, scan_failed: .controller.latest_remote_scan_failed, scan_time: .controller.latest_remote_scan_time}'
(poll 1, up=true, scan_failed=null, scan_time=null)
(poll 2, ~13s after UP_TIME)
{"up": true, "scan_failed": false, "scan_time": "1793229041.9848"}
```

First successful remote scan: `1793229041.9848` (2026-10-28 18:10:41 -0500), 31 s after
UP_TIME. `scan_failed: false`. No scanner ERROR line appeared at all between UP_TIME and this
check (`docker logs seedsyncarr --since <UP_TIME>` grepped for `error|traceback|unavailable|fatal`:
0 matches), so no warm-up-error-then-later-success sequence was needed this time — the first
scan succeeded cleanly.

Sonarr/Radarr reachability (the app's own Test Connection endpoints are GET, not POST — the
plan's interface note assumed POST; corrected to match the actual route registration in
`src/python/web/handler/config.py`, `web_app.add_handler` not `add_post_handler`):

```
$ curl -s http://localhost:8800/server/config/sonarr/test-connection
{"success": true, "version": "4.0.20.3014"}
$ curl -s http://localhost:8800/server/config/radarr/test-connection
{"success": true, "version": "6.4.4.10685"}
```

Both **success**.

5-minute steady state (uptime 309 s, read at `2026-10-28 18:15:20 -0500`), from the full
container log since start:

```
unavailable lines: 0
cleared lines: 0
Backing up: 0
Traceback: 0
ERROR: 0
WARNING: 3          (the three standing [SECURITY] config notices, present since before 1.8.0)
Fatal: 0
Starting SeedSyncarr: 1
$ sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.State.Status}} restarts={{.RestartCount}} started={{.State.StartedAt}}'
running restarts=0 started=2026-10-28T23:10:24.479639297Z
$ curl -s http://localhost:8800/server/status | jq '{up, scan_failed: .controller.latest_remote_scan_failed, scan_time: .controller.latest_remote_scan_time}'
{"up": true, "scan_failed": false, "scan_time": "1793229311.996521"}   (2026-10-28 18:15:11 -0500, a later successful scan within the steady-state window)
```

Zero `unavailable` lines over the 309 s window means no stuck/unavailable arr hold appeared
(Phase 117's XFER-02 contract: an unreachable/unparseable arr status surfaces as an
`unavailable` log line, not silently). `restarts=0` — the container never crash-looped.

```
$ ls -l /volume1/docker/seedsync/settings.cfg /volume1/docker/seedsync/controller.persist /volume1/docker/seedsync/autoqueue.persist
-rw------- 1 jule1651 users  1265 Oct 28 18:15 settings.cfg
-rw------- 1 jule1651 users 26626 Oct 28 18:15 controller.persist
-rw------- 1 jule1651 users    22 Oct 28 18:15 autoqueue.persist
$ ls /volume1/docker/seedsync/ | grep -c '\.tmp$'
0
```

Persist files present, non-empty, 0600, no `.tmp` files. No `Backing up` log line appeared, so
there was no rollback trigger from the load path.

### 1g no secrets (count-only, fail-closed)

A staged script (`umask 077`, `mktemp -d`, `trap 'rm -rf "$T"' EXIT`) ran the extractor against
production, captured the running container's log and the plain-file logs, and counted matches —
it never printed a value:

```
$ sha256sum extract_secrets.py   (NAS copy)
c35768d7effedb6e3be2922b6ac59cb5c818b4448138c7f135ee179cdbbbaef6  extract_secrets.py
```

Matches the recorded value (`126-SMOKE-EVIDENCE.md`, identical to `119.1-extract_secrets.py`).

```
$ sudo /usr/local/bin/docker run --rm -i --read-only --network none --cap-drop ALL --user 1026:100 -v /volume1/docker/seedsync:/c:ro --entrypoint python3 -w /app/python ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 - < extract_secrets.py > "$T/values" 2> "$T/fields"; RC=$?
extractor rc=0
fields: FIELDS Lftp.remote_password Sonarr.sonarr_api_key Radarr.radarr_api_key N=3 LINES=3
values: mode=600 wc_l=3 empty=0 N=3 LINES=3        (precondition: rc 0, wc == LINES >= N, 0 empty -> met)
$ sudo /usr/local/bin/docker logs seedsyncarr > "$T/log" 2>&1
log capture exit=0 lines=21 starts=1
$ grep -cFf "$T/values" "$T/log"; GRC=$?
container log vs values: count=0 rc=1
Config ready at: 1
$ cat /volume1/docker/seedsync/log/*.log > "$T/app.log"
plain-file logs capture exit=0 lines=56922
$ grep -cFf "$T/values" "$T/app.log"; PRC=$?
plain-file logs vs values: count=0 rc=1
script_exit=0     ($T removed by the trap)
```

**Count line:** production `seedsyncarr` (1.8.0, container `34470550b27f`) container log: matches
0 / LINES=3 value forms (N=3 fields: `Lftp.remote_password Sonarr.sonarr_api_key
Radarr.radarr_api_key`), grep rc=1; status line: 1; plain-file logs: 0, rc=1 — **PASS**.

Encryption is off in production and `webhook_secret`/`api_token` are empty, so N=3, matching
119.1-04's prior count. No value holds a `%`, so there is no extra serialized form (LINES=3).

## Rollback rule (D-16) — not triggered

1e-1g show production recovered cleanly: the new container started with `downloaded_files=96`
preserved, the first remote scan succeeded 31 s after UP_TIME with no prior scanner error, both
arrs' Test Connection returned `success`, zero `unavailable`/`Traceback`/`ERROR` lines over a
309 s steady-state window, restarts=0, persist files intact, and the no-secrets check matched
zero values. None of the D-16 can't-sync signals (won't start/stay up, scans failing with no
later success, arr unreachable) occurred, and nothing was ambiguous. **Rollback was not
executed.**

### 1h wud restored last

```
Pre-wud fingerprint:
seedsyncarr:      34470550b27f  sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309  running
seedsyncarr-test: 1fb1a7bdeb56  sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309  running  (already on 1.8.0 since Plan 05)
WUD_START_TIME: 1793229340  Wed Oct 28 18:15:40 -05 2026
$ cd /volume1/docker && sudo /usr/local/bin/docker compose start wud
 Container wud  Starting
 Container wud  Started
$ sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}} {{.State.StartedAt}}'
running 2026-10-28T23:15:44.609102981Z
health=healthy (polled)
```

Post-wud re-fingerprint, 195 s after WUD_START_TIME (`2026-10-28 18:18:55 -0500`):

```
$ sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Id}} {{.Image}} {{.Config.Image}} {{.State.Status}} {{.State.StartedAt}}'
34470550b27f231b8acd67543e3336aaa4b3a131e2e099aaeb7408370d0dca39 sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309 ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 running 2026-10-28T23:10:24.479639297Z
$ sudo /usr/local/bin/docker inspect seedsyncarr-test --format '{{.Id}} {{.Image}} {{.Config.Image}} {{.State.Status}} {{.State.StartedAt}}'
1fb1a7bdeb56fd1128120bbfdd2e34b6f91df3ee7f10aa17b8ffedbda593323c sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309 ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 running 2026-10-28T23:00:59.200827558Z
```

Both `Id`, `Image` and `StartedAt` unchanged from the pre-wud fingerprint — wud did not touch
either container, which is expected since both are already on `:1.8.0` (the newest numeric
tag matching `wud.tag.include=^\d+\.\d+\.\d+$`).

### 1i rollback runbook (not executed)

No rollback trigger occurred (see "Rollback rule (D-16) — not triggered" above). The exact
commands for this deploy's backups, if a rollback is ever needed, in this order:

1. **Stop wud, then stop seedsyncarr:** `ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose stop wud'`, then `sudo /usr/local/bin/docker compose stop seedsyncarr`; confirm `sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.FinishedAt}}'` starts with `exited`. Classify CLEAN_STOP/FORCED_STOP as in 1b.
2. **Restore the three state files:** `cd /volume1/docker/seedsync && cp -p settings.cfg.pre-1.8.0-20261028-1807 settings.cfg && cp -p controller.persist.pre-1.8.0-20261028-1807 controller.persist && cp -p autoqueue.persist.pre-1.8.0-20261028-1807 autoqueue.persist`. Then `sha256sum settings.cfg controller.persist autoqueue.persist` must print `065af6bf...033ed`, `ef9109b5...4a16a` and `53ba6639...c4df` (1b above). **Any checksum mismatch -> LEAVE_STOPPED**: start no image, return to the owner.
3. **Force AutoDelete off (REQUIRED — 1c recorded `AutoDelete.enabled=True` in the restored backup):** `sed -i '/^\[AutoDelete\]/,/^\[/ s/^enabled = .*/enabled = False/' /volume1/docker/seedsync/settings.cfg`
4. **Verify:** `grep -A3 '^\[AutoDelete\]' /volume1/docker/seedsync/settings.cfg` prints `enabled = False`. Do not proceed until it does.
5. **Re-pin compose** to `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` with `cat docker-compose.yml.pre-1.8.0-20261028-1807 > docker-compose.yml` (write-through, inode unchanged at `101692302`; that backup is the exact pre-deploy file, sha256 `32455502...60a87`, with the wud labels intact). Confirm `ls -i docker-compose.yml` still prints `101692302`.
6. **Recreate on 1.7.6:** `ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose up -d seedsyncarr'`. Then `sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Image}} {{.State.Status}}'` must print `sha256:5b801f8397d68bf9bb35eed0d4f882cae2ab24100e4d28be4006f8f028e0ef62 running`. Check `server.up` true, a successful remote scan, and no `Backing up` line in the log.
7. **Keep auto-delete off** until the owner confirms in the UI that every expected import shows as imported.
8. **Only after the rollback is verified**, restore wud: `sudo /usr/local/bin/docker compose start wud`, verify `running`/healthy.

No data conversion is needed either direction — Research (`126-RESEARCH.md` §Rollback Safety)
confirmed `common/persist.py`, `common/config.py`, `controller_persist.py` and `auto_queue.py`
are byte-for-byte unchanged between `v1.7.6` and `main` (zero-line `git diff`), so 1.7.6 reads
1.8.0-written state unchanged. The only two carried-forward cautions are: (a) remove `%` from
any secret saved under 1.8.0 before rolling back (unchanged escaping behavior — not applicable
here, `LINES=N=3` in 1g confirms no `%`-bearing secret); (b) the AutoDelete re-arm caution above,
which **does** apply this time (`AutoDelete.enabled=True`).

### Deploy verdict

REL-06 / D-15 / D-17: **PASS**.
- Production runs `:1.8.0@sha256:6e8d453f...4879aa7` in the new container `34470550b27f`, with
  `.Image` == SMOKE_IMAGE_ID (`sha256:12fba785...79309`). The old `2feb4073db71` container and
  its log are gone.
- The stop was CLEAN_STOP (ExitCode 0, OOMKilled false, 1.9 s SIGTERM-to-exit).
- Backups: four files, all non-empty, checksummed, and pass the loader check in both images
  (`PARSE_OK`, `EXIT=0`), with `AutoDelete.enabled=True` recorded for the rollback runbook.
- Compose: same inode before/after, exactly one line changed, wud label count unchanged
  (34 == 34), zero `:dev`/`:latest` references.
- The config loaded without a reset (`downloaded_files=96`, carried over exactly). A clean
  remote scan ran 31 s after start, with no warm-up error at all. Both arrs return Test
  Connection `success` (Sonarr 4.0.20.3014, Radarr 6.4.4.10685). Zero `unavailable`/`Traceback`/
  `ERROR` lines and restarts=0 over a 309 s steady-state window. Downtime was 115 s.
- Production log and plain-file logs: 0 matches of 3 secret values (grep rc=1 both).
- wud was restored last, confirmed `running`/healthy, and a 195 s-later re-fingerprint of both
  `seedsyncarr` and `seedsyncarr-test` shows wud made zero changes to either (both already on
  the newest numeric tag).
- D-16 rollback was not triggered; nothing was ambiguous.

Pending: owner confirmation (D-17, Task 2 of this plan).

## Deviations from Plan

**1. [Rule 3 - Blocking] Sonarr/Radarr Test Connection endpoints are GET, not POST**
- **Found during:** Task 1, step 1f (arr reachability check)
- **Issue:** The plan's interface recipe said `POST /server/config/sonarr/test-connection` and
  `/server/config/radarr/test-connection`. Both returned `405 Method Not Allowed` on POST.
  Reading `src/python/web/handler/config.py` showed both routes are registered with
  `web_app.add_handler` (GET), not `add_post_handler` (POST) — the plan's recipe text did not
  match the actual route registration.
- **Fix:** Called both endpoints with GET instead. Both returned `{"success": true, "version": "..."}`.
  No product code was touched; only the verification command was corrected to match the
  application's actual API.
- **Cost if wrong:** None to production — this only affects how the verification command was
  phrased in this evidence file. The actual check (both arrs reachable with a version response)
  still ran and still passed; if GET somehow were not equivalent to the intended check, the
  numeric version strings returned (4.0.20.3014, 6.4.4.10685) are independent confirmation the
  app successfully reached both services with valid credentials.
- **Files modified:** None (verification command only; no `<files>` listed for this task besides
  this evidence file)
- **Commit:** part of this plan's Task 1 commit

---

**Total deviations:** 1 auto-fixed (Rule 3, verification-command-only, no product or config
change).

## Owner confirmation (Plan 126-06, 2026-10-28)

Owner reply, verbatim: `confirmed`

D-17 is satisfied: a successful scan was observed after start (1f, 31 s after UP_TIME, no
warm-up error), Sonarr and Radarr were both reachable with no stuck holds (1f), wud was
restored last with an unchanged post-restore fingerprint (1h), and the owner has now confirmed
the deployed state. REL-06 is complete.
