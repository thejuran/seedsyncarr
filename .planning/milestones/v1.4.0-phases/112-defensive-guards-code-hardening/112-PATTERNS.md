# Phase 112: Defensive Guards & Code Hardening — Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 8 (5 modified source + 3 test files extended)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/python/common/app_process.py` | process base class | event-driven | `src/python/common/multiprocessing_logger.py` | exact (same `__getstate__`/`__setstate__` spawn-safety pattern) |
| `src/python/seedsyncarr.py` (GUARD-01/02) | application startup | request-response | `src/python/seedsyncarr.py:372-397` (self, existing `_emit_startup_warnings`) | self-referential extend |
| `src/python/seedsyncarr.py` (GUARD-06) | application startup | request-response | `src/python/seedsyncarr.py:38-82` (self, `__init__` ordering) | self-referential reorder |
| `src/python/controller/delete/delete_process.py` | one-shot worker process | CRUD | `DeleteRemoteProcess.run_once` (same file, lines 42-50) | exact (same file, same log-and-continue shape) |
| `.gitignore` | repo config | — | `.gitignore` lines 21-24, 61 (existing AI-tooling block) | exact (identical entry pattern) |
| `src/python/tests/unittests/test_seedsyncarr.py` | unit test | request-response | `TestSeedsyncarrStartupWarnings` (same file, lines 198-274) | self-referential extend |
| `src/python/tests/unittests/test_controller/test_delete_process.py` | unit test | CRUD | `TestDeleteRemoteProcess` (same file, lines 12-81) | exact (same setUp/patch/assertLogs pattern) |
| `src/python/tests/unittests/test_common/test_app_process.py` | unit test | event-driven | `TestAppProcess` (same file, lines 95-182) | self-referential (red test goes green, no new infrastructure) |

---

## Pattern Assignments

### `src/python/common/app_process.py` — GUARD-04 (spawn-safety `__getstate__`/`__setstate__`)

**Analog:** `src/python/common/multiprocessing_logger.py` lines 49-80

**What the analog does:** `MultiprocessingLogger` was passed as an *argument* to a spawn child; its `__getstate__` drops `threading.Thread` and `threading.Event` instances that hold `_thread.lock` objects unpicklable under spawn, then restores them to `None` in `__setstate__`.

**Critical difference vs. analog (from RESEARCH.md):** `AppProcess` *subclasses* `Process` — its entire `__dict__` is pickled when `.start()` is called. The analog stripped its own internal thread objects. Here the `threading.Thread` instance is added by the *subclass* `LongRunningThreadProcess` in its `__init__`, so `__getstate__` must strip any value whose type is `threading.Thread` generically. `Queue` and `Event` stored by `AppProcess.__init__` must NOT be stripped — they survive the spawn boundary correctly for `Process` subclasses and are required for cross-process `propagate_exception()` and `terminate()` to work.

**Analog — imports block** (`multiprocessing_logger.py` lines 1-8):
```python
import multiprocessing
import threading
import queue
import logging
import time
import sys
from logging.handlers import QueueHandler
```
`app_process.py` already imports `threading` (line 8) — no new import needed.

**Analog — `__getstate__` shape** (`multiprocessing_logger.py` lines 49-65):
```python
def __getstate__(self) -> dict:
    """Return only the child-side picklable state for spawn serialization.

    Exists solely so that a MultiprocessingLogger instance survives being
    pickled by a spawn-started child process ...
    The child never calls start()/stop(); it only calls
    get_process_safe_logger(), which needs only the queue and level.
    """
    state = dict(self.__dict__)
    state.pop("_MultiprocessingLogger__listener", None)
    state.pop("_MultiprocessingLogger__listener_shutdown", None)
    state.pop("_MultiprocessingLogger__listener_exc_info", None)
    return state
```

**Analog — `__setstate__` shape** (`multiprocessing_logger.py` lines 67-80):
```python
def __setstate__(self, state: dict) -> None:
    """Restore child-side state after spawn deserialization.

    Exists solely so that a MultiprocessingLogger instance survives being
    pickled by a spawn-started child process. ...
    """
    self.__dict__.update(state)
    self.__dict__["_MultiprocessingLogger__listener"] = None
    self.__dict__["_MultiprocessingLogger__listener_shutdown"] = None
    self.__dict__["_MultiprocessingLogger__listener_exc_info"] = None
```

