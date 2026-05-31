# Phase 99: Low-Priority Python Coverage - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 2 (both EXTEND existing test files — no new files, no production-code changes anticipated)
**Analogs found:** 2 / 2 (both in-file / sibling-class analogs)

> Both deliverables are unit tests that extend an existing `unittest.TestCase` file.
> The closest analogs live **inside the same file** (or its base fixture), so the
> planner should treat these as "copy the established convention from the
> neighbor method" assignments, not "find a new pattern elsewhere."

---

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `src/python/tests/unittests/test_controller/test_auto_delete.py` (COVLOW-01: new `TestAutoDeleteToggleDuringTimer` class, 2 tests) | unit test (controller, live-Timer) | event-driven (scheduled callback) | `TestAutoDeleteScheduling` (33-69) for the **schedule/Timer arm** + `TestAutoDeleteExecution.test_execute_disabled_skips_deletion` / `test_execute_dry_run_does_not_delete` (101-116) for the **assertion style** | role-match (composite — no single existing test drives schedule→flip→fire) |
| `src/python/tests/unittests/test_common/test_bounded_ordered_set.py` (COVLOW-02: 1 new method on `TestBoundedOrderedSet`) | unit test (data structure, plain) | transform / eviction | `test_from_iterable_with_eviction` (213-219) + `test_eviction_when_full` (71-85) | exact (same class, same idiom) |

---

## KEY DISTINCTION (read first — this is the whole point of COVLOW-01)

The existing `TestAutoDeleteExecution` tests call `__execute_auto_delete` **DIRECTLY**
after flipping config (see `test_auto_delete.py:101-116`). That proves the *method*
honors config — it does **NOT** close the COVLOW-01 gap.

COVLOW-01 is specifically the **schedule → flip → fire** window:
- `__schedule_auto_delete` (`controller.py:806-821`) reads `delay_seconds` and arms a real `threading.Timer` at line 815.
- `__execute_auto_delete` (`controller.py:838-850`) **re-reads** `enabled`/`dry_run` when the Timer fires — deliberately split across the timer window.

So the new tests MUST:
1. Arm a **real** `threading.Timer` via `self.controller._Controller__schedule_auto_delete(name)` (analog: `TestAutoDeleteScheduling.test_schedule_creates_timer`, lines 40-45).
2. Flip the config mock **after** scheduling, **before** the timer fires.
3. Join the pending timer (pulled from `__pending_auto_deletes`) and assert on the `delete_local` mock (analog: the assertion lines in `test_execute_disabled_skips_deletion` / `test_execute_dry_run_does_not_delete`).

Do **NOT** copy the direct-call body of `test_execute_disabled_skips_deletion` verbatim — copy its *assertion*, but graft it onto the *scheduling* path.

---

## Pattern Assignments

### `test_auto_delete.py` — COVLOW-01 (controller, event-driven / live Timer)

**Primary analog (schedule + Timer arm):** `TestAutoDeleteScheduling`, `test_auto_delete.py:33-69`
**Assertion analog:** `TestAutoDeleteExecution.test_execute_disabled_skips_deletion` / `test_execute_dry_run_does_not_delete`, `test_auto_delete.py:101-116`
**Fixture to inherit:** `BaseAutoDeleteTestCase`, `test_auto_delete.py:10-31`
**Helper to reuse:** `_make_safe_mock_file`, `test_auto_delete.py:75-81`

**Recommended placement (per CONTEXT D / discretion):** new class
`TestAutoDeleteToggleDuringTimer(TestAutoDeleteExecution)` — subclassing
`TestAutoDeleteExecution` inherits both the `_make_safe_mock_file` helper AND the
`BaseAutoDeleteTestCase` setUp/tearDown chain (same pattern `TestAutoDeleteCoverageGuard`
uses at line 256). A fresh top-level class name makes the live-Timer distinction explicit.

**Imports pattern** (`test_auto_delete.py:1-7`) — already present in the file, add `import pytest` and `import time` only if needed for the join/timeout:
```python
import threading
from unittest.mock import MagicMock

from controller import Controller
from controller.controller_persist import ControllerPersist
from model import ModelFile, ModelError
from tests.unittests.test_controller.base import BaseControllerTestCase
```

