# Phase 87: Python Test Fixes -- Critical & Warning - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 10 (all are existing files, modified in place)
**Analogs found:** 10 / 10 (self-analogs — each file is its own pattern source)

## File Classification

| Modified File (relative to `src/python/`) | Role | Data Flow | Closest Analog | Match Quality |
|-------------------------------------------|------|-----------|----------------|---------------|
| `tests/unittests/test_controller/test_extract/test_extract_process.py` | test | event-driven | self (line 182) | exact — single-line fix |
| `tests/unittests/test_controller/test_lftp_manager.py` | test | request-response | self (lines 83-98) | exact — replace `pass` with assertion |
| `tests/unittests/test_common/test_config.py` | test | file-I/O | self (lines 413, 503) | exact — addCleanup insertions |
| `tests/unittests/test_web/test_handler/test_status_handler.py` | test | request-response | self (lines 13-28) | exact — add assert_called_once_with |
| `tests/unittests/test_lftp/test_lftp.py` | test | file-I/O | self (line 30) | exact — chmod scope fix |
| `tests/conftest.py` | test-infrastructure | event-driven | self (lines 20-43) | exact — logger fixture teardown |
| `tests/unittests/test_controller/test_auto_queue.py` | test | CRUD | self (line 1-5) | exact — add ANY to import |
| `tests/integration/test_web/test_handler/test_stream_model.py` | test | streaming | self (line 1-3) | exact — add ANY to import |
| `tests/unittests/test_web/test_handler/test_server_handler.py` | test | request-response | self (line 1-2) | exact — add ANY to import |
| `tests/integration/test_controller/test_extract/test_extract.py` | test | file-I/O | self (line 51) | exact — context manager wrap |
| `tests/integration/test_controller/test_controller.py` | test | file-I/O | self (lines 88, 2275-2279) | exact — context manager wraps |

---

## Pattern Assignments

### PYFIX-01: `tests/unittests/test_controller/test_extract/test_extract_process.py` line 182

**Bug:** Thread target called immediately instead of passed as callable.

**Current code** (line 182):
```python
threading.Thread(target=_callback_sequence()).start()
```

**Fix — remove `()`:**
```python
threading.Thread(target=_callback_sequence).start()
```

**Context** (lines 168-182 for reference):
```python
def _add_listener(listener: ExtractListener):
    print("Listener added")

    def _callback_sequence():
        listener.extract_completed(name="a", is_dir=True)
        time.sleep(0.1)
        self.completed_signal.value = 1

        time.sleep(1.0)
        listener.extract_completed(name="b", is_dir=False)
        listener.extract_completed(name="c", is_dir=True)
        time.sleep(0.1)
        self.completed_signal.value = 2

    threading.Thread(target=_callback_sequence()).start()  # <-- BUG: line 182
```

**Note:** After fix, the `while self.completed_signal.value < 1: pass` loops (lines 188, 198) are now actually needed to gate on the background thread completing. The test logic is correct for the fixed version.

---

### PYFIX-02: `tests/unittests/test_controller/test_lftp_manager.py` lines 83-98

**Bug:** Test body is `pass` — always passes regardless of production behavior.

**Current code** (lines 82-98):
```python
@patch('controller.lftp_manager.Lftp')
def test_init_skips_rate_limit_when_zero(self, mock_lftp_class):
    """Test that __init__ does not set rate_limit on lftp when 0 (unlimited)."""
    self.mock_context.config.lftp.rate_limit = 0
    mock_lftp = MagicMock()
    mock_lftp_class.return_value = mock_lftp

    manager = LftpManager(self.mock_context)  # noqa: F841

    # ... long comment block ...
    pass  # No assertion needed — test passes if __init__ doesn't crash
```

**Fix — replace `pass` with real assertion:**
```python
@patch('controller.lftp_manager.Lftp')
def test_init_skips_rate_limit_when_zero(self, mock_lftp_class):
    """Test that __init__ does not set rate_limit on lftp when 0 (unlimited)."""
    self.mock_context.config.lftp.rate_limit = 0
    mock_lftp = MagicMock()
    mock_lftp_class.return_value = mock_lftp

    manager = LftpManager(self.mock_context)  # noqa: F841

    # MagicMock auto-creates attributes on access but never assigns 0.
    # Production code only assigns rate_limit when rate_limit > 0.
    # If it were assigned, mock_lftp.rate_limit would equal 0 (an int),
    # not the MagicMock auto-attribute.
    self.assertNotEqual(mock_lftp.rate_limit, 0)
```

