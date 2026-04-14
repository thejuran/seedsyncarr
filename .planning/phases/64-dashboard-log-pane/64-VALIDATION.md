---
phase: 64
slug: dashboard-log-pane
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 64 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Karma + Jasmine (Angular 21) |
| **Config file** | `src/angular/karma.conf.js` |
| **Quick run command** | `npx ng test --watch=false --browsers=ChromeHeadless` |
| **Full suite command** | `npx ng test --watch=false --browsers=ChromeHeadless` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `npx ng test --watch=false --browsers=ChromeHeadless`
- **After every plan wave:** Run `npx ng test --watch=false --browsers=ChromeHeadless && npx ng build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 64-01-01 | 01 | 1 | DASH-12 | — | N/A | unit | `npx ng test` | ❌ W0 | ⬜ pending |
| 64-01-02 | 01 | 1 | DASH-13 | — | N/A | unit | `npx ng test` | ❌ W0 | ⬜ pending |
| 64-01-03 | 01 | 1 | DASH-14 | — | N/A | unit | `npx ng test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/angular/src/app/tests/unittests/pages/files/dashboard-log-pane.component.spec.ts` — stubs for DASH-12, DASH-13, DASH-14

*Existing test infrastructure covers framework — only component spec needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual match to design spec | DASH-12 | CSS rendering comparison | Screenshot at 1440x900 and compare to design.html |
| Level colors correct | DASH-14 | Visual verification | Verify INFO=green, WARN=amber, ERROR=red in browser |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
