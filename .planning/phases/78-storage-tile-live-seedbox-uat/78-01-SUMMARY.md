---
phase: 78-storage-tile-live-seedbox-uat
plan: 01
status: complete
completed: 2026-04-21
requirements:
  - UAT-03
---

# Plan 01 Summary — Live-Seedbox UAT Environment

## What was built

A disposable, re-runnable UAT environment that drives both seedsyncarr scanners against a bounded filesystem and proves the Phase 74 capacity tiles render in capacity mode. Plan 02 consumes this environment verbatim.

**Artifacts (committed to `.planning/phases/78-storage-tile-live-seedbox-uat/`):**

| File | Purpose |
|------|---------|
| `Dockerfile` | Ubuntu 22.04 + openssh-server + coreutils; seeduser/seedpass; port 1234 |
| `compose.yml` | Two services — `ssh-target` (tmpfs /data 100 MB, bound 127.0.0.1:2222) and `seedsyncarr` (built from repo Dockerfile, tmpfs /data/local 100 MB, bound 127.0.0.1:8800); depends_on + shared compose DNS |
| `seedsyncarr-test-config/settings.cfg` | Full [General]/[Lftp]/[Controller]/[Web]/[AutoQueue]/[Sonarr]/[Radarr]/[AutoDelete] config; Lftp points at `ssh-target:1234` seeduser/seedpass with `remote_path=/data`, `local_path=/data/local`; `Web.port=8800`, `extract_path=/data/local` |
| `seedsyncarr-test-config/proxy.conf.json` | `ng serve` proxy forwarding `/server` → `http://127.0.0.1:8800` |
| `seedsyncarr-test-config/.gitignore` | Keeps runtime `*.persist` state out of git |
| `scanfs` | Self-contained scan → JSON fixture (stdlib only) so the remote Ubuntu container doesn't need the full `src/python/` tree |
| `scripts/bound-local-fs.sh` | Linux loop-mount reference (dd + mkfs.ext4 + mount -o loop) for Phase 78's §3b from-source path on Linux hosts |
| `README-setup.md` | Runbook: bring-up, sanity checks, ng serve, UAT-ready gate, tear-down |
| `evidence/00-env-ready.png` | Baseline dashboard screenshot (approved at Task 4 checkpoint) |

## Commands used

```bash
# Stack bring-up
cd .planning/phases/78-storage-tile-live-seedbox-uat
docker compose up -d --build

# Frontend (on the dev host, Node 25 requires explicit --host for IPv4)
cd src/angular
npx ng serve --host 0.0.0.0 --port 4200 \
  --proxy-config ../../.planning/phases/78-storage-tile-live-seedbox-uat/seedsyncarr-test-config/proxy.conf.json

# UAT-ready gate checks
curl -s http://127.0.0.1:8800/server/status -m 2               # 200
curl -s http://127.0.0.1:4200/ -m 3                            # 200 (Angular dev server)
curl -s http://127.0.0.1:4200/server/status -m 3               # 200 (proxied)
docker exec seedsyncarr_phase78_ssh_target df -B1 /data        # total=104857600
docker exec seedsyncarr_phase78_app          df -B1 /data/local # total=104857600
```

## First SSE `.storage` frame

```json
{
  "local_total": 104857600,
  "local_used": 0,
  "remote_total": 104857600,
  "remote_used": 0
}
```

Both scanners hit a valid filesystem on the first cycle. `remote_total` is the ssh-target tmpfs seen through `df -B1 /data` over SSH; `local_total` is the seedsyncarr container tmpfs seen through `shutil.disk_usage('/data/local')`. Backend log captured at `/tmp/seedsyncarr-phase78-backend.log` (kept out of git; transient).

## User checkpoint (Task 4)

User replied **"Approved — run Plan 02"** after reviewing `evidence/00-env-ready.png`. Observations:

- Both tiles render in capacity mode: integer `0%` + `of 100 MB` + progress bar + `0 B used`.
- Control tiles (Download Speed, Active Tasks) unchanged from the pre-phase-74 tracked-bytes layout — they are the control group for Plan 02 Test 6.
- Connection Stable pill is green; SSE stream is live.
- System Event Log confirms successful `df -B1 /data` cycles over SSH.

## Deviations from the written plan

