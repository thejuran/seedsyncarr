# Phase 89: Python Test Architecture - Research

**Researched:** 2026-04-25
**Domain:** Python test infrastructure reorganization (pytest, unittest.TestCase, test classification)
**Confidence:** HIGH

## Summary

Phase 89 is a pure test-infrastructure reorganization phase. No production code changes are required. The codebase has 112 `unittest.TestCase` test classes across ~80 test files, all running inside a Docker container via `make run-tests-python`. The tests use pytest as the test runner (pytest 9.x) but all test classes inherit from `unittest.TestCase` and use `setUp/tearDown` patterns rather than pytest fixture injection.

The six requirements decompose into: (1) making conftest fixtures actually reachable or converting them to importable helpers, (2) consolidating two near-identical base test classes, (3) moving a misclassified integration test, (4) documenting coverage gaps, (5) documenting an accepted trade-off regarding name-mangling, and (6) extracting duplicated INI string literals. All changes are low-risk refactors with clear success criteria measurable by `make run-tests-python`.

**Primary recommendation:** Keep all tests as `unittest.TestCase` (do not convert to pytest-style); convert conftest fixtures to importable helper functions or a helper module, consolidate base classes by inheritance, and move the misclassified test file.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Test fixture management | Test infrastructure | -- | conftest.py and base classes are test-only |
| Test classification (unit vs integration) | Test directory structure | Docker compose | Directory determines what runs where; Docker provides SSH for integration tests |
| Coverage gap documentation | Documentation | -- | Markdown file, no code changes |
| INI string deduplication | Test infrastructure | -- | Shared constants within test module |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=9.0.3 | Test runner | Already in use; runs unittest.TestCase natively [VERIFIED: pyproject.toml] |
| pytest-timeout | >=2.3.1 | Test timeout enforcement | Already in use [VERIFIED: pyproject.toml] |
| pytest-cov | >=7.0.0 | Coverage reporting | Already in use [VERIFIED: pyproject.toml] |
| unittest | stdlib | Test framework | All 112 test classes use unittest.TestCase [VERIFIED: codebase grep] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| parameterized | >=0.9.0 | Parameterized test cases | Already in dev deps, used for data-driven tests [VERIFIED: pyproject.toml] |
| testfixtures | >=11.0.0 | Test assertion helpers | Already in dev deps [VERIFIED: pyproject.toml] |
| webtest | >=3.0.7 | WSGI testing | Already in dev deps for web handler tests [VERIFIED: pyproject.toml] |

**No new packages required.** This phase uses only existing dependencies.

## Architecture Patterns

### Current Test Structure
```
src/python/tests/
├── __init__.py                    # empty
├── conftest.py                    # 3 pytest fixtures (unreachable by unittest.TestCase tests)
├── utils.py                       # TestUtils.chmod_from_to helper
├── integration/
│   ├── test_controller/
│   │   ├── test_controller.py     # 2300+ lines, uses SSH + real lftp
│   │   └── test_extract/
│   ├── test_lftp/
│   │   └── test_lftp.py           # 165 lines, integration (SSH + lftp)
│   └── test_web/
│       ├── test_web_app.py        # BaseTestWebApp base class
│       └── test_handler/          # 7 handler tests inherit BaseTestWebApp
└── unittests/
    ├── test_common/               # config, encryption, job, persist, etc.
    ├── test_controller/
    │   ├── test_controller_unit.py # BaseControllerTestCase (lines 11-89)
    │   ├── test_auto_delete.py    # BaseAutoDeleteTestCase (lines 10-60) -- DUPLICATE
    │   ├── test_controller.py     # older controller tests
    │   └── test_scan/
    ├── test_lftp/
    │   └── test_lftp.py           # 794 lines -- MISCLASSIFIED (uses SSH, real lftp)
    ├── test_model/
    ├── test_ssh/
    ├── test_system/
    └── test_web/
```

### Test Execution Flow

