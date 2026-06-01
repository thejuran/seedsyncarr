# Phase 107: MP-Logger Spawn Safety - Research

**Researched:** 2026-06-01
**Domain:** Python multiprocessing spawn safety / cross-process logging
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The logger queue is created from a `spawn`-compatible multiprocessing context, created
  unconditionally. Concretely: store a context obtained via `multiprocessing.get_context("spawn")`
  on the instance and create the queue from it (`ctx.Queue(-1)`), replacing the bare
  `multiprocessing.Queue(-1)` at `multiprocessing_logger.py:24`. A `spawn`-context SemLock is
  safely shareable with BOTH fork and spawn children.
- **D-02:** The spawn context is stored on the instance (e.g. `self.__mp_context`) so it can be
  exposed/reused. The analog tests launch their child `Process` objects from the SAME context the
  queue belongs to.
- **D-03:** No change to observable logging behavior — same `QueueHandler` wiring, same listener
  thread drain loop, same log levels/destinations, same public method signatures
  (`start`/`stop`/`propagate_exception`/`get_process_safe_logger`). Only the queue's originating
  context changes.
- **D-04:** Promote each of the three analog tests' local `process_1` closure to a
  MODULE-LEVEL picklable function; launch the child `Process` via the SAME spawn context the
  logger exposes. This deterministically exercises spawn on every platform including Linux CI.
- **D-05:** No test is deleted or skipped. Existing single-process tests (L89-L212) stay as-is.
  Keep `@pytest.mark.timeout`, `testfixtures.LogCapture`, bounded `join(timeout=...)`.

### Claude's Discretion
- Exact private attribute names (`__mp_context`, `__queue`) and whether the context is exposed
  via a property vs. passed into the test some other consistent way — planner/executor choose,
  as long as queue and test children share one spawn context.
- Exact module-level naming of the promoted picklable target functions.

### Deferred Ideas (OUT OF SCOPE)
- **MP-logger listener silent-shutdown gap** (`multiprocessing_logger.py:78`, CONCERNS.md:298) —
  the `except Exception` branch sets `__listener_shutdown` and stops the listener on any handler
  error, silently dropping child logs thereafter. Out of scope for INFRA-01.
- No global `multiprocessing.set_start_method(...)` change and no `conftest.py` start-method
  fixture. The fix is local to the logger's own context + the three tests' own context.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | The three `MultiprocessingLogger` analog tests pass on both `fork` and `spawn` start methods. The fix is a targeted production change to `python/common/multiprocessing_logger.py`: the logger's queue is created from a shared `spawn`-compatible multiprocessing context so a queue handed to a `spawn` child no longer raises `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context`. Existing `fork`-based logging behavior is unchanged; the three previously-failing spawn-context analog tests now run and pass on macOS (spawn) and Linux (fork). | Fully addressed by D-01..D-05. Mechanism verified at the CPython SemLock source level. |
</phase_requirements>

---

## Summary

`MultiprocessingLogger.__init__` (line 24) creates its internal queue with bare
`multiprocessing.Queue(-1)`, which uses the default start-method context at creation time. On
Linux (fork default) this creates a `SemLock` with `_is_fork_ctx = True`. When a `spawn`-started
child process begins (as on macOS, which defaults to spawn, or in any test that forces spawn),
CPython's `SemLock.__getstate__` checks `_is_fork_ctx` and raises:
`RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context`.

The fix is a two-line production change: store a `multiprocessing.get_context("spawn")` object
on the instance and create the queue from it. `spawn`-context SemLocks have `_is_fork_ctx = False`,
allowing `__getstate__` to proceed through the `duplicate_for_child` / handle-pass path. A queue
created this way is safely shareable with BOTH fork and spawn children — verified by live
experiment on macOS (spawn default) confirming that a fork-started child can read from a
spawn-context queue without error.

