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

Release branch `release/1.7.5`, PR #127 (https://github.com/thejuran/seedsyncarr/pull/127) into
`main`. Nothing was published: on a PR the publish jobs are skipped, and no tag exists.

- Final head: `cbd99dc386afc35c9071dfd7153a10b9d2d79ad3` (same as local `main` HEAD and
  `origin/release/1.7.5`).
- CI run URL: https://github.com/thejuran/seedsyncarr/actions/runs/38726397226 — conclusion `success`.
- CodeQL run: https://github.com/thejuran/seedsyncarr/actions/runs/38726392573 — conclusion `success`
  (Analyze actions / javascript-typescript / python).
- Per-job conclusions (CI run, `gh run view 38726397226`, observed 2026-10-15):

| Job | Conclusion |
|-----|------------|
| Lint (Python) | success |
| Lint (Angular) | success |
| Python unit tests | success |
| Angular unit tests | success |
| Verify Python package | success |
| Verify release metadata | success |
| Release metadata verifier tests | success |
| Build Docker Image | success |
| End-to-end tests on Docker Image (amd64) | success |
| Publish Docker Image / Publish Docker Image (:dev) / Publish to PyPI / Publish Documentation / Publish GitHub Release | skipped (PR) |

- Dependabot alert #93 state after CI: `open` — expected; GitHub rescans once the lockfile change
  reaches `main` (119-10).

### Release-gate catches (two earlier CI attempts on PR #127 failed; fixed on the release branch)

1. **Build Docker Image failed.** The image build ran an unpinned `pip3 install poetry` into the
   system interpreter, which pulled the newly published cffi 2.1.1; `poetry install`
   (`virtualenvs.create=false`) then tried to downgrade cffi/certifi to the lock's versions while
   running on them (`FileNotFoundError` on `cffi-2.1.1.dist-info`). Fix: install Poetry 2.3.4 into an
   isolated `/opt/poetry` venv in `src/docker/build/docker-image/Dockerfile`. Landed in commit
   `6a323ee` (whose message names only the HMAC change; `cbd99dc`'s message records the Dockerfile fix).
2. **CodeQL high alert `py/weak-sensitive-data-hashing`** on the arr API-key change-detection
   fingerprint (first SHA-256, then HMAC-SHA256 in `6a323ee`). Fix in `cbd99dc`: replace hashing
   with opaque in-memory per-key counter tokens — no hash of the key exists, the identity never
   carries the raw key, and it is never logged. Tests updated; 94 targeted tests pass; ruff clean.
   CodeQL on the final head: success.

## Coverage (informational)

The host run does not print coverage (no `--cov` in the default options); CI runs no `--cov`
either. Not recorded.

## Owner decision (2026-10-15)

Verbatim: "Approve as drafted" — items (a) limitation/cleanup wording as drafted, (b) rollback to
1.7.4 with .pre-1.7.5 suffix, (c) close #123/#124 after the tag with a "rolled into 1.7.5" comment,
(e) leave #126 out. Item (d): CI via branch + PR (chosen).

Recorded before any tag. Tag, merge, push and publish are plan 119-10.

## Owner approval (Plan 119-09)

Verbatim (2026-10-15): "Approve as drafted" — items (a) limitation/cleanup wording as drafted,
(b) rollback to 1.7.4 with .pre-1.7.5 suffix, (c) close #123/#124 after the tag with a "rolled into
1.7.5" comment, (e) leave #126 out. Item (d): CI via branch + PR (chosen; PR #127). No amendments,
so no `apply owner amendments` commit.

## wud suspension (Plan 119-10)

Run before any push of the 1.7.5 release (NAS `date`: Thu Oct 15 06:33:28 -05 2026).

```
$ ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose stop wud'
 Container wud  Stopping
 Container wud  Stopped
$ ssh nas "sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}} {{.State.FinishedAt}}'"
exited 2026-10-15T11:33:41.00746253Z
$ ssh nas "sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Config.Image}} {{.State.Status}}'"
ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595 running
$ ssh nas "sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Image}}'"
sha256:0e33b030b41004f077d05742286b5599506f27e171b624b6c5122d59811c6d45
```

wud stays stopped until Plan 119-11 restores it (after the deploy is verified or a rollback
completes). All NAS auto-updates are paused meanwhile.

Also present on the NAS and NOT touched by this plan: `seedsyncarr-test` (compose project `v5test`,
`/volume1/docker/v5test/docker-compose.yml`, image `:1.7.4`, host port 8801). The 1.7.5 smoke
therefore uses host port 8802.

## Merge and tag (Plan 119-10)

Run after the owner approval and the verified wud suspension above (committed as `0928017` before
the first push of this plan).

1. Pushed `0928017` (planning-docs delta only: ROADMAP, STATE, 119-09-SUMMARY, this file) to
   `origin/release/1.7.5` (fast-forward `cbd99dc..0928017`).
2. PR #127 checks re-ran on `092801725d55dd212de72238a28a64914f1fadd5`:
   CI https://github.com/thejuran/seedsyncarr/actions/runs/38728273194 — `success` (9 gate jobs
   success, 5 publish jobs skipped); CodeQL run 38728265144 — all three Analyze jobs pass.
