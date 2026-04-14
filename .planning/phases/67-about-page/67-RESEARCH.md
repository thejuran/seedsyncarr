# Phase 67: About Page - Research

**Researched:** 2026-04-14
**Domain:** Angular 21 / Bootstrap 5 + SCSS UI — static page with card layout, system info table, link grid, license footer
**Confidence:** HIGH

## Summary

Phase 67 is a complete rewrite of `AboutPageComponent` to match the AIDesigner mockup at pixel-exact fidelity. The mockup is a Tailwind HTML artifact; all Tailwind classes must be converted to literal CSS values in Bootstrap 5 + SCSS. No new Angular services, routing changes, or backend endpoints are needed. The component already exists and reads `appVersion` from package.json — that wiring is preserved.

The page has four distinct visual sections: (1) an identity card with brand favicon, "SeedSync**arr**" branded title, version badge, tagline, and optional build info; (2) a system info key-value table with divider rows and hover highlight; (3) a 2×2 / 4-column responsive grid of link cards with hover-to-amber transitions; (4) a license badge and copyright footer.

The critical constraint is **exact value porting** — the user memory feedback record explicitly flags that "close enough" Bootstrap approximations have caused rework. Use literal hex colors, px padding, and exact spacing values extracted from the mockup's Tailwind config, not Bootstrap utility class approximations.

**Primary recommendation:** Rewrite all three component files (HTML, TS, SCSS) in a single wave, extracting every design token value from the mockup's Tailwind config and inline styles directly into SCSS.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**System Info Data**
- D-01: No new backend endpoint for this phase. System info shows only build-time or existing service data.
- D-02: Rows: App Version (from package.json), Angular Version (build-time constant). Remaining rows (Python version, OS, uptime, PID, config path) show static placeholder dashes or generic values (`~/.seedsyncarr` for config path).
- D-03: Key-value row layout: uppercase label left, monospace value right, with divider lines between rows and hover highlight.

**Identity Card**
- D-04: App icon uses the actual SeedSyncarr brand favicon from `doc/brand/` — NOT the Phosphor arrows-merge icon from the mockup. Displayed in an amber-bordered rounded container.
- D-05: Brand text uses "SeedSync" + amber "arr" pattern from Phase 62 D-03.
- D-06: Tagline: "Sync files from your seedbox to your local media server — fast, automated, and integrated with Sonarr and Radarr."
- D-07: Version string shows app version from package.json with "(Stable)" suffix. Build info (commit hash, build date) included if available at build time, otherwise omitted.

**Link Cards**
- D-08: Four link cards in a responsive grid: GitHub, Docs, Report Issue, Changelog.
- D-09: URLs: GitHub → `https://github.com/thejuran/seedsyncarr`, Docs → `https://thejuran.github.io/seedsyncarr/`, Report Issue → `https://github.com/thejuran/seedsyncarr/issues`, Changelog → `https://github.com/thejuran/seedsyncarr/releases`.
- D-10: All links open in new tabs (`target="_blank"`).
- D-11: Each card uses a Phosphor icon (ph-github-logo, ph-book, ph-bug, ph-git-commit) with hover-to-amber color transition on both icon and text.

**License & Copyright**
- D-12: License badge shows "Apache License 2.0" (not "MIT License" from mockup).
- D-13: Copyright text — Claude's discretion to match LICENSE.txt content exactly.

### Claude's Discretion
- Exact fade-in-up animation timing for page load
- System info table row hover effect intensity
- Identity card ambient glow effect (subtle amber radial gradient behind the icon)
- Fork attribution note ("Based on SeedSync by Inderpreet Singh") — keep, restyle, or fold into copyright
- Responsive breakpoints for link cards grid (4-col on desktop, 2-col on mobile per mockup)

