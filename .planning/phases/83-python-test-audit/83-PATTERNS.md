# Phase 83: Python Test Audit - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 0 new files / 0 modified test files (audit found zero stale tests)
**Analogs found:** N/A — no removals required; patterns documented for verification pass and SUMMARY.md authoring

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| *(none — zero stale tests found)* | — | — | — | — |

> The staleness audit (RESEARCH.md) verified all 84 test files against their production import targets. Every production module exists on disk. No test methods or files meet the D-01 removal criteria. The planner's implementation action is: run `pytest --cov`, record the 85.05% baseline, and mark PY-01/PY-02/PY-03 complete.

---

## Pattern Assignments

No test files are being created or modified. Patterns below are extracted for reference by the planner when authoring the removal inventory table (D-05) and the gate command.

---

## Shared Patterns

### Test Infrastructure — pytest config
**Source:** `src/python/pyproject.toml` lines 73–98
**Apply to:** All actions that invoke the test suite

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
timeout = 60
cache_dir = "/tmp/.pytest_cache"

[tool.coverage.run]
source = ["."]
omit = ["tests/*", "docs/*"]
branch = true

[tool.coverage.report]
fail_under = 84
show_missing = true
skip_empty = true
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.",
    "pass",
]
```

Gate command (from `src/python/`):
```
poetry run pytest tests/ --cov
```

Quick smoke command (unittests only):
```
poetry run pytest tests/unittests/ -q --tb=no
```

---

### Shared Fixtures
**Source:** `src/python/tests/conftest.py` lines 1–107
**Apply to:** Any new pytest-style tests added in future phases

```python
import pytest
from unittest.mock import MagicMock
from common import Config

