---
phase: 87-python-test-fixes-critical-warning
reviewed: 2026-04-25T01:27:26Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/python/tests/conftest.py
  - src/python/tests/integration/test_controller/test_controller.py
  - src/python/tests/integration/test_controller/test_extract/test_extract.py
  - src/python/tests/integration/test_web/test_handler/test_stream_model.py
  - src/python/tests/unittests/test_common/test_config.py
  - src/python/tests/unittests/test_controller/test_auto_queue.py
  - src/python/tests/unittests/test_controller/test_extract/test_extract_process.py
  - src/python/tests/unittests/test_controller/test_lftp_manager.py
  - src/python/tests/unittests/test_lftp/test_lftp.py
  - src/python/tests/unittests/test_web/test_handler/test_server_handler.py
  - src/python/tests/unittests/test_web/test_handler/test_status_handler.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 87: Code Review Report

**Reviewed:** 2026-04-25T01:27:26Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

The test suite spans integration tests (TestController, TestExtract, TestLftp) and a large set of unit tests (AutoQueue, ExtractProcess, LftpManager, config, web handlers). Overall quality is high: fixtures are well-structured, test isolation is good, and all spin-wait loops carry `@timeout_decorator` guards. No security issues were found.

Three warnings were identified: a file-descriptor leak in `test_to_file`, a flaky early-exit threshold in `__wait_for_initial_model`, and a logic gap in `test_extract_process.py` where a signal-driven callback thread is detached with no join/cancel. Five informational items cover leftover `print()` debug statements and one minor naming inconsistency.

## Warnings

### WR-01: File descriptor leak in `test_to_file`

**File:** `src/python/tests/unittests/test_common/test_config.py:501`
**Issue:** `tempfile.NamedTemporaryFile(suffix="test_config", delete=False).name` creates a `NamedTemporaryFile` object and immediately discards it. The underlying file descriptor is leaked until CPython's garbage collector finalises the object. On CI hosts with strict fd limits this can cause `Too many open files` failures in long test runs, and the behavior is undefined on non-CPython runtimes.
**Fix:** Extract the file handle so it can be explicitly closed before being removed:
```python
_tmp = tempfile.NamedTemporaryFile(suffix="test_config", delete=False)
config_file_path = _tmp.name
_tmp.close()
self.addCleanup(os.remove, config_file_path)
```

### WR-02: Race-prone early-exit threshold in `__wait_for_initial_model`

**File:** `src/python/tests/integration/test_controller/test_controller.py:382-383`
**Issue:** `__wait_for_initial_model` spins until `get_model_files()` returns at least 5 entries, but `initial_state` has 9 top-level files. Any test that calls this helper and then immediately reads the model (e.g. `test_initial_model`) can observe a partially-populated model at the moment `__wait_for_initial_model` returns, and then spin the outer loop further—but tests that do _not_ spin further (e.g. those that add a listener right after the helper) may act on an incomplete model, producing intermittent assertion failures. The comment at line 382 (`# wait for initial scan`) implies intent to wait for the full scan, not just half of it.
**Fix:** Change the threshold to match the actual initial state size:
```python
def __wait_for_initial_model(self):
    while len(self.controller.get_model_files()) < len(self.initial_state):
        self.controller.process()
```

### WR-03: Detached callback thread in `test_retrieves_completed` has no cleanup path

**File:** `src/python/tests/unittests/test_controller/test_extract/test_extract_process.py:182-183`
**Issue:** Inside the `_add_listener` side-effect, a `threading.Thread(target=_callback_sequence).start()` is launched without saving a reference. If the test times out (guarded by `@timeout_decorator.timeout(10)`) before `completed_signal.value` reaches 2, the thread continues executing in the background, calling `listener.extract_completed` on an already-terminated `ExtractProcess`. This can corrupt shared `multiprocessing.Value` state that bleeds into subsequent tests or produce spurious error output from the background thread.
**Fix:** Save the thread reference and join it with a timeout in `tearDown`, or use `daemon=True` so the thread is forcibly killed when the test process exits the timeout:
```python
t = threading.Thread(target=_callback_sequence, daemon=True)
t.start()
```

## Info

### IN-01: Debug `print()` calls in `test_auto_queue.py`

**File:** `src/python/tests/unittests/test_controller/test_auto_queue.py:201-202,222`
**Issue:** Three bare `print()` calls are left in `test_from_str` (lines 201, 202) and `test_to_str` (line 222). They produce noise in CI output and appear to be development-time debugging rather than intentional diagnostic logging.
**Fix:** Remove the three `print()` calls, or replace with `self.logger.debug(...)` if the content is genuinely useful for diagnosing failures.

### IN-02: Debug `print()` call in `test_config.py`

**File:** `src/python/tests/unittests/test_common/test_config.py:548`
**Issue:** `print(actual_str)` in `test_to_file` echoes the full serialised config to stdout on every test run. The content is already asserted line-by-line immediately below, so the print adds no diagnostic value.
**Fix:** Remove line 548.

### IN-03: Debug `print()` calls in `test_extract_process.py`

**File:** `src/python/tests/unittests/test_controller/test_extract/test_extract_process.py:169,236`
**Issue:** Two `print()` calls (`"Listener added"` and `file.name`) are inside mock side-effects. They pollute CI output each time the mock is triggered.
**Fix:** Remove both `print()` calls.

### IN-04: Debug `print()` calls in `test_lftp.py`

**File:** `src/python/tests/unittests/test_lftp/test_lftp.py:27`
**Issue:** `print(f"Temp dir: {TestLftp.temp_dir}")` in `setUpClass` runs on every test-class instantiation. The temp dir path is only useful when debugging a specific test failure.
**Fix:** Remove the `print()` call; the temp dir path will appear in the traceback if a file-not-found error occurs.

### IN-05: `mock_context` fixture exposes a plaintext password attribute without `@pytest.mark.sensitive` or equivalent masking

**File:** `src/python/tests/conftest.py:67`
**Issue:** `context.config.lftp.remote_password = "password"` sets a plaintext string on a shared fixture. While the inline comment correctly notes this is a test-only credential, some pytest reporter plugins (e.g. `pytest-html`) can capture fixture parameters and write them to an HTML report in plaintext. This is low-risk in practice but worth noting.
**Fix:** No code change is required if test reports are not shared externally. If HTML reports are generated and retained, consider using a redacted placeholder (`"<test-password>"`) and noting that any authentication under test uses the mock, not a real connection. The comment already documents intent correctly; this is an informational observation only.

---

_Reviewed: 2026-04-25T01:27:26Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
