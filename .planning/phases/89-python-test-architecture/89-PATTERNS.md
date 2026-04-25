# Phase 89: Python Test Architecture - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 9 (new + modified)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/helpers.py` (NEW) | utility | transform | `tests/utils.py` | exact |
| `tests/conftest.py` (MODIFY) | config | transform | `tests/conftest.py` (self) | exact |
| `tests/unittests/test_controller/base.py` (NEW) | test-base-class | CRUD | `integration/test_web/test_web_app.py` | role-match |
| `tests/unittests/test_controller/test_controller_unit.py` (MODIFY) | test | CRUD | `tests/unittests/test_controller/test_controller_unit.py` (self) | exact |
| `tests/unittests/test_controller/test_auto_delete.py` (MODIFY) | test | CRUD | `tests/unittests/test_controller/test_auto_delete.py` (self) | exact |
| `tests/integration/test_lftp/test_lftp_protocol.py` (NEW - moved) | test | request-response | `tests/integration/test_lftp/test_lftp.py` | exact |
| `docs/coverage-gaps.md` (NEW) | documentation | N/A | N/A | N/A |
| `docs/name-mangling-tradeoff.md` (NEW) | documentation | N/A | N/A | N/A |
| `tests/unittests/test_common/test_config.py` (MODIFY) | test | transform | `tests/unittests/test_common/test_config.py` (self) | exact |

Note: All file paths below are relative to `src/python/`. The project runs tests inside Docker with `PYTHONPATH=/src`, so imports use bare module names (e.g., `from common import Config`).

## Pattern Assignments

### `tests/helpers.py` (utility, transform) -- NEW

**Analog:** `tests/utils.py`

**Imports pattern** (lines 1-1):
```python
import os
```

**Core pattern -- static helper class** (lines 4-25):
```python
class TestUtils:
    @staticmethod
    def chmod_from_to(from_path: str, to_path: str, mode: int):
        """
        Chmod from_path and all its parents up to and including to_path
        :param from_path:
        :param to_path:
        :param mode:
        :return:
        """
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

**Convention notes:**
- `tests/utils.py` uses a static class (`TestUtils`) with `@staticmethod` methods, no `__init__`.
- However, the RESEARCH.md recommends module-level functions for `helpers.py` (see RESEARCH Architecture Patterns, PYARCH-01). The planner should use module-level functions (`def create_test_logger(...)`) rather than a class, since these are factory functions not utility methods.
- The existing import pattern from `tests/utils.py` is: `from tests.utils import TestUtils` (see `integration/test_lftp/test_lftp.py` line 11, `integration/test_controller/test_controller.py` line 16).
- New helpers should be imported as: `from tests.helpers import create_test_logger, create_mock_context`.

**Source material for conversion** -- current conftest.py fixtures to convert (lines 20-109):

Fixture 1 -- `test_logger` (conftest.py lines 20-46):
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
    logger.propagate = False
    yield logger
    logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
```

Fixture 2 -- `mock_context` (conftest.py lines 49-92):
```python
@pytest.fixture
def mock_context(test_logger):
    context = MagicMock()
    context.logger = test_logger
    # lftp config
    context.config.lftp.local_path = "/local/path"
    context.config.lftp.remote_address = "remote.server.com"
    context.config.lftp.remote_username = "user"
    context.config.lftp.remote_password = "password"
    context.config.lftp.use_ssh_key = False
    context.config.lftp.remote_port = 22
    context.config.lftp.remote_path = "/remote/path"
    context.config.lftp.remote_path_to_scan_script = "/usr/bin/scanfs"
    context.config.lftp.use_temp_file = False
    context.config.lftp.num_max_parallel_downloads = 2
    context.config.lftp.num_max_parallel_files_per_download = 3
    context.config.lftp.num_max_connections_per_root_file = 4
    context.config.lftp.num_max_connections_per_dir_file = 2
    context.config.lftp.num_max_total_connections = 8
    # controller config
    context.config.controller.interval_ms_downloading_scan = 500
    context.config.controller.interval_ms_local_scan = 30000
    context.config.controller.interval_ms_remote_scan = 30000
    context.config.controller.use_local_path_as_extract_path = True
    context.config.controller.extract_path = "/extract/path"
    # general config
    context.config.general.verbose = False
    # args
    context.args.local_path_to_scanfs = "/local/bin/scanfs"
    return context
```

