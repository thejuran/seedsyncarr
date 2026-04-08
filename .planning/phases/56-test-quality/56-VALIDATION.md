---
phase: 56
slug: test-quality
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python), Karma/Jasmine (Angular), Playwright (E2E) |
| **Config file** | pyproject.toml, karma.conf.js, playwright.config.ts |
| **Quick run command** | `make run-tests-python` |
| **Full suite command** | `make run-tests-python && cd src/angular && npm test -- --watch=false` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make run-tests-python`
- **After every plan wave:** Run `make run-tests-python && cd src/angular && npm test -- --watch=false`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 56-01-01 | 01 | 1 | HARD-03 | — | N/A | unit | `make run-tests-python` | ✅ | ⬜ pending |
| 56-01-02 | 01 | 1 | HARD-04 | — | N/A | e2e | `cd src/e2e && npx playwright test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements.

*No new test framework or fixtures needed — pytest, Karma, and Playwright are already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UI error state rendering | HARD-04 | E2E test covers programmatically; visual check confirms layout | Run E2E, inspect screenshot for error toast/banner |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
