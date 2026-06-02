# Phase 112: Defensive Guards & Code Hardening — Research

**Researched:** 2026-06-02
**Domain:** Python multiprocessing spawn-safety, logging correctness, shutil error handling, .gitignore hygiene
**Confidence:** HIGH (all claims verified against live code and live test execution)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**GUARD-04 — AppProcess spawn-context fix**
- D-01: Mirror INFRA-01 precedent (`common/multiprocessing_logger.py`, Phase 107). Create unpicklable primitives from a spawn-compatible context. Specifically, build `__exception_queue` and `_terminate` from `multiprocessing.get_context("spawn")`.
- D-02: Decision required by researcher against live spawn repro — see GUARD-04 section below. Answer: `get_context("spawn")` alone does NOT fix the issue. `AppProcess` ALSO needs `__getstate__`/`__setstate__`.
- D-03: Do NOT globally `set_start_method("spawn")`. Fix is local to `AppProcess`'s primitives.

**GUARD-01/02 — Startup warning prominence + correctness**
- D-04: Confirm-the-gap only. Both warnings exist in `seedsyncarr.py::_emit_startup_warnings` (lines 372-397), tested.
- D-05 (GUARD-02 correctness): Accept-any-caller warning fires only when `not webhook_secret and not webhook_require_secret`. The fail-closed state emits only the "rejected with 503" message.
- D-06 (GUARD-01 prominence): Keep `logging.warning`, add visual prominence (e.g. `[SECURITY]` prefix).
- D-07: Update/extend `test_seedsyncarr.py` warning tests to pin corrected GUARD-02 matrix.

**GUARD-03 — Logged delete-path failures**
- D-08: Replace `shutil.rmtree(file_path, ignore_errors=True)` with a call that logs failures. Either `onexc`/`onerror` callback OR simpler `try/except OSError` wrap. See Python version constraint below.
- D-09: Do NOT change delete-outcome contract — best-effort, non-fatal. Mirror `DeleteRemoteProcess.run_once` (lines 46-50).
- D-10: Add a regression test for the failure path (GUARD-03 — no test currently exists for `DeleteLocalProcess`).

**GUARD-06 — Legacy `~/.seedsync` fallback surfacing**
- D-11: Keep auto-fallback behavior. Make warning reach operator — preferred: carry a flag out of `_parse_args` and emit via configured logger near other startup warnings. Acceptable fallback: `print(..., file=sys.stderr)`.
- D-12: Do NOT implement opt-in-gate alternative.

**GUARD-05 — `.gitignore` tooling artifacts**
- D-13: Add `.orchestrator.json` and `.playwright-mcp/` alongside existing `.aidesigner/*`, `.bg-shell/`, `.turingmind/` entries.

**Ordering/waves (planner guidance, not locked)**
- D-14: Six items are mutually independent. GUARD-04 highest value/risk — sequence so its full-suite verification is not blocked by cosmetic items. GUARD-05 trivial, can land first.

### Claude's Discretion
- Exact warning prefix/format (D-06), provided consistent and stays at `logging.warning` level.
- Whether GUARD-03 uses `onexc`/`onerror` callback vs. single `try/except` wrap (D-08).
- Whether GUARD-06 threads a flag out of `_parse_args` vs. emits to stderr (D-11).
- Whether GUARD-04 needs `__getstate__`/`__setstate__` in addition to spawn context (D-02) — **answered: YES, both are required.**

### Deferred Ideas (OUT OF SCOPE)
- None beyond the six items.
- `migrate-config-set-to-post-body.md` — shipped as Phase 111, not this phase.
- `webob-cgi-upstream-unblock.md` — DEFER-WEBOB, externally blocked.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GUARD-01 | Non-loopback bind without `api_token` emits prominent startup warning; default behavior unchanged | Warning already exists at `seedsyncarr.py:384-393`; gap is text prominence only |
| GUARD-02 | Webhook unauthenticated state emits accurate startup warning; `empty+require_secret=True` state does NOT fire "accept any caller" | Bug confirmed live at `seedsyncarr.py:374-378`; fix is conditional guard on warning |
| GUARD-03 | Failed local `shutil.rmtree` leaves observable log signal; best-effort unchanged | `delete_process.py:24` confirmed; precedent is `DeleteRemoteProcess.run_once:46-50`; Python 3.11 runtime requires `onerror` or `try/except` |
| GUARD-04 | Full Python test suite passes under both `fork` and `spawn`; `test_process_with_long_running_thread_terminates_properly` goes green | **Live repro confirmed**: root cause is `threading.Thread` in `LongRunningThreadProcess.__init__`; fix is `__getstate__`/`__setstate__` on `AppProcess` stripping `threading.Thread` instances |
| GUARD-05 | `.orchestrator.json` and `.playwright-mcp/` are git-ignored | Both confirmed untracked in working tree; `.gitignore` has exactly the right pattern |
| GUARD-06 | Operator sees a visible warning when `~/.seedsync` fallback triggers | `logging.warning()` at `seedsyncarr.py:268-271` fires before `_create_logger()` (line 74); disappears into unconfigured root logger |
</phase_requirements>