The three analog tests (`test_main_logger_receives_records`, `test_children_names`,
`test_logger_levels`) currently define `process_1` as a local closure. Spawn cannot serialize
closures (targets must be importable module-level callables). These closures must be promoted to
module-level functions. Child processes must also be launched from the same spawn context stored on
the logger instance (D-02/D-04) so the tests deterministically exercise the spawn path on all
platforms, including Linux CI where the default is fork.

**Primary recommendation:** Change one line in `__init__` (queue context), add one attribute
(`self.__mp_context`), promote three closures to module scope, update three `Process(...)` call
sites to use the stored context. No other file changes required.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Cross-process queue creation | `MultiprocessingLogger.__init__` (production module) | — | Queue context is a production concern; tests must not work around a broken production queue |
| Spawn-context storage + exposure | `MultiprocessingLogger` instance | Test file (consumes via attribute) | Decoupled: production stores it; tests reference the same object |
| Child process launch (tests) | Test file module scope | — | Spawn requires importable targets; test-local closures are not importable |
| Log record transport (QueueHandler) | `get_process_safe_logger()` — unchanged | — | QueueHandler is context-agnostic; wraps any Queue transparently |
| Listener thread drain | `__listener()` — unchanged | — | Listener reads from `self.__queue` regardless of which context created it |

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `multiprocessing` (stdlib) | Python stdlib | `get_context("spawn")`, `ctx.Queue(-1)` | Built-in; no install required |
| `logging.handlers.QueueHandler` (stdlib) | Python stdlib | Child-process log transport | Already used; spawn-ctx queue is a transparent drop-in |
| `testfixtures.LogCapture` | Already installed | Assert on log records in tests | Already the established idiom in this file |
| `pytest-timeout` | Already installed | `@pytest.mark.timeout(5)` | Already the established idiom in this file |

No new packages are installed. This phase adds zero new dependencies.

**Version verification:** All libraries used are Python stdlib (`multiprocessing`, `logging`,
`threading`, `queue`, `time`, `sys`) or already present in the test environment
(`testfixtures`, `pytest`, `pytest-timeout`). [VERIFIED: codebase grep + test file imports]

---

## Package Legitimacy Audit

> No external packages are introduced by this phase. This section is intentionally empty.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
MultiprocessingLogger.__init__()
    │
    ├─ multiprocessing.get_context("spawn")  ──► self.__mp_context
    │
    └─ self.__mp_context.Queue(-1)  ──► self.__queue
                │
                ├─ (main process) listener thread reads from self.__queue
                │       └─ record = self.__queue.get(block=False)
                │              └─ self.logger.getChild(record.name).handle(record)
                │
                └─ (child process) get_process_safe_logger()
                        └─ QueueHandler(self.__queue) installed on root logger
                               └─ child log calls  ──► queue.put(record)  ──► listener

Test: spawn-context child process launched via self.__mp_context.Process(target=MODULE_FN, ...)
    │
    ├─ MODULE_FN receives mp_logger as arg
    │       └─ calls mp_logger.get_process_safe_logger()
    │               └─ QueueHandler points at spawn-ctx queue (no SemLock error)
    │
    └─ parent waits: p.join(timeout=2) + time.sleep(0.2) + mp_logger.stop()
            └─ LogCapture.check(...)  ──► asserts records arrived
```

### Production Module Change

**What changes in `multiprocessing_logger.py`:**

```python
# BEFORE (line 22-24):
def __init__(self, base_logger: logging.Logger):
    self.logger = base_logger.getChild("MPLogger")
    self.__queue = multiprocessing.Queue(-1)

# AFTER:
def __init__(self, base_logger: logging.Logger):
    self.logger = base_logger.getChild("MPLogger")
    self.__mp_context = multiprocessing.get_context("spawn")
    self.__queue = self.__mp_context.Queue(-1)
