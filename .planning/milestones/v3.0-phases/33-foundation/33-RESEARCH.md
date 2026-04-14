# Phase 33: Foundation - Research

**Researched:** 2026-02-16
**Domain:** SCSS theming, Bootstrap 5.3 dark mode, Google Fonts, CSS visual effects
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIS-01 | User sees Fira Code font for all data displays (filenames, speeds, sizes, progress) | Fira Code loaded via Google Fonts preconnect+stylesheet; `$font-family-monospace` Bootstrap variable overrides `--bs-font-monospace` CSS var; apply `font-family: var(--bs-font-monospace)` to data elements |
| VIS-02 | User sees IBM Plex Sans for UI labels, buttons, and navigation | IBM Plex Sans loaded via Google Fonts; override `$font-family-sans-serif` Bootstrap variable → propagates to `--bs-font-sans-serif` → `font-family: var(--bs-font-base)` on `html, body`; replaces current Verdana |
| VIS-03 | User sees deep dark backgrounds (#0d1117 base) with green accent palette (#00ff41 neon, #3fb950 readable, #238636 muted) | Override `$body-bg-dark: #0d1117` and `$body-color-dark: #e6edf3` in `_bootstrap-variables.scss`; replace all `--app-*` CSS vars in `:root` in `styles.scss`; remove light-mode block entirely |
| VIS-04 | User sees CRT scan-line overlay effect (subtle, low opacity repeating gradient) | Implemented as `body::after { content: ''; position: fixed; ... background: repeating-linear-gradient(...); pointer-events: none; z-index: 9999; }` — no library needed |
| VIS-05 | User sees custom dark scrollbar styling (webkit + Firefox) | `::-webkit-scrollbar` pseudo-elements for Chrome/Safari/Edge; `scrollbar-color` + `scrollbar-width` CSS properties for Firefox (Gecko); both are pure CSS in `_bootstrap-overrides.scss` |
</phase_requirements>

---

## Summary

Phase 33 replaces the existing dual light/dark theme system with a single dark-only Terminal/Hacker palette. The work is entirely CSS/SCSS — no TypeScript changes in this phase. The current codebase uses Bootstrap 5.3's `data-bs-theme` attribute system (established in Phase 29) with a JavaScript FOUC-prevention script in `index.html`; this phase removes that script, hardcodes `data-bs-theme="dark"` on `<html>`, and replaces the entire `--app-*` CSS variable set with the new palette.

The key architectural insight is that Bootstrap 5.3's dark mode works by overriding CSS variables scoped to `[data-bs-theme="dark"]`. The custom `--app-*` variables defined in `styles.scss` (Section 5) are the per-theme values used by components. Phase 33 removes the `[data-bs-theme="light"]` block, promotes the `[data-bs-theme="dark"]` block to `:root`, and updates all values to the Terminal palette. Components already use `var(--app-*)` — they do not need changes in this phase.

Font loading is via Google Fonts preconnect links in `index.html`. Bootstrap's `$font-family-sans-serif` and `$font-family-monospace` SCSS variables control what gets emitted as `--bs-font-sans-serif` and `--bs-font-monospace` CSS custom properties. Overriding these in `_bootstrap-variables.scss` (before Bootstrap's `_variables.scss` is imported) is the correct injection point. The current global `font-family: Verdana, sans-serif` rule on `html, body` in `styles.scss` must be replaced with `IBM Plex Sans`.

