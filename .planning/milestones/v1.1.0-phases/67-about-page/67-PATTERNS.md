# Phase 67: About Page — Pattern Map

**Generated:** 2026-04-14
**Purpose:** Concrete code analogs for each file Phase 67 will rewrite. Downstream implementation agents must read this before writing a single line.

---

## File 1: `src/angular/src/app/pages/about/about-page.component.ts`

### Role

Standalone Angular component. Exposes two public properties to the template: `version` (app version from `package.json`) and `angularVersion` (Angular framework version via `VERSION.full`). No services, no subscriptions, no lifecycle hooks beyond constructor initialization.

### Closest Analog

`src/angular/src/app/pages/main/app.component.ts` — also reads `appVersion` from `package.json` via `require()` and holds it as a public property on the component.

Secondary analog for the `VERSION` import pattern: the existing `about-page.component.ts` itself, extended with the Angular core VERSION import.

### Key Code Excerpts from Analog

**package.json version read (from `app.component.ts` lines 9–10):**
```typescript
declare function require(moduleName: string): { version: string };
const { version: appVersion } = require("../../../../package.json");
```

**Standalone component decorator pattern (from `about-page.component.ts` lines 6–12):**
```typescript
@Component({
    selector: "app-about-page",
    templateUrl: "./about-page.component.html",
    styleUrls: ["./about-page.component.scss"],
    providers: [],
    standalone: true
})
```

Note: The existing `about-page.component.ts` has no `imports: []` array because it uses no Angular directives. Phase 67 keeps this — no `*ngIf`, no pipes, no child components needed. `CommonModule` is not required for a fully static template.

**Constructor assignment pattern (from `about-page.component.ts` lines 17–19):**
```typescript
constructor() {
    this.version = appVersion;
}
```

**Pattern to add — Angular VERSION (standard Angular API):**
```typescript
import { VERSION } from '@angular/core';
// ...
this.angularVersion = VERSION.full;  // returns "21.2.8"
```

### Data Flow

- **Inputs:** None (no `@Input()` bindings, no route params, no services injected)
- **Outputs:** None (no `@Output()` events)
- **Template bindings produced:**
  - `{{ version }}` — string from `package.json` via module-level `require()`
  - `{{ angularVersion }}` — string from `@angular/core` `VERSION.full`
- **Service dependencies:** None
- **Lifecycle:** Constructor-only initialization; no `OnInit`, no `OnDestroy`

---

## File 2: `src/angular/src/app/pages/about/about-page.component.html`

### Role

Full-page static template with four semantic sections: (1) identity card with brand favicon, title, version, tagline; (2) system info key-value table; (3) link cards grid; (4) license badge and copyright footer. Wraps all sections in a `<main>` element that is centered and max-width constrained.

### Closest Analog

`src/angular/src/app/pages/settings/settings-page.component.html` — the best structural analog for card-based layout with section headers and body content. Also:

- `src/angular/src/app/pages/main/app.component.html` — canonical source of the brand text pattern (`SeedSync<span class="brand-arr">arr</span>`) used in the identity card title.

### Key Code Excerpts from Analogs

**Brand text pattern — "SeedSync" + amber "arr" (from `app.component.html` line 8):**
```html
<h1 class="brand-text">SeedSync<span class="brand-arr">arr</span></h1>
```

**Card structure pattern (from `settings-page.component.html` lines 2–21):**
```html
<div class="settings-card">
  <div class="settings-card-header">
    <i class="fa {{icon}}"></i>
    <span>{{header}}</span>
  </div>
  <div class="settings-card-body">
    <!-- content rows -->
  </div>
</div>
```

**Card header with uppercase label + icon (from `settings-page.component.html` lines 30–33):**
```html
<div class="settings-card-header">
  <i class="fa fa-sliders"></i>
  <span>General Options</span>
</div>
```

**Phosphor icon usage in settings (from `settings-page.component.html` — `i.ph` class noted in SCSS line 42):**
```html
<i class="fa fa-server"></i>  <!-- FA 4.7 — settings uses FA -->
<i class="ph ph-github-logo"></i>  <!-- Phosphor — About page uses PH per D-11 -->
```

**`target="_blank"` link pattern (from existing `about-page.component.html` lines 33–38):**
```html
<a target="_blank" href="https://thejuran.github.io/seedsyncarr/">Documentation</a>
<a target="_blank" href="https://github.com/thejuran/seedsyncarr">GitHub</a>
<a target="_blank" href="https://github.com/thejuran/seedsyncarr/issues">Report an Issue</a>
```

**Version binding pattern (from existing `about-page.component.html` line 5):**
```html
<div id="version">v{{version}}</div>
```

