---
status: awaiting_human_verify
trigger: "Two production bugs found 2026-09-16 on The.Burbs.1989.2160p.UHD.BluRay.x265-B0MBARDiERS: (1) in-place extraction output visible to Radarr mid-unrar, imported a 6 GB partial of a 38.5 GB mkv; (2) auto-delete skipped while root EXTRACTING and never re-armed, local copy sits forever"
created: 2026-09-16
updated: 2026-09-16
---

# Debug Session: extract-staging-autodel-rearm

## Symptoms

- **Expected behavior:** (Bug 1) Extracted files must not be visible inside the release folder until unrar has fully finished, so Sonarr/Radarr completed-download handling never imports a partial file. (Bug 2) An auto-delete that is skipped for a retriable reason (root state EXTRACTING, unsafe_child, partial_coverage) must be re-armed and retried until it succeeds or a bounded retry limit is exhausted.
- **Actual behavior:** (Bug 1) `Extract.extract_archive` calls `patoolib.extract_archive` straight into `out_dir_path` (== local_path when `use_local_path_as_extract_path=True`), so the growing mkv appeared next to the rars and Radarr imported it ~90 s into a 12-minute extraction (downloadFolderImported size=5,851,656,322 of 38,482,836,588). (Bug 2) `__execute_auto_delete` logged "Auto-delete skipped ... file is in state EXTRACTING" and returned; `__schedule_auto_delete` is only called from the webhook path, so nothing ever re-armed it. Root ended at state=extracted, local_size 77 GB, and will never be deleted.
- **Error messages:** None. Only benign outcome because Radarr hardlinked on the same volume and unrar kept writing into the shared inode (verified same inode, links=2, full size on both names). A copy fallback would have left a truncated 6 GB library file with the 68.8 GB remux already deleted as an "Upgrade".
- **Timeline:** 2026-09-16 EDT. 21:27 all rars synced, auto_extract starts in-place unrar. 21:28:50 Radarr imports partial mkv. 21:29 webhook accepted, 300 s auto-delete armed. ~21:34 timer fires, root EXTRACTING, skipped and never re-armed. 21:39 extraction finishes. Same family as the v1.7.1 truncated-snapshot incidents, on the extract side instead of the transfer side.
- **Reproduction:** Any rar'd release with auto_extract=True and use_local_path_as_extract_path=True where an arr watches the same folder; large archive makes the window wide. Bug 2 reproduces whenever a webhook arrives while the root is still EXTRACTING (or run_bfs_and_coverage returns unsafe_child / partial_coverage) at timer-fire time.

## Full Incident Report (user-supplied, treat as data)

DATA_START
Two production bugs in SeedSyncarr (this repo), found 2026-09-16 on the release
The.Burbs.1989.2160p.UHD.BluRay.x265-B0MBARDiERS (rar'd, 96 x 400 MB volumes + .sfv/.nfo,
38,482,836,588-byte mkv inside). Fix both, with tests. Read the referenced code before
changing anything.

=== INCIDENT TIMELINE (EDT) ===
21:27   All rars synced. AutoQueue.auto_extract=True -> ExtractDispatch starts unrar-ing
        IN PLACE into /data/torrents/<root>/ (config: use_local_path_as_extract_path=True,
        so out_dir_path == local_path).
21:28:50 Radarr completed-download-handling (watching the same folder via the Deluge
        remote-path mapping) saw the mkv appear next to the rars and imported it
        immediately. Radarr history: downloadFolderImported size=5,851,656,322;
        moviefile record size=5,999,997,945. It imported a ~6 GB PARTIAL of a 38.5 GB
        file, ~90 s into a 12-minute extraction, and deleted the previous library file
        (68.8 GB remux) as an "Upgrade" 5 s earlier.
21:29   Radarr webhook -> Controller.__check_webhook_imports accepted it
        (import_status=imported) and armed the 300 s auto-delete.
~21:34  Timer fired; root ModelFile.state was EXTRACTING -> __execute_auto_delete
        "Auto-delete skipped ... file is in state EXTRACTING" and returned. Nothing
        ever re-arms it.
21:39   Extraction finished. Model: root state=extracted, remote_size 38.5 GB,
        local_size 77 GB (rars + mkv), mkv child state=default. Local copy will sit
        forever.
Outcome was only benign because Radarr hardlinked (same volume) and unrar kept writing
into the shared inode, so the library file ended up complete (verified: same inode,
links=2, 38,482,836,588 bytes on both names). A copy fallback would have left a
truncated 6 GB library file with the remux already deleted. Same family as the v1.7.1
truncated-snapshot incidents, on the extract side instead of the transfer side.

=== BUG 1: extraction output is visible to Sonarr/Radarr while in progress ===
Where: src/python/controller/extract/dispatch.py (ExtractDispatch.extract builds
(archive_path, out_dir_path) pairs; __worker calls Extract.extract_archive per pair) and
src/python/controller/extract/extract.py (Extract.extract_archive -> patoolib.extract_archive
straight into out_dir_path).