```
make run-tests-python
  -> Docker Compose builds seedsyncarr/test/python image
  -> Starts container with sshd + seedsyncarrtest user
  -> Mounts src/python as /src (read-only)
  -> Runs: pytest -v -p no:cacheprovider
  -> All tests (unit + integration) run together in same container
  -> PYTHONPATH=/src, so imports like "from common import Config" work
```

### Pattern: Base Test Case Consolidation (PYARCH-02)
**What:** `BaseControllerTestCase` and `BaseAutoDeleteTestCase` share ~95% identical setUp code (6 patches, mock instances, Controller instantiation). `BaseAutoDeleteTestCase` adds: auto-delete config defaults and timer cleanup in tearDown.
**Approach:** Make `BaseAutoDeleteTestCase` inherit from `BaseControllerTestCase`, overriding only setUp to add auto-delete config and tearDown to add timer cleanup.

```python
# After consolidation — BaseAutoDeleteTestCase inherits from BaseControllerTestCase
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
[VERIFIED: codebase analysis of test_controller_unit.py lines 11-89 and test_auto_delete.py lines 10-60]

### Pattern: Conftest Fixture Conversion (PYARCH-01)
**What:** The 3 conftest.py fixtures (`test_logger`, `mock_context`, `mock_context_with_real_config`) use pytest's `@pytest.fixture` decorator. Since all 112 test classes are `unittest.TestCase`, pytest fixture injection does not apply -- these fixtures are unreachable. No test currently calls them.
**Approach:** Convert conftest fixtures to regular importable helper functions (or a helper class) in a shared module. Keep conftest.py with the helpers importable, or move to `tests/helpers.py`.

```python
# Option A: Convert to importable helper functions in tests/helpers.py
# (preferred — cleanest separation, no pytest magic needed)

import logging
import sys
from unittest.mock import MagicMock
from common import Config


def create_test_logger(name: str) -> tuple[logging.Logger, logging.Handler]:
    """Create a logger with handler. Caller must remove handler in tearDown."""
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger, handler


def create_mock_context(logger=None) -> MagicMock:
    """Create a MagicMock context with standard config attributes."""
    context = MagicMock()
    if logger:
        context.logger = logger
    else:
        context.logger = MagicMock()
    # ... (same attribute setup as current conftest)
    return context