**Copyright and fork note (from existing `about-page.component.html` lines 44–50 — preserved content, restyled):**
```html
<div id="copyright">Copyright © 2017-2026 Inderpreet Singh, thejuran</div>
<div id="fork-note">
    Based on the original
    <a target="_blank" href="https://github.com/ipsingh06/seedsync">SeedSync</a>
    by Inderpreet Singh
</div>
```

**Logs page status bar pattern — div-based row with flex justify-between (from `logs-page.component.html` lines 87–102):**
```html
<div class="status-bar">
  <div class="status-bar__left">...</div>
  <div class="status-bar__right">...</div>
</div>
```
Relevant as structural reference for the sysinfo row layout (label left, value right, flex justify-between).

### Data Flow

- **Inputs to template:**
  - `{{ version }}` — bound from component `.version` property
  - `{{ angularVersion }}` — bound from component `.angularVersion` property
  - All link URLs, labels, icons — static string literals (no binding)
- **User interactions:** All links open external URLs in new tabs (`target="_blank"`); no Angular event handlers
- **Child components:** None (no `<app-*>` selectors)
- **Angular directives used:** None (`@if`, `@for`, `@switch` not needed — fully static content)

---

## File 3: `src/angular/src/app/pages/about/about-page.component.scss`

### Role

Component-scoped SCSS for all visual styling of the About page. Defines the page wrapper layout, card sections, identity card glow + icon container, system info table rows, link card grid with hover-to-amber transitions, license badge, and copyright footer. Uses literal hex values from the design spec — no Bootstrap utility class approximations.

### Closest Analog

`src/angular/src/app/pages/logs/logs-page.component.scss` — the strongest structural analog because it:
1. Uses `@use '../../common/common' as *;` import (same as current about SCSS)
2. Defines local palette variables as `$amber`, `$card`, `$border`, `$row`, `$text`, `$textsec`, `$muted`, `$base` matching the exact hex values needed
3. Uses `:host` scoping with `flex-direction: column; flex-grow: 1`
4. Implements hover-to-amber transitions on interactive elements
5. Writes literal hex values, not Bootstrap variables

Secondary analog: `src/angular/src/app/pages/main/app.component.scss` — canonical source for `.brand-text`, `.brand-arr` amber color, `.brand-version` monospace badge, and `.brand-icon-box` amber-bordered container patterns.

### Key Code Excerpts from Analogs

**SCSS file opening — import and local palette variables (from `logs-page.component.scss` lines 1–14):**
```scss
@use '../../common/common' as *;

$amber: #c49a4a;
$text: #e0e8d6;
$textsec: #9aaa8a;
$border: #3e4a38;
$card: #222a20;
$base: #151a14;
$muted: #2c3629;
$row: #1a2019;
```

**`:host` flex column scoping (from `logs-page.component.scss` lines 16–26):**
```scss
:host {
    display: flex;
    flex-direction: column;
    flex-grow: 1;
    min-height: 0;
    max-width: 1600px;
    width: 100%;
    margin: 0 auto;
    padding: 1.25rem 1.5rem;
    gap: 1rem;
}
```

Note: About page uses a narrower `max-width: 42rem` centered layout instead of 1600px, per the mockup spec.

**Card container pattern — background, border, border-radius (from `settings-page.component.scss` lines 21–27):**
```scss
.settings-card {
    background: var(--app-header-bg);         // #222a20
    border: 1px solid var(--app-file-border-color);  // #3e4a38
    border-radius: 6px;
    min-width: 0;
    overflow: hidden;
}
```

**Card header — uppercase label style (from `settings-page.component.scss` lines 28–46):**
```scss
.settings-card-header {
    background: #1a2019;
    border-bottom: 1px solid var(--app-file-border-color);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--app-muted-text);
    border-radius: 6px 6px 0 0;
}
```

**Option separator / divider line (from `settings-page.component.scss` lines 62–65):**
```scss
.option-separator {
    height: 1px;
    background: rgba(62, 74, 56, 0.50);
    margin: 0 16px;
}
```
Directly maps to the `border-top: 1px solid rgba(62, 74, 56, 0.40)` divider on sysinfo rows.

**Amber hover transition on interactive button (from `logs-page.component.scss` lines 61–86):**
```scss
.level-btn {
    color: $textsec;
    background: transparent;
    border: none;
    transition: all 0.15s ease;

    &:hover {
        color: $text;
        background-color: $muted;
    }

    &--active {
        background-color: $amber;
        color: $base;
    }
}
```

**Brand icon box — amber-bordered container (from `app.component.scss` lines 41–52):**
```scss
.brand-icon-box {
    width: 32px;
    height: 32px;
    border-radius: 4px;
    border: 1px solid #c49a4a;
    background: rgba(196, 154, 74, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #c49a4a;
    font-size: 1rem;
    box-shadow: 0 0 15px rgba(196, 154, 74, 0.2);
}
```
This is the direct parent of the identity card's `.identity-icon-container`, scaled up to `6rem × 6rem`.

