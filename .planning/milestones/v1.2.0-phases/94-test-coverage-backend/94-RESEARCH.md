# Phase 94: Test Coverage -- Backend - Research

**Researched:** 2026-04-28
**Domain:** Python backend test writing — SSE streaming WSGI harness, webhook integration, SSH mock, multiprocessing mock
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use a thin WSGI iterator harness — call `web_app(environ, start_response)` directly to get the SSE generator, iterate it in the test thread. Zero new dependencies.
- **D-02:** Preserve the existing Timer-stop pattern from the skipped tests. The Timer fires during `time.sleep()` inside the generator, sets the stop flag, and the generator exits on the next loop check.
- **D-03:** Build a small helper (e.g., `tests/helpers/wsgi_stream.py`) that constructs the WSGI environ dict and wraps the call. The 3 existing skipped test files (`test_stream_status.py`, `test_stream_model.py`, `test_stream_log.py`) should be unskipped and updated to use this harness.
- **D-04:** Test to HTTP → controller dispatch boundary only. Mock `webhook_manager`, assert `enqueue_import` called with correct args after `self.test_app.post("/server/webhook/sonarr", ...)`.
- **D-05:** Follow the established `BaseTestWebApp` pattern — `webhook_manager` is already wired as a `MagicMock` by `WebAppBuilder`. This matches how `test_controller.py` tests POST routes.
- **D-06:** Do NOT test through to `WebhookManager.process()` — that path is already covered by existing `test_webhook_manager.py` unit tests. The gap is specifically the Bottle routing + WSGI dispatch layer.
- **D-07:** Mock `Sshcp` at the module level via `patch('controller.delete.delete_process.Sshcp')`. Matches the pattern used in `test_extract_process.py`.
- **D-08:** Assert exact `rm -rf <shlex.quoted-path>` command string passed to `shell()`. Test `SshcpError` is caught and logged. Verify constructor args (host, port, user, password) forwarded correctly.
- **D-09:** Do NOT use real SSH via Docker — the class logic is `os.path.join` + `shlex.quote`, which doesn't benefit from a live SSH daemon.
- **D-10:** Mock both `multiprocessing.Queue` and `SystemScanner` via `unittest.mock`. Zero timing dependencies, fully deterministic.
- **D-11:** Cross-process IPC fidelity is `ScannerProcess`'s responsibility (already tested in `test_scanner_process.py`). ActiveScanner tests focus on queue-drain logic, scan scheduling, and result aggregation.
- **D-12:** Test paths: empty queue on first scan, multiple `set_active_files` calls (drain loop), `SystemScannerError` suppression, and the `(files, None, None)` return contract.

### Claude's Discretion
None specified.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COVER-01 | Add SSE streaming integration tests — evaluate thin WSGI harness | WSGI iterator harness: call `web_app(environ, start_response)` directly; unskip 3 existing skipped test files with updated harness |
| COVER-04 | Add webhook end-to-end test — Sonarr/Radarr POST through web layer to controller | `BaseTestWebApp` + `self.test_app.post("/server/webhook/sonarr", ...)` + assert `webhook_manager.enqueue_import` |
| COVER-05 | Add `DeleteRemoteProcess` unit tests — SSH command construction, error handling, deletion paths | `patch('controller.delete.delete_process.Sshcp')` at module level; assert `rm -rf` command string + `SshcpError` catch |
| COVER-06 | Add `ActiveScanner` dedicated test file — scan scheduling, result aggregation | `patch('controller.scan.active_scanner.multiprocessing.Queue')` + `patch('controller.scan.active_scanner.SystemScanner')` |
</phase_requirements>

---

## Summary

Phase 94 adds dedicated tests for four previously untested backend paths. All four tasks are test-writing-only — no production code changes. The codebase already has a rich, consistent test infrastructure to follow: `BaseTestWebApp` for integration tests, `unittest.mock.patch` at module level for unit tests, and `conftest.py`/`helpers.py` for shared fixtures.

The core challenge is the SSE tests (COVER-01): the existing skipped tests used `webtest.TestApp.get()` which buffers the full response and blocks forever on a streaming generator. The fix is a thin WSGI iterator harness that calls `web_app(environ, start_response)` directly, iterating the generator in the same thread. The Timer-stop pattern already embedded in the skipped tests is preserved — the Timer calls `web_app.stop()` which sets `_stop_flag = True`, causing the generator loop to exit cleanly.

