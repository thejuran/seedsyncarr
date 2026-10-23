---
phase: 122-safety-acceptance-and-logging-fixes
plan: 06
subsystem: infra
tags: [live-acceptance, nas-sandbox, restart-persistence, import-credit]

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes (plan 12)
    provides: "D-06(e)/(a)/(c)/(b) PASS evidence on the fixed DEV_PIN (sha256:e3941f97...); same sandbox, same capture dir, reused by this plan"
provides:
  - "Live-sandbox PASS evidence for D-06(d): an early per-episode import credit survives a restart of seedsyncarr-test, the credited root is held again (not re-released) after the restart, and the whole-folder delete still waits for full coverage over a 390s post-restart window"
  - "CHECK_STATUS=PASS recorded in the NAS capture dir; D-03 checkpoint not triggered"
affects: ["122-07 (extraction, still pending)", "122-08 (SAFE-02 reconciliation)", "SAFE-01 overall (import/auto-delete and restart-persistence halves now evidenced; extraction still pending)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  modified:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md
  created:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md

key-decisions:
  - "requirements-completed left empty for SAFE-01 in this plan, consistent with 122-10/122-11/122-12's own precedent: this plan closes only the restart-persistence (D-06d) half of SAFE-01 on the fixed build. Extraction (D-07, Plan 07) still needs its own live evidence before SAFE-01 as a whole can be marked complete in REQUIREMENTS.md."
  - "Two distinct test-harness-only bugs (Rule 3) aborted the first two attempts on this session before any pass/fail evidence was produced; both fixed and the scenario rerun cleanly on a third, freshly-named root. See Deviations."
  - "Logged a pre-existing, out-of-scope shutdown-path discovery (lftp's pexpect child not terminating within the SIGTERM window on docker restart) to deferred-items.md for Phase 123 rather than investigating or fixing it here, per the executor's Scope Boundary rule -- it did not affect this plan's own checks (the controller still exited and restarted cleanly with the credit intact)."

patterns-established: []

requirements-completed: []

# Metrics
duration: ~42min
completed: 2026-10-23
---

# Phase 122 Plan 06: SAFE-01 Restart Persistence (D-06d) Summary

**An early per-episode import credit for a synthetic root (`SSA122.Bravo3.S01`) survives a full `docker restart` of `seedsyncarr-test` on the fixed build (same `controller.persist` entry before and after), the one-shot manual queue release does not survive the restart (the root is held again with `hold_reason=no_queue_entry`, never resumes transferring), and over a 390s post-restart window the whole-folder auto-delete never schedules or fires while local bytes stay byte-identical — CHECK_STATUS=PASS, D-03 not triggered.**

## Performance

- **Duration:** ~42 min (including two aborted attempts and their harness fixes, and a 390s live observation window)
- **Started:** 2026-10-23T17:45:34Z (approx.)
- **Completed:** 2026-10-23T18:27:00Z (approx.)
- **Tasks:** 3 of 3 completed (Task 3's checkpoint skipped per its own "executor skips this when CHECK_STATUS=PASS" rule)
- **Files modified:** 1 (`122-SAFE01-EVIDENCE.md`); 1 created (`deferred-items.md`)

## Accomplishments

- Confirmed preflight on every attempt: `seedsyncarr-test` on the `122-10`-fixed DEV_PIN (`sha256:e3941f97...`), seedbox port 22 open, no leftover `SSA122.*` material, `general.debug=False`, `lftp.rate_limit=0`, autodelete enabled/not-dry-run/300s delay, all as expected
- **Clean run (`SSA122.Bravo3.S01`, sizes 8/300/300 MiB):** held as `No matching queue entry`; one-shot release at NAS UTC `18:14:22Z`; E01 caught DOWNLOADED while E02/E03 were still at 0%; signed webhook posted and credited within 8s via `Credited early import of 'SSA122.Bravo3.S01E01.mkv' in 'SSA122.Bravo3.S01' (root still transferring)`; `persist.imported_children['SSA122.Bravo3.S01']` confirmed to contain `ssa122.bravo3.s01e01.mkv` **before** the restart (`persist-bravo-before.json`)
- `sudo /usr/local/bin/docker restart seedsyncarr-test` issued at `18:14:35Z`; `/server/status` returned 200 again at `18:15:13Z`; image pin unchanged (a restart, not a recreate); the identical credit confirmed **after** the restart (`persist-bravo-after.json`)
- The root went back through the completion gate fresh and was held again (`Completion hold for 'SSA122.Bravo3.S01': No matching queue entry`, the second occurrence of that exact line in the session, well after the restart) — the one-shot manual release is in-memory only and does not survive a restart (D-05)
- Over a 390s post-restart observation window (floor was 360s), the root's total local size (`307119406` bytes: E01 `8388608` + E02 `162350766` + E03 `136380032`) was read at every ~20-25s poll and was **identical at every single sample, zero variance**; zero `Scheduled auto-delete of 'SSA122.Bravo3'` lines and zero `Auto-deleted local file 'SSA122.Bravo3'` lines anywhere in the session's log window
- Exact-match secret scan over all capture files from the successful run: 0 hits; `teardown.sh` (not `--final`) printed `SANDBOX_RESTORED ok`; sandbox confirmed still on the fixed DEV_PIN afterward (`rate_limit` back to 0, `webhook_secret` empty, no leftover synthetic material); production `seedsyncarr` fingerprint re-confirmed byte-identical to the 122-11/122-12 baseline
- Wrote the "Plan 06: D-06(d) Restart persistence on the fixed build" evidence section (numbered milestones, verbatim log lines with both clocks, the `imported_children` reads before/after, per-child size readings at both ends of the observation window, teardown status lines, unit-test cross-references including `test_restart_with_persisted_credit_arms_on_commit`, and a PASS verdict citing D-06(d) and D-05)
- Logged a pre-existing, out-of-scope shutdown-path discovery (an lftp pexpect child failing to terminate within the `docker restart` SIGTERM window) to `deferred-items.md` for Phase 123's triage, per the Scope Boundary rule — it did not affect this plan's own checks

## Task Commits

1. **Task 1: Run the restart scenario on SSA122.Bravo3.S01, then session teardown** — no separate commit (no `files_modified` for this task per the plan; raw captures stayed in the NAS capture dir `/volume1/docker/v5test/results/safe01-122-20261023T165741Z`)
2. **Task 2: Write the D-06(d) evidence section with verdict** - `156c43e` (docs)
3. **Task 3: D-03 failure review** - not triggered (CHECK_STATUS=PASS); recorded below, no separate commit

**Plan metadata:** this commit (docs: complete plan)

## Files Created/Modified

- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` — appended "Plan 06: D-06(d) Restart persistence on the fixed build" (numbered milestones, verbatim log blocks, both clocks, persist `imported_children` reads before/after restart, per-child size stability readings, PASS verdict)
- `.planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md` — new file; one out-of-scope shutdown-path discovery logged for Phase 123

(Raw captures — `log-bravo.txt`, `model-d-held.json`, `model-d-e01ready.json`, `model-d-before-restart.json`, `model-d-after-*.json`, `model-d-after-final.json`, `persist-bravo-before.json`, `persist-bravo-after.json`, `webhooks.log`, `state.env`, and the throwaway orchestration script `d06restart.sh` plus two superseded attempt logs `runner-p06-attempt1-fail.log`/`runner-p06-attempt2-fail.log` — live only in the NAS capture dir `/volume1/docker/v5test/results/safe01-122-20261023T165741Z`, per the plan's output spec; not committed to the repo.)

## Decisions Made

See `key-decisions` in frontmatter. In summary: (1) SAFE-01 as a whole stays open in REQUIREMENTS.md — this plan closes only the restart-persistence (D-06d) piece; Plan 07 still owes extraction (D-07) evidence. (2) Two test-harness-only bugs (not product defects) were found and fixed in sequence on this session, each confirmed via code-level diagnosis before the fix, each followed by a clean sandbox teardown before the next attempt. (3) A pre-existing, unrelated shutdown-path warning surfaced incidentally during the restart was logged to `deferred-items.md` rather than investigated, since it is out of this plan's scope and did not affect the restart-persistence result.

## Deviations from Plan

### Auto-fixed Issues (test harness only — no product code touched)

**1. [Rule 3 - Blocking] Fixed a persist-read race in my own orchestration script (first attempt, `SSA122.Bravo.S01`)**
- **Found during:** Task 1, first attempt. Immediately after observing the `Credited early import of 'SSA122.Bravo.S01E01.mkv' in 'SSA122.Bravo.S01' (root still transferring)` log line, the script read `controller.persist` once and found `imported_children` had no entry for the root (`persist-bravo-before.json` saved as `null`), triggering `fail_exit`.
- **Issue:** `_persist_controller_now`'s synchronous write (`with self.__persist_lock: self.controller_persist.to_file(...)`) shares `__persist_lock` with the app's own periodic full-persist save. A read immediately after the credit log line (itself possibly delayed slightly behind the in-process event by the multiprocessing logger's own listener) can land in the brief window before that lock is released, observing the pre-credit file. Direct inspection of `controller.persist` minutes later, after this aborted attempt's own teardown had already run, confirmed the credit *had* in fact landed correctly (`imported_children['SSA122.Bravo.S01'] = ['ssa122.bravo.s01e01.mkv']`) — the product wrote it correctly, just not instantaneously relative to my single unretried read.
- **Fix:** Added a bounded retry loop (up to 20 attempts, 1s apart) around the persist read before concluding the credit never landed, both before and after the restart. Renamed the scenario's root to `SSA122.Bravo2.S01` for the retry, since the aborted attempt's `controller.persist` already carries a (harmless but confusing) stale `imported_children`/`stopped` entry for `SSA122.Bravo.S01` from before its teardown removed the physical files.
- **Files modified:** none under `src/` or `.planning/` — a throwaway NAS-side script (`d06restart.sh`), not a committed artifact.
- **Verification:** The retried read on the next attempt succeeded on the very first iteration (no retries actually needed that time, but the loop is now defensive against the same race recurring). Teardown after the aborted attempt printed `SANDBOX_RESTORED ok`; independently confirmed clean (`rate_limit=0`, `webhook_secret` empty, no leftover `SSA122.*` material) before the next attempt began.
- **Committed in:** not applicable (no repo file changed by this fix).

**2. [Rule 3 - Blocking] Fixed a stale pre-restart baseline in my own orchestration script's size-stability check (second attempt, `SSA122.Bravo2.S01`)**
- **Found during:** Task 1, second attempt, at the very end of the 390s observation window. The script compared a size snapshot taken *before* the restart (`SIZES_BEFORE_RESTART`, both children read as `local=0`) against the snapshot at the *end* of the observation window (`local=137994885`/`168639336`) and flagged a false `e02_local_size_changed_across_window` failure.
- **Issue:** The model's `local_size` field is only as fresh as the last completed `LocalScanner` cycle. The pre-restart snapshot was taken ~7-15s before the restart command was actually issued, during which lftp (not gated by SeedSyncarr's own scan cadence) continued writing real bytes to disk — bytes the model hadn't yet scanned and reported. The restart then froze those files at whatever lftp had genuinely written by that wall-clock moment, which was already well past the stale `local=0` reading. Independently, the HOLD-AGAIN-WAIT and OBSERVE polling loops (reading the root's *total* local size, not gated on this comparison) already showed the root-level total frozen at the exact same value for the entire 390s+ window, proving the restart-persistence behavior itself was correct — the bug was purely in which two snapshots the script chose to diff. The plan's own acceptance criterion says the size must be "unchanged between the **post-restart** snapshots" (both ends after the restart), which this comparison violated by using a pre-restart baseline.
- **Fix:** Moved the baseline capture to immediately after the root is first confirmed held again post-restart (the same snapshot already saved as `model-d-after-1.json`), and compared that against the end-of-window snapshot. Renamed the scenario's root to `SSA122.Bravo3.S01` for the clean rerun, for the same stale-persist-entry reason as the first fix.
- **Files modified:** none under `src/` or `.planning/` — same throwaway script.
- **Verification:** The corrected comparison passed on the clean rerun (`SIZES_AFTER_RESTART` and `SIZES_AFTER_WINDOW` byte-identical for both children); the full scenario then ran to completion, including the final log scan (`scheduled=0 deleted=0`), secret scan (`0` hits), and `teardown.sh` printing `SANDBOX_RESTORED ok`.
- **Committed in:** not applicable (no repo file changed by this fix).

---

**Total deviations:** 2 auto-fixed (test-harness only, Rule 3). No product-level deviations — `src/python/controller/controller.py` was read for context (confirming the arm-on-commit-covers-restart comment and the `_persist_controller_now` write path) but not modified; this plan's constraint is live acceptance evidence only, no code changes.
**Impact on plan:** Both harness fixes were necessary to get a clean, complete capture set (the two aborted attempts never reached the log-window-save/secret-scan/teardown tail of the script, so no `log-bravo.txt` or `persist-bravo-*.json` existed from either of them). Neither fix touched product code or changed any check's real-world outcome — the underlying restart-persistence behavior was already correct in both aborted attempts, just not fully evidenced due to the harness bugs. Fully contained to a non-repo throwaway script.

## Issues Encountered

- See the two Rule 3 deviations above — the only issues this session, both resolved without any product code change.
- A pre-existing, unrelated shutdown-path warning (`Could not terminate the child` from lftp's pexpect session during the `docker restart`'s `SIGTERM`) surfaced incidentally in the app log; logged to `deferred-items.md` for Phase 123 rather than investigated here (out of this plan's scope; did not affect the restart-persistence result — the controller still exited and the container restarted cleanly with the credit intact).

## User Setup Required

None — no external service configuration required.

## Task 3: D-03 failure review

**D-03 not triggered (PASS).** `CHECK_STATUS=PASS` was confirmed in the NAS capture dir's `state.env` after the clean `SSA122.Bravo3.S01` run. Per the plan's own instruction ("If PASS, write 'D-03 not triggered (PASS)' in the SUMMARY and finish without pausing"), this plan completes without a checkpoint pause.

## Next Phase Readiness

- Restart persistence (D-06d) is now evidenced on the fixed DEV_PIN (`sha256:e3941f97...`); combined with 122-12's D-06(e)/(a)/(c)/(b) evidence, the import/auto-delete half of SAFE-01 plus restart persistence are both PASS on the build that will ship
- Plan 07 (extraction, D-07) is the last live-evidence piece still owed before SAFE-01 as a whole can be marked complete in REQUIREMENTS.md
- Sandbox (`seedsyncarr-test`) fully restored: `lftp.rate_limit=0`, `webhook_secret` empty, no synthetic material on the seedbox or under `/volume1/data/v5test/torrents`, confirmed via `teardown.sh`'s `SANDBOX_RESTORED ok` plus independent `ls`/config read-backs; still pinned to the fixed DEV_PIN (teardown ran without `--final`)
- Production (`seedsyncarr`) was never named by any write command this plan; fingerprint (`Id`, image, `StartedAt`) confirmed byte-identical to the 122-11/122-12 baseline before and after this session
- A pre-existing shutdown-path discovery (lftp pexpect child not terminating within the SIGTERM window) is carried to Phase 123 via `deferred-items.md`

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-23*

## Self-Check: PASSED

- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` (modified, contains the new "Plan 06: D-06(d) Restart persistence on the fixed build" section)
- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md` (new file)
- FOUND commit `156c43e` (`git log --oneline --all | grep 156c43e`)
- Log lines, model snapshots, `persist-bravo-before.json`/`persist-bravo-after.json`, and `webhooks.log` quoted in the evidence file were read directly from the live sandbox app log and NAS capture dir during this plan's execution, not inferred; the restart timing, hold-line count, and size-stability readings were computed directly from those same captures. `SANDBOX_RESTORED ok` and `SECRET_SCAN=0` were independently re-verified by reading `state.env` and `runner-p06.log` after the run completed.
