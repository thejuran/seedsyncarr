# Phase 109: Controller Decomposition - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Decompose the `Controller` god-class (`src/python/controller/controller.py`, 1150 lines) into cohesive single-responsibility collaborators **inside the existing `controller/` package**. This is the final ARCH item of v1.3.0 slice 4 (ARCH-01).

This is a **behavior-preserving** refactor:
- No change to user-observable UI/CLI behavior, HTTP request/response contract, or on-disk config/persist format.
- The public surface the rest of the app depends on is **frozen**: the `controller/__init__.py` exports (`Controller`, `ControllerJob`, `ControllerPersist`, `AutoQueue`, `AutoQueuePersist`), the `Controller` constructor signature, `start()` / `process()` / `exit()`, all command entry-point method names, and the model-read interface the web layer uses (`get_model_files`, `get_model_files_and_add_listener`, `add_model_listener`, `remove_model_listener`, `is_file_stopped`, `is_file_downloaded`, `queue_command`).
- The existing Python test suite is the regression net and stays green **without modification or deletion** — including tests that `patch('controller.controller.<Name>')` and tests that import `Controller` internals.
- **No release/tag/version work** — the single `v1.3.0` tag is a milestone-end action after the batched pre-release walkthrough.

No file outside the `controller/` package may require modification to accommodate the decomposition.

</domain>

<decisions>
## Implementation Decisions

> The user delegated all four discussed gray areas to Claude's recommendation ("take your recommendation for all"). The decisions below are therefore locked recommendations grounded in the codebase analysis, not open questions. The planner/researcher implement to these.

### Collaborator split (seams)
- **D-01:** Decompose into **three new collaborator modules plus a coordinator facade**, following the package's existing extraction pattern (scan_manager, lftp_manager, file_operation_manager, model_builder, webhook_manager, memory_monitor are already pulled out of the central class):
  - `controller/command_processor.py` — command-queue dispatch: the `Command` inner class (or a moved equivalent), `queue_command`, `__process_commands`, and the four `__handle_{queue,stop,extract,delete}_command` methods (`controller.py:1009-1141`).
  - `controller/auto_delete_manager.py` — auto-delete lifecycle: `__schedule_auto_delete`, `__execute_auto_delete`, `__pending_auto_deletes`, the bounded BFS + coverage-check sequence, and the auto-delete lock+event machinery (`controller.py:823-1007`).
  - `controller/model_pipeline.py` — scan→build→diff→apply pipeline: `__update_model`, `_collect_scan_results`, `_collect_lftp_status`, `_collect_extract_results`, `_set_import_status`, `_update_active_file_tracking`, `_feed_model_builder`, `_detect_and_track_queued`, `_detect_and_track_download`, `_prune_extracted_files`, `_prune_downloaded_files`, `_apply_model_diff`, `_build_and_apply_model`, `_update_controller_status`, `__check_webhook_imports` (`controller.py:342-822`). This is the bulk of the line count.
