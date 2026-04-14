# Phase 36: Secondary Pages - Research

**Researched:** 2026-02-17
**Domain:** Angular 19 SCSS-only terminal UI — Settings section headers, AutoQueue monospace buttons, Logs colored-by-level terminal view, About ASCII art page
**Confidence:** HIGH

## Summary

Phase 36 applies the Terminal/Hacker aesthetic established in Phases 33–35 to the four remaining pages: Settings, AutoQueue, Logs, About. All four requirements are pure HTML/SCSS changes — no new libraries, no new Angular services, and minimal TypeScript changes. The work spans six files (HTML + SCSS pairs for each page), plus one optional minor TypeScript change to Settings to remove the dead Appearance/Theme toggle section.

The most structural change is Settings (PAGE-01): the Bootstrap accordion-card layout stays functionally intact, but each card header gets a terminal-style `--- Section Name ---` label. The Appearance section (theme toggle buttons) should be removed since Phase 33 hardcoded `data-bs-theme="dark"` and Phase 33-03 set `ThemeService` to dark-only — the light/auto toggle is dead UI. The AutoQueue page (PAGE-02) needs Fira Code on the pattern text (already partially done — `font-family: monospace` exists), and the + / − buttons need `btn-outline-success` / `btn-outline-danger` (the ghost-button pattern from Phase 35). The Logs page (PAGE-03) already uses `font-family: monospace` at 70%/95%, but uses background block coloring for warning/error — the requirement explicitly asks for `no background blocks`, so the `background-color` rules must be removed and colors applied only via `color`. The About page (PAGE-04) is a cosmetic redesign: replace the logo image with ASCII art, apply Fira Code to version/title, style feature list items with `>` terminal-prompt markers instead of CSS bullets.

**Primary recommendation:** Implement all four requirements as pure SCSS + targeted HTML edits within the existing component files. The only TypeScript that may need touching is Settings (remove dead Appearance section from settings-page.component.ts `onSetTheme` method — LOW priority) and About (version string already pulled from `package.json` via `require` — no change needed).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PAGE-01 | User sees terminal-style section headers in Settings (`--- Server ---`) | The existing `card-header` button text (e.g., "Server") must change to `--- Server ---` format. The `header` field in `IOptionsContext` (options-list.ts) drives the template. Either update the `header` strings in `options-list.ts`, or modify the template to wrap `{{header}}` with dashes. Styling: font-family Fira Code (`var(--bs-font-monospace)`), color `#3fb950`. Also remove the dead Appearance card (theme toggle) from the right column — Phase 33 made it permanently dark. |
| PAGE-02 | User sees monospace patterns in AutoQueue with green/red buttons | Pattern text already has `font-family: monospace` in SCSS — upgrade to `var(--bs-font-monospace)` (Fira Code). Buttons: change `btn btn-danger` (remove) → `btn-outline-danger` (ghost red), `btn btn-success` (add) → `btn-outline-success` (ghost green), following Phase 35 ghost-button pattern. Add glow hover effects matching file-actions-bar ghost buttons. |
| PAGE-03 | User sees true terminal-style Logs (monospace, colored by level green/amber/red, no background blocks) | Currently `&.warning` and `&.error/&.critical` rules use `background-color` and `border-color` in addition to `color`. Remove `background-color` and `border-color` from log level rules. Set specific terminal colors: DEBUG = `#8b949e` (muted gray), INFO = `#e6edf3` (body text, unchanged), WARNING = `#f0883e` (amber), ERROR/CRITICAL = `#f85149` (red). The `color` rules already exist — just delete the background/border lines. |
| PAGE-04 | User sees ASCII-art inspired About page with monospace version display | Replace `<img src="assets/logo.png">` + `<span>SeedSync</span>` banner with ASCII art block. Version display: add `font-family: var(--bs-font-monospace)` + green color to `#version`. Section titles: use `>` terminal prefix. Feature/platform list items: change CSS bullet from `\2022` to `>` character. The `version` variable is already injected from `package.json` — no TypeScript change. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular 19 | 19.2.x | Component templates, `[class]` binding | Project standard |
| Bootstrap 5.3 | 5.3.3 | `btn-outline-*` ghost buttons, card/accordion | Project standard |
| SCSS | (Sass via Angular CLI) | Color-by-level rules, font overrides | Project standard |
| Fira Code | Google Fonts CDN (already loaded) | Monospace for pattern text, version, section headers | Already in `index.html` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bootstrap `btn-outline-*` | 5.3.3 | Ghost buttons with colored borders | PAGE-02 — already available, no install |
| CSS `var(--bs-font-monospace)` | (Fira Code via custom property) | Reference Fira Code consistently | PAGE-01, PAGE-02, PAGE-03, PAGE-04 |
| Bootstrap card/accordion | 5.3.3 | Settings accordion — keep as-is | PAGE-01 — structural, do not replace |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Editing `header` strings in `options-list.ts` | Template wrapping `--- {{header}} ---` | Template approach is less invasive; string changes in TS is cleaner for the `---` format. Both work. Recommendation: modify the template to inject dashes so `options-list.ts` remains a clean data file. |
| Inline ASCII art in HTML | CSS `::before`/`content` approach | Inline HTML preserves copy-paste ability; `::before` pseudo-element keeps HTML clean. For the About banner, inline `<pre>` ASCII is more maintainable. |
| `btn-outline-success` (muted green `#238636`) | `btn-outline-primary` (bright green `#3fb950`) | Phase 35 used `btn-outline-success` for Queue — PAGE-02 should match for consistency. The actual rendered border uses the project's `$success: #238636`. If bright green is needed, use `btn-outline-primary`. |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
src/angular/src/app/pages/
├── settings/
│   ├── settings-page.component.html    # PAGE-01: section header format, remove Appearance card
│   ├── settings-page.component.scss    # PAGE-01: card-header font override
│   └── settings-page.component.ts      # PAGE-01: remove onSetTheme(), theme/resolvedTheme signals (optional)
├── autoqueue/
│   ├── autoqueue-page.component.html   # PAGE-02: btn-outline-success/danger, Fira Code input
│   └── autoqueue-page.component.scss   # PAGE-02: ghost button glow, font-family upgrade
├── logs/
│   └── logs-page.component.scss        # PAGE-03: remove background-color/border-color from level rules, add direct colors
└── about/
    ├── about-page.component.html       # PAGE-04: ASCII banner, terminal markers, monospace version
    └── about-page.component.scss       # PAGE-04: font-family, color, section markers
