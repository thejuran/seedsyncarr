# Test Suite Hardening — Deep Review Findings

**Reviewed:** 2026-04-24
**Scope:** Python test suite (`src/python/tests/`) — 72 test files, 1,227 tests, 68 source modules
**Context:** Findings surfaced during phase 83 (python test audit) deep review. All items are out of scope for the v1.1.2 Test Suite Audit milestone per REQUIREMENTS.md exclusions (no refactoring test infrastructure, no writing new tests, no updating fixtures, no performance optimization).

---

## Critical (95-100) — False Coverage

### C-01: Thread target called instead of passed — concurrency never tested
- **File:** `tests/unittests/test_controller/test_extract/test_extract_process.py:182`
- **Confidence:** 98
- **Issue:** `threading.Thread(target=_callback_sequence()).start()` calls `_callback_sequence()` immediately (note parentheses), passes `None` as thread target. The callback fires synchronously before the process starts, `completed_signal` is set prematurely, and the busy-wait exits without `ExtractProcess` doing any real work. The test claims to verify concurrent extraction completion but exercises zero concurrency.
- **Fix:**
  ```diff
  - threading.Thread(target=_callback_sequence()).start()
  + threading.Thread(target=_callback_sequence).start()
  ```
- **Impact:** Extract-completion concurrency has zero real test coverage. The 85.05% coverage baseline counts this as "covered."

### C-02: Assertion-less test — always passes regardless of behavior
- **File:** `tests/unittests/test_controller/test_lftp_manager.py:83-98`
- **Confidence:** 97
- **Issue:** `test_init_skips_rate_limit_when_zero` body is just `pass`. If production code starts writing `rate_limit=0` when it shouldn't, this test won't catch it.
- **Fix:** Assert that `mock_lftp.mock_calls` does not contain a `rate_limit` attribute assignment.
- **Impact:** Rate-limit-skip behavior is unverified. Inflates coverage metrics with false confidence.

---

## Warning (80-94) — Security & Correctness

### W-01: Temp file with credentials never deleted
- **File:** `tests/unittests/test_common/test_config.py:503`
- **Confidence:** 92
- **Issue:** `NamedTemporaryFile(delete=False)` creates a file containing plaintext passwords (`pass-on-remote-server`, `abc123`) that persists in `/tmp` indefinitely. On shared CI runners, any co-tenant process can read it.
- **Fix:** Add `self.addCleanup(lambda: os.unlink(config_file_path) if os.path.exists(config_file_path) else None)`.

### W-02: Temp file leaked on test failure
- **File:** `tests/unittests/test_common/test_config.py:413`
- **Confidence:** 88
- **Issue:** `os.remove(config_file.name)` at line ~500 is only reached if all assertions pass. On failure, the file with plaintext `remote_password=remote-pass` lingers.
- **Fix:** Add `self.addCleanup(...)` immediately after creation.

### W-03: Mock class vs instance confusion — silent refactor breakage
- **File:** `tests/unittests/test_web/test_handler/test_status_handler.py:13-28`
- **Confidence:** 90
- **Issue:** `@patch('web.handler.status.SerializeStatusJson')` replaces the class. Test asserts on `mock_serialize_cls.status` (classmethod path). If production switches to instance method, MagicMock's transparent attribute access masks the breakage silently.
- **Fix:** Add a guard assertion that checks both call paths.

### W-04: Group-writable permissions walked up to /tmp
- **File:** `tests/integration/test_lftp/test_lftp.py:24`
- **Confidence:** 85
- **Issue:** `TestUtils.chmod_from_to(temp_dir, tempfile.gettempdir(), 0o775)` sets every ancestor directory up to `/tmp` as group-writable, exposing sibling temp dirs on shared systems.
- **Fix:** `os.chmod(TestLftp.temp_dir, 0o750)` — only the leaf directory.

### W-05: Logger fixture leaks handlers across runs
- **File:** `tests/conftest.py:36-43`
- **Confidence:** 82
- **Issue:** `test_logger` fixture doesn't disable `propagate` or reset the level on teardown. Parametrized tests with the same node name accumulate duplicate handlers.
- **Fix:** Set `logger.propagate = False` before yield, reset `logger.setLevel(logging.NOTSET)` after.

