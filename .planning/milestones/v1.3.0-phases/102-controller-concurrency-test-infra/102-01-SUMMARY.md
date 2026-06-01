---
phase: 102-controller-concurrency-test-infra
plan: "01"
subsystem: controller
tags:
  - bug-fix
  - concurrency
  - threading
  - auto-delete
  - BUG-03
dependency_graph:
  requires: []
  provides:
    - "BUG-03 criterion #2: lock-serialized shutdown guard for __execute_auto_delete"
    - "Dedicated __shutdown_event (threading.Event) set under __auto_delete_lock in exit()"
    - "Entry guard + final-commit guard in __execute_auto_delete against shutdown race"
    - "Synchronous regression tests A/B/C/D pinning the shutdown-guard behavior"
  affects:
    - controller/controller.py
    - tests/unittests/test_controller/test_auto_delete.py
tech_stack:
  added: []
  patterns:
    - "Lock-serialized Event: threading.Event set UNDER the same lock as the guarded final-commit block eliminates preempt-after-check races"
    - "TDD RED/GREEN: failing test first, then minimal production code to pass"
key_files:
  created: []
  modified:
    - src/python/controller/controller.py
    - src/python/tests/unittests/test_controller/test_auto_delete.py
decisions:
  - "D-02 (strengthened): dedicated threading.Event, NOT __started reuse (D-03)"
  - "D-04: no thread join/drain; the lock — not a join — serializes shutdown vs dispatch"
  - "Final-commit pop moved from __model_lock into __auto_delete_lock to apply BUG-03 guard without reopening WR-02 TOCTOU window"
  - "Test D uses timer.finished.is_set() (not is_alive()) as the canonical cancelled-timer check (consistent with existing TestAutoDeleteScheduling pattern)"
metrics:
  duration_minutes: 4
  completed_date: "2026-06-01T01:21:51Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 102 Plan 01: BUG-03 Shutdown Guard (Criterion #2) Summary

Dedicated `threading.Event` shutdown guard with entry + lock-serialized final-commit protection in `__execute_auto_delete`, proven by a synchronous RED/GREEN test suite (A/B/C positive control + D criterion-#1 verify-only).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED: synchronous shutdown-guard regression tests | 51225c4 | test_auto_delete.py |
| 2 | GREEN: dedicated shutdown Event + entry guard + final-commit guard | 537804d | controller.py |

## What Was Built

### Task 1 — RED tests (51225c4)

Added `TestAutoDeleteShutdownGuard` class to `test_auto_delete.py` with four synchronous tests:

- **Test A** (entry guard): Sets `_Controller__shutdown_event` before invoking `__execute_auto_delete`. Before Task 2: AttributeError (no attribute). After Task 2: entry guard returns early → no `delete_local`, no `imported_children.pop`.
- **Test B** (final-commit guard): Side-effect on `model.get_file` sets the shutdown event during `__model_lock` work, simulating "shutdown began mid-callback". Before Task 2: `delete_local` still called. After Task 2: final-commit guard under `__auto_delete_lock` fires → no `delete_local`, no pop.
- **Test C** (positive control): Event never set → `delete_local` called exactly once + `imported_children` popped. Proves the guards are causal.
- **Test D** (criterion #1 verify-only): Real `threading.Timer` scheduled, `exit()` called → `pending_auto_deletes` empty, `timer.finished.is_set()` True. Pins the already-shipped cancel-on-exit behaviour.

Tests A and B were properly RED before Task 2 landed. Tests C and D were GREEN throughout.

### Task 2 — GREEN production code (537804d)

Three changes to `controller.py`:

1. **`__init__`** (near line 198): `self.__shutdown_event = threading.Event()` — dedicated Event, not `__started` reuse (D-03).

2. **`exit()`**: `self.__shutdown_event.set()` as the **first statement** inside the existing `with self.__auto_delete_lock:` block (before the cancel loop). Setting the event under the same lock that the callback's final-commit block acquires makes `set()` strictly ordered against "check + pop + dispatch" — no preempt-after-check race (D-02).

3. **`__execute_auto_delete`**:
   - **Entry guard** (inside existing `with self.__auto_delete_lock:` at entry): `if self.__shutdown_event.is_set(): return` — fast path, no model read.
   - **Final-commit restructure**: `imported_children.pop` moved OUT of `__model_lock` and INTO a new `with self.__auto_delete_lock:` block immediately after `__model_lock` releases. Inside that block: shutdown check → `return` if set, else `pop`. `delete_local` dispatched AFTER releasing the lock (subprocess-safe, already outside lock in prior code).

### Lock ordering (deadlock-free)

`exit()` takes only `__auto_delete_lock`. The callback takes `__auto_delete_lock` (entry), releases, takes `__model_lock` (model read + BFS), releases, then re-acquires `__auto_delete_lock` (final commit). No circular wait.

### WR-02 semantics preserved

The coverage guard ran and committed "delete is final" under `__model_lock`. Moving the pop to `__auto_delete_lock` immediately after does not reopen the TOCTOU window for the webhook path: any child added between the two lock acquires is for a future import cycle; the deletion decision is already final.

## Verification

```
cd src/python && python -m pytest tests/unittests/test_controller/test_auto_delete.py -v
```

Result: **100 passed** (all existing tests + new A/B/C/D). No FAILED.

```
grep -c "self.__shutdown_event.is_set()" src/python/controller/controller.py  # → 2
grep -n "self.__shutdown_event.set()"  src/python/controller/controller.py   # → line 245 (inside exit()'s __auto_delete_lock block)
grep -n "self.__shutdown_event = threading.Event()" src/python/controller/controller.py  # → line 198
```

All acceptance criteria pass. No thread `.join()` of callback threads added to `exit()` (D-04).

## Deviations from Plan

### Auto-fixed (minor)

**1. [Rule 1 - Bug] Test D assertion: `timer.finished.is_set()` instead of `timer.is_alive()`**
- **Found during:** Task 1 RED verification
- **Issue:** `timer.is_alive()` may still return `True` immediately after `timer.cancel()` because the Timer thread takes a scheduler tick to exit its `wait()` call; the test would fail intermittently. The existing `TestAutoDeleteScheduling` class already uses `timer.finished.is_set()` as the correct check.
- **Fix:** Changed Test D assertion to `timer.finished.is_set()` (the canonical "was this timer cancelled?" signal, set synchronously by `cancel()`).
- **Files modified:** `test_auto_delete.py`
- **Commit:** 51225c4 (included in the RED commit)

## Known Stubs

None — all guards are wired and exercised by the regression tests.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The changes are confined to an in-process threading guard (`threading.Event` + `threading.Lock`). T-102-01 and T-102-LOG mitigations implemented as planned (entry guard + final-commit guard + no new log interpolation of raw strings; early returns add no log lines).

## Self-Check: PASSED

- `src/python/controller/controller.py` — exists and contains `__shutdown_event` guards
- `src/python/tests/unittests/test_controller/test_auto_delete.py` — exists and contains `TestAutoDeleteShutdownGuard`
- Commits `51225c4` and `537804d` both exist in git log
- Test suite: 100 passed, 0 FAILED
