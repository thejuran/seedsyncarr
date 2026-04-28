# Phase 94: Test Coverage -- Backend - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 8 (3 modified + 5 new)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/helpers/__init__.py` (rename from `helpers.py`) | utility | — | `tests/helpers.py` (itself) | exact — rename only |
| `tests/helpers/wsgi_stream.py` | utility / test-helper | streaming | `tests/integration/test_web/test_web_app.py` (BaseTestWebApp setup) | partial — novel pattern, no existing analog |
| `tests/integration/test_web/test_handler/test_stream_status.py` | test (integration) | streaming | itself + `test_stream_model.py`, `test_stream_log.py` | exact — modify in place |
| `tests/integration/test_web/test_handler/test_stream_model.py` | test (integration) | streaming | itself | exact — modify in place |
| `tests/integration/test_web/test_handler/test_stream_log.py` | test (integration) | streaming | itself | exact — modify in place |
| `tests/integration/test_web/test_handler/test_webhook.py` | test (integration) | request-response | `tests/integration/test_web/test_handler/test_controller.py` | exact — same BaseTestWebApp POST pattern |
| `tests/unittests/test_controller/test_delete_process.py` | test (unit) | request-response | `tests/unittests/test_controller/test_extract/test_extract_process.py` | role-match — same module-level patch pattern |
| `tests/unittests/test_controller/test_scan/test_active_scanner.py` | test (unit) | event-driven / batch | `tests/unittests/test_controller/test_scan_manager.py` | role-match — same multi-patch setUp pattern |

---

## Pattern Assignments

### `tests/helpers/__init__.py` (rename/convert, utility)

**Analog:** `tests/helpers.py` (the file itself)

**Action:** Rename `tests/helpers.py` to `tests/helpers/__init__.py`. No code changes — existing imports (`from tests.helpers import ...`) continue to work identically after the rename because Python resolves both `tests.helpers` (module) and `tests.helpers` (package `__init__`) the same way. This rename is a prerequisite for creating `tests/helpers/wsgi_stream.py`.

**Existing imports pattern** (`tests/helpers.py` lines 1–14):
```python
import logging
import sys
from unittest.mock import MagicMock

from common import Config


def create_test_logger(name: str) -> tuple:
    ...

def create_mock_context(logger=None):
    ...

def create_mock_context_with_real_config(logger=None):
    ...
```

---

### `tests/helpers/wsgi_stream.py` (new, utility / test-helper, streaming)

**Analog:** None in codebase — novel pattern. Use RESEARCH.md Pattern 1 directly.

**Key constraint from production code:**
- `WebApp.__web_stream` registers at `@self.get("/server/stream")` via Bottle (verified: `web_app.py` lines 248–298)
- `WebApp.stop()` uses `object.__setattr__(self, '_stop_flag', True)` (lines 202–207)
- Never set `_stop_flag` directly — always call `web_app.stop()`
- The poll loop sleeps 100ms (`_STREAM_POLL_INTERVAL_IN_MS`) between idle iterations; 10ms when data is available (`_STREAM_YIELD_INTERVAL_IN_MS`) (lines 54–55, 286–288)

**Full implementation pattern** (from RESEARCH.md Pattern 1):
```python
import io
from threading import Timer


def make_wsgi_environ(path: str = "/server/stream", method: str = "GET") -> dict:
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


def collect_sse_chunks(web_app, path: str = "/server/stream", stop_after_s: float = 0.5):
    """
    Iterate the SSE generator and collect all yielded chunks.

    Timer fires after stop_after_s seconds, calls web_app.stop() which sets
    _stop_flag = True via object.__setattr__, causing the while-not-stop_flag
    loop in __web_stream to exit cleanly.

    Returns:
        (response_started, chunks) where response_started is a list of
        (status, headers_dict) tuples and chunks is a list of bytes/str.
    """
    environ = make_wsgi_environ(path=path)
    Timer(stop_after_s, web_app.stop).start()

    response_started = []

    def start_response(status, headers, exc_info=None):
        response_started.append((status, dict(headers)))

    chunks = list(web_app(environ, start_response))
    return response_started, chunks
```

---

### `tests/integration/test_web/test_handler/test_stream_status.py` (modify, test integration, streaming)

**Analog:** itself — `tests/integration/test_web/test_handler/test_stream_status.py`

**Current state:** Class decorated with `@unittest.skip(...)` (line 8). All test methods call `self.test_app.get("/server/stream")` (lines 19, 41) which blocks forever.

