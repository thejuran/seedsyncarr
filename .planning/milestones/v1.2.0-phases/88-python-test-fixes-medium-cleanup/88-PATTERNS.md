# Phase 88: Python Test Fixes -- Medium & Cleanup - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 14 (all existing files, modified in place)
**Analogs found:** 14 / 14 (self-analogs -- each file is its own pattern source, plus cross-file patterns from conftest.py and Phase 87)

## File Classification

| Modified File (relative to `src/python/`) | Role | Data Flow | PYFIX | Closest Analog | Match Quality |
|-------------------------------------------|------|-----------|-------|----------------|---------------|
| `tests/unittests/test_web/test_web_app.py` | test | request-response | 11, 14 | self (lines 137-181 meta tag tests) | exact |
| `tests/unittests/test_controller/test_scan/test_scanner_process.py` | test | event-driven | 12 | self (lines 82, 100, 129, 140, 155, 173 busy-wait loops) | exact |
| `tests/unittests/test_controller/test_extract/test_dispatch.py` | test | event-driven | 13 | self (lines 229, 566, 718, 721, 726, 856 sleep calls) | exact |
| `tests/unittests/test_controller/test_extract/test_extract_process.py` | test | event-driven | 13 | self (lines 173, 176, 179, 274 sleep calls) | exact |
| `tests/unittests/test_common/test_job.py` | test | event-driven | 13, 17 | self (lines 29, 39 sleep calls) | exact |
| `tests/unittests/test_common/test_multiprocessing_logger.py` | test | event-driven | 13, 16 | self (lines 41, 67 sleep calls; line 17 handler leak) | exact |
| `tests/unittests/test_web/test_handler/test_controller_handler.py` | test | request-response | 13 | self (line 672 sleep call) | exact -- skip (0.15s, rate limiter) |
| `tests/unittests/test_web/test_auth.py` | test | request-response | 15 | self (lines 214, 236 bottle import) | exact |
| `tests/unittests/test_lftp/test_lftp.py` | test | file-I/O | 16, 18 | self (lines 113-118 handler leak; lines 210+ busy-wait loops) | exact |
| `tests/unittests/test_lftp/test_job_status_parser_components.py` | test | transform | 19 | self (lines 195-202 conditional assertion) | exact |
| `tests/integration/test_lftp/test_lftp.py` | test | file-I/O | 16 | self (line 44 handler leak) | exact |
| `tests/integration/test_web/test_web_app.py` | test | request-response | 16 | self (line 26 handler leak) | exact |
| `tests/integration/test_controller/test_controller.py` | test | file-I/O | 16 | self (line 359 handler leak) | exact |
| `tests/conftest.py` | test-infrastructure | event-driven | -- | self (Phase 87 PYFIX-07 established removeHandler pattern) | reference-only |

---

## Pattern Assignments

### PYFIX-11: `tests/unittests/test_web/test_web_app.py` -- XSS Prevention Test

**Analog:** Same file, `TestWebAppMetaTagInjection` class (lines 134-229)

**Test method pattern** (lines 137-142 -- representative existing test):
```python
def test_index_contains_meta_tag_with_token(self):
    """index.html should contain api-token meta tag with configured token."""
    app, _tmpd = _make_web_app_with_index(api_token="my-secret-token")
    client = TestApp(app)
    response = client.get("/")
    self.assertIn('<meta name="api-token" content="my-secret-token">', response.text)
```

**New test to add** (follows same pattern, add after line 181):
```python
def test_meta_tag_escapes_html_special_chars(self):
    """XSS prevention: HTML special characters in token must be escaped in meta tag."""
    xss_token = '<script>"alert(1)\'&'
    app, _tmpd = _make_web_app_with_index(api_token=xss_token)
    self.addCleanup(_tmpd.cleanup)  # PYFIX-14 pattern
    client = TestApp(app)
    response = client.get("/")
    # Verify raw XSS payload is NOT in output
    self.assertNotIn("<script>", response.text)
    # Verify escaped version IS in output
    import html as html_mod
    escaped = html_mod.escape(xss_token, quote=True)
    self.assertIn(
        '<meta name="api-token" content="{}">'.format(escaped),
        response.text
    )
```

