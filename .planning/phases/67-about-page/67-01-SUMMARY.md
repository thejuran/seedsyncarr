---
phase: 67-about-page
plan: "01"
subsystem: angular-ui
tags: [angular, about-page, scss, unit-tests, ui-redesign]
dependency_graph:
  requires: []
  provides: [about-page-component-v2]
  affects: [src/angular/src/app/pages/about]
tech_stack:
  added: []
  patterns: [fade-in-up-animation, card-section-layout, sysinfo-div-table, link-cards-grid, phosphor-icons]
key_files:
  created:
    - src/angular/src/app/pages/about/about-page.component.spec.ts
  modified:
    - src/angular/src/app/pages/about/about-page.component.ts
    - src/angular/src/app/pages/about/about-page.component.html
    - src/angular/src/app/pages/about/about-page.component.scss
decisions:
  - Used favicon-192.png for identity card icon (higher resolution than favicon.png at 6rem display)
  - Kept fork attribution as separate .fork-note paragraph below copyright line
  - Used HTML entity &#x2014; for em-dash placeholders in sysinfo rows
metrics:
  duration_minutes: 25
  completed_date: "2026-04-14T22:20:14Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 3
requirements:
  - ABUT-01
  - ABUT-02
  - ABUT-03
  - ABUT-04
---

# Phase 67 Plan 01: About Page Component Rewrite Summary

**One-liner:** Full rewrite of AboutPageComponent with 4-section layout (identity card, system info table, link cards grid, license footer) using Deep Moss + Amber palette, pixel-exact mockup values, and 15 passing unit tests covering ABUT-01 through ABUT-04.

## What Was Built

The About page component was completely rewritten across all three component files (TS, HTML, SCSS) plus a new spec file created from scratch:

**TypeScript (`about-page.component.ts`):**
- Added `VERSION` to `@angular/core` import
- Added `public angularVersion: string` property
- Set `this.angularVersion = VERSION.full` in constructor to expose Angular version at build time

**HTML template (`about-page.component.html`):**
- Replaced the old `#about #wrapper` structure with a semantic 4-section layout inside `<main class="about-main">`
- Identity card: `favicon-192.png` in amber-bordered container, "SeedSync**arr**" branded title, tagline, version-badge
- System info table: 7 div-based `sysinfo-row` elements (App Version, Frontend Core with Angular version, 4 em-dash placeholders, Config Path)
- Link cards grid: 4 `<a class="link-card">` elements with Phosphor icons (ph-github-logo, ph-book, ph-bug, ph-git-commit) and correct hrefs
- License footer: Apache License 2.0 badge, copyright line, fork attribution

**SCSS (`about-page.component.scss`):**
- Complete rewrite using literal hex values from the AIDesigner mockup
- `$amber: #c49a4a`, `$text: #e0e8d6`, `$textsec: #9aaa8a`, `$border: #3e4a38`, `$card: #222a20`, etc.
- `fade-in-up` keyframe animation with `cubic-bezier(0.16, 1, 0.3, 1) forwards`
- `.about-main` max-width 42rem centered layout with 2rem gap between sections
- Identity card, sysinfo table, link cards grid, footer — all styled with literal hex values, no Bootstrap utility approximations

**Spec file (`about-page.component.spec.ts`):**
- 15 unit tests covering all 4 ABUT requirements
- ABUT-01: brand title with `.brand-arr` span, version badge, favicon image, tagline
- ABUT-02: 7 sysinfo rows, App Version row, Angular version row, em-dash placeholders, config path
- ABUT-03: 4 link cards, correct hrefs, `target="_blank"` on all cards
- ABUT-04: Apache License 2.0 badge, copyright text with year/names, fork attribution

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite AboutPageComponent TypeScript and create unit test scaffold | 0b0c160 | about-page.component.ts, about-page.component.spec.ts |
| 2 | Rewrite About page HTML template and SCSS with pixel-exact mockup values | 1a38561 | about-page.component.html, about-page.component.scss |

## Verification Results

| Check | Result |
|-------|--------|
| `ng build --configuration=production` | PASS — no errors |
| All 15 unit tests pass | PASS — 15/15 SUCCESS |
| `grep -c 'sysinfo-row' about-page.component.html` | 7 (correct) |
| `grep 'Apache License 2.0' about-page.component.html` | FOUND |
| `grep 'VERSION' about-page.component.ts` | FOUND (import + usage) |
| No Bootstrap utility approximations in SCSS | CONFIRMED |
| Old `#about` and `#wrapper` IDs removed | CONFIRMED |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

The following sysinfo rows intentionally show `—` (em dash) as placeholders per D-02 (no backend endpoint in this phase):
- PYTHON VERSION — deferred to future phase with `/server/status` endpoint
- HOST OS — deferred
- UPTIME — deferred
- PROCESS ID — deferred

These are intentional per the locked decision D-01/D-02 in CONTEXT.md. The config path row (`~/.seedsyncarr`) is a static display value, not a stub.

## Threat Flags

None — this page is fully static with no user input, no API calls, and no new network endpoints.

## Self-Check: PASSED

- `src/angular/src/app/pages/about/about-page.component.ts` — FOUND
- `src/angular/src/app/pages/about/about-page.component.html` — FOUND
- `src/angular/src/app/pages/about/about-page.component.scss` — FOUND
- `src/angular/src/app/pages/about/about-page.component.spec.ts` — FOUND
- Commit `0b0c160` — FOUND (Task 1)
- Commit `1a38561` — FOUND (Task 2)
- 15/15 unit tests PASS
