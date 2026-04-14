---
phase: 66
slug: logs-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 66 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Karma + Jasmine (Angular 21) |
| **Config file** | `src/angular/karma.conf.js` |
| **Quick run command** | `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless` |
| **Full suite command** | `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless`
- **After every plan wave:** Run `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 66-01-01 | 01 | 1 | LOGS-01 | — | N/A | manual | Visual inspection of segmented button group | N/A | ⬜ pending |
| 66-01-02 | 01 | 1 | LOGS-02 | T-66-01 | Regex input sanitized before use | unit | `ng test --include=**/logs*` | ❌ W0 | ⬜ pending |
| 66-01-03 | 01 | 1 | LOGS-03 | — | N/A | manual | Auto-scroll toggle, clear, export buttons functional | N/A | ⬜ pending |
| 66-01-04 | 01 | 1 | LOGS-04 | — | N/A | manual | Status bar shows connection status, count, timestamp | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements. Angular test framework already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Segmented button group filters log entries | LOGS-01 | Visual UI interaction | Click each level button, verify filtered display |
| Regex search filters in real time | LOGS-02 | Visual + regex behavior | Type regex patterns, verify matching entries shown |
| Auto-scroll toggle behavior | LOGS-03 | Scroll interaction | Toggle auto-scroll, verify behavior on new logs |
| Clear button resets display | LOGS-03 | Visual state reset | Click clear, verify logs removed and line counter resets |
| Export downloads .log file | LOGS-03 | Browser download trigger | Click export, verify file downloads with correct format |
| Status bar live updates | LOGS-04 | Real-time data display | Observe status bar during active log streaming |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
