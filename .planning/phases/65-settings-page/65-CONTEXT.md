# Phase 65: Settings Page - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the existing settings page to Triggarr-level visual polish: two-column masonry layout with card sections, icon headers with dark header bars, pill-shaped toggle switches, inline AutoQueue CRUD, webhook display with copy buttons, Sonarr/Radarr brand-colored cards, and a floating save confirmation bar. All existing functionality (auto-save, pattern CRUD, test connections, webhook URLs, API token) is preserved — this is a visual upgrade only.

</domain>

<decisions>
## Implementation Decisions

### Card Header Icons & Styling
- **D-01:** Pixel-exact match to the AIDesigner spec. Each card gets a dark header bar (`bg-row` / `#1a2019` background with `border-b border-edge`) and an FA 4.7 icon. Map Phosphor icons from mockup to closest FA 4.7 equivalents:
  - General Options → `fa-sliders`
  - Remote Server (LFTP) → `fa-server`
  - File Discovery Polling → `fa-search`
  - Archive Operations → `fa-file-archive-o`
  - LFTP Connection Limits → `fa-tachometer`
  - AutoQueue Engine → `fa-list`
  - Sonarr → `fa-television`
  - Radarr → `fa-film`
  - Post-Import Pruning (Auto-Delete) → `fa-trash`
  - API & Security → `fa-shield`
- **D-02:** Card header text uses uppercase tracking, `text-xs` equivalent size, `font-semibold`, in `text-sec` color — matching the mockup's label treatment.

### Toggle Switch Styling
- **D-03:** Pixel-exact to spec. All boolean settings render as pill-shaped toggle switches instead of plain checkboxes. Match mockup dimensions: `w-9 h-5` for primary toggles, `w-7 h-4` for inline/compact toggles.
- **D-04:** Toggle states: OFF = `bg-muted border-edge` with `text-sec` colored circle. ON = `bg-amber/10 border-amber/50` with amber-colored circle. Focus ring uses `ring-amber/50`.
- **D-05:** Implementation approach is Claude's discretion — pure CSS on existing checkbox or new component, whichever best achieves pixel-exact match.

### Save Behavior & Floating Bar
- **D-06:** Keep the existing auto-save behavior (individual field saves with 1s debounce via `ConfigService.set()`). No batch save migration.
- **D-07:** Add a floating bar at bottom-right matching the mockup design: `bg-card/90 backdrop-blur-xl border-edge` container with "Unsaved Changes" text and amber "Save Settings" button. This bar serves as visual confirmation — it appears when changes are pending (during debounce) and transitions to a "Changes saved" state after the save completes.
- **D-08:** The existing `#commands` section with the "Restart" button is replaced by integrating restart into the floating bar or as a separate action within it.

### Sonarr/Radarr Brand Colors
- **D-09:** Sonarr card uses brand blue: header bg `#1b232e`, border `#2b3a4a`, accent color `#00c2ff`. Left border accent `border-l-2 border-[#00c2ff]/30`. Toggle checked state uses `#00c2ff` instead of amber.
- **D-10:** Radarr card uses brand gold: header bg `#2b2210`, border `#4a3415`, accent color `#ffc230`. Left border accent `border-l-2 border-[#ffc230]/30`. Toggle checked state uses `#ffc230` instead of amber.
- **D-11:** Sonarr/Radarr cards render side-by-side in a sub-grid (`grid-cols-2`) on desktop, stacked on mobile — matching mockup layout.

### Auto-Delete Card Styling
- **D-12:** Post-Import Pruning card uses red/error accent (`#c45b5b`) for the icon, header text tint, and toggle checked state — matching the mockup's danger styling. When disabled, the card body has reduced opacity (`opacity-60`) and `pointer-events-none` — matching mockup pattern.

