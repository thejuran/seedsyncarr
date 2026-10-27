---
phase: 123-startup-and-shutdown-lifecycle
reviewed: 2026-10-27T00:14:12Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - src/python/common/job.py
  - src/python/common/multiprocessing_logger.py
  - src/python/controller/controller_job.py
  - src/python/controller/controller.py
  - src/python/controller/file_operation_manager.py
  - src/python/controller/scan_manager.py
  - src/python/lftp/lftp.py
  - src/python/seedsyncarr.py
  - src/python/web/web_app_job.py
  - src/python/tests/unittests/test_common/test_job.py
  - src/python/tests/unittests/test_common/test_multiprocessing_logger.py
  - src/python/tests/unittests/test_controller/test_controller_job.py
  - src/python/tests/unittests/test_controller/test_controller.py
  - src/python/tests/unittests/test_controller/test_file_operation_manager.py
  - src/python/tests/unittests/test_controller/test_scan_manager.py
  - src/python/tests/unittests/test_lftp/test_lftp_exit.py
  - src/python/tests/unittests/test_seedsyncarr.py
  - src/python/tests/unittests/test_web/test_web_app_job.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 123: Code Review Report

**Reviewed:** 2026-10-27T00:14:12Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

I reviewed the phase diff (`git diff origin/main...HEAD -- src/`): Job setup/cleanup capture, the
partial-start rollback in Controller and ScanManager, the D-01/GAP-1 shutdown-requested signal
plumbing, the GAP-2 reap fallback in `Lftp.exit()`, and the guards in WebAppJob and
MultiprocessingLogger. The core changes hold up when traced through:

- A failed `Controller.start()` stops lftp and every component that already started, then
  re-raises.
- `ControllerJob.setup()` wraps the error so it reaches RECOV-01.
- `Job.run()` still runs `cleanup()` (`Controller.exit()` does nothing because `__started` is
  False), and D-06 keeps the original exception.
- The reap fallback is bounded and handles ECHILD/None correctly.

I found no blockers. One real gap remains in the GAP-1 classification: it covers SIGTERM only,
but the same handler also handles SIGINT. The rest are minor robustness and consistency items.

I did not re-raise the known or accepted items in `deferred-items.md`:
- `WebAppJob.cleanup()` per-step isolation (backlogged)
- `ControllerJob.execute()` non-AppError errors skipping RECOV-01 (backlogged)
- the owner-approved bounded reap wait in `Lftp.exit()` (2.0 s maximum)
- the 10 s SIGTERM grace
- the possible exception masking in `Lftp.exit()`'s `finally` (deep-review sub-note)
- the unguarded shutdown-path `persist()`
- the lftp spawn in `Controller.__init__`

The convention check (`verify conventions --check`) returned no findings. These are Python files,
and there is no Python rule pack, so it was skipped without error.

## Warnings

### WR-01: GAP-1 grace only recognises SIGTERM deaths, but SIGINT is an equally handled shutdown signal

**File:** `src/python/controller/scan_manager.py:312` (with `src/python/seedsyncarr.py:118-119`, `src/python/common/app_process.py:67-68`)
**Issue:** `Seedsyncarr` installs `self.signal` for both SIGTERM and SIGINT. `note_shutdown_requested()` is documented as "the main thread's SIGTERM/SIGINT handler" (`controller.py:379`). Scanner children reset both SIGTERM and SIGINT to `SIG_DFL` (`app_process.py:67-68`). A process-group SIGINT therefore kills them with `exitcode == -2`. Examples are Ctrl-C on a foreground `python seedsyncarr.py` or `docker run -it`, which `tini -g` forwards to the group. The grace branch only matches `-signal.SIGTERM`, so a SIGINT shutdown hits the same race D-01 was meant to close. If the ControllerJob health check runs before the main thread's handler, it:
1. logs `ERROR Scanner process(es) died unexpectedly`
2. raises `ScannerProcessDiedError` (an AppError)
3. lets the main loop raise `ServiceRestart(auto=True)`