3. `gh pr merge 127 --merge --subject "Merge 1.7.5 safety release (#127)"` → merge commit
   `7ebfac9622abd284084f2c32ee405a117fbbcd75`, parents `f6ff78a` (previous `origin/main`) and
   `0928017` (release head). History kept. `git diff 0928017 7ebfac9` is empty (same tree as the
   tested release head). Local `main` fast-forwarded to `origin/main` = `7ebfac9`.
4. Annotated tag:

```
$ git tag -a v1.7.5 -m "SeedSyncarr 1.7.5 — safety release" 7ebfac9
$ git cat-file -t v1.7.5
tag
$ git rev-parse v1.7.5 v1.7.5^{commit}
cb1c33ed616690e9f7bafb99c6096e9e61619f54
7ebfac9622abd284084f2c32ee405a117fbbcd75
$ git push origin v1.7.5
 * [new tag]         v1.7.5 -> v1.7.5
$ ssh nas "sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}}'"   # after the tag push
exited
```

## Tag and CI (Plan 119-10)

Tag CI run: https://github.com/thejuran/seedsyncarr/actions/runs/38729554457 (event `push`,
ref `v1.7.5`, head `7ebfac9622abd284084f2c32ee405a117fbbcd75`) — conclusion `success`.
(The `main` push CI run 38729547458 for the same commit also ran; it publishes `:dev` and docs.)

| Job | Conclusion |
|-----|------------|
| Release metadata verifier tests | success |
| Verify release metadata | success |
| Angular unit tests | success |
| Lint (Angular) | success |
| Lint (Python) | success |
| Python unit tests | success |
| Verify Python package | success |
| Build Docker Image | success |
| End-to-end tests on Docker Image (amd64) | success |
| End-to-end tests on Docker Image (arm64) | success |
| Publish Docker Image | success |
| Publish GitHub Release | success |
| Publish to PyPI | success |
| Publish Documentation | success |
| Publish Docker Image (:dev) | skipped (tag ref) |

### GitHub Release

```
$ gh release view v1.7.5 --json name,tagName,url,isDraft,isPrerelease
{"isDraft":false,"isPrerelease":false,"name":"v1.7.5 — SeedSyncarr","tagName":"v1.7.5","url":"https://github.com/thejuran/seedsyncarr/releases/tag/v1.7.5"}
```

### PyPI

Clean venv (`/opt/homebrew/bin/python3.12 -m venv <scratchpad>/pypi`, no cache):

```
$ pip index versions seedsyncarr
seedsyncarr (1.7.5)
Available versions: 1.7.5, 1.7.2, 1.7.1, 1.6.0, ...
$ pip install --no-cache-dir seedsyncarr==1.7.5
Successfully installed bottle-0.13.4 certifi-2026.7.22 cffi-2.1.1 charset_normalizer-3.5.2 cryptography-50.0.2 idna-3.20 paste-3.10.1 patool-4.1.0 pexpect-4.9.0 ptyprocess-0.7.0 pycparser-3.11 pytz-2026.5 requests-2.34.2 seedsyncarr-1.7.5 setuptools-84.0.0 tblib-3.2.2 urllib3-2.8.0
INSTALL_EXIT=0
$ pip show seedsyncarr
Name: seedsyncarr
Version: 1.7.5
$ seedsyncarr --help   (tail)
Seedsyncarr daemon

options:
  -h, --help            show this help message and exit
  -c CONFIG_DIR, --config_dir CONFIG_DIR
                        Path to config directory
  --logdir LOGDIR       Directory for log files
  -d, --debug           Enable debug logs
  --exit                Exit on error
  --html HTML           Path to directory containing html resources
  --scanfs SCANFS       Path to scanfs executable
HELP_EXIT=0
```

