# Phase 109: Controller Decomposition - Research

**Researched:** 2026-06-01
**Domain:** Python refactoring — god-class decomposition, mock.patch binding semantics, Python name-mangling across class boundaries
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01/D-02:** Three new collaborator modules — `command_processor.py`, `auto_delete_manager.py`, `model_pipeline.py` — plus `controller.py` retained as thin coordinator. Exact method assignment per seam map below.
- **D-03/D-04:** `Controller` retains ownership of `__model_lock`, `__auto_delete_lock`, `__shutdown_event`; collaborators receive the SAME lock objects via constructor injection. No new lock, no new acquisition ordering.
- **D-05:** Patch targets `controller.controller.{ModelBuilder,LftpManager,ScanManager,FileOperationManager,MultiprocessingLogger,MemoryMonitor}` must remain resolvable in `controller.controller` after the refactor. No test file is modified.
- **D-06:** Three sequential plans — 109-01 (command_processor), 109-02 (auto_delete_manager), 109-03 (model_pipeline) — each gated on the full Python suite.

### Claude's Discretion

- Exact module/class names (`command_processor` vs `command_dispatcher`, `model_pipeline` vs `model_coordinator`) and whether collaborators are classes vs module-level functions.
- Whether the `Command` inner class moves to `command_processor.py` or stays nested on `Controller`.
- How collaborators receive their dependencies (constructor injection vs. small context object) so long as injected locks are the same objects and no patch target breaks.
- Whether `__check_webhook_imports` lands in `model_pipeline` or stays on the coordinator.

### Deferred Ideas (OUT OF SCOPE)

- Mutable model state / freeze-contract fix (ModelFile._unfreeze pattern).
- Bulk command timeout / cancellation support.
- Model event coalescing / busy-poll removal.
- Full single+bulk dispatch unification.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARCH-01 | Controller god-class decomposed into cohesive collaborators; public surface frozen; existing test suite stays green unmodified; thread-safety invariants preserved; CI green; `fail_under >= 88` holds. | Full analysis below covers: exact method-to-collaborator mapping, name-mangling constraint, mock.patch binding rule, lock-ordering invariants, regression-gate command. |
</phase_requirements>

---

## Summary

`src/python/controller/controller.py` is 1151 lines across three seams: command dispatch (`:1009–1151`), auto-delete lifecycle (`:823–1007`), and model/scan pipeline (`:342–822`). The coordinator facade (constructor, lifecycle, read-accessors) occupies roughly `:95–341`. All three planned collaborators must be classes rather than module-level functions because the test suite extensively accesses their state through Python name-mangling via the `controller` variable — `self.controller._Controller__pending_auto_deletes`, `self.controller._Controller__execute_auto_delete(...)`, `self.controller._Controller__model`, etc. If a method moves to a collaborator class, the mangling prefix becomes the collaborator class name (e.g. `_AutoDeleteManager__pending_auto_deletes`), which breaks every test that accesses those attributes through `_Controller__`.

**The single most important implementation constraint:** All private state and method calls tested by name-mangling MUST remain on the `Controller` class — meaning the coordinator does NOT merely delegate; it keeps owning all private fields and the mangled private methods. The collaborators implement the logic; the coordinator keeps the private fields and re-exposes the methods as thin wrappers if and only if tests call them via `self.controller._Controller__X(...)`.

**Primary recommendation:** Use a "method-forwarding" pattern where the coordinator retains all `__private` methods and fields referenced by tests via mangling, and the collaborator is instantiated internally to handle logic that is NOT directly called via `_Controller__` in any test.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Command queue dispatch | Controller (coordinator) owns `__command_queue`, `__process_commands`; CommandProcessor implements handle logic | — | Tests access `_Controller__command_queue` and call `_Controller__process_commands()` directly |
| Auto-delete lifecycle | Controller (coordinator) owns `__pending_auto_deletes`, `__auto_delete_lock`, `__shutdown_event`, `__schedule_auto_delete`, `__execute_auto_delete`; AutoDeleteManager implements BFS+coverage logic | — | Tests access ALL of these via `_Controller__` mangling |
| Model/scan pipeline | Controller (coordinator) owns `__model`, `__model_builder`, `__active_downloading_file_names`, `_update_controller_status`; ModelPipeline implements pipeline orchestration | — | Tests access `_Controller__model`, `_Controller__active_downloading_file_names` |
| Model read accessors | Controller (coordinator) | — | Web layer calls these; must stay on Controller |
| Lock ownership | Controller (coordinator) | — | D-03: locks created in Controller.__init__, injected to collaborators |

---

## Standard Stack

No new external packages are introduced. This is a pure code-structure refactor within the existing `controller/` package.

### Existing Dependency Inventory (relevant to the refactor)