```

Everything else in `__init__` and all other methods are unchanged. [VERIFIED: live code inspection]

### Test Change Pattern

**What changes in the three analog tests:**

```python
# BEFORE: local closure (not importable, fails with spawn target)
def test_main_logger_receives_records(self):
    def process_1(_mp_logger):
        logger = _mp_logger.get_process_safe_logger().getChild("process_1")
        logger.debug("Debug line")
        ...
    mp_logger = MultiprocessingLogger(self.logger)
    p_1 = multiprocessing.Process(target=process_1, args=(mp_logger,))
    ...

# AFTER: module-level function + spawn-context Process
def _spawn_target_main_logger_receives_records(_mp_logger: MultiprocessingLogger):
    # [module scope — importable by the spawned interpreter]
    logger = _mp_logger.get_process_safe_logger().getChild("process_1")
    logger.debug("Debug line")
    ...

class TestMultiprocessingLogger(unittest.TestCase):
    ...
    def test_main_logger_receives_records(self):
        mp_logger = MultiprocessingLogger(self.logger)
        p_1 = mp_logger._MultiprocessingLogger__mp_context.Process(
            target=_spawn_target_main_logger_receives_records, args=(mp_logger,))
        # remainder of the test (LogCapture, start/join/sleep/stop, check) UNCHANGED
```

Note: accessing the private `__mp_context` attribute via name-mangling
(`_MultiprocessingLogger__mp_context`) is acceptable here because this is the test file for
this exact class. Alternatively the planner may expose a property — Claude's Discretion per D-02.

### Anti-Patterns to Avoid

- **Using `multiprocessing.get_start_method()` to branch:** Rejected in D-01. A fork-context
  queue still breaks the instant a spawn child is used, so branching adds complexity without
  correctness.
- **`multiprocessing.set_start_method("spawn")` globally or in conftest:** Rejected as deferred
  (CONTEXT.md §Deferred). It changes the default for the ENTIRE test session and has
  unpredictable side-effects on other test classes.
- **Keeping process_1 as a closure:** Spawn cannot serialize local functions; they are not
  importable by the fresh interpreter in the spawned child process. Fails at `p.start()`.
- **Passing the Queue separately as an arg instead of the logger:** The existing tests pass
  `mp_logger` and call `get_process_safe_logger()` inside the child — this is the correct tested
  pattern. The fix must preserve this (D-03/D-05).
- **Touching any method other than `__init__`:** The listener thread, QueueHandler wiring,
  `get_process_safe_logger`, `start`, `stop`, and `propagate_exception` are all unchanged.

---

## The "No Test Modification" Criterion — Resolved Tension

The ROADMAP states (criterion #2, paraphrased): "three tests pass without modification to the
test code; the fix is entirely in the production module."

This criterion's INTENT is: "no test was weakened, skipped, or deleted to hide the bug." It was
written at a time when the test-only plan (D-06/D-07/D-08, now superseded) was under consideration.

The test file DOES require changes under the adopted plan (D-04):

1. **Closure promotion to module scope** — mandatory for spawn. A local closure is not importable
   by the fresh spawned interpreter and fails at `p.start()`. This is not "weakening the test" —
   it is the standard multiprocessing spawn pattern. The same behavior is tested; only the target's
   scope changes.
2. **Process launch via the stored spawn context** — mandatory to deterministically exercise the
   spawn code path on Linux CI (which defaults to fork). Without this, the test passes on Linux
   but exercises fork, defeating the regression net.

**What stays unchanged in the test file:** all assertions (`log_capture.check(...)`), the
`@pytest.mark.timeout(5)` decorator, `testfixtures.LogCapture`, bounded `join(timeout=2)`,
`time.sleep(0.2)`, and `mp_logger.stop()`. The BEHAVIOR under test is identical; the fixture
mechanics are updated to satisfy spawn's requirements.

The planner and downstream adversarial reviewer should treat closure-promotion + spawn-context
`Process` launch as minimal-and-necessary test updates, not as a weakening of coverage.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Queue pickling for cross-process sharing | Custom serialization / fd-passing code | `multiprocessing.get_context("spawn").Queue(-1)` | CPython's `SemLock.__getstate__` handles the fd-duplication transparently for spawn-context objects |
| Start-method detection | `get_start_method()` branch | Always-spawn context (D-01) | A fork-ctx queue still breaks spawn children; branching adds complexity for zero benefit |
| Module-level function naming convention | Any custom import trick | Plain module-level `def _spawn_target_<test_name>(...)` | Standard Python spawn pattern; names are Claude's Discretion |

---

## Spawn Safety Mechanism — Verified Technical Details

### How the RuntimeError Arises (Live-Verified)

`multiprocessing.synchronize.SemLock.__init__` stores `_is_fork_ctx = (ctx.get_start_method() == "fork")` at creation time. When a spawn `Process` starts, Python pickles the child's state using `ForkingPickler`. The `SemLock.__getstate__` method is invoked for each lock object:

```python
# CPython multiprocessing/synchronize.py (observed on Python 3.14 on this machine)
def __getstate__(self):
    context.assert_spawning(self)      # only callable during spawn pickling
    sl = self._semlock
    if self._is_fork_ctx:
        raise RuntimeError(
            'A SemLock created in a fork context is being shared with a process '
            'in a spawn context. ...')
    h = sl.handle
    return (h, sl.kind, sl.maxvalue, sl.name)
