---
phase: 123-startup-and-shutdown-lifecycle
plan: 06
subsystem: live-verification
tags: [nas-sandbox, docker-restart, d-01, d-07, live-check]
status: complete
check_status: FAIL
owner_decision: fix-in-phase

requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "05"
    provides: "Draft PR #137, CI run 407 green, DEV_PIN"
provides:
  - "Restart-cycle harness and SSA123 teardown helper (committed)"
  - "Live D-01 restart evidence on DEV_PIN: CHECK_STATUS=FAIL"
  - "Owner decision: fix-in-phase -> /bm:plan-phase 123 --gaps"

key-files:
  created:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-teardown.sh
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md

duration: ~70 min (executor stalled after the cycles; orchestrator finished diagnosis and the decision gate)
completed: 2026-10-26
---

# Phase 123 Plan 06: Live restart check Summary

**The live `docker restart` check on the PR #137 build failed. The false "Scanner process(es) died unexpectedly" ERROR still fires in 3 of 5 cycles, because the 123-04 one-cycle grace loses the race against the main thread's SIGTERM handler on the real NAS. The owner chose to fix it in this phase.**

## Tasks

| Task | Name | Commit | Outcome |
|------|------|--------|---------|
| 1 | Restart-cycle harness + SSA123 teardown helper | `bb7146f` | done |
| 2 | Re-pin sandbox to DEV_PIN, run I1, I2, A1, A2, I3 | (evidence commit with this SUMMARY) | cycles ran; CHECK_STATUS=FAIL; session teardown NOT run |
| 3 | Failure review (checkpoint:decision) | (this SUMMARY) | owner decision recorded |

## Results

Full per-cycle table and log timings: `123-LIFE-EVIDENCE.md` § "Sandbox re-pin (123-06)". NAS capture dir: `/volume1/docker/v5test/results/life01-123-20261025T185719Z` (mode 0700).

- I1, A1, A2: scanner ERROR plus `Caught exception in job ControllerJob`. In each case the scanners died 0.67–1.55 s before the main thread logged `Caught signal SIGTERM`.
- I2: the handler ran first. The scanners were logged at INFO `stopped during shutdown`, then `Exited successfully`. This is the intended behavior.
- A2: three lftp `Could not terminate the child` lines, after the scanner-error exit path.
- I3: no scanner error. `Exited successfully` is missing, but it is also missing in the 1.7.6 baseline, so this is pre-existing.

## Diagnosis

`ScanManager._check_process_health()` (src/python/controller/scan_manager.py) gives SIGTERM-killed scanners exactly one extra ControllerJob cycle (0.5 s, `Job._DEFAULT_SLEEP_INTERVAL_IN_SECS`) before raising. The docstring assumes the main thread's handler (`Seedsyncarr.signal()` -> `Controller.note_shutdown_requested()`) runs "a few milliseconds" after tini's group SIGTERM. Live, it ran up to 1.55 s later. A likely contributor is that CPython runs Python-level signal handlers only on the main thread, and the process-directed SIGTERM can land on any thread. The gap fix should not depend on that timing.

## Deviations / Issues

- The executor agent stalled (watchdog, 600 s without progress) while recalibrating the app-log vs NAS clock. That happened after all five cycles had run and CHECK_STATUS had been written. The orchestrator finished the diagnosis from the capture dir.
- No `CYCLE_I2=` line was written to state.env (the session was split). I2's window file and cycle-I2.env show a pass.
- **Session teardown was not run.** `SANDBOX_RESTORED ok` was never printed. No `SSA123.` name is under `/volume1/data/v5test/torrents`, but seedbox staging is not verified clean. The sandbox is still on DEV_PIN and healthy. The gap round must run the SSA123 teardown, and 123-07 must restore the sandbox with `--final`.
- Production fingerprint unchanged in both sessions.

## Owner decision (Task 3, verbatim)

"Fix in this phase (Recommended)". Option `fix-in-phase`. Route: `/bm:plan-phase 123 --gaps`. 123-07 must not mark the live check passed while this is open.