@pytest.fixture
def test_logger(request):
    """Configured logger yielded per test; removes handler on teardown."""
    logger = logging.getLogger(request.node.name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield logger
    logger.removeHandler(handler)

@pytest.fixture
def mock_context(test_logger):
    """MagicMock context with pre-populated lftp/controller/general config."""
    context = MagicMock()
    context.logger = test_logger
    # lftp, controller, general attributes pre-set — see conftest.py lines 59–88
    return context

@pytest.fixture
def mock_context_with_real_config(test_logger):
    """MagicMock context with a REAL Config() object for validation tests."""
    context = MagicMock()
    context.config = Config()
    context.logger = test_logger
    return context
```

---

### Shared Test Utility
**Source:** `src/python/tests/utils.py` lines 1–25
**Apply to:** Integration tests that change filesystem permissions

```python
class TestUtils:
    @staticmethod
    def chmod_from_to(from_path: str, to_path: str, mode: int):
        """chmod from_path and all parents up to to_path."""
        path = from_path
        try:
            os.chmod(path, mode)
        except PermissionError:
            pass
        while path != "/" and path != to_path:
            path = os.path.dirname(path)
            try:
                os.chmod(path, mode)
            except PermissionError:
                pass
```

---

### unittest.TestCase base pattern (unit tests)
**Source:** `src/python/tests/unittests/test_controller/test_auto_delete.py` lines 1–60
**Apply to:** All files under `tests/unittests/`

```python
import unittest
from unittest.mock import MagicMock, patch

from controller import Controller
from controller.controller_persist import ControllerPersist
from model import ModelFile, ModelError


class BaseAutoDeleteTestCase(unittest.TestCase):
    """Base class with patched Controller dependencies."""

    def setUp(self):
        self.mock_context = MagicMock()
        # patch production dependencies at their import location in the module under test
        self.patcher_dep = patch('controller.controller.DepClass')
        self.mock_dep_cls = self.patcher_dep.start()
        self.mock_dep = self.mock_dep_cls.return_value

    def tearDown(self):
        self.patcher_dep.stop()


class TestSpecificBehavior(BaseAutoDeleteTestCase):
    def test_something(self):
        result = self.controller._Controller__private_method("arg")
        self.assertEqual(expected, result)
```

Key conventions:
- Production code patched at its import location in the module under test (e.g., `'controller.controller.DepClass'`, not `'dep_module.DepClass'`)
- Private methods tested via name-mangling (`_ClassName__method`)
- Base `setUp` classes share patch/mock setup; concrete test classes inherit

---

### unittest.TestCase base pattern (handler unit tests)
**Source:** `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` lines 1–80
**Apply to:** All files under `tests/unittests/test_web/test_handler/`

```python
import json
import unittest
from unittest.mock import MagicMock, patch

from common import Config, ConfigError
from web.handler.config import ConfigHandler


class TestConfigHandlerGet(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.handler = ConfigHandler(self.mock_config)

    @patch('web.handler.config.SerializeConfig')
    def test_get_returns_200(self, mock_serialize_cls):
        mock_serialize_cls.config.return_value = '{"test":"data"}'
        response = self.handler._ConfigHandler__handle_get_config()
        self.assertEqual(200, response.status_code)
```

Key conventions:
- Handler instantiated directly (not via WSGI TestApp)
- Private route methods invoked by name-mangling
- One assertion per test method

---

### WebTest WSGI integration pattern
**Source:** `src/python/tests/integration/test_web/test_web_app.py` lines 1–59
**Apply to:** All files under `tests/integration/test_web/`

```python
import unittest
from webtest import TestApp
from common import overrides, Status, Config
from controller import AutoQueuePersist
from web import WebAppBuilder


class BaseTestWebApp(unittest.TestCase):
    @overrides(unittest.TestCase)
    def setUp(self):
        self.context = MagicMock()
        self.controller = MagicMock()
        # Real status + real config (not mocked)
        self.context.status = Status()
        self.context.config = Config()
        self.auto_queue_persist = AutoQueuePersist()
        # Build the real WSGI app
        self.web_app_builder = WebAppBuilder(
            self.context, self.controller, self.auto_queue_persist, MagicMock()
        )
        self.web_app = self.web_app_builder.build()
        self.test_app = TestApp(self.web_app)
```

Integration test subclass pattern (`src/python/tests/integration/test_web/test_handler/test_config.py` lines 1–70):
```python
from tests.integration.test_web.test_web_app import BaseTestWebApp

class TestConfigHandler(BaseTestWebApp):
    def test_get(self):
        resp = self.test_app.get("/server/config/get")
        self.assertEqual(200, resp.status_int)

    def test_set_bad_value(self):
        resp = self.test_app.get("/server/config/set/general/debug/cat", expect_errors=True)
        self.assertEqual(400, resp.status_int)
```

Key conventions:
- `expect_errors=True` for 4xx responses
- `resp.status_int` (integer) not `resp.status_code`
- `str(resp.html)` to extract body text
- All integration web tests inherit `BaseTestWebApp`

---

### SSE serialize shared utility
**Source:** `src/python/tests/unittests/test_web/test_serialize/test_serialize.py` lines 1–15
**Apply to:** `test_serialize_log_record.py`, `test_serialize_model.py`, `test_serialize_status.py`

```python
from web.serialize import Serialize

class DummySerialize(Serialize):
    def dummy(self):
        return self._sse_pack(event="event", data="data")

def parse_stream(serialized_str: str):
    parsed = dict()
    for line in serialized_str.split("\n"):
        if line:
            key, value = line.split(":", maxsplit=1)
            parsed[key.strip()] = value.strip()
    return parsed
```

---

### Environment-conditioned skip patterns
**Apply to:** Any new tests that require external binaries or OS-specific behavior

```python
import unittest
import shutil
import sys

# Binary-conditional:
@unittest.skipIf(shutil.which("rar") is None, "rar not installed")
def test_extract_archive(self): ...

# Platform-conditional:
@unittest.skipIf(sys.platform == "win32", "not applicable on Windows")
def test_unix_only(self): ...

# Tool-limitation skip (permanent):
@unittest.skip("webtest doesn't support SSE streaming")
def test_sse_stream(self): ...
```

---

## No Analog Found

Not applicable. This audit phase creates no new files.

---

## Removal Inventory (D-05 table — result of audit)

Per RESEARCH.md findings: **zero tests removed.**

| Test File Path | Test Count Removed | Reason |
|----------------|-------------------|--------|
| *(none)* | 0 | All 84 test files verified LIVE against production modules |

---

## Coverage Baseline

| Metric | Value |
|--------|-------|
| Total coverage | 85.05% |
| fail_under threshold | 84% |
| Safety margin | 1.05 pp |
| Tests collected | 1,271 |
| Tests passing | 1,136 |
| Tests skipped | 71 |
| Tests failing (env) | 30 |
| Test errors (env) | 38 |

Baseline verified: `poetry run pytest tests/ --cov` — 2026-04-24

---

## Metadata

**Analog search scope:** `src/python/tests/` (conftest, utils, 5 representative test files)
**Files scanned:** 8 (pyproject.toml + conftest.py + utils.py + 5 test files)
**Pattern extraction date:** 2026-04-24
