---
phase: 87
slug: python-test-fixes-critical-warning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 87 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `src/python/pyproject.toml` |
| **Quick run command** | `make run-tests-python` |
| **Full suite command** | `make run-tests-python` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make run-tests-python`
- **After every plan wave:** Run `make run-tests-python`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 87-01-01 | 01 | 1 | PYFIX-01 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-01-02 | 01 | 1 | PYFIX-02 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-02-01 | 02 | 1 | PYFIX-03 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-02-02 | 02 | 1 | PYFIX-04 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-02-03 | 02 | 1 | PYFIX-05 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-02-04 | 02 | 1 | PYFIX-06 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-02-05 | 02 | 1 | PYFIX-07 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-02-06 | 02 | 1 | PYFIX-08 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-02-07 | 02 | 1 | PYFIX-09 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 87-02-08 | 02 | 1 | PYFIX-10 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
