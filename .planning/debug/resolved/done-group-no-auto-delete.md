---
status: resolved
trigger: "check out seedsyncarr done group -- any ideas why these didn't auto-delete when they were done?"
created: 2026-10-14
updated: 2026-10-23
closed: 2026-10-23 (Phase 122; owner confirmed cleanup)
---

# Debug Session: done-group-no-auto-delete

## Symptoms

- **Expected behavior:** A root that SeedSyncarr synced and that Sonarr/Radarr then imported should be recorded as imported and auto-deleted locally (webhook -> evidence gate -> 300 s timer -> delete).
- **Actual behavior:** Two roots sit in the Done group (state `downloaded`) on the NAS (seedsyncarr:1.7.4) and were never auto-deleted.
- **Error messages:** "Ignoring webhook import for '<root>': not downloaded by SeedSyncarr (no transfer evidence)"; for Days of Hope also "Auto-delete given up ... after 24 deferrals; last reason: not every on-disk video child has been imported yet".
- **Timeline:** Days of Hope 2026-10-09 21:11-23:20 EDT; Obsession 2026-10-13 20:17-21:19 EDT.
- **Reproduction:** Arr imports (webhook arrives) before SeedSyncarr has committed the root to `downloaded_file_names`.

## Evidence gathered by orchestrator (2026-10-14)

Logs: `ssh nas` -> `/volume1/docker/seedsync/log/seedsyncarr.log` (app-log time is EDT; NAS host clock/mtimes are -05, app = host + 1h). Persist JSON: `/volume1/docker/seedsync/controller.persist`. Radarr key in `/volume1/docker/radarr/config.xml`, API on localhost:7878. Container `seedsyncarr`, image 1.7.4 (StartedAt 2026-10-09T14:10:14Z, no restart during either incident).

### Case A: Days.of.Hope.1975.DVDRip.x264-HANDJOB (dir, 4 mkv parts, 8,007,628,364 B, Sonarr)
- 21:11:36 auto-queued. 21:14:06 / 21:14:14 / 21:14:16: Sonarr webhooks for Parts 3, 1, 2 -> all three "Ignoring webhook import ... no transfer evidence".
- 21:15:03 Part 4 webhook -> "Recorded webhook import" + auto-delete scheduled (root was in downloaded_file_names by then; MemoryMonitor downloaded_files 83 -> 84 between 21:10 and 21:15).
- Timer: "partial import (1 of 4 on-disk video children imported)" deferred 24 x 300 s, then gave up at 23:20.
- Model now: state downloaded, import_status imported, local_size == remote_size.

### Case B: Obsession.2025...CiNEPHiLES.mkv (single file, remote 55,477,377,022 B, Radarr) -- DATA INTEGRITY
- 20:17:31 auto-queued; ActiveScanner "Path does not exist" (normal at start).
- No log lines for this file until 20:47:48: auto-queued AGAIN (first lftp job ended without the root being committed as downloaded).
- 20:48:32 Radarr webhook -> "no transfer evidence" -> ignored.
- Radarr history: downloadFolderImported 2026-10-14T00:48:32Z, droppedPath `/data/torrents/Obsession...mkv`, size **54,676,946,944** (about 800 MB short of remote). Radarr moved it (link count 1).
- Pre-remediation state: library file `/volume1/data/media/movies/Obsession (2026) {tmdb-1339713}/...mkv` inode 8318763, 54,676,946,944 B (TRUNCATED, Radarr moviefile id 991). Source `/volume1/data/torrents/Obsession...mkv` inode 8318765, 55,477,377,022 B (complete, re-downloaded by second job; downloaded_files 85 -> 86 between 21:14 and 21:19).
- **NOTE (2026-10-14, post-evidence remediation by user):** The user manually re-imported Obsession in Radarr. Library file is now inode 8318765, 55,477,377,022 B (complete). The source in `/volume1/data/torrents/` is gone (Radarr moved it). The truncated 54,676,946,944 B file (inode 8318763) no longer exists. The pre-reimport evidence above stays valid. Current NAS state differing from it is the result of this remediation, not a contradiction. Do not use current library/torrents state to re-test Case B. Rely on logs, Radarr history and persist forensics. (The `stat` evidence below was captured before this remediation.)

