# Phase 96: Rate Limiting & Tooling - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 8 new/modified files
**Analogs found:** 7 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/web/rate_limit.py` | utility | request-response | `src/python/web/handler/controller.py` (lines 229-251) | exact (logic extraction) |
| `src/python/web/handler/controller.py` | handler | request-response | self (refactor) | exact |
| `src/python/web/handler/config.py` | handler | request-response | `src/python/web/handler/status.py` | exact |
| `src/python/web/handler/status.py` | handler | request-response | `src/python/web/handler/config.py` | exact |
| `src/python/tests/unittests/test_web/test_rate_limit.py` | test | request-response | `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` (lines 606-702) | exact |
| `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` | test | request-response | `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` | role-match |
| `src/python/tests/unittests/test_web/test_handler/test_status_handler.py` | test | request-response | `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` | role-match |
| `shield-claude-skill/configs/semgrep-rules/javascript.yaml` | config | transform | `shield-claude-skill/configs/semgrep-rules/go.yaml` (line 141) | role-match |

---

## Pattern Assignments

### `src/python/web/rate_limit.py` (utility, request-response)

**Analog:** `src/python/web/handler/controller.py` lines 1-16 (imports) and 229-283 (sliding-window + 429 response)

**Imports pattern** (`controller.py` lines 1-16):
```python
import json
import logging
import time
from threading import Lock
from typing import List

from bottle import HTTPResponse

logger = logging.getLogger(__name__)
```

**Core sliding-window pattern** (`controller.py` lines 229-251):
```python
def _check_bulk_rate_limit(self) -> bool:
    now = time.time()
    with self._bulk_rate_lock:
        # Remove timestamps outside the window
        self._bulk_request_times = [
            t for t in self._bulk_request_times
            if now - t < self._BULK_RATE_WINDOW
        ]
        # Check if limit exceeded
        if len(self._bulk_request_times) >= self._BULK_RATE_LIMIT:
            return False
        # Record this request
        self._bulk_request_times.append(now)
        return True
```

**429 response pattern** (`controller.py` lines 277-283):
```python
return HTTPResponse(
    body=json.dumps({"error": "Rate limit exceeded. Please try again later."}),
    status=429,
    content_type="application/json"
)
```

**Decorator wrapper requirement** (from `functools.wraps` — used throughout project):
```python
import functools
from typing import Callable

def rate_limit(max_requests: int, window_seconds: float) -> Callable:
    def decorator(func: Callable) -> Callable:
        request_times: List[float] = []
        lock = Lock()

        @functools.wraps(func)   # REQUIRED: Bottle inspects wrapped signature for path variables
        def wrapper(*args, **kwargs):
            ...
            return func(*args, **kwargs)

        return wrapper
    return decorator
```

**Critical note:** `functools.wraps(func)` is non-optional. The config/set route uses path variables (`/server/config/set/<section>/<key>/<value:re:.+>`). Without `wraps`, Bottle cannot resolve path variables and the handler crashes with a TypeError. Verified: `controller.py` adds routes with path variables at lines 67-72 using the same `add_post_handler` API.

---

### `src/python/web/handler/controller.py` (handler, request-response — refactor)

**Analog:** self — this is a refactor of the existing file

**Lines to remove:** Class constants at lines 207-209 (`_BULK_RATE_LIMIT`, `_BULK_RATE_WINDOW`), instance state in `__init__` at line 62-63 (`_bulk_request_times`, `_bulk_rate_lock`), and the entire `_check_bulk_rate_limit()` method (lines 229-251), plus the rate limit check block inside `__handle_bulk_command` (lines 276-283).

**Import to add** (following the import pattern at `controller.py` lines 1-16 — place after project imports):
```python
from web.rate_limit import rate_limit
```

**Route registration change** (`controller.py` lines 65-72, change line 72):
```python
# Before:
web_app.add_post_handler("/server/command/bulk", self.__handle_bulk_command)