The other three requirements (COVER-04, COVER-05, COVER-06) follow patterns already established in the codebase. Webhook integration reuses `BaseTestWebApp` exactly as `test_controller.py` does. `DeleteRemoteProcess` mocks mirror `test_extract_process.py`'s `patch('module.ClassName')` style. `ActiveScanner` mocks follow `test_scan_manager.py`'s approach of patching both dependencies at module level.

**Primary recommendation:** Write four test files following existing patterns. No new dependencies required. The WSGI harness is the only novel pattern — a 15-line helper in `tests/helpers/wsgi_stream.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SSE streaming (COVER-01) | API / Backend (Bottle WSGI) | — | Generator lives in `WebApp.__web_stream`; test calls the WSGI interface directly |
| Webhook dispatch (COVER-04) | API / Backend (Bottle routing) | — | Test boundary is Bottle route → `WebhookHandler._handle_webhook` → `webhook_manager.enqueue_import` |
| DeleteRemoteProcess (COVER-05) | API / Backend (controller) | — | Pure Python class, no web layer; SSH mocked at module level |
| ActiveScanner (COVER-06) | API / Backend (controller) | — | Pure Python class, multiprocessing Queue mocked; no web layer |

---

## Standard Stack

### Core (already in `pyproject.toml`)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | ^9.0.3 | Test runner | Project standard [VERIFIED: pyproject.toml] |
| pytest-timeout | ^2.3.1 | Per-test timeouts via `@pytest.mark.timeout` | Already used in `test_scanner_process.py` [VERIFIED: pyproject.toml] |
| webtest | ^3.0.7 | WSGI test client (`TestApp`) | `BaseTestWebApp` wraps it; all integration tests use it [VERIFIED: pyproject.toml] |
| unittest.mock | stdlib | `MagicMock`, `patch` | All existing mock patterns use this [VERIFIED: codebase] |

No new dependencies required for any of the four requirements. [VERIFIED: codebase review]

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
src/python/tests/
├── helpers/
│   └── wsgi_stream.py          # NEW: WSGI iterator harness helper (COVER-01)
├── integration/test_web/test_handler/
│   ├── test_stream_status.py   # MODIFY: remove @unittest.skip, add wsgi harness
│   ├── test_stream_model.py    # MODIFY: remove @unittest.skip, add wsgi harness
│   └── test_stream_log.py      # MODIFY: remove @unittest.skip, add wsgi harness
│   └── test_webhook.py         # NEW: integration test (COVER-04)
└── unittests/test_controller/
    ├── test_delete_process.py  # NEW: DeleteRemoteProcess unit tests (COVER-05)
    └── test_scan/
        └── test_active_scanner.py  # NEW: ActiveScanner unit tests (COVER-06)
```

**Note on the helpers directory:** `tests/helpers.py` already exists as a flat module file. A `tests/helpers/` subdirectory would conflict with it. The WSGI stream helper should either be placed at `tests/helpers/wsgi_stream.py` (which requires converting `tests/helpers.py` to `tests/helpers/__init__.py`) OR at `tests/wsgi_stream_helper.py` as a sibling file. The CONTEXT.md decision D-03 says `tests/helpers/wsgi_stream.py`. The planner must decide whether to convert `helpers.py` to a package or adjust the path.

### Pattern 1: WSGI Iterator Harness (COVER-01)
**What:** Call `web_app(environ, start_response)` directly to obtain the SSE generator, then iterate it in the test thread. The Timer calls `web_app.stop()` after N seconds to terminate the loop.
**When to use:** Any test against the `/server/stream` SSE endpoint.

