---
phase: 101-webhook-and-log-injection-security-cluster
plan: "06"
subsystem: lftp/security
tags: [cwe-117, log-injection, sanitize, tdd, lftp, remote-scanner]
dependency_graph:
  requires: [101-01]
  provides: [lftp-kill-log-sanitized, lftp-run-command-log-sanitized, job-status-parser-log-sanitized, remote-scanner-log-sanitized]
  affects: [SEC-01]
tech_stack:
  added: []
  patterns: [sanitize_log_value, cwe-117-escaping, nameerror-safe-except]
key_files:
  created:
    - src/python/tests/unittests/test_lftp/test_lftp_log_sanitization.py
  modified:
    - src/python/lftp/lftp.py
    - src/python/lftp/job_status_parser.py
    - src/python/controller/scan/remote_scanner.py
    - src/python/tests/unittests/test_lftp/test_job_status_parser.py
    - src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py
decisions:
  - "D-02 applied: sanitize_log_value applied only to provably remote-/user-tainted log sites (kill job name, raw lftp output, raw jobs -v block, raw SSH scan output) — not a blanket wrap"
  - "D-03 re-derived: lftp cluster and remote_scanner:118 both brought into scope — confirmed taint-reachable via fresh data-flow pass"
  - "Accepted tradeoff: job_status_parser.py:725 and remote_scanner.py:118 escape the full multi-line block (including legitimate internal newlines) — this is correct CWE-117 behavior, documented in code comments"
  - "NameError-safety: remote_scanner.py:118 uses locally-derived safe_out (not out_str which may be undefined when decode raised) — enforced by verification gate and bytes-only test"
  - "Excluded sites kept unsanitized with per-site rationale: lftp.py:114 (bytes repr already escapes CR/LF), 119/139 (hardcoded constants), 309 (integer count)"
metrics:
  duration: "~40m"
  completed: "2026-05-31T22:40:00Z"
  tasks_completed: 3
  files_modified: 5
---

# Phase 101 Plan 06: lftp + remote_scanner Log-Injection Sanitization (SEC-01) Summary

**One-liner:** CWE-117 log-injection hardening across 10 lftp log sites (kill job-name at 356/362/365, raw pexpect output at 126/129/144/147/148, parse-error at 724/725) and 1 remote-scanner site (118 — both str(err) and raw SSH output via NameError-safe safe_out), all routed through `sanitize_log_value` from Plan 01.

## What Was Built

Closed all remaining SEC-01 log-injection sinks in the lftp subsystem and the remote-scanner raw-output site.

### lftp/lftp.py (8 call sites)

Extended import to `from common import AppError, sanitize_log_value`. Applied `sanitize_log_value` at:

- `kill()` lines 356/362/365: wrapped `name` with `sanitize_log_value(name)` in all three job-name log lines. The raw name is still used for `status.name == name` matching and the kill/queue-delete dispatch receives the raw `job_to_kill.id`.
- `__run_command()` lines 126/144: `sanitize_log_value(out)` for the raw pexpect output bytes.
- `__run_command()` lines 129/147: `sanitize_log_value(after)` for the raw after buffer.
- `__run_command()` line 148: `sanitize_log_value(error_out)` for the error log.

Excluded with per-site rationale (not sanitized):
- Line 114 (`command.encode('utf8','surrogateescape')` — bytes repr already escapes CR/LF/control bytes to `\r`/`\n`/`\xHH`; sanitizing would double-escape)
- Lines 119/139 (`"Lftp timeout exception"` — hardcoded constant, no interpolation)
- Line 309 (integer counter — not taint-reachable)

The excluded-site gate in verification confirms line 114 is NOT sanitized.

### lftp/job_status_parser.py (2 call sites)

Extended import to `from common import AppError, sanitize_log_value`. In the `parse()` except branch:

- Line 724: `sanitize_log_value(str(e))` — ValueError messages interpolate raw remote line/name content (raised at lines 432/514/552/579/593).
- Line 725: `sanitize_log_value(output)` — full raw `jobs -v` output block.

Code comment documents the accepted CWE-117 tradeoff: escaping the full multi-line block escapes legitimate internal newlines too — this is intentional, not a bug.

### controller/scan/remote_scanner.py (2 interpolated values at line 118)

Extended import to `from common import overrides, Localization, sanitize_log_value`. In the except branch at line 117:

- Derives `safe_out` locally: `out.decode('utf-8', errors='replace') if isinstance(out, bytes) else str(out)` — avoids referencing `out_str` which is defined at line 114 inside the try and is NOT guaranteed defined when the decode itself raised (UnicodeDecodeError is a ValueError subclass caught by the except).
- Logs `sanitize_log_value(str(err))` + `sanitize_log_value(safe_out)`.
- The raised `ScannerError` and all control flow are unchanged.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Failing tests for lftp.py kill/run_command log sanitization | 87a7171 | test_lftp_log_sanitization.py |
| 1 GREEN | Implement lftp.py kill/run_command sanitization | f507a7c | lftp.py, test_lftp_log_sanitization.py |
| 2 RED | Failing tests for job_status_parser.py parse-error log sanitization | 18c736e | test_job_status_parser.py |
| 2 GREEN | Implement job_status_parser.py parse-error sanitization | e85f3fb | job_status_parser.py, test_job_status_parser.py |
| 3 RED | Failing tests for remote_scanner.py JSON-decode-error log sanitization | 2fdc96e | test_remote_scanner.py |
| 3 GREEN | Implement remote_scanner.py JSON-decode-error sanitization | 0c5108b | remote_scanner.py, test_remote_scanner.py |

