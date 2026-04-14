---
phase: 62
slug: nav-bar-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 62 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Karma + Jasmine |
| **Config file** | `src/angular/karma.conf.js` |
| **Quick run command** | `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI --include=**/app.component.spec.ts` |
| **Full suite command** | `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI --include=**/app.component.spec.ts`
- **After every plan wave:** Run `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 62-01-01 | 01 | 0 | NAV-03, NAV-04 | — | N/A | unit | `ng test --include=**/app.component.spec.ts` | ❌ W0 | ⬜ pending |
| 62-02-01 | 02 | 1 | NAV-01 | — | N/A | visual/manual | Manual browser inspection | ❌ Not applicable | ⬜ pending |
| 62-02-02 | 02 | 1 | NAV-02 | — | N/A | visual/manual | Manual browser inspection | ❌ Not applicable | ⬜ pending |
| 62-03-01 | 03 | 1 | NAV-03 | — | N/A | unit | `ng test --include=**/app.component.spec.ts` | ❌ W0 | ⬜ pending |
| 62-04-01 | 04 | 2 | NAV-04 | — | N/A | unit | `ng test --include=**/app.component.spec.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/angular/src/app/pages/main/app.component.spec.ts` — stubs for NAV-03 (connected badge state) and NAV-04 (bell badge presence)
- [ ] Test `connected$` Observable binding and `notifications$` size-to-badge logic

*Existing Karma + Jasmine infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Nav backdrop-filter CSS applied | NAV-01 | CSS visual effect — unit tests cannot assert rendered pixel-level CSS | Open app in browser, scroll page content behind nav, verify blur effect visible |
| Active link `::after` amber underline | NAV-02 | CSS-only pseudo-element — not testable via unit tests | Navigate between pages, verify amber underline appears on active link and fades on transition |
| Connection badge pulse animation | NAV-03 | Animation keyframes — visual verification needed | With server running, verify green pulsing dot; stop server, verify red static dot |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