**Primary recommendation:** Work file-by-file in dependency order — `index.html` first (fonts + hardcode dark), then `_bootstrap-variables.scss` (SCSS vars), then `_common.scss` (layout vars), then `_bootstrap-overrides.scss` (component overrides, scrollbars), then `styles.scss` (CSS custom properties, CRT overlay, keyframes). Verify build after each file.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Bootstrap 5.3 | 5.3.3 (installed) | CSS framework, dark-mode variable system | Already used; `data-bs-theme` system is the foundation for Phase 33 |
| Sass (Dart Sass) | 1.97.3 (installed) | SCSS compilation, `@use` module system | Already used; migrated to `@use` in Phase 12-13 |
| Angular CLI | 19.x | Build system, `ng serve` / `ng build` | Already used; no changes to build config needed |
| Google Fonts | CDN | Fira Code + IBM Plex Sans font delivery | Zero build-time cost, no npm packages needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CSS `@keyframes` | Native | Blinking cursor, green pulse animations | Built into CSS — no library |
| CSS `repeating-linear-gradient` | Native | CRT scan-line overlay | Built into CSS — no library |
| CSS `::-webkit-scrollbar` | Native | Webkit custom scrollbar | Chrome, Safari, Edge |
| CSS `scrollbar-color` / `scrollbar-width` | Native (Firefox) | Firefox custom scrollbar | Gecko-based browsers |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Google Fonts CDN | Self-hosted fonts via npm packages | CDN is zero-setup; self-hosting is better for privacy/offline but adds build complexity |
| CSS `::after` for CRT overlay | SVG pattern or Canvas | CSS is simplest, no DOM overhead, `pointer-events: none` keeps it non-interactive |
| Bootstrap `$body-bg-dark` override | CSS var override only | SCSS variable override is cleaner — propagates through Bootstrap's own generated CSS vars |

**Installation:** No new packages needed. All tools already installed.

---

## Architecture Patterns

### Recommended File Edit Order

```
1. index.html                          — Google Fonts preconnect + link, hardcode data-bs-theme="dark"
2. _bootstrap-variables.scss           — SCSS palette variables, $font-family overrides
3. _common.scss                        — Layout variables (sidebar widths: keep 170px for Phase 33)
4. _bootstrap-overrides.scss           — Remove [data-bs-theme="dark"] guards (now always dark), scrollbars
5. styles.scss                         — CSS custom properties, CRT overlay, keyframes, utility classes
```

### Pattern 1: Google Fonts Preconnect + Load

**What:** Two `<link>` elements per font domain — one `preconnect` for DNS+TCP, one `preconnect crossorigin` for CORS, then one `stylesheet` link.
**When to use:** Always for Google Fonts — reduces font load latency.

```html
<!-- Source: Google Fonts standard embed pattern -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
```

Both fonts can be combined in a single `css2?` request by separating families with `&family=`. Use `display=swap` to avoid invisible text during load (FOIT).

### Pattern 2: Bootstrap SCSS Variable Override for Fonts

**What:** Override `$font-family-sans-serif` and `$font-family-monospace` before Bootstrap imports, which causes Bootstrap's `_root.scss` to emit the new values as CSS custom properties.
**When to use:** When you want fonts to cascade through Bootstrap's own components (buttons, inputs, etc.)

```scss
// In _bootstrap-variables.scss (before Bootstrap's _variables.scss is imported):
// Source: Bootstrap 5.3 _variables.scss lines 606-607, _root.scss lines 44-45
$font-family-sans-serif: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
$font-family-monospace: 'Fira Code', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
```

Bootstrap's `_root.scss` emits these as `--bs-font-sans-serif` and `--bs-font-monospace`. The `$font-family-base` variable (which defaults to `var(--#{$prefix}font-sans-serif)`) then feeds into `body { font-family: $font-family-base }` via Bootstrap's `_reboot.scss`. This means overriding the SCSS variable is sufficient — the `font-family: Verdana,sans-serif` rule in `styles.scss` Section 4 should also be updated for belt-and-suspenders.

### Pattern 3: Bootstrap Dark Mode Body Background Override

**What:** Override `$body-bg-dark` and `$body-color-dark` SCSS variables to replace Bootstrap's default dark mode colors (`#212529` background, `#dee2e6` text) with the Terminal palette.

```scss
// In _bootstrap-variables.scss:
// Source: Bootstrap 5.3 _variables-dark.scss lines 43-44
$body-bg-dark: #0d1117;      // Terminal deep background (replaces Bootstrap's #212529)
$body-color-dark: #e6edf3;   // Terminal primary text
```

