# Phase 102: Controller Concurrency + Test Infra - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

**One scoped fix this phase — a concurrency hardening.** (INFRA-01, the second item originally scoped here, was DEFERRED during adversarial review — see Decisions and the Deferred section.)

1. **BUG-03** — auto-delete `threading.Timer` lifecycle is safe across controller shutdown. Pending timers are tracked and cancelled on `exit()` (**already implemented in Phase 101's Plan 05** — see Code Context), and a callback that has **already fired** and is mid-execution when shutdown begins must detect shutdown and **no-op** — performing no model read, no persist-state mutation, and no `delete_local` dispatch against a half-torn-down controller, with the final guard+dispatch **serialized on `__auto_delete_lock`** (adversarial round 2).
2. ~~**INFRA-01** — the three `MultiprocessingLogger` analog tests pass under both `fork` and `spawn`.~~ **DEFERRED out of Phase 102 (adversarial round 2, 2026-05-31).** Codex review + a live repro proved the test-only fix is insufficient: the `MultiprocessingLogger` queue is created in the default (fork) context, so handing it to a `spawn` child raises `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context`. A correct fix needs the queue created from a shared `spawn` context — a production-module change that exceeds INFRA-01's "lowest priority; must not expand the milestone, test-only" constraint. Re-filed to a later v1.3.0 slice. **Phase 102 is now BUG-03 only.**

Scope anchor from ROADMAP.md (Phase 102) — fixed. Phase 101 (webhook + log-injection) is done; Phase 103 (Angular defects: BUG-01, BUG-04) is out of scope here.

**Cross-cutting (locked by REQUIREMENTS.md):** COMPAT — existing config files and on-disk persist formats load unchanged, no new *required* fields; CI green amd64+arm64 (Python); Python `fail_under` ≥ 88 holds or rises; no concurrency fix logs sensitive data, generic client errors with server-side detail; **no release/tag/version work**.
</domain>

<decisions>
## Implementation Decisions

### BUG-03 — Auto-delete Timer in-flight shutdown guard
- **D-01 (key finding — narrows scope):** The timer **tracking + cancel-on-exit** half of BUG-03 already exists in the codebase as of Phase 101's Plan 05. `controller.py` already has `self.__pending_auto_deletes: Dict[str, threading.Timer]` (line 190) + `self.__auto_delete_lock` (line 191); `exit()` cancels every pending timer and clears the dict under the lock (lines 226-230); `__schedule_auto_delete` registers each timer (line 815); `__execute_auto_delete` pops itself on fire (line 834). **ROADMAP criterion #1 ("timers tracked + cancelled on shutdown; none armed after exit") is therefore already satisfied — do NOT re-implement it.** Planning must verify this with a test if one does not already cover it, but the production change for #1 is a no-op.
- **D-02 (STRENGTHENED — adversarial round 2):** The remaining gap is **ROADMAP criterion #2**: an already-fired callback mid-execution during shutdown does not check any shutdown signal — it still acquires `__model_lock`, reads the model (`controller.py:859-866`), mutates persist state (`imported_children.pop`, `controller.py:958`), and may dispatch `delete_local` (`controller.py:972`). Close it with a **dedicated `threading.Event`** checked at **TWO points**, with the second point **serialized on `__auto_delete_lock`** so there is no preempt-after-check race:
  - Add `self.__shutdown_event = threading.Event()` in `__init__`.
  - `exit()` calls `self.__shutdown_event.set()` **under `__auto_delete_lock`**, inside the same lock acquisition that does the timer cancel loop (so the set is ordered against the callback's lock-guarded commit step).
  - `__execute_auto_delete` checks `self.__shutdown_event.is_set()` at **entry** under `__auto_delete_lock` (cheap early-out for the common case) — returns early, no model read.
  - At the **final commit step**, `__execute_auto_delete` acquires `__auto_delete_lock` and, **within that lock**, performs: `if self.__shutdown_event.is_set(): return` → `imported_children.pop(...)` → resolve the file → release lock → `delete_local(file)`. Because `exit()` sets the event under the *same* lock, "shutdown begins before the commit step ⇒ no pop and no dispatch" holds strictly. The `delete_local` call itself stays outside the lock (it spawns a subprocess; holding the lock across it would starve other timer ops) — but the guard immediately precedes it within the serialized decision, so the only residual window is a dispatch that was already committed-to before shutdown, which is correct behavior.
  - **Why both points:** the entry check alone leaves a TOCTOU hole (codex blocker, adversarial round 2): a callback passes entry (event unset), blocks on `__model_lock`/BFS while `exit()` sets the event + stops `__file_op_manager`, then dispatches against a stopped subsystem. The lock-serialized final guard closes it; the `imported_children.pop` moving inside the guarded window also prevents "delete-succeeded" persist state when no delete ran.
- **D-03:** **Do NOT reuse the existing `__started` bool** as the shutdown signal. `__started` is a "has start() run / is running" flag (set True in `start()`, False at the end of `exit()`), and `exit()` only sets it False *after* the teardown sequence — so it is not a clean "shutdown has begun" barrier. A dedicated Event has unambiguous semantics and is the threading-safe primitive for cross-thread signalling.
- **D-04 (drain policy):** **No drain / no join of in-flight callback threads on exit.** Timers are daemon threads (`timer.daemon = True`, line 814). The lock-serialized D-02 guard (event set under `__auto_delete_lock` in `exit()`; final guard+pop+dispatch decision under the same lock) makes a fired callback no-op without a thread join: `exit()` sets the event + cancels + clears under the lock, then proceeds to teardown. The lock — not a join — is what serializes shutdown against dispatch, so no shutdown-latency window or thread bookkeeping is added. (The only callback that still dispatches is one that already passed the lock-guarded commit *before* `exit()` acquired the lock to set the event — i.e. dispatch was already correctly committed-to; that is intended behavior, not a race.)
- **D-05 (test-first):** A slice-1 regression suite already pins the current toggle/dry-run behavior of `__execute_auto_delete`: `test_auto_delete.py` class `TestAutoDeleteToggleDuringTimer` (real `threading.Timer`, Event-gated to land a config flip before the callback re-reads — see Code Context). **Reuse that harness** for the new shutdown-guard test (schedule via the real path, set `__shutdown_event` before releasing the callback, assert no `delete_local` and no model read). Land the guard test-first (red → green). Those existing toggle/dry-run tests MUST still pass unchanged.

### INFRA-01 — MultiprocessingLogger spawn-safe analog tests — ⚠️ DEFERRED OUT OF PHASE 102
- **D-06 / D-07 / D-08 (SUPERSEDED — INFRA-01 deferred, adversarial round 2, 2026-05-31):** The original plan was test-only — promote `process_1` to a module-level picklable target (D-06) + force `multiprocessing.get_context('spawn')` (D-07) with the production module unchanged (D-08). Adversarial review (codex) + a **live repro on this machine** proved this is insufficient: `MultiprocessingLogger.__init__` creates `self.__queue = multiprocessing.Queue(-1)` in the **default (fork on Linux) context**, and passing that queue to a `spawn`-context child fails at `p.start()` with `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context`. The only correct fix creates the queue from a **shared `spawn` context** (`ctx.Queue()`), which is a **production-module change** — that violates D-08 (test-only) and INFRA-01's REQUIREMENTS.md guard ("lowest priority; include only if it does not expand the milestone"). **INFRA-01 is therefore deferred to a later v1.3.0 slice** where a `MultiprocessingLogger` production change is in scope. No INFRA-01 plan ships in Phase 102; `102-02-PLAN.md` was removed.

### Claude's Discretion
- Exact name of the BUG-03 `threading.Event` attribute.
- Whether the D-02 guard's early-return emits a debug log line (if it does, the file_name must pass through `sanitize_log_value()` per the SEC-01 convention already in this file).
- Whether to add an explicit test asserting criterion #1 (no timer armed after `exit()`) if no existing test already covers it.
- Test placement for the new shutdown-guard test (new method in `TestAutoDeleteToggleDuringTimer` vs a sibling class).
- The exact patched hook used to set `__shutdown_event` mid-callback in Test B (e.g. a `get_children` side-effect on a directory root, or patching the eligibility path) — must be a real seam in `__execute_auto_delete`.
</decisions>

<specifics>
## Specific Ideas

- BUG-03 turned out to be **half-done already** — the discussion narrowed it from "implement timer tracking + cancellation + guard" to "add the in-flight callback guard only; verify the rest with tests." Don't let the planner re-derive the already-landed tracking/cancel work.
- INFRA-01 is explicitly **lowest priority and must not expand the milestone** (REQUIREMENTS.md line 23). Keep it a tight test-only change: promote target to module scope + force spawn context in the three tests. No global start-method change, no conftest fixture.
- Land the BUG-03 guard test-first, reusing the existing real-Timer + Event-gated harness from `TestAutoDeleteToggleDuringTimer`.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (source of truth)
- `.planning/REQUIREMENTS.md` — BUG-03 (line 15) + INFRA-01 (line 23) full statements; Cross-Cutting Constraints (COMPAT, CI green, coverage floors ≥88, safe observability, no-release) lines 25-33; Out-of-Scope table lines 35-45.
- `.planning/ROADMAP.md` §"Phase 102: Controller Concurrency + Test Infra" (lines 446-456) — phase goal + 4 success criteria (criterion #1 already satisfied per D-01; criterion #2 is the real work; criterion #3 = INFRA-01; criterion #4 = COMPAT cross-cutting).
- `.planning/codebase/CONCERNS.md` — original Known-Bugs audit detail for BUG-03 (auto-delete Timer lifecycle) and INFRA-01 source.

### Code surfaces (read before implementing)
- `src/python/controller/controller.py`:
  - `__init__` lines 189-193 — existing `__pending_auto_deletes` dict + `__auto_delete_lock` + `__started`; **add `__shutdown_event` here (D-02)**.
  - `exit()` lines 222-237 — already cancels/clears timers under the lock (D-01); **add `__shutdown_event.set()` before the cancel loop (D-02)**.
  - `__schedule_auto_delete` lines 804-819 — registers timer in the dict (already done).
  - `__execute_auto_delete` lines 821-973 — fired-callback body; **add the `__shutdown_event.is_set()` early-return at entry, under `__auto_delete_lock` at lines 833-834 (D-02)**. Config re-read (enabled/dry_run) at lines 837-848; model read under `__model_lock` at 859-866; `delete_local` dispatch at line 972.
- `src/python/tests/unittests/test_controller/test_auto_delete.py` §`TestAutoDeleteToggleDuringTimer` (lines ~469-611) — slice-1 real-Timer + Event-gated regression harness to reuse for the BUG-03 guard test (D-05); methods `test_disabled_flip_during_timer_window_skips_delete`, `test_dry_run_flip_during_timer_window_skips_delete`, `test_no_flip_during_timer_window_deletes`.
- `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` — three tests to fix (`test_main_logger_receives_records` ~215, `test_children_names` ~245, `test_logger_levels` ~270); each defines a local `process_1` closure passed to `multiprocessing.Process(target=...)` (D-06/D-07).
- `src/python/common/multiprocessing_logger.py` §`MultiprocessingLogger` — module under test; **unchanged** by INFRA-01 (D-08).

### Conventions
- `.planning/codebase/CONVENTIONS.md` — Python thread-safety ("copy-under-lock"), logging via `context.logger.getChild(...)`, `sanitize_log_value()` for any logged remote-/user-supplied string, no mutable default args, specific-exception catches.
- `.planning/codebase/TESTING.md` — Python multiprocessing test pattern (`@pytest.mark.timeout`, `testfixtures.LogCapture`, `join(timeout=...)`); regression tests tag the phase/issue ID in the title.

### No external specs
This phase is bug/test work against existing code — no ADRs or feature specs beyond the requirements/roadmap above.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Timer tracking infra already present** — `__pending_auto_deletes` dict + `__auto_delete_lock` + cancel-on-exit loop (`controller.py:190-191, 226-230, 815, 834`). BUG-03 criterion #1 reuses this as-is; only the in-flight guard (criterion #2) is new code.
- **Real-Timer + Event-gated test harness** — `TestAutoDeleteToggleDuringTimer` (`test_auto_delete.py`) schedules via the real `__schedule_auto_delete` path with a short delay and a `threading.Event` to deterministically order a config flip before the callback re-reads. Directly reusable for the shutdown-guard test.
- **`sanitize_log_value()`** already imported and used throughout `controller.py` — any new log line in the guard path uses it.
- **`testfixtures.LogCapture` + `@pytest.mark.timeout(5)`** — the established multiprocessing-test idiom in `test_multiprocessing_logger.py`.

### Established Patterns
- **Copy-under-lock / lock-scoped state mutation** — `__execute_auto_delete` already does its dict pop and all model reads under locks; the D-02 guard slots into the existing `__auto_delete_lock` window at entry (lines 833-834), no new lock.
- **Daemon timers** — auto-delete timers set `timer.daemon = True`; shutdown does not need to join them (D-04).
- **Module-scope picklable targets for `spawn`** — the INFRA-01 fix follows the standard multiprocessing rule that `Process` targets must be importable (module-level), not closures.

### Integration Points
- BUG-03 touches **only** `controller.py` (`__init__`, `exit()`, `__execute_auto_delete`) + its test file. No config, no web, no model-API change → COMPAT trivially holds (no new fields, no persist-format change).
- INFRA-01 touches **only** `test_multiprocessing_logger.py` (test-only) → no production surface, COMPAT trivially holds.
- The two fixes are independent (different files, different requirements) — can be separate plans / separate waves with no ordering dependency.
</code_context>

<deferred>
## Deferred Ideas

- **INFRA-01 (MultiprocessingLogger spawn-safe analog tests) — DEFERRED to a later v1.3.0 slice (adversarial round 2, 2026-05-31).** The test-only fix (module-scope target + `get_context('spawn')`) was proven insufficient: the logger's queue is created in the default (fork) context, so a `spawn` child errors at `p.start()` with `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context` (codex finding, confirmed by live repro). A correct fix needs the queue created from a shared `spawn` context — a `MultiprocessingLogger` **production-module change** — which exceeds INFRA-01's "lowest priority; must not expand the milestone" guard. Re-file to a slice where that production change is in scope. `102-02-PLAN.md` was removed from this phase.
- **Best-effort join/drain of in-flight callback threads on exit** — considered for D-04, rejected as unnecessary given daemon timers + the lock-serialized guard; adds shutdown latency and thread bookkeeping for no benefit over the lock. Revisit only if a real shutdown-during-delete defect is observed.
- BUG-01, BUG-04 (Angular defects) — Phase 103, out of scope here.

### Reviewed Todos (not folded)
- `todo.match-phase 102` returned 2 matches, both score 0.6 on generic keywords (`test`, `python`, `server`, `config`) — **neither folded**:
  - `webob-cgi-upstream-unblock` — blocked on upstream webob 2.0; unrelated to BUG-03/INFRA-01.
  - `migrate-config-set-to-post-body` — a separate-milestone API contract change (per STATE.md deferred items); unrelated to this phase.
</deferred>

---

*Phase: 102-controller-concurrency-test-infra*
*Context gathered: 2026-05-31*
