# Phase 129: Web-Service Cleanup Isolation - Pattern Map

**Mapped:** 2026-11-19
**Files analyzed:** 2 (1 production modified, 1 test extended)
**Analogs found:** 2 / 2 (plus supporting analogs for locks, daemon threads, subprocess tests, real-thread tests)

All paths below are relative to `src/python/` unless they start with `.planning/`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `web/web_app_job.py` (`WebAppJob.setup/cleanup`, `MyWSGIRefServer.__init__/run/stop`) | service (Job lifecycle + server adapter) | event-driven (shutdown sequence) | `controller/controller.py` `exit()` (lines 430-440); `controller/scan_manager.py` `_terminate_and_join` (lines 170-191) | exact (same isolation problem, Phase 123) |
| `tests/unittests/test_web/test_web_app_job.py` | test | event-driven (mock step-failure injection + real thread/subprocess) | `tests/unittests/test_controller/test_scan_manager.py` (lines 486-543) | exact (same isolation tests) |

No changes to `seedsyncarr.py`, `common/job.py`, or `web/web_app.py` (RESEARCH "Recommended Change Footprint").

## Pattern Assignments

### `web/web_app_job.py` (service, event-driven shutdown)

**Current code under change** (lines 1-9 imports, 23-35 setup, 41-49 cleanup, 67-83 server adapter):
```python
import logging
from threading import Thread

import bottle
from paste import httpserver
from paste.translogger import TransLogger

from .web_app import WebApp
from common import overrides, Job, Context
...
        self.__server_thread = Thread(target=bottle.run,
                                      kwargs={
                                          'app': self.__app,
                                          'server': self.__server,
                                          'debug': self.__context.args.debug
                                      })
        self.__server_thread.start()
...
    @overrides(Job)
    def cleanup(self):
        # Job.run now calls cleanup() after a setup() that may have raised
        # before these were assigned.
        self.__app.stop()
        if self.__server is not None:
            self.__server.stop()
        if self.__server_thread is not None:
            self.__server_thread.join()
...
    def __init__(self, logger: logging.Logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger
        self.server = None

    @overrides(bottle.ServerAdapter)
    def run(self, handler):
        self.logger.debug("Starting web server")
        handler = TransLogger(handler, logger=self.logger, setup_console_handler=(not self.quiet))
        self.server = httpserver.serve(handler, host=self.host, port=str(self.port), start_loop=False,
                                       handler=MyWSGIHandler,
                                       **self.options)
        self.server.serve_forever()

    def stop(self):
        self.logger.debug("Stopping web server")
        self.server.server_close()
```
Keep the import block as is. `Thread` is imported by name (`from threading import Thread`), which is what lets tests `patch("web.web_app_job.Thread")`. Add `import threading` (or `from threading import Thread, Lock`) for the lock. Note `Lock` by name would also be patchable; either is fine, but the repo's production modules use `threading.Lock()` (see Shared Patterns).

**Primary analog: per-step isolation** — `controller/controller.py` lines 430-440:
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
```
Copy: the explanatory comment shape, `except Exception:` + `self.logger.exception("Error stopping {} during ...".format(step))`, and `.format()` (not f-strings) for log messages. Message names the step only (no request data).

**Secondary analog: separate terminate/join phases** — `controller/scan_manager.py` lines 170-191:
```python
    def _terminate_and_join(self, processes) -> None:
        """
        Terminate and join each ``(name, process)`` pair independently.

        One process's terminate() or join() raising does not skip the
        others: every raised error is logged via logger.exception, never
        swallowed silently. A process whose terminate() raised is not
        joined -- it may still be running, and join() has no bound, so
        joining it could block shutdown indefinitely.
        """
        joinable = []
        for name, process in processes:
            try:
                process.terminate()
            except Exception:
                self.logger.exception("Error terminating {} process".format(name))
            else:
                joinable.append((name, process))
        for name, process in joinable:
            try:
                process.join()
            except Exception:
                self.logger.exception("Error joining {} process".format(name))
