# Phase 66: Logs Page - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the existing logs page to a full-viewport terminal-style log viewer with: level filtering via segmented button group, regex search, auto-scroll toggle, clear, export-as-.log, and a live status bar footer. Pixel-exact match to the AIDesigner mockup. All existing LogService streaming functionality is preserved — this is a visual and interaction upgrade.

</domain>

<decisions>
## Implementation Decisions

### Log Viewer Layout & Styling
- **D-01:** Pixel-exact match to the AIDesigner mockup. Dark terminal background (`#0a0d09` / `seed-term`), monospace font, full-viewport height. The terminal area is a flex-1 container with `overflow-y: auto` and custom scrollbar styling.
- **D-02:** Sequential line numbers in a fixed-width gutter column (left-aligned, muted `textsec/30` color, `border-r border-seed-border/30`). Numbers reset when logs are cleared. Each row is a flex container: `[line-num | timestamp | level-badge | message]`.
- **D-03:** ERROR rows get a distinct red tinted background (`bg-error/10`) with top/bottom border (`border-y border-seed-error/20`). The ERROR level badge uses a filled pill (`bg-seed-error text-white px-1.5 py-0.5 rounded text-[10px] font-bold`). Error message text is `#ff8e8e`.
- **D-04:** WARN rows get warning-tinted background on hover (`hover:bg-seed-warning/10`). WARN text and timestamp tinted warning color.
- **D-05:** DEBUG entries use dimmed text (`textsec/50` for level, `textsec/70` for message). INFO entries use green-bold level badge (`text-seed-success font-bold`) and standard text color for message.
- **D-06:** Timestamps displayed in `HH:MM:SS.mmm` format in amber/70 color. Row hover effect: `hover:bg-seed-row/80`.
- **D-07:** Bottom gradient fade on the terminal viewport (`h-8 bg-gradient-to-t from-seed-term to-transparent pointer-events-none`).

### Toolbar & Controls
- **D-08:** Sticky card-styled toolbar above the terminal viewport: `bg-seed-card border border-seed-border rounded-md p-2.5` with `flex-wrap items-center justify-between`. Contains level filter (left) and action buttons (right).
- **D-09:** Segmented button group for level filtering: ALL / INFO / WARN / ERROR / DEBUG. Contained in a `bg-seed-base rounded-md p-1 border border-seed-border` wrapper. Active button: amber background with dark text (`bg-seed-amber text-seed-base shadow`). Inactive buttons use level-specific text colors: WARN in `text-seed-warning`, ERROR in `text-seed-error`, DEBUG/INFO in `text-seed-textsec`.
- **D-10:** Level mapping: ALL = show all levels. INFO = LogRecord.Level.INFO only. WARN = LogRecord.Level.WARNING only. ERROR = LogRecord.Level.ERROR + LogRecord.Level.CRITICAL. DEBUG = LogRecord.Level.DEBUG only.
- **D-11:** Regex search field: `bg-seed-base border border-seed-border rounded-md` with FA 4.7 `fa-search` icon (left) replacing Phosphor magnifying glass. Placeholder: "Grep logs (regex supported)...". Focus state: `border-seed-amber ring-1 ring-seed-amber`. Width ~320px. Filters visible log entries in real time as user types.
- **D-12:** Auto-scroll toggle button: FA 4.7 `fa-check-circle` icon (green) + "Auto-scroll" text when ON, with bordered button style. When OFF, icon changes to `fa-circle-o` and text dims. Default: ON. Scrolling up manually disables auto-scroll. New log arrival while OFF does not scroll.
- **D-13:** Clear button: `fa-trash` icon + "Clear" text, transparent border, muted text. Export button: `fa-download` icon + "Export .log" text, bordered with `bg-seed-muted` background. Vertical divider (`h-6 w-px bg-seed-border`) separates auto-scroll from clear/export.

### Status Bar Footer
- **D-14:** Fixed footer at bottom of viewport: `bg-seed-base border-t border-seed-border px-6 py-2` with flex justify-between. Text: `text-xs text-seed-textsec`.
- **D-15:** Left side: green pulsing dot (same pattern as Phase 62 nav bar) + "Connected to active seedbox daemon" text. Disconnected state: red dot (no pulse) + "Disconnected — waiting for connection". Data source: `ConnectedService.connected` Observable.
- **D-16:** Right side: log count ("N logs indexed") + clock icon (`fa-clock-o`) + "LAST UPDATED: HH:MM:SS AM/PM" in uppercase tracking. Log count updates in real time as new entries arrive.
- **D-17:** No ping display — that would require new backend work outside phase scope.