**Fixture (inherited — do NOT re-implement)** (`test_auto_delete.py:10-31`). Critical
points the new tests rely on:
```python
class BaseAutoDeleteTestCase(BaseControllerTestCase):
    def setUp(self):
        super().setUp()
        self.mock_context.config.autodelete.enabled = True
        self.mock_context.config.autodelete.dry_run = False
        self.mock_context.config.autodelete.delay_seconds = 10   # <-- OVERRIDE to ~0.05 in the new test
        self.controller = Controller(context=self.mock_context, persist=self.persist,
                                     webhook_manager=self.mock_webhook_manager)

    def tearDown(self):
        # Cancels any pending timers BEFORE stopping patches -- prevents thread leak.
        for timer in list(self.controller._Controller__pending_auto_deletes.values()):
            timer.cancel()
        self.controller._Controller__pending_auto_deletes.clear()
        super().tearDown()
```

**Safe-file helper (inherited via TestAutoDeleteExecution)** (`test_auto_delete.py:75-81`):
```python
def _make_safe_mock_file(self, state=ModelFile.State.DOWNLOADED, is_dir=False, children=None):
    mock_file = MagicMock(spec=ModelFile)
    mock_file.state = state
    mock_file.is_dir = is_dir
    mock_file.get_children.return_value = children or []
    return mock_file
```

**Schedule / Timer-arm pattern** (analog `test_auto_delete.py:40-45`) — read the live timer back out of the pending dict:
```python
self.controller._Controller__schedule_auto_delete("test_file.mkv")
timer = self.controller._Controller__pending_auto_deletes["test_file.mkv"]
self.assertIsInstance(timer, threading.Timer)   # (optional sanity, from analog)
```

**Config-flip mid-test pattern** (mock attribute write — analog `test_auto_delete.py:103, 112`):
```python
# Flip AFTER scheduling, BEFORE the timer fires:
self.mock_context.config.autodelete.enabled = False   # COVLOW-01 (a) skip path
# -- or --
self.mock_context.config.autodelete.dry_run = True    # COVLOW-01 (b) logs-only path
```

**Binding assertion** (analog `test_auto_delete.py:107-108, 116`):
```python
self.mock_file_op_manager.delete_local.assert_not_called()
self.mock_file_op_manager.delete_remote.assert_not_called()   # safety, from line 99
```

**Flake control (D-01a — join, do NOT sleep a fixed interval)** — the `timer`
object pulled from `__pending_auto_deletes` is a `threading.Timer` (a `Thread`),
so `timer.join(timeout=...)` blocks until the callback completes:
```python
timer.join(timeout=5)               # generous cap; callback finishes well under this
self.assertFalse(timer.is_alive())  # confirm it actually fired (not still pending)
```
Set the schedule delay short by overriding the fixture default before scheduling:
```python
self.mock_context.config.autodelete.delay_seconds = 0.05
```
Note: `_make_safe_mock_file` + `self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)`
(analog `test_auto_delete.py:85-86`) is still required so that, on the **enabled+non-dry-run**
control path, `delete_local` *would* be called — otherwise the `assert_not_called` is
vacuous. Recommend pairing each toggle test with the understanding that the only reason
`delete_local` is not called is the re-read, not a missing file.

**Timeout guard (D-01a — established repo pattern)** — `@pytest.mark.timeout(N)` is
already used across the suite (e.g. `tests/unittests/test_ssh/test_sshcp.py:71` with
`import pytest` at line 10; `pytest-timeout` is configured/available). Apply it to each
live-Timer test:
```python
import pytest
...
@pytest.mark.timeout(10)
def test_disabled_flip_during_timer_window_skips_delete(self):
    ...
```

---

### `test_bounded_ordered_set.py` — COVLOW-02 (data structure, eviction transform)

**Primary analog:** `test_from_iterable_with_eviction`, `test_bounded_ordered_set.py:213-219`
**Secondary analog (eviction return-value + membership idiom):** `test_eviction_when_full`, `test_bounded_ordered_set.py:71-85`
**Style:** plain `unittest.TestCase` method on the existing `TestBoundedOrderedSet` class — no fixtures, fully self-contained (per CONTEXT code_context note).

**Imports pattern** (`test_bounded_ordered_set.py:1-3`) — already present, nothing to add:
```python
import unittest

from common import BoundedOrderedSet
```

**Load-via-from_iterable pattern** (analog `test_bounded_ordered_set.py:215`):
```python
bset = BoundedOrderedSet.from_iterable(['a', 'b', 'c'], maxlen=3)
```

