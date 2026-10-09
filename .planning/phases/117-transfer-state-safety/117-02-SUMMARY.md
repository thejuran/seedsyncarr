---
phase: 117-transfer-state-safety
plan: 02
subsystem: controller/auto-queue tests
tags: [python, pytest, auto-queue, stability-clock, regression, red-first]
requires: []
provides:
  - "RED regressions for XFER-04 (remote clock) and XFER-05 (local clock) — failed scans advancing stability"
  - "AutoQueue harnesses initialise latest_successful_{remote,local}_scan_time = None"
  - "failed= kwarg on TestAutoQueueStabilityAndSweep._set_scan and TestAutoQueueLocalStabilityGate._cycle"
affects:
  - "Plan 117-06 (moves AutoQueue stability onto successful-scan clocks; must turn these 8 tests green)"
tech-stack:
  added: []
  patterns:
    - "Composed write-path/read-path test: Controller.__new__ + real Status shared with AutoQueue"
key-files:
  created:
    - src/python/tests/unittests/test_controller/test_scan_clock_safety.py
  modified:
    - src/python/tests/unittests/test_controller/test_auto_queue.py
    - src/python/tests/unittests/test_controller/test_controller_unit.py
decisions:
  - "Composed tests assert only on queue commands and existing UI clock fields; never read latest_successful_* (keeps RED as AssertionError, not AttributeError)"
metrics:
  duration: "~15 min"
  completed: 2026-10-08
  tasks: 3
  files: 3
requirements: [XFER-04, XFER-05]
---

# Phase 117 Plan 02: B3 Stability-Clock RED Regressions Summary

Failing unit and composed (Controller -> real Status -> AutoQueue) tests proving that failed remote and local scans currently advance the auto-queue stability clocks, plus harness changes that keep Plan 06's clock-source switch from reading MagicMock clocks or hitting AttributeError.

**The suite is intentionally red (8 failures) until Plan 06 lands.**

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Initialise new clock fields in every AutoQueue harness; add `failed=` to `_set_scan`/`_cycle` | 3442fd5 |
| 2 | D-03/D-04/D-05 remote and local unit cases (4 RED, 2 preservation) | dcbe69a |
| 3 | Composed `test_scan_clock_safety.py` (4 RED, 2 preservation) | 3ee2a0f |

## Verification (observed)

Task 1: `test_auto_queue.py` + `test_controller_unit.py` -> `210 passed` (no change from before); whole-tree `ruff check` -> `All checks passed!`.

Final plan verification: `pytest test_auto_queue.py test_scan_clock_safety.py test_controller_unit.py -q -rf --tb=line` -> `8 failed, 214 passed`. Short summary verbatim:

```
FAILED tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_changed_size_after_remote_outage_restarts_window
FAILED tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_failed_remote_scans_spanning_window_do_not_establish_stability
FAILED tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_changed_local_size_after_outage_restarts_window
FAILED tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_failed_local_scans_spanning_window_do_not_establish_local_idle
FAILED tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_failed_local_scans_spanning_window_do_not_queue
FAILED tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_failed_remote_scans_spanning_window_do_not_queue
FAILED tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_local_recovery_with_changed_size_restarts_window
FAILED tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_remote_recovery_with_changed_size_restarts_window
8 failed, 214 passed, 3 warnings in 0.86s
```

All 8 failures are `AssertionError: 0 != 1` on the queued-command count, observed with `--tb=short`, at exactly the predicted point: remote cases at `t=90` (= W), local cases at `t=30` (= W). (This pytest version's `-rf --tb=line` summary does not print the exception text, so the reason was checked separately.) The 4 preservation tests (`*_is_stable`, `*_is_idle`, `*_matching_size_queues` x2) pass. All existing tests pass. Whole-tree ruff: `All checks passed!`. No production source modified (`git status` shows only test files).

## Deviations from Plan

- **Commit granularity:** the plan asked for a single commit `test(117-02): add failing B3 stability-clock regressions (RED)`. The orchestrator asked for one commit per task, so this plan has three commits. The final commit uses the plan's message. All three commits contain test files only.
- **Helper ordering:** in `_set_scan`/`_cycle`, clock writes now happen before the model update, so the `failed=True` path can return early. This has no effect on behavior because `process()` is only called after the helper returns. All existing tests still pass.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/python/tests/unittests/test_controller/test_scan_clock_safety.py
- FOUND commits: 3442fd5, dcbe69a, 3ee2a0f
