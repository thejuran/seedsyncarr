---
phase: 86
slug: final-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 86 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python), Karma/Jasmine (Angular), Playwright (E2E) |
| **Config file** | `src/python/pyproject.toml`, `src/angular/karma.conf.js`, `src/e2e/playwright.config.ts` |
| **Quick run command** | `make run-tests-python` |
| **Full suite command** | `make run-tests-python && make run-tests-angular && make run-tests-e2e` |
| **Estimated runtime** | ~300 seconds (all three layers) |

---

## Sampling Rate

- **After every task commit:** Run `make run-tests-python`
- **After every plan wave:** Run `make run-tests-python && make run-tests-angular && make run-tests-e2e`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 86-01-01 | 01 | 1 | VAL-01 | — | N/A | CI | GitHub Actions CI run green | ✅ | ⬜ pending |
| 86-01-02 | 01 | 2 | VAL-02 | — | N/A | manual | Read CI logs for coverage % | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI pipeline green on GitHub Actions | VAL-01 | Requires real GitHub Actions environment | Push to main, check Actions tab for all-green |
| Coverage % extraction from CI logs | VAL-02 | CI log parsing is manual | Read `unittests-python` job output for coverage line |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
