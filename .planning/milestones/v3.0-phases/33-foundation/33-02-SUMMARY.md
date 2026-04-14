---
phase: 33-foundation
plan: 02
subsystem: ui
tags: [scss, bootstrap, css-custom-properties, terminal-palette, crt-effect, scrollbars, keyframes]

# Dependency graph
requires:
  - phase: 33-01
    provides: Terminal SCSS variables (_bootstrap-variables.scss) and dark-only index.html

provides:
  - Single :root Terminal palette CSS custom properties (--app-*) consumed by all components
  - Dark-only Bootstrap component overrides (dropdown, form-control) without [data-bs-theme] guards
  - CRT scan-line overlay via body::after
  - Custom Webkit and Firefox scrollbars (thin, green hover)
  - cursor-blink and green-pulse @keyframes
  - glow-green, text-terminal, cursor-blink utility classes

affects: [34-shell, 35-dashboard, 36-secondary-pages, 37-theme-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dark-only CSS: all component overrides written as direct rules, no [data-bs-theme] guards"
    - "Single :root palette: all var(--app-*) defined once, no light/dark branching"
    - "Terminal effects in global stylesheet: CRT overlay, keyframes, utility classes"

key-files:
  created: []
  modified:
    - src/angular/src/app/common/_bootstrap-overrides.scss
    - src/angular/src/styles.scss

key-decisions:
  - "Use hardcoded hex values in _bootstrap-overrides.scss for dropdown/form instead of SCSS variable interpolation — old variables don't map to new palette semantics"
  - "CRT scan-line overlay uses z-index 9999 with pointer-events:none — must float above all content without blocking interaction"
  - "Custom scrollbar opacity 0.03 for CRT lines — subtle enough not to impede readability"

patterns-established:
  - "Terminal palette: #0d1117 body bg, #161b22 surface, #30363d border, #3fb950 accent green, #238636 hover green, #e6edf3 text, #8b949e muted text"

requirements-completed: [VIS-03, VIS-04, VIS-05]

# Metrics
duration: 6min
completed: 2026-02-17
---

# Phase 33 Plan 02: Terminal CSS Custom Properties + CRT Overlay Summary

**Single dark-only :root palette replacing dual light/dark CSS vars, with CRT scan-line overlay, custom green scrollbars, and animation keyframes for phases 34-36**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-17T04:27:23Z
- **Completed:** 2026-02-17T04:33:26Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Removed all `[data-bs-theme="dark"]` guards from `_bootstrap-overrides.scss` — component overrides now apply unconditionally
- Replaced dual light/dark `--app-*` variable blocks in `styles.scss` with a single `:root` Terminal palette block
- Added CRT scan-line overlay (`body::after`, `pointer-events: none`, `z-index: 9999`) for the signature terminal aesthetic
- Added custom scrollbars (Webkit 8px with green hover, Firefox `scrollbar-color`/`scrollbar-width: thin`)
- Added `cursor-blink` and `green-pulse` `@keyframes` and utility classes for phases 34-36 to use

## Task Commits

Each task was committed atomically:

1. **Task 1: Dark-Only Overrides + Custom Scrollbars** - `42d75b0` (feat)
2. **Task 2: Terminal CSS Custom Properties + CRT Overlay + Keyframes** - `29e7d5d` (feat)

## Files Created/Modified

- `src/angular/src/app/common/_bootstrap-overrides.scss` - Removed [data-bs-theme="dark"] guards; rewrote dropdown/form overrides with Terminal palette hex values; added Webkit + Firefox custom scrollbar rules
- `src/angular/src/styles.scss` - Updated font-family to IBM Plex Sans; replaced dual light/dark --app-* blocks with single :root Terminal palette; added Section 6 with CRT overlay, keyframes, utility classes

## Decisions Made

- Used hardcoded hex values in `_bootstrap-overrides.scss` for dropdown/form overrides instead of SCSS variable interpolation. The old variables (`$primary-color` etc.) don't map to the new Terminal palette semantics, so direct hex is cleaner and more explicit.
- CRT overlay uses `z-index: 9999` with `pointer-events: none` so it floats above all UI layers without blocking clicks.
- Scan-line opacity set to `0.03` — barely perceptible at normal viewing distance, adds texture without reducing legibility.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Angular CLI binary was at `node_modules/.bin/ng` rather than `node_modules/@angular/cli/bin/ng` as specified in the plan's verify step. This is a shell environment path difference (not a project issue) — resolved immediately.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All `var(--app-*)` custom properties are now defined in their final Terminal palette values
- Component SCSS files that consume `var(--app-*)` will automatically inherit the new palette without changes
- CRT overlay is globally active
- Animation keyframes and utility classes are available for Phase 34 (Shell)
- Phase 37 (Theme Cleanup) can now safely remove ThemeService — no runtime `[data-bs-theme]` switching remains in CSS

---
*Phase: 33-foundation*
*Completed: 2026-02-17*
