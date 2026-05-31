---
phase: 101-webhook-and-log-injection-security-cluster
plan: "05"
subsystem: controller/auto-delete + model/security
tags: [cwe-117, log-injection, sanitize, auto-delete, model, tdd]
dependency_graph:
  requires: [sanitize_log_value-helper, webhook-command-log-injection-closed]
  provides: [auto-delete-exit-model-log-injection-closed]
  affects: [101-06-PLAN]
tech_stack:
  added: []
  patterns: [log-output-only-sanitization, tdd-red-green]
key_files:
  created: []
  modified:
    - src/python/controller/controller.py
    - src/python/model/model.py
    - src/python/tests/unittests/test_controller/test_controller.py
    - src/python/tests/unittests/test_model/test_model.py
decisions:
  - "D-01: only the log variable is wrapped; scheduling dict keys, model __files keys, BFS, lookups, and persist values stay raw"
  - "D-02: apply helper only to provably remote-/user-tainted log sites (auto-delete timer cluster + model remote-scanner debug logs)"
  - "D-03 (re-evaluated): controller.py:229 is included (not deferred) — it logs a __pending_auto_deletes key, which is the scheduled remote-derived name populated at controller.py:817"
metrics:
  duration: "~7m"
  completed: "2026-05-31T22:51:00Z"
  tasks_completed: 2
  files_modified: 4
---

# Phase 101 Plan 05: Auto-Delete Timer + Model Log Injection Cluster (CWE-117) Summary

**One-liner:** Wrapped the 9 auto-delete timer/exit-cancel log sites in controller.py (lines 229/820/841/848/866/876/897/926/948) and the 3 model remote-scanner debug log sites in model/model.py (lines 81/97/112) with `sanitize_log_value()`, closing CWE-117 for the auto-delete→model taint lifecycle.

## What Was Built

Applied the shared `sanitize_log_value()` helper (built in Plan 01, imported in Plan 04) to the auto-delete timer cluster and model-layer debug log sinks — log sinks fed directly by remote-derived scheduled file names (lftp scan output via `root_name`) and by remote-scanner file names (fed from remote_scanner.py / system/file.py).

### controller.py (Sites 229/820/841/848/866/876/897/926/948)

The import `sanitize_log_value` on line 19 was already present from Plan 04 — reused without re-adding.

- **Site 229 (exit):** `"Canceled pending auto-delete for '{}'"` — logs a `__pending_auto_deletes` key = the scheduled remote-derived name. Previously deferred (D-03); re-evaluated as tainted (controller.py:817 ← 803-804 `root_name` taint chain). Wrapped: `sanitize_log_value(file_name)`.
- **Site 820 (`__schedule_auto_delete`):** `"Scheduled auto-delete of '{}' in {} seconds"` — first log of the remote-derived scheduled name. Wrapped: `sanitize_log_value(file_name)`.
- **Site 841 (`__execute_auto_delete` feature-disabled skip):** `"Auto-delete skipped for '{}': feature was disabled"`. Wrapped: `sanitize_log_value(file_name)`.
- **Site 848 (dry-run skip):** `"DRY-RUN: Would delete local file '{}'"`. Wrapped: `sanitize_log_value(file_name)`.
- **Site 866 (model-miss skip):** `"File '{}' no longer in model, skipping auto-delete"`. Wrapped: `sanitize_log_value(file_name)`.
- **Site 876 (state-guard skip):** `"Auto-delete skipped for '{}': file is in state {}"`. Wrapped: `sanitize_log_value(file_name)`.
- **Site 897 (BFS-limit skip):** `"Auto-delete skipped for '{}': BFS node limit ({}) exceeded"`. Wrapped: `sanitize_log_value(file_name)`.
- **Sites 926-927 (unsafe-child skip):** `"Auto-delete skipped for '{}': child '{}' is in state {}"` — interpolates both `file_name` and `unsafe_child.name` (a remote-scanner child name). Wrapped BOTH: `sanitize_log_value(file_name)` and `sanitize_log_value(unsafe_child.name)`.
- **Site 948 (partial-import skip):** `"Auto-delete skipped for '{}': partial import (...)"` — wrapped `file_name` only; the `shown` list of basenames and the numeric counts are left as-is per D-01.

All `__pending_auto_deletes` dict keys (lines 808-817), `model.get_file(file_name)` lookups (line 861), BFS traversal, `imported_children.pop(file_name)` (lines 904, 968), and all control flow stay RAW.

### model/model.py (Sites 81/97/112)

- Added `from common import AppError, sanitize_log_value` (model.py had no prior `sanitize_log_value` import; `common/types.py` has zero circular-import risk with model, per Plan 01 research).
- **Site 81 (`add_file`):** `"LftpModel: Adding file '{}'"` → `sanitize_log_value(file.name)`.
- **Site 97 (`remove_file`):** `"LftpModel: Removing file '{}'"` → `sanitize_log_value(filename)`.
- **Site 112 (`update_file`):** `"LftpModel: Updating file '{}'"` → `sanitize_log_value(file.name)`.

`self.__files[file.name]` storage keys, `del self.__files[filename]`, `get_file()` lookups, listener notifications (`file_added`, `file_removed`, `file_updated`) all keep the RAW name/filename.

### Tests Added

