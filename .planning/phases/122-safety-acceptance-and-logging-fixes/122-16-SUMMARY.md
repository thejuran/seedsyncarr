---
phase: 122-safety-acceptance-and-logging-fixes
plan: 16
subsystem: infra
tags: [gap-closure, live-acceptance, nas-sandbox, re-pin, d-06c-rerun, wr-02-live, log-01, wr-01-live]
gap_closure: true

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes
    plan: 15
    provides: "New DEV_PIN (sha256:f8204207...) containing 122-13/122-14's fixes, pushed to PR #134, CI run 404 green"
provides:
  - "seedsyncarr-test re-pinned from IMAGE_PIN_L0 (1.7.6) to the gap-cycle-2 DEV_PIN; production confirmed byte-identical before/after"
  - "LOG-01 and WR-01 reconfirmed live on the new build (seedsyncarr.WebhookHandler / seedsyncarr.StatusHandler lines observed)"
  - "D-06(c) rerun PASS on the narrowed (122-13) post-transfer grace window: SSA122.India.S01 (with held decoy) and SSA122.Juliet.S01 both show late child webhooks accepted via 'Recorded webhook import' well inside the new 120 s window, never dropped"
  - "WR-02 live PASS: a child webhook kept pending on SSA122.Hotel.S01 is discarded instantly on a user STOP ('Discarded 1 pending import notice(s) ... user stop'); Hotel is never credited, recorded or scheduled"
  - "CHECK_STATUS=PASS recorded in the NAS capture dir; D-03 checkpoint not triggered"