## Current Focus

hypothesis: CONFIRMED for both cases (see Resolution)
test: n/a
expecting: n/a
next_action: return ROOT CAUSE FOUND to orchestrator (goal: find_root_cause_only); no code changes made

## Evidence

- timestamp: 2026-10-14 (code read)
  checked: `Controller.__check_webhook_imports` (src/python/controller/controller.py:602-637) and `WebhookManager.process` (src/python/controller/webhook_manager.py:87-131)
  found: `process()` drains the Queue with `get_nowait()` -- every event is consumed. In the controller, a root not yet in `downloaded_file_names` passes only if `root_file.local_size >= root_file.remote_size` (ROOT-level; for a dir that is the sum of children). On failure the code does `continue` (line 637). The event is neither re-enqueued nor stored; nothing re-evaluates it later.
  implication: a webhook that arrives while the ROOT is still downloading is permanently lost, even when the specific CHILD it names is complete on disk.

- timestamp: 2026-10-14 (code read)
  checked: `AutoDeleteManager.run_bfs_and_coverage` (src/python/controller/auto_delete_manager.py:197-217) and `ModelPipeline._commit_downloaded_membership` (src/python/controller/model_pipeline.py:283-329)
  found: coverage requires every on-disk video basename under the root to be present in `imported_children[root]`; that entry exists only when at least one child webhook was accepted. The commit pass's second rule (imported_file_names + remote copy) cannot help because dropped events never reach `imported_file_names`.
  implication: once one child webhook is accepted and the others were dropped, the pack is permanently "partial"; the deferral budget (24 x 300 s) just runs out. Sonarr never re-sends (it already imported those episodes).

- timestamp: 2026-10-14 (NAS log, seedsyncarr.log lines 16567-16657)
  checked: Days of Hope webhook sequence vs commit time
  found: Parts 3/1/2 webhooks at 21:14:06-21:14:16 rejected while mirror was still transferring Part 4 (root DOWNLOADING, dir local_size < remote_size). Part 4 webhook at 21:15:03 accepted (root committed in between). persist `imported_children` for the root = `['days.of.hope.part.4.1975.dvdrip.x264-handjob.mkv']` only. Coverage log says "1 of 4 on-disk video children imported" => Sonarr hardlinked/copied (all 4 parts still on disk), so coverage can never pass.
  implication: Case A root cause confirmed: pre-commit child webhooks dropped by the root-level evidence gate, never replayed.