**test_controller.py (3 new tests in TestAutoDeleteLogSanitization):**
- `test_schedule_auto_delete_log_sanitized`: CRLF in file_name → no literal newline in "Scheduled auto-delete" log; `__pending_auto_deletes` still keyed by raw name
- `test_execute_auto_delete_skip_log_sanitized`: CRLF in file_name through feature-disabled skip branch → "feature was disabled" log is escaped
- `test_exit_cancel_log_sanitized`: CRLF-bearing key in `__pending_auto_deletes` → "Canceled pending auto-delete" log is escaped; dict cleared; timer canceled

**test_model.py (3 new tests in TestModelDebugLogSanitization):**
- `test_add_file_log_sanitized`: CRLF in file.name → "Adding file" log escaped; file stored/retrievable by raw name
- `test_remove_file_log_sanitized`: CRLF in filename → "Removing file" log escaped; removal still works on raw key
- `test_update_file_log_sanitized`: CRLF in file.name → "Updating file" log escaped; update still keyed on raw name

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | controller auto-delete + exit failing CWE-117 tests | 3c1b631 | test_controller.py |
| 1 GREEN | Sanitize auto-delete timer + exit-cancel log sites in controller.py | 45ff4bd | controller.py, test_controller.py (fixture fix) |
| 2 RED | model add/remove/update failing CWE-117 tests | 7035477 | test_model.py |
| 2 GREEN | Add sanitize_log_value to model.py + wrap 3 debug log sites | f64a874 | model.py |

## Deviations from Plan

**1. [Rule 1 - Bug] Test fixture missing exit() manager dependencies**

- **Found during:** Task 1 GREEN (test_exit_cancel_log_sanitized)
- **Issue:** `_make_controller_for_auto_delete` fixture did not include `__lftp_manager`, `__scan_manager`, or `__mp_logger` — `exit()` calls `.exit()` and `.stop()` on these after the timer-cancellation loop. The test failed with `AttributeError: 'Controller' object has no attribute '_Controller__lftp_manager'`.
- **Fix:** Added `MagicMock()` entries for all three managers in the fixture. The test was fixed in the same GREEN commit (not a plan deviation — the fixture was incomplete when written, corrected before any commit of the GREEN implementation).
- **Files modified:** `test_controller.py`
- **Commit:** 45ff4bd

Otherwise — plan executed exactly as written.

## Verification Results

Per-site gate results (all pass):

| Gate | Expected | Actual |
|------|----------|--------|
| controller all 9 message-anchor sites | sanitize_log_value present | PASS |
| `sanitize_log_value(unsafe_child.name)` | present | PASS |
| `sanitize_log_value(file_name)` count in controller.py | 10 | 10 |
| Total `sanitize_log_value` in controller.py (non-comment) | >=16 | 16 |
| model import `from common import .*sanitize_log_value` | present | PASS |
| model all 3 message-anchor sites (Adding/Removing/Updating) | sanitize_log_value present | PASS |
| `sanitize_log_value(file.name)` count in model.py | 2 | 2 |
| `sanitize_log_value(filename)` count in model.py | 1 | 1 |
| Total `sanitize_log_value` in model.py (non-comment) | >=4 | 4 |
| test_controller tests (incl. 3 new) | 27 pass | 27 pass |
| test_model tests (incl. 3 new) | 17 pass | 17 pass |
| Combined test_controller + test_model | 44 pass | 44 pass |

## TDD Gate Compliance

- RED gate Task 1: commit `3c1b631` — `test(101-05): add failing CWE-117 sanitization tests for auto-delete timer + exit-cancel log sites (RED)` — all 3 tests fail (literal newline in log output)
- GREEN gate Task 1: commit `45ff4bd` — `feat(101-05): sanitize auto-delete timer + exit-cancel log sites in controller.py (GREEN)` — 27 test_controller tests pass
- RED gate Task 2: commit `7035477` — `test(101-05): add failing CWE-117 sanitization tests for model add/remove/update debug log sites (RED)` — all 3 tests fail (literal newline in model log output)
- GREEN gate Task 2: commit `f64a874` — `feat(101-05): add sanitize_log_value import and wrap add/remove/update debug logs in model/model.py (GREEN)` — 17 test_model tests pass

## Known Stubs

None.

## Threat Flags

No new security surface introduced. This plan only wraps existing log sinks in a sanitizer. No new network endpoints, auth paths, file access patterns, or schema changes.

## Hand-off Note

After Plans 04 + 05, SEC-01 coverage spans: webhook/command cluster (04) + auto-delete timer/exit cluster + model remote-scanner debug logs (05). The lftp cluster (lftp/lftp.py kill + __run_command output sinks, lftp/job_status_parser.py:724/725) is addressed by Plan 06. No site in Plans 04 or 05 mutates scheduling/model/persist keys — the log-output-only invariant (D-01) is fully enforced.

## Self-Check: PASSED

- [x] `src/python/controller/controller.py` — `sanitize_log_value(file_name)` count = 10; `sanitize_log_value(unsafe_child.name)` present; >=16 total
- [x] `src/python/model/model.py` — `from common import AppError, sanitize_log_value` present; `sanitize_log_value(file.name)` = 2; `sanitize_log_value(filename)` = 1
- [x] `src/python/tests/unittests/test_controller/test_controller.py` — contains `TestAutoDeleteLogSanitization` with 3 methods
- [x] `src/python/tests/unittests/test_model/test_model.py` — contains `TestModelDebugLogSanitization` with 3 methods
- [x] Commit 3c1b631 exists (Task 1 RED)
- [x] Commit 45ff4bd exists (Task 1 GREEN)
- [x] Commit 7035477 exists (Task 2 RED)
- [x] Commit f64a874 exists (Task 2 GREEN)
- [x] 44 tests pass in test_controller.py + test_model.py combined
