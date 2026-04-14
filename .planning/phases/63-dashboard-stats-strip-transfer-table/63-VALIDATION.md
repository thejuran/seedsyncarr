---
phase: 63
slug: dashboard-stats-strip-transfer-table
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 63 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest 29.x (Angular TestBed) |
| **Config file** | jest.config.js |
| **Quick run command** | `npx jest --testPathPattern="dashboard" --bail` |
| **Full suite command** | `npx jest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npx jest --testPathPattern="dashboard" --bail`
- **After every plan wave:** Run `npx jest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 63-01-01 | 01 | 1 | DASH-01 | — | N/A | unit | `npx jest --testPathPattern="stat-card"` | ❌ W0 | ⬜ pending |
| 63-01-02 | 01 | 1 | DASH-02 | — | N/A | unit | `npx jest --testPathPattern="stat-card"` | ❌ W0 | ⬜ pending |
| 63-01-03 | 01 | 1 | DASH-03 | — | N/A | unit | `npx jest --testPathPattern="stat-card"` | ❌ W0 | ⬜ pending |
| 63-02-01 | 02 | 1 | DASH-04 | — | N/A | unit | `npx jest --testPathPattern="transfer-table"` | ❌ W0 | ⬜ pending |
| 63-02-02 | 02 | 1 | DASH-05 | — | N/A | unit | `npx jest --testPathPattern="transfer-table"` | ❌ W0 | ⬜ pending |
| 63-02-03 | 02 | 1 | DASH-06 | — | N/A | unit | `npx jest --testPathPattern="transfer-table"` | ❌ W0 | ⬜ pending |
| 63-02-04 | 02 | 1 | DASH-07 | — | N/A | unit | `npx jest --testPathPattern="transfer-table"` | ❌ W0 | ⬜ pending |
| 63-02-05 | 02 | 1 | DASH-08 | — | N/A | unit | `npx jest --testPathPattern="transfer-table"` | ❌ W0 | ⬜ pending |
| 63-02-06 | 02 | 1 | DASH-09 | — | N/A | unit | `npx jest --testPathPattern="transfer-table"` | ❌ W0 | ⬜ pending |
| 63-02-07 | 02 | 1 | DASH-10 | — | N/A | unit | `npx jest --testPathPattern="transfer-table"` | ❌ W0 | ⬜ pending |
| 63-02-08 | 02 | 1 | DASH-11 | — | N/A | unit | `npx jest --testPathPattern="transfer-table"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/app/dashboard/stat-card/stat-card.component.spec.ts` — stubs for DASH-01, DASH-02, DASH-03
- [ ] `src/app/dashboard/transfer-table/transfer-table.component.spec.ts` — stubs for DASH-04 through DASH-11

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Animated striped progress bars | DASH-09 | CSS animation not testable in JSDOM | Inspect in browser: bars should animate left-to-right |
| Responsive 4-card grid layout | DASH-01 | Layout breakpoints need visual check | Resize browser from 1920px to 375px, verify cards stack |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