---

### PYFIX-12: `tests/unittests/test_controller/test_scan/test_scanner_process.py` -- Scanner Busy-Wait Fix

**Analog:** Same file, 6 busy-wait loops at lines 82, 100, 129, 140, 155, 173

**Current pattern** (line 82-83):
```python
while self.scan_counter.value < 2:
    pass
```

**Fix pattern -- add `time.sleep(0.01)` replacing `pass`:**
```python
while self.scan_counter.value < 2:
    time.sleep(0.01)
```

**Import requirement:** `import time` must be added to the imports block (lines 1-12). Currently imports: `unittest`, `multiprocessing`, `logging`, `sys`, `tempfile`, `MagicMock`, `timeout_decorator`. No `time` import exists.

**All 6 locations requiring this fix:**
- Line 82-83: `while self.scan_counter.value < 2: pass`
- Line 99-101: `while self.scan_counter.value < orig_counter+2: pass`
- Line 128-130: `while self.scan_counter.value < orig_counter+2: pass`
- Line 139-141: `while self.scan_counter.value < orig_counter+2: pass`
- Line 155-158: `while True: result = self.process.pop_latest_result(); if result: break` (already has body, but no sleep)
- Line 172-174: `while True:` in `test_sends_fatal_exception_on_nonrecoverable_error` (already has body, no sleep)

---

### PYFIX-13: Sleep Replacement -- 5 Files

#### File 1: `tests/unittests/test_controller/test_extract/test_dispatch.py`

**Analog:** Same file, imports at lines 1-14

**Imports pattern** (lines 1-9):
```python
import unittest
import os
from unittest.mock import patch, MagicMock, call
import time
import threading
import logging
import sys

import timeout_decorator
```

**Shutdown-race sleep pattern** (lines 226-229 and 563-566):
```python
def _extract_archive(**kwargs):
    print(kwargs)
    self.call_stop = True
    time.sleep(0.5)  # wait a bit so shutdown is called
```

**Fix:** Replace `time.sleep(0.5)` with `threading.Event.wait(0.5)`. Create event in test, signal it after `stop()`, so the wait exits early:
```python
# In test setUp or test body:
self.shutdown_event = threading.Event()

def _extract_archive(**kwargs):
    print(kwargs)
    self.call_stop = True
    self.shutdown_event.wait(0.5)  # returns immediately when event is set

# After dispatch.stop():
self.shutdown_event.set()
```

**Stabilization sleep pattern** (lines 718, 721, 726, 856):
```python
time.sleep(0.1)
```

**Fix:** Mock `time.sleep` at the test method level or reduce to `time.sleep(0.01)`. These are "wait for worker thread to process" sleeps -- safe to reduce or mock.

#### File 2: `tests/unittests/test_controller/test_extract/test_extract_process.py`

**Analog:** Same file, imports at lines 1-10

**Imports pattern** (lines 1-10):
```python
import unittest
import logging
from unittest.mock import patch
import sys
import multiprocessing
import ctypes
import threading
import time

import timeout_decorator
```

**Callback sequence sleep pattern** (lines 171-182):
```python
def _callback_sequence():
    listener.extract_completed(name="a", is_dir=True)
    time.sleep(0.1)
    self.completed_signal.value = 1

    time.sleep(1.0)
    listener.extract_completed(name="b", is_dir=False)
    listener.extract_completed(name="c", is_dir=True)
    time.sleep(0.1)
    self.completed_signal.value = 2

threading.Thread(target=_callback_sequence).start()
```

**Fix:** Replace `time.sleep(1.0)` with `threading.Event.wait(timeout=1.0)` and signal the event from the test after first assertions complete. The `time.sleep(0.1)` calls can be reduced to `0.01` or replaced with events.

