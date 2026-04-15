---
phase: 70
slug: drilldown-segment-filters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 70 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest 29.x (Angular testing with @angular/core/testing) |
| **Config file** | jest.config.ts |
| **Quick run command** | `npx jest --testPathPattern transfer-table` |
| **Full suite command** | `npx jest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npx jest --testPathPattern transfer-table`
- **After every plan wave:** Run `npx jest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 70-01-01 | 01 | 1 | UI-DRILL-01 | — | N/A | unit | `npx jest --testPathPattern transfer-table` | ✅ | ⬜ pending |
| 70-01-02 | 01 | 1 | UI-DRILL-01 | — | N/A | unit | `npx jest --testPathPattern transfer-table` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual token fidelity (colors, spacing, glow) | UI-DRILL-01 | CSS token values require visual comparison against mockup | Open dashboard, compare each filter state against /tmp/filter-mockup.html |
| Chevron rotation animation | UI-DRILL-01 | CSS transition timing is visual | Click Active/Errors, verify chevron rotates smoothly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
