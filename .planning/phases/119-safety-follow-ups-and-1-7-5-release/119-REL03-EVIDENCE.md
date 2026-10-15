# Phase 119 REL-03 gate evidence (fail-before / pass-after, suite, lint, packaging, CI)

Release tree: `0306b27` (branch `main`, `chore(119-09): bump to 1.7.5, ...`) — the Phase 119 plan
commits, the five post-review fix commits, and the 1.7.5 metadata/Dependabot commit. Recorded
2026-10-15.

Method: every RED run was made in a throwaway detached `git worktree` under the session scratchpad
at the plan's `test(119-0N)` commit, with the project venv interpreter
(`seedsyncarr-5QbP0KwB-py3.12`), then the worktree was removed with `git worktree remove --force`.

```
PY="$(cd src/python && poetry env info -p)/bin/python"
git worktree add --detach <scratch>/wt-<sha> <sha>
cd <scratch>/wt-<sha>/src/python && "$PY" -m pytest <files> -q -p no:cacheprovider -o addopts="" -rfE --continue-on-collection-errors
git worktree remove --force <scratch>/wt-<sha>
```

`--continue-on-collection-errors` is used so a test file whose module does not exist yet
(ModuleNotFoundError at import) does not hide the failures in the other files of the same commit.
Per-test failure classes were taken from the `E ...Error` line of each test's failure block.

## RED (pre-fix)

### RED 119-01 (XFER-06, lftp resync) at `e645508`

```
FAILED tests/unittests/test_lftp/test_lftp_resync.py::TestLftpResync::test_resync_marker_ignores_tty_echo
FAILED tests/unittests/test_lftp/test_lftp_resync.py::TestLftpResync::test_resync_uses_fresh_nonce_each_attempt
FAILED tests/unittests/test_lftp/test_lftp_resync.py::TestLftpResync::test_stale_prompt_after_timeout_never_yields_empty_status
FAILED tests/unittests/test_lftp/test_lftp_resync.py::TestLftpResync::test_unsynced_resync_failure_keeps_status_unavailable_and_queue_raises
4 failed, 1 warning in 0.03s
```

All four: AssertionError.

### RED 119-03 (DEL-01, submitted-unobserved guard and root reservation) at `32250fb`

```
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteSubmittedUnobserved::test_submitted_guard_runs_after_state_guard_and_respects_rearm_budget
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteSubmittedUnobserved::test_timer_defers_when_root_submitted_unobserved_and_status_unavailable
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteSubmittedUnobserved::test_timer_deletes_after_status_observed_clears_submitted_set
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_auto_delete_defers_while_queue_submission_holds_root
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_manual_delete_local_keeps_root_reserved_until_subprocess_exits
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_manual_delete_local_refused_while_auto_delete_holds_root
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_queue_refused_while_auto_delete_holds_root
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_queue_stays_refused_after_delete_local_returns_until_subprocess_exits
FAILED .../test_auto_delete_rearm.py::TestAutoDeleteRootReservation::test_reservation_released_on_every_non_delete_timer_path
FAILED .../test_lftp_manager.py::TestLftpManager::test_queue_adds_name_before_lftp_queue_and_discards_on_error
FAILED .../test_lftp_manager.py::TestLftpManager::test_submitted_set_snapshot_is_lock_protected
ERROR tests/unittests/test_controller/test_file_operation_manager.py   (ModuleNotFoundError: No module named 'controller.root_reservation')
ERROR tests/unittests/test_controller/test_root_reservation.py         (ModuleNotFoundError: No module named 'controller.root_reservation')
11 failed, 45 passed, 1 warning, 2 errors in 5.41s
```

Classes: AssertionError for all failures except `test_reservation_released_on_every_non_delete_timer_path`
(AttributeError: `Controller` has no `_Controller__root_reservations`). The 27 tests of
`test_file_operation_manager.py` (including `test_delete_local_holds_reservation_until_process_exit`
and `test_reservation_held_across_register_start_window`) and the 7 of `test_root_reservation.py`
could not import the reservation module at this commit: ModuleNotFoundError.