```
[VERIFIED: conftest.py content and grep showing zero actual consumers]

### Anti-Patterns to Avoid
- **Converting unittest.TestCase to pytest-style tests:** The entire test suite uses unittest.TestCase. Converting would be a massive scope change with no quality benefit. Out of scope per REQUIREMENTS.md ("parameterized->pytest.mark migration (PY-15) -- Style preference, extra dependency").
- **Adding new conftest.py fixtures for unittest.TestCase tests:** pytest fixture injection does not work with `unittest.TestCase.setUp()`. Any new shared setup must use importable helpers or class inheritance.
- **Moving test files without updating imports:** The misclassified `test_lftp.py` move (PYARCH-03) requires verifying that no other test file imports from the old path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test logger setup/teardown | Copy-paste logger setup in each test | Shared helper function (`create_test_logger`) | Currently duplicated in 10+ test setUp methods |
| Controller dependency patching | Copy-paste 6 `patch()` calls per test class | `BaseControllerTestCase` base class | Already exists; consolidation eliminates the duplicate |

## Common Pitfalls

### Pitfall 1: unittest.TestCase vs pytest fixture injection
**What goes wrong:** Defining `@pytest.fixture` in conftest.py and expecting unittest.TestCase tests to receive them via function arguments. pytest discovers but does NOT inject fixtures into TestCase methods.
**Why it happens:** pytest's fixture injection only works with plain test functions or classes that don't inherit from unittest.TestCase.
**How to avoid:** Use importable helper functions/classes for shared setup. Call them explicitly in setUp().
**Warning signs:** conftest.py fixtures exist but no test function signature references them.

### Pitfall 2: Test file move breaking pytest discovery
**What goes wrong:** Moving `test_lftp.py` from `unittests/test_lftp/` to `integration/test_lftp/` could cause duplicate class name conflicts (both directories already have a `TestLftp` class in `test_lftp.py`).
**Why it happens:** Both the existing integration `test_lftp.py` and the misclassified unit `test_lftp.py` define `class TestLftp(unittest.TestCase)`.
**How to avoid:** Rename the moved class (e.g., `TestLftpProtocol`) or merge into the existing integration test file.
**Warning signs:** pytest collection warnings about duplicate test names.

### Pitfall 3: Base class constructor re-invocation
**What goes wrong:** When `BaseAutoDeleteTestCase` inherits from `BaseControllerTestCase`, the Controller is constructed twice if setUp calls `super().setUp()` then re-creates Controller with different config.
**Why it happens:** `BaseControllerTestCase.setUp()` creates a Controller with `autodelete.enabled = False`. `BaseAutoDeleteTestCase` needs `autodelete.enabled = True`.
**How to avoid:** Either: (a) set config before Controller construction in a hook, or (b) accept the double-construction as cheap (all dependencies are mocked). Option (b) is fine -- the first Controller is immediately garbage-collected.
**Warning signs:** Unexpected mock call counts in auto-delete tests.

### Pitfall 4: INI string extraction breaking test isolation
**What goes wrong:** Extracting duplicated INI strings to a shared constant may inadvertently couple tests that currently test slightly different config states.
**Why it happens:** The 7 INI string occurrences in `test_config.py` have subtle differences (different field values, presence/absence of sections like `[Encryption]`, `[Sonarr]`, `[Radarr]`).
**How to avoid:** Only extract the INI "skeleton" (sections + keys) as a template function with parameters for the varying fields. Do NOT use a single static constant.
**Warning signs:** Tests that need different config values being forced to share the same constant.

### Pitfall 5: Misunderstanding the scope of "unreachable" conftest fixtures
**What goes wrong:** Deleting conftest.py entirely, losing the documented fixture patterns that future pytest-style tests could use.
**Why it happens:** The fixtures ARE unreachable today, but the docstrings serve as documentation for the intended usage pattern.
**How to avoid:** Convert to importable helpers but preserve the documented patterns and usage examples.
**Warning signs:** Removing conftest.py and later having to recreate the same patterns.

## Code Examples

### Example 1: INI Template Function for Config Encryption Tests (PYARCH-06)

```python
# Source: analysis of test_config.py lines 680-963 — 7 occurrences of near-identical INI strings
def build_config_ini(
    *,
    # Fields that vary across tests
    webhook_secret="",
    api_token="",
    remote_password="pass",
    sonarr_api_key="",
    radarr_api_key="",
    encryption_enabled=None,  # None = omit section, True/False = include
    # Fields that are always the same
    debug="False",
    verbose="False",
) -> str:
    """Build a full config INI string with parameterized secret fields.

    Used by encryption tests that need the same INI skeleton with different
    encrypted/plaintext values in the 5 secret fields.
    """
    sections = f"""
[General]
debug={debug}
verbose={verbose}
webhook_secret={webhook_secret}
api_token={api_token}
allowed_hostname=

[Lftp]
remote_address=host
remote_username=user
remote_password={remote_password}
remote_port=22
remote_path=/remote
local_path=/local
remote_path_to_scan_script=/scan.sh
use_ssh_key=False
num_max_parallel_downloads=2
num_max_parallel_files_per_download=3
num_max_connections_per_root_file=4
num_max_connections_per_dir_file=5
num_max_total_connections=6
use_temp_file=False

[Controller]
interval_ms_remote_scan=30000
interval_ms_local_scan=10000
interval_ms_downloading_scan=2000
extract_path=/extract
use_local_path_as_extract_path=False
max_tracked_files=5000

[Web]
port=8800

[AutoQueue]
enabled=False
patterns_only=False
auto_extract=False

[Sonarr]
enabled=False
sonarr_url=
sonarr_api_key={sonarr_api_key}

[Radarr]
enabled=False
radarr_url=
radarr_api_key={radarr_api_key}

[AutoDelete]
enabled=False
dry_run=False
delay_seconds=60
"""
    if encryption_enabled is not None:
        sections += f"""
[Encryption]
enabled={encryption_enabled}
"""
    return sections
