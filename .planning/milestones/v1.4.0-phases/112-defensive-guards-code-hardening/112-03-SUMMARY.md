---
phase: 112-defensive-guards-code-hardening
plan: "03"
subsystem: delete-worker
tags: [delete, logging, error-handling, log-injection, hardening, tdd]
requirements: [GUARD-03]

dependency_graph:
  requires: []
  provides:
    - GUARD-03: logged local rmtree failures via logger.exception
    - TestDeleteLocalProcess failure-path regression test
  affects:
    - src/python/controller/delete/delete_process.py
    - src/python/tests/unittests/test_controller/test_delete_process.py

tech_stack:
  added: []
  patterns:
    - "try/except OSError wrapping shutil.rmtree (3.11-safe, mirrors DeleteRemoteProcess precedent)"
    - "sanitize_log_value on filename in log call (SEC-01 convention, log-injection guard)"
    - "assertLogs failure-path regression test pattern (TestDeleteRemoteProcess analog)"

key_files:
  modified:
    - src/python/controller/delete/delete_process.py
    - src/python/tests/unittests/test_controller/test_delete_process.py

decisions:
  - "D-08: try/except OSError chosen over onerror= callback — cleaner, identical 3.11/3.12 compatibility"
  - "D-09: no re-raise — best-effort, non-fatal delete contract preserved, mirroring DeleteRemoteProcess"
  - "D-10: failure-path regression test added (TestDeleteLocalProcess); success-path tests pin unchanged contract"

metrics:
  duration_seconds: 165
  completed_date: "2026-06-02"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 112 Plan 03: GUARD-03 — Logged Local Delete Failures Summary

**One-liner:** Replace `shutil.rmtree(ignore_errors=True)` with `try/except OSError` + `logger.exception` (sanitized filename) in `DeleteLocalProcess.run_once`, adding a `TestDeleteLocalProcess` failure-path regression test via TDD.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing DeleteLocalProcess rmtree-failure test (RED) | af0a08c | test_delete_process.py |
| 2 | Replace ignore_errors=True with logged try/except OSError (GREEN, GUARD-03) | df35a2c | delete_process.py |

## What Was Built

**Task 1 (RED):** Added `TestDeleteLocalProcess(unittest.TestCase)` to `test_delete_process.py` with three tests:
- `test_local_delete_logs_rmtree_failure` — asserts `assertLogs("DeleteLocalProcess", level="ERROR")` captures a record when `shutil.rmtree` raises `OSError`. RED before Task 2 (assertLogs raised `AssertionError` because `ignore_errors=True` swallowed the error with no log output).
- `test_local_delete_file_success` — asserts `os.remove()` is called when `isfile` is `True`, `shutil.rmtree` is NOT called. PASS before and after Task 2 (pins unchanged file-branch contract).
- `test_local_delete_dir_success` — asserts `shutil.rmtree()` is called once for the directory branch with no ERROR log. PASS before and after Task 2 (pins unchanged dir-branch success contract).

**Task 2 (GREEN):** In `delete_process.py`:
- Extended `from common import AppOneShotProcess` to `from common import AppOneShotProcess, sanitize_log_value`
- Replaced `shutil.rmtree(file_path, ignore_errors=True)` (line 24) with:
  ```python
  try:
      shutil.rmtree(file_path)
  except OSError:
      self.logger.exception(
          "Failed to delete local directory: %s",
          sanitize_log_value(self.__file_name)
      )
  ```
- `%`-style lazy logging args; `except OSError` (not bare except, per CLAUDE.md); no re-raise; no `onexc=` (3.12+ only; runtime is 3.11-slim).

## Verification Results

- `ruff check .` (whole-tree from `src/python/`): All checks passed
- `pytest tests/unittests/test_controller/test_delete_process.py -v`: 7 passed (4 TestDeleteRemoteProcess + 3 TestDeleteLocalProcess)
- `grep -nE 'ignore_errors' controller/delete/delete_process.py`: no match (flag removed)
- `grep -n 'except OSError'`: line 26 (1 match)
- `grep -n 'sanitize_log_value'`: line 6 (import) and line 29 (log call)

## Deviations from Plan

None — plan executed exactly as written.

The `@patch` decorator order was confirmed as outside-in (last decorator = first positional arg after `self`) per Python's `unittest.mock` convention. Patches were applied at the global `shutil.rmtree` / `os.path.isfile` / `os.path.exists` / `os.remove` paths (not the module-local path) because `delete_process.py` uses the standard `import shutil` / `import os` module imports rather than `from shutil import rmtree`.

One ruff finding (`F841: Local variable logger assigned to but never used` in `test_local_delete_dir_success`) was caught during ruff check before the RED commit and removed inline — the `assertLogs` call does not require a logger reference.

## Known Stubs

None.

## Threat Flags

None. This plan only touches the local delete worker and its tests. No new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- [x] `src/python/controller/delete/delete_process.py` — FOUND (modified, contains `except OSError` and `sanitize_log_value`)
- [x] `src/python/tests/unittests/test_controller/test_delete_process.py` — FOUND (modified, contains `TestDeleteLocalProcess`)
- [x] RED commit `af0a08c` — FOUND in git log
- [x] GREEN commit `df35a2c` — FOUND in git log