Fixture 3 -- `mock_context_with_real_config` (conftest.py lines 95-109):
```python
@pytest.fixture
def mock_context_with_real_config(test_logger):
    context = MagicMock()
    context.config = Config()
    context.logger = test_logger
    return context
```

**Key conversion detail:** The `test_logger` fixture uses `request.node.name` for the logger name (pytest-specific). The helper function version should accept a `name: str` parameter instead. The yield + cleanup pattern becomes a tuple return `(logger, handler)` where callers remove the handler in `tearDown`.

---

### `tests/conftest.py` (config, transform) -- MODIFY

**Current state:** 110 lines, 3 pytest fixtures, zero consumers.

**Action:** Either (a) gut the file to only import and re-export from `helpers.py` as pytest fixtures (preserving future pytest-style test support), or (b) replace fixture bodies with calls to helpers. Prefer (a) for forward compatibility.

**Pattern to follow for re-export** (modeled on the existing fixture structure):
```python
# After modification -- thin wrappers around helpers
import pytest
from tests.helpers import create_test_logger, create_mock_context, create_mock_context_with_real_config


@pytest.fixture
def test_logger(request):
    logger, handler = create_test_logger(request.node.name)
    yield logger
    logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


@pytest.fixture
def mock_context(test_logger):
    return create_mock_context(logger=test_logger)


@pytest.fixture
def mock_context_with_real_config(test_logger):
    return create_mock_context_with_real_config(logger=test_logger)
```

---

### `tests/unittests/test_controller/base.py` (test-base-class, CRUD) -- NEW

**Analog:** `tests/integration/test_web/test_web_app.py` (BaseTestWebApp)

This is the closest analog for a shared base test class that lives in its own module and is imported by multiple test files.

**Import pattern from analog** (test_web_app.py lines 1-11):
```python
import unittest
from unittest.mock import MagicMock
import logging
import sys

from webtest import TestApp

from common import overrides, Status, Config
from controller import AutoQueuePersist
from web import WebAppBuilder
```

**Base class definition pattern** (test_web_app.py lines 13-58):
```python
class BaseTestWebApp(unittest.TestCase):
    """
    Base class for testing web app
    Sets up the web app with mocks
    """
    @overrides(unittest.TestCase)
    def setUp(self):
        self.context = MagicMock()
        self.controller = MagicMock()
        # ... mock setup ...

    @overrides(unittest.TestCase)
    def tearDown(self):
        # ... cleanup ...
```

**Cross-file import pattern** (how handler tests import the base class):
```python
# From tests/integration/test_web/test_handler/test_auto_queue.py line 5:
from tests.integration.test_web.test_web_app import BaseTestWebApp
```

