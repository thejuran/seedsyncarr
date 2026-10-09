---
phase: 117-transfer-state-safety
plan: 05
subsystem: lftp
tags: [python, lftp, status-contract, none-vs-empty, b2]
requires: ["117-03"]
provides:
  - "Lftp.status() -> Optional[List[LftpJobStatus]]: None = unavailable (tolerated parse error or timed-out jobs -v), [] = genuinely no jobs"
  - "Lftp.kill() raises LftpJobStatusParserError on unavailable status"
affects:
  - src/python/lftp/lftp.py
  - controller.CommandProcessor._handle_stop (behaviour via existing handler)
tech-stack:
  added: []
  patterns: ["per-command timeout flag consulted only by status()", "None-vs-empty status contract"]
key-files:
  created: []
  modified:
    - src/python/lftp/lftp.py
    - src/python/tests/unittests/test_lftp/test_lftp_status_contract.py
    - src/python/tests/integration/test_lftp/test_lftp_protocol.py
    - src/python/tests/unittests/test_controller/test_lftp_manager.py
decisions:
  - "A timed-out jobs -v returns None without parsing and neither increments nor resets the parse-error counter; stalls stay LftpManager's stall-backoff concern"
  - "Lftp.kill raises on unavailable status (fixed message, no job name); Stop during a transient status failure now returns the generic Lftp error (owner-accepted)"
metrics:
  duration: "~20m"
  completed: 2026-10-08
  tasks: 2
  files: 4
requirements: [XFER-02, XFER-03]
---

# Phase 117 Plan 05: Lftp status None-vs-empty (B2) Summary

`Lftp.status()` now reports a tolerated parse failure or a timed-out `jobs -v` as unavailable (`None`) instead of an empty job list, with `MAX_CONSECUTIVE_STATUS_ERRORS = 2` and the escalation boundary unchanged; `Lftp.kill()` refuses to act on an unavailable status.

## What changed

- `lftp.py`
  - `__init__`: new `__last_command_timed_out = False`.
  - `__run_command`: resets the flag before `sendline`, sets it in both `pexpect.exceptions.TIMEOUT` branches. Warning text, buffer decode, error detection and the `str` return are untouched, so every other command behaves as before.
  - `status()`: signature `-> Optional[List[LftpJobStatus]]`; returns `None` immediately (fixed warning "Lftp status command timed out; status unavailable") when the command timed out; tolerated parse error branch returns `None` (warning now ends "status unavailable", contains only the counter); `else: raise` and `<=` comparison kept.
  - `kill()`: `statuses = self.status()`; `None` raises `LftpJobStatusParserError("Lftp status unavailable; cannot locate job to kill")` before any `kill`/`queue --delete` is sent.
- Contract tests: `TestLftpStatusTimeoutSemantics` (2) and `TestLftpKillWhenStatusUnavailable` (3) appended.
- Integration (`test_lftp_protocol.py`): 10 tolerated-error assertions flipped to `assertIsNone`; the genuine-empty success line (`# SUCCESS -> count reset to 0`) stays `assertEqual([], ...)`; docstrings reworded from "swallowed (return [])" to "reported unavailable (None)".
- `test_lftp_manager.py`: `test_status_passes_none_through_unchanged`, `test_status_passes_empty_list_through_unchanged`.

## Product-visible effect (accepted)

Pressing Stop while lftp status is transiently unavailable (tolerated parse error or `jobs -v` timeout) now makes `Lftp.kill` raise `LftpJobStatusParserError`, which `CommandProcessor._handle_stop` already maps to the generic "Lftp error" 500 response; nothing is added to the stopped set. Previously the empty list made kill return "not found", and the Stop could report success while lftp kept downloading. The owner accepted this change; the user can retry Stop once status recovers.

## Timeout semantics