Fix: extract into a staging directory on the SAME filesystem as the final out_dir, then
move the results into place with os.rename (atomic on one filesystem) only after patool
returns successfully for that archive.
- Staging location: <extract_root>/.seedsyncarr-extracting/<root_name>/<relative dir>/
  where extract_root is the configured extract path (== local_path when
  use_local_path_as_extract_path is true). Put it at the extract ROOT level, not inside
  the release folder: the arrs' completed-download handling only scans the torrent's own
  folder (from the download client), so a sibling dot-dir at the root is invisible to
  them. Do NOT use /tmp or any other filesystem (rename would become a copy).
- After a successful extract_archive: walk the staging dir, os.makedirs the target dirs,
  os.rename each file to its final path (if a target already exists, log a warning and
  os.replace it — the newly extracted copy is authoritative), then remove the emptied
  staging tree. On ExtractError, leave nothing behind in the final out_dir: remove the
  staging tree for that archive and log what was cleaned up.
- The local SystemScanner must not model the staging dir: add
  scanner.add_exclude_prefix(".seedsyncarr-extracting") (see system/scanner.py
  exclude_prefixes; find where the local scanner is constructed and wire it there) so
  the UI never shows it as a root entry (the model currently does show .DS_Store and
  @eaDir, so the exclusion is required, not optional).
- Keep ExtractStatus/ExtractCompletedResult semantics unchanged: extract_completed still
  fires once per task, after ALL of that task's archives have been extracted AND moved.
  The controller's ModelFile.State.EXTRACTING must stay true until the moves are done.
- Startup hygiene: if <extract_root>/.seedsyncarr-extracting/ exists at ExtractDispatch
  start (crash mid-extract), delete it and log at WARNING — its contents are partial by
  definition and the archives are still there to re-extract.
Tests (src/python/tests/unittests, follow the existing extract tests' style): a
multi-file archive is never visible in out_dir until patool finishes (assert the final
path does not exist while a patched patoolib.extract_archive is mid-call, and does exist
with full size afterwards); a PatoolError leaves out_dir untouched and no staging
residue; existing-target is replaced; startup cleanup of a stale staging dir;
scanner exclusion of the staging prefix.

=== BUG 2: a skipped auto-delete never re-arms ===
Where: src/python/controller/controller.py, __execute_auto_delete. It returns without
re-scheduling when the root state is not in deletable_states (DEFAULT/DOWNLOADED/EXTRACTED)
and when AutoDeleteManager.run_bfs_and_coverage returns skip with reason "unsafe_child"
or "partial_coverage". Comments call these "retriable ... the next Timer-fire retries",
but __schedule_auto_delete is only ever called from the webhook path
(controller.py ~line 630), so there is no next fire. Confirm with grep.

Fix: make the retriable skips actually retry.
- In __execute_auto_delete, for the state-guard skip and for skip reasons
  "unsafe_child" and "partial_coverage", call self.__schedule_auto_delete(file_name)
  again (same autodelete.delay_seconds) instead of silently returning. Do NOT re-arm on:
  "bfs_limit" (terminal by design), feature disabled, dry-run, file gone from model,
  evidence-gate refusal (not in downloaded_file_names), or shutdown.
- Bound it: add a per-root retry counter in __pending_auto_deletes' bookkeeping (or a
  sibling dict under __auto_delete_lock); give up after N re-arms (make N a constant,
  e.g. 24 = ~2 h at 300 s) with one WARNING log naming the root and the last skip reason,
  and clear the counter on success, on terminal skip, and when a new webhook re-arms the
  root. The log line on each re-arm should say why and which attempt it is, e.g.
  "Auto-delete deferred for '<root>' (attempt 3/24): file is in state EXTRACTING;
  retrying in 300 s".
- exit()/shutdown must still cancel everything in __pending_auto_deletes, including
  re-armed timers (check the existing BUG-03 shutdown criteria and keep them green).
- Lock order stays __model_lock THEN __auto_delete_lock; do the re-arm outside
  __model_lock (schedule after releasing it, same pattern as the webhook path).
Tests: replay the incident — webhook accepted while root is EXTRACTING, timer fires and
defers, extraction completes (root -> EXTRACTED), next fire deletes; unsafe_child and
partial_coverage defer then succeed; bfs_limit does not re-arm; N exhausted stops with a
warning; shutdown cancels a re-armed timer; existing auto-delete tests unchanged.

=== ALSO ===
- Add a CHANGELOG.md entry under a new [1.7.3] - Unreleased section describing both
  fixes in the same style as 1.7.1/1.7.2 (incident, what escaped the existing gates,
  what changed). Do not tag or bump package versions.