### Claude's Discretion
- Exact CSS implementation technique for toggle switches (pure CSS vs component)
- Card ordering within each column (follow mockup layout)
- Copy-to-clipboard button styling for webhook URLs
- Transition animations on floating bar appearance
- Responsive breakpoint adjustments if needed
- Whether to add the "API & Security" card shown in mockup (currently has a Security card with API token — may just need icon/header upgrade)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Artifacts (Visual Spec)
- `.aidesigner/runs/2026-04-14T03-43-48-899Z-seedsyncarr-settings-v2-all-sections/design.html` — AIDesigner settings v2 mockup with all 10 sections, toggle switches, masonry layout, floating save bar, Sonarr/Radarr brand colors. THIS IS THE PIXEL-EXACT TARGET.

### Existing Settings Code (modify in place)
- `src/angular/src/app/pages/settings/settings-page.component.html` — Current settings template with two-column layout, cards, AutoQueue CRUD, *arr integration, webhooks, API token
- `src/angular/src/app/pages/settings/settings-page.component.scss` — Current settings styles with card, pattern, token, webhook styling
- `src/angular/src/app/pages/settings/settings-page.component.ts` — Settings controller with config subscription, pattern management, connection testing
- `src/angular/src/app/pages/settings/option.component.ts` — Option component with Text/Checkbox/Password types, debounced onChange
- `src/angular/src/app/pages/settings/option.component.html` — Option template (checkbox input to be restyled as toggle)
- `src/angular/src/app/pages/settings/option.component.scss` — Option styles
- `src/angular/src/app/pages/settings/options-list.ts` — Options context definitions for all 7 setting sections

### Data Layer
- `src/angular/src/app/services/settings/config.ts` — Config model with 8 sections (general, lftp, controller, web, autoqueue, sonarr, radarr, autodelete)
- `src/angular/src/app/services/settings/config.service.ts` — ConfigService with individual set(), testSonarrConnection(), testRadarrConnection()
- `src/angular/src/app/services/autoqueue/autoqueue.service.ts` — AutoQueue pattern CRUD service

### Palette & Variables
- `src/angular/src/styles.scss` — CSS custom properties with Deep Moss palette values

### Prior Phase Context
- `.planning/phases/62-nav-bar-foundation/62-CONTEXT.md` — Phase 62 decisions on palette, blur, amber accent patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OptionComponent` — Already handles Text, Checkbox, Password with debounced change events. Toggle styling can be applied to its Checkbox type.
- `ConfigService` — Auto-save with individual `set()` calls and `WebReaction` response pattern. Already working — no changes needed.
- `AutoQueueService` — Pattern CRUD (add/remove) already implemented and wired into settings template.
- Two-column layout — Already exists in SCSS with `flex-direction: column` on mobile, `flex-direction: row` on desktop at `$medium-min-width`.
- Settings cards — Already use `settings-card` class with `settings-card-header` and `settings-card-body`.

### Established Patterns
- Standalone components with explicit imports (Angular 21)
- `takeUntil(this.destroy$)` for subscription cleanup
- CSS custom properties for all palette colors (`--app-header-bg`, `--app-logo-color`, etc.)
- `ChangeDetectionStrategy.OnPush` with manual `markForCheck()`

### Integration Points
- Settings page is routed via `app.routes.ts` — no routing changes needed
- `OptionComponent` is the unit of change for toggle switch styling
- `settings-page.component.html` needs card header restructuring (add icons, dark header bars)
- `settings-page.component.scss` needs extensive updates for mockup-matching styles

</code_context>

<specifics>
## Specific Ideas

- Pixel-exact match to `.aidesigner/runs/2026-04-14T03-43-48-899Z-seedsyncarr-settings-v2-all-sections/design.html` — no approximations
- Translate Tailwind classes from mockup to Bootstrap 5 + SCSS equivalents
- FA 4.7 icons instead of Phosphor icons
- Keep system font stack (Inter/JetBrains Mono from mockup are reference only — project uses system fonts)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 65-settings-page*
*Context gathered: 2026-04-14*