**Source content to extract** -- `BaseControllerTestCase` from `test_controller_unit.py` (lines 1-89):
```python
import unittest
from unittest.mock import MagicMock, patch

from controller import Controller
from controller.controller import ControllerError
from controller.controller_persist import ControllerPersist
from model import ModelFile, IModelListener, ModelDiff, Model
from lftp import LftpError, LftpJobStatus, LftpJobStatusParserError


class BaseControllerTestCase(unittest.TestCase):
    """Base class that patches all 6 Controller internal dependencies."""

    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.persist = ControllerPersist(max_tracked_files=100)

        # Start patches for all 6 internal dependencies
        self.patcher_mb = patch('controller.controller.ModelBuilder')
        self.patcher_lftp = patch('controller.controller.LftpManager')
        self.patcher_sm = patch('controller.controller.ScanManager')
        self.patcher_fom = patch('controller.controller.FileOperationManager')
        self.patcher_mpl = patch('controller.controller.MultiprocessingLogger')
        self.patcher_mm = patch('controller.controller.MemoryMonitor')

        self.mock_model_builder_cls = self.patcher_mb.start()
        self.mock_lftp_manager_cls = self.patcher_lftp.start()
        self.mock_scan_manager_cls = self.patcher_sm.start()
        self.mock_file_op_manager_cls = self.patcher_fom.start()
        self.mock_mp_logger_cls = self.patcher_mpl.start()
        self.mock_memory_monitor_cls = self.patcher_mm.start()

        # Get mock instances (return values of mock classes)
        self.mock_model_builder = self.mock_model_builder_cls.return_value
        self.mock_lftp_manager = self.mock_lftp_manager_cls.return_value
        self.mock_scan_manager = self.mock_scan_manager_cls.return_value
        self.mock_file_op_manager = self.mock_file_op_manager_cls.return_value
        self.mock_mp_logger = self.mock_mp_logger_cls.return_value
        self.mock_memory_monitor = self.mock_memory_monitor_cls.return_value
        # Create mock WebhookManager (not patched, passed as parameter)
        self.mock_webhook_manager = MagicMock()
        # Default: process returns empty list (no imports)
        self.mock_webhook_manager.process.return_value = []
        # Default: auto-delete disabled (prevents Timer with MagicMock delay)
        self.mock_context.config.autodelete.enabled = False

        self.controller = Controller(context=self.mock_context, persist=self.persist, webhook_manager=self.mock_webhook_manager)

    def tearDown(self):
        self.patcher_mb.stop()
        self.patcher_lftp.stop()
        self.patcher_sm.stop()
        self.patcher_fom.stop()
        self.patcher_mpl.stop()
        self.patcher_mm.stop()

    def _make_controller_started(self):
        """Helper: set __started flag and configure no-op model update mocks."""
        self.controller._Controller__started = True
        self.mock_scan_manager.pop_latest_results.return_value = (None, None, None)
        self.mock_lftp_manager.status.return_value = None
        self.mock_file_op_manager.pop_extract_statuses.return_value = None
        self.mock_file_op_manager.pop_completed_extractions.return_value = []
        self.mock_model_builder.has_changes.return_value = False

    def _add_file_to_model(self, name, is_dir=False, state=ModelFile.State.DEFAULT,
                           remote_size=None, local_size=None):
        """Helper: create a ModelFile, set properties, add to controller's model."""
        f = ModelFile(name, is_dir)
        if state != ModelFile.State.DEFAULT:
            f.state = state
        if remote_size is not None:
            f.remote_size = remote_size
        if local_size is not None:
            f.local_size = local_size
        self.controller._Controller__model.add_file(f)
        return f

    def _queue_and_process_command(self, action, filename, callbacks=None):
        """Helper: create command, optionally add callbacks, queue, and process."""
        cmd = Controller.Command(action, filename)
        if callbacks:
            for cb in callbacks:
                cmd.add_callback(cb)
        self.controller.queue_command(cmd)
        self.controller.process()
        return cmd
```

**Import pattern for base.py consumers:**
```python
# Modeled on: from tests.integration.test_web.test_web_app import BaseTestWebApp
from tests.unittests.test_controller.base import BaseControllerTestCase
```

---

### `tests/unittests/test_controller/test_controller_unit.py` (test, CRUD) -- MODIFY

**Current state:** 1100+ lines, 21 test classes inheriting from `BaseControllerTestCase` defined at top of same file.

**Action:** Remove `BaseControllerTestCase` class definition (lines 11-89), add import from `base.py`. All 21 test classes remain unchanged.

**Before** (lines 1-11):
```python
import unittest
from unittest.mock import MagicMock, patch

from controller import Controller
from controller.controller import ControllerError
from controller.controller_persist import ControllerPersist
from model import ModelFile, IModelListener, ModelDiff, Model
from lftp import LftpError, LftpJobStatus, LftpJobStatusParserError


class BaseControllerTestCase(unittest.TestCase):
```

**After** (replace lines 1-10, remove lines 11-89):
```python
import unittest
from unittest.mock import MagicMock, patch

from controller import Controller
from controller.controller import ControllerError
from controller.controller_persist import ControllerPersist
from model import ModelFile, IModelListener, ModelDiff, Model
from lftp import LftpError, LftpJobStatus, LftpJobStatusParserError

from tests.unittests.test_controller.base import BaseControllerTestCase
```

---

### `tests/unittests/test_controller/test_auto_delete.py` (test, CRUD) -- MODIFY

**Current state:** 490+ lines, `BaseAutoDeleteTestCase` defined at lines 10-60 with near-identical setUp to `BaseControllerTestCase`.

**Action:** Replace `BaseAutoDeleteTestCase(unittest.TestCase)` with `BaseAutoDeleteTestCase(BaseControllerTestCase)`, keeping only the auto-delete-specific setUp overrides and timer tearDown.

