# Phase 34: Shell - Research

**Researched:** 2026-02-17
**Domain:** Angular 19 sidebar layout restructure, CSS-only collapsible icon-rail, mobile hamburger nav
**Confidence:** HIGH

## Summary

Phase 34 restructures the app shell from the current mobile-first overlay sidebar into a persistent, collapsible icon-rail sidebar (56px collapsed → 200px expanded on hover) for large screens, while preserving the existing hamburger/overlay behavior on mobile. The work lives entirely in three component files (`app.component.*`, `sidebar.component.*`, `header.component.*`) plus the shared `_common.scss` for variable updates.

The current sidebar is a `display: none / block` overlay panel (`position: fixed`, width `$sidebar-width: 170px`) that slides in from the left. The new design is a permanently-visible vertical icon rail on the left edge at 56px that widens to 200px on CSS `:hover` — no Angular state, no JS. Icons are already SVGs; labels just need to be hidden at 56px and visible at 200px. The `#top-content` margin-left must track the sidebar width change via the same CSS transition.

NAV-02 (`>` prompt indicator) adds a small monospace prefix character to the active link using `::before` CSS pseudo-element on `.selected`. NAV-03 (version at sidebar bottom) can reuse the same `require("../../../package.json")` pattern already used by `AboutPageComponent`. NAV-04 preserves the existing hamburger toggle for screens ≤ `$medium-max-width` (992px) — the current breakpoint logic in `app.component.scss` already handles this; it just needs to be updated to show/hide the icon-rail vs overlay correctly.

**Primary recommendation:** Implement the icon-rail purely in SCSS using `width` + `overflow: hidden` transition on `:hover` on the `#top-sidebar` container. No new Angular state, no HostListener — this is purely a CSS job.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NAV-01 | User sees sidebar as 56px icon rail that expands to 200px on hover (CSS-only transition) | CSS `width` transition on `#top-sidebar:hover`, `overflow: hidden` hides labels at 56px; labels have `opacity` + `width: 0` → `auto` transition. Breakpoint guard: only applies at `$large-min-width` (993px+). |
| NAV-02 | User sees `>` prompt indicator on active route in sidebar | `routerLinkActive="selected"` already applies `.selected` class. Add `a.button.selected::before { content: '> '; font-family: var(--bs-font-monospace); color: #3fb950; }` in `sidebar.component.scss`. |
| NAV-03 | User sees app version at bottom of sidebar | Add version property to `SidebarComponent` using same pattern as `AboutPageComponent`: `declare function require(m: string): { version: string }; const { version } = require("../../../../package.json");`. Display in sidebar template below the `<hr>`. |
| NAV-04 | User can navigate via mobile hamburger menu (preserved from current behavior) | Current `showSidebar` toggle + `#top-sidebar` display:block/none overlay + `#outside-sidebar` click-to-dismiss pattern in `app.component.*` is unchanged. At `$medium-max-width` (≤992px) the icon-rail CSS does not apply; the overlay drawer pattern remains. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular Router | 19.2.x | `routerLinkActive` directive adds `.selected` class | Already wired in `sidebar.component.ts` |
| Bootstrap 5.3 | 5.3.3 | Responsive breakpoints, `d-flex`, spacing utilities | Already the CSS framework |
| SCSS | 1.32+ (Sass) | `width` transitions, pseudo-elements, media queries | Project-standard, already compiled via Angular build |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Angular `routerLinkActive` directive | 19.2.x | Applies `.selected` to active nav links | NAV-02 — already used, no change needed |
| CSS `transition` | N/A | CSS-only hover expansion | NAV-01 — no JS needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS-only `:hover` | Angular `mouseenter`/`mouseleave` + state | CSS is zero-cost, works without change detection; Angular events would add complexity and a `ChangeDetectorRef` concern |
| `width` transition | `transform: scaleX()` | `width` transition with `overflow: hidden` is simpler and doesn't distort icon rendering |
| `max-width` transition | `width` transition | `max-width: 0 → 200px` is a common CSS trick that avoids animating `auto`; equivalent outcome |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
src/angular/src/app/
├── pages/main/
│   ├── app.component.html       # Remove old logo block, keep router-outlet + header + toast
│   ├── app.component.scss       # Update margin-left to icon-rail width, add transition
│   ├── app.component.ts         # Minor: pass version or keep as-is
│   ├── sidebar.component.html   # Add icon-only layout + labels + version footer
│   ├── sidebar.component.scss   # Add width transition, ::before prompt, overflow:hidden
│   ├── sidebar.component.ts     # Add version property
│   └── header.component.*       # Restyle header (phase scope: remove title-bar redundancy)
└── common/
    └── _common.scss             # Update $sidebar-width (or add $sidebar-collapsed-width, $sidebar-expanded-width)