**Target pattern for `app_process.py`** (verified working against all 9 test scenarios under spawn — from RESEARCH.md live repro):
```python
def __getstate__(self) -> dict:
    """Return picklable state for spawn serialization.

    Strips threading.Thread instances set by subclasses in __init__ that
    cannot be pickled under macOS/Windows spawn start method.  Queue and
    Event objects are retained — Python's spawn mechanism transfers them
    correctly for Process subclasses.  Subclasses that create Thread
    objects in __init__ must re-create them in run_init().
    """
    state = self.__dict__.copy()
    stripped = [k for k, v in state.items() if isinstance(v, threading.Thread)]
    for k in stripped:
        state.pop(k)
    return state

def __setstate__(self, state: dict) -> None:
    """Restore state after spawn deserialization."""
    self.__dict__.update(state)
```

**Placement:** Add both methods to `AppProcess` class, after `propagate_exception` (line 122) and before `run_init` (line 124). This keeps the public API methods together.

**Current target lines** (`app_process.py` lines 41-48 — the `__init__` storing the primitives that must NOT be stripped):
```python
def __init__(self, name: str):
    self.__name = name
    super().__init__(name=self.__name)

    self.mp_logger = None
    self.logger = logging.getLogger(self.__name)
    self.__exception_queue = Queue()   # name-mangled to _AppProcess__exception_queue — DO NOT strip
    self._terminate = Event()           # DO NOT strip
```

**Name-mangling note:** `self.__exception_queue` becomes `_AppProcess__exception_queue` in `__dict__`. The generic `isinstance(v, threading.Thread)` check ignores it because `Queue` is not a `Thread` — no special-casing needed.

---

### `src/python/seedsyncarr.py` — GUARD-02 (warning correctness fix in `_emit_startup_warnings`)

**Analog:** Same function, same file (`seedsyncarr.py` lines 371-397 — existing `_emit_startup_warnings`)

**Current code** (lines 371-397):
```python
@staticmethod
def _emit_startup_warnings(logger: logging.Logger, config: Config) -> None:
    """Emit security warnings for insecure configuration states."""
    if not config.general.webhook_secret:           # BUG: fires even when fail-closed
        logger.warning(
            "Security: webhook_secret is not configured. "
            "Webhook endpoints will accept requests from any caller."
        )
    if config.general.webhook_require_secret and not config.general.webhook_secret:
        logger.warning(
            "Security: webhook_require_secret is True but webhook_secret is not set. "
            "All webhook requests will be rejected with 503 until a secret is configured."
        )
    if not config.general.api_token:
        logger.warning(
            "Security: No API token configured. "
            "All API requests will be accepted without authentication."
        )
        logger.warning(
            "Security: Application is bound to 0.0.0.0 without an API token. "
            "Any host on the network can access the API."
        )
    else:
        logger.info(
            "Security: API token configured — "
            "all /server/* endpoints require Bearer authentication."
        )
```

**GUARD-02 fix — single condition change on line 374:**
Change `if not config.general.webhook_secret:` to `if not config.general.webhook_secret and not config.general.webhook_require_secret:`.

This makes the first warning fire only when the endpoint actually accepts unauthenticated callers. The fail-closed state (`require_secret=True` + no secret) fires only the 503 warning (second block). The existing `test_startup_warns_both_when_both_empty` assertion (`== 3 warnings`) is preserved because that test uses `webhook_require_secret=False` (the `_make_mock_config` default).

**GUARD-01 prominence fix — add `[SECURITY]` prefix to all four `logger.warning` calls** in the function (discretionary per D-06), keeping the level at `logging.warning`. Pattern from the existing text: all four calls already start with `"Security:"` — update to `"[SECURITY]"` for visual distinctiveness in log streams.

---

### `src/python/seedsyncarr.py` — GUARD-06 (legacy fallback warning ordering)

**Analog:** Same file, `__init__` ordering (`seedsyncarr.py` lines 38-82) and `_parse_args` return (line 274)

**Current broken code** (`seedsyncarr.py` lines 265-274):
```python
        if not os.path.exists(args.config_dir):
            legacy_dir = os.path.expanduser("~/.seedsync")
            if os.path.exists(legacy_dir):
                logging.warning(           # bare root logger — no handlers configured yet
                    "Config directory %s not found; falling back to legacy %s",
                    args.config_dir, legacy_dir
                )
                args.config_dir = legacy_dir

        return args
```