The late ServiceExit then lands inside the restart's `except Exception` teardown, interrupting the join/persist sequence. This is the exact false-error shape the phase fixed for SIGTERM.
**Fix:** Treat any shutdown signal the app handles as part of the same race:
```python
_SHUTDOWN_EXITCODES = frozenset((-signal.SIGTERM, -signal.SIGINT))
...
if all(process.exitcode in self._SHUTDOWN_EXITCODES for _, process in dead):
```
Add a `test_scan_manager.py` case that mirrors the existing all-SIGTERM grace test with `exitcode = -signal.SIGINT`. Also update the docstring and the debug message ("ended by SIGTERM").

## Info

### IN-01: WebAppJob's new `__server_thread is not None` guard does not cover a constructed-but-unstarted thread

**File:** `src/python/web/web_app_job.py:29-35, 48-49`
**Issue:** In `setup()`, `self.__server_thread` is assigned before `.start()`. If `Thread.start()` raises (for example `RuntimeError: can't start new thread`), `cleanup()` passes the `is not None` guard and calls `join()` on an unstarted thread, which raises `RuntimeError`. In practice `__server.stop()` already fails first with `AttributeError` on the `None` inner server. That case is the backlogged per-step-isolation item, so this is advisory only. It means the guard added in this phase does not do what its comment says.
**Fix:** When the backlogged isolation work lands, guard with `self.__server_thread.ident is not None` (the same check `MultiprocessingLogger.stop()` now uses) rather than `is not None`.

### IN-02: Cross-thread check-then-set on `Job.exc_info` without a lock

**File:** `src/python/common/job.py:37, 63-64, 79-81`
**Issue:** The setup/execute except blocks set `exc_info`. The main thread can clear it via `propagate_exception()` before the job thread reaches the cleanup except block. In that case the `if self.exc_info is None` D-06 guard passes, and a cleanup error is stored as a second, later exception instead of being suppressed. Today this does no harm: `ControllerJob.cleanup()` → `Controller.exit()` never raises, and the main thread stops polling after the first exception. It is still a latent race in the shared base class.
**Fix:** Track a local `run_failed` flag inside `run()` (set in the setup/execute except blocks), and gate the cleanup assignment on that flag rather than on the shared `exc_info` field.

### IN-03: FileOperationManager.stop() isolation is partial compared with ScanManager

**File:** `src/python/controller/file_operation_manager.py:142-145`
**Issue:** This phase isolated each reservation release, but `__extract_process.terminate()` and `.join()` are still unguarded. If `terminate()` raises, `__started` stays True and `join()` is skipped. That differs from `ScanManager._terminate_and_join()`, which logs each step and skips the join only for a process whose terminate failed. `Controller.exit()`/`start()` still catch and log the error at the component level, so nothing leaks silently.
**Fix:** Mirror ScanManager: wrap `terminate()` in try/except with `logger.exception`, join only on success, and set `__started = False` in all cases.

### IN-04: Reap fallback reports success when the child's status is unavailable

**File:** `src/python/lftp/lftp.py:571-575, 606-611`
**Issue:** When `isalive()` raises ExceptionPexpect, `__poll_isalive()` returns None. The fallback then logs "already reaped elsewhere" at WARNING and returns normally, so `exit()` reports success. ECHILD is the expected cause, but any other ExceptionPexpect from `isalive()` is treated the same way. That hides a possible leak, which is the opposite of the fallback's stated goal ("surfaces honestly").
**Fix:** In `__poll_isalive()`, inspect the wrapped cause (or fall back to `os.waitpid(pid, os.WNOHANG)` and catch `ChildProcessError` explicitly). Return None only for ECHILD, and let other errors propagate as `LftpError`.

---

_Reviewed: 2026-10-27T00:14:12Z_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_
