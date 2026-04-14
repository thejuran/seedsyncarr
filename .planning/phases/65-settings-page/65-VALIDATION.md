---
phase: 65
slug: settings-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 65 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Angular TestBed (Karma/Jasmine) |
| **Config file** | `src/angular/karma.conf.js` |
| **Quick run command** | `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless` |
| **Full suite command** | `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless --code-coverage` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless`
- **After every plan wave:** Run `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless --code-coverage`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 65-01-01 | 01 | 1 | SETT-01 | — | N/A | visual | Manual browser check — two-column layout on desktop | N/A | ⬜ pending |
| 65-01-02 | 01 | 1 | SETT-02 | — | N/A | visual | Manual browser check — 10 card sections with icon headers | N/A | ⬜ pending |
| 65-01-03 | 01 | 1 | SETT-03 | — | N/A | unit | `npx ng test --watch=false` — toggle component renders switch | ❌ W0 | ⬜ pending |
| 65-01-04 | 01 | 1 | SETT-04 | — | N/A | visual | Manual browser check — AutoQueue inline CRUD | N/A | ⬜ pending |
| 65-01-05 | 01 | 1 | SETT-05 | — | N/A | unit | `npx ng test --watch=false` — webhook copy button triggers clipboard | ❌ W0 | ⬜ pending |
| 65-01-06 | 01 | 1 | SETT-06 | — | N/A | visual | Manual browser check — floating save bar position and behavior | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Toggle switch component unit test stubs for SETT-03
- [ ] Clipboard copy unit test stubs for SETT-05

*Existing infrastructure covers remaining phase requirements via visual/manual verification.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Two-column masonry layout on desktop | SETT-01 | CSS layout requires visual viewport check | Open settings page at 1200px+ width, confirm two columns with card borders |
| 10 card sections with icon headers | SETT-02 | Visual icon rendering | Open settings page, count all card sections, verify FA icons in headers |
| AutoQueue inline CRUD | SETT-04 | Interactive add/remove requires browser | Add pattern, verify it appears; remove pattern, verify it disappears |
| Floating save bar position | SETT-06 | CSS fixed positioning requires visual check | Make a change, confirm bar appears bottom-right; save, confirm "saved" state |
| Sonarr/Radarr brand colors | SETT-05 | Color accuracy requires visual check | Compare Sonarr card blue (#00c2ff) and Radarr card gold (#ffc230) to mockup |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
