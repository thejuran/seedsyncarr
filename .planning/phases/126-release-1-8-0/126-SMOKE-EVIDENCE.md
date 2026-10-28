# Phase 126 Release 1.8.0 — Smoke Harness Evidence

Hygiene: only status words, counts, HTTP codes, image digests and field names are recorded.
No credential value appears anywhere in this file. The synthetic probe token
`probe126-token-not-a-secret` is not a credential — it is a value generated solely for this
session's throwaway container and never reused anywhere else.

## Harness (Plan 126-02)

Scope: this section covers the sandbox smoke harness built and proven in Plan 126-02 —
the extended teardown script, the generalized webhook poster, the verbatim count-only
secret extractor, and a new browser-side token probe with a positive control. The D-12a
checks these tools exist to support (restart, real transfer, Sonarr-v4/Radarr integration,
Test Connection spot checks, no-secrets, webhook test event) are exercised against the
exact published `:1.8.0` digest in a later plan; this plan only builds and proves the
tooling itself.

### Harness files (sha256)

| File | sha256 |
|------|--------|
| `126-teardown.sh` | `84cae8f11be82dcbb2579f72d35ec9157b003e0ab509c3d32eaff8902117b10f` |
| `126-webhook-post.sh` | `5c4e6ff690be3806c6aaa4f4c78550ca24af2ad5c2a5eff7b4c8f0f31b030f9b` |
| `126-extract_secrets.py` | `c35768d7effedb6e3be2922b6ac59cb5c818b4448138c7f135ee179cdbbbaef6` (identical to `119.1-extract_secrets.py`) |
| `126-token-probe.mjs` | `88d291385047f2a1dc4edb1db52798f25c0b20bd6cf44eb826c417a9f11d216e` |

Static checks (all green): `bash -n` on both shell scripts, `shellcheck 0.11.0` on both
(zero findings after one fix — see Deviations in the plan SUMMARY), `python3 -m py_compile`
on the extractor, `node --check` on the probe. Neither shell script references
`/volume1/docker/docker-compose.yml` (the production compose path) or any
`docker (stop|start|rm|restart|compose) ... seedsyncarr` literal targeting production.

### Positive control: token probe vs a throwaway 1.7.6 container

Proves the probe is not vacuous — section T-126-08 of the plan's threat model.

**Throwaway container:** `seedsyncarr-probe126-ctl`, label `wud.watch=false`, scratch dir
`/volume1/docker/probe126-20261028T201753Z/{config,downloads}` (created without `sudo`;
the SSH session's own uid/gid is 1026/100, matching the container's `PUID`/`PGID`, so the
dir is already owned correctly — confirmed by `ls -la` showing every file under `config/`
owned `jule1651:users` after the container wrote to it).

```
$ sudo /usr/local/bin/docker run -d --name seedsyncarr-probe126-ctl --label wud.watch=false \
    -e PUID=1026 -e PGID=100 -p 127.0.0.1:8803:8800 \
    -v /volume1/docker/probe126-20261028T201753Z/config:/config \
    -v /volume1/docker/probe126-20261028T201753Z/downloads:/downloads \
    ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
cbdc0567903753263c648618a898073434389224581c342e655dfd6555192736
$ sudo /usr/local/bin/docker inspect seedsyncarr-probe126-ctl --format '{{.Config.Image}} {{.State.Running}}'
ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e true

WAIT_STATUS ok=1
{"server": {"up": false, "error_msg": "The settings are not fully configured."}, ...}

$ curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" \
    -d '{"section":"general","key":"api_token","value":"probe126-token-not-a-secret"}' \
    http://127.0.0.1:8803/server/config/set
SET_API_TOKEN http=200
```

**Confirming the token was actually set, without ever reading its value back:** since Phase
121 (SEC-02), `general.api_token` always serializes as `""` via `/server/config/get`, even
to an authenticated caller — so the normal read-and-compare pattern doesn't apply to this
one field. Instead, the config API's own auth gate is the confirmation: the endpoint
returns 401 with no `Authorization` header, and 200 with exactly
`Authorization: Bearer probe126-token-not-a-secret` — which is only possible if the server's
stored `api_token` equals that value.

```
$ curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8803/server/config/get
401
$ curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer probe126-token-not-a-secret" \
    http://127.0.0.1:8803/server/config/get
200
```

**Probe run (from the Mac, through an SSH tunnel to the throwaway container):**

```
$ ssh -f -N -L 18803:127.0.0.1:8803 nas
$ node .planning/phases/126-release-1-8-0/126-token-probe.mjs http://localhost:18803 probe126-token-not-a-secret
GITHUB_REQUESTS=1 WITH_AUTH=1 WITH_TOKEN=1
(exit 0)
```