| Module | Currently used in controller.py | Stays in coordinator? |
|--------|----------------------------------|-----------------------|
| `threading.Lock`, `threading.Timer`, `threading.Event` | Yes | Yes (lock objects stay on Controller) |
| `queue.Queue` | `__command_queue` | Yes (owned by Controller) |
| `collections.deque` | Auto-delete BFS | Moves with BFS logic to auto_delete_manager |
| `os.path.splitext` | Auto-delete video extension check | Moves with BFS logic |
| `copy.copy` | `_set_import_status` | Moves with model_pipeline |
| `enum.Enum` | `Command.Action` | Stays on Controller (inner class) |

---

## Package Legitimacy Audit

No external packages installed. Not applicable.

---

## Architecture Patterns

### Python Name-Mangling — The Critical Constraint

Python name-mangling transforms `self.__foo` in class `Foo` to `self._Foo__foo` at compile time. This mangling is based on the **class in which the method is textually defined**, not on the instance type. Two consequences:

1. A method defined in `class CommandProcessor` that accesses `self.__model_lock` will mangle to `_CommandProcessor__model_lock`, which does NOT exist on the injected lock attribute name. You must NOT use `self.__model_lock` inside a collaborator — you use whatever name the collaborator stores the injected lock under.

2. Tests that call `self.controller._Controller__execute_auto_delete(...)` are calling a method **by its mangled name on the Controller instance**. If `__execute_auto_delete` is moved to `AutoDeleteManager`, `self.controller._Controller__execute_auto_delete` no longer exists, and the test raises `AttributeError`.

**The solution is not to move `__private` methods that tests call by mangled name.** Instead, the coordinator keeps a thin `__execute_auto_delete` that calls into the collaborator, OR the collaborator logic is incorporated as a non-dunder helper that the private method on Controller calls. The former is lower risk.

### mock.patch Binding-Site Rule (D-05)

`patch('controller.controller.ScanManager')` replaces the `ScanManager` name **in the `controller.controller` module namespace** at the time `patch` is applied. The patch resolves at the point where Python did `from .scan_manager import ScanManager` into `controller.controller`. After patch, any code in `controller.controller` that calls `ScanManager(...)` will call the mock.

**The rule for the refactor:**

If a collaborator (e.g. `ModelPipeline`) is constructed inside `Controller.__init__` and `ModelPipeline.__init__` calls `ScanManager(...)`, the patch on `controller.controller.ScanManager` has NO effect because the call to `ScanManager` happens inside `model_pipeline.py`, not inside `controller.controller`. The test will receive a real `ScanManager`, not the mock, and the test will break or hang.

**Concrete rule the planner must encode:**

> The six manager classes — `ModelBuilder`, `LftpManager`, `ScanManager`, `FileOperationManager`, `MultiprocessingLogger`, `MemoryMonitor` — must continue to be **constructed inside `Controller.__init__` in `controller.py`**, not inside any collaborator. The coordinator instantiates them, holds them as `self.__model_builder`, `self.__lftp_manager`, etc., and passes the already-constructed instances to collaborators as constructor arguments (or the collaborator receives them by reference via the coordinator). This is the pattern already used by `FileOperationManager` (receives `force_local_scan_callback` from the coordinator) and is the template for the three new collaborators.

Verified: `base.py:18–21` patches six names. `test_auto_delete.py` and `test_controller_unit.py` both call `self.controller._Controller__execute_auto_delete(...)` and `self.controller._Controller__schedule_auto_delete(...)` extensively — those two methods must stay on `Controller`. [VERIFIED: direct inspection of test files]

### Recommended Project Structure

```
src/python/controller/
├── __init__.py           (unchanged — frozen public surface)
├── controller.py         (coordinator facade, thinned to ~350 lines)
├── command_processor.py  (NEW — handle_*_command logic, no __private state)
├── auto_delete_manager.py (NEW — BFS+coverage logic, no __private state)
├── model_pipeline.py     (NEW — scan→build→diff→apply orchestration)
├── scan_manager.py       (existing, unchanged)
├── lftp_manager.py       (existing, unchanged)
├── file_operation_manager.py (existing, unchanged)
├── model_builder.py      (existing, unchanged)
├── webhook_manager.py    (existing, unchanged)
├── memory_monitor.py     (existing, unchanged)
├── controller_persist.py (existing, unchanged)
└── auto_queue.py         (existing, unchanged)
```

### Pattern 1: Collaborator as Logic Container (No Mangled State)

The existing collaborators (`ScanManager`, `LftpManager`, `FileOperationManager`) do NOT hold any state that Controller tests reference via `_Controller__` mangling. They hold their own private state under their own class prefix. The three new collaborators must follow the same pattern: they hold NO state that is accessed by the test suite via `_Controller__` mangling.