**Changes required:**
1. Remove `@unittest.skip(...)` decorator (line 8)
2. Replace `self.test_app.get("/server/stream")` with `collect_sse_chunks(self.web_app)` from the wsgi_stream helper
3. Add import for `collect_sse_chunks`

**Existing imports pattern** (lines 1–5):
```python
import unittest
from unittest.mock import patch
from threading import Timer

from tests.integration.test_web.test_web_app import BaseTestWebApp
```

**After change — imports:**
```python
import unittest
from unittest.mock import patch
from threading import Timer

from tests.integration.test_web.test_web_app import BaseTestWebApp
from tests.helpers.wsgi_stream import collect_sse_chunks
```

**Existing Timer-stop pattern to preserve** (lines 12–13, 29–30):
```python
# Schedule server stop
Timer(0.5, self.web_app.stop).start()
```
This pattern is already correct — the Timer calls `web_app.stop()` not direct `_stop_flag` access. Keep as-is. The only replacement is `self.test_app.get("/server/stream")` → `collect_sse_chunks(self.web_app)`.

**Mock setup pattern to preserve** (lines 16–18):
```python
mock_serialize = mock_serialize_status_cls.return_value
mock_serialize.status.return_value = "\n"
```
Return `"\n"` (a non-empty string) so `had_value = True` fires, using the 10ms yield interval instead of the 100ms poll interval — reduces flake risk.

---

### `tests/integration/test_web/test_handler/test_stream_model.py` (modify, test integration, streaming)

**Analog:** itself — same pattern as `test_stream_status.py`

**Existing imports pattern** (lines 1–7):
```python
import unittest
from unittest.mock import patch, ANY
from threading import Timer

from tests.integration.test_web.test_web_app import BaseTestWebApp
from web.serialize import SerializeModel
from model import ModelFile
```

**After change — imports:**
```python
import unittest
from unittest.mock import patch, ANY
from threading import Timer

from tests.integration.test_web.test_web_app import BaseTestWebApp
from web.serialize import SerializeModel
from model import ModelFile
from tests.helpers.wsgi_stream import collect_sse_chunks
```

**Same changes as test_stream_status.py:** Remove `@unittest.skip`, replace all `self.test_app.get("/server/stream")` with `collect_sse_chunks(self.web_app)`.

Note: `test_stream_model_serializes_updates` uses `Timer(2.0, self.web_app.stop)` (line 44) — keep the longer timer as-is, it is testing update events that arrive at 0.5s.

---

### `tests/integration/test_web/test_handler/test_stream_log.py` (modify, test integration, streaming)

**Analog:** itself — same pattern

**Existing imports pattern** (lines 1–7):
```python
import logging
import unittest
from unittest.mock import patch
from threading import Timer

from tests.integration.test_web.test_web_app import BaseTestWebApp
```

**After change — imports:**
```python
import logging
import unittest
from unittest.mock import patch
from threading import Timer

from tests.integration.test_web.test_web_app import BaseTestWebApp
from tests.helpers.wsgi_stream import collect_sse_chunks
```

**Same changes:** Remove `@unittest.skip`, replace `self.test_app.get("/server/stream")` with `collect_sse_chunks(self.web_app)`.

---

### `tests/integration/test_web/test_handler/test_webhook.py` (new, test integration, request-response)

**Analog:** `tests/integration/test_web/test_handler/test_controller.py`

**Class structure pattern** (test_controller.py lines 1–7):
```python
from unittest.mock import MagicMock
from urllib.parse import quote

from tests.integration.test_web.test_web_app import BaseTestWebApp
from controller import Controller


class TestControllerHandler(BaseTestWebApp):
```

**POST dispatch pattern** (test_controller.py lines 9–16):
```python
def test_queue(self):
    def side_effect(cmd: Controller.Command):
        cmd.callbacks[0].on_success()
    self.controller.queue_command = MagicMock()
    self.controller.queue_command.side_effect = side_effect

    print(self.test_app.post("/server/command/queue/test1"))
    command = self.controller.queue_command.call_args[0][0]
    self.assertEqual(Controller.Command.Action.QUEUE, command.action)
```

**Webhook-specific adapter:** `BaseTestWebApp.setUp` (test_web_app.py line 53–56) passes `MagicMock()` as the 4th arg to `WebAppBuilder`. That becomes `WebhookHandler.__webhook_manager` via:
```python
# web_app_builder.py line 35:
self.webhook_handler = WebhookHandler(webhook_manager, context.config)
```
Access the mock via name-mangling: `self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager`.