# After:
web_app.add_post_handler(
    "/server/command/bulk",
    rate_limit(max_requests=10, window_seconds=60.0)(self.__handle_bulk_command)
)
```

**Preserved behavior:** 10 req/60s threshold is unchanged per D-03.

---

### `src/python/web/handler/config.py` (handler, request-response — modified)

**Analog:** `src/python/web/handler/config.py` lines 1-25 (self, current state)

**Current `add_routes` pattern** (`config.py` lines 19-25):
```python
@overrides(IHandler)
def add_routes(self, web_app: WebApp):
    web_app.add_handler("/server/config/get", self.__handle_get_config)
    # The regex allows slashes in values
    web_app.add_handler("/server/config/set/<section>/<key>/<value:re:.+>", self.__handle_set_config)
    web_app.add_handler("/server/config/sonarr/test-connection", self.__handle_test_sonarr_connection)
    web_app.add_handler("/server/config/radarr/test-connection", self.__handle_test_radarr_connection)
```

**Import to add** (top of file, after `from ..web_app import IHandler, WebApp`):
```python
from web.rate_limit import rate_limit
```

**Modified `add_routes`** — wrap three handlers inline at registration (D-01 thresholds):
```python
@overrides(IHandler)
def add_routes(self, web_app: WebApp):
    web_app.add_handler("/server/config/get", self.__handle_get_config)
    web_app.add_handler(
        "/server/config/set/<section>/<key>/<value:re:.+>",
        rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_set_config)
    )
    web_app.add_handler(
        "/server/config/sonarr/test-connection",
        rate_limit(max_requests=5, window_seconds=60.0)(self.__handle_test_sonarr_connection)
    )
    web_app.add_handler(
        "/server/config/radarr/test-connection",
        rate_limit(max_requests=5, window_seconds=60.0)(self.__handle_test_radarr_connection)
    )
```

**Each `rate_limit(...)` call produces a separate closure** — config/set and each test-connection endpoint have independent rate limit counters.

---

### `src/python/web/handler/status.py` (handler, request-response — modified)

**Analog:** `src/python/web/handler/status.py` lines 1-17 (self, current state)

**Current `add_routes` pattern** (`status.py` lines 11-13):
```python
@overrides(IHandler)
def add_routes(self, web_app: WebApp):
    web_app.add_handler("/server/status", self.__handle_get_status)
```

**Import to add** (after `from ..web_app import IHandler, WebApp`):
```python
from web.rate_limit import rate_limit
```

**Modified `add_routes`** (D-01: 60 req/60s):
```python
@overrides(IHandler)
def add_routes(self, web_app: WebApp):
    web_app.add_handler(
        "/server/status",
        rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_get_status)
    )
```

---

### `src/python/tests/unittests/test_web/test_rate_limit.py` (test — new file)

**Analog:** `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` lines 1-7 (imports) and lines 606-702 (rate limit test class)

**Imports pattern** (`test_controller_handler.py` lines 1-7):
```python
import unittest
from unittest.mock import MagicMock, patch
import json

from web.handler.controller import ControllerHandler, WebResponseActionCallback
```

**Test class structure** (`test_controller_handler.py` lines 606-702) — copy this pattern directly, replacing class-constant references with decorator-level introspection or numeric literals:
```python
class TestControllerHandlerRateLimit(unittest.TestCase):
    def setUp(self):
        self.mock_controller = MagicMock(spec=Controller)
        self.handler = ControllerHandler(self.mock_controller)
        self._setup_command_callback(success=True)

    def _call_bulk_handler(self, body):
        with patch('bottle.request') as mock_req:
            mock_req.json = body
            return self.handler._ControllerHandler__handle_bulk_command()

    def test_rate_limit_allows_requests_under_limit(self):
        for i in range(ControllerHandler._BULK_RATE_LIMIT):   # <-- this constant will be removed
            ...

    def test_rate_limit_blocks_requests_over_limit(self):
        ...
        self.assertEqual(429, response.status_code)
        body = json.loads(response.body)
        self.assertIn("error", body)
        self.assertIn("Rate limit", body["error"])

    def test_rate_limit_resets_after_window(self):
        # Mutates _BULK_RATE_WINDOW on the class — after refactor, mutate the decorator closure instead
        ...

    def test_rate_limit_response_content_type_is_json(self):
        self.assertEqual("application/json", response.content_type)
```

**New test file structure** — adapt to test the `rate_limit` decorator module directly:
```python
import unittest
import json
from unittest.mock import MagicMock
from web.rate_limit import rate_limit
from bottle import HTTPResponse


