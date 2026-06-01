---
phase: 107-mp-logger-spawn-safety
plan: "01"
subsystem: python-common
tags: [multiprocessing, spawn-safety, pickle, logging, infra]
requirements: [INFRA-01]

dependency_graph:
  requires: []
  provides:
    - MultiprocessingLogger spawn-picklable instance (__getstate__/__setstate__)
    - Spawn-compatible internal queue (get_context("spawn").Queue(-1))
    - Three analog tests exercising spawn path on all platforms with exitcode assertions
  affects:
    - src/python/common/multiprocessing_logger.py
    - src/python/tests/unittests/test_common/test_multiprocessing_logger.py

tech_stack:
  added: []
  patterns:
    - "spawn-context queue: multiprocessing.get_context('spawn').Queue(-1)"
    - "__getstate__/__setstate__ for spawn-picklable class instances"
    - "module-level picklable spawn targets (closure-to-module-scope promotion)"

key_files:
  created: []
  modified:
    - src/python/common/multiprocessing_logger.py
    - src/python/tests/unittests/test_common/test_multiprocessing_logger.py

decisions:
  - "Use name-mangled access _MultiprocessingLogger__mp_context in tests (consistent with existing precedent in the test file for __queue and __listener_shutdown)"
  - "__getstate__ uses dict(self.__dict__) + pop() pattern to return a filtered copy (never mutates self.__dict__)"
  - "__setstate__ explicitly sets the three dropped fields to None for safe accidental-read behavior"
  - "One shared module-level target _spawn_target_logger_levels serves all four sub-cases in test_logger_levels (bodies are identical)"
  - "Pre-existing test_app_process.py::test_process_with_long_running_thread_terminates_properly failure documented as deferred (out-of-scope, pre-existing before this plan)"

metrics:
  duration: "5 minutes"
  completed_date: "2026-06-01"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 107 Plan 01: MP-Logger Spawn Safety Summary

**One-liner:** Spawn-picklable MultiprocessingLogger via `__getstate__`/`__setstate__` + spawn-context queue, with three analog tests promoted to module-scope targets launched from the stored spawn context.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Spawn-safe queue context AND spawn-picklable instance | 5eb00ad | src/python/common/multiprocessing_logger.py |
| 2 | Promote three analog closures to module-scope spawn targets, launch via logger's spawn context, assert clean child exit | 67476dd | src/python/tests/unittests/test_common/test_multiprocessing_logger.py |

## What Was Built

### Task 1: Production Module Fix (`multiprocessing_logger.py`)

Three coupled changes to `MultiprocessingLogger.__init__` and two new methods:

1. **Spawn-context queue (D-01/D-02):** Added `self.__mp_context = multiprocessing.get_context("spawn")` before the queue line, then replaced `self.__queue = multiprocessing.Queue(-1)` with `self.__queue = self.__mp_context.Queue(-1)`. The spawn context's SemLock has `_is_fork_ctx=False`, which means it passes CPython's `SemLock.__getstate__` check for both fork and spawn children, eliminating the `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context`.

2. **`__getstate__` (SPAWN-PICKLE):** Returns a filtered copy of `self.__dict__` containing only the four child-side picklable fields (`logger`, `_MultiprocessingLogger__mp_context`, `_MultiprocessingLogger__queue`, `_MultiprocessingLogger__logger_level`) and excludes the three main-only unpicklable fields (`_MultiprocessingLogger__listener` threading.Thread, `_MultiprocessingLogger__listener_shutdown` threading.Event, `_MultiprocessingLogger__listener_exc_info`). Uses `dict(self.__dict__)` + `pop()` pattern for safety.

3. **`__setstate__` (SPAWN-PICKLE):** Restores the four child-side fields via `self.__dict__.update(state)` then explicitly sets the three dropped fields to `None` so any accidental child access returns a clean `None` (no missing-attribute error). The child only ever calls `get_process_safe_logger()`, which uses `self.__queue` + `self.__logger_level`.

All public API bodies (`start`, `stop`, `propagate_exception`, `get_process_safe_logger`) and the `__listener` method body (including the L78 out-of-scope `except Exception` silent-shutdown gap) are untouched.

### Task 2: Test Updates (`test_multiprocessing_logger.py`)