```

### Pattern 1: Terminal Section Headers in Settings (PAGE-01)

**What:** Wrap the card header button text with `---` dashes in the template, styled in Fira Code green.
**When to use:** PAGE-01 only.

The `optionsList` `ng-template` in `settings-page.component.html` renders:
```html
<button class="btn" ...>
    {{header}}
</button>
```

Change to:
```html
<button class="btn terminal-header" ...>
    --- {{header}} ---
</button>
```

And the hardcoded card headers ("*arr Integration", "Appearance"):
```html
<button class="btn terminal-header" ...>
    --- *arr Integration ---
</button>
```

SCSS in `settings-page.component.scss`:
```scss
.card-header {
    .btn.terminal-header {
        font-family: var(--bs-font-monospace);  // Fira Code
        color: #3fb950;                          // terminal green
        font-size: 80%;                          // unchanged from current 80%
        cursor: default;

        &:focus {
            box-shadow: none;
        }
    }
}
```

**Remove the Appearance card entirely:** The theme toggle UI (light/dark/auto buttons) is dead — Phase 33-03 hardcoded `applyTheme('dark')`. The entire Appearance card block (lines 191–246 of `settings-page.component.html`) should be deleted. In `settings-page.component.ts`, remove the `onSetTheme()` method and the `ThemeService` inject lines. This simplifies the component and removes confusing dead UI.

**Subsection headers** (`<h4 class="subsection-header">Sonarr</h4>`) should also get Fira Code treatment:
```scss
.subsection-header {
    font-family: var(--bs-font-monospace);
    color: #8b949e;  // muted gray, not bright green (subordinate element)
}
```

### Pattern 2: AutoQueue Ghost Buttons + Fira Code Patterns (PAGE-02)

**What:** Replace `btn btn-danger` / `btn btn-success` with ghost outline variants. Upgrade pattern font to Fira Code.
**When to use:** PAGE-02 only.

Current HTML:
```html
<button class="btn btn-danger" type="button" ...>
    <span>&#8722;</span>
</button>
<button class="btn btn-success" type="button" ...>
    <span>&#43;</span>
</button>
```

Target HTML:
```html
<button class="btn btn-outline-danger ghost-btn" type="button" ...>
    <span>&#8722;</span>
