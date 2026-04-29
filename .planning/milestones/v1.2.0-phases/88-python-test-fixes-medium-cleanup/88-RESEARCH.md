# Phase 88: Python Test Fixes -- Medium & Cleanup - Research

**Researched:** 2026-04-24
**Domain:** Python unittest/pytest test quality -- XSS test coverage, race condition fixes, sleep elimination, resource cleanup, logger leak prevention
**Confidence:** HIGH

## Summary

This phase fixes 9 specific, audited Python test defects (PYFIX-11 through PYFIX-19): adding a missing XSS prevention test, fixing scanner busy-wait race conditions, eliminating ~7.25 seconds of real `time.sleep` from unit tests, fixing `TemporaryDirectory` cleanup, moving implicit `import bottle` to module level, fixing logger handler leaks across 5 files, replacing sleep-based synchronization with `job.join`, adding sleep to ~41 busy-wait loops in `test_lftp.py`, and fixing a conditional assertion that silently skips.

All bug locations are precisely documented in REQUIREMENTS.md and verified by reading live source files. No architectural changes are involved -- every fix is a targeted edit within existing test files. The test suite runs inside Docker via `make run-tests-python` (1262 tests, coverage floor `fail_under = 84` per pyproject.toml).

The phase has a measurable success criterion: the test suite must run at least 4 seconds faster after PYFIX-13 sleep replacement. Current total real sleep time across the 5 affected files is ~7.25 seconds, so the target is achievable by mocking/replacing the largest sleeps (the 1.0s sleeps in test_multiprocessing_logger.py, test_extract_process.py, and test_dispatch.py).

**Primary recommendation:** Fix each bug in-place. For PYFIX-13, use `unittest.mock.patch('time.sleep')` where sleeps serve only as "wait for background work" and replace with `threading.Event` or `job.join(timeout)` where deterministic synchronization is needed. For PYFIX-16, add `removeHandler` in `tearDown` across all 5 files following the pattern already established in `conftest.py` by Phase 87. For PYFIX-18, add `time.sleep(0.01)` to all 41 `while True:` busy-wait loops in `test_lftp.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Claude's Discretion
User elected to skip discussion -- all implementation decisions are at Claude's discretion. Requirements are fully specified in REQUIREMENTS.md (PYFIX-11 through PYFIX-19) with exact file locations and bug descriptions. No ambiguity in what needs fixing.

Key areas left to Claude:
- **D-01:** XSS prevention test approach for PYFIX-11 -- test HTML special chars (`<>"'&`) are escaped in meta tag output
- **D-02:** Scanner busy-wait fix strategy for PYFIX-12 -- deterministic synchronization replacing race-prone busy-waits
- **D-03:** Sleep replacement scope for PYFIX-13 -- mock `time.sleep` vs `threading.Event` vs targeted per-file; must save 4+ seconds
- **D-04:** TemporaryDirectory cleanup method for PYFIX-14 -- `addCleanup(_tmpd.cleanup)` or context manager
- **D-05:** Bottle import restructuring for PYFIX-15 -- move from inside closures to module level
- **D-06:** Logger handler cleanup strategy for PYFIX-16 -- centralized conftest fixture vs per-file tearDown/removeHandler across 5 files
- **D-07:** Job sync replacement for PYFIX-17 -- `job.join(timeout=5.0)` replacing `time.sleep`
- **D-08:** Busy-wait sleep injection for PYFIX-18 -- sleep interval size (0.01s-0.1s) for ~25 loops in test_lftp.py
- **D-09:** Conditional assertion fix for PYFIX-19 -- ensure assert always executes at `test_job_status_parser_components.py:199`