**Extract-then-wait pattern** (lines 273-278):
```python
self.process.extract(a)
time.sleep(1)
self.process.extract(b)
self.process.extract(c)
while self.extract_counter.value < 3:
    pass
```

**Fix:** Replace `time.sleep(1)` with `while self.extract_counter.value < 1: time.sleep(0.01)` (wait for first extract to complete, then send next two).

#### File 3: `tests/unittests/test_common/test_job.py`

**Handled primarily by PYFIX-17.** See PYFIX-17 section below.

#### File 4: `tests/unittests/test_common/test_multiprocessing_logger.py`

**Analog:** Same file, imports at lines 1-10

**Imports pattern** (lines 1-10):
```python
import unittest
import logging
import sys
import time
import multiprocessing

from testfixtures import LogCapture
import timeout_decorator

from common import MultiprocessingLogger
```

**Parent-side sleep pattern** (lines 38-43):
```python
with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
    p_1.start()
    mp_logger.start()
    time.sleep(1)
    p_1.join()
    mp_logger.stop()
```

**Fix:** Replace `time.sleep(1)` with `p_1.join(timeout=2)` to wait for child process to exit, then small sleep (0.05s) before `mp_logger.stop()` to let logger drain queue:
```python
with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
    p_1.start()
    mp_logger.start()
    p_1.join(timeout=2)
    time.sleep(0.05)  # allow logger thread to drain remaining records
    mp_logger.stop()
```

**Key constraint:** `unittest.mock.patch('time.sleep')` does NOT work across `multiprocessing.Process` boundaries. Child-side sleeps (lines 27, 29, 31 inside `process_1`) cannot be mocked and should remain as-is.

#### File 5: `tests/unittests/test_web/test_handler/test_controller_handler.py` -- SKIP

**Reason:** The `time.sleep(0.15)` at line 672 tests a real time-window-based rate limiter. Mocking it would defeat the test purpose. Only 0.15s total. The `time.sleep(0.001)` is negligible. Skip this file for PYFIX-13.

---

### PYFIX-14: `tests/unittests/test_web/test_web_app.py` -- TemporaryDirectory Cleanup

**Analog:** Same file, `_make_web_app_with_index()` helper (lines 41-62) returns `(app, tmp_dir_obj)`

**Current pattern at each call site** (e.g., line 139):
```python
app, _tmpd = _make_web_app_with_index(api_token="my-secret-token")
client = TestApp(app)
```

**Fix -- add `self.addCleanup(_tmpd.cleanup)` after each call:**
```python
app, _tmpd = _make_web_app_with_index(api_token="my-secret-token")
self.addCleanup(_tmpd.cleanup)
client = TestApp(app)
```

**All call sites in `TestWebAppMetaTagInjection` class (lines 134-229):**
- Line 139: `test_index_contains_meta_tag_with_token`
- Line 146: `test_index_meta_tag_empty_when_no_token`
- Line 153: `test_index_content_type_is_html`
- Line 160: `test_dashboard_route_serves_injected_index`
- Line 166: `test_settings_route_serves_injected_index`
- Line 172: `test_logs_route_serves_injected_index`
- Line 178: `test_about_route_serves_injected_index`
- Line 185: `test_meta_tag_inserted_before_head_close`
- Line 197: `test_original_html_preserved`
- Line 205: `test_security_headers_on_index`
- Line 213: `test_static_files_not_affected`

**Phase 87 analog:** `self.addCleanup(os.remove, config_file_path)` pattern from PYFIX-03/04 in `test_config.py`.

---

### PYFIX-15: `tests/unittests/test_web/test_auth.py` -- Bottle Import Restructuring

**Analog:** Same file, imports at lines 1-9

**Current imports** (lines 1-9):
```python
# Tests for Bearer token authentication middleware (R001-R005, R008)

import logging
import unittest
from unittest.mock import MagicMock

from webtest import TestApp

from web.web_app import WebApp
```

**Fix -- add `import bottle` to module-level imports:**
```python
# Tests for Bearer token authentication middleware (R001-R005, R008)

import logging
import unittest
from unittest.mock import MagicMock

import bottle
from webtest import TestApp

from web.web_app import WebApp
```

