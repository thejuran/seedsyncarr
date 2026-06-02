# Phase 109: Controller Decomposition - Pattern Map

**Mapped:** 2026-06-01
**Files analyzed:** 4 (3 new collaborators + 1 modified coordinator)
**Analogs found:** 3 / 3 (new files); coordinator is modified in place

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/python/controller/command_processor.py` | service/collaborator | request-response (command dispatch) | `src/python/controller/file_operation_manager.py` | role-match (receives callbacks + manager instances, no own lock) |
| `src/python/controller/auto_delete_manager.py` | service/collaborator | event-driven (timer callback + BFS) | `src/python/controller/webhook_manager.py` | role-match (injected context, single-underscore state, thin public API) |
| `src/python/controller/model_pipeline.py` | service/collaborator | batch/transform (scan→build→diff→apply) | `src/python/controller/scan_manager.py` | role-match (orchestrates sub-processes/managers, lifecycle start/stop pattern analogous to pipeline start/run) |
| `src/python/controller/controller.py` | coordinator/facade | request-response + event-driven | self (thinned) | exact (modified in place) |

---

## Pattern Assignments

### `src/python/controller/command_processor.py` (collaborator, request-response)

**Analog:** `src/python/controller/file_operation_manager.py`

**Rationale for analog:** `FileOperationManager` is the closest construction-injection match: it receives already-constructed manager instances as constructor arguments (`force_local_scan_callback`, `mp_logger`), stores them under single-underscore names, and exposes public methods that accept `ModelFile` objects and return outcomes without owning any lock. `CommandProcessor` follows the exact same shape — it receives `lftp_manager`, `file_op_manager`, `persist` already constructed, and its `handle_*` methods accept `(file, command)` tuples with no lock of their own.

**Imports pattern** — analog `file_operation_manager.py` lines 1-6:
```python
from typing import List, Optional, Callable

from common import Context, MultiprocessingLogger, AppOneShotProcess
from model import ModelFile
from .extract import ExtractProcess, ExtractStatus
from .delete import DeleteLocalProcess, DeleteRemoteProcess
```

For `command_processor.py`, the import set narrows to only what the handle methods actually use:
```python
from typing import Optional, Tuple

from common import sanitize_log_value
from model import ModelFile
from lftp import LftpError, LftpJobStatusParserError
# No import of Controller or Command — command objects are received as parameters (duck-typed)
# TYPE_CHECKING-only import if type annotations are desired:
# from __future__ import annotations
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from .controller import Controller
```

**Constructor injection pattern** — analog `file_operation_manager.py` lines 31-75:
```python
class FileOperationManager:
    def __init__(self,
                 context: Context,
                 mp_logger: MultiprocessingLogger,
                 force_local_scan_callback: Callable,
                 force_remote_scan_callback: Callable):
        self.__context = context
        self.__mp_logger = mp_logger
        self.logger = context.logger.getChild("FileOperationManager")
        self.__force_local_scan = force_local_scan_callback
        self.__force_remote_scan = force_remote_scan_callback
        ...
```

`CommandProcessor` follows this exactly — receives already-constructed instances, stores them. Key constraint: uses `self.__lftp_manager` (double-underscore is fine WITHIN the collaborator class body because mangling resolves to `_CommandProcessor__lftp_manager`, which is never accessed by tests):
```python
class CommandProcessor:
    def __init__(self,
                 lftp_manager,        # LftpManager instance, already constructed in Controller.__init__
                 file_op_manager,     # FileOperationManager instance, already constructed
                 persist,             # ControllerPersist instance
                 logger):
        self.__lftp_manager = lftp_manager
        self.__file_op_manager = file_op_manager
        self.__persist = persist
        self.logger = logger.getChild("CommandProcessor")
```

**Core pattern — handle methods return (success, msg, code) tuple:**
Source: `controller.py` lines 1009–1097. These four methods have NO lock acquisition — they run after `__process_commands` releases `__model_lock`. They take `(file: ModelFile, command)` and return `(bool, Optional[str], Optional[int])`.

```python
# controller.py lines 1009-1022 — the QUEUE handle (moves to CommandProcessor)
def __handle_queue_command(self, file: ModelFile, command: Command) -> (bool, str, int):
    if file.remote_size is None:
        return False, "File '{}' does not exist remotely".format(command.filename), 404
    try:
        self.__lftp_manager.queue(file.name, file.is_dir)
        self.__persist.stopped_file_names.discard(file.name)
        return True, None, None
    except LftpError as e:
        return False, "Lftp error: {}".format(str(e)), 500