- Update docs/CONFIGURATION.md and docs/ARCHITECTURE.md where they describe extraction
  or auto-delete behaviour.
- CI gates: the Python suite green AND `ruff check src/python/` clean — ruff is a
  separate gate from pytest. Run both before you report done.
- Report back with: the files changed, the two new log lines verbatim, and anything you
  found in the code that contradicts the timeline above.
DATA_END

## Key Files

- src/python/controller/extract/dispatch.py (ExtractDispatch.extract, __worker)
- src/python/controller/extract/extract.py (Extract.extract_archive)
- src/python/system/scanner.py (exclude_prefixes)
- src/python/controller/controller.py (__execute_auto_delete, __schedule_auto_delete, __check_webhook_imports, exit)
- src/python/tests/unittests (extract tests, auto-delete tests)
- CHANGELOG.md, docs/CONFIGURATION.md, docs/ARCHITECTURE.md

## Current Focus

status_note: Both root causes CONFIRMED, both fixes applied and self-verified (unit suite + ruff). Awaiting human verification on the NAS bake; nothing committed, tagged, or bumped.

reasoning_checkpoint:
  hypothesis: "(1) patool unpacks straight into the release folder because ExtractDispatch hands Extract.extract_archive the final out_dir, so any *arr scanning that folder can import a half-written file. (2) A skipped auto-delete is never retried because __execute_auto_delete returns on every skip and the only __schedule_auto_delete caller is the webhook path."
  confirming_evidence:
    - "extract.py:57 patoolib.extract_archive(archive_path, outdir=out_dir_path) with out_dir_path = join(extract_root, dirname(child.full_path)); no temp/staging path exists anywhere in src/python/controller/extract"
    - "grep: __schedule_auto_delete has exactly one caller, controller.py:630 in __check_webhook_imports; every skip branch of __execute_auto_delete (718 state guard, 736-747 bfs skips) is a bare return"
  falsification_test: "If a second __schedule_auto_delete caller existed (e.g. from model-diff or extract-completed handling) or if Extract already wrote to a temp dir and renamed, the diagnosis would be wrong. Neither is present."
  fix_rationale: "(1) Extract into <extract_root>/.seedsyncarr-extracting/<root>/<rel dir>/ (same filesystem) and publish with os.rename/os.replace after patool returns, so the release folder only ever contains complete files; exclude the dot-dir from the local scan; remove stale staging at start. (2) On retriable skips re-arm the timer from outside __model_lock with a per-root counter capped at 24, clearing the counter on success/terminal skip/fresh webhook arm and refusing to arm after shutdown."
  blind_spots: "Cannot run the CI Docker suite locally (daemon down); relying on the poetry venv and a recorded baseline of 24 macOS-environment failures. Cannot exercise a real 38 GB unrar; staging behaviour is verified with a patched extract_archive writing real files into real temp dirs."

design_decisions:
  - Extract.extract_archive signature unchanged; ExtractDispatch passes the staging dir as out_dir_path and owns publish/discard/startup cleanup (it alone knows the extract root). Real-archive integration tests stay valid.
  - Existing test_dispatch.py golden out_dir_path values must change to the staging path (contract extended, not weakened); new staging tests use real temp dirs with a patched extract_archive.
  - Staging dir name centralised in common.Constants (precedent: LFTP_TEMP_FILE_SUFFIX shared by scanners).
  - Re-arm bookkeeping: sibling dict __auto_delete_rearms under __auto_delete_lock; module constant _AUTO_DELETE_MAX_REARMS = 24 (mirrors _AUTO_DELETE_BFS_NODE_LIMIT naming).

continuation_2026-09-16_deep_review_AB: DONE. User replied "do A B C"; orchestrator scoped this continuation to A and B only. A applied (dispatch.py 270-273 call site, 301-320 __warn_unpublished_output, 328 discard now uses the shared helper, 340-347 __list_staged_output; test test_dispatch_staging.py:278-334). B applied for the branch that actually exists at dispatch.py:289-292 -- extracted FILE over an existing DIRECTORY (test :242-276). Item B's wording was inverted; the literal reverse case (extracted DIRECTORY over an existing plain FILE) is unhandled today (os.replace -> ENOTDIR -> ExtractError) and is recorded as deferred item H, not fixed (out of scope). C-G deferred. Gates: targeted 47 passed; full suite 21 failed / 1383 passed / 3 errors, failure set identical to the 24-entry baseline; ruff clean. Nothing committed, tagged, or bumped.
continuation_2026-09-16_orchestrator_HC: DONE. Orchestrator applied H and C after the agent returned. H: __move_tree now os.remove()s an existing plain file or symlink when the extracted entry is a directory (dispatch.py, lexists branch, new elif before os.replace); test test_extracted_directory_replaces_existing_file_of_same_name verified RED without the branch (task failed, ENOTDIR) and GREEN with it. C: new __strip_symlinks(staging_dir_path) runs in __publish_staged_output before __move_tree; os.walk removes every symlink (top-level, nested, dangling, dir-target) with WARNING "Skipping symlink '<path>' -> '<target>' in extracted output; symlinks are never published into the release folder"; test test_symlinks_in_extracted_output_are_dropped_before_publish. CHANGELOG [1.7.3] and docs/ARCHITECTURE.md + docs/CONFIGURATION.md amended for both. D-G remain deferred. Gates re-run after C: see orchestrator report. Nothing committed, tagged, or bumped.