```python
# Source: D-01/D-02 decisions + analysis of web_app.py __web_stream generator
import io

def make_wsgi_environ(path="/server/stream", method="GET"):
    """Build a minimal Bottle-compatible WSGI environ dict."""
    return {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.StringIO(),
        "wsgi.url_scheme": "http",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "HTTP_HOST": "localhost:8080",
    }

def collect_sse_events(web_app, environ, *, stop_after_s=0.5):
    """
    Iterate the SSE generator and collect all yielded strings.
    Timer fires after stop_after_s seconds, sets web_app._stop_flag,
    which causes the while-not-stop_flag loop to exit.
    """
    from threading import Timer
    Timer(stop_after_s, web_app.stop).start()

    response_started = []
    def start_response(status, headers, exc_info=None):
        response_started.append((status, dict(headers)))

    events = []
    result = web_app(environ, start_response)
    for chunk in result:
        events.append(chunk)
    return response_started, events
```

**Key insight:** `WebApp.__web_stream` is a Bottle route decorated with `@self.get("/server/stream")`. When called as a WSGI app, Bottle invokes the route function and wraps the generator. The `while not self._stop_flag` loop in `__web_stream` exits when `web_app.stop()` sets `_stop_flag = True` via `object.__setattr__`. [VERIFIED: web_app.py lines 206–207, 266–288]

**Timer-sleep interaction:** `time.sleep(_STREAM_POLL_INTERVAL_IN_MS / 1000)` is 100ms. The Timer fires at 500ms, giving approximately 4–5 iterations before exit. This is sufficient to verify initial events are delivered. [VERIFIED: web_app.py lines 54–56, 285–288]

### Pattern 2: Integration Webhook Test (COVER-04)
**What:** Inherit `BaseTestWebApp`, POST JSON to `/server/webhook/sonarr`, assert `self.web_app_builder.webhook_handler.__webhook_manager.enqueue_import` was called.
**When to use:** HTTP → Bottle routing → handler dispatch verification.

```python
# Source: test_controller.py pattern + webhook.py analysis
import json
from tests.integration.test_web.test_web_app import BaseTestWebApp

class TestWebhookIntegration(BaseTestWebApp):
    def test_sonarr_download_enqueues_via_web_layer(self):
        body = {
            "eventType": "Download",
            "episodeFile": {"sourcePath": "/downloads/Show.S01E01-GROUP"}
        }
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)
        self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager\
            .enqueue_import.assert_called_once_with("Sonarr", "Show.S01E01-GROUP")
```

**Note on `webhook_manager` access:** `WebAppBuilder.__init__` creates `self.webhook_handler = WebhookHandler(webhook_manager, context.config)`. The `webhook_manager` argument comes from `WebAppBuilder(self.context, self.controller, self.auto_queue_persist, MagicMock())` — that fourth positional argument is the `webhook_manager`, and it is already a `MagicMock` in `BaseTestWebApp.setUp`. Access it via `self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager`. [VERIFIED: web_app_builder.py lines 35, 56]

### Pattern 3: DeleteRemoteProcess Unit Test (COVER-05)
**What:** Patch `Sshcp` at module level, instantiate `DeleteRemoteProcess`, call `run_once()`, assert `shell()` called with correct `rm -rf` command.

```python
# Source: D-07/D-08 decisions + delete_process.py analysis
import unittest
from unittest.mock import patch, MagicMock
from controller.delete.delete_process import DeleteRemoteProcess
from ssh import SshcpError

class TestDeleteRemoteProcess(unittest.TestCase):
    def setUp(self):
        sshcp_patcher = patch('controller.delete.delete_process.Sshcp')
        self.addCleanup(sshcp_patcher.stop)
        self.mock_sshcp_cls = sshcp_patcher.start()
        self.mock_sshcp = self.mock_sshcp_cls.return_value

    def test_constructs_sshcp_with_correct_args(self):
        DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password="pass", remote_port=22,
            remote_path="/remote", file_name="file.mkv"
        )
        self.mock_sshcp_cls.assert_called_once_with(
            host="host", port=22, user="user", password="pass"
        )

    def test_run_once_issues_rm_rf_command(self):
        import shlex, os
        proc = DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password="pass", remote_port=22,
            remote_path="/remote/path", file_name="file name.mkv"
        )
        self.mock_sshcp.shell.return_value = b""
        proc.run_once()
        expected_path = shlex.quote(os.path.join("/remote/path", "file name.mkv"))
        self.mock_sshcp.shell.assert_called_once_with("rm -rf {}".format(expected_path))

    def test_run_once_catches_sshcp_error(self):
        proc = DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password=None, remote_port=22,
            remote_path="/remote", file_name="file.mkv"
        )
        self.mock_sshcp.shell.side_effect = SshcpError("connection refused")
        # Should not raise — SshcpError is caught and logged
        proc.run_once()
```

