---
phase: 85
slug: e2e-test-audit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 85 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (via Docker compose harness) |
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
| 85-01-01 | 01 | 1 | E2E-01 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 85-01-02 | 01 | 1 | E2E-02 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |
| 85-01-03 | 01 | 1 | E2E-03 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| arm64 E2E pass | E2E-02 | CI-only (needs ARM runner) | Push to CI, verify arm64 job green |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