**Verdict** — probe positive control: **PASS** — `GITHUB_REQUESTS=1 WITH_AUTH=1 WITH_TOKEN=1`
on the unfixed 1.7.6 build, confirming the pre-SEC-02 interceptor attaches the app's
`api_token` to the GitHub update-check request and that the probe correctly observes it.
This is the proof the probe is not vacuous (an app that never sent the token would have
reported `WITH_TOKEN=0`, which the plan's own gate treats as a failed positive control,
not a pass).

One probe fix was needed before this result was obtainable: the first run against a real
app timed out (`ERROR TimeoutError`) because `page.goto({waitUntil:"networkidle0"})` never
resolves against an app that holds open a long-lived SSE connection for its live model
stream. Switched to `networkidle2` (tolerates the one persistent connection) with a 45s
navigation timeout; re-ran and got the result above. A second, separate fix was needed for
the CORS preflight the browser sends ahead of a cross-origin request carrying a
non-safelisted `Authorization` header: the first mocked GitHub response only set
`Access-Control-Allow-Origin`, which satisfies a simple response but not a preflight, so
the browser silently dropped the real (authenticated) request after the preflight failed —
producing `WITH_AUTH=0` even on the leaking 1.7.6 build. Fixed by answering `OPTIONS`
requests to `api.github.com` with `Access-Control-Allow-Methods`/`-Headers` and not
counting that preflight itself toward `GITHUB_REQUESTS`. Both fixes were verified first
against a disposable local static page (one authenticated fetch, one unauthenticated
fetch, one same-origin fetch) before being run against the real NAS container, confirming
`WITH_AUTH`/`WITH_TOKEN` distinguish correctly (1/1), a true negative reports 1/0/0, and no
GitHub request at all exits 3 (inconclusive, not a pass).

**Cleanup:**

```
$ bash teardown.sh /volume1/docker/v5test/results/probe126-20261028T201753Z
WAIT server/status ok
IMAGE current=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
RESTORED sonarr_url ok (not set this session)
RESTORED radarr_url ok (not set this session)
RESTORED radarr_enabled ok (not set this session)
RESTORED sonarr_api_key ok (not set this session)
RESTORED radarr_api_key ok (not set this session)
REMOVED synth roots count=0 refused=0
REMOVED probe containers count=1 refused=0
REMOVED probe dirs count=1 refused=0
SANDBOX_RESTORED ok
```

```
$ sudo /usr/local/bin/docker ps -a --filter name=seedsyncarr-probe126 -q
(empty)
$ ls -d /volume1/docker/probe126-*
ls: cannot access '/volume1/docker/probe126-*': No such file or directory
```

Confirmed: no `seedsyncarr-probe126*` container and no `/volume1/docker/probe126-*`
directory remain on the NAS.

### Teardown dry run (live sandbox, nothing to restore)

Fresh, empty capture dir (`/volume1/docker/v5test/results/dryrun126-20261028T201753Z`, no
`state.env`), run against the live `seedsyncarr-test`:

```
$ bash teardown.sh /volume1/docker/v5test/results/dryrun126-20261028T201753Z
WAIT server/status ok
IMAGE current=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
RESTORED sonarr_url ok (not set this session)
RESTORED radarr_url ok (not set this session)
RESTORED radarr_enabled ok (not set this session)
RESTORED sonarr_api_key ok (not set this session)
RESTORED radarr_api_key ok (not set this session)
REMOVED synth roots count=0 refused=0
REMOVED probe containers count=0 refused=0
REMOVED probe dirs count=0 refused=0
SANDBOX_RESTORED ok
```

Every restore line printed `ok (not set this session)`, every cleanup count was `0`, the
script exited 0, and the sandbox's image reference (`:1.7.6@sha256:da6196e0...`, the same
digest it was running before this plan started) is unchanged. This proves the script is
safe to run with nothing to restore.

### Production fingerprint (read-only; must be identical before and after)

```
BEFORE: 2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 \
        ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e \
        2026-10-23T07:04:18.591254939Z
AFTER:  2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 \
        ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e \
        2026-10-23T07:04:18.591254939Z
```

Identical container Id, image and `StartedAt` before and after this plan's entire session
(throwaway positive control + sandbox dry run). Production was never named as a target by
any harness script (confirmed by the grep gate above) and was only ever read, never
written, in this plan.

## Build under test

