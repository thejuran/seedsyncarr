# Phase 78 UAT — Environment Setup & Tear-Down

**Scope:** bring up the disposable SSH target + bounded local FS + seedsyncarr (D-01..D-05 of `78-CONTEXT.md`). Plan 02 (`78-02-PLAN.md`) is the UAT execution; that plan assumes this environment is live.

**macOS note:** seedsyncarr hardcodes `/usr/bin/lftp` (`src/python/lftp/lftp.py:62`). macOS cannot provide that path (SIP-protected `/usr/bin`), so the Phase 78 compose stack runs the backend itself in a Linux container. Linux dev hosts can alternatively skip the `seedsyncarr` service and run from source — see §3b.

## 0. Host prerequisites

- Docker + docker-compose v2 (Docker Desktop on macOS; docker-ce on Linux)
- Node + Angular CLI (`cd src/angular && npm ci`)
- Python 3.11+ and Poetry — only if running the backend from source (§3b)
- Optional: `sshpass` (Linux: `apt install sshpass`; macOS: `brew install hudochenkov/sshpass/sshpass`). Only needed for the §1 smoke; the backend's own Sshcp opens the session when it starts scanning and that is the real smoke.

## 1. Bring up the stack (ssh-target + seedsyncarr)

```
cd .planning/phases/78-storage-tile-live-seedbox-uat
docker compose up -d --build
# sanity #1 — ssh-target tmpfs at /data is bounded to exactly 100 MiB
docker exec seedsyncarr_phase78_ssh_target df -B1 /data | tail -1
# expect: tmpfs  104857600  0  104857600  0%  /data
# sanity #2 — seedsyncarr tmpfs at /data/local is bounded to ~100 MiB
docker exec seedsyncarr_phase78_app df -B1 /data/local | tail -1
# expect: tmpfs  104857600  0  104857600  0%  /data/local
# sanity #3 — backend is serving on 127.0.0.1:8800
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8800/server/status -m 2
# expect: 200
```

Container `ssh-target` is bound to `127.0.0.1:2222` only (T-78-01). Credentials `seeduser:seedpass` are disposable (T-78-03). The `seedsyncarr` service reaches the ssh target via compose DNS (`ssh-target:1234`), not the host port mapping.

Optional manual SSH smoke (from the host, requires sshpass):
```
sshpass -p seedpass ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 seeduser@127.0.0.1 'df -B1 /data'
# fallback without sshpass (interactive prompt, password is `seedpass`):
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 seeduser@127.0.0.1 'df -B1 /data'
```

## 2. Bounded local FS for the Local Storage tile (D-05)

The backend container provisions its own bounded local FS via a `tmpfs` mount at `/data/local` (size=100m) — no host-side `mount -o loop` or `hdiutil` is required when using the dockerized flow. `shutil.disk_usage('/data/local')` inside the container reports total ≈ 104857600.

Host-side alternatives (used only if running the backend from source — see §3b):

### Linux (loop-mounted ext4, ~100 MB)

```
./scripts/bound-local-fs.sh up
# expect: df line at /tmp/seedsyncarr-phase78-local with total ~104857600
```

### macOS (hdiutil HFS+ image, ~100 MB)

```
hdiutil create -size 100m -fs 'Case-sensitive HFS+' -volname seedsyncarr-p78 /tmp/seedsyncarr-phase78-local.dmg
mkdir -p /tmp/seedsyncarr-phase78-local
hdiutil attach /tmp/seedsyncarr-phase78-local.dmg -mountpoint /tmp/seedsyncarr-phase78-local -nobrowse
python3 -c "import shutil; u = shutil.disk_usage('/tmp/seedsyncarr-phase78-local'); print('total=' + str(u.total), 'used=' + str(u.used), 'free=' + str(u.free))"
# expect: total ~1048xxxxx
```

## 3. Frontend (ng serve + proxy)

The Angular app calls `/server/...` relative URLs. The phase's `proxy.conf.json` forwards `/server` → `http://127.0.0.1:8800` (the published backend port from §1):

```
cd src/angular
npx ng serve --port 4200 --proxy-config ../../.planning/phases/78-storage-tile-live-seedbox-uat/seedsyncarr-test-config/proxy.conf.json
# Dashboard at http://127.0.0.1:4200/
```

## 3b. Alternative: run backend from source (Linux only)

If the dev host has `/usr/bin/lftp` available, skip the `seedsyncarr` service in compose (`docker compose up -d ssh-target` only), set up a host-side bounded local FS via §2, then:

```
cd src/python
python3 seedsyncarr.py \
  -c ../../.planning/phases/78-storage-tile-live-seedbox-uat/seedsyncarr-test-config \
  --html ../angular/src \
  --scanfs ../../.planning/phases/78-storage-tile-live-seedbox-uat/scanfs \
  --debug 2>&1 | tee /tmp/seedsyncarr-phase78-backend.log
```

This path also requires `remote_address` + `remote_port` in `settings.cfg` to point at `127.0.0.1` + `2222` instead of `ssh-target` + `1234`, and `local_path` to point at the host-side mount.

## 4. UAT-ready sanity check — confirm tiles render in capacity mode

1. Wait ~10 s after the stack boots for the first remote + local scan cycle to complete.
2. Tap the SSE stream and confirm a non-null `storage` block:
   ```
   curl -N -s -m 15 http://127.0.0.1:8800/server/status | head -c 4000 | tee /tmp/seedsyncarr-phase78-first-scan.log
   # expect: data: {"server":{...},"controller":{...},"storage":{"local_total":<int>,"local_used":<int>,"remote_total":104857600,"remote_used":<int>}}
   ```
3. Open http://127.0.0.1:4200/ (or via `gsd-browser navigate`). Both **Remote Storage** and **Local Storage** tiles MUST show an integer `N%` + `of 100.00 MB` + progress bar + `X.XX MB used`. This is the gate that unblocks Plan 02 — if either tile is still showing the tracked-bytes fallback layout, stop and debug before continuing.

Common causes of tiles stuck in fallback mode:
  - First scan cycle hasn't completed yet → wait another 10 s and reload.
  - SSE `/server/status` stream not being consumed by the Angular `ServerStatusService` → open browser devtools Network tab and confirm the EventSource is open.
  - `storage` block keys missing from the frame → re-run the `curl` above; if `"storage"` is not present, inspect `docker logs seedsyncarr_phase78_app` for the `df` / `disk_usage` failure reason.

## 5. Tear-down

```
# 1. Stop ng serve (Ctrl-C in its terminal)
# 2. Tear down the compose stack (both containers, tmpfs included)
cd .planning/phases/78-storage-tile-live-seedbox-uat
docker compose down -v
# 3. If a host-side bounded local FS was brought up for §3b, tear it down too:
# Linux:
./scripts/bound-local-fs.sh down
# macOS:
hdiutil detach /tmp/seedsyncarr-phase78-local && rm /tmp/seedsyncarr-phase78-local.dmg
```

## 6. Re-run between UAT items

Plan 02 mutates `/data` inside ssh-target via `docker exec ... fallocate` and `/data/local` inside seedsyncarr via the same pattern. No host-side teardown is required between items. Tear-down only at the end of Plan 02.