```

In `CommandProcessor` these become `_handle_queue`, `_handle_stop`, `_handle_extract`, `_handle_delete` (single-underscore, public within package). A top-level `handle(file, command) -> Tuple[bool, Optional[str], Optional[int]]` method routes by `command.action.name` or `command.action` value without importing `Controller.Command.Action` by name (compare values via the enum object passed in as a parameter attribute — no import needed).

**CWE-117 pattern** — `sanitize_log_value` must travel with any log call that touches `command.filename`:
```python
# controller.py line 1104 — log-injection guard (must copy into collaborator)
self.logger.warning("Command failed. {}".format(sanitize_log_value(_msg)))
```

**What stays on Controller (NOT moved to CommandProcessor):**
- `controller.py` lines 1099–1141 — `__process_commands` entire body: the queue drain loop, the `with self.__model_lock:` model lookup, and the `_notify_failure` closure. This method stays on `Controller` because tests call `c._Controller__process_commands()` directly (`test_controller.py:279,311`).
- The delegation from `__process_commands` calls `self.__command_processor.handle(file, command)` after the lock is released.

---

### `src/python/controller/auto_delete_manager.py` (collaborator, event-driven)

**Analog:** `src/python/controller/webhook_manager.py`

**Rationale for analog:** `WebhookManager` is the tightest structural match: single-`__init__`-injected `context`, stores state as `self.__` attributes, exposes a narrow public API (`enqueue_import`, `process`), has a thread-safety docstring on the class explaining which thread calls which method, and contains CWE-117 `sanitize_log_value` guards. `AutoDeleteManager` follows the same shape but receives injected lock objects (stored under single-underscore to avoid mangling conflicts — the critical constraint absent from `WebhookManager` since it has no injected locks).

**Imports pattern** — analog `webhook_manager.py` lines 1-4:
```python
from queue import Queue, Empty
from typing import Dict, List, Tuple

from common import Context, sanitize_log_value
```

For `auto_delete_manager.py`:
```python
import collections
import os
from typing import Optional, Set

from common import sanitize_log_value
from model import ModelFile, ModelError
# No import from controller.py (would be a circular import)
```

**Module-level constants that MOVE from `controller.py` to `auto_delete_manager.py`:**

Source: `controller.py` lines 30-45:
```python
# controller.py lines 30-45 — these constants MOVE to auto_delete_manager.py
_VIDEO_EXTENSIONS = frozenset({
    '.mkv', '.mp4', '.avi', '.m4v', '.mov',
    '.ts', '.wmv', '.flv', '.webm',
})
_AUTO_DELETE_BFS_NODE_LIMIT = 10_000
```

These are only used by `__execute_auto_delete` (which stays on Controller as a thin wrapper but delegates BFS+coverage logic into the collaborator). No test references them by module path, so moving them is safe.

**Constructor injection with single-underscore lock storage** — the CRITICAL constraint:

Analog `webhook_manager.py` lines 20-23 (simple injection, no locks):
```python
def __init__(self, context: Context):
    self.__context = context
    self.logger = context.logger.getChild("WebhookManager")
    self.__import_queue = Queue()
```

`AutoDeleteManager` adds injected lock objects. The constraint (RESEARCH.md Pattern 3 anti-pattern): injected locks MUST be stored as `self._model_lock`, NOT `self.__model_lock`. Double-underscore on an injected attribute inside `class AutoDeleteManager` would mangle to `_AutoDeleteManager__model_lock`, a completely different attribute from `_Controller__model_lock`. Single-underscore preserves identity:

```python
class AutoDeleteManager:
    """
    BFS pack-guard and coverage-check logic for the auto-delete lifecycle.

    Thread-safety: All methods that access model state expect the caller
    (Controller.__execute_auto_delete) to hold __model_lock for the duration
    of the call. This class does NOT acquire any lock — lock acquisition
    and release is managed by Controller to preserve the documented WR-02
    lock-ordering invariant (model_lock THEN auto_delete_lock).
    """
    def __init__(self,
                 context,
                 persist,
                 file_op_manager,
                 logger):
        self._context = context
        self._persist = persist
        self._file_op_manager = file_op_manager
        self.logger = logger.getChild("AutoDeleteManager")
        # Note: no lock objects injected here — Controller.__execute_auto_delete
        # controls all lock acquisition/release; this collaborator only receives
        # the data it needs to execute BFS + coverage logic.