</button>
<button class="btn btn-outline-success ghost-btn" type="button" ...>
    <span>&#43;</span>
</button>
```

SCSS additions in `autoqueue-page.component.scss`:
```scss
.ghost-btn {
    transition: box-shadow 0.15s ease;

    &.btn-outline-success:hover:not(:disabled) {
        box-shadow: 0 0 8px rgba(63, 185, 80, 0.5);   // green glow
    }
    &.btn-outline-danger:hover:not(:disabled) {
        box-shadow: 0 0 8px rgba(248, 81, 73, 0.5);   // red glow
    }
}

.pattern {
    .text {
        font-family: var(--bs-font-monospace);  // Fira Code (was generic "monospace")
        // ... rest unchanged
    }
}
```

The `#add-pattern` input already has `class="form-control"` — the Bootstrap override in `_bootstrap-overrides.scss` already makes it dark-styled. No input changes needed.

**Description text terminal style:** The `#description` span can get a terminal prefix `>` and Fira Code:
```scss
#description {
    font-family: var(--bs-font-monospace);
    color: #8b949e;  // muted
    &::before {
        content: '> ';
        color: #3fb950;
    }
}
```

### Pattern 3: Log Level Colors Without Background Blocks (PAGE-03)

**What:** Remove `background-color` and `border-color` from log level CSS rules. Rely on `color` only for level indication.
**When to use:** PAGE-03 only.

Current SCSS that must change:
```scss
// CURRENT (has background blocks):
&.warning {
    color: var(--bs-warning-text-emphasis);
    background-color: var(--bs-warning-bg-subtle);    // REMOVE
    border-color: var(--bs-warning-border-subtle);    // REMOVE
}
&.error, &.critical {
    color: var(--bs-danger-text-emphasis);
    background-color: var(--bs-danger-bg-subtle);     // REMOVE
    border-color: var(--bs-danger-border-subtle);     // REMOVE
}
```

Target SCSS (terminal-pure, color only):
```scss
&.debug {
    color: #8b949e;  // muted gray (was var(--bs-secondary-color))
}
&.info {
    color: #e6edf3;  // body text (was var(--bs-body-color))
}
&.warning {
    color: #f0883e;  // amber — direct value matches $warning
}
&.error, &.critical {
    color: #f85149;  // red — direct value matches $danger
}
```

**Why direct values instead of CSS variables:** The `_common.scss` SCSS variables (`$warning-text-emphasis: #f0883e`) are already the correct values. But in component SCSS files, CSS custom properties like `var(--bs-warning-text-emphasis)` can vary by theme. Since we're dark-only, the direct values are stable and consistent with other Phase 35 patterns.

**Scroll buttons:** `btn-scroll` currently uses `btn btn-primary` (filled green). Keep as-is — the scroll-to-top/bottom buttons are functional navigation, not decorative.

**Font-size note:** The 70% font size on mobile and 95% on medium+ is already good for terminal density. Consider upgrading the status message text:
```scss
.status-message {
    font-family: var(--bs-font-monospace);
    color: #8b949e;
    &::before {
        content: '> ';
        color: #3fb950;
    }
}
```

### Pattern 4: ASCII Art About Page (PAGE-04)

**What:** Replace image banner with ASCII art, style version in Fira Code, change list markers to `>`.
**When to use:** PAGE-04 only.