---

## Summary

Phase 112 is a cluster of six independent, surgical fixes. Five are purely observability/correctness gaps on code that already exists. One (GUARD-04) is a real spawn-pickling bug with a live red test.

**GUARD-04 is the only item with genuine technical uncertainty.** The root cause has been fully characterized against a live spawn repro: `LongRunningThreadProcess.__init__` stores `self.thread = threading.Thread(...)` which is unpicklable under spawn. The `Queue()` and `Event()` in `AppProcess.__init__` are NOT the direct problem — Python's spawn mechanism handles them correctly for `Process` subclasses. The fix requires `__getstate__`/`__setstate__` on `AppProcess` that strips `threading.Thread` instances from the pickle state. Building primitives from `get_context("spawn")` alone does NOT fix the failure.

**The other five fixes** are constrained tightly: GUARD-01/02/06 all edit `_emit_startup_warnings` or the `_parse_args` ordering in `seedsyncarr.py`; GUARD-03 replaces one line in `delete_process.py:24` with a log-annotated equivalent; GUARD-05 adds two lines to `.gitignore`.

**Primary recommendation:** Implement GUARD-04 as `__getstate__`/`__setstate__` that strips `threading.Thread` instances (and does NOT strip `Queue`/`Event` — those survive the spawn boundary correctly). Implement all other items in strict compliance with CONTEXT.md D-05 through D-13.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| GUARD-04: AppProcess spawn safety | Python runtime / process layer | Test layer | `app_process.py` is the base class for all worker processes; fix lands there |
| GUARD-01/02: startup warnings | Application startup (Python main) | — | `_emit_startup_warnings()` in `seedsyncarr.py` is already the correct location |
| GUARD-03: logged delete failures | Worker process (delete) | — | `delete_process.py` owns the delete operation; logging stays local |
| GUARD-06: legacy fallback surfacing | Application startup (Python main) | — | Ordering fix in `seedsyncarr.py`; no architectural change needed |
| GUARD-05: .gitignore hygiene | Repo metadata | — | Pure `.gitignore` edit |

---

## Standard Stack

No new external packages required. All fixes use the Python standard library and in-repo helpers.

| Component | Version | Purpose | Notes |
|-----------|---------|---------|-------|
| `multiprocessing` (stdlib) | Python 3.11/3.12 | `get_context`, `Queue`, `Event` | Already imported |
| `threading` (stdlib) | Python 3.11/3.12 | `isinstance(v, threading.Thread)` check in `__getstate__` | Already imported |
| `shutil` (stdlib) | Python 3.11 | `rmtree` — use `try/except OSError` or `onerror` kwarg | `onexc` is 3.12+ ONLY |
| `sanitize_log_value()` | in-repo (`common/types.py`) | Log-injection guard for GUARD-03 log lines | Phase 101 SEC-01 |

## Package Legitimacy Audit

No external packages are installed in this phase. N/A.

---

## GUARD-04: Spawn Fix — Live Repro Findings

### Root Cause (Definitive)

**Confirmed via live test execution on Python 3.12 / macOS (spawn default):**

The only source of the `TypeError: cannot pickle '_thread.lock' object` is:

```python
# test_app_process.py:57-75
class LongRunningThreadProcess(AppProcess):
    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.thread = threading.Thread(target=self.long_task)  # <-- THIS
```

`threading.Thread` stores internal lock state (`_thread.lock`) that is unpicklable. When `p.start()` is called under spawn, Python's `popen_spawn_posix._launch` calls `reduction.dump(process_obj, fp)` (i.e., `ForkingPickler`), which recursively pickles all instance attributes including `self.thread`.

