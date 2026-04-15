# Phase 62: Nav Bar Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 62-nav-bar-foundation
**Areas discussed:** Nav bar visual style, Active link indicator, Connection status badge, Notification bell

---

## Nav Bar Visual Style

### Background Transparency

| Option | Description | Selected |
|--------|-------------|----------|
| Match mockup closely | ~80% opacity on forest-base with backdrop-blur. Content scrolls visibly behind the nav. Modern glass-morphism feel. | ✓ |
| Subtle blur, higher opacity | ~90% opacity with light blur. Content barely visible behind nav — more conservative. | |
| You decide | Claude picks the best balance of blur and readability. | |

**User's choice:** Match mockup closely (~80% opacity, backdrop-blur 12px)
**Notes:** None

### Brand Icon

| Option | Description | Selected |
|--------|-------------|----------|
| Keep text-only brand | Matches the 'text-only UI, no SVG icons' project decision. Just 'SeedSyncarr' + version badge. | |
| Add the 'arr' amber highlight | Still text-only but style the 'arr' suffix in amber like the mockup shows. | ✓ |
| You decide | Claude picks whichever looks best. | |

**User's choice:** Add the 'arr' amber highlight — SeedSync in primary + arr in amber accent
**Notes:** None

### Border Color

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, use forest-border | Matches the mockup and Deep Moss palette. Current $gray-300 is a Bootstrap default. | ✓ |
| You decide | Claude picks the right border treatment. | |

**User's choice:** Yes, use forest-border (#3e4a38)
**Notes:** None

---

## Active Link Indicator

### Indicator Style

| Option | Description | Selected |
|--------|-------------|----------|
| 2px bottom bar, full link width | Matches the mockup. A 2px amber line sits below the link text via ::after pseudo-element. | ✓ |
| 3px bottom bar, slight inset | Slightly thicker and inset from link edges. More prominent. | |
| You decide | Claude picks the best indicator style. | |

**User's choice:** 2px bottom bar, full link width
**Notes:** None

### Animation

| Option | Description | Selected |
|--------|-------------|----------|
| Fade in/out on route change | Subtle opacity transition (0.15s ease). Old bar fades out, new bar fades in. | ✓ |
| No animation | Instant swap — the bar just appears/disappears. | |
| You decide | Claude picks the transition approach. | |

**User's choice:** Fade in/out on route change (0.15s ease)
**Notes:** None

---

## Connection Status Badge

### Badge Appearance

| Option | Description | Selected |
|--------|-------------|----------|
| Dot + text in bordered pill | Green pulsing dot + 'Connected' text in semantic-success bordered pill. Red dot + 'Disconnected' when down. | ✓ |
| Dot only, no text | Minimal: just a pulsing green/red dot. Hover tooltip shows status text. | |
| Text only, no dot | 'Connected'/'Disconnected' text with color change. No dot, no pill border. | |

**User's choice:** Dot + text in bordered pill
**Notes:** None

### Responsive Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Hide text, show dot only on small screens | Below ~640px, collapse pill to just the dot. Saves space on mobile. | ✓ |
| Hide entire badge on small screens | Below ~640px, hide the connection badge completely. | |
| Always show full badge | Keep full dot + text pill at all breakpoints. | |

**User's choice:** Hide text, show dot only on small screens (below ~640px)
**Notes:** None

---

## Notification Bell

### Bell Rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Font Awesome 4.7 bell | Use fa-bell from FA 4.7. Icon font, not SVG — consistent with project's FA 4.7 usage. | ✓ |
| Unicode bell character | Use Unicode bell character. Truly text-only but may render inconsistently. | |
| Text label 'Alerts' | Skip bell entirely, show text label like 'Alerts (2)'. | |

**User's choice:** Font Awesome 4.7 bell (fa-bell)
**Notes:** None

### Click Action

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown panel below the bell | A dropdown panel shows the notification list. Dismiss individual notifications from panel. | ✓ |
| Keep inline alerts, bell is indicator only | Bell shows count with badge dot. Notifications still display as Bootstrap alerts below nav. | |
| You decide | Claude picks the best interaction pattern. | |

**User's choice:** Dropdown panel below the bell
**Notes:** None

### Alert Bar Replacement

| Option | Description | Selected |
|--------|-------------|----------|
| Remove inline alerts entirely | The dropdown bell replaces the alert bar. All notifications in one place. | ✓ |
| Keep both — alerts for critical, bell for all | DANGER-level stays as inline alerts. INFO/WARNING go to bell dropdown only. | |
| You decide | Claude picks based on notification severity. | |

**User's choice:** Remove inline alerts entirely — bell dropdown is the single notification surface
**Notes:** None

---

## Claude's Discretion

- Pulse animation keyframes and timing
- Dropdown panel dismiss-all behavior
- Nav height adjustments (currently 48px)
- Mobile hamburger behavior for nav links

## Deferred Ideas

None — discussion stayed within phase scope