`_parse_args` is a `@staticmethod`. The call site at `__init__:40` is:
```python
args = self._parse_args(sys.argv[1:])
```
The configured logger is created at `__init__:74`:
```python
logger = self._create_logger(name=Constants.SERVICE_NAME, debug=is_debug, logdir=args.logdir)
```

**Option A pattern (preferred per D-11):** Change `_parse_args` return from `args` to `(args, legacy_fallback_warning: str | None)`, and emit after `_create_logger`:

```python
# _parse_args — change return value (lines 263-274):
        legacy_fallback_warning: str | None = None
        if not os.path.exists(args.config_dir):
            legacy_dir = os.path.expanduser("~/.seedsync")
            if os.path.exists(legacy_dir):
                legacy_fallback_warning = (
                    "Config directory %s not found; falling back to legacy %s" %
                    (args.config_dir, legacy_dir)
                )
                args.config_dir = legacy_dir
        return args, legacy_fallback_warning

# __init__ call site (line 40) — unpack tuple:
        args, legacy_fallback_warning = self._parse_args(sys.argv[1:])

# __init__ after _create_logger (line ~81) — emit via configured logger:
        if legacy_fallback_warning:
            logger.warning(legacy_fallback_warning)
```

**Option B (acceptable fallback per D-11):** Replace `logging.warning(...)` at line 268 with `print(..., file=sys.stderr)`. No structural change needed, but warning lands on stderr not in the log stream.

Planner chooses Option A or B per D-11 discretion. Option A is the cleaner outcome (warning lands alongside GUARD-01/02 warnings in the same log stream).

---

### `src/python/controller/delete/delete_process.py` — GUARD-03 (logged delete failure)

**Analog:** `DeleteRemoteProcess.run_once` in the same file (lines 42-50)

**Analog — log-and-continue shape** (lines 46-50):
```python
    def run_once(self):
        self.__ssh.set_base_logger(self.logger)
        file_path = os.path.join(self.__remote_path, self.__file_name)
        self.logger.debug("Deleting remote file {}".format(self.__file_name))
        try:
            out = self.__ssh.shell("rm -rf {}".format(shlex.quote(file_path)))
            self.logger.debug("Remote delete output: {}".format(out.decode()))
        except SshcpError:
            self.logger.exception("Exception while deleting remote file")
```

**Current broken code** (`delete_process.py` lines 15-24):
```python
    def run_once(self):
        file_path = os.path.join(self.__local_path, self.__file_name)
        self.logger.debug("Deleting local file {}".format(self.__file_name))
        if not os.path.exists(file_path):
            self.logger.error("Failed to delete non-existing file: {}".format(file_path))
        else:
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                shutil.rmtree(file_path, ignore_errors=True)   # line 24 — swallows all errors
```

**Target fix — replace line 24** (try/except approach, Python 3.11-compatible per RESEARCH.md Pitfall 2):
```python
            else:
                try:
                    shutil.rmtree(file_path)
                except OSError:
                    self.logger.exception(
                        "Failed to delete local directory: %s",
                        sanitize_log_value(self.__file_name)
                    )
```

**Import to add** at top of `delete_process.py` (line 1-5 currently `import os / import shlex / import shutil / from typing import Optional`):
```python
from common.types import sanitize_log_value
```
Check whether `sanitize_log_value` is already accessible via the `common` barrel import (`from common import ...`). If not, add the explicit import from `common.types`.

**Log-injection note:** `self.__file_name` is operator-provided config (not user-HTTP-input), but the SEC-01 convention applies consistently across the delete cluster per D-09. Use `sanitize_log_value(self.__file_name)`, consistent with existing `DeleteRemoteProcess` approach. The `file_path` variable (concatenation of `local_path` + `file_name`) would also be suitable but `self.__file_name` matches the remote precedent.

**Best-effort contract preserved:** The `except OSError` block does not re-raise. The one-shot process continues normally after logging (D-09).

---

### `.gitignore` — GUARD-05 (tooling artifact entries)

**Analog:** Lines 21-24 (AI tooling block) and line 61 (TuringMind block):
```
# AI tooling (local only)
.agents/
.aidesigner/*
!.aidesigner/.gitkeep
.claude/
.mcp.json
...
.bg-shell/
...
.turingmind/
```