### Deferred Ideas (OUT OF SCOPE)
- Backend `/server/status` endpoint for live system info (Python version, OS, uptime, PID, config path)
- Build info injection (commit hash, build date) via environment variables at Docker build time
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ABUT-01 | App identity card with icon, branded title, version, tagline, build info | Identity card section with brand favicon asset at `src/angular/src/assets/favicon.png`; version from existing `appVersion` field; brand text pattern from Phase 62 D-03 |
| ABUT-02 | System info table with key-value pairs (Python, Angular, OS, Uptime, PID, Config) | All rows present per mockup; Python/OS/Uptime/PID show `—` placeholder; Angular version as build-time constant; Config path as `~/.seedsyncarr` |
| ABUT-03 | Link cards grid (GitHub, Docs, Report Issue, Changelog) with hover-to-amber | 4-card grid in 2-col / 4-col responsive layout; Phosphor icons confirmed available; hover pattern extracted from mockup |
| ABUT-04 | License badge and copyright footer | Apache License 2.0 per D-12; copyright from current `about-page.component.html`: "Copyright © 2017-2026 Inderpreet Singh, thejuran" |
</phase_requirements>

---

## Standard Stack

### Core (no new installs required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular | ^21.2.8 | Component framework | Already in project |
| Bootstrap 5 | 5.3.x | Grid, spacing, typography base | Project standard |
| SCSS | (Angular CLI) | Component styles | Project standard |
| Phosphor Icons | CDN (unpkg) | Link card and system section icons | Already loaded in `index.html` [VERIFIED: codebase grep] |
| Bootstrap-variables.scss | local | Deep Moss palette tokens | `_bootstrap-variables.scss` already has all needed color values [VERIFIED: file read] |

**Installation:** No new packages needed. All dependencies are present. [VERIFIED: file read of package.json]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Inter (Google Fonts) | loaded in index.html | UI sans-serif font | Already loaded; used for all UI text |
| JetBrains Mono (Google Fonts) | loaded in index.html | Monospace font | System info values, version badge, build info |

**Version verification:** Angular ^21.2.8 confirmed from `src/angular/package.json`. [VERIFIED: bash npm view]

---

## Architecture Patterns

### Component File Structure

```
src/angular/src/app/pages/about/
├── about-page.component.ts    # Rewrite: add angularVersion constant, keep appVersion
├── about-page.component.html  # Full rewrite: 4-section layout
└── about-page.component.scss  # Full rewrite: literal design-spec values
```

### Pattern 1: Centered Scrollable Page Layout

**What:** `app-about-page` grows to fill the flex column via `flex-grow: 1` (already set in `styles.scss` line 100). The inner main element is `max-width: 42rem` (672px) centered, with `py: 3rem` top/bottom, `gap: 2rem` between sections.

**When to use:** This page is a static content page — no viewport-filling tricks like the Logs page. Scrolling is normal document scroll.

**Mockup source values (Tailwind → CSS):**
```scss
// Source: design.html main element
// Tailwind: max-w-2xl mx-auto px-6 py-12 flex flex-col gap-8
main {
  flex-grow: 1;
  width: 100%;
  max-width: 42rem;      // max-w-2xl = 672px
  margin: 0 auto;
  padding: 3rem 1.5rem;  // py-12 = 3rem, px-6 = 1.5rem
  display: flex;
  flex-direction: column;
  gap: 2rem;             // gap-8 = 2rem
  opacity: 0;
  animation: fade-in-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
```

### Pattern 2: Card Section (used by Identity Card + System Info)

**What:** Consistent card treatment matching prior phases — `bg-seed-card` background, `border-seed-border` border, `rounded-2xl` corners, `shadow-sm`.

**Mockup source values:**
```scss
// Source: design.html section elements
// Tailwind: bg-seed-card border border-seed-border rounded-2xl p-8 shadow-sm
.about-card {
  background: #222a20;        // seed-card
  border: 1px solid #3e4a38;  // seed-border
  border-radius: 1rem;        // rounded-2xl
  padding: 2rem;              // p-8
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); // shadow-sm
}
```

### Pattern 3: Identity Card — Favicon Icon Container

**What:** Amber-bordered rounded square container with ambient glow, holding the brand favicon. The mockup uses a Phosphor icon but D-04 substitutes the actual favicon asset.

