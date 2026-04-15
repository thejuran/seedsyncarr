---
phase: 68-ui-polish
plan: "01"
subsystem: frontend/scss
tags: [scss, palette, refactor, tech-debt, nav-bar, version]
dependency_graph:
  requires: []
  provides: [palette-consolidated-settings, palette-consolidated-logs, brand-favicon-nav, version-check-shared-import]
  affects: [settings-page, logs-page, app-nav-bar, version-check-service]
tech_stack:
  added: []
  patterns: [scss-palette-aliases, shared-version-import]
key_files:
  created: []
  modified:
    - src/angular/src/app/pages/settings/settings-page.component.scss
    - src/angular/src/app/pages/logs/logs-page.component.scss
    - src/angular/src/app/pages/main/app.component.html
    - src/angular/src/app/pages/main/app.component.scss
    - src/angular/src/app/services/utils/version-check.service.ts
decisions:
  - "Local $success/$danger/$check-green defined in settings SCSS — not promoted to shared palette as they are page-semantic, not forest-palette"
  - "Sonarr/Radarr brand hex values preserved with identity comments — external app brand colors must not be aliased"
  - "font-icon-only CSS properties (color, font-size) removed from .brand-icon-box — image centering handled by existing flex layout"
metrics:
  duration_minutes: 8
  completed_date: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 68 Plan 01: UI Polish — SCSS Palette Consolidation & Brand Favicon Summary

SCSS palette drift eliminated in settings and logs pages, nav bar brand icon replaced with favicon-192.png, and version-check.service.ts migrated to shared APP_VERSION import.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Consolidate SCSS palette drift in settings and logs | 2e9773d | settings-page.component.scss, logs-page.component.scss |
| 2 | Replace nav bar brand icon with favicon, migrate version-check | 8d68e7a | app.component.html, app.component.scss, version-check.service.ts |

## What Was Built

**Task 1 — SCSS palette consolidation:**
- `settings-page.component.scss`: All 6 forest palette hex values (`#1a2019`, `#2c3629`, `#3e4a38`, `#151a14`, `#9aaa8a`, `#c49a4a`) replaced with shared aliases (`$row`, `$muted`, `$border`, `$base`, `$textsec`, `$amber`). Also replaced `rgba(hex, alpha)` patterns with `rgba($alias, alpha)` for option-separator, toggle, btn-save-settings, and btn-regenerate.
- Local semantic vars `$success`, `$danger`, `$check-green` added at top of settings SCSS for page-specific repeated colors.
- Sonarr and Radarr brand hex values preserved with explanatory comments ("external app identity, not forest palette").
- `logs-page.component.scss`: `#ff8e8e` replaced with `lighten($error, 20%)` in `.log-msg--error`. Documentation comment added above local vars block.

**Task 2 — Nav bar favicon + version import:**
- `app.component.html`: `<i class="fa fa-exchange">` replaced with `<img src="assets/favicon-192.png" alt="SeedSyncarr" class="brand-favicon">` inside `.brand-icon-box`.
- `app.component.scss`: Added `.brand-favicon { width: 20px; height: 20px; object-fit: contain; }`. Removed `color: #c49a4a` and `font-size: 1rem` from `.brand-icon-box` (font-icon-only properties). Existing flex centering handles image alignment.
- `version-check.service.ts`: Removed `declare function require` + `require("package.json")` pattern. Added `import { APP_VERSION } from "../../common/version"`. Replaced `appVersion` with `APP_VERSION` in `isVersionNewer`.

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Forest hex in settings SCSS | `grep -c '#1a2019\|...' settings-page.component.scss` | 0 |
| #ff8e8e in logs SCSS | `grep -c '#ff8e8e' logs-page.component.scss` | 0 |
| brand-favicon in HTML | `grep -c 'brand-favicon' app.component.html` | 1 |
| APP_VERSION in service | `grep -c 'APP_VERSION' version-check.service.ts` | 2 |
| declare-require outside version.ts | `grep -rn 'declare function require' src/app/ \| grep -vc 'common/version.ts'` | 0 |

Note: `npx ng build --configuration=production` shows a pre-existing TS2531 error in `transfer-table.component.html:67` that exists on the base commit (7b78b71) — confirmed out of scope. SCSS compilation itself succeeds (only pre-existing Bootstrap `@import` Sass deprecation warnings present).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — pure CSS refactor and local asset swap. No new network endpoints, auth paths, or data flows introduced.

## Self-Check: PASSED

- `src/angular/src/app/pages/settings/settings-page.component.scss` — exists, modified
- `src/angular/src/app/pages/logs/logs-page.component.scss` — exists, modified
- `src/angular/src/app/pages/main/app.component.html` — exists, modified
- `src/angular/src/app/pages/main/app.component.scss` — exists, modified
- `src/angular/src/app/services/utils/version-check.service.ts` — exists, modified
- Commit 2e9773d — confirmed in git log
- Commit 8d68e7a — confirmed in git log
