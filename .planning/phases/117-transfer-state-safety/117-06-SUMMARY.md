---
phase: 117-transfer-state-safety
plan: 06
subsystem: controller/auto-queue
tags: [python, auto-queue, stability-clock, controller-status, b3]
requires: ["117-03"]
provides:
  - "ControllerStatus.latest_successful_remote_scan_time / latest_successful_local_scan_time (non-serialized)"
  - "AutoQueue stability measured on successful-scan clocks only"
affects: [controller, auto_queue, status]
tech-stack:
  added: []
  patterns: ["success-only clock written under `not scan.failed` (mirrors ModelPipeline idiom)"]
key-files:
  created: []
  modified:
    - src/python/common/status.py
    - src/python/controller/controller.py
    - src/python/controller/auto_queue.py
    - src/python/tests/unittests/test_common/test_status.py
    - src/python/tests/unittests/test_controller/test_controller.py
    - src/python/tests/unittests/test_web/test_serialize/test_serialize_status.py
decisions:
  - "B3 success clocks live on ControllerStatus (not AutoQueue-internal tracking), matching AutoQueue's existing status-clock read pattern"
  - "REQUEUE cooldown stays on the UI remote clock (latest_remote_scan_time): it is a retry throttle, not a safety gate"
metrics:
  duration: "~15 min"
  completed: 2026-10-08
requirements: [XFER-04, XFER-05]
---

# Phase 117 Plan 06: Successful-scan stability clock (B3) Summary

AutoQueue remote size-stability and local idle-stability now advance only on scans that did not fail. Two new ControllerStatus fields hold the timestamp of the latest successful remote and local scan. The controller writes them only when `not scan.failed`. They are not serialized, so the SSE payload and the UI "last scan" fields are unchanged.

## What changed

- `common/status.py`: `ControllerStatus` gains `latest_successful_local_scan_time` and `latest_successful_remote_scan_time`. Both default to None.
- `controller/controller.py`: `_update_controller_status` still writes the UI fields from every scan. It now also sets each success clock under `if not remote_scan.failed:` / `if not local_scan.failed:`. The docstring is updated to match.
- `controller/auto_queue.py`: `process()` now reads `remote_stable_time` and `local_stable_time` from the success clocks. These feed `__update_remote_size_history`, `__update_local_idle_history` and both gates in `sweep_accept`. `scan_time`, the UI remote clock, is now used only by the cooldown block, which is unchanged. The unused `latest_local_scan_time` read is removed. The class docstring and the process comment now describe the D-03 and D-04 rules and why the cooldown stays on the UI clock.
- Tests:
  - `test_status.py` defaults now cover both success clocks.
  - New `TestUpdateControllerStatusSuccessClocks` has 6 tests built on real `ScannerResult` objects: remote and local success, failure after success, failed first scans, and None scans.
  - New `test_controller_status_keys_unchanged_by_success_clocks` pins the SSE controller key set and checks that no `latest_successful` text appears in the payload.

## Verification (observed)

- Task 1: `test_status.py`, `test_controller.py` and `test_controller_unit.py` gave **183 passed**. Whole-tree ruff: `All checks passed!`
- Task 2: `test_auto_queue.py`, `test_scan_clock_safety.py` and `test_controller_unit.py` gave **222 passed**. The 8 B3 tests (`-k "outage or spanning_window"`) gave **8 passed**. They cover the 4 AutoQueue outage/restart tests and the 4 composed tests in `test_scan_clock_safety.py`. Their RED state against unfixed code is recorded in `117-REL01-EVIDENCE.md` (Plan 03). Ruff clean.
- Task 3: the five listed files gave **149 passed**. After the final amend, those five plus `test_controller_unit.py` gave **283 passed**. Ruff clean.
- Phase quick run (Plan 03 file set): **18 failed, 479 passed**, down from the RED baseline of 26 failed. The fix accounts for the 8-test drop. Every one of the 18 remaining failures belongs to another plan:
  - `test_job_status_parser.py`: 5 (Plan 04)
  - `test_lftp_status_contract.py`: 4 (Plan 05)
  - `test_transfer_state_safety.py`: 9 (Plans 05/08)
- The commit touches exactly the six `files_modified`. `serialize_status.py` is not in the commit.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1-3 | 7cfa98f | fix(117-06): measure auto-queue stability on the successful-scan clock only (B3) |

## Deviations from Plan

- **Single commit for all three tasks.** The plan's Task 3 action and acceptance criteria require one commit containing exactly six files. I followed the plan rather than the executor's default of one commit per task. Each task's verify command was run and passed before the commit.
- **Amended once.** At first the two `_create_property(` calls were wrapped over two lines, which made the acceptance grep `_create_property("latest_successful_` return 0. I put them back on one line (ruff stays clean) and amended my own, unpushed commit so the single-commit, six-file criterion still holds.
- **Extra test.** `TestUpdateControllerStatusSuccessClocks` has 6 tests, more than the 4 required. The extra case is "failed first scans leave success clocks None".

## Decisions

- **Where the success clocks live:** on ControllerStatus, not tracked inside AutoQueue. This was the discretion choice. AutoQueue already reads its clocks from status, and because model sizes only change on successful scans, D-04 (restart the window when the size changes on recovery) needs no extra logic.
- **Cooldown clock:** stays on `latest_remote_scan_time`. It throttles retries for a file stuck in DEFAULT and is not a safety gate. Moving it to the success clock would freeze retries during a scanner outage for no safety benefit (RESEARCH Anti-Patterns, assumption A3).

## Threat Flags

None. No new endpoints or serialized fields. T-117-04 and T-117-05 are mitigated as planned.

## Self-Check: PASSED

- All six modified files exist and are in commit 7cfa98f.
- Commit 7cfa98f is present on branch worktree-agent-ab1f083670e9f7e0d.