```python
# Source: existing scan_manager.py and lftp_manager.py pattern
class CommandProcessor:
    def __init__(self,
                 context: Context,
                 persist: ControllerPersist,
                 lftp_manager: LftpManager,
                 file_op_manager: FileOperationManager,
                 model: Model,
                 model_lock: Lock):
        self.__context = context
        self.__persist = persist
        self.__lftp_manager = lftp_manager
        self.__file_op_manager = file_op_manager
        self.__model = model
        self.__model_lock = model_lock
        self.logger = context.logger.getChild("CommandProcessor")

    def handle_queue(self, file: ModelFile, command) -> tuple:
        """Extracted handle_queue_command logic."""
        ...
```

Notice: no `__command_queue` (that stays on `Controller`), no `__pending_auto_deletes` (that stays on `Controller`). The collaborator receives only what it needs to execute its logic.

### Pattern 2: Coordinator Keeps All Mangled State and Methods Called by Tests

```python
# controller.py — what stays UNCHANGED
class Controller:
    def __init__(self, ...):
        # All private fields stay here
        self.__command_queue = Queue()          # tested via _Controller__command_queue
        self.__model = Model()                  # tested via _Controller__model
        self.__model_lock = Lock()              # tested via _Controller__model_lock
        self.__active_downloading_file_names = []  # tested via _Controller__active_downloading_file_names
        self.__pending_auto_deletes = {}        # tested via _Controller__pending_auto_deletes
        self.__auto_delete_lock = threading.Lock()  # tested via _Controller__auto_delete_lock
        self.__shutdown_event = threading.Event()   # tested via _Controller__shutdown_event

        # Manager instances — constructed HERE so patch() targets in controller.controller still fire
        self.__model_builder = ModelBuilder()   # patched as controller.controller.ModelBuilder
        self.__lftp_manager = LftpManager(...)  # patched as controller.controller.LftpManager
        self.__scan_manager = ScanManager(...)  # patched as controller.controller.ScanManager
        self.__file_op_manager = FileOperationManager(...)  # patched as controller.controller.FileOperationManager
        self.__mp_logger = MultiprocessingLogger(...)       # patched as controller.controller.MultiprocessingLogger
        self.__memory_monitor = MemoryMonitor()             # patched as controller.controller.MemoryMonitor

        # NEW: create collaborators, inject already-constructed managers
        self.__command_processor = CommandProcessor(
            lftp_manager=self.__lftp_manager,
            file_op_manager=self.__file_op_manager,
            persist=self.__persist,
            logger=self.logger,
        )
        self.__auto_delete_mgr = AutoDeleteManager(
            context=self.__context,
            persist=self.__persist,
            model=self.__model,
            model_lock=self.__model_lock,
            auto_delete_lock=self.__auto_delete_lock,
            shutdown_event=self.__shutdown_event,
            file_op_manager=self.__file_op_manager,
            logger=self.logger,
        )
        self.__model_pipeline = ModelPipeline(
            context=self.__context,
            persist=self.__persist,
            model=self.__model,
            model_lock=self.__model_lock,
            model_builder=self.__model_builder,
            scan_manager=self.__scan_manager,
            lftp_manager=self.__lftp_manager,
            file_op_manager=self.__file_op_manager,
            webhook_manager=self.__webhook_manager,
            logger=self.logger,
        )

    # These __private methods STAY on Controller because tests call them by mangled name:
    def __process_commands(self):
        # Thin wrapper: get file from model under lock (stays here), then delegate to CommandProcessor
        ...

    def __schedule_auto_delete(self, file_name: str):
        # Thin wrapper: manages __pending_auto_deletes (stays here), delegates timer logic
        ...

    def __execute_auto_delete(self, file_name: str):
        # Thin wrapper: manages __pending_auto_deletes, __shutdown_event (stays here),
        # delegates BFS+coverage logic to AutoDeleteManager
        ...

    def __update_model(self):
        # Thin wrapper: calls self.__model_pipeline.update_model(...)
        ...

    def __check_webhook_imports(self):
        # Thin wrapper: delegates to self.__model_pipeline.check_webhook_imports(...)
        ...
```

### Anti-Patterns to Avoid

- **Moving `__private` methods that tests call by mangled name:** `self.controller._Controller__execute_auto_delete(...)` and `self.controller._Controller__schedule_auto_delete(...)` are called in 30+ test locations. Renaming the class prefix breaks all of them.
- **Constructing managers inside collaborators:** `CommandProcessor.__init__` must NOT call `ScanManager(...)`. Only `Controller.__init__` may construct manager classes, to preserve patch binding.
- **Adding `__` prefixes to injected lock attributes inside collaborators:** A collaborator that stores `self.__model_lock = model_lock` in class `AutoDeleteManager` makes `self._AutoDeleteManager__model_lock`; use a non-dunder name like `self._model_lock` instead.
- **Creating a new lock inside a collaborator:** D-03 is explicit — no new lock objects.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe lock injection | Custom synchronized wrapper | Pass the same `Lock` object directly | Identity equality (`is`) must hold between coordinator and collaborator for test assertions like `self.controller._Controller__model_lock.locked()` |
| Command dispatch routing | New dispatcher class with its own queue | Keep `__command_queue` on Controller, delegate only the `__handle_*` methods | Tests verify `_Controller__command_queue.qsize()` |
| Circular import avoidance | Separate `_types.py` module | Keep `Command`, `Action`, `ControllerError` on `Controller`; collaborators receive `Command` instances as parameters | No test imports from a `_types` module; all imports from `controller.controller` |