### Log Data Handling
- **D-18:** Switch from ViewContainerRef template insertion to array-based accumulation (following DashboardLogPaneComponent's `scan` pattern). Accumulate logs into a component array with the existing 5000-record cap from LogService.
- **D-19:** Level filter and regex search applied as client-side array filters on the accumulated buffer. Filtered results re-render the visible entries. Filter changes are instant (no debounce needed on level buttons; search input gets ~200ms debounce).
- **D-20:** Clear button clears the component's display array and resets line counter. LogService ReplaySubject buffer is NOT flushed. New logs after clear start from line 1. Cleared state persists within the component (navigating away and back does not restore cleared logs).
- **D-21:** Export produces a plain text `.log` file download. Format: `YYYY/MM/DD HH:MM:SS - LEVEL - loggerName - message` (one line per entry). Exports currently visible (filtered) entries only, not the full buffer. Uses Blob + URL.createObjectURL + download link pattern.

### Claude's Discretion
- Exact responsive breakpoint behavior for toolbar wrapping on mobile
- Custom scrollbar CSS specifics (webkit-scrollbar styling from mockup as reference)
- Debounce timing on regex search input
- Whether to use Angular's `trackBy` or other optimization for the log list rendering
- Transition animations on filter/clear state changes
- Keyboard shortcuts for toolbar actions (if any)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Artifacts (Visual Spec)
- `.aidesigner/runs/2026-04-14T03-35-39-500Z-seedsyncarr-logs-page-triggarr-style/design.html` — AIDesigner logs page mockup with terminal viewer, toolbar, segmented level filter, search field, auto-scroll/clear/export buttons, and status bar footer. THIS IS THE PIXEL-EXACT TARGET.

### Existing Logs Code (modify in place)
- `src/angular/src/app/pages/logs/logs-page.component.ts` — Current logs controller with ViewContainerRef insertion, scroll management, connection subscription
- `src/angular/src/app/pages/logs/logs-page.component.html` — Current logs template with record template, scroll buttons, status message
- `src/angular/src/app/pages/logs/logs-page.component.scss` — Current logs styles with monospace font, level colors, scroll buttons

### Data Layer
- `src/angular/src/app/services/logs/log.service.ts` — LogService with ReplaySubject(5000) hot observable, SSE-based streaming
- `src/angular/src/app/services/logs/log-record.ts` — LogRecord immutable with Level enum (DEBUG/INFO/WARNING/ERROR/CRITICAL), time, loggerName, message, exceptionTraceback
- `src/angular/src/app/services/utils/connected.service.ts` — ConnectedService.connected Observable for status bar

### Reference Implementation (array pattern)
- `src/angular/src/app/pages/files/dashboard-log-pane.component.ts` — DashboardLogPaneComponent with scan-based array accumulation, levelBadge(), copyLogs() — reuse this pattern

### Palette & Variables
- `src/angular/src/styles.scss` — CSS custom properties with Deep Moss palette values (lines 106+)

### Prior Phase Context
- `.planning/phases/62-nav-bar-foundation/62-CONTEXT.md` — Phase 62 decisions on palette, blur, amber accents, connection status badge patterns
- `.planning/phases/65-settings-page/65-CONTEXT.md` — Phase 65 decisions on pixel-exact mockup matching, FA 4.7 icon mapping

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LogService` — Hot observable with 5000-record ReplaySubject buffer. Already streams log records via SSE.
- `LogRecord` — Immutable record with time, level (DEBUG/INFO/WARNING/ERROR/CRITICAL), loggerName, message, exceptionTraceback.
- `DashboardLogPaneComponent` — Already has array-based accumulation via `scan`, `levelBadge()` helper, `copyLogs()` clipboard method. Pattern to reuse for full logs page.
- `ConnectedService` — Already exposes `connected: Observable<boolean>` for status bar.
- CSS custom properties — Full Deep Moss palette defined in `styles.scss`.
- Font Awesome 4.7 — Available for all icons (`fa-search`, `fa-check-circle`, `fa-circle-o`, `fa-trash`, `fa-download`, `fa-clock-o`).

### Established Patterns
- Standalone components with explicit imports (Angular 21)
- `takeUntilDestroyed(this.destroyRef)` for subscription cleanup (modern pattern from DashboardLogPaneComponent)
- `ChangeDetectionStrategy.OnPush` with `markForCheck()`
- `scan` operator for accumulating observable emissions into arrays
- `debounceTime` for batching rapid updates

### Integration Points
- Logs page routed via `app.routes.ts` at path `"logs"` — no routing changes needed
- `LogsPageComponent` is the main component to modify — complete rewrite of template and styles, significant controller changes
- `styles.scss` already has `app-logs-page` display flex rule (line 99)
- Scroll-to-top/bottom buttons in current component can be removed (auto-scroll toggle replaces them)

</code_context>

<specifics>
## Specific Ideas

- Pixel-exact match to `.aidesigner/runs/2026-04-14T03-35-39-500Z-seedsyncarr-logs-page-triggarr-style/design.html` — no approximations
- Translate Tailwind classes from mockup to Bootstrap 5 + SCSS equivalents (project uses SCSS, not Tailwind)
- FA 4.7 icons instead of Phosphor icons (consistent with all other phases)
- Keep system font stack for UI elements; monospace font (`var(--bs-font-monospace)`) for log entries only
- Reuse `DashboardLogPaneComponent`'s scan/accumulation pattern rather than inventing a new data flow
- The `seed-term` color (`#0a0d09`) is new — add as CSS custom property if not already present

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 66-logs-page*
*Context gathered: 2026-04-14*
