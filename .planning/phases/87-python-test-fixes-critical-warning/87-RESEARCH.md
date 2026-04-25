# Phase 87: Python Test Fixes -- Critical & Warning - Research

**Researched:** 2026-04-24
**Domain:** Python unittest / pytest test quality — false coverage, resource leaks, mock correctness
**Confidence:** HIGH

## Summary

This phase fixes 10 specific, already-audited Python test defects: 2 critical false-coverage bugs (PYFIX-01: thread target called instead of passed; PYFIX-02: assertion-less test) and 8 warning-level issues spanning resource leaks, mock confusion, permission escalation, logger fixture state, implicit imports, and unclosed file handles.

All bug locations are precisely documented in the TEST-HARDENING-REVIEW.md audit (`.planning/backlog/TEST-HARDENING-REVIEW.md`) and verified by reading the live source files in this session. No architectural changes are involved — every fix is a targeted edit within an existing test file.

The test suite runs inside Docker via `make run-tests-python` (1262 tests, 85% coverage floor — actual `fail_under = 84` per pyproject.toml). Tests use `unittest.TestCase` with `setUp/tearDown` patterns, run by pytest. All fixes must leave the coverage number at or above the existing threshold.

**Primary recommendation:** Fix each bug in-place using the smallest change that eliminates the defect. No new test files needed. Use `self.addCleanup()` for resource cleanup (robust to failure), explicit `from unittest.mock import ANY` for import clarity, and `with` statements for file handles.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Claude's Discretion
User elected to skip discussion — all implementation decisions are at Claude's discretion. Requirements are fully specified in REQUIREMENTS.md (PYFIX-01 through PYFIX-10) with exact file locations and bug descriptions. No ambiguity in what needs fixing.

Key areas left to Claude:
- **D-01:** Fix strategy for PYFIX-01 (thread target bug) and PYFIX-02 (assertion-less test) -- fix in place vs rewrite
- **D-02:** Resource cleanup approach for PYFIX-03/04/09/10 -- context managers, addCleanup, or tmpdir fixtures
- **D-03:** Logger infrastructure fix for PYFIX-07 (conftest handler leak) and PYFIX-08 (implicit ANY import) -- fixture vs setUp/tearDown
- **D-04:** Permissions fix scope for PYFIX-06 -- chmod scoping strategy
- **D-05:** Mock restructuring approach for PYFIX-05 (class vs instance confusion)

### Locked Decisions
None — user skipped discussion.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PYFIX-01 | Fix `threading.Thread(target=_callback_sequence())` — target called instead of passed, concurrency never tested | Remove `()` so `_callback_sequence` is passed as callable, not called. Thread then runs the function. |
| PYFIX-02 | Fix assertion-less `test_init_skips_rate_limit_when_zero` — always passes regardless of behavior | Use `mock_lftp.rate_limit.assert_not_called()` or check `mock_lftp.__dict__` / `_mock_children`. See research below. |
| PYFIX-03 | Fix temp file with credentials never deleted in `test_config.py:503` | `test_to_file` never removes the file. Add `self.addCleanup(os.remove, config_file_path)` immediately after creation. |
| PYFIX-04 | Fix temp file leaked on test failure in `test_config.py:413` | `test_from_file` calls `os.remove` only at end. Wrap with `self.addCleanup(...)` so it runs even on assertion failure. |
| PYFIX-05 | Fix mock class vs instance confusion in `test_status_handler.py` | Tests mock the `SerializeStatusJson` class but set up `.status` on the mock class directly. Issue: fragile if production switches to instance. Add guard assertion distinguishing class-call vs instance-call path. |
| PYFIX-06 | Fix group-writable permissions walked up to /tmp in `test_lftp.py:24` | Replace `TestUtils.chmod_from_to(temp_dir, tempfile.gettempdir(), 0o775)` with `os.chmod(TestLftp.temp_dir, 0o750)` — leaf-dir only. |
| PYFIX-07 | Fix logger fixture handler leak and propagation in `conftest.py` | Add `logger.propagate = False` before yield; add `logger.setLevel(logging.NOTSET)` and `logger.propagate = True` in teardown. |
| PYFIX-08 | Fix implicit `unittest.mock.ANY` import via side effect across 3+ files | Add `ANY` to explicit `from unittest.mock import` lines in 3 files. |
| PYFIX-09 | Fix resource leak — bare `open(os.devnull)` without context manager in 2 integration tests | Wrap with `with open(os.devnull, 'w') as fnull:` at both locations. |
| PYFIX-10 | Fix resource leak — bare `open()` in `create_large_file` helper | Replace `f = open(...)` / `f.close()` pattern with `with open(...) as f:`. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Thread concurrency testing | Test layer | — | unittest/threading — no production code change |
| Resource cleanup | Test layer | — | addCleanup / context managers in test setup/teardown |
| Mock correctness | Test layer | — | unittest.mock API usage in test assertions |
| File permission safety | Test layer | — | chmod scope limited to test temp directories |
| Logger fixture state | Test infrastructure (conftest.py) | — | Shared pytest fixtures affect all tests that request them |
| Import hygiene | Test layer | — | Explicit imports in test files, no production impact |

