---
phase: 90
slug: angular-test-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 90 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Karma 6.4.4 + Jasmine 6.2.0 |
| **Config file** | `src/angular/karma.conf.js` |
| **Quick run command** | `cd src/angular && ng test --watch=false` |
| **Full suite command** | `cd src/angular && ng test --watch=false` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src/angular && ng test --watch=false`
- **After every plan wave:** Run `cd src/angular && ng test --watch=false`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 90-01-01 | 01 | 1 | ANGFIX-01 | — | N/A | unit | `cd src/angular && ng test --watch=false` | ✅ | ⬜ pending |
| 90-01-02 | 01 | 1 | ANGFIX-02 | — | N/A | unit | `cd src/angular && ng test --watch=false` | ✅ | ⬜ pending |
| 90-01-03 | 01 | 1 | ANGFIX-07 | — | N/A | unit | `cd src/angular && ng test --watch=false` | ✅ | ⬜ pending |
| 90-02-01 | 02 | 1 | ANGFIX-03 | — | N/A | unit | `cd src/angular && ng test --watch=false` | ✅ | ⬜ pending |
| 90-02-02 | 02 | 1 | ANGFIX-04 | — | N/A | unit | `cd src/angular && ng test --watch=false` | ✅ | ⬜ pending |
| 90-02-03 | 02 | 1 | ANGFIX-05 | — | N/A | unit | `cd src/angular && ng test --watch=false` | ✅ | ⬜ pending |
| 90-02-04 | 02 | 1 | ANGFIX-06 | — | N/A | unit | `cd src/angular && ng test --watch=false` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