[VERIFIED: delete_process.py lines 26–50]

### Pattern 4: ActiveScanner Unit Test (COVER-06)
**What:** Patch `multiprocessing.Queue` and `SystemScanner` at module level. Test queue-drain logic, multi-put drain, `SystemScannerError` suppression, and `(files, None, None)` return.

```python
# Source: D-10/D-11/D-12 decisions + active_scanner.py analysis
import unittest
from unittest.mock import patch, MagicMock, call
import queue
from controller.scan.active_scanner import ActiveScanner
from system import SystemScannerError, SystemFile

class TestActiveScanner(unittest.TestCase):
    def setUp(self):
        # Patch multiprocessing.Queue to use regular queue.Queue (no pickle needed)
        queue_patcher = patch(
            'controller.scan.active_scanner.multiprocessing.Queue',
            side_effect=lambda: queue.Queue()
        )
        self.addCleanup(queue_patcher.stop)
        queue_patcher.start()

        scanner_patcher = patch('controller.scan.active_scanner.SystemScanner')
        self.addCleanup(scanner_patcher.stop)
        self.mock_scanner_cls = scanner_patcher.start()
        self.mock_scanner = self.mock_scanner_cls.return_value

    def test_scan_returns_empty_on_first_call(self):
        scanner = ActiveScanner("/local/path")
        files, total, used = scanner.scan()
        self.assertEqual([], files)
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_set_active_files_then_scan(self):
        scanner = ActiveScanner("/local/path")
        f = SystemFile("a.mkv", 100, False)
        self.mock_scanner.scan_single.return_value = f
        scanner.set_active_files(["a.mkv"])
        files, total, used = scanner.scan()
        self.assertEqual([f], files)
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_scan_drains_all_queued_file_lists(self):
        """Multiple set_active_files calls — only the last list is used."""
        scanner = ActiveScanner("/local/path")
        f1 = SystemFile("old.mkv", 10, False)
        f2 = SystemFile("new.mkv", 20, False)
        self.mock_scanner.scan_single.side_effect = [f1, f2]
        scanner.set_active_files(["old.mkv"])
        scanner.set_active_files(["new.mkv"])
        files, _, _ = scanner.scan()
        # Drain loop consumes both puts; last list wins
        self.assertEqual(["new.mkv"], [f.name for f in files])

    def test_scan_suppresses_system_scanner_error(self):
        scanner = ActiveScanner("/local/path")
        scanner.set_active_files(["missing.mkv"])
        self.mock_scanner.scan_single.side_effect = SystemScannerError("not found")
        files, total, used = scanner.scan()
        self.assertEqual([], files)
        self.assertIsNone(total)
        self.assertIsNone(used)
```

[VERIFIED: active_scanner.py lines 1–52]

### Anti-Patterns to Avoid
- **Using `webtest.TestApp.get("/server/stream")` for SSE:** TestApp buffers the entire response body before returning; it will block forever waiting for the generator to terminate. [VERIFIED: existing skip comment in test_stream_status.py line 8]
- **Using real `multiprocessing.Queue` in ActiveScanner unit tests:** `MagicMock` objects cannot be pickled across process boundaries; this causes `_pickle.PicklingError`. [VERIFIED: live test run of test_scanner_process.py::TestScannerProcess::test_retrieves_scan_results shows this exact failure]
- **Patching at the wrong module level:** `patch('ssh.Sshcp')` patches the wrong reference. Must patch `'controller.delete.delete_process.Sshcp'` where the name is imported. [VERIFIED: delete_process.py line 7 `from ssh import Sshcp, SshcpError`]
- **Testing WebhookManager internals in integration tests:** `test_webhook_manager.py` already covers `process()` logic exhaustively (28 passing tests). The integration test's only job is verifying Bottle routing + dispatch — not re-testing handler logic. [VERIFIED: test_webhook_handler.py — 28 tests pass]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WSGI environ dict | Custom full-spec dict | Minimal dict with required keys only | Bottle only reads the keys it needs; 12-key dict is sufficient |
| SSE event parsing | SSE parser | Iterate raw chunks, check string content | Tests verify event delivery, not SSE format |
| MagicMock with spec | Generic MagicMock | Generic MagicMock | Spec constraints create extra friction for these simple mocks |

