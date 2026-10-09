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

These pin new contracts introduced by the fixes. They have no pre-fix behavior to fail against, so they are not part of the RED evidence. Status was updated by the Plan 117-07 GREEN run (names listed in the GREEN section below):

| Plan | Tests | Status |
|------|-------|--------|
| 117-05 | `Lftp.kill` on unavailable status raises (x3) | passed (Plan 117-07) |
| 117-05 | Lftp timeout neither counts toward nor resets the parser-error counter; timeout logs no raw output (x2) | passed (Plan 117-07) |
| 117-05 | `LftpManager.status()` passes `None` / `[]` through unchanged (x2) | passed (Plan 117-07) |
| 117-06 | `ControllerStatus` successful-scan clock defaults | passed (Plan 117-07) |
| 117-06 | Successful-scan clock set only on not-failed scans (x4; landed as x6) | passed (Plan 117-07) |
| 117-06 | Status serializer keys unchanged (D-06) | passed (Plan 117-07) |
| 117-08 | `LftpManager` submitted-but-unobserved tracking (x6) + kill-path reconciliation (x3) | passed (Plan 117-07) |
| 117-08 | `ModelBuilder` submitted -> QUEUED derivation (x7) | passed (Plan 117-07) |
| 117-08 | `CommandProcessor` submitted-but-unobserved guard (x4) | passed (Plan 117-07) |

### CI-only: integration counter tests flip `[]` -> `None`

Four integration tests in `src/python/tests/integration/test_lftp/test_lftp_protocol.py` pin the old tolerated-error contract (`[] == self.lftp.status()`): `test_status_real_parser_raises_on_malformed_output`, `test_status_parser_error_increments_and_swallows`, `test_status_parser_error_exceeds_max_reraises`, `test_status_parser_error_counter_resets_on_success`. They need the Docker sshd / `testgroup` fixture and the lftp binary, so they cannot run on this host and are not part of this RED run. The host-runnable `test_lftp_status_contract.py` carries the RED proof for the same boundary. Plan 117-05 flips the integration assertions to `assertIsNone`, and CI `unittests-python` verifies them.

## GREEN (post-fix) — Plan 117-07

Run on the merged phase tree at post-fix SHA **`d7c76bc`** (branch `safety-patch-1.7.4`, after all four fix plans were merged). The run used a git worktree checked out at that SHA with the main checkout's Poetry interpreter (`/Users/julianamacbook/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12/bin/python -m pytest`), for the same reason as the RED run.

**Fix commits** (production code; test-only commits omitted):

| Plan | Fix | Commits |
|------|-----|---------|
| 117-04 | B1 parser peek-before-pop (XFER-01) | `eaa4847`, `292c496` |
| 117-05 | B2 `Lftp.status()` None-vs-empty, timeout as unavailable, `kill` refuses on None (XFER-02, XFER-03) | `d313ff3` (test pin `e8907d8`) |
| 117-06 | B3 successful-scan stability clock (XFER-04, XFER-05) | `7cfa98f` |
| 117-08 | B2 submitted-but-unobserved protection (XFER-02) | `4bc2b79`, `0d5b1b8`, `a96e160` |

`git diff --stat 7da18e0 d7c76bc -- src/python/lftp src/python/common src/python/controller ':!src/python/tests'` lists exactly nine production files: `common/status.py`, `controller/auto_queue.py`, `controller/command_processor.py`, `controller/controller.py`, `controller/lftp_manager.py`, `controller/model_builder.py`, `controller/model_pipeline.py`, `lftp/job_status_parser.py`, `lftp/lftp.py` (220 insertions, 40 deletions).

### Targeted regressions (the 26 RED tests)

**Command:**

```
cd src/python && <poetry python> -m pytest \
  tests/unittests/test_lftp/test_job_status_parser.py \
  tests/unittests/test_lftp/test_lftp_status_contract.py \
  tests/unittests/test_controller/test_transfer_state_safety.py \
  tests/unittests/test_controller/test_auto_queue.py \
  tests/unittests/test_controller/test_scan_clock_safety.py \
  -v -p no:cacheprovider -k "<the 26 RED names joined by ' or '>"
```