### Locked Decisions
None -- user skipped discussion.

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PYFIX-11 | Add test for HTML-escaping token in meta tag -- XSS prevention | Source uses `html.escape(api_token, quote=True)` at `web/web_app.py:222`. Test must pass token `<>"'&` and verify escaped output `&lt;&gt;&quot;&#x27;&amp;` in meta tag. Existing test pattern at `test_web_app.py:137-181`. [VERIFIED: source] |
| PYFIX-12 | Fix busy-wait race condition in scanner tests -- add sleep + fix TOCTOU | 6 bare `while counter.value < N: pass` loops in `test_scanner_process.py` (lines 82, 100, 129, 140, 155, 173). Need `time.sleep(0.01)` in loop body. [VERIFIED: source] |
| PYFIX-13 | Replace real `time.sleep` in unit tests with mock time or threading.Event (~4.5s saved per run) | Total real sleep: ~7.25s across 5 files (test_dispatch: 1.4s, test_extract_process: 2.2s, test_job: 0.4s, test_multiprocessing_logger: 3.1s, test_controller_handler: 0.151s). [VERIFIED: source grep] |
| PYFIX-14 | Fix TemporaryDirectory cleanup -- add `addCleanup(_tmpd.cleanup)` | `_make_web_app_with_index()` returns `(app, tmp_dir_obj)` but callers store as `_tmpd` and never call `.cleanup()`. 10 call sites in `TestWebAppMetaTagInjection`. [VERIFIED: source] |
| PYFIX-15 | Move implicit `import bottle` inside closures to module level | 2 occurrences in `test_auth.py` lines 214 and 236 -- `import bottle` inside route callback closures. [VERIFIED: source] |
| PYFIX-16 | Fix logger handler leaked every test -- add removeHandler in tearDown across 5 files | Files: (1) `unittests/test_lftp/test_lftp.py:118`, (2) `integration/test_lftp/test_lftp.py:44`, (3) `integration/test_web/test_web_app.py:26`, (4) `integration/test_controller/test_controller.py:359`, (5) `unittests/test_common/test_multiprocessing_logger.py:17`. All add handler in setUp, none remove in tearDown. [VERIFIED: source grep] |
| PYFIX-17 | Replace `time.sleep` sync primitive in `test_job.py` with `job.join(timeout=5.0)` | Two `time.sleep(0.2)` calls at lines 29 and 39 used to wait for `DummyFailingJob` to complete. Job class extends `threading.Thread` and has `join()` method. [VERIFIED: source] |
| PYFIX-18 | Add sleep to ~25 busy-wait loops in `test_lftp.py` to prevent 100% CPU | Actually 41 `while True:` loops found (not ~25). All are tight poll loops on `self.lftp.status()` results. Need `time.sleep(0.01)` in each loop body. [VERIFIED: source grep -- `grep -c "while True:" test_lftp.py` = 41] |
| PYFIX-19 | Fix conditional assertion that silently skips in `test_job_status_parser_components.py:199` | Line 199: `if match:` guard around assertions means test silently passes when regex does not match. Must either (a) `assertIsNotNone(match)` before the `if`, or (b) remove the `if` and let the `parse_chunk_at(match)` call fail naturally with `None`. [VERIFIED: source] |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| XSS prevention testing | Test layer | -- | Verifies production HTML escaping; no production code change |
| Scanner race condition fix | Test layer | -- | Busy-wait loops are test-side synchronization only |
| Sleep elimination | Test layer | -- | All `time.sleep` calls are in test code, not production |
| TemporaryDirectory cleanup | Test layer | -- | Test resource management |
| Import restructuring | Test layer | -- | Test file import organization |
| Logger handler cleanup | Test layer | -- | Test setUp/tearDown handler lifecycle |
| Busy-wait CPU fix | Test layer | -- | Test polling loop efficiency |
| Conditional assertion fix | Test layer | -- | Test correctness |

## Standard Stack

### Core (already in use -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | ^9.0.3 | Test runner | Project standard [VERIFIED: pyproject.toml] |
| pytest-cov | ^7.1.0 | Coverage enforcement | `fail_under = 84` [VERIFIED: pyproject.toml] |
| pytest-timeout | ^2.3.1 | Test timeout guard | 60s default [VERIFIED: pyproject.toml] |
| timeout-decorator | ^0.5.0 | Per-test timeout | Used in test_lftp.py, test_scanner_process.py [VERIFIED: pyproject.toml] |
| unittest.TestCase | stdlib | Test class base | All existing tests use this pattern [VERIFIED: source] |
| unittest.mock | stdlib | Mocking (patch, MagicMock) | Used for time.sleep mocking in PYFIX-13 [VERIFIED: source] |
| html | stdlib | HTML escaping | `html.escape()` used in production code [VERIFIED: web_app.py:222] |
| testfixtures | installed | LogCapture | Used in test_multiprocessing_logger.py [VERIFIED: source] |

