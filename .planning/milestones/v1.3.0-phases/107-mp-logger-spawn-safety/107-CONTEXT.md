# Phase 107: MP-Logger Spawn Safety - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Make `MultiprocessingLogger` work correctly under both `fork` (Linux default) and `spawn` (macOS default) multiprocessing start methods, by creating its internal queue from a shared `spawn`-compatible multiprocessing context. The three previously-failing/skipped spawn-context analog tests must run and pass on both platforms.

This is requirement **INFRA-01** — a tightly-scoped, behavior-preserving **production-module change** to `src/python/common/multiprocessing_logger.py`. It is the lowest-priority item of slice 4 and must NOT expand into adjacent refactors. The only production behavior that changes is the multiprocessing context the queue is created from — not logging output, levels, destinations, or any public API.

**Origin:** Deferred out of Phase 102 (adversarial round 2, 2026-05-31). The original test-only plan (D-06/D-07/D-08: module-scope picklable target + `get_context('spawn')` in the tests, production unchanged) was proven insufficient by codex review + a live repro: the queue is created in the default (fork) context at `__init__`, so handing it to a `spawn` child raises `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context`. The correct fix requires a production change — which is now in scope here.

</domain>

<decisions>
## Implementation Decisions

### Production queue context
- **D-01:** The logger queue is created from a **`spawn`-compatible** multiprocessing context, created **unconditionally** (not branched on the active start method). Concretely: store a context obtained via `multiprocessing.get_context("spawn")` on the instance and create the queue from it (`ctx.Queue(-1)`), replacing the bare `multiprocessing.Queue(-1)` at `multiprocessing_logger.py:24`. Rationale: a `spawn`-context `SemLock` is safely shareable with **both** `fork` and `spawn` children, so a single always-spawn queue fixes macOS without regressing Linux. "Match the active start method" was rejected — it adds branching and a fork-context queue still breaks the instant any child is spawned, which is the exact bug.
- **D-02:** The spawn context is **stored on the instance** (e.g. `self.__mp_context`) so it can be exposed/reused. This lets the analog tests launch their child `Process` objects from the *same* context the queue belongs to (see D-04), and keeps queue + child on a single consistent context.

### Behavior preservation (COMPAT)
- **D-03:** No change to observable logging behavior — same `QueueHandler` wiring in `get_process_safe_logger()`, same listener-thread drain loop, same log levels/destinations, same public method signatures (`start`/`stop`/`propagate_exception`/`get_process_safe_logger`). Only the queue's originating context changes. Existing `fork`-based behavior on Linux is unchanged.

### Test strategy
- **D-04:** The three analog tests (`test_main_logger_receives_records` ~L215, `test_children_names` ~L245, `test_logger_levels` ~L270 in `test_multiprocessing_logger.py`) **explicitly exercise the spawn path on every platform**: promote each test's local `process_1` closure to a **module-level picklable function** (spawn requires importable targets), and launch the child `Process` via the **same spawn context** the logger now exposes (D-02), rather than the bare `multiprocessing.Process(...)` platform default. This deterministically exercises spawn on Linux CI too — so a future fork-only regression cannot slip through. "Rely on platform default only" was rejected as a weaker regression net.
- **D-05:** No test is deleted or skipped to accommodate the fix. The existing single-process tests (exception capture, propagate, empty-queue, clean-shutdown — L89-188) stay as-is. Keep the established multiprocessing-test idiom already in this file (`@pytest.mark.timeout`, `testfixtures.LogCapture`, bounded `join(timeout=...)`).

### Claude's Discretion
- Exact private attribute names (`__mp_context`, `__queue`) and whether the context is exposed via a property vs. passed into the test some other consistent way — planner/executor choose, as long as queue and test children share one spawn context.
- Exact module-level naming of the promoted picklable target functions.

</decisions>

<specifics>
## Specific Ideas

