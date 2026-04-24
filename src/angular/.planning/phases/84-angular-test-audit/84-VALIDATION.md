---
phase: 84
slug: angular-test-audit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 84 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Karma + Jasmine 5.1.0 (Angular 21) |
| **Config file** | `src/angular/karma.conf.js` |
| **Quick run command** | `node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false` |
| **Full suite command** | `node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false --code-coverage` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false`
- **After every plan wave:** Run `node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false --code-coverage`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 84-01-01 | 01 | 1 | NG-01 | — | N/A | integration | `ng test --watch=false` | ✅ | ⬜ pending |
| 84-01-02 | 01 | 1 | NG-01 | — | N/A | integration | `ng test --watch=false` | ✅ | ⬜ pending |
| 84-01-03 | 01 | 1 | NG-02 | — | N/A | integration | `ng test --watch=false` | ✅ | ⬜ pending |
| 84-01-04 | 01 | 1 | NG-03 | — | N/A | integration | `ng test --watch=false --code-coverage` | ✅ | ⬜ pending |

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
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
