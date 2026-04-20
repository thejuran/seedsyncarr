---
phase: 72-restore-dashboard-file-selection-and-action-bar
plan: 01
subsystem: ui
tags: [angular, scss, bulk-actions, font-awesome, variant-b, dark-theme]

# Dependency graph
requires: []
provides:
  - "BulkActionsBarComponent template: Variant B literal port with 5 action buttons, btn-divider, selection label"
  - "BulkActionsBarComponent SCSS: literal hex palette (#252e23 band, #d4a574 amber, #c97d7d red, no Bootstrap tokens)"
  - "bulk-actions-bar spec: 4 new Variant B DOM contract it() blocks alongside all 29 original passing specs"
affects:
  - "72-04 — transfer-table wiring: uses BulkActionsBarComponent with unchanged @Input/@Output contract"
  - "72-05 — E2E plan: selectors .bulk-actions-bar, .selection-label, button.action-btn, .btn-divider, .action-queue, .action-danger, .action-neutral"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Variant B literal hex port: all palette values (#252e23, rgba(212,165,116,0.3), etc.) written directly in SCSS — no CSS custom properties, no Bootstrap semantic tokens"
    - "Sanctioned Phosphor→FA4.7 mapping: ph-play→fa-play, ph-stop→fa-stop, ph-archive→fa-file-archive-o, ph-trash→fa-trash, ph-cloud-slash→fa-cloud+fa-ban.action-overlay (stacked)"
    - "componentRef.setInput() for OnPush DOM tests: needed to mark OnPush component dirty before fixture.detectChanges() for @if control flow to render"

key-files:
  created: []
  modified:
    - src/angular/src/app/pages/files/bulk-actions-bar.component.html
    - src/angular/src/app/pages/files/bulk-actions-bar.component.scss
    - src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts

key-decisions:
  - "D-13: Adapt orphaned BulkActionsBarComponent in place — keep .ts contract, rewrite template+SCSS only"
  - "D-14: Existing spec is the regression anchor — all 29 original specs still pass; 4 new DOM specs added"
  - "Stacked-glyph Delete Remote icon: fa-cloud + fa-ban.action-overlay — only sanctioned deviation (no fa-cloud-slash in FA4.7)"
  - "componentRef.setInput() required for OnPush DOM tests — direct property assignment does not mark component dirty for @if re-evaluation"

patterns-established:
  - "OnPush DOM tests: use fixture.componentRef.setInput() then call ngOnChanges manually then fixture.detectChanges() — direct property assignment skips dirty-marking in Angular 21"

requirements-completed: []

# Metrics
duration: 25min
completed: 2026-04-19
---

# Phase 72 Plan 01: Bulk Actions Bar Variant B Port Summary

**Variant B card-internal action bar ported literally into BulkActionsBarComponent — amber Queue fill, red-outline Stop/Delete danger buttons, neutral Extract, stacked fa-cloud+fa-ban Delete Remote icon, zero Bootstrap semantic tokens, 33/33 specs green**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-19T21:30:00Z
- **Completed:** 2026-04-19T21:55:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Rewrote `bulk-actions-bar.component.html` to Variant B literal port: `{{ selectedCount }} selected` label, 5 action buttons in Queue/Stop/Extract/|/Delete Local/Delete Remote order, FA4.7 icons, no Bootstrap semantic classes
- Rewrote `bulk-actions-bar.component.scss` with every literal hex/rgba value from the Variant B palette (#252e23 band, rgba(212,165,116,0.3) amber divider, inset shadow, #d4a574 Queue fill, #c97d7d danger text/border, action-overlay for stacked Delete Remote icon)
- Added 4 new `describe("Variant B DOM contract")` specs asserting button count/order, divider placement, selection label format, and absence of count suffixes — all 33 specs pass, D-14 regression anchor preserved

## CSS Class Surface (for plan 05 E2E selectors)

| Class | Element | Purpose |
|-------|---------|---------|
| `.bulk-actions-bar` | outer `<div>` | bar container, guarded by `@if (hasSelection)` |
| `.bar-left` | left group `<div>` | selection label + clear button |
| `.selection-label` | `<span>` | "N selected" amber label |
| `.clear-btn` | `<button>` | underlined clear link |
| `.actions` | right group `<div>` | button row |
| `.action-btn` | all action `<button>` | shared button base class |
| `.action-queue` | Queue `<button>` | amber-filled primary variant |
| `.action-danger` | Stop, Delete Local, Delete Remote `<button>` | red-outline variant |
| `.action-neutral` | Extract `<button>` | dim neutral variant (disabled appearance) |
| `.btn-divider` | `<div>` | 1px × 20px #2d3a2d vertical divider |
| `.action-overlay` | `<i class="fa fa-ban">` | stacked ban glyph over cloud for Delete Remote |
| `.progress-indicator` | `<span>` (inside `.actions`) | shown only when `operationInProgress` |

## Icon mapping

### Sanctioned Phosphor → FA4.7 icon mapping (all 5 action buttons)

Per CONTEXT.md line 87: "text-only UI — Variant B uses Phosphor icons in small roles, map to equivalent Font Awesome 4.7 glyphs per memory." This plan honors that sanctioned mapping rule for all 5 icons.

**Single-glyph mappings (4 of 5 buttons):**

| Button | Phosphor (Variant B) | FA4.7 equivalent | Class used |
|--------|---------------------|------------------|------------|
| Queue | `ph-play` | `fa-play` | `fa fa-play` |
| Stop | `ph-stop` | `fa-stop` | `fa fa-stop` |
| Extract | `ph-archive` | `fa-file-archive-o` | `fa fa-file-archive-o` |
| Delete Local | `ph-trash` | `fa-trash` | `fa fa-trash` |

**Stacked-glyph construction (Delete Remote only — the sole sanctioned Phosphor deviation):**

Phosphor ships `ph-cloud-slash` as a single-glyph "cloud with strike-through" icon. FA 4.7 has NO equivalent single-glyph — no `fa-cloud-slash`, no `fa-cloud-off`. The closest approximation is stacking `<i class="fa fa-cloud">` + `<i class="fa fa-ban action-overlay">` where the `.action-overlay` class positions the ban glyph over the cloud via `margin-left: -0.9em` (SCSS `.action-overlay` rule). This is NOT a palette deviation (the hex values remain Variant B literal — `#c97d7d` status-red for the ban overlay color) — only the icon family is mapped, which the CONTEXT.md rule explicitly permits.

This fallback applies ONLY to the Delete Remote button. The other 4 action-button icons each have a direct single-glyph FA4.7 equivalent — no stacking, no approximation.

All palette hex values, paddings, gaps, border-radii, font sizes, and class names are ported literally from Variant B — no approximations, no shortcuts.

## Task Commits

1. **Task 1: Rewrite bulk-actions-bar template** — `2a9666c` (feat)
2. **Task 2: Rewrite bulk-actions-bar SCSS** — `fae0837` (feat)
3. **Task 3: Extend spec with Variant B DOM contract** — `92508ec` (test)

## Files Modified

- `src/angular/src/app/pages/files/bulk-actions-bar.component.html` — Variant B literal port: 5 action buttons, FA icons, no Bootstrap classes, terse label wording
- `src/angular/src/app/pages/files/bulk-actions-bar.component.scss` — Full literal hex palette rewrite: #252e23 background, rgba amber divider/shadow, #d4a574/#c97d7d/#6b736a button variants, .action-overlay stacked-glyph rule, responsive media queries
- `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` — 4 new DOM contract specs added (533 lines total, was 466 lines; +67 lines)

## No Bootstrap Semantic Classes Confirmation

`grep -cE "\$primary|\$secondary|\$danger|var\(--app-" bulk-actions-bar.component.scss` returns `0`.
`grep -cE "btn[[:space:]]+btn-sm|btn-primary|btn-danger|btn-outline-danger" bulk-actions-bar.component.html` returns `0`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] OnPush component requires `componentRef.setInput()` for DOM tests**
- **Found during:** Task 3 (Variant B DOM contract specs)
- **Issue:** New DOM tests using `setInputsAndDetectChanges` + `fixture.detectChanges()` returned 0 buttons from `querySelectorAll("button.action-btn")`. Direct property assignment (`component.selectedFiles = ...`) does not mark an `OnPush` component as dirty for Angular 21's `@if` control flow, so the `@if (hasSelection)` block never rendered even after `detectChanges()`.
- **Fix:** Added a `setInputsForDOM` local helper within the new `describe` block that calls `fixture.componentRef.setInput("selectedFiles", ...)` and `fixture.componentRef.setInput("visibleFiles", ...)` before manually calling `ngOnChanges` and `fixture.detectChanges()`. The `setInput()` API properly marks the component dirty. The existing `setInputsAndDetectChanges` helper (used by all 29 original tests) was NOT modified.
- **Files modified:** bulk-actions-bar.component.spec.ts (new describe block only)
- **Verification:** All 33 specs pass (TOTAL: 33 SUCCESS)
- **Committed in:** `92508ec`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug — OnPush DOM rendering in Angular 21 tests)
**Impact on plan:** Required fix for test correctness. No scope creep. Existing spec contract (D-14) fully preserved.