## Deviations from Plan

### Test Assertion Refinement (Rule 1 — Bug)

**Found during:** Task 1 (GREEN phase)

**Issue:** Initial RED tests asserted `assertNotIn("INJECTED_LINE", log_line)` — but "INJECTED_LINE" is part of the name content that legitimately appears in the escaped form (the sanitized output still contains the text, just with `\r` and `\n` escaped to tokens). The correct assertion is `assertNotIn("\r", log_line)` checking for literal control bytes.

**Fix:** Replaced all "INJECTED_LINE" substring checks with literal `"\r"` byte checks. For `test_run_command_output_log_sanitized`, the format string `"out ({} bytes):\n {}"` has a structural `\n` (not from user input) — so we check only for the literal `\r` from the injected output, and also verify the escaped tokens `\r` and `\n` are present.

### Task 3 Test — String vs Bytes Return Value

**Found during:** Task 3 (RED phase)

**Issue:** Initial RED test used `mock_ssh.shell.return_value = malformed_json_bytes` (bytes). The bytes repr already escapes CR/LF so the test passed vacuously — it was not a true RED test.

**Fix:** Changed to `mock_ssh.shell.return_value = malformed_json_str` (str with literal CRLF). When `out` is a str, line 114's `isinstance(out, bytes)` check is False so `out_str = out` directly, then `json.loads(out_str)` raises. In the except, `out` is a str with literal CR/LF — without sanitization this would appear in the log verbatim. This makes the test properly RED.

### Verification Gate Formatting (Rule 3 — Blocking Issue)

**Found during:** Task 3 (GREEN phase verify)

**Issue:** Plan's verify gate counted `sanitize_log_value` occurrences by line (`grep -c`). Both `sanitize_log_value(str(err))` and `sanitize_log_value(safe_out)` were on the same line (inside the `format()` call), so `grep -c` returned 2 (import + 1 call line) instead of the required `>=3`.

**Fix:** Split the format arguments onto separate lines:
```python
self.logger.error("JSON decode error: {}\n{}".format(
    sanitize_log_value(str(err)),
    sanitize_log_value(safe_out)))
```
This gives 3 matching lines (import + two call lines), satisfying `>=3`.

## Verification Results

All plan-specified gates pass:

```
# Task 1 (lftp.py)
4 passed test_lftp_log_sanitization.py
import + 8 lftp call sites OK
per-site anchors present
all 3 kill-name sites wrapped (sanitize_log_value(name)==3)
both out sites wrapped (sanitize_log_value(out)==2)
both after sites wrapped (sanitize_log_value(after)==2)
error_out site wrapped (sanitize_log_value(error_out)==1)
EXCLUDED 114 correctly untouched

# Task 2 (job_status_parser.py)
import OK
per-site anchors 724+725 present
import + 2 call sites OK
42 passed test_job_status_parser.py

# Task 3 (remote_scanner.py)
import OK
118 message-anchored
str(err) wrapped
raw out sanitized via NameError-safe safe_out (==1)
except does NOT reference out_str (NameError-safe)
import + 2 interpolated values OK
34 passed test_remote_scanner.py

# Overall
160 passed across test_lftp/ + test_remote_scanner.py
```

## TDD Gate Compliance

- Task 1 RED gate: commit `87a7171` — `test(101-06): add failing tests for lftp.py kill/run_command log sanitization (RED)`
- Task 1 GREEN gate: commit `f507a7c` — `feat(101-06): sanitize lftp.py kill/run_command log sites via sanitize_log_value (GREEN)`
- Task 2 RED gate: commit `18c736e` — `test(101-06): add failing tests for job_status_parser.py parse-error log sanitization (RED)`
- Task 2 GREEN gate: commit `e85f3fb` — `feat(101-06): sanitize job_status_parser.py parse-error log sites via sanitize_log_value (GREEN)`
- Task 3 RED gate: commit `2fdc96e` — `test(101-06): add failing tests for remote_scanner.py JSON-decode-error log sanitization (RED)`
- Task 3 GREEN gate: commit `0c5108b` — `feat(101-06): sanitize remote_scanner.py JSON-decode-error log via sanitize_log_value (GREEN)`

## Known Stubs

None. All sanitized values are fully wired to `sanitize_log_value`; no placeholder implementations.

## Threat Flags

No new security surface introduced. All changes are log-output-only sanitization within existing error paths. No new network endpoints, auth paths, file access patterns, or schema changes.

## Self-Check: PASSED

- [x] `src/python/lftp/lftp.py` — contains `sanitize_log_value` (import + 8 call sites)
- [x] `src/python/lftp/job_status_parser.py` — contains `sanitize_log_value` (import + 2 call sites at 724/725)
- [x] `src/python/controller/scan/remote_scanner.py` — contains `sanitize_log_value` (import + 2 call sites at 118 via str(err) + safe_out)
- [x] `src/python/tests/unittests/test_lftp/test_lftp_log_sanitization.py` — created, 4 tests pass
- [x] `src/python/tests/unittests/test_lftp/test_job_status_parser.py` — 3 new tests added, 42 total pass
- [x] `src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py` — 3 new tests added, 34 total pass
- [x] Commit 87a7171 exists (Task 1 RED)
- [x] Commit f507a7c exists (Task 1 GREEN)
- [x] Commit 18c736e exists (Task 2 RED)
- [x] Commit e85f3fb exists (Task 2 GREEN)
- [x] Commit 2fdc96e exists (Task 3 RED)
- [x] Commit 0c5108b exists (Task 3 GREEN)
- [x] 160 tests pass across targeted test suites
