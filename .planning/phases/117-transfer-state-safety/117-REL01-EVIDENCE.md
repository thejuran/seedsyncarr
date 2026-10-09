# Phase 117 REL-01 gate-1 evidence (fail-before / pass-after)

RED run executed against pre-fix code at `05f03ae` (branch `safety-patch-1.7.4`, after the Plan 117-01 / 117-02 RED test commits were merged, before any fix plan). The production tree at that SHA is byte-identical to `7da18e0`:

```
$ git diff --stat 7da18e0 05f03ae -- src/python/lftp src/python/common src/python/controller ':!src/python/tests'
(empty)
```

No file under `src/python/lftp/`, `src/python/common/` or `src/python/controller/` differs from `7da18e0`. Only test files and `.planning/` changed between the two SHAs, so every failure below is a fail-before against unfixed production code.

## RED (pre-fix) — Plans 117-01 / 117-02

**Command** (phase quick run, plus `-rf --tb=line`; per-test exception types taken from the `--junitxml` of the same invocation):

```
cd src/python && poetry run pytest \
  tests/unittests/test_lftp \
  tests/unittests/test_controller/test_auto_queue.py \
  tests/unittests/test_controller/test_lftp_manager.py \
  tests/unittests/test_controller/test_controller_unit.py \
  tests/unittests/test_controller/test_controller.py \
  tests/unittests/test_controller/test_model_builder.py \
  tests/unittests/test_controller/test_transfer_state_safety.py \
  tests/unittests/test_controller/test_scan_clock_safety.py \
  tests/unittests/test_common/test_status.py \
  tests/unittests/test_web/test_serialize/test_serialize_status.py \
  -q -p no:cacheprovider -rf --tb=line --junitxml=<scratchpad>/117-red.xml
```

Executed from a git worktree checked out at `05f03ae`. `poetry run` inside a worktree resolves to a fresh empty virtualenv (different path hash), so the identical arguments were passed to the main checkout's Poetry interpreter, running against the worktree's code:
`/Users/julianamacbook/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12/bin/python -m pytest <same arguments>` from `<worktree>/src/python`.

**Failures** (26). The node IDs are verbatim from the `-rf` short summary. This pytest version's `-rf --tb=line` summary prints no exception text, so the ` - <exception>` suffix is the first line of the `<failure message>` of the same test in the junit XML of the same run (one long repr truncated with `...`):

