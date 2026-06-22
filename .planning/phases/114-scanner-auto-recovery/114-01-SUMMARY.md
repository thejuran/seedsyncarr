---
phase: 114-scanner-auto-recovery
plan: 01
subsystem: controller/scan + ssh
requirements-completed: [SCAN-01, SCAN-02, SCAN-03]  # recovery half (in-scan bounded name-resolution retry); RECOV-01 is plan 114-02. Back-filled at v1.4.1 audit 2026-06-22 — code shipped 2026-06-21 (f497cd2, cfe5e37).
tags: [scanner, ssh, dns, retry, backoff, resilience, tdd]
requires:
  - "ssh.SshcpError + TRANSIENT/PERMANENT_ERROR_PATTERNS (existing classification)"
  - "ScannerError(recoverable=...) flag (scanner_process.py)"
  - "Localization.Error.REMOTE_SERVER_SCAN / REMOTE_SERVER_INSTALL"
provides:
  - "ssh.NAME_RESOLUTION_ERROR_PATTERNS tuple (collapsed + raw resolver surfaces, lower-case)"
  - "RemoteScanner._is_name_resolution_ssh_error (case-insensitive matcher)"
  - "RemoteScanner.__ssh_call_with_name_resolution_retry (ONE shared bounded retry helper)"
  - "RemoteScanner.__to_scanner_error (factored __first_run-aware classification)"
  - "In-scan bounded name-resolution recovery on BOTH the main scan and install (md5sum/copy) paths"
affects:
  - "RemoteScanner.scan() main SSH call"
  - "RemoteScanner._install_scanfs() md5sum + copy SSH ops"
tech-stack:
  added: []
  patterns:
    - "Bounded jittered exponential backoff retry (stdlib time + random), name-resolution-only gate"
    - "Shared zero-arg-callable retry helper wrapping multiple SSH op sites"
    - "Dedicated classification tuple (lowest blast radius) rather than moving a pattern between tuples"
key-files:
  created: []
  modified:
    - "src/python/ssh/sshcp.py"
    - "src/python/ssh/__init__.py"
    - "src/python/controller/scan/remote_scanner.py"
    - "src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py"
decisions:
  - "Retry gate is name-resolution ONLY (timeout/refused keep immediate-raise + next-interval recovery — can each block up to the 180s Sshcp timeout)"
  - "Matcher covers ALL resolver-string surfaces (collapsed 'Bad hostname:' AND raw fallthrough 'Could not resolve hostname'/'Name or service not known'/'Temporary failure in name resolution'), case-insensitive"
  - "'Bad hostname:' stays in PERMANENT_ERROR_PATTERNS; the new tuple is the only place name-resolution is treated retryable"
  - "ONE shared helper wraps the main scan call AND the install md5sum/copy ops (df untouched)"
  - "Backoff: 3 attempts, 1s->2s exp with +/-20% jitter, 4s ceiling; bare time.sleep with documented shutdown tradeoff (Phase 114 D-02 option a)"
metrics:
  duration: ~45m
  completed: 2026-06-21
  tasks: 2
  files: 4
  commits: 2
---

# Phase 114 Plan 01: Scanner Name-Resolution In-Scan Retry Summary

Transient DNS (name-resolution) failures during a seedbox scan or its startup/post-restart install are now retried in-scan with bounded jittered backoff via ONE shared helper that wraps both the main scan SSH call and the install md5sum/copy ops, so a momentary resolver blip no longer kills the scanner and freezes the file list — while genuinely-wrong hostnames still surface fatal byte-for-byte as today.

## What Was Built

Implemented SCAN-01/02/03 (the recovery half of Phase 114). RECOV-01 (controller auto-restart) is a separate plan (114-02) and was intentionally out of scope here.

- **SCAN-01 — reclassify name-resolution as in-scan-retryable.** Added `NAME_RESOLUTION_ERROR_PATTERNS` to `ssh/sshcp.py` covering every resolver-string surface the SSH layer can present: the collapsed `bad hostname:` (pexpect indices 3/5) AND the raw non-zero-exit fallthrough substrings `could not resolve hostname` / `name or service not known` / `temporary failure in name resolution` (sshcp.py:155 raises raw `sp.before` un-collapsed). Stored lower-case and matched case-insensitively via a new `RemoteScanner._is_name_resolution_ssh_error` static matcher. Re-exported the tuple from `ssh/__init__.py`. `Bad hostname:` deliberately remains in `PERMANENT_ERROR_PATTERNS` (lowest blast radius) — the retry layer is the only place name-resolution is treated retryable.

- **SCAN-02 — bounded retry, shared by both paths.** Added ONE private helper `RemoteScanner.__ssh_call_with_name_resolution_retry(ssh_call, op_label)` that retries ONLY name-resolution failures (the sole gate is `_is_name_resolution_ssh_error`), bounded by `__SCAN_MAX_ATTEMPTS = 3` with jittered exponential backoff (`__SCAN_BACKOFF_BASE_SECS = 1.0`, ceiling `4.0`, jitter `0.2`) via `__sleep_backoff`. The helper wraps the main scan `shell()` call, the install md5sum `shell()` op, and the install `copy()` op (df capacity is left untouched). It never builds a `ScannerError` — it re-raises the original `SshcpError` so each caller converts it on its own path.

