---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 06
subsystem: controller
tags: [incomplete-import, obsession, completion-gate, temp-file, manual-release, imp-01, imp-02, regression-red-first, non-blocking-gate]
requires:
  - "119-03: RootReservations + CommandProcessor queue reservation"
  - "119-04: CompletionGate / ArrQueueClient / FakeArrClient"
  - "119-05: import credit (unchanged here)"
provides:
  - "Controller.evaluate_completion(candidates) / completion_verdict(name, remote_size)"
  - "Controller.Command(..., release_unverified=False) — one-shot, never persisted"
  - "CommandProcessor(completion_gate=...) execution-time gate: AUTO skip / USER 428 / release WARNING; proof consumed on submission"
  - "POST /server/command/queue/<f>?release_unverified=true; bulk body release_unverified (strict bool, queue only)"
  - "Forced temp-file transfers (lftp + ActiveScanner + LocalScanner)"
  - "Test base patches controller.controller.CompletionGate / ArrQueueClient to PROVEN"
affects: [119-07, 119-09, 119-12]
tech-stack:
  added: []
  patterns:
    - "batched per-cycle gate verdict before the requeue cooldown stamp"
    - "verdict + submission atomic inside the per-root reservation"
key-files:
  created: []
  modified:
    - src/python/controller/controller.py
    - src/python/controller/auto_queue.py
    - src/python/controller/command_processor.py
    - src/python/controller/lftp_manager.py
    - src/python/controller/scan_manager.py
    - src/python/web/handler/controller.py
    - src/python/tests/unittests/test_controller/base.py
    - src/python/tests/unittests/test_controller/test_auto_queue.py
    - src/python/tests/unittests/test_controller/test_controller_unit.py
    - src/python/tests/unittests/test_controller/test_lftp_manager.py
    - src/python/tests/unittests/test_controller/test_scan_manager.py
    - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py
    - src/python/tests/unittests/test_controller/test_scan_clock_safety.py
    - src/python/tests/unittests/test_controller/test_transfer_state_safety.py
    - src/python/tests/unittests/test_controller/test_file_operation_manager.py
decisions:
  - "CommandProcessor.completion_gate is a required constructor argument (no default), so no processor can be built that silently skips the gate"
  - "The release flag is ignored for AUTO commands (AUTO held is always a quiet skip)"
  - "Proof is consumed only when lftp.queue actually ran: not on LftpError, not when the submitted-unobserved check skipped the submit"
metrics:
  duration: "~35 min"
  completed: 2026-10-14
  tasks: 3
  files: 15
---

# Phase 119 Plan 06: Incomplete-import prevention (IMP-01 + IMP-02) Summary

Automatic transfers now start only after the Sonarr/Radarr queue proves a root has finished downloading. When no arr is enabled, the gate doesn't apply and the stability rules decide alone. lftp and both local scanners always use `*.lftp` temp files. Every queue command re-checks the gate inside the per-root reservation, and a user can release an unverified root for one transfer only by confirming it explicitly (428 → `release_unverified`).

## What was built

- **AutoQueue sweep** (`auto_queue.py`): after the stopped/downloaded filter, it calls `controller.evaluate_completion({name: remote_size})` once per cycle, even when there are no candidates. A held root is skipped with a DEBUG line before the cooldown check, so it is never cooldown-stamped and queues on the first cycle after it is proven. The class docstring now says stability is a prerequisite only (D-03/D-16).
- **Controller** (`controller.py`): builds `ArrQueueClient` and `CompletionGate` after `LftpManager`, which keeps them patchable at `controller.controller.*`. Adds `evaluate_completion` / `completion_verdict`, both documented as non-blocking on the controller thread. Adds `Command.release_unverified` (bool, one-shot, never persisted), lists 428 in the `ICallback.on_failure` docstring, and injects the gate into `CommandProcessor`.
- **CommandProcessor** (`command_processor.py`): takes the verdict inside `with reservation:` (lines 163 acquire < 183 verdict < 206 `lftp.queue`).
  - AUTO + held → INFO skip, `(True, None, None)`.
  - USER + held → `(False, "Completion could not be verified: <label>", 428)`.
  - USER + flag → WARNING "Manual release of unverified '<name>' (<label>); source-completion check bypassed for this transfer only", then the normal submit path.
  - After `lftp.queue` returns → `completion_gate.invalidate(name, "transfer submitted")`.
  - Names are sanitized in every log line.