REL-02 (PyPI publication of 1.7.5) is satisfied. 1.7.4 never reached PyPI (118-04); 1.7.5 is the
first release on PyPI since 1.7.2.

### GHCR digest

`gh api .../packages/...` needs `read:packages` (not in the gh token, HTTP 403) and the NAS docker
has no `buildx`, so the digest was read from the registry API with an anonymous pull token
(`HEAD /v2/thejuran/seedsyncarr/manifests/<tag>`, Accept OCI index):

```
1.7.5:  content-type: application/vnd.oci.image.index.v1+json
1.7.5:  docker-content-digest: sha256:b061d95a50aad29d00d623191bebbb61290195b7b5eea6ec53d0b99af98bb3de
latest: docker-content-digest: sha256:d2f06b49c30a63a83a23aacd5036082895fb0cde038f69070f1946bfe49d743f
1.7.5 index children:
  sha256:85e8e08cc1feaf14e726c598f7abdf894697e100525821a0e47966fc1a29fa13 linux/amd64
  sha256:3ab66702376197edcf91da440766c1c96f4d000f2a3a80eb758d54571cc61c11 linux/arm64
  sha256:04ef3cf7… / sha256:3cc09bfa…  unknown/unknown (attestations)
latest index children:
  sha256:85e8e08cc1feaf14e726c598f7abdf894697e100525821a0e47966fc1a29fa13 linux/amd64
  sha256:3ab66702376197edcf91da440766c1c96f4d000f2a3a80eb758d54571cc61c11 linux/arm64
  sha256:b08ddd52… / sha256:e462913f…  unknown/unknown (attestations)
```

`:latest` has a different index digest only because the publish job pushes it in a second step,
which writes new attestation manifests. The amd64 and arm64 image manifests are identical, so the
images are the same. The deploy pins the `:1.7.5` index digest.

RELEASE_DIGEST=sha256:b061d95a50aad29d00d623191bebbb61290195b7b5eea6ec53d0b99af98bb3de
Platforms: linux/amd64, linux/arm64.

```
$ ssh nas uname -m
x86_64
$ ssh nas 'sudo /usr/local/bin/docker pull -q ghcr.io/thejuran/seedsyncarr:1.7.5@sha256:b061d95a50aad29d00d623191bebbb61290195b7b5eea6ec53d0b99af98bb3de'
$ ssh nas 'sudo /usr/local/bin/docker image inspect <IMG> --format "{{.Id}} {{.Architecture}} {{json .RepoDigests}}"'
sha256:ade5863fef7d27ab01ecdd38f2124b44e142da1feafeceb8200f6b832d14b4b3 amd64 ["ghcr.io/thejuran/seedsyncarr@sha256:b061d95a50aad29d00d623191bebbb61290195b7b5eea6ec53d0b99af98bb3de"]
```

NAS_IMAGE_ID=sha256:ade5863fef7d27ab01ecdd38f2124b44e142da1feafeceb8200f6b832d14b4b3

Checked right after the pull: wud `exited`; production
`ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129d… running` (not touched).

### Dependabot PRs (owner item c)

```
$ gh pr close 123 --comment "Rolled into 1.7.5 (commit 7ebfac9, tag v1.7.5: https://github.com/thejuran/seedsyncarr/releases/tag/v1.7.5)."
✓ Closed pull request thejuran/seedsyncarr#123 (chore(deps): bump cryptography from 50.0.1 to 50.0.2 in /src/python)
$ gh pr close 124 --comment "Rolled into 1.7.5 (...)"
✓ Closed pull request thejuran/seedsyncarr#124 (chore(deps): bump pytz from 2026.3.post1 to 2026.5 in /src/python)
$ gh api repos/thejuran/seedsyncarr/dependabot/alerts/93 --jq .state
fixed
```

#126 left open (owner item e).

## Smoke test on NAS (Plan 119-10, REL-03)

