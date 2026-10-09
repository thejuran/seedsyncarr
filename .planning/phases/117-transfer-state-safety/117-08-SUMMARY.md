---
phase: 117-transfer-state-safety
plan: 08
subsystem: controller
tags: [python, lftp-manager, model-builder, model-pipeline, command-processor, submitted-unobserved, b2]
requires: ["117-05", "117-06"]
provides:
  - "LftpManager.submitted_unobserved_file_names(): names lftp accepted a QUEUE for but no successful status has observed yet"
  - "ModelBuilder.set_submitted_files(): such names build as QUEUED when they have no lftp status"
  - "CommandProcessor execution-time guard: extract/delete refuse (409) and queue skips re-submit for a submitted-unobserved name"
affects:
  - src/python/controller/lftp_manager.py
  - src/python/controller/model_builder.py
  - src/python/controller/model_pipeline.py
  - src/python/controller/command_processor.py
tech-stack:
  added: []
  patterns: ["in-process submitted set reconciled by the next successful observation", "execution-time guard against same-batch command ordering"]
key-files:
  created:
    - .planning/phases/117-transfer-state-safety/deferred-items.md
  modified:
    - src/python/controller/lftp_manager.py
    - src/python/controller/model_builder.py
    - src/python/controller/model_pipeline.py
    - src/python/controller/command_processor.py
    - src/python/tests/unittests/test_controller/test_lftp_manager.py
    - src/python/tests/unittests/test_controller/test_model_builder.py
    - src/python/tests/unittests/test_controller/test_controller_unit.py
decisions:
  - "The submitted-but-unobserved set is owned by LftpManager, surfaced as the existing QUEUED state through ModelBuilder, synced by ModelPipeline each cycle, and consulted directly by CommandProcessor at execution time"
  - "Any list-returning status (including []) clears the whole set; None leaves it; LftpManager.kill discards only the killed name after Lftp.kill returns"
  - "A repeated QUEUE for a submitted-unobserved name is an idempotent success without a second lftp job; STOP handler unchanged"
metrics:
  duration: "~10m"
  completed: 2026-10-08
  tasks: 3
  files: 7
requirements: [XFER-02]
---

# Phase 117 Plan 08: Protect submitted-but-unobserved transfers (B2) Summary

A transfer whose QUEUE lftp accepted but which no successful status has observed yet is now tracked in LftpManager and shown as the existing "Queued" state. While status is unavailable it is never re-queued (even after the cooldown), never marked DOWNLOADED from a preallocated local size, never committed or auto-extracted, and Extract/Delete commands for it are refused with 409, including inside the same `process()` batch as the QUEUE.

## What changed

- **lftp_manager.py**: `__submitted_unobserved` set. `queue()` adds the name after `Lftp.queue` returns. `status()` clears the set when it returns a list (including `[]`) and leaves it alone on `None`, exception or stall backoff. `kill()` discards the killed name after `Lftp.kill` returns, whether True or False. It is not wrapped in try/finally, so a raising kill leaves the name protected. New `submitted_unobserved_file_names()` returns a sorted copy.
- **model_builder.py**: `set_submitted_files()` invalidates the cache only when membership changes. `clear()` resets the set. `_set_initial_state` gains `elif name in __submitted_files: QUEUED`, so an observed lftp status always wins. `build_model`'s name union is unchanged, so a submitted name with no other source is ignored. `_check_downloaded_state`, `_determine_child_state` and the commit path are untouched; they already treat QUEUED correctly.
- **model_pipeline.py**: `feed_model_builder` syncs the set right after the `lftp_statuses is not None` guard every cycle.
- **command_processor.py**: new `_is_submitted_unobserved(file)` helper. `_handle_extract` and both `_handle_delete` branches return 409 after their state guard and before any `file_op_manager` call or persist add. `_handle_queue` skips the lftp re-submit but still runs the USER persist discards and returns success. `_handle_stop` is unchanged.

## Discretion rationale

- **Set in LftpManager**: LftpManager is the one object that knows a queue command was actually sent and whether the next status was available. The rejected alternative was a Controller-owned set plus a new AutoQueue filter. Every AutoQueue test mocks the controller, so a MagicMock predicate would be truthy, and QUEUED already gates sweep, extract/delete and DOWNLOADED derivation without new branches.
- **Execution-time handler guard instead of a synchronous rebuild**: `Controller.__process_commands` handles every command against the ModelFile frozen at the last build, before `__update_model`. So a QUEUE earlier in the batch is invisible in `file.state` (codex pass-2). Rebuilding the model inside `_handle_queue` would take `__model_lock` and run a full build per command on the controller thread. A membership test against the LftpManager set gives the same guarantee for almost no cost.
- **Cheap `_handle_queue` check (T-117-13)**: a user double-click, or an AUTO sweep racing a USER queue in the same batch, would otherwise start a second lftp job on the same path.