**Second RED — launch window (start-then-register), at fix commit `21fa7bd`** with one local edit
in `FileOperationManager.__launch_and_track` moving `self.__active_command_processes.append(wrapper)`
(and its lock) above `wrapper.process.start()`:

```
 src/python/controller/file_operation_manager.py | 4 ++--
E           AssertionError: 'delete' != None
FAILED tests/unittests/test_controller/test_file_operation_manager.py::TestFileOperationManager::test_reservation_held_across_register_start_window
1 failed, 26 deselected, 1 warning in 0.06s
```

`holder_of("f") == "delete"` fails: the in-window `cleanup_completed_processes` reaped the
unstarted child and released the root. Worktree discarded.

### RED 119-04 (IMP-02, arr queue client and completion gate) at `8194567` and `c1f192d`

```
== 8194567  tests/unittests/test_controller/test_arr_queue.py
E   ModuleNotFoundError: No module named 'controller.arr_queue'
ERROR tests/unittests/test_controller/test_arr_queue.py
1 warning, 1 error in 0.13s

== c1f192d  tests/unittests/test_controller/test_completion_gate.py
E   ModuleNotFoundError: No module named 'controller.completion_gate'
ERROR tests/unittests/test_controller/test_completion_gate.py
1 warning, 1 error in 0.13s
```

All 27 `test_arr_queue.py` tests and all 64 `test_completion_gate.py` tests: ModuleNotFoundError
(the modules did not exist yet).

**Second RED — non-blocking fetch handoff, at client commit `d7e2354`** with one local edit in
`ArrQueueClient.start_fetch` calling `self.__fetch_worker(target, fetch_id, started)` on the calling
thread instead of `worker.start()`:

```
 src/python/controller/arr_queue.py | 2 +-
E               Failed: Timeout (>60.0s) from pytest-timeout.
FAILED tests/unittests/test_controller/test_arr_queue.py::TestArrQueueRealSocket::test_poll_reports_overrun_without_blocking_real_socket
1 failed, 26 deselected, 1 warning in 60.19s (0:01:00)
```

With the synchronous call, `start_fetch` itself blocked on the stalled real socket, so the calling
thread never returned to reach the elapsed-time assertions; pytest-timeout killed it at 60 s.
(The plan expected the elapsed-time assertions to fail; the calling thread blocked outright
instead, which is the same defect more strongly.) Worktree discarded.

### RED 119-05 (IMP-03, Days of Hope early credit) at `7a73d8b`

```
FAILED .../test_import_credit.py::TestEarlyChildCredit::test_arm_on_commit_without_further_webhook
FAILED .../test_import_credit.py::TestEarlyChildCredit::test_child_notices_before_commit_are_credited_not_dropped
FAILED .../test_import_credit.py::TestEarlyChildCredit::test_credit_alone_never_deletes
FAILED .../test_import_credit.py::TestEarlyChildCredit::test_credit_persists_immediately_via_callback
FAILED .../test_import_credit.py::TestEarlyChildCredit::test_credit_survives_persist_round_trip
FAILED .../test_import_credit.py::TestEarlyChildCredit::test_restart_with_persisted_credit_arms_on_commit
FAILED .../test_import_credit.py::TestEarlyChildCredit::test_root_commit_then_last_child_webhook_arms_and_deletes
FAILED .../test_import_credit.py::TestEarlyCreditGuards::test_pending_notice_expires_with_warning
FAILED .../test_import_credit.py::TestEarlyCreditGuards::test_pending_notice_reevaluated_when_child_becomes_downloaded
FAILED .../test_import_credit.py::TestPendingNoticeLifecycle::test_discard_pending_notices_returns_count_and_bumps_generation
FAILED .../test_import_credit.py::TestPendingNoticeLifecycle::test_pending_notice_discarded_on_user_requeue_cannot_credit_new_attempt
FAILED .../test_import_credit.py::TestPendingNoticeLifecycle::test_pending_notice_discarded_when_resolved_path_changes
FAILED .../test_import_credit.py::TestPendingNoticeLifecycle::test_pending_notice_discarded_when_root_leaves_model
FAILED .../test_import_credit.py::TestPendingNoticeLifecycle::test_pending_notice_revalidated_against_current_model_rejects_new_ambiguity
FAILED .../test_import_credit.py::TestPendingNoticeLifecycle::test_pending_notice_with_stale_generation_never_credits
15 failed, 2 passed, 1 warning in 0.21s
```