**Brand text + arr span (from `app.component.scss` lines 54–65):**
```scss
.brand-text {
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: -0.025em;
    color: #e0e8d6;
    margin: 0;
    line-height: 1;

    .brand-arr {
        color: #c49a4a;
    }
}
```

**Brand version badge — monospace pill (from `app.component.scss` lines 67–75):**
```scss
.brand-version {
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', $font-family-monospace;
    color: #9aaa8a;
    background: #2c3629;
    border: 1px solid #3e4a38;
    padding: 2px 8px;
    border-radius: 4px;
}
```

**Hover-to-amber on nav icon button (from `app.component.scss` lines 193–209):**
```scss
.nav-icon-btn {
    color: #9aaa8a;
    transition: color 0.15s ease, background 0.15s ease;

    &:hover {
        color: #c49a4a;
        background: #2c3629;
    }
}
```
This exact pattern is replicated in the link cards: icon and text both transition to `#c49a4a` on hover.

**`@keyframes` animation pattern in SCSS (from `app.component.scss` lines 179–190):**
```scss
@keyframes status-pulse {
    0%, 100% {
        opacity: 1;
        transform: scale(1);
        box-shadow: 0 0 0 0 rgba(89, 163, 98, 0.4);
    }
    50% { ... }
}
```
Structural reference for the `@keyframes fade-in-up` animation block needed in about.scss.

### Data Flow

- **No inputs or outputs** — purely presentational, no Angular bindings in SCSS
- **Palette source:** All hex values taken directly from the mockup's Tailwind config (documented in `67-RESEARCH.md` Patterns 1–7). The local `$amber`, `$card`, `$border`, etc. variables mirror the same values already used in `logs-page.component.scss`
- **Shared SCSS via `@use '../../common/common' as *`:** Provides `$font-family-monospace`, `$small-max-width`, `$medium-min-width` breakpoint variables. Does NOT provide the palette hex values directly — those must be re-declared locally as in the logs SCSS pattern
- **CSS custom properties available** (from `styles.scss` `:root`):
  - `--app-header-bg: #222a20`
  - `--app-muted-text: #9aaa8a`
  - `--app-logo-color: #c49a4a`
  - `--app-file-border-color: #3e4a38`
  - `--app-separator-color: #4a5440`
  - `--bs-font-monospace` (Bootstrap) — for sysinfo value cells

---

## Cross-File Notes

### `styles.scss` flex-grow setup (lines 97–104)

The global stylesheet already registers `app-about-page` in the flex-grow rule:

```scss
app-files-page,
app-settings-page,
app-logs-page,
app-about-page {
    display: flex;
    flex-direction: column;
    flex-grow: 1;
}
```

The about page SCSS `:host` block should reinforce this with `flex-grow: 1` but does NOT need to fight the global rule — they are additive.

### `app-routing.module.ts` — no changes needed

The `/about` route is already wired. `AboutPageComponent` is the existing routed component — Phase 67 rewrites its template/style/TS files in place.

### Icon Sets Per Page

| Page | Icon Set | Why |
|------|----------|-----|
| Settings | Font Awesome 4.7 (`fa fa-*`) | Phase 65 pattern |
| Logs | Font Awesome 4.7 (`fa fa-*`) | Phase 66 pattern |
| Nav bar | Font Awesome 4.7 (`fa fa-*`) | Phase 62 pattern |
| **About** | **Phosphor (`ph ph-*`)** | **D-11 explicit decision** |

Phosphor is loaded globally via unpkg CDN in `src/angular/src/index.html` (verified in RESEARCH.md Sources).

### Design Token Reference

All hex values in this patterns doc are confirmed against `src/angular/src/app/common/_bootstrap-variables.scss` and `src/angular/src/styles.scss`:

| Token | Hex | Variable Source |
|-------|-----|----------------|
| seed-base | `#151a14` | `$forest-base` / `--app-top-header-bg` |
| seed-card | `#222a20` | `$forest-card` / `--app-header-bg` |
| seed-row | `#1a2019` | `$forest-row` |
| seed-muted | `#2c3629` | `$forest-muted` |
| seed-border | `#3e4a38` | `$forest-border` / `--app-file-border-color` |
| seed-amber | `#c49a4a` | `$primary` / `$logo-color` / `--app-logo-color` |
| seed-text | `#e0e8d6` | `$body-color-dark` |
| seed-textMuted | `#9aaa8a` | `$secondary` / `--app-muted-text` |

---

*Phase: 67-about-page*
*Patterns mapped: 2026-04-14*
