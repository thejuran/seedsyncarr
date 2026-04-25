---
phase: 89
slug: python-test-architecture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 89 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.3 (running unittest.TestCase tests) |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
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
| 89-01-01 | 01 | 1 | PYARCH-01 | — | N/A | smoke | `make run-tests-python` | N/A | ⬜ pending |
| 89-01-02 | 01 | 1 | PYARCH-02 | — | N/A | smoke | `make run-tests-python` | N/A | ⬜ pending |
| 89-01-03 | 01 | 1 | PYARCH-03 | — | N/A | smoke | `make run-tests-python` | N/A | ⬜ pending |
| 89-01-04 | 01 | 1 | PYARCH-06 | — | N/A | smoke | `make run-tests-python` | N/A | ⬜ pending |
| 89-02-01 | 02 | 1 | PYARCH-04 | — | N/A | manual-only | Verify file exists | N/A | ⬜ pending |
| 89-02-02 | 02 | 1 | PYARCH-05 | — | N/A | manual-only | Verify documentation exists | N/A | ⬜ pending |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Coverage gap documentation exists | PYARCH-04 | Documentation file, no code behavior | Verify `COVERAGE-GAPS.md` exists and lists ActiveScanner, WebAppJob, WebAppBuilder, scan_fs |
| Name-mangling trade-off documented | PYARCH-05 | Documentation, no code behavior | Verify documentation section exists listing 155 name-mangling references |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