Classes: AssertionError, except `test_credit_persists_immediately_via_callback` (TypeError — the
persist callback did not exist).

### RED 119-06 (IMP-01/IMP-02, Obsession replay, gate wiring, manual release) at `7bf68b2`

```
FAILED .../test_auto_queue.py::TestAutoQueueCompletionGate::test_gate_called_even_with_no_candidates
FAILED .../test_auto_queue.py::TestAutoQueueCompletionGate::test_gate_called_once_per_cycle_with_all_candidates
FAILED .../test_auto_queue.py::TestAutoQueueCompletionGate::test_held_item_not_cooldown_stamped_then_queued_immediately_when_proven
FAILED .../test_auto_queue.py::TestAutoQueueCompletionGate::test_obsession_sweep_holds_while_still_downloading
FAILED .../test_auto_queue.py::TestAutoQueueCompletionGate::test_obsession_sweep_queues_once_proven
FAILED .../test_auto_queue.py::TestAutoQueueCompletionGate::test_stopped_or_downloaded_files_are_not_gate_candidates
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_auto_queue_ignores_release_flag
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_auto_queue_unverified_is_quiet_skip
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_gate_recheck_runs_inside_root_reservation
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_proof_consumed_on_successful_submission
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_release_approval_is_not_remembered
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_release_flag_defaults_false_on_command
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_requeue_after_submission_reproves_from_responding_arr_while_other_unavailable
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_requeue_after_submission_stays_held_when_nothing_fresh_proves
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_user_queue_returns_428_immediately_while_fetch_pending
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_user_queue_unverified_returns_428
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_user_queue_with_release_flag_submits_once_with_warning
FAILED .../test_controller_unit.py::TestQueueCompletionGate::test_verdict_receives_name_and_remote_size
FAILED .../test_lftp_manager.py::TestLftpManager::test_use_temp_file_forced_true_when_config_false
FAILED .../test_scan_manager.py::TestScanManager::test_init_creates_scanners_and_processes
FAILED .../test_scan_manager.py::TestScanManager::test_scanners_constructed_with_temp_file_forced
FAILED .../test_web/test_handler/test_controller_handler.py::TestControllerHandlerSingleAction::test_single_queue_non_true_query_leaves_flag_false
FAILED .../test_web/test_handler/test_controller_handler.py::TestControllerHandlerSingleAction::test_single_queue_release_unverified_query_sets_flag
FAILED .../test_web/test_handler/test_controller_handler.py::TestControllerHandlerSingleAction::test_single_queue_without_query_leaves_flag_false
FAILED .../test_web/test_handler/test_controller_handler.py::TestControllerHandlerBulkCommand::test_bulk_queue_release_unverified_sets_flag_on_each_command
FAILED .../test_web/test_handler/test_controller_handler.py::TestControllerHandlerBulkCommand::test_bulk_queue_without_release_unverified_defaults_false
FAILED .../test_web/test_handler/test_controller_handler.py::TestControllerHandlerBulkCommand::test_bulk_release_unverified_must_be_boolean
FAILED .../test_web/test_handler/test_controller_handler.py::TestControllerHandlerBulkCommand::test_bulk_release_unverified_only_valid_for_queue
28 failed, 320 passed, 1 warning in 1.68s
```

