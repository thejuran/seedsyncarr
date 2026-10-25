---
phase: 123
slug: startup-and-shutdown-lifecycle
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-25
---

# Phase 123 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (with pytest-timeout, pytest-cov) |
| **Config file** | `src/python/pyproject.toml` (`[tool.pytest.ini_options]` timeout = 60; coverage `fail_under = 88`) |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_common/test_job.py tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_controller_job.py tests/unittests/test_controller/test_file_operation_manager.py tests/unittests/test_controller/test_auto_delete.py -q` |
| **Full suite command** | `cd src/python && poetry run pytest tests/unittests -q` (compare failures against the known macOS-local baseline) plus `cd src/python && poetry run ruff check .` (CI's separate lint gate, whole tree) |
| **Estimated runtime** | ~20 s quick, ~90 s full |

Known macOS-local baseline (environmental, not regressions): failures in `test_sshcp.py`, `test_scanner.py` (latin chars), `test_scanner_process.py`, `test_extract_process.py`. New lifecycle tests inject fakes instead of spawning real processes.

---

## Sampling Rate

- **After every task commit:** quick run command for the touched test files + whole-tree ruff
- **After every plan wave:** full suite (failure set must equal the baseline) + whole-tree ruff
- **Before `/bm:verify-work`:** full suite + ruff green, plus the D-07 live restart check on the sandbox
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Req / Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------------|----------|-----------|-------------------|-------------|--------|
| LIFE-01 | `Job.run()` setup() failure sets exc_info + shutdown flag and runs cleanup() | unit | `poetry run pytest tests/unittests/test_common/test_job.py -k setup -x` | ❌ W0 | ⬜ pending |
| LIFE-01 | `ScanManager.start()` partial failure stops/joins already-started processes; exception propagates | unit | `poetry run pytest tests/unittests/test_controller/test_scan_manager.py -k partial_start -x` | ❌ W0 | ⬜ pending |
| LIFE-01 | `Controller.start()` partial failure stops already-started components; original exception propagates unmasked (D-06) | unit | `poetry run pytest tests/unittests/test_controller/test_controller.py -k partial_start -x` | ❌ W0 | ⬜ pending |
| LIFE-02 | `ScanManager._terminate_and_join_all()` one process raising doesn't skip the others; first error logged | unit | `poetry run pytest tests/unittests/test_controller/test_scan_manager.py -k cleanup_isolation -x` | ❌ W0 | ⬜ pending |
| LIFE-02 | `FileOperationManager.stop()` one release raising doesn't skip the rest or extract_process stop | unit | `poetry run pytest tests/unittests/test_controller/test_file_operation_manager.py -k stop_cleanup_isolation -x` | ❌ W0 | ⬜ pending |
| LIFE-02 (regression) | `Controller.exit()` loop, auto-delete shutdown guards, lock ordering unchanged | unit (existing) | `poetry run pytest tests/unittests/test_controller/test_auto_delete.py -x` | ✅ | ⬜ pending |
| D-01 (unit half) | Dead scanner observed during a requested shutdown does not log ERROR / raise ScannerProcessDiedError | unit | `poetry run pytest tests/unittests/test_controller/test_scan_manager.py -k shutdown_aware -x` (or test_controller_job.py) | ❌ W0 | ⬜ pending |
| D-01 / D-07 (live half) | Sandbox `docker restart` cycles (idle and active-transfer) log neither "Scanner process(es) died unexpectedly" nor "Could not terminate the child"; /server/status 200; scans resume | manual (sandbox) | see Manual-Only below | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_common/test_job.py` — setup()-raising Job subclass tests
- [ ] `tests/unittests/test_controller/test_scan_manager.py` — partial-start cleanup, terminate/join fault isolation, shutdown-aware health check
- [ ] `tests/unittests/test_controller/test_controller.py` — Controller.start() partial-failure cleanup class
- [ ] `tests/unittests/test_controller/test_file_operation_manager.py` — stop() release-loop fault isolation
- [ ] Optional: `MultiprocessingLogger.stop()` without prior start() guard test

*No framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Normal restarts log no shutdown errors and the app comes back | D-01, D-07 (LIFE-01/02 live) | Signal delivery from `tini -g` to forked/pty children only happens in the real container | Pin `seedsyncarr-test` to the phase PR CI staging digest; run several `sudo /usr/local/bin/docker restart seedsyncarr-test` cycles incl. at least one during an active transfer; grep the app log window for the two error strings (must be 0); `/server/status` 200 and a new scan after each; restore the original pin with fresh-session check; production fingerprint unchanged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
