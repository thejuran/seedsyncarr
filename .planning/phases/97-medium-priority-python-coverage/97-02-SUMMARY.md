---
phase: 97-medium-priority-python-coverage
plan: 02
subsystem: testing-common
tags: [coverage, python, multiprocessing, logging, threading, COVMED-01]
requires:
  - "97-01 (coverage baseline captured before phase-97 tests land)"
provides:
  - "Full-path coverage of common/multiprocessing_logger.py:67-86 listener lifecycle (100% line+branch)"
affects:
  - "Phase 100 CI threshold ratchet — adds covered lines/branches to the Python total"
tech-stack:
  added: []
  patterns:
    - "In-process queue drive: call get_process_safe_logger() in the test process (not a spawned child) and restore the root logger handlers synchronously after enqueue to break the propagate->re-enqueue feedback loop — spawn-safe, deterministic"
    - "Module-scope sentinel exception + raising logging.Handler to drive the listener's outer except branch"
    - "Assert listener exception state only via the public propagate_exception() (raise then no-op), never the name-mangled __listener_exc_info"
key-files:
  created: []
  modified:
    - "src/python/tests/unittests/test_common/test_multiprocessing_logger.py"
decisions:
  - "Drive records in-process rather than via multiprocessing.Process: macOS Python 3.12 defaults to the spawn start method, which cannot pickle the existing tests' local-closure process targets; in-process drive is platform-independent and the plan explicitly sanctions it"
  - "Synchronously restore the root logger's handlers immediately after enqueue: the listener handles records on a logger that propagates to root; leaving the QueueHandler on root would re-enqueue every handled record forever"
  - "No source change to multiprocessing_logger.py — the outer except correctly captures and propagate_exception correctly surfaces; D-05 trivial-fix posture did not trigger, nothing to defer"
metrics:
  duration: ~20m
  completed: 2026-05-29
requirements: [COVMED-01]
---

# Phase 97 Plan 02: MultiprocessingLogger Listener-Thread Shutdown Coverage Summary

Added five timeout-guarded tests to `TestMultiprocessingLogger` that drive the real
listener thread through all four documented branches of the `__listener` loop
(`common/multiprocessing_logger.py:67-86`): a handler raising during `handle(record)`
makes the listener stash `exc_info` and set shutdown; `propagate_exception()` re-raises
that exact exception and is a no-op on the second call; an inner-loop `queue.Empty` break
does NOT terminate the listener (records sent after an empty cycle are still received);
and a clean `stop()` joins without raising — proven non-hollow by asserting a real record
was RECEIVED via `LogCapture` before shutdown. The five new tests alone bring
`multiprocessing_logger.py` to **100% line and branch coverage**. COVMED-01 closed.

## What Was Built

- **`test_listener_captures_handler_exception_and_shuts_down`** — attaches a sentinel-raising
  `logging.Handler` to the child logger the listener routes to (`...MPLogger.process_1`),
  enqueues one real ERROR record, and proves the listener stashed the exception + set
  shutdown via `assertRaises` on `propagate_exception()` (lines 75 → 78-83).
- **`test_propagate_exception_reraises_captured`** — asserts `propagate_exception()` re-raises
  the SAME type (`_ListenerSentinelError`) and message the failing handler raised (lines 38-46).
- **`test_propagate_exception_second_call_is_noop`** — after the first call re-raises (clearing
  `exc_info` to `None` at line 45), the second call returns `None` without raising.
- **`test_inner_queue_empty_does_not_terminate_listener`** — sends a record, sleeps past
  `__LISTENER_SLEEP_INTERVAL_IN_SECS` (0.1s) so the inner loop hits `queue.Empty` and breaks
  (line 77) while the outer `while not __listener_shutdown` continues (branch 70->…), sends
  MORE records, and asserts the later batch is still received via `LogCapture` — proving the
  listener survived the empty-queue cycle.
- **`test_clean_shutdown_joins_without_error`** — NON-HOLLOW: enqueues one real record and
  asserts it was RECEIVED via `LogCapture` BEFORE `stop()` (a no-op stop against an idle
  listener cannot pass), then `stop()` joins the thread without raising and
  `propagate_exception()` is a no-op (line 85 sleep + shutdown-event loop exit).
- **Shared test scaffolding:** module-scope `_ListenerSentinelError` + `_RaisingHandler`, and a
  `_drive_record_in_process` helper that enqueues a record via `get_process_safe_logger()` and
  restores the root logger handlers synchronously to avoid the propagate→re-enqueue loop and to
  prevent leaking `QueueHandler`s into other tests.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Handler-raise capture + propagate_exception re-raise/no-op (3 tests) | `2197ac9` | `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` |
| 2 | Empty-queue resilience + non-hollow clean shutdown (2 tests) | `fcdda45` | `src/python/tests/unittests/test_common/test_multiprocessing_logger.py`, `.planning/phases/97-medium-priority-python-coverage/deferred-items.md` |

## TDD Notes