affects: ["122-17 (writes the full rerun evidence narrative into 122-SAFE01-EVIDENCE.md, restores the sandbox to IMAGE_PIN_L0 via teardown.sh --final, and updates the SAFE-01 verdict for the gap-cycle-2 build)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  modified:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md

key-decisions:
  - "requirements-completed left empty: SAFE-01 and LOG-01 are already [x] Complete in REQUIREMENTS.md (122-08 owner-approved verdict; Plan 04). This plan re-confirms both live on the gap-cycle-2 build; it does not newly complete either requirement. 122-17 updates the formal SAFE-01 verdict text to point at this rerun."
  - "Task 1's first re-pin attempt failed on a harness-only timing race (single HTTP-200 readiness check raced the container recreate); diagnosed, fixed, and rerun once per the checkpoint rule's own stated precedent (122-05 round 1 / 122-06). No product code was touched. See Deviations."
  - "The sandbox is deliberately left on the gap-cycle-2 DEV_PIN at the end of this plan (session teardown, not --final) — 122-17 runs the --final restore to IMAGE_PIN_L0."

patterns-established: []

requirements-completed: []

# Metrics
duration: ~40min
completed: 2026-10-23
---

# Phase 122 Plan 16: Sandbox Re-pin, Live LOG-01/WR-01 Recheck, D-06(c) Rerun (India/Juliet), Live WR-02 Stop Check (Hotel) Summary

**Re-pinned `seedsyncarr-test` to the 122-15 gap-cycle-2 build (`sha256:f8204207...`), reconfirmed LOG-01 and WR-01 live, then reran the narrowed D-06(c) post-transfer grace window on two independent roots (India with a held decoy, Juliet) — both show a late child webhook accepted via `Recorded webhook import` 62-73 s after posting, well inside 122-13's new 120 s window, never dropped — and added a live WR-02 check on a third root (Hotel): a pending notice is discarded within 0.1 s of a user STOP, with no credit, record or schedule ever issued for it.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-10-23T23:46:13Z
- **Completed:** 2026-10-24T00:26:38Z
- **Tasks:** 3 of 3 completed (Task 3's checkpoint was skipped per its own "executor skips this when CHECK_STATUS=PASS" rule)
- **Files modified:** 1 (`122-SAFE01-EVIDENCE.md`)

## Accomplishments

- **Task 1 (re-pin, LOG-01, WR-01):** Re-pinned `seedsyncarr-test` from `IMAGE_PIN_L0` (`ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0...`) to the 122-15 `NEW_DEV_PIN` (`ghcr.io/thejuran/seedsyncarr@sha256:f8204207...`) via the inode-preserving compose edit (`stat -c %i` unchanged: `101505523` before and after). Confirmed LOG-01 live: an unsigned `{"eventType":"Test"}` POST returned HTTP 200 `Test OK`, and the app log gained `seedsyncarr.WebhookHandler ... Sonarr webhook test event received` (app-log `2026-10-23 19:59:22,427`, NAS UTC `23:59:22.427Z`). Confirmed WR-01 live: a 61-request `/server/status` burst produced `200=60, 429=1`, and the app log gained `seedsyncarr.StatusHandler ... Rate limit exceeded for __handle_get_status` (app-log `20:00:29,752`, NAS UTC `2026-10-24T00:00:29.752Z`). Production `seedsyncarr` fingerprint (`Id`, image, `StartedAt`) confirmed byte-identical before/after, matching the documented 122-08 baseline exactly (no drift this session).
- **Task 2 (D-06(c) rerun + live WR-02):** Ran all three rounds on the first attempt with no retries needed:
  - **Round A (`SSA122.India.S01` + held decoy `SSA122.IndiaDecoy.S01`, sizes 8/300/800/1200 MiB, decoy 8 MiB):** both roots held as `No matching queue entry`; one-shot release queued India only (decoy confirmed held/untouched at hold time, mid-transfer, and after India's own deletion). E01 caught `DOWNLOADED` while E02/E03/E04 were still transferring (0%/0%/0% locally at the moment E01 posted) and was credited immediately. E02 (33.2% complete) and E03 (12.0% complete) were posted genuinely incomplete and credited early (`root still transferring`). **E04 was posted at 10.3% complete and accepted 61.8 s later via `Recorded webhook import: 'SSA122.India.S01' (child: 'SSA122.India.S01E04.mkv')` — not dropped**, well inside 122-13's new 120 s grace window. `Scheduled auto-delete of 'SSA122.India.S01' in 300 seconds` followed immediately (1 line after the accept), and `Auto-deleted local file 'SSA122.India.S01'` fired exactly 300.004 s later (`20:10:15.254` to `20:15:15.258`); the local directory is confirmed gone. Zero `Ignoring webhook import for 'SSA122.` and zero `Completion hold cleared for 'SSA122.` lines anywhere in the session.
  - **Round B (`SSA122.Juliet.S01`, (c)-only repeat, sizes 8/800/1200 MiB, no decoy):** held, released once; E02 (0%) and E03 (0%) posted genuinely incomplete. E02 credited early; **E03 accepted 73.4 s later via `Recorded webhook import` — again not dropped.** `Scheduled auto-delete of 'SSA122.Juliet.S01' in 300 seconds` observed (no delete wait required for this round).
  - **Round C (`SSA122.Hotel.S01`, live WR-02 stop check, sizes 8/1200 MiB):** held, released once; E02's webhook posted the instant it was observed `downloading` at 0% of 1200 MiB (well under the 30% ceiling), and recorded as `Sonarr webhook import enqueued`/`Sonarr import detected` — kept pending, never credited. 6 s later E02 was reconfirmed still incomplete (0%/1200 MiB). `POST /server/command/stop/SSA122.Hotel.S01` returned HTTP 200; **`Discarded 1 pending import notice(s) for 'SSA122.Hotel.S01': user stop` appeared 0.1 s after the STOP was processed.** A further 90 s watch found zero `Credited early import of 'SSA122.Hotel.S01E02`, zero `Recorded webhook import: 'SSA122.Hotel.S01'` and zero `Scheduled auto-delete of 'SSA122.Hotel.S01'` lines; `persist.imported_children['SSA122.Hotel.S01']` is `null`.
  - All 7 webhook posts (4 India + 2 Juliet + 1 Hotel) returned exactly one HTTP 200 each (`webhooks.log`). Exact-match secret scan over every capture file: 0 hits. `teardown.sh` (not `--final`) printed `SANDBOX_RESTORED ok`; re-run a second time (this plan's own literal verify command) printed the identical result, confirming idempotence. Production fingerprint re-confirmed byte-identical. Sandbox confirmed still on the gap-cycle-2 `DEV_PIN` afterward.
- Appended the "Sandbox re-pin, LOG-01 and WR-01 live recheck (gap cycle 2)" evidence subsection to `122-SAFE01-EVIDENCE.md` (Task 1's output only, per the plan's own scope — Task 2's full D-06(c)/WR-02 narrative with verdicts is written by 122-17).

## Task Commits

1. **Task 1: Re-pin to gap-cycle-2 DEV_PIN; confirm LOG-01 and WR-01 live; record evidence** — `ac98f7e` (docs)
2. **Task 2: D-06 rerun (India + held decoy, Juliet) and live WR-02 stop check (Hotel); teardown on every exit path** — no separate commit (no `files_modified` for this task per the plan; raw captures stayed in the NAS capture dir `/volume1/docker/v5test/results/safe01-122-20261023T234813Z`)
3. **Task 3: D-03 failure review** — not triggered (`CHECK_STATUS=PASS`); recorded below, no separate commit

**Plan metadata:** this commit (docs: complete plan)

## Files Created/Modified

- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` — appended "Sandbox re-pin, LOG-01 and WR-01 live recheck (gap cycle 2)" (capture dir, re-pin facts, inode check, deploy transcript, the first-attempt harness bug and fix, production fingerprint, verbatim LOG-01/WR-01 lines with all three clocks, status-burst tally, CR-01 unit-only note)

(Raw captures — `log-gap2.txt`, `model-e-held.json`, `model-india-*.json`, `model-juliet-*.json`, `model-hotel-*.json`, `model-hotel-prestop.json`, `persist-india.json`, `persist-juliet.json`, `persist-hotel.json`, `posts-india.txt`, `posts-juliet.txt`, `posts-hotel.txt`, `webhooks.log`, `status-burst.txt`, `prod-before*.txt`/`prod-after*.txt`, `state.env`, and the throwaway orchestration scripts `task1.sh`/`task1b.sh`/`task2.sh`/`model_tools2.py` — live only in the NAS capture dir `/volume1/docker/v5test/results/safe01-122-20261023T234813Z`, per the plan's output spec; not committed to the repo.)

## Decisions Made

See `key-decisions` in frontmatter. In summary: (1) SAFE-01/LOG-01 stay `requirements-completed: []` — both are already `[x]` in REQUIREMENTS.md and this plan only reconfirms them live on the gap-cycle-2 build; 122-17 updates the formal verdict text. (2) A test-harness-only timing bug in Task 1's first re-pin attempt (not product code) was diagnosed and fixed, then the corrected script was rerun once, per the checkpoint rule's own cited precedent. (3) The sandbox is intentionally left on `DEV_PIN` (not restored) at the end of this plan; 122-17 owns the `--final` restore.

## Deviations from Plan

### Auto-fixed Issues (test harness only — no product code touched)

**1. [Rule 3 - Blocking] Fixed a re-pin readiness race in my own orchestration script (Task 1, first attempt)**
- **Found during:** Task 1, first re-pin attempt. The script's `READY-POLL` loop accepted a single HTTP 200 from `/server/status` as proof the new container was up, then immediately took the `LOG01_START_LINES` baseline. The unsigned Test webhook POST returned HTTP 200 `Test OK` as expected, but the follow-up check for a new `seedsyncarr.WebhookHandler` / `Sonarr webhook test event received` line failed — no such line existed anywhere in the checked window.
- **Issue:** Reading the app log directly confirmed the `LOG01_START_LINES` baseline (`wc -l` = 5512) was taken at the exact line corresponding to the OLD (1.7.6) container's own shutdown (`Exited successfully`), roughly 53 s *before* the NEW container's first `Starting SeedSyncarr` line was ever written. The container recreate (stop old, create new, start new) took unusually long on this NAS run, and a single HTTP-200 check was not a reliable proxy for "the new process has started and begun logging" — it is plausible the port briefly responded in a transitional state, or the readiness loop's own curl timeouts absorbed enough wall time that the check landed in an ambiguous window. Either way this was purely a harness timing assumption, not a product defect: the webhook endpoint itself answered correctly (200, `Test OK`), and the full log window was independently checked for the missing line with no false negative possible (20-line window covering the whole gap, confirmed by direct `sed`/`grep`).
- **Fix:** Rewrote the readiness check to require a fresh `Starting SeedSyncarr` app-log line (proof the new process actually started) *in addition to* the HTTP-200 check, added an 8 s settle delay before taking the `LOG01_START_LINES` baseline, and changed both the LOG-01 and WR-01 "new line" checks from a single grep-after-fixed-sleep into a bounded 20 s retry poll. The first attempt's own `EXIT` trap correctly ran `teardown.sh --final`, which printed `SANDBOX_RESTORED ok` and independently confirmed the sandbox back on `IMAGE_PIN_L0` and production unchanged, before the corrected script (`task1b.sh`) was uploaded and run once.
- **Files modified:** none under `src/` or `.planning/` (beyond the evidence file, which documents the fix) — the fix is confined to a throwaway NAS-side script, not a committed artifact.
- **Verification:** The corrected script's run found `STARTING-POLL` taking 7 attempts (~35 s) to observe the fresh `Starting SeedSyncarr` line, then succeeded immediately on `READY-POLL` attempt 1. The LOG-01 and WR-01 checks both found their target line on the very first retry iteration. Production fingerprint confirmed byte-identical before and after this (second) run.
- **Committed in:** not applicable (no repo file changed by this fix; the evidence file documents it as a narrative, not a code change).

---

**Total deviations:** 1 auto-fixed (test-harness only, Rule 3). No product-level deviations — `src/python/controller/controller.py` was read for context (confirming `__check_webhook_imports`'s evidence gate, `_discard_pending_notices`, and the STOP/DELETE_LOCAL wiring in `__process_commands`) but not modified; this plan's constraint is live acceptance evidence only, no code changes.
**Impact on plan:** The harness fix was necessary to get a clean LOG-01/WR-01 pass and did not require re-running Task 2 or change any check's real-world outcome — Task 2 then ran cleanly on the first attempt with zero retries (no Kilo or Hotel2 fallback needed for either Round A or Round C).

## Issues Encountered

- See the Rule 3 deviation above — the only issue this session, resolved without touching any product code.

## User Setup Required

None — no external service configuration required.

## Task 3: D-03 failure review

**D-03 not triggered (PASS).** `CHECK_STATUS=PASS` was confirmed in the NAS capture dir's `state.env`, cross-checked via the plan's own literal Task 2 `<verify>` command: `Ignoring webhook import for 'SSA122.` = 0, `Discarding pending webhook import 'SSA122.` = 0, `for 'SSA122.Hotel.S01': user stop` = 1, `Auto-deleted local file 'SSA122.India.S01'` = 1, `persist-india.json` lists all four children, `SECRET_SCAN=0`, production fingerprint diff empty (`PROD_UNCHANGED_T2`), and a fresh re-run of `teardown.sh` printed `SANDBOX_RESTORED ok` again. Per the plan's own instruction ("If PASS, write 'D-03 not triggered (PASS)' in the SUMMARY and finish without pausing"), this plan completes without a checkpoint pause.

## Next Phase Readiness

- The narrowed D-06(c) fix (122-13) is proven live on the gap-cycle-2 build (`DEV_PIN sha256:f8204207...`) on two independent roots (India with a held decoy, Juliet), and the new WR-02 stop-discard behavior (122-13) is proven live on a third (Hotel).
- LOG-01 and WR-01 (122-14) are both reconfirmed live on this same build.
- 122-17 should: write the full D-06(c)/WR-02 rerun narrative (per-round milestones, verbatim log lines, persist reads) into `122-SAFE01-EVIDENCE.md`, run `teardown.sh --final` to restore the sandbox to `IMAGE_PIN_L0` (1.7.6) and independently re-verify, and update the SAFE-01 verdict table to point at this gap-cycle-2 evidence (superseding the pre-122-13/14 evidence recorded in "Plan 12: D-06 rerun on the fixed build").
- Sandbox (`seedsyncarr-test`) is currently on the gap-cycle-2 `DEV_PIN`, `lftp.rate_limit=0`, `webhook_secret` empty, no synthetic material anywhere (confirmed via `teardown.sh`'s `SANDBOX_RESTORED ok`, run twice). Production (`seedsyncarr`) was never named by any write command this session; fingerprint confirmed byte-identical throughout.
- Branch `gsd/phase-122-safety-acceptance-and-logging-fixes` / PR #134 is unchanged except for this plan's one docs-only commit; no merge, no new PR, no `gh pr ready`.

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-23*

## Self-Check: PASSED

- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-16-SUMMARY.md`
- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` (contains "Sandbox re-pin, LOG-01 and WR-01 live recheck (gap cycle 2)")
- FOUND commit `ac98f7e` (`git log --oneline --all | grep ac98f7e`)
- Log lines, model snapshots, `persist-india.json`/`persist-juliet.json`/`persist-hotel.json`, `posts-*.txt`, and `webhooks.log` quoted above were read directly from the live sandbox app log and NAS capture dir during this plan's execution, not inferred. The 300.004 s auto-delete timing, the 61.8 s/73.4 s accept spans, and the 0.1 s STOP-to-discard span were computed directly from the app log's own timestamps. `SANDBOX_RESTORED ok`, `SECRET_SCAN=0`, and `CHECK_STATUS=PASS` were independently re-verified via the plan's own literal Task 2 verify command after the run completed.
