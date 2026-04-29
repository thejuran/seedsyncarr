---
phase: 88-python-test-fixes-medium-cleanup
plan: "02"
subsystem: python-tests
tags: [test-quality, busy-wait, cpu-starvation, race-condition, handler-leak]
dependency_graph:
  requires: []
  provides: [PYFIX-12, PYFIX-16, PYFIX-18]
  affects:
    - src/python/tests/unittests/test_controller/test_scan/test_scanner_process.py
    - src/python/tests/unittests/test_lftp/test_lftp.py
tech_stack:
  added: []
  patterns:
    - "time.sleep(0.01) busy-wait yield pattern"
    - "self._test_handler instance variable for tearDown cleanup"
key_files:
  created: []
  modified:
    - src/python/tests/unittests/test_controller/test_scan/test_scanner_process.py
    - src/python/tests/unittests/test_lftp/test_lftp.py
decisions:
  - "Use time.sleep(0.01) (10ms) as the standard CPU yield duration in busy-wait loops"
  - "Place sleep as last statement in loop body, after all break checks, so it only runs when looping continues"
  - "Track handler as self._test_handler instance variable so tearDown can remove it"
metrics:
  duration: "~12 minutes"
  completed: "2026-04-25T02:42:12Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 88 Plan 02: Scanner + LFTP Busy-Wait CPU Fix and Handler Leak Fix Summary

**One-liner:** Added `time.sleep(0.01)` to 47 busy-wait loops (6 scanner + 41 lftp) to prevent CPU starvation, and fixed logger handler accumulation across 40+ lftp tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Scanner busy-wait fix + test_lftp handler cleanup (PYFIX-12 + PYFIX-16) | 967699f | test_scanner_process.py, test_lftp.py |
| 2 | Lftp busy-wait sleep injection — 41 loops (PYFIX-18) | 2ff698d | test_lftp.py |

## What Was Built

**PYFIX-12 (scanner busy-wait):** `test_scanner_process.py` had 4 counter-based busy-wait loops using bare `pass` (`while self.scan_counter.value < N: pass`) and 2 result-based loops (`while True: ... if result: break`). All 6 replaced/augmented with `time.sleep(0.01)` to yield the GIL so the worker process can increment the multiprocessing.Value counter. Added `import time`.

**PYFIX-16 (test_lftp handler leak):** `test_lftp.py` setUp added a `logging.StreamHandler` to the root logger on every test run but never removed it. Changed `handler` local variable to `self._test_handler` instance variable, then added `logging.getLogger().removeHandler(self._test_handler)` as the first line of `tearDown`. This prevents handler count from accumulating to 40+ across the test class.

**PYFIX-18 (lftp busy-wait):** `test_lftp.py` had 41 `while True:` polling loops that spun at 100% CPU waiting for `self.lftp.status()` to return results. Each loop now has `time.sleep(0.01)` as the last statement before the loop repeats (placed after all `if condition: break` checks). The transformation was applied via a Python script to ensure consistent placement across all 41 loops. Added `import time`.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `time.sleep(0.01)` (10ms) | Sufficient to yield CPU without meaningfully slowing tests (41 loops x ~2 iterations x 10ms = ~0.8s, well within 5s timeout) |
| Sleep placed AFTER all break checks | Unreachable sleep after break would be a bug; sleep before break would add latency on every iteration including the final one |
| Python script for bulk loop transformation | 41 loops with identical surrounding context would make Edit tool matches non-unique; script approach is deterministic and verifiable |
| `self._test_handler` instead of `logging.getLogger().handlers[-1]` in tearDown | Instance variable is explicit; index-based approach fragile if other handlers added |

## Deviations from Plan

None — plan executed exactly as written. The Python script approach for Task 2 was used instead of individual Edit calls due to 41 near-identical loop bodies that would fail non-unique match requirements, but the semantic outcome is identical to what the plan specified.

## Verification

- `grep -c "time.sleep(0.01)" test_scanner_process.py` → **6** (acceptance: 6)
- `grep -c "while True:" test_lftp.py` → **41** (unchanged)
- `grep -c "time.sleep(0.01)" test_lftp.py` → **41** (acceptance: 41)
- `grep -c "removeHandler(self._test_handler)" test_lftp.py` → **1** (acceptance: 1)
- No bare `pass` statements remain in while loop bodies in either file
- `import time` present in both files

## Known Stubs

None.

## Threat Flags

None — test-only changes with no production code, network surfaces, or trust boundary crossings.

## Self-Check: PASSED

- `test_scanner_process.py` exists and has 6 `time.sleep(0.01)` calls: CONFIRMED
- `test_lftp.py` exists and has 41 `time.sleep(0.01)` calls: CONFIRMED
- Task 1 commit `967699f` exists: CONFIRMED
- Task 2 commit `2ff698d` exists: CONFIRMED
