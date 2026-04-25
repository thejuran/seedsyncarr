---
phase: 87-python-test-fixes-critical-warning
plan: "01"
subsystem: python-tests
tags: [test-quality, false-coverage, resource-leak, mock-guard]
dependency_graph:
  requires: []
  provides: [PYFIX-01, PYFIX-02, PYFIX-03, PYFIX-04, PYFIX-05]
  affects: [python-test-suite]
tech_stack:
  added: []
  patterns: [addCleanup-lifo, thread-callable-target, assertNotEqual-mock-guard]
key_files:
  created: []
  modified:
    - src/python/tests/unittests/test_controller/test_extract/test_extract_process.py
    - src/python/tests/unittests/test_controller/test_lftp_manager.py
    - src/python/tests/unittests/test_common/test_config.py
    - src/python/tests/unittests/test_web/test_handler/test_status_handler.py
decisions:
  - "PYFIX-01: remove () after _callback_sequence to pass callable not result to threading.Thread"
  - "PYFIX-04: addCleanup registered in LIFO order (remove second, close first) so file is closed before removal"
metrics:
  duration: 264s
  completed_date: "2026-04-25"
  tasks_completed: 2
  files_modified: 4
---

# Phase 87 Plan 01: Python Test Fixes — Critical and Warning Summary

**One-liner:** Fixed 2 critical false-coverage bugs (thread callable bug, assertion-less test) and 3 warning-level issues (temp file leaks, missing mock guards) across 4 test files.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix critical false-coverage bugs (PYFIX-01 + PYFIX-02) | 7a06112 | test_extract_process.py, test_lftp_manager.py |
| 2 | Fix temp file leaks and mock guard (PYFIX-03 + PYFIX-04 + PYFIX-05) | 4c70437 | test_config.py, test_status_handler.py |

## Changes Made

### PYFIX-01 — Thread callable target (test_extract_process.py:182)

Removed `()` after `_callback_sequence` in `threading.Thread(target=_callback_sequence).start()`. The original code called the function synchronously and passed `None` as the thread target, meaning the background thread body never ran. The busy-wait loops at lines 188 and 198 would block forever if the test ever ran without the coincidental timing covering it.

### PYFIX-02 — Explicit assertion in test_init_skips_rate_limit_when_zero (test_lftp_manager.py)

Replaced `pass  # No assertion needed` with `self.assertNotEqual(mock_lftp.rate_limit, 0)`. MagicMock auto-attributes are MagicMock objects (never `0`), so this assertion verifies that production code did not assign `rate_limit = 0` to the mock. Previously the test provided zero coverage of the rate-limit-skip branch.

### PYFIX-03 — Temp file cleanup in test_to_file (test_config.py)

Added `self.addCleanup(os.remove, config_file_path)` immediately after the `NamedTemporaryFile` creation. File handle is already closed (only `.name` is retained), so only `os.remove` cleanup is needed.

### PYFIX-04 — Temp file cleanup in test_from_file (test_config.py)

Added `self.addCleanup(os.remove, config_file.name)` and `self.addCleanup(config_file.close)` in LIFO order immediately after `NamedTemporaryFile` creation (close registered last so it runs first). Removed the old end-of-body `config_file.close()` / `os.remove(config_file.name)` lines that were skipped whenever any assertion before them failed.

### PYFIX-05 — Mock call guard assertions (test_status_handler.py)

Added `mock_serialize_cls.status.assert_called_once_with(self.mock_status)` to the end of `test_get_status_returns_200` and `test_get_status_body_is_serialized`. The third test already had this assertion. This ensures all three tests verify the serializer class method was called with the correct argument, guarding against class-vs-instance call regressions.

## Verification

All 5 success criteria confirmed:

1. `threading.Thread(target=_callback_sequence).start()` at line 182 (no `()`)
2. `self.assertNotEqual(mock_lftp.rate_limit, 0)` replaces `pass`
3. `self.addCleanup(os.remove, config_file_path)` in test_to_file
4. `addCleanup` LIFO pair in test_from_file, old end-of-body cleanup removed
5. 3 occurrences of `assert_called_once_with(self.mock_status)` in test_status_handler.py
6. `make run-tests-python`: 1200 passed, 71 skipped, exit 0

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — test-only changes, no production code modified, no new network surfaces introduced.

## Self-Check: PASSED

- `7a06112` exists: confirmed via `git log`
- `4c70437` exists: confirmed via `git log`
- All 4 modified files exist at their paths
- `grep -c "assert_called_once_with" test_status_handler.py` = 3
- `grep -c "self.addCleanup(os.remove" test_config.py` = 2
- Test suite: 1200 passed, 71 skipped, 0 failures