Run 2026-10-15 06:45 to 07:09 -0500 (NAS `date`; app-log/UTC times below are NAS + 5 h).
Scratch only: containers `seedsyncarr-smoke` (host port **8802**; 8801 belongs to the untouched
`seedsyncarr-test`) and `seedsyncarr-smoke-remote`, network `seedsyncarr-smoke-net`, dir
`/volume1/docker/seedsync-smoke-1.7.5`. Nothing touched `/volume1/docker/seedsync`, the compose
file, the production `seedsyncarr` container, `seedsyncarr-test`, or wud. The scratch sshd password
and the scratch webhook secret were generated on the NAS (`openssl rand`), held in an owner-only
(0700/0600) dir, passed into JSON bodies with `jq --arg` and into `chpasswd` over stdin, never
printed, and deleted at teardown. They are not in this file.

DIGEST=sha256:b061d95a50aad29d00d623191bebbb61290195b7b5eea6ec53d0b99af98bb3de
IMG=ghcr.io/thejuran/seedsyncarr:1.7.5@sha256:b061d95a50aad29d00d623191bebbb61290195b7b5eea6ec53d0b99af98bb3de
SMOKE_IMAGE_ID=sha256:ade5863fef7d27ab01ecdd38f2124b44e142da1feafeceb8200f6b832d14b4b3

SMOKE_IMAGE_ID equals NAS_IMAGE_ID from §GHCR digest (`docker inspect seedsyncarr-smoke --format '{{.Image}}'`).

### Step 0: preconditions

```
wud: exited
prod: ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595 running
no seedsyncarr-smoke* containers; scratch dir absent; port 8802 free
```

Disposable remote: `debian:bookworm-slim` + openssh-server, label `wud.watch=false`, no published
port (scratch bridge only). Files: `/home/smokeuser/files/smoke-a.bin` (209715200 bytes) and
`/home/smokeuser/staging/smoke-b.bin` (5242880 bytes, moved into `files/` at step 7).

```
REMOTE sha256 smoke-a.bin = 6743336a5e0ac98b2d71c1aa3d829cc51093af010ea93ac098ab4abd62555165
REMOTE sha256 smoke-b.bin = 7fe011740f2228c79cc98b0f4c5e2a2c4525ac2a69825dcf5e41e1ec0befa369
Server listening on 0.0.0.0 port 22.
```

(A first checksum read was taken while `/dev/urandom` was still writing the file and is
discarded. The values above were read after `Server listening`, which the container only reaches
after both files are complete.)

### Step 1: startup (D-16 path: both integrations disabled) and D-19 line

```
$ sudo /usr/local/bin/docker run -d --name seedsyncarr-smoke --label wud.watch=false --network seedsyncarr-smoke-net -e PUID=1026 -e PGID=100 -p 8802:8800 -v $D/config:/config -v $D/downloads:/downloads $IMG
SMOKE container .Image: sha256:ade5863fef7d27ab01ecdd38f2124b44e142da1feafeceb8200f6b832d14b4b3
BEFORE: {"up":false,"error_msg":"The settings are not fully configured."}
set lftp/remote_address=seedsyncarr-smoke-remote -> HTTP 200
set lftp/remote_username=smokeuser -> HTTP 200
set lftp/remote_password=<redacted> -> HTTP 200
set lftp/remote_port=22 -> HTTP 200
set lftp/remote_path=/home/smokeuser/files -> HTTP 200
set lftp/local_path=/downloads -> HTTP 200
set lftp/use_ssh_key=false -> HTTP 200
set lftp/use_temp_file=False -> HTTP 200
set lftp/rate_limit=8388608 -> HTTP 200
set autoqueue/enabled=True -> HTTP 200
set autoqueue/patterns_only=True -> HTTP 200
set autoqueue/remote_stability_seconds=0 -> HTTP 200
set autoqueue/local_stability_seconds=0 -> HTTP 200
set autodelete/enabled=True -> HTTP 200
set autodelete/dry_run=False -> HTTP 200
set autodelete/delay_seconds=20 -> HTTP 200
set general/webhook_secret=<redacted> -> HTTP 200
set sonarr/enabled=False -> HTTP 200
set radarr/enabled=False -> HTTP 200
$ sudo /usr/local/bin/docker restart seedsyncarr-smoke
STARTUP: server.up == true
AFTER: {"up":true,"error_msg":null}
2026-10-15 11:58:51,851 - INFO - seedsyncarr (MainProcess/MainThread) - Starting SeedSyncarr
2026-10-15 11:58:52,412 - INFO - seedsyncarr.LftpManager (MainProcess/MainThread) - Temp-file transfers are always on in 1.7.5; use_temp_file=False in config is ignored
status.controller: {"latest_local_scan_time":"1792065542.543252","latest_remote_scan_time":"1792065532.546979","latest_remote_scan_failed":false,"latest_remote_scan_error":null}
```