```
Copy the docstring style (explain *why* each step is independent) and the "Error joining ..." wording. **Deliberately diverge** on one point (D-06): the bounded join runs even when `server.stop()` failed; the docstring/comment should say why (the timeout makes the wait safe), since a reader comparing to this analog will expect a skip.

**Bounded-wait constant analog** — `controller/scan_manager.py` lines 32-36:
```python
    # GAP-1: docker's default stop timeout. The live main-thread SIGTERM
    # handler latency was measured at 0.67-1.55 s (123-06), so the grace
    # window must comfortably exceed that while still being bounded by the
    # same deadline docker itself uses before escalating to SIGKILL.
    _SIGTERM_SHUTDOWN_GRACE_IN_SECS = 10.0
```
Copy: class-level `_..._IN_SECS` float constant with a comment justifying the value against Docker's 10 s grace. Proposed: `WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS = 5.0` (D-04). Class attribute (not `Constants`) so tests can `patch.object(WebAppJob, "_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS", 0.05)`. Also matches `Job._DEFAULT_SLEEP_INTERVAL_IN_SECS` in `common/job.py`.

**Daemon thread creation analog** — `controller/arr_queue.py` lines 222-225:
```python
        worker = threading.Thread(name="ArrQueueFetch-" + code, target=self.__fetch_worker,
                                  args=(target, fetch_id, started), daemon=True)
        self.__fetches[code] = _Fetch(worker, fetch_id, started, target.label)
        worker.start()
```
Apply: add `daemon=True` as a keyword to the existing `Thread(target=bottle.run, kwargs={...})` call in `setup()` (D-05). A `name=` kwarg is optional; if added, tests that assert on `call_args.kwargs` must not break.

**Lock-guarded flag analog** — `controller/file_operation_manager.py` lines 101-104 (name-mangled lock declared next to the state it guards, with a comment):
```python
        # Track active command processes (delete operations); guarded by
        # __processes_lock because the auto-delete Timer thread appends too
        self.__active_command_processes: List[CommandProcessWrapper] = []
        self.__processes_lock = threading.Lock()
```
Apply in `MyWSGIRefServer.__init__`: `self.__stop_requested = False` + `self.__lock = threading.Lock()` with a comment that it serializes `stop()` (job thread) against `run()` (server thread) assigning `self.server`. Keep `self.server` public (existing attribute; real-server tests poll it). Target shape for `run()`/`stop()` is RESEARCH Pattern 3 (lines 207-241), verified by experiment E7: snapshot under the lock, act (`server_close()` / `serve_forever()`) outside it. Do NOT call `server.shutdown()` (E4: deadlocks with paste). Add `daemon_threads=True` to `httpserver.serve(...)` before `**self.options`.

**Cleanup target shape:** RESEARCH Pattern 1 (lines 166-196): three explicit blocks (steps have different applicability), `app.stop()` always; `server.stop()` if `self.__server is not None`; join only if `thread is not None and thread.is_alive()` (covers never-started threads, since `join()` on an unstarted thread raises `RuntimeError`), then `logger.warning(...)` if still alive after `join(timeout=...)`.

---

### `tests/unittests/test_web/test_web_app_job.py` (test)

**Current file** (lines 1-12) — extend, do not replace:
```python
import unittest
from unittest.mock import MagicMock

from web.web_app_job import WebAppJob


class TestWebAppJobCleanup(unittest.TestCase):
    def test_cleanup_without_setup_does_not_raise(self):
        web_app = MagicMock()
        job = WebAppJob(context=MagicMock(), web_app=web_app)
        job.cleanup()
        web_app.stop.assert_called_once()