**Eviction return-value + membership assertion idiom** (analog `test_bounded_ordered_set.py:78-85`):
```python
evicted = bset.add('d')
self.assertEqual('b', evicted)          # COVLOW-02 (a): oldest NON-touched evicts
```

**Ordering assertion idiom** (analog `as_list` usage at `test_bounded_ordered_set.py:218`, and `list(bset)` at 132-133):
```python
self.assertEqual(['c', 'a', 'd'], bset.as_list())   # COVLOW-02 (b): touched 'a' retained + reordered
```

**Eviction-count idiom** (analog `test_bounded_ordered_set.py:219`):
```python
self.assertEqual(1, bset.total_evictions)            # COVLOW-02 (c)
```

**Full assembled shape (D-03)** — the one new method, built entirely from the two analogs plus a `touch` call:
```python
def test_eviction_order_after_touch(self):
    """A touched item survives; the oldest NON-touched item evicts first."""
    bset = BoundedOrderedSet.from_iterable(['a', 'b', 'c'], maxlen=3)
    self.assertTrue(bset.touch('a'))        # move_to_end -> 'a' becomes most-recent
    evicted = bset.add('d')                 # forces exactly one eviction
    self.assertEqual('b', evicted)          # (a) oldest non-touched
    self.assertEqual(['c', 'a', 'd'], bset.as_list())  # (b) order
    self.assertEqual(1, bset.total_evictions)          # (c) count
```
(System-under-test confirmed: `touch` → `OrderedDict.move_to_end` at `bounded_ordered_set.py:104`; `add` eviction → `popitem(last=False)` at `bounded_ordered_set.py:85`.)

---

## Shared Patterns

### Name-mangled private access (controller tests)
**Source:** `test_auto_delete.py:27, 42, 86, 88, 134`
**Apply to:** COVLOW-01 tests
The controller's private members are reached via the `_Controller__<name>` mangled handle. Established handles the new tests use:
```python
self.controller._Controller__schedule_auto_delete(file_name)   # arm timer
self.controller._Controller__pending_auto_deletes              # dict[str, threading.Timer]
self.controller._Controller__execute_auto_delete(file_name)    # (NOT called directly in COVLOW-01)
self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
```

### Config-as-mock toggling
**Source:** `test_auto_delete.py:15-17, 103, 112`; `base.py:44`
**Apply to:** COVLOW-01 tests
`self.mock_context.config.autodelete.*` is a `MagicMock` attribute; assigning to it
mid-test changes what the next attribute read sees — no real config reload. This is
exactly why the in-method re-read at `controller.py:838-850` is observable from a test
that flips the value after `__schedule_auto_delete` returns.

### MagicMock(spec=ModelFile) for SUT inputs
**Source:** `test_auto_delete.py:77-80, 215-222`
**Apply to:** COVLOW-01 tests (via inherited `_make_safe_mock_file`)
Use `MagicMock(spec=ModelFile)` and explicitly set `state`, `is_dir`, `get_children.return_value`
so the file passes the state + pack guards and the only deciding factor is the config re-read.

### Timer-leak teardown
**Source:** `BaseAutoDeleteTestCase.tearDown`, `test_auto_delete.py:25-30`
**Apply to:** COVLOW-01 tests
Inherited automatically — cancels and clears `__pending_auto_deletes` before patches stop.
The new tests must NOT bypass this base class (subclass `TestAutoDeleteExecution` or
`BaseAutoDeleteTestCase` directly so the chain runs).

### @pytest.mark.timeout hang-guard
**Source:** `tests/unittests/test_ssh/test_sshcp.py:10, 71` (and many others across the suite)
**Apply to:** COVLOW-01 tests (any test that joins a real thread)
```python
import pytest
@pytest.mark.timeout(10)
```

---

## No Analog Found

None. Every required pattern has a concrete in-repo analog. COVLOW-01 is the only
"composite" case: no single existing test drives the schedule→flip→fire path end-to-end,
so it is assembled from `TestAutoDeleteScheduling` (Timer arm) + `TestAutoDeleteExecution`
disabled/dry-run tests (assertion). This is a role-match, not a missing analog.

---

## Metadata

**Analog search scope:** `src/python/tests/unittests/test_controller/`, `src/python/tests/unittests/test_common/`, `src/python/controller/controller.py`, `src/python/common/bounded_ordered_set.py`, `src/python/tests/unittests/test_ssh/` (timeout idiom)
**Files scanned:** 6
**Pattern extraction date:** 2026-05-29