**Full new file pattern:**
```python
import json
import unittest

from tests.integration.test_web.test_web_app import BaseTestWebApp


class TestWebhookIntegration(BaseTestWebApp):
    def test_sonarr_download_enqueues_via_web_layer(self):
        body = {
            "eventType": "Download",
            "episodeFile": {"sourcePath": "/downloads/Show.S01E01-GROUP"}
        }
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)
        mock_wm = self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager
        mock_wm.enqueue_import.assert_called_once_with("Sonarr", "Show.S01E01-GROUP")

    def test_radarr_download_enqueues_via_web_layer(self):
        body = {
            "eventType": "Download",
            "movieFile": {"sourcePath": "/downloads/Movie.2024-GROUP"}
        }
        resp = self.test_app.post_json("/server/webhook/radarr", body)
        self.assertEqual(200, resp.status_int)
        mock_wm = self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager
        mock_wm.enqueue_import.assert_called_once_with("Radarr", "Movie.2024-GROUP")

    def test_sonarr_test_event_returns_200_without_enqueue(self):
        body = {"eventType": "Test"}
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)
        mock_wm = self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager
        mock_wm.enqueue_import.assert_not_called()

    def test_sonarr_unknown_event_returns_200_without_enqueue(self):
        body = {"eventType": "Grab"}
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)
        mock_wm = self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager
        mock_wm.enqueue_import.assert_not_called()
```

**Note on HMAC:** `BaseTestWebApp` uses a real `Config()` (`test_web_app.py` line 39: `self.context.config = Config()`). `Config().general.webhook_secret` defaults to empty/None, so `_verify_hmac()` short-circuits and skips signature validation — no HMAC header needed in tests.

---

### `tests/unittests/test_controller/test_delete_process.py` (new, test unit, request-response)

**Analog:** `tests/unittests/test_controller/test_extract/test_extract_process.py`

**Module-level patch pattern** (test_extract_process.py lines 16–24):
```python
class TestExtractProcess(unittest.TestCase):
    def setUp(self):
        dispatch_patcher = patch('controller.extract.extract_process.ExtractDispatch')
        self.addCleanup(dispatch_patcher.stop)
        self.mock_dispatch_cls = dispatch_patcher.start()
        self.mock_dispatch = self.mock_dispatch_cls.return_value

        # by default mock returns empty statuses
        self.mock_dispatch.status.return_value = []
```

**Logger setup pattern** (test_extract_process.py lines 26–30):
```python
logger = logging.getLogger()
self._test_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(self._test_handler)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
self._test_handler.setFormatter(formatter)
```

**tearDown cleanup** (test_extract_process.py lines 37–40):
```python
def tearDown(self):
    logging.getLogger().removeHandler(self._test_handler)
    if self.process:
        self.process.terminate()
```

**Production code reference** (delete_process.py lines 26–50):
```python
# Constructor — keyword args to Sshcp:
self.__ssh = Sshcp(host=remote_address, port=remote_port,
                   user=remote_username, password=remote_password)

# run_once — the rm -rf command:
file_path = os.path.join(self.__remote_path, self.__file_name)
out = self.__ssh.shell("rm -rf {}".format(shlex.quote(file_path)))

# Error handling:
except SshcpError:
    self.logger.exception("Exception while deleting remote file")
```

**Full new file pattern:**
```python
import logging
import os
import shlex
import sys
import unittest
from unittest.mock import patch

from controller.delete.delete_process import DeleteRemoteProcess
from ssh import SshcpError


class TestDeleteRemoteProcess(unittest.TestCase):
    def setUp(self):
        sshcp_patcher = patch('controller.delete.delete_process.Sshcp')
        self.addCleanup(sshcp_patcher.stop)
        self.mock_sshcp_cls = sshcp_patcher.start()
        self.mock_sshcp = self.mock_sshcp_cls.return_value

        logger = logging.getLogger()
        self._test_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(self._test_handler)
        logger.setLevel(logging.DEBUG)
        logger.setFormatter = None  # noqa — logger handler handles formatting
        self._test_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )

    def tearDown(self):
        logging.getLogger().removeHandler(self._test_handler)

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
        proc = DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password="pass", remote_port=22,
            remote_path="/remote/path", file_name="file name.mkv"
        )
        self.mock_sshcp.shell.return_value = b""
        proc.run_once()
        expected_path = shlex.quote(os.path.join("/remote/path", "file name.mkv"))
        self.mock_sshcp.shell.assert_called_once_with(
            "rm -rf {}".format(expected_path)
        )

    def test_run_once_catches_sshcp_error_without_raising(self):
        proc = DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password=None, remote_port=22,
            remote_path="/remote", file_name="file.mkv"
        )
        self.mock_sshcp.shell.side_effect = SshcpError("connection refused")
        # Must not raise — SshcpError is caught and logged
        proc.run_once()

    def test_constructs_sshcp_with_none_password(self):
        DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password=None, remote_port=2222,
            remote_path="/remote", file_name="file.mkv"
        )
        self.mock_sshcp_cls.assert_called_once_with(
            host="host", port=2222, user="user", password=None
        )
```