Bootstrap's dark mode is triggered by `[data-bs-theme="dark"]` on the `<html>` element. Since we're hardcoding this in `index.html`, it will always be active. Setting it in the SCSS variable layer means Bootstrap's own `_root.scss` emits `--bs-body-bg: #0d1117` inside the `[data-bs-theme="dark"]` block.

### Pattern 4: CSS Custom Properties for App-Specific Colors

**What:** The `--app-*` CSS variables in `styles.scss` (Section 5) are the per-component color system. Currently they have two blocks: `:root, [data-bs-theme="light"]` and `[data-bs-theme="dark"]`. Phase 33 removes the light block and moves the dark block to `:root`.

```scss
// In styles.scss — REPLACE current two-block system with:
// Source: Current codebase pattern (styles.scss lines 94-150), new values from design spec
:root {
  // Backgrounds
  --app-header-bg: #161b22;
  --app-top-header-bg: #0d1117;
  --app-sidebar-overlay-bg: rgba(0, 0, 0, 0.7);

  // File list
  --app-file-header-bg: #161b22;
  --app-file-header-color: #3fb950;
  --app-file-row-even: #161b22;
  --app-file-border-color: #30363d;
  --app-bulk-overlay-bg: rgba(13, 17, 23, 0.85);

  // Text
  --app-logo-color: #3fb950;
  --app-muted-text: #8b949e;
  --app-separator-color: #484f58;

  // Accents (green)
  --app-accent-teal-border: #238636;

  // Selection/accent — now green-based instead of teal
  --app-selection-bg: #238636;
  --app-selection-bg-subtle: rgba(63, 185, 80, 0.1);
  --app-selection-bg-alpha: rgba(63, 185, 80, 0.15);
  --app-selection-border: #3fb950;
  --app-selection-text-emphasis: #3fb950;
}
```

### Pattern 5: CRT Scan-Line Overlay

**What:** A full-viewport fixed `::after` pseudo-element on `body` with a repeating linear gradient creating very subtle horizontal lines.
**When to use:** After all other body styles — placed in `styles.scss`.

```scss
// Source: Design spec (sparkling-inventing-llama.md), standard CRT effect pattern
body::after {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.03) 0px,
    rgba(0, 0, 0, 0.03) 1px,
    transparent 1px,
    transparent 2px
  );
}
```

Key properties: `pointer-events: none` (clicks pass through), `z-index: 9999` (above everything), very low opacity (0.03 is subtle — adjust if too visible/invisible).

### Pattern 6: Custom Scrollbars

**What:** Webkit pseudo-elements for Chrome/Safari/Edge; standard CSS properties for Firefox.

```scss
// Webkit (Chrome, Safari, Edge) — in _bootstrap-overrides.scss
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: #0d1117;
}
::-webkit-scrollbar-thumb {
  background: #30363d;
  border-radius: 4px;
  &:hover {
    background: #3fb950;
  }
}

// Firefox (standard CSS) — in _bootstrap-overrides.scss
* {
  scrollbar-color: #30363d #0d1117;
  scrollbar-width: thin;
}
```

### Pattern 7: Keyframe Animations (Utility Classes)

**What:** `@keyframes` + utility classes in `styles.scss` for cursor blink and green pulse (used in later phases but foundation defines them).

```scss
// Source: Design spec
@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

@keyframes green-pulse {
  0%, 100% { box-shadow: 0 0 4px rgba(0, 255, 65, 0.3); }
  50% { box-shadow: 0 0 12px rgba(0, 255, 65, 0.6); }
}
```

### Anti-Patterns to Avoid