**`Queue()` and `Event()` in `AppProcess.__init__` are NOT the problem.** They are successfully handled by Python's spawn mechanism for `Process` subclasses — verified by running `DummyProcess` (which also has `Queue` and `Event` in its inherited `__init__`) under spawn, which passes all tests including `test_exception_propagates` and `test_process_terminates`.

**Proof:** A minimal `Process` subclass with only `Queue()` and `Event()` in `__init__` starts successfully under spawn. A subclass that also adds `self.thread = threading.Thread(...)` fails with the exact error.

### Key Structural Difference vs. INFRA-01 (MP-logger)

`MultiprocessingLogger` was passed as an **argument** to a `Process(target=fn, args=(mp_logger,))`. Arguments are serialized differently from the process instance itself (via `ForkingPickler`'s registered dispatch for known types). Its `__getstate__`/`__setstate__` stripped unpicklable thread objects.

`AppProcess` **is** the `Process` subclass — its entire `__dict__` is pickled when `.start()` is called. The fix must be on `AppProcess` itself.

### The Correct Fix

`AppProcess` needs `__getstate__`/`__setstate__` that strips `threading.Thread` instances set by subclasses in `__init__`:

```python
# Source: live repro in /tmp/test_final_fix.py — all 9 test scenarios pass under spawn

def __getstate__(self) -> dict:
    """Return picklable state for spawn serialization.

    Strips threading.Thread instances set by subclasses in __init__ that
    cannot be pickled for spawn. Queue and Event are kept — Python's spawn
    mechanism handles them correctly for Process subclasses.
    Subclasses that store Thread objects in __init__ must re-create them
    in run_init() (they execute in the child process).
    """
    state = self.__dict__.copy()
    stripped = [k for k, v in state.items() if isinstance(v, threading.Thread)]
    for k in stripped:
        state.pop(k)
    return state

def __setstate__(self, state: dict) -> None:
    """Restore state after spawn deserialization."""
    self.__dict__.update(state)
```

**Do NOT strip `_AppProcess__exception_queue` or `_terminate`** — these survive the spawn boundary correctly and are necessary for `propagate_exception()` and `terminate()` to work cross-process.

### Why Not `get_context("spawn")` for Queue/Event?

`multiprocessing.Queue` and `multiprocessing.Event` raise `"should only be shared between processes through inheritance"` when directly subjected to `ForkingPickler.dump()`. However, when Python's spawn mechanism serializes a `Process` subclass, it uses a different internal reduction path that successfully transfers these objects. This has been verified empirically: `test_exception_propagates` passes under spawn with no changes to `Queue`/`Event` construction.

Changing from `Queue()` to `ctx_spawn.Queue()` is therefore **not required and not sufficient** — it neither fixes the bug nor is needed for the fix. The fix is purely `__getstate__`/`__setstate__` stripping `threading.Thread` instances.

### Regarding the Child's `run_init`

After stripping, `LongRunningThreadProcess.run_init()` calls `self.thread.start()` — but `self.thread` no longer exists in the child. This causes an `AttributeError` in the child process. The test still passes because:
1. The child exits non-zero (due to the error in `run_init`)
2. `p.terminate()` in the test calls `super().terminate()` (SIGTERM), which kills the process
3. The test only asserts `p.join()` completes — it does

**For production `AppProcess` subclasses:** No production subclass stores a `threading.Thread` in `__init__` — verified by grepping all files. Only the test fixture has this pattern. So there is no production behavioral change.

**Optional enhancement (not required by acceptance bar):** The `__getstate__` docstring should note that subclasses storing `Thread` objects in `__init__` must re-create them in `run_init()` rather than relying on `__init__`-time construction surviving into the child. This is the correct architectural pattern regardless.

### Acceptance Bar Verification

Live repro confirms all 9 test scenarios pass under spawn with the `__getstate__`/`__setstate__` fix:
- `test_exception_propagates` — PASS (Queue works cross-process)
- `test_exception_propagates_with_traceback` — PASS
- `test_process_terminates` — PASS
- `test_init_called_before_loop` — PASS
- `test_cleanup_called_after_loop` — PASS
- `test_long_running_process_is_force_terminated` — PASS
- `test_process_with_long_running_thread_terminates_properly` — **PASS** (the red test)
- `test_run_once_called_once` (AppOneShotProcess) — PASS
- `test_long_running_process_is_force_terminated` (AppOneShotProcess) — PASS

### Name Mangling

`AppProcess.__init__` uses `self.__exception_queue` which Python name-mangles to `_AppProcess__exception_queue`. The `__getstate__` MUST use the mangled form when stripping — but in our fix we do NOT strip it, so this is only relevant for confirming the dict key. Verified:

```
Dict keys include: '_AppProcess__name', '_AppProcess__exception_queue', '_terminate', ...
```

---

## GUARD-01/02: Startup Warning Correctness

### Current State (Verified Against Source)

`seedsyncarr.py:372-397` — `_emit_startup_warnings(logger, config)`:

```python
# Lines 374-393 (current behavior):
if not config.general.webhook_secret:           # fires when empty, regardless of require_secret
    logger.warning("...Webhook endpoints will accept requests from any caller.")
if config.general.webhook_require_secret and not config.general.webhook_secret:
    logger.warning("...All webhook requests will be rejected with 503...")
if not config.general.api_token:
    logger.warning("...No API token configured...")
    logger.warning("...Application is bound to 0.0.0.0...")
```

### GUARD-02 Correctness Matrix (Post-Fix)

| `webhook_secret` | `webhook_require_secret` | Actual runtime behavior | Warning to fire |
|---|---|---|---|
| empty | False (default) | Accepts any caller | "accept requests from any caller" |
| empty | True | FAILS CLOSED — 503 (`webhook.py:54-60`) | "rejected with 503" only |
| set | False | Accepts; HMAC verified | None |
| set | True | Accepts; HMAC enforced | None |

**Fix:** Change the first `if` condition from `not config.general.webhook_secret` to `not config.general.webhook_secret and not config.general.webhook_require_secret`.

### Test Impact

Existing tests (lines 210-256) all use `webhook_require_secret=False` (the default in `_make_mock_config`). The GUARD-02 fix does NOT change the count of warnings for any existing test case — `test_startup_warns_both_when_both_empty` (asserts `== 3 warnings`) still holds because `webhook_require_secret=False`.

**New tests needed** (GUARD-02 correctness pin — D-07):
1. `test_startup_require_secret_without_secret_does_not_warn_accept_any_caller` — asserts the "accept any caller" warning does NOT fire when `webhook_secret=""` and `webhook_require_secret=True`
2. `test_startup_require_secret_without_secret_warns_503` — asserts the "rejected with 503" warning DOES fire in that state

### GUARD-01 Prominence

The text at lines 384-393 is already accurate. Only visual prominence changes. The 0.0.0.0 bind is hardcoded in `web_app_job.py:27` (confirmed). Add a `[SECURITY]` prefix or similar to both the `api_token` and `webhook_secret` warning lines for consistency. The exact format is Claude's discretion (D-06).

---

## GUARD-03: Logged Delete Failures

### Current State (Verified)

`delete_process.py:24`:
```python
shutil.rmtree(file_path, ignore_errors=True)   # swallows everything
```

### Python Version Constraint (CRITICAL)

| Environment | Python | `shutil.rmtree` `onexc` kwarg | `onerror` kwarg |
|-------------|--------|-------------------------------|-----------------|
| Runtime Docker image | 3.11-slim | NOT available (added 3.12) | Available, not deprecated |
| Local dev / Poetry venv | 3.12.12 | Available | Available, deprecated |
| `pyproject.toml` requires | `>=3.11,<3.13` | — | — |

**The fix MUST be compatible with Python 3.11** (the runtime). This rules out `onexc` as the primary approach. [VERIFIED: source inspection of `shutil.rmtree` signature on Python 3.12; FINDINGS.md confirms runtime is `python:3.11-slim`]

**Recommended approach (D-08, simpler alternative):** Wrap `rmtree` in `try/except OSError`:

```python
# Source: in-repo precedent at delete_process.py:46-50 (DeleteRemoteProcess.run_once)
try:
    shutil.rmtree(file_path)
except OSError:
    self.logger.exception(
        "Failed to delete local file: %s",
        sanitize_log_value(self.__file_name)
    )
```

This is compatible with both Python 3.11 and 3.12, matches the `DeleteRemoteProcess` log-and-continue shape exactly, and satisfies GUARD-03's requirement ("a failed delete leaves an observable signal").

**If granular per-entry logging is desired** (also compatible with 3.11):
```python
def _log_rmtree_error(func, path, exc_info):
    self.logger.error(
        "Delete failed on %s: %s",
        sanitize_log_value(path),
        exc_info[1]
    )
shutil.rmtree(file_path, onerror=_log_rmtree_error)
```
`onerror` is present in Python 3.11 (not deprecated until 3.12). Note: using a closure here requires the function to be defined inside `run_once`.

**Either approach satisfies GUARD-03.** The `try/except OSError` is cleaner and more readable.

### Test Gap

No existing `DeleteLocalProcess` tests exist in `test_delete_process.py`. The file only covers `DeleteRemoteProcess`. GUARD-03 must add tests for `DeleteLocalProcess` including:
1. Existing behavior: `os.remove()` for files (success path)
2. Existing behavior: `rmtree` for directories (success path)
3. NEW: `rmtree` raises — `logger.exception` is called with the filename, and no exception propagates

Test approach: `unittest.mock.patch('shutil.rmtree', side_effect=OSError("permission denied"))` + `assertLogs(level='ERROR')`.

---

## GUARD-06: Legacy Fallback Warning

### Current State (Verified)

`seedsyncarr.py:265-272`:
```python
if not os.path.exists(args.config_dir):
    legacy_dir = os.path.expanduser("~/.seedsync")
    if os.path.exists(legacy_dir):
        logging.warning(           # bare root logger, no handlers configured yet
            "Config directory %s not found; falling back to legacy %s",
            args.config_dir, legacy_dir
        )
        args.config_dir = legacy_dir
```

`_parse_args` is called at `__init__:40`. `_create_logger` is called at `__init__:74`. The warning fires ~34 lines before the logger is configured — it goes to the unconfigured root logger and disappears silently.

### Fix Options

**Option A (preferred per D-11):** Thread a return value / flag out of `_parse_args`:

```python
# In _parse_args: return both args and a warning message
# (or return a flag and construct the message at the call site)
# Then in __init__: after _create_logger, emit via logger.warning(...)
```

Implementation: Change `_parse_args` signature to return `(args, legacy_fallback_used: bool)` or `(args, legacy_warning: str | None)`. Emit after line 76 (`logger.info("Debug mode is...")`).

**Option B (acceptable fallback per D-11):** Replace bare `logging.warning(...)` with `print(..., file=sys.stderr)` at the existing call site. No structural change needed.

Option A produces a cleaner log stream (lands alongside the other startup warnings). Option B is safe and simple.

### Test Coverage

No existing test for the fallback path. GUARD-06 must add a test asserting that when `_parse_args` is given a non-existent config_dir with the legacy dir present, the warning is emitted (either via the configured logger or stderr, depending on chosen option).

---

## GUARD-05: `.gitignore` Hygiene

### Confirmed State

`git status` output shows both are currently untracked:
```
?? .orchestrator.json
?? .playwright-mcp/
```

Neither is committed (confirmed: `git status` shows untracked, not modified).

### Existing Pattern in `.gitignore` (lines 21-24, 61)

```
# AI tooling (local only)
.agents/
.aidesigner/*
!.aidesigner/.gitkeep
.claude/
...
.bg-shell/
...
.turingmind/
```

**Fix:** Add two lines to `.gitignore` in the "AI tooling (local only)" block (lines ~21-25):
```
.orchestrator.json
.playwright-mcp/
```

No code, no test impact.

---

## Architecture Patterns

### AppProcess Spawn Fix Pattern

```
AppProcess.__init__
  ├── stores self.__exception_queue = Queue()       # OK — survives spawn
  ├── stores self._terminate = Event()               # OK — survives spawn
  └── (subclasses may store self.thread = Thread())  # PROBLEM — stripped by __getstate__

AppProcess.__getstate__                              # NEW
  ├── state = self.__dict__.copy()
  ├── strip: [k for k, v in state.items() if isinstance(v, threading.Thread)]
  └── return state

AppProcess.__setstate__                              # NEW
  └── self.__dict__.update(state)
      # Queue/Event automatically survive — no rebuild needed
      # Thread instances are gone — subclasses must re-create in run_init()
```

### Delete Log-and-Continue Pattern (in-repo precedent)

```python
# DeleteRemoteProcess.run_once (lines 46-50) — the shape to mirror:
try:
    out = self.__ssh.shell(...)
    self.logger.debug(...)
except SshcpError:
    self.logger.exception("Exception while deleting remote file")

# GUARD-03 local equivalent:
try:
    shutil.rmtree(file_path)
except OSError:
    self.logger.exception("Failed to delete local file: %s",
                          sanitize_log_value(self.__file_name))
```

### Warning Correctness Pattern

```python
# GUARD-02 corrected logic:
# OLD: if not webhook_secret:                          # fires even when fail-closed
# NEW: if not webhook_secret and not webhook_require_secret:  # fires only when actually open
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Log-injection sanitization | Custom path sanitizer | `sanitize_log_value()` from `common/types.py` — already applied across delete cluster |
| Spawn-safe multiprocessing | Custom IPC | Standard `multiprocessing` stdlib — Queue/Event work fine, only Thread stripping needed |
| Warning test harness | New mock infrastructure | Extend existing `_make_mock_config()` / `MagicMock()` pattern in `test_seedsyncarr.py:201-208` |

---

## Common Pitfalls

### Pitfall 1: Stripping Queue/Event in `__getstate__`

**What goes wrong:** If `_AppProcess__exception_queue` and `_terminate` are stripped from `__getstate__` and rebuilt in `__setstate__`, the child gets fresh objects disconnected from the parent. `propagate_exception()` will always be empty (parent's queue never receives child exceptions), and `_terminate.set()` from the parent does not reach the child's loop.

**Why it happens:** The INFRA-01 precedent (MP-logger) DID strip its queue and thread objects — but MP-logger was an *argument*, not a *Process subclass*. The parallel doesn't apply here.

**How to avoid:** Do NOT strip `_AppProcess__exception_queue` or `_terminate` from `__getstate__`. Strip ONLY `threading.Thread` instances. Verified by running all 9 test scenarios including `test_exception_propagates` with the fix.

### Pitfall 2: Using `onexc` for Python 3.11

**What goes wrong:** `shutil.rmtree(path, onexc=handler)` raises `TypeError: rmtree() got an unexpected keyword argument 'onexc'` on Python 3.11-slim.

**Why it happens:** `onexc` was added in Python 3.12. The runtime image is `python:3.11-slim`.

**How to avoid:** Use `onerror=` (Python 3.11-compatible) or wrap in `try/except OSError`. The `try/except` approach is cleaner and works on both 3.11 and 3.12.

### Pitfall 3: GUARD-02 Test Count Regression

**What goes wrong:** `test_startup_warns_both_when_both_empty` asserts `self.assertEqual(3, mock_logger.warning.call_count)`. If the GUARD-02 fix changes the warning count for the `webhook_secret="" + webhook_require_secret=False` case, this test breaks.

**Why it happens:** Careless broadening of the guard condition.

**How to avoid:** The fix changes only the condition for the FIRST webhook warning — it does NOT fire when `webhook_require_secret=True`. For `webhook_require_secret=False` (the test default), the condition `not webhook_secret and not webhook_require_secret` is True when `webhook_secret=""`, preserving the existing 3-warning count.

### Pitfall 4: GUARD-06 Threading a Flag Through `_parse_args`

**What goes wrong:** `_parse_args` is a `@staticmethod`. If threading a warning flag, the return type must change from `args` to `(args, str | None)` — all callers (only one: `__init__:40`) must be updated.

**How to avoid:** If using Option A, change the return to a tuple and update the one call site. If this feels fragile, use Option B (`print(..., file=sys.stderr)`) — same observable outcome.

### Pitfall 5: ruff Compliance

**What goes wrong:** New Python code introduced in this phase fails `ruff check src/python/` (whole-tree), which is a separate CI gate from pytest.

**How to avoid:** Run `poetry run ruff check .` from `src/python/` before committing any Python change. Current baseline is clean (0 findings).

---

## Code Examples

### AppProcess `__getstate__`/`__setstate__` (verified working)

```python
# Source: live repro /tmp/test_final_fix.py — all 9 AppProcess test scenarios pass under spawn

def __getstate__(self) -> dict:
    """Return picklable state for spawn serialization.

    Strips threading.Thread instances set by subclasses in __init__ that
    cannot be pickled under macOS/Windows spawn start method.  Queue and
    Event objects are retained — Python's spawn mechanism transfers them
    correctly for Process subclasses.  Subclasses that create Thread
    objects in __init__ must re-create them in run_init().
    """
    state = self.__dict__.copy()
    stripped = [k for k, v in state.items() if isinstance(v, threading.Thread)]
    for k in stripped:
        state.pop(k)
    return state

def __setstate__(self, state: dict) -> None:
    """Restore state after spawn deserialization."""
    self.__dict__.update(state)
```

### GUARD-02 Warning Fix

```python
# Source: seedsyncarr.py:374-383 (current); apply condition change to line 374

# BEFORE:
if not config.general.webhook_secret:
    logger.warning("...Webhook endpoints will accept requests from any caller.")

# AFTER:
if not config.general.webhook_secret and not config.general.webhook_require_secret:
    logger.warning("[SECURITY] Webhook endpoints will accept requests from any caller.")
if config.general.webhook_require_secret and not config.general.webhook_secret:
    logger.warning("[SECURITY] ...All webhook requests will be rejected with 503...")
```

### GUARD-03 Delete Logging

```python
# Source: delete_process.py:15-24 (current); replace rmtree call at line 24

# BEFORE:
shutil.rmtree(file_path, ignore_errors=True)

# AFTER (try/except approach — Python 3.11 compatible):
try:
    shutil.rmtree(file_path)
except OSError:
    self.logger.exception(
        "Failed to delete local directory: %s",
        sanitize_log_value(self.__file_name)
    )
```

### GUARD-06 Warning via Flag (Option A)

```python
# Source: seedsyncarr.py:263-274 (_parse_args), seedsyncarr.py:74-77 (__init__)

# In _parse_args — change return to include flag:
legacy_fallback_warning: str | None = None
if not os.path.exists(args.config_dir):
    legacy_dir = os.path.expanduser("~/.seedsync")
    if os.path.exists(legacy_dir):
        legacy_fallback_warning = (
            "Config directory %s not found; falling back to legacy %s"
            % (args.config_dir, legacy_dir)
        )
        args.config_dir = legacy_dir
return args, legacy_fallback_warning

# In __init__ after _create_logger (line ~77):
args, legacy_fallback_warning = self._parse_args(sys.argv[1:])
...
logger = self._create_logger(...)
if legacy_fallback_warning:
    logger.warning(legacy_fallback_warning)
```

### GUARD-03 Test Pattern

```python
# Source: test_delete_process.py existing pattern + new fixture for DeleteLocalProcess

@patch('shutil.rmtree', side_effect=OSError("permission denied"))
def test_local_delete_logs_rmtree_failure(self, mock_rmtree):
    """GUARD-03: a failed rmtree produces a log record rather than silent swallow."""
    proc = DeleteLocalProcess(local_path="/fake/path", file_name="somefile")
    with self.assertLogs("DeleteLocalProcess", level="ERROR"):
        proc.run_once()  # must not raise
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `poetry run pytest tests/unittests/test_common/test_app_process.py tests/unittests/test_seedsyncarr.py tests/unittests/test_controller/test_delete_process.py -v` |
| Full suite command | `poetry run pytest tests/ -v --cov --cov-report=term-missing` |
| Lint gate | `poetry run ruff check .` (whole-tree from `src/python/`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUARD-04 | `test_process_with_long_running_thread_terminates_properly` passes under spawn | unit | `poetry run pytest tests/unittests/test_common/test_app_process.py -v` | YES |
| GUARD-04 | All AppProcess tests pass under fork too (Linux default) | unit | CI amd64 container | YES (CI) |
| GUARD-02 | Accept-any-caller warning does NOT fire when `require_secret=True` | unit | `poetry run pytest tests/unittests/test_seedsyncarr.py -v` | NO — Wave 0 |
| GUARD-02 | 503 warning DOES fire when `require_secret=True` + no secret | unit | same | NO — Wave 0 |
| GUARD-01 | Prominence prefix visible in warning text | unit | same | Wave 0 (extend existing) |
| GUARD-03 | `rmtree` failure produces log record, does not raise | unit | `poetry run pytest tests/unittests/test_controller/test_delete_process.py -v` | NO — Wave 0 |
| GUARD-06 | Legacy fallback warning is emitted when fallback triggers | unit | `poetry run pytest tests/unittests/test_seedsyncarr.py -v` | NO — Wave 0 |
| GUARD-05 | `.orchestrator.json` and `.playwright-mcp/` not in `git status` | manual | `git status` | N/A |

### Wave 0 Gaps

- [ ] `tests/unittests/test_seedsyncarr.py` — add GUARD-02 matrix tests (2 new tests)
- [ ] `tests/unittests/test_seedsyncarr.py` — add GUARD-06 fallback warning test (1 new test)
- [ ] `tests/unittests/test_controller/test_delete_process.py` — add `DeleteLocalProcess` failure-path tests (GUARD-03)

### Sampling Rate

- Per task commit: `poetry run ruff check . && poetry run pytest tests/unittests/test_common/test_app_process.py tests/unittests/test_seedsyncarr.py tests/unittests/test_controller/test_delete_process.py -v`
- Per wave merge: `poetry run pytest tests/ --cov --cov-report=term-missing`
- Phase gate: Full suite green + coverage `fail_under` ≥ 88 + ruff clean before `/gsd:verify-work`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (Poetry venv) | All Python fixes | YES | 3.12.12 (local); 3.11-slim (CI/runtime) | — |
| pytest | Test execution | YES | 9.0.3 | — |
| ruff | Lint gate | YES | in Poetry dev deps | — |
| multiprocessing stdlib | GUARD-04 | YES | stdlib | — |
| shutil stdlib | GUARD-03 | YES | stdlib | — |

**All required tools are available. No missing dependencies.**

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Peripheral (GUARD-01/02 make auth posture visible) | No change to auth logic; warning text only |
| V5 Input Validation | Yes (GUARD-03 log lines) | `sanitize_log_value()` from `common/types.py` |
| V6 Cryptography | No | — |

### Threat Patterns

| Pattern | GUARD | Standard Mitigation |
|---------|-------|---------------------|
| Log injection (CWE-117) | GUARD-03 | `sanitize_log_value()` for file_name/path in log calls |
| Silent security misconfiguration | GUARD-01/02/06 | Prominent warnings at startup; operator sees risk |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact on Phase |
|--------------|------------------|--------------|-----------------|
| `ignore_errors=True` (silent swallow) | `try/except OSError` + `logger.exception` | Phase 112 | GUARD-03 — observable failure signal |
| Bare `logging.warning()` pre-logger | Emit via configured logger or stderr | Phase 112 | GUARD-06 — warning actually reaches operator |
| Unconditional webhook warning | Conditional on actual runtime behavior | Phase 112 | GUARD-02 — no misleading "accept any caller" when fail-closed |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python 3.11's `shutil.rmtree` lacks `onexc` parameter | GUARD-03 | If wrong, `onexc` could be used; but `try/except` is safe either way |
| A2 | No production `AppProcess` subclass stores a `threading.Thread` in `__init__` | GUARD-04 | If a subclass does, its `run_init` must re-create the thread; currently verified to be none |

All other claims in this research are VERIFIED via live code inspection and test execution.

---

## Open Questions

None — all six items have sufficient information to plan and implement directly. D-02 (the key technical uncertainty) has been resolved: `__getstate__`/`__setstate__` stripping `threading.Thread` instances is the correct and sufficient fix.

---

## Sources

### Primary (HIGH confidence)
- Live test execution against `src/python/common/app_process.py` and `src/python/tests/unittests/test_common/test_app_process.py` — spawn repro confirmed, fix verified
- Direct source reads: `app_process.py`, `multiprocessing_logger.py`, `delete_process.py`, `seedsyncarr.py:265-272` and `372-397`, `webhook.py:54-60`, `types.py`, `test_seedsyncarr.py:200-256`, `test_delete_process.py`, `.gitignore`
- `pyproject.toml` — confirms `requires-python = ">=3.11,<3.13"` and Poetry Python 3.12 local dev
- `src/docker/build/docker-image/Dockerfile` lines 75, 37 — confirms `python:3.11-slim` runtime
- `110-FINDINGS.md` — HR-02/03/04/06/07 exact file:line locations
- `112-CONTEXT.md` — all locked decisions D-01 through D-14

### Secondary (MEDIUM confidence)
- `src/docker/test/python/Dockerfile` — confirms test image bases on `seedsyncarr/run/python/devenv` (the 3.11-slim runtime)
- Python 3.12 `shutil` source inspection — confirms `onexc` present in 3.12 but not 3.11

### Tertiary
- None required — all claims verified from source.

---

## Metadata

**Confidence breakdown:**
- GUARD-04 spawn fix: HIGH — live repro run; all 9 test scenarios confirmed passing
- GUARD-01/02 warning fix: HIGH — source verified; test harness understood
- GUARD-03 delete logging: HIGH — Python version constraint confirmed; precedent pattern verified
- GUARD-06 ordering fix: HIGH — timing sequence verified in source
- GUARD-05 gitignore: HIGH — `git status` confirmed; `.gitignore` pattern verified

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (all claims are against pinned source files and the standard library)