**Critical patch target:** `'controller.delete.delete_process.Sshcp'` — NOT `'ssh.Sshcp'`. The import in delete_process.py is `from ssh import Sshcp, SshcpError` (line 7), so the name bound in `controller.delete.delete_process` is the patch target.

---

### `tests/unittests/test_controller/test_scan/test_active_scanner.py` (new, test unit, event-driven/batch)

**Analog:** `tests/unittests/test_controller/test_scan_manager.py`

**Multi-patch setUp pattern** (test_scan_manager.py lines 33–38):
```python
@patch('controller.scan_manager.ScannerProcess')
@patch('controller.scan_manager.ActiveScanner')
@patch('controller.scan_manager.LocalScanner')
@patch('controller.scan_manager.RemoteScanner')
def test_init_creates_scanners_and_processes(
        self, mock_remote_scanner, mock_local_scanner,
        mock_active_scanner, mock_scanner_process):
```

**Alternative: setUp-level patchers** (test_extract_process.py lines 17–21) — preferred for ActiveScanner because all tests share the same two mocks:
```python
def setUp(self):
    patcher = patch('controller.extract.extract_process.ExtractDispatch')
    self.addCleanup(patcher.stop)
    self.mock_cls = patcher.start()
    self.mock_instance = self.mock_cls.return_value
```

**Production code reference** (active_scanner.py lines 17–52):
```python
# Constructor — creates Queue and SystemScanner:
self.__scanner = SystemScanner(local_path)
self.__active_files_queue = multiprocessing.Queue()
self.__active_files = []

# set_active_files — puts to queue:
def set_active_files(self, file_names: List[str]):
    self.__active_files_queue.put(file_names)

# scan — drains queue (while True get non-blocking), then scans each file:
try:
    while True:
        self.__active_files = self.__active_files_queue.get(block=False)
except queue.Empty:
    pass

result = []
for file_name in self.__active_files:
    try:
        result.append(self.__scanner.scan_single(file_name))
    except SystemScannerError as ex:
        self.logger.warning(str(ex))
return result, None, None
```

**Existing 3-tuple contract test** (test_scanner_process.py lines 182–197):
```python
class TestIScannerContract(unittest.TestCase):
    def test_active_scanner_returns_three_tuple(self):
        scanner = ActiveScanner(tempfile.gettempdir())
        result = scanner.scan()
        self.assertIsInstance(result, tuple)
        self.assertEqual(3, len(result))
        files, total, used = result
        self.assertIsInstance(files, list)
        self.assertIsNone(total)
        self.assertIsNone(used)
```
Do NOT duplicate this test — it already passes in `test_scanner_process.py::TestIScannerContract`.

**Full new file pattern:**
```python
import queue
import unittest
from unittest.mock import patch, MagicMock

from controller.scan.active_scanner import ActiveScanner
from system import SystemScannerError, SystemFile


class TestActiveScanner(unittest.TestCase):
    def setUp(self):
        # Patch multiprocessing.Queue to use stdlib queue.Queue (no pickle needed)
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

    def test_set_active_files_then_scan_returns_scanned_file(self):
        scanner = ActiveScanner("/local/path")
        f = SystemFile("a.mkv", 100, False)
        self.mock_scanner.scan_single.return_value = f
        scanner.set_active_files(["a.mkv"])
        files, total, used = scanner.scan()
        self.assertEqual([f], files)
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_scan_drains_all_queued_puts_uses_last(self):
        """Multiple set_active_files calls — queue drains; last list is used."""
        scanner = ActiveScanner("/local/path")
        f_old = SystemFile("old.mkv", 10, False)
        f_new = SystemFile("new.mkv", 20, False)
        self.mock_scanner.scan_single.side_effect = [f_old, f_new]
        scanner.set_active_files(["old.mkv"])
        scanner.set_active_files(["new.mkv"])
        files, _, _ = scanner.scan()
        # Drain loop consumes both puts; last list ("new.mkv") wins
        self.assertEqual(1, len(files))
        self.assertEqual("new.mkv", files[0].name)

    def test_scan_suppresses_system_scanner_error(self):
        scanner = ActiveScanner("/local/path")
        scanner.set_active_files(["missing.mkv"])
        self.mock_scanner.scan_single.side_effect = SystemScannerError("not found")
        files, total, used = scanner.scan()
        self.assertEqual([], files)
        self.assertIsNone(total)
        self.assertIsNone(used)
```