---

## Complete Field Inventory: What Stays on Controller vs. Moves

### Fields that MUST stay on Controller (accessed by tests via `_Controller__` mangling)

| Field | Test file | Access pattern |
|-------|-----------|---------------|
| `__command_queue` | `test_controller_unit.py:140`, `test_controller.py:260,277` | `_Controller__command_queue.qsize()`, `.put(cmd)` |
| `__model` | `base.py:75`, `test_controller_unit.py:795–828`, `test_auto_delete.py:87,96,...`, `test_controller.py:183,261` | `.add_file()`, `.get_file()`, `.get_file_names()`, `.update_file`, replacement assignment |
| `__model_lock` | `test_auto_delete.py:157,171,877,924`, `test_controller.py:185,262,350` | `.locked()`, assignment replacement |
| `__active_downloading_file_names` | `test_controller_unit.py:853,861,864,867` | direct read and assignment |
| `__pending_auto_deletes` | `test_auto_delete.py:28–70,135,146,...`, `test_controller.py:344,372,393,432,439` | dict read/write/clear, value count |
| `__auto_delete_lock` | `test_controller.py:343` | assignment replacement |
| `__shutdown_event` | `test_auto_delete.py:662,709`, `test_controller.py:345` | `.set()`, assignment replacement |
| `__started` | `base.py:58`, `test_auto_delete.py:412,420,433,791`, `test_controller.py:346` | assignment (`_Controller__started = True`) |
| `__persist` | `test_auto_delete.py:385`, `test_controller.py:191,351` | assignment replacement |
| `__context` | `test_controller.py:50,179,257,340` | assignment replacement |
| `__webhook_manager` | `test_controller.py:194,210,238` | assignment and method mock |
| `__file_op_manager` | `test_controller.py:352,188` | assignment replacement |
| `__lftp_manager` | `integration/test_controller.py:906–2306` | `._Controller__lftp_manager.lftp.rate_limit` |
| `__scan_manager` | `test_controller.py:356` | assignment replacement |
| `__mp_logger` | `test_controller.py:357` | assignment replacement |

### Private methods that MUST stay on Controller (called by tests via mangled name)

| Method | Test file | Call pattern |
|--------|-----------|-------------|
| `__execute_auto_delete` | `test_auto_delete.py:89,98,106,115,...` (30+ calls) | `self.controller._Controller__execute_auto_delete("file.mkv")` |
| `__schedule_auto_delete` | `test_auto_delete.py:43,50,56,58,66,67`, `test_controller.py:369,786` | `self.controller._Controller__schedule_auto_delete("file.mkv")` |
| `__process_commands` | `test_controller.py:279,311` | `c._Controller__process_commands()` |
| `__check_webhook_imports` | `test_controller.py:214,242` | `c._Controller__check_webhook_imports()` |

[VERIFIED: direct grep of entire test directory]

**Conclusion:** `__execute_auto_delete`, `__schedule_auto_delete`, `__process_commands`, and `__check_webhook_imports` CANNOT move to a collaborator class. They must remain as `def __X(self)` methods on `Controller`. The collaborators implement the underlying logic those methods call, but the dunder-private entry points themselves stay on `Controller`.

---

## Thread-Safety Landmines — Method by Method

### `__process_commands` (stays on Controller, `:1099–1141`)

**Locks acquired:** `__model_lock` (held during `self.__model.get_file(command.filename)` lookup only, then released before the handle calls).

**Critical invariant:** The model lock is released BEFORE calling `__handle_queue_command`, `__handle_stop_command`, etc. The file reference (`file`) is a frozen `ModelFile` and is safe to use outside the lock. This is the "release lock before subprocess spawn" pattern — `__handle_delete_command` calls `self.__file_op_manager.delete_local(file)` which spawns a subprocess.

**Risk on move:** None — the handle methods don't re-acquire `__model_lock`, so no re-entrancy issue. The `__command_queue` stays on Controller.

### `__handle_queue_command`, `__handle_stop_command`, `__handle_extract_command`, `__handle_delete_command` (`:1009–1097`)

**Locks acquired:** NONE. These methods run after the model lock is released in `__process_commands`.

**Dependencies:** `self.__lftp_manager`, `self.__file_op_manager`, `self.__persist`. All are straightforward.

**Movement:** These are the methods that CAN safely move to `CommandProcessor`. They receive `(file, command)` as parameters and return `(success, error_msg, error_code)`. The coordinator's `__process_commands` remains on `Controller` as a thin coordinator that does the lock/queue/dispatch scaffolding and calls the collaborator for the actual handle logic.

