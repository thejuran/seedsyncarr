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