**ASCII banner (replaces `<img>` + `<span>`):**
```html
<!-- Replace the #banner div contents -->
<div id="banner">
    <pre class="ascii-logo">
 ____                _ ____
/ ___|  ___  ___  __| / ___| _   _ _ __   ___
\___ \ / _ \/ _ \/ _` \___ \| | | | '_ \ / __|
 ___) |  __/  __/ (_| |___) | |_| | | | | (__
|____/ \___|\___|\__,_|____/ \__, |_| |_|\___|
                              |___/
    </pre>
</div>
```

SCSS:
```scss
#banner {
    .ascii-logo {
        font-family: var(--bs-font-monospace);
        color: #3fb950;           // terminal green
        font-size: 0.5rem;        // small enough to fit on mobile (~350px wide)
        line-height: 1.2;
        text-align: left;
        display: inline-block;
        margin: 0 auto;
        user-select: none;
        white-space: pre;
    }
}
```

**Version display:**
```scss
#version {
    font-family: var(--bs-font-monospace);
    color: #3fb950;
    font-size: 150%;  // unchanged from current
    margin-bottom: 15px;
    &::before { content: 'v'; display: none; }  // version string already has "v" prefix from template
}
```

Note: The template already renders `v{{version}}`, so no HTML change is needed for the version prefix.

**Feature/platform list markers:**
```scss
#features, #platforms {
    ul li::before {
        content: '> ';            // terminal prompt marker
        color: #3fb950;
        font-family: var(--bs-font-monospace);
        font-weight: normal;      // override current bold
        width: auto;
        margin-left: 0;
        display: inline;
    }
}
```

**Section titles:**
```scss
.section-title {
    font-family: var(--bs-font-monospace);
    color: #3fb950;
    &::before { content: '-- '; }
    &::after  { content: ' --'; }
}
```

**ASCII art sizing concern:** The SeedSync ASCII art at 0.5rem font size will render at approximately 230px wide (assuming ~8px per char at 0.5rem ≈ 8px). The wrapper is `max-width: 500px`, mobile-first. Test at 320px width to verify it doesn't overflow. Alternative: use a shorter 4-line ASCII mark instead of the full word-art.

### Anti-Patterns to Avoid

- **Replacing the Bootstrap accordion in Settings:** The collapsible cards are functional on mobile and always-open on desktop. Do not replace with a flat layout — the accordion is structural, not cosmetic.
- **Removing the Bootstrap `card` class:** The `card` classes drive the collapse/expand behavior on mobile. Keep them; style inside them.
- **Using `background-color` for log levels:** PAGE-03 explicitly requires no background blocks — removing them is the requirement, not just making them transparent.
- **Hardcoding a multi-line string for ASCII art in TypeScript:** Put ASCII art directly in the HTML template inside a `<pre>` element. TypeScript has no business knowing the logo shape.
- **Using `:host` styling on Settings/AutoQueue/Logs/About:** These pages are not virtual-scroll components — they don't have the `82px :host` constraint. Normal SCSS scoping applies.
- **Modifying `options-list.ts` header strings:** The `---` decoration belongs in the template, not the data. If the planner format is `--- Server ---`, put the dashes in the `ng-template` rendering, not the data object. Keep `options-list.ts` as clean data.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ghost outline buttons | Custom CSS outlined buttons | Bootstrap `btn-outline-success` / `btn-outline-danger` | Already in bundle, Phase 35 established this pattern |
| Hover glow effects | Custom `:hover` box-shadow from scratch | Copy the `.ghost-btn` pattern from `file-actions-bar.component.scss` | Established in Phase 35; identical color values |
| Monospace font references | `font-family: 'Fira Code', monospace` | `font-family: var(--bs-font-monospace)` | CSS custom property already set to Fira Code via `$font-family-monospace` in `_bootstrap-variables.scss` |
| Log level color values | New color constants | Direct palette values `#f0883e` / `#f85149` / `#8b949e` | Same values used in `_common.scss` and across Phase 33-35 patterns |
| ASCII art logo | Image generation or external assets | Inline `<pre>` in HTML | Zero dependencies, works without CDN, scales with font |

**Key insight:** All visual primitives for this phase are already in the project. The work is reshuffling existing CSS variables, classes, and patterns onto four new pages.

## Common Pitfalls

### Pitfall 1: `background-color` Removal in Logs Leaves No Visual Separation
**What goes wrong:** Removing the background block from warning/error log lines means adjacent lines are harder to distinguish at a glance.
**Why it happens:** The background was the primary visual differentiator; color-only is more subtle.
**How to avoid:** The requirement explicitly asks for no background blocks. The color contrast of amber (`#f0883e`) and red (`#f85149`) on the dark body (`#0d1117`) is sufficient. Do not re-add backgrounds — trust the terminal aesthetic.
**Warning signs:** If the reviewer says "warning lines are too hard to find", the answer is "that's the terminal look" — it's intentional.

### Pitfall 2: ASCII Art Overflows Mobile Width
**What goes wrong:** A wide ASCII logo like the full "SeedSync" word art exceeds 320px mobile width and causes horizontal scroll.
**Why it happens:** ASCII art character width × font-size > viewport width.
**How to avoid:** Use a compact ASCII mark (short version or just initials), or scale font-size down. At 0.5rem (~8px per char), 45-char wide art ≈ 360px — borderline. Use `font-size: 0.45rem` or `overflow: hidden` as a fallback. Test at 320px width.
**Warning signs:** Horizontal scrollbar appears on About page at mobile width.