The D-19 line also appeared on the very first boot (default config, 11:58:34), because a freshly
generated default config carries `use_temp_file = False`. The first boot's
`ERROR - Config is incomplete` is the expected BEFORE state.

Verdict, startup + D-19: **PASS**.

### Step 2: real transfer with the `.lftp` temp name

```
add pattern: Added auto-queue pattern 'smoke-a'. HTTP 200
06:59:06 ls: 10354688 smoke-a.bin.lftp;
06:59:06 ls: 159318016 smoke-a.bin.lftp;
06:59:07 ls: 170510128 smoke-a.bin.lftp;
...
06:59:12 ls: 208994304 smoke-a.bin.lftp;
06:59:12 ls: 209715200 smoke-a.bin;
SEEN_LFTP=1
-rwxrwxrwx+ 1 jule1651 users 209715200 Oct 15 06:52 smoke-a.bin
local sha256:  6743336a5e0ac98b2d71c1aa3d829cc51093af010ea93ac098ab4abd62555165
remote sha256: 6743336a5e0ac98b2d71c1aa3d829cc51093af010ea93ac098ab4abd62555165
```

Model stream (`/server/stream`, `model-updated` new_file, uniq):

```
{"name":"smoke-a.bin","state":"downloading","import_status":"none","hold_reason":null,"local_size":12255232}
... downloading ... local_size 204722597
{"name":"smoke-a.bin","state":"default","import_status":"none","hold_reason":null,"local_size":204722597}
{"name":"smoke-a.bin","state":"downloaded","import_status":"none","hold_reason":null,"local_size":209715200}
```

Verdict, real transfer: **PASS**. The in-flight file was only ever `smoke-a.bin.lftp`, it was
renamed on completion, the sha256 matches, and the final state is `downloaded` with
`hold_reason: null`. Observation: one `default` update sits between the last `downloading` and
`downloaded` (lftp finished, local scan not yet at full size). See step 7.

### Step 3: webhook import (HMAC-signed, Sonarr-style)

Payload: `{"eventType":"Download","series":{"title":"Smoke Show"},"episodeFile":{"relativePath":"Season 01/smoke-a.bin","sourcePath":"/downloads/smoke-a.bin"},"release":{"releaseTitle":"smoke-a.bin"}}`,
signature `X-Webhook-Signature: <hex HMAC-SHA256 of the body with the scratch secret>` (computed on
the NAS with `openssl dgst -hmac`, not printed).

```
unsigned: HTTP 401
07:01:30 signed: OK HTTP 200
2026-10-15 12:01:29,476 - INFO - web_access - "POST /server/webhook/sonarr HTTP/1.1" 401 25
2026-10-15 12:01:30,499 - INFO - seedsyncarr.WebhookManager - Sonarr webhook import enqueued: 'smoke-a.bin' (eventType=Download, episodeFile.sourcePath)
2026-10-15 12:01:30,916 - INFO - seedsyncarr.Controller - Recorded webhook import: 'smoke-a.bin' (child: 'smoke-a.bin')
model: {"name":"smoke-a.bin","state":"downloaded","import_status":"imported","hold_reason":null}
```

Verdict, import visibility + webhook: **PASS** (`import_status: "imported"`; unsigned request refused 401).

### Step 4: automatic cleanup

```
2026-10-15 12:01:31,556 - INFO - seedsyncarr.Controller - Scheduled auto-delete of 'smoke-a.bin' in 20 seconds
2026-10-15 12:01:51,559 - INFO - seedsyncarr.Controller (MainProcess/Thread-4) - Auto-deleted local file 'smoke-a.bin'
07:01:30 ls downloads: [smoke-a.bin ]
07:01:51 ls downloads: []
model: {"name":"smoke-a.bin","state":"deleted","import_status":"imported","hold_reason":null}
```