- **Temp files**: `LftpManager` sets `use_temp_file = True` unconditionally and logs one INFO line when the config says False. `ScanManager` builds `ActiveScanner` and `LocalScanner` with `use_temp_file=True`. The config key still loads.
- **Web** (`web/handler/controller.py`): the single queue endpoint reads `?release_unverified=true` (case-insensitive; anything else means False). The bulk endpoint takes a strict-bool `release_unverified`: a non-bool gets 400 "release_unverified must be a boolean", and True with a non-queue action gets 400 "release_unverified is only valid for action queue". The existing per-file `error_code` path already passes 428 through to the client.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 RED | 7bf68b2 | test(119-06): add failing IMP-01/IMP-02 Obsession replay and manual-release regressions |
| 2 GREEN | 733b5cf | fix(119-06): gate auto-queue on arr completion verdict and force temp-file transfers (IMP-01, IMP-02) |
| 3 GREEN | e5f22a5 | fix(119-06): re-check completion at queue execution; confirmed one-shot manual release (IMP-02) |

`git log` shows `test(119-06)` before both `fix(119-06)` commits. The RED commit touches only test files.

## Verification (observed)

**RED, at 7bf68b2.** I ran the six plan files plus the two extra harness files (scan-clock / transfer-state): **28 failed, 339 passed**. Every failure is a new or contract-updated test, and all pre-existing tests stayed green.
- `test_obsession_sweep_holds_while_still_downloading`: `AssertionError: Expected 'queue_command' to not have been called. Called 1 times.`
- `test_requeue_after_submission_reproves_from_responding_arr_while_other_unavailable` and the stays-held variant: `AssertionError: ... unexpectedly found in {...: _Proof(download_id='ABC', ...)} : submission consumes the proof`.
- `test_user_queue_returns_428_immediately_while_fetch_pending`, plus the other release-flag tests: `TypeError: Controller.Command.__init__() got an unexpected keyword argument 'release_unverified'` (or `AttributeError` on the attribute).
- `test_gate_recheck_runs_inside_root_reservation`: `Lists differ: ['queue'] != []` (the verdict was never taken).
- `test_proof_consumed_on_successful_submission`: `Expected 'invalidate' to be called once. Called 0 times.`
- Temp-file tests: `ActiveScanner('/local/path', use_temp_file=False)` where True was expected. For lftp, the ignored-key notice was missing.
- Handler: `AttributeError` on `release_unverified`, and `400 != 200`.

**GREEN, Task 2.** auto_queue + lftp_manager + scan_manager + transfer_state_safety + scan_clock_safety: **155 passed**. `ruff check .`: All checks passed.

**GREEN, Task 3.**
- controller_unit + controller_handler + auto_queue + import_credit + auto_delete_rearm + file_operation_manager: **371 passed** (after the Rule 3 fix below). The 14 `TestQueueCompletionGate` tests pass.
- **Host full suite**, with the 4 conventional `--ignore`s: **1651 passed, 19 subtests passed, 0 failed** (44.8 s).
- Whole-tree `ruff check .`: **All checks passed**.
- No-wait grep (`.join(`, `time.sleep`, `.wait(`) over command_processor.py and auto_queue.py: 0 matches.
- Every `process()` call in the real-gate tests finished in under 0.1 s, as asserted.

**Acceptance greps:**
- lftp `use_temp_file = True`: 1. scan_manager `use_temp_file=True`: 2.
- `CompletionGate(`: 1. `def evaluate_completion`: 1.
- `evaluate_completion(` (line 345) comes before the cooldown stamp (line 367).
- `release_unverified` in controller.py: 3. `428` in command_processor.py: 4.
- "Completion could not be verified: " / "Manual release of unverified" / `__completion_gate.invalidate(`: 1 each.
- `release_unverified` in web/handler/controller.py: 14.
- base.py `patcher_cg`: 3.
- `import FakeArrClient` / `from controller.arr_queue import`: 1 each. `fetch_queue`: 0.

**Not verified here:** `tests/integration/test_controller/test_controller.py` needs the lftp/SSH test environment and was not run on this host. It doesn't enable Sonarr/Radarr, and Config defaults leave both disabled (`enabled = None`), so the gate should return NOT_REQUIRED there. That is inferred, not run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `patch(..., create=True)` in base.py**
- Without it, the base patchers would raise AttributeError at the RED commit, because `CompletionGate` / `ArrQueueClient` didn't exist in `controller.controller` until Task 2. That would have broken all ~100 existing controller tests before GREEN. `create=True` keeps them green before and after. Commit 7bf68b2.