```
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_chunk_without_data_line_followed_by_chunk PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_chunk_without_data_line_followed_by_mirror_header PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_mirror_empty_followed_by_header_containing_getting_file_list PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_pget_no_data_line_followed_by_mirror_header PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_pget_no_data_line_followed_by_pget_header PASSED
tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_boundary_sequence_pinned_exactly PASSED
tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_timed_out_status_with_empty_buffer_is_unavailable PASSED
tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_timed_out_status_with_partial_parseable_buffer_is_unavailable PASSED
tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_tolerated_parse_failures_report_unavailable_not_empty PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_timed_out_status_with_empty_buffer_keeps_protection PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_timed_out_status_with_partial_parseable_buffer_keeps_protection PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestControllerActiveListFrozenWhileStatusUnavailable::test_active_downloading_list_and_scanner_feed_unchanged_on_parse_failure PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_delete_local_in_one_process_does_not_delete PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_delete_remote_in_one_process_does_not_delete PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_extract_in_one_process_does_not_extract PASSED
tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_changed_size_after_remote_outage_restarts_window PASSED
tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_failed_remote_scans_spanning_window_do_not_establish_stability PASSED
tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_changed_local_size_after_outage_restarts_window PASSED
tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_failed_local_scans_spanning_window_do_not_establish_local_idle PASSED
tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_failed_local_scans_spanning_window_do_not_queue PASSED
tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_failed_remote_scans_spanning_window_do_not_queue PASSED
tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_local_recovery_with_changed_size_restarts_window PASSED
tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_remote_recovery_with_changed_size_restarts_window PASSED
```

**Summary line:** `26 passed, 133 deselected, 1 warning in 0.14s`

All 26 RED rows in the table above now pass, with 0 failures.

### Phase quick run

Same ten paths as the RED command, without `-rf --junitxml`: `524 passed, 1 warning in 0.77s`. 0 failed.

**Delta vs RED.** The RED run was `26 failed, 464 passed`, so 490 tests were collected.

- The 26 RED tests now pass: 464 + 26 = 490 passing.
- The fix plans added 34 new test functions, all passing: 490 + 34 = **524**, which matches the observed total.
  - 117-05: 7 (`Lftp.kill` x3, timeout semantics x2, `LftpManager` pass-through x2)
  - 117-06: 7 (success-clock writes x6 plus serializer keys x1). The plan asked for 4 success-clock tests; Plan 06 added 2 extra cases. The status-defaults check extends the existing `test_default_values` and is not a new function.
  - 117-08: 20 (`LftpManager` tracking x6 + kill-path reconciliation x3, `ModelBuilder` x7, `CommandProcessor` guard x4)
  - 7 + 7 + 20 = 34. The plan estimated 32 before execution. The extra 2 are the success-clock cases recorded in the 117-06 SUMMARY.

### New-contract tests (pass after fix; not regressions)

All 34 new functions pass in the quick run. A separate `-v` run selecting these classes and names gave `34 passed`. That selection covered 33 of the new functions plus the extended `test_default_values`. The `-k` filter missed `test_queue_failure_does_not_record_submission`, but the quick run covers it.

- 117-05, `test_lftp_status_contract.py`:
  - `TestLftpKillWhenStatusUnavailable::test_kill_raises_when_status_unavailable`
  - `TestLftpKillWhenStatusUnavailable::test_kill_still_returns_false_when_job_absent_from_available_status`
  - `TestLftpKillWhenStatusUnavailable::test_kill_error_message_does_not_echo_job_name`
  - `TestLftpStatusTimeoutSemantics::test_timeout_does_not_count_toward_or_reset_parser_error_counter`
  - `TestLftpStatusTimeoutSemantics::test_timed_out_status_logs_no_raw_output`
