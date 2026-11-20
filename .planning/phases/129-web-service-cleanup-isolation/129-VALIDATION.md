---
phase: 129
slug: web-service-cleanup-isolation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-11-19
---

# Phase 129 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ^9.0.3 + pytest-timeout (global 60 s) |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider` |
| **Full suite command** | `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider` then, from repo root, `ruff check src/python/` |
| **Estimated runtime** | ~3 seconds quick (22 tests); full unittests a few minutes |

---

## Sampling Rate

- **After every task commit:** Run quick run command plus `ruff check src/python/`
- **After every plan wave:** Run full suite command
- **Before `/bm:verify-work`:** Full suite must be green, ruff clean
- **Max feedback latency:** 30 seconds (quick run)

---

## Per-Task Verification Map

Every command runs from the repo root as written.

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| WEB-01a | `app.stop()` raises; `server.stop()` and join still run; logged (red first) | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k app_stop_failure` | ✅ | ✅ green |
| WEB-01b | `server.stop()` raises; join still runs; logged | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k server_stop_failure` | ✅ | ✅ green |
| WEB-01c | `thread.join` raises; others ran; logged; cleanup returns | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k join_failure` | ✅ | ✅ green |
| WEB-01d | All three raise; all attempted and logged; no raise | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k all_steps_fail` | ✅ | ✅ green |
| WEB-02a | Cleanup without setup: no raise, no exception logged | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k cleanup_without_setup` | ✅ | ✅ green |
| WEB-02b | Thread never started: join skipped, no error | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k thread_not_started` | ✅ | ✅ green |
| WEB-02c | `stop()` before `run()` assigns server: no raise; run closes instead of serving | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k stop_before_run` | ✅ | ✅ green |
| WEB-02d | `daemon_threads=True` and `daemon=True` | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k daemon` | ✅ | ✅ green |
| WEB-02e | Stuck thread: bounded join, WARNING, returns | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k stuck` | ✅ | ✅ green |
| WEB-02f | Subprocess with never-stopped real server exits (red first) | integration (subprocess) | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k process_exits` | ✅ | ✅ green |
| WEB-02g | Real server clean stop; port rebinds | unit (real socket) | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k real_server_stop` | ✅ | ✅ green |
| WEB-02h | Real cleanup against a real five-worker server with all five workers stuck returns within the bound, warns, never calls `os._exit` (red first) | integration (real socket) | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k stuck_requests` | ✅ | ✅ green |
| WEB-02i | `stop()` while the server is still being constructed (event barrier): closed, never serves | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k stop_during_server_construction` | ✅ | ✅ green |
| WEB-02j | `stop()` right after the server is published (event barrier): loop ended through running flag and socket close | unit | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider -k stop_right_after_publication` | ✅ | ✅ green |
| LINT | Whole-tree lint | static | `ruff check src/python/` | n/a | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Each selector was run alone on 2026-11-19 and selected at least one test (`daemon` 2, `stuck` 3, `real_server_stop` 2, all others 1); all exited 0. The whole file passed three runs in a row (22 passed each, 2.41 s, 2.41 s, 2.50 s).

### Local environment notes

- The full unit suite on the macOS dev machine has four modules that fail for environment reasons unrelated to this phase (multiprocessing spawn start method, no local sshd): `tests/unittests/test_controller/test_extract/test_extract_process.py`, `tests/unittests/test_controller/test_scan/test_scanner_process.py`, `tests/unittests/test_ssh/test_sshcp.py`, `tests/unittests/test_system/test_scanner.py`. They are pre-existing and are not touched by Phase 129; Linux CI on the pull request is the authoritative full-suite and coverage gate (fail_under 88). Observed locally on 2026-11-19, each module run alone under a 90 s cap: test_extract_process.py hung until the cap (exit 124), test_scanner_process.py `1 failed, 1 error` (with `-x`), test_sshcp.py `1 failed` (with `-x`), test_scanner.py `1 failed, 3 passed` (with `-x`). The rest of the unit suite, run with those four modules ignored: `1996 passed, 58 warnings, 179 subtests passed in 51.14s`.
- The local pytest used here does not have the pytest-timeout plugin loaded (`Unknown config option: timeout` warning), so the 60 s global timeout is enforced by CI only. The web test file's slowest test takes about 1 s locally.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. TDD: WEB-01a, WEB-02f and WEB-02h are written first and must fail on current code. Each red reason is confirmed from the captured output of a run of that one selector (expected failure text, `1 failed`, no import or collection error), not from the exit status. Done: red runs recorded in 129-01-SUMMARY.md and 129-02-SUMMARY.md.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live restart on NAS frees the port and restarts cleanly | WEB-02 | Needs deployed container | Handed off to Phase 130's release-image smoke test per D-08 (no deploy in Phase 129). Restart the 1.8.1 image and confirm a clean web-service shutdown: none of the three `Error ... during web service cleanup` lines, no `Web server did not stop within` warning, and no bind error after restart. Check container logs (stderr) as well as the app log file, because a server-thread bind failure is written to stderr. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-11-19, gate green