**Fix:** Add two lines to the AI tooling block (after `.mcp.json`, before `docs/superpowers/`):
```
.orchestrator.json
.playwright-mcp/
```

The `.orchestrator.json` entry matches the bare-filename pattern (`.mcp.json` on line 26 is the precedent). The `.playwright-mcp/` entry matches the trailing-slash directory pattern (`.bg-shell/`, `.turingmind/` are precedents).

---

## Test File Pattern Assignments

### `src/python/tests/unittests/test_seedsyncarr.py` — GUARD-02 matrix + GUARD-06 fallback

**Analog:** `TestSeedsyncarrStartupWarnings` in the same file (lines 198-274) — extend the existing class.

**Existing harness to reuse** (lines 201-208):
```python
def _make_mock_config(self, webhook_secret="", api_token="", decrypt_errors=None,
                      webhook_require_secret=False):
    mock_config = MagicMock()
    mock_config.general.webhook_secret = webhook_secret
    mock_config.general.api_token = api_token
    mock_config.general.webhook_require_secret = webhook_require_secret
    mock_config._decrypt_errors = decrypt_errors if decrypt_errors is not None else []
    return mock_config
```
`_make_mock_config` already accepts `webhook_require_secret` — the new GUARD-02 tests just pass `webhook_require_secret=True`.

**Existing assertion style to mirror** (lines 210-218, 251-256):
```python
def test_startup_warns_when_webhook_secret_empty(self):
    mock_logger = MagicMock()
    mock_config = self._make_mock_config(webhook_secret="", api_token="configured")
    Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
    warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
    self.assertTrue(
        any("webhook_secret" in call for call in warning_calls),
        msg="Expected a warning containing 'webhook_secret'"
    )

# Count assertion (lines 251-256):
def test_startup_warns_both_when_both_empty(self):
    mock_logger = MagicMock()
    mock_config = self._make_mock_config(webhook_secret="", api_token="")
    Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
    self.assertEqual(3, mock_logger.warning.call_count)
```

**New tests to add (GUARD-02 correctness matrix — D-07):**
```python
def test_startup_require_secret_without_secret_does_not_warn_accept_any_caller(self):
    """GUARD-02: fail-closed state must NOT emit the 'accept any caller' warning."""
    mock_logger = MagicMock()
    mock_config = self._make_mock_config(webhook_secret="", api_token="configured",
                                         webhook_require_secret=True)
    Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
    warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
    self.assertFalse(
        any("any caller" in call for call in warning_calls),
        msg="'accept any caller' warning must not fire when fail-closed (require_secret=True)"
    )

def test_startup_require_secret_without_secret_warns_503(self):
    """GUARD-02: fail-closed state MUST emit the '503' warning."""
    mock_logger = MagicMock()
    mock_config = self._make_mock_config(webhook_secret="", api_token="configured",
                                         webhook_require_secret=True)
    Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
    warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
    self.assertTrue(
        any("503" in call for call in warning_calls),
        msg="Expected a '503' warning when require_secret=True and no secret set"
    )
```

**New test for GUARD-06 fallback (D-12):** Add to a new `TestSeedsyncarrLegacyFallback` class or extend existing `TestSeedsyncarrArgs` (look for existing args tests in the file). Pattern: mock `os.path.exists` to simulate missing config dir + present legacy dir, call `_parse_args(...)`, assert the warning is emitted (either via a `logger.warning` call if Option A, or via `assertLogs` / `capsys` if Option B).

---

### `src/python/tests/unittests/test_controller/test_delete_process.py` — GUARD-03 `DeleteLocalProcess` failure path

**Analog:** `TestDeleteRemoteProcess` in the same file (lines 12-81)

**Existing setUp pattern** (lines 23-35):
```python
def setUp(self):
    sshcp_patcher = patch('controller.delete.delete_process.Sshcp')
    self.addCleanup(sshcp_patcher.stop)
    self.mock_sshcp_cls = sshcp_patcher.start()
    self.mock_sshcp = self.mock_sshcp_cls.return_value

    logger = logging.getLogger("DeleteRemoteProcess")
    self._test_handler = logging.StreamHandler(sys.stdout)
    self._test_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(self._test_handler)
    logger.setLevel(logging.DEBUG)

def tearDown(self):
    logging.getLogger("DeleteRemoteProcess").removeHandler(self._test_handler)
```

