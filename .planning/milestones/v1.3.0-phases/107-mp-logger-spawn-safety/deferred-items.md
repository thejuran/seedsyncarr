# Phase 107 Deferred Items

## Pre-existing Failure: test_app_process::test_process_with_long_running_thread_terminates_properly

**Discovered during:** Phase 107-01 Task 2 wider regression check (`tests/unittests/test_common/`)

**Error:** `TypeError: cannot pickle '_thread.lock' object` at `LongRunningThreadProcess().start()`

**Root cause:** `AppProcess.__init__` stores `self.__exception_queue = Queue()` and
`self._terminate = Event()`, both holding `_thread.lock` objects. `LongRunningThreadProcess`
additionally holds `self.thread = threading.Thread(...)`. When macOS (spawn default) pickles
the process object at `start()`, ForkingPickler hits these unpicklable objects — same class of
bug as INFRA-01 but in `AppProcess` / its test subclass. No `__getstate__`/`__setstate__` fix
exists on `AppProcess`.

**Scope determination:** `test_app_process.py` was NOT modified by this plan. The failure
exists on the BASE COMMIT (c6dcb91) before any 107 changes — confirmed via `git diff
c6dcb91 HEAD -- src/python/tests/unittests/test_common/test_app_process.py` returning empty.
This is a pre-existing, out-of-scope failure per deviation rule scope boundary.

**Action:** No fix applied. Document for future work. The two files modified in phase 107
(`multiprocessing_logger.py`, `test_multiprocessing_logger.py`) are unaffected.