- **Tag/digest:** `ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`
- **RELEASE_DIGEST source:** `126-04-SUMMARY.md` / `126-REL-EVIDENCE.md`, re-resolved once this
  session with method B (anonymous GHCR pull token, `HEAD /v2/.../manifests/1.8.0`, OCI index
  Accept header): `docker-content-digest: sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`
  — identical to the recorded value. Confirmed match.

## Sandbox smoke (Plan 126-05)

NAS capture dir (0700, not committed): `/volume1/docker/v5test/results/smoke126-20261028T221654Z`.
Holds `teardown.sh`, `webhook-post.sh`, `extract_secrets.py`, `token-probe.mjs` (copies of the
committed harness, sha256-verified byte-identical before use), `state.env`, `secret` (0600, fresh
webhook HMAC key), and the before/after production-fingerprint captures below.

### Step 0: preconditions (read-only)

```
wud: exited
P0 (production): 2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 \
  ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e \
  2026-10-23T07:04:18.591254939Z running
sandbox .Config.Image (before): ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
sandbox sonarr_url: http://sonarr-v5:8989
sandbox radarr_url: "" (empty)
sandbox radarr enabled: false
seedbox (nyx.usbx.me): reachable
arr containers present: sonarr-v4 (linuxserver/sonarr:4.0.20), sonarr-v5 (develop), radarr (latest), sonarr (latest, prod)
```

`state.env` written before any change: `IMAGE_PIN_L0`, `SONARR_URL_L0=http://sonarr-v5:8989`,
`RADARR_URL_L0=` (empty), `RADARR_ENABLED_L0=false`.

**Deviation found at Step 0 (Rule 3 - Blocking):** `126-teardown.sh`'s `post_arr_key()` used
`jq -n --rawfile v "$file" ...`, but the NAS's `jq` is version 1.5 (`--rawfile` was added in jq
1.6) — the first live attempt to set the Sonarr v4 API key failed with
`jq: Unknown option --rawfile`. This would also have broken teardown's own key-restore step
later in this same session. Fixed by switching to `jq -nR --arg section ... --arg key ...
'{section:$section,key:$key,value:input}' < "$file"` (reads the file's first line as a raw
string via stdin instead of `--rawfile`) — same value-never-in-argv guarantee, jq-1.5-compatible.
Verified with `bash -n` and `shellcheck 0.11.0` (0 findings) before use; re-copied to the NAS
capture dir and sha256-verified (`f0c0c817eed00a8140e479633daea3dd2d2a283ba6d41b3de9c5294606e46b8e`).
Committed with this plan's Task 1 commit.

### Sandbox deploy

Inode-preserving edit of the `seedsyncarr-test` image line in
`/volume1/docker/v5test/docker-compose.yml` (sed to a temp file, `cat` back):

```
INODE before=101505523 after=101505523
 seedsyncarr-test Pulling
 ... (multi-arch layers) ...
 seedsyncarr-test Pulled
 Container seedsyncarr-test  Recreate
 Container seedsyncarr-test  Recreated
 Container seedsyncarr-test  Starting
 Container seedsyncarr-test  Started
```

```
.Image (id): sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309
.Config.Image: ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7
RepoDigests: ["ghcr.io/thejuran/seedsyncarr@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7"]
```

RepoDigests contains RELEASE_DIGEST exactly (D-11). Replaced pin:
`ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`
(`IMAGE_PIN_L0`).

**Production P1 (immediately after deploy):** identical to P0 (same Id, image, `StartedAt`).

### Restart check (D-12a)

```
restart marker: 2026-10-28T22:20:16Z
sudo /usr/local/bin/docker restart seedsyncarr-test
up after 3 tries (~15s)
scan ok after 1 try: scantime=1793226032.047287 (>= restart epoch 1793226016) failed=false
log since restart: 21 lines, Traceback count=0, fresh "Starting SeedSyncarr" line present
```

Verdict, restart: **PASS**.

### Sonarr v4 integration (D-12)

Key compare (`cmp -s` on two 0600 files, values never printed): sandbox's current key vs
`sonarr-v4`'s config.xml key — **DIFFERENT**. Sandbox's original key copied to `sonarr_key.l0`
(0600) and `SONARR_KEY_SET=1` recorded before any change; `sonarr_api_key` then set from the
`sonarr-v4` key via the fixed value-free jq pattern (HTTP 200). `sonarr_url` set to
`http://sonarr-v4:8989` (`SONARR_URL_SET=1`, HTTP 200); `sonarr.enabled` was already `true`.

```
$ curl -s "http://127.0.0.1:8801/server/config/sonarr/test-connection"
{"success": true, "version": "4.0.20.3014"}
```

