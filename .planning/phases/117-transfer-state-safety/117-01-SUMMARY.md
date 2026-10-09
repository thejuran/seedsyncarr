---
phase: 117-transfer-state-safety
plan: 01
subsystem: lftp-status / controller transfer state
tags: [python, pytest, lftp, parser, status-contract, regression, red-first]
requires: []
provides:
  - RED evidence for XFER-01 (parser header swallowing, 5 tests)
  - RED evidence for XFER-03 (Lftp status boundary + timed-out jobs -v, 4 tests)
  - RED evidence for XFER-02 (composed downstream + same-cycle command ordering, 9 tests)
  - 6 preservation tests that pass on unfixed code and must stay green
affects:
  - Plan 04 (parser peek-before-pop + header guard)
  - Plan 05 (Lftp.status returns None on tolerated error / timeout)
  - Plan 08 (submitted-but-unobserved protection, command-ordering guard, Stop reconciliation)
tech-stack:
  added: []
  patterns:
    - scripted pexpect process driving the REAL Lftp.__run_command (str = completed output, _TimedOut = pexpect TIMEOUT)
    - real LftpManager injected via patch('controller.lftp_manager.Lftp') and patch('controller.controller.LftpManager')
key-files:
  created:
    - src/python/tests/unittests/test_lftp/test_lftp_status_contract.py
    - src/python/tests/unittests/test_controller/test_transfer_state_safety.py
  modified:
    - src/python/tests/unittests/test_lftp/test_job_status_parser.py
decisions:
  - "Genuine-empty-status preservation test asserts exactly one QUEUE plus one EXTRACT of the completed File.One.rar, not queue_command.call_count == 1 (auto-extract of a really completed archive is correct behavior)"
metrics:
  duration: ~25 min
  completed: 2026-10-08
  tasks: 3
  files: 3
---

# Phase 117 Plan 01: RED regressions for parser header-swallowing and the status contract Summary

Eighteen failing regression tests now pin three defects: parser header-swallowing at sites #2, #9 and #10; the tolerated-error and timed-out `jobs -v` paths reporting `[]` instead of "unavailable"; and the downstream damage that causes (demoted DOWNLOADING files, false DOWNLOADED commits, duplicate re-queues, a cleared active list, and same-cycle extract/delete dispatch). Six preservation tests pass on current code. Only test files changed.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Five B1 header-swallowing parser regressions | 5fde19f | test_job_status_parser.py |
| 2 | Host-runnable Lftp status-boundary contract tests | 0def8a6 | test_lftp_status_contract.py (new) |
| 3 | Composed B2 downstream regression module | e6fe451 | test_transfer_state_safety.py (new) |

## Verification (observed on unfixed code)

`pytest tests/unittests/test_lftp tests/unittests/test_controller/test_transfer_state_safety.py -q -rf --tb=no`. Result: **18 failed, 132 passed**. Verbatim `-rf` short summary:

```
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_chunk_without_data_line_followed_by_chunk
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_chunk_without_data_line_followed_by_mirror_header
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_mirror_empty_followed_by_header_containing_getting_file_list
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_pget_no_data_line_followed_by_mirror_header
FAILED tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_pget_no_data_line_followed_by_pget_header
FAILED tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_boundary_sequence_pinned_exactly
FAILED tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_timed_out_status_with_empty_buffer_is_unavailable
FAILED tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_timed_out_status_with_partial_parseable_buffer_is_unavailable
FAILED tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_tolerated_parse_failures_report_unavailable_not_empty
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_timed_out_status_with_empty_buffer_keeps_protection
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_timed_out_status_with_partial_parseable_buffer_keeps_protection
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestControllerActiveListFrozenWhileStatusUnavailable::test_active_downloading_list_and_scanner_feed_unchanged_on_parse_failure
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_delete_local_in_one_process_does_not_delete
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_delete_remote_in_one_process_does_not_delete
FAILED tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_extract_in_one_process_does_not_extract
18 failed, 132 passed, 1 warning
```

Failure reasons, taken from the `--tb=line` output of each per-file run:
- Parser: `..._followed_by_pget_header` and `..._followed_by_chunk` fail with `LftpJobStatusParserError` (the root `ValueError` is an orphaned sftp line or an orphaned chunk data line). The other three fail with `AssertionError: 2 != 1` because a job is silently dropped.
- Contract: all four fail with an `AssertionError` (`[] is not None`, or a one-element job list `is not None`). The two preservation tests pass.
- Composed: all nine fail with an `AssertionError`. Model-state mismatches show up as DOWNLOADING != DOWNLOADED, QUEUED != DEFAULT or QUEUED != DOWNLOADED. The active list shows `['File.One.rar'] != []`. The extract/delete_local/delete_remote checks fail with "Expected ... to not have been called. Called 1 times". The four preservation tests pass.
- No `ImportError`, `AttributeError` or `TypeError` appears in any run.