```
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_chunk_without_data_line_followed_by_chunk - lftp.job_status_parser.LftpJobStatusParserError: Error parsing lftp job status
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_chunk_without_data_line_followed_by_mirror_header - AssertionError: 2 != 1
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_mirror_empty_followed_by_header_containing_getting_file_list - AssertionError: 2 != 1
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_pget_no_data_line_followed_by_mirror_header - AssertionError: 2 != 1
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_pget_no_data_line_followed_by_pget_header - lftp.job_status_parser.LftpJobStatusParserError: Error parsing lftp job status
FAILED tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_boundary_sequence_pinned_exactly - AssertionError: [] is not None : failure 1 must be unavailable (None)
FAILED tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_timed_out_status_with_empty_buffer_is_unavailable - AssertionError: [] is not None : a timed-out jobs -v is an incomplete observation, not an empty job list
FAILED tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_timed_out_status_with_partial_parseable_buffer_is_unavailable - AssertionError: [{'_LftpJobStatus__id': 1, '_LftpJobStatus__type': <Type.PGET: 'pget'>, '_LftpJobStatus__state': <State.RUNNING: 1>, '_LftpJobStatus__name': ...
FAILED tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_tolerated_parse_failures_report_unavailable_not_empty - AssertionError: [] is not None : failure 1 must be unavailable (None), never []
FAILED tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_changed_size_after_remote_outage_restarts_window - AssertionError: 0 != 1 : failed scans must not establish stability during the outage (D-03/D-04) [t=90]
FAILED tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_failed_remote_scans_spanning_window_do_not_establish_stability - AssertionError: 0 != 1 : failed scans must not advance the stability clock (D-03) [t=90]
FAILED tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_changed_local_size_after_outage_restarts_window - AssertionError: 0 != 1 : failed local scans must not establish idleness during the outage (D-03/D-05) [t=30]
FAILED tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_failed_local_scans_spanning_window_do_not_establish_local_idle - AssertionError: 0 != 1 : failed local scans must not advance the local stability clock (D-03/D-05) [t=30]
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands - AssertionError: <State.DOWNLOADING: 1> != <State.DOWNLOADED: 3>
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size - AssertionError: <State.QUEUED: 2> != <State.DOWNLOADED: 3>
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry - AssertionError: <State.QUEUED: 2> != <State.DEFAULT: 0>
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_timed_out_status_with_empty_buffer_keeps_protection - AssertionError: <State.DOWNLOADING: 1> != <State.DOWNLOADED: 3>
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_timed_out_status_with_partial_parseable_buffer_keeps_protection - AssertionError: <State.DOWNLOADING: 1> != <State.DOWNLOADED: 3>
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestControllerActiveListFrozenWhileStatusUnavailable::test_active_downloading_list_and_scanner_feed_unchanged_on_parse_failure - AssertionError: Lists differ: ['File.One.rar'] != []
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_delete_local_in_one_process_does_not_delete - AssertionError: Expected 'delete_local' to not have been called. Called 1 times.
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_delete_remote_in_one_process_does_not_delete - AssertionError: Expected 'delete_remote' to not have been called. Called 1 times.
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_extract_in_one_process_does_not_extract - AssertionError: Expected 'extract' to not have been called. Called 1 times.
FAILED tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_failed_local_scans_spanning_window_do_not_queue - AssertionError: 0 != 1 : failed local scans must not advance the local stability clock (XFER-05, D-03/D-05) [t=30]
FAILED tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_failed_remote_scans_spanning_window_do_not_queue - AssertionError: 0 != 1 : failed remote scans must not advance the stability clock (XFER-04, D-03) [t=90]
FAILED tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_local_recovery_with_changed_size_restarts_window - AssertionError: 0 != 1 : failed local scans must not establish idleness during the outage (XFER-05, D-03/D-05) [t=30]
FAILED tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_remote_recovery_with_changed_size_restarts_window - AssertionError: 0 != 1 : failed remote scans must not establish stability during the outage (XFER-04, D-03/D-04) [t=90]
```

Breakdown: 5 B1 parser, 4 Lftp status contract (two boundary, two timed-out `jobs -v`), 9 composed B2 (two observed-transfer, two submitted-but-unobserved, two timed-out status, three same-cycle command ordering), 4 AutoQueue B3 unit, 4 composed B3. 5 + 4 + 9 + 4 + 4 = 26, matching the expected count from Plans 117-01 and 117-02.