```

### Pattern 1: CSS-Only Icon-Rail Sidebar Expansion
**What:** The sidebar container has a fixed narrow width at rest and expands on `:hover` via a CSS `width` transition. Labels are hidden (opacity 0, max-width 0, overflow hidden) at collapsed state and visible at expanded state. No Angular component state changes.
**When to use:** Always for desktop (large-min-width and above). At mobile widths the old overlay approach takes over.

```scss
// sidebar.component.scss (or applied to #top-sidebar in app.component.scss)
// Source: CSS transition pattern — verified SCSS capability, no library needed

$sidebar-icon-width: 56px;
$sidebar-expanded-width: 200px;

#top-sidebar {
  width: $sidebar-icon-width;
  overflow: hidden;
  transition: width 0.25s ease;
  white-space: nowrap;       // prevent label wrapping during animation

  &:hover {
    width: $sidebar-expanded-width;
  }
}

// Labels hidden by default, visible on expansion
.sidebar-label {
  opacity: 0;
  max-width: 0;
  overflow: hidden;
  transition: opacity 0.2s ease, max-width 0.25s ease;
  display: inline-block;
  vertical-align: middle;
}

#top-sidebar:hover .sidebar-label {
  opacity: 1;
  max-width: 120px;  // enough for longest label
}
```

**Key insight:** `white-space: nowrap` on the sidebar prevents labels from wrapping during the width animation, which looks broken without it.

### Pattern 2: `>` Prompt Indicator via `::before`
**What:** Add a CSS pseudo-element on the `.selected` state of sidebar nav links.
**When to use:** NAV-02. Already have `routerLinkActive="selected"` producing the `.selected` class.

```scss
// sidebar.component.scss
.button {
  // ... existing styles ...

  &.selected {
    // ... existing selected styles ...

    &::before {
      content: '> ';
      font-family: var(--bs-font-monospace);
      color: #3fb950;  // terminal green -- matches --app-logo-color
    }
  }
}
```

**Note:** The `> ` prefix occupies space in the flow. At 56px collapsed width this may cause icon misalignment. Consider moving the `::before` to the label span, or suppress it at collapsed state.

### Pattern 3: Version in Sidebar Footer (NAV-03)
**What:** Read `version` from `package.json` the same way `AboutPageComponent` already does.

```typescript
// sidebar.component.ts
declare function require(moduleName: string): { version: string };
const { version: appVersion } = require("../../../../package.json");

export class SidebarComponent implements OnInit {
  routeInfos = ROUTE_INFOS;
  public version: string;
  public commandsEnabled: boolean;
  // ...

  constructor(...) {
    // ...
    this.version = appVersion;
  }
}
```

```html
<!-- sidebar.component.html — at bottom of sidebar div, after Restart button -->
<div class="sidebar-version">v{{version}}</div>
```

**Note:** The `require()` path must be relative from `sidebar.component.ts` location. `AboutPageComponent` uses `"../../../../package.json"` — `SidebarComponent` is at the same depth (`src/app/pages/main/`), so the same path works.

### Pattern 4: Mobile Hamburger (NAV-04) — Preserve Existing
**What:** The current `showSidebar` boolean in `AppComponent`, the `#top-sidebar [class.top-sidebar-open/closed]`, and `#outside-sidebar` click-dismiss overlay stay untouched.
**When to use:** At ≤ `$medium-max-width` (992px), the icon-rail CSS does NOT apply — the media query restricts it to `$large-min-width` (993px+). The mobile sidebar remains a full-width overlay drawer.