- **D-02:** `controller.py` remains a **coordinator (thin facade)**, NOT fully dissolved. It keeps `__init__`, `start()` / `process()` / `exit()`, the run loop / `__propagate_exceptions`, the model + listener read-accessors the web layer depends on (`get_model_files`, `get_model_files_and_add_listener`, `add/remove_model_listener`, `is_file_stopped`, `is_file_downloaded`, `__get_model_files`), and delegates the three extracted responsibilities to the collaborators. Rationale: the model/listener read-surface is precisely what the web layer (`web/handler/controller.py`, `web/handler/stream_model.py`, `web_app.py`) calls, so it MUST stay on `Controller` to keep the public surface frozen (D-domain). Target: `controller.py` thinned toward ~350 lines; **no single new module exceeds ~350 lines** (criterion #1).

### Lock ownership across the split
- **D-03:** `Controller` **retains ownership** of `__model_lock`, `__auto_delete_lock`, and `__shutdown_event`; the collaborators receive the *same lock objects* via constructor injection. This is a pure code-move, NOT a locking redesign — **no new lock object and no new acquisition ordering are introduced** (criterion #4). The documented invariants are preserved verbatim:
  - `exit()` takes ONLY `__auto_delete_lock`, never `__model_lock` (`controller.py:240-244` comment block).
  - The auto-delete callback releases `__model_lock` before re-acquiring `__auto_delete_lock` for the final commit; lock order where both are held is `__model_lock` THEN `__auto_delete_lock` (`controller.py:983-997` comment block, WR-02 TOCTOU mitigation).
  - The "release lock before subprocess spawn" contract — `delete_local`/subprocess dispatch runs OUTSIDE the lock (`controller.py:823-833`, `:1004`). Never extend a lock to cover a subprocess spawn (CONCERNS.md:162).
- **D-04:** The auto-delete WR-02 ordering constraint (dispatch BEFORE `imported_children.pop` releases; coverage check inside the lock-held window) must survive the move into `auto_delete_manager.py` unchanged — the relative order of `pop` and `delete_local` dispatch is preserved (CONCERNS.md:180). The collaborator holds a reference to the injected lock + the model accessor it needs, but does not invent new synchronization.

### Test-internal coupling
- **D-05:** Preserve the exact `patch()` target names the existing suite depends on. `tests/unittests/test_controller/base.py:18-21` patches `controller.controller.ModelBuilder`, `controller.controller.LftpManager`, `controller.controller.ScanManager`, `controller.controller.FileOperationManager` by string path. Those names MUST remain importable/resolvable in the `controller.controller` module namespace after the refactor — i.e. the coordinator keeps importing (and constructing, or re-exporting) those manager classes so every `patch('controller.controller.X')` still resolves. `ControllerError` stays importable from `controller.controller` (`test_controller_unit.py:4`). **No test file is modified** (criterion #3, strict). If a collaborator needs one of those managers, it receives it from the coordinator rather than importing it under a new module path that would dodge the patch.

### Decomposition staging
- **D-06:** **Three sequential plans**, lowest-risk seam first, each landing green independently with the full Python suite as its gate:
  - `109-01` — extract `command_processor` (most self-contained; clearest public-contract boundary via `queue_command`).
  - `109-02` — extract `auto_delete_manager` (the thread-safety-critical seam; isolated after dispatch is already out).
  - `109-03` — extract `model_pipeline` (largest; done last when `controller.py` is already thinned).
  - Rationale: incremental waves give clean git-bisect and reviewable diffs for a high-risk refactor, and match how slice 4 already structures independent items. Sequential (not parallel) because all three touch the same `controller.py` coordinator and would conflict.

### Claude's Discretion
- Exact module/class names (`command_processor` vs `command_dispatcher`, `model_pipeline` vs `model_coordinator`) and whether collaborators are classes vs module-level functions — planner chooses, provided D-01..D-05 hold.
- Whether the `Command` inner class moves to `command_processor.py` or stays nested on `Controller` for import-compat — planner decides based on what keeps `Controller.Command` references (if any external/test) resolving.
- How collaborators receive their dependencies (constructor injection vs. a small context object) so long as injected locks are the *same* objects and no patch target breaks.
- Whether `__check_webhook_imports` lands in `model_pipeline` or stays on the coordinator — planner decides by cohesion, provided thread-safety docstrings move with it.

</decisions>

<specifics>
## Specific Ideas

- The decomposition must make the class **smaller and more cohesive without changing a single observable behavior** — the win is maintainability (CONCERNS.md:159-163 "god-class" entry), measured by per-module line count (~350 ceiling) and single-responsibility clarity, not by any new feature.
- Every multiline thread-safety docstring (the lock-ordering note at `:240-244`, the WR-02 TOCTOU block at `:983-997`, the "runs outside the lock" note at `:823-833`) must travel WITH the code it documents into the collaborator — these comments are the institutional memory that prevents a future contributor from re-introducing a deadlock or a TOCTOU.
- The existing extracted collaborators (`scan_manager.py`, `lftp_manager.py`, `file_operation_manager.py`) are the **style template** for the new ones — same construction-injection idiom, same `controller/`-package home.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — ARCH-01 (line 16), cross-cutting COMPAT (line 28), behavior-change guardrail (line 40), traceability ARCH-01 → Phase 109 (line 53).
- `.planning/ROADMAP.md` §"Phase 109: Controller Decomposition" — Goal + 5 success criteria (the locked acceptance contract; criterion #1 = module cohesion + ~350-line ceiling + facade, #2 = public-API frozen, #3 = suite unchanged, #4 = thread-safety invariants, #5 = COMPAT + no tag work).
- `.planning/codebase/CONCERNS.md` — "`Controller` god-class (1115 lines)" (lines 159-163, responsibilities + safe-modification rules), "Auto-delete BFS + coverage check sequence" (lines 177-181, WR-02 ordering), "Mutable model state pattern leaks through controller" (lines 13-16, protected-API freeze contract on `ModelFile`).

### Target source file
- `src/python/controller/controller.py` (1150 lines) — the god-class. Seam map: command dispatch `:1009-1141`; auto-delete lifecycle `:823-1007`; model/scan pipeline `:342-822`; coordinator/public surface `:95-341` + `:1099-1150`.

### Public-surface consumers (must keep compiling unchanged)
- `src/python/controller/__init__.py` — the package export list (frozen public API).
- `src/python/seedsyncarr.py:18,141` — constructs `Controller`, `ControllerJob`, `ControllerPersist`, `AutoQueue`, `AutoQueuePersist`.
- `src/python/web/web_app.py:12`, `src/python/web/web_app_builder.py:2,6` — construct `Controller`.
- `src/python/web/handler/controller.py:13`, `src/python/web/handler/stream_model.py:8` — call `queue_command` + model accessors.

### Regression net (must stay green, unmodified)
- `tests/integration/test_controller/test_controller.py` — integration coverage of the controller run loop.
- `tests/integration/test_web/test_handler/test_controller.py` — single + bulk command paths through the web layer.
- `tests/unittests/test_controller/base.py:18-21` — the `patch('controller.controller.{ModelBuilder,LftpManager,ScanManager,FileOperationManager}')` targets that constrain D-05.
- `tests/unittests/test_controller/test_auto_delete.py` — auto-delete edge cases (Phase 75 GH#19 D-01..D-16 + Phase 102 shutdown-guard); the auto_delete_manager extraction must keep all of these green.
- `tests/unittests/test_controller/test_controller_unit.py`, `test_controller_job.py`, `test_controller_persist.py`, `test_auto_queue.py` — import `Controller`/`ControllerError`/`ControllerJob`/`ControllerPersist` internals.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The `controller/` package already contains extracted collaborators — `scan_manager.py`, `lftp_manager.py`, `file_operation_manager.py`, `model_builder.py`, `webhook_manager.py`, `memory_monitor.py`, `auto_queue.py`, `controller_persist.py`. These are the construction-injection style template for the three NEW collaborators; the decomposition continues an in-progress extraction rather than inventing a new pattern.
- `controller/__init__.py` is the single public-export choke point — keeping its export list identical is the cheapest way to satisfy "no external file changes."

### Established Patterns
- Collaborators are constructed in `Controller.__init__` and held as private fields; thread-safety lives in the central class's lock fields. The new split keeps the locks central (D-03) and injects them, matching how the central class already coordinates the existing managers.
- Tests patch dependencies by their *imported name in `controller.controller`* (`patch('controller.controller.ScanManager')`), not by their definition module. This is the hard constraint (D-05): the patch resolves against wherever the name is bound in `controller.controller`, so the coordinator must keep binding those names.
- Lock discipline is documented inline, not enforced structurally — every relevant method carries a docstring explaining its lock contract. Moving a method means moving its docstring (specifics).

### Integration Points
- The web layer reads the model exclusively through `Controller`'s accessor methods and `queue_command`; it never touches the scan/auto-delete internals. So the model-read accessors must stay on the coordinator (D-02) while everything behind them can move freely.
- `seedsyncarr.py` wires `Controller` + `ControllerJob` + persistence at startup; the constructor signature is part of the frozen surface (criterion #2).
- `__shutdown_event` + `exit()` couple the auto-delete manager to controller shutdown — the event is injected so `exit()` (staying on the coordinator) and the auto-delete callback (moving to the collaborator) still set/read the *same* event under the *same* lock (Phase 102's BUG-03 guarantee must survive).

</code_context>

<deferred>
## Deferred Ideas

- The CONCERNS.md "Mutable model state pattern leaks through controller" item (protected `_unfreeze()`/`_set_parent()`/`_replace_children()` access on `ModelFile`, `controller.py:355-381`) is a real fragility but is a **separate design concern**, not part of this behavior-preserving move-only refactor — do not change the freeze contract here.
- The "bulk command timeouts can leave commands queued" concern (CONCERNS.md:69-72, in `web/handler/controller.py`, not this file) is a distinct bug for another phase.
- Coalescing consecutive `UPDATED` model events / the 0.5s busy-poll (CONCERNS.md:140, 149) is a performance idea, out of scope for ARCH-01.
- Full single+bulk dispatch unification (deferred from Phase 108 D-03) remains deferred.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock.md` (score 0.9, area: testing) — **not folded.** Already tracked as a Deferred Item in STATE.md ("testing — blocked on upstream webob 2.0"). Unrelated to controller decomposition; blocked externally.
- `2026-04-24-migrate-config-set-to-post-body.md` (score 0.9, area: security) — **not folded.** Already tracked as a Deferred Item in STATE.md ("security — API contract change, separate milestone"). It is an HTTP-contract change, which directly contradicts this phase's behavior-preserving / frozen-contract boundary.

</deferred>

---

*Phase: 109-controller-decomposition*
*Context gathered: 2026-06-01*