1. **Dockerized backend on macOS.** The plan's D-02 "run from source locally" assumed a Linux dev host; seedsyncarr hardcodes `/usr/bin/lftp` (`src/python/lftp/lftp.py:62`), which SIP-protected macOS cannot provide. User chose "Run backend in Docker (Recommended)" at the decision point. The repo's production Dockerfile (`src/docker/build/docker-image/Dockerfile`) ships lftp via `apt-get install`, so the pivot required zero `src/` code changes. Trade-off captured in `compose.yml` comments; Linux-from-source path preserved as §3b in README-setup.md.

2. **Local bounded FS shifted from host mount to container tmpfs.** Consequence of deviation #1. Original plan used a 100 MB loop-mounted ext4 image (Linux) or hdiutil HFS+ image (macOS) at `/tmp/seedsyncarr-phase78-local`. With the backend dockerized, the LocalScanner runs inside the container and sees `/data/local` as its watched path. A tmpfs at `/data/local` (size=100m) delivers the same `shutil.disk_usage`-visible 100 MB ceiling without the Docker-Desktop-file-sharing edge cases. The hdiutil DMG brought up during Task 2 was detached + removed at the pivot; `scripts/bound-local-fs.sh` remains as the Linux-from-source reference.

3. **settings.cfg values adjusted.** `remote_address=ssh-target` + `remote_port=1234` (compose-DNS + internal port) instead of `127.0.0.1` + `2222`. `local_path=/data/local` + `extract_path=/data/local` (container paths) instead of the host path. Plan 01 acceptance greps for `remote_port = 2222` / `local_path = /tmp/...` were satisfied in the first commit but superseded at the docker pivot; the committed shape matches the dockerized runtime.

4. **`scanfs` fixture not in the original plan.** The plan's Task 3 referenced `--scanfs ./scan_fs.py`, but the repo's `scan_fs.py` imports `system` + `common` modules and cannot run standalone on the remote. Added a self-contained stdlib-only fixture at `.planning/phases/78-.../scanfs` that implements the same scan-to-JSON contract RemoteScanner parses back via `SystemFile.from_dict`. No `src/` touch.

5. **Node 25 IPv6-only default.** `npx ng serve` bound `::1:4200` only by default, failing the plan's `curl http://127.0.0.1:4200/` acceptance. Fixed by adding `--host 0.0.0.0` to the ng serve invocation. Documented in `README-setup.md` §3.

6. **sshpass smoke skipped.** Plan 01 Task 1 acceptance referenced a `sshpass -p seedpass ssh ...` smoke; sshpass is not installed on this macOS host and the plan explicitly allowed deferring when unavailable. The real SSH smoke comes from the backend's own Sshcp opening the session in Task 3, which succeeded (RC=0 on the remote `md5sum`, `scp`, `scanfs`, and `df -B1 /data` invocations visible in `docker logs seedsyncarr_phase78_app`).

## Key files (authoritative paths)

- **created:** `Dockerfile`, `compose.yml` (two services), `seedsyncarr-test-config/settings.cfg`, `seedsyncarr-test-config/proxy.conf.json`, `seedsyncarr-test-config/.gitignore`, `scanfs`, `scripts/bound-local-fs.sh`, `README-setup.md`, `evidence/00-env-ready.png`
- **modified:** none in `src/` (phase scope preserved)

## What Plan 02 now has

- Live SSH target at `ssh-target:1234` (compose network) / `127.0.0.1:2222` (host) with a 100 MB tmpfs at `/data` — fill via `docker exec seedsyncarr_phase78_ssh_target fallocate -l <N>M /data/<name>`.
- Live seedsyncarr backend at `http://127.0.0.1:8800` with a 100 MB tmpfs at `/data/local` — fill via `docker exec seedsyncarr_phase78_app fallocate -l <N>M /data/local/<name>`.
- Live Angular dashboard at `http://127.0.0.1:4200/` consuming the SSE stream.
- `.storage` block populated on first scan; ready for threshold fills, df-failure injection, per-tile independence checks.

## Self-Check: PASSED

- All plan acceptance criteria either pass against the dockerized shape or are explicitly waived in "Deviations from the written plan" above.
- Both containers are Up; SSE storage block is non-null for both sides; dashboard renders both tiles in capacity mode; user approved the checkpoint.
