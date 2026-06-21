---
phase: 114
slug: scanner-auto-recovery
status: draft
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
| 114-xx | TBD | 1 | SCAN-01 | — | `Bad hostname:` reclassified retryable by new matcher / retried by loop; permanent classes (wrong pw, host-key) stay permanent | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k name_resolution -x` | ❌ W0 | ⬜ pending |
| 114-xx | TBD | 1 | SCAN-02 | — | Bounded retry recovers on attempt N (fails twice, succeeds third); sleep called N-1 times | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k retry_recovers -x` | ❌ W0 | ⬜ pending |
| 114-xx | TBD | 1 | SCAN-02 | — | Retry is bounded — never more than MAX_ATTEMPTS scan calls on persistent failure | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k retry_bounded -x` | ❌ W0 | ⬜ pending |
| 114-xx | TBD | 1 | SCAN-03 | — | Retry exhaustion raises `ScannerError(recoverable=False)` with the unchanged localized message | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k retry_exhausts -x` | ❌ W0 | ⬜ pending |
| 114-xx | TBD | 1 | SCAN-03 | — | Existing permanent-error tests (wrong pw, host-key change, SystemScannerError, mangled output) still surface `recoverable=False` immediately | unit (regression) | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -x` | ✅ (must stay green) | ⬜ pending |
| 114-xx | TBD | 1 | RECOV-01 | — | First permanent-class controller death raises `ServiceRestart` (auto-restart) when budget remains | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_within_cap -x` | ❌ W0 | ⬜ pending |
| 114-xx | TBD | 1 | RECOV-01 | — | After the cap, `AppError` falls through to `server.up=False` + `error_msg` (no `ServiceRestart`, no crash) | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_cap_exhausted -x` | ❌ W0 | ⬜ pending |
| 114-xx | TBD | 1 | RECOV-01 | — | A run that stays up past the reset threshold resets the consecutive counter | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_reset -x` | ❌ W0 | ⬜ pending |
| 114-xx | TBD | all | (cross-cutting) | — | Whole-tree lint clean | lint | `ruff check src/python/` | ✅ (separate gate) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_controller/test_scan/test_remote_scanner.py` — extend with retry-recovers / retry-exhausts / retry-bounded / name-resolution tests (covers SCAN-01/02/03). Patch the scan-path `time.sleep`. Reuse the existing call-counter `ssh_shell` harness.
- [ ] `tests/unittests/test_seedsyncarr.py` — add restart-cap / cap-exhausted / stayed-up-reset tests (covers RECOV-01). Prefer extracting the restart-budget decision into a small pure/static helper (e.g. `_should_auto_restart(...)`) so it is unit-testable without spinning the full `run()` loop — mirrors how `_emit_startup_warnings` / `_detect_incomplete_config` are tested as static methods.
- [ ] No framework install needed — pytest/ruff/pytest-timeout already present.
- [ ] No new shared fixtures required — existing `tests/helpers` + inline mock-Sshcp harness suffice.

*Spawn-vs-fork note: new retry-loop unit tests call `scanner.scan()` directly (no spawn) — start-method-agnostic. If the terminate-Event pitfall fix adds an attribute to `RemoteScanner`, ensure it is picklable (spawn-safe per `app_process.py:__getstate__`) and add one process-level test asserting prompt abort during backoff.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end recovery from a real DNS blip against the live seedbox | SCAN-01/02/03 | Live-NAS deploy verification is QEMU-blocked (Out of Scope as a gate); a real transient DNS blip cannot be reliably reproduced on demand | Optional post-merge: observe scanner survives a transient resolution failure in NAS logs. Not a phase gate. |

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
