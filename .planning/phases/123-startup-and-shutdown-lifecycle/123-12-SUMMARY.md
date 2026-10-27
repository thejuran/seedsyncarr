---
phase: 123-startup-and-shutdown-lifecycle
plan: 12
subsystem: live-verification
tags: [nas-sandbox, docker-restart, d-01, gap-1, active-transfer, failure-gate]
status: complete
gap_closure: true
check_status: FAIL
owner_decision: fix-in-phase

requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "11"
    provides: "Sandbox on DEV_PIN_GAP, GAP_CAPTURE_DIR, idle cycles I1/I2 PASS"
provides:
  - "Active-transfer cycles A1/A2 and final idle I3 on DEV_PIN_GAP"
  - "GAP-1 closed live (no scanner false ERROR in any of 6 restarts)"
  - "Session teardown SANDBOX_RESTORED ok"
  - "Owner decision fix-in-phase for the remaining lftp error (GAP-2)"

key-files:
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md

duration: ~26 min (executor) + orchestrator decision gate
completed: 2026-10-26
---

# Phase 123 Plan 12: Active-transfer restart cycles and failure gate Summary

**GAP-1 is closed live: the false "Scanner process(es) died unexpectedly" ERROR did not appear in any of the six restarts on the gap build (I1 x2, I2, A1, A2, I3). The check still fails, because both active-transfer restarts logged the lftp "Could not terminate the child" error, the other half of D-01. The owner chose to fix that in this phase too.**

## Tasks

| Task | Name | Commit | Outcome |
|------|------|--------|---------|
| 1 | Active setup and cycles A1 (SSA123.Delta.S01) / A2 (SSA123.Echo.S01) | folded into `c17d8ed` | Both proven mid-transfer (Delta 38.9%→49.2%, Echo 13.0%→19.4%) |
| 2 | I3, CHECK_STATUS, production bracketing, session teardown, evidence | `c17d8ed` | I3 PASS; CHECK_STATUS=FAIL (A1, A2: could_not_terminate, error_stopping); teardown `SANDBOX_RESTORED ok` |
| 3 | Failure review (checkpoint:decision) | (this SUMMARY) | Owner decision recorded |

## Results

- **Scanner false ERROR (GAP-1):** SCANNER_DIED=0 and CAUGHT_EXCEPTION_IN_JOB=0 in every cycle. A2 logged the intended `Scanner process(es) stopped during shutdown` INFO 0.41 s after `Caught signal SIGTERM`.
- **lftp error:** A1 logged `Error stopping lftp during controller exit` / `PtyProcessError: Could not terminate the child.` 1.80 s after SIGTERM (19:38:14.093Z). A2 logged it 1.65 s after SIGTERM (19:44:35.232Z). Both restarts still came back up and scanned (RESTART_RC=0, STARTING_OK=1, READY_OK=1, SCAN_OK=1).
- **"Exited successfully"** (recorded only, per 123-09): A1=0, A2=0, I3=1.
- **Teardown and production:** the teardown ended `SANDBOX_RESTORED ok`. No `SSA123.` names remain on the seedbox or in sandbox torrents, the stage dir is gone, `lftp.rate_limit` was restored, and the sandbox is still on DEV_PIN_GAP. The production fingerprint was byte-identical before and after (`PROD_UNCHANGED_S2B`).

## Diagnosis (lftp)

`Controller.exit()` stops lftp first. `Lftp.exit()` (src/python/lftp/lftp.py) calls the pexpect/ptyprocess `close(force=True)`. During an active transfer, the pty child does not terminate within ptyprocess's own timeout, so it raises `PtyProcessError`. `Controller.exit()`'s per-component try/except contains the error, and the remaining components are still stopped (LIFE-02 behaviour holds). This code path was not touched by 123-01..04 or 123-08.

## Owner decision (Task 3, verbatim)

"Fix in this phase (Recommended)". Option `fix-in-phase`. Route: `/bm:plan-phase 123 --gaps` (GAP-2: lftp shutdown during an active transfer). 123-07 must not mark the live check passed while this is open.