```

**Core pattern — BFS + coverage logic (caller holds `__model_lock`):**

Source: `controller.py` lines 904–980 (the BFS body inside `with self.__model_lock:` in `__execute_auto_delete`). This block moves to a `run_bfs_and_coverage(file, file_name) -> Tuple[bool, str, set]` method that returns `(skip, reason, on_disk_videos)`:

```python
# controller.py lines 911-980 — BFS traversal and coverage guard
# This logic moves to AutoDeleteManager.run_bfs_and_coverage()
# Caller MUST hold __model_lock for duration of this call.
on_disk_videos = set()
if file.is_dir:
    unsafe_child = None
    frontier = collections.deque(file.get_children())
    nodes_visited = 0
    while frontier:
        nodes_visited += 1
        if nodes_visited > _AUTO_DELETE_BFS_NODE_LIMIT:
            self.logger.warning(
                "Auto-delete skipped for '{}': BFS node limit ({}) exceeded".format(...)
            )
            self.__persist.imported_children.pop(file_name, None)
            return
        child = frontier.popleft()
        if child.state not in deletable_states:
            unsafe_child = child
            break
        grandchildren = child.get_children()
        if not child.is_dir:
            ext = os.path.splitext(child.name)[1].lower()
            if ext in _VIDEO_EXTENSIONS:
                on_disk_videos.add(child.name.lower())
        frontier.extend(grandchildren)
    if unsafe_child is not None:
        ...
        return
    # Coverage guard...
    imported_child_bset = self.__persist.imported_children.get(file_name)
    if imported_child_bset is not None:
        ...
```

**What stays on Controller (NOT moved to AutoDeleteManager):**

Per RESEARCH.md field/method inventory — all of the following MUST stay on `Controller` because tests access them via `_Controller__` mangling:

- `__schedule_auto_delete` (lines 823–838): tests call `self.controller._Controller__schedule_auto_delete(...)` at `test_auto_delete.py:43,50,56,58,66,67` and `test_controller.py:369,786`. The `threading.Timer` callback is `self.__execute_auto_delete` — if this moved to a collaborator, the timer would fire the collaborator's method, not the Controller's, breaking `_Controller__execute_auto_delete` calls in 30+ test locations.
- `__execute_auto_delete` (lines 840–1007): called directly by tests at `test_auto_delete.py:89,98,106,115,...`. Stays on Controller as the lock-management harness. It acquires `__auto_delete_lock`, then `__model_lock`, calls `self.__auto_delete_mgr.run_bfs_and_coverage(file, file_name)` for the BFS portion, then handles the WR-02 final commit (`with self.__auto_delete_lock: self.__persist.imported_children.pop(...)`) inside `with self.__model_lock:`, then calls `self.__file_op_manager.delete_local(file)` OUTSIDE all locks.
- `__pending_auto_deletes` (dict): tests read/write it at `test_auto_delete.py:28–70,135,146,...`.
- `__auto_delete_lock`, `__shutdown_event`: tests replace them at `test_controller.py:343,345`.

**WR-02 lock-ordering docstring** — MUST travel with `__execute_auto_delete` when that method's inline comment block (`controller.py:982–997`) is written. It cannot be split from the code it documents:
```python
# controller.py lines 982-997 — this docstring block MUST stay with __execute_auto_delete on Controller
# Final commit: serialize BOTH against exit()'s shutdown signal AND the
# webhook path's add_imported_child. Lock order is __model_lock THEN
# __auto_delete_lock (exit() takes ONLY __auto_delete_lock and never
# __model_lock, so this ordering cannot deadlock). The pop runs under
# __model_lock so it is mutually exclusive with add_imported_child
# (controller.py:804), which also mutates imported_children under
# __model_lock. The shutdown re-check stays under __auto_delete_lock so
# it remains ordered against exit()'s __shutdown_event.set()...
```

---

### `src/python/controller/model_pipeline.py` (collaborator, batch/transform)

**Analog:** `src/python/controller/scan_manager.py`

**Rationale for analog:** `ScanManager` is the closest match for a multi-component orchestration collaborator: it manages several sub-components (`__active_scan_process`, `__local_scan_process`, `__remote_scan_process`), has a rich class docstring listing its responsibilities, stores context/logger under `self.__context` / `self.logger`, exposes single-purpose methods named for what they collect/update, and has a thread-safety docstring on the class. `ModelPipeline` orchestrates the analogous multi-stage data-collection pipeline (`_collect_scan_results` → `_feed_model_builder` → `_build_and_apply_model`) with the same `ScanManager`-style "one method per pipeline stage" decomposition.

**Imports pattern** — analog `scan_manager.py` lines 1-4:
```python
from typing import List, Optional, Tuple