**Analog for passing test in same file** (lines 72-80, for style reference):
```python
@patch('controller.lftp_manager.Lftp')
def test_init_sets_rate_limit_when_nonzero(self, mock_lftp_class):
    """Test that __init__ sets rate_limit on lftp when nonzero."""
    self.mock_context.config.lftp.rate_limit = 500
    mock_lftp = MagicMock()
    mock_lftp_class.return_value = mock_lftp

    manager = LftpManager(self.mock_context)  # noqa: F841

    # rate_limit should have been set on the lftp instance
    self.assertEqual(mock_lftp.rate_limit, 500)
```

---

### PYFIX-03: `tests/unittests/test_common/test_config.py` line 503

**Bug:** Temp file created via `NamedTemporaryFile(delete=False)` is never removed.

**Current code** (line 502-503):
```python
def test_to_file(self):
    config_file_path = tempfile.NamedTemporaryFile(suffix="test_config", delete=False).name
```

**Fix — add `addCleanup` immediately after creation:**
```python
def test_to_file(self):
    config_file_path = tempfile.NamedTemporaryFile(suffix="test_config", delete=False).name
    self.addCleanup(os.remove, config_file_path)
```

---

### PYFIX-04: `tests/unittests/test_common/test_config.py` lines 411-500

**Bug:** `config_file.close()` and `os.remove(config_file.name)` at end of test body (lines 499-500) are skipped if any assertion fails before them.

**Current code** (lines 411-413 setup, lines 498-500 cleanup):
```python
def test_from_file(self):
    # Create empty config file
    config_file = tempfile.NamedTemporaryFile(mode="w", suffix="test_config", delete=False)
    # ... test body with many assertions ...
    # Remove config file
    config_file.close()
    os.remove(config_file.name)
```

**Fix — replace end-of-body cleanup with `addCleanup` (LIFO order: close runs first, then remove):**
```python
def test_from_file(self):
    # Create empty config file
    config_file = tempfile.NamedTemporaryFile(mode="w", suffix="test_config", delete=False)
    self.addCleanup(os.remove, config_file.name)  # registered first → runs SECOND
    self.addCleanup(config_file.close)            # registered last  → runs FIRST
    # ... test body with many assertions, unchanged ...
    # REMOVE the old config_file.close() and os.remove() lines at the end
```

**`addCleanup` LIFO rule:** last registered runs first. Register `close` last so it runs first (before `remove`).

---

### PYFIX-05: `tests/unittests/test_web/test_handler/test_status_handler.py` lines 13-28

**Bug:** Two tests set up `mock_serialize_cls.status.return_value` but never assert the call was made on the class. Only test 3 (line 25-28) already has `assert_called_once_with`.

**Current code** (lines 12-28):
```python
@patch('web.handler.status.SerializeStatusJson')
def test_get_status_returns_200(self, mock_serialize_cls):
    mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
    response = self.handler._StatusHandler__handle_get_status()
    self.assertEqual(200, response.status_code)

@patch('web.handler.status.SerializeStatusJson')
def test_get_status_body_is_serialized(self, mock_serialize_cls):
    mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
    response = self.handler._StatusHandler__handle_get_status()
    self.assertEqual('{"server":{"up":true}}', response.body)

@patch('web.handler.status.SerializeStatusJson')
def test_get_status_calls_serializer_with_status(self, mock_serialize_cls):
    mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
    self.handler._StatusHandler__handle_get_status()
    mock_serialize_cls.status.assert_called_once_with(self.mock_status)
```

**Fix — add guard assertion to tests 1 and 2:**
```python
@patch('web.handler.status.SerializeStatusJson')
def test_get_status_returns_200(self, mock_serialize_cls):
    mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
    response = self.handler._StatusHandler__handle_get_status()
    self.assertEqual(200, response.status_code)
    mock_serialize_cls.status.assert_called_once_with(self.mock_status)  # ADD

@patch('web.handler.status.SerializeStatusJson')
def test_get_status_body_is_serialized(self, mock_serialize_cls):
    mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
    response = self.handler._StatusHandler__handle_get_status()
    self.assertEqual('{"server":{"up":true}}', response.body)
    mock_serialize_cls.status.assert_called_once_with(self.mock_status)  # ADD
```

---

### PYFIX-06: `tests/unittests/test_lftp/test_lftp.py` line 30

**Bug:** `chmod_from_to` walks ancestor directories up to `/tmp`, granting group-write to all of them.

**Current code** (lines 23-30):
```python
@classmethod
def setUpClass(cls):
    # Create a temp directory
    TestLftp.temp_dir = tempfile.mkdtemp(prefix="test_lftp_")
    print(f"Temp dir: {TestLftp.temp_dir}")

    # Allow group access for the seedsyncarrtest account
    TestUtils.chmod_from_to(TestLftp.temp_dir, tempfile.gettempdir(), 0o775)
```