**Key insight:** The existing test infrastructure covers all setup/teardown needs. The only novel helper is the 15-line `wsgi_stream.py` harness.

---

## Common Pitfalls

### Pitfall 1: `helpers.py` vs `helpers/` Package Conflict
**What goes wrong:** `tests/helpers.py` (a module file) already exists. Creating `tests/helpers/wsgi_stream.py` requires a directory named `helpers`, which conflicts with the existing file.
**Why it happens:** Python cannot have both `tests/helpers.py` (module) and `tests/helpers/` (package) on the same path.
**How to avoid:** Either (a) rename `helpers.py` to `helpers/__init__.py` and put `wsgi_stream.py` alongside it, OR (b) place the helper at `tests/wsgi_stream_helper.py`. Decision D-03 says `tests/helpers/wsgi_stream.py`, so option (a) is the locked path — but the planner must explicitly include the `helpers/__init__.py` rename step.
**Warning signs:** `ModuleNotFoundError: No module named 'tests.helpers'` after creating the directory.

### Pitfall 2: SSE Timer Race on Slow CI
**What goes wrong:** If CI is slow, `Timer(0.5, web_app.stop)` fires before any iteration completes, causing tests that assert specific call counts to flake.
**Why it happens:** The 100ms sleep in the poll loop means 5 iterations in 500ms nominally, but CI jitter can reduce this.
**How to avoid:** For tests that count specific calls (e.g., `assertEqual(1, len(mock_serialize.status.call_args_list))`), ensure the `get_value()` mock returns a non-empty value so `had_value=True` triggers the shorter 10ms sleep. The initial status test always fires on first iteration so 500ms is ample.
**Warning signs:** Intermittent `AssertionError: 0 != 1` on call count assertions.

### Pitfall 3: `_stop_flag` Assignment in `WebApp`
**What goes wrong:** Directly assigning `web_app._stop_flag = False` in test teardown (or accessing it) may fail because Bottle overrides `__setattr__`.
**Why it happens:** `WebApp.__init__` uses `object.__setattr__(self, '_stop_flag', False)` specifically to bypass Bottle's `__setattr__`. The `stop()` method does the same.
**How to avoid:** Always call `web_app.stop()` rather than setting `_stop_flag` directly. The Timer approach in existing tests is correct.
**Warning signs:** `AttributeError` or silent no-op when setting `_stop_flag`.

### Pitfall 4: `WebhookHandler.__webhook_manager` Name Mangling
**What goes wrong:** `self.web_app_builder.webhook_handler.webhook_manager` raises `AttributeError` — the attribute is name-mangled.
**Why it happens:** `self.__webhook_manager` in `WebhookHandler.__init__` becomes `_WebhookHandler__webhook_manager`.
**How to avoid:** Access via `webhook_handler._WebhookHandler__webhook_manager`. Alternatively, access the `MagicMock` that was passed in: `WebAppBuilder.__init__` receives `webhook_manager` as its 4th argument, but that argument is not stored on the builder — it's only passed to `WebhookHandler`. The only way to access it is through name-mangling.
**Warning signs:** `AttributeError: 'WebhookHandler' object has no attribute 'webhook_manager'`

### Pitfall 5: `multiprocessing.Queue` import path in `active_scanner.py`
**What goes wrong:** `patch('multiprocessing.Queue')` patches the global multiprocessing module, not the reference inside `active_scanner`.
**Why it happens:** `active_scanner.py` imports `import multiprocessing` (whole module). Calls it as `multiprocessing.Queue()`. The correct patch target is `controller.scan.active_scanner.multiprocessing.Queue`.
**How to avoid:** Always patch the reference at the module that uses it. Confirmed: `active_scanner.py` line 1: `import multiprocessing`; line 19: `self.__active_files_queue = multiprocessing.Queue()`. [VERIFIED: active_scanner.py]

---

## Code Examples

