---
phase: 69
slug: e2e-selector-update
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 69 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (E2E) |
| **Config file** | `playwright.config.ts` |
| **Quick run command** | `npx playwright test --project=chromium` |
| **Full suite command** | `npx playwright test` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npx playwright test --project=chromium`
- **After every plan wave:** Run `npx playwright test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 69-01-01 | 01 | 1 | E2E-01 | — | N/A | e2e | `npx playwright test dashboard.spec.ts` | ✅ | ⬜ pending |
| 69-01-02 | 01 | 1 | E2E-02 | — | N/A | e2e | `npx playwright test bulk-actions.spec.ts` | ✅ | ⬜ pending |
| 69-01-03 | 01 | 1 | E2E-03 | — | N/A | e2e | `npx playwright test` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