**Fix — chmod leaf directory only:**
```python
@classmethod
def setUpClass(cls):
    # Create a temp directory
    TestLftp.temp_dir = tempfile.mkdtemp(prefix="test_lftp_")
    print(f"Temp dir: {TestLftp.temp_dir}")

    # Allow group access for the seedsyncarrtest account — leaf dir only
    os.chmod(TestLftp.temp_dir, 0o750)
```

**Required import:** `os` is already imported at line 2 of `test_lftp.py`.

---

### PYFIX-07: `tests/conftest.py` lines 20-43

**Bug:** `test_logger` fixture adds handler and sets level before `yield` but only calls `removeHandler` after `yield`. Missing: `logger.propagate = False` (prevents double-logging during test), `logger.setLevel(logging.NOTSET)` (resets level for next user of same logger name), `logger.propagate = True` (restores Python default).

**Current code** (lines 20-43):
```python
@pytest.fixture
def test_logger(request):
    logger = logging.getLogger(request.node.name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield logger
    logger.removeHandler(handler)
```

**Fix — add propagation control before yield and full reset after yield:**
```python
@pytest.fixture
def test_logger(request):
    logger = logging.getLogger(request.node.name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False      # ADD: prevent double-logging to root logger
    yield logger
    logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)   # ADD: reset level to default
    logger.propagate = True           # ADD: restore Python default (True)
```

---

### PYFIX-08a: `tests/unittests/test_controller/test_auto_queue.py` lines 1-5

**Bug:** `unittest.mock.ANY` used at line 652, 662, 830, 838, 846 via qualified access, relying on side-effect import from `from unittest.mock import MagicMock`.

**Current imports** (lines 1-5):
```python
import unittest
from unittest.mock import MagicMock
import logging
import sys
import json
```

**Fix — add `ANY` to explicit import:**
```python
import unittest
from unittest.mock import MagicMock, ANY
import logging
import sys
import json
```

---

### PYFIX-08b: `tests/integration/test_web/test_handler/test_stream_model.py` lines 1-3

**Bug:** `unittest.mock.ANY` used at line 17 via qualified access, relying on side-effect import from `from unittest.mock import patch`.

**Current imports** (lines 1-3):
```python
import unittest
from unittest.mock import patch
from threading import Timer
```

**Fix — add `ANY` to explicit import:**
```python
import unittest
from unittest.mock import patch, ANY
from threading import Timer
```

---

### PYFIX-08c: `tests/unittests/test_web/test_handler/test_server_handler.py` lines 1-2

**Bug:** `unittest.mock.ANY` used at line 49 via qualified access, relying on side-effect import from `from unittest.mock import MagicMock`.

**Current imports** (lines 1-2):
```python
import unittest
from unittest.mock import MagicMock
```

**Fix — add `ANY` to explicit import:**
```python
import unittest
from unittest.mock import MagicMock, ANY
```

---

### PYFIX-09a: `tests/integration/test_controller/test_extract/test_extract.py` line 51

**Bug:** Bare `open(os.devnull, 'w')` — file handle not closed if `subprocess.run` raises.

**Current code** (lines 50-59):
```python
# rar - use subprocess.run to wait for completion
fnull = open(os.devnull, 'w')
TestExtract.ar_rar = os.path.join(archive_dir, "file.rar")
subprocess.run(["rar",
                "a",
                "-ep",
                TestExtract.ar_rar,
                temp_file],
               stdout=fnull,
               check=True)
```

**Fix — wrap with context manager:**
```python
# rar - use subprocess.run to wait for completion
TestExtract.ar_rar = os.path.join(archive_dir, "file.rar")
with open(os.devnull, 'w') as fnull:
    subprocess.run(["rar",
                    "a",
                    "-ep",
                    TestExtract.ar_rar,
                    temp_file],
                   stdout=fnull,
                   check=True)
```

---

### PYFIX-09b: `tests/integration/test_controller/test_controller.py` line 88

**Bug:** Bare `open(os.devnull, 'w')` — file handle not closed if `Popen.communicate()` raises.

**Current code** (lines 87-98):
```python
elif ext == "rar":
    fnull = open(os.devnull, 'w')
    subprocess.Popen(
        [
            "rar",
            "a",
            "-ep",
            path,
            temp_file_path
        ],
        stdout=fnull
    ).communicate()
```

**Fix — wrap with context manager:**
```python
elif ext == "rar":
    with open(os.devnull, 'w') as fnull:
        subprocess.Popen(
            [
                "rar",
                "a",
                "-ep",
                path,
                temp_file_path
            ],
            stdout=fnull
        ).communicate()
```

---

### PYFIX-10: `tests/integration/test_controller/test_controller.py` lines 2275-2279