### `__schedule_auto_delete` (stays on Controller, `:823–838`)

**Locks acquired:** `__auto_delete_lock` (for the entire body — cancel old timer, create new timer, insert into `__pending_auto_deletes`).

**Must stay on Controller:** `__pending_auto_deletes` is accessed by tests via `_Controller__pending_auto_deletes`. The `threading.Timer` fires `self.__execute_auto_delete` — the callback must be a bound method of `Controller` so the mangled `_Controller__execute_auto_delete` call in tests works.

**Risk on move:** HIGH — if moved, `timer = threading.Timer(delay, self.__execute_auto_delete, ...)` would bind to the collaborator's method and the test's direct invocation via `_Controller__execute_auto_delete` would be a no-op.

### `__execute_auto_delete` (stays on Controller, `:840–1007`)

**Locks acquired (in order):**
1. `__auto_delete_lock` — entry guard (check shutdown, pop from `__pending_auto_deletes`)
2. `__model_lock` — model read + BFS + coverage guard (`:883–997`)
3. `__auto_delete_lock` (re-acquired inside the `with __model_lock` block at `:997`) — WR-02 final commit

**The WR-02 ordering invariant (`:982–997` docstring):**
- Lock order: `__model_lock` THEN `__auto_delete_lock` for the final commit.
- `exit()` takes ONLY `__auto_delete_lock`, never `__model_lock` — no circular wait possible.
- The `pop` of `imported_children` (`:1001`) is inside `__model_lock` so it cannot race `add_imported_child` (`:804`) which is also under `__model_lock`.
- `delete_local` (`:1006`) runs OUTSIDE ALL LOCKS — no lock held during subprocess spawn.

**Must stay on Controller:** Called by tests directly. If the BFS+coverage logic is extracted to `AutoDeleteManager`, `__execute_auto_delete` on Controller calls the collaborator's method. The lock acquisition/release sequence must happen on the Controller side (or be explicitly passed through to the collaborator's method that receives the lock objects as args).

**Safest decomposition:** `__execute_auto_delete` stays on Controller as the lock-management harness. It acquires locks in the correct order and calls `self.__auto_delete_mgr.execute(file_name, file, on_disk_videos, imported_child_bset)` for the BFS + coverage decision, then handles the pop + dispatch itself.

### `__update_model` (`:708–743`)

**Locks acquired:** NONE directly. Delegates to `_build_and_apply_model` which acquires `__model_lock`.

**Movement:** Safe to move to `ModelPipeline`. `__update_model` stays on Controller as a thin wrapper calling `self.__model_pipeline.update_model()`.

### `_build_and_apply_model` (`:616–655`)

**Locks acquired:** `__model_lock` — held for diff, apply, prune operations. Released before method returns.

**Movement:** Safe to move to `ModelPipeline`. The injected `model_lock` is the SAME lock object (D-03), so tests that check `self.controller._Controller__model_lock.locked()` during `update_file` (`:1085`) will still pass because it IS the same lock.

### `__check_webhook_imports` (`:745–821`)

**Locks acquired:** `__model_lock` twice (two narrow windows). `Timer` operations run outside lock.

**Movement:** The test suite calls `c._Controller__check_webhook_imports()` directly (`test_controller.py:214,242`). It MUST stay on Controller as a `__private` method. The logic can be delegated to `ModelPipeline`, but the entry point stays.

---

## Circular-Import Risk Analysis

### The Problem

If `controller.py` imports `CommandProcessor` from `command_processor.py`, and `command_processor.py` imports `ControllerError` or `Controller.Command` from `controller.py`, that is a cycle.

### What Types Are Needed by Collaborators

| Collaborator | Types needed from controller.py |
|-------------|----------------------------------|
| `CommandProcessor` | `Controller.Command` (the command object passed in), `LftpError`, `ModelFile`, `ModelError` |
| `AutoDeleteManager` | `_VIDEO_EXTENSIONS`, `_AUTO_DELETE_BFS_NODE_LIMIT`, `ModelFile`, `ModelError` |
| `ModelPipeline` | `ModelFile`, `ModelDiff`, `ScannerResult`, `LftpJobStatus` |

### Assessment

`Controller.Command` and `ControllerError` are defined in `controller.py`. If `command_processor.py` imports `Controller.Command` from `controller.py`, that IS a cycle.

### Recommendation: Pass `Command` Instances as Parameters, Not as Type Imports