Classes: AssertionError for most; TypeError for `test_obsession_sweep_queues_once_proven`,
`test_stopped_or_downloaded_files_are_not_gate_candidates`, `test_auto_queue_ignores_release_flag`,
`test_release_approval_is_not_remembered`, `test_user_queue_with_release_flag_submits_once_with_warning`;
AttributeError for `test_release_flag_defaults_false_on_command` and the five handler tests that set or
read the flag (the `release_unverified` command field did not exist); the two bulk-validation handler
tests (`must_be_boolean`, `only_valid_for_queue`) fail with AssertionError.

### RED 119-07 (hold visibility, lifecycle reset of proofs and pending notices) at `907ada9` and `e28a0a0`

```
== 907ada9
FAILED .../test_model_builder.py::TestModelBuilder::test_clear_resets_hold_reasons
FAILED .../test_model_builder.py::TestModelBuilder::test_hold_reason_applied_to_default_root
FAILED .../test_model_builder.py::TestModelBuilder::test_hold_reason_for_unknown_name_is_ignored
FAILED .../test_model_builder.py::TestModelBuilder::test_hold_reason_not_applied_to_children
FAILED .../test_model_builder.py::TestModelBuilder::test_hold_reason_not_applied_to_downloaded_root
FAILED .../test_model_builder.py::TestModelBuilder::test_hold_reason_not_applied_to_transferring_root
FAILED .../test_model_builder.py::TestModelBuilder::test_set_hold_reasons_copies_input
FAILED .../test_model_builder.py::TestModelBuilder::test_set_hold_reasons_invalidates_cache_only_on_change
FAILED .../test_model/test_file.py::TestModelFile::test_hold_reason
FAILED .../test_model/test_file.py::TestModelFile::test_hold_reason_frozen
10 failed, 76 passed, 1 warning in 0.26s

== e28a0a0
FAILED .../test_controller_unit.py::TestControllerFeedModelBuilder::test_feed_syncs_completion_holds
FAILED .../test_controller_unit.py::TestControllerFeedModelBuilder::test_process_syncs_completion_holds_once_per_cycle
FAILED .../test_controller_unit.py::TestControllerLifecycleReset::test_regrab_after_long_absence_resets_proof_and_pending_notices
FAILED .../test_controller_unit.py::TestControllerApplyModelDiff::test_removed_root_resets_proof_and_pending_notices
FAILED .../test_controller_unit.py::TestRootLifecycleResetCallback::test_callback_does_not_take_model_lock
FAILED .../test_controller_unit.py::TestRootLifecycleResetCallback::test_callback_invalidates_proof_and_discards_notices
FAILED .../test_web/test_serialize/test_serialize_model.py::TestSerializeModel::test_hold_reason
7 failed, 175 passed, 1 warning in 0.82s
```

Classes: 907ada9 AttributeError (no `hold_reason` / `set_hold_reasons`), except
`test_hold_reason_frozen` (AssertionError). e28a0a0: the two lifecycle-reset tests (re-grab after
long absence, REMOVED diff) — AssertionError; `test_callback_*` — AttributeError; serializer
`test_hold_reason` — KeyError.

## Adversarial regressions (codex rewrites 1-5 + checker non-blocking revision)