**Mockup source values:**
```scss
// Source: design.html icon container
// Tailwind: w-24 h-24 rounded-2xl bg-gradient-to-b from-seed-row to-seed-card border border-seed-amber/30 shadow-[0_0_20px_rgba(196,154,74,0.15)]
.identity-icon-container {
  width: 6rem;   // w-24
  height: 6rem;  // h-24
  border-radius: 1rem;  // rounded-2xl
  background: linear-gradient(to bottom, #1a2019, #222a20);  // seed-row to seed-card
  border: 1px solid rgba(196, 154, 74, 0.30);  // border-seed-amber/30
  box-shadow: 0 0 20px rgba(196, 154, 74, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;  // mb-6
  position: relative;
  z-index: 10;
}

img.brand-favicon {
  width: 3rem;   // approx text-4xl equivalent for icon
  height: 3rem;
  object-fit: contain;
}
```

**Ambient glow (Claude's discretion):**
```scss
// Source: design.html absolute radial overlay
// Tailwind: absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 bg-seed-amber/5 blur-[80px]
.identity-card-glow {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 16rem;   // w-64
  height: 8rem;   // h-32
  background: rgba(196, 154, 74, 0.05);  // bg-seed-amber/5
  filter: blur(80px);
  pointer-events: none;
  border-radius: 50%;
}
```

### Pattern 4: System Info Table

**What:** Rounded bordered container with divider rows, hover highlight, uppercase label left / monospace value right.

**Mockup source values:**
```scss
// Source: design.html system info rows
// Inner container: bg-seed-row border border-seed-border/40 rounded-xl overflow-hidden shadow-inner
.sysinfo-table {
  background: #1a2019;  // seed-row
  border: 1px solid rgba(62, 74, 56, 0.40);  // seed-border/40
  border-radius: 0.75rem;  // rounded-xl
  overflow: hidden;
  box-shadow: inset 0 2px 4px 0 rgba(0,0,0,0.05); // shadow-inner
  display: flex;
  flex-direction: column;
}

// Row dividers: divide-y divide-seed-border/40 (CSS border-top on siblings)
.sysinfo-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1.25rem;   // py-3.5 px-5
  border-top: 1px solid rgba(62, 74, 56, 0.40); // divide-seed-border/40
  transition: background-color 150ms;

  &:first-child { border-top: none; }

  &:hover {
    background: rgba(44, 54, 41, 0.30);  // hover:bg-seed-muted/30
  }
}

.sysinfo-label {
  font-size: 0.75rem;   // text-xs
  font-weight: 600;     // font-semibold
  text-transform: uppercase;
  letter-spacing: 0.05em;  // tracking-wider
  color: #9aaa8a;        // seed-textMuted
  width: 33.333%;        // w-1/3
}

.sysinfo-value {
  font-size: 0.8125rem;  // text-[13px]
  font-family: var(--bs-font-monospace);
  color: #e0e8d6;        // seed-text
  width: 66.666%;        // w-2/3
  text-align: right;
}
```

### Pattern 5: Link Cards Grid — Hover-to-Amber

**What:** 2-column (mobile) / 4-column (desktop) grid of link cards. Hover state changes border to amber, background tints amber, icon and text transition to amber color.

**Mockup source values:**
```scss
// Source: design.html link card section
// Section: grid grid-cols-2 md:grid-cols-4 gap-3
.link-cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;   // gap-3

  @media (min-width: 768px) {  // md breakpoint
    grid-template-columns: repeat(4, 1fr);
  }
}

// Card: flex flex-col items-center justify-center gap-2 p-4 rounded-xl bg-seed-card border border-seed-border shadow-sm
// Hover: hover:border-seed-amber hover:bg-seed-muted/40 transition-all duration-200 group
.link-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;    // gap-2
  padding: 1rem;  // p-4
  border-radius: 0.75rem;  // rounded-xl
  background: #222a20;     // seed-card
  border: 1px solid #3e4a38;  // seed-border
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); // shadow-sm
  text-decoration: none;
  transition: all 200ms;

  &:hover {
    border-color: #c49a4a;  // seed-amber
    background: rgba(44, 54, 41, 0.40);  // seed-muted/40
  }

  i {   // Phosphor icon
    font-size: 1.25rem;  // text-xl
    color: #9aaa8a;      // seed-textMuted
    transition: color 200ms;
  }

  span {
    font-size: 0.875rem;  // text-sm
    font-weight: 500;     // font-medium
    color: #e0e8d6;       // seed-text
    transition: color 200ms;
  }

  &:hover i,
  &:hover span {
    color: #c49a4a;  // seed-amber on hover
  }
}
```

### Pattern 6: License Badge + Footer

**What:** Centered pill badge for license, copyright text below.

**Mockup source values (with D-12 correction — Apache not MIT):**
```scss
// Source: design.html footer section
// Container: mt-4 mb-8 text-center flex flex-col items-center gap-2
.about-footer {
  margin-top: 1rem;   // mt-4
  margin-bottom: 2rem; // mb-8
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;  // gap-2
}

// Badge: inline-flex items-center gap-2 px-3 py-1 rounded-full bg-seed-card/50 border border-seed-border/30
.license-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;   // gap-2
  padding: 0.25rem 0.75rem;  // py-1 px-3
  border-radius: 9999px;  // rounded-full
  background: rgba(34, 42, 32, 0.50);   // seed-card/50
  border: 1px solid rgba(62, 74, 56, 0.30);  // seed-border/30

  i {
    color: rgba(154, 170, 138, 0.60);  // seed-textMuted/60
  }

  span {
    font-size: 0.75rem;   // text-xs
    font-family: var(--bs-font-monospace);
    color: rgba(154, 170, 138, 0.80);  // seed-textMuted/80
    text-transform: uppercase;
    letter-spacing: 0.1em;  // tracking-widest
  }
}

.copyright-text {
  font-size: 0.75rem;   // text-[12px]
  color: rgba(154, 170, 138, 0.50);  // seed-textMuted/50
}
```

### Pattern 7: Fade-In-Up Page Animation

**What:** The mockup applies a CSS animation to the main container on load. Angular removes the initial `opacity: 0` via the animation.

```scss
// Source: design.html — tailwind animation config
@keyframes fade-in-up {
  0% {
    opacity: 0;
    transform: translateY(10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

// Applied to main element:
// animation: fade-in-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
// Claude's discretion: timing — 0.4s or 0.5s acceptable
```

### Pattern 8: TypeScript — Build-Time Constants

**What:** `AboutPageComponent` needs `angularVersion` as a build-time constant and `appVersion` from package.json.

```typescript
// Source: existing about-page.component.ts pattern + new constant
import { VERSION } from '@angular/core';

@Component({ ... })
export class AboutPageComponent {
  public version: string;
  public angularVersion: string;

  constructor() {
    this.version = appVersion;         // from package.json via require()
    this.angularVersion = VERSION.full; // Angular's built-in VERSION export
  }
}
```

[VERIFIED: Angular exports `VERSION` from `@angular/core` — standard Angular pattern. `VERSION.full` returns the full version string like "21.2.8"]

### Anti-Patterns to Avoid

- **Bootstrap utility class approximations:** Never use `bg-secondary`, `text-muted`, or `p-4` as substitutes for exact design-spec values. Write `background: #222a20`, `color: #9aaa8a`, `padding: 1rem` directly.
- **Using the Phosphor arrows-merge icon in the identity card:** D-04 explicitly requires the brand favicon asset (`assets/favicon.png`), not the icon from the mockup.
- **Using "MIT License":** The mockup shows MIT; D-12 overrides this to "Apache License 2.0".
- **Calling the Phosphor ph-scales icon for license:** The mockup uses `ph-fill ph-scales`; verify the Phosphor web CDN supports filled variants via `ph-fill` class prefix.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Angular version string | Custom version file or env injection | `VERSION.full` from `@angular/core` | Built in; always accurate |
| App version string | Manual constant | `require('../../../../package.json').version` | Already in component — keep it |
| CSS transitions on hover | JavaScript mouse enter/leave | CSS `transition` + `:hover` pseudo-class | No Angular binding overhead needed |
| Responsive grid | Custom JS breakpoint detection | CSS Grid `repeat(2,1fr)` + media query | Pure CSS, no JS |

**Key insight:** This is a fully static page — no services, no subscriptions, no RxJS. Keep the TypeScript minimal (just two public properties).

---

## Common Pitfalls

### Pitfall 1: Icon Asset Path in Angular

**What goes wrong:** Using `doc/brand/favicon.png` as the `src` for the identity card image fails because Angular's asset pipeline only serves files from `src/angular/src/assets/`.

**Why it happens:** `doc/brand/` is not in `angular.json`'s `assets` array.

**How to avoid:** Use `assets/favicon.png` — this file already exists at `src/angular/src/assets/favicon.png` [VERIFIED: directory listing]. The `favicon.png` in assets is the correct brand icon.

**Warning signs:** Image fails to load in dev server; 404 in Network tab.

### Pitfall 2: Phosphor `ph-fill` Class Availability

**What goes wrong:** The license badge in the mockup uses `ph-fill ph-scales`. The fill variant requires the Phosphor web library to be loaded correctly.

**Why it happens:** The unpkg CDN script is already loaded. `ph-fill` is the standard Phosphor web class prefix for filled weight icons. This should work.

**How to avoid:** Use `<i class="ph-fill ph-scales"></i>` exactly as in the mockup. Verify visually after implementation. [ASSUMED — Phosphor CDN fill variant class behavior based on training knowledge; not re-verified this session against current CDN docs]

### Pitfall 3: Mockup Icons vs D-11 (Project Uses FA 4.7 for Settings/Logs)

**What goes wrong:** Prior phases (Settings, Logs) use Font Awesome 4.7 and explicitly map Phosphor icons to FA equivalents. This About page phase uses Phosphor icons (D-11 explicitly says ph-github-logo, ph-book, ph-bug, ph-git-commit).

**Why it happens:** About page CONTEXT D-11 explicitly specifies Phosphor; this is not a FA 4.7 page. The icon set is correct because Phosphor is already loaded globally.

**How to avoid:** Use Phosphor icon classes as specified in D-11. Do not map to FA 4.7 for this page.

### Pitfall 4: `opacity: 0` Initial State in Angular

**What goes wrong:** If Angular renders the component before the CSS animation fires, the element may flash with opacity 0 if CSS hasn't loaded yet, or stay invisible if the animation never fires.

**Why it happens:** The mockup sets `opacity: 0` as initial inline style. In Angular SCSS, the `opacity: 0` initial state should be part of the `@keyframes` definition (from value), not set as a separate property — otherwise it persists if animation is disabled.

**How to avoid:** Use `animation-fill-mode: forwards` (already in the design spec's `0.5s ... forwards`). This fills the end state (`opacity: 1`). The `opacity: 0` at start is defined in the `0%` keyframe, not as a static property.

### Pitfall 5: System Info Table Row Borders

**What goes wrong:** Using Bootstrap's `.table` or `<table>` element and then trying to override borders leads to specificity battles.

**Why it happens:** The mockup uses `div`-based rows with `divide-y` utility (CSS `border-top` on siblings). Bootstrap tables add their own border styles.

**How to avoid:** Implement the system info table as a `<div>` container with child `<div>` rows, as in the mockup. Use CSS `border-top` on all rows and remove it from the first child. Do not use `<table>/<tr>/<td>`.

---

## Code Examples

### Identity Card HTML Structure (Angular template pattern)

```html
<!-- Source: design.html identity section, with D-04/D-05/D-06/D-07 substitutions -->
<section class="identity-card">
  <div class="identity-card-glow"></div>
  <div class="identity-icon-container">
    <img src="assets/favicon.png" alt="SeedSyncarr" class="brand-favicon" />
  </div>
  <h2 class="identity-title">SeedSync<span class="text-amber">arr</span></h2>
  <p class="identity-tagline">
    Sync files from your seedbox to your local media server — fast, automated,
    and integrated with Sonarr and Radarr.
  </p>
  <div class="identity-version-block">
    <span class="version-badge">Version {{ version }} (Stable)</span>
  </div>
</section>
```

### System Info Rows (static placeholder pattern per D-02)

```html
<!-- Source: design.html rows, with D-02 placeholder values -->
<div class="sysinfo-table">
  <div class="sysinfo-row">
    <span class="sysinfo-label">App Version</span>
    <span class="sysinfo-value">{{ version }} (Stable)</span>
  </div>
  <div class="sysinfo-row">
    <span class="sysinfo-label">Frontend Core</span>
    <span class="sysinfo-value">Angular {{ angularVersion }}</span>
  </div>
  <div class="sysinfo-row">
    <span class="sysinfo-label">Python Version</span>
    <span class="sysinfo-value">—</span>
  </div>
  <div class="sysinfo-row">
    <span class="sysinfo-label">Host OS</span>
    <span class="sysinfo-value">—</span>
  </div>
  <div class="sysinfo-row">
    <span class="sysinfo-label">Uptime</span>
    <span class="sysinfo-value">—</span>
  </div>
  <div class="sysinfo-row">
    <span class="sysinfo-label">Process ID</span>
    <span class="sysinfo-value">—</span>
  </div>
  <div class="sysinfo-row">
    <span class="sysinfo-label">Config Path</span>
    <span class="sysinfo-value">~/.seedsyncarr</span>
  </div>
</div>
```

### Link Cards (Phosphor icons per D-11)

```html
<!-- Source: design.html link cards section, with D-09 URLs -->
<section class="link-cards-grid">
  <a href="https://github.com/thejuran/seedsyncarr" target="_blank" rel="noopener noreferrer" class="link-card">
    <i class="ph ph-github-logo"></i>
    <span>GitHub</span>
  </a>
  <a href="https://thejuran.github.io/seedsyncarr/" target="_blank" rel="noopener noreferrer" class="link-card">
    <i class="ph ph-book"></i>
    <span>Docs</span>
  </a>
  <a href="https://github.com/thejuran/seedsyncarr/issues" target="_blank" rel="noopener noreferrer" class="link-card">
    <i class="ph ph-bug"></i>
    <span>Report Issue</span>
  </a>
  <a href="https://github.com/thejuran/seedsyncarr/releases" target="_blank" rel="noopener noreferrer" class="link-card">
    <i class="ph ph-git-commit"></i>
    <span>Changelog</span>
  </a>
</section>
```

### License Footer (Apache 2.0 correction per D-12)

```html
<!-- Source: design.html footer, with D-12 license and actual copyright text from current about page -->
<section class="about-footer">
  <div class="license-badge">
    <i class="ph-fill ph-scales"></i>
    <span>Apache License 2.0</span>
  </div>
  <p class="copyright-text">
    &copy; 2017-2026 Inderpreet Singh, thejuran. Open source software.
  </p>
  <!-- Fork attribution: Claude's discretion to keep/restyle from current template -->
  <p class="fork-note">
    Based on the original
    <a href="https://github.com/ipsingh06/seedsync" target="_blank" rel="noopener noreferrer">SeedSync</a>
    by Inderpreet Singh
  </p>
</section>
```

### TypeScript — Component with Angular VERSION

```typescript
// Source: existing about-page.component.ts + Angular VERSION import
import { Component } from '@angular/core';
import { VERSION } from '@angular/core';
import { CommonModule } from '@angular/common';

declare function require(moduleName: string): { version: string };
const { version: appVersion } = require('../../../../package.json');

@Component({
  selector: 'app-about-page',
  templateUrl: './about-page.component.html',
  styleUrls: ['./about-page.component.scss'],
  standalone: true,
  imports: [CommonModule],
})
export class AboutPageComponent {
  public version: string;
  public angularVersion: string;

  constructor() {
    this.version = appVersion;
    this.angularVersion = VERSION.full;
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plain text/link list about page | Card-based redesign with identity, system info, link grid, footer | Phase 67 | Full visual upgrade |
| Custom `@Component` imports list | `standalone: true` with explicit imports array | Phase 62+ | Matches project pattern |

**Deprecated/outdated:**
- The current `about-page.component.html` features section, platform list, and simple links div — all replaced entirely by the new 4-section layout.
- The `#about #wrapper` SCSS structure — replaced by semantic section + utility class approach.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `VERSION.full` from `@angular/core` returns the full semver string (e.g., "21.2.8") | Code Examples / TS | If wrong, `angularVersion` would be undefined or partial; display would show blank/error in system info row |
| A2 | Phosphor `ph-fill ph-scales` class syntax works with the unpkg CDN version loaded in index.html | Pitfalls / License badge | If fill variant class syntax differs, the scales icon renders as outline or not at all |
| A3 | `assets/favicon.png` is visually appropriate for the 6rem × 6rem icon container (not too low-res) | Identity card | favicon.png is 32px; at 96px display size it may appear blurry; `favicon-192.png` would be sharper |

---

## Open Questions

1. **Brand favicon resolution for 96px display**
   - What we know: `assets/favicon.png` exists (32px source). `assets/favicon-192.png` also exists (192px).
   - What's unclear: Which asset looks better at 6rem × 6rem in the identity card?
   - Recommendation: Use `assets/favicon-192.png` for the identity card icon container — higher resolution at display size. CLAUDE's discretion applies here (D-04 says "brand favicon asset from doc/brand/" — closest match in assets/ is favicon-192.png for quality).

2. **Fork attribution note placement**
   - What we know: Current `about-page.component.html` shows it as a separate `#fork-note` div. CONTEXT marks placement as Claude's discretion.
   - What's unclear: Whether to fold it into the copyright line or keep it as a separate smaller-text line.
   - Recommendation: Keep as a separate `<p class="fork-note">` below the copyright line, styled with the same `color: rgba(154, 170, 138, 0.50)` but slightly smaller font. This preserves attribution clarity.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 67 is a pure Angular component rewrite (HTML/TS/SCSS). No external CLI tools, databases, or services are required beyond the existing Angular dev server.

---

## Validation Architecture

`workflow.nyquist_validation` key is absent from `.planning/config.json` — treated as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Angular CLI built-in test runner (Karma + Jasmine) |
| Config file | `src/angular/src/tsconfig.spec.json` |
| Quick run command | `cd src/angular && ng test --watch=false --browsers ChromeHeadless --include='**/about-page.component.spec.ts'` |
| Full suite command | `cd src/angular && ng test --watch=false --browsers ChromeHeadless` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ABUT-01 | Identity card renders brand title, version, tagline | Unit | `ng test --include='**/about-page.component.spec.ts'` | ❌ Wave 0 |
| ABUT-02 | System info table renders all 7 rows including placeholder dashes | Unit | `ng test --include='**/about-page.component.spec.ts'` | ❌ Wave 0 |
| ABUT-03 | Link cards render with correct hrefs and target="_blank" | Unit | `ng test --include='**/about-page.component.spec.ts'` | ❌ Wave 0 |
| ABUT-04 | License badge shows "Apache License 2.0", copyright text present | Unit | `ng test --include='**/about-page.component.spec.ts'` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Quick run (about-page spec only)
- **Per wave merge:** Full Angular test suite
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/angular/src/app/pages/about/about-page.component.spec.ts` — covers ABUT-01 through ABUT-04
- [ ] Framework install: None — Karma/Jasmine already configured in project

---

## Security Domain

This phase adds no authentication, session handling, API calls, or user input. All content is static — version strings, hardcoded URLs, and CSS. No ASVS categories apply.

V5 Input Validation: N/A — no user input on this page.
V4 Access Control: N/A — public page behind existing app routing.

---

## Sources

### Primary (HIGH confidence)
- `design.html` at `.aidesigner/runs/2026-04-14T03-35-42-278Z-seedsyncarr-about-page-triggarr-styl/design.html` — full mockup read, all design tokens extracted
- `src/angular/src/app/pages/about/about-page.component.*` — all three files read directly
- `src/angular/src/index.html` — confirmed Phosphor Icons CDN script present
- `src/angular/src/app/common/_bootstrap-variables.scss` — confirmed palette token values
- `src/angular/src/styles.scss` — confirmed CSS custom properties, font stack, flex grow setup
- `src/angular/package.json` — confirmed Angular ^21.2.8, app version 1.0.0

### Secondary (MEDIUM confidence)
- Angular `VERSION` export from `@angular/core` — standard Angular API, consistent across v2+

### Tertiary (LOW confidence)
- Phosphor Icons `ph-fill` class syntax for filled icon variants [ASSUMED from training knowledge; not re-verified against current CDN docs]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all files read directly
- Architecture: HIGH — mockup read completely, all Tailwind values extracted to CSS
- Pitfalls: HIGH for known Angular patterns; MEDIUM for Phosphor fill variant behavior
- Content values: HIGH — copyright text verified from existing component, URLs from CONTEXT.md

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable stack; Angular version pinned)