from common import Context, MultiprocessingLogger, AppError
from .scan import ScannerProcess, ScannerResult, ActiveScanner, LocalScanner, RemoteScanner
```

For `model_pipeline.py`:
```python
import copy
from typing import List, Optional, Tuple

from common import Context, sanitize_log_value
from model import ModelError, ModelFile, Model, ModelDiff, ModelDiffUtil
from lftp import LftpJobStatus
from .extract import ExtractStatusResult, ExtractCompletedResult
from .scan import ScannerResult
# No import from controller.py — avoids circular import.
# _should_update_capacity is either duplicated as a module-level function
# or ModelPipeline._update_controller_status is kept on Controller (see Open Question 2 in RESEARCH.md).
```

**Constructor injection pattern** — analog `scan_manager.py` lines 29-82:
```python
class ScanManager:
    def __init__(self,
                 context: Context,
                 mp_logger: MultiprocessingLogger):
        self.__context = context
        self.logger = context.logger.getChild("ScanManager")
        ...
        self.__active_scanner = ActiveScanner(context.config.lftp.local_path)
        ...
        self.__started = False
```

`ModelPipeline` receives already-constructed manager instances (CRITICAL: NOT constructed inside this class — see D-05 / RESEARCH.md Pitfall 2):
```python
class ModelPipeline:
    """
    Orchestrates the scan→build→diff→apply model update pipeline.

    Responsible for:
    - Collecting scan results, LFTP status, extract results
    - Feeding the model builder with collected data
    - Building and applying model diffs
    - Tracking downloading and downloaded files in persist
    - Pruning stale tracking entries

    Thread-safety: _build_and_apply_model acquires model_lock (the same
    Lock object owned by Controller) for all model mutations. No other
    lock is acquired by this collaborator.
    """
    def __init__(self,
                 context,
                 persist,
                 model,
                 model_lock,      # SAME Lock object as Controller.__model_lock — stored as _model_lock
                 model_builder,   # ModelBuilder instance already constructed in Controller.__init__
                 scan_manager,    # ScanManager instance already constructed in Controller.__init__
                 lftp_manager,    # LftpManager instance already constructed in Controller.__init__
                 file_op_manager, # FileOperationManager instance already constructed in Controller.__init__
                 logger):
        self._context = context
        self._persist = persist
        self._model = model
        self._model_lock = model_lock    # single-underscore: avoids _ModelPipeline__model_lock mangling
        self._model_builder = model_builder
        self._scan_manager = scan_manager
        self._lftp_manager = lftp_manager
        self._file_op_manager = file_op_manager
        self.logger = logger.getChild("ModelPipeline")
```

**Core pattern — pipeline orchestration:** The `update_model()` public method mirrors the body of `Controller.__update_model` (lines 708–743). The coordinator's `__update_model` becomes a one-line thin wrapper:

```python
# controller.py lines 708-743 — __update_model stays on Controller as thin wrapper
def __update_model(self):
    self.__model_pipeline.update_model()