### W-06: Implicit `unittest.mock.ANY` import via side effect
- **Files:** `tests/unittests/test_controller/test_auto_queue.py` (19 occurrences), `tests/integration/test_web/test_handler/test_stream_model.py`, `tests/unittests/test_web/test_handler/test_server_handler.py`
- **Confidence:** 85
- **Issue:** Files reference `unittest.mock.ANY` by qualifying through `unittest` module, which only works because `from unittest.mock import MagicMock` loaded `unittest.mock` as a side effect. Fragile if import line is removed.
- **Fix:** Add `ANY` to the `from unittest.mock import` line explicitly.

### W-07: Resource leak — bare `open(os.devnull)` without context manager
- **Files:** `tests/integration/test_controller/test_extract/test_extract.py:51`, `tests/integration/test_controller/test_controller.py:88`
- **Confidence:** 95
- **Issue:** `fnull = open(os.devnull, 'w')` in `setUpClass` without `with` statement. File handle never explicitly closed; triggers `ResourceWarning` under `-Wd`.
- **Fix:** Wrap in `with open(os.devnull, 'w') as fnull:`.

### W-08: Resource leak — bare `open()` in `create_large_file` helper
- **File:** `tests/integration/test_controller/test_controller.py:2276-2279`
- **Confidence:** 92
- **Issue:** `f = open(_path, "wb")` with manual `f.close()` — no try/finally. If `f.seek()` or `f.write()` raises, 140 MB file handle leaks.
- **Fix:** Use `with open(_path, "wb") as f:`.

---

## Medium (70-79) — Correctness & Performance

### M-01: No test for HTML-escaping token in meta tag
- **File:** `tests/unittests/test_web/test_web_app.py:142`
- **Confidence:** 78
- **Issue:** Tests verify `api_token` is injected into `<meta content="...">` but never test with `"`, `<`, or `>` characters. A missing HTML escape would be a stored XSS.
- **Fix:** Add a test with `api_token='tok"><script>alert(1)</script>'` and assert `<script>` is not in response.

### M-02: Busy-wait race condition in scanner tests
- **File:** `tests/unittests/test_controller/test_scan/test_scanner_process.py:82-141`
- **Confidence:** 72
- **Issue:** `while self.scan_counter.value < N: pass` busy-spins without yielding. The `orig_counter` snapshot is taken after the signal write, creating a TOCTOU window.
- **Fix:** Add `time.sleep(0.001)` in the loop body; take `orig_counter` before setting the signal.

### M-03: Performance — real `time.sleep` in unit tests
- **Files:**
  - `tests/unittests/test_web/test_handler/test_controller_handler.py:672` — 150ms sleep for rate-limit window (confidence: 82)
  - `tests/unittests/test_common/test_multiprocessing_logger.py:41,67` — 1-second sleep per test (confidence: 75)
  - `tests/unittests/test_controller/test_extract/test_extract_process.py:176,274` — 1-second sleep per test (confidence: 73)
  - `tests/unittests/test_controller/test_extract/test_dispatch.py:229,566` — 500ms sleep-as-sync (confidence: 78)
- **Issue:** ~4.5 seconds of wall-clock sleeps in unit tests per run. Should use mock time or threading.Event for deterministic synchronization.

### M-04: `TemporaryDirectory` cleanup depends on GC
- **File:** `tests/unittests/test_web/test_web_app.py:45-62`
- **Confidence:** 78
- **Issue:** `_make_web_app_with_index` returns a `TemporaryDirectory` object that callers hold as `_tmpd` without calling `.cleanup()`. Under Python 3.12+ emits `ResourceWarning`.
- **Fix:** Add `self.addCleanup(_tmpd.cleanup)` after each call.

### M-05: Implicit local import of `bottle` inside closure
- **File:** `tests/unittests/test_web/test_auth.py:213,237`
- **Confidence:** 72
- **Issue:** `import bottle` inside a closure on every call rather than at module level. Hidden dependency that bypasses declared imports.
- **Fix:** Move `import bottle` to module level.

---

## Architectural Findings

### A-01: Conftest fixtures are never consumed
- **Confidence:** 91
- **Issue:** `conftest.py` defines 3 well-designed pytest fixtures (`test_logger`, `mock_context`, `mock_context_with_real_config`) that are used by zero test files. All 1,227 tests use `unittest.TestCase` with `setUp()`. The lftp config setup is duplicated by hand in at least 3 test files (18+ attribute assignments each).
- **Recommendation:** Either adopt pytest-style tests or convert conftest fixtures to importable helpers callable from `setUp()`.