Three module-level picklable functions replace the former local closures:
- `_spawn_target_main_logger_receives_records` — logs DEBUG/INFO/WARNING/ERROR under `process_1`
- `_spawn_target_children_names` — logs under `process_1`, `process_1.child_1`, `process_1.child_1_1`
- `_spawn_target_logger_levels` — logs at all four levels (shared across all four sub-cases)

All six `p_1` launch sites updated to `mp_logger._MultiprocessingLogger__mp_context.Process(target=<module_target>, args=(mp_logger,))`. Six `self.assertEqual(p_1.exitcode, 0)` assertions added after each `join(timeout=2)` as the spawn-pickle regression net. All existing `log_capture.check(...)` assertions, `@pytest.mark.timeout(5)` decorators, and `time.sleep`/`mp_logger.stop()` ordering are unchanged.

## Verification Results

| Check | Result |
|-------|--------|
| `get_context("spawn")` present, bare `multiprocessing.Queue(-1)` removed | PASS |
| `__getstate__` and `__setstate__` defined | PASS |
| Three excluded keys referenced in `__getstate__`/`__setstate__` | PASS |
| No `set_start_method`/`get_start_method` branching | PASS |
| `except Exception` listener body intact (out-of-scope gap untouched) | PASS |
| Module-level `_spawn_target*` functions at module scope | PASS |
| Spawn context used for all `p_1` Process creations | PASS |
| No bare `multiprocessing.Process(target=process_1` remaining | PASS |
| 6 `self.assertEqual(p_1.exitcode, 0)` assertions | PASS |
| All 8 test methods present (AST check) | PASS |
| No skip markers | PASS |
| 5/5 single-process regression tests (Task 1 gate) | PASS |
| 8/8 full module tests (decisive spawn-pickle gate) | PASS |
| COMPAT: only two files under change modified | PASS |

**Decisive spawn-pickle gate:** `poetry run pytest tests/unittests/test_common/test_multiprocessing_logger.py -v` — 8 passed in 3.89s on macOS (spawn default). All three spawn-path tests (`test_main_logger_receives_records`, `test_children_names`, `test_logger_levels`) passed with `exitcode == 0`, proving the whole `MultiprocessingLogger` instance survived spawn serialization without `TypeError: cannot pickle '_thread.lock' object`.

## Deviations from Plan

### Pre-existing Out-of-Scope Failure

**`test_app_process.py::TestAppProcess::test_process_with_long_running_thread_terminates_properly`**

- **Found during:** Task 2 wider `test_common/` regression run (verification check 4)
- **Issue:** `TypeError: cannot pickle '_thread.lock' object` — `LongRunningThreadProcess().start()` fails because `AppProcess.__init__` stores `self.__exception_queue = Queue()` and `self._terminate = Event()`, and the test subclass adds `self.thread = threading.Thread(...)`. On macOS (spawn default), ForkingPickler serializes the process object at `start()` and hits these unpicklable fields — the same class of bug as INFRA-01 but in `AppProcess`, which has no `__getstate__`/`__setstate__`.
- **Scope determination:** `test_app_process.py` has ZERO diff vs. the base commit (c6dcb91). This failure pre-dates this plan entirely. Confirmed via `git diff c6dcb91 HEAD -- src/python/tests/unittests/test_common/test_app_process.py` returning empty.
- **Action:** No fix applied (out of scope per deviation rule scope boundary). Documented in `deferred-items.md`. This is a distinct future work item requiring `__getstate__`/`__setstate__` on `AppProcess` or its subclasses.

## Known Stubs

None — this plan wires real production behavior (spawn-context queue creation and pickle dunders). No placeholder text, hardcoded empty values, or unwired data paths exist in the modified files.

## Threat Flags

None — this plan introduces no new trust boundaries, network endpoints, auth paths, file access patterns, or schema changes. The `__getstate__`/`__setstate__` dunders are only invoked when the app itself pickles its own `MultiprocessingLogger` to start its own child process; they are never exposed to untrusted/external pickle sources.

## Self-Check: PASSED

- FOUND: src/python/common/multiprocessing_logger.py
- FOUND: src/python/tests/unittests/test_common/test_multiprocessing_logger.py
- FOUND: .planning/milestones/v1.3.0-phases/107-mp-logger-spawn-safety/107-01-SUMMARY.md
- FOUND: commit 5eb00ad (Task 1 — production module fix)
- FOUND: commit 67476dd (Task 2 — test file updates)
