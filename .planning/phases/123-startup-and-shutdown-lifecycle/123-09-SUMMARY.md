---
phase: 123-startup-and-shutdown-lifecycle
plan: 09
subsystem: testing
tags: [harness, restart-cycle, resumability, bash-trap, gap-closure, d-07]

requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "06"
    provides: "Committed restart-cycle harness (bb7146f); live FAIL evidence showing I2 ran with no CYCLE_I2= line and the executor stalling mid-session"
provides:
  - "Resumable restart-cycle harness: every invocation always leaves a CYCLE_<label>= outcome (PASS, FAIL:<reasons>, or INCOMPLETE:<step>) in state.env, even on SIGTERM/SIGINT/SIGHUP before a verdict"
  - "STEP <name> <utc> progress lines at each of 12 steps, enabling detached (nohup) runs polled via state.env/out file instead of a blocking watchdog"
  - "RESTART_ELAPSED_S informational signal for docker restart wall time"
  - "Exited successfully demoted from a PASS/FAIL criterion to recorded-only, with the 1.7.6 baseline justification documented in the script header"
affects: ["123-10", "123-11", "123-12"]

tech-stack:
  added: []
  patterns: ["Bash EXIT trap with a VERDICT_WRITTEN guard to distinguish a clean verdict from an interrupted run", "STEP progress markers for detached/polled script execution"]

key-files:
  created: []
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh

key-decisions:
  - "Exited successfully stays counted (EXITED_SUCCESSFULLY) but is recorded-only, not a PASS/FAIL criterion, because it is logged only after the full shutdown sequence completes and is therefore absent whenever docker's 10s stop timeout SIGKILLs the process -- the pre-existing 1.7.6 baseline window shows the identical gap (BASELINE_EXITED_SUCCESSFULLY=0)"
  - "All D-01 shutdown-error criteria (scanner_died, could_not_terminate, caught_exception_in_job, error_stopping, restart_rc) are unchanged hard pass/fail checks"

requirements-completed: [LIFE-01, LIFE-02]

duration: ~20min
completed: 2026-10-26
---

# Phase 123 Plan 09: Restart-cycle harness hardening Summary

**123-restart-cycle.sh now always records a cycle outcome (PASS/FAIL/INCOMPLETE:<step>) via a STARTED marker plus an EXIT trap, prints per-step progress for detached/polled runs, tracks restart wall-clock time, and treats "Exited successfully" as a documented recorded-only signal instead of a pass/fail criterion.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 completed (combined into a single commit per the plan's explicit sequencing: prove the smoke test before committing)
- **Files modified:** 1

## Accomplishments
- Added `STEP=init`/`VERDICT_WRITTEN=0` state, an `INT TERM HUP` trap that exits 130, and an `EXIT` trap (`on_exit`) that writes `CYCLE_<label>=INCOMPLETE:<step>` to `state.env` whenever the script exits without a verdict having been written
- Added a `CYCLE_<label>_STARTED=<utc>` line written before the restart, so a SIGKILLed run is still visible as started-without-verdict
- Added a `step()` helper printing `STEP <name> <utc>` at the start of each of the 12 existing steps (pre_scan, marker, restart, starting_poll, ready_poll, settle, scan_poll, rotation, window, counts, env, verdict)
- Added `RESTART_ELAPSED_S` (wall seconds around `$DOCKER restart seedsyncarr-test`), written to `cycle-<label>.env` right after `RESTART_RC` and included in the first summary echo line
- Removed the `if [ "$EXITED_SUCCESSFULLY" -lt 1 ]; then add_fail exited_successfully; fi` line; `EXITED_SUCCESSFULLY` is still counted and written to `cycle-<label>.env`, just no longer a fail reason
- Set `VERDICT_WRITTEN=1` immediately before each of the two verdict appends to `state.env`, so the EXIT trap can tell a completed verdict from an interrupted run
- Rewrote the header comment: removed "Exited successfully" from the PASS-requires sentence, added a "Recorded only" paragraph (naming `EXITED_SUCCESSFULLY`, `STOPPED_DURING_SHUTDOWN`, `ERROR_LINES`, `RESTART_ELAPSED_S`) with the baseline justification (`BASELINE_EXITED_SUCCESSFULLY=0`), documented the two new `state.env` line shapes, and documented detached use (`nohup ... > run-<label>.out 2>&1 < /dev/null &`, poll `state.env`)
- Proved the INCOMPLETE trap locally with a fake `PATH` (stub `sudo` that sleeps 3s standing in for a slow restart, stub `curl` that exits 0, no `jq` override needed since the `null`-fallback path tolerates a missing/failing `jq`): sending `SIGTERM` 1s into the fake restart produced exit code 130, `state.env` with `CYCLE_SMOKE_STARTED=2026-10-26T18:25:32Z` and exactly one `CYCLE_SMOKE=INCOMPLETE:restart` line, and the out file containing `STEP restart 2026-10-26T18:25:32Z` and `CYCLE SMOKE INCOMPLETE restart`. The missing `LOG` path on the Mac produced the expected "No such file or directory" (non-fatal, script continued past it to the restart step), confirmed in the out file.

## Task Commits

Both tasks landed in a single commit, per the plan's own sequencing (Task 2's action explicitly runs the smoke test first, then commits the harness once proven):