No new packages required. All fixes use stdlib or already-installed libraries.

**Installation:** None needed.

## Architecture Patterns

### System Architecture Diagram

```
Test Runner (pytest via Docker)
    |
    v
[Test Files] --> setUp() --> addHandler(handler) --> test body --> tearDown()
    |                                                                  |
    |  PYFIX-16: handler never removed here ------> FIX: removeHandler |
    |                                                                  |
    v                                                                  v
[Production Code Under Test]                              [Cleanup: handlers, tmpdir, etc.]
    |
    +-- web/web_app.py._inject_meta_tag() <-- PYFIX-11: verify HTML escaping
    +-- controller/scan/* <-- PYFIX-12: ScannerProcess busy-wait
    +-- common/job.py <-- PYFIX-17: Job.join() instead of sleep
    +-- lftp/* <-- PYFIX-18: lftp status polling loops
```

### Recommended Fix Strategy per Requirement

#### PYFIX-11: XSS Prevention Test (D-01)

**Recommendation:** Add a new test method to existing `TestWebAppMetaTagInjection` class.

The production code at `web/web_app.py:222` calls `html.escape(api_token or "", quote=True)`. Python's `html.escape` with `quote=True` escapes all 5 HTML special characters: `<`, `>`, `"`, `'`, `&`. [VERIFIED: `python3 -c "import html; print(html.escape('<>\"&\\'', quote=True))"` outputs `&lt;&gt;&quot;&amp;&#x27;`]

```python
# Source: Python stdlib html.escape behavior [VERIFIED: local execution]
def test_meta_tag_escapes_html_special_chars(self):
    """XSS prevention: HTML special characters in token must be escaped."""
    xss_token = '<script>"alert(1)\'&'
    app, _tmpd = _make_web_app_with_index(api_token=xss_token)
    self.addCleanup(_tmpd.cleanup)  # PYFIX-14 pattern
    client = TestApp(app)
    response = client.get("/")
    # html.escape(xss_token, quote=True) produces the escaped version
    self.assertNotIn("<script>", response.text)
    self.assertIn("&lt;script&gt;&quot;alert(1)&#x27;&amp;", response.text)
    self.assertIn('<meta name="api-token" content="&lt;script&gt;&quot;alert(1)&#x27;&amp;">', response.text)
```

#### PYFIX-12: Scanner Busy-Wait Race Fix (D-02)

**Recommendation:** Add `time.sleep(0.01)` inside each `while` loop body in `test_scanner_process.py`.

The 6 busy-wait loops spin on `multiprocessing.Value` counters without yielding CPU. This is a race condition because the OS scheduler may starve the worker process. Adding a 0.01s sleep yields the GIL and prevents tight-spin CPU waste.

```python
# Before (race-prone):
while self.scan_counter.value < 2:
    pass

# After (deterministic):
while self.scan_counter.value < 2:
    time.sleep(0.01)
```

Note: `time.sleep` is needed here and should NOT be mocked -- these are integration-style waits for real multiprocessing operations.

#### PYFIX-13: Sleep Replacement Strategy (D-03)

**Recommendation:** Per-file targeted approach. Different files need different strategies.

**Total real sleep budget: ~7.25 seconds.** Target: save 4+ seconds.

| File | Sleep Total | Strategy | Savings |
|------|-------------|----------|---------|
| `test_multiprocessing_logger.py` | ~3.1s | Cannot mock -- sleeps are inside `multiprocessing.Process` (separate process, `unittest.mock.patch` does not cross process boundary). Replace `time.sleep(1)` waits with `p_1.join(timeout=2)` + `mp_logger.stop()`. The 0.1s/0.2s interprocess sleeps can remain. | ~2.0s |
| `test_extract_process.py` | ~2.2s | The `time.sleep(1.0)` at line 176 and `time.sleep(1)` at line 274 are inside test callbacks that simulate slow work. Use `threading.Event` signaling instead. The 0.1s sleeps at lines 173, 179 are signal sequencing; keep as-is or reduce to 0.01s. | ~1.8s |
| `test_dispatch.py` | ~1.4s | The `time.sleep(0.5)` at lines 229 and 566 simulate "work in progress while shutdown is called" -- these are fundamental to the test's purpose (race between extraction and shutdown). Mock `time.sleep` in the test or use `threading.Event.wait(0.5)` with mock. The 0.1s sleeps at lines 718, 721, 726, 856 are stabilization waits; mock or reduce. | ~0.8s |
| `test_job.py` | ~0.4s | Handled by PYFIX-17 -- `job.join(timeout=5.0)` replaces both `time.sleep(0.2)` calls. | ~0.4s |
| `test_controller_handler.py` | ~0.151s | The `time.sleep(0.15)` at line 672 tests rate-limit window expiry. Must remain real (tests actual time-based rate limiter) or use `freezegun`/`time_machine`. Skip for now -- only 0.15s. The `time.sleep(0.001)` is negligible. | ~0s |