Verdict, automatic cleanup: **PASS**.

### Step 5: settings persistence

```
set lftp/num_max_parallel_downloads=3 -> HTTP 200
set sonarr/sonarr_url=http://127.0.0.1:9 -> HTTP 200
set sonarr/sonarr_api_key=<redacted> -> HTTP 200     (dummy scratch value)
controller.persist keys: {"downloaded":1,"extracted":0,"stopped":0,"imported":1,"imported_children":0,"absent_since":0}
autoqueue.persist: {"patterns": ["{\"pattern\": \"smoke-a\"}"]}
.tmp files in config dir: 0
```

The config API updates the in-memory config, and `settings.cfg` is written at shutdown. Before the
restart, the file still showed `num_max_parallel_downloads = 2` / `sonarr_url = `. After the step 6
restart:

```
$ grep -E '^num_max_parallel_downloads = |^sonarr_url = ' settings.cfg
num_max_parallel_downloads = 3
sonarr_url = http://127.0.0.1:9
sonarr_api_key non-empty: 1
-rw------- 1 jule1651 users 1245 Oct 15 07:04 settings.cfg
```

Verdict, settings persistence: **PASS**.

### Step 6: restart

```
$ sudo /usr/local/bin/docker restart seedsyncarr-smoke
RESTART: server.up == true
config/get num_max_parallel_downloads: 3
config/get sonarr: {"enabled":false,"sonarr_url":"http://127.0.0.1:9","key_set":true}
autoqueue/get: [{"pattern": "smoke-a"}]
status.controller after 45 s: {"latest_local_scan_time":"1792065863.962692","latest_remote_scan_time":"1792065863.96334","latest_remote_scan_failed":false,"latest_remote_scan_error":null}
downloads after 45 s (smoke-a must NOT be re-downloaded): []
model: {"name":"smoke-a.bin","state":"deleted","import_status":"imported","hold_reason":null}
2026-10-15 12:03:53,273 - INFO - seedsyncarr - Starting SeedSyncarr
2026-10-15 12:03:53,835 - INFO - seedsyncarr.LftpManager - Temp-file transfers are always on in 1.7.5; use_temp_file=False in config is ignored
2026-10-15 12:03:54,015 - INFO - seedsyncarr.Controller.MemoryMonitor - Memory stats: process=50.0MB, downloaded_files=1, ...
2026-10-15 12:03:54,942 - INFO - RemoteScanner.RemoteScanner - Skipping remote scanfs installation: already installed
```

Persist loader check: the 118 checker (`118-05-parse_check.py`, sha256 `920363ac…dd53`, unchanged)
was run with the 1.7.5 image on the scratch files, using the 119-11 flags:

```
$ sudo /usr/local/bin/docker run --rm -i --read-only --user 1026:100 --network none --cap-drop ALL --entrypoint python3 -w /app/python -v /volume1/docker/seedsync-smoke-1.7.5/config:/c:ro $IMG - settings.cfg controller.persist autoqueue.persist < 118-05-parse_check.py
PASS settings.cfg loader=Config
AutoDelete.enabled=True
PASS controller.persist loader=ControllerPersist
PASS autoqueue.persist loader=AutoQueuePersist
PARSE_OK
EXIT=0
```

The one traceback around the restart is the known shutdown race from 118-05, not a startup error:

```
2026-10-15 12:03:38,806 - INFO - seedsyncarr - Exiting Seedsyncarr
2026-10-15 12:03:39,000 - ERROR - seedsyncarr.ScanManager - Scanner process(es) died unexpectedly: RemoteScanner, LocalScanner, ActiveScanner
2026-10-15 12:03:39,000 - ERROR - seedsyncarr.ControllerJob - Caught exception in job ControllerJob
2026-10-15 12:03:41,013 - INFO - seedsyncarr - Exited successfully
```

Verdict, restart: **PASS**. The setting persisted, all three persist files loaded, and the
`downloaded`/`imported` memory survived, so the deleted file was not fetched again.

### Step 7: held item + manual release (1.7.5)