```

### Example 2: Coverage Gap Documentation Structure (PYARCH-04)

```markdown
# Python Test Coverage Gaps

## Modules Without Dedicated Test Files

| Module | Path | Lines | Why Not Tested | Covered Indirectly? |
|--------|------|-------|----------------|---------------------|
| ActiveScanner | controller/scan/active_scanner.py | 52 | Orchestrates scanner processes; requires multiprocessing | Partially via test_scanner_process.py |
| WebAppJob | web/web_app_job.py | 79 | Manages web app lifecycle thread | No |
| WebAppBuilder | web/web_app_builder.py | 62 | Constructs Bottle app with middleware | Partially via integration test_web_app.py |
| scan_fs | scan_fs.py | 40 | Remote filesystem scanning script | No |

## Tracked for Phase 94
COVER-06 addresses ActiveScanner. Other modules tracked as future work.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pytest fixtures in conftest.py | Not applicable (all tests are unittest.TestCase) | N/A | Fixtures defined but unreachable |
| Duplicate base classes per file | Single base class with inheritance | This phase | Eliminates ~50 lines of duplication |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `BaseAutoDeleteTestCase` can safely inherit from `BaseControllerTestCase` without breaking the 4 auto-delete test classes (63 tests) | Architecture Patterns | Medium -- could require setUp refactoring if mock state conflicts |
| A2 | Moving `unittests/test_lftp/test_lftp.py` to `integration/test_lftp/` requires renaming the class to avoid `TestLftp` duplicate | Pitfalls | Low -- pytest may handle it via module path, but explicit rename is safer |
| A3 | The 7 INI string blocks in `test_config.py` share enough structure to extract to a single parameterized template | Code Examples | Low -- visual inspection confirms 5 are nearly identical; 2 have minor structural differences (missing sections) |

## Open Questions

1. **Should `BaseAutoDeleteTestCase` import from `test_controller_unit.py` or should the base class move to a shared module?**
   - What we know: `BaseControllerTestCase` is currently defined in `test_controller_unit.py` (line 11). `BaseAutoDeleteTestCase` is in `test_auto_delete.py` (line 10).
   - What's unclear: Whether importing between test files is acceptable project convention or if a shared `tests/unittests/test_controller/base.py` module is preferred.
   - Recommendation: Move `BaseControllerTestCase` to `tests/unittests/test_controller/base.py` and import from both files. This is cleaner than cross-file test imports and makes the shared nature explicit.

2. **Should the moved test_lftp.py be merged into the existing integration test_lftp.py or kept as a separate file?**
   - What we know: Integration `test_lftp.py` (165 lines) tests download edge cases (quotes, spaces). Unit `test_lftp.py` (794 lines) tests lftp protocol operations (queue, kill, status, auth). They test different aspects.
   - What's unclear: Whether the project prefers few large test files or many focused ones.
   - Recommendation: Keep as separate files. Rename the moved file to avoid duplicate class names (e.g., `test_lftp_protocol.py` with `TestLftpProtocol`).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PYARCH-01 | Convert conftest fixtures to importable helpers or adopt pytest-style tests | All 112 test classes use unittest.TestCase; conftest fixtures are unreachable. Convert to importable helpers in a helper module. See Architecture Patterns section. |