```scss
// app.component.scss — large screen guard for icon-rail
@media only screen and (min-width: $large-min-width) {
  #top-sidebar {
    display: block;  // always visible
    position: fixed;
    top: 0;
    left: 0;
    height: 100%;
    width: 56px;
    transition: width 0.25s ease;
    overflow: hidden;
    white-space: nowrap;

    &:hover {
      width: 200px;
    }
  }

  #top-content {
    margin-left: 56px;
    transition: margin-left 0.25s ease;
  }

  // Hide mobile-only buttons on large screens
  .sidebar-btn, #title-bar {
    display: none;
  }

  .outside-sidebar-show {
    display: none;
  }
}
```

**Critical:** The current `app.component.scss` already has `@media (min-width: $large-min-width)` rules that `display: block` the sidebar and hide the hamburger buttons. The Phase 34 change replaces `width: $sidebar-width` (170px fixed) with the animated 56px→200px behavior.

### Anti-Patterns to Avoid
- **Animating `margin-left` on `#top-content` in sync with sidebar hover:** This creates a layout reflow on every animation frame and looks jittery. Keep content at `margin-left: 56px` — icons are always visible, content is never re-reflowed.
- **Using Angular `@HostListener('mouseenter')` for the expansion:** CSS `:hover` is zero-overhead and works without triggering Angular change detection.
- **`position: absolute` sidebar:** Must stay `position: fixed` so it spans full viewport height and doesn't scroll with content.
- **Putting version text at top of sidebar:** It will be obscured when collapsed. Put it at the bottom, truncate/hide at narrow width.
- **`overflow: hidden` cutting off tooltip/popups:** If future phases add tooltips on sidebar icons, they'll need `overflow: visible` — flag as a known future concern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Active route detection | Custom route listener to toggle classes | `routerLinkActive="selected"` directive | Angular handles exact/partial matching, cleanup on navigation |
| Width animation | JS-based resizer with `requestAnimationFrame` | CSS `transition: width 0.25s ease` | GPU-composited, no JS overhead, no change detection |
| App version | HTTP call or backend endpoint | `require("../../../../package.json")` | Already done in `AboutPageComponent`; Angular CLI includes JSON in bundle |
| Responsive breakpoints | Custom `BreakpointObserver` service | SCSS `@media` queries using existing `$large-min-width` | Already defined in `_common.scss`, no new service needed |

**Key insight:** Everything in this phase is CSS + minimal TypeScript. No new services, no new libraries, no new Angular patterns.

## Common Pitfalls

### Pitfall 1: Content Margin Does Not Track Sidebar Width
**What goes wrong:** `#top-content` keeps `margin-left: 170px` (old `$sidebar-width`) after sidebar narrows to 56px — content is pushed too far right, leaving dead space.
**Why it happens:** `margin-left` is set to old `$sidebar-width` and not updated.
**How to avoid:** Change `#top-content` `margin-left` to `56px` (icon-rail width). Content always sits at 56px regardless of hover state — this is the standard icon-rail UX pattern. Do NOT animate `margin-left` in sync with sidebar hover.
**Warning signs:** Large gap between sidebar and content on load.

### Pitfall 2: `white-space: nowrap` Missing — Labels Wrap During Animation
**What goes wrong:** During the width transition (56px → 200px), labels start wrapping at narrow widths, causing visual glitch.
**Why it happens:** `div` elements inside the sidebar wrap by default when they can't fit.
**How to avoid:** Add `white-space: nowrap` to `#top-sidebar` or the `.button` elements.
**Warning signs:** Text visibly wraps and then un-wraps as the sidebar animates.

### Pitfall 3: Mobile Overlay Broken by Icon-Rail CSS
**What goes wrong:** After adding `position: fixed; width: 56px; height: 100%` to `#top-sidebar` at large screens, the mobile overlay behavior breaks because the element is always visible.
**Why it happens:** The large-screen media query must be correctly scoped to `min-width: $large-min-width`. Below that breakpoint, the old `top-sidebar-open/closed` classes must still control visibility.
**How to avoid:** Wrap ALL icon-rail CSS changes inside `@media only screen and (min-width: $large-min-width)`.
**Warning signs:** On mobile, sidebar is always visible and covers content.

