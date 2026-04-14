# Phase 66: Logs Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 66-logs-page
**Areas discussed:** Log viewer layout & styling, Toolbar & controls, Status bar footer, Log data handling

---

## Log Viewer Layout & Styling

| Option | Description | Selected |
|--------|-------------|----------|
| Pixel-exact to AIDesigner mockup | Match design.html exactly. Dark terminal bg, monospace font, color-coded levels, full-viewport height. | ✓ |
| Enhanced current layout | Keep existing `<p>` tag structure but upgrade styling to match Deep Moss palette. | |
| You decide | Claude picks best approach. | |

**User's choice:** Pixel-exact to AIDesigner mockup
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential line numbers as in mockup | Numbered 1, 2, 3... in a fixed-width gutter column with muted styling. Resets when logs are cleared. | ✓ |
| No line numbers | Skip the gutter column. | |
| You decide | Claude picks. | |

**User's choice:** Sequential line numbers as in mockup
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Match mockup exactly | ERROR rows get red tinted background with borders. WARN gets warning tinted hover. DEBUG dimmed. INFO green-bold. | ✓ |
| Simplified level colors | Just color the level badge and message text. No row background tinting. | |
| You decide | Claude picks. | |

**User's choice:** Match mockup exactly
**Notes:** None

---

## Toolbar & Controls

| Option | Description | Selected |
|--------|-------------|----------|
| Sticky toolbar matching mockup | Card-styled toolbar fixed above terminal viewport. All controls in single row. | ✓ |
| Inline non-sticky toolbar | Toolbar scrolls with content. | |
| You decide | Claude picks. | |

**User's choice:** Sticky toolbar matching mockup
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| ALL/INFO/WARN/ERROR/DEBUG buttons | Match mockup labels. Map WARNING→WARN, combine ERROR+CRITICAL under ERROR. | ✓ |
| Match enum exactly | 6 buttons: ALL/DEBUG/INFO/WARNING/ERROR/CRITICAL. | |
| You decide | Claude picks. | |

**User's choice:** ALL/INFO/WARN/ERROR/DEBUG buttons
**Notes:** Maps WARNING→WARN label, combines ERROR+CRITICAL under ERROR button

| Option | Description | Selected |
|--------|-------------|----------|
| Level-colored labels, amber active | Inactive WARN in warning color, ERROR in error color. Active button amber. | ✓ |
| All amber | Active amber, all inactive muted. | |
| You decide | Claude picks. | |

**User's choice:** Level-colored labels, amber active state
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle button matching mockup | Green check icon + text when ON. Changes icon/dims when OFF. ON by default. | ✓ |
| Simple checkbox toggle | Plain checkbox + label. | |
| You decide | Claude picks. | |

**User's choice:** Toggle button matching mockup
**Notes:** Auto-scroll ON by default. Scrolling up manually disables it.

---

## Status Bar Footer

| Option | Description | Selected |
|--------|-------------|----------|
| Match mockup minus ping | Fixed footer with connection status, log count, last updated. Skip ping display. | ✓ |
| Match mockup exactly including ping | Include ping display — needs new backend endpoint. | |
| You decide | Claude picks. | |

**User's choice:** Match mockup minus ping
**Notes:** Ping would require new backend work — out of scope

| Option | Description | Selected |
|--------|-------------|----------|
| Connected/Disconnected with descriptive text | Green pulse + full descriptive text. Mirrors Phase 62 nav bar pattern. | ✓ |
| Short labels only | Just "Connected" / "Disconnected". | |
| You decide | Claude picks. | |

**User's choice:** Connected/Disconnected with descriptive text
**Notes:** None

---

## Log Data Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Client-side array with pipe filtering | Accumulate into array via scan, apply filters as array operations. | ✓ |
| Observable pipe chain | Filter at Observable level before accumulation. | |
| You decide | Claude picks. | |

**User's choice:** Client-side array with pipe filtering
**Notes:** Follows DashboardLogPaneComponent's scan pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Clear display only | Clears visible entries and resets line counter. Buffer NOT flushed. | ✓ |
| Flush entire buffer | Clears display AND LogService ReplaySubject buffer. | |
| You decide | Claude picks. | |

**User's choice:** Clear display only
**Notes:** New logs after clear start from line 1

| Option | Description | Selected |
|--------|-------------|----------|
| Plain text .log file download | Exports filtered entries as .log file. Uses Blob + download link. | ✓ |
| Export full buffer regardless of filter | Always exports all buffered logs. | |
| You decide | Claude picks. | |

**User's choice:** Plain text .log file download
**Notes:** Exports currently visible (filtered) entries only

---

## Claude's Discretion

- Responsive breakpoint behavior for toolbar wrapping
- Custom scrollbar CSS specifics
- Debounce timing on regex search input
- Angular rendering optimizations (trackBy, etc.)
- Transition animations
- Keyboard shortcuts

## Deferred Ideas

None — discussion stayed within phase scope