| PYARCH-02 | Consolidate duplicated BaseControllerTestCase and BaseAutoDeleteTestCase | setUp code is ~95% identical (6 patches, mock instances, Controller init). BaseAutoDeleteTestCase can inherit from BaseControllerTestCase. See Architecture Patterns and Code Examples. |
| PYARCH-03 | Move misclassified test_lftp.py from unittests to integration | `unittests/test_lftp/test_lftp.py` (794 lines) uses SSH, real lftp processes, timeout_decorator, filesystem ops -- clearly integration. Must rename class to avoid duplicate `TestLftp` in `integration/test_lftp/test_lftp.py`. |
| PYARCH-04 | Document coverage gaps for ActiveScanner, WebAppJob, WebAppBuilder, scan_fs | All 4 modules confirmed to have no dedicated test files. ActiveScanner has 1 partial reference in test_scanner_process.py. See Code Examples for documentation structure. |
| PYARCH-05 | Document private-API coupling via name-mangling as accepted trade-off | 155 name-mangling references (`_Controller__`, `_ControllerHandler__`) across 5 test files. This is an accepted trade-off for testing private methods. |
| PYARCH-06 | Extract duplicated INI strings in config encryption tests to shared constant | 7 occurrences of near-identical INI config blocks in test_config.py (1124 lines). Extract to a parameterized template function. See Code Examples. |
</phase_requirements>

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.3 (running unittest.TestCase tests) |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `make run-tests-python` (Docker-based, no local pytest) |
| Full suite command | `make run-tests-python` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PYARCH-01 | Conftest fixtures importable as helpers | smoke | `make run-tests-python` (all tests still pass) | N/A -- structural change |
| PYARCH-02 | Single BaseControllerTestCase, all controller tests inherit | smoke | `make run-tests-python` (all controller tests pass) | N/A -- structural change |
| PYARCH-03 | test_lftp.py in integration directory | smoke | `make run-tests-python` (lftp tests discovered and pass) | N/A -- file move |
| PYARCH-04 | Coverage gap documentation exists | manual-only | Verify markdown file exists | N/A -- documentation |
| PYARCH-05 | Name-mangling trade-off documented | manual-only | Verify documentation exists | N/A -- documentation |
| PYARCH-06 | INI strings extracted to shared template | smoke | `make run-tests-python` (config encryption tests pass) | N/A -- refactor |

### Sampling Rate
- **Per task commit:** `make run-tests-python`
- **Per wave merge:** `make run-tests-python`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. No new test framework or config needed.

## Security Domain

This phase involves only test infrastructure reorganization. No production code changes. No new attack surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | -- |
| V3 Session Management | no | -- |
| V4 Access Control | no | -- |
| V5 Input Validation | no | -- |
| V6 Cryptography | no | -- |

No security controls needed -- this is a test-only refactoring phase.

## Sources

### Primary (HIGH confidence)
- `src/python/pyproject.toml` -- pytest configuration, dependencies, coverage settings
- `src/python/tests/conftest.py` -- 3 pytest fixtures, all unreachable by unittest.TestCase
- `src/python/tests/unittests/test_controller/test_controller_unit.py` -- BaseControllerTestCase definition (lines 11-89)
- `src/python/tests/unittests/test_controller/test_auto_delete.py` -- BaseAutoDeleteTestCase definition (lines 10-60)
- `src/python/tests/unittests/test_lftp/test_lftp.py` -- Misclassified integration test (794 lines, SSH + lftp)
- `src/python/tests/integration/test_lftp/test_lftp.py` -- Existing integration test (165 lines)
- `src/python/tests/unittests/test_common/test_config.py` -- 7 duplicated INI blocks (1124 lines total)
- `Makefile` -- `run-tests-python` target (Docker compose based)
- `src/docker/test/python/Dockerfile` -- Test container setup with sshd
- `.planning/REQUIREMENTS.md` -- Requirement definitions and scope exclusions

### Secondary (MEDIUM confidence)
- Codebase grep: 112 unittest.TestCase classes, 0 pytest-style test functions consuming conftest fixtures
- Codebase grep: 155 name-mangling references across 5 test files
- Module line counts: ActiveScanner (52), WebAppJob (79), WebAppBuilder (62), scan_fs (40)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, versions verified from pyproject.toml
- Architecture: HIGH -- all patterns derived from direct codebase analysis
- Pitfalls: HIGH -- each pitfall identified from actual codebase structure

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (stable -- test infrastructure changes slowly)
