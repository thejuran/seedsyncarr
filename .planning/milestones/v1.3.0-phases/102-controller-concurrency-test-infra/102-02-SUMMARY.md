---
phase: 102-controller-concurrency-test-infra
plan: "02"
subsystem: controller
tags:
  - bug-fix
  - concurrency
  - threading
  - auto-delete
  - code-review
dependency_graph:
  requires:
    - "102-01: BUG-03 shutdown guard (provides __shutdown_event + final-commit block)"
  provides:
    - "Thread-safe imported_children.pop: serialized under __model_lock + __auto_delete_lock"
    - "Regression test pinning __model_lock is held during final-commit pop"
  affects:
    - controller/controller.py
    - tests/unittests/test_controller/test_auto_delete.py
tech_stack:
  added: []
  patterns:
    - "Nested lock acquisition: __model_lock THEN __auto_delete_lock (deadlock-free because exit() takes ONLY __auto_delete_lock)"
    - "Observable lock assertion: side_effect wrapper checking Lock.locked() from calling thread to prove lock ordering"
key_files:
  created: []
  modified:
    - src/python/controller/controller.py
    - src/python/tests/unittests/test_controller/test_auto_delete.py
decisions:
  - "Lock order is __model_lock THEN __auto_delete_lock (exit() takes ONLY __auto_delete_lock; no reverse path exists, so no deadlock)"
  - "pop runs inside both locks; delete_local outside both locks (subprocess-safe invariant preserved)"
  - "BUG-03 D-02 invariant preserved: shutdown re-check under __auto_delete_lock, so exit()'s set() cannot interleave between check and pop"
metrics:
  duration_minutes: 15
  completed_date: "2026-06-01T01:42:38Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 102 Plan 02: Model-Lock Serialization Fix for imported_children.pop — Summary

Code-review fix re-serializing `imported_children.pop` in `__execute_auto_delete`'s final-commit block under `__model_lock`, eliminating an OrderedDict thread-safety hazard introduced by the Phase-102-plan-01 BUG-03 fix.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED: regression test asserting pop holds __model_lock | 57ca66a | test_auto_delete.py |
| 2 | GREEN: nest __auto_delete_lock inside __model_lock | 738e439 | controller.py |

## What Was Built

### The Bug (cross-confirmed by two reviewers)

Phase-102-plan-01's BUG-03 fix moved `imported_children.pop` OUT of `__model_lock` and INTO a standalone `with self.__auto_delete_lock:` block. This introduced a thread-safety hazard:

- `imported_children` is a plain `collections.OrderedDict` — NOT thread-safe.
- Every other accessor holds `__model_lock`:
  - `add_imported_child` at controller.py:804 (called on the `process()` thread)
  - BFS-limit pop at ~928 (inside the existing `with self.__model_lock:` block)
  - Coverage-guard read at ~960 (inside the same block)
- `__execute_auto_delete` runs on a daemon `threading.Timer` thread, concurrent with `add_imported_child` on the `process()` thread.
- With the pop under `__auto_delete_lock` only, a concurrent `add_imported_child` (which does compound `__contains__` + conditional `popitem(last=False)` eviction + `__setitem__`) and the pop can mutate the same OrderedDict with NO mutual exclusion, causing structural corruption, KeyError, or wrong coverage results.

### Task 1 — RED test (57ca66a)

Added `TestAutoDeleteModelLockSerialization` to `test_auto_delete.py` with two tests:

**`test_imported_children_pop_holds_model_lock`**: Wraps `self.persist.imported_children.pop` with `asserting_pop`, a side_effect that records `__model_lock.locked()` at call time. Since the test is synchronous and single-threaded, `locked()` returning True means the calling thread holds the lock (the pop is inside `with self.__model_lock:`). Against the Phase-102-plan-01 code, `locked()` returns False (pop is outside `__model_lock`) — assertion fails (RED). After the fix, `locked()` returns True — assertion passes (GREEN).

**`test_delete_local_is_outside_model_lock`**: Confirms `delete_local` is dispatched OUTSIDE `__model_lock` post-fix (subprocess-safe invariant). Was GREEN before and after fix.

### Task 2 — GREEN production code (738e439)

Restructured the final-commit block in `__execute_auto_delete` (controller.py:982-1007):

**Before (buggy — __model_lock already released at pop time):**
```python
        with self.__auto_delete_lock:           # only __auto_delete_lock
            if self.__shutdown_event.is_set():
                return
            self.__persist.imported_children.pop(file_name, None)
        self.__file_op_manager.delete_local(file)
```

**After (fixed — nested inside __model_lock):**
```python
            # still inside with self.__model_lock: block
            with self.__auto_delete_lock:       # nested: both locks held
                if self.__shutdown_event.is_set():
                    return
                self.__persist.imported_children.pop(file_name, None)
        # __model_lock released here
        self.__file_op_manager.delete_local(file)
```

### Lock Ordering Analysis (Deadlock-free)

- `exit()` takes ONLY `__auto_delete_lock` (sets `__shutdown_event` inside the lock, then cancels timers, then releases).
- The callback takes `__auto_delete_lock` at entry (guard), releases, takes `__model_lock` (model read + BFS + coverage guard), then acquires `__auto_delete_lock` nested inside `__model_lock` for the final commit.
- No code path holds `__auto_delete_lock` while acquiring `__model_lock`. The order is always `__model_lock` then `__auto_delete_lock`. No circular wait is possible.

### All Invariants Verified

1. `imported_children.pop` under `__model_lock` — verified by regression test `test_imported_children_pop_holds_model_lock` (locked() = True).
2. Shutdown re-check under `__auto_delete_lock` — the nested block still holds `__auto_delete_lock` when checking the event.
3. No deadlock — `exit()` takes only `__auto_delete_lock`; lock order is `__model_lock` then `__auto_delete_lock` in the callback.
4. `delete_local` outside both locks — verified by `test_delete_local_is_outside_model_lock` (locked() = False).
5. BUG-03 D-02 criterion preserved — Tests A/B/C/D in `TestAutoDeleteShutdownGuard` all pass.

## Verification

```
cd src/python && poetry run pytest tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_controller.py -p no:cacheprovider
```

Result: **129 passed** (102 auto-delete + 27 controller tests). No FAILED.

## Deviations from Plan

None — the fix followed the recommended structure in the task description exactly.

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The change is confined to in-process lock ordering within an existing callback.

## Self-Check: PASSED

- `src/python/controller/controller.py` — final-commit block nests `with self.__auto_delete_lock:` inside `with self.__model_lock:` at lines 997-1001.
- `src/python/tests/unittests/test_controller/test_auto_delete.py` — `TestAutoDeleteModelLockSerialization` class present with 2 tests.
- Commits `57ca66a` and `738e439` both exist in git log.
- Test suite: 129 passed, 0 FAILED.