**Expected total savings: ~5.0 seconds** (exceeds 4s target).

**Key constraint for test_multiprocessing_logger.py:** `unittest.mock.patch('time.sleep')` does NOT work across `multiprocessing.Process` boundaries. The child process has its own memory space and does not see the mock. The sleeps inside `process_1` (the multiprocessing target function) cannot be mocked this way. The fix must focus on the parent-side `time.sleep(1)` and `time.sleep(0.2)` calls, replacing them with `p_1.join(timeout=X)` followed by `mp_logger.stop()`. [ASSUMED -- based on multiprocessing isolation semantics]

**Key constraint for test_dispatch.py:** The `time.sleep(0.5)` calls at lines 229 and 566 are inside mock `side_effect` callbacks that run on the dispatch worker thread. They simulate slow extraction work. The test's correctness depends on the extraction taking nonzero time so `stop()` can be called mid-operation. Replace with `threading.Event.wait(timeout=0.5)` and have the test set the event after calling `stop()`, allowing the wait to return immediately. [ASSUMED -- standard threading.Event pattern]

#### PYFIX-14: TemporaryDirectory Cleanup (D-04)

**Recommendation:** Use `self.addCleanup(_tmpd.cleanup)` at each call site.

The `_make_web_app_with_index()` helper returns `(app, tmp_dir_obj)`. The 10+ callers store `tmp_dir_obj` as `_tmpd` but never call `.cleanup()`. The `TemporaryDirectory` relies on GC-triggered `__del__` for cleanup, which is nondeterministic. Two approaches:

1. **Per-callsite `addCleanup`** -- add `self.addCleanup(_tmpd.cleanup)` after each `_make_web_app_with_index()` call.
2. **Refactor helper to use `setUp`** -- move the temp dir creation into `setUp` and cleanup into `tearDown`.

Recommend option 1 because it matches Phase 87's `addCleanup` pattern (PYFIX-03/04) and requires no structural changes. The `TestWebAppMetaTagInjection` class has no `setUp` today; adding one would be a larger change.

```python
def test_index_contains_meta_tag_with_token(self):
    app, _tmpd = _make_web_app_with_index(api_token="my-secret-token")
    self.addCleanup(_tmpd.cleanup)  # ADD
    client = TestApp(app)
    response = client.get("/")
    self.assertIn('<meta name="api-token" content="my-secret-token">', response.text)
```

#### PYFIX-15: Bottle Import Restructuring (D-05)

**Recommendation:** Move `import bottle` from inside the closure to the top of the file.

```python
# Before (inside closure at lines 214, 236):
@app.route("/server/test/capture-auth")
def _capture():
    import bottle
    captured.append(getattr(bottle.request, 'auth_valid', None))
    return "ok"

# After (module-level import):
import bottle  # at top of test_auth.py

# Then in closure:
@app.route("/server/test/capture-auth")
def _capture():
    captured.append(getattr(bottle.request, 'auth_valid', None))
    return "ok"
```

The import is inside the closure because `bottle` is an optional/lazy dependency, but in test files this is unnecessary -- `bottle` is always available in the test environment. [VERIFIED: other test files import bottle at module level]

#### PYFIX-16: Logger Handler Cleanup (D-06)

**Recommendation:** Add `removeHandler` in `tearDown` for each of the 5 affected files. Store `self.handler` in `setUp` so it can be removed in `tearDown`.