## Standard Stack

### Core (already in use — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | ^9.0.3 | Test runner | Project standard [VERIFIED: pyproject.toml] |
| pytest-cov | ^7.1.0 | Coverage enforcement | `fail_under = 84` [VERIFIED: pyproject.toml] |
| pytest-timeout | ^2.3.1 | Test timeout guard | 60s default [VERIFIED: pyproject.toml] |
| unittest.TestCase | stdlib | Test class base | All existing tests use this pattern [VERIFIED: source] |
| unittest.mock | stdlib | Mocking | MagicMock, patch, ANY [VERIFIED: source] |

No new packages required. All fixes use stdlib or already-installed libraries.

**Installation:** None needed.

## Architecture Patterns

### System Architecture Diagram

```
make run-tests-python
       |
       v
Docker compose (src/docker/test/python/compose.yml)
       |
       v
pytest runner (poetry run pytest --cov ...)
       |
       +-- conftest.py fixtures (test_logger, mock_context)
       |
       +-- unittests/         (unittest.TestCase classes)
       |     test_common/test_config.py         PYFIX-03, PYFIX-04
       |     test_controller/test_lftp_manager.py  PYFIX-02
       |     test_controller/test_extract/...   PYFIX-01
       |     test_web/test_handler/test_status_handler.py  PYFIX-05
       |     test_lftp/test_lftp.py             PYFIX-06
       |
       +-- integration/       (integration tests, Docker services required)
             test_controller/test_controller.py   PYFIX-09, PYFIX-10
             test_controller/test_extract/...     PYFIX-09

Coverage threshold: fail_under = 84 (pyproject.toml line 91)
```

### Recommended Project Structure
No structural changes. All fixes are in-place edits to existing test files.

### Pattern 1: addCleanup for guaranteed teardown (PYFIX-03, PYFIX-04)

**What:** `self.addCleanup(fn, *args)` registers a function to be called after the test completes, whether it passes or fails. Superior to cleanup code at the end of the test body.

**When to use:** Any resource created in a test that must be cleaned up even on assertion failure.

```python
# Source: Python stdlib unittest docs [ASSUMED - standard well-known API]
# PYFIX-03 fix: test_to_file
config_file_path = tempfile.NamedTemporaryFile(suffix="test_config", delete=False).name
self.addCleanup(os.remove, config_file_path)

# PYFIX-04 fix: test_from_file
config_file = tempfile.NamedTemporaryFile(mode="w", suffix="test_config", delete=False)
self.addCleanup(os.remove, config_file.name)
self.addCleanup(config_file.close)
```

### Pattern 2: Context manager for file handles (PYFIX-09, PYFIX-10)

**What:** `with open(...) as f:` guarantees file handle closure even on exception.

**When to use:** Every `open()` call that isn't immediately inside a `with` block.

```python
# PYFIX-09 fix: setUpClass in two integration test files
with open(os.devnull, 'w') as fnull:
    subprocess.Popen([...], stdout=fnull).communicate()

# PYFIX-10 fix: create_large_file helper
with open(_path, "wb") as f:
    f.seek(size - 1)
    f.write(b"\0")
```

### Pattern 3: Thread target as callable (PYFIX-01)