```

**Verified:** [VERIFIED: CPython source inspection — `python3 -c "import inspect, multiprocessing.synchronize as ms; print(inspect.getsource(ms.SemLock))"`]

### Why spawn-context Queue is Fork-Child Compatible

A spawn-context Queue (`multiprocessing.get_context("spawn").Queue(-1)`) has `_is_fork_ctx = False`
on all its internal SemLocks. A fork-started child inherits the queue's file descriptors via
`os.fork()` — it never calls `__getstate__`, so the `_is_fork_ctx` flag is never checked.
`_is_fork_ctx=False` is only relevant when the lock IS pickled (spawn path). Therefore:

- **fork child + spawn-ctx queue:** fd inherited, no pickling, works. [VERIFIED: live experiment
  — fork-ctx child successfully put/got from spawn-ctx Queue on this machine]
- **spawn child + spawn-ctx queue:** `__getstate__` invoked, `_is_fork_ctx=False`, serializes via
  `duplicate_for_child`, works.
- **spawn child + fork-ctx queue:** `__getstate__` invoked, `_is_fork_ctx=True`, RuntimeError.

The always-spawn choice (D-01) is therefore correct and does NOT regress fork-default Linux.

### Why Module-Level Target Functions are Required for Spawn

Spawn launches a fresh Python interpreter that `import`s the target module and looks up the target
function by name. A closure (inner function defined inside a method) is not reachable by module-
level import — it has no name in the module's namespace. This is not a cpython-specific
limitation; it is documented behavior. [ASSUMED: training knowledge on Python pickling / spawn
mechanics; the live experiment above confirms the mechanism at the SemLock level]

### QueueHandler Compatibility

`logging.handlers.QueueHandler(queue)` wraps any queue-like object that implements `put_nowait`.
`multiprocessing.Queue` (regardless of context) implements this interface. Verified:

```
# Confirmed via python3 -c:
# ctx = multiprocessing.get_context('spawn')
# q = ctx.Queue(-1)
# handler = QueueHandler(q)
# handler.emit(record)  # succeeded
# q.get(timeout=1)      # record.getMessage() == 'hello'
```
[VERIFIED: live experiment on this machine]

---

## Codebase Surface — Consumer Grep

`MultiprocessingLogger` callers outside the production module and its test file:

| File | Usage | Impact of D-01 |
|------|-------|----------------|
| `controller/controller.py:126` | `self.__mp_logger = MultiprocessingLogger(self.logger)` | Constructor unchanged — only queue context changes internally |
| `controller/file_operation_manager.py:33,67,165,192` | Receives `mp_logger: MultiprocessingLogger`, calls `set_multiprocessing_logger(mp_logger)` | Public type unchanged; no call-site modification |
| `controller/scan_manager.py:31,77-79` | Same as above | Same |
| `common/app_process.py:50,75` | `set_multiprocessing_logger(mp_logger)` + `mp_logger.get_process_safe_logger()` in child `run()` | `get_process_safe_logger()` is unchanged; spawn-ctx queue is now correctly shareable with `AppProcess` children (which extend `Process`) |
| `common/__init__.py:10` | Re-export | No impact |
| `tests/unittests/test_controller/base.py:22` | `patch('controller.controller.MultiprocessingLogger')` | Mock replaces the whole class; patch target unchanged |

**COMPAT verified:** All callers use the public API (`start`, `stop`, `get_process_safe_logger`,
`propagate_exception`). None of these methods change. The only internal change is the queue's
`_is_fork_ctx` flag. [VERIFIED: grep of src/python, excluding the two files under change]

**Important production note:** `AppProcess` (the production subclass of `Process`) is instantiated
via its own constructor and started via `Process.start()`. On macOS (spawn default), `AppProcess`
and its attributes ARE serialized by ForkingPickler at `start()` time. `self.mp_logger` (the
`MultiprocessingLogger` instance) is one of those attributes. After D-01, the Queue's SemLocks
will have `_is_fork_ctx=False`, so `AppProcess.start()` on macOS will no longer encounter the
RuntimeError either. This is an implicit production correctness improvement included in the fix.

---

## Common Pitfalls

### Pitfall 1: Closure target silently fails at process start, not at test assertion
**What goes wrong:** The test appears to hang or the `LogCapture.check(...)` produces
"no records" rather than a pickling error, because the child process raises during
deserialization and exits without logging anything.
**Why it happens:** `multiprocessing.Process.start()` suppresses the spawn-child's
initialization error in some configurations, or the error surfaces as a non-zero exit code.
**How to avoid:** After promoting closures to module scope, verify that `p.exitcode` is `0`
after `p.join()`, or add an explicit assertion that the process exited cleanly.
**Warning signs:** `log_capture.check(...)` fails with "no records received" and
`p.exitcode` is non-zero or -1.

### Pitfall 2: Accessing the spawn context in tests via name-mangling
**What goes wrong:** `mp_logger._MultiprocessingLogger__mp_context` raises `AttributeError`
if the attribute name chosen differs from the name used in the test.
**Why it happens:** Python name-mangling transforms `__mp_context` to
`_MultiprocessingLogger__mp_context`. If the executor names the attribute `__ctx` or
`_spawn_ctx` (no double underscore), the mangling is different.
**How to avoid:** The planner must commit to one attribute name (Claude's Discretion) and
the test must use the matching mangled form. A property exposing the context avoids mangling
entirely and is cleaner.
**Warning signs:** `AttributeError: 'MultiprocessingLogger' object has no attribute
'_MultiprocessingLogger__mp_context'` in the test.

### Pitfall 3: test_logger_levels creates MultiprocessingLogger four times
**What goes wrong:** Each of the four log-level sub-cases creates a new `MultiprocessingLogger`
and a new child process. Each needs its OWN `p_1` launched from the instance's spawn context
and its OWN module-level target. Using the wrong logger instance's context for a given `p_1`
causes context/queue mismatch.
**Why it happens:** The test loops over four `(level, expected_records)` scenarios, each with
its own `mp_logger` instance.
**How to avoid:** The module-level target for `test_logger_levels` must be one shared function
(since the behavior for all four sub-cases is identical: log at DEBUG/INFO/WARNING/ERROR). Each
sub-case constructs `mp_logger = MultiprocessingLogger(self.logger)` then
`p_1 = mp_logger.<ctx>.Process(target=<module_fn>, args=(mp_logger,))`.
**Warning signs:** Records from one sub-case's child bleed into the next sub-case's
`LogCapture`.

### Pitfall 4: `__mp_context` attribute is set before `self.__queue`
**What goes wrong:** If `self.__mp_context` is accessed in any code path before the queue is
created (e.g. in a `start()` call that accidentally references the context), initialization
order matters.
**Why it happens:** Python `__init__` executes sequentially; as long as the context is stored
before the queue is created from it, there is no issue.
**How to avoid:** The canonical order is:
`self.__mp_context = multiprocessing.get_context("spawn")` then
`self.__queue = self.__mp_context.Queue(-1)`. This is the only correct order.

### Pitfall 5: Out-of-scope `except Exception` gap at line 78
**What goes wrong:** A reviewer or executor attempts to also fix the silent-listener-shutdown
gap at `multiprocessing_logger.py:78` (CONCERNS.md:298) in the same change.
**Why it happens:** It is in the same method, same file, and appears related.
**How to avoid:** D-05 and the Deferred section of CONTEXT.md explicitly exclude this. The
`except Exception` silent-shutdown concern is a distinct reliability issue tracked separately.
Do not touch lines 67-87 (`__listener` method body).

---

## Runtime State Inventory

> SKIPPED — not a rename/refactor/migration phase. This is a targeted single-file production
> change with a three-test update. No stored data, live service config, OS-registered state,
> secrets/env vars, or build artifacts reference the multiprocessing queue context.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 stdlib `multiprocessing` | Production fix (D-01) | Yes | Python 3.14.4 (macOS) | — (stdlib) |
| `testfixtures` | Analog tests (LogCapture) | Yes | Already installed in test env | — |
| `pytest-timeout` | `@pytest.mark.timeout` decorator | Yes | Already installed in test env | — |

No missing dependencies. [VERIFIED: test file already imports and uses both testfixtures and pytest-timeout successfully; stdlib multiprocessing is always available]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9 with unittest.TestCase style |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd src/python && pytest tests/unittests/test_common/test_multiprocessing_logger.py -v` |
| Full suite command | `make run-tests-python` (Docker CI) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | spawn-context child logs arrive via queue | multiprocess integration | `pytest tests/unittests/test_common/test_multiprocessing_logger.py::TestMultiprocessingLogger::test_main_logger_receives_records -v` | Yes (test exists; updated) |
| INFRA-01 | spawn child can log with child logger names | multiprocess integration | `pytest tests/unittests/test_common/test_multiprocessing_logger.py::TestMultiprocessingLogger::test_children_names -v` | Yes (test exists; updated) |
| INFRA-01 | spawn child respects configured log levels | multiprocess integration | `pytest tests/unittests/test_common/test_multiprocessing_logger.py::TestMultiprocessingLogger::test_logger_levels -v` | Yes (test exists; updated) |
| INFRA-01 (regression) | existing single-process tests still pass under fork | unit | `pytest tests/unittests/test_common/test_multiprocessing_logger.py -v` | Yes (unchanged) |