- The canonical fix shape from the Phase 102 deferral finding: `ctx = multiprocessing.get_context("spawn")` → `self.__queue = ctx.Queue(-1)`. The deferred D-06/D-07 (module-scope target + spawn-context Process in the tests) are now **valid and adopted** because the production queue is spawn-safe.
- Must stay green on both amd64 + arm64 CI and on a macOS dev machine (where the original repro was observed).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement & roadmap
- `.planning/REQUIREMENTS.md` §INFRA-01 (line 22) — full requirement statement; Cross-Cutting Constraints (COMPAT, CI green, coverage floor `fail_under` ≥ 88, safe observability, no release/tag work) lines 25-33.
- `.planning/ROADMAP.md` §"Phase 107: MP-Logger Spawn Safety" (lines 468-478) — phase goal + 4 success criteria.

### Origin of the deferred decision (READ — explains why this is a production change)
- `.planning/milestones/v1.3.0-phases/102-controller-concurrency-test-infra/102-CONTEXT.md` §"INFRA-01 — MultiprocessingLogger spawn-safe analog tests — DEFERRED" (D-06/D-07/D-08 superseded, lines 34-49) — the live-repro finding that test-only is insufficient and a shared spawn context is required.
- `.planning/codebase/CONCERNS.md` lines 53-54, 298-299 — MP-logger source audit detail (note: the `except Exception` silent-shutdown gap at `multiprocessing_logger.py:78` is a SEPARATE concern — out of scope here, see Deferred).

### Source under change
- `src/python/common/multiprocessing_logger.py` §`MultiprocessingLogger.__init__` (line 24, the `multiprocessing.Queue(-1)` to replace) — production module changed by this phase.
- `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` — the three analog tests to update (L215/L245/L270) + their local `process_1` closures to promote to module scope.

### Test conventions
- `.planning/codebase/TESTING.md` — Python multiprocessing test pattern (`@pytest.mark.timeout`, `testfixtures.LogCapture`, bounded `join`); regression tests tag the phase/issue ID in the title.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MultiprocessingLogger` (`src/python/common/multiprocessing_logger.py`) — single class; the only change point is the queue construction at L24 plus storing the context. Listener thread, QueueHandler wiring, and shutdown logic are untouched.
- Existing multiprocessing tests in `test_multiprocessing_logger.py` (L215-336) already use `testfixtures.LogCapture` and per-process targets — the spawn-safe versions follow the same shape with module-scope targets.

### Established Patterns
- **Module-scope picklable targets for `spawn`** — standard multiprocessing rule: `Process` targets must be importable, not closures. Adopted by D-04.
- **`testfixtures.LogCapture` + `@pytest.mark.timeout(N)`** — the established multiprocessing-test idiom in this file; keep it.
- **Coverage ratchet** — slice-1 floor `fail_under` ≥ 88 must hold or rise; INFRA-01 brings 3 previously-uncounted tests into the suite, so coverage holds or increases.

### Integration Points
- `MultiprocessingLogger` is consumed wherever cross-process logging is set up (controller/process spawn paths). The public surface (`start`/`stop`/`get_process_safe_logger`/`propagate_exception`) is unchanged, so no caller outside the module needs modification (COMPAT).

</code_context>

<deferred>
## Deferred Ideas

- **MP-logger listener silent-shutdown gap** (`multiprocessing_logger.py:78`, CONCERNS.md:298) — the `except Exception` branch sets `__listener_shutdown` and stops the listener on any handler error, silently dropping child logs thereafter. Same file, but a distinct reliability concern unrelated to spawn-safety. Out of scope for INFRA-01; note for a future phase/backlog.
- No global `multiprocessing.set_start_method(...)` change and no `conftest.py` start-method fixture — explicitly avoided. The fix is local to the logger's own context (queue) + the three tests' own context (children). Keeps blast radius minimal per INFRA-01's "must not expand the milestone" guard.

</deferred>

---

*Phase: 107-mp-logger-spawn-safety*
*Context gathered: 2026-06-01*