**What:** `threading.Thread(target=fn)` expects a callable. `threading.Thread(target=fn())` calls the function immediately in the current thread and passes its return value (typically `None`) as target — so the Thread never runs the body.

```python
# BEFORE (buggy): _callback_sequence() called here, Thread gets None as target
threading.Thread(target=_callback_sequence()).start()

# AFTER (correct): _callback_sequence passed as callable, Thread calls it
threading.Thread(target=_callback_sequence).start()
```

### Pattern 4: Asserting attribute NOT set on MagicMock (PYFIX-02)

**What:** MagicMock auto-creates attributes on access, so checking `hasattr` or `mock.rate_limit` always succeeds. The correct approach checks whether an assignment was recorded.

```python
# AFTER (correct): verify rate_limit was never assigned
# MagicMock tracks attribute *assignments* via mock_calls
# Two viable approaches:

# Option A: assert rate_limit is still the MagicMock auto-attribute (not assigned to 0)
self.assertNotEqual(mock_lftp.rate_limit, 0)

# Option B: check mock_calls does not include an assignment
rate_limit_sets = [c for c in mock_lftp.mock_calls
                   if 'rate_limit' in str(c) and '=' in str(c)]
self.assertEqual([], rate_limit_sets)

# Option C (cleaner): check that the attribute setter was not called by inspecting
# the mock's _mock_children does not contain rate_limit with value 0
# The simplest reliable check for "rate_limit was not set to 0":
self.assertNotEqual(mock_lftp.rate_limit, 0)
```

The production code sets `self.__lftp.rate_limit = context.config.lftp.rate_limit` only when rate_limit > 0. When 0, it is skipped. So `mock_lftp.rate_limit` will be a fresh MagicMock auto-attribute (not `0`). `assertNotEqual(mock_lftp.rate_limit, 0)` is the simplest assertion. [VERIFIED: lftp_manager.py lines 57-58]

### Pattern 5: Logger fixture propagation reset (PYFIX-07)

**What:** `logging.getLogger(name)` returns the same logger instance for the same name across calls. Without resetting, handlers accumulate across test runs (especially with parametrized tests).

```python
# conftest.py test_logger fixture — AFTER fix
@pytest.fixture
def test_logger(request):
    logger = logging.getLogger(request.node.name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False   # ADD: prevent double-logging to root
    yield logger
    logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)   # ADD: reset level
    logger.propagate = True           # ADD: restore default
```

### Pattern 6: Explicit ANY import (PYFIX-08)