Both tasks were written test-first per the `tdd="true"` markers. Because COVMED-01 is a
*coverage* plan against already-correct source, the "RED" expectation is that the new tests
exercise previously-uncovered branches (verified via `--cov-report=term-missing`), not that
the feature is absent. Task 1's three tests passed on first run (the source behavior they
cover already exists); Task 2's two tests legitimately went RED first — the initial
`_drive_record_in_process` left the `QueueHandler` on the root logger, so the listener
re-enqueued every handled record in an infinite loop (LogCapture saw the same record hundreds
of times). Fixed by restoring the root logger handlers synchronously after enqueue; both
tests then passed. No `feat`/`refactor` source commits because no production code changed.

## Coverage Achieved

`multiprocessing_logger.py` measured with the five new tests in isolation:
```
Name                                Stmts   Miss Branch BrPart  Cover   Missing
common/multiprocessing_logger.py      53      0      6      0   100%
```
All four documented branches covered: handler-raise (75→78-83), propagate re-raise + no-op
(38-46), inner `queue.Empty` non-termination (77), clean shutdown (85 + shutdown-event exit).

## Verification

- `poetry run pytest tests/unittests/test_common/test_multiprocessing_logger.py` — the 5 new
  tests pass; under the CI/Linux `fork` start method ALL 8 tests in the file pass (verified by
  forcing `fork` on this host → `8 passed`).
- No name-mangled access: `grep -c '_MultiprocessingLogger__' …test_multiprocessing_logger.py` = **0**.
- All 5 new tests carry `@pytest.mark.timeout(5)`.
- The clean-shutdown test asserts a real record received BEFORE `stop()` (non-hollow).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provisioned lockfile-pinned Python dev dependencies**
- **Found during:** Pre-Task 1 setup.
- **Issue:** The worktree had no installed venv; `pytest` / `testfixtures` / `pytest-timeout`
  were absent so the test command could not run.
- **Fix:** Ran `poetry install` — installs already-committed, lockfile-pinned deps (`poetry.lock`).
  Not a `poetry add` of an unverified package, so the Rule-3 slopsquat exclusion does not apply.
- **Files modified:** None tracked (only the gitignored venv).
- **Commit:** n/a.

**2. [Rule 3 - Blocking] In-process drive instead of child-process spawn**
- **Found during:** Task 1.
- **Issue:** The existing analog tests pass a local-closure `process_1` as a
  `multiprocessing.Process` target. macOS Python 3.12 defaults to `spawn`, which pickles the
  target; local closures are unpicklable, so copying that drive pattern verbatim would fail
  on this host.
- **Fix:** Drove records in-process via `get_process_safe_logger()` (sanctioned by the plan
  as an alternative), with synchronous root-logger restoration after enqueue to prevent the
  propagate→re-enqueue feedback loop. Platform-independent and deterministic.
- **Files modified:** `src/python/tests/unittests/test_common/test_multiprocessing_logger.py`.
- **Commit:** `2197ac9` (helper), `fcdda45` (hardening).

### D-05 Trivial-fix Posture

Not triggered. The outer `except Exception` (line 78) correctly captures the handler
exception and `propagate_exception()` correctly surfaces it — proven by
`test_propagate_exception_reraises_captured`. No swallow bug was found, so no inline fix
and no v1.4.0 deferral are needed for the listener code.

## Deferred / Out-of-Scope (logged, NOT fixed)

Pre-existing macOS-only failures in the three analog tests
(`test_main_logger_receives_records`, `test_children_names`, `test_logger_levels`) caused by
the `spawn` start method being unable to pickle their local-closure `Process` targets. These
pass on Linux/CI (`fork`) — confirmed all 8 pass when `fork` is forced on this host. Out of
scope (pre-existing, not authored by this plan); recorded in
`.planning/phases/97-medium-priority-python-coverage/deferred-items.md` as a v1.4.0 candidate.

## Authentication Gates

None.

## Known Stubs

None — the five tests drive the real listener thread and assert real behavior.

## Threat Flags

None — no new security surface. The threat-register item T-97-02-01 (listener exception
captured and surfaced rather than silently killing logging) is now covered by
`test_listener_captures_handler_exception_and_shuts_down` and
`test_propagate_exception_reraises_captured`.

## Notes for Orchestrator

- STATE.md and ROADMAP.md were NOT modified (parallel worktree executor).
- `.planning/HANDOFF.json` is a pre-existing untracked file from before this plan — left untouched.
- COVMED-01 can be marked complete in REQUIREMENTS.md by the orchestrator.

## Self-Check: PASSED

- Test file exists: FOUND `src/python/tests/unittests/test_common/test_multiprocessing_logger.py`
- deferred-items.md exists: FOUND `.planning/phases/97-medium-priority-python-coverage/deferred-items.md`
- Task 1 commit exists: FOUND `2197ac9`
- Task 2 commit exists: FOUND `fcdda45`
- 5 new tests present, all `@pytest.mark.timeout(5)`, 0 name-mangled accesses, 100% module coverage.