**Critical patch target:** `'controller.scan.active_scanner.multiprocessing.Queue'` — NOT `'multiprocessing.Queue'`. `active_scanner.py` does `import multiprocessing` (line 3) then calls `multiprocessing.Queue()` (line 19). Patching the attribute on the module-level reference is correct.

---

## Shared Patterns

### BaseTestWebApp inheritance
**Source:** `tests/integration/test_web/test_web_app.py` lines 13–58
**Apply to:** `test_webhook.py`, SSE stream tests (already use it)

```python
# BaseTestWebApp.setUp wires everything needed:
self.web_app_builder = WebAppBuilder(self.context,
                                     self.controller,
                                     self.auto_queue_persist,
                                     MagicMock())   # <-- 4th arg becomes webhook_manager
self.web_app = self.web_app_builder.build()
self.test_app = TestApp(self.web_app)
```

The 4th positional `MagicMock()` flows to `WebhookHandler.__init__` as `webhook_manager` (web_app_builder.py line 35). Access it via `self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager`.

### Module-level patch with addCleanup
**Source:** `tests/unittests/test_controller/test_extract/test_extract_process.py` lines 17–21
**Apply to:** `test_delete_process.py`, `test_active_scanner.py`

```python
patcher = patch('module.path.ClassName')
self.addCleanup(patcher.stop)
self.mock_cls = patcher.start()
self.mock_instance = self.mock_cls.return_value
```

Always use `addCleanup(patcher.stop)` immediately after creating the patcher — ensures cleanup even if setUp itself raises partway through.

### Logger setup / teardown
**Source:** `tests/unittests/test_controller/test_extract/test_extract_process.py` lines 26–30, 37–38
**Apply to:** `test_delete_process.py` (unit tests that exercise logging paths)

```python
def setUp(self):
    logger = logging.getLogger()
    self._test_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(self._test_handler)
    logger.setLevel(logging.DEBUG)
    self._test_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )

def tearDown(self):
    logging.getLogger().removeHandler(self._test_handler)
```

Alternatively, use `create_test_logger(name)` from `tests/helpers.py` (helpers/__init__.py after rename) which already encapsulates this pattern.

---

## No Analog Found

All files have analogs. The only novel pattern is the WSGI stream harness (`tests/helpers/wsgi_stream.py`), which has no direct codebase analog but follows patterns derived from `web_app.py`'s WSGI interface and the existing Timer-stop usage in the skipped test files.

---

## Critical Pitfalls (for planner reference)

| Pitfall | File affected | Guard |
|---------|--------------|-------|
| `helpers.py` vs `helpers/` package conflict | `wsgi_stream.py` | Rename `helpers.py` → `helpers/__init__.py` BEFORE creating `wsgi_stream.py` |
| Wrong patch target for Sshcp | `test_delete_process.py` | Use `'controller.delete.delete_process.Sshcp'`, not `'ssh.Sshcp'` |
| Wrong patch target for multiprocessing.Queue | `test_active_scanner.py` | Use `'controller.scan.active_scanner.multiprocessing.Queue'`, not `'multiprocessing.Queue'` |
| Name mangling on `__webhook_manager` | `test_webhook.py` | Access via `._WebhookHandler__webhook_manager`, not `.webhook_manager` |
| Direct `_stop_flag` assignment fails | SSE stream tests | Always call `web_app.stop()`, never set `_stop_flag` directly |
| `webtest.TestApp.get()` blocks on SSE | SSE stream tests | Replace with `collect_sse_chunks(self.web_app)` from wsgi helper |
| Duplicate of `TestIScannerContract` | `test_active_scanner.py` | Do NOT re-test 3-tuple contract — already in `test_scanner_process.py` lines 182–197 |

---

## Metadata

**Analog search scope:** `src/python/tests/` (integration + unittests subdirectories)
**Files scanned:** 8 source + test files read directly
**Pattern extraction date:** 2026-04-28