**What:** `unittest.mock.ANY` works by qualified access only because `from unittest.mock import MagicMock` already loaded the `unittest.mock` module into `sys.modules`. If that import line changes, qualified access breaks silently (no ImportError — it resolves via `unittest` module's `mock` attribute but only after the side-effect load). Explicit import eliminates fragility.

```python
# BEFORE (fragile — 3 files)
from unittest.mock import MagicMock
# ... uses unittest.mock.ANY relying on side-effect

# AFTER (explicit)
from unittest.mock import MagicMock, ANY
# ... uses unittest.mock.ANY or just ANY
```

Files requiring this fix [VERIFIED: source grep]:
1. `tests/unittests/test_controller/test_auto_queue.py` — 19 occurrences of `unittest.mock.ANY`
2. `tests/integration/test_web/test_handler/test_stream_model.py` — 1 occurrence
3. `tests/unittests/test_web/test_handler/test_server_handler.py` — 1 occurrence

Note: These files may keep using `unittest.mock.ANY` (qualified) or switch to bare `ANY` — either works after adding `ANY` to the import line.

### Pattern 7: PYFIX-05 mock class vs instance guard

The production `StatusHandler.__handle_get_status` calls `SerializeStatusJson.status(self.__status)` as a **class-level static/class method** [VERIFIED: web/handler/status.py line 16]. The test patches at the class level and calls `mock_serialize_cls.status.return_value`. This is currently consistent.

The audit warning (W-03) is that if production switches to instance-method call (`SerializeStatusJson().status(...)`), MagicMock's auto-attribute creation masks the breakage — tests still pass because `mock_serialize_cls.return_value.status` is auto-created and returns a MagicMock that evaluates truthy.

**Fix:** Add a guard assertion that verifies the class-level call actually happened — `mock_serialize_cls.status.assert_called_once_with(self.mock_status)` already does this in one test. The other two tests set up the return value but don't assert the call was made on the class. Add `mock_serialize_cls.status.assert_called_once_with(...)` to the two tests that lack it.

### Pattern 8: PYFIX-06 chmod scope

**What:** `TestUtils.chmod_from_to(temp_dir, tempfile.gettempdir(), 0o775)` walks upward through ancestors to `/tmp`, setting each to group-writable (0o775). This modifies `/tmp` and its subdirectories for the test user's group — a security overreach.

**Fix:** Replace the `chmod_from_to` call with a targeted `os.chmod` on the leaf directory only:
```python
# BEFORE:
TestUtils.chmod_from_to(TestLftp.temp_dir, tempfile.gettempdir(), 0o775)

# AFTER: only chmod the leaf — the test's own temp dir
os.chmod(TestLftp.temp_dir, 0o750)
```

Note: The SFTP test user (`seedsyncarrtest`) needs group-read access to the temp dir. `0o750` (owner rwx, group rx, other none) is sufficient. `0o755` is also acceptable if public-read is needed. The key fix is stopping at the leaf. [VERIFIED: test_lftp.py line 30, utils.py]

### Anti-Patterns to Avoid

- **cleanup at end of test body:** `os.remove(path)` at the bottom is skipped on assertion failure. Always use `addCleanup` or a context manager.
- **`pass` as test body:** A test with only `pass` will always green regardless of what the code does. Replace with a real assertion.
- **`open()` without `with`:** Even with explicit `.close()`, any exception between open and close leaks the handle. Always use `with`.
- **Modifying shared mutable state in fixtures without teardown:** Logger instances are global (`logging.getLogger` returns same object). Always reset to pre-test state in teardown.
- **Relying on import side-effects for names:** `unittest.mock.ANY` works only if `unittest.mock` has been imported elsewhere. Be explicit.
- **Granting permissions to ancestor directories:** Test isolation requires the minimum footprint. Never chmod ancestors shared with other processes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Guaranteed cleanup | Custom try/finally in test body | `self.addCleanup()` | Runs even on setUp failure, stacks correctly, unittest native |
| File handle safety | Manual `.close()` with try/finally | `with open(...) as f:` | Context manager is idiomatic, exception-safe, PEP 343 |
| Thread synchronization | Busy-wait loops (`while flag < N: pass`) | `threading.Event` or short sleeps (out of scope for this phase) | Not in scope — phase 88 |

**Key insight:** Python's `addCleanup` and context managers already solve every resource-safety problem in this phase. No custom infrastructure needed.

## Runtime State Inventory

> Phase involves test file edits only. No rename/refactor of identifiers.

Not applicable — this is a targeted bug-fix phase. No stored state, renamed identifiers, or runtime registrations are involved.

## Common Pitfalls

### Pitfall 1: MagicMock makes "not set" assertions tricky

**What goes wrong:** `mock.some_attr` on an unaccessed MagicMock auto-creates the attribute and returns a MagicMock, so `self.assertIsNone(mock.rate_limit)` always fails (it's a MagicMock, not None). And `assertIsNotNone` always passes trivially.

**Why it happens:** MagicMock's `__getattr__` creates child mocks on first access. The assignment `mock.rate_limit = 0` writes to `_mock_children` AND records in `mock_calls`. Accessing `mock.rate_limit` without prior assignment also creates a child mock but does NOT record in `mock_calls`.

**How to avoid:** To assert "attribute was NOT explicitly assigned to X": use `assertNotEqual(mock.rate_limit, 0)`. The auto-created MagicMock attribute will not equal `0`. [VERIFIED: production code at lftp_manager.py line 57-58]

**Warning signs:** A test with `pass` as its entire body (PYFIX-02 current state).

### Pitfall 2: Thread.start() returns before the thread body executes

**What goes wrong:** After fixing PYFIX-01 (removing `()`), the test depends on `self.completed_signal.value < 1` busy-wait to synchronize. This loop must actually be in the calling thread while `_callback_sequence` runs in the spawned thread. With the bug present, `_callback_sequence` runs synchronously and returns before `Thread.start()` is called — so `completed_signal` reaches 1 before the wait loop even begins. After the fix, the wait loop is actually needed.

**Why it happens:** The test was "working" (not hanging) only because the threading was broken.

**How to avoid:** After removing `()`, verify the test still passes by confirming the wait loops (`while self.completed_signal.value < 1`) gate on the background thread. They do — the test logic is correct for the fixed version.

**Warning signs:** Test hangs after fix (would indicate signal never set), or test passes instantly (would indicate signal still set synchronously).

### Pitfall 3: addCleanup ordering

**What goes wrong:** If `addCleanup(config_file.close)` and `addCleanup(os.remove, config_file.name)` are registered, they run in LIFO (last-in, first-out) order. Removing before closing raises `PermissionError` on some platforms.

**Why it happens:** `addCleanup` is a stack.

**How to avoid:** Register close first (so it runs last), then register remove (so it runs first):
```python
self.addCleanup(os.remove, config_file.name)  # registered first = runs last... wait:
# Actually: LIFO means LAST registered runs FIRST.
# So register remove LAST so it runs FIRST? No — we want close FIRST, then remove.
# Register in this order:
self.addCleanup(config_file.close)   # registered first → runs LAST
self.addCleanup(os.remove, config_file.name)  # registered last → runs FIRST
# Result: file is closed, then removed. Correct.
```

Wait — re-check: Python docs say "cleanup functions will be called in reverse order of registration (i.e., LIFO)." So the LAST registered runs FIRST. To run `close` before `remove`: register `remove` first, then register `close`.

```python
self.addCleanup(os.remove, config_file.name)  # runs SECOND
self.addCleanup(config_file.close)            # runs FIRST (registered last)
```

**Warning signs:** `PermissionError` or `FileNotFoundError` during cleanup.

Note: For `test_to_file` (PYFIX-03), the file is created and immediately closed (`.name` only is kept), so only `addCleanup(os.remove, config_file_path)` is needed.

### Pitfall 4: Logger.propagate default

**What goes wrong:** Not resetting `logger.propagate` in teardown leaves it as `False` for any subsequent test that reuses the same logger name (only possible with parametrized tests sharing `request.node.name` — unlikely but not impossible).

**Why it happens:** Logger instances are global singletons keyed by name. `logging.getLogger("foo")` always returns the same object.

**How to avoid:** Always restore `propagate = True` in teardown (the Python default). [VERIFIED: Python logging module documentation, ASSUMED for exact reset behavior]

### Pitfall 5: Test was passing due to MagicMock transparency (PYFIX-05)

**What goes wrong:** `mock_serialize_cls.status.return_value = '...'` sets up the return value but if production code calls `SerializeStatusJson().status(...)` (instance method) instead, it would use `mock_serialize_cls.return_value.status.return_value` — a different path. Since MagicMock creates both, both calls succeed and return MagicMocks. Tests appear green but don't verify the right code path.

**How to avoid:** In tests 1 and 2 (which currently only set up the return value but don't assert the call), add `mock_serialize_cls.status.assert_called_once_with(self.mock_status)`. Test 3 already has this assertion.

## Code Examples

### PYFIX-01: Thread target fix
```python
# Source: test_extract_process.py line 182 [VERIFIED]
# BEFORE:
threading.Thread(target=_callback_sequence()).start()
# AFTER:
threading.Thread(target=_callback_sequence).start()
```

### PYFIX-02: Assertion for rate-limit skip
```python
# Source: test_lftp_manager.py line 83-98 [VERIFIED]
# AFTER (replace pass with assertion):
manager = LftpManager(self.mock_context)  # noqa: F841
# MagicMock auto-creates rate_limit on access, but does NOT make it equal to 0
self.assertNotEqual(mock_lftp.rate_limit, 0)
```

### PYFIX-03: Cleanup for test_to_file
```python
# Source: test_config.py line 503 [VERIFIED]
config_file_path = tempfile.NamedTemporaryFile(suffix="test_config", delete=False).name
self.addCleanup(os.remove, config_file_path)  # ADD THIS LINE
```

### PYFIX-04: Cleanup for test_from_file
```python
# Source: test_config.py line 413 [VERIFIED]
config_file = tempfile.NamedTemporaryFile(mode="w", suffix="test_config", delete=False)
self.addCleanup(os.remove, config_file.name)  # ADD: registered first, runs last
self.addCleanup(config_file.close)            # ADD: registered last, runs first
# REMOVE the existing os.remove(config_file.name) and config_file.close() calls at the end
```

### PYFIX-05: Add missing call assertions to test_status_handler
```python
# Source: test_status_handler.py lines 13-28 [VERIFIED]
# Add to test_get_status_returns_200 and test_get_status_body_is_serialized:
mock_serialize_cls.status.assert_called_once_with(self.mock_status)
```

### PYFIX-06: Scoped chmod
```python
# Source: test_lftp.py line 30 [VERIFIED]
# BEFORE:
TestUtils.chmod_from_to(TestLftp.temp_dir, tempfile.gettempdir(), 0o775)
# AFTER:
os.chmod(TestLftp.temp_dir, 0o750)
```

### PYFIX-07: Logger fixture with reset
```python
# Source: conftest.py lines 20-43 [VERIFIED]
@pytest.fixture
def test_logger(request):
    logger = logging.getLogger(request.node.name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False      # ADD
    yield logger
    logger.removeHandler(handler)  # already present
    logger.setLevel(logging.NOTSET)  # ADD
    logger.propagate = True          # ADD
```

### PYFIX-08: Explicit ANY import (example for test_server_handler.py)
```python
# Source: test_server_handler.py line 1-3 [VERIFIED]
# BEFORE:
from unittest.mock import MagicMock
# AFTER:
from unittest.mock import MagicMock, ANY
```
Same change in test_auto_queue.py (add ANY) and test_stream_model.py (add ANY).

### PYFIX-09: Context manager for os.devnull
```python
# Source: test_extract.py line 51, test_controller.py line 88 [VERIFIED]
# BEFORE:
fnull = open(os.devnull, 'w')
subprocess.run([...], stdout=fnull, check=True)
# AFTER:
with open(os.devnull, 'w') as fnull:
    subprocess.run([...], stdout=fnull, check=True)
```

### PYFIX-10: Context manager for create_large_file
```python
# Source: test_controller.py lines 2275-2279 [VERIFIED]
def create_large_file(_path, size):
    # BEFORE: f = open(_path, "wb"); f.seek(size - 1); f.write(b"\0"); f.close()
    # AFTER:
    with open(_path, "wb") as f:
        f.seek(size - 1)
        f.write(b"\0")
    print("File size: ", os.stat(_path).st_size)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `threading.Thread(target=fn())` (bug) | `threading.Thread(target=fn)` | This phase | Actually tests concurrent behavior |
| `os.remove` at test body end | `self.addCleanup(os.remove, ...)` | This phase | Cleanup guaranteed even on failure |
| `f = open(); f.close()` | `with open() as f:` | This phase | Handle closed on exception |
| Implicit `unittest.mock.ANY` access | Explicit `from unittest.mock import ANY` | This phase | Import fragility eliminated |
| `chmod_from_to` up to /tmp | `os.chmod` on leaf only | This phase | Permission scope minimized |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `assertNotEqual(mock_lftp.rate_limit, 0)` reliably detects the "not assigned" case for PYFIX-02 | Code Examples / PYFIX-02 | If wrong, assertion would pass even when rate_limit WAS set to 0 — but since MagicMock auto-attribute is a MagicMock object (not 0), this is reliable |
| A2 | `logger.propagate = True` is the Python logging default | Pattern 7 | If default were False, resetting to True would change behavior — but Python docs specify True as default |
| A3 | PYFIX-06 fix: `os.chmod(TestLftp.temp_dir, 0o750)` is sufficient for the SFTP test account to access the directory | Code Examples | If seedsyncarrtest needs group-execute on the temp dir specifically, 0o750 works. If other group members need access up the chain, the integration test will fail with permission errors. Risk: LOW (Docker test container is controlled) |

**All three assumptions are LOW risk given the verified source code and controlled test environment.**

## Open Questions

1. **PYFIX-02: Is `assertNotEqual(mock_lftp.rate_limit, 0)` the right assertion?**
   - What we know: Production code at lftp_manager.py:57-58 assigns `self.__lftp.rate_limit = rate_limit` only when `rate_limit > 0`. When 0, the attribute is never assigned. MagicMock auto-attributes are MagicMock objects, not integers.
   - What's unclear: Whether `mock_lftp.rate_limit` after `LftpManager.__init__` is a pristine MagicMock (never accessed) or has been accessed internally.
   - Recommendation: The simplest safe assertion is `assertNotEqual(mock_lftp.rate_limit, 0)`. Could also use `mock_lftp.assert_has_calls([])` for `rate_limit` or inspect `mock_lftp.mock_calls` — but `assertNotEqual` is sufficient given the implementation.

2. **PYFIX-05: Is the guard assertion change observable?**
   - What we know: Current tests set `mock_serialize_cls.status.return_value` but tests 1 and 2 don't assert the call was made.
   - What's unclear: Whether adding `assert_called_once_with` to tests 1 and 2 would catch any current regression.
   - Recommendation: Add the assertion — it strengthens the tests and eliminates W-03 from the audit report.

## Environment Availability

Step 2.6: Verification that tests run in Docker.

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Docker | `make run-tests-python` | ✓ | Host Docker | — |
| pytest | Python test runner | ✓ (in Docker) | ^9.0.3 | — |
| Python | Test execution | ✓ (in Docker) | >=3.11,<3.13 | — |

Tests run exclusively inside Docker. Local `pytest` is not available on the host (confirmed). All test verification must use `make run-tests-python` or the Docker compose directly.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + unittest.TestCase |
| Config file | `src/python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `make run-tests-python` (builds + runs full suite in Docker) |
| Full suite command | `make run-tests-python` |

Note: There is no subset/quick run available outside Docker. The full suite is the only validation target. Total: 1262 tests.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PYFIX-01 | Thread target called as callable; background thread completes | unit | `make run-tests-python` | ✅ `test_extract_process.py` |
| PYFIX-02 | Explicit assertion for rate-limit-skip behavior | unit | `make run-tests-python` | ✅ `test_lftp_manager.py` |
| PYFIX-03 | No leaked temp files after test run | unit | `make run-tests-python` | ✅ `test_config.py` |
| PYFIX-04 | No leaked temp files even on assertion failure | unit | `make run-tests-python` | ✅ `test_config.py` |
| PYFIX-05 | Class-call path asserted in all three status handler tests | unit | `make run-tests-python` | ✅ `test_status_handler.py` |
| PYFIX-06 | chmod only applies to leaf temp dir | unit | `make run-tests-python` | ✅ `test_lftp.py` (unittests) |
| PYFIX-07 | Logger fixture resets propagate + level after yield | unit | `make run-tests-python` | ✅ `conftest.py` |
| PYFIX-08 | `ANY` explicitly imported in 3 files | unit | `make run-tests-python` | ✅ 3 files |
| PYFIX-09 | `open(os.devnull)` wrapped in context manager | integration | `make run-tests-python` | ✅ 2 integration test files |
| PYFIX-10 | `open()` in `create_large_file` uses `with` | integration | `make run-tests-python` | ✅ `test_controller.py` |

### Sampling Rate
- **Per task commit:** `make run-tests-python` (only option)
- **Per wave merge:** `make run-tests-python`
- **Phase gate:** Full suite green + zero ResourceWarning/mock-confusion warnings

### Wave 0 Gaps
None — all test files exist. No new test infrastructure required.

## Security Domain

These changes are test-only edits with no production code impact. The only security-relevant fix is PYFIX-06 (chmod scope), which reduces the attack surface by not making /tmp ancestor directories group-writable.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | test code only |
| V6 Cryptography | no | test code only |
| File permission hygiene | yes (PYFIX-06) | `os.chmod` leaf-dir only, 0o750 |

## Sources

### Primary (HIGH confidence)
- Source code read directly in this session:
  - `src/python/tests/unittests/test_controller/test_extract/test_extract_process.py:182` — PYFIX-01 bug [VERIFIED]
  - `src/python/tests/unittests/test_controller/test_lftp_manager.py:83-98` — PYFIX-02 bug [VERIFIED]
  - `src/python/tests/unittests/test_common/test_config.py:413,503` — PYFIX-03, PYFIX-04 bugs [VERIFIED]
  - `src/python/tests/unittests/test_web/test_handler/test_status_handler.py:13-28` — PYFIX-05 [VERIFIED]
  - `src/python/tests/unittests/test_lftp/test_lftp.py:30` — PYFIX-06 [VERIFIED]
  - `src/python/tests/conftest.py:20-43` — PYFIX-07 [VERIFIED]
  - `tests/unittests/test_controller/test_auto_queue.py`, `test_stream_model.py`, `test_server_handler.py` — PYFIX-08 [VERIFIED]
  - `src/python/tests/integration/test_controller/test_extract/test_extract.py:51` — PYFIX-09 [VERIFIED]
  - `src/python/tests/integration/test_controller/test_controller.py:88,2275-2279` — PYFIX-09, PYFIX-10 [VERIFIED]
  - `src/python/web/handler/status.py:16` — PYFIX-05 production code [VERIFIED]
  - `src/python/tests/utils.py` — chmod_from_to implementation [VERIFIED]
  - `src/python/pyproject.toml` — pytest config, coverage threshold, dependencies [VERIFIED]
  - `.planning/backlog/TEST-HARDENING-REVIEW.md` — original audit findings W-01 through W-08 [VERIFIED]

### Secondary (MEDIUM confidence)
- Python stdlib `unittest` documentation — `addCleanup` LIFO ordering [ASSUMED — standard well-documented behavior]
- Python `logging` module — `propagate` default is `True` [ASSUMED — standard well-documented behavior]

## Metadata

**Confidence breakdown:**
- Bug locations: HIGH — all verified by reading live source files
- Fix strategies: HIGH — all derived from reading actual code + audit document
- Coverage threshold: HIGH — verified in pyproject.toml (fail_under = 84, not 85.05 as stated in CONTEXT.md)
- MagicMock assertion behavior: MEDIUM — derived from well-known stdlib behavior, not tested

**Research date:** 2026-04-24
**Valid until:** 90 days (Python stdlib and project structure are stable)

---

## Appendix: Exact File Locations (for planner reference)

| PYFIX | File (relative to `src/python/`) | Line(s) |
|-------|----------------------------------|---------|
| PYFIX-01 | `tests/unittests/test_controller/test_extract/test_extract_process.py` | 182 |
| PYFIX-02 | `tests/unittests/test_controller/test_lftp_manager.py` | 83-98 |
| PYFIX-03 | `tests/unittests/test_common/test_config.py` | 503 |
| PYFIX-04 | `tests/unittests/test_common/test_config.py` | 413 |
| PYFIX-05 | `tests/unittests/test_web/test_handler/test_status_handler.py` | 13-28 |
| PYFIX-06 | `tests/unittests/test_lftp/test_lftp.py` | 30 |
| PYFIX-07 | `tests/conftest.py` | 20-43 |
| PYFIX-08a | `tests/unittests/test_controller/test_auto_queue.py` | 1-5 (import line) |
| PYFIX-08b | `tests/integration/test_web/test_handler/test_stream_model.py` | 1-3 (import line) |
| PYFIX-08c | `tests/unittests/test_web/test_handler/test_server_handler.py` | 1-2 (import line) |
| PYFIX-09a | `tests/integration/test_controller/test_extract/test_extract.py` | 51 |
| PYFIX-09b | `tests/integration/test_controller/test_controller.py` | 88 |
| PYFIX-10 | `tests/integration/test_controller/test_controller.py` | 2275-2279 |

Note: `src/python/tests/unittests/test_status_handler.py` referenced in CONTEXT.md resolves to `src/python/tests/unittests/test_web/test_handler/test_status_handler.py` (verified by filesystem search).

Note: `src/python/tests/unittests/test_config.py` referenced in CONTEXT.md resolves to `src/python/tests/unittests/test_common/test_config.py` (verified by filesystem search).

Note: Coverage `fail_under` in pyproject.toml is `84`, not `85.05` as referenced in CONTEXT.md. Planner should use the actual value `84` from pyproject.toml as authoritative.