### WSGI Environ Construction
```python
# Source: analysis of bottle.Bottle.__call__ and wsgiref.handlers required keys
import io

MINIMAL_WSGI_ENVIRON = {
    "REQUEST_METHOD": "GET",
    "PATH_INFO": "/server/stream",
    "SERVER_NAME": "localhost",
    "SERVER_PORT": "8080",
    "wsgi.input": io.BytesIO(b""),
    "wsgi.errors": io.StringIO(),
    "wsgi.url_scheme": "http",
    "wsgi.multithread": False,
    "wsgi.multiprocess": False,
    "wsgi.run_once": False,
    "HTTP_HOST": "localhost:8080",
}
```

### Collecting SSE Chunks
```python
# Source: D-01 decision + web_app.py __web_stream generator
from threading import Timer

def collect_stream_chunks(web_app, stop_after_s=0.5):
    Timer(stop_after_s, web_app.stop).start()
    started = []
    def start_response(status, headers, exc_info=None):
        started.append((status, headers))
    chunks = list(web_app(MINIMAL_WSGI_ENVIRON, start_response))
    return started, chunks
```

### DeleteRemoteProcess `patch` Setup
```python
# Source: delete_process.py import structure
# File: controller/delete/delete_process.py, line 7:
#   from ssh import Sshcp, SshcpError
# Correct patch target: 'controller.delete.delete_process.Sshcp'
with patch('controller.delete.delete_process.Sshcp') as mock_cls:
    mock_instance = mock_cls.return_value
    # ... test body
```