- **Changing `$sidebar-width` in `_common.scss` during Phase 33:** The sidebar width change (56px → icon rail) is Phase 34's work. Phase 33 must NOT change `$sidebar-width: 170px` or layout will break before Phase 34 is implemented.
- **Applying `font-family: 'Fira Code'` globally:** Only UI data elements (filenames, speeds, sizes) should use Fira Code. IBM Plex Sans is the default for all UI. Adding Fira Code globally would make buttons and labels monospace.
- **Forgetting to remove the FOUC script:** The JavaScript in `index.html` that reads localStorage and sets `data-bs-theme` must be removed when hardcoding dark. Leaving it in allows user's old localStorage setting to override the hardcoded attribute on refresh.
- **Using `[data-bs-theme="dark"]` guards in overrides after Phase 33:** Once `data-bs-theme="dark"` is hardcoded on `<html>` and the attribute is never changed, guards become redundant noise. Phase 33 removes all `[data-bs-theme="dark"]` wrappers in `_bootstrap-overrides.scss` and writes rules directly.
- **Touching component SCSS files:** Phase 33 is foundation only. Component files (files, settings, sidebar, etc.) use `var(--app-*)` already and will automatically pick up the new values. Components are for Phases 34-36.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font loading performance | Custom JS loader | Google Fonts with `preconnect` + `display=swap` | Google Fonts handles subsetting, caching, CDN; `display=swap` handles FOIT |
| CRT effect | Canvas/WebGL overlay | CSS `repeating-linear-gradient` on `body::after` | Zero JS, GPU-composited, `pointer-events: none` |
| Dark scrollbars | JS scrollbar replacement | Native CSS `::-webkit-scrollbar` + `scrollbar-color` | Native APIs have zero overhead and match OS behavior |
| Dark mode detection | Custom JS logic | Remove entirely — hardcode `data-bs-theme="dark"` | App is dark-only; no detection needed |

**Key insight:** This entire phase is pure CSS/SCSS. No TypeScript, no Angular component changes, no npm packages.

---

## Common Pitfalls

### Pitfall 1: FOUC From Leftover FOUC Script

