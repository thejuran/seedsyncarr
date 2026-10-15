---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 03
subsystem: controller / auto-delete
tags: [auto-delete, submitted-unobserved, lock, root-reservation, del-01, regression-red-first]
requires: []
provides:
  - "controller.root_reservation.RootReservations / RootReservation (reused unchanged by 119-06 Task 3)"
  - "FileOperationManager.delete_local(file, reservation=None) with process-lifetime ownership"
  - "Auto-delete Timer submitted-unobserved guard ('transfer submitted, awaiting lftp status')"
affects:
  - src/python/controller/controller.py
  - src/python/controller/command_processor.py
  - src/python/controller/file_operation_manager.py
  - src/python/controller/lftp_manager.py
tech-stack:
  added: []
  patterns:
    - "Non-blocking per-root reservation; ownership hand-off to a tracked subprocess wrapper"
    - "Start, then register: a wrapper is added to the cleanup list only after process.start() has returned"
key-files:
  created:
    - src/python/controller/root_reservation.py
    - src/python/tests/unittests/test_controller/test_root_reservation.py
  modified:
    - src/python/controller/lftp_manager.py
    - src/python/controller/controller.py
    - src/python/controller/command_processor.py
    - src/python/controller/file_operation_manager.py
    - src/python/tests/unittests/test_controller/test_auto_delete_rearm.py
    - src/python/tests/unittests/test_controller/test_lftp_manager.py
    - src/python/tests/unittests/test_controller/test_file_operation_manager.py
    - src/python/tests/unittests/test_controller/test_auto_delete.py
decisions:
  - "Lock order is reservation -> __model_lock -> __auto_delete_lock; the registry lock and __submitted_lock / __processes_lock are leaves"
  - "Start-then-register chosen over a STARTING/RUNNING launch state: cleanup never sees an unstarted child, so no extra state is needed"
  - "A USER QUEUE/DELETE_LOCAL on a reserved root gets 409 'operation in progress'; an AUTO QUEUE skips quietly; the Timer defers with 'root operation in progress'"
metrics:
  duration: "~35 min"
  completed: 2026-10-14
  tasks: 2
  files: 10
---

# Phase 119 Plan 03: DEL-01 Submitted-Unobserved Guard and Per-Root Reservation Summary

The auto-delete Timer now defers while a root's transfer has been submitted but lftp status has not yet confirmed it. A new non-blocking per-root reservation (`RootReservations`) is shared by queue submission, the auto-delete Timer and manual Delete Local. It is held for the deletion child's entire lifetime, and a deletion process is registered for cleanup only after `start()` has returned, so a deletion and a re-download of the same root can never overlap.

## What was built

- **LftpManager**: `__submitted_lock` (a `threading.Lock`) guards every access to the submitted-unobserved set: add, discard on error, kill discard, status clear and snapshot. The name is now added *before* `lftp.queue` and removed again on `LftpError`, so the Timer never sees lftp holding a job the set is missing. The class docstring was updated to say the set is read from the Timer thread.
- **Controller.__execute_auto_delete**:
  - Takes `RootReservations.acquire(file_name, "auto-delete")` before `__model_lock`. If the root is already reserved, the Timer defers with "root operation in progress".
  - New `elif` guard after the state guard: "transfer submitted, awaiting lftp status". Like the other deferrals, it retries through the existing re-arm limit.
  - On the delete path the reservation is passed to `delete_local(file, reservation=reservation)`, with a `handed_off` flag. Every other path releases the reservation in a `finally`.
- **CommandProcessor**:
  - New ctor kwarg `root_reservations`.
  - QUEUE holds the reservation (`with reservation:`) across the submitted check and `lftp.queue`.
  - DELETE_LOCAL acquires the reservation and passes it to `delete_local`.
  - When the root is reserved: a USER command gets 409 "...has an operation in progress (<holder>); retry shortly", and an AUTO QUEUE gets an INFO skip.
