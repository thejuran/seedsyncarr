---
phase: 117-transfer-state-safety
verified: 2026-10-08T00:00:00Z
status: passed
score: 5/5 roadmap success criteria verified; 5/5 requirements satisfied
has_blocking_gaps: false
overrides_applied: 0
---

# Phase 117: Transfer-State Safety Verification Report

**Phase Goal:** SeedSyncarr never makes a re-queue, auto-queue, or delete decision from a transfer state it did not actually observe — (B1) the LFTP `jobs -v` parser never consumes another job's header; (B2) an unparseable or timed-out status is reported as unavailable (`None` at `LftpManager.status()`), never `[]`, with the existing consecutive-error counter/threshold unchanged and no downstream consumer converting unavailable into "no jobs" (including protection of transfers submitted to lftp but not yet observed, plus the same-cycle command guard and Stop reconcile); (B3) remote and local size-stability are measured only on the clock of successful scans while the UI "last scan" keeps its meaning.
**Verified:** 2026-10-08
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP §Phase 117 Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A pget job with no data line, immediately followed by another job header (pget or mirror variant) → every job appears in the parsed status with its correct name and state; no header swallowed (XFER-01) | VERIFIED | `job_status_parser.py:277-297` pops the pget data line only `if lines and RegexPatterns.is_chunk_data(lines[0])` (code read). `tests/unittests/test_lftp/test_job_status_parser.py::test_jobs_pget_no_data_line_followed_by_pget_header` and `..._followed_by_mirror_header` independently re-run — PASSED. Whole `test_lftp` package re-run (137 tests incl. `test_queue_and_jobs_4`, `test_jobs_missing_pget_data_line`, `test_parse_header_consumes_sftp_line`) — all pass, confirming existing fixtures are unchanged. |
| 2 | An isolated parse failure during an active download → file stays active/protected, active-downloading list unchanged, nothing re-queued or deleted; status reported as unavailable (`None`), never `[]`; no downstream consumer converts it back to "no jobs" (XFER-02) | VERIFIED | `lftp.py:304-335` (`Lftp.status`) returns `None` on tolerated error/timeout, never `[]`. Every consumer trace confirmed by direct code read: `LftpManager.status` passes `None`/`[]` through (`lftp_manager.py:167-187`), `ModelPipeline.feed_model_builder` gates on `lftp_statuses is not None` (`model_pipeline.py:165`), `Controller._update_active_file_tracking` only replaces the active list when not None. Composed regressions `test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands` and `test_active_downloading_list_and_scanner_feed_unchanged_on_parse_failure` independently re-run — PASSED. |
| 2b | Transfers submitted to lftp but not yet observed by a successful status stay protected (no re-queue after cooldown, no false-DOWNLOADED from preallocated local size, no extract/delete); same-cycle QUEUE-then-destructive-command ordering is guarded; Stop reconciles the submitted set (codex findings, owner-scoped into XFER-02) | VERIFIED | `lftp_manager.py:94,127-212` — `__submitted_unobserved` set added in `queue()`, cleared only on a list-returning `status()`, discarded in `kill()` after `Lftp.kill` returns. `model_builder.py:91-101,228-243` derives `QUEUED` from the set only when no lftp status exists for the name (observed status always wins), and the set is not unioned into `all_file_names` so a submitted name with no other source is silently ignored (confirmed by reading `build_model` lines 134-147). `command_processor.py:91-241` — `_is_submitted_unobserved` guards `_handle_extract` and both `_handle_delete` branches with 409; `_handle_queue` skips re-submission for an already-submitted name. Composed tests `test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry`, `test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size`, `test_queue_then_extract_in_one_process_does_not_extract`, `test_queue_then_delete_local_in_one_process_does_not_delete`, `test_queue_then_delete_remote_in_one_process_does_not_delete`, `test_stop_then_user_queue_after_unavailable_status_resubmits_to_lftp` all independently re-run — PASSED. Test bodies read directly (not just trusted): real assertions on `ModelFile.State`, `queue_command.call_count`, `file_op_manager` mock calls — not placeholders. |
| 3 | Status-error boundary pinned exactly: failures 1..MAX_CONSECUTIVE_STATUS_ERRORS tolerated+unavailable, failure MAX+1 raises, success resets counter, genuinely empty status still clears active state (XFER-03) | VERIFIED | `lftp.py:12` `MAX_CONSECUTIVE_STATUS_ERRORS = 2` unchanged. `status()` body (lines 319-335) matches the pinned boundary exactly, including the added timeout branch (`__last_command_timed_out`, lines 55,118,123,144,320-322) which returns `None` without touching the counter. `test_boundary_sequence_pinned_exactly`, `test_timed_out_status_with_empty_buffer_is_unavailable`, `test_timed_out_status_with_partial_parseable_buffer_is_unavailable`, `test_tolerated_parse_failures_report_unavailable_not_empty` independently re-run — PASSED. 4 CI-only integration tests in `tests/integration/test_lftp/test_lftp_protocol.py` confirmed by direct grep to have exactly 10 `assertIsNone(self.lftp.status())` (tolerated-error flips) and 1 remaining `assertEqual([], ...)` (genuine-empty preservation) — matches the documented count; cannot execute without Docker sshd fixture (CI-only, correctly out of local scope). |
| 4 | Failed remote scans spanning the stability window → file not stable, not auto-queued; UI "last scan" timestamp keeps its meaning (XFER-04) | VERIFIED | `common/status.py:115-131` adds `latest_successful_remote_scan_time`/`latest_successful_local_scan_time` (default `None`), independent of the pre-existing `latest_remote_scan_time`/`latest_local_scan_time` UI fields. `controller.py:503-523` writes the UI fields from every scan and the success clock only `if not remote_scan.failed` / `if not local_scan.failed`. `auto_queue.py:272-302` reads `remote_stable_time`/`local_stable_time` from the success clocks for history/sweep, while the UI clock (`scan_time`) is used only by the unchanged cooldown block (line 331-336). `web/serialize/serialize_status.py` grep-confirmed to reference only the pre-existing fields — no `latest_successful_*` key leaked into the SSE payload (D-06 honored). `test_failed_remote_scans_spanning_window_do_not_establish_stability`, `test_changed_size_after_remote_outage_restarts_window`, `test_failed_remote_scans_spanning_window_do_not_queue`, `test_remote_recovery_with_changed_size_restarts_window`, `test_controller_status_keys_unchanged_by_success_clocks` independently re-run — PASSED. |
| 5 | Failed local scans spanning the local-stability window → local gate holds; with successful scans, remote and local gating behave exactly as before (XFER-05) | VERIFIED | Same code sites as #4 (local branch). `test_failed_local_scans_spanning_window_do_not_establish_local_idle`, `test_changed_local_size_after_outage_restarts_window`, `test_failed_local_scans_spanning_window_do_not_queue`, `test_local_recovery_with_changed_size_restarts_window`, plus preservation `test_matching_size_across_remote_outage_is_stable` / `test_matching_local_size_across_outage_is_idle` / `test_remote_recovery_with_matching_size_queues` / `test_local_recovery_with_matching_size_queues` independently re-run — PASSED. |

