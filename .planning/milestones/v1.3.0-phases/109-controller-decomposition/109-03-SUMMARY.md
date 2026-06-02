---
phase: 109-controller-decomposition
plan: 03
subsystem: controller
tags: [python, refactor, decomposition, model-pipeline, god-class, arch-01]

requires:
  - phase: 109-02
    provides: controller.py baseline (~975 lines) after AutoDeleteManager extraction
  - phase: 109-01
    provides: CommandProcessor collaborator extracted first

provides:
  - ModelPipeline collaborator in controller/model_pipeline.py (295 lines) with scan->build->diff->apply pipeline LOGIC
  - controller.py thinned from 975 to 757 lines; 9 test-pinned helpers kept as forwarding wrappers
  - ModelPipeline export from controller/__init__.py
  - ARCH-01 satisfied: controller.py coordinator/facade from 1150 to 757 lines total; three collaborators extracted

affects:
  - Phase 109 ARCH-01 complete: all three collaborators extracted (command_processor, auto_delete_manager, model_pipeline)

tech-stack:
  added: []
  patterns:
    - "ModelPipeline construction-injection pattern: receives already-constructed model, model_builder, scan_manager, lftp_manager, file_op_manager, persist, context from Controller.__init__; single-underscore fields only"
    - "model_lock single-underscore storage (self._model_lock): preserves identity with Controller._Controller__model_lock (D-03); with self._model_lock acquires the SAME lock object"
    - "update_model() returns 4-tuple (latest_remote_scan, latest_local_scan, lftp_statuses, latest_extract_statuses) so coordinator can call retained stages (_update_active_file_tracking, _update_controller_status) without re-collecting"
    - "Forwarding wrapper pattern: test-pinned helpers keep their def on Controller (callable name stays); only body moves to ModelPipeline. Eleven wrappers total: nine originally test-pinned + _set_import_status (discovered indirect coupling)"

key-files:
  created:
    - src/python/controller/model_pipeline.py
  modified:
    - src/python/controller/controller.py
    - src/python/controller/__init__.py

decisions:
  - "_update_active_file_tracking and _update_controller_status retained on Controller: _update_active_file_tracking writes __active_downloading_file_names (test-pinned field); _update_controller_status calls Controller._should_update_capacity (circular-import guard if moved)"
  - "__check_webhook_imports retained on Controller: test_controller.py:214,242 call c._Controller__check_webhook_imports() directly"
  - "_set_import_status kept as forwarding wrapper (not deleted): test_controller.py:212,240 assigns c._set_import_status = MagicMock() to intercept the __check_webhook_imports call path; plan grep missed this instance-attribute coupling pattern"
  - "update_model() returns 4-tuple (not 3-tuple): lftp_statuses added to return so coordinator does not need to re-call collect_lftp_status() for _update_active_file_tracking"

metrics:
  duration: "~65 minutes"
  completed: "2026-06-02T02:43:37Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 109 Plan 03: ModelPipeline Extraction Summary

One-liner: Extracted scan->build->diff->apply pipeline logic from Controller into ModelPipeline collaborator (295 lines), leaving 9 test-pinned one-line forwarding wrappers on Controller; full Docker suite 1343 passed / 0 failed.

## What Was Built

### Task 1: ModelPipeline collaborator (`model_pipeline.py`, 295 lines)

Created `src/python/controller/model_pipeline.py` defining `class ModelPipeline` modeled on `ScanManager` (construction-injection, one method per pipeline stage). The collaborator holds all scan->build->diff->apply pipeline logic:

- `update_model()`: public entry point returning 4-tuple `(remote_scan, local_scan, lftp_statuses, extract_statuses)` so the coordinator can call retained stages without re-collecting
- `collect_scan_results()`, `collect_lftp_status()`, `collect_extract_results()`: collection stage
- `feed_model_builder(...)`: feeds collected data to the model builder
- `detect_and_track_queued(diff)`, `detect_and_track_download(diff)`: file state tracking
- `prune_extracted_files()`, `_prune_downloaded_files(scan)`: pruning stage
- `apply_model_diff(diffs)`: diff application stage
- `build_and_apply_model(scan)`: builds new model and applies with `with self._model_lock` (SAME lock object, D-03)
- `_set_import_status(model, file_name)`: internal helper; also called via Controller forwarding wrapper

Key constraints honored:
- `self._model_lock` (single-underscore): same Lock object as `Controller.__model_lock` (D-03 / Pitfall 3)
- No manager construction, no new Lock, no runtime import of Controller (circular-import avoidance)
- `_set_import_status` intentional-protected-access comment (`_unfreeze()`) preserved verbatim

### Task 2: Controller wiring (`controller.py`, 757 lines)

Modified `Controller`:
- Added `from .model_pipeline import ModelPipeline` import
- Constructed `self.__model_pipeline = ModelPipeline(...)` with all already-built managers and `model_lock=self.__model_lock` (same object)
- Replaced 9 test-pinned helper bodies with one-line forwarding wrappers (callable names stay on Controller)
- Added `_set_import_status` forwarding wrapper (discovered indirect test coupling — see Deviations)
- Deleted `_prune_downloaded_files` def (zero test call sites confirmed)
- Thinned `__update_model` to delegate to `self.__model_pipeline.update_model()` + retained coordinator stages
- `__check_webhook_imports` updated to call `self._set_import_status(...)` (instance method, interceptable by test MagicMock)
- Removed unused `copy` import and `ModelDiffUtil` from import line

Line count journey: 1150 (pre-109) -> 1058 (after 109-01) -> ~975 (after 109-02) -> 757 (after 109-03). Materially fewer than the 1150 pre-109 baseline (ARCH-01 criterion #1).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_set_import_status` kept as forwarding wrapper (plan said delete)**
- **Found during:** Task 2, after first test run (2 failures)
- **Issue:** Plan's grep for test call sites only matched `controller._set_import_status(` (call pattern). The test at `test_controller.py:212,240` uses `c._set_import_status = MagicMock()` (instance attribute assignment) to intercept the call from `__check_webhook_imports` via `self._set_import_status(...)`. This indirect coupling was not caught by the plan's grep. After the body was deleted, `__check_webhook_imports` was calling `self.__model_pipeline._set_import_status(...)` on a Controller manually constructed via `__new__` (without `__model_pipeline`), raising `AttributeError`.
- **Fix:** Added `_set_import_status` as a forwarding wrapper on Controller (delegates to `self.__model_pipeline._set_import_status(...)`). `__check_webhook_imports` calls `self._set_import_status(...)` so the test MagicMock instance attribute intercepts it correctly.
- **Files modified:** `src/python/controller/controller.py`
- **Commit:** `4fb13b4`

## Regression Gate Results

Final Docker run: **1343 passed, 62 skipped, 0 failed** (`make run-tests-python`)
- Coverage `fail_under >= 88` threshold: passed
- All 9 test-pinned forwarding wrappers callable on Controller class
- `_update_active_file_tracking`, `_update_controller_status`, `_should_update_capacity`, `__check_webhook_imports` still defined on Controller
- No test file modified or deleted
- No file outside `src/python/controller/` changed

## Known Stubs

None. All implemented functionality is wired to real data sources through the existing manager instances.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This is a behavior-preserving structure-only refactor. CWE-117 `sanitize_log_value()` guards traveled with all moved log call sites.

## Self-Check: PASSED

- `src/python/controller/model_pipeline.py`: FOUND
- `src/python/controller/controller.py`: FOUND (757 lines)
- `109-03-SUMMARY.md`: FOUND
- Commit `0639221` (Task 1): FOUND
- Commit `4fb13b4` (Task 2): FOUND
- Docker suite: 1343 passed, 62 skipped, 0 failed