The collaborator's `handle_queue`, `handle_stop`, etc. methods receive `command` as a parameter typed as `Any` or using a forward reference. The `Command` inner class can have a type annotation comment (`# type: Controller.Command`) or use `TYPE_CHECKING`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import Controller
```

This means the import only happens at type-check time (mypy/pyright), not at runtime — no circular import at runtime.

**Lowest-risk option:** Do NOT import `Controller.Command` at all in the collaborator. The collaborator's methods receive the command object and access `.action`, `.filename`, `.callbacks` as plain attribute access (duck typing). Since `Controller.Command` is a simple data class, this works without any import. Python's `isinstance` check against `Controller.Command` is never needed.

For `_VIDEO_EXTENSIONS` and `_AUTO_DELETE_BFS_NODE_LIMIT`: these are module-level constants in `controller.py`. They should be moved to `auto_delete_manager.py` (or `model_pipeline.py` if BFS lives there). No cycle — `controller.py` does NOT import these from the collaborator; the collaborator defines them.

**`ControllerError`:** Must remain defined in `controller.py` because `test_controller_unit.py:4` does `from controller.controller import ControllerError`. Collaborators should NOT define or import `ControllerError`; if a collaborator needs to signal an error, it raises `ValueError` or a collaborator-specific exception that the coordinator catches and re-raises as `ControllerError`.

---

## Common Pitfalls

### Pitfall 1: Renaming a `__private` Method by Moving It to a Collaborator

**What goes wrong:** `__execute_auto_delete` defined in `class AutoDeleteManager` becomes `_AutoDeleteManager__execute_auto_delete`. Every test that calls `self.controller._Controller__execute_auto_delete(...)` raises `AttributeError`.

**Why it happens:** Python name-mangling is compile-time, based on the class body where the `def __x` appears.

**How to avoid:** Keep all `__private` methods called by tests on `Controller`. Collaborators expose `_single_underscore` or `public` methods.

**Warning signs:** Any collaborator method that starts with `__` is almost certainly wrong.

### Pitfall 2: Constructing a Manager Class Inside a Collaborator

**What goes wrong:** `ModelPipeline.__init__` calls `ModelBuilder()`. The test's `patch('controller.controller.ModelBuilder')` has no effect because `ModelBuilder` was not resolved in `controller.controller` at call time.

**Why it happens:** `patch('controller.controller.ModelBuilder')` only intercepts lookups in the `controller.controller` module namespace.

**How to avoid:** All six manager class instantiations stay in `Controller.__init__`. Collaborators receive the already-constructed instances via constructor injection.

**Warning signs:** Any `patch('controller.controller.X')` test that passes before the refactor and fails after is a sign that a collaborator is constructing X.

### Pitfall 3: Lock Identity Broken by Wrapping

**What goes wrong:** Collaborator wraps the injected lock in a `with self._model_lock:` context manager using a different object, or copies the lock.

**Why it happens:** Lock objects are not copyable (contain a `_thread.lock`). Reassignment to a new `Lock()` breaks the "same object" guarantee.

**How to avoid:** Pass `self.__model_lock` directly. Collaborator stores it as `self._model_lock = model_lock`. The test assertion `self.controller._Controller__model_lock.locked()` will be True because `self.controller._Controller__model_lock IS self.__auto_delete_mgr._model_lock` — same object.

**Warning signs:** `threading.Lock()` appearing inside a collaborator's `__init__` or anywhere else is a bug.

### Pitfall 4: Breaking the WR-02 Lock Ordering in auto_delete_manager

**What goes wrong:** The BFS loop and coverage check are moved to a collaborator method, but the final `with self.__auto_delete_lock:` that pops `imported_children` and checks `__shutdown_event` is also moved — except now it runs AFTER releasing the outer `__model_lock` context, not inside it.

**Why it happens:** Re-structuring the method creates a new lock-release window between the coverage guard and the pop.

**How to avoid:** The `__execute_auto_delete` on `Controller` controls the `with self.__model_lock:` block. Inside that block, the BFS/coverage guard logic can be delegated to a collaborator method that takes `file` and `on_disk_videos` as parameters. The nested `with self.__auto_delete_lock:` pop (`:997–1002`) stays inside the `with self.__model_lock:` block on `Controller`. The `delete_local` call stays OUTSIDE both locks on `Controller`.

**Warning signs:** The `with self.__auto_delete_lock:` (the pop/shutdown check) appearing AFTER the `with self.__model_lock:` block closes.

### Pitfall 5: Losing Thread-Safety Docstrings

**What goes wrong:** The lock-ordering note (`:240–244`), the WR-02 TOCTOU block (`:983–997`), and the "runs outside the lock" note (`:823–833`) are the institutional memory preventing future deadlocks.

**How to avoid:** Every multi-line thread-safety docstring must travel WITH the code block it documents. This is a hard requirement from CONTEXT.md specifics.

---

## Code Examples

### Correct: Coordinator `__process_commands` Delegating Handle Logic

```python
# controller.py — stays on Controller
def __process_commands(self):
    def _notify_failure(_command, _msg: str, _code: int = 400):
        self.logger.warning("Command failed. {}".format(sanitize_log_value(_msg)))
        for _callback in _command.callbacks:
            _callback.on_failure(_msg, _code)

    while not self.__command_queue.empty():
        command = self.__command_queue.get()
        self.logger.info("Received command {} for file {}".format(
            str(command.action), sanitize_log_value(command.filename)))
        with self.__model_lock:
            try:
                file = self.__model.get_file(command.filename)
            except ModelError:
                _notify_failure(command, "File '{}' not found".format(command.filename), 404)
                continue

        # Delegate to CommandProcessor — no lock held here
        success, error_msg, error_code = self.__command_processor.handle(file, command)

        if not success:
            _notify_failure(command, error_msg, error_code)
            continue
        for callback in command.callbacks:
            callback.on_success()