**Then remove the two `import bottle` statements inside closures:**
- Line 214: `import bottle` inside `_capture()` closure in `setUp`
- Line 236: `import bottle` inside `_capture()` closure in `test_auth_valid_true_on_no_token_config`

---

### PYFIX-16: Logger Handler Cleanup -- 5 Files

**Shared analog:** `tests/conftest.py` lines 20-46 (Phase 87 PYFIX-07 pattern)

**Reference pattern from conftest.py** (lines 35-46):
```python
logger = logging.getLogger(request.node.name)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False
yield logger
logger.removeHandler(handler)
logger.setLevel(logging.NOTSET)
logger.propagate = True
```

**Adaptation for unittest.TestCase:** Store handler as `self._test_handler` in `setUp`, call `removeHandler` in `tearDown`.

#### File 1: `tests/unittests/test_lftp/test_lftp.py` (lines 113-118)

**Current setUp** (lines 113-118):
```python
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
```

**Current tearDown** (lines 120-122):
```python
def tearDown(self):
    self.lftp.raise_pending_error()
    self.lftp.exit()
```

**Fix:** Store handler, remove in tearDown:
```python
# In setUp, change `handler` to `self._test_handler`:
self._test_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
self._test_handler.setFormatter(formatter)
logger.addHandler(self._test_handler)

# In tearDown, add before existing lines:
logging.getLogger().removeHandler(self._test_handler)
```

#### File 2: `tests/integration/test_lftp/test_lftp.py` (lines 39-44)

**Current setUp** (lines 39-44):
```python
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
```

**Current tearDown** (lines 50-53):
```python
def tearDown(self):
    self.lftp.exit()
    shutil.rmtree(os.path.join(TestLftp.temp_dir, "remote"))
    shutil.rmtree(os.path.join(TestLftp.temp_dir, "local"))
```

**Fix:** Same as File 1 -- store as `self._test_handler`, remove in tearDown.

#### File 3: `tests/integration/test_web/test_web_app.py` (lines 24-29)

**Current setUp** (lines 24-29):
```python
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)
```

**No existing tearDown.** Must add one.

**Fix:**
```python
# In setUp, change `handler` to `self._test_handler`:
self._test_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(self._test_handler)
# ...

# Add tearDown:
def tearDown(self):
    logging.getLogger().removeHandler(self._test_handler)
```

#### File 4: `tests/integration/test_controller/test_controller.py` (lines 357-362)

**Current setUp** (lines 357-362):
```python
logger = logging.getLogger(TestController.__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)
```

**Current tearDown** (lines 372-379):
```python
@overrides(unittest.TestCase)
def tearDown(self):
    if self.controller:
        self.controller.exit()
    # Cleanup
    if not TestController.__KEEP_FILES:
        shutil.rmtree(self.temp_dir)
```

**Fix:** Store handler, add remove to tearDown. Note this uses a named logger (`TestController.__name__`), not root:
```python
# In setUp:
self._test_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(self._test_handler)

# In tearDown, add:
logging.getLogger(TestController.__name__).removeHandler(self._test_handler)
```

#### File 5: `tests/unittests/test_common/test_multiprocessing_logger.py` (lines 14-20)

**Current setUp** (lines 14-20):
```python
def setUp(self):
    self.logger = logging.getLogger(TestMultiprocessingLogger.__name__)
    handler = logging.StreamHandler(sys.stdout)
    self.logger.addHandler(handler)
    self.logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
```

**No existing tearDown.** Must add one.

**Fix:**
```python
# In setUp, change `handler` to `self._test_handler`:
self._test_handler = logging.StreamHandler(sys.stdout)
self.logger.addHandler(self._test_handler)

# Add tearDown:
def tearDown(self):
    self.logger.removeHandler(self._test_handler)
```

---

### PYFIX-17: `tests/unittests/test_common/test_job.py` -- Job.join Replacement