# model_pipeline.py — update_model() implements all the steps
def update_model(self) -> None:
    """
    Advance the model state by collecting data from all sources and updating accordingly.
    Steps: collect → track active files → feed builder → build/apply → update status.
    """
    latest_remote_scan, latest_local_scan, latest_active_scan = self._collect_scan_results()
    lftp_statuses = self._collect_lftp_status()
    latest_extract_statuses, latest_extracted_results = self._collect_extract_results()
    self._update_active_file_tracking(lftp_statuses, latest_extract_statuses)
    self._feed_model_builder(
        latest_remote_scan, latest_local_scan, latest_active_scan,
        lftp_statuses, latest_extract_statuses, latest_extracted_results
    )
    self._build_and_apply_model(latest_remote_scan)
    self._update_controller_status(latest_remote_scan, latest_local_scan)
```

**_build_and_apply_model lock pattern** — analog `scan_manager.py` does not acquire locks (scanners communicate via multiprocessing queues). For `ModelPipeline`, the lock comes from the injected `_model_lock`:

Source: `controller.py` lines 616–655 (the WITH block pattern):
```python
# controller.py lines 645-655 — lock pattern to copy into ModelPipeline._build_and_apply_model
with self.__model_lock:          # in ModelPipeline: with self._model_lock:
    model_diff = ModelDiffUtil.diff_models(self.__model, new_model)
    self._apply_model_diff(model_diff)
    self._prune_extracted_files()
    self._prune_downloaded_files(latest_remote_scan)
```

**`_set_import_status` pattern** — uses protected access on `ModelFile`:
Source: `controller.py` lines 374–400:
```python
# controller.py lines 383-400 — intentional protected access comment MUST travel with this method
new_file._unfreeze()  # intentional protected access: controller owns the freeze lifecycle
```

**What stays on Controller (NOT moved to ModelPipeline):**

- `__update_model` as a thin wrapper calling `self.__model_pipeline.update_model()` — tests do not call `__update_model` directly (no `_Controller__update_model` in test grep), but it is called from `process()` which is the public API; the coordinator retains it as the delegation point.
- `__check_webhook_imports` (lines 745–821): tests call `c._Controller__check_webhook_imports()` at `test_controller.py:214,242`. MUST stay on Controller as a `def __check_webhook_imports` method. Logic may remain on the coordinator entirely (RESEARCH.md Open Question 1 recommendation) or be partially delegated to `ModelPipeline` — but the `def __check_webhook_imports(self):` entry point stays on `Controller`.
- `_should_update_capacity` (lines 657–669): tests call `Controller._should_update_capacity(...)` as a static method (`test_controller.py:14–41`). MUST stay as `@staticmethod` on `Controller`. If `_update_controller_status` moves to `ModelPipeline`, it must call the static method as `Controller._should_update_capacity(...)` requiring an import, which creates a circular import. **Recommended resolution** (RESEARCH.md Open Question 2): keep `_update_controller_status` AND `_should_update_capacity` both on the coordinator (30 lines total), or duplicate the 5-line static as a module-level function in `model_pipeline.py` and keep the original on `Controller`.
- `__active_downloading_file_names` (line 146): tests access `_Controller__active_downloading_file_names` at `test_controller_unit.py:853,861,864,867`. MUST stay on `Controller`. However, `_update_active_file_tracking` writes to `self.__active_downloading_file_names` directly. **Resolution**: keep `_update_active_file_tracking` on the coordinator, OR have `ModelPipeline` return the new list and let the coordinator assign it. The former is simpler (fewer parameters).

---

## Shared Patterns

### Construction of Manager Instances (D-05 / RESEARCH.md Pitfall 2)

**Source:** `src/python/controller/controller.py` lines 119–143
**Apply to:** ALL three new collaborators
**Rule:** `ModelBuilder`, `LftpManager`, `ScanManager`, `FileOperationManager`, `MultiprocessingLogger`, `MemoryMonitor` are constructed ONLY inside `Controller.__init__`. Collaborators receive already-constructed instances as constructor arguments.

```python
# controller.py lines 119-143 — the construction site that MUST remain here
self.__model_builder = ModelBuilder()
self.__model_builder.set_base_logger(self.logger)
...
self.__lftp_manager = LftpManager(context=self.__context)
self.__scan_manager = ScanManager(context=self.__context, mp_logger=self.__mp_logger)
self.__file_op_manager = FileOperationManager(
    context=self.__context,
    mp_logger=self.__mp_logger,
    force_local_scan_callback=self.__scan_manager.force_local_scan,
    force_remote_scan_callback=self.__scan_manager.force_remote_scan
)
```

### Lock Injection (D-03 / RESEARCH.md Pitfall 3)

**Source:** `src/python/controller/controller.py` lines 117, 191–198
**Apply to:** `auto_delete_manager.py`, `model_pipeline.py`
**Rule:** Injected lock objects are stored as `self._lock_name` (single-underscore), never `self.__lock_name` (double-underscore). Lock identity (`is`) must be preserved — no new `threading.Lock()` inside collaborators.

```python
# controller.py lines 117, 191-198 — lock objects owned by Controller, passed by reference
self.__model_lock = Lock()
self.__auto_delete_lock = threading.Lock()
self.__shutdown_event = threading.Event()