### Pitfall 3: Settings Appearance Card Removal Causes TypeScript Import Errors
**What goes wrong:** If you delete the Appearance card from HTML but leave `ThemeService` inject and `onSetTheme()` in the component TS, ESLint will warn about unused methods. If you remove the TS without removing the template bindings, Angular compilation fails.
**Why it happens:** Template bindings reference TS properties — mismatch causes compile errors.
**How to avoid:** Remove both HTML and TS together atomically. In `settings-page.component.ts`, remove: `private _themeService = inject(ThemeService)`, `public theme = this._themeService.theme`, `public resolvedTheme = this._themeService.resolvedTheme`, and `onSetTheme()` method. Also remove the `ThemeService` and `ThemeMode` imports if nothing else uses them.
**Warning signs:** TypeScript errors on build after partial removal.

### Pitfall 4: `btn-outline-success` vs `btn-outline-primary` Color Confusion
**What goes wrong:** The "green" add button in AutoQueue may appear dimmer than expected because `$success: #238636` (muted green), not `$primary: #3fb950` (bright green).
**Why it happens:** Phase 35 used `btn-outline-success` for the Queue action — but for AutoQueue's explicit + button, bright green may be more appropriate.
**How to avoid:** Use `btn-outline-success` to match Phase 35 convention. If the planner decides the + button should be brighter, use `btn-outline-primary` instead. Document the choice.
**Warning signs:** Add button looks dim compared to terminal green elsewhere.

### Pitfall 5: `ng-template` Header Format Must Match for All 7 Settings Sections
**What goes wrong:** The `optionsList` ng-template is used 6 times (Server, AutoQueue, Extract, Connections, Discovery, Other). If the `--- {{header}} ---` change is in the template, it applies to all 6 uniformly. But the 2 hardcoded cards (`*arr Integration`, `Appearance`) need manual updates.
**Why it happens:** Only 6 of 8 card headers use the template; 2 are hardcoded HTML.
**How to avoid:** After updating the ng-template, manually update all hardcoded card headers. If removing Appearance entirely, only 7 cards total remain (6 template + 1 `*arr Integration`).
**Warning signs:** Section headers inconsistent between template-driven and hardcoded sections.

### Pitfall 6: `cursor-blink` Utility Class in `styles.scss` Is Unused in This Phase
**What goes wrong:** The `cursor-blink` utility class in `styles.scss` is tempting to apply to Settings headers, but it creates visual noise on static content.
**Why it happens:** The blinking cursor is defined globally and easy to reference.
**How to avoid:** Do NOT apply `cursor-blink` to Settings headers or any static text. Reserve it for animated prompt indicators only.
**Warning signs:** None — just don't use it here.

## Code Examples

Verified patterns from the actual codebase:

### Existing Log Level SCSS (Current — Must Change for PAGE-03)
```scss
// Source: src/angular/src/app/pages/logs/logs-page.component.scss
p.record {
    &.debug {
        color: var(--bs-secondary-color);
    }
    &.info {
        color: var(--bs-body-color);
    }
    &.warning {
        color: var(--bs-warning-text-emphasis);
        background-color: var(--bs-warning-bg-subtle);    // REMOVE THIS
        border-color: var(--bs-warning-border-subtle);    // REMOVE THIS
    }
    &.error, &.critical {
        color: var(--bs-danger-text-emphasis);
        background-color: var(--bs-danger-bg-subtle);     // REMOVE THIS
        border-color: var(--bs-danger-border-subtle);     // REMOVE THIS
    }
}
```

### Settings Section Headers — Current ng-template (PAGE-01)
```html
<!-- Source: src/angular/src/app/pages/settings/settings-page.component.html -->
<ng-template #optionsList let-header="header" let-options="options" let-id="id">
    <div class="card">
        <h3 class="card-header" id="heading-{{id}}">
            <button class="btn" ...>
                {{header}}       <!-- change to: --- {{header}} --- -->
            </button>
        </h3>
        ...
    </div>
</ng-template>
```

### Settings options-list.ts — Header Strings (DATA ONLY — do NOT add dashes here)
```typescript
// Source: src/angular/src/app/pages/settings/options-list.ts
export const OPTIONS_CONTEXT_SERVER: IOptionsContext = {
    header: "Server",   // stays "Server" — dashes applied in template
    id: "server",
    ...
};
```