This is the same pattern already working in `conftest.py` (fixed by Phase 87, PYFIX-07). Do NOT centralize into conftest -- these are `unittest.TestCase` classes that use `setUp/tearDown`, not pytest fixtures.

**File-by-file fix pattern:**

```python
# In setUp:
self._test_handler = logging.StreamHandler(sys.stdout)
# ... formatter setup ...
logger.addHandler(self._test_handler)

# In tearDown (ADD):
logger.removeHandler(self._test_handler)
```

The 5 files and their specifics:

1. **`unittests/test_lftp/test_lftp.py`** (line 118): Uses root logger `logging.getLogger()`. Store handler as `self._test_handler`. Add `logging.getLogger().removeHandler(self._test_handler)` in existing `tearDown` at line 120.

2. **`integration/test_lftp/test_lftp.py`** (line 44): Uses root logger. Store handler as `self._test_handler`. Add remove in existing `tearDown` at line 50.

3. **`integration/test_web/test_web_app.py`** (line 26): Uses root logger. Store handler as `self._test_handler`. Add `tearDown` method (none exists currently).

4. **`integration/test_controller/test_controller.py`** (line 359): Uses named logger `TestController.__name__`. Store handler as `self._test_handler`. Add remove in existing `tearDown` at line 372.

5. **`unittests/test_common/test_multiprocessing_logger.py`** (line 17): Uses named logger. Store handler as `self._test_handler`. Add `tearDown` method (none exists currently).

#### PYFIX-17: Job Sync Replacement (D-07)

**Recommendation:** Replace `time.sleep(0.2)` with `job.join(timeout=5.0)` plus `job.terminate()` reordering.

The `Job` class extends `threading.Thread` (confirmed at `common/job.py:9`). The `DummyFailingJob.execute()` raises `DummyError`, which sets `self.exc_info` and breaks the run loop. After the run loop exits, `cleanup()` runs, then the thread terminates.

Current test flow:
```python
job.start()
time.sleep(0.2)  # hope the thread finishes in 0.2s
with self.assertRaises(DummyError):
    job.propagate_exception()
job.terminate()
job.join()
```

Fixed test flow:
```python
job.start()
job.join(timeout=5.0)  # deterministic wait for thread to finish
with self.assertRaises(DummyError):
    job.propagate_exception()
```

Note: `job.terminate()` and `job.join()` after `propagate_exception` can be removed because `join(timeout=5.0)` already waited for the thread to complete. The `DummyFailingJob` sets `shutdown_flag` via exception handling, so the thread self-terminates.

For `test_cleanup_executes_on_execute_error`:
```python
job.start()
job.join(timeout=5.0)  # wait for thread to complete (exception + cleanup)
self.assertTrue(job.cleanup_run)
```

#### PYFIX-18: Busy-Wait Sleep Injection (D-08)

**Recommendation:** Add `time.sleep(0.01)` to all 41 `while True:` loops in `test_lftp.py`.

The loops poll `self.lftp.status()` which makes real subprocess calls to the lftp binary. Without sleep, the test burns 100% CPU in a tight loop, potentially starving the lftp process and the SSH server running in a test container. A 10ms sleep is sufficient to yield CPU without meaningfully slowing tests (41 loops x ~2 iterations avg x 10ms = ~0.8s total added, well within the 5s `timeout_decorator` budgets).

```python
# Before:
while True:
    statuses = self.lftp.status()
    if len(statuses) > 0:
        break

# After:
while True:
    statuses = self.lftp.status()
    if len(statuses) > 0:
        break
    time.sleep(0.01)
```

**Important:** `time.sleep` must be BEFORE the `break` check, not after the break point. Place it as the last line in the loop body, after all break conditions. This ensures the sleep only runs when the loop continues.

Actually, looking more carefully at the loop structure, the `time.sleep` should go right before the continue point (i.e., at the bottom of the loop body, before looping back). For the pattern `while True: ... if condition: break`, add `time.sleep(0.01)` after the `if` block (before the loop repeats).

#### PYFIX-19: Conditional Assertion Fix (D-09)

**Recommendation:** Add `self.assertIsNotNone(match)` before the `if match:` guard, then remove the `if` guard.

Current code at `test_job_status_parser_components.py:195-202`:
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