**Before** (lines 1-61):
```python
import unittest
from unittest.mock import MagicMock, patch
import threading

from controller import Controller
from controller.controller_persist import ControllerPersist
from model import ModelFile, ModelError


class BaseAutoDeleteTestCase(unittest.TestCase):
    """Base class with patched Controller dependencies for auto-delete tests."""

    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.mock_context.config.autodelete.enabled = True
        self.mock_context.config.autodelete.dry_run = False
        self.mock_context.config.autodelete.delay_seconds = 10
        self.persist = ControllerPersist(max_tracked_files=100)

        # Start patches for all 6 internal dependencies
        self.patcher_mb = patch('controller.controller.ModelBuilder')
        # ... (6 identical patches) ...

        self.controller = Controller(context=self.mock_context, persist=self.persist, webhook_manager=self.mock_webhook_manager)

    def tearDown(self):
        # Cancel any pending timers to prevent thread leaks
        for timer in list(self.controller._Controller__pending_auto_deletes.values()):
            timer.cancel()
        self.controller._Controller__pending_auto_deletes.clear()

        self.patcher_mb.stop()
        # ... (6 stops) ...
```

**After** (RESEARCH-recommended pattern):
```python
import threading

from controller import Controller
from controller.controller_persist import ControllerPersist
from model import ModelFile, ModelError

from tests.unittests.test_controller.base import BaseControllerTestCase


class BaseAutoDeleteTestCase(BaseControllerTestCase):
    """Extends BaseControllerTestCase with auto-delete defaults and timer cleanup."""

    def setUp(self):
        super().setUp()
        self.mock_context.config.autodelete.enabled = True
        self.mock_context.config.autodelete.dry_run = False
        self.mock_context.config.autodelete.delay_seconds = 10
        # Re-create controller with auto-delete enabled
        self.controller = Controller(
            context=self.mock_context,
            persist=self.persist,
            webhook_manager=self.mock_webhook_manager,
        )

    def tearDown(self):
        # Cancel pending timers before stopping patches
        for timer in list(self.controller._Controller__pending_auto_deletes.values()):
            timer.cancel()
        self.controller._Controller__pending_auto_deletes.clear()
        super().tearDown()
```

---

### `tests/integration/test_lftp/test_lftp_protocol.py` (test, request-response) -- NEW (moved)

**Analog:** `tests/integration/test_lftp/test_lftp.py` (existing integration test in same directory)

**Source file:** `tests/unittests/test_lftp/test_lftp.py` (794 lines, misclassified)

**Existing integration test_lftp.py import pattern** (lines 1-12):
```python
import logging
import os
import shutil
import sys
import tempfile
import unittest
from filecmp import dircmp

import timeout_decorator

from tests.utils import TestUtils
from lftp import Lftp
```

**Misclassified file import pattern** (lines 1-11):
```python
import logging
import os
import shutil
import sys
import tempfile
import time
import unittest

import timeout_decorator

from lftp import Lftp, LftpJobStatus, LftpError
```

**Key differences to handle:**
- Class must be renamed from `TestLftp` to `TestLftpProtocol` to avoid conflict with existing `TestLftp` in same directory.
- The file does NOT use `from tests.utils import TestUtils` (sets permissions inline instead).
- The `__init__.py` in `tests/unittests/test_lftp/` must remain (other files may exist). Verify with `ls` before deleting the directory.

**Existing integration setUp pattern** (test_lftp.py lines 15-48):
```python
class TestLftp(unittest.TestCase):
    temp_dir = None

    @classmethod
    def setUpClass(cls):
        TestLftp.temp_dir = tempfile.mkdtemp(prefix="test_lftp_")
        TestUtils.chmod_from_to(TestLftp.temp_dir, tempfile.gettempdir(), 0o775)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TestLftp.temp_dir)

    def setUp(self):
        os.mkdir(os.path.join(TestLftp.temp_dir, "remote"))
        os.mkdir(os.path.join(TestLftp.temp_dir, "local"))
        self.lftp = Lftp(address="localhost", port=22, user="seedsyncarrtest", password=None)
        # ...
```

**Misclassified file setUp pattern** (test_lftp.py lines 20-49):
```python
class TestLftp(unittest.TestCase):
    temp_dir = None

    @classmethod
    def setUpClass(cls):
        TestLftp.temp_dir = tempfile.mkdtemp(prefix="test_lftp_")
        os.chmod(TestLftp.temp_dir, 0o750)
        # Creates elaborate test directory structure with files
```

