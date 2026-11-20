---
phase: 129
slug: web-service-cleanup-isolation
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| **Estimated runtime** | ~5 seconds quick; full unittests a few minutes |

---

## Sampling Rate

- **After every task commit:** Run quick run command plus `ruff check src/python/`
- **After every plan wave:** Run full suite command
- **Before `/bm:verify-work`:** Full suite must be green, ruff clean
- **Max feedback latency:** 30 seconds (quick run)

---

## Per-Task Verification Map

Filled in by the planner per task. Requirement → test mapping (from 129-RESEARCH.md Validation Architecture):

| Req | Behavior | Test Type | Automated Command (`-k` on test_web_app_job.py) | File Exists | Status |
|-----|----------|-----------|-------------------------------------------------|-------------|--------|
| WEB-01a | `app.stop()` raises; `server.stop()` and join still run; logged (red first) | unit | `-k app_stop_failure` | ✅ extend | ⬜ pending |
| WEB-01b | `server.stop()` raises; join still runs; logged | unit | `-k server_stop_failure` | ✅ extend | ⬜ pending |
| WEB-01c | `thread.join` raises; others ran; logged; cleanup returns | unit | `-k join_failure` | ✅ extend | ⬜ pending |
| WEB-01d | All three raise; all attempted and logged; no raise | unit | `-k all_steps_fail` | ✅ extend | ⬜ pending |
| WEB-02a | Cleanup without setup: no raise, no exception logged | unit | existing `test_cleanup_without_setup_does_not_raise` | ✅ | ⬜ pending |
| WEB-02b | Thread never started: join skipped, no error | unit | `-k thread_not_started` | ✅ extend | ⬜ pending |
| WEB-02c | `stop()` before `run()` assigns server: no raise; run closes instead of serving | unit | `-k stop_before_run` | ✅ extend | ⬜ pending |
| WEB-02d | `daemon_threads=True` and `daemon=True` | unit | `-k daemon` | ✅ extend | ⬜ pending |
| WEB-02e | Stuck thread: bounded join, WARNING, returns | unit | `-k stuck` | ✅ extend | ⬜ pending |
| WEB-02f | Subprocess with never-stopped real server exits (red first) | integration (subprocess) | `-k process_exits` | ✅ extend | ⬜ pending |
| WEB-02g | Real server clean stop; port rebinds | unit (real socket) | `-k real_server_stop` | ✅ extend | ⬜ pending |
| LINT | Whole-tree lint | static | `ruff check src/python/` | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. TDD: WEB-01a and WEB-02f are written first and must fail on current code.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live restart on NAS frees the port and restarts cleanly | WEB-02 | Needs deployed container | Handed off to Phase 130 restart smoke check (D-08); check container logs for bind errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