Other checks:
- `tests/unittests/test_controller` (excluding test_extract and test_scan): 9 failed (only the new RED tests) and 567 passed, so no cross-test interference.
- Whole-tree `ruff check src/python/`: `All checks passed!` (ruff 0.15.9).
- `git status --porcelain src/python/lftp/ src/python/common/ src/python/controller/` is empty. No production file was touched.
- Acceptance greps: parser `def test_` = 47 and `assertRaises` unchanged at 3. Contract `def test_` = 6, `MAX_CONSECUTIVE_STATUS_ERRORS` = 4, `range(2)` = 0, no kill tests, `class _TimedOut` = 1. Composed `def test_` = 13, `status.return_value = None` = 0, `submitted_unobserved_file_names|set_submitted_files` = 0, `_Lftp__run_command` = 0, `_CommandProcessor__` = 0, `controller.controller.LftpManager` = 1, `REQUEUE_COOLDOWN_SECONDS` = 1. The file is 556 lines (min 320).

**The suite is intentionally red until Plans 04, 05 and 08 land:**
- The 5 parser tests turn green with Plan 04.
- The 4 contract tests, including both unit `test_timed_out_status_*_is_unavailable` tests, turn green with Plan 05.
- `test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands` and the active-list test turn green with Plan 05.
- The two `test_submitted_but_unobserved_*` tests, the three `test_queue_then_*_in_one_process_*` tests and the two composed `test_timed_out_status_*_keeps_protection` tests stay red through wave 3. They turn green only once Plan 08 has landed; the timed-out pair also needs Plan 05.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong expectation in the genuine-empty preservation test**
- **Found during:** Task 3
- **Issue:** The plan has `test_genuinely_empty_status_clears_downloading_state` assert `queue_command.call_count == 1`. With `auto_extract=True`, File.One.rar really is complete after a genuine empty status: it becomes DOWNLOADED, `.rar` is extractable and the local size is greater than 0. So AutoQueue correctly issues one EXTRACT, and the test failed with `1 != 2` on unfixed code, although it is a preservation test that must pass.
- **Fix:** The test now asserts exactly one QUEUE command (no re-queue inside the cooldown) and that the EXTRACT commands are exactly `["File.One.rar"]`. Both are correct before and after the fixes.
- **Files modified:** test_transfer_state_safety.py
- **Commit:** e6fe451

**2. [Process] Three per-task commits instead of the single commit named in the plan**
- The plan's `<output>` names one combined commit. The executor protocol and this run's instructions require atomic per-task commits, so there are three `test(117-01)` commits, each containing only test files.

**3. [Environment] Verification ran with the main checkout's Poetry venv interpreter**
- `poetry run` in the worktree creates a fresh, empty virtualenv because the path hash differs. Verification instead ran `/Users/julianamacbook/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12/bin/python -m pytest` from the worktree's `src/python`, so the worktree code was tested. Ruff came from `ruff` on PATH (0.15.9), not the venv. A stray empty venv `seedsyncarr-Xo-G7qCG-py3.12` was created in the Poetry cache by the first `poetry run` attempt. It is harmless and outside the repo.

### Implementation notes (within plan latitude)
- Parser goldens came from running the real parser on well-formed variants of each fixture. `e.txt at 10 (5%)` gives TransferState(None x5), mirror `c` gives (100, 1126, 9, None, None) with `c/ca` (None x5), the `got 100 of 1000` pget gives (100, 1000, 10, None, None), and the `1/2 (50%)` mirrors give (1, 2, 50, None, None).
- The pipeline class's `jobs -v` script is a list consumed in place, and `_cycle` appends one item per cycle. Scan results are set per cycle through `pop_latest_results.return_value`, which is equivalent to the planned per-cycle side_effect queue.
- `_RUNNING_PGET_*` fixtures are built by one `_running_pget_output(basename, job_id)` helper.

## Known Stubs

None.

## Self-Check: PASSED
- FOUND: src/python/tests/unittests/test_lftp/test_lftp_status_contract.py
- FOUND: src/python/tests/unittests/test_controller/test_transfer_state_safety.py
- FOUND: src/python/tests/unittests/test_lftp/test_job_status_parser.py (modified)
- FOUND commits: 5fde19f, 0def8a6, e6fe451
