---
phase: 96
slug: rate-limiting-tooling
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
---

# Phase 96 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `src/python/pyproject.toml` |
| **Quick run command** | `cd src/python && python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `cd src/python && python -m pytest tests/ --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src/python && python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `cd src/python && python -m pytest tests/ --timeout=60`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 96-01-01 | 01 | 1 | RATE-01 | — | Rate limit decorator returns 429 after threshold | unit | `cd src/python && python -m pytest tests/unittests/test_web/test_rate_limit.py -x -q` | ✅ (TDD — Plan 01 creates) | ⬜ pending |
| 96-01-02 | 03 | 2 | RATE-02 | — | Config/set endpoint rate limited at 60/60s | unit | `cd src/python && python -m pytest tests/unittests/test_web/test_handler/test_config_handler.py -x -q` | ✅ | ⬜ pending |
| 96-01-03 | 03 | 2 | RATE-03 | — | Test-connection endpoints rate limited at 5/60s | unit | `cd src/python && python -m pytest tests/unittests/test_web/test_handler/test_config_handler.py -x -q` | ✅ | ⬜ pending |
| 96-01-04 | 03 | 2 | RATE-04 | — | Status endpoint rate limited at 60/60s | unit | `cd src/python && python -m pytest tests/unittests/test_web/test_handler/test_status_handler.py -x -q` | ✅ | ⬜ pending |
| 96-02-01 | 02 | 1 | TOOL-01 | — | Semgrep js-nosql-injection-where requires MongoDB context | lint | `semgrep --validate --config javascript.yaml && semgrep scan TP/FP tests` | ✅ | ⬜ pending |
| 96-02-02 | 02 | 1 | TOOL-02 | — | Semgrep js-xss-eval-user-input excludes function callbacks | lint | `semgrep --validate --config javascript.yaml && semgrep scan TP/FP tests` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*No separate Wave 0 needed — Plan 01 (TDD) creates `tests/unittests/test_web/test_rate_limit.py` as its first deliverable. Existing test infrastructure covers RATE-02, RATE-03, RATE-04, TOOL-01, TOOL-02.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plan 01 TDD creates test file)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-28