**Failure types** (from the junit XML: 24 `AssertionError`, 2 `LftpJobStatusParserError`). Two tests fail because `lftp.job_status_parser.LftpJobStatusParserError` escapes the test body: `test_jobs_pget_no_data_line_followed_by_pget_header` and `test_jobs_chunk_without_data_line_followed_by_chunk`. In both, the swallowed header leaves an orphaned sftp or chunk data line that the parser cannot place. pytest reports both as FAILED with that exception, not as a setup ERROR. All other 24 failures are `AssertionError`. None of the 26 is an ImportError, AttributeError or TypeError, so every failure comes from a behavioral assertion (or the parser's own error) and none comes from a missing symbol or a harness mistake.

**Summary line:** `26 failed, 464 passed, 1 warning in 1.39s`

**Ruff** (`ruff check <worktree>/src/python/`, whole tree, ruff 0.15.9 on PATH): `All checks passed!`

**Preservation tests passing on pre-fix code** (part of the 464 passed; each must stay green through the fixes):

- `test_lftp_status_contract.py::TestLftpStatusBoundary::test_empty_output_is_genuinely_empty_list` (empty `jobs -v` output -> `[]`, XFER-03)
- `test_lftp_status_contract.py::TestLftpStatusBoundary::test_escalation_does_not_reset_counter` (escalation at failure `MAX_CONSECUTIVE_STATUS_ERRORS + 1` does not reset the counter, XFER-03 / D-02)
- `test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_genuinely_empty_status_clears_downloading_state` (a genuine empty status clears model state; asserts exactly one QUEUE plus one EXTRACT of the completed `File.One.rar`, XFER-02)
- `test_transfer_state_safety.py::TestControllerActiveListFrozenWhileStatusUnavailable::test_genuinely_empty_status_clears_active_list` (a genuine empty status clears the active-downloading list, XFER-02)
- `test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_delete_local_of_unsubmitted_file_in_same_process_still_dispatches` (name-keyed delete of a different, unsubmitted file in the same batch still dispatches)
- `test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_stop_then_user_queue_after_unavailable_status_resubmits_to_lftp` (Stop then USER QUEUE re-submits to LFTP; codex pass-3 guard for Plan 117-08's kill-path reconciliation)
- `test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_matching_size_across_remote_outage_is_stable` (D-03, remote unit)
- `test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_matching_local_size_across_outage_is_idle` (D-03, local unit)
- `test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_remote_recovery_with_matching_size_queues` (D-03, remote composed)
- `test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_local_recovery_with_matching_size_queues` (D-03, local composed)

| # | Failing test | Requirement | Decision |
|---|--------------|-------------|----------|
| 1 | `test_jobs_pget_no_data_line_followed_by_pget_header` | XFER-01 | D-07, D-08 (audit site #2) |
| 2 | `test_jobs_pget_no_data_line_followed_by_mirror_header` | XFER-01 | D-07, D-08 (audit site #2) |
| 3 | `test_jobs_mirror_empty_followed_by_header_containing_getting_file_list` | XFER-01 | D-07, D-08 (audit site #9) |
| 4 | `test_jobs_chunk_without_data_line_followed_by_mirror_header` | XFER-01 | D-07, D-08 (audit site #10) |
| 5 | `test_jobs_chunk_without_data_line_followed_by_chunk` | XFER-01 | D-07, D-08 (audit site #10) |
| 6 | `test_tolerated_parse_failures_report_unavailable_not_empty` | XFER-03 | D-01, D-02 (spec B2: failures 1..MAX reported unavailable, never `[]`) |
| 7 | `test_boundary_sequence_pinned_exactly` | XFER-03 | D-01, D-02 (spec B2: boundary pinned, failure MAX+1 raises, success resets counter) |
| 8 | `test_timed_out_status_with_empty_buffer_is_unavailable` | XFER-03 | D-01, D-02; codex pass-3 timeout finding (fix: Plan 117-05) |
| 9 | `test_timed_out_status_with_partial_parseable_buffer_is_unavailable` | XFER-03 | D-01, D-02; codex pass-3 timeout finding (fix: Plan 117-05) |
| 10 | `test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands` | XFER-02 | D-01, D-02 (spec B2: isolated parse failure keeps the file active/protected; nothing re-queued or deleted) |
| 11 | `test_active_downloading_list_and_scanner_feed_unchanged_on_parse_failure` | XFER-02 | D-01 (spec B2: active-downloading list unchanged; no downstream `None` -> `[]` collapse) |
| 12 | `test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size` | XFER-02 | D-01, D-02; codex adversarial finding (fix: Plan 117-08) |
| 13 | `test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry` | XFER-02 | D-01, D-02; codex adversarial finding (fix: Plan 117-08) |
| 14 | `test_timed_out_status_with_empty_buffer_keeps_protection` | XFER-02 | D-01, D-02; codex pass-3 timeout finding (fix: Plans 117-05 + 117-08) |
| 15 | `test_timed_out_status_with_partial_parseable_buffer_keeps_protection` | XFER-02 | D-01, D-02; codex pass-3 timeout finding (fix: Plans 117-05 + 117-08) |
| 16 | `test_queue_then_delete_local_in_one_process_does_not_delete` | XFER-02 | D-01; codex pass-2 command-ordering finding (fix: Plan 117-08 Task 3) |
| 17 | `test_queue_then_delete_remote_in_one_process_does_not_delete` | XFER-02 | D-01; codex pass-2 command-ordering finding (fix: Plan 117-08 Task 3) |
| 18 | `test_queue_then_extract_in_one_process_does_not_extract` | XFER-02 | D-01; codex pass-2 command-ordering finding (fix: Plan 117-08 Task 3) |
| 19 | `test_failed_remote_scans_spanning_window_do_not_establish_stability` | XFER-04 | D-03, D-05, D-06 (remote unit) |
| 20 | `test_changed_size_after_remote_outage_restarts_window` | XFER-04 | D-03, D-04, D-05 (remote unit) |
| 21 | `test_failed_local_scans_spanning_window_do_not_establish_local_idle` | XFER-05 | D-03, D-05, D-06 (local unit) |
| 22 | `test_changed_local_size_after_outage_restarts_window` | XFER-05 | D-03, D-04, D-05 (local unit) |
| 23 | `test_failed_remote_scans_spanning_window_do_not_queue` | XFER-04 | D-03, D-05, D-06 (remote composed) |
| 24 | `test_remote_recovery_with_changed_size_restarts_window` | XFER-04 | D-03, D-04, D-05 (remote composed) |
| 25 | `test_failed_local_scans_spanning_window_do_not_queue` | XFER-05 | D-03, D-05, D-06 (local composed) |
| 26 | `test_local_recovery_with_changed_size_restarts_window` | XFER-05 | D-03, D-04, D-05 (local composed) |

Rows 12-18 sit under XFER-02 (downstream consumers must not collapse unavailable or not-yet-observed state into "no jobs"). Rows 8-9 and 14-15 are the timed-out `jobs -v` cases: rows 8-9 are unit tests (XFER-03 boundary, Plan 117-05) and rows 14-15 are the composed tests (XFER-02, Plans 117-05 + 117-08).

### New-contract tests (added with the fixes; not regressions)

These pin new contracts introduced by the fixes. They have no pre-fix behavior to fail against, so they are not part of the RED evidence. Each is `pending` until its plan lands:

| Plan | Tests | Status |
|------|-------|--------|
| 117-05 | `Lftp.kill` on unavailable status raises (x3) | pending |
| 117-05 | Lftp timeout neither counts toward nor resets the parser-error counter; timeout logs no raw output (x2) | pending |
| 117-05 | `LftpManager.status()` passes `None` / `[]` through unchanged (x2) | pending |
| 117-06 | `ControllerStatus` successful-scan clock defaults | pending |
| 117-06 | Successful-scan clock set only on not-failed scans (x4) | pending |
| 117-06 | Status serializer keys unchanged (D-06) | pending |
| 117-08 | `LftpManager` submitted-but-unobserved tracking (x6) + kill-path reconciliation (x3) | pending |
| 117-08 | `ModelBuilder` submitted -> QUEUED derivation (x7) | pending |
| 117-08 | `CommandProcessor` submitted-but-unobserved guard (x4) | pending |

### CI-only: integration counter tests flip `[]` -> `None`

Four integration tests in `src/python/tests/integration/test_lftp/test_lftp_protocol.py` pin the old tolerated-error contract (`[] == self.lftp.status()`): `test_status_real_parser_raises_on_malformed_output`, `test_status_parser_error_increments_and_swallows`, `test_status_parser_error_exceeds_max_reraises`, `test_status_parser_error_counter_resets_on_success`. They need the Docker sshd / `testgroup` fixture and the lftp binary, so they cannot run on this host and are not part of this RED run. The host-runnable `test_lftp_status_contract.py` carries the RED proof for the same boundary. Plan 117-05 flips the integration assertions to `assertIsNone`, and CI `unittests-python` verifies them.

## GREEN (post-fix) — Plan 117-07

pending