**Score:** 5/5 roadmap truths verified (5a sub-truth for the codex-driven submitted-unobserved/command-ordering scope also verified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/python/lftp/job_status_parser.py` | `is_chunk_data` predicate, `JOB_HEADER` guard, 3 peek-before-pop sites | VERIFIED | All three call sites confirmed by direct read (lines 293, 664, 676); no `TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER` present |
| `src/python/lftp/lftp.py` | `status() -> Optional[List[LftpJobStatus]]`, timeout flag, `kill()` None guard | VERIFIED | Confirmed by direct read (lines 55,118-144,304-335,366-375) |
| `src/python/common/status.py` | Two new non-serialized `ControllerStatus` properties | VERIFIED | Lines 121-131 |
| `src/python/controller/controller.py` | Success-clock writes guarded by `not .failed` | VERIFIED | Lines 503-523 |
| `src/python/controller/auto_queue.py` | Stability reads success clocks; cooldown stays on UI clock | VERIFIED | Lines 263-302 |
| `src/python/controller/lftp_manager.py` | `__submitted_unobserved` set; `submitted_unobserved_file_names()` | VERIFIED | Lines 94,127-212 |
| `src/python/controller/model_builder.py` | `set_submitted_files()`; QUEUED derivation | VERIFIED | Lines 91-101,228-243 |
| `src/python/controller/model_pipeline.py` | Per-cycle sync of submitted set | VERIFIED | Line 170 |
| `src/python/controller/command_processor.py` | `_is_submitted_unobserved` guard on extract/delete/queue | VERIFIED | Lines 91-241 |
| `tests/unittests/test_lftp/test_lftp_status_contract.py` | B2 boundary + timeout + kill-on-None | VERIFIED | 291 lines (min 120); exists, substantive, all tests pass |
| `tests/unittests/test_controller/test_transfer_state_safety.py` | Composed B2 downstream + submitted-unobserved + command-ordering | VERIFIED | 556 lines (min 320); test bodies read directly — real assertions, not stubs |
| `tests/unittests/test_controller/test_scan_clock_safety.py` | Composed B3 | VERIFIED | 279 lines (min 100) |
| `.planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md` | RED + GREEN fail-before/pass-after evidence | VERIFIED | RED SHA's production tree confirmed byte-identical to `7da18e0` (re-ran `git diff --stat`); GREEN production diff re-ran independently: 9 files, 220 insertions/40 deletions — matches exactly |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `PgetJobParser.parse_header` | `RegexPatterns.is_chunk_data` | guarded pop of data line | WIRED | `job_status_parser.py:293` |
| `ActiveJobsParser._handle_auxiliary_lines` CHUNK_HEADER | `is_chunk_data` | guarded pop; raise removed | WIRED | Line 676 |
| `ActiveJobsParser._handle_auxiliary_lines` MIRROR_EMPTY | `RegexPatterns.JOB_HEADER` | header guard ANDed with follower checks | WIRED | Line 664 |
| `Lftp.status` tolerated-error branch | `return None` | — | WIRED | Line 332 |
| `Lftp.__run_command` TIMEOUT branches | `Lftp.status` early `None` | `__last_command_timed_out` flag | WIRED | Lines 118-144, 320-322 |
| `Lftp.kill` | `LftpJobStatusParserError` | raise when `status()` is `None` | WIRED | Line 374-375 |
| `Controller._update_controller_status` | `status.controller.latest_successful_*_scan_time` | `if not scan.failed` | WIRED | Lines 507-508, 521-522 |
| `AutoQueue.process` | success clocks | `remote_stable_time`/`local_stable_time` feed history + sweep_accept | WIRED | Lines 272-302 |
| `LftpManager.queue` | `__submitted_unobserved.add` | after `Lftp.queue` returns | WIRED | Line 144 |
| `LftpManager.status` | `__submitted_unobserved.clear` | only on list-returning path | WIRED | Line 183 |
| `LftpManager.kill` | `__submitted_unobserved.discard` | after `Lftp.kill` returns | WIRED | Line 165 |
| `ModelPipeline.feed_model_builder` | `ModelBuilder.set_submitted_files` | every cycle, after `lftp_statuses` None guard | WIRED | Line 170 |
| `ModelBuilder._set_initial_state` | `ModelFile.State.QUEUED` | `elif name in __submitted_files` | WIRED | Line 242-243 |
| `CommandProcessor._handle_extract`/`_handle_delete`/`_handle_queue` | `LftpManager.submitted_unobserved_file_names()` | `_is_submitted_unobserved(file)` | WIRED | Lines 139,180,207,234 |
| `web/serialize/serialize_status.py` | controller status fields | unchanged key set | CONFIRMED UNCHANGED | grep shows only pre-existing `latest_local_scan_time`/`latest_remote_scan_time`/`latest_remote_scan_failed`/`latest_remote_scan_error`; no `latest_successful_*` leaked |

### Behavioral Spot-Checks (independently executed, not trusted from EVIDENCE.md)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Phase quick-run (10-file set) is fully green on current code | `poetry run pytest tests/unittests/test_lftp tests/unittests/test_controller/test_auto_queue.py test_lftp_manager.py test_controller_unit.py test_controller.py test_model_builder.py test_transfer_state_safety.py test_scan_clock_safety.py tests/unittests/test_common/test_status.py tests/unittests/test_web/test_serialize/test_serialize_status.py -q` | `524 passed, 1 warning in 1.12s` | PASS |
| Whole-tree lint is clean | `poetry run ruff check /Users/julianamacbook/seedsyncarr/src/python/` | `All checks passed!` | PASS |
| Full host suite (part 1, excluding 4 documented baseline files) shows no new failures | `poetry run pytest tests/unittests -q --ignore=test_ssh/test_sshcp.py --ignore=.../test_scanner_process.py --ignore=test_system/test_scanner.py --ignore=.../test_extract_process.py` | `1471 passed, 2 warnings in 41.36s`, 0 failed | PASS |
| The 4 pre-existing baseline-failure files fail identically to the documented Phase 116 baseline | ran each of the 4 files individually | `11 failed` (sshcp) + `3 failed/1 passed/3 errors` (scanner_process) + `1 failed/19 passed` (test_scanner) + `6 failed` (extract_process) = **21 failed / 3 errors total** | PASS — matches documented baseline exactly, no regression |
| Integration counter-test flips are present in the file (cannot execute: needs Docker sshd) | `grep -n "assertIsNone(self.lftp.status())\|assertEqual(\[\], self.lftp.status())" tests/integration/test_lftp/test_lftp_protocol.py` | 10 `assertIsNone` + 1 `assertEqual([], ...)` | PASS (static confirmation; execution is CI-only, correctly out of scope here) |
| Production diff matches claimed scope exactly | `git diff --stat 7da18e0 349363d -- src/python/lftp src/python/common src/python/controller ':!src/python/tests'` | 9 files, 220 insertions(+), 40 deletions(-) | PASS |
| All cited commits exist in history | `git cat-file -e` on 14 cited commit SHAs | all FOUND | PASS |
| Git working tree is clean | `git status --short` | clean | PASS |

### Probe Execution

No probe scripts (`scripts/*/tests/probe-*.sh`) declared or referenced by this phase's PLAN/SUMMARY/VALIDATION files. Skipped — not applicable (this phase uses pytest regression tests as its verification mechanism, not shell probes).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| XFER-01 | 117-01 (RED), 117-04 (fix) | Parser never swallows another job's header; other next-line-consuming sites audited | SATISFIED | `job_status_parser.py` peek-before-pop at 3 confirmed sites; 5 regressions pass; whole `test_lftp` package unchanged |
| XFER-02 | 117-01 (RED), 117-05 + 117-08 (fix) | Unavailable status never becomes `[]`; active files protected; no downstream "no jobs" collapse; submitted-but-unobserved transfers and same-cycle command ordering protected | SATISFIED | `lftp.py`, `lftp_manager.py`, `model_builder.py`, `model_pipeline.py`, `command_processor.py` all confirmed; 15+ composed regressions independently re-run, pass |
| XFER-03 | 117-01 (RED), 117-05 (fix) | Boundary pinned exactly; timeout semantics; genuine-empty still clears | SATISFIED | `lftp.py:304-335`; boundary + timeout tests pass; 10 CI-only integration assertions confirmed flipped |
| XFER-04 | 117-02 (RED), 117-06 (fix) | Remote stability on successful-scan clock only; UI meaning kept | SATISFIED | `status.py`, `controller.py`, `auto_queue.py` confirmed; serializer unchanged; tests pass |
| XFER-05 | 117-02 (RED), 117-06 (fix) | Local stability gate same | SATISFIED | Same evidence, local branch; tests pass |

**Documentation gap (non-blocking, informational):** `.planning/REQUIREMENTS.md` still shows XFER-01 through XFER-05 as unchecked (`- [ ]`) and "Pending" in the requirements-coverage table (lines 16-20, 49-53), even though ROADMAP.md marks Phase 117 complete (2026-10-09) and the code/test evidence above confirms all five are satisfied. Phase 116's IMPORT-01/IMPORT-02 were marked `[x]` / "Complete" at the same point in its lifecycle (see `116-VERIFICATION.md` precedent), so this looks like a bookkeeping step that was simply missed for Phase 117, not a functional gap. Recommend updating REQUIREMENTS.md to `[x]` / "Complete" for XFER-01..05 to match the Phase 116 precedent. This does not block the phase goal and is not counted as a gap.

No orphaned requirements: REQUIREMENTS.md maps exactly XFER-01..05 to Phase 117; all five are declared across plan frontmatters (117-01/02/03/04/05/06/07/08) and satisfied above.

### Anti-Patterns Found

None. Scanned all 9 modified production files (`job_status_parser.py`, `lftp.py`, `status.py`, `controller.py`, `auto_queue.py`, `lftp_manager.py`, `model_builder.py`, `model_pipeline.py`, `command_processor.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — zero matches.

### Regression Check (Phase 116)

Phase 117's production diff (`git diff --stat 7da18e0 349363d`) touches only `lftp/`, `common/status.py`, and 6 `controller/*.py` files — none of which overlap with Phase 116's touched files (`controller/controller.py` Window 1 build / `webhook_manager.py` / `auto_delete_manager.py` import-ambiguity logic). `controller.py` is shared, but the diff is additive and scoped to `_update_controller_status` (success clocks only) — the Phase 116 webhook-import `name_to_paths` logic is untouched. No regression risk identified; confirmed no new failures in the full host suite run above.

### Known Context Honored

- **Codex adversarial pass-4 finding** (LFTP command-stream resync after timeout) — confirmed recorded as `ROADMAP.md` §"Phase 999.2: LFTP command-stream resync after timeout" (BACKLOG), owner-accepted 2026-10-08, with a placeholder directory `.planning/phases/999.2-lftp-command-stream-resync-after-timeout/`. Correctly out of scope for this phase.
- **Three parser sites #1, #6, #8 deferred per D-09** — confirmed recorded in `deferred-items.md`-adjacent location (117-04-SUMMARY.md "Deferred parser sites (D-09)" and 117-REL01-EVIDENCE.md "Deferred parser sites (D-09)"), matching the research audit exactly.
- **Four integration counter tests (10 assertions) CI-only** — confirmed via static grep of the test file; cannot execute locally (no Docker sshd/lftp binary), correctly deferred to CI.
- **Four macOS spawn-context test failures pre-existing at Phase 116 baseline** — independently re-ran all four baseline files; counts (21 failed / 3 errors total) match the documented Phase 116 baseline exactly, confirming no regression.

### Human Verification Required

None. This phase is Python-only backend logic (D-01: explicitly no frontend/UI/e2e changes — active downloads keep last-known state frozen with no new UI indicator). All 5 success criteria and the codex-driven sub-scope are deterministically testable and were independently re-verified via automated tests executed during this verification pass, not merely trusted from SUMMARY.md or EVIDENCE.md claims.

### Gaps Summary

No gaps. All 5 ROADMAP success criteria (XFER-01 through XFER-05) and the codex-driven protective scope folded into XFER-02 (submitted-but-unobserved transfers, same-cycle command guard, Stop-path reconciliation, timeout-as-unavailable) are VERIFIED against the actual codebase — not merely claimed in SUMMARY.md. Every production code site named in the plans was read directly and matches the committed fix exactly. Every regression test cited as passing was independently re-executed in this verification session (524 passed quick-run; 1471 passed full-suite part 1; ruff clean; baseline-file failure counts unchanged at 21 failed/3 errors). The only finding is a non-blocking documentation bookkeeping gap: REQUIREMENTS.md was not updated to check off XFER-01..05, unlike the Phase 116 precedent. This is recommended for cleanup but does not affect phase-goal achievement and is not treated as a gap for routing purposes.

---

_Verified: 2026-10-08_
_Verifier: Claude (bm-verifier)_