| Test | Guards against | RED class (commit) | GREEN |
|------|----------------|--------------------|-------|
| test_queue_refused_while_auto_delete_holds_root | delete-vs-queue barrier | AssertionError (32250fb) | pass |
| test_auto_delete_defers_while_queue_submission_holds_root | delete-vs-queue barrier | AssertionError (32250fb) | pass |
| test_queue_stays_refused_after_delete_local_returns_until_subprocess_exits | reservation held across deletion subprocess lifetime | AssertionError (32250fb) | pass |
| test_delete_local_holds_reservation_until_process_exit | reservation held across deletion subprocess lifetime | ModuleNotFoundError (32250fb) | pass |
| test_reservation_held_across_register_start_window | reservation held across register/start launch window | ModuleNotFoundError (32250fb); AssertionError with register-then-start mutation (21fa7bd) | pass |
| test_same_name_same_size_regrab_overrides_cached_proof | same-name re-grab | ModuleNotFoundError (c1f192d) | pass |
| test_malformed_sibling_missing_download_id_holds_ambiguous | malformed records | ModuleNotFoundError (c1f192d) | pass |
| test_malformed_sibling_bad_sizeleft_holds_still_downloading | malformed records | ModuleNotFoundError (c1f192d) | pass |
| test_cached_proof_not_used_while_any_enabled_arr_unavailable | cached proof under outage | ModuleNotFoundError (c1f192d) | pass |
| test_fetch_preserves_malformed_records_as_invalid | malformed records | ModuleNotFoundError (8194567) | pass |
| test_invalidate_then_verdict_before_refresh_deadline_requires_fresh_fetch | invalidate-then-verdict fence | ModuleNotFoundError (c1f192d) | pass |
| test_url_change_same_service_clears_snapshots_and_backoff | URL/key identity reset | ModuleNotFoundError (c1f192d) | pass |
| test_fence_blocks_absence_cache_while_target_in_backoff | fence under backoff | ModuleNotFoundError (c1f192d) | pass |
| test_fetch_oversized_chunked_response_aborts_at_cap | bounded streamed fetch | ModuleNotFoundError (8194567) | pass |
| test_fetch_slow_trickle_exceeds_deadline_worker_side | bounded streamed fetch | ModuleNotFoundError (8194567) | pass |
| test_poll_reports_overrun_without_blocking_real_socket | non-blocking fetch handoff (real socket) | ModuleNotFoundError (8194567); pytest-timeout with synchronous-worker mutation (d7e2354) | pass |
| test_start_fetch_refused_while_prior_worker_alive_and_late_result_discarded | one worker per target, late result discarded | ModuleNotFoundError (8194567) | pass |
| test_fresh_proof_from_responding_arr_after_invalidation_while_other_unavailable | fresh single-arr proof after invalidation (D-17, gate unit) | ModuleNotFoundError (c1f192d) | pass |
| test_stale_pre_invalidation_snapshot_never_proves | invalidate-then-verdict fence | ModuleNotFoundError (c1f192d) | pass |
| test_response_from_fetch_started_before_invalidation_never_satisfies_fence | pre-invalidation request never satisfies the fence | ModuleNotFoundError (c1f192d) | pass |
| test_evaluate_never_blocks_on_pending_fetch | non-blocking evaluate | ModuleNotFoundError (c1f192d) | pass |
| test_two_stalled_targets_do_not_block_controller | two stalled arrs never block the controller | ModuleNotFoundError (c1f192d) | pass |
| test_proof_consumed_on_successful_submission | proof consumed on submission | AssertionError (7bf68b2) | pass |
| test_gate_recheck_runs_inside_root_reservation | re-check inside the reservation | AssertionError (7bf68b2) | pass |
| test_requeue_after_submission_reproves_from_responding_arr_while_other_unavailable | fresh single-arr proof (D-17, CommandProcessor end to end) | AssertionError (7bf68b2) | pass |
| test_user_queue_returns_428_immediately_while_fetch_pending | USER queue 428 immediately while evidence pending | AssertionError (7bf68b2) | pass |
| test_pending_notice_discarded_on_user_requeue_cannot_credit_new_attempt | pending-notice discard on USER requeue | AssertionError (7a73d8b) | pass |
| test_pending_notice_revalidated_against_current_model_rejects_new_ambiguity | pending-notice revalidation | AssertionError (7a73d8b) | pass |
| test_regrab_after_long_absence_resets_proof_and_pending_notices | lifecycle reset of both caches (re-grab) | AssertionError (e28a0a0) | pass |
| test_removed_root_resets_proof_and_pending_notices | lifecycle reset of both caches (REMOVED diff) | AssertionError (e28a0a0) | pass |