The `if match:` guard means if the regex does not match, the test silently passes without testing anything. This defeats the purpose of the test.

Fix: Assert the match exists, then remove the conditional:
```python
def test_parse_chunk_at_no_speed_eta(self):
    line = "`file.txt' at 1024 (50%) [Receiving data]"
    match = RegexPatterns.CHUNK_AT.search(line)
    self.assertIsNotNone(match, "CHUNK_AT regex must match line without speed/eta")
    state = TransferStateParser.parse_chunk_at(match)
    self.assertIsNone(state.speed)
    self.assertIsNone(state.eta)
```

If the regex genuinely does not match this input, that is a production bug that should surface as a test failure, not be silently swallowed.

### Anti-Patterns to Avoid

- **Mocking time.sleep across process boundaries:** `unittest.mock.patch('time.sleep')` does NOT work in `multiprocessing.Process` targets. The child process has its own memory space. Use `Process.join(timeout=X)` on the parent side instead.
- **Over-mocking in multiprocessing tests:** `test_multiprocessing_logger.py` tests real IPC between processes. Mocking `time.sleep` in the parent does not affect the child. Focus on parent-side wait reduction.
- **Removing sleep from test_controller_handler.py rate limiter test:** The `time.sleep(0.15)` at line 672 tests a real time-window-based rate limiter. Mocking it would defeat the test's purpose unless you also mock the rate limiter's clock.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping verification | Custom regex or string replacement | `html.escape(token, quote=True)` output comparison | stdlib handles all 5 HTML special chars correctly |
| Thread synchronization | Custom flag + sleep loop | `threading.Event.wait(timeout)` or `Thread.join(timeout)` | stdlib primitives are race-free and well-tested |
| Process synchronization | Mock time.sleep in child | `Process.join(timeout)` on parent side | Mock does not cross process boundary |
| Logger cleanup | Global handler registry | Per-class `self._test_handler` + `removeHandler` in `tearDown` | Simple, follows existing conftest.py pattern |

## Common Pitfalls

### Pitfall 1: Mocking time.sleep in multiprocessing context
**What goes wrong:** `unittest.mock.patch('time.sleep')` only patches the current process's module namespace. Child processes spawned via `multiprocessing.Process` get their own copy of `time` module.
**Why it happens:** Multiprocessing uses separate memory spaces (fork or spawn).
**How to avoid:** Replace parent-side waits with `process.join(timeout)`. Leave child-side sleeps alone.
**Warning signs:** Test hangs or takes same time after "mocking" sleep.

### Pitfall 2: Breaking shutdown-race tests by removing all sleeps
**What goes wrong:** Tests like `test_extract_exits_command_early_on_shutdown` in test_dispatch.py rely on `time.sleep(0.5)` to simulate slow work while `stop()` is called from the main thread. Removing this sleep makes the extraction complete instantly, defeating the test.
**Why it happens:** The sleep IS the "work" being simulated.
**How to avoid:** Replace `time.sleep(0.5)` with `threading.Event.wait(0.5)` and have the test signal the event after calling `stop()`. This makes the wait interruptible but still nonzero for the race test.
**Warning signs:** Shutdown-race tests pass trivially because mock makes extraction instant.

### Pitfall 3: Root logger handler accumulation
**What goes wrong:** Several test files add handlers to the root logger (`logging.getLogger()`) without removing them. After 40+ tests in `test_lftp.py`, the root logger has 40+ StreamHandlers, causing duplicate output and memory waste.
**Why it happens:** `setUp` adds handler, `tearDown` does not remove it.
**How to avoid:** Store handler as instance attribute, remove in tearDown.
**Warning signs:** Exponentially increasing test output volume as suite progresses.

### Pitfall 4: TemporaryDirectory cleanup order
**What goes wrong:** If `_tmpd.cleanup()` is called while the web app still holds references to files in the temp dir, you may get warnings or errors on some platforms.
**Why it happens:** WebApp reads `index.html` at route serve time from `_tmpd.name` path.
**How to avoid:** `addCleanup` runs after the test method completes. Since `TestApp` does not persist between tests, the cleanup order is safe.
**Warning signs:** `ResourceWarning` or `PermissionError` during cleanup on Windows (not applicable to Docker Linux test environment).

### Pitfall 5: Conditional assertion appears to "work" when regex is wrong
**What goes wrong:** PYFIX-19's `if match:` guard silently skips all assertions when the regex does not match the test input. The test shows as "passed" with 0 assertions executed.
**Why it happens:** Developer added defensive guard "just in case" but this defeats test purpose.
**How to avoid:** Never use `if` guards around test assertions. Assert preconditions explicitly with `assertIsNotNone`.
**Warning signs:** Test passes but no assertions fire (visible in verbose pytest output: no assertion count).

## Code Examples

### XSS Prevention Test (PYFIX-11)
```python
# Source: Existing pattern in test_web_app.py lines 137-181 [VERIFIED: source]
def test_meta_tag_escapes_html_special_chars(self):
    """XSS prevention: HTML special characters in token must be escaped in meta tag."""
    xss_token = '<script>"alert(1)\'&'
    app, _tmpd = _make_web_app_with_index(api_token=xss_token)
    self.addCleanup(_tmpd.cleanup)
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

