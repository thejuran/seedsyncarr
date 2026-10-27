# Phase 124: Model-Stream Overflow Recovery - Pattern Map

**Mapped:** 2026-10-26
**Files analyzed:** 8 (3 production + 5 test)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `src/python/web/utils.py` (+`StreamQueue.clear()`) | utility | streaming (bounded queue) | itself — `StreamQueue.get_next_event()`/`put()` (same file) | exact (extend in place) |
| `src/python/controller/controller.py` (+`resync_model_files`) | service | event-driven (atomic lock-protected snapshot) | `Controller.get_model_files_and_add_listener` (same file, line 516) | exact |
| `src/python/web/handler/stream_model.py` (`ModelStreamHandler.get_value`) | controller (SSE stream handler) | streaming | `StatusStreamHandler.get_value` (`src/python/web/handler/stream_status.py`) | role-match (shows the "self-healing via full snapshot" pattern this phase must replicate for drops) |
| `src/python/tests/unittests/test_web/test_stream_queue.py` | test | streaming | itself — `test_overflow_drops_oldest`, `test_multiple_overflows` (same file) | exact (extend in place) |
| `src/python/tests/unittests/test_controller/test_controller_unit.py` (or `test_controller.py`) | test | event-driven / concurrency | `TestRootLifecycleResetCallback.test_callback_does_not_take_model_lock` (`test_controller_unit.py:1066-1076`) | exact (real-lock, real-thread pattern to copy directly) |
| `src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py` | test | streaming | itself — `TestModelStreamHandler` (same file) + `TestStatusStreamHandler` (`test_stream_status_handler.py`) for the "first_run"-style gating pattern | exact (extend in place) |
| `src/python/tests/integration/test_web/test_handler/test_stream_model.py` | test (integration) | streaming | itself — `test_stream_model_serializes_updates` (same file, Timer-based producer) | exact (extend in place) |
| `src/python/tests/helpers/wsgi_stream.py` (possible new stall-capable variant) | test utility | streaming | itself — `collect_sse_chunks` (same file) | role-match (needs a new function, not a rewrite, per Pitfall 3) |

## Pattern Assignments

### `src/python/web/utils.py` (utility, streaming) — add `StreamQueue.clear()`

**Analog:** itself, `StreamQueue.put()` / `get_next_event()` (`src/python/web/utils.py:33-72`)

**Imports pattern** (lines 1-8):
```python
import logging
from queue import Queue, Empty, Full
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

# Default maximum queue size to prevent unbounded memory growth
DEFAULT_QUEUE_MAXSIZE = 1000
```

**Core pattern to mirror** — non-blocking drain loop, same style as `get_next_event` (lines 65-72):
```python
def get_next_event(self) -> Optional[T]:
    """
    Returns the next event if there is one, otherwise returns None
    """
    try:
        return self.__queue.get(block=False)
    except Empty:
        return None
```
`clear()` is the same `get(block=False)` / `except Empty` idiom repeated in a loop until empty — do not reach into `Queue`'s private deque. Per RESEARCH.md's sketch:
```python
def clear(self) -> None:
    """
    Discard all currently queued events without affecting dropped_count.
    """
    while True:
        try:
            self.__queue.get(block=False)
        except Empty:
            return
```

**Error handling pattern** — mirror `put()`'s `except Full` / `except Empty` style (lines 33-63); no new exception types needed, `queue.Empty` is already imported.