Note on the RED classes: for tests whose module did not exist at the test commit, the RED run shows
only that the contract was absent (ModuleNotFoundError). The two mutation runs above are the
behavioural RED proofs for the launch-window and non-blocking-handoff properties. The plan text
expected TypeError for the 119-03 file-operation-manager tests at `32250fb`; the actual class is
ModuleNotFoundError because that file imports `controller.root_reservation` at module level.

## Post-review hardening (added with fix, not RED-first)

The post-execution deep review (vibe-check, 2 passes, REVIEW.md APPROVED) produced five fix
commits. Each added its regression tests in the same commit as the fix, so they are recorded as
"added with fix", not as fail-before evidence. All pass on the release tree (GREEN below).

| Commit | Defect | Tests added |
|--------|--------|-------------|
| `1711a5d` | `poll()` race: worker posting just after the results pop was reported as ended without a result | `test_poll_recovers_result_posted_between_pop_and_liveness_check` |
| `3565c41` | incomplete records sharing a download ID could bypass completion verification | `test_incomplete_record_without_output_path_sharing_download_id_holds`, `test_incomplete_record_sharing_download_id_in_other_arr_holds` |
| `bdcc4f2` | failed resync aborted shutdown before child processes stopped | `test_exit_force_closes_after_command_timeout`, `test_exit_force_closes_after_command_timeout_and_failed_resync`, `test_exit_stops_every_manager_even_when_lftp_exit_fails` |
| `7862978` | USER requeue / lifecycle reset left the previous auto-delete Timer armed | `test_user_requeue_cancels_timer_and_clears_rearms`, `test_lifecycle_reset_cancels_timer_and_clears_rearms`, `test_timer_already_running_from_cancelled_lifecycle_neither_deletes_nor_rearms`, `test_new_lifecycle_timer_still_deletes` |
| `1dc5d2f` | root-level notice for a still-transferring pack was kept and replayed at commit | `test_root_level_notice_while_pack_transferring_is_dropped` (plus updated expectations in `test_import_credit.py`) |

## GREEN (release tree `0306b27`)

`cd src/python && poetry run pytest <files> -q -p no:cacheprovider`:

```
== 119-01  test_lftp_resync.py                                                   6 passed, 1 warning in 0.02s
== 119-03  test_auto_delete_rearm, test_file_operation_manager,
           test_lftp_manager, test_root_reservation                              96 passed, 1 warning in 0.31s
== 119-04  test_arr_queue, test_completion_gate                                  94 passed, 1 warning, 19 subtests passed in 3.57s
== 119-05  test_import_credit                                                    18 passed, 1 warning in 0.13s
== 119-06  test_auto_queue, test_controller_unit, test_lftp_manager,
           test_scan_manager, test_web/test_handler/test_controller_handler      360 passed, 1 warning in 1.14s
== 119-07  test_model_builder, test_model/test_file, test_controller_unit,
           test_web/test_serialize/test_serialize_model                          269 passed, 1 warning in 0.74s
== review  test_arr_queue, test_completion_gate, test_lftp_resync,
           test_controller_unit, test_auto_delete, test_auto_delete_rearm,
           test_controller, test_import_credit                                   476 passed, 1 warning, 19 subtests passed in 4.96s
```

0 failed in every group.

## Full host suite

```
cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider \
  --ignore=tests/unittests/test_ssh/test_sshcp.py \
  --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py \
  --ignore=tests/unittests/test_system/test_scanner.py \
  --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py
1685 passed, 2 warnings, 19 subtests passed in 43.82s
```

0 failed. The four ignored files are the host-only exclusions (ssh / multiprocessing scanner /
extract process); CI runs them.

## Ruff 0.15.22 (whole tree)