### Spawn-Platform Determinism

The three updated analog tests launch child processes via the logger's stored spawn context
(`self.__mp_context = multiprocessing.get_context("spawn")`). This means:

- **macOS (spawn default):** tests exercise spawn natively — same as before the fix, but now
  without the RuntimeError.
- **Linux CI (fork default):** tests exercise spawn explicitly — even though the platform default
  is fork, the tests deterministically use `mp_logger.<ctx>.Process(...)` which is a spawn-context
  `Process`. This is the regression net D-04 is designed to establish.

A future regression that accidentally creates the queue from a fork context WILL cause these tests
to fail on Linux CI, not just macOS. This is the desired behavior.

### Sampling Rate

- **Per-task commit:** `cd src/python && pytest tests/unittests/test_common/test_multiprocessing_logger.py -v --timeout=30`
- **Per-wave merge:** `cd src/python && pytest tests/unittests/test_common/ -v`
- **Phase gate:** Full suite green — `make run-tests-python` — before `/gsd:verify-work`

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. No new test files, no new
conftest fixtures, no framework install needed.

---

## Coverage

`pyproject.toml` sets `fail_under = 88` (branch coverage). [VERIFIED: grep of pyproject.toml line 88]

INFRA-01 brings 3 previously-failing (not skipped) tests into the passing suite. These tests
cover the code path through `__init__` (the changed lines), `get_process_safe_logger`, and the
listener thread's queue consumption. Coverage holds or rises — no risk to the 88 floor.