```
T0=2026-10-15T12:05:36Z
set lftp/rate_limit=1048576 -> HTTP 200
set sonarr/enabled=True -> HTTP 200            (sonarr_url = http://127.0.0.1:9, dummy key — unreachable)
add pattern: Added auto-queue pattern 'smoke-b'. HTTP 200
07:05:36 placed smoke-b.bin on remote
07:06:04 {"name":"smoke-b.bin","state":"default","import_status":"none","hold_reason":"sonarr_unavailable"}
local downloads: []
-- 3+ further remote-scan cycles (95 s) --
07:07:39 {"name":"smoke-b.bin","state":"default","import_status":"none","hold_reason":"sonarr_unavailable"}
hold-start lines for smoke-b since T0: 1
2026-10-15 12:05:56,543 - WARNING - seedsyncarr.ArrQueueClient (ArrQueueFetch-sonarr) - Sonarr queue check failed: ConnectionError
2026-10-15 12:05:57,091 - INFO - seedsyncarr.CompletionGate - Completion hold for 'smoke-b.bin': Sonarr unavailable
2026-10-15 12:06:27,482 - WARNING - seedsyncarr.ArrQueueClient (ArrQueueFetch-sonarr) - Sonarr queue check failed: ConnectionError
2026-10-15 12:07:28,129 - WARNING - seedsyncarr.ArrQueueClient (ArrQueueFetch-sonarr) - Sonarr queue check failed: ConnectionError
local downloads (must be empty, held): []
```

One hold-start INFO line over 12:05:57 to 12:07:45, about 108 s at a 30 s remote-scan interval,
with no per-cycle repeats. The Sonarr fetch failures back off (30 s, then 61 s).

```
-- bulk queue without release flag --
{"results": [{"file": "smoke-b.bin", "success": false, "error": "Completion could not be verified: Sonarr unavailable", "error_code": 428}], "summary": {"total": 1, "succeeded": 0, "failed": 1}} HTTP 200
-- bulk queue with release_unverified --
{"results": [{"file": "smoke-b.bin", "success": true}], "summary": {"total": 1, "succeeded": 1, "failed": 0}} HTTP 200
2026-10-15 12:07:45,861 - WARNING - seedsyncarr.Controller.CommandProcessor - Manual release of unverified 'smoke-b.bin' (Sonarr unavailable); source-completion check bypassed for this transfer only
2026-10-15 12:07:45,861 - INFO - seedsyncarr.LftpManager - rate_limit changed: 8388608 -> 1048576
2026-10-15 12:07:46,083 - INFO - seedsyncarr.CompletionGate - Completion hold cleared for 'smoke-b.bin'
07:07:47 ls: 1222283 smoke-b.bin.lftp;
07:07:47 ls: 1506553 smoke-b.bin.lftp;
07:07:48 ls: 1792575 smoke-b.bin.lftp;
07:07:48 ls: 5103200 smoke-b.bin.lftp;
07:07:48 ls: 5242880 smoke-b.bin.lftp;
07:07:49 ls: 5242880 smoke-b.bin;
local sha256 smoke-b:  7fe011740f2228c79cc98b0f4c5e2a2c4525ac2a69825dcf5e41e1ec0befa369  (= remote)
2026-10-15 12:07:48,917 - INFO - seedsyncarr.CompletionGate - Completion hold for 'smoke-b.bin': Sonarr unavailable
2026-10-15 12:07:54,485 - INFO - seedsyncarr.CompletionGate - Completion hold cleared for 'smoke-b.bin'
07:08:01 {"name":"smoke-b.bin","state":"downloaded","import_status":"none","hold_reason":null}
-- disable Sonarr --
set sonarr/enabled=False -> HTTP 200
07:08:45 {"name":"smoke-b.bin","state":"downloaded","import_status":"none","hold_reason":null}
holds in model (any file with non-null hold_reason): 0
Traceback since T0: 0
```

**Observation (not a failure):** after the manual release, the gate logged one more
`Completion hold for 'smoke-b.bin'` at 12:07:48.917, the moment lftp finished. It cleared at
12:07:54 when the local scan saw the full file as `downloaded`. This is the same transient
`default` state between `downloading` and `downloaded` as in step 2: for about 5 s the gate
re-evaluates the root as not-yet-downloaded. Nothing was re-transferred, and the file ended
`downloaded`, `hold_reason: null`. In production with Sonarr reachable, a just-finished file could
briefly show a hold label. It is cosmetic and logged once.

