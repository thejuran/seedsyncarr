---
phase: 122-safety-acceptance-and-logging-fixes
plan: 12
subsystem: infra
tags: [gap-closure, live-acceptance, nas-sandbox, synthetic-webhook, d-06c-rerun, regression]
gap_closure: true

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes (plan 11)
    provides: "New DEV_PIN (sha256:e3941f97...) containing 122-10's fix, re-pinned to seedsyncarr-test; capture dir safe01-122-20261023T165741Z"
provides:
  - "Live-sandbox PASS evidence for all four D-06 import/auto-delete scenarios (e/a/c/b) on the build that will ship, closing 122-05's D-06(c) FAIL"
  - "A second (c)-only repeat on an independent root (SSA122.Foxtrot.S01), also PASS, reducing the chance either pass was a race-window miss"
  - "CHECK_STATUS=PASS recorded in the NAS capture dir; D-03 checkpoint not triggered"
affects: ["122-06/07 (restart persistence, extraction — continue on this same DEV_PIN)", "122-08 (SAFE-02 reconciliation)", "SAFE-01 overall (import/auto-delete half now evidenced; extraction and restart persistence still pending in Plans 06/07)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  modified:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md

key-decisions:
  - "requirements-completed left empty for SAFE-01 in this plan, consistent with 122-10/122-11's own precedent: this plan closes only the D-06(e/a/c/b) import/auto-delete half of SAFE-01 on the fixed build. Restart persistence (D-06d, Plan 06) and extraction (D-07, Plan 07) still need their own live evidence before SAFE-01 as a whole can be marked complete in REQUIREMENTS.md."
  - "The NAS-side orchestration script's scan_secret() helper had a bash bug (grep -c's own zero-count output plus an `|| echo 0` fallback double-printed '0\\n0' whenever a file had zero matches, which is a bash arithmetic *syntax* error, not just a nonzero exit status — and syntax errors inside `$(( ))` terminate the whole script immediately in bash, even without `set -e`). This fired right after the real D-06 checks had already completed successfully (the script's own 'RUN SUCCESS: all checks passed' line was printed first), so the script exited before it could run the exact-secret scan with a valid count, teardown.sh, or set CHECK_STATUS in state.env. Treated as a Rule 3 (blocking, test-harness-only) issue: manually re-ran the corrected exact-match secret scan over all 20 capture files (zero hits), recorded SECRET_SCAN=0 and CHECK_STATUS=PASS in state.env by hand, then ran teardown.sh, which printed SANDBOX_RESTORED ok. No product code was touched; the bug and fix are confined to the throwaway NAS-side script, not committed to the repo."

patterns-established: []

requirements-completed: []

# Metrics
duration: ~35min
completed: 2026-10-23
---

# Phase 122 Plan 12: D-06 Rerun on the Fixed Build Summary

**All four D-06 import/auto-delete scenarios (Waiting hold + one-shot release, early per-episode credit, pending-notice deferral/revalidation, arm-on-commit with a real 300s auto-delete) now PASS live on the DEV_PIN containing 122-10's fix — including a second independent repeat of the exact race that failed in 122-05 (a deferred child webhook accepted via "Recorded webhook import" instead of dropped with "Ignoring webhook import"), closing the 122-05 D-06(c) gap.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-10-23T17:11:26Z
- **Completed:** 2026-10-23T17:37:57Z
- **Tasks:** 3 of 3 completed (Task 3's checkpoint was skipped per its own "executor skips this when CHECK_STATUS=PASS" rule)
- **Files modified:** 1 (`122-SAFE01-EVIDENCE.md`)

## Accomplishments

- Confirmed preflight: `seedsyncarr-test` on the new DEV_PIN (`sha256:e3941f97...`), seedbox port 22 open, no leftover `SSA122.*` material anywhere, `general.debug=False`, `lftp.rate_limit=0`, `autodelete` enabled/not-dry-run/300s delay — all as expected
- **Round A (`SSA122.Echo.S01` + held decoy `SSA122.EchoDecoy.S01`, sizes 8/300/800/1200 MiB):** both roots held as `No matching queue entry`; one-shot release queued only Echo; E01 caught DOWNLOADED while all three siblings were still at 0%, credited immediately; E02/E03 posted and credited genuinely incomplete (0% and ~17.5%); **E04 posted at ~11.6% complete and accepted 62 seconds later via `Recorded webhook import: 'SSA122.Echo.S01' (child: 'SSA122.Echo.S01E04.mkv')` — not dropped** (122-05's analogous post on `SSA122.Alpha2.S01E04` was dropped after 61 seconds on the pre-fix build); `persist.imported_children['SSA122.Echo.S01']` holds all four video children; decoy confirmed held and untransferred at three separate points across the whole session, including after Echo had already auto-deleted; real 300.004s auto-delete timer fired and the local directory is confirmed gone
- **Round B (`SSA122.Foxtrot.S01`, (c)-only repeat, no decoy, E01 deliberately never webhooked):** E02/E03 posted genuinely incomplete (both 0%); E02 credited via the ordinary early-credit path; **E03 accepted via `Recorded webhook import` ~104 seconds after posting — again not dropped**; `persist.imported_children['SSA122.Foxtrot.S01']` holds both webhooked children
- Zero `Ignoring webhook import for 'SSA122.` lines and zero `Completion hold cleared for 'SSA122.` lines anywhere in the session's full log window (`grep -c` = 0 for both, confirmed independently via the plan's own verify command)
- Exact-match secret scan (corrected after a harness bug — see Deviations) over all 20 capture files: 0 hits; `teardown.sh` (not `--final`) printed `SANDBOX_RESTORED ok`; sandbox confirmed still on the new DEV_PIN afterward (rate_limit back to 0, no leftover synthetic material); production `seedsyncarr` fingerprint (Id, image, `StartedAt`) re-confirmed byte-identical to the 122-11 baseline
- Wrote the "Plan 12: D-06 rerun on the fixed build" evidence section (five subsections, each ending with a PASS verdict), appended a one-line "Superseded" note to the original Plan 05 D-06(c) FAIL subsection without editing its original text (confirmed via `git diff`, additions-only)

## Task Commits

1. **Task 1: Rerun (e), (a), (c), (b) on SSA122.Echo.S01 with held decoy, then a (c)-only repeat on SSA122.Foxtrot.S01** — no separate commit (no `files_modified` for this task per the plan; raw captures stayed in the NAS capture dir `/volume1/docker/v5test/results/safe01-122-20261023T165741Z`)
2. **Task 2: Write the Plan 12 D-06 rerun evidence with verdicts** - `74659f7` (docs)
3. **Task 3: D-03 failure review** - not triggered (CHECK_STATUS=PASS); recorded below, no separate commit

**Plan metadata:** this commit (docs: complete plan)

## Files Created/Modified

- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` — appended "Plan 12: D-06 rerun on the fixed build" (five subsections: D-06(e)/(a)/(c) rerun, D-06(c) Foxtrot repeat, D-06(b), each with numbered milestones, verbatim log blocks, both clocks, per-post child-state tables, persist `imported_children` lists, final file state, PASS verdicts) and a one-line "Superseded" note appended to the end of Plan 05's original D-06(c) FAIL subsection

(Raw captures — `log-echo-foxtrot.txt`, `model-e-held.json`, `model-echo-*.json`, `model-foxtrot-*.json`, `persist-echo.json`, `persist-foxtrot.json`, `posts-echo.txt`, `posts-foxtrot.txt`, `webhooks.log`, `state.env`, and the throwaway orchestration scripts `d06rerun.sh`/`child_check.py` — live only in the NAS capture dir `/volume1/docker/v5test/results/safe01-122-20261023T165741Z`, per the plan's output spec; not committed to the repo.)

## Decisions Made

See `key-decisions` in frontmatter. In summary: (1) SAFE-01 as a whole stays open in REQUIREMENTS.md — this plan closes only the import/auto-delete (D-06) half; Plans 06/07 still owe restart-persistence and extraction evidence on this same build. (2) A test-harness-only bash bug in the session's own cleanup helper (not product code) was fixed by hand after the fact, once I confirmed from the script's own transcript that every actual D-06 check had already passed before the bug fired.

## Deviations from Plan

### Auto-fixed Issues (test harness only — no product code touched)

**1. [Rule 3 - Blocking] Fixed a bash arithmetic-syntax-error in my own orchestration script's `scan_secret` helper, and manually completed the post-run housekeeping it had short-circuited**
- **Found during:** Task 1, end of Round B, immediately after the script printed `RUN SUCCESS: all checks passed`.
- **Issue:** `scan_secret()`'s per-file count line was `c=$(grep -c -F -f "$D/secret" "$f" 2>/dev/null || echo 0)`. `grep -c` with zero matches still prints `0` to stdout but exits with status 1; because the exit status was nonzero, bash's `||` *also* ran `echo 0`, so `$c` became the two-line string `"0\n0"` for every clean (no-match) file. `total=$((total + c))` then failed with a genuine bash arithmetic *syntax* error (not just a nonzero exit code) — and a syntax error inside `$(( ))` terminates the entire script immediately, even without `set -e`. The script had already logged every one of the plan's required PASS conditions (zero `Ignoring` lines, zero `Completion hold cleared` lines, complete `imported_children` for both roots, correct accept-before-schedule ordering, the real 300.004s auto-delete, the directory confirmed gone) before this line ran, but it exited before reaching the exact-secret scan's final count, before `state_set CHECK_STATUS`, and before calling `teardown.sh` — leaving `lftp.rate_limit=4194304` live and all three synthetic roots (`SSA122.Echo.S01`/`EchoDecoy.S01`/`Foxtrot.S01`, the first two already auto-deleted/held, the third still fully present) un-cleaned-up.
- **Fix:** Confirmed via `ps aux` that the script process had genuinely exited (not stalled). Manually re-ran the corrected scan (`c=$(grep -c -F -f "$D/secret" "$f" 2>/dev/null); c=${c:-0}`, no `||`) over all 20 capture files — 0 hits on every file, total 0 — and appended `SECRET_SCAN=0` and `CHECK_STATUS=PASS` to `state.env` by hand (both values the script would itself have written had the bug not fired, based on its own already-logged checks). Then ran `bash teardown.sh` directly, which printed `RESTORED rate_limit ok`, `REMOVED synth roots count=3 refused=0`, `RESTORED webhook_secret ok (len=0)`, and `SANDBOX_RESTORED ok`. Independently re-confirmed afterward: sandbox still on the new DEV_PIN (teardown without `--final` doesn't change the pin), `lftp.rate_limit` reads back `0`, no `SSA122.*` material anywhere, production `seedsyncarr` fingerprint unchanged.
- **Files modified:** none under `src/` or `.planning/` — this was a throwaway NAS-side script (`d06rerun.sh`), not a committed artifact. The corrected scan logic was applied by hand on the NAS, not re-uploaded as a new script version (the session was already complete).
- **Verification:** Re-ran the plan's own literal Task 1 `<verify>` command after the manual recovery — `grep -c "Ignoring webhook import for .SSA122"` → `0`, `grep -c "Auto-deleted local file .SSA122.Echo.S01"` → `1`, `persist-echo.json` lists all four children, `state.env` shows `CHECK_STATUS=PASS`/`SECRET_SCAN=0`, and `bash teardown.sh | tail -1` → `SANDBOX_RESTORED ok` (teardown is documented idempotent; re-running it a second time is safe and produced the identical result).
- **Committed in:** not applicable (no repo file changed by this fix).

---

**Total deviations:** 1 auto-fixed (test-harness only, Rule 3). No product-level deviations — `src/python/controller/controller.py` was read for context (confirming the `Recorded webhook import` log line's exact source, `controller.py:882`) but not modified; this plan's constraint is live acceptance evidence only, no code changes.
**Impact on plan:** The harness fix was necessary to complete the session's cleanup (secret scan + sandbox restore) after the real D-06 checks had already all passed; it did not require re-running any scenario and did not change any check's outcome. Fully contained to a non-repo throwaway script.

## Issues Encountered

- See the Rule 3 deviation above (the `scan_secret` bash bug) — the only issue this session, resolved without re-running any live scenario.

## User Setup Required

None — no external service configuration required.

## Task 3: D-03 failure review

**D-03 not triggered (PASS).** `CHECK_STATUS=PASS` was confirmed in the NAS capture dir's `state.env` (after the manual recovery documented above, which only completed already-passed-check bookkeeping and never altered any check's outcome). Per the plan's own instruction ("If PASS, write 'D-03 not triggered (PASS)' in the SUMMARY and finish without pausing"), this plan completes without a checkpoint pause.

## Next Phase Readiness

- The 122-05 D-06(c) gap is closed with running-build evidence on the new DEV_PIN (`sha256:e3941f97...`); Plans 06 (restart persistence) and 07 (extraction) can proceed on this same build
- SAFE-01 stays `[ ]` in REQUIREMENTS.md — this plan closes the import/auto-delete (D-06) half only; restart persistence and extraction evidence are still owed by Plans 06/07 before SAFE-01 as a whole can be marked complete
- Sandbox (`seedsyncarr-test`) fully restored: `lftp.rate_limit=0`, `webhook_secret` empty, no synthetic material on the seedbox or under `/volume1/data/v5test/torrents`/`/downloads`, confirmed via `teardown.sh`'s `SANDBOX_RESTORED ok` plus independent `ls`/config read-backs; still pinned to the new DEV_PIN (teardown ran without `--final`)
- Production (`seedsyncarr`) was never named by any write command this plan; fingerprint (Id, image, `StartedAt`) confirmed byte-identical to the 122-11 baseline before and after this session

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-23*

## Self-Check: PASSED

- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` (modified, contains the new "Plan 12: D-06 rerun on the fixed build" section and the Plan 05 "Superseded" line)
- FOUND commit `74659f7` (`git log --oneline --all | grep 74659f7`)
- Log lines, model snapshots, `persist-echo.json`/`persist-foxtrot.json`, `posts-echo.txt`/`posts-foxtrot.txt`, and `webhooks.log` quoted in the evidence file were read directly from the live sandbox app log and NAS capture dir during this plan's execution, not inferred; the 300.004s auto-delete timing was computed directly from the app log's own timestamps; the `SANDBOX_RESTORED ok` and `SECRET_SCAN=0` results were independently re-verified via the plan's own literal verify command after the manual recovery.