class TestRateLimitDecorator(unittest.TestCase):
    def _make_handler(self):
        """Return a simple handler function for wrapping."""
        def handler(*args, **kwargs):
            return HTTPResponse(body="ok", status=200)
        return handler

    def test_allows_under_limit(self): ...
    def test_blocks_over_limit(self): ...
    def test_resets_after_window(self): ...
    def test_429_body_is_json(self): ...
    def test_429_content_type(self): ...
    def test_functools_wraps_preserves_name(self): ...
    def test_separate_closures_have_independent_state(self): ...
```

---

### `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` (test — modified)

**Analog:** `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` lines 606-702

**Existing test class structure** (`test_config_handler.py` lines 1-21):
```python
import json
import socket
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import requests

from common import Config, ConfigError
from web.handler.config import ConfigHandler


class TestConfigHandlerSet(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.handler = ConfigHandler(self.mock_config)
```

**Rate limit test class to add** — follow the controller rate limit test structure, calling the private handler method directly (bypassing the decorator since the handler is tested in isolation):
```python
class TestConfigHandlerRateLimit(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.handler = ConfigHandler(self.mock_config)
        # Configure mock_config for set_config calls
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner

    def _make_rate_limited_handler(self, max_requests, window_seconds):
        """Wrap the private method with rate_limit to test threshold behaviour."""
        from web.rate_limit import rate_limit
        return rate_limit(max_requests, window_seconds)(
            self.handler._ConfigHandler__handle_set_config
        )

    def test_set_config_rate_limited_at_60_per_60s(self): ...
    def test_test_connection_rate_limited_at_5_per_60s(self): ...
```

---

### `src/python/tests/unittests/test_web/test_handler/test_status_handler.py` (test — modified)

**Analog:** `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` lines 606-702

**Existing test structure** (`test_status_handler.py` lines 1-30 — full file):
```python
import unittest
from unittest.mock import MagicMock, patch

from web.handler.status import StatusHandler


class TestStatusHandler(unittest.TestCase):
    def setUp(self):
        self.mock_status = MagicMock()
        self.handler = StatusHandler(self.mock_status)

    @patch('web.handler.status.SerializeStatusJson')
    def test_get_status_returns_200(self, mock_serialize_cls):
        mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
        response = self.handler._StatusHandler__handle_get_status()
        self.assertEqual(200, response.status_code)
```

**Rate limit test class to add:**
```python
class TestStatusHandlerRateLimit(unittest.TestCase):
    def setUp(self):
        self.mock_status = MagicMock()
        self.handler = StatusHandler(self.mock_status)

    def _make_rate_limited_handler(self, max_requests, window_seconds):
        from web.rate_limit import rate_limit
        with patch('web.handler.status.SerializeStatusJson') as mock_s:
            mock_s.status.return_value = '{}'
            return rate_limit(max_requests, window_seconds)(
                self.handler._StatusHandler__handle_get_status
            )

    def test_status_rate_limited_at_60_per_60s(self): ...
```

---

### `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` (test — modified)

**Analog:** self (existing rate limit tests at lines 606-702 — update only)

**Lines to update** — tests reference `ControllerHandler._BULK_RATE_LIMIT` (line 615, 627, 657) and `ControllerHandler._BULK_RATE_WINDOW` (lines 652, 681), which will no longer exist after the D-05 refactor.

**Replacement pattern** — use numeric literals directly (10, 60.0) or capture the decorator's closure:
```python
# Before (will break after refactor):
for i in range(ControllerHandler._BULK_RATE_LIMIT):
    ...
ControllerHandler._BULK_RATE_WINDOW = 0.1

# After (use literals matching the rate_limit() call in add_routes()):
_BULK_RATE_LIMIT = 10   # module-level constant in test file matching add_routes() value
for i in range(_BULK_RATE_LIMIT):
    ...
# For window mutation tests, construct a fresh rate-limited handler with a short window:
from web.rate_limit import rate_limit
rate_limited = rate_limit(max_requests=10, window_seconds=0.1)(handler._ControllerHandler__handle_bulk_command)
```

---

### `shield-claude-skill/configs/semgrep-rules/javascript.yaml` (config — modified)

**Analog (metavariable-regex syntax):** `shield-claude-skill/configs/semgrep-rules/go.yaml` lines 141-143

**metavariable-regex syntax from go.yaml:**
```yaml
      - metavariable-regex:
          metavariable: $X
          regex: (?i)(password|passwd|secret|api_key|...)
```

**TOOL-01 change** — current rule at lines 267-280 (single `pattern:`), convert to `patterns:` block:

Current (lines 267-280):
```yaml
  - id: js-nosql-injection-where
    pattern: |
      $COLLECTION.$WHERE($INPUT)
    message: >
      ...
```

Fixed (replace `pattern:` with `patterns:` block, add `metavariable-regex` sibling):
```yaml
  - id: js-nosql-injection-where
    patterns:
      - pattern: |
          $COLLECTION.$WHERE($INPUT)
      - metavariable-regex:
          metavariable: $WHERE
          regex: '^\$where$'
    message: >
      ...
```

Note: Single-quoted YAML string for the regex value prevents YAML from interpreting `$where` as a variable reference (see Pitfall 4 in RESEARCH.md).

**TOOL-02 change** — current rule at lines 87-110 has one `pattern-not` entry. Add six more `pattern-not` siblings within the existing `patterns:` block (after line 99):

Current `patterns:` block (lines 88-99):
```yaml
    patterns:
      - pattern-either:
          - pattern: |
              eval($INPUT)
          - pattern: |
              new Function($INPUT)
          - pattern: |
              setTimeout($INPUT, ...)
          - pattern: |
              setInterval($INPUT, ...)
      - pattern-not: |
          eval("...")
```

Additions — insert after line 99 (`eval("...")`):
```yaml
      - pattern-not: |
          setTimeout(($ARGS) => $BODY, ...)
      - pattern-not: |
          setTimeout(() => $BODY, ...)
      - pattern-not: |
          setTimeout(function $NAME($PARAMS) { $BODY }, ...)
      - pattern-not: |
          setInterval(($ARGS) => $BODY, ...)
      - pattern-not: |
          setInterval(() => $BODY, ...)
      - pattern-not: |
          setInterval(function $NAME($PARAMS) { $BODY }, ...)
```

Both zero-arg `() => $BODY` and parameterized `($ARGS) => $BODY` forms are required (see Assumption A3 and Pitfall 5 in RESEARCH.md).

---

## Shared Patterns

### Thread-Safe State (applies to `rate_limit.py`)

**Source:** `src/python/web/handler/controller.py` lines 62-63 and 239-250
```python
# Instance-level state initialization (init pattern):
self._bulk_request_times: List[float] = []
self._bulk_rate_lock = Lock()

# Thread-safe mutation inside lock (use in-place slice assignment, not rebinding):
with self._bulk_rate_lock:
    self._bulk_request_times = [
        t for t in self._bulk_request_times
        if now - t < self._BULK_RATE_WINDOW
    ]
```

For the decorator, the list and lock live in the closure (not on `self`), but the `with lock:` pattern and `request_times[:] = [...]` in-place mutation are identical.

### JSON HTTPResponse Error Format (applies to `rate_limit.py` and any new 4xx responses)

**Source:** `src/python/web/handler/controller.py` lines 279-283
```python
return HTTPResponse(
    body=json.dumps({"error": "Rate limit exceeded. Please try again later."}),
    status=429,
    content_type="application/json"
)
```

**Apply to:** The `rate_limit.py` wrapper's over-limit branch.

### Handler Test Class Structure (applies to all new/modified test files)

**Source:** `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` lines 1-21
```python
import json
import unittest
from unittest.mock import MagicMock, patch

from web.handler.config import ConfigHandler


class TestConfigHandlerSet(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.handler = ConfigHandler(self.mock_config)
```

Pattern: one `unittest.TestCase` subclass per behaviour group, `setUp` constructs handler with `MagicMock` dependencies, private methods accessed via Python name-mangled attribute (`_ClassName__method_name`).

### `@overrides(IHandler)` decorator (applies to any `add_routes` modification)

**Source:** `src/python/web/handler/config.py` line 19, `src/python/web/handler/status.py` line 11
```python
from common import overrides
...
@overrides(IHandler)
def add_routes(self, web_app: WebApp):
```

All `add_routes` methods carry `@overrides(IHandler)`. Do not remove this when modifying the method.

---

## No Analog Found

All files have close analogs in the codebase. No entries in this section.

---

## Metadata

**Analog search scope:** `src/python/web/`, `src/python/tests/unittests/test_web/`, `shield-claude-skill/configs/semgrep-rules/`
**Files scanned:** 8 source files read directly (controller.py, config.py, status.py, web_app.py, javascript.yaml, go.yaml, test_controller_handler.py, test_config_handler.py, test_status_handler.py)
**Pattern extraction date:** 2026-04-28