- 117-05, `test_lftp_manager.py`: `test_status_passes_none_through_unchanged`, `test_status_passes_empty_list_through_unchanged`
- 117-06, `test_status.py`: `TestStatus::test_default_values` (extended to cover both success clocks; not a new function)
- 117-06, `test_controller.py::TestUpdateControllerStatusSuccessClocks`: `test_remote_success_advances_success_clock`, `test_remote_failure_does_not_advance_success_clock`, `test_local_success_advances_success_clock`, `test_local_failure_does_not_advance_success_clock`, `test_failed_first_scans_leave_success_clocks_none`, `test_none_scan_results_leave_success_clocks_none`
- 117-06, `test_serialize_status.py`: `test_controller_status_keys_unchanged_by_success_clocks`
- 117-08, `test_lftp_manager.py` (tracking x6): `test_queue_records_submitted_unobserved_file`, `test_queue_failure_does_not_record_submission`, `test_successful_status_clears_submitted_set`, `test_genuinely_empty_status_clears_submitted_set`, `test_unavailable_status_keeps_submitted_set`, `test_submitted_unobserved_file_names_returns_copy`
- 117-08, `test_lftp_manager.py` (kill-path reconciliation x3): `test_successful_kill_reconciles_submitted_name`, `test_kill_not_found_still_reconciles_submitted_name`, `test_failed_kill_keeps_submitted_name`
- 117-08, `test_model_builder.py` (x7): `test_submitted_file_without_status_is_queued`, `test_submitted_file_with_preallocated_local_size_is_not_downloaded`, `test_lftp_status_takes_precedence_over_submitted`, `test_submitted_name_with_no_other_source_is_ignored`, `test_submitted_directory_children_are_queued`, `test_set_submitted_files_invalidates_cache_only_on_change`, `test_clear_resets_submitted_files`
- 117-08, `test_controller_unit.py::TestControllerCommandSubmittedUnobservedGuard` (x4): `test_extract_rejected_while_submitted_unobserved`, `test_delete_local_rejected_while_submitted_unobserved`, `test_delete_remote_rejected_while_submitted_unobserved`, `test_queue_not_resubmitted_while_submitted_unobserved`

**Preservation tests.** These passed before the fix and still pass after it. They are the ten tests listed in the RED section, including the four in the safety module: `test_genuinely_empty_status_clears_downloading_state`, `test_genuinely_empty_status_clears_active_list`, `test_delete_local_of_unsubmitted_file_in_same_process_still_dispatches` and `test_stop_then_user_queue_after_unavailable_status_resubmits_to_lftp`. A `-k` run of the ten names on `d7c76bc` gave `10 passed, 102 deselected`.

### CI-only: integration counter tests

Four counter tests in `src/python/tests/integration/test_lftp/test_lftp_protocol.py` were not run on this host: `test_status_real_parser_raises_on_malformed_output`, `test_status_parser_error_increments_and_swallows`, `test_status_parser_error_exceeds_max_reraises` and `test_status_parser_error_counter_resets_on_success`. They need the Docker sshd / `testgroup` fixture and the lftp binary.

Plan 117-05 flipped **10** tolerated-error assertions in these tests to `assertIsNone(self.lftp.status())`. Its action text said 8, but its own acceptance criterion and line list gave 10, and 10 were flipped. The one genuine-empty success line stays `assertEqual([], ...)`. CI `unittests-python` verifies these tests.

### Deferred parser sites (D-09)

These sites are recorded in the 117-04 SUMMARY and deliberately left unchanged:

- **#1 pget sftp-line check** (`"sftp" in lines[0]` in `PgetJobParser.parse_header`). When it misfires, a later parse step almost always raises loudly, so it does not cause a silent job loss.
- **#6 QueueParser line-3 unconditional pop.** This assumes lftp always prints "Now executing:" or "Queue is stopped." when a job is active.
- **#8 `\transfer` with no data line** (`_handle_file_transfer`, consume-then-raise). After B2 this shows up as "status unavailable", never as a lost job. Revisit if NAS logs show "Missing chunk data for filename".

### Accepted behavior change: Stop during a status failure

`Lftp.kill` now raises `LftpJobStatusParserError` when status is unavailable, which happens after a tolerated parse error or a timed-out `jobs -v`. `CommandProcessor._handle_stop` already maps that error to the generic "Lftp error" 500 response, and nothing is added to the stopped set. Before the fix, the empty list made kill report "not found", so Stop could report success while lftp kept downloading. The owner accepted this change. The user can retry Stop once status recovers.

### Timeout semantics

A `jobs -v` whose pexpect expect timed out is an incomplete observation. `Lftp.status()` returns `None` without parsing the buffer, even if the partial buffer would parse. The timeout neither counts toward nor resets `MAX_CONSECUTIVE_STATUS_ERRORS`, which is still 2. Stalls remain `LftpManager`'s stall-backoff concern. Timeout handling for every other command (setters, queue, kill, kill_all) is unchanged. This came from the codex pass-3 finding and is pinned by `test_timeout_does_not_count_toward_or_reset_parser_error_counter`.