hypothesis: (confirmed — see reasoning_checkpoint)
test: DONE — `python -m pytest tests/unittests -p no:cacheprovider -q` from src/python via the poetry venv, failures diffed against scratchpad baseline; `ruff check src/python/` with ruff 0.15.22
expecting: no failure outside the 24-entry macOS baseline; new tests green; ruff clean — ALL MET
next_action: Human verification on the NAS bake: deploy the working tree build, sync a rar'd release with auto_extract on and an arr watching the folder; confirm (a) during unrar the release folder shows only the rars while `<local_path>/.seedsyncarr-extracting/<release>/` grows, the UI never lists the dot-dir, and the mkv appears in the release folder at full size only at the end; (b) send/trigger the arr import while the root is still EXTRACTING and watch the log for `Auto-delete deferred for '<root>' (attempt 1/24): file is in state State.EXTRACTING; retrying in 300 s` followed by `Auto-deleted local file '<root>'` after extraction completes. On "confirmed fixed": archive_session (move to resolved/, commit code + docs, append knowledge base).

## Evidence

- timestamp: 2026-09-16 21:28:50 EDT (Radarr history)
  content: "downloadFolderImported size=5,851,656,322; moviefile record size=5,999,997,945 — imported a partial of a 38,482,836,588-byte mkv ~90 s into a 12-minute extraction"
- timestamp: 2026-09-16 ~21:34 EDT (SeedSyncarr log)
  content: "Auto-delete skipped ... file is in state EXTRACTING — timer fired once, never re-armed"
- timestamp: 2026-09-16 post-incident (filesystem)
  content: "Library file and torrent mkv share one inode, links=2, both 38,482,836,588 bytes — hardlink saved the outcome; a copy fallback would have truncated"
- timestamp: 2026-09-16 (code read, Bug 1)
  checked: src/python/controller/extract/extract.py Extract.extract_archive; src/python/controller/extract/dispatch.py ExtractDispatch.extract/__worker; src/python/controller/file_operation_manager.py:58-65
  found: extract_archive does `if not exists(out_dir_path): makedirs; patoolib.extract_archive(archive_path, outdir=out_dir_path, interactive=False)` — no staging step anywhere. Dispatch builds out_dir_path = join(extract_root, dirname(child.full_path)) so with use_local_path_as_extract_path=True the archive unpacks in place inside the release folder. ExtractStatus.EXTRACTING is derived from tasks still in the dispatch queue; the task is popped in the worker's `finally` right after the last extract_archive returns, so EXTRACTING covers the whole unrar. Consistent with the timeline.
  implication: Root cause 1 confirmed exactly as reported. Fix belongs in the dispatch (it alone knows the extract root) with Extract left as the thin patool wrapper.
- timestamp: 2026-09-16 (code read, Bug 2)
  checked: grep for __schedule_auto_delete across src/python (non-test); controller.py __execute_auto_delete 649-772; auto_delete_manager.py run_bfs_and_coverage
  found: Exactly ONE call site of __schedule_auto_delete — controller.py:630 inside __check_webhook_imports. __execute_auto_delete pops itself from __pending_auto_deletes on entry, then returns (no re-arm) on: disabled, dry-run, ModelError, evidence gate, state guard (line 718, "Auto-delete skipped for '{}': file is in state {}"), and every BFS skip (bfs_limit pops imported_children; unsafe_child/partial_coverage leave it intact). Comments in auto_delete_manager.py:23 ("the next Timer-fire retries") and :88-91 ("retriable") describe a retry that no code performs.
  implication: Root cause 2 confirmed exactly as reported. Nothing contradicts the timeline. Minor extra finding: auto_delete_manager.py:23 module comment says the bfs_limit skip is retried on "the next Timer-fire", contradicting its own docstring at :87 (terminal). Will correct the comment.
- timestamp: 2026-09-16 (code read, wiring)
  checked: controller/scan/local_scanner.py, controller/scan/active_scanner.py, common/constants.py, extract_process.py run_init
  found: LocalScanner and ActiveScanner each build their own SystemScanner; neither adds an exclude prefix today (only scan_fs.py CLI uses add_exclude_prefix). Constants already centralises LFTP_TEMP_FILE_SUFFIX used by both scanners — precedent for a shared EXTRACT_STAGING_DIR_NAME constant. ExtractDispatch is constructed in ExtractProcess.run_init (child process); ExtractProcess never calls dispatch.set_base_logger, so the dispatch logs via logging.getLogger("ExtractDispatch").
  implication: Wire the exclusion in LocalScanner.__init__ via a Constants entry; verify the child-process root logger forwards so the startup-cleanup WARNING is visible.
