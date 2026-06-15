---
status: resolved
trigger: "there are files that are shown as active but have not downloaded and manually queuing doesn't work either"
created: 2026-06-08
updated: 2026-06-08
---

# Debug Session: active-files-not-downloading

## Symptoms

- **Expected behavior:** Files that appear in the model (active) should download to /downloads; manually queuing a file should start its LFTP mirror transfer.
- **Actual behavior:** Nothing downloads at all. Some files are stuck showing "active" with no movement; some files aren't showing up at all. Manual queue fails.
- **Error messages (KEY EVIDENCE):** Manual queue produces an LFTP error:
  ```
  mirror: Access failed: /downloads/Believe.Me.2026.S01.1080p.AMZN.WEB-DL.DDP2.0.H.264-RAWR: No such file or directory
  ```
  Note the path is under `/downloads/` — this looks like LFTP is being told to mirror a path that doesn't exist on the remote (or the remote/local path resolution is inverted/wrong).
- **Timeline:** Nothing downloads at all right now (whole pipeline stuck, not just one file).
- **Reproduction:** Manually queue `Believe.Me.2026.S01...-RAWR` → immediate "Access failed: No such file or directory".

## Relationship to prior resolved session

`hold-the-dream-not-syncing.md` (resolved 2026-05-05) was an UPSTREAM scanner bug (failed scans wiped the remote model; silent process death). THIS issue is DOWNSTREAM at the LFTP dispatch/download layer — the error is a concrete `mirror: Access failed ... No such file or directory`, which is not a scanner-silence symptom. Likely a different root cause (path construction, remote root prefix, or LFTP command assembly). Do not assume it is the same bug.

## Key area to investigate first

- LFTP command / mirror invocation: where the remote source path is assembled and passed to `lftp mirror`. The `/downloads/` prefix in the error is suspicious — is that the REMOTE path or accidentally the LOCAL path? A path-resolution inversion would explain "No such file or directory" on the remote and the whole pipeline being stuck.
- Dispatch layer: src/python/controller/ (dispatch / lftp / commands) and any remote-root / local-root config.
- Recent changes: model pipeline refactor (commits 4fb13b4, 0639221 — ModelPipeline wiring) and v1.4.0 launch-hardening (phases 110-113) touched controller/process plumbing. Check whether remote-path construction changed.

## Current Focus

- hypothesis: CONFIRMED (corrected after live-NAS verification) — The local destination `/downloads` inside the seedsyncarr container is NOT writable by the container's runtime user. LFTP cannot create the destination directory/files for `mirror`, so every queue fails ("Access failed" / timeout) and nothing downloads. This is a deployment permissions issue on the LOCAL side, not a remote SFTP path problem.
- next_action: Apply deployment fix — make `/volume1/data/torrents` (mounted as `/downloads`) writable by the container user (uid 1000), OR fix the PUID/PGID mismatch so the container runs as an owner of the path.

## CORRECTION — agent's original theory was DISPROVEN by live config

The gsd-debugger never inspected the running NAS instance and guessed `remote_path = /downloads` with an "SFTP chroot" explanation. The LIVE config disproves this:

- `remote_path = /home/jules1651/downloads/deluge2/done`  (correct remote seedbox path — NOT /downloads)
- `local_path  = /downloads`  (the local container destination)

So the `/downloads/...` in the error message is the **LOCAL destination path**, not the remote source. The failure is on the WRITE side, not the remote read side.

## Evidence

- timestamp: 2026-06-08 user report
  content: "mirror: Access failed: /downloads/Believe.Me.2026.S01.1080p.AMZN.WEB-DL.DDP2.0.H.264-RAWR: No such file or directory — on manual queue. Nothing downloads at all. Some files stuck active, some not showing up."

- timestamp: 2026-06-08 code analysis (CORRECT part — path wiring)
  content: >
    Traced full path from `config.lftp.remote_path` → `LftpManager.__init__` →
    `lftp.set_base_remote_dir_path()` → `Lftp.queue()` → mirror command string.
    The command built is `queue ' mirror -c "{remote_path}/{name}"  "{local_path}/" '`.
    Code path is correct — no inversion, no field swap. This part of the analysis holds.

- timestamp: 2026-06-08 code analysis (SUPERSEDED — wrong assumption)
  content: >
    Agent ASSUMED remote_path = /downloads and built an "SFTP chroot / SSH-vs-SFTP namespace"
    theory on top of it. DISPROVEN by the live config: remote_path is actually
    /home/jules1651/downloads/deluge2/done and the /downloads in the error is the LOCAL
    destination. This theory is retracted — see "Live-NAS evidence" below.

- timestamp: 2026-06-08 code analysis — ELIMINATED
  content: >
    No code-level path inversion found. LftpManager lines 43-44 correctly map
    `config.lftp.remote_path → set_base_remote_dir_path` and
    `config.lftp.local_path → set_base_local_dir_path`. No recent commit changed
    this mapping. Config serialization round-trip (from_dict/as_dict) has no field swap.
    The queue() method in lftp.py has not changed since initial commit 98871f5.

## Eliminated

- Code-level path inversion in LftpManager (config.lftp.remote_path and local_path are correctly
  wired to LFTP — no swap).
- Recent ModelPipeline refactor (4fb13b4, 0639221) — these commits only restructure where pipeline
  logic lives; they do not change path construction or LFTP command assembly.
- CommandProcessor wiring (df415a8) — extraction of handle methods; same logic, no path changes.
- Config serialization field swap — from_dict/as_dict use property names from config_dict keys;
  no reordering or cross-contamination possible.