### AutoQueue Buttons — Current (PAGE-02)
```html
<!-- Source: src/angular/src/app/pages/autoqueue/autoqueue-page.component.html -->
<button class="btn btn-danger" type="button" ...>   <!-- change to btn-outline-danger ghost-btn -->
    <span>&#8722;</span>
</button>
<button class="btn btn-success" type="button" ...>   <!-- change to btn-outline-success ghost-btn -->
    <span>&#43;</span>
</button>
```

### Ghost Button SCSS Pattern (from Phase 35 — copy verbatim for PAGE-02)
```scss
// Source: src/angular/src/app/pages/files/file.component.scss and file-actions-bar.component.scss
.ghost-btn {
    transition: box-shadow 0.15s ease;

    &.btn-outline-success:hover:not(:disabled) {
        box-shadow: 0 0 8px rgba(63, 185, 80, 0.5);
    }
    &.btn-outline-danger:hover:not(:disabled) {
        box-shadow: 0 0 8px rgba(248, 81, 73, 0.5);
    }
    &.btn-outline-secondary:hover:not(:disabled) {
        box-shadow: 0 0 8px rgba(139, 148, 158, 0.4);
    }
}
```

### About Page Version Injection (TypeScript — No Change Needed)
```typescript
// Source: src/angular/src/app/pages/about/about-page.component.ts
declare function require(moduleName: string): { version: string };
const { version: appVersion } = require("../../../../package.json");

// Template: v{{version}} — already prefixed with "v"
```

### Established Terminal Color Palette (for reference across all pages)
```scss
// Source: src/angular/src/app/common/_bootstrap-variables.scss + styles.scss
$primary: #3fb950;    // bright green — for section headers, ASCII art logo
$secondary: #8b949e;  // muted gray — for debug logs, description text
$danger: #f85149;     // red — for error/critical logs, remove buttons
$warning: #f0883e;    // amber — for warning logs
$info: #58a6ff;       // blue — not used in this phase

// CSS custom property (same values as above):
var(--bs-font-monospace)  // Fira Code — use this everywhere for monospace
```