```

```python
# command_processor.py — new file, no __private attrs
class CommandProcessor:
    def __init__(self, lftp_manager, file_op_manager, persist, logger):
        self._lftp_manager = lftp_manager
        self._file_op_manager = file_op_manager
        self._persist = persist
        self.logger = logger

    def handle(self, file, command) -> tuple:
        """Route command to the correct handler. Returns (success, error_msg, error_code)."""
        from controller.controller import Controller  # TYPE_CHECKING only; use Action directly
        action = command.action
        if action.name == 'QUEUE':
            return self._handle_queue(file, command)
        elif action.name == 'STOP':
            return self._handle_stop(file, command)
        # etc.
        return False, "Unknown action", 500

    def _handle_queue(self, file, command):
        ...
```

**Better approach:** Avoid the import entirely by comparing `command.action` to values passed in or by using the enum's identity (the enum class is accessible via `command.action.__class__`). The collaborator doesn't need to name `Controller.Command.Action` at all.

### Correct: AutoDeleteManager Receiving Lock Objects (Non-Dunder Storage)

```python
# auto_delete_manager.py — new file
import collections, os
from typing import Set

_VIDEO_EXTENSIONS = frozenset({'.mkv', '.mp4', '.avi', '.m4v', '.mov', '.ts', '.wmv', '.flv', '.webm'})
_AUTO_DELETE_BFS_NODE_LIMIT = 10_000

class AutoDeleteManager:
    def __init__(self, context, persist, model, model_lock, file_op_manager, logger):
        self._context = context
        self._persist = persist
        self._model = model
        self._model_lock = model_lock          # NOT __model_lock (avoids mangling to _AutoDeleteManager__model_lock)
        self._file_op_manager = file_op_manager
        self.logger = logger

    def run_bfs_and_coverage(self, file, file_name) -> tuple:
        """
        Run BFS pack-guard + coverage check under __model_lock (held by caller).
        Returns (skip: bool, reason: str, on_disk_videos: set).
        Caller holds __model_lock; this method does NOT acquire any lock.
        """
        ...
```

This ensures `self._model_lock IS self.controller._Controller__model_lock` — same object.

### Correct: `_VIDEO_EXTENSIONS` and `_AUTO_DELETE_BFS_NODE_LIMIT` Move to Collaborator

```python
# auto_delete_manager.py
_VIDEO_EXTENSIONS = frozenset({...})
_AUTO_DELETE_BFS_NODE_LIMIT = 10_000
```

These constants disappear from `controller.py` (they were only used by `__execute_auto_delete`). No test references them by module path, so this is safe.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Monolithic controller | Partial extraction (scan_manager, lftp_manager, file_operation_manager, model_builder, webhook_manager, memory_monitor) | Phases 1-108 | 6 of 9 responsibilities already extracted |
| All logic in Controller | Coordinator facade after Phase 109 | Phase 109 | ARCH-01 satisfied |

---

## How the Test Suite Is Run (D-06 Regression Gate)

### Full Python Suite — the gate command for each plan

```bash
make run-tests-python
```

This runs the full unit + integration suite in Docker (`docker/test/python/compose.yml`), which is the CI-equivalent run. It applies `fail_under = 88` via `pyproject.toml` `[tool.coverage.report]`.

### Ad-hoc local run (from `src/python/`)

```bash
cd src/python && pytest tests/ --cov=. --cov-report=term-missing
```

The `fail_under = 88` floor is checked by pytest-cov automatically via `pyproject.toml`. [VERIFIED: `src/python/pyproject.toml` — `fail_under = 88` in `[tool.coverage.report]`]

### Controller-specific tests only (for fast iteration during development)

```bash
cd src/python && pytest tests/unittests/test_controller/ -v
cd src/python && pytest tests/integration/test_controller/ -v
```

The integration suite requires the Docker environment (real `rar` binary for extraction tests; skipped on arm64 where `rar` is absent). The unit suite runs standalone.

### Per-plan gate (D-06 requires full suite after each of the three plans)

Each plan's success criterion: `make run-tests-python` exits 0 (all tests pass, coverage >= 88). Not just the controller subset.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All controller code | Assumed in Docker | >= 3.11 | — |
| Docker + Docker Compose | `make run-tests-python` | Assumed (prior phases used it) | — | `cd src/python && pytest` for unit-only |
| `rar` binary | Integration test extraction | amd64 only | — | Tests auto-skip on arm64 via `@skipIf(shutil.which("rar") is None, ...)` |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9 + unittest |
| Config file | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd src/python && pytest tests/unittests/test_controller/ -v` |
| Full suite command | `make run-tests-python` (Docker) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | Public API unchanged | Integration/unit | `make run-tests-python` | Yes |
| ARCH-01 | Thread-safety invariants (WR-02) | Unit | `pytest tests/unittests/test_controller/test_auto_delete.py -v` | Yes |
| ARCH-01 | Mock.patch binding (D-05) | Unit | `pytest tests/unittests/test_controller/ -v` | Yes |
| ARCH-01 | Coverage >= 88% | Coverage gate | `make run-tests-python` | Yes |