### Pitfall 4: `>` Prompt Takes Space at 56px Width
**What goes wrong:** At icon-rail width (56px), the `::before { content: '> ' }` on `.selected` pushes the icon out of view or misaligns it.
**Why it happens:** `::before` is in the normal flow and adds width.
**How to avoid:** Only show `::before` when the sidebar is expanded. Use `#top-sidebar:hover .button.selected::before` or conditionally apply with `opacity: 0` when not hovering. Alternatively, place the prompt in the label span (which is already hidden at 56px).
**Warning signs:** Icon misaligned or cut off on active route when collapsed.

### Pitfall 5: Sidebar `overflow: hidden` Cuts Off Absolutely-Positioned Children
**What goes wrong:** If any sidebar child uses `position: absolute` or `position: fixed` (e.g., a tooltip), it gets clipped.
**Why it happens:** `overflow: hidden` clips all content including absolutely-positioned descendants at the container boundary.
**How to avoid:** Ensure no sidebar children use absolute/fixed positioning that needs to escape the sidebar bounds. Current children (nav links, hr, restart button) are all in-flow — this is safe for Phase 34. Note for future phases.
**Warning signs:** Dropdown or tooltip rendered inside sidebar is clipped.

### Pitfall 6: Duplicate `$sidebar-width` Variable
**What goes wrong:** `_common.scss` has `$sidebar-width: 170px`. `app.component.scss` references `$sidebar-width` via the `#top-content { margin-left: $sidebar-width; }` rule. After Phase 34 changes the content margin to 56px, the old variable may still be referenced elsewhere.
**Why it happens:** Variable renaming/addition without auditing all usages.
**How to avoid:** Add `$sidebar-collapsed-width: 56px` and `$sidebar-expanded-width: 200px` to `_common.scss`. Replace `$sidebar-width` usage in `app.component.scss`. Check if `$sidebar-width` is used elsewhere.
**Warning signs:** Build compiles fine but spacing is visually wrong.

## Code Examples

Verified patterns from the actual codebase:

### Current Sidebar HTML Structure (to be restructured)
```html
<!-- sidebar.component.html - CURRENT -->
<div id="sidebar">
    <a *ngFor="let routeInfo of routeInfos"
       class="button"
       routerLink="{{routeInfo.path}}"
       routerLinkActive="selected">
        <img src="{{routeInfo.icon}}" />
        <span class="text">{{routeInfo.name}}</span>
    </a>
    <hr>
    <a class="button"
       [attr.disabled]="commandsEnabled ? null : true"
       (click)="!commandsEnabled || onCommandRestart()">
        <img src="assets/icons/refresh.svg" />
        <span class="text">Restart</span>
    </a>
</div>
```

### Proposed Sidebar HTML (Icon-Rail)
```html
<!-- sidebar.component.html - TARGET -->
<nav id="sidebar">
    <a *ngFor="let routeInfo of routeInfos"
       class="button"
       routerLink="{{routeInfo.path}}"
       routerLinkActive="selected">
        <img src="{{routeInfo.icon}}" class="sidebar-icon" />
        <span class="sidebar-label">{{routeInfo.name}}</span>
    </a>

    <hr>

    <a class="button"
       [attr.disabled]="commandsEnabled ? null : true"
       (click)="!commandsEnabled || onCommandRestart()">
        <img src="assets/icons/refresh.svg" class="sidebar-icon" />
        <span class="sidebar-label">Restart</span>
    </a>

    <div class="sidebar-spacer"></div>

    <div class="sidebar-version sidebar-label">v{{version}}</div>
</nav>
```

### Current App Component Large-Screen Media Query (to be updated)
```scss
// app.component.scss - CURRENT (large screens)
@media only screen and (min-width: $large-min-width) {
    #top-sidebar {
        display: block;  // always show sidebar
    }
    .outside-sidebar-show {
        display: none;
    }
    .sidebar-btn {
        display: none;
    }
    #title-bar {
        display: none;
    }
}
```