```
$ <scratch>/ruff/bin/ruff --version
ruff 0.15.22
$ <scratch>/ruff/bin/ruff check src/python/
All checks passed!
```

Local project ruff (0.15.9), `cd src/python && poetry run ruff check .`: All checks passed!

## Packaging

`build` and `twine` are not in the project venv; a scratch venv mirrors CI's `pip install build twine`:

```
$ cd src/python && rm -rf dist && <scratch>/pkg/bin/python -m build
Successfully built seedsyncarr-1.7.5.tar.gz and seedsyncarr-1.7.5-py3-none-any.whl
$ <scratch>/pkg/bin/twine check dist/*
Checking dist/seedsyncarr-1.7.5-py3-none-any.whl: PASSED with warnings
Checking dist/seedsyncarr-1.7.5.tar.gz: PASSED with warnings
  (warnings: long_description / long_description_content_type missing — pre-existing, not blocking)
$ python3 ../../scripts/verify-python-package.py dist
PASS seedsyncarr-1.7.5-py3-none-any.whl members=85
INFO seedsyncarr-1.7.5-py3-none-any.whl files=85
PASS seedsyncarr-1.7.5.tar.gz members=84
TOTAL members=169
PACKAGE_OK
```

## Release metadata

```
$ node scripts/verify-release-metadata.mjs 1.7.5
Release metadata matches 1.7.5:
- CHANGELOG.md has release section [1.7.5]
- release-notes.md links to CHANGELOG.md through the {{VERSION}} tag placeholder
- package.json version is 1.7.5
- src/angular/package.json version is 1.7.5
- src/angular/package-lock.json version is 1.7.5
- src/angular/package-lock.json packages[""].version is 1.7.5
```

`src/python/pyproject.toml` has both `version = "1.7.5"` lines; the root `package-lock.json` (was 1.7.2,
stale) is also 1.7.5.

## Dependabot roll-ins (D-21)

- #123 cryptography 50.0.1 → 50.0.2 and #124 pytz 2026.3.post1 → 2026.5: `poetry update cryptography pytz`;
  lockfile diff limited to those two packages (versions and hashes), identical versions to the PRs.
  Sanity `poetry run pytest tests/unittests/test_common -q`: 187 passed.
- #93 source-map-js: `npm update source-map-js` in `src/angular` → 1.2.2 on both paths
  (`@angular/build › postcss` and `sass`), no override needed. `npm audit --audit-level=high`
  shows no source-map-js finding (remaining: `braces` via `karma › chokidar`, dev-only test
  runner, no open Dependabot alert, not in the shipped image).
- `gh api repos/thejuran/seedsyncarr/dependabot/alerts/93 --jq .state` (2026-10-15, before push): `open`
  — expected; GitHub rescans after the lockfile change reaches `main`.
- Not rolled in: #125 testfixtures (dev), #117 puppeteer (dev, root), #126 npm_and_yarn group
  (23 Angular-tree updates, opened 2026-10-14 after D-21; no security alert attached) — see the
  checkpoint packet.

## CI

**Pending — not pushed.** The release tree is 90 commits ahead of `origin/main` and has not been
pushed; this executor was instructed not to push before the owner checkpoint. CI on the exact
release tree (jobs unittests-release-metadata, unittests-python, unittests-angular, lint-python,
lint-angular, verify-python-package, build-docker-image, e2etests-docker-image, and
verify-release-metadata — which only does real work on a tag) is an awaited item in the 119-09
checkpoint. Run URL and per-job conclusions to be recorded here once CI has run:

- CI run URL: _pending_
- Per-job conclusions: _pending_
- Dependabot alert #93 state after CI: _pending_

Note: a push to `main` also runs `publish-docker-image-dev` (`:dev`) and `publish-docs`; pushing the
same commits to a non-main branch with a PR to `main` runs every gate above without publishing
anything.

## Coverage (informational)

The host run does not print coverage (no `--cov` in the default options); CI runs no `--cov`
either. Not recorded.