- timestamp: 2026-09-16 (docs read)
  checked: docs/CONFIGURATION.md [AutoDelete] table
  found: Describes auto-delete as "delete files from the remote server after a successful download" and delay as "before deleting the remote file". The code only ever calls delete_local after an arr import webhook (test_auto_delete pins "NEVER calls delete_remote").
  implication: Docs are wrong about what auto-delete does; correct while updating the section for the re-arm behaviour.
- timestamp: 2026-09-16 (baseline test run, before any change)
  checked: poetry venv seedsyncarr-5QbP0KwB-py3.12, `python -m pytest tests/unittests -p no:cacheprovider -q -x` from src/python
  found: 1 failed, 578 passed, stopped at first failure: tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_calls_start_dispatch
  implication: Pre-existing failure unrelated to this change (multiprocessing-based test); must characterise as flaky vs deterministic and report actual counts honestly.
- timestamp: 2026-09-16 (baseline, full run without -x)
  checked: same venv, `pytest tests/unittests -p no:cacheprovider -q --timeout=60`
  found: 21 failed, 1355 passed, 3 errors. All 24 entries are macOS-environment-bound: test_extract_process.py (6, multiprocessing spawn), test_scanner_process.py (3 failed + 3 errors, multiprocessing spawn), test_sshcp.py (11, need an SSH host), test_scanner.py::test_scan_file_with_latin_chars (APFS). List saved to scratchpad/baseline_failures.txt. Docker daemon is down so the CI container run (`make run-tests-python`) is unavailable locally.
  implication: Comparison set for the post-change run; CI (Linux container) is expected to pass these.
- timestamp: 2026-09-16 (child-process logging)
  checked: common/multiprocessing_logger.py get_process_safe_logger
  found: It attaches a QueueHandler to the ROOT logger of the child process, so ExtractDispatch's `logging.getLogger("ExtractDispatch")` propagates to the main log.
  implication: The new startup-cleanup WARNING and discard/replace WARNINGs will be visible in production logs without rewiring set_base_logger.
- timestamp: 2026-09-16 (post-fix targeted suites)
  checked: test_dispatch.py, test_dispatch_staging.py (new), test_auto_delete_rearm.py (new), test_auto_delete.py, test_controller.py, test_local_scanner.py
  found: 186 passed. One regression caught and fixed on the way: test_controller.py::TestAutoDeleteLogSanitization builds a Controller via `Controller.__new__` and hand-sets private attrs, so the new `__auto_delete_rearms` dict had to be added to that fixture (3 tests). The real-zip round trip through patool passes (py fallback / unzip).
  implication: Fix verified against the original symptoms at unit level: release folder unchanged mid-extract, full-size file present when extract_completed fires, no staging residue after failure, incident timeline replay defers then deletes.
- timestamp: 2026-09-16 (post-fix full suite)
  checked: full `tests/unittests` run, failures diffed against baseline_failures.txt
  found: 21 failed, 1381 passed, 3 errors. Failure set identical to baseline (24/24 same entries, none new, none removed). +26 passing = the 26 new tests.
  implication: No regression anywhere in the unit suite on this machine.
- timestamp: 2026-09-16 (lint gate)
  checked: `ruff check src/python/` with ruff 0.15.22 installed into the poetry venv (CI pins 0.15.22)
  found: All checks passed!
  implication: Lint gate green.
