---
phase: 91
slug: e2e-test-fixes-platform
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 91 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright 1.x (E2E) |
| **Config file** | `src/e2e/playwright.config.ts` |
| **Quick run command** | `make run-tests-e2e` |
| **Full suite command** | `make run-tests-e2e` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make run-tests-e2e`
- **After every plan wave:** Run `make run-tests-e2e`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 91-01-01 | 01 | 1 | E2EFIX-01 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 91-01-02 | 01 | 1 | E2EFIX-05 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 91-01-03 | 01 | 1 | E2EFIX-07 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 91-02-01 | 02 | 1 | E2EFIX-02 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 91-02-02 | 02 | 1 | E2EFIX-03 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 91-02-03 | 02 | 1 | E2EFIX-06 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 91-03-01 | 03 | 1 | E2EFIX-04 | — | CSP enforcement not bypassed | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 91-03-02 | 03 | 1 | PLAT-01 | — | CSP violations detected and fail tests | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 91-04-01 | 04 | 1 | PLAT-02 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| arm64 sort correctness | PLAT-02 | Requires arm64 hardware | Run `make run-tests-e2e` on arm64 host and verify dashboard sort tests pass |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