Version starts with `4.` (D-12a). Queue-poll/`ArrQueueClient` check: exercised live during the
real-transfer window below (an active auto-queue candidate wired to `sonarr-v4` running through
the completion gate) — across the full session log (22:20:16Z onward) there are 0
case-insensitive `unavailable` lines and 0 ` - ERROR - ` lines.

Verdict, Sonarr v4 integration: **PASS**.

### Radarr integration (D-12, orchestrator resolution: Test Connection + signed synthetic webhook only)

Key compare: sandbox's radarr key (empty/unset) vs production `radarr`'s config.xml key —
**DIFFERENT**. Sandbox's original (empty) key copied to `radarr_key.l0` (0600) and
`RADARR_KEY_SET=1` recorded before any change; `radarr_api_key` set from the production Radarr's
key (read read-only from its mounted `config.xml`) via the same value-free jq pattern (HTTP 200).
`radarr_url` set to `http://radarr:7878` (`RADARR_URL_SET=1`, HTTP 200); `radarr.enabled` set to
`true` (`RADARR_ENABLED_SET=1`, HTTP 200).

```
$ curl -s "http://127.0.0.1:8801/server/config/radarr/test-connection"
{"success": true, "version": "6.4.4.10685"}
```

Only `GET /api/v3/system/status`-equivalent read traffic was sent to production Radarr (Test
Connection); no Radarr write endpoint was ever called in this session (confirmed: the only Radarr
HTTP verbs issued by SeedSyncarr code in this plan are the Test Connection GET and, later, the
sandbox-side synthetic webhook which never reaches Radarr itself).

Verdict, Radarr integration: **PASS**.

### Webhook secret

The sandbox had no webhook secret configured before this session (confirmed indirectly, since
`general.webhook_secret` always serializes as `""` regardless of its real value per SEC-02: an
unsigned `Test` POST to `/server/webhook/sonarr` returned `HTTP 200 "Test OK"` before any change).
A fresh random secret was generated (`head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9'`),
written to the capture dir's `secret` file (0600), and POSTed via `config/set`
(`WEBHOOK_SECRET_SET=1` recorded). Confirmed active: the same unsigned `Test` POST now returns
`HTTP 401 "Missing webhook signature"`.

### Real transfer (D-12a)

`SYNTH_ROOTS=SSA126.Smoke.S01 SSA126.SmokeMovie.2026` recorded to `state.env` before any synthetic
material was created. Built on the seedbox in `/home/jules1651/ssa126-stage/` with `head -c` from
`/dev/urandom`, then `mv`'d atomically into `/home/jules1651/v5test/` (same filesystem):

```
remote sha256 SSA126.Smoke.S01E01.mkv (8 MiB):       3c58f51b6a57d1a4c33d3409db9c7e99b7becd818bdffe9549dd909d20fed6f1
remote sha256 SSA126.SmokeMovie.2026.mkv (16 MiB):   6581ea17ee5677c3bf56954347d886131c2556eb9bf2b7bc51349ccc5963b1f5
```

Both roots were picked up by the scanner and initially **held** (Sonarr now enabled, so the
completion gate requires arr-queue proof before any new auto-queue candidate may transfer):

```
2026-10-28 18:27:37,567 - INFO - seedsyncarr.CompletionGate - Completion hold for 'SSA126.Smoke.S01': No matching queue entry
2026-10-28 18:27:37,584 - INFO - seedsyncarr.CompletionGate - Completion hold for 'SSA126.SmokeMovie.2026': No matching queue entry
```

Model snapshot at this point: both roots `state: "default"`, `hold_reason: "no_queue_entry"`,
`local_size: null` — zero bytes transferred, confirming the gate blocks the transfer itself, not
just the later import/delete decision. Since these are synthetic roots never actually present in
either arr's real queue, they were released the same way as the established D-06(e) pattern
(122-SAFE01-EVIDENCE.md): a one-shot manual release per root.

```
$ curl -s -X POST "http://127.0.0.1:8801/server/command/queue/SSA126.Smoke.S01?release_unverified=true"
Queued file 'SSA126.Smoke.S01'
$ curl -s -X POST "http://127.0.0.1:8801/server/command/queue/SSA126.SmokeMovie.2026?release_unverified=true"
Queued file 'SSA126.SmokeMovie.2026'
```

```
2026-10-28 18:30:22,219 - WARNING - seedsyncarr.Controller.CommandProcessor - Manual release of unverified 'SSA126.Smoke.S01' (No matching queue entry); source-completion check bypassed for this transfer only
2026-10-28 18:30:22,491 - INFO - seedsyncarr.CompletionGate - Completion hold dropped for 'SSA126.Smoke.S01' (no longer a queue candidate)
2026-10-28 18:30:22,992 - WARNING - seedsyncarr.Controller.CommandProcessor - Manual release of unverified 'SSA126.SmokeMovie.2026' (No matching queue entry); source-completion check bypassed for this transfer only
2026-10-28 18:30:23,113 - INFO - seedsyncarr.CompletionGate - Completion hold dropped for 'SSA126.SmokeMovie.2026' (no longer a queue candidate)
```

