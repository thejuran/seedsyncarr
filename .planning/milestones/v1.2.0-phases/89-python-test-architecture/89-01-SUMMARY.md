---
phase: 89-python-test-architecture
plan: "01"
subsystem: python-tests
tags: [refactoring, test-infrastructure, deduplication]
dependency_graph:
  requires: []
  provides: [helpers.py, base.py, test_lftp_protocol.py, _build_config_ini]
  affects: [conftest.py, test_controller_unit.py, test_auto_delete.py, test_config.py]
tech_stack:
  added: []
  patterns: [helper-backed-fixtures, shared-base-test-class, parameterized-ini-template]
key_files:
  created:
    - src/python/tests/helpers.py
    - src/python/tests/unittests/test_controller/base.py
    - src/python/tests/integration/test_lftp/test_lftp_protocol.py
  modified:
    - src/python/tests/conftest.py
    - src/python/tests/unittests/test_controller/test_controller_unit.py
    - src/python/tests/unittests/test_controller/test_auto_delete.py
    - src/python/tests/unittests/test_common/test_config.py
  deleted:
    - src/python/tests/unittests/test_lftp/test_lftp.py
decisions:
  - "3 encryption INI blocks kept inline because they test edge cases with intentionally missing sections (backward compat, non-boolean encryption, missing keyfile)"
  - "BaseAutoDeleteTestCase re-creates Controller in setUp after setting autodelete config on inherited mock_context"
metrics:
  duration: 17m
  completed: 2026-04-25T13:04:02Z
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 4
  files_deleted: 1
---

# Phase 89 Plan 01: Python Test Infrastructure Refactoring Summary

Extracted conftest fixtures to importable helpers, consolidated duplicated BaseControllerTestCase into shared base module, moved misclassified integration test to correct directory, and deduplicated INI config strings via parameterized template function.

## What Was Done

### Task 1: Create helpers.py, refactor conftest.py, extract BaseControllerTestCase

**Commit:** c034893

- Created `src/python/tests/helpers.py` with 3 importable factory functions:
  - `create_test_logger(name)` -- returns (logger, handler) tuple
  - `create_mock_context(logger=None)` -- returns MagicMock with 20+ config attributes
  - `create_mock_context_with_real_config(logger=None)` -- returns MagicMock with real Config()
- Refactored `conftest.py` to delegate all 3 pytest fixtures to helpers.py (thin wrappers)
- Removed `sys`, `MagicMock`, `Config` imports from conftest.py (now in helpers.py)
- Created `src/python/tests/unittests/test_controller/base.py` with `BaseControllerTestCase`:
  - 6 patches (ModelBuilder, LftpManager, ScanManager, FileOperationManager, MultiprocessingLogger, MemoryMonitor)
  - 3 helper methods (_make_controller_started, _add_file_to_model, _queue_and_process_command)
- Modified `test_controller_unit.py` to import BaseControllerTestCase from base.py
- Modified `test_auto_delete.py`: BaseAutoDeleteTestCase now inherits from BaseControllerTestCase with only auto-delete-specific overrides (removed ~50 lines of duplicated patch setup code)

### Task 2: Move misclassified test, extract INI template

**Commit:** ead4c33

- Moved `tests/unittests/test_lftp/test_lftp.py` (794 lines) to `tests/integration/test_lftp/test_lftp_protocol.py`
- Renamed class `TestLftp` to `TestLftpProtocol` (all internal references updated)
- Deleted original file; confirmed other files in `unittests/test_lftp/` remain intact
- Added `_build_config_ini()` parameterized template function at module level in test_config.py
  - 9 keyword parameters: webhook_secret, api_token, remote_password, sonarr_api_key, radarr_api_key, encryption_enabled, debug, verbose
  - Produces complete 10-section INI string
- Replaced 2 of 5 encryption test INI blocks with template calls
- 3 blocks kept inline: they test edge cases with intentionally missing sections (backward compat without Sonarr/Radarr/AutoDelete, non-boolean encryption value, missing keyfile with format strings)

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- `make run-tests-python`: 1201 passed, 71 skipped, 0 failures (exit 0)
- `grep -r "class BaseControllerTestCase" src/python/tests/`: exactly 1 result (in base.py)
- `grep -r "class BaseAutoDeleteTestCase" src/python/tests/`: shows inheritance from BaseControllerTestCase
- `test_lftp_protocol.py` exists at integration/test_lftp/ with class TestLftpProtocol
- Original `unittests/test_lftp/test_lftp.py` deleted
- `_build_config_ini` function exists (1 definition in test_config.py)
- `[General]` literal count in test_config.py reduced from 7 to 6 (1 in template, 5 inline -- 2 blocks replaced)

## Self-Check: PASSED

- [x] src/python/tests/helpers.py exists
- [x] src/python/tests/unittests/test_controller/base.py exists
- [x] src/python/tests/integration/test_lftp/test_lftp_protocol.py exists
- [x] src/python/tests/unittests/test_lftp/test_lftp.py deleted
- [x] Commit c034893 exists in git log
- [x] Commit ead4c33 exists in git log
- [x] All 1201 tests pass