### Settings ThemeService Code to Remove (PAGE-01)
```typescript
// Source: src/angular/src/app/pages/settings/settings-page.component.ts
// REMOVE THESE LINES:
import {ThemeService} from "../../services/theme/theme.service";
import {ThemeMode} from "../../services/theme/theme.types";
// ...
private _themeService = inject(ThemeService);
public theme = this._themeService.theme;
public resolvedTheme = this._themeService.resolvedTheme;
// ...
onSetTheme(mode: ThemeMode): void {
    this._themeService.setTheme(mode);
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plain text card headers ("Server") | Terminal-format headers (`--- Server ---`) | Phase 36 | Visual consistency with terminal aesthetic |
| Filled `btn-danger` / `btn-success` in AutoQueue | Ghost `btn-outline-danger` / `btn-outline-success` | Phase 36 | Matches Phase 35 action button pattern |
| Generic `monospace` font in AutoQueue patterns | Fira Code via `var(--bs-font-monospace)` | Phase 36 | Explicit Fira Code across all monospace elements |
| Background-block log level coloring | Color-only log level coloring | Phase 36 | True terminal look — no background colors per PAGE-03 |
| Image logo + text banner on About | ASCII art logo in `<pre>` | Phase 36 | Zero-dependency, scales with font, aesthetic |
| Non-monospace version display ("v1.0.0") | Fira Code monospace version display | Phase 36 | Terminal style |
| CSS bullet `\2022` on feature list | `>` terminal prompt character | Phase 36 | Consistent terminal marker across all pages |
| Theme toggle UI in Settings (dead code) | Removed | Phase 36 | Phase 33 made it permanently dark; dead UI removed |

**Deprecated/outdated in this phase:**
- Theme toggle UI in Settings (`Appearance` card with Light/Dark/Auto buttons) — Phase 33 hardcoded dark, this card is dead
- `background-color` and `border-color` on log level rules — removed per PAGE-03
- `<img src="assets/logo.png">` on About page — replaced with ASCII art

## Open Questions

1. **ASCII art for About page — full word art vs. compact mark**
   - What we know: The full "SeedSync" ASCII word art is ~45 chars wide. At 0.5rem ≈ 8px/char, that's ~360px — tight on 320px mobile.
   - What's unclear: Whether the planner wants the full word art or a shorter version.
   - Recommendation: Use a 5-line ASCII mark for "SS" initials, or the full art at `0.45rem` font-size with `overflow: hidden` on the wrapper. If the planner wants copy-paste-able ASCII art in the research doc, here is a compact 3-line option:
     ```
     ╔══╗╔═══╗╔═══╗╔═══╗╔══╗╔╗ ╔╗╔═══╗
     ╚══╝║╔══╝║╔══╝║╔═╗║╚══╝║╚╗║║║╔══╝
     ╔══╗║╚══╗║╚══╗║║ ║║╔══╗║╔╝║║║║
     ╚══╝╚═══╝╚═══╝╚╝ ╚╝╚══╝╚╝ ╚╝╚═══╝
     ```
   - The planner should define the exact ASCII art or defer to the implementor.

2. **Settings `--- *arr Integration ---` label**
   - What we know: The `*arr Integration` section is a hardcoded card (not through `optionsList` template) with its own `heading-arr` id.
   - What's unclear: Whether `*arr` in a terminal header `--- *arr Integration ---` looks correct (asterisk could be mistaken for shell glob).
   - Recommendation: Render as `--- *arr Integration ---` — the asterisk is part of the official name. No change to the name text.

3. **Appearance section removal: TS cleanup scope**
   - What we know: `ThemeService` is injected in Settings and its `setTheme()`, `theme()`, and `resolvedTheme()` are exposed to the template. Phase 33-03 hardcoded dark.
   - What's unclear: Whether `ThemeService` is used elsewhere in the app (would affect whether the import can be removed from Settings).
   - Recommendation: The planner should check if other components use `ThemeService`. The Settings component can remove its inject safely regardless — other components' usage doesn't matter. The service itself stays in the codebase.

4. **Log scroll buttons aesthetics**
   - What we know: `#btn-scroll-top` and `#btn-scroll-bottom` use `btn-primary` (filled green).
   - What's unclear: Whether PAGE-03 requires them to become ghost buttons too.
   - Recommendation: PAGE-03 is about the log records aesthetic, not the scroll controls. Leave scroll buttons as-is. If the planner disagrees, switch to `btn-outline-primary`.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection:
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/settings/settings-page.component.html` — accordion structure, Appearance card, ng-template pattern
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/settings/settings-page.component.ts` — ThemeService inject, dead onSetTheme() method
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/settings/settings-page.component.scss` — current card-header button styling (font-size: 80%)
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/settings/options-list.ts` — header string values (7 sections)
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/autoqueue/autoqueue-page.component.html` — btn-danger / btn-success current classes
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/autoqueue/autoqueue-page.component.scss` — font-family: monospace (generic), controls layout
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/logs/logs-page.component.scss` — background-color and border-color rules on warning/error
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/about/about-page.component.html` — img logo, section-title pattern, li::before CSS bullet
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/about/about-page.component.ts` — version from package.json, no change needed
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/about/about-page.component.scss` — current banner, version, list bullet styles
  - `/Users/julianamacbook/seedsync/src/angular/src/styles.scss` — established CSS custom properties, keyframes
  - `/Users/julianamacbook/seedsync/src/angular/src/app/common/_bootstrap-variables.scss` — palette, font family
  - `/Users/julianamacbook/seedsync/src/angular/src/app/common/_bootstrap-overrides.scss` — form-control dark styling
  - `/Users/julianamacbook/seedsync/src/angular/src/app/pages/files/file.component.scss` — ghost-btn pattern (Phase 35, copy)
  - `/Users/julianamacbook/seedsync/.planning/phases/35-dashboard/35-RESEARCH.md` — Phase 35 ghost button pattern, established conventions

### Secondary (MEDIUM confidence)
- Prior phase context decisions (from phase_context in the task): Phases 33–35 established decisions confirmed by direct code inspection

### Tertiary (LOW confidence)
- None — all findings backed by direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing Angular/Bootstrap/SCSS, confirmed in codebase
- Architecture: HIGH — all four pages directly inspected; patterns verified against Phase 35 established work
- Pitfalls: HIGH — identified from direct inspection of component HTML/SCSS/TS (ThemeService dead code, background-color log rules, ASCII art mobile width)

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable — no fast-moving dependencies; Angular 19 / Bootstrap 5.3 APIs are stable)