- timestamp: 2026-09-16 (log wording)
  checked: `str(ModelFile.State.EXTRACTING)`
  found: Renders as `State.EXTRACTING`, so the real deferral line reads `file is in state State.EXTRACTING` (the incident report's "file is in state EXTRACTING" was an abbreviation of the same pre-existing format).
  implication: Tests format the enum the same way production does; no behaviour change.
- timestamp: 2026-09-16 (continuation: deep-review items A + B)
  checked: dispatch.py __publish_staged_output / __move_tree / __discard_staged_output; os.replace semantics probed in the poetry venv (dir-over-file -> OSError 20 ENOTDIR, file-over-dir -> OSError 21 EISDIR); scratchpad probe running the real ExtractDispatch with an extracted directory over an existing file; CHANGELOG [1.7.3] and docs for publish-failure wording
  found: No listing helper existed (the listing was inline in __discard_staged_output), so one shared staticmethod __list_staged_output was factored out. The rmtree(dst) branch at :289-292 is file-over-directory, not directory-over-file as item B was worded; the reverse case is unhandled and fails the task (recorded as item H). CHANGELOG/docs describe only the ExtractError path ("a failed extraction leaves the release folder untouched"), not the mid-publish failure, so they were left alone per instructions. Gates: targeted 47 passed; full suite 21 failed / 1383 passed / 2 warnings / 3 errors in 75.30s with the failure set diffed identical to the 24-entry baseline; ruff 0.15.22 All checks passed.
  implication: A closes the brief's "log what was cleaned up" requirement on the publish-failure path; B covers the highest-consequence uncovered line (rmtree of a release-dir path). Item H is a small, real gap for a follow-up; A's new WARNING already makes it visible in the log if it ever happens.

## Eliminated

(none yet)

## Resolution

root_cause: |
  (1) ExtractDispatch handed Extract.extract_archive the FINAL directory (join(extract_root, dirname(child.full_path)) == the release folder when use_local_path_as_extract_path=True), and Extract called patoolib.extract_archive straight into it. There was no staging step, so the growing output file was visible to Radarr/Sonarr completed-download handling (which scans the release folder) for the whole extraction.
  (2) Controller.__execute_auto_delete returned without re-scheduling on every skip, and __schedule_auto_delete had exactly one caller (the webhook path, controller.py:630). The "retriable" skips (root state not deletable, unsafe_child, partial_coverage) were therefore one-shot: a timer that fired while the root was EXTRACTING was never retried.
fix: |
  (1) src/python/controller/extract/dispatch.py: each archive is extracted into <extract_root>/.seedsyncarr-extracting/<root>/<relative dir>/ (same filesystem; per-file staging path stored in the task triple), then __publish_staged_output moves top-level entries into the final dir with os.rename (os.replace + WARNING when the target exists, recursive merge when both are directories), removes the emptied staging dir, and __remove_task_staging prunes <staging_root>/<root> before the task is popped so EXTRACTING holds until the moves are done. ExtractError -> __discard_staged_output removes the staging dir and logs what was removed at WARNING; the release folder is never touched. start() removes a stale staging root with a WARNING. Constants.EXTRACT_STAGING_DIR_NAME added; LocalScanner adds it as an exclude prefix. Extract.extract_archive's signature is unchanged.
  (2) src/python/controller/controller.py: module constants _AUTO_DELETE_MAX_REARMS = 24 and _AUTO_DELETE_DEFER_REASONS; new __auto_delete_rearms counter dict under __auto_delete_lock; __schedule_auto_delete (fresh webhook arm) resets the counter and delegates to __arm_auto_delete_timer; __execute_auto_delete records a defer_reason for the state guard / unsafe_child / partial_coverage skips and calls __defer_auto_delete AFTER releasing __model_lock; __defer_auto_delete refuses to arm once __shutdown_event is set, increments the counter, re-arms and logs "Auto-delete deferred for '<root>' (attempt n/24): <reason>; retrying in <delay> s", or on exhaustion clears the counter and logs one WARNING "Auto-delete given up for '<root>' after 24 deferrals; last reason: <reason>. Local copy left in place". Terminal skips (disabled, dry-run, ModelError, evidence gate, bfs_limit) clear the counter and never re-arm; success clears it in the final-commit block; exit() clears it alongside the timer dict. Lock order unchanged (model THEN auto_delete). auto_delete_manager.py's false "next Timer-fire retries" comment on the BFS limit corrected.
  Deep-review follow-up A (same day, continuation): __publish_staged_output's OSError handler now calls __warn_unpublished_output before raising ExtractError, logging at WARNING the staged entries that never reached the release folder and are about to be discarded by __remove_task_staging ("Discarding unpublished extraction output of <archive>: <n> file(s) [<top-level entries>] in staging dir <staging> never reached <out dir> and will be removed"). The helper is guarded so a listing failure cannot mask the original OSError. The staging listing (top-level entries + recursive file count) was factored into one shared staticmethod __list_staged_output used by both __discard_staged_output and the new warning. No other behaviour changed.
verification: |
  Targeted suites: 186 passed (test_dispatch, test_dispatch_staging, test_auto_delete_rearm, test_auto_delete, test_controller, test_local_scanner), including a real zip round trip through patool via staging.
  Full unit suite (poetry venv py3.12, `pytest tests/unittests -p no:cacheprovider -q` from src/python): 21 failed, 1381 passed, 3 errors — failure set identical to the pre-change baseline of 24 macOS-environment-bound entries (multiprocessing spawn, sshcp needs a host, APFS latin-1). Zero new failures; +26 = the new tests.
  `ruff check src/python/` with ruff 0.15.22: All checks passed.
  Not yet verified: human bake on the NAS with a real rar'd release and a live arr (status awaiting_human_verify). Not committed, tagged, or version-bumped per instructions.
  Deep-review follow-up run (A + B): targeted `pytest tests/unittests/test_controller/test_extract/test_dispatch_staging.py tests/unittests/test_controller/test_auto_delete_rearm.py tests/unittests/test_controller/test_extract/test_dispatch.py -p no:cacheprovider -q` -> 47 passed, 1 warning in 29.26s. Full suite `pytest tests/unittests -p no:cacheprovider -q` -> 21 failed, 1383 passed, 2 warnings, 3 errors in 75.30s; failure set diffed against baseline_failures.txt: identical (24/24), +2 passing = the two new tests. `ruff check src/python/` (0.15.22) -> All checks passed!
files_changed:
  - src/python/common/constants.py
  - src/python/controller/extract/dispatch.py
  - src/python/controller/scan/local_scanner.py
  - src/python/controller/controller.py
  - src/python/controller/auto_delete_manager.py
  - src/python/tests/unittests/test_controller/test_extract/test_dispatch.py
  - src/python/tests/unittests/test_controller/test_extract/test_dispatch_staging.py (new)
  - src/python/tests/unittests/test_controller/test_auto_delete_rearm.py (new)
  - src/python/tests/unittests/test_controller/test_scan/test_local_scanner.py
  - src/python/tests/unittests/test_controller/test_controller.py
  - CHANGELOG.md
  - docs/CONFIGURATION.md
  - docs/ARCHITECTURE.md

## Specialist Review

reviewer: python (vibe-check:language-python, stand-in for python-expert-best-practices-code-review)
verdict: LOOKS_GOOD
summary: |
  Staging dir is os.path.join(out_dir_path, Constants.EXTRACT_STAGING_DIR_NAME), always under the extract root, never /tmp, so os.rename/os.replace in __move_tree are atomic on one filesystem. Publish walk renames each top-level entry, falls back to os.replace with a warning when the target exists, recurses to merge real directories; any OSError mid-walk is wrapped as ExtractError so the task reports failed rather than leaving a half-published tree silently. Cleanup is unconditional: finally: __remove_task_staging(task) runs on both success and ExtractError paths and the task is popped only after staging is empty, so EXTRACTING spans the whole move. Startup cleanup tolerates an absent dir and logs+continues on OSError.
  Auto-delete re-arm: __defer_auto_delete takes __auto_delete_lock, checks __shutdown_event first (closes the arm-after-shutdown window; covered by test_no_rearm_when_shutdown_begins_mid_callback); exit() clears __auto_delete_rearms alongside cancelling timers. Lock order preserved (__clear_auto_delete_rearms only ever acquires __auto_delete_lock from inside __model_lock, never the reverse). The if/elif in __execute_auto_delete short-circuits BFS once the state guard sets defer_reason. The 24-bound is off-by-one-safe: exactly MAX deferrals succeed, give-up on the MAX+1th, matching test_deferrals_accumulate_then_give_up.
  No mutable defaults, no bare except, no swallowed exceptions (OSError in __discard_staged_output / __remove_task_staging logged via logger.exception). Tests assert the requested invariants directly: release folder unchanged mid-extract, full size after, zero staging residue on success and on ExtractError, counter bound with a single give-up warning, exit() cancelling a re-armed timer.
  Low-severity edge noted, not a blocker: __move_tree os.rename across a merge when dst is a broken symlink.

## Verification Plan

decision: 2026-09-16 user deferred the human-verify bake until after deploy. Code, tests, CHANGELOG [1.7.3] - Unreleased, and docs are complete in the working tree (uncommitted); pytest and ruff gates observed green modulo the macOS environment baseline.
after_deploy: |
  1. Sync a rar-d release with auto_extract on. During unrar the release folder must show only the rars while <local_path>/.seedsyncarr-extracting/<release>/ grows; the UI must never list the dot-dir; the mkv appears in the release folder at full size only at the end.
  2. Trigger the arr import while the root is still EXTRACTING. Expect "Auto-delete deferred ... (attempt 1/24) ... retrying in 300 s", then "Auto-deleted local file ..." after extraction completes.
resume: /gsd:debug continue extract-staging-autodel-rearm

## Deep Review (vibe-check fan-out, 2026-09-16)

reviewers: language-python (LOOKS_GOOD), bugs, security, compliance (0 findings), architecture, impact (verdict: shippable), test-sufficiency
coverage: tests/unittests/test_controller minus process-spawn tests, 630 passed; dispatch.py 94%, controller.py 99%, local_scanner.py 89%, auto_delete_manager.py 97%, constants.py 100%; all uncovered lines in controller.py / local_scanner.py / auto_delete_manager.py are pre-existing, outside this diff.

recommended_now (small, inside this changeset, before deploy):
  A. APPLIED 2026-09-16 (continuation). dispatch.py ~224/269: on OSError mid-publish, log which staged entries were NOT moved before the finally-block rmtree discards them (they are regenerable from the archives, but today nothing says what was dropped). Add a test that patches os.rename to raise mid-loop and asserts ExtractError, the log, and the release-dir/staging end state. (bugs HIGH + test-sufficiency MEDIUM)
     -> dispatch.py 270-273 (call in the OSError handler), 301-320 (__warn_unpublished_output), 328 (__discard_staged_output uses the shared helper), 340-347 (__list_staged_output). Test: TestExtractDispatchStaging.test_publish_failure_logs_dropped_entries_and_leaves_no_staging_residue (test_dispatch_staging.py:278-334): os.rename patched to succeed once then raise; asserts extract_failed (not completed), logger.exception("Caught an extraction error"), release folder == release.rar + the one entry that landed, no staging root, and the WARNING naming exactly the two dropped files.
  B. APPLIED 2026-09-16 (continuation), with a wording correction. dispatch.py 292: add a test for the merge branch where an existing FILE blocks an extracted DIRECTORY (shutil.rmtree on a path in the release dir). Highest-consequence uncovered line in the diff. (test-sufficiency MEDIUM)
     -> The rmtree(dst) branch at dispatch.py:289-292 handles the OPPOSITE case from the review wording: an extracted FILE landing on an existing DIRECTORY (os.replace(file, dir) raises EISDIR, hence the rmtree first). Test written for that branch: TestExtractDispatchStaging.test_extracted_file_replaces_existing_directory_of_same_name (test_dispatch_staging.py:242-276): pre-creates <release>/movie.mkv/stale/leftover.bin, extracts a file movie.mkv; asserts extract_completed, the directory is gone and the file is in place with full content, release folder == [movie.mkv, release.rar], no staging root, and the "Replacing existing '<path>' with the newly extracted copy" WARNING. The literal reverse case is item H below.
  C. DEFERRED (follow-up). dispatch.py ~275-294: refuse symlink entries at publish (skip with a WARNING) plus a test. Pre-existing exposure, not a regression - patool wrote symlinks straight into the release folder before - but the staging step is the natural chokepoint. (security HIGH CWE-59; bugs LOW)

optional_followups (scope call) -- all DEFERRED (follow-up):
  D. autodelete.max_deferrals config key defaulting to 24, 0 restoring 1.7.2 one-shot behaviour. (impact LOW)
  E. Move the five staging helpers into controller/extract/staging.py; move _AUTO_DELETE_DEFER_REASONS next to the reason codes in auto_delete_manager.py. (architecture MEDIUM/LOW, cohesion only)
  F. sanitize_log_value on archive-derived paths in the new dispatch log lines. (security LOW CWE-117)
  G. Tests: three cleanup OSError handlers, lock-order recorder across a re-arm cycle, dispatch loop stop path. (test-sufficiency LOW)
  H. NEW (found while applying B) -- APPLIED by orchestrator in continuation_2026-09-16_orchestrator_HC (was DEFERRED at the time this was written). __move_tree does not handle an extracted DIRECTORY landing on an existing plain FILE of the same name: entry.is_dir() is true but os.path.isdir(dst) is false, so it falls to the lexists branch, logs "Replacing existing ..." (misleadingly), skips rmtree (dst is not a dir), and os.replace(dir, file) raises ENOTDIR (errno 20; verified on macOS, same on Linux per rename(2)). Net effect today: ExtractError -> extract_failed, the stale file stays in the release folder, no staging residue, and (after A) the WARNING "Discarding unpublished extraction output of ...: 1 file(s) ['Subs'] ..." names the dropped directory. Verified end-to-end with a scratchpad probe against the real ExtractDispatch. Likely fix: in the lexists branch, `if os.path.isdir(dst) and not islink: rmtree(dst) elif entry.is_dir(follow_symlinks=False): os.remove(dst)` then os.replace, plus a test asserting the file is removed and the directory lands intact (the assertions item B originally asked for). Pre-existing in spirit: patool in-place would have failed the same way. (bugs LOW-MEDIUM; test-sufficiency)

accepted_as_specified_or_preexisting (no action):
  - os.replace on an existing target and unconditional startup rmtree of the staging root: both specified by the incident brief. Shared extract path across two SeedSyncarr instances would let a restart of one delete the other in-flight staging (impact MEDIUM) - unusual deployment.
  - Exclude prefix is a startswith match at every scan depth (SystemScanner mechanism, as specified); collision needs a user file named .seedsyncarr-extracting* (impact MEDIUM, negligible likelihood).
  - extract_path missing/read-only surfaces per-archive, not at startup: same as 1.7.2.
  - Multi-archive task: archive N failing after 1..N-1 published reports the whole root failed with earlier output live: same as 1.7.2 semantics.
  - Benign double-arm race between a fresh webhook and an in-flight deferral: harmless, log line may look stale.
  - TOCTOU between lexists and os.replace: single writer thread.
  - local_size reads smaller mid-extraction with use_local_path_as_extract_path=True (bytes sit in the excluded staging dir) and jumps at publish: cosmetic, may be reported by users.