# In collaborator constructors — single-underscore storage
self._model_lock = model_lock           # IS self.controller._Controller__model_lock
self._auto_delete_lock = auto_delete_lock  # IS self.controller._Controller__auto_delete_lock
```

### Logger Child Pattern

**Source:** All five existing collaborator files
**Apply to:** All three new collaborators

```python
# Pattern consistent across scan_manager.py:40, lftp_manager.py:30, file_operation_manager.py:47,
# webhook_manager.py:22 — child logger named after the class
self.logger = context.logger.getChild("ScanManager")    # scan_manager.py:40
self.logger = context.logger.getChild("LftpManager")    # lftp_manager.py:30
self.logger = context.logger.getChild("FileOperationManager")  # file_operation_manager.py:47
self.logger = context.logger.getChild("WebhookManager") # webhook_manager.py:22
```

New collaborators follow the same convention:
```python
self.logger = logger.getChild("CommandProcessor")
self.logger = logger.getChild("AutoDeleteManager")
self.logger = logger.getChild("ModelPipeline")
```

Note: `MemoryMonitor` uses `logging.getLogger("MemoryMonitor")` with a separate `set_base_logger` method (lines 51-52) — that is the exception, not the rule. New collaborators use the child-logger convention.

### CWE-117 Log Injection Guards

**Source:** `src/python/controller/webhook_manager.py` lines 37, 76; `src/python/controller/controller.py` lines 837, 863, 899, etc.
**Apply to:** All three new collaborators — any log statement where a string comes from `command.filename`, `file_name`, or `file.name` (user-supplied or webhook-supplied values)

```python
# webhook_manager.py lines 37 and 76 — the guard pattern
safe_file_name = sanitize_log_value(file_name)
self.logger.info("{} webhook import enqueued: '{}'".format(source, safe_file_name))
```

```python
# controller.py line 1104 — in __process_commands, must copy into CommandProcessor
self.logger.warning("Command failed. {}".format(sanitize_log_value(_msg)))
```

### Thread-Safety Docstrings (CONTEXT.md specifics)

**Source:** `src/python/controller/controller.py` lines 229–244 (exit() lock-ordering note), 982–997 (WR-02 TOCTOU block), 823–833 ("runs outside the lock" note)
**Apply to:** `auto_delete_manager.py` and `controller.py` (modified coordinator)
**Rule:** Every multi-line thread-safety docstring MUST travel WITH the code block it documents. These are load-bearing institutional memory, not decorative comments. The WR-02 block at lines 982–997 in particular documents the `__model_lock` THEN `__auto_delete_lock` nested acquisition ordering and must appear on the `__execute_auto_delete` method body on the coordinator.

---

## No Analog Found

No new files fall into the "no analog" category. All three collaborators have clear structural analogs within `src/python/controller/`.

---

## Metadata

**Analog search scope:** `src/python/controller/` (all existing collaborators: `scan_manager.py`, `lftp_manager.py`, `file_operation_manager.py`, `webhook_manager.py`, `memory_monitor.py`)
**Files scanned:** 7 (5 existing collaborators + `controller.py` + `controller.py` seam sections)
**Pattern extraction date:** 2026-06-01

**Key constraint cross-reference:**
- Name-mangling inventory → RESEARCH.md "Complete Field Inventory" section
- mock.patch binding rule → RESEARCH.md "mock.patch Binding-Site Rule"
- WR-02 lock ordering → RESEARCH.md "Thread-Safety Landmines — `__execute_auto_delete`"
- Circular import avoidance → RESEARCH.md "Circular-Import Risk Analysis"
