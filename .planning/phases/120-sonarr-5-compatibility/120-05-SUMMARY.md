---
phase: 120-sonarr-5-compatibility
plan: 05
status: complete
subsystem: live-capture
tags: [sonarr5, live-capture, nas-sandbox, webhook-sink, deluge-per-torrent, completion-gate]
requires:
  - phase: 120-02
    provides: 120-webhook_sink.py (disposable capture sink) and 120-sanitize_fixtures.py
provides:
  - Live Sonarr 5.0.0.2701 evidence for SON5-01, SON5-02 (incomplete -> complete pair, same downloadId) and SON5-03 (Test + real Download webhook, single Recorded webhook import)
  - Raw fixture sources on the NAS for Plan 06 (system_status, testconn-*, webhook_test, webhook_download, queue_details_incomplete/complete)
  - 120-teardown.sh, the single idempotent sandbox teardown (defaults to its own dir; FAILs on missing Deluge state)
affects: [120-06]
tech-stack:
  added: []
  patterns:
    - "Staged NAS scripts with trap 'exit 130' INT TERM HUP plus an EXIT trap that runs teardown.sh"
    - "Per-torrent Deluge Web JSON-RPC (set_torrent_options, move_storage) on the capture torrent only"
key-files:
  created:
    - .planning/phases/120-sonarr-5-compatibility/120-teardown.sh
    - .planning/phases/120-sonarr-5-compatibility/120-CAPTURE-NOTES.md
  modified:
    - .planning/phases/120-sonarr-5-compatibility/deferred-items.md
key-decisions:
  - "D-14 grab-private (owner): Hacks S04E01 1080p HEVC x265-MeGusta from TorrentDay via sonarr-v5 POST release; the torrent keeps seeding and is never removed"
  - "MODE A (per-torrent) used; the Deluge password comes from the sandbox Sonarr DB because the API masks it"
  - "The 17:01:49 early 'Completion hold cleared' is the gate's prune path, not a release: no transfer, re-held on a stale snapshot, released only on a completed snapshot; version-independent, logged as an observability item"
requirements-completed: [SON5-01, SON5-02, SON5-03]
duration: ~4h wall clock, including the owner decision pauses and a seedbox SSH outage
completed: 2026-10-20
---

# Phase 120 Plan 05: Sonarr 5 live capture Summary

On the NAS sandbox (seedsyncarr-test 1.7.6 against sonarr-v5 **5.0.0.2701**), one owner-approved TorrentDay episode was captured end to end:
- Test Connection succeeds over the Tailscale URL (SON5-01).
- The same downloadId was held as "Still downloading" while incomplete, and released and transferred only after Sonarr reported it complete (SON5-02).
- The real Sonarr 5 Download webhook produced exactly one `Recorded webhook import` (SON5-03).

Every exit path ended in `SANDBOX_RESTORED ok`, and the torrent was left seeding.

## Accomplishments
- **SON5-01.** The container-name URL fails with the known private-IP limitation (D-02). The Tailscale URL returns `success=true version=5.0.0.2701`. The URL was restored and verified.
- **SON5-02** (`PAIR_OK 1`).
  - Incomplete: `queue_details_incomplete.json` (`downloading`, `sizeleft=165052416`), the log line `Completion hold for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta': Still downloading`, and stream `hold_reason=still_downloading`.
  - Complete: `queue_details_complete.json` for the same downloadId (`completed`, `sizeleft=0`, `importPending`), then `Completion hold cleared`, `Auto queueing` and `Action.QUEUE` at 17:03:21 app clock.
- **SON5-03** (`WEBHOOK_OK`).
  - Test events: Seedsyncarr returned access-log `200 7` from `Sonarr/5.0.0.2701` with zero import lines, and the sink caught `webhook_test.json`.
  - Real import: `webhook_download.json` (eventType `Download`, the same downloadId, `episodeFile.sourcePath` set) arrived with `import enqueued` → `import detected … matched` → `Recorded webhook import: '<root>' (child: '<mkv>')`, `IMPORT_LINES single=1 total=1 mine=1`.
- **D-07.** The version was 5.0.0.2701 at every check: L0, L1 and L3 setup before and after, and V_BEFORE and V_AFTER around the completion capture.

## Task Commits
1. **Task 1: Teardown script, rig fingerprint, SON5-01, L3 setup, D-14 inventory** - `62ad5de` (feat)
2. **Task 2: D-14 checkpoint.** The first answer was owner-adds-content, with teardown: `090654d` (docs). The owner later revised it to grab-private.
3. **Step 0: teardown fix** - `ea8c85c` (fix)
4. **Task 3: capture** - `a3c168d` (grab, SSH outage, incomplete evidence, S02 findings), `f675967` (completion, webhook, teardown), plus this plan's final docs commit (hold-clear account and SUMMARY)
5. **Task 4: skipped.** The plan skips it because `CAPTURE_STATUS=COMPLETE`.

## Verification (observed)
- Task 3 `<verify>` run on the NAS printed: `CAPTURE_STATUS=COMPLETE`, sink containers `0`, the three files at mode `600` (1154, 1367 and 3306 B), `PAIR_OK 1`, `WEBHOOK_OK`.
- Fresh-session teardown read-back: `RESTORED sonarr_url ok`, `DELUGE per-torrent mode, no client change (downloadDirectory matches L0: yes)`, `RESTORED notifications count=1 son5-capture-present=0`, `NOTIF_URLS_OK`, `REMOVED sink (absent)`, `SANDBOX_RESTORED ok`, exit=0.
- The hygiene grep on the notes (32-hex, `100.x`, `/home/<user>`, `magnet:`, docker IPs, seedbox host) printed 0.
- `bash -n` and `shellcheck -S warning` on 120-teardown.sh both pass. The three teardown failure-mode cases were run on the NAS (FAIL, FAIL, ok).
- Not verified live: the missing-entry, API-error and unrelated-download negatives (CI from Plan 04 is authoritative). The model stream between 17:01:49 and 17:03:20 was not captured.