**Analog:** Same file (lines 1-42)

**Current test** (lines 25-33):
```python
def test_exception_propagates(self):
    context = MagicMock()
    job = DummyFailingJob("DummyFailingJob", context)
    job.start()
    time.sleep(0.2)
    with self.assertRaises(DummyError):
        job.propagate_exception()
    job.terminate()
    job.join()
```

**Fix:**
```python
def test_exception_propagates(self):
    context = MagicMock()
    job = DummyFailingJob("DummyFailingJob", context)
    job.start()
    job.join(timeout=5.0)
    with self.assertRaises(DummyError):
        job.propagate_exception()
```

**Current test** (lines 35-42):
```python
def test_cleanup_executes_on_execute_error(self):
    context = MagicMock()
    job = DummyFailingJob("DummyFailingJob", context)
    job.start()
    time.sleep(0.2)
    job.terminate()
    job.join()
    self.assertTrue(job.cleanup_run)
```

**Fix:**
```python
def test_cleanup_executes_on_execute_error(self):
    context = MagicMock()
    job = DummyFailingJob("DummyFailingJob", context)
    job.start()
    job.join(timeout=5.0)
    self.assertTrue(job.cleanup_run)
```

**Note:** After these fixes, the `import time` at line 3 may become unused if no other `time` usage exists. Remove it if so.

---

### PYFIX-18: `tests/unittests/test_lftp/test_lftp.py` -- Busy-Wait Sleep Injection

**Analog:** Same file, 41 `while True:` loops

**Current imports** (lines 1-10):
```python
import logging
import os
import shutil
import sys
import tempfile
import unittest

import timeout_decorator

from lftp import Lftp, LftpJobStatus, LftpError
```

**Import fix:** Add `import time` to the imports block (no `time` import currently exists).

**Representative current loop** (lines 210-213):
```python
while True:
    statuses = self.lftp.status()
    if len(statuses) > 0:
        break
```

**Fix -- add `time.sleep(0.01)` after break condition:**
```python
while True:
    statuses = self.lftp.status()
    if len(statuses) > 0:
        break
    time.sleep(0.01)
```

**Important placement rule:** The `time.sleep(0.01)` goes AFTER all `if condition: break` checks, as the last statement in the loop body before it loops back. This ensures sleep only runs when the loop continues.

**Scope:** All 41 `while True:` loops in the file. Each follows the same pattern: poll `self.lftp.status()` or similar, check condition, break if met.

---

### PYFIX-19: `tests/unittests/test_lftp/test_job_status_parser_components.py` -- Conditional Assertion Fix

**Analog:** Same file, adjacent test method `test_parse_chunk_at` (lines 185-193)

**Correct pattern without conditional** (lines 185-193):
```python
def test_parse_chunk_at(self):
    line = "`file.txt' at 1024 (50%) 512K/s eta:30s [Receiving data]"
    match = RegexPatterns.CHUNK_AT.search(line)
    state = TransferStateParser.parse_chunk_at(match)
    self.assertIsNone(state.size_local)
    self.assertIsNone(state.size_remote)
    self.assertIsNone(state.percent_local)
    self.assertEqual(512 * 1024, state.speed)
    self.assertEqual(30, state.eta)
```

**Current buggy code** (lines 195-202):
```python
def test_parse_chunk_at_no_speed_eta(self):
    # Some chunk_at patterns don't have speed or eta
    line = "`file.txt' at 1024 (50%) [Receiving data]"
    match = RegexPatterns.CHUNK_AT.search(line)
    if match:  # Pattern may not match without speed/eta
        state = TransferStateParser.parse_chunk_at(match)
        self.assertIsNone(state.speed)
        self.assertIsNone(state.eta)
```

**Fix -- assert match exists, remove conditional:**
```python
def test_parse_chunk_at_no_speed_eta(self):
    # Some chunk_at patterns don't have speed or eta
    line = "`file.txt' at 1024 (50%) [Receiving data]"
    match = RegexPatterns.CHUNK_AT.search(line)
    self.assertIsNotNone(match, "CHUNK_AT regex must match line without speed/eta")
    state = TransferStateParser.parse_chunk_at(match)
    self.assertIsNone(state.speed)
    self.assertIsNone(state.eta)