### A-02: Duplicated base test classes
- **Confidence:** 88
- **Issue:** `BaseControllerTestCase` (in `test_controller_unit.py`) and `BaseAutoDeleteTestCase` (in `test_auto_delete.py`) are 95% identical — differ by 3 config attributes and a timer cleanup in `tearDown`. No shared parent.
- **Recommendation:** Consolidate into a single base class with configurable constructor options.

### A-03: Misclassified integration test
- **Confidence:** 86
- **Issue:** `tests/unittests/test_lftp/test_lftp.py` uses a real `Lftp` object connecting to localhost SSH — functionally an integration test. Running "unit tests only" fails without an SSH daemon.
- **Recommendation:** Move to `integration/test_lftp/` or add `@unittest.skipUnless(shutil.which("lftp"), ...)`.

### A-04: Coverage gaps — modules without dedicated tests
- **Confidence:** 88
- **Modules missing tests:**
  - `controller/scan/active_scanner.py` — `ActiveScanner` only tested indirectly through `ScanManager` mocks
  - `web/web_app_job.py` — `WebAppJob` top-level job wrapper, no unit test
  - `web/web_app_builder.py` — `WebAppBuilder`, no unit test
  - `scan_fs.py` — CLI utility, no integration tests
- **SSE gap:** All integration-level SSE tests are `@unittest.skip("webtest doesn't support SSE streaming")`.

### A-05: Private-API coupling via name-mangling
- **Confidence:** 82
- **Issue:** 100+ uses of Python name-mangling (`_Controller__model`, `_Controller__started`, `_Controller__pending_auto_deletes`) in `test_controller_unit.py` and `test_auto_delete.py`. Integration tests reach two levels deep (`_Controller__lftp_manager.lftp.rate_limit`). Any private attribute rename silently breaks many tests.
- **Recommendation:** Accept as trade-off for thorough internal testing, but document the coupling.

### A-06: Duplicated INI strings in config encryption tests
- **Confidence:** 84
- **Issue:** `test_config.py` encryption tests at lines 680-720, 780-843, and 905-961 construct full multi-section INI strings from scratch (3 copies). A new required config field means updating all three.
- **Recommendation:** Extract into a module-level constant, mirroring the `_build_plaintext_config()` helper pattern.

---

## CLAUDE.md Compliance

The test suite is **compliant** across 13/14 rules checked:

| Rule | Status |
|------|--------|
| Coverage minimum 84% (`fail_under = 84`) | Compliant |
| Pytest timeout 60s per test | Compliant |
| Test file naming `test_*.py` | Compliant |
| Test class naming `TestXxx(unittest.TestCase)` | Compliant |
| Test method naming `test_*` prefix | Compliant |
| `setUp`/`tearDown` lifecycle with cleanup | Compliant |
| Real `Config`/`Status`, `MagicMock` for services | Compliant |
| Patch at module-under-test's import location | Compliant |
| Private methods via name-mangling | Compliant |
| `@unittest.skipIf` for env/platform dependencies | Compliant |
| Test credentials annotated as non-production | Compliant |
| `cache_dir` not overridden | Compliant |
| Integration web tests inherit `BaseTestWebApp` | Compliant |
| `ruff` linter compliance | **Partial** — no `[tool.ruff]` config section; long lines in `test_config.py` |

---

## Suggested Milestone Structure

If this work is prioritized, a natural breakdown:

1. **Wave 1 — False Coverage Fixes** (C-01, C-02): Fix the two tests that inflate coverage numbers without verifying behavior. Low risk, high value.
2. **Wave 2 — Security Hygiene** (W-01, W-02, W-04, W-07, W-08): Temp file cleanup, permissions fix, resource leaks. All mechanical fixes.
3. **Wave 3 — Correctness** (W-03, W-05, W-06, M-01, M-02): Mock confusion, logger leak, implicit imports, XSS test, race condition.
4. **Wave 4 — Architecture** (A-01 through A-06): Infrastructure improvements — conftest adoption, base class consolidation, test reclassification.
5. **Wave 5 — Performance** (M-03): Replace wall-clock sleeps with mock time / events. Lower priority but saves ~4.5s per run.

---

*Generated by deep code review, 2026-04-24. All file paths relative to `src/python/`.*