**Rate-limited warning pattern to reuse for the resync log** (lines 46-52, D-08's "rate-limited like the existing `StreamQueue overflow` warning"):
```python
self.__dropped_count += 1
if self.__dropped_count % 100 == 1:
    self.__logger.warning(
        "StreamQueue overflow: dropped {} events total".format(
            self.__dropped_count
        )
    )
```

---

### `src/python/controller/controller.py` (service, event-driven) — add `resync_model_files(discard_backlog)`

**Analog:** `Controller.get_model_files_and_add_listener` (`src/python/controller/controller.py:516-530`)

**Imports pattern** (file already imports what's needed; no new imports except `typing.Callable` if not already present — check existing `typing` import line near the top of the file):
```python
# existing pattern at line ~502-530, same file
```

**Core atomic-snapshot pattern to extend** (lines 516-530, verbatim):
```python
def get_model_files_and_add_listener(self, listener: IModelListener):
    """
    Adds a listener and returns the current state of model files in one atomic operation
    This guarantees that model update events are not missed or duplicated for the clients
    Without an atomic operation, the following scenarios can happen:
        1. get_model() -> model updated -> add_listener()
           The model update never propagates to client
        2. add_listener() -> model updated -> get_model()
           The model update is duplicated on client side (once through listener, and once
           through the model).
    """
    with self.__model_lock:
        self.__model.add_listener(listener)
        model_files = self.__get_model_files()
    return model_files
```
New method sits immediately next to it, same docstring style, same `with self.__model_lock:` block, swapping `add_listener` for an injected no-arg callback (see RESEARCH.md's `resync_model_files(discard_backlog: Callable[[], None])` sketch) — **do not** type the parameter as `StreamQueue`/`WebResponseModelListener`; `controller/` has zero imports from `web/` today (verified) and must stay that way.

**Neighboring lock-only methods for style reference** (lines 502-514):
```python
def add_model_listener(self, listener: IModelListener):
    """
    Adds a listener to the controller's model
    """
    with self.__model_lock:
        self.__model.add_listener(listener)

def remove_model_listener(self, listener: IModelListener):
    """
    Removes a listener from the controller's model
    """
    with self.__model_lock:
        self.__model.remove_listener(listener)
```

**Error handling:** none — these methods don't catch; they rely on the `with` block and propagate anything from `self.__model.add_listener`/`__get_model_files`. Follow suit (no try/except around the lock body).

---

### `src/python/web/handler/stream_model.py` (controller/SSE handler, streaming) — `ModelStreamHandler.get_value()` resync gate

**Analog A (same file, current structure to extend):** lines 1-74, in particular `get_value` (lines 50-68):
```python
from typing import Optional, List

from ..web_app import IStreamHandler
from ..utils import StreamQueue
from ..serialize import SerializeModel
from model import IModelListener, ModelFile
from common import overrides
from controller import Controller

...

@overrides(IStreamHandler)
def get_value(self) -> Optional[str]:
    # Send the entire initial model as a single "model-init" event.
    # ...
    if self.initial_model_files is not None:
        files = self.initial_model_files
        self.initial_model_files = None
        return self.serialize.model(files)

    # After the initial model is sent, process real-time updates
    event = self.model_listener.get_next_event()
    if event is not None:
        return self.serialize.update_event(event)
    return None
```
The new resync gate is a **second early-return, inserted strictly before the final `get_next_event()` call** (Pitfall 1) — same two-early-returns shape, same "set state to None/False after consuming it" idiom already used for `initial_model_files`.

**Analog B — the sibling stream that already does what this phase needs** (`src/python/web/handler/stream_status.py:20-42`), useful because it shows the project's existing "full snapshot replaces partial state" idiom this phase is porting to the model stream on-demand:
```python
class StatusStreamHandler(IStreamHandler):
    def __init__(self, status: Status):
        self.status = status
        self.serialize = SerializeStatus()
        self.status_listener = StatusListener(status)
        self.first_run = True

    @overrides(IStreamHandler)
    def get_value(self) -> Optional[str]:
        if self.first_run:
            self.first_run = False
            status = self.status.copy()
            return self.serialize.status(status)
        else:
            status = self.status_listener.get_next_event()
            if status is not None:
                return self.serialize.status(status)
            else:
                return None
```
`StatusListener.notify()` (`stream_status.py:16-18`) puts a *full* snapshot on every event (`self.put(self.__status.copy())`), which is why the status stream self-heals for free (D-06 evidence) — the model stream's incremental add/remove/update events don't have that property, which is exactly the gap this phase closes with an on-demand `model-init` resend.

**Validated end-state for `get_value()`** (RESEARCH.md sketch — labeled there as synthesized, not an existing-file quote; use it as the target shape, set up `self._last_seen_dropped`, `self._resync_pending`, `self._resync_count`, `self.logger` in `__init__`):
```python
def get_value(self) -> Optional[str]:
    if self.initial_model_files is not None:
        files = self.initial_model_files
        self.initial_model_files = None
        return self.serialize.model(files)

    dropped_now = self.model_listener.get_dropped_count()
    if dropped_now != self._last_seen_dropped:
        self._resync_pending = True

    if self._resync_pending:
        self._resync_pending = False
        files = self.controller.resync_model_files(self.model_listener.clear)
        # Re-read AFTER the snapshot (Pitfall 4): any drop racing the resync
        # itself is absorbed into THIS snapshot rather than immediately
        # triggering a second one.
        self._last_seen_dropped = self.model_listener.get_dropped_count()
        self._resync_count += 1
        if self._resync_count % 100 == 1:
            self.logger.warning(
                "Model stream resynced after overflow (dropped_total={})".format(dropped_now)
            )
        return self.serialize.model(files)

    event = self.model_listener.get_next_event()
    if event is not None:
        return self.serialize.update_event(event)
    return None
```

**Error handling:** none added — same as `get_value()` today, no try/except; exceptions propagate to the `web_app.__web_stream` loop's existing handling.

**Log-sanitization note (Pitfall 5):** the resync warning logs only an integer count, so `sanitize_log_value` (used at `controller.py:426,774,912,...` for file/root names) is **not** needed here — but if a future edit adds a file/path name to this log line, route it through `sanitize_log_value` like every other such site in this codebase.

---

### Shared test patterns (apply across all 5 test files)

#### `test_stream_queue.py` — existing drop/overflow assertion style to copy for `clear()` and reproduction tests
```python
# src/python/tests/unittests/test_web/test_stream_queue.py:37-54
def test_overflow_drops_oldest(self):
    queue = StreamQueue(maxsize=3)
    queue.put("event1")
    queue.put("event2")
    queue.put("event3")
    self.assertEqual(3, queue.get_queue_size())
    self.assertEqual(0, queue.get_dropped_count())

    # Add fourth event, should drop event1
    queue.put("event4")
    self.assertEqual(1, queue.get_dropped_count())
    # Queue should still be at max size
    self.assertEqual(3, queue.get_queue_size())
    ...
```
New tests (`test_clear_discards_backlog`, `test_clear_does_not_affect_dropped_count`, D-01 reproduction `test_stalled_consumer_overflow_diverges_from_producer_state`) should use this exact bare-`StreamQueue` setup style — no mocks needed, this class has zero collaborators.

#### `test_stream_model_handler.py` — mocked-`Controller` harness to extend for D-02/D-03/D-04 convergence + coalescing tests
```python
# src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py:48-58
class TestModelStreamHandler(unittest.TestCase):
    def setUp(self):
        self.mock_controller = MagicMock(spec=Controller)
        self.handler = ModelStreamHandler(self.mock_controller)

    def test_setup_registers_listener(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        self.mock_controller.get_model_files_and_add_listener.assert_called_once()
        call_args = self.mock_controller.get_model_files_and_add_listener.call_args[0][0]
        self.assertIs(call_args, self.handler.model_listener)
```
`MagicMock(spec=Controller)` means `self.mock_controller.resync_model_files` will raise `AttributeError` until the real method exists on `Controller` — add the production method first, then stub `self.mock_controller.resync_model_files.return_value = [...]` in the new tests. To simulate an overflow without draining, call `self.handler.model_listener.put(...)` (or `.file_added(...)`) more than `maxsize` times directly on the real `WebResponseModelListener` instance (`self.handler.model_listener`), matching Pitfall 3 option (a) — no WSGI machinery required.

#### `test_controller_unit.py` — real-lock, real-thread pattern to copy directly for D-03 atomicity
```python
# src/python/tests/unittests/test_controller/test_controller_unit.py:1066-1076
def test_callback_does_not_take_model_lock(self):
    """Both pipeline call sites hold the model lock; re-taking it would deadlock."""
    lock = self.controller._Controller__model_lock
    with lock:
        worker = threading.Thread(
            target=self.controller._on_root_lifecycle_reset, args=("X", "under lock"), daemon=True
        )
        worker.start()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive(), "callback blocked on the model lock")
    self.mock_completion_gate.invalidate.assert_called_once_with("X", "under lock")
```
For `resync_model_files`, invert the assertion: hold `__model_lock` externally, start a thread calling `controller.resync_model_files(some_callable)`, assert it *blocks* until the lock is released (`worker.is_alive()` is `True` while held, `False` shortly after release), then assert the returned snapshot reflects every model mutation made before release and none made after. `BaseControllerTestCase` (`src/python/tests/unittests/test_controller/base.py:10-61`) already wires a real `Controller` with a real `threading.Lock()`-backed `__model_lock` and mocks every other collaborator — use it as the base class, same as `TestRootLifecycleResetCallback`.

#### `test_stream_model.py` (integration) + `wsgi_stream.py` — Timer-based producer pattern, extended for a stalling consumer
```python
# src/python/tests/integration/test_web/test_handler/test_stream_model.py:57-67
def send_updates():
    assert self.model_listener is not None, "listener not set before Timer fired"
    self.model_listener.file_added(added_file)
    self.model_listener.file_removed(removed_file)
    self.model_listener.file_updated(old_file, new_file)
Timer(0.5, send_updates).start()

# Stop at 2.0s to allow the 0.5s updates to arrive
collect_sse_chunks(self.web_app, stop_after_s=2.0)
```
`collect_sse_chunks` (`src/python/tests/helpers/wsgi_stream.py:29-50`) does `list(web_app(environ, start_response))`, which **continuously drains** the generator — it cannot express a stall (Pitfall 3). If the plan includes an integration-level "fails before/passes after" test, add a new helper function alongside `collect_sse_chunks` in the same file (same `make_wsgi_environ` setup, same `Timer`-based stop convention) that returns the raw generator (`gen = web_app(environ, start_response)`) and lets the test call `next(gen)` a controlled number of times itself, pausing between calls while a background `Timer` floods `model_listener.file_added(...)` past `maxsize`. This is explicitly Claude's Discretion per CONTEXT.md and explicitly optional per RESEARCH.md Open Question 1 — the unit-level pair above is sufficient on its own for STRM-01/STRM-02 if the plan chooses not to add it.

#### `ModelFile.__eq__` — convergence-test equality helper (verified, `src/python/model/file.py:87-120`)
`ModelFile` already defines deep `__eq__` (excludes timestamp/parent/frozen flag, recurses into children), so a convergence test can assert `self.assertEqual(expected_files, actual_files)` directly on lists of `ModelFile` objects without a custom comparator. For a test that reconstructs the model from the exact wire-format JSON (RESEARCH.md's "Don't Hand-Roll" recommendation), parse `SerializeModel.model()`/`update_event()` output and compare the resulting dicts/JSON, not a hand-rolled Python reimplementation of the frontend reducer.

---

## No Analog Found

None — every file in the change footprint has a same-file or sibling-file analog (see table above). The one open design choice (whether to add a new `wsgi_stream.py` helper) is flagged above as Claude's Discretion, not a missing pattern — `collect_sse_chunks` is the correct starting point to extend, not replace.

## Shared Patterns

### Lock-protected atomic snapshot
**Source:** `Controller.get_model_files_and_add_listener` (`src/python/controller/controller.py:516-530`)
**Apply to:** `Controller.resync_model_files` — same `with self.__model_lock:` block shape, same "mutate state, then call `__get_model_files()`, then release" ordering. Never discard a listener's backlog (`clear()`) outside this lock (Anti-Pattern in RESEARCH.md).

### Rate-limited counting warning (no time-based throttling)
**Source:** `StreamQueue.put()` (`src/python/web/utils.py:46-52`) — `dropped_count % 100 == 1`
**Apply to:** The new resync warning in `ModelStreamHandler.get_value()`; count *resyncs* (`_resync_count % 100 == 1`), not raw drops, per RESEARCH.md's Open Question 2 recommendation — drops are already logged by `StreamQueue.put()` itself.

### Full-snapshot-replaces-partial-state (frontend, unchanged)
**Source:** `ModelFileService.parseEvent`, `model-init` branch (`src/angular/src/app/services/files/model-file.service.ts:136-161`)
```typescript
if (name === this.EVENT_INIT) {
    const parsed: ModelFileJson[] = JSON.parse(data);
    const newFiles: ModelFile[] = [];
    for (const file of parsed) { newFiles.push(ModelFile.fromJson(file)); }
    const newMap = Immutable.Map<string, ModelFile>(newFiles.map(value => ([value.name, value])));
    this._files.next(newMap);   // unconditional full replace — already idempotent for a 2nd model-init
}
```
**Apply to:** Nothing new — this confirms D-02's premise that no frontend change is needed. If a frontend spec is added (Claude's Discretion) to prove a repeated `model-init` still fully replaces the list, it belongs in `src/angular/src/app/tests/unittests/services/files/model-file.service.spec.ts`, asserting two consecutive `parseEvent(EVENT_INIT, ...)` calls each produce a full-replace with no residue from the first.

### Log-injection discipline (CWE-117)
**Source:** `sanitize_log_value` usage, e.g. `controller.py:912,923,932,950,978-981` (always wraps file/root names, never raw counts)
**Apply to:** Not required for the resync warning (count-only), but keep in mind if the log line is ever extended to include a tab/connection identifier or file name.

## Conventions

Derived via the shared `gsd-tools.cjs verify conventions --derive` module, scope `src/python` (covers every file in this phase's change footprint: `web/`, `controller/`, `tests/`).

| Axis | Dominant | Share | Entropy | Status |
|------|----------|-------|---------|--------|
| File-name casing | none (mixed) | 38.8% | 0.985 | contested hotspot |
| Identifier casing | none (mixed: camel 426, Pascal 289, CONSTANT 47) | 54.1% | 0.613 | contested hotspot |
| Export style | `cjs` | 100% | 0.0 | named contract |
| Import style | — | — | — | insufficient data (n=2) |

(Supplementary, same run: `py-wildcard-import` is a named contract at 100% explicit — no `from x import *` anywhere; `py-import-relativity` is a contested hotspot at 63.6% relative vs. 36.4% absolute.)

**Contested hotspots (author's choice):** file-name casing and identifier casing fall below the 70% dominance threshold repo-wide, so neither can be treated as a named contract — this mirrors the project's own CJS↔SDK dual-resolver split (`bin/lib/**` is CJS `module.exports`/`require`; `sdk/src/**` is ESM `export`/`import`), the prototype intentional-contested pattern: each half is internally consistent per-directory, contested only when compared repo-wide. For this phase specifically, match the **local** convention already observed directly in every analog above: `snake_case` filenames and `snake_case` identifiers throughout `src/python/web/`, `src/python/controller/`, and `src/python/tests/` (every file read in this mapping — `utils.py`, `controller.py`, `stream_model.py`, `stream_status.py`, `test_stream_queue.py`, `test_controller_unit.py`, `wsgi_stream.py` — uses snake_case filenames and snake_case method/variable names with PascalCase classes, consistent with PEP 8). The repo-wide "contested" signal comes from the Angular/TypeScript tree (`src/angular/**`, camelCase) being mixed into the same scope, not from any disagreement within the Python backend itself. Planners should not treat this phase's naming as a free choice — follow the Python-side convention shown in every excerpt above, not the repo-wide aggregate.

## Metadata

**Analog search scope:** `src/python/web/`, `src/python/web/handler/`, `src/python/controller/`, `src/python/model/`, `src/python/tests/unittests/test_web/`, `src/python/tests/unittests/test_controller/`, `src/python/tests/integration/test_web/test_handler/`, `src/python/tests/helpers/`, `src/angular/src/app/services/files/`
**Files scanned:** 15 read directly (listed in Sources below) + conventions tool scan of `src/python` (116 files, file-name axis; 788 identifiers)
**Pattern extraction date:** 2026-10-26

### Sources read directly for this mapping
- `src/python/web/utils.py` (full, 96 lines)
- `src/python/web/handler/stream_model.py` (full, 74 lines)
- `src/python/web/handler/stream_status.py` (full, 48 lines)
- `src/python/web/serialize/serialize_model.py` (full, 113 lines)
- `src/python/controller/controller.py` (lines 495-540, plus grep context for `__model_lock`/`sanitize_log_value` call sites)
- `src/python/model/model.py` (lines 1-80)
- `src/python/model/file.py` (lines 80-125, `__eq__`)
- `src/python/tests/unittests/test_web/test_stream_queue.py` (full, 91 lines)
- `src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py` (full, 153 lines)
- `src/python/tests/unittests/test_web/test_handler/test_stream_status_handler.py` (grep for test names)
- `src/python/tests/unittests/test_controller/test_controller_unit.py` (lines 1040-1130)
- `src/python/tests/unittests/test_controller/base.py` (full, 104 lines)
- `src/python/tests/unittests/test_controller/test_controller.py` (lines 1-40, existence/shape check)
- `src/python/tests/helpers/wsgi_stream.py` (full, 50 lines)
- `src/python/tests/integration/test_web/test_handler/test_stream_model.py` (full, 78 lines)
- `src/angular/src/app/services/files/model-file.service.ts` (lines 110-170)