- **SCAN-03 — exhaustion surface preserved byte-for-byte.** On name-resolution exhaustion the main-scan path raises `ScannerError(REMOTE_SERVER_SCAN, recoverable=False)` and the install path surfaces via its UNCHANGED except as `ScannerError(REMOTE_SERVER_INSTALL, recoverable=False)`. Factored the existing main-scan classification into `__to_scanner_error(e)` so the `__first_run`-aware recoverable value (including transient-after-first-run `recoverable=True`) is preserved for the immediate-raise branch. Transient timeout/refused are NOT retried in-scan on either path — they keep their existing immediate-raise + next-interval recovery.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | RED: name-resolution matcher + tuple + failing retry/install tests (all resolver surfaces) | cfe5e37 | sshcp.py, ssh/__init__.py, remote_scanner.py, test_remote_scanner.py |
| 2 | GREEN: ONE shared bounded name-resolution retry helper wrapping scan + install ops | f497cd2 | remote_scanner.py |

## TDD Gate Compliance

Plan `type: tdd`. Gate sequence verified in git log:
- RED gate: `test(114-01): ...` (cfe5e37) — classification tests pass, retry/install tests fail (pinning the not-yet-built helper). Confirmed the targeted retry selector exited non-zero before Task 2.
- GREEN gate: `feat(114-01): ...` (f497cd2) — implements the shared helper; all 60 test_remote_scanner.py tests green.
- REFACTOR: none required.

## Verification Results

- `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k name_resolution -x` → 22 passed, exit 0.
- `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -x` → 60 passed, exit 0 (34 pre-existing + 26 new; all existing first-run timeout/refused, install md5sum/copy timeout, wrong-password, host-key-change, SystemScannerError, and exact call-count regressions stay green unchanged).
- `ruff check src/python/` (whole-tree, run from repo/worktree root) → All checks passed, exit 0.
- TDD gate-order assertion: `test(...)` commit precedes `feat(...)` commit.

## Deviations from Plan

### Auto-fixed Issues

None affecting behavior. One minor in-helper stylistic alignment to satisfy a literal acceptance grep:

**1. [Rule 3 - Blocking acceptance check] Introduced an explicit `retryable` local in the retry helper**
- **Found during:** Task 2
- **Issue:** The shared helper initially inlined the gate as `if not self._is_name_resolution_ssh_error(e): raise`, which is functionally identical but did not satisfy the plan's acceptance grep `grep -n "retryable"`.
- **Fix:** Assigned `retryable = self._is_name_resolution_ssh_error(e)` then branched on `if not retryable`. No behavior change; the gate remains name-resolution ONLY (`_is_transient_ssh_error` appears in `retryable` 0 times, per the acceptance grep).
- **Files modified:** src/python/controller/scan/remote_scanner.py
- **Commit:** f497cd2

## Out-of-Scope / Environmental Notes (not fixed — logged)

These are pre-existing failures in the LOCAL macOS worktree environment, proven to fail identically on the unmodified phase base commit (bdd098d), and are NOT caused by this plan's changes. They pass in the project's docker/CI test harness (`make run-tests-python`):

- `tests/unittests/test_ssh/test_sshcp.py` — 11 failures: these are SSH integration tests requiring a Unix `testgroup` group (`grp.getgrnam('testgroup')` → KeyError) and a live SSH server. This plan made NO raise-site changes in `sshcp.py` (only added the `NAME_RESOLUTION_ERROR_PATTERNS` classification tuple + comments — verified by `git diff` showing no `raise SshcpError` edits), so the SSH contract these tests assert is unaffected.
- `tests/unittests/test_controller/test_scan/test_scanner_process.py` — 3 failures + 3 teardown errors: real-multiprocessing tests where `self._popen` is `None` (the spawn-based subprocess does not start under this local macOS env; `AttributeError: 'NoneType' object has no attribute 'terminate'`). Verified to fail identically (3 failed, 3 errors) when this plan's changes are reverted to the phase base. Unrelated to `remote_scanner.py`.
- `tests/unittests/test_controller/test_extract/test_extract_process.py` — hangs locally (spawns real processes); not run to completion. Outside this plan's scope.

The plan's own verification scope (test_remote_scanner.py + whole-tree ruff) is fully green; the full Python suite + test_sshcp.py green is asserted via the per-wave merge gate `make run-tests-python` in the docker environment.

## Threat Surface

No new security-relevant surface beyond the plan's `<threat_model>`. The shared helper wraps the SAME already-`shlex.quote`'d `shell(...)` calls and the `copy(local_path=, remote_path=)` kwargs via lambdas closing over the existing quoted strings (no command rebuild — T-114-03). The attempt-counter log line uses lazy `%`-style logging and logs only the op label + counters + the app/SSH error string; the password is never logged (T-114-02). The retry gate is strictly name-resolution and disjoint from auth/host-key/timeout/refused (T-114-01); attempts are bounded with short backoff and slow error classes are excluded (T-114-04).

## Self-Check: PASSED

- FOUND: src/python/ssh/sshcp.py (NAME_RESOLUTION_ERROR_PATTERNS)
- FOUND: src/python/ssh/__init__.py (re-export)
- FOUND: src/python/controller/scan/remote_scanner.py (_is_name_resolution_ssh_error, __ssh_call_with_name_resolution_retry, __to_scanner_error, __SCAN_MAX_ATTEMPTS)
- FOUND: src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py (114-01 test classes)
- FOUND commit: cfe5e37 (test RED gate)
- FOUND commit: f497cd2 (feat GREEN gate)
