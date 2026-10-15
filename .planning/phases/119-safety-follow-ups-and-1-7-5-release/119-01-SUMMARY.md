---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 01
subsystem: lftp
tags: [lftp, pexpect, resync, xfer-06, regression-red-first]
requires: []
provides:
  - "Lftp.__synced state + nonce sentinel resync (SEEDSYNCARR-SYNC-<nonce>-END)"
  - "status() None / queue() LftpError while the command stream is unsynchronized"
affects: [controller/lftp_manager, controller/command_processor]
tech-stack:
  added: []
  patterns: ["fake pty byte-buffer stream driving the real Lftp.__run_command"]
key-files:
  created:
    - src/python/tests/unittests/test_lftp/test_lftp_resync.py
  modified:
    - src/python/lftp/lftp.py
decisions:
  - "Unsynchronized status is detected in status() via the LftpError message 'not synchronized' (per plan), returning None without touching the consecutive-error counter"
  - "Resync timeout is 15 s (RESYNC_TIMEOUT_SECS), independent of the 180 s command timeout"
requirements: [XFER-06]
metrics:
  duration: ~10m
  completed: 2026-10-14
  tasks: 2
  files: 2
---

# Phase 119 Plan 01: LFTP command-stream resync after timeout (XFER-06) Summary

After any pexpect timeout, Lftp now treats its pty stream as unsynchronized and refuses to trust any command output until a quote-split nonce sentinel (`echo SEEDSYNCARR-SYNC-"<nonce>"-END`) round-trips; until then `status()` returns None and `queue()` raises, so a delayed stale prompt can never become a trusted empty job list.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | RED: fake pty stream regression | e645508 | src/python/tests/unittests/test_lftp/test_lftp_resync.py |
| 2 | GREEN: synced flag + nonce sentinel resync | f462733 | src/python/lftp/lftp.py |

## RED evidence (commit e645508, against pre-fix lftp.py)

```
FAILED tests/unittests/test_lftp/test_lftp_resync.py::TestLftpResync::test_resync_marker_ignores_tty_echo
FAILED tests/unittests/test_lftp/test_lftp_resync.py::TestLftpResync::test_resync_uses_fresh_nonce_each_attempt
FAILED tests/unittests/test_lftp/test_lftp_resync.py::TestLftpResync::test_stale_prompt_after_timeout_never_yields_empty_status
FAILED tests/unittests/test_lftp/test_lftp_resync.py::TestLftpResync::test_unsynced_resync_failure_keeps_status_unavailable_and_queue_raises
4 failed, 3 warnings in 0.04s
```

Failure reasons were all AssertionErrors (no harness errors):
- stale-prompt test: `AssertionError: [] == [] : a stale prompt from a timed-out command became a trusted empty job list`
- unsynced contract: `AssertionError: LftpError not raised`
- tty-echo test: `AssertionError: [<one job>] is not None` (pre-fix parsed output with no sentinel)
- fresh-nonce test: `AssertionError: [] is not None`

## GREEN evidence (commit f462733)

```
tests/unittests/test_lftp/test_lftp_resync.py: 4 passed, 3 warnings in 0.02s
tests/unittests/test_lftp + test_controller/test_lftp_manager.py + test_controller/test_transfer_state_safety.py:
187 passed, 3 warnings in 0.36s
ruff check src/python/: All checks passed!
```

Acceptance greps: `__synced = False` (non-comment) = 2; `not synchronized` = 3; `SEEDSYNCARR-SYNC-` present in code.

## Deviations from Plan

None - plan executed exactly as written.

Note: the worktree was spawned at f6ff78a (older than the expected base 33823af); it was reset to 33823af per the worktree branch check before any work.

## Verification scope

Verified with the fake pty stream only. The live-lftp behaviour (echo quote removal) is taken from RESEARCH (verified on lftp 4.9.2); it was not re-run against a real lftp in this plan. Docker-backed integration tests were not run.

## Self-Check: PASSED

- FOUND: src/python/tests/unittests/test_lftp/test_lftp_resync.py
- FOUND: src/python/lftp/lftp.py (modified)
- FOUND: e645508, f462733
