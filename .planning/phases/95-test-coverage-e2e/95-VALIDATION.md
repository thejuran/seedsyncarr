---
phase: 95
slug: test-coverage-e2e
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 95 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (via @playwright/test) |
| **Config file** | `src/e2e/playwright.config.ts` |
| **Quick run command** | `cd src/e2e && npx playwright test --grep "@smoke"` |
| **Full suite command** | `cd src/e2e && npx playwright test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src/e2e && npx playwright test --grep "@smoke"`
- **After every plan wave:** Run `cd src/e2e && npx playwright test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 95-01-01 | 01 | 1 | COVER-02 | — | N/A | e2e | `cd src/e2e && npx playwright test logs.spec.ts` | ❌ W0 | ⬜ pending |
| 95-02-01 | 02 | 1 | COVER-03 | — | N/A | e2e | `cd src/e2e && npx playwright test settings.spec.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/e2e/tests/logs.spec.ts` — stubs for COVER-02
- [ ] `src/e2e/tests/settings.spec.ts` — stubs for COVER-03

*Existing infrastructure covers Playwright setup (Phase 92).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