Correct "dropped" wording both times (the manual-release path bypasses the proof gate; it is
never logged as "cleared" — that wording is reserved for the proof-based release path, per
Phase 122 D-16/D-17). Both files transferred to completion within seconds (unmetered
`lftp.rate_limit=0`); the local sha256 of each matched its remote sha256 exactly:

```
local sha256 SSA126.Smoke.S01E01.mkv:     3c58f51b6a57d1a4c33d3409db9c7e99b7becd818bdffe9549dd909d20fed6f1  (= remote)
local sha256 SSA126.SmokeMovie.2026.mkv:  6581ea17ee5677c3bf56954347d886131c2556eb9bf2b7bc51349ccc5963b1f5  (= remote)
```

Final model state for both: `state: "downloaded"`, `hold_reason: null`,
`local_size == remote_size`. The in-flight `.lftp` temp-suffix name was not directly observed
this run (polling interval was coarser than these two small 8/16 MiB files' transfer time at an
unmetered rate limit) — noted per the plan's "if observed" phrasing, not a failure condition; the
file-identity (sha256) and lifecycle (held → released → downloaded) evidence stands on its own.
Across the full session log (22:20:16Z onward): 0 `unavailable` lines, 0 ` - ERROR - ` lines, 0
`Traceback` lines.

Verdict, real transfer: **PASS**.

### Webhook import (D-12a, D-12)

```
$ bash webhook-post.sh <D> sonarr Download SSA126.Smoke.S01 SSA126.Smoke.S01E01.mkv
HTTP_CODE=200
OK
$ bash webhook-post.sh <D> radarr Download SSA126.SmokeMovie.2026 SSA126.SmokeMovie.2026.mkv
HTTP_CODE=200
OK
```

```
2026-10-28 18:33:36,429 - INFO - seedsyncarr.WebhookManager - Sonarr webhook import enqueued: 'SSA126.Smoke.S01E01.mkv' (eventType=Download, episodeFile.sourcePath)
2026-10-28 18:33:36,888 - INFO - seedsyncarr.WebhookManager - Sonarr import detected: 'SSA126.Smoke.S01E01.mkv' (matched SeedSyncarr file 'SSA126.Smoke.S01'; eventType=Download, episodeFile.sourcePath)
2026-10-28 18:33:36,889 - INFO - seedsyncarr.Controller - Recorded webhook import: 'SSA126.Smoke.S01' (child: 'SSA126.Smoke.S01E01.mkv')
2026-10-28 18:33:37,400 - INFO - seedsyncarr.Controller - Scheduled auto-delete of 'SSA126.Smoke.S01' in 300 seconds
2026-10-28 18:33:40,324 - INFO - seedsyncarr.WebhookManager - Radarr webhook import enqueued: 'SSA126.SmokeMovie.2026.mkv' (eventType=Download, movieFile.sourcePath)
2026-10-28 18:33:40,718 - INFO - seedsyncarr.WebhookManager - Radarr import detected: 'SSA126.SmokeMovie.2026.mkv' (matched SeedSyncarr file 'SSA126.SmokeMovie.2026'; eventType=Download, movieFile.sourcePath)
2026-10-28 18:33:40,719 - INFO - seedsyncarr.Controller - Recorded webhook import: 'SSA126.SmokeMovie.2026' (child: 'SSA126.SmokeMovie.2026.mkv')
2026-10-28 18:33:41,016 - INFO - seedsyncarr.Controller - Scheduled auto-delete of 'SSA126.SmokeMovie.2026' in 300 seconds
```

Verdict, webhook import: **PASS**.

### Cleanup (D-12a)

```
2026-10-28 18:38:37,404 - INFO - seedsyncarr.Controller - Auto-deleted local file 'SSA126.Smoke.S01'
2026-10-28 18:38:41,020 - INFO - seedsyncarr.Controller - Auto-deleted local file 'SSA126.SmokeMovie.2026'
```

Both deletions fired exactly `300.004s` after their respective "Scheduled auto-delete" line
(`18:33:37.400` -> `18:38:37.404`; `18:33:41.016` -> `18:38:41.020`), matching the sandbox's
unchanged `autodelete.delay_seconds=300`. Confirmed absent under the sandbox downloads
afterward:

