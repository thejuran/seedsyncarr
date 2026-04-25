---
phase: 88
slug: python-test-fixes-medium-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 88 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (unittest.TestCase) |
| **Config file** | `src/python/pyproject.toml` |
| **Quick run command** | `make run-tests-python` |
| **Full suite command** | `make run-tests-python` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make run-tests-python`
- **After every plan wave:** Run `make run-tests-python`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 88-01-01 | 01 | 1 | PYFIX-11 | — | XSS chars escaped in meta tag | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 88-01-02 | 01 | 1 | PYFIX-12 | — | Deterministic scanner sync | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 88-01-03 | 01 | 1 | PYFIX-19 | — | Assertion always executes | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 88-02-01 | 02 | 2 | PYFIX-13 | — | Real sleep replaced, 4s savings | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 88-02-02 | 02 | 2 | PYFIX-14 | — | TemporaryDirectory cleaned up | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 88-02-03 | 02 | 2 | PYFIX-15 | — | Bottle imports at module level | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 88-02-04 | 02 | 2 | PYFIX-16 | — | Logger handlers removed in tearDown | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 88-02-05 | 02 | 2 | PYFIX-17 | — | job.join replaces sleep | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 88-02-06 | 02 | 2 | PYFIX-18 | — | Busy-wait loops have sleep | unit | `make run-tests-python` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 4-second suite speedup | PYFIX-13 | Timing measurement | Run `make run-tests-python` before and after, compare wall-clock time |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