**Existing assertLogs failure-path assertion** (lines 73-81):
```python
def test_run_once_catches_sshcp_error_without_raising(self):
    proc = DeleteRemoteProcess(...)
    self.mock_sshcp.shell.side_effect = SshcpError("connection refused")
    with self.assertLogs("DeleteRemoteProcess", level="ERROR"):
        proc.run_once()
```

**New `TestDeleteLocalProcess` class to add** — import `DeleteLocalProcess` from `controller.delete.delete_process`, patch `shutil.rmtree`:

```python
class TestDeleteLocalProcess(unittest.TestCase):

    def setUp(self):
        logger = logging.getLogger("DeleteLocalProcess")
        self._test_handler = logging.StreamHandler(sys.stdout)
        self._test_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )
        logger.addHandler(self._test_handler)
        logger.setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger("DeleteLocalProcess").removeHandler(self._test_handler)

    @patch('shutil.rmtree', side_effect=OSError("permission denied"))
    @patch('os.path.isfile', return_value=False)
    @patch('os.path.exists', return_value=True)
    def test_local_delete_logs_rmtree_failure(self, mock_exists, mock_isfile, mock_rmtree):
        """GUARD-03: a failed rmtree produces a log record rather than silent swallow."""
        proc = DeleteLocalProcess(local_path="/fake", file_name="somefile")
        with self.assertLogs("DeleteLocalProcess", level="ERROR"):
            proc.run_once()   # must not raise
```

The `@patch` decorator order is inside-out: the last `@patch` is the first parameter after `self`. Adjust import paths to match the module structure (`controller.delete.delete_process.shutil` may be needed if `shutil` is imported at module level).

---

### `src/python/tests/unittests/test_common/test_app_process.py` — GUARD-04 red test goes green

**No new test infrastructure needed.** The existing test at line 175 is the acceptance bar:

```python
@pytest.mark.timeout(5)
def test_process_with_long_running_thread_terminates_properly(self):
    self.process = LongRunningThreadProcess()
    self.process.start()
    time.sleep(0.2)
    self.process.terminate()
    self.process.join()
    self.process = None
```

`LongRunningThreadProcess` stores `self.thread = threading.Thread(target=self.long_task)` in `__init__` (lines 57-60). After the `__getstate__`/`__setstate__` fix in `app_process.py`, this test passes under spawn because `__getstate__` strips the unpicklable `threading.Thread` before pickling.

**No changes to this test file.** The test is the green target, not a file to modify.

---

## Shared Patterns

### Log-injection sanitization
**Source:** `src/python/common/types.py` lines 17-36 — `sanitize_log_value(value: str) -> str`
**Apply to:** Any `logger.error` / `logger.exception` call in GUARD-03 that interpolates `file_name` or `path`.
```python
from common.types import sanitize_log_value
# Usage:
self.logger.exception(
    "Failed to delete local directory: %s",
    sanitize_log_value(self.__file_name)
)
```

### Log-and-continue (best-effort, non-fatal)
**Source:** `src/python/controller/delete/delete_process.py` lines 46-50 (`DeleteRemoteProcess.run_once`)
**Apply to:** GUARD-03 fix in `DeleteLocalProcess.run_once`
```python
try:
    <operation>
except <SpecificError>:
    self.logger.exception("Descriptive message: %s", sanitize_log_value(identifier))
# no re-raise — best-effort, non-fatal
```

### `assertLogs` failure-path test assertion
**Source:** `src/python/tests/unittests/test_controller/test_delete_process.py` lines 73-81
**Apply to:** GUARD-03 `TestDeleteLocalProcess.test_local_delete_logs_rmtree_failure`
```python
with self.assertLogs("ClassName", level="ERROR"):
    proc.run_once()  # must not raise
```

### Warning test harness (`_make_mock_config` + `MagicMock`)
**Source:** `src/python/tests/unittests/test_seedsyncarr.py` lines 201-208
**Apply to:** All new GUARD-01/02/06 warning tests
```python
mock_logger = MagicMock()
mock_config = self._make_mock_config(webhook_secret="", api_token="configured",
                                     webhook_require_secret=True)
Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
```

---

## No Analog Found

All files have close analogs in the codebase. No novel patterns are needed.

---

## Metadata

**Analog search scope:** `src/python/common/`, `src/python/controller/delete/`, `src/python/tests/unittests/`, `.gitignore`
**Files scanned:** 7 source + test files read in full
**Pattern extraction date:** 2026-06-02