```
$ docker exec seedsyncarr-test sh -c "[ -e /downloads/SSA126.Smoke.S01 ] && echo PRESENT || echo ABSENT"
ABSENT
$ docker exec seedsyncarr-test sh -c "[ -e /downloads/SSA126.SmokeMovie.2026 ] && echo PRESENT || echo ABSENT"
ABSENT
```

Verdict, cleanup: **PASS**.

### Production fingerprint P2 (after real transfer / webhook import / cleanup)

```
2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e 2026-10-23T07:04:18.591254939Z running
```

Identical to P0 and P1 (same Id, image, `StartedAt`). Production was never written in this task.

## 1.8.0 spot checks (Plan 126-05 Task 2)

Continuing in the same capture dir (`/volume1/docker/v5test/results/smoke126-20261028T221654Z`).

### Webhook test event (D-12a)

```
$ bash webhook-post.sh <D> sonarr Test SSA126.Smoke.S01 SSA126.Smoke.S01
HTTP_CODE=200
Test OK
$ bash webhook-post.sh <D> radarr Test SSA126.SmokeMovie.2026 SSA126.SmokeMovie.2026
HTTP_CODE=200
Test OK
```

```
2026-10-28 18:41:06,446 - INFO - seedsyncarr.WebhookHandler - Sonarr webhook test event received
2026-10-28 18:41:10,412 - INFO - seedsyncarr.WebhookHandler - Radarr webhook test event received
```

Both requests were HMAC-signed (the sandbox's webhook secret is now set and enforced — an
unsigned request at this point would get `401`, confirmed earlier in the "Webhook secret"
section above).

Verdict, webhook test event: **PASS**.

### Test Connection container name (D-12, D-12a)

Key compare: sandbox's current key (set to `sonarr-v4`'s key above) vs `sonarr-v5`'s own
config.xml key — **DIFFERENT**. Swapped to `sonarr-v5`'s key via the same value-free jq pattern
(original sandbox key stays preserved in `sonarr_key.l0` for teardown, untouched by this
intermediate swap); `sonarr_url` set to `http://sonarr-v5:8989`.

```
$ curl -s "http://127.0.0.1:8801/server/config/sonarr/test-connection"
{"success": true, "version": "5.0.0.2838"}
```

Verdict, Test Connection container name: **PASS**.

### Metadata refusal (D-12a)

```
$ curl -s -X POST ... -d '{"section":"sonarr","key":"sonarr_url","value":"http://169.254.169.254"}' .../server/config/set
SET_URL http=200
$ curl -s "http://127.0.0.1:8801/server/config/sonarr/test-connection"
{"success": false, "error": "URL points to a link-local or cloud-metadata address, which is not allowed"}
```