```
Add `job.logger.exception.assert_not_called()` to this test (WEB-02a). `job.logger` is the MagicMock context's `logger`.

**Primary analog: isolation tests** — `tests/unittests/test_controller/test_scan_manager.py` lines 486-513:
```python
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_cleanup_isolation_terminate_error_continues(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """LIFE-02: one process's terminate() raising does not skip the
        other two; the failed process is not joined because it may still
        be running and join() has no bound."""
        ...
        mock_active_process.terminate.side_effect = RuntimeError("terminate failed")

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        manager.stop()  # must not raise

        mock_active_process.terminate.assert_called_once()
        mock_active_process.join.assert_not_called()
        ...
        manager.logger.exception.assert_called_once()
```
Copy: `unittest.TestCase` class style, `@patch('<module>.<Name>')` decorators at the module where the name is looked up (`'web.web_app_job.MyWSGIRefServer'`, `'web.web_app_job.Thread'`, `'web.web_app_job.httpserver'`), docstring prefixed with the requirement ID (`"""WEB-01: ..."""`), drive through the public lifecycle (`job.setup()` then `job.cleanup()  # must not raise`), `side_effect = RuntimeError("...")` for injection, `logger.exception.assert_called_once()` plus a check that `call_args[0][0]` names the step. Use `self.assert*` methods (file is unittest-style), not bare `assert`.

Imports to add, following `test_scan_manager.py` lines 1-6: `import time`, `import threading`, `from unittest.mock import MagicMock, patch`, plus `os`, `subprocess`, `sys`, `textwrap`, `socket` for the subprocess and real-server tests.

Mock-thread guidance (RESEARCH Pitfall 3): always set `thread.is_alive.side_effect = [True, False]` (joined in time) or `[True, True]` (timed out). Assert `thread.join.assert_called_once_with(timeout=WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)` and `mock_thread_cls.call_args.kwargs["daemon"] is True`.

**Constant-assertion analog** — `test_scan_manager.py` line 629:
```python
        self.assertEqual(ScanManager._SIGTERM_SHUTDOWN_GRACE_IN_SECS, 10.0)
```
Apply: pin `WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS` and assert it is `< 10.0` (D-04 must sit below Docker grace).

**Real-thread / bounded-timing analog** — `tests/unittests/test_controller/test_arr_queue.py` lines 301-322:
```python
        release = threading.Event()
        ...
        def blocking_get(*args, **kwargs):
            release.wait(5.0)
            return resp
        ...
        t = time.monotonic()
        outcome = self.client.poll("sonarr")
        self.assertLess(time.monotonic() - t, 0.05)
        ...
        release.set()
```
Apply to the stuck-thread real variant (WEB-02e): a real `Thread` blocked on `threading.Event().wait(...)` with a bounded wait, `patch.object(WebAppJob, "_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS", 0.05)`, measure with `time.monotonic()`, `assertLess(elapsed, 1.0)`, and `release.set()` in a `finally`/`addCleanup` so the thread ends. Name-mangled attributes (`_WebAppJob__server_thread`) only if no `setup()` path exists (Pitfall 4).

**Real-server on loopback analog** — `test_arr_queue.py` lines 71-81 (ephemeral port on 127.0.0.1, daemon test thread):
```python
    server = ThreadingHTTPServer(("127.0.0.1", 0), TrickleHandler)
    ...
    thread = threading.Thread(name="TrickleServer", target=server.serve_forever,
                              kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
```
Apply to WEB-02g: `MyWSGIRefServer(logging.getLogger(...), host="127.0.0.1", port=0)` (never `0.0.0.0`, Pitfall 6) on a `threading.Thread(target=bottle.run, kwargs={"app": bottle.Bottle(), "server": srv, "quiet": True}, daemon=True)`; poll (bounded, `time.monotonic()` deadline) until `srv.server` is set; read port from `srv.server.server_address[1]`; `srv.stop()`; `thread.join(3.0)`; `assertFalse(thread.is_alive())`.

**Subprocess analog** — `tests/unittests/test_docker_image/test_setup_default_config.py` line 86:
```python
        proc = subprocess.run(["bash", copy], capture_output=True, text=True, timeout=30)
        return proc.returncode, proc.stdout + proc.stderr
```
Apply to WEB-02f (D-05 proof): `subprocess.run([sys.executable, "-c", SCRIPT], cwd=<src/python derived from __file__>, capture_output=True, text=True, timeout=20)`; `assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)`. The script (RESEARCH lines 332-340) must wait (bounded) until `srv.server` is set before exiting. On current code this raises `subprocess.TimeoutExpired` (the required red). Keep under pytest-timeout's global 60 s.

## Shared Patterns

### Cleanup never raises; log every failure
**Source:** `common/job.py` lines 55-63 and 103-105
```python
        try:
            self.cleanup()
            self.logger.debug("Finished cleanup for {}".format(self.name))
        except Exception:
            self.logger.exception("Caught exception in cleanup for {}".format(self.name))
            # Do not replace an earlier setup/execute failure (D-06); only
            # surface a cleanup failure when the run was otherwise clean.
            if self.exc_info is None:
                self.exc_info = sys.exc_info()
...
    def cleanup(self):
        """Run once when the job is about to terminate. Must not raise; log errors instead."""
```
**Apply to:** `WebAppJob.cleanup()`. The Job.run net is defensive only; the new cleanup must catch per step itself (D-02).

### Log messages
**Source:** `controller/controller.py` line 440, `scan_manager.py` lines 185/191
**Apply to:** all new log lines. `"Error <verb>ing <step> during web service cleanup"` via `.format()`; `logger.exception` for failures, `logger.warning` for the D-04 timeout, `logger.debug` for the deferred-stop no-op in `MyWSGIRefServer.stop()`. No request data or secrets.

### Bounded waits
**Source:** `scan_manager.py` lines 32-36 (`_..._IN_SECS` class constant with justification comment), `test_arr_queue.py` `settle()` lines 90-95 (monotonic deadline loop in tests).
**Apply to:** the join timeout and every test that waits on a real thread or server.

### Verification gates
`cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider`, then full `tests/unittests`, then repo-root `ruff check src/python/` (whole tree, CI lint gate separate from pytest).

## Conventions

Derived with `gsd-tools verify conventions --derive --scope src/python/web`:

| Axis | Dominant | Share | Entropy | Status |
|------|----------|-------|---------|--------|
| File-name casing | (none; snake 14 / camel 7 / other 2) | 61% | 0.80 | contested hotspot |
| Identifier casing (classes) | Pascal | 100% | 0.00 | named contract |
| Export style | n/a (Python) | - | - | insufficient data |
| Import style | relative (`py-import-relativity`), explicit (no wildcards, 100%) | 74% | 0.83 | named contract |

**Contested hotspots (author's choice):** file-name casing in `web/` is split because the scope includes non-Python assets; Python modules are uniformly snake_case, so no new files are needed here anyway. Import style in `web_app_job.py` itself mixes relative (`from .web_app import WebApp`) and top-level package (`from common import ...`); keep that exact local mix. The repo-wide prototype of an intentional contested split is the CJS<->SDK dual resolver in the GSD tooling (`bin/lib/**` CJS `module.exports`/`require` vs `sdk/src/**` ESM `export`/`import`): each half is internally consistent per directory, so match the directory's local style rather than the repo-wide majority.

## No Analog Found

None. Two sub-patterns have no codebase precedent and should follow RESEARCH.md directly:

| Item | Reason | Use |
|------|--------|-----|
| Stop-requested flag closing a server that starts after `stop()` | No existing adapter handles a stop/start race | RESEARCH Pattern 3 (lines 207-241), verified E7 |
| `daemon_threads=True` on `paste.httpserver.serve` | Only call site of paste in the repo | RESEARCH "Verified Library Behaviour" E5-E7 |

## Metadata

**Analog search scope:** `src/python/web`, `src/python/controller`, `src/python/common`, `src/python/tests/unittests`
**Files scanned:** ~12
**Pattern extraction date:** 2026-11-19
**Hand-off note (D-08):** live restart/clean-shutdown check belongs to Phase 130's release-image smoke test; check container logs (stderr), not only the app log file (RESEARCH Open Question 2).