- **FileOperationManager**:
  - `CommandProcessWrapper.reservation`.
  - `__processes_lock` guards the wrapper list.
  - `__launch_and_track(wrapper)` is the single place a wrapper is added. It calls `start()` first and adds the wrapper only afterwards; if `start()` fails it releases the reservation and nothing is added.
  - `cleanup_completed_processes` releases a finished wrapper's reservation in a `finally`, before `propagate_exception`. Release depends only on `is_alive()`, whatever the exit status.
  - `stop()` releases any outstanding reservations before the `__started` early return.
  - The class docstring documents the leak bound.
- **root_reservation.py** (new, stdlib only): `RootReservation` (idempotent, owner-checked `release()`, context manager) and `RootReservations` (`acquire`, `holder_of`). The module docstring explains the ownership rule, why the hold lasts the child's whole lifetime, and the lock order.

## RED evidence (commit 32250fb, before the fix)

```
FAILED test_auto_delete_rearm.py::TestAutoDeleteSubmittedUnobserved::test_submitted_guard_runs_after_state_guard_and_respects_rearm_budget
FAILED test_auto_delete_rearm.py::TestAutoDeleteSubmittedUnobserved::test_timer_defers_when_root_submitted_unobserved_and_status_unavailable
FAILED test_auto_delete_rearm.py::TestAutoDeleteSubmittedUnobserved::test_timer_deletes_after_status_observed_clears_submitted_set
FAILED test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_auto_delete_defers_while_queue_submission_holds_root
FAILED test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_manual_delete_local_keeps_root_reserved_until_subprocess_exits
FAILED test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_manual_delete_local_refused_while_auto_delete_holds_root
FAILED test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_queue_refused_while_auto_delete_holds_root
FAILED test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_queue_stays_refused_after_delete_local_returns_until_subprocess_exits
FAILED test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_reservation_released_on_every_non_delete_timer_path
FAILED test_lftp_manager.py::TestLftpManager::test_queue_adds_name_before_lftp_queue_and_discards_on_error
FAILED test_lftp_manager.py::TestLftpManager::test_submitted_set_snapshot_is_lock_protected
ERROR tests/unittests/test_controller/test_root_reservation.py      (ModuleNotFoundError: controller.root_reservation)
ERROR tests/unittests/test_controller/test_file_operation_manager.py (ModuleNotFoundError: controller.root_reservation -> all 7 lifetime/launch-window tests)
11 failed, 8 passed, 37 deselected, 1 warning, 2 errors in 5.31s
```

Failure reasons, observed:
- "Expected 'delete_local' to not have been called" (submitted guard and barrier tests).
- "Expected 'on_success' to not have been called" (QUEUE accepted while a deletion was pending).
- "unexpectedly None : reservation must be handed to delete_local".
- "Lists differ: [['a']] != [[]]" (add happened after the lftp queue).
- "submitted set must be guarded by a lock".
- AttributeError on `_Controller__root_reservations`.

`test_timer_deletes_after_status_observed_clears_submitted_set` also failed before the fix: its first firing deleted instead of deferring. All reservation-lifetime tests in `test_file_operation_manager.py` (including the legacy-behaviour one) could not be collected because of the module-level import, as the plan intended.

**Second RED (launch-window ordering):** I temporarily changed `__launch_and_track` back to append-then-start. `test_reservation_held_across_register_start_window` then failed with `AssertionError: 'delete' != None`: the cleanup sweep running inside `start()` reaped the unstarted child and released the root. The file was restored with `git checkout --` and that variant was never committed. 119-09 still records this formally.

## GREEN evidence (commit 21fa7bd)

```
$ poetry run pytest test_auto_delete_rearm.py test_auto_delete.py test_lftp_manager.py test_root_reservation.py \
    test_file_operation_manager.py test_transfer_state_safety.py test_controller_unit.py -q -p no:cacheprovider
372 passed, 1 warning in 1.30s
$ ruff check src/python/
All checks passed!
```

I ran the barrier, lifetime and launch-window subset 3 more times in a row: 20 passed each time, with no flakes.

