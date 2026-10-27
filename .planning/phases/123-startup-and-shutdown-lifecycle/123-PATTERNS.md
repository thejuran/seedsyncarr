# Phase 123: Startup and Shutdown Lifecycle - Pattern Map

**Mapped:** 2026-10-25
**Files analyzed:** 12 (7 source, 5 test)
**Analogs found:** 11 / 12 (1 secondary/low-confidence file has only a partial analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|----------------|
| `src/python/common/job.py` (`Job.run()`) | middleware (shared thread-lifecycle base class) | event-driven (thread run loop, exception capture) | same file — `execute()`'s existing `try/except` block, lines 38-45 | exact (extend the sibling block already in the file) |
| `src/python/controller/controller.py` (`Controller.start()`) | service/controller (component orchestrator) | event-driven (startup sequencing) | same file — `Controller.exit()`'s per-component loop, lines 393-400 | exact (same class, cleanup-side counterpart) |
| `src/python/controller/scan_manager.py` (`start()`, `_terminate_and_join_all()`) | service (process manager) | event-driven / batch (3-process lifecycle) | `controller/controller.py` `exit()`'s per-component `try/except Exception: logger.exception(...)` loop | role-match |
| `src/python/controller/scan_manager.py` (`_check_process_health()` / `propagate_exceptions()`, D-01 shutdown-aware variant) | service (health check) | event-driven | `Controller.__shutdown_event` BUG-03 pattern (`controller.py` lines 283-289, 382-383) — existing purpose-built "already shutting down" flag | role-match (same shutdown-flag idiom, different owner) |
| `src/python/controller/file_operation_manager.py` (`stop()` reservation-release loop) | service (process manager) | batch (per-wrapper cleanup loop) | `controller/controller.py` `exit()`'s per-component loop (same shape, smaller unit) | role-match |
| `src/python/controller/controller_job.py` (`execute()`, D-01 candidate) | job/adapter (thin `Job` subclass) | event-driven | `common/job.py` `Job.shutdown_flag` (`threading.Event`, already read elsewhere) | role-match |
| `src/python/common/multiprocessing_logger.py` (`stop()` never-started guard) | service (thread wrapper) | event-driven | `controller/scan_manager.py` `ScanManager.stop()`'s `if not self.__started: return` guard, lines 105-106 | exact (same guard idiom, one-line port) |
| `src/python/web/web_app_job.py` (`cleanup()` None-guard, secondary) | job/adapter | event-driven | `controller/file_operation_manager.py` `FileOperationManager.stop()`'s `if not self.__started: return` early-return guard | partial (low-confidence, secondary per Pitfall 1) |
| `src/python/tests/unittests/test_common/test_job.py` (new `DummySetupFailingJob` + tests) | test | event-driven | same file — existing `DummyFailingJob`/`TestJob`, lines 12-39 | exact |
| `src/python/tests/unittests/test_controller/test_scan_manager.py` (new partial-start / cleanup-isolation / shutdown-aware tests) | test | event-driven / batch | same file — `test_stop_terminates_and_joins_all_processes` (92-106) and `test_propagate_exceptions_raises_when_process_dies` (264-286) | exact |
| `src/python/tests/unittests/test_controller/test_controller.py` (new `TestControllerStart`/`TestControllerExit` class) | test | event-driven | `tests/unittests/test_controller/base.py` `BaseControllerTestCase` (patches all 6 collaborators) + `test_auto_delete.py`'s `TestAutoDeleteShutdown` (499-523) | role-match (fixture lives in a sibling file, pattern is directly reusable) |
| `src/python/tests/unittests/test_controller/test_file_operation_manager.py` (new `stop_cleanup_isolation` tests) | test | batch | same file — `test_stop_releases_outstanding_reservations` (456-483) | exact |
| `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` (new stop-without-start test) | test | event-driven | `test_scan_manager.py`'s `test_stop_without_start_is_safe` (112-124) | role-match |

## Pattern Assignments

### `src/python/common/job.py` (middleware, event-driven) — `Job.run()`'s `setup()` gap

**Analog:** same file, `execute()`'s existing except-block (the pattern to mirror one line up)

**Current shape** (lines 27-54):
```python
@overrides(threading.Thread)
def run(self):
    self.logger.debug("Thread {} started".format(self.name))

    # ... Setup code here ...
    self.logger.debug("Calling setup for {}".format(self.name))
    self.setup()                                            # <- NOT wrapped (the gap)
    self.logger.debug("Finished setup for {}".format(self.name))

    while not self.shutdown_flag.is_set():
        # ... Job code here ...
        try:
            self.execute()
        except Exception:
            self.exc_info = sys.exc_info()
            self.logger.exception("Caught exception in job {}".format(self.name))
            # break out of run loop and proceed to cleanup
            self.shutdown_flag.set()
            break

        time.sleep(Job._DEFAULT_SLEEP_INTERVAL_IN_SECS)

    # ... Clean shutdown code here ...
    self.logger.debug("Calling cleanup for {}".format(self.name))
    self.cleanup()
    self.logger.debug("Finished cleanup for {}".format(self.name))

    self.logger.debug("Thread {} stopped".format(self.name))
```
`propagate_exception()` (lines 62-70) already raises whatever lands in `self.exc_info` — it does not need to change, only something must populate `exc_info` on a `setup()` failure.

**Core fix pattern (mirror the `execute()` except-block, applied to `setup()`):** wrap `self.setup()` in the identical `try/except Exception: self.exc_info = sys.exc_info(); self.logger.exception(...); self.shutdown_flag.set()` shape, then fall through to the same `cleanup()` call the normal path already reaches — do not duplicate the cleanup call into the except-block; let control flow continue downward into the existing `cleanup()` lines so `ControllerJob.cleanup()` → `Controller.exit()` is reached exactly once either way.

**D-06 (no masking):** `cleanup()` itself must never raise past this point — `ControllerJob.cleanup()`/`Controller.exit()` already satisfies this (`try/except Exception: self.logger.exception(...)` per component); this file's job is only to make sure `setup()`'s exception reaches `exc_info`, not to add new masking risk.

---

### `src/python/controller/controller.py` (service/controller, event-driven) — `Controller.start()` partial-failure cleanup

**Analog:** same file, `Controller.exit()`, lines 367-402

**The exact pattern to mirror** (lines 390-402 — already LIFE-02-correct at this level):
```python
# Each cleanup runs independently: a failure in one (e.g. lftp's
# graceful exit failing on an unsynchronized command stream) must
# never leave the remaining child processes running.
for component, stop in (("lftp", self.__lftp_manager.exit),
                        ("scanner", self.__scan_manager.stop),
                        ("file operations", self.__file_op_manager.stop),
                        ("multiprocessing logger", self.__mp_logger.stop)):
    try:
        stop()
    except Exception:
        self.logger.exception("Error stopping {} during controller exit".format(component))
self.__started = False
self.logger.info("Exited controller")
```

**Current `start()` gap** (lines 340-349 — single flag flipped only at the end):
```python
def start(self):
    """
    Start the controller
    Must be called after ctor and before process()
    """
    self.logger.debug("Starting controller")
    self.__scan_manager.start()
    self.__file_op_manager.start()
    self.__mp_logger.start()
    self.__started = True
```
If `self.__file_op_manager.start()` raises, `__scan_manager` is already running and `__started` is still `False`, so a later `exit()` is a no-op for it — the LIFE-01 gap.

**Fix shape (Claude's Discretion, CONTEXT.md D-04/D-06):** track which components actually started (e.g. a local list built up as each `start()` succeeds, not a single boolean), and on a later failure run the *same* per-component `try/except Exception: self.logger.exception(...)` loop shape as `exit()` above — but only over the already-started subset — then **re-raise the original exception unchanged** (do not let a cleanup failure inside this new block replace it). `self.__started` must stay `False` throughout (D-05: no degraded mode where some components are started and the controller looks usable).

---

### `src/python/controller/scan_manager.py` (service, event-driven/batch) — `start()` partial-start + `_terminate_and_join_all()` fault isolation

**Analog:** `Controller.exit()`'s per-component loop (above) — same shape, applied one level down to 3 processes instead of 4 components

**Current `start()` gap** (lines 87-97):
```python
def start(self) -> None:
    """
    Start all scanner processes.

    Must be called after construction and before pop_latest_results().
    """
    self.logger.debug("Starting scanner processes")
    self.__active_scan_process.start()
    self.__local_scan_process.start()
    self.__remote_scan_process.start()
    self.__started = True
```

**Current `_terminate_and_join_all()` gap** (lines 110-119 — one raising `terminate()`/`join()` skips the rest):
```python
def _terminate_and_join_all(self) -> None:
    """Terminate and join all scanner processes unconditionally."""
    self.logger.debug("Stopping scanner processes")
    self.__active_scan_process.terminate()
    self.__local_scan_process.terminate()
    self.__remote_scan_process.terminate()
    self.__active_scan_process.join()
    self.__local_scan_process.join()
    self.__remote_scan_process.join()
    self.logger.debug("Scanner processes stopped")
```

**Existing `stop()` guard to reuse verbatim for the never-started case** (lines 99-108, also the pattern `multiprocessing_logger.py`'s new guard should copy):
```python
def stop(self) -> None:
    """
    Terminate and join all scanner processes.

    Safe to call multiple times or if not started.
    """
    if not self.__started:
        return
    self.__started = False
    self._terminate_and_join_all()
```

**Fix shape:** (a) in `start()`, track each process that actually started and, on a later `.start()` raising, run the `_terminate_and_join_all()`-style per-process `try/except` loop only over the already-started ones, then re-raise the original exception (D-06); (b) in `_terminate_and_join_all()`, wrap each process's `terminate()`+`join()` pair in its own `try/except Exception: self.logger.exception(...)`, first error logged, remaining two still get their turn — same tuple-of-(name, callable) idiom as `Controller.exit()`.

**D-01 shutdown-aware health check** — `_check_process_health()` (lines 176-204, called from `propagate_exceptions()` at line 173-174):
```python
def _check_process_health(self) -> None:
    ...
    dead_processes = []
    if not self.__remote_scan_process.is_alive():
        dead_processes.append("RemoteScanner")
    if not self.__local_scan_process.is_alive():
        dead_processes.append("LocalScanner")
    if not self.__active_scan_process.is_alive():
        dead_processes.append("ActiveScanner")

    if dead_processes:
        self.__started = False
        names = ", ".join(dead_processes)
        self.logger.error(
            "Scanner process(es) died unexpectedly: {}".format(names)
        )
        self._terminate_and_join_all()
        raise ScannerProcessDiedError(
            "A scanner process stopped unexpectedly. Please check server logs for details."
        )
```
RESEARCH.md's recommended lever (Open Question 1): thread a read-only "already shutting down" signal in (the existing `Job.shutdown_flag` or `Controller.__shutdown_event` idiom — do NOT invent a third shutdown primitive, per CONTEXT.md's discretion note and the Don't-Hand-Roll table) and demote this branch from `logger.error` + raise to `logger.info`/no-op when that signal is already set. Exact plumbing path (through `ControllerJob.execute()`'s early-return candidate vs. threading the flag down into `ScanManager`) is left to the planner per Open Question 1 — both are unit-testable with a dead-process mock + "shutdown already requested" flag.

---

### `src/python/controller/file_operation_manager.py` (service, batch) — `stop()`'s reservation-release loop

**Analog:** `Controller.exit()`'s per-component loop (same shape, applied to the wrapper list)

**Current gap** (lines 118-142 — the reservation-release loop has no per-wrapper isolation):
```python
def stop(self) -> None:
    """
    Stop the extract process and wait for it to terminate.

    Safe to call multiple times or if not started. Releases every root
    reservation still owned by a tracked delete process (the children are
    not joined); this runs even when the manager was never started.
    """
    with self.__processes_lock:
        wrappers = list(self.__active_command_processes)
    for wrapper in wrappers:
        if wrapper.reservation is not None:
            wrapper.reservation.release()
            self.logger.debug("Released root reservation for '{}' on stop".format(
                sanitize_log_value(wrapper.reservation.name)
            ))

    if not self.__started:
        return

    self.logger.debug("Stopping file operation manager")
    self.__extract_process.terminate()
    self.__extract_process.join()
    self.__started = False
    self.logger.debug("File operation manager stopped")
```
One wrapper's `reservation.release()` raising today skips every remaining wrapper's release *and* the `extract_process.terminate()/join()` below it.

**Fix shape:** wrap each wrapper's `release()` call in its own `try/except Exception: self.logger.exception(...)` (first error logged, remaining wrappers still released), matching `Controller.exit()`'s tuple-loop idiom; the `if not self.__started: return` guard and the extract-process terminate/join below it are already correctly isolated from the loop above (they run regardless), so no change needed there beyond the loop itself. Note the existing, already-correct precedent for "always run even if never started" in this same method's docstring/shape — the new loop must preserve that (the loop runs before the `__started` check, same as today).

---

### `src/python/controller/controller_job.py` (job/adapter, event-driven) — D-01 `execute()` shutdown-aware candidate

**Analog:** `common/job.py`'s `shutdown_flag` (`threading.Event`), already a `Job` instance attribute every subclass inherits

**Current shape** (entire file, 18 lines):
```python
from common import overrides, Job, Context
from .controller import Controller
from .auto_queue import AutoQueue

class ControllerJob(Job):
    """
    The controller service
    Handles querying and downloading of files
    """
    def __init__(self,
                 context: Context,
                 controller: Controller,
                 auto_queue: AutoQueue):
        super().__init__(name=self.__class__.__name__, context=context)
        self.__controller = controller
        self.__auto_queue = auto_queue

    @overrides(Job)
    def setup(self):
        self.__controller.start()

    @overrides(Job)
    def execute(self):
        self.__controller.process()
        self.__auto_queue.process()

    @overrides(Job)
    def cleanup(self):
        self.__controller.exit()
```

**RESEARCH.md candidate shape** (smallest-footprint D-01 lever, needs pairing with `Seedsyncarr.signal()` setting `shutdown_flag` synchronously — see Open Question 1 for the tradeoff against threading the flag into `ScanManager` instead):
```python
@overrides(Job)
def execute(self):
    if self.shutdown_flag.is_set():
        return
    self.__controller.process()
    self.__auto_queue.process()
```
Test analog: `test_controller_job.py`'s existing `test_execute_processes_controller`/`test_execute_calls_controller_before_auto_queue` (lines 23-36) show the existing mock-based assertion style (`self.mock_controller.process.assert_called_once()` / `assert_not_called()`) to extend for "when `shutdown_flag` is set, neither `controller.process()` nor `auto_queue.process()` is called."

---

### `src/python/common/multiprocessing_logger.py` (service, event-driven) — `stop()` never-started guard (Pitfall 3)

**Analog:** `controller/scan_manager.py`'s `ScanManager.stop()` guard (verbatim idiom to port)

**Current gap** (lines 42-47 — no guard at all):
```python
def start(self):
    self.__listener.start()

def stop(self):
    self.__listener_shutdown.set()
    self.__listener.join()          # RuntimeError if start() was never called
```
`threading.Thread.join()` raises `RuntimeError: cannot join thread before it is started` when called on a thread that was never `.start()`-ed — this fires exactly when `Controller.start()`'s new partial-cleanup logic (above) calls `stop()` on a component it never reached (per RESEARCH.md Pitfall 3, `mp_logger.start()` is the *last* step in today's `Controller.start()` ordering, so it is the most likely one to be skipped by an earlier failure).

**Fix shape (port `ScanManager`'s idiom):**
```python
def stop(self):
    if not self.__listener.is_alive() and not self.__started:  # exact guard shape TBD by planner;
        return                                                  # minimum requirement: stop() must
    self.__listener_shutdown.set()                               # not raise when start() was never called
    self.__listener.join()
```
(The concrete guard condition — e.g. an explicit `__started` flag mirroring `ScanManager`'s, or checking `self.__listener.ident is None` — is left to the planner; the shape to copy is `ScanManager.stop()`'s early-return-if-never-started, lines 105-106 of `scan_manager.py`.)

---

### `src/python/web/web_app_job.py` (job/adapter, event-driven) — `cleanup()` None-guard (secondary, Pitfall 1)

**Analog:** `FileOperationManager.stop()`'s `if not self.__started: return` early-return guard (closest available shape; no exact analog exists because this gap is latent/defensive rather than a reproducing bug)

**Current gap** (lines 15-45 — `cleanup()` assumes `setup()` fully ran):
```python
def __init__(self, context: Context, web_app: WebApp):
    super().__init__(name=self.__class__.__name__, context=context)
    self.web_access_logger = context.web_access_logger
    self.__context = context
    self.__app = web_app
    self.__server = None
    self.__server_thread = None

@overrides(Job)
def setup(self):
    self.__server = MyWSGIRefServer(...)
    self.__server_thread = Thread(target=bottle.run, kwargs={...})
    self.__server_thread.start()

@overrides(Job)
def cleanup(self):
    self.__app.stop()
    self.__server.stop()           # AttributeError if setup() never reached this line
    self.__server_thread.join()    # AttributeError if setup() never reached this line
```
Once `common/job.py`'s fix makes `cleanup()` reachable after a `setup()` that raised partway through, a `WebAppJob.setup()` failure before `self.__server`/`self.__server_thread` are assigned would hit `AttributeError` here (today unreachable because `Job.run()` never calls `cleanup()` after a `setup()` failure at all).

**Fix shape:** guard each not-yet-assigned attribute (`if self.__server is not None: self.__server.stop()`, same for `__server_thread.join()`), the same "only touch what was actually created" principle `FileOperationManager.stop()`'s `if not self.__started: return` and `ScanManager.stop()`'s guard both already apply, just inlined per-attribute instead of per-component. RESEARCH.md flags this as low-risk/defensive (Assumption A3) — no currently-reachable statement in `MyWSGIRefServer.__init__`/`Thread.__init__` realistically raises — so treat as a cheap, optional hardening alongside the `Job.run()` fix rather than a RED-first regression target unless the planner wants a dedicated test.

---

### Test files

#### `src/python/tests/unittests/test_common/test_job.py` — new `DummySetupFailingJob`

**Analog:** same file's existing `DummyFailingJob`/`TestJob` (lines 1-39, full file):
```python
class DummyError(Exception):
    pass


class DummyFailingJob(Job):
    def setup(self):
        self.cleanup_run = False

    def execute(self):
        raise DummyError()

    def cleanup(self):
        self.cleanup_run = True


class TestJob(unittest.TestCase):
    def test_exception_propagates(self):
        context = MagicMock()
        job = DummyFailingJob("DummyFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        with self.assertRaises(DummyError):
            job.propagate_exception()

    def test_cleanup_executes_on_execute_error(self):
        context = MagicMock()
        job = DummyFailingJob("DummyFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        self.assertTrue(job.cleanup_run)
```
**Mirror shape for the RED-first regression test** (per RESEARCH.md Code Examples): a `DummySetupFailingJob(Job)` whose `setup()` raises `DummyError()` instead of `execute()`, `execute()` is a no-op, `cleanup()` sets `self.cleanup_run = True` — then the same two assertions (`job.start(); job.join(timeout=5.0); assertFalse(job.is_alive()); assertRaises(DummyError): job.propagate_exception()` and `assertTrue(job.cleanup_run)`), run as a real `Job` subclass through the actual thread `run()` loop (per Pitfall 1 warning — do not only mock `Controller`/`ControllerJob`, since that would pass even with the gap present).

#### `src/python/tests/unittests/test_controller/test_scan_manager.py` — partial-start / cleanup-isolation / shutdown-aware tests

**Analog:** same file's `test_stop_terminates_and_joins_all_processes` (lines 92-106) and `test_propagate_exceptions_raises_when_process_dies` (264-286):
```python
@patch('controller.scan_manager.ScannerProcess')
@patch('controller.scan_manager.ActiveScanner')
@patch('controller.scan_manager.LocalScanner')
@patch('controller.scan_manager.RemoteScanner')
def test_stop_terminates_and_joins_all_processes(
        self, mock_remote_scanner, mock_local_scanner,
        mock_active_scanner, mock_scanner_process):
    """Test that stop() terminates and joins all scanner processes."""
    mock_process = MagicMock()
    mock_scanner_process.return_value = mock_process

    manager = ScanManager(self.mock_context, self.mock_mp_logger)
    manager.start()
    manager.stop()

    self.assertEqual(mock_process.terminate.call_count, 3)
    self.assertEqual(mock_process.join.call_count, 3)
```
and the distinct-mock-per-process idiom already used for exactly this kind of per-process assertion (lines 130-157, `test_pop_latest_results_returns_results_from_all_scanners`):
```python
mock_scanner_process.side_effect = [
    mock_active_process, mock_local_process, mock_remote_process
]
```
**New test shapes to add:** (1) partial-start — give `mock_remote_scanner`'s/`mock_scanner_process`'s *third* `.start()` call a `side_effect=RuntimeError`, assert the first two processes' `terminate()`/`join()` were called and the original `RuntimeError` propagates; (2) cleanup-isolation — give one of the three distinct process mocks (via `side_effect=[...]` as in `test_pop_latest_results_...`) a `terminate.side_effect=RuntimeError` and assert the other two still got `terminate()`+`join()` and `self.mock_context.logger` (via `manager.logger`) had `.exception()` called once; (3) shutdown-aware health check — extend `test_propagate_exceptions_raises_when_process_dies` (264-286) with a sibling test that first sets whatever "already shutting down" signal the planner chose, then asserts no `ScannerProcessDiedError` and `logger.error` was not called (only `logger.info`/`debug`, if anything).

#### `src/python/tests/unittests/test_controller/test_controller.py` — new `TestControllerStart`/`TestControllerExit` class

**Analog:** `tests/unittests/test_controller/base.py`'s `BaseControllerTestCase` (patches all 6 `Controller` collaborators as class-level mocks) combined with `test_auto_delete.py`'s `TestAutoDeleteShutdown`:
```python
# base.py — BaseControllerTestCase.setUp() (lines 13-61), the fixture to extend from
self.patcher_sm = patch('controller.controller.ScanManager')
self.patcher_fom = patch('controller.controller.FileOperationManager')
self.patcher_mpl = patch('controller.controller.MultiprocessingLogger')
...
self.mock_scan_manager = self.mock_scan_manager_cls.return_value
self.mock_file_op_manager = self.mock_file_op_manager_cls.return_value
self.mock_mp_logger = self.mock_mp_logger_cls.return_value
...
self.controller = Controller(context=self.mock_context, persist=self.persist, webhook_manager=self.mock_webhook_manager)
```
```python
# test_auto_delete.py — TestAutoDeleteShutdown (lines 499-523), the exit()-cleanup assertion shape
def test_exit_cancels_all_pending_timers(self):
    ...
    self.controller._Controller__started = True
    self.controller.exit()
    self.assertEqual(0, len(self.controller._Controller__pending_auto_deletes))
```
Note from RESEARCH.md: no `TestControllerStart`/`TestControllerExit` class exists today in `test_controller.py` — `Controller.exit()`'s only current coverage is `test_auto_delete.py`'s timer-focused `TestAutoDeleteShutdown`. **New test shapes to add** (extending `BaseControllerTestCase`, name-mangled private-attribute access per the established style): give `self.mock_file_op_manager.start.side_effect = RuntimeError` (after `scan_manager.start()` already "succeeded" via the mock's default no-op), call `self.controller.start()`, assert `self.mock_scan_manager.stop.assert_called_once()` (already-started component cleaned up), `self.mock_mp_logger.start.assert_not_called()` (never-started component untouched), the original `RuntimeError` propagates unmasked (D-06), and `self.controller._Controller__started` stays `False` (D-05, no degraded mode).

#### `src/python/tests/unittests/test_controller/test_file_operation_manager.py` — `stop()` cleanup-isolation test

**Analog:** same file's `test_stop_releases_outstanding_reservations` (lines 456-483):
```python
@patch('controller.file_operation_manager.DeleteLocalProcess')
@patch('controller.file_operation_manager.ExtractProcess')
def test_stop_releases_outstanding_reservations(self, mock_extract_class, mock_delete_class):
    mock_delete = MagicMock()
    mock_delete.is_alive.return_value = True
    mock_delete_class.return_value = mock_delete
    reservations = RootReservations()

    token = reservations.acquire("f", "delete")
    try:
        manager = self._make_manager()
        manager.start()
        manager.delete_local(self._named_file(), reservation=token)
        self.assertEqual("delete", reservations.holder_of("f"))
        manager.stop()
        self.assertIsNone(reservations.holder_of("f"))
    finally:
        token.release()
```
**New test shape to add:** acquire two reservations ("f" and "g"), register two wrappers via `delete_local`, make the *first* reservation's `.release()` raise (`reservation.release = MagicMock(side_effect=RuntimeError)` or a subclassed fake), call `manager.stop()`, assert the *second* reservation was still released (`reservations.holder_of("g") is None`) and the extract process's `terminate()`/`join()` still ran — first error logged via `manager.logger`, not swallowed and not blocking the rest, matching the `_make_manager()`/`_named_file()` helpers already defined at lines 372-384.

#### `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` — stop-without-start test

**Analog:** `test_scan_manager.py`'s `test_stop_without_start_is_safe` (lines 112-124):
```python
def test_stop_without_start_is_safe(
        self, mock_remote_scanner, mock_local_scanner,
        mock_active_scanner, mock_scanner_process):
    """Test that stop() without start() doesn't raise errors."""
    mock_process = MagicMock()
    mock_scanner_process.return_value = mock_process

    manager = ScanManager(self.mock_context, self.mock_mp_logger)
    # Should not raise
    manager.stop()

    mock_process.terminate.assert_not_called()
```
**New test shape to add:** construct a bare `MultiprocessingLogger(base_logger)` (per the file's existing constructor-call style, e.g. a stdlib `logging.getLogger(...)` as in the module's other tests), call `.stop()` without ever calling `.start()`, assert no exception — confirming Pitfall 3's guard once added.

## Shared Patterns

### Per-component/per-process independent cleanup (LIFE-02's core idiom)
**Source:** `src/python/controller/controller.py`, `Controller.exit()`, lines 390-400
**Apply to:** `ScanManager.start()`/`_terminate_and_join_all()`, `Controller.start()`, `FileOperationManager.stop()`'s reservation loop — every new cleanup-on-failure or cleanup-isolation code path added in this phase
```python
for component, stop in (("lftp", self.__lftp_manager.exit),
                        ("scanner", self.__scan_manager.stop),
                        ("file operations", self.__file_op_manager.stop),
                        ("multiprocessing logger", self.__mp_logger.stop)):
    try:
        stop()
    except Exception:
        self.logger.exception("Error stopping {} during controller exit".format(component))
```
CONTEXT.md explicitly forbids a new lifecycle-registry abstraction — every new cleanup site must inline this same tuple-of-`(name, callable)` + `try/except Exception: logger.exception(...)` shape, not factor it into a shared helper class.

### "Never started" early-return guard
**Source:** `src/python/controller/scan_manager.py`, `ScanManager.stop()`, lines 99-108
**Apply to:** `multiprocessing_logger.py`'s new `stop()` guard (Pitfall 3); any new partial-start cleanup in `Controller.start()`/`ScanManager.start()` that must not call `stop()`/`exit()` on a component that never started
```python
def stop(self) -> None:
    if not self.__started:
        return
    self.__started = False
    self._terminate_and_join_all()
```

### Existing shutdown-signal primitives (do not add a third)
**Source:** `src/python/common/job.py`'s `self.shutdown_flag` (`threading.Event`, set in `Job.run()`'s except-block and read by subclasses) and `src/python/controller/controller.py`'s `self.__shutdown_event` (`threading.Event`, BUG-03/D-03, set under `__auto_delete_lock` in `exit()`, lines 283-289 and 382-383)
**Apply to:** D-01's shutdown-aware scanner health check — whichever of `ControllerJob.execute()`'s early-return or `ScanManager`'s own health check is chosen, it must read one of these two existing `Event`s (or a value threaded from one of them), never a new lock/flag/polling thread
```python
# Job.shutdown_flag — common/job.py:22, set at run():44 and 1854263-style propagate at :62-70
self.shutdown_flag = threading.Event()
...
self.shutdown_flag.set()
```
```python
# Controller.__shutdown_event — controller.py:283-289, 382-383 (analogous existing idiom,
# not the same flag, but the same "set under a lock first, read elsewhere" shape)
self.__shutdown_event = threading.Event()
...
with self.__auto_delete_lock:
    self.__shutdown_event.set()
```

### D-06: never mask the original exception
**Source:** `src/python/controller/controller.py`, `Controller.exit()`'s per-component loop (above) — the existing precedent that already avoids this
**Apply to:** every new cleanup-on-partial-start block in `Controller.start()`/`ScanManager.start()`; any cleanup called from inside an `except`/`finally` that is also responsible for re-raising something else (RESEARCH.md Pitfall 4 also flags `Seedsyncarr.run()`'s bare `self.persist()` call in its shutdown-path except-block as a pre-existing, out-of-primary-scope instance of this same risk — flag for planner judgment, not required by CONTEXT.md's named files)
```python
try:
    stop()
except Exception:
    self.logger.exception("Error stopping {} during controller exit".format(component))
# control falls through; the ORIGINAL exception (if any) is re-raised by the caller
# unchanged, never replaced by whatever this except-block logged
```

### Name-mangled private-attribute test access style
**Source:** `src/python/tests/unittests/test_controller/test_auto_delete.py`, `TestAutoDeleteShutdown`/`TestAutoDeleteShutdownGuard` (lines 510, 518, 761, 808) and `base.py`'s `_make_controller_started()` (`self.controller._Controller__started = True`)
**Apply to:** every new `test_controller.py` test that needs to set up or assert `Controller`'s private `__started`/`__scan_manager`/etc. state directly
```python
self.controller._Controller__started = True
self.controller._Controller__pending_auto_deletes  # read
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| D-07 live restart check procedure (not a pytest file; e.g. a new `123-restart-check.sh` or inline checklist) | ops script | manual/batch | No exact prior script for a *restart-cycle* check exists, but `.planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh` (259 lines, idempotent sandbox pin-restore-and-verify pattern, `SANDBOX_RESTORED ok` terminal line) is the explicit reuse target named in CONTEXT.md/RESEARCH.md — extend/companion it rather than write from scratch. |
| `src/python/web/web_app_job.py` cleanup None-guard dedicated regression test | test | event-driven | RESEARCH.md rates this a low-confidence, defensive-only gap (Assumption A3) with no currently-reachable failure path; no existing `test_web_app_job.py` file exists in the repo to extend. If the planner wants a test, it would be a new file borrowing `test_job.py`'s `DummySetupFailingJob`-style harness rather than an existing `WebAppJob`-specific analog. |

## Conventions

Derived via the shared `gsd-tools.cjs verify conventions --derive` module, scoped to `src/python/controller` (the directory most new/modified files in this phase live in):

| Axis | Dominant | Share | Entropy | Status |
|------|----------|-------|---------|--------|
| File-name casing | snake_case | 75% | 0.667 | named contract |
| Identifier casing | PascalCase (classes) | 82% | 0.530 | named contract |
| Export style | n/a (Python, no module export list) | — | — | insufficient data |
| Import style (relative vs. absolute) | relative | 61% | 0.967 | contested hotspot |

All new/modified files in this phase (`job.py`, `controller.py`, `scan_manager.py`, `file_operation_manager.py`, `controller_job.py`, `multiprocessing_logger.py`, `web_app_job.py`, and every new `test_*.py`) are modifications to existing files, so file-name casing and identifier casing are already fixed by the file itself — no new-file naming decision applies in this phase. Import style is the one contested axis measured in this subtree (61%/39% relative-vs-absolute split, entropy 0.967): every file touched in this phase already uses `from .scan_manager import ScanManager`-style relative imports for its own package siblings (see `controller.py` lines 10-23, `scan_manager.py` line 4, `file_operation_manager.py` lines 4-8, `controller_job.py` lines 1-3) and `from common import ...`/`from model import ...`-style absolute imports for cross-package collaborators — match whichever the specific file being edited already does; do not normalize a file's import style while fixing a lifecycle bug in it.

### Contested hotspots (author's choice)
Python's relative/absolute import split in this subtree is the local instance of the same pattern this repo's prototype intentional-contested split embodies at the top level: the CJS↔SDK dual resolver (`bin/lib/**` is CJS `module.exports`/`require`; `sdk/src/**` is ESM `export`/`import`) — each half is internally consistent per-directory and contested only when measured repo-wide. The same rule applies here: a file that already imports its package siblings relatively (e.g. `scan_manager.py`) stays relative; a file that already imports absolutely keeps doing so. Phase 123's edits are all bug fixes inside existing files, so every touched file's existing import style is authoritative for that file — no new file is being created in this phase where the choice would need to be made fresh.

## Metadata

**Analog search scope:** `src/python/common/`, `src/python/controller/`, `src/python/web/`, `src/python/lftp/`, `src/python/tests/unittests/test_common/`, `src/python/tests/unittests/test_controller/`
**Files scanned:** 7 source files read in full (`job.py`, `controller.py` partial [1-1235 of 1522, the `__init__`/`start`/`exit`/early-model methods — auto-delete business logic past line ~1240 was not needed], `scan_manager.py`, `file_operation_manager.py`, `controller_job.py`, `multiprocessing_logger.py`, `web_app_job.py`, `app_process.py` [1-145], `lftp.py` [440-480]); 6 test files read in full or targeted (`test_job.py`, `test_scan_manager.py`, `test_file_operation_manager.py`, `test_controller_job.py`, `test_controller.py` [header + class list], `test_auto_delete.py` [header, `BaseAutoDeleteTestCase`, `TestAutoDeleteShutdown`], `base.py`, `test_multiprocessing_logger.py` [header])
**Pattern extraction date:** 2026-10-25
