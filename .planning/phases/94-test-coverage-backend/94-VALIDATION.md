---
phase: 94
slug: test-coverage-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 94 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd src/python && poetry run pytest tests/integration/test_web/test_handler/ tests/unittests/test_controller/test_delete_process.py tests/unittests/test_controller/test_scan/test_active_scanner.py -x` |
| **Full suite command** | `cd src/python && poetry run pytest --cov --cov-report=term-missing` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run the single new/modified test file with `-x`
- **After every plan wave:** `cd src/python && poetry run pytest tests/integration/test_web tests/unittests/test_controller -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 94-01-01 | 01 | 1 | COVER-01 | — | N/A | integration | `poetry run pytest tests/integration/test_web/test_handler/test_stream_status.py tests/integration/test_web/test_handler/test_stream_model.py tests/integration/test_web/test_handler/test_stream_log.py -x` | ✅ (skipped) | ⬜ pending |
| 94-02-01 | 02 | 1 | COVER-04 | — | N/A | integration | `poetry run pytest tests/integration/test_web/test_handler/test_webhook.py -x` | ❌ W0 | ⬜ pending |
| 94-03-01 | 03 | 1 | COVER-05 | — | N/A | unit | `poetry run pytest tests/unittests/test_controller/test_delete_process.py -x` | ❌ W0 | ⬜ pending |
| 94-04-01 | 04 | 1 | COVER-06 | — | N/A | unit | `poetry run pytest tests/unittests/test_controller/test_scan/test_active_scanner.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/helpers/wsgi_stream.py` (plus rename `helpers.py` → `helpers/__init__.py`) — WSGI harness for COVER-01
- [ ] `tests/integration/test_web/test_handler/test_webhook.py` — COVER-04 stub
- [ ] `tests/unittests/test_controller/test_delete_process.py` — COVER-05 stub
- [ ] `tests/unittests/test_controller/test_scan/test_active_scanner.py` — COVER-06 stub

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