**What goes wrong:** The existing FOUC-prevention script in `index.html` reads localStorage and sets `data-bs-theme` at page load. If the script is left in but localStorage has `'light'` from a previous session, the page briefly renders with Bootstrap's light defaults before Angular mounts.
**Why it happens:** The script runs synchronously before render (that's its purpose), so it overrides the hardcoded `data-bs-theme="dark"` on `<html>`.
**How to avoid:** Remove the entire `<script>` block from `index.html` when hardcoding `data-bs-theme="dark"` on `<html lang="en" data-bs-theme="dark">`.
**Warning signs:** Page flashes light/white on hard refresh in browsers where localStorage still has `'light'`.

### Pitfall 2: Bootstrap `$body-bg-dark` Not Propagating

**What goes wrong:** Override of `$body-bg-dark` in `_bootstrap-variables.scss` doesn't change the rendered background.
**Why it happens:** Bootstrap's dark variables (`_variables-dark.scss`) have `!default`, meaning they only take effect if not already set. But the import order in `styles.scss` matters: `_bootstrap-variables.scss` must be imported BEFORE `../node_modules/bootstrap/scss/variables-dark`. Check current `styles.scss` import order — it already does this correctly (line 21: `@import 'app/common/bootstrap-variables'` comes before line 25: `@import '../node_modules/bootstrap/scss/variables-dark'`).
**How to avoid:** Maintain existing import order. Do not move `@import 'app/common/bootstrap-variables'`.
**Warning signs:** Background stays Bootstrap's default `#212529` dark gray instead of `#0d1117`.

### Pitfall 3: `$font-family-sans-serif` Override Affects Code/Pre Elements

**What goes wrong:** Overriding `$font-family-monospace` in Bootstrap variables also affects `<code>`, `<pre>`, `<kbd>` elements that Bootstrap styles via `$font-family-code`.
**Why it happens:** Bootstrap's `$font-family-code` defaults to `var(--#{$prefix}font-monospace)`, which picks up the override. This is actually desired behavior — monospace elements will correctly use Fira Code.
**How to avoid:** This is expected and correct. Document it as intentional.
**Warning signs:** None — this is the desired outcome.

### Pitfall 4: `z-index` Conflict With CRT Overlay

**What goes wrong:** Bootstrap modals (z-index 1050-1060) or dropdowns appear behind the CRT overlay.
**Why it happens:** `z-index: 9999` on `body::after` is above everything including modals.
**How to avoid:** Use `pointer-events: none` (which is already required for the overlay to work). The CRT overlay is purely visual — even at z-index 9999, it doesn't intercept clicks. Modals will still function. Visually the scan lines appear over the modal, which is the correct terminal aesthetic.
**Warning signs:** CRT overlay not visible over modals (in that case z-index might need increasing, not decreasing).

### Pitfall 5: Scrollbar CSS Specificity in Sass `@use` Context

**What goes wrong:** Scrollbar styles in `_bootstrap-overrides.scss` don't apply when using `@use` module system.
**Why it happens:** `@use` does not cause styles to leak. `_bootstrap-overrides.scss` is `@use`d in `styles.scss` which is the global style entry point — this is correct and styles DO apply globally.
**How to avoid:** Confirm `styles.scss` has `@use 'app/common/bootstrap-overrides'` (it does, line 7). Scrollbar styles in `_bootstrap-overrides.scss` will be emitted globally.
**Warning signs:** None expected — existing pattern already works for `.modal-body` styles.

### Pitfall 6: Google Fonts Blocked in Docker/Offline Build

**What goes wrong:** `ng serve` works but Docker build or E2E tests in CI fail or show fallback fonts because Google Fonts CDN is unavailable.
**Why it happens:** The `<link>` tag is a runtime request (browser fetches it), not build-time. Angular does not bundle Google Fonts from a CDN link.
**How to avoid:** This is acceptable behavior — fonts degrade gracefully to `system-ui`/`monospace` fallbacks. The app renders correctly; it just looks different without the Google Fonts. No action needed for Phase 33.
**Warning signs:** Font fails to load in local dev only if behind a strict proxy. Check with browser devtools Network tab.

---

## Code Examples

Verified patterns from official sources and current codebase:

### index.html — Final State

```html
<!-- Source: Google Fonts standard embed, current codebase index.html -->
<!doctype html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <title>SeedSync</title>
    <base href="/">

    <!-- Fonts: Fira Code (monospace data) + IBM Plex Sans (UI) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">

    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#0d1117">
    <link rel="icon" type="image/png" href="assets/favicon.png">
</head>
<body>
    <app-root></app-root>
</body>
</html>
```

Changes: (1) `data-bs-theme="dark"` on `<html>`, (2) FOUC script removed, (3) Google Fonts links added, (4) `theme-color` updated to `#0d1117`.

### _bootstrap-variables.scss — Key Changes

```scss
// Source: Bootstrap 5.3 _variables.scss, current _bootstrap-variables.scss, design spec

// NEW: Font families
$font-family-sans-serif: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
$font-family-monospace: 'Fira Code', SFMono-Regular, Menlo, Monaco, Consolas, monospace;

// NEW: Dark body colors (override Bootstrap's gray-900/gray-300 defaults)
$body-bg-dark: #0d1117;
$body-color-dark: #e6edf3;

// CHANGED: Theme colors (Terminal/Hacker palette)
$primary: #3fb950;    // GitHub green (readable)
$secondary: #8b949e;  // Secondary text/muted
$danger: #f85149;     // GitHub red
$warning: #f0883e;    // Amber for speeds/warnings

// CHANGED: Component active state → green
$component-active-bg: #3fb950;
$component-active-color: #0d1117;  // Dark text on green background

// CHANGED: Logo font
$logo-font: 'Fira Code', monospace;

// REMOVE: $primary-light-color, $primary-lighter-color (light mode only)
// KEEP: $primary-dark-color (used for hover states)
// UPDATE: secondary and primary color deriving variables to match new palette
```

### styles.scss — CSS Custom Properties (Section 5 replacement)

```scss
// Source: Current styles.scss Section 5 pattern + design spec palette
// REPLACE the entire Section 5 (lines 91-151) with:

// ============================================================================
// SECTION 5: App CSS Custom Properties — Terminal/Hacker Palette (dark-only)
// ============================================================================
:root {
  // Layout backgrounds
  --app-header-bg: #161b22;
  --app-top-header-bg: #0d1117;
  --app-sidebar-overlay-bg: rgba(0, 0, 0, 0.7);

  // File list
  --app-file-header-bg: #161b22;
  --app-file-header-color: #3fb950;
  --app-file-row-even: #161b22;
  --app-file-border-color: #30363d;
  --app-bulk-overlay-bg: rgba(13, 17, 23, 0.85);

  // Text
  --app-logo-color: #3fb950;
  --app-muted-text: #8b949e;
  --app-separator-color: #484f58;

  // Accents
  --app-accent-teal-border: #238636;

  // Selection/accent (green)
  --app-selection-bg: #238636;
  --app-selection-bg-subtle: rgba(63, 185, 80, 0.1);
  --app-selection-bg-alpha: rgba(63, 185, 80, 0.15);
  --app-selection-border: #3fb950;
  --app-selection-text-emphasis: #3fb950;
}
```

### styles.scss — Keyframe Animations

```scss
// Source: Design spec
@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

@keyframes green-pulse {
  0%, 100% { box-shadow: 0 0 4px rgba(0, 255, 65, 0.3); }
  50% { box-shadow: 0 0 12px rgba(0, 255, 65, 0.6); }
}
```

### styles.scss — CRT Overlay

```scss
// Source: Design spec + standard CRT effect CSS pattern
body::after {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.03) 0px,
    rgba(0, 0, 0, 0.03) 1px,
    transparent 1px,
    transparent 2px
  );
}
```

### styles.scss — Utility Classes

```scss
// Source: Design spec
.glow-green {
  box-shadow: 0 0 8px rgba(0, 255, 65, 0.5);
}

.text-terminal {
  font-family: var(--bs-font-monospace);
  color: #3fb950;
}

.cursor-blink::after {
  content: '_';
  animation: cursor-blink 1s step-end infinite;
}
```

### _bootstrap-overrides.scss — Scrollbars (replace current [data-bs-theme="dark"] blocks)

```scss
// Source: MDN Web Docs — ::-webkit-scrollbar, scrollbar-color, scrollbar-width
// Remove all [data-bs-theme="dark"] guards — write rules directly

// Custom dark scrollbars — Webkit (Chrome, Safari, Edge)
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: #0d1117;
}
::-webkit-scrollbar-thumb {
  background: #30363d;
  border-radius: 4px;

  &:hover {
    background: #3fb950;
  }
}

// Custom dark scrollbars — Firefox
* {
  scrollbar-color: #30363d #0d1117;
  scrollbar-width: thin;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bootstrap `@import` | Bootstrap `@import` (still required) | Bootstrap 6 will add `@use` | App SCSS uses `@use`, Bootstrap internals use `@import` — hybrid is accepted (Phase 12-13) |
| `[data-bs-theme]` toggled by JS | `data-bs-theme="dark"` hardcoded on `<html>` | Phase 33 | No runtime JS needed; ThemeService cleanup in Phase 37 |
| Dual light/dark CSS var blocks | Single `:root` block (dark-only) | Phase 33 | Simpler, less code |
| Verdana fallback font | IBM Plex Sans primary | Phase 33 | Google-hosted, professional terminal aesthetic |

**Deprecated/outdated after Phase 33:**
- `[data-bs-theme="light"]` CSS block in `styles.scss`: Removed entirely
- FOUC script in `index.html`: Removed entirely
- Bootstrap `.dropdown-menu` dark-mode guard in `_bootstrap-overrides.scss`: Remove `[data-bs-theme="dark"]` wrapper, write directly
- `$primary-light-color`, `$primary-lighter-color` SCSS vars: Remove (light-mode only derivations)
- `$primary-color: $primary` re-export and similar aliases: Evaluate — keep if used by components, remove if not

---

## Open Questions

1. **Are `$primary-color`, `$secondary-color`, `$secondary-light-color`, `$secondary-dark-color`, `$secondary-darker-color`, `$header-color`, `$header-dark-color` SCSS variables used by component SCSS files?**
   - What we know: They are defined in `_bootstrap-variables.scss` and forwarded through `_common.scss`
   - What's unclear: Whether any component SCSS files reference them via `@use '../../common/common' as *`
   - Recommendation: Run `grep -r "\$secondary-color\|\$primary-color\|\$header-color\|\$secondary-light\|\$secondary-dark" src/angular/src/app/pages/` before editing. If unused by components, remove them. If used, keep and update values to Terminal palette equivalents.

2. **Does `app.component.scss` reference `$logo-font` directly, or only via `_common.scss` forward?**
   - What we know: `app.component.scss` has `font-family: $logo-font` at line 77; it uses `@use '../../common/common' as *`
   - What's unclear: Whether the `@forward 'bootstrap-variables'` in `_common.scss` properly makes `$logo-font` available in the wildcard namespace
   - Recommendation: This is already working (it's the current production build). Changing `$logo-font` in `_bootstrap-variables.scss` will propagate automatically.

3. **Should `--app-file-row-even` be `#161b22` or `#0d1117` (same as base)?**
   - What we know: Design spec says backgrounds are `#0d1117` (deep), `#161b22` (surface). Alternating rows was `#F6F6F6`/`white` in light mode.
   - What's unclear: Whether alternating rows are wanted in Terminal UI or if rows should be uniform
   - Recommendation: Use `#161b22` for even rows (subtle distinction from `#0d1117` base) — this matches the design spec's "surface" layer concept and the file list header.

---

## Sources

### Primary (HIGH confidence)
- Current codebase: `/Users/julianamacbook/seedsync/src/angular/src/styles.scss` — existing CSS var pattern, current font rules
- Current codebase: `/Users/julianamacbook/seedsync/src/angular/src/app/common/_bootstrap-variables.scss` — existing SCSS var pattern and import position
- Current codebase: `/Users/julianamacbook/seedsync/src/angular/src/app/common/_bootstrap-overrides.scss` — existing override pattern
- Bootstrap 5.3 source: `node_modules/bootstrap/scss/_variables.scss` lines 606-609 — font family variables
- Bootstrap 5.3 source: `node_modules/bootstrap/scss/_root.scss` lines 44-45 — CSS var emission for fonts
- Bootstrap 5.3 source: `node_modules/bootstrap/scss/_variables-dark.scss` lines 43-44 — dark body bg/color defaults
- Design spec: `/Users/julianamacbook/.claude/plans/sparkling-inventing-llama.md` — full color palette, typography spec, file list
- Project REQUIREMENTS.md: VIS-01 through VIS-05 — exact requirement text

### Secondary (MEDIUM confidence)
- Google Fonts standard embed pattern: `preconnect` + combined `css2?family=...&family=...&display=swap` format — verified as industry standard, format confirmed by two sources
- Roadmap: `/Users/julianamacbook/seedsync/.planning/milestones/v3.0-ROADMAP.md` — acceptance criteria, file list, phase dependencies

### Tertiary (LOW confidence)
- CRT scan-line gradient opacity value (`0.03`) — subjective aesthetic choice; actual value should be validated visually during implementation. May need adjustment between 0.02-0.05.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already installed and used; versions confirmed from `package.json` and installed `node_modules`
- Architecture patterns: HIGH — derived from reading actual codebase files and Bootstrap source; no guessing
- Pitfalls: HIGH for import order and FOUC script pitfalls (directly observed in codebase); MEDIUM for CRT z-index (reasoning from CSS spec behavior)
- Code examples: HIGH for SCSS/CSS patterns (based on existing codebase structure and Bootstrap source); MEDIUM for exact color values (from design spec, subjective visual validation still needed)

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (stable stack — Bootstrap 5.3, Angular 19, Sass are not fast-moving for this work)