**Bug:** `f = open(_path, "wb")` / `f.close()` pattern — handle leaked if `f.seek` or `f.write` raises.

**Current code** (lines 2275-2280):
```python
def create_large_file(_path, size):
    f = open(_path, "wb")
    f.seek(size - 1)
    f.write(b"\0")
    f.close()
    print("File size: ", os.stat(_path).st_size)
```

**Fix — replace with context manager:**
```python
def create_large_file(_path, size):
    with open(_path, "wb") as f:
        f.seek(size - 1)
        f.write(b"\0")
    print("File size: ", os.stat(_path).st_size)
```

---

## Shared Patterns

### Pattern A: `self.addCleanup()` for guaranteed resource teardown

**Source:** Python stdlib `unittest.TestCase.addCleanup`
**Apply to:** PYFIX-03, PYFIX-04

- Runs cleanup functions **after** the test, **even on assertion failure** or exception.
- Stack-based (LIFO): last registered runs first.
- For PYFIX-04 where two cleanups are needed (`close` then `remove`): register `os.remove` first, `config_file.close` second — so close runs first, then remove.

```python
# PYFIX-03 (one cleanup — file already closed, only path kept):
self.addCleanup(os.remove, config_file_path)

# PYFIX-04 (two cleanups — must close before remove):
self.addCleanup(os.remove, config_file.name)  # registered first → runs second
self.addCleanup(config_file.close)            # registered last  → runs first
```

### Pattern B: `with open(...) as f:` context manager

**Source:** Python stdlib, PEP 343
**Apply to:** PYFIX-09a, PYFIX-09b, PYFIX-10

Always use a `with` block when opening files. Guarantees handle closure even on exception — no manual `.close()` needed.

```python
# Replaces: fnull = open(os.devnull, 'w')
with open(os.devnull, 'w') as fnull:
    subprocess.run([...], stdout=fnull, check=True)

# Replaces: f = open(path, "wb"); ...; f.close()
with open(path, "wb") as f:
    f.seek(size - 1)
    f.write(b"\0")
```

### Pattern C: Explicit `from unittest.mock import ANY`

**Source:** Pattern from existing explicit imports in `tests/unittests/test_web/test_handler/test_status_handler.py` line 2
**Apply to:** PYFIX-08a, PYFIX-08b, PYFIX-08c

Add `ANY` to whatever `from unittest.mock import ...` line already exists. Do not change qualified uses (`unittest.mock.ANY`) or bare uses (`ANY`) — both work after the explicit import is present.

```python
# test_auto_queue.py:
from unittest.mock import MagicMock, ANY

# test_stream_model.py:
from unittest.mock import patch, ANY

# test_server_handler.py:
from unittest.mock import MagicMock, ANY
```

### Pattern D: `assert_called_once_with` guard for class-method mock

**Source:** `tests/unittests/test_web/test_handler/test_status_handler.py` lines 25-28 (test 3, which already has the assertion)
**Apply to:** PYFIX-05 (tests 1 and 2 in the same file)

```python
# Already present in test_get_status_calls_serializer_with_status (test 3):
mock_serialize_cls.status.assert_called_once_with(self.mock_status)

# Add same line to test_get_status_returns_200 and test_get_status_body_is_serialized.
```

### Pattern E: `threading.Thread(target=fn)` — callable, not called

**Source:** Python stdlib `threading.Thread` documentation
**Apply to:** PYFIX-01

```python
# WRONG (calls fn() immediately, passes return value to target):
threading.Thread(target=fn()).start()

# CORRECT (passes fn as callable — Thread calls it in the new thread):
threading.Thread(target=fn).start()
```

### Pattern F: Logger fixture state reset

**Source:** `tests/conftest.py` lines 20-43 (existing fixture, to be extended)
**Apply to:** PYFIX-07

```python
logger.propagate = False   # before yield — prevent double-logging
# yield ...
logger.setLevel(logging.NOTSET)  # after yield — reset to default level
logger.propagate = True          # after yield — restore Python default
```

---

## No Analog Found

None. All fixes are targeted in-place edits to existing test files. All patterns are either from the same file or from Python stdlib.

---

## Metadata

**Analog search scope:** `src/python/tests/` (unittests + integration + conftest.py)
**Files scanned:** 11 source files read directly
**Pattern extraction date:** 2026-04-24

**Key insight:** Every fix is a minimal in-place edit — 1 to 4 lines changed per bug. No new files, no new imports beyond `ANY`, no new test infrastructure. All patterns are standard Python stdlib (`addCleanup`, `with`, `threading.Thread(target=fn)`, `assert_called_once_with`) already in use elsewhere in the test suite.