**2. [Rule 3 - Blocking] Gate stubs in every MagicMock AutoQueue harness, not only two**
- A bare `MagicMock` controller returns a MagicMock verdict whose `.held` is truthy, so every harness would have held everything after GREEN.
- `test_auto_queue.py` has five such harnesses, not two: TestAutoQueue, CommandOrigin, ComposedPipeline, StabilityAndSweep and LocalStabilityGate. All five, plus the new class, got the stubs, so the `evaluate_completion = MagicMock` count is 6 rather than the planned 2.
- `test_scan_clock_safety.py` and `test_transfer_state_safety.py` (their AutoQueue harnesses) also got the stub. Commit 7bf68b2.

**3. [Rule 3 - Blocking] Existing contract assertion updated**
- `test_scan_manager.py::test_init_creates_scanners_and_processes` asserted `use_temp_file=False`, which is the old contract that IMP-01 replaces. I changed it to True in the RED commit, so it fails RED alongside the new test. Commit 7bf68b2.

**4. [Rule 3 - Blocking] Single-queue handler tests need a request context**
- The handler now reads `request.query`. `_call_queue_handler` in the single-action test class now patches `web.handler.controller.request` with a query dict, matching how the bulk helper already patches `request`. Commit 7bf68b2.

**5. [Rule 3 - Blocking] Real-Controller harnesses outside the base**
- `TestSameCycleCommandOrderingProtectsSubmittedTransfers` builds a real Controller with a MagicMock context. That made the real gate see "enabled" MagicMock arrs, and 5 tests got 428. The harness now disables Sonarr/Radarr, so the gate is NOT_REQUIRED (D-16) and the tests exercise command ordering only.
- `test_file_operation_manager.py` constructs `CommandProcessor` directly. It now passes a gate stub that returns `Verdict.proven()`.
- Commit e5f22a5.

**6. [Rule 2 - Correctness] `invalidate` only when `lftp.queue` actually ran**
- The plan said not to invalidate when the submitted-unobserved check skips the submit. The call is placed inside that `if`, and a dedicated test covers it (`test_proof_not_consumed_when_submission_skipped_as_unobserved`).

### Additional tests beyond the plan

These guard edges the plan's text implies:
- `test_gate_called_even_with_no_candidates`
- `test_stopped_or_downloaded_files_are_not_gate_candidates`
- `test_auto_queue_ignores_release_flag`
- `test_verdict_receives_name_and_remote_size`
- `test_release_flag_defaults_false_on_command`
- the non-"true" query string case
- `test_use_temp_file_true_logs_no_ignored_notice`

## Assumption Drift (advisory)

**1. Step 3a label in the re-queue test**
- **Found during:** Task 3, `test_requeue_after_submission_reproves_from_responding_arr_while_other_unavailable`.
- **Planned:** 3a returns 428 "Completion could not be verified: Sonarr unavailable".
- **Actual:** the real 119-04 gate returns **"Radarr unavailable"** (provisional, not registered). The test asserts that, plus `gate.holds == {}`. The behavior that matters holds: an immediate 428, no wait, then success at 3b when Radarr's forced refresh proves it while Sonarr is still down.
- **Why:** Radarr's stale snapshot still holds the matching completed record, so per 119-04's algorithm the arr whose pre-fence evidence is waiting on a refresh is the one reported. This is the same drift recorded in 119-04's SUMMARY. The "nothing fresh proves it" variant does report "Sonarr unavailable", as planned.

**2. Release-flag sequence in the pending-fetch test**
- **Found during:** Task 3, `test_user_queue_returns_428_immediately_while_fetch_pending`.
- **Planned:** after the release-flag submission, clearing `stalled` and delivering responses lets the next USER queue succeed.
- **Actual:** the release-flag submission itself consumes the proof and fences the name. The pending fetches started before that, so their results count as stale, and one forced refresh has to finish first. The test runs two `gate.evaluate` calls (two AutoQueue sweeps) after the arrs answer, and then the next click succeeds without the flag.
- **Why:** the proof-on-submission rule (codex finding 1) applies to every submission, including a manual release. That is the intended safety property, not a regression.

## Known Stubs

None.

## Threat Flags

None. The only new input surface is `release_unverified`, which the threat model already covers (T-119-21): queue only, strict boolean, a WARNING on every use, never persisted.

## Requirements

IMP-01 (forced temp files) and IMP-02 (completion-gated transfer starts plus the execution-time re-check) are delivered for the controller. Model hold display and lifecycle invalidation remain with 119-07, per the phase plan.

## Self-Check: PASSED

- FOUND: src/python/controller/auto_queue.py, command_processor.py, controller.py, lftp_manager.py, scan_manager.py, web/handler/controller.py
- FOUND commits: 7bf68b2, 733b5cf, e5f22a5