- timestamp: 2026-10-14 (NAS: stat of source file taken BEFORE user remediation; Radarr radarr.txt; Radarr /api/v3/history/movie?movieId=362; /downloadclient; /remotepathmapping)
  checked: Obsession end-to-end timeline
  found: Radarr grabbed 20:15:15 EDT (Deluge on seedbox jules1651.nyx.usbx.me, remote /home/jules1651/downloads/deluge -> /data/torrents/). Source file mtime 19:22:45 -0500 = 20:22:45 EDT (lftp preserves remote mtime => the seedbox finished writing the torrent at 20:22:45, i.e. 5 min 14 s AFTER SeedSyncarr auto-queued it at 20:17:31). Radarr log (same clock as app log): from 20:22:46 every ~90 s "Import failed, path does not exist ... /data/torrents/Obsession...mkv" (file was still the `.lftp` temp) through 20:46:59; at 20:48:32 "Assigning file" (import). Source ctime 20:17:14 -0500 = 21:17:14 EDT = job 2's temp->final rename; downloaded_files 85->86 between 21:14 and 21:19 matches.
  implication: lftp job 1 ran 20:17:31 -> ~20:47 (54.68 GB at ~31 MB/s, same throughput as job 2's 55.48 GB in 29.5 min), renamed temp -> final name on normal completion, and Radarr's next completed-download poll imported that file 44 s later.

- timestamp: 2026-10-14 (arithmetic)
  checked: imported size 54,676,946,944 B
  found: = exactly 52,144 MiB = 3,259 x 16 MiB. Total remote 55,477,377,022 B = 3,306.7 x 16 MiB. The short size is an exact torrent piece boundary.
  implication: the size SeedSyncarr observed at queue time was the sparse-file st_size of an in-progress libtorrent download whose highest written piece was #3258 of ~3307 -- the last 48 pieces (~800 MB) were not yet written. pget sized the transfer from that snapshot and faithfully copied 54.68 GB. Same class as the v1.7.0 postmortem "truncated snapshot"; `remote_stability_seconds = 90` (settings.cfg) did not prevent it because a sparse file's size plateaus at the highest written piece and can stay unchanged for >= 90 s while lower pieces are still being filled.

- timestamp: 2026-10-14 (NAS log + code)
  checked: why re-queue only at 20:47:48 and why no job-end log line
  found: AutoQueue is a level-triggered sweep (src/python/controller/auto_queue.py:283-337): the file was not a candidate while job 1 ran (state DOWNLOADING); it became DEFAULT with local 54.68 GB < remote 55.48 GB when job 1 ended ~20:47, passed remote (90 s, stable since 20:22:45) + local (30 s) stability and the 300 s cooldown, so it re-queued within ~1 min. No "Lftp timeout", "status unavailable", "Lftp detected error", "stalled", "Caught lftp", shutdown or restart lines in the log for 2026-10-13 20:00-21:30. MemoryMonitor `lftp_statuses` is a data-size counter, not a job count. Job completion is not logged at INFO (only the commit, which for job 2 happened ~21:17).
  implication: v1.7.4 LFTP timeout / None-status handling, pget temp-rename, and job kill played NO role. Job 1 ended normally with a complete copy of a short remote snapshot. The orchestrator's open questions are closed.

- timestamp: 2026-10-14 (NAS log lines 17952-17954 + code + persist)
  checked: Radarr webhook at 20:48:32 for Obsession; persist membership
  found: root not in downloaded_file_names; local_size 54,676,946,944 < remote_size 55,477,377,022 => no evidence => dropped. Job 2 completed ~21:17 and the commit pass added the root to downloaded_file_names. Radarr never sends another Download webhook (already imported). persist: downloaded=True, imported=False.
  implication: the Done-group symptom for Case B is the correct, safe outcome of the evidence gate; the real defect is upstream (truncated snapshot queued, then imported by Radarr). Replaying the dropped webhook here would only have tagged a root whose library copy was truncated.

- timestamp: 2026-10-14 (code read)
  checked: availability of a stronger completion signal for a fix
  found: `ModelFile.remote_modified_timestamp` (src/python/model/file.py:278) and `SystemFile.timestamp_modified` (src/python/system/file.py:42) already exist; the remote scanner serialises `time_modified`. A torrent being written has an mtime that advances on every write even when st_size plateaus. The app also holds Radarr/Sonarr API keys (`/api/v3/queue` reports per-download status).
  implication: a remote mtime-stability requirement, and/or an arr queue-status check, is implementable without a scanner change.

## Eliminated

- hypothesis: lftp job 1 was killed / timed out / hit the v1.7.4 None-status path and left a short file at the final name
  evidence: no lftp warning/error/timeout/stall/restart lines in seedsyncarr.log for 2026-10-13 20:00-21:30; container StartedAt 2026-10-09 (no restart); job 1 duration (~30 min for 54.68 GB) matches job 2's throughput; the short size is an exact 16 MiB piece boundary (remote snapshot), not an arbitrary abort point; lftp only renames temp -> final on successful completion.
  timestamp: 2026-10-14

- hypothesis: lftp temp-file handling (use_temp_file) exposed a partial file at the final name during transfer
  evidence: use_temp_file = True in settings.cfg; Radarr's "path does not exist" errors from 20:22:46 to 20:46:59 prove the final name did NOT exist while job 1 was transferring. The file appeared at the final name only when job 1 finished.
  timestamp: 2026-10-14

- hypothesis: AutoQueue re-queued at 20:47:48 because of a stability-window bug
  evidence: re-queue is the designed level-triggered behaviour: DEFAULT + local < remote + remote stable 90 s + local stable 30 s + cooldown 300 s elapsed. Timing matches job 1 ending ~20:47.
  timestamp: 2026-10-14

## Specialist Review

reviewer: python (python-expert-best-practices-code-review direction), 2026-10-14
verdict: SUGGEST_CHANGE

Case A -- prefer option (a) per-child evidence, constrained:
- A child counts as evidence only if its remote copy exists (remote_size not None) and local_size >= remote_size. This keeps the 2026-08-21 foreign-directory guard.
- Child evidence may only call add_imported_child. It must NOT commit the root to downloaded_file_names or schedule auto-delete. Split the commit+schedule step at controller.py ~620-650. Arm the timer when the root commits, and have the auto-delete path refuse roots still DOWNLOADING/QUEUED.
- An in-flight child reports its lftp-status/temp size, so it fails the size check. A child whose remote copy is still growing can still pass (the Case B issue again).
- Option (b), an in-memory pending map, is weaker. A restart loses it, leaving infinite deferral. It also needs a cap, TTL, dedupe and a commit hook. Use it only as a short fallback alongside (a).

Case B -- remote mtime is necessary but not sufficient:
- Per-file st_mtime updates on every libtorrent write and is better than size. With full preallocation, size never changes.
- For directories, scanner.py:124 uses the directory's own st_mtime, which does not change on child writes. The gate needs the max mtime across all descendants.
- A stalled swarm (no peers > 90 s) defeats both size and mtime windows.
- The arr /api/v3/queue check is the stronger signal. If the arr is unreachable, refuse to queue (log it, time-cap it). Content the arr didn't grab falls back to the mtime gate. Match on outputPath/downloadId rather than title. Treat downloading/queued/paused as not ready. Call from the AutoQueue thread with a timeout and cache per scan cycle.
- Add a commit-time check: if remote size or mtime changed during the transfer, re-queue instead of committing.

## Resolution

root_cause: |
  Two distinct defects, one per case.

  CASE A (Days of Hope -- dropped pre-commit webhooks): `Controller.__check_webhook_imports`
  (src/python/controller/controller.py:619-637) evaluates download evidence at the ROOT
  level (root in downloaded_file_names, or root.local_size >= root.remote_size) and, on
  failure, `continue`s -- the event has already been dequeued by `WebhookManager.process`
  and is discarded forever. With `mirror` and parallel files, individual episodes reach
  their final names (and Sonarr imports them) while the directory root is still
  DOWNLOADING, so the first N-1 child webhooks are dropped and only the last is recorded.
  The coverage guard (auto_delete_manager.py:197-217) then sees imported_children = {part4}
  vs 4 on-disk videos and defers until the 24-attempt budget is exhausted. No retry path
  exists: Sonarr will not re-send, and the commit pass cannot see the dropped events.

  CASE B (Obsession -- truncated import, data integrity): AutoQueue's remote-size
  stability gate (auto_queue.py sweep_accept, remote_stability_seconds=90) accepted an
  in-progress seedbox torrent. libtorrent writes a sparse file whose st_size equals the
  highest written piece boundary; it plateaued at 3,259 x 16 MiB = 54,676,946,944 B for
  >= 90 s while the last 48 pieces were still downloading (seedbox finished 20:22:45,
  5 min after SeedSyncarr queued at 20:17:31). lftp pget sized the transfer from that
  snapshot, completed normally (~30 min), renamed temp -> final, and Radarr -- polling
  for that exact path since Deluge reported completion at 20:22 -- imported the 54.68 GB
  file 44 s later. SeedSyncarr then correctly saw local < remote, re-queued, downloaded
  the full file and committed it; Radarr's webhook had already been (correctly) refused
  by the evidence gate and never recurs. Size stability is an insufficient completion
  signal; the lftp/timeout/temp-file machinery behaved correctly.
fix: |
  CASE A: Phase 119 Plan 05 (IMP-03, "Early Per-Episode Import Credit"). Split per-child
  evidence from the root-level commit: a webhook naming a child whose own remote copy
  exists and is fully on disk is credited via `__credit_early_child` (writes
  `imported_children[root]` only) even while the root is still transferring, instead of
  being `continue`d and lost. A credit alone never commits the root or arms a delete; the
  root still only arms once it is independently committed. A credited-but-unresolved
  notice is kept (not dropped) and revalidated on later cycles until the root's own
  bookkeeping catches up (122-10 closed the one remaining race in this revalidation
  window; see extract-staging-autodel-rearm.md's sibling incident for the unrelated
  extraction-side bug). Restart recovery re-applies a persisted credit on the first
  post-restart commit.
  CASE B: Phase 119 Plans 04, 06, 07, 08, 12 (IMP-01/IMP-02, "Incomplete-import
  prevention"). AutoQueue and the webhook path now require evidence from the
  configured arr's own queue (`ArrQueueClient` + `CompletionGate`) that the matching
  download is actually complete, not just that local size/mtime look stable; a download
  the arr reports as still in progress (or an arr that is unreachable) produces a visible
  "Waiting" hold instead of a release. A held file can be manually released exactly once
  via a confirmed UI action (`release_unverified=true`), which bypasses the evidence
  check for that single transfer only and does not persist across a restart.
verification: |
  Both cases are exercised, not rebuilt, by the live SAFE-01 acceptance run in Phase 122
  on the build that will ship as 1.8.0 (sandbox `seedsyncarr-test`; production untouched).
  See "## Reconciliation (Phase 122)" below for the finding-by-finding evidence links and
  the live, read-only production facts gathered for this reconciliation (Sonarr/Radarr
  library state, NAS filesystem state, production log excerpts). Original Phase 119 unit
  verification (full suite + whole-tree ruff, both green) is recorded in
  `119-05-SUMMARY.md` (Case A) and `119-04-SUMMARY.md`/`119-06-SUMMARY.md`/
  `119-07-SUMMARY.md`/`119-08-SUMMARY.md`/`119-12-SUMMARY.md` (Case B).
files_changed:
  - src/python/controller/controller.py
  - src/python/controller/model_pipeline.py
  - src/python/controller/auto_delete_manager.py
  - src/python/controller/arr_queue.py
  - src/python/controller/completion_gate.py
  - src/python/controller/auto_queue.py
  - src/python/controller/command_processor.py
  - src/python/controller/scan/active_scanner.py
  - src/python/controller/scan/local_scanner.py
  - src/python/controller/scan_manager.py
  - src/python/model/file.py
  - src/python/model/model_builder.py
  - src/python/model/serialize.py
  - src/python/web/handler/controller.py
  - src/angular/src/app/model/model-file.ts
  - src/angular/src/app/model/view-file.ts
  - src/angular/src/app/model/view-file.service.ts
  - src/angular/src/app/components/transfer-row/transfer-row.component.ts
  - src/angular/src/app/components/transfer-row/transfer-row.component.html
  - src/angular/src/app/common/localization.ts
  - src/angular/src/app/services/bulk-action-dispatcher.service.ts
  - src/angular/src/app/services/bulk-command.service.ts
  - src/angular/src/app/pages/settings/options-list.ts
  - src/e2e/seed-state.ts
  - docs/CONFIGURATION.md
  - src/python/docs/configuration.md

## Reconciliation (Phase 122)

Production (`seedsyncarr`, still running 1.7.6; the fix below ships in 1.8.0 and has not
reached production yet) was inspected read-only on 2026-10-23 (NAS host UTC
`2026-10-23T19:37:42Z` / NAS local `2026-10-23 14:37:42 -05`, unless noted): `ls -ld`/
`du -sb` on the exact Days of Hope and Obsession paths under `/volume1/data/torrents/`,
`grep` of `/volume1/docker/seedsync/log/seedsyncarr.log` for each root name, and read-only
GET calls to the production Sonarr (`:8989`) and Radarr (`:7878`) APIs with their keys
read into shell variables and never printed. No write command was issued.

| Finding | Fix (plan + commits) | Evidence | Status |
|---|---|---|---|
| Case A — Days of Hope (pre-commit child webhooks dropped) | Phase 119 Plan 05 (IMP-03): RED `7a73d8b`, GREEN `9309bab`, `2e53cbb` | `122-SAFE01-EVIDENCE.md` → "Plan 12: D-06 rerun on the fixed build" → D-06(a) (early credit), D-06(b) (arm on commit), D-06(c) (deferral/revalidation — supersedes the original Plan 05 FAIL, closed by 122-10); "Plan 06: D-06(d) Restart persistence on the fixed build" (credit survives a restart) | **verified fixed (evidence)** — all four cited scenarios PASS on the build shipping as 1.8.0 |
| Case B — Obsession (truncated import from a still-growing seedbox file) | Phase 119 Plans 04 (`8194567`, `d7e2354`, `c1f192d`, `d29a147`), 06 (`7bf68b2`, `733b5cf`, `e5f22a5`), 07 (`907ada9`, `8f126a4`, `e28a0a0`, `a17e680`), 08 (`41cc7aa`, `8719d05`, `4736763`, `b7bb74b`), 12 (`3000994`, `931d742`) | `122-SAFE01-EVIDENCE.md` → "Plan 12: D-06 rerun on the fixed build" → D-06(e) (Waiting hold + one-shot release); `120-SON5-EVIDENCE.md` §SON5-02 (real Sonarr-queue hold/release, 11/11 pass) per D-04; `119-HUMAN-UAT.md` tests 1–2 (Waiting badge, manual-release confirm modal, pass 2026-10-18 on 1.7.6) | **verified fixed (evidence)** |

### Remaining operator cleanup

- **Days of Hope local copy** (`/volume1/data/torrents/Days.of.Hope.1975.DVDRip.x264-HANDJOB`): **verified absent** — `ls -ld`/`du -sb` on the exact path returned "No such file or directory" at `2026-10-23T19:37:42Z`. The production log shows you issued the delete yourself: `Action.DELETE_LOCAL for file Days.of.Hope.1975.DVDRip.x264-HANDJOB` at `2026-10-16 22:03:32`. Nothing to do — please just confirm.
- **Days of Hope Sonarr library completeness**: **verified complete** — Sonarr (series id 815) reports all 4 episodes with files (ids 29470–29473), total `8,007,628,364` bytes, exactly matching the original torrent's full size; added `2026-10-10T01:14–01:15Z`. Nothing to do — please just confirm.
- **Obsession local copy** (`/volume1/data/torrents/Obsession.2025....mkv`): **verified absent** — same `ls`/`du` check, same timestamp, "No such file or directory". Radarr moved (not hardlinked) this file on import, so its disappearance from the torrents folder is expected once the real import completed. Nothing to do — please just confirm.
- **Obsession Radarr library file**: **verified present, full-size** — Radarr movieFile id 993, `55,389,018,125` bytes, added `2026-10-14T19:56:10Z` (matches your 2026-10-14 manual re-import, per `PROJECT.md`). This is no longer the truncated `54,676,946,944`-byte copy. One thing worth knowing: this size is about 88 MB (0.16%) smaller than the `55,477,377,022` bytes originally recorded for the complete remote file in this debug session — consistent with a fresh grab of the same release (same `CiNEPHiLES` group) rather than a leftover truncation, but it is not a byte-for-byte match either. If you want certainty beyond the size check, playing the file through once would confirm it; otherwise this is likely fine as-is.

All four production facts above were gathered read-only this session and are not an
assumption carried over from the original 2026-10-14 diagnosis. Per the phase's close rule
(D-12), this record can only move to `.planning/debug/resolved/` once you confirm every
item above.

**Owner confirmation (2026-10-23, Phase 122 Plan 09 Task 2):** verbatim reply "All
confirmed" — Days of Hope and Obsession cleanup both confirmed done, including the
Obsession Radarr library file despite its ~88 MB / 0.16% size difference from the
originally-recorded complete remote size (flagged, not treated as an exact match). Both
non-deferred findings (Case A, Case B) are "verified fixed (evidence)" and every cleanup
item is now owner-confirmed, so per D-12 this record is **resolved** and moved to
`.planning/debug/resolved/`.