1. **Task 1: Add STARTED marker, INCOMPLETE trap, progress lines, restart timing; make Exited successfully recorded-only** - combined into commit below
2. **Task 2: Local smoke test of the INCOMPLETE trap (fake PATH, no NAS) and commit** - `5ce19b6` (docs)

`docs(123-09): make the restart-cycle harness resumable and record Exited successfully as informational` - `5ce19b6`

## Files Created/Modified
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh` - STARTED marker, INCOMPLETE EXIT trap, STEP progress lines, RESTART_ELAPSED_S, Exited-successfully demoted to recorded-only, header rewritten

## Smoke Test Evidence (Task 2)

Fake PATH directory held two stubs (`sudo` -> `exec sleep 3`; `curl` -> `exit 0`); ran `bash 123-restart-cycle.sh "$T/D" SMOKE idle` backgrounded, sent `SIGTERM` after 1s, then `wait`'d. Exit code: `130`.

`$T/D/state.env`:
```
CYCLE_SMOKE_STARTED=2026-10-26T18:25:32Z
CYCLE_SMOKE=INCOMPLETE:restart
```

`$T/out` (last lines):
```
STEP pre_scan 2026-10-26T18:25:32Z
STEP marker 2026-10-26T18:25:32Z
.../123-restart-cycle.sh: line 106: /volume1/docker/v5test/seedsyncarr/log/seedsyncarr.log: No such file or directory
STEP restart 2026-10-26T18:25:32Z
CYCLE SMOKE INCOMPLETE restart
```

The temp directory was removed after the test. No NAS or docker was touched; only the fake `sudo`/`curl` stubs ran.

## Decisions Made
- Exited successfully stays counted (`EXITED_SUCCESSFULLY`) but moves to recorded-only, per the plan's explicit instruction, justified in the header with the 1.7.6 baseline evidence (`BASELINE_EXITED_SUCCESSFULLY=0`) and the `src/python/seedsyncarr.py:669` logging-only-after-full-shutdown mechanism from 123-LIFE-EVIDENCE.md
- All other D-01 pass/fail criteria (scanner_died, could_not_terminate, caught_exception_in_job, error_stopping, restart_rc, starting, ready, scan, rotated) are unchanged -- verified by grep counts in the acceptance checks below

## Deviations from Plan

None - plan executed exactly as written. Both tasks' commits were combined into one, as the plan itself specifies (Task 2's action text says "Commit the harness" as the single commit point after the smoke test, not a separate Task 1 commit).

## Issues Encountered

None. The expected `wc -l: No such file or directory` on the nonexistent Mac log path appeared and did not stop the script before the restart step, exactly as anticipated in the plan's `<action>` note.

## Verification (all commands actually run; outputs observed, not assumed)

- `bash -n 123-restart-cycle.sh` -> passed, no output (clean)
- `grep -v '^#' 123-restart-cycle.sh | grep -c -F "add_fail exited_successfully"` -> `0`
- `grep -v '^#' 123-restart-cycle.sh | grep -c -F "add_fail scanner_died"` -> `1`; `could_not_terminate` -> `1`; `caught_exception_in_job` -> `1`; `error_stopping` -> `1`; `restart_rc` -> `1` (all five D-01 criteria unchanged)
- `grep -c -F "INCOMPLETE:" 123-restart-cycle.sh` -> `3`
- `grep -c -F "_STARTED=" 123-restart-cycle.sh` -> `2`
- `grep -c -F "VERDICT_WRITTEN=1" 123-restart-cycle.sh` -> `2`
- `grep -c -F "RESTART_ELAPSED_S" 123-restart-cycle.sh` -> `5`
- `grep -c -F "seedsyncarr " 123-restart-cycle.sh` -> `0` (production never named)
- `grep -c -F "Recorded only" 123-restart-cycle.sh` -> `1`; `grep -c -F "BASELINE_EXITED_SUCCESSFULLY" 123-restart-cycle.sh` -> `1`
- `git log -1 --format=%s` -> `docs(123-09): make the restart-cycle harness resumable and record Exited successfully as informational`
- `git show --stat --format= HEAD` -> only `.planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh` (62 insertions, 4 deletions)
- `git diff HEAD~1 --name-only -- src/` -> empty (no product code touched)
- `git diff --diff-filter=D --name-only HEAD~1 HEAD` -> empty (no unintended deletions)
- Smoke test exit code -> `130`; `state.env` and out-file contents quoted above, matched exactly

## User Setup Required

None - no external service configuration required. This plan is local-only (no NAS, no docker, no ssh), as required by the orchestrator amendment and parallel-execution constraints.

## Next Phase Readiness

The hardened harness is committed and ready for the gap round's live cycles (123-11/123-12), which can now launch it with `nohup ... &` and poll `state.env`/the out file for progress without hitting the 600s-watchdog stall seen in 123-06. The D-01 shutdown-error criteria that actually gate pass/fail are unchanged, so prior live evidence interpretation (123-06, 123-LIFE-EVIDENCE.md) remains valid; only the "Exited successfully" bookkeeping and the resumability mechanics changed.

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*

## Self-Check: PASSED

- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh" ]` -> FOUND
- `git log --oneline --all | grep -q "5ce19b6"` -> FOUND
