# Phase 102: Controller Concurrency + Test Infra - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 102-CONTEXT.md — this log preserves the analysis.

**Date:** 2026-05-31
**Phase:** 102-controller-concurrency-test-infra
**Mode:** discuss (orchestrator-driven; decisions delegated to Claude via "you decide")
**Areas analyzed:** BUG-03 auto-delete Timer shutdown guard; INFRA-01 MultiprocessingLogger spawn-safe tests

## Pre-discussion finding (reshaped the phase)

Codebase scout (Explore subagent) + direct read of `controller.py` revealed that BUG-03's
**timer tracking + cancel-on-exit** infrastructure was **already implemented** during Phase 101's
Plan 05 (the SEC-01 auto-delete-timer cluster touched this code):

- `controller.py:190-191` — `self.__pending_auto_deletes: Dict[str, threading.Timer]` + `self.__auto_delete_lock`
- `controller.py:222-237` — `exit()` cancels every pending timer + clears the dict, under the lock
- `controller.py:815` — `__schedule_auto_delete` registers each timer
- `controller.py:834` — `__execute_auto_delete` pops itself on fire

⇒ ROADMAP criterion #1 already satisfied. The genuine remaining gap is criterion #2:
an already-fired callback mid-execution during shutdown checks no shutdown signal and can
still read the model + dispatch `delete_local`. Discussion focused on that gap + INFRA-01.

## Areas Presented

### BUG-03 — in-flight callback shutdown guard
| Question | Options | Decision |
|----------|---------|----------|
| How should a fired callback detect shutdown and no-op? | Dedicated `threading.Event` / reuse `__started` bool / guard at dispatch only | **Dedicated `threading.Event`** (set in `exit()` before cancel loop; checked at entry under `__auto_delete_lock`) |
| Should `exit()` drain in-flight callbacks before teardown? | No drain (guard is enough) / best-effort short join | **No drain** — daemon timers + entry guard suffice |

### INFRA-01 — spawn-safe analog tests
| Question | Options | Decision |
|----------|---------|----------|
| Shape of the promoted (module-scope) `process_1` target? | One parametrized module fn / three named module fns / planner decides | **One parametrized module fn** |
| How far should spawn coverage go? | Force `spawn` via `get_context('spawn')` in the 3 tests / module-scope fix only | **Force `spawn`** in the three tests (portable proof on Linux CI; no global start-method change) |

## Decisions Made

All four decisions resolved to the recommended option. The user reviewed the reshaped scope
(BUG-03 half-done) and delegated the specific choices with "you decide"; Claude selected the
standard lowest-risk options consistent with existing codebase patterns. See 102-CONTEXT.md
D-01 … D-08 for full rationale.

- **D-01:** BUG-03 timer tracking/cancel already exists (Phase 101 Plan 05) — do not re-implement criterion #1.
- **D-02:** Close criterion #2 with a dedicated `threading.Event`, set in `exit()`, checked at `__execute_auto_delete` entry under `__auto_delete_lock`.
- **D-03:** Do NOT reuse `__started` as the shutdown signal (muddy semantics; set False only after teardown).
- **D-04:** No drain/join of in-flight callbacks on exit (daemon timers + guard).
- **D-05:** Reuse `TestAutoDeleteToggleDuringTimer` real-Timer + Event-gated harness; land guard test-first.
- **D-06:** Promote `process_1` to one parametrized module-level function.
- **D-07:** Force `spawn` via `multiprocessing.get_context('spawn')` in the three tests only.
- **D-08:** `MultiprocessingLogger` production module + the tests' `log_capture.check(...)` assertions unchanged.

## Deferred Ideas

- Best-effort join/drain of in-flight callback threads on exit — rejected (D-04 rationale).
- Global/conftest spawn start-method override — rejected (would expand milestone; localized to 3 tests instead).
- BUG-01 / BUG-04 (Angular) — Phase 103.

## Reviewed Todos (not folded)

- `webob-cgi-upstream-unblock` (score 0.6) — upstream-blocked, unrelated.
- `migrate-config-set-to-post-body` (score 0.6) — separate-milestone API change, unrelated.