## Deviations from Plan

1. **[Rule 3] Deluge password source.** The sonarr-v5 API returns the Deluge password masked, so MODE A could not get it as the plan described. It is read read-only from the sandbox Sonarr DB (`/volume1/docker/v5test/sonarr/sonarr.db`) into a variable and never printed. The source stays inside v5test scope.
2. **[Rule 2, owner requirement] Per-torrent ratio flags.** On the capture torrent only, `stop_at_ratio=false` and `remove_at_ratio=false`, so Deluge never pauses it at a ratio and Sonarr never sees it as removable. No torrent was removed, paused or deleted from the queue, and sonarr-v5 has `removeCompletedDownloads=false`.
3. **[Rule 3] Temporary per-torrent speed cap.** The seedbox fills 359 MB in seconds, so the capture torrent was capped at 256 KiB/s right after it was detected (at 16%). The cap was cut to 4 KiB/s while the seedbox refused SSH (15:45 to 15:55), so that the "still downloading" window survived. The owner approved removing it, and it was lifted to -1 (unlimited) at 16:01:32, after the monitor and sink were live. The pre-cap value was not recorded; -1 is Deluge's default, and Sonarr sets no limit.
4. **[Rule 1] Trap fix.** The plan's `trap 'bash "$D/teardown.sh"' EXIT INT TERM HUP` does not exit on a signal; after teardown the script keeps running. Later scripts use `trap 'exit 130' INT TERM HUP` plus an EXIT trap. The first `run-L2.sh` was stopped with SIGKILL, and teardown was run by hand (`SANDBOX_RESTORED ok`).
5. **[Rule 1] Teardown hardening** (`ea8c85c`). `D` defaults to the script's own dir. A missing `state.env`, `MODE=A` without L0, or `MODE=B` without the saved client JSON now FAIL instead of silently passing. This changes the plan's "missing state.env = clean" contract on purpose, at the coordinator's direction.
6. **The incomplete snapshot was taken outside the main loop**, read-only at 15:57 after SSH recovered, while the capture notification was **not** live. The pair is still the same downloadId (`PAIR_OK 1`), and the sink plus notification were re-created (NID 5) before the cap was lifted.
7. **The capture dir was reused** (`son5-capture-20261020-163945`) for the completion half, so both halves sit side by side. `state.env` holds several `CAPTURE_STATUS` lines; the last one is `COMPLETE`.
8. **Task 4 skipped**, as the plan specifies for `CAPTURE_STATUS=COMPLETE`.

## Assumption Drift (advisory)
- **Found during Task 3.** The plan assumed MODE A could read the Deluge password from `GET downloadclient`. Sonarr 5 masks it, so the DB was used instead (deviation 1).
- **Found during Task 3.** The plan assumed a seedbox-paced download leaves a natural incomplete window. In fact it fills in seconds, so a per-torrent cap was needed (deviation 3).
- **Found during Task 3.** The plan assumed the remote scanner stays healthy. The seedbox refused SSH for about 10 minutes, which blocked the gate from seeing the root.

## Early hold-clear finding (17:01:49 app clock)
"Completion hold cleared" was logged while Sonarr's queue still said `downloading`. The full account is in 120-CAPTURE-NOTES.md.

**Verdict: not a safety gap, version-independent, and an observability defect.**
- **Cause.** The root left the AutoQueue stability sweep, because the remote size changed when the download finished at about 16:01:36 host. `CompletionGate._run(prune=True)` then dropped the hold through `_clear_hold`, which uses the same "cleared" message as a release.
- **Nothing was transferred.** No queue or transfer happened between 17:01:49 and 17:03:21, and the local root did not exist at 17:03:22.
- **Re-held, then released on proof.** When the root re-entered the candidates at 17:03:20, the gate re-held it on its stale "downloading" snapshot. It released only after a fresh `completed` / `sizeleft=0` snapshot arrived, 0.57 s later.
- **No premature transfer is possible via this path.** The wording issue is logged in deferred-items.md.

## Owner cleanup (keep-seeding torrent)
- **Deluge:** `Hacks.S04E01.1080p.HEVC.x265-MeGusta`, label `tv-v5test`, **Seeding**, 100%, stop/remove-at-ratio off. The seeding data is on the seedbox at `~/v5test/Hacks.S04E01.1080p.HEVC.x265-MeGusta`.
- **NAS:** the imported episode is at `/volume1/data/v5test/media/tv/Hacks/Season 4/Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv`. seedsyncarr-test auto-deletes its staging copy in `/volume1/data/v5test/torrents/` 300 s after import.

## Raw captures for Plan 06
`/volume1/docker/v5test/results/son5-capture-20261020-163945/` (mode 0700, files 0600). It holds `system_status.json`/`status-L0.json`, `webhook_test.json`, `webhook_download.json`, `queue_details_incomplete.json`, `queue_details_complete.json`, the `log-*` extracts, `stream-L2-incomplete.txt`, 119 queue snapshots and `state.env`.

This run did not re-capture the `testconn-*.json` (SON5-01) sources; they are in `/volume1/docker/v5test/results/son5-capture-20261020-151815/`.

Sanitize, then delete both dirs (D-13).

## Known Stubs
None.

## Self-Check: PASSED
Commits 62ad5de, 090654d, ea8c85c, a3c168d and f675967 exist. 120-teardown.sh and 120-CAPTURE-NOTES.md exist. The NAS files listed above were confirmed by the Task 3 verify (`stat` 600).
