---
phase: 87-python-test-fixes-critical-warning
plan: 02
subsystem: python-tests
tags: [test-quality, resource-safety, chmod, logger, imports, context-manager]
dependency_graph:
  requires: []
  provides: [PYFIX-06, PYFIX-07, PYFIX-08, PYFIX-09, PYFIX-10]
  affects: [src/python/tests]
tech_stack:
  added: []
  patterns: [context-manager-for-file-handles, explicit-mock-imports, fixture-teardown-reset]
key_files:
  created: []
  modified:
    - src/python/tests/unittests/test_lftp/test_lftp.py
    - src/python/tests/conftest.py
    - src/python/tests/unittests/test_controller/test_auto_queue.py
    - src/python/tests/integration/test_web/test_handler/test_stream_model.py
    - src/python/tests/unittests/test_web/test_handler/test_server_handler.py
    - src/python/tests/integration/test_controller/test_extract/test_extract.py
    - src/python/tests/integration/test_controller/test_controller.py
decisions:
  - "Wrapped both rar subprocess calls in single with open(os.devnull) context in test_extract.py since fnull was shared across both calls"
metrics:
  duration: "5 minutes"
  completed: "2026-04-24"
---

# Phase 87 Plan 02: Warning-Level Python Test Fixes Summary

Fix 5 warning-level Python test defects across 7 files: chmod scope escalation to /tmp (PYFIX-06), logger fixture handler/propagation leak (PYFIX-07), implicit ANY imports in 3 files (PYFIX-08), bare open(os.devnull) in 2 integration tests (PYFIX-09), bare open() in create_large_file helper (PYFIX-10).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix chmod scope, logger fixture, and implicit imports (PYFIX-06/07/08) | d82c39a | test_lftp.py, conftest.py, test_auto_queue.py, test_stream_model.py, test_server_handler.py |
| 2 | Fix integration test resource leaks (PYFIX-09/10) | 8734994 | test_extract.py, test_controller.py |

## What Was Built

### PYFIX-06: chmod scope reduced to leaf directory
`test_lftp.py` `setUpClass` previously called `TestUtils.chmod_from_to(TestLftp.temp_dir, tempfile.gettempdir(), 0o775)` which walked UP ancestor directories (including `/tmp`) and granted them group-write. Replaced with `os.chmod(TestLftp.temp_dir, 0o750)` — only the leaf test temp directory is chmod'd.

### PYFIX-07: Logger fixture full teardown reset
`conftest.py` `test_logger` fixture now sets `logger.propagate = False` before `yield logger` (prevents double-logging to root logger during test) and after `logger.removeHandler(handler)` adds `logger.setLevel(logging.NOTSET)` and `logger.propagate = True` (fully resets logger state for subsequent tests).

### PYFIX-08: Explicit ANY imports in 3 files
All 3 files that used `unittest.mock.ANY` via side-effect import now have explicit `ANY` in their `from unittest.mock import` line:
- `test_auto_queue.py`: `from unittest.mock import MagicMock, ANY`
- `test_stream_model.py`: `from unittest.mock import patch, ANY`
- `test_server_handler.py`: `from unittest.mock import MagicMock, ANY`

### PYFIX-09: Context managers for os.devnull opens
- `test_extract.py`: Both `rar` and `rar split` subprocess calls now share a single `with open(os.devnull, 'w') as fnull:` context manager block
- `test_controller.py`: The `rar` branch `Popen` call now uses `with open(os.devnull, 'w') as fnull:`

### PYFIX-10: Context manager for create_large_file helper
`test_controller.py` `create_large_file` helper replaced `f = open / f.close()` pattern with `with open(_path, "wb") as f:`. The `print` statement moved outside the `with` block since it only needs the path.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one minor observation:

In `test_extract.py`, `fnull` was reused across both the `rar` and `rar split` subprocess.run calls. The plan's suggested replacement showed `ar_rar` assignment before the `with` block (correct) and a single call inside. I grouped both subprocess.run calls that shared `fnull` inside the same `with` context, which is idiomatic and correct Python — the handle stays open for both calls and closes cleanly after both complete.

## Verification Results

All plan verification checks passed:
- `grep -c "chmod_from_to" test_lftp.py` → 0
- `grep "os.chmod(TestLftp.temp_dir, 0o750)"` → matched
- `grep -c "propagate = False" conftest.py` → 1
- `grep -c "propagate = True" conftest.py` → 1
- All 3 PYFIX-08 files have `ANY` in import lines
- `grep -c "fnull = open"` in both integration files → 0
- `grep -c "f = open" test_controller.py` → 0
- `grep -c "with open" test_controller.py` → 15 (>= 2)

## Known Stubs

None.

## Threat Flags

None — all changes are test-layer only. PYFIX-06 reduces privilege scope (positive security change). No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

Files verified present:
- src/python/tests/unittests/test_lftp/test_lftp.py — FOUND
- src/python/tests/conftest.py — FOUND
- src/python/tests/unittests/test_controller/test_auto_queue.py — FOUND
- src/python/tests/integration/test_web/test_handler/test_stream_model.py — FOUND
- src/python/tests/unittests/test_web/test_handler/test_server_handler.py — FOUND
- src/python/tests/integration/test_controller/test_extract/test_extract.py — FOUND
- src/python/tests/integration/test_controller/test_controller.py — FOUND

Commits verified:
- d82c39a — FOUND (Task 1)
- 8734994 — FOUND (Task 2)