```

---

## Shared Patterns

### Pattern A: `self.addCleanup()` for Guaranteed Resource Teardown

**Source:** Phase 87 PYFIX-03/04 pattern, Python stdlib `unittest.TestCase.addCleanup`
**Apply to:** PYFIX-14 (TemporaryDirectory cleanup in test_web_app.py)

```python
# Register cleanup immediately after resource creation:
app, _tmpd = _make_web_app_with_index(api_token="token")
self.addCleanup(_tmpd.cleanup)
```

Runs cleanup **after** the test, **even on assertion failure** or exception. Stack-based (LIFO): last registered runs first.

### Pattern B: Logger Handler Cleanup in unittest.TestCase

**Source:** `tests/conftest.py` lines 35-46 (Phase 87 PYFIX-07)
**Apply to:** PYFIX-16 across all 5 files

```python
# In setUp:
self._test_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
self._test_handler.setFormatter(formatter)
logger.addHandler(self._test_handler)

# In tearDown:
logger.removeHandler(self._test_handler)
```

Key: Store handler as instance attribute so `tearDown` can reference it. Use the same logger reference in both `setUp` and `tearDown` (root logger `logging.getLogger()` or named logger `logging.getLogger(ClassName.__name__)`).

### Pattern C: Busy-Wait Sleep Injection

**Source:** Standard Python best practice
**Apply to:** PYFIX-12 (scanner, 6 loops), PYFIX-18 (lftp, 41 loops)

```python
# Before (CPU spin):
while condition_not_met:
    pass

# After (yields CPU):
while condition_not_met:
    time.sleep(0.01)

# For `while True:` pattern:
while True:
    result = check_something()
    if result:
        break
    time.sleep(0.01)  # last line before loop repeats
```

### Pattern D: `threading.Event` for Interruptible Waits

**Source:** Python stdlib `threading.Event`
**Apply to:** PYFIX-13 (test_dispatch.py shutdown-race tests, test_extract_process.py callback sequence)

```python
# Create event:
self.shutdown_event = threading.Event()

# In side_effect callback (replaces time.sleep(0.5)):
self.shutdown_event.wait(0.5)  # returns immediately when event is set

# In test body, after calling stop():
self.shutdown_event.set()
```

### Pattern E: `Thread.join(timeout)` / `Process.join(timeout)` for Deterministic Sync

**Source:** Python stdlib `threading.Thread.join`, `multiprocessing.Process.join`
**Apply to:** PYFIX-17 (test_job.py), PYFIX-13 (test_multiprocessing_logger.py)

```python
# Replaces time.sleep(0.2) -- deterministic wait for thread completion:
job.start()
job.join(timeout=5.0)

# Replaces time.sleep(1) -- deterministic wait for process completion:
p_1.start()
mp_logger.start()
p_1.join(timeout=2)
time.sleep(0.05)  # small drain time for logger IPC queue
mp_logger.stop()
```

---

## No Analog Found

None. All fixes are targeted in-place edits to existing test files. All patterns are standard Python stdlib (`addCleanup`, `threading.Event`, `Thread.join`, `removeHandler`) already established in the codebase by Phase 87 or present in the stdlib.

---

## Metadata

**Analog search scope:** `src/python/tests/` (unittests + integration + conftest.py)
**Files scanned:** 14 source files read directly
**Pattern extraction date:** 2026-04-24

**Key insight:** Every fix is a targeted in-place edit. No new files, no new imports beyond `time` (in 2 files) and `bottle` (module-level move). All patterns are either self-analogs (same file provides the pattern) or cross-file patterns from `conftest.py` (Phase 87 PYFIX-07 established the `removeHandler` pattern). The RESEARCH.md provides comprehensive per-file strategies that align with the extracted code patterns.