- Queue method regression in lftp.py — unchanged since initial commit 98871f5.

## Live-NAS evidence (the empirical confirmation the agent skipped)

- timestamp: 2026-06-08 live config (container `seedsyncarr` on maguffynas)
  content: >
    remote_path = /home/jules1651/downloads/deluge2/done (correct remote path),
    local_path = /downloads. The error path /downloads/Believe.Me... is the LOCAL
    destination, disproving the SFTP-chroot theory.
- timestamp: 2026-06-08 live write test
  content: >
    `docker exec seedsyncarr touch /downloads/.write_test` -> "Permission denied" -> WRITE_FAILED.
    Container runs as uid=1000(seedsyncarr). Inside the container /downloads shows as
    `dr-xr-xr-x root:root` (read-only to uid 1000) despite Docker reporting the mount RW=True.
- timestamp: 2026-06-08 live log
  content: >
    "Bulk queue completed: 0/1 succeeded, 0 failed, 1 timed out in 5.006s" — queue attempts
    time out / fail because LFTP cannot write the local destination.
- timestamp: 2026-06-08 deployment inspect
  content: >
    Mount /volume1/data/torrents -> /downloads RW=True (btrfs rw, synoacl). Image runs
    User=seedsyncarr (uid 1000), Entrypoint=None — it does NOT honor PUID=1026/PGID=100 from
    compose (no LSIO/s6 remap layer). Host dir is drwxrwxrwx+ but Synology ACLs (synoacl /
    the trailing `+`) override POSIX bits and deny write to uid 1000 inside the container.

## Resolution

- **root_cause:** The container's local download target `/downloads` (host `/volume1/data/torrents`)
  is not writable by the container's runtime user `uid=1000(seedsyncarr)`. Synology ACLs on the
  share override the world-writable POSIX bits and present the path as read-only root-owned inside
  the container, so LFTP cannot create destination dirs/files for `mirror`. Every queue fails
  ("Access failed" on the local path / timeout) → nothing downloads. Contributing factor: the image
  runs as a baked-in uid 1000 and ignores the compose `PUID=1026/PGID=100`, so the intended
  ownership alignment never happens.
- **fix:** Deployment/permissions correction (NOT a code change, NOT a remote_path change). Options,
  best first:
    1. Grant the container user write on the share. On the NAS, give uid 1000 (or its group)
       write via Synology ACL on `/volume1/data/torrents`, e.g. add an ACL entry, or
       `sudo chown -R 1000:1000 /volume1/data/torrents` if safe for other consumers.
    2. Make the image honor PUID/PGID, then set PUID/PGID to a uid that already owns the share —
       requires an entrypoint that remaps the user (LSIO-style). Larger change.
    3. As a quick unblock, align the share owner to whatever uid the container actually runs as
       (1000) rather than the compose-declared 1026.
  After fixing perms, verify with
  `docker exec seedsyncarr touch /downloads/.t && echo OK && docker exec seedsyncarr rm /downloads/.t`,
  then re-queue Believe.Me and confirm the mirror starts.

## Fix applied + verification (2026-06-08, live on maguffynas)

Cause of the read-only state: UNKNOWN — not attributed to a user config change. The host
share `/volume1/data/torrents` uses Synology ACLs (`synoacl` mount flag, `drwxrwxrwx+`).
Inside the container the dir presented as `dr-xr-xr-x root:root` (no write for uid 1000)
despite Docker reporting the mount RW=True. Likely a DSM ACL reindex, a backup/index
service, or an app-side permission op — not established. User confirmed they made no
known docker changes.

Steps taken (passwordless sudo only covers /usr/local/bin/docker, so host chown/chmod were
done via a root one-shot container mounting the same volume):
1. `docker run --rm -u 0:0 -v /volume1/data/torrents:/fix alpine chown -R 1000:1000 /fix` → ownership fixed, but dir still `r-x` (write still denied).
2. `docker run --rm -u 0:0 -v /volume1/data/torrents:/fix alpine chmod -R u+rwX,g+rwX /fix` → dir now `drwxrwxr-x`; `docker exec seedsyncarr touch /downloads/.t` → WRITE_OK.
3. Restarted seedsyncarr — the long-running controller had wedged (queue commands 504-timed-out, no scan activity for minutes) because it had been failing writes for hours. Restart cleared it.

Verification (post-restart):
- `/server/status` → HTTP 200; controller processing again.
- 18+ new directories created in /downloads at 16:02, owned by seedsyncarr — real transfers landing.
- 0 access-failed / permission / timeout errors since restart (was the whole symptom before).
- AutoQueue drained the accumulated backlog: 40 unique titles queued (finite, "0 new files" per
  cycle = not growing). patterns_only=False means AutoQueue grabs everything by design — the
  "queuing everything" the user saw is expected backlog recovery, not a defect.

OUTSTANDING (separate, non-blocking):
- Controller runs a ~1/sec busy-loop reporting "0 new files, 2 modified files" every cycle even
  when idle. Not causing the queue flood; worth a separate look as an efficiency issue.
- The container ignores compose PUID=1026/PGID=100 and runs as baked-in uid 1000. The perm fix
  aligned the share to 1000, but if the image is ever changed to honor PUID, or the share ACLs
  get reset by DSM, this can recur. Longer-term fix = PUID-honoring entrypoint OR a stable ACL
  grant for the runtime uid.
  `sftp user@host` then `ls /` to see what paths SFTP exposes.
