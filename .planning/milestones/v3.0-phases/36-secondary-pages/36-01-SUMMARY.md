---
phase: 36-secondary-pages
plan: 01
subsystem: ui
tags: [angular, scss, bootstrap, fira-code, terminal-aesthetic]

# Dependency graph
requires:
  - phase: 35-dashboard
    provides: Ghost button pattern (btn-outline-* + glow) and terminal aesthetic established in dashboard

provides:
  - Terminal-format --- Name --- card headers in green Fira Code for Settings page
  - Muted gray Fira Code subsection headers (Sonarr, Radarr, Webhook URLs)
  - Removed Appearance card and all ThemeService dead code from Settings
  - Ghost outline buttons (btn-outline-danger/success + ghost-btn) for AutoQueue
  - Green glow / red glow hover effects on AutoQueue buttons
  - Fira Code for AutoQueue pattern text
  - Terminal > prefix on AutoQueue description text

affects: [37-theme-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ".btn.terminal-header for card section headers with --- Name --- format and #3fb950 green Fira Code"
    - "ghost-btn SCSS class for outline buttons with color-specific box-shadow glow on hover"
    - "#description::before with content '> ' for terminal prefix on description text"

key-files:
  created: []
  modified:
    - src/angular/src/app/pages/settings/settings-page.component.html
    - src/angular/src/app/pages/settings/settings-page.component.scss
    - src/angular/src/app/pages/settings/settings-page.component.ts
    - src/angular/src/app/pages/autoqueue/autoqueue-page.component.html
    - src/angular/src/app/pages/autoqueue/autoqueue-page.component.scss

key-decisions:
  - "color: #8b949e direct hex for subsection headers — consistent with Phase 33-35 terminal palette, not var(--bs-secondary) which may drift"
  - ".btn.terminal-header scoped selector for card headers — prevents conflict with other .btn usages in the page (e.g. test connection buttons)"
  - "ghost-btn added as sibling inside #controls block in SCSS — consistent with Phase 35 dashboard ghost-btn placement pattern"

patterns-established:
  - "Terminal header pattern: .btn.terminal-header with --- {{header}} --- text, #3fb950 color, var(--bs-font-monospace)"
  - "Ghost button glow pattern: .ghost-btn with color-specific hover box-shadow, reused from Phase 35 dashboard"

requirements-completed:
  - PAGE-01
  - PAGE-02

# Metrics
duration: 12min
completed: 2026-02-17
---

# Phase 36 Plan 01: Secondary Pages — Settings & AutoQueue Terminal Styling Summary

**Terminal-format --- Name --- headers in green Fira Code on Settings, dead Appearance card and ThemeService removed, AutoQueue ghost outline buttons with hover glow, pattern text upgraded to Fira Code with terminal > prefix**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-02-17T17:50:00Z
- **Completed:** 2026-02-17T18:01:54Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Settings card headers display as `--- Server ---`, `--- AutoQueue ---`, `--- *arr Integration ---`, etc. in green (#3fb950) Fira Code monospace via `.btn.terminal-header`
- Subsection headers (Sonarr, Radarr, Webhook URLs) display in muted gray (#8b949e) Fira Code
- Entire Appearance card removed from Settings HTML along with ThemeService/ThemeMode imports, `_themeService`/`theme`/`resolvedTheme` properties, `onSetTheme()` method, and dead SCSS blocks (`.theme-description`, `.theme-toggle`, `.theme-status`, responsive media query)
- AutoQueue remove button changed to `btn-outline-danger ghost-btn` with red glow on hover
- AutoQueue add button changed to `btn-outline-success ghost-btn` with green glow on hover
- AutoQueue pattern text uses `var(--bs-font-monospace)` (upgraded from generic `monospace`)
- AutoQueue description text has Fira Code, muted gray color, and terminal `>` prefix via `::before`

## Task Commits

Each task was committed atomically:

1. **Task 1: Terminal-style Settings headers and remove Appearance card** - `b7fdff1` (feat)
2. **Task 2: AutoQueue ghost buttons, Fira Code patterns, and terminal description** - `0bdeef5` (feat)

## Files Created/Modified
- `src/angular/src/app/pages/settings/settings-page.component.html` - Added terminal-header class + --- format to all card headers, removed Appearance card block
- `src/angular/src/app/pages/settings/settings-page.component.scss` - .btn.terminal-header with green Fira Code, subsection-header with #8b949e Fira Code, removed dead theme SCSS blocks
- `src/angular/src/app/pages/settings/settings-page.component.ts` - Removed ThemeService/ThemeMode imports, removed three ThemeService properties, removed onSetTheme method
- `src/angular/src/app/pages/autoqueue/autoqueue-page.component.html` - btn-danger → btn-outline-danger ghost-btn, btn-success → btn-outline-success ghost-btn
- `src/angular/src/app/pages/autoqueue/autoqueue-page.component.scss` - .ghost-btn glow effects, #description terminal prefix, .pattern .text Fira Code upgrade

## Decisions Made
- `color: #8b949e` direct hex for subsection headers — consistent with Phase 33-35 terminal palette, not `var(--bs-secondary)` which may drift
- `.btn.terminal-header` scoped selector for card headers — prevents conflict with other `.btn` usages in the page (e.g. test connection buttons)
- `ghost-btn` added as sibling inside `#controls` block in SCSS — consistent with Phase 35 dashboard ghost-btn placement pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. Build succeeded with zero errors on both task verifications. All 6 plan verification criteria confirmed passing.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Settings and AutoQueue terminal aesthetic complete; visual consistency across all secondary pages achieved
- Phase 36 Plan 02 (remaining secondary pages) can proceed
- Phase 37 (Theme Cleanup) will have a clean ThemeService state — the Settings page no longer references ThemeService at all

---
*Phase: 36-secondary-pages*
*Completed: 2026-02-17*