### Submitted-unobserved protection (Plan 08, codex finding)

- `LftpManager` owns an in-process set of names that lftp accepted a QUEUE for but that no successful status has observed yet. `ModelBuilder` shows them as the existing **Queued** state until the first successful status, with no new UI indicator (D-01). An observed lftp status always wins.
- Any status that returns a list, including a genuine `[]`, clears the whole set. `None`, an exception or the stall backoff leave it in place. While status stays unavailable, the file stays Queued. This is the D-02 freeze and mirrors the frozen DOWNLOADING state for observed transfers. The file is never re-queued after the cooldown, never marked DOWNLOADED from a preallocated local size and never auto-extracted. The set lives in process memory only and is not persisted.
- `CommandProcessor` also checks the set when it executes a command. Extract, delete-local and delete-remote of a submitted-but-unobserved name return 409. A repeated QUEUE returns success without submitting the job to lftp again. This closes the same-cycle QUEUE-then-destructive ordering gap from the codex pass-2 finding: commands in one batch are handled against the model as it was frozen at the last build.
- The STOP handler is unchanged. `LftpManager.kill` removes the stopped name from the set after `Lftp.kill` returns, whether it returned True or False. If kill raises, the name stays protected. A Stop followed by a user re-queue therefore really re-submits the job (codex pass-3). This is pinned by the Plan 01 preservation test `test_stop_then_user_queue_after_unavailable_status_resubmits_to_lftp` and the three kill-path `LftpManager` unit tests.
- Discretion rationale (from the 117-08 SUMMARY): the set lives in `LftpManager` because it is the only object that knows a queue command was actually sent and whether the next status was available. A synchronous model rebuild per command was rejected in favour of a cheap membership test.

### Codex adversarial review

Four codex passes reviewed the phase plans. Passes 1-3 produced findings that plan revisions fixed: submitted-but-unobserved protection, the same-cycle command guard, and timeout-as-unavailable plus Stop-path reconciliation. The owner accepted the pass-4 finding as a known follow-up: after a timeout, the LFTP command stream needs to resync, because a delayed prompt can make the next status look like "no jobs". It is recorded as backlog Phase 999.2 (`.planning/phases/999.2-lftp-command-stream-resync-after-timeout/`) and is not fixed in this phase.

### Full host suite

**Full host suite.** Run in two parts, as in Phase 116, at `d7c76bc` with the main checkout's Poetry interpreter. That interpreter has pytest-timeout, so the extract-process tests now fail on the 60 s per-test timeout (or the 2 s in-test timeout) instead of hanging the run.

- Part 1, every file except the four baseline files (`--ignore` on each): `1471 passed, 2 warnings in 40.88s`. 0 failed, 0 errors. The Phase 116 figure was 1401; the 70 extra are the tests Phase 117 added.
- Part 2, the baseline files run one at a time under a 60 s external alarm (`perl -e 'alarm 60; exec @ARGV'`):
  - `test_ssh/test_sshcp.py`: `11 failed` (needs a local sshd)
  - `test_controller/test_scan/test_scanner_process.py`: `3 failed, 1 passed, 3 errors`
  - `test_system/test_scanner.py`: `1 failed, 19 passed` (`test_scan_file_with_latin_chars`)
  - `test_controller/test_extract/test_extract_process.py`: `6 failed in 32.93s` (pytest-timeout fired on each; no alarm needed)
- Total: 21 failed / 3 errors, all in the four pre-existing baseline files. This equals the Phase 116 baseline of 21 failed / 3 errors: **no new failures** vs baseline.

The four macOS-only failures that Plan 117-08 logged in `deferred-items.md` (3 in `test_scanner_process.py` and `test_extract_process.py::test_calls_start_dispatch`, from `spawn` pickling a MagicMock or a 2 s timeout) are part of these baseline files. The same files fail with the same counts in the Phase 116 baseline, which predates every Phase 117 production change. They are pre-existing and environmental (macOS `spawn` vs Linux `fork` in CI), not caused by this phase.

**Ruff** (`ruff check <worktree>/src/python/`, whole tree, ruff 0.15.9 on PATH): `All checks passed!`