### Current `_common.scss` Layout Variables
```scss
// _common.scss - CURRENT
$small-max-width: 600px;
$medium-min-width: 601px;
$medium-max-width: 992px;
$large-min-width: 993px;

$sidebar-width: 170px;  // To be split into collapsed/expanded
```

### Version Pattern (from about-page.component.ts — already working)
```typescript
declare function require(moduleName: string): { version: string };
const { version: appVersion } = require("../../../../package.json");
// Path is relative to src/app/pages/main/ — same depth as sidebar.component.ts
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mobile-only overlay drawer | Icon-rail (desktop) + overlay drawer (mobile) | Phase 34 | Desktop always has nav visible; content never fully hidden |
| `display: none/block` toggle | CSS `width` + `overflow: hidden` transition | Phase 34 | Smooth animation, no layout pop |
| Logo in sidebar overlay panel | Logo/version at sidebar bottom | Phase 34 | Persistent branding in icon-rail footer |
| `$sidebar-width: 170px` single variable | `$sidebar-collapsed-width: 56px` + `$sidebar-expanded-width: 200px` | Phase 34 | Explicit, self-documenting |

**Deprecated/outdated:**
- `#top-sidebar` as an overlay panel with `animation: animateleft` keyframe (slide-in from left): Replaced by persistent icon-rail at large screens. The keyframe animation stays relevant for mobile overlay only.
- `$sidebar-width: 170px`: Split into two new variables.
- Logo block (`#logo`) inside `#top-sidebar` in `app.component.html`: Logo/branding moves to sidebar footer as version text. The hamburger close button (`#sidebar-btn-close`) in the logo block remains for mobile only.

## Open Questions

1. **Should `margin-left` on `#top-content` transition to match sidebar expansion?**
   - What we know: Animating `margin-left` in sync with the sidebar `:hover` requires CSS variable tricks or JS — neither is zero-cost. Standard icon-rail UX (VS Code, Notion) keeps content at a fixed offset equal to the collapsed width.
   - What's unclear: Whether the user wants content to shift when sidebar expands (pushing content right) or overlay (sidebar slides over content).
   - Recommendation: Default to overlay-over-content (no `margin-left` change). Content stays at `margin-left: 56px`. Sidebar hover slides over content at 200px. This is simpler and more terminal-aesthetic.

2. **Where exactly does the `>` prompt appear at 56px collapsed?**
   - What we know: At 56px, labels are hidden; only icons show. `::before` content on `.button.selected` would show inline with the icon, potentially disrupting icon alignment.
   - What's unclear: Whether the `>` should be visible at collapsed state or only when expanded.
   - Recommendation: Scope `::before` inside `#top-sidebar:hover .button.selected` so it only appears when expanded. At collapsed state, rely on the existing `.selected` background-color highlight to indicate active route.

3. **Header restyling scope in Phase 34**
   - What we know: Phase description says "restyle header" but no explicit NAV requirements cover the header beyond the existing notification area in `header.component.*`.
   - What's unclear: What specific header changes are expected (typography, background, remove `#title-bar` from large screens, etc.)
   - Recommendation: At minimum, confirm `#title-bar` (containing hamburger + page title) is already hidden on large screens (it is — current CSS does this). The `header.component` notification banner stays as-is unless a specific visual change is needed.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `app.component.*`, `sidebar.component.*`, `header.component.*`, `_common.scss`, `_bootstrap-variables.scss`, `routes.ts`, `about-page.component.ts`, `styles.scss`, `index.html`
- Angular Router `routerLinkActive` — behavior verified via existing usage in `sidebar.component.html`

### Secondary (MEDIUM confidence)
- CSS icon-rail pattern (width + overflow:hidden transition) — standard CSS, no library, widely documented
- `require("package.json")` version pattern — verified in `about-page.component.ts` at exact same directory depth

### Tertiary (LOW confidence)
- None — all findings backed by direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing Angular/Bootstrap/SCSS
- Architecture: HIGH — patterns verified directly in existing codebase
- Pitfalls: HIGH — identified from direct inspection of current SCSS variables and media queries

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable — Angular/Bootstrap APIs not changing)
