# Phase 65: Settings Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 65-settings-page
**Areas discussed:** Card header icons, Toggle switch styling, Save behavior, Sonarr/Radarr brand colors

---

## Card Header Icons

| Option | Description | Selected |
|--------|-------------|----------|
| FA icons + dark header bar (Recommended) | Map each Phosphor icon to closest FA 4.7 equivalent. Use the darker row-bg background on card headers like the mockup shows. Keeps project consistency. | |
| FA icons, no header bar change | Add FA icons to existing card headers but keep current styling (no dark header bar) | |
| You decide | Claude picks appropriate FA 4.7 icons and header treatment | |

**User's choice:** "match spec pixel exact" (free text — interpreted as FA icons + dark header bar with pixel-exact spec matching)
**Notes:** User wants exact visual match to the AIDesigner design artifact, not just approximate styling.

---

## Toggle Switch Styling

| Option | Description | Selected |
|--------|-------------|----------|
| Pure CSS toggle (Recommended) | Style the existing checkbox input as a pill toggle using CSS only. Matches mockup's amber glow on/off states. No new component needed. | |
| New Toggle component | Create a separate ToggleComponent with its own template. Cleaner separation but more files. | |
| You decide | Claude picks the approach that best matches the design spec | |

**User's choice:** "pixel exact to spec" (free text — interpreted as matching the mockup toggle dimensions and colors precisely, implementation approach at Claude's discretion)
**Notes:** Priority is visual fidelity, not implementation approach.

---

## Save Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Keep auto-save, add visual bar (Recommended) | Keep the working auto-save behavior. Add the floating bar as a visual element that shows confirmation after edits. No backend changes needed. | ✓ |
| Switch to batch save | Buffer all changes locally, only submit when user clicks Save. Requires new state management, dirty tracking, and backend batch endpoint. Major rework. | |
| Floating restart button only | Replace the current bottom 'Restart' button with a floating bar. Keep auto-save. Show restart prompt when config changes require it. | |

**User's choice:** Keep auto-save, add visual bar (Recommended)
**Notes:** None

---

## Sonarr/Radarr Brand Colors

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, brand-colored headers (Recommended) | Sonarr gets blue header bg, Radarr gets gold. Matches the mockup exactly and makes each integration visually distinct. | ✓ |
| Deep Moss palette only | Keep all cards in the Deep Moss palette. Consistent but less visual distinction. | |
| Subtle brand accents | Keep Deep Moss card bg but add brand-colored left border or icon tint. Middle ground. | |

**User's choice:** Yes, brand-colored headers (Recommended)
**Notes:** None

---

## Claude's Discretion

- Toggle implementation technique (pure CSS vs component)
- Card ordering within columns
- Copy button styling for webhooks
- Floating bar transitions
- Responsive breakpoints

## Deferred Ideas

None — discussion stayed within phase scope