A `jobs -v` whose pexpect expect timed out is an incomplete observation: `status()` returns `None` without parsing the buffer (empty or partially parseable), and the consecutive parse-error counter is neither incremented nor reset. The counter exists to escalate a parser that cannot read lftp output; a stall is a transport condition that `LftpManager.STATUS_STALL_THRESHOLD_SECS` / `STATUS_BACKOFF_SECS` already throttle, and counting it would change the locked parser-error threshold. Pinned by `test_timeout_does_not_count_toward_or_reset_parser_error_counter`. `__run_command` timeout behaviour for every other command (setters, queue, kill, kill_all) is unchanged; only `status()` reads the flag. Paths that patch `_Lftp__run_command` never set the flag and parse normally.

## CI-only note

The four counter tests in `tests/integration/test_lftp/test_lftp_protocol.py` need the Docker sshd fixture and were not run on the host. Verified here only that the file compiles, that exactly one `assertEqual([], self.lftp.status())` remains (line 827, the success line) and that 10 `assertIsNone(self.lftp.status())` exist. Their pass/fail is confirmed in CI.

## Verification (observed)

- `tests/unittests/test_lftp/test_lftp_status_contract.py`: 11 passed (6 Plan 01 + 2 timeout semantics + 3 kill).
- `tests/unittests/test_controller/test_transfer_state_safety.py`: 6 passed, 7 failed. The failing tests are exactly the Plan-08-owned ones: `test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry`, `test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size`, `test_timed_out_status_with_empty_buffer_keeps_protection`, `test_timed_out_status_with_partial_parseable_buffer_keeps_protection`, `test_queue_then_extract_in_one_process_does_not_extract`, `test_queue_then_delete_local_in_one_process_does_not_delete`, `test_queue_then_delete_remote_in_one_process_does_not_delete`. Both composed timeout tests now fail on the `File.Two.rar` QUEUED assertion (observed `DOWNLOADED`/`DEFAULT` for File.Two), not on File.One, so the timeout path maps to None.
- `tests/unittests/test_lftp`: 137 passed, 5 failed. The 5 failures are the B1 parser goldens in `test_job_status_parser.py` (Plan 04 scope, not merged into this worktree).
- `tests/unittests/test_controller/test_lftp_manager.py`: 19 passed.
- Whole-tree `ruff check` from `src/python`: All checks passed.
- All grep acceptance criteria checked: `MAX_CONSECUTIVE_STATUS_ERRORS = 2` x1, `statuses = []` x0, `statuses is None` x1, `for status in self.status()` x0, flag `= True` x2, `= False` x2, `if self.__last_command_timed_out` x1. No removed lines touch the TIMEOUT handling, its log or `return out`.
- Full `tests/unittests` run: 1444 passed, 41 failed, 3 errors. Besides the 12 above: XFER-04/05 scan-clock REDs in `test_auto_queue.py` (4) and `test_scan_clock_safety.py` (4), owned by Plan 06; host-environment failures in `test_sshcp.py` (11, need sshd), `test_extract_process.py` (6), `test_scanner_process.py` (3 failed + 3 errors), `test_system/test_scanner.py::test_scan_file_with_latin_chars` (1). None of these touch `Lftp.status`/`kill`, and none are in this plan's files.

## Deviations from Plan

**1. [Commit split] Two commits instead of one combined commit.** The plan put all four files in one commit (`git diff --stat HEAD~1 HEAD` lists four files). The orchestrator asked for one commit per task, so Task 1 (`lftp.py` + contract tests) is `d313ff3` with the plan's subject `fix(117-05): report tolerated lftp status errors as unavailable (None), never empty (B2)`, and Task 2 (integration + manager tests) is `e8907d8` `test(117-05): ...`. `git diff --stat HEAD~2 HEAD` lists exactly the four planned files.

**2. [Count clarification] 10 integration flips, not eight.** The action text said "exactly eight" but its own acceptance criterion and candidate line list give 10 (2+2+2+4). All 10 tolerated-error lines were flipped, matching the acceptance criterion.

## Threat Flags

None. No new surface: the timeout warning and kill exception are fixed strings with no lftp output or job name (CWE-117 pinned by `test_timed_out_status_logs_no_raw_output` and `test_kill_error_message_does_not_echo_job_name`).

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/python/lftp/lftp.py, test_lftp_status_contract.py, test_lftp_protocol.py, test_lftp_manager.py
- FOUND: d313ff3, e8907d8