**Badge "Waiting":** the badge is drawn in the browser from `hold_reason`
(`transfer-row.component.ts`: `if (this.isHeld) { return "Waiting"; }`, label from
`Localization.Hold`). The shipped bundle `/app/html/main-C3GCEDMV.js` in the image contains the
`Waiting` literal and the `Sonarr unavailable` label. The model JSON carried
`hold_reason: "sonarr_unavailable"`. **Not verified:** the badge was not looked at in a browser.
That is for the batched pre-release walkthrough.

Verdict, held item + manual release: **PASS**.

### Step 8: scanner errors

```
$ docker logs seedsyncarr-smoke | grep -nE "Scanner process|scan.*(fail|error)|Caught exception|Exiting|Starting SeedSyncarr|Config is incomplete"
139: ERROR - Config is incomplete                     (first boot, default config — expected BEFORE state)
260: ERROR - ScanManager - Scanner process(es) died unexpectedly ...   (12:03:39, 194 ms after "Exiting Seedsyncarr" — shutdown race)
261: ERROR - ControllerJob - Caught exception in job ControllerJob     (same)
scanner errors after the 12:03:53 start: 0; latest_remote_scan_failed: false throughout
```

No startup scanner error occurred, so no recovery line is needed. Verdict: **PASS**.

### Teardown and end state

```
NAS Thu Oct 15 07:09:20 -05 2026
$ sudo /usr/local/bin/docker rm -f seedsyncarr-smoke seedsyncarr-smoke-remote && sudo /usr/local/bin/docker network rm seedsyncarr-smoke-net
smoke containers left: 0
wud: exited
prod: ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595 sha256:0e33b030… running started=2026-10-09T14:10:14Z   (unchanged)
test: ghcr.io/thejuran/seedsyncarr:1.7.4 running started=2026-10-12T23:18:54Z   (unchanged)
```

Scratch dir `/volume1/docker/seedsync-smoke-1.7.5/{config,downloads}` kept until 119-11 completes
(secret files removed; the scratch `settings.cfg` holds only scratch credentials for the destroyed
remote).

### Finding outside this plan's scope: secrets in container stdout (pre-existing since v1.0.0)

The `grep` in step 3 showed that `src/docker/build/docker-image/setup_default_config.sh` runs
`cat ${SETTINGS_FILE}` twice on every container start (lines 27 and 36, unchanged since
`98871f5` "Initial commit: SeedSyncarr v1.0.0", present in v1.7.4 and v1.7.5). So `docker logs`
contains every `settings.cfg` value. Read-only counts on the NAS (no values printed):

```
production seedsyncarr (1.7.4) docker logs, non-empty lines:  remote_password 1, sonarr_api_key 1, radarr_api_key 1
  of which Fernet ciphertext (gAAAAA…): 0   → plaintext;  [Encryption] enabled = True: 0
/volume1/docker/seedsync/log/* (app plain-file logs): no match
```

The deploy will not change this: the 1.7.5 container prints the same dump at start. It is not a
1.7.5 regression and is not fixed here (it needs a new release). It is logged in
`deferred-items.md` and raised at the 119-10 checkpoint. The scratch webhook secret seen once in
this session's terminal output was destroyed with the scratch setup.

### Smoke verdict summary

| # | Check | Verdict |
|---|-------|---------|
| 1 | Startup (D-16, integrations off) + D-19 ignored-config line | PASS |
| 2 | Real transfer: `smoke-a.bin.lftp` → `smoke-a.bin`, sha256 match | PASS |
| 3 | Webhook (signed) → `import_status: "imported"`; unsigned 401 | PASS |
| 4 | Auto-cleanup: "Auto-deleted local file 'smoke-a.bin'" after 20 s | PASS |
| 5 | Settings persistence (file written at shutdown) | PASS |
| 6 | Restart: settings + persist files load (PARSE_OK), no re-download | PASS |
| 7 | Held `sonarr_unavailable`, single hold log line, 428, manual release WARNING, `.lftp` → rename, no holds after disable | PASS (one cosmetic re-hold blip, noted) |
| 8 | No startup scanner error (shutdown race only, as in 118) | PASS |