**Action:** Copy `tests/unittests/test_lftp/test_lftp.py` to `tests/integration/test_lftp/test_lftp_protocol.py`, rename class `TestLftp` -> `TestLftpProtocol`, update all `TestLftp.temp_dir` references to `TestLftpProtocol.temp_dir`, then delete the original file.

---

### `tests/unittests/test_common/test_config.py` (test, transform) -- MODIFY

**Analog:** self (internal refactoring)

**Current INI duplication pattern** -- 7 near-identical INI blocks spanning lines 680-1060+. Each block has the same section skeleton with varying values in 5 secret fields and optional presence of `[Encryption]`, `[Sonarr]`, `[Radarr]`, `[AutoDelete]` sections.

**Existing private helper pattern** (lines 623-670):
```python
def _build_plaintext_config(self) -> "Config":
    """Return a fully-populated Config with encryption disabled and plaintext secrets."""
    c = Config()
    c.general.debug = False
    c.general.verbose = False
    c.general.webhook_secret = "my_webhook"
    c.general.api_token = "my_token"
    # ... (47 field assignments) ...
    return c
```

**Action:** Add a module-level or class-level helper function `_build_config_ini(...)` with keyword arguments for the varying fields. Pattern from RESEARCH Code Example 1:

```python
def _build_config_ini(
    *,
    webhook_secret="",
    api_token="",
    remote_password="pass",
    sonarr_api_key="",
    radarr_api_key="",
    encryption_enabled=None,  # None = omit section, True/False = include
    debug="False",
    verbose="False",
) -> str:
    """Build a full config INI string with parameterized secret fields."""
    # ... see RESEARCH Code Examples, Example 1 ...
```

**Key detail:** The `_build_plaintext_config` method returns a `Config` object (programmatic). The new `_build_config_ini` returns an INI string. These serve different purposes -- `_build_plaintext_config` should remain as-is; `_build_config_ini` replaces only the inline INI string literals in `test_encryption_disabled_by_default`, `test_from_file_enabled_decrypts`, `test_from_str_enabled_with_plaintext_falls_back`, `test_from_str_invalid_encryption_enabled_value`, and similar.

---

## Shared Patterns

### Logger Setup Pattern
**Source:** `tests/conftest.py` lines 35-42 (also duplicated in `integration/test_web/test_web_app.py` lines 24-29, `integration/test_lftp/test_lftp.py` lines 39-44)
**Apply to:** `tests/helpers.py` (centralized), then consumed by any test that needs a logger

```python
logger = logging.getLogger(name)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False
```

### unittest.TestCase Base Class Pattern
**Source:** `tests/integration/test_web/test_web_app.py` lines 13-58
**Apply to:** `tests/unittests/test_controller/base.py`, all base test class definitions

Key conventions:
- Use `@overrides(unittest.TestCase)` decorator on setUp/tearDown (optional -- `test_web_app.py` uses it, `test_controller_unit.py` does not)
- Document what the base class provides in the docstring
- Put all `patch()` calls in setUp, all `.stop()` calls in tearDown
- Provide helper methods prefixed with `_` for common test operations

### Cross-File Test Import Pattern
**Source:** Multiple files importing from `tests.integration.test_web.test_web_app` and `tests.utils`
**Apply to:** All files importing from `tests/unittests/test_controller/base.py` and `tests/helpers.py`

```python
# Existing pattern (8 handler test files use this):
from tests.integration.test_web.test_web_app import BaseTestWebApp

# Existing pattern (3 test files use this):
from tests.utils import TestUtils

# New imports should follow same convention:
from tests.unittests.test_controller.base import BaseControllerTestCase
from tests.helpers import create_test_logger, create_mock_context
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/coverage-gaps.md` | documentation | N/A | Pure documentation; no code analog needed. Use RESEARCH.md Example 2 for structure. |
| `docs/name-mangling-tradeoff.md` | documentation | N/A | Pure documentation; no code analog needed. Content is descriptive prose about the 155 name-mangling references. |

Note: The documentation files (PYARCH-04, PYARCH-05) require no code patterns -- they are markdown describing existing codebase characteristics. The planner should use the RESEARCH.md tables and descriptions directly.

## Metadata

**Analog search scope:** `src/python/tests/` (all test directories: conftest.py, utils.py, integration/, unittests/)
**Files scanned:** 9 source files read, ~15 grep searches
**Pattern extraction date:** 2026-04-24
