---
phase: 117
slug: transfer-state-safety
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-10-08
---

# Phase 117 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `117-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + unittest.TestCase; pytest-timeout 60s |
| **Config file** | `src/python/pyproject.toml` (`fail_under = 88`) |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_lftp tests/unittests/test_controller/test_auto_queue.py tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_controller_unit.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_model_builder.py tests/unittests/test_controller/test_transfer_state_safety.py tests/unittests/test_controller/test_scan_clock_safety.py tests/unittests/test_common/test_status.py tests/unittests/test_web/test_serialize/test_serialize_status.py -q -p no:cacheprovider` |
| **Full suite command** | `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider --ignore=tests/unittests/test_ssh/test_sshcp.py --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py --ignore=tests/unittests/test_system/test_scanner.py --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py` (host part 1), then the four baseline files individually under a 60 s external alarm (host part 2); CI `make run-tests-python` |
| **Lint gate** | `ruff check <repo>/src/python/` (whole tree) |
| **Estimated runtime** | ~1 second (quick), ~45 seconds (host part 1) + ~35 seconds (host part 2) |

---

## Sampling Rate

- **After every task commit:** quick run command + whole-tree ruff
- **After every plan wave:** host full suite (no new failures vs baseline)
- **Before `/bm:verify-work`:** CI `unittests-python` (integration + coverage ≥ 88) and `lint-python` green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Requirement→test mapping. Status is from the Plan 117-07 GREEN run at `d7c76bc` (see `117-REL01-EVIDENCE.md` § GREEN).

| Requirement | Behavior | Test Type | Automated Command | Tests | Fails on old code? | Status |
|-------------|----------|-----------|-------------------|-------|--------------------|--------|
| XFER-01 | pget (no data) → pget / mirror header; `\chunk` (no data) → mirror / `\chunk`; mirror-empty → "Getting file list" header | unit | `pytest tests/unittests/test_lftp/test_job_status_parser.py -q` | `test_jobs_pget_no_data_line_followed_by_pget_header`, `test_jobs_pget_no_data_line_followed_by_mirror_header`, `test_jobs_chunk_without_data_line_followed_by_mirror_header`, `test_jobs_chunk_without_data_line_followed_by_chunk`, `test_jobs_mirror_empty_followed_by_header_containing_getting_file_list` | YES | ✅ green |
| XFER-01 | Existing parser fixtures unchanged | unit | `pytest tests/unittests/test_lftp -q` | whole `test_lftp` package (incl. `test_queue_and_jobs_4`, `test_jobs_missing_pget_data_line`, `test_parse_header_consumes_sftp_line`) | passes both | ✅ green |
| XFER-02 | Composed parse error mid-download → protection kept, no QUEUE/EXTRACT/delete | composed | `pytest tests/unittests/test_controller/test_transfer_state_safety.py -q` | `test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands`, `test_active_downloading_list_and_scanner_feed_unchanged_on_parse_failure` | YES | ✅ green |
| XFER-02 | `Lftp.kill` on unavailable raises `LftpJobStatusParserError` | unit | `pytest tests/unittests/test_lftp/test_lftp_status_contract.py -q` | `TestLftpKillWhenStatusUnavailable` x3 | new | ✅ green |
| XFER-02 | Transfer submitted to lftp but not yet observed (parse failure right after QUEUE) stays QUEUED: no re-queue after cooldown expiry, not DOWNLOADED from a preallocated local size, not committed/extracted/deleted (codex finding; Plan 08) | composed + unit | safety file + `pytest tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_model_builder.py -q` | composed: `test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size`, `test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry`; unit: `LftpManager` tracking x6, `ModelBuilder` submitted → QUEUED x7 | YES (composed) / new (unit) | ✅ green |
| XFER-02 | Same-cycle command ordering: QUEUE then EXTRACT / DELETE_LOCAL / DELETE_REMOTE for one DEFAULT file in a single `Controller.process()` dispatches no file operation and reports 409; repeated QUEUE is not re-submitted; a never-submitted file in the same batch is unaffected (codex pass-2 finding; Plan 08 Task 3 CommandProcessor guard) | composed (Controller + real LftpManager) + unit | safety file + `pytest tests/unittests/test_controller/test_controller_unit.py -q` | composed: `test_queue_then_extract_in_one_process_does_not_extract`, `test_queue_then_delete_local_in_one_process_does_not_delete`, `test_queue_then_delete_remote_in_one_process_does_not_delete`, preservation `test_delete_local_of_unsubmitted_file_in_same_process_still_dispatches`; unit: `TestControllerCommandSubmittedUnobservedGuard` x4 | YES (composed x3) / new (unit x4) | ✅ green |
| XFER-02 / XFER-03 | A `jobs -v` whose pexpect expect timed out (empty or partially parseable buffer) is reported unavailable (None), never parsed as a complete listing; timeouts neither count toward nor reset the parser-error counter; composed: observed DOWNLOADING and submitted QUEUED protection survive the timeout (codex pass-3 finding; Plan 05 unit, Plans 05+08 composed) | unit + composed | contract file + safety file | unit: `test_timed_out_status_with_empty_buffer_is_unavailable`, `test_timed_out_status_with_partial_parseable_buffer_is_unavailable`, `TestLftpStatusTimeoutSemantics` x2; composed: `test_timed_out_status_with_empty_buffer_keeps_protection`, `test_timed_out_status_with_partial_parseable_buffer_keeps_protection` | YES (unit x2, composed x2) / new (counter semantics x2) | ✅ green |
| XFER-02 | After submitted → unavailable → STOP (Lftp.kill returned) → USER QUEUE, a second lftp `queue` command is really sent: LftpManager.kill discards the stopped name from the submitted set (codex pass-3 finding; Plan 08 Task 1) | composed + unit | safety file + `pytest tests/unittests/test_controller/test_lftp_manager.py -q` | `test_stop_then_user_queue_after_unavailable_status_resubmits_to_lftp`; unit: `test_successful_kill_reconciles_submitted_name`, `test_kill_not_found_still_reconciles_submitted_name`, `test_failed_kill_keeps_submitted_name` | preservation (passes on old code; guards Plan 08) / new (unit x3) | ✅ green |
| XFER-03 | Failures 1..MAX → None; MAX+1 raises; success resets; empty → [] clears | unit + composed | contract file + safety file | `test_tolerated_parse_failures_report_unavailable_not_empty`, `test_boundary_sequence_pinned_exactly`; preservation `test_empty_output_is_genuinely_empty_list`, `test_escalation_does_not_reset_counter`, `test_genuinely_empty_status_clears_downloading_state`, `test_genuinely_empty_status_clears_active_list`; `LftpManager` pass-through x2 | YES / preservation | ✅ green (integration flips: CI-only) |
| XFER-04 | Failed remote scans spanning window → not queued; D-03/D-04 cases; UI fields unchanged | unit + composed | `pytest tests/unittests/test_controller/test_auto_queue.py tests/unittests/test_controller/test_scan_clock_safety.py -q` + serializer test | `test_failed_remote_scans_spanning_window_do_not_establish_stability`, `test_changed_size_after_remote_outage_restarts_window`, `test_failed_remote_scans_spanning_window_do_not_queue`, `test_remote_recovery_with_changed_size_restarts_window`; preservation `test_matching_size_across_remote_outage_is_stable`, `test_remote_recovery_with_matching_size_queues`; new `TestUpdateControllerStatusSuccessClocks` x6, `test_controller_status_keys_unchanged_by_success_clocks`, `test_default_values` (extended) | YES | ✅ green |
| XFER-05 | Failed local scans spanning window → gate holds; D-05 both cases | unit + composed | `pytest tests/unittests/test_controller/test_auto_queue.py tests/unittests/test_controller/test_scan_clock_safety.py -q` | `test_failed_local_scans_spanning_window_do_not_establish_local_idle`, `test_changed_local_size_after_outage_restarts_window`, `test_failed_local_scans_spanning_window_do_not_queue`, `test_local_recovery_with_changed_size_restarts_window`; preservation `test_matching_local_size_across_outage_is_idle`, `test_local_recovery_with_matching_size_queues` | YES | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unittests/test_lftp/test_lftp_status_contract.py` — B2 boundary + timed-out `jobs -v` (scripted pexpect process) + kill-on-None + timeout counter semantics
- [x] `tests/unittests/test_controller/test_transfer_state_safety.py` — composed B2 downstream (observed + submitted-but-unobserved transfers + timed-out status + same-cycle command ordering with a real LftpManager inside the Controller + Stop-then-requeue preservation)
- [x] `tests/unittests/test_controller/test_scan_clock_safety.py` — composed B3 (remote and local successful-scan clock, D-03/D-04/D-05)
- [x] `tests/unittests/test_controller/test_auto_queue.py` — new-field None init in setUps; `_set_scan(failed=)`; `_cycle` success clock
- [x] `117-REL01-EVIDENCE.md` — RED section (old code + test-only commit) and GREEN section

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Integration counter tests flipped `[]`→`None` (10 assertions in 4 tests) | XFER-03 | Require CI Docker (lftp binary + ssh) | Confirm CI `unittests-python` green |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

Host evidence at `d7c76bc`: 26/26 RED regressions pass; quick run `524 passed`; host full suite part 1 `1471 passed`, 0 failed / 0 errors; baseline files 21 failed / 3 errors (unchanged from the Phase 116 baseline); whole-tree ruff `All checks passed!`.

**Approval:** signed off 2026-10-08, pending CI unittests-python + lint-python