## Issues Encountered

- Angular 21 `@if` control flow with `ChangeDetectionStrategy.OnPush` requires `componentRef.setInput()` for proper dirty-marking in Karma tests. Direct property assignment + `fixture.detectChanges()` alone does not trigger re-render of `@if` blocks.

## Next Phase Readiness

- `BulkActionsBarComponent` is ready to be wired into `TransferTableComponent` in plan 04 — `@Input` / `@Output` contract is unchanged, selector is `app-bulk-actions-bar`
- Plan 05 E2E can reference `.bulk-actions-bar`, `.selection-label`, `button.action-btn`, `.action-queue`, `.action-danger`, `.action-neutral`, `.btn-divider` selectors
- Angular dev build exits 0; all 33 specs pass

## Self-Check: PASSED

- `src/angular/src/app/pages/files/bulk-actions-bar.component.html` — exists, contains Variant B markup
- `src/angular/src/app/pages/files/bulk-actions-bar.component.scss` — exists, contains literal hex palette
- `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` — exists, 533 lines
- Commits: `2a9666c`, `fae0837`, `92508ec` — all present in git log
- `npx ng test` exits 0 with 33 SUCCESS, 0 FAILED
- `npx ng build --configuration=development` exits 0

---
*Phase: 72-restore-dashboard-file-selection-and-action-bar*
*Completed: 2026-04-19*