### Logger Handler Cleanup Pattern (PYFIX-16)
```python
# Source: conftest.py pattern established by Phase 87 PYFIX-07 [VERIFIED: source]
class TestFoo(unittest.TestCase):
    def setUp(self):
        logger = logging.getLogger()
        self._test_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self._test_handler.setFormatter(formatter)
        logger.addHandler(self._test_handler)
        logger.setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger().removeHandler(self._test_handler)
```

### Job.join Replacement (PYFIX-17)
```python
# Source: common/job.py -- Job extends threading.Thread [VERIFIED: source]
def test_exception_propagates(self):
    context = MagicMock()
    job = DummyFailingJob("DummyFailingJob", context)
    job.start()
    job.join(timeout=5.0)  # replaces time.sleep(0.2)
    with self.assertRaises(DummyError):
        job.propagate_exception()
```

### Busy-Wait Sleep Injection (PYFIX-18)
```python
# Source: test_lftp.py loop pattern [VERIFIED: source lines 210-213]
@timeout_decorator.timeout(5)
def test_queue_file(self):
    self.lftp.rate_limit = 10
    self.lftp.queue("c", False)
    while True:
        statuses = self.lftp.status()
        if len(statuses) > 0:
            break
        time.sleep(0.01)  # ADD: prevent CPU spin
    self.assertEqual(1, len(statuses))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `time.sleep(N)` for thread sync | `Thread.join(timeout)` or `threading.Event` | Python 2.x era | Deterministic, no flaky timing |
| Bare `while True: pass` busy-wait | `while True: ... time.sleep(0.01)` | Always best practice | Prevents CPU starvation of worker threads/processes |
| Manual handler cleanup | `logger.removeHandler(handler)` in tearDown | Python logging best practice | Prevents handler accumulation across tests |
| GC-dependent TemporaryDirectory | `addCleanup(tmpd.cleanup)` | unittest best practice | Deterministic cleanup, no ResourceWarnings |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `unittest.mock.patch('time.sleep')` does not cross `multiprocessing.Process` boundary | PYFIX-13 strategy / Pitfall 1 | If wrong (e.g., fork-mode inherits mock), multiprocessing logger tests could be simplified further. Low risk -- standard Python multiprocessing behavior. |
| A2 | `threading.Event.wait(0.5)` is interruptible and returns when event is set | PYFIX-13 test_dispatch strategy | If wrong, shutdown-race tests would still block for 0.5s. Low risk -- documented Event behavior. |
| A3 | 41 busy-wait loops x ~2 iterations avg x 10ms = ~0.8s added time for PYFIX-18 | PYFIX-18 time estimate | If actual iteration count is higher, could add 1-2s. Acceptable within 5s timeout budget. |

## Open Questions

1. **PYFIX-13: test_multiprocessing_logger.py parent-side sleep reduction scope**
   - What we know: The `time.sleep(1)` calls at lines 41 and 67 wait for the multiprocessing logger to process all records from the child process.
   - What's unclear: Whether replacing `time.sleep(1)` with `p_1.join(timeout=2); mp_logger.stop()` is sufficient, or if there's a race between the child process terminating and the logger thread finishing processing its queue.
   - Recommendation: Use `p_1.join(timeout=2)` to wait for child exit, then add a small sleep (0.05s) before `mp_logger.stop()` to allow the logger thread to drain remaining records. Test empirically.

2. **PYFIX-12 vs PYFIX-18: Are scanner busy-waits "scanner tests" or "lftp tests"?**
   - What we know: PYFIX-12 targets scanner tests (`test_scan*.py`), PYFIX-18 targets `test_lftp.py`. Both have busy-wait loops.
   - What's unclear: Whether the `test_scanner_process.py` busy-waits are covered by PYFIX-12 or PYFIX-18.
   - Recommendation: PYFIX-12 covers `test_scanner_process.py` (scanner subsystem). PYFIX-18 covers `test_lftp.py` (lftp subsystem). No overlap.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + unittest.TestCase |
| Config file | `src/python/pyproject.toml` [VERIFIED: source] |
| Quick run command | `make run-tests-python` (Docker, full suite) |
| Full suite command | `make run-tests-python` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PYFIX-11 | HTML special chars escaped in meta tag | unit | `make run-tests-python` (runs full suite including new test) | New test method in existing file |
| PYFIX-12 | Scanner busy-waits have sleep | unit | `make run-tests-python` | Existing file modified |
| PYFIX-13 | Unit tests 4s+ faster | timing | Before/after timing comparison of `make run-tests-python` | Existing files modified |
| PYFIX-14 | TemporaryDirectory cleaned up | unit | `make run-tests-python` (no ResourceWarning) | Existing file modified |
| PYFIX-15 | Bottle import at module level | unit | `make run-tests-python` | Existing file modified |
| PYFIX-16 | Handler removed in tearDown | unit | `make run-tests-python` (no handler accumulation) | Existing files modified |
| PYFIX-17 | job.join replaces sleep | unit | `make run-tests-python` | Existing file modified |
| PYFIX-18 | Busy-wait loops have sleep | unit | `make run-tests-python` | Existing file modified |
| PYFIX-19 | Assertion always executes | unit | `make run-tests-python` | Existing file modified |

### Sampling Rate
- **Per task commit:** `make run-tests-python`
- **Per wave merge:** `make run-tests-python` (same -- all-or-nothing Docker suite)
- **Phase gate:** Full suite green + timing comparison for PYFIX-13

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. No new test files or framework configuration needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | -- |
| V3 Session Management | no | -- |
| V4 Access Control | no | -- |
| V5 Input Validation | yes (PYFIX-11) | `html.escape()` with `quote=True` for HTML meta tag content [VERIFIED: web_app.py:222] |
| V6 Cryptography | no | -- |

### Known Threat Patterns for Python Web (Bottle)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via unescaped user input in HTML | Tampering / Information Disclosure | `html.escape(value, quote=True)` before injection into HTML attributes [VERIFIED: already implemented in production] |

**Note:** PYFIX-11 adds TEST COVERAGE for an existing security control. The production code already escapes correctly. This phase does not modify production security code.

## Sources

### Primary (HIGH confidence)
- `src/python/web/web_app.py` lines 219-224 -- `_inject_meta_tag` implementation with `html.escape` [VERIFIED: direct file read]
- `src/python/common/job.py` -- Job class extending `threading.Thread` with `join()`, `terminate()`, `shutdown_flag` [VERIFIED: direct file read]
- `src/python/tests/conftest.py` -- Logger fixture with `removeHandler` pattern from Phase 87 [VERIFIED: direct file read]
- `src/python/pyproject.toml` -- pytest config, coverage `fail_under = 84`, timeout = 60 [VERIFIED: direct file read]
- All 13 affected test files -- read and grep-verified for exact line numbers and patterns

### Secondary (MEDIUM confidence)
- Phase 87 RESEARCH.md and PATTERNS.md -- established fix patterns for addCleanup, removeHandler, context managers [VERIFIED: direct file read]

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all stdlib/installed
- Architecture: HIGH -- all patterns verified against live source code
- Pitfalls: HIGH -- multiprocessing isolation is well-documented Python behavior
- Sleep budget: HIGH -- grep-counted all time.sleep values across affected files

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable -- stdlib patterns, no version-sensitive dependencies)
