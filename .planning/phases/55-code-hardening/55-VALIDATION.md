---
phase: 55
slug: code-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + Angular Karma/ESLint |
| **Config file** | `src/python/pyproject.toml`, `src/angular/.eslintrc.json` |
| **Quick run command** | `ruff check src/python && cd src/angular && npm run lint` |
| **Full suite command** | `ruff check src/python && cd src/angular && npm run lint` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `ruff check src/python && cd src/angular && npm run lint`
- **After every plan wave:** Run full lint suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 1 | HARD-01 | — | N/A | grep | `git ls-files \| grep -i planning` | ✅ | ⬜ pending |
| 55-01-02 | 01 | 1 | HARD-02 | — | N/A | grep | `grep -rn "# Copyright 2017" src/python/` | ✅ | ⬜ pending |
| 55-02-01 | 02 | 1 | HARD-06 | — | N/A | lint | `cd src/angular && npm run lint` | ✅ | ⬜ pending |
| 55-03-01 | 03 | 2 | HARD-05 | — | N/A | lint | `ruff check src/python` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Code style consistency | HARD-05 | Subjective assessment | Review files for consistent structure |
| Comment quality | HARD-02 | Requires human judgment | Spot-check comments describe "why" not "what" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
