---
phase: 65
slug: settings-page
status: draft
nyquist_compliant: true
wave_0_complete: true
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
| 65-01-00 | 01 | 1 | Nyquist | — | N/A | unit | `npx ng test --watch=false --include='**/settings/**/*.spec.ts'` — test stubs created | Wave 0 | ⬜ pending |
| 65-01-01 | 01 | 1 | SETT-01 | — | N/A | visual + build | `npx ng build --configuration=development` — two-column layout on desktop | N/A | ⬜ pending |
| 65-01-02 | 01 | 1 | SETT-02 | — | N/A | visual + build | `npx ng build --configuration=development` — 10 card sections with icon headers | N/A | ⬜ pending |
| 65-01-03 | 01 | 1 | SETT-03 | — | N/A | unit | `npx ng test --watch=false --include='**/settings/**/*.spec.ts'` — toggle component renders switch | ✅ W0 | ⬜ pending |
| 65-01-04 | 01 | 1 | SETT-04 | — | N/A | visual + build | `npx ng build --configuration=development` — AutoQueue inline CRUD preserved | N/A | ⬜ pending |
| 65-02-01 | 02 | 2 | SETT-04, SETT-05 | T-65-03 | N/A | unit + build | `npx ng build --configuration=development` — brand cards, webhook copy, AUTODELETE inline template | N/A | ⬜ pending |
| 65-02-02 | 02 | 2 | SETT-06 | T-65-04 | N/A | visual + build | `npx ng build --configuration=development` — floating save bar position and behavior | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Toggle switch component unit test stubs for SETT-03 — created in Plan 01 Task 0 (`option.component.spec.ts`)
- [x] Settings page component creation test — created in Plan 01 Task 0 (`settings-page.component.spec.ts`)

*Wave 0 test stubs are created as the first task in Plan 01, before template changes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Two-column masonry layout on desktop | SETT-01 | CSS layout requires visual viewport check | Open settings page at 1200px+ width, confirm two columns with card borders |
| 10 card sections with icon headers | SETT-02 | Visual icon rendering | Open settings page, count all card sections, verify FA icons in headers |
| Compact toggles in inline contexts | SETT-03/D-03 | Size comparison requires visual check | Compare inline toggles (SSH Key, Use Temp File) to primary toggles — compact should be visibly smaller |
| AutoQueue inline CRUD | SETT-04 | Interactive add/remove requires browser | Add pattern, verify it appears; remove pattern, verify it disappears |
| Floating save bar position | SETT-06 | CSS fixed positioning requires visual check | Make a change, confirm bar appears bottom-right; save, confirm "saved" state |
| Sonarr/Radarr brand colors | D-09/D-10 | Color accuracy requires visual check | Compare Sonarr card blue (#00c2ff) and Radarr card gold (#ffc230) to mockup |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