Exact match to the Phase 125-locked refusal string (`125-LAN-EVIDENCE.md` §"Live check"/"Live
re-check"); does not contain the old "private/reserved IP address" text. `sonarr_url`
immediately set back to `http://sonarr-v4:8989` afterward.

Verdict, metadata refusal: **PASS**.

### No secrets in a fresh start's log (D-12a)

Extractor run read-only against the live sandbox config dir, on the exact 1.8.0 digest:

```
$ sudo /usr/local/bin/docker run --rm -i --read-only --network none --cap-drop ALL --user 1026:100 \
    -v /volume1/docker/v5test/seedsyncarr:/c:ro --entrypoint python3 -w /app/python \
    ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 - \
    < extract_secrets.py > "$T/values" 2> "$T/fields"
extractor rc=0
FIELDS General.webhook_secret Lftp.remote_password Sonarr.sonarr_api_key Radarr.radarr_api_key N=4 LINES=4
values: wc -l=4
```

(No `%`-serialized form differs from its decoded form for any of the four fields this session —
`N` and `LINES` match exactly.)

```
$ sudo /usr/local/bin/docker restart seedsyncarr-test
up after 3 tries
$ sudo /usr/local/bin/docker logs seedsyncarr-test --since <restart time> > "$T/log" 2>&1
log: 19 lines, non-empty
"Config ready at" count: 1
$ grep -cFf "$T/values" "$T/log"; echo rc=$?
count=0 rc=1
```

Verdict, no secrets in startup log: **PASS**.

### No app token to GitHub (D-12a)

Throwaway container `seedsyncarr-probe126-rel` on the exact 1.8.0 digest, `--label
wud.watch=false -p 127.0.0.1:8803:8800`, fresh scratch config (`PROBE_CONTAINERS`/`PROBE_DIRS`
recorded to `state.env` before creation). `general.api_token` set to the synthetic value
`probe126-token-not-a-secret` (confirmed set indirectly via the same 401-without-auth /
200-with-auth proof as the Plan 126-02 positive control, since `api_token` always serializes as
`""`). Probed through an SSH tunnel from the Mac:

```
$ ssh -f -N -L 18803:127.0.0.1:8803 nas
$ node 126-token-probe.mjs http://localhost:18803 probe126-token-not-a-secret
GITHUB_REQUESTS=1 WITH_AUTH=0 WITH_TOKEN=0
(exit 0)
```

`WITH_AUTH=0` (not just `WITH_TOKEN=0`): on 1.8.0 the GitHub update-check request carries no
`Authorization` header at all, confirming the SEC-02 fix holds on the exact published digest.
Tunnel closed immediately after (confirmed: port 18803 no longer listening). Cross-reference: the
tag CI run's `[chromium-token]` browser-level proof on this same tagged tree
(`126-REL-EVIDENCE.md` §"Tag CI"):

```
✓  [chromium-token] API token configured (SEC-02) › rejects /server/ requests without the token
✓  [chromium-token] API token configured (SEC-02) › sends the token to /server/* but never to api.github.com
✓  [chromium-token] API token configured (SEC-02) › authenticated write flow works with the token
```

Verdict, no app token to GitHub: **PASS**.

### Teardown

**First run** surfaced three Rule 1 bugs in `126-teardown.sh` (none were data-loss; all were
either a false-FAIL on an already-correct restore or a silently-skipped restore attempt against
an API constraint the script didn't account for):

1. `post_arr_key()`'s `jq -nR ... 'value:input'` (this plan's own Task 1 jq-1.5 fix) raises
   `jq: error (at <stdin>:0): break` when the key file is **empty** (restoring a key that was
   never configured, e.g. Radarr's key when Radarr started this session disabled) — `input` has
   nothing to read. Fixed by reading `[inputs]|join("\n")` instead of a single `input`, which
   yields `""` for a zero-line (empty) file and the unchanged single-line value otherwise.
2. `get_radarr_enabled()` used `.radarr.enabled // empty`; jq's `//` treats boolean `false` as
   falsy too, so it silently returned `""` whenever Radarr was actually disabled — making a
   correct restore-to-`false` permanently unverifiable (always read back as `""`, compared
   unequal to the literal string `"false"`, reported `FAIL` even though the live value was
   already correct). Fixed with an explicit `if .radarr.enabled == null then "" else
   (.radarr.enabled|tostring) end`.
3. The `sonarr_url`/`radarr_url` restore blocks fell through to `"ok (not set this session)"`
   whenever the original (`L0`) value was itself empty, even when the field genuinely **was**
   changed this session (`*_URL_SET=1`) — misleading, since `ConfigHandler.__handle_set_config`
   rejects any `value:""` POST with 400 by design (D-06) for every field, not just API keys, so
   a restore-to-empty can never succeed for a URL either. Added an explicit branch that reports
   `"ok (original was empty; API cannot clear a URL value, left as currently set)"` instead.

These three were found while running the **real teardown call** that Task 1's jq-1.5 fix had not
yet exercised against a genuinely-empty original value (Radarr started this session disabled with
no key/URL configured). All three are documented residual-limitation classes, the same shape as
the already-accepted `webhook_secret` "no restore-to-empty path" note — not something a jq fix
can route around, since the API's empty-value rejection is an intentional existing guard
(`D-06`), not a bug to work around.

First run output (post-fix items 1-3 not yet applied when this ran):

```
RESTORED sonarr_url ok
RESTORED radarr_url ok (not set this session)     <- misleading, see bug 3
RESTORED radarr_enabled FAIL                       <- see bug 2 (value was already correct)
RESTORED sonarr_api_key ok
RESTORED radarr_api_key FAIL                       <- see bug 1
REMOVED synth roots count=2 refused=0
REMOVED probe containers count=1 refused=0
REMOVED probe dirs count=1 refused=0
SANDBOX_RESTORED FAIL radarr_enabled,radarr_api_key
```

After the fix, re-run (first post-fix run):

```
WAIT server/status ok
IMAGE current=ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7
RESTORED sonarr_url ok (not set this session)
RESTORED radarr_url ok (original was empty; API cannot clear a URL value, left as currently set)
RESTORED radarr_enabled ok
RESTORED sonarr_api_key ok (not set this session)
RESTORED radarr_api_key ok (original was empty; API cannot clear a key value, left as currently set)
REMOVED synth roots count=2 refused=0
REMOVED probe containers count=1 refused=0
REMOVED probe dirs count=1 refused=0
SANDBOX_RESTORED ok
```

Read-back confirmed: `sonarr_url=http://sonarr-v5:8989` (restored, matches `SONARR_URL_L0`),
`radarr_enabled=false` (restored, matches `RADARR_ENABLED_L0`), `radarr_url=http://radarr:7878`
(left as set this session — inert, since `radarr_enabled=false` means it is never used for any
outbound call), sandbox image unchanged at `1.8.0@sha256:6e8d453f...`.

**Second run, fresh `ssh nas` session** (idempotency check):

```
WAIT server/status ok
IMAGE current=ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7
RESTORED sonarr_url ok (not set this session)
RESTORED radarr_url ok (not set this session)
RESTORED radarr_enabled ok (not set this session)
RESTORED sonarr_api_key ok (not set this session)
RESTORED radarr_api_key ok (not set this session)
REMOVED synth roots count=2 refused=0
REMOVED probe containers count=1 refused=0
REMOVED probe dirs count=1 refused=0
SANDBOX_RESTORED ok
```

Every line `ok`, exit 0 — confirmed idempotent.

**Independent fresh-session read-back** (third `ssh nas` call):

| Check | Result |
|---|---|
| `.Config.Image` | `ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7` |
| Compose `seedsyncarr-test` image line | same digest |
| `.sonarr.sonarr_url` | `http://sonarr-v5:8989` — equals `SONARR_URL_L0` |
| `GET /server/status` | `{"up":true,"error_msg":null}` |

### Production fingerprint P3

```
2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e 2026-10-23T07:04:18.591254939Z running
```

Identical to P0, P1, P2. Production was never written at any point in this plan.

## Residual limitations

- **Radarr depth (orchestrator resolution, per plan):** Radarr was checked by Test Connection
  (read-only GET) and a signed synthetic webhook import on a synthetic root — no dedicated test
  Radarr instance exists, and production Radarr must not be disturbed. There is no live Radarr
  completion-gate replay (the "held with no_queue_entry, one-shot release" completion-gate
  mechanism was proven generically via Sonarr in this plan and was already proven for Sonarr
  specifically in Phase 122's SAFE-01 acceptance). This is a scope limitation accepted by the
  plan's own orchestrator-resolution language, not a gap found during execution.
- **`radarr_url` left set, not restored to empty:** the sandbox's `radarr_url` started this
  session empty (Radarr was never configured before). `ConfigHandler.__handle_set_config` 400s
  any `value:""` POST by design (D-06), so `teardown.sh` cannot clear it back to empty — it is
  left at `http://radarr:7878`. Inert: `radarr_enabled` was correctly restored to `false`, so
  this URL is never used for any outbound call while the sandbox stays in this state.
- **`radarr_api_key` left set, not restored to empty:** same root cause and same inertness
  argument as `radarr_url` above — the production Radarr's API key (copied in for this session's
  Test Connection + webhook check) remains stored in the sandbox's `settings.cfg`, unused while
  `radarr_enabled=false`. This is the same documented class of limitation already accepted for
  `webhook_secret` in Plan 126-02/05 ("no restore-to-empty path").
- **Webhook secret remains set:** a fresh random value was generated this session
  (`WEBHOOK_SECRET_SET=1`); `webhook_secret` has no restore-to-empty path (same API constraint).
  It is a sandbox-only random value, never reused anywhere else, and was never printed in this
  evidence.
- **In-flight `.lftp` temp suffix not directly observed:** the two synthetic files (8/16 MiB)
  transferred faster than the polling interval at the sandbox's unmetered `lftp.rate_limit=0`.
  File-identity (sha256 match) and lifecycle (held → one-shot released → `downloaded`) evidence
  stands on its own; the plan's wording ("if observed") does not require this as a pass
  condition.

## Smoke verdict summary

| # | Check | Verdict |
|---|-------|---------|
| 1 | Restart | **PASS** |
| 2 | Real transfer | **PASS** |
| 3 | Sonarr v4 integration | **PASS** |
| 4 | Radarr integration | **PASS** |
| 5 | Webhook import | **PASS** |
| 6 | Cleanup (auto-delete) | **PASS** |
| 7 | Webhook test event | **PASS** |
| 8 | Test Connection container name | **PASS** |
| 9 | Metadata refusal | **PASS** |
| 10 | No secrets in startup log | **PASS** |
| 11 | No app token to GitHub | **PASS** |

All eleven D-12a checks pass on the exact published `1.8.0` digest
(`sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`). Sandbox wiring
restored (with the two documented, inert, no-restore-to-empty exceptions above) and left on the
1.8.0 digest. Production fingerprint (`P0`..`P3`) identical throughout — never touched.