### Sampling Rate

- **Per task commit:** `cd src/python && pytest tests/unittests/test_controller/ tests/integration/test_controller/ -v`
- **Per wave merge:** `make run-tests-python`
- **Phase gate:** Full suite green (`make run-tests-python`) before `/gsd:verify-work`

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. No new test files are needed; the existing suite is the regression net (ARCH-01 criterion #3).

---

## Security Domain

> `security_enforcement` absent from config.json — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | No new input paths introduced |
| V6 Cryptography | no | — |

This is a behavior-preserving code-structure refactor. No new inputs, no new outputs, no security surface changes. CWE-117 log-injection mitigations (sanitize_log_value calls) must travel with the methods that contain them into collaborators.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `make run-tests-python` is available and uses the same Docker environment as CI | Test suite / D-06 gate | If Docker is unavailable, fallback to `cd src/python && pytest tests/` — coverage gate still applies via `fail_under = 88` in pyproject.toml |
| A2 | `fail_under = 88` (current value in pyproject.toml) has not been raised since this research was done | Coverage gate | Verify with `grep fail_under src/python/pyproject.toml` before each plan |

---

## Open Questions (RESOLVED)

1. **Should `__check_webhook_imports` stay on Controller or move to model_pipeline?**
   - What we know: Tests call `c._Controller__check_webhook_imports()` at `test_controller.py:214,242`.
   - What's clear: It MUST stay on `Controller` as a `def __check_webhook_imports(self)` method.
   - Recommendation: Keep it on coordinator entirely (it is 76 lines; model_pipeline is already the largest collaborator). The line-count saving is marginal and the risk of a cycle via `WebhookManager` import is real.

2. **Where does `_should_update_capacity` (static method) go?**
   - Tests call `Controller._should_update_capacity(...)` as a static method on `Controller` (`test_controller.py:14–41`).
   - It MUST stay on `Controller` as a `@staticmethod`.
   - `_update_controller_status` calls `Controller._should_update_capacity(...)` (using the class name explicitly).
   - If `_update_controller_status` moves to `ModelPipeline`, it must call `Controller._should_update_capacity(...)` which requires importing `Controller` from `controller.py` — that IS a cycle.
   - **Recommendation:** Keep `_update_controller_status` and `_should_update_capacity` both on the `Controller` coordinator, or duplicate the static method. Duplicating a 5-line static method into `model_pipeline.py` and keeping the original on `Controller` is the lowest-risk option (zero circular imports).

---

## Sources

### Primary (HIGH confidence)

- Direct file inspection: `src/python/controller/controller.py` (1151 lines, full read)
- Direct file inspection: `src/python/tests/unittests/test_controller/base.py` — patch targets confirmed
- Direct file inspection: `src/python/tests/unittests/test_controller/test_auto_delete.py` — all `_Controller__` mangling usage enumerated
- Direct file inspection: `src/python/tests/unittests/test_controller/test_controller_unit.py` — all `_Controller__` mangling usage enumerated
- Direct file inspection: `src/python/tests/unittests/test_controller/test_controller.py` — `_Controller__check_webhook_imports`, `__process_commands`, `__schedule_auto_delete` call patterns
- Direct file inspection: `src/python/pyproject.toml` — `fail_under = 88` confirmed
- Direct file inspection: `Makefile` — `run-tests-python` target confirmed
- Direct file inspection: `src/python/controller/scan_manager.py`, `lftp_manager.py`, `file_operation_manager.py` — construction-injection style template

### Secondary (MEDIUM confidence)

- Python language reference: name-mangling behavior (compile-time, class-body-based) — training knowledge, confirmed by behavioral inspection of test attribute accesses

---

## Metadata

**Confidence breakdown:**
- Exact test coupling (mangling inventory): HIGH — enumerated from source
- mock.patch binding semantics: HIGH — confirmed from test file + Python language semantics
- Lock-ordering invariants: HIGH — documented inline at `controller.py:240-244`, `:823-833`, `:983-997`
- Test run commands: HIGH — confirmed from Makefile and pyproject.toml

**Research date:** 2026-06-01
**Valid until:** This is a code-structure analysis. Valid until the codebase changes — re-read before implementing if any test files are modified.