### `shlex.quote` Expected Command
```python
# Source: delete_process.py lines 44-47
import os, shlex
remote_path = "/remote/path"
file_name = "My Show S01E01.mkv"
file_path = os.path.join(remote_path, file_name)
expected_cmd = "rm -rf {}".format(shlex.quote(file_path))
# => "rm -rf '/remote/path/My Show S01E01.mkv'"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `webtest.TestApp.get()` for SSE | WSGI iterator harness | Phase 94 (D-01) | Unblocks the 3 skipped SSE test files |
| SSE tests skipped | SSE tests active | Phase 94 | COVER-01 gap closed |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `WebAppBuilder` stores `webhook_handler` as a public attribute accessible via `self.web_app_builder.webhook_handler` | Code Examples / Pitfall 4 | Test cannot access the mock without a different access path — LOW risk, confirmed by reading `web_app_builder.py` [VERIFIED] |

**All other claims in this research were verified directly against source files.**

---

## Open Questions

1. **`helpers.py` vs `helpers/` package conflict**
   - What we know: `tests/helpers.py` exists as a flat file. D-03 specifies `tests/helpers/wsgi_stream.py`.
   - What's unclear: Whether the planner should (a) convert `helpers.py` to `helpers/__init__.py` or (b) use an alternate path.
   - Recommendation: The plan should include an explicit task to rename `helpers.py` → `helpers/__init__.py` before creating `wsgi_stream.py`. This is a one-line rename with no import changes needed (existing imports use `from tests.helpers import ...` which works identically with a package).

---

## Environment Availability

Step 2.6: The phase is test-writing-only. All dependencies (`pytest`, `webtest`, `unittest.mock`) are in `pyproject.toml` dev dependencies and confirmed available via `poetry run pytest`.

```
poetry run pytest ... -> 5 passed (test_controller.py integration tests)
poetry run pytest ... -> 28 passed (test_webhook_handler.py unit tests)
```
[VERIFIED: live test runs above]

No missing dependencies.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd src/python && poetry run pytest tests/integration/test_web/test_handler/ tests/unittests/test_controller/test_delete_process.py tests/unittests/test_controller/test_scan/test_active_scanner.py -x` |
| Full suite command | `cd src/python && poetry run pytest --cov --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COVER-01 | SSE streaming delivers events through WSGI layer | integration | `poetry run pytest tests/integration/test_web/test_handler/test_stream_status.py tests/integration/test_web/test_handler/test_stream_model.py tests/integration/test_web/test_handler/test_stream_log.py -x` | Exists (skipped — unskip + update) |
| COVER-04 | Sonarr/Radarr POST routes to `enqueue_import` | integration | `poetry run pytest tests/integration/test_web/test_handler/test_webhook.py -x` | Does not exist — Wave 0 |
| COVER-05 | DeleteRemoteProcess SSH command + error handling | unit | `poetry run pytest tests/unittests/test_controller/test_delete_process.py -x` | Does not exist — Wave 0 |
| COVER-06 | ActiveScanner queue drain + error suppression | unit | `poetry run pytest tests/unittests/test_controller/test_scan/test_active_scanner.py -x` | Does not exist — Wave 0 |

### Sampling Rate
- **Per task commit:** Run the single new/modified test file with `-x`
- **Per wave merge:** `cd src/python && poetry run pytest tests/integration/test_web tests/unittests/test_controller -x`
- **Phase gate:** `cd src/python && poetry run pytest --cov --cov-report=term-missing` (coverage gate ≥ 84%)

### Wave 0 Gaps
- [ ] `tests/integration/test_web/test_handler/test_webhook.py` — COVER-04
- [ ] `tests/unittests/test_controller/test_delete_process.py` — COVER-05
- [ ] `tests/unittests/test_controller/test_scan/test_active_scanner.py` — COVER-06
- [ ] `tests/helpers/wsgi_stream.py` (plus rename `helpers.py` → `helpers/__init__.py`) — COVER-01

No framework install needed — pytest is already available.

---

## Security Domain

This phase writes tests only. No production code changes. No new authentication, session management, or input validation surface area introduced. No ASVS categories apply.

---

## Sources

### Primary (HIGH confidence)
- `src/python/web/web_app.py` — SSE generator implementation, `_stop_flag` mechanism, `IStreamHandler` interface
- `src/python/web/web_app_builder.py` — How `webhook_manager` is wired as `MagicMock` via 4th constructor arg
- `src/python/controller/delete/delete_process.py` — `DeleteRemoteProcess` full implementation (50 lines)
- `src/python/controller/scan/active_scanner.py` — `ActiveScanner` full implementation (52 lines)
- `src/python/web/handler/webhook.py` — `WebhookHandler._handle_webhook` dispatch logic
- `src/python/tests/integration/test_web/test_web_app.py` — `BaseTestWebApp` setup pattern
- `src/python/tests/integration/test_web/test_handler/test_controller.py` — POST-through-webtest pattern
- `src/python/tests/integration/test_web/test_handler/test_stream_status.py` — Existing skipped SSE test with Timer pattern
- `src/python/tests/integration/test_web/test_handler/test_stream_model.py` — Existing skipped SSE test
- `src/python/tests/integration/test_web/test_handler/test_stream_log.py` — Existing skipped SSE test
- `src/python/tests/unittests/test_controller/test_extract/test_extract_process.py` — Module-level patch pattern for SSH-like mocks
- `src/python/tests/unittests/test_controller/test_scan/test_scanner_process.py` — `ActiveScanner` 3-tuple contract test (already exists at `TestIScannerContract`)
- `src/python/tests/unittests/test_web/test_webhook_handler.py` — Existing 28-test webhook unit test baseline
- `src/python/pyproject.toml` — Confirmed test dependencies and pytest config
- `src/python/tests/helpers.py` — Confirmed flat file (module, not package) — impacts wsgi_stream.py placement

### Verified via live test runs
- `poetry run pytest tests/integration/test_web/test_handler/test_controller.py` — 5 passed
- `poetry run pytest tests/unittests/test_web/test_webhook_handler.py` — 28 passed
- `poetry run pytest tests/integration/test_web/test_handler/test_stream_status.py` — 2 skipped (confirms problem)
- `poetry run pytest tests/unittests/test_controller/test_scan/test_scanner_process.py::TestScannerProcess::test_retrieves_scan_results` — FAILED with `_pickle.PicklingError` (confirms MagicMock + multiprocessing.Queue incompatibility)
- `poetry run pytest tests/unittests/test_controller/test_scan/test_scanner_process.py::TestIScannerContract` — 1 passed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified in pyproject.toml and by live test run
- Architecture patterns: HIGH — all patterns verified directly against source code and live test runs
- Pitfalls: HIGH — Pitfalls 1 and 2 verified by inspection; Pitfall 2 (pickle error) verified by live test run

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable codebase, no upstream changes expected)