## Product-visible effects

- A file submitted during a status outage shows the existing "Queued" badge until the first successful status. This is honest, and there is no new indicator (D-01).
- An Extract or Delete issued in the same tick as a Queue for the same file is now refused with the same 409 the UI already handles for queued files. Previously it could destroy the transfer's source or destination.
- D-02 corollary: under a persistent parse failure such a file stays Queued. It is never re-submitted and cannot be extracted or deleted, mirroring the frozen DOWNLOADING state for observed transfers.
- No permanent stickiness: ANY successful status clears the set. A job lftp silently dropped falls back to DEFAULT at the next successful status, and the sweep retries after the cooldown.
- STOP handler unchanged; `LftpManager.kill` removes the stopped name from the set once `Lftp.kill` returns. A Stop followed by a user re-queue therefore really restarts the transfer (codex pass-3; preservation test `test_stop_then_user_queue_after_unavailable_status_resubmits_to_lftp` green). A QUEUE-then-STOP for a DEFAULT file inside one batch keeps the pre-existing 409.

## Tests added (for Plan 07's new-contract accounting): 9 + 7 + 4 = 20

- test_lftp_manager.py +9 (19 -> 28 in `TestLftpManager`'s file run): queue records / failure not recorded / list clears / `[]` clears / None-parser-error-LftpError keep / returns copy / successful kill reconciles / kill-not-found reconciles / failed kill keeps.
- test_model_builder.py +7 (47 -> 54).
- test_controller_unit.py +4 in `TestControllerCommandSubmittedUnobservedGuard` (134 -> 138).

## Verification (observed)

- RED observed before each GREEN: 9, 7 and 4 failures respectively.
- `test_transfer_state_safety.py`: 13 passed. These include all seven Plan 08-owned tests and the Stop->USER QUEUE preservation test.
- Phase quick-run set (test_lftp, test_auto_queue, test_lftp_manager, test_controller_unit, test_controller, test_model_builder, test_transfer_state_safety, test_scan_clock_safety, test_status, test_serialize_status): **524 passed, 0 failed**. The previous run was 497 passed and 7 failed, plus 20 new tests.
- Whole-tree `ruff check src/python/`: All checks passed.
- `grep -rn "submitted_unobserved|set_submitted_files|_is_submitted_unobserved" src/python/web/ src/python/common/persist.py`: no matches, so nothing changed in the UI or persistence layers.
- STOP untouched: `git diff HEAD~1 HEAD -- command_processor.py | grep "^[-+]" | grep -c "_handle_stop\|kill("` = 0.
- Broader regression run, tests/unittests/test_controller + test_web excluding test_extract: 1023 passed. The 3 test_scanner_process failures and the 1 test_extract_process timeout are a macOS `spawn` MagicMock-pickling problem, unrelated to this plan's files. They are logged in deferred-items.md.

## Deviations from Plan

- **Commit granularity**: the plan asked for one combined commit at the end of Task 3. The orchestrator asked for an atomic commit per task, and TDD RED/GREEN gates apply, so the work is six commits: a test and an implementation commit per task. The final commit `a96e160` keeps the planned subject `fix(117-08): protect submitted-but-unobserved transfers until first successful status (B2)`. Because of the split, the acceptance check "`git diff --stat HEAD~1 HEAD` lists exactly the seven files" holds across the range `cfac533..a96e160`, not across HEAD~1 alone.

Otherwise the plan was executed as written.

## TDD Gate Compliance

test -> feat/fix sequence present for each task: 0b5a82e -> 4bc2b79, 92d1053 -> 0d5b1b8, d7df2fe -> a96e160.

## Commits

- 0b5a82e test(117-08): add failing tests for LftpManager submitted-unobserved tracking
- 4bc2b79 feat(117-08): track submitted-but-unobserved transfers in LftpManager
- 92d1053 test(117-08): add failing tests for ModelBuilder submitted-file QUEUED derivation
- 0d5b1b8 feat(117-08): derive QUEUED in ModelBuilder for submitted names without a status
- d7df2fe test(117-08): add failing handler-guard tests for submitted-unobserved names
- a96e160 fix(117-08): protect submitted-but-unobserved transfers until first successful status (B2)

## Self-Check: PASSED

All seven modified files exist, and all six commits are present in `git log cfac533..HEAD`.