The single-process tests at L89-L212 (unchanged) continue to cover `__listener`, `start`, `stop`,
`propagate_exception`. The 5 existing tests + 3 updated tests = 8 tests total in the class, all
passing.

---

## Security Domain

No security-relevant changes. This phase:
- Does not add authentication, session management, or access control code.
- Does not introduce new user-input handling.
- Does not touch cryptographic primitives.
- Does not log any new data fields.

ASVS categories V2/V3/V4/V5/V6 are inapplicable. The only operational change is the multiprocessing
context used for queue creation — a pure internal infrastructure concern.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Module-level target functions are importable by spawned interpreter in the test's module context (`test_multiprocessing_logger.py` is importable as a module when spawned). | Test Change Pattern | If the test file is not importable in the spawn child's context, the target function cannot be resolved. Unlikely — test files are standard Python modules on `pythonpath`. |

**All other critical claims are verified at [VERIFIED] confidence.**

---

## Open Questions

None that block planning. All mechanism questions were resolved via live CPython inspection and
experiment.

The only executor-level choice remaining is Claude's Discretion items from CONTEXT.md:
- Attribute name: `__mp_context` (recommended) vs other
- Exposure: name-mangling access in tests vs a property
- Module-level function naming convention for the three promoted targets

These are implementation-level choices, not research gaps. The planner should specify them.