All grep gates were checked on the GREEN tree:
- `__submitted_lock` appears 7 times.
- In `queue()`, `add(` is on line 151 and `lftp.queue(` on line 153, so the add comes first.
- In `__execute_auto_delete`, `acquire(` is on line 815, before the first `with self.__model_lock:` on line 836.
- `handed_off` appears 3 times and `with reservation:` 0 times in controller.py.
- CommandProcessor: 2 `acquire(` calls and 1 `with reservation:`.
- FileOperationManager: exactly one `append(` (line 217), which comes after the only `wrapper.process.start()` (line 211). `__launch_and_track(wrapper)` is called twice. In cleanup, `release()` is on line 316, before `propagate_exception()` on line 318. In `stop()`, the release sweep (line 130) comes before `if not self.__started` (line 135).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adapted existing auto-delete assertions to the new `delete_local` signature**
- **Found during:** Task 2
- **Issue:** 42 existing tests in `test_auto_delete.py` and `test_auto_delete_rearm.py` asserted `delete_local.assert_called_once_with(mock_file)` or used single-argument side effects (`check_lock_on_delete(file)`, `lambda _file:`). The Timer now passes `reservation=` as well, so all 42 failed.
- **Fix:** Changed the assertions to `assert_called_once_with(mock_file, reservation=ANY)` and gave the side effects a `reservation=None` parameter. Nothing else in the tests changed.
- **Files modified:** `test_auto_delete.py` (not listed in the plan's files_modified), `test_auto_delete_rearm.py`
- **Commit:** 21fa7bd

**2. [Rule 2 - Correctness] `delete_local` releases the reservation if building the process fails**
- **Found during:** Task 2
- **Issue:** Ownership passes to the manager as soon as `delete_local` is entered. If the `DeleteLocalProcess` constructor or `set_multiprocessing_logger` raised before `__launch_and_track`, the token would leak.
- **Fix:** Wrapped construction in try/except so the reservation is released and the exception re-raised.
- **Commit:** 21fa7bd

**3. [Rule 2 - Correctness] Cleanup keeps finished wrappers it has not yet handled tracked when a callback or propagation raises**
- **Found during:** Task 2
- **Issue:** The plan swaps the list at the end of the sweep. Swapping first (needed so concurrently added wrappers are kept) meant that if `propagate_exception` raised partway through, the remaining finished wrappers would drop out of the list with their reservations still held.
- **Fix:** On an exception, the not-yet-handled finished wrappers are put back under `__processes_lock` before re-raising, so the next sweep or `stop()` still releases them. The raising wrapper's own reservation is already released, before propagation.
- **Commit:** 21fa7bd

**4. [Rule 3 - Blocking] Worktree poetry venv was empty**
- `poetry run pytest` picked up the global pipx pytest, which lacks pytest-timeout. I ran `poetry install --no-root` from the existing lockfile; no new packages were added and the repo is unchanged.

## Deferred Issues (out of scope, unchanged by this plan)

The full `tests/unittests` run on macOS shows 21 failures and 3 errors, all in modules this plan does not touch:
- `test_ssh/test_sshcp.py` — needs the `testgroup` user.
- `test_extract/test_extract_process.py` and `test_scan/test_scanner_process.py` — multiprocessing timeouts.
- `test_system/test_scanner.py`.

These are environmental: CI runs them in its container. The other 1526 tests passed.

## Known Stubs

None.

## TDD Gate Compliance

The RED commit `test(119-03)` (32250fb) comes before the GREEN commit `fix(119-03)` (21fa7bd). The plan named the GREEN commit `fix(...)`, so it is a fix-type commit rather than `feat(...)`. No refactor commit was needed.

## Self-Check: PASSED

- FOUND: src/python/controller/root_reservation.py
- FOUND: src/python/tests/unittests/test_controller/test_root_reservation.py
- FOUND: commit 32250fb (test)
- FOUND: commit 21fa7bd (fix)
