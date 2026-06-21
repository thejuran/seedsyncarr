---
phase: 114
slug: scanner-auto-recovery
status: revised
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-21
---

# Phase 114 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (>= 9.x) with pytest-timeout, pytest-cov; tests are `unittest.TestCase` classes run by pytest |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` (`pythonpath=["."]`, global `timeout=60`) |
| **Quick run command** | `cd src/python && python -m pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py tests/unittests/test_seedsyncarr.py -x` |
| **Full suite command** | `make run-tests-python` (Docker: `pytest -v -p no:cacheprovider`) **AND** `ruff check src/python/` (separate CI gate) |
| **Estimated runtime** | ~quick: seconds; full suite: minutes |

---

## Sampling Rate

- **After every task commit:** Run the targeted quick run for the file(s) touched (`pytest <file> -x`) **and** `ruff check src/python/`
- **After every plan wave:** Run `make run-tests-python` (full Python suite) **and** `ruff check src/python/`
- **Before `/gsd:verify-work`:** Full Python suite green **AND** `ruff check src/python/` clean
- **Max feedback latency:** quick run = seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 114-01.1 | 114-01 | 1 | SCAN-01 | T-114-01 | name-resolution reclassified retryable by the new CASE-INSENSITIVE `_is_name_resolution_ssh_error` matcher across ALL resolver surfaces (collapsed `Bad hostname:` AND raw `Could not resolve hostname` / `Name or service not known` / `Temporary failure in name resolution`); permanent classes (wrong pw, host-key) and transient (timeout/refused) are NOT name-resolution (matcher-excludes asserts) | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k "name_resolution and not retry and not install and not recovers and not exhausts and not bounded" -x` | ❌ W0 | ⬜ pending |
| 114-01.2 | 114-01 | 1 | SCAN-02 | T-114-04 | Bounded NAME-RESOLUTION retry recovers in-scan on the MAIN-SCAN path on attempt N (fails twice, succeeds third) for BOTH the collapsed and the RAW resolver surface; sleep called N-1 times — via the ONE shared retry helper | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k "name_resolution_retry_recovers_main_scan or name_resolution_raw_recovers_main_scan" -x` | ❌ W0 | ⬜ pending |
| 114-01.3 | 114-01 | 1 | SCAN-02 | T-114-04 | MAIN-SCAN name-resolution retry is bounded — never more than MAX_ATTEMPTS main-scan calls on persistent failure (collapsed AND raw resolver string) | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k name_resolution_retry_bounded_main_scan -x` | ❌ W0 | ⬜ pending |
| 114-01.4 | 114-01 | 1 | SCAN-03 | T-114-01 | MAIN-SCAN name-resolution exhaustion raises `ScannerError(REMOTE_SERVER_SCAN, recoverable=False)` with the unchanged localized message, for the collapsed AND raw resolver surface | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k name_resolution_retry_exhausts_main_scan -x` | ❌ W0 | ⬜ pending |
| 114-01.5 | 114-01 | 1 | SCAN-03 (finding 2) | T-114-04 | Transient timeout/refused are NOT retried in-scan: they raise immediately (recoverable=True) on the first attempt and recover on the next interval — the existing first-run timeout/refused tests stay green UNCHANGED | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k "transient_timeout_not_retried_in_scan or first_run_timeout or first_run_connection_refused or recovers_after_first_run_timeout" -x` | ❌ W0 (new test) / ✅ (existing must stay green) | ⬜ pending |
| 114-01.6 | 114-01 | 1 | SCAN-03 | T-114-01 | Existing permanent-error tests (wrong pw, host-key change, SystemScannerError, mangled output) still surface `recoverable=False` immediately; new matcher-excludes asserts confirm timeout/refused/auth/host-key are NOT name-resolution (matcher not over-broadened) | unit (regression) | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -x` | ✅ (must stay green) | ⬜ pending |
| 114-01.7 | 114-01 | 1 | SCAN-01/02 (codex install-path finding) | T-114-01/04 | INSTALL path (`__install_done=false`, runs at startup + after every auto-restart): an install-time name-resolution error (md5sum check OR copy) recovers within the cap via the SAME shared name-resolution-only retry helper → `scan()` proceeds, no ScannerError; sleep called k times — for the collapsed `Bad hostname:` surface | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k install_name_resolution_recovers -x` | ❌ W0 | ⬜ pending |
| 114-01.8 | 114-01 | 1 | SCAN-01/02 (codex matcher-coverage finding) | T-114-01/04 | INSTALL path: an install-time RAW resolver string (`Could not resolve hostname` / `Name or service not known` / `Temporary failure in name resolution`) on the md5sum OR copy op recovers within the cap via the SAME shared helper, case-insensitively — proves the broadened matcher covers the raw fallthrough surface on the install path, not just `Bad hostname:` | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k install_name_resolution_raw_recovers -x` | ❌ W0 | ⬜ pending |
| 114-01.9 | 114-01 | 1 | SCAN-02/03 (codex install-path + matcher-coverage findings) | T-114-01/04 | INSTALL path: a persistent install-time name-resolution error (collapsed OR raw) is bounded (md5sum/copy op count never exceeds the cap) and surfaces `ScannerError(REMOTE_SERVER_INSTALL, recoverable=False)` with the unchanged message — a persistently-wrong hostname at startup/post-restart still surfaces (SCAN-03) and is bounded (SCAN-02) without burning RECOV-01 budget on a blip | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k install_name_resolution_bounded -x` | ❌ W0 | ⬜ pending |
| 114-01.10 | 114-01 | 1 | SCAN-03 (finding 2, install path) | T-114-04 | INSTALL-path timeout/connection-refused keep existing behavior: NOT retried, raise immediately on attempt 1 with `ScannerError(REMOTE_SERVER_INSTALL, recoverable=True)`; the existing `test_raises_recoverable_error_on_md5sum_timeout` / `_on_copy_timeout` and the install/df exact call-count tests stay green UNCHANGED | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k "install_timeout_unchanged or md5sum_timeout or copy_timeout or md5sum_error or failed_copy or calls_correct_ssh_md5sum_command" -x` | ❌ W0 (new test) / ✅ (existing must stay green) | ⬜ pending |
| 114-01.11 | 114-01 | 1 | SCAN-01/03 (SSH contract) | T-114-01 | The SSH-layer contract is unaffected: broadening NAME_RESOLUTION_ERROR_PATTERNS changes how RemoteScanner CLASSIFIES errors, NOT what sshcp.py RAISES — no sshcp.py raise site changes — so `test_sshcp.py` stays green | unit (regression) | `pytest tests/unittests/test_ssh/test_sshcp.py -x` | ✅ (must stay green) | ⬜ pending |
| 114-02.1 | 114-02 | 1 | RECOV-01 | T-114-05 | First permanent-class controller death raises `ServiceRestart(auto=True, reset=False)` when budget remains (decision evaluated at failure time, returns `(True, False)`) | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_within_cap -x` | ❌ W0 | ⬜ pending |
| 114-02.2 | 114-02 | 1 | RECOV-01 | T-114-05 | After the cap with a too-young current run, `_should_auto_restart` returns `(False, False)` and `AppError` falls through to `server.up=False` + `error_msg` (no `ServiceRestart`, no crash) | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_cap_exhausted -x` | ❌ W0 | ⬜ pending |
| 114-02.3 | 114-02 | 1 | RECOV-01 (finding 1) | T-114-06 | A run started older than reset_secs that dies AT THE CAP returns `(True, True)` (stayed-up reset computed from current run age) ⇒ raises `ServiceRestart(auto=True, reset=True)` — the reset signal is carried out | unit | `pytest tests/unittests/test_seedsyncarr.py -k "restart_reset or restart_reset_at_cap" -x` | ❌ W0 | ⬜ pending |
| 114-02.4 | 114-02 | 1 | RECOV-01 (finding 1) | T-114-08 | UI-requested restart (`ServiceRestart(auto=False)`) does NOT increment/burn the auto-recovery consecutive counter | unit | `pytest tests/unittests/test_seedsyncarr.py -k ui_restart -x` | ❌ W0 | ⬜ pending |
| 114-02.5 | 114-02 | 1 | RECOV-01 (finding 2 — codex follow-on) | T-114-06 | A reset-at-cap auto restart NORMALIZES the counter to a FRESH budget: main()'s mapping sets the next counter to **1** (NOT cap+1), and a subsequent quick failure with consecutive=1 (< cap, run too young) still returns `(True, False)` so it is NOT denied immediately — intermittent failures recover with a refreshed budget | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_fresh_budget -x` | ❌ W0 | ⬜ pending |
| 114-xx | both | all | (cross-cutting) | T-114-02/03/07 | Whole-tree lint clean | lint | `ruff check src/python/` | ✅ (separate gate) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_controller/test_scan/test_remote_scanner.py` — extend with NAME-RESOLUTION retry-recovers / retry-exhausts / retry-bounded / classification tests for the MAIN-SCAN path (covers SCAN-01/02/03) AND for the INSTALL path (`__install_done=false` — the path that runs at startup and after every auto-restart): `install_name_resolution_recovers` (md5sum-op and copy-op variants), `install_name_resolution_bounded` (md5sum-op and copy-op variants, asserting `ScannerError(REMOTE_SERVER_INSTALL, recoverable=False)` with the unchanged message + bounded op count), and `install_timeout_unchanged` (md5sum-op and copy-op timeout variants pinning that timeout/refused are NOT retried on the install path either). **CRITICAL (codex matcher-coverage finding):** the classification AND retry tests MUST exercise the RAW resolver strings (`Could not resolve hostname`, `Name or service not known`, `Temporary failure in name resolution`) and a case-insensitive variant — not only `Bad hostname:` — on BOTH the main scan (`name_resolution_raw_recovers_main_scan`) and the install path (`install_name_resolution_raw_recovers`, md5sum-op and copy-op). Also add a `transient_timeout_not_retried_in_scan` test pinning finding 2 on the main-scan path AND matcher-excludes asserts (matcher returns False for timeout/refused/wrong-password/host-key). The existing first-run timeout/refused tests at :334-399, `test_recovers_after_first_run_timeout` :401, the install md5sum/copy timeout tests :470-514, and the install/df exact call-count tests (:145, :631) stay green UNCHANGED (their errors are timeout/permanent, never name-resolution, so the shared retry gate is False and they raise on attempt 1 with their exact existing call counts). Retry condition is name-resolution ONLY, enforced once in the ONE shared retry helper that wraps BOTH the main scan call and the install md5sum/copy calls. Patch `controller.scan.remote_scanner.time.sleep`. Reuse the existing call-counter `ssh_shell` harness for md5sum/main-scan ops and `self.mock_ssh.copy.side_effect` for copy ops.
- [ ] `tests/unittests/test_seedsyncarr.py` — add restart-within-cap / cap-exhausted / stayed-up-reset / reset-at-cap (finding 1) / fresh-budget-after-reset (finding 2, codex follow-on) / UI-does-not-burn-budget (finding 1) tests (covers RECOV-01). Extract the restart-budget decision into a pure `_should_auto_restart(consecutive, cap, current_run_start, reset_secs, now) -> (should_restart, reset_applied)` static helper (current-run-age aware) so it is unit-testable without spinning the full `run()` loop — mirrors how `_emit_startup_warnings` / `_detect_incomplete_config` are tested as static methods. The decision is evaluated at failure time, not as a precomputed bool; `ServiceRestart` carries `auto` AND `reset` flags so UI restarts do not burn the auto budget and a reset-at-cap auto restart normalizes the counter to 1 (a fresh budget) rather than cap+1.
- [ ] No framework install needed — pytest/ruff/pytest-timeout already present.
- [ ] No new shared fixtures required — existing `tests/helpers` + inline mock-Sshcp harness suffice.

*Spawn-vs-fork note: new retry-helper unit tests call `scanner.scan()` directly (no spawn) — start-method-agnostic. 114-01 chose Pitfall-1 option (a) (bare `time.sleep` + low ceiling), so NO new attribute is added to `RemoteScanner` and the spawn-pickle surface is unchanged; no process-level abort-during-backoff test is required. If a future change wires a terminate Event into `RemoteScanner`, ensure it is picklable (spawn-safe per `app_process.py:__getstate__`) and add one process-level test asserting prompt abort during backoff.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end recovery from a real DNS blip against the live seedbox (at startup/install AND mid-scan) | SCAN-01/02/03 | Live-NAS deploy verification is QEMU-blocked (Out of Scope as a gate); a real transient DNS blip cannot be reliably reproduced on demand | Optional post-merge: observe scanner survives a transient resolution failure in NAS logs, including a blip during the startup install path and a raw-resolver-string ("Temporary failure in name resolution") surface. Not a phase gate. |

*All unit-level phase behaviors have automated verification; the only manual item is explicitly out-of-scope as a gate.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < ~60s (quick run)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