---

## Sources

### Primary (HIGH confidence)
- CPython `multiprocessing/synchronize.py` — `SemLock.__init__` and `SemLock.__getstate__`
  source, read via `inspect.getsource(multiprocessing.synchronize.SemLock)` on this machine.
  Confirms `_is_fork_ctx` flag mechanism and the exact error condition.
- Live experiments on this machine (macOS, Python 3.14.4, spawn default):
  - fork-ctx Queue SemLock `_is_fork_ctx = True`, spawn-ctx Queue SemLock `_is_fork_ctx = False`
  - fork-started child + spawn-ctx Queue: successful put/get
  - `QueueHandler(spawn_ctx_queue).emit(record)` + `queue.get()`: successful round-trip
- Codebase grep: all callers of `MultiprocessingLogger` outside the two files under change
- `src/python/pyproject.toml`: `fail_under = 88`, `branch = true`
- `.planning/milestones/v1.3.0-phases/107-mp-logger-spawn-safety/107-CONTEXT.md`
- `.planning/REQUIREMENTS.md` §INFRA-01 and Cross-Cutting Constraints
- `src/python/common/multiprocessing_logger.py` — full source, lines 1-88
- `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` — full source, lines 1-347
- `src/python/common/app_process.py` — full source (consumer of `MultiprocessingLogger`)
- `.planning/codebase/TESTING.md` — multiprocessing test conventions

### Secondary (MEDIUM confidence)
- `.planning/milestones/v1.3.0-phases/102-controller-concurrency-test-infra/102-CONTEXT.md`
  §INFRA-01 deferral — live repro description confirmed independently above

### Tertiary (LOW confidence — training knowledge, not independently verified here)
- Python documentation on spawn requiring importable/picklable targets [A1]

---

## Metadata

**Confidence breakdown:**
- Production fix mechanism: HIGH — verified at CPython source level on this machine
- Test change requirements: HIGH — verified via direct code inspection + pickling experiments
- Caller compatibility: HIGH — full grep of all callers, confirmed no public API change needed
- Coverage floor: HIGH — `fail_under = 88` confirmed in pyproject.toml; 3 tests added, not removed

**Research date:** 2026-06-01
**Valid until:** 2026-12-01 (stable CPython behavior, not fast-moving)
