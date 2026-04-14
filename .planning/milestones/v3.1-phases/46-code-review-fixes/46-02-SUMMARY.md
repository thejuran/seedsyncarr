---
phase: 46-code-review-fixes
plan: "02"
subsystem: python-backend
tags: [thread-safety, concurrency, code-quality, refactor]
dependency_graph:
  requires: []
  provides: [atomic-extract-dispatch, resilient-worker, internal-unfreeze-api, narrow-except-scope]
  affects: [src/python/controller/extract/dispatch.py, src/python/model/file.py, src/python/controller/controller.py]
tech_stack:
  added: []
  patterns: [atomic-mutex-deque-append, try-except-queue-empty, single-underscore-internal-api, narrow-except-scope]
key_files:
  created: []
  modified:
    - src/python/controller/extract/dispatch.py
    - src/python/model/file.py
    - src/python/controller/controller.py
decisions:
  - "CR-04: atomic extract() uses queue.append+not_empty.notify under one mutex to eliminate TOCTOU; cannot use queue.put() while holding mutex (would deadlock)"
  - "CR-07: queue.get(block=False) in worker finally wrapped in try/except queue.Empty; prevents edge-case thread death"
  - "CR-10: ModelFile._unfreeze() uses single underscore (not double) to mark as protected without name mangling"
  - "CR-12: except ModelError in _set_import_status wraps only get_file; update_file errors now propagate"
metrics:
  duration: "~10 minutes"
  completed: "2026-02-23"
  tasks_completed: 2
  files_modified: 3
---

# Phase 46 Plan 02: Python Code Review Fixes (CR-04, CR-07, CR-10, CR-12) Summary

Eliminated TOCTOU race in extract() duplicate check, hardened worker thread against empty-queue edge case, marked unfreeze as internal API with underscore prefix, and narrowed except scope so update_file errors propagate.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Atomic extract() + resilient worker finally | 784e1ff | dispatch.py |
| 2 | Rename unfreeze to _unfreeze + narrow except | 8daf221 | file.py, controller.py |

## Changes Made

### Task 1: Atomic extract() and Resilient Worker Finally Block

**File:** `src/python/controller/extract/dispatch.py`

**CR-04 — Atomic duplicate check + queue insertion:**

Before: The mutex was acquired for the duplicate check, released, then `queue.put(task)` was called separately. This created a narrow TOCTOU window where a concurrent thread could insert the same file between the check and the put.

After: The task is built completely outside the mutex (no shared state access needed). The mutex is then acquired once for both the duplicate scan over `self.__task_queue.queue` AND the insertion via `self.__task_queue.queue.append(task)` plus `self.__task_queue.not_empty.notify()`. Using direct deque append instead of `queue.put()` is required because `put()` would try to re-acquire the mutex and deadlock.

**CR-07 — Worker finally block resilience:**

Before: `self.__task_queue.get(block=False)` in the worker finally block could raise `queue.Empty` if the queue was empty due to a race, killing the worker thread permanently.

After: The `get()` call is wrapped in `try/except queue.Empty: pass`. The `queue` module was already imported.

### Task 2: Rename unfreeze() to _unfreeze(), Update Callers, Narrow Except Scope

**File:** `src/python/model/file.py`

**CR-10 — Mark unfreeze as internal-only:**

Renamed `unfreeze()` to `_unfreeze()`. Single leading underscore signals "internal/protected use only" per Python convention, matching the copy-then-modify pattern's intent. Double underscore was deliberately avoided (name mangling would break cross-class access patterns).

Updated docstring: "Internal: unfreeze this file for copy-then-modify patterns. Not part of the public API."

**File:** `src/python/controller/controller.py`

**CR-12 — Narrow except ModelError scope in _set_import_status:**

Before: The `try/except ModelError` block wrapped both `model.get_file()` AND `model.update_file()`. The intent was to silently skip files not in the model, but this also swallowed `update_file` errors which indicate real problems.

After: Only `model.get_file(file_name)` is inside the `try/except`; the method returns early if `ModelError` is raised. The `copy`, `_unfreeze()`, import_status assignment, and `update_file()` calls are all outside the except scope and will propagate if they fail.

Updated caller to use `new_file._unfreeze()` with `# noinspection PyProtectedMember`.

## Verification

All plan verification criteria confirmed:

1. All 389 model + controller unit tests pass (21 dispatch + 368 model/controller tests)
2. `grep -n "def _unfreeze" src/python/model/file.py` → line 78: `def _unfreeze(self):`
3. `grep -rn "\.unfreeze()" src/python/` → zero results (all renamed)
4. `grep -rn "\._unfreeze()" src/python/` → controller.py:364 only
5. Visual: `extract()` has task build outside mutex, then one `with self.__task_queue.mutex:` block containing both duplicate check loop and `queue.append + not_empty.notify`
6. Visual: worker finally has `try: get(block=False) except queue.Empty: pass`
7. Visual: `_set_import_status` has `get_file` inside try/except (returns on ModelError), `update_file` outside

Pre-existing failures (not caused by our changes):
- `test_calls_start_dispatch`: multiprocess timeout on Apple Silicon (known, in tech debt)
- lftp tests: require live SSH server connection
- integration tests: require `rar` binary (amd64-only, Apple Silicon unsupported)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

Files modified:
- [x] src/python/controller/extract/dispatch.py (exists, contains `with self.__task_queue.mutex:`, `except queue.Empty`)
- [x] src/python/model/file.py (exists, contains `def _unfreeze`)
- [x] src/python/controller/controller.py (exists, contains `_unfreeze()`, narrow except scope)

Commits:
- [x] 784e1ff — Task 1 commit
- [x] 8daf221 — Task 2 commit

## Self-Check: PASSED
