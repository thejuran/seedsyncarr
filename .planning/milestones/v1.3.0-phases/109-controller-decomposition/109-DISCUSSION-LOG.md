# Phase 109: Controller Decomposition - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 109-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-06-01
**Phase:** 109-controller-decomposition
**Mode:** discuss
**Areas analyzed:** Collaborator split (seams), Lock ownership across split, Test-internal coupling, Decomposition staging

## Gray Areas Presented

The four gray areas were surfaced from a structural scan of `src/python/controller/controller.py` (1150 lines), the existing `controller/` package layout, the external import graph, the test-patch targets, and CONCERNS.md's god-class / auto-delete entries.

| Area | Question put to user | Options framed |
|------|----------------------|----------------|
| Collaborator split (seams) | Which responsibilities become separate modules; facade vs coordinator | 3-seam analysis: model/scan pipeline, auto-delete lifecycle, command dispatch |
| Lock ownership across split | Do collaborators own their locks, or does Controller keep + inject them | Deadlock-risk decision tied to criterion #4 |
| Test-internal coupling | Keep `patch('controller.controller.X')` targets resolvable, or allow test-base adjustment | Criterion #3 forbids test changes |
| Decomposition staging | One big-bang plan vs incremental waves | Bisect/review safety vs plan count |

## User Response

- **Selection:** "take your recommendation for all" — the user delegated all four gray areas to Claude's recommendation rather than choosing per-area.

## Decisions Recorded (Claude's recommendation, locked)

### Collaborator split (seams)
- **Original framing:** 3 candidate seams + facade-vs-coordinator open.
- **Decision (D-01/D-02):** Three new collaborator modules — `command_processor.py`, `auto_delete_manager.py`, `model_pipeline.py` — plus `controller.py` retained as a thin **coordinator** holding `__init__`/`start`/`process`/`exit`/run-loop and the model-read accessors the web layer depends on. No new module > ~350 lines; coordinator thinned toward ~350.
- **Reason:** Continues the package's in-progress extraction pattern (scan/lftp/file-operation managers already pulled out); keeps the web-layer read-surface on `Controller` to freeze the public API.

### Lock ownership across split
- **Decision (D-03/D-04):** `Controller` retains `__model_lock`, `__auto_delete_lock`, `__shutdown_event`; collaborators receive the *same* objects via constructor injection. Pure code-move — no new lock, no new ordering. All documented invariants (exit() takes only auto_delete_lock; model→auto_delete order; release-lock-before-subprocess; WR-02 dispatch-before-pop) preserved verbatim.
- **Reason:** Lowest-deadlock-risk path for criterion #4; a locking *redesign* would be the riskiest possible interpretation of a behavior-preserving refactor.

### Test-internal coupling
- **Decision (D-05):** Keep `controller.controller.{ModelBuilder,LftpManager,ScanManager,FileOperationManager}` and `ControllerError` resolvable in the `controller.controller` namespace so every existing `patch(...)`/import target still binds. No test file modified.
- **Reason:** Criterion #3 is strict ("no test changed or deleted"); `mock.patch` resolves against the name's binding site, so the coordinator must keep binding those names.

### Decomposition staging
- **Decision (D-06):** Three sequential plans — `109-01` command dispatch → `109-02` auto-delete → `109-03` model pipeline — each gated on the full Python suite. Sequential (not parallel) because all touch the same coordinator.
- **Reason:** Clean bisect + reviewable diffs for a high-risk refactor; lowest-risk seam first, largest seam last after the class is already thinned.

## Deferred Ideas

- ModelFile freeze-contract / protected-API leak (CONCERNS.md:13-16) — separate design concern, not this move-only refactor.
- Bulk-command-timeout-leaves-queued (CONCERNS.md:69-72) — distinct bug, different file/phase.
- UPDATED-event coalescing / 0.5s busy-poll (CONCERNS.md:140,149) — performance, out of scope.
- Single+bulk dispatch unification — remains deferred from Phase 108 D-03.

## Reviewed Todos (not folded)

- `2026-04-21-webob-cgi-upstream-unblock.md` (score 0.9) — already a STATE.md Deferred Item, blocked on upstream webob 2.0; unrelated to controller decomposition.
- `2026-04-24-migrate-config-set-to-post-body.md` (score 0.9) — already a STATE.md Deferred Item; an HTTP-contract change, which contradicts this phase's frozen-contract boundary.

## Claude's Discretion (handed to planner)

- Exact module/class names; classes vs module-level functions.
- Whether `Command` inner class moves or stays nested (import-compat driven).
- Dependency-injection shape (constructor vs context object), provided injected locks are the same objects.
- Whether `__check_webhook_imports` lands in `model_pipeline` or stays on the coordinator.
