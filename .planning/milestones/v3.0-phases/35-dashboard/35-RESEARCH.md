# Phase 35: Dashboard - Research

**Researched:** 2026-02-17
**Domain:** Angular 19 SCSS-only terminal UI redesign — ASCII progress bars, status dots, colored borders, glow effects, ghost buttons
**Confidence:** HIGH

## Summary

Phase 35 redesigns the file list dashboard to reinforce the Terminal/Hacker aesthetic established in Phases 33–34. All six requirements are pure HTML/SCSS changes — no new libraries, no new Angular services, no TypeScript logic changes. The work is confined to three files: `file-options.component.html` + `file-options.component.scss` (DASH-01 search prompt), `file.component.html` + `file.component.scss` (DASH-02 through DASH-05), and `file-actions-bar.component.html` + `file-actions-bar.component.scss` (DASH-06). The `styles.scss` already defines `@keyframes green-pulse` and `.glow-green` utility — DASH-04 consumes that keyframe directly.

The most complex requirement is DASH-03 (ASCII progress bar), which replaces Bootstrap's `<div class="progress">` component with a pure-CSS block-character bar using Fira Code (already loaded via Google Fonts CDN). The technique uses a CSS custom property `--pct` bound via Angular's `[style.--pct]` or computed via `background` gradient. The status-dot pattern (DASH-05) removes all eight SVG `<img>` tags and their conditionals, replacing them with a single CSS-colored `::before` pseudo-element and a status text span. The ghost button pattern (DASH-06) uses Bootstrap's `btn-outline-*` classes already in the project.

**Primary recommendation:** Implement all six requirements as pure SCSS + minimal HTML restructuring within the existing component files. No new Angular patterns, no new packages, no runtime JS.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | User sees search input with terminal prompt `>` prefix | Replace the SVG `<img>` icon with a `<span class="prompt">&gt;</span>` element styled with Fira Code monospace; adjust input `padding-left` to match. The `.form-control` override in `_bootstrap-overrides.scss` already handles dark background and placeholder color. |
| DASH-02 | User sees colored left border on file rows by status (green=downloading, teal=downloaded, amber=queued, red=stopped) | Add `border-left: 3px solid <color>` on `:host` in `file.component.scss`. Use `[class]` binding or `[ngClass]` on the host via `@HostBinding` or on the inner `.file` div. Status colors are already defined: `$primary: #3fb950` (green), `$success: #238636` (teal), `$warning: #f0883e` (amber), `$danger: #f85149` (red). |
| DASH-03 | User sees ASCII-style block progress bars (`[████░░░░] 67%`) replacing Bootstrap progress component | Remove `<div class="progress">` and replace with a `<span class="ascii-bar">` rendered via CSS. Two techniques: (A) pure CSS using `background: linear-gradient` with `--pct` custom property — no character drawing required; (B) Angular computed template expression building `████░░░░` string from `percentDownloaded`. Technique B (template expression) is simpler and more "real ASCII". |
| DASH-04 | User sees green glow effect on actively downloading rows (box-shadow pulse) | `@keyframes green-pulse` already exists in `styles.scss`. Apply `animation: green-pulse 2s ease-in-out infinite` on `:host` when `file.status === ViewFile.Status.DOWNLOADING`. Use `[class.downloading]="file.status === ViewFile.Status.DOWNLOADING"` on the host via `@HostBinding` or on `.file` div. |
| DASH-05 | User sees colored dot + text for file status (no SVG icons) | Remove all eight `<img src="assets/icons/…">` elements and their `*ngIf` chains. Replace with a single `<span class="status-dot"></span>` plus the existing `<span class="text">{{file.status | capitalize}}</span>`. The dot is a CSS circle (`border-radius: 50%`) colored by CSS class per status value. |
| DASH-06 | User sees ghost-style action buttons with green/red outlines and glow on hover | Replace `btn btn-primary`, `btn btn-danger`, `btn btn-secondary` with `btn-outline-success`, `btn-outline-danger`. Add `box-shadow` glow on `:hover` using existing palette colors. Applies to both `file.component.html` (inline actions, currently `display: none`) and `file-actions-bar.component.html` (visible action bar). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular 19 | 19.2.x | Component template, `[ngClass]`, `@HostBinding`, `ChangeDetectionStrategy.OnPush` | Project standard |
| Bootstrap 5.3 | 5.3.3 | `btn-outline-*` ghost buttons, `form-control` input styling | Project standard |
| SCSS | (Sass via Angular CLI) | Status-keyed CSS classes, animation, pseudo-elements | Project standard |
| Fira Code | Google Fonts CDN (already loaded) | Monospace font for `>` prompt and ASCII bar characters | Already in `index.html` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bootstrap `btn-outline-*` | 5.3.3 | Ghost buttons with colored borders | DASH-06 — already available, no install |
| CSS `@keyframes green-pulse` | (in `styles.scss`) | Downloading row glow animation | DASH-04 — already defined, just reference |
| CSS custom properties (`--pct`) | Native browser | Pass percentage to CSS for gradient-based progress | Optional for DASH-03 approach A |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Template-built ASCII bar string | CSS gradient progress bar | Template expression is more "real" terminal ASCII text; gradient is purely visual without actual characters. Template expression requires a TypeScript getter in the component. |
| `@HostBinding('class.status-X')` per-status | `[ngClass]` on `.file` div | `@HostBinding` applies class to host element directly (needed for `:host.downloading` SCSS to work). `[ngClass]` on inner div is simpler but requires SCSS to target `.file.downloading` instead of `:host.downloading`. Either works. |
| `btn-outline-success` / `btn-outline-danger` | Custom CSS ghost buttons | Bootstrap utility avoids hand-rolling outline hover logic; already in bundle. |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
src/angular/src/app/pages/files/
├── file-options.component.html    # DASH-01: replace <img> search icon with > prompt span
├── file-options.component.scss    # DASH-01: prompt styling, adjust input padding
├── file.component.html            # DASH-02, DASH-03, DASH-04, DASH-05: restructure status + size sections
├── file.component.scss            # DASH-02, DASH-03, DASH-04, DASH-05: border, animation, dot, ascii bar
├── file.component.ts              # DASH-03 (if template method chosen): add asciiBar() getter
├── file-actions-bar.component.html # DASH-06: replace btn-primary/danger/secondary with btn-outline-*
└── file-actions-bar.component.scss # DASH-06: add glow hover effects
```

### Pattern 1: Terminal Prompt in Search Input (DASH-01)

**What:** Replace the current SVG search icon (`<img src="assets/icons/search.svg">`) with a styled monospace `>` character in front of the input.
**When to use:** DASH-01 only.

Current HTML:
```html
<!-- file-options.component.html -->
<div id="filter-search">
    <img src="assets/icons/search.svg" />
    <div class="input-group">
        <input class="form-control" placeholder="Filter by name..." type="search" ...>
    </div>
</div>
```

Target HTML:
```html
<div id="filter-search">
    <span class="prompt">&gt;</span>
    <div class="input-group">
        <input class="form-control" placeholder="filter by name..." type="search" ...>
    </div>
</div>
```

Target SCSS:
```scss
// file-options.component.scss
#filter-search {
    .prompt {
        font-family: var(--bs-font-monospace);  // Fira Code
        color: #3fb950;                          // terminal green
        font-size: 1.1rem;
        font-weight: 500;
        position: absolute;
        left: 10px;
        top: 50%;
        transform: translateY(-50%);
        z-index: $zindex-file-search;
        pointer-events: none;
        user-select: none;
    }
    input {
        padding-left: 28px;  // was 30px for the img; adjust to match prompt width
    }
}
```

**Note:** The `position: relative` is already on `#filter-search`. The `z-index: $zindex-file-search` variable is already defined in `_common.scss` at 100.

### Pattern 2: Status-Colored Left Border (DASH-02)

**What:** Add a 3px left border to each file row, color-keyed by status. Applied to `:host` since the host element is the outermost border container in `file.component.scss`.
**When to use:** DASH-02.

```scss
// file.component.scss — add to :host block or as separate status-specific rules
:host {
    border-left: 3px solid transparent;  // reserve space — no visual jump on status change
}

:host.status-downloading { border-left-color: #3fb950; }  // green — $primary
:host.status-downloaded  { border-left-color: #238636; }  // teal/muted green — $success
:host.status-queued      { border-left-color: #f0883e; }  // amber — $warning
:host.status-stopped     { border-left-color: #f85149; }  // red — $danger
```

Apply via `@HostBinding` in the component TS:
```typescript
// file.component.ts
@HostBinding('class') get hostClass(): string {
    return this.file ? `status-${this.file.status}` : '';
}
```

OR via `[class]` binding on the inner `.file` div (simpler, no `@HostBinding` needed):
```html
<div class="file" [class]="'status-' + file.status" ...>
```
```scss
.file.status-downloading { border-left: 3px solid #3fb950; }
// etc.
```

**Recommended:** Use inner `.file` div approach — avoids touching the `:host` block which has carefully tuned `height: 82px` for virtual scroll. The border must be accounted for in the total height (box-sizing: border-box already applies from global `div { box-sizing: border-box; }`).

**Height budget:** `:host` is `82px` total. Adding `border-left: 3px` does NOT affect height (it affects width). `border-bottom: 1px` already exists. No height adjustment needed for a left border.

### Pattern 3: ASCII Progress Bar (DASH-03)

**What:** Replace Bootstrap's `<div class="progress"><div class="progress-bar">` with an ASCII block bar.
**When to use:** DASH-03.

**Technique B — Template expression (recommended):** Build the character string in the component TypeScript. Simpler, renders actual Unicode block characters, works without CSS tricks.

```typescript
// file.component.ts — add getter
readonly BAR_WIDTH = 10;  // total segments

getAsciiBar(): string {
    const pct = Math.min(Math.max(this.file?.percentDownloaded ?? 0, 0), 100);
    const filled = Math.round((pct / 100) * this.BAR_WIDTH);
    const empty = this.BAR_WIDTH - filled;
    return '[' + '█'.repeat(filled) + '░'.repeat(empty) + '] ' + pct + '%';
}
```

Template:
```html
<!-- Replace the entire <div class="progress">...</div> block -->
<div class="size">
    <div class="ascii-bar" [class.active]="file.status === ViewFile.Status.DOWNLOADING">
        {{getAsciiBar()}}
    </div>
    <div class="size_info">
        {{file.localSize | fileSize:3}} of {{file.remoteSize | fileSize:3}}
    </div>
</div>
```

SCSS:
```scss
// file.component.scss
.content .ascii-bar {
    font-family: var(--bs-font-monospace);  // Fira Code
    font-size: 85%;
    color: var(--bs-body-color);
    letter-spacing: 0;                       // Fira Code has consistent block spacing
    margin-bottom: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: clip;

    &.active {
        color: #3fb950;  // green when downloading
    }
}
```

**Note on `ChangeDetectionStrategy.OnPush`:** `getAsciiBar()` is a method call in the template. With `OnPush`, it re-evaluates only when the `file` `@Input()` reference changes (which it does on each status/progress update since `ViewFile` is an Immutable.js Record). This is safe — no infinite change detection loop.

**Technique A — CSS gradient (alternative, no TS change):**
```html
<div class="ascii-bar" [style.--pct]="file.percentDownloaded + '%'">
    [<span class="bar-fill"></span>] {{file.percentDownloaded}}%
</div>
```
```scss
.ascii-bar {
    .bar-fill {
        display: inline-block;
        width: calc(var(--pct, 0%) * 0.1);  // scale: 100% → 10 chars wide
        background: repeating-linear-gradient(90deg, #3fb950 0px, #3fb950 7px, transparent 7px, transparent 8px);
    }
}
```
Technique A is visually impure — it does not produce actual Unicode block characters. Technique B is cleaner for the "ASCII" requirement.

### Pattern 4: Green Glow on Downloading Rows (DASH-04)

**What:** Apply the existing `green-pulse` keyframe animation to downloading rows as a `box-shadow` pulse.
**When to use:** DASH-04 only, scoped to `DOWNLOADING` status.

The keyframe is already in `styles.scss`:
```scss
@keyframes green-pulse {
  0%, 100% { box-shadow: 0 0 4px rgba(0, 255, 65, 0.3); }
  50% { box-shadow: 0 0 12px rgba(0, 255, 65, 0.6); }
}
```

Apply via a class on `:host` or the `.file` div:
```scss
// file.component.scss
:host.downloading-active {
    animation: green-pulse 2s ease-in-out infinite;
}
```

In the template, add to the host via `@HostBinding`:
```typescript
@HostBinding('class.downloading-active')
get isDownloading(): boolean {
    return this.file?.status === ViewFile.Status.DOWNLOADING;
}
```

OR more simply, use `[class.downloading-active]` on the inner `.file` div:
```html
<div class="file"
     [class.downloading-active]="file.status === ViewFile.Status.DOWNLOADING"
     ...>
```
```scss
.file.downloading-active {
    animation: green-pulse 2s ease-in-out infinite;
}
```

**Performance note:** CSS `box-shadow` animation is GPU-composited and does not trigger layout or paint. Using `animation` rather than `transition` correctly handles the infinite pulse. The `green-pulse` keyframe uses `box-shadow` which is a composited property in modern browsers — safe for 100+ rows.

**Conflict check:** `:host` already has `border-bottom` and `content-visibility: auto`. The `animation` property does not conflict with these. `content-visibility: auto` may suppress animation for off-screen rows (which is correct behavior).

### Pattern 5: Colored Status Dot (DASH-05)

**What:** Remove all eight `<img src="assets/icons/…">` elements with their `*ngIf` chains. Replace with a single dot + status text.
**When to use:** DASH-05.

Current HTML (8 `<img>` + 1 `<span>` pattern):
```html
<div class="status">
    <img src="assets/icons/default-remote.svg" id="default-remote" *ngIf="..."/>
    <!-- 7 more <img> lines -->
    <span *ngIf="file.status != ViewFile.Status.DEFAULT" class="text">{{file.status | capitalize}}</span>
    <span class="badge bg-success import-badge" *ngIf="...">Imported</span>
</div>
```

Target HTML:
```html
<div class="status">
    <span class="status-dot" [class]="'dot-' + file.status"></span>
    <span class="status-text" *ngIf="file.status !== ViewFile.Status.DEFAULT">
        {{file.status | capitalize}}
    </span>
    <span class="badge bg-success import-badge"
          *ngIf="file.importStatus === ViewFile.ImportStatus.IMPORTED">
        Imported
    </span>
</div>
```

SCSS:
```scss
// file.component.scss
.content .status {
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-bottom: 4px;
        flex-shrink: 0;

        // Status colors
        &.dot-downloading { background-color: #3fb950; box-shadow: 0 0 6px rgba(63, 185, 80, 0.6); }
        &.dot-downloaded  { background-color: #238636; }
        &.dot-queued      { background-color: #f0883e; }
        &.dot-stopped     { background-color: #f85149; }
        &.dot-extracting  { background-color: #58a6ff; }  // $info blue
        &.dot-extracted   { background-color: #58a6ff; }
        &.dot-deleted     { background-color: #8b949e; }  // $secondary muted
        &.dot-default     { background-color: transparent; }  // no dot for DEFAULT
    }

    .status-text {
        margin-top: 3px;
        font-size: 70%;
    }
}
```

**Note on status values:** `ViewFile.Status` enum values are lowercase strings: `"default"`, `"queued"`, `"downloading"`, `"downloaded"`, `"stopped"`, `"deleted"`, `"extracting"`, `"extracted"`. The `[class]="'dot-' + file.status"` binding maps directly (e.g., `dot-downloading`).

### Pattern 6: Ghost Action Buttons (DASH-06)

**What:** Replace filled Bootstrap buttons with outline/ghost variants. Add glow on hover.
**When to use:** DASH-06 — applies to both `file-actions-bar.component.html` (primary action bar) and optionally the hidden inline `.actions` in `file.component.html`.

Current:
```html
<button class="btn btn-primary" ...>Queue</button>
<button class="btn btn-danger" ...>Stop</button>
<button class="btn btn-secondary" ...>Extract</button>
```

Target:
```html
<button class="btn btn-outline-success ghost-btn" ...>Queue</button>
<button class="btn btn-outline-danger ghost-btn" ...>Stop</button>
<button class="btn btn-outline-secondary ghost-btn" ...>Extract</button>
<button class="btn btn-outline-danger ghost-btn" ...>Delete Local</button>
<button class="btn btn-outline-danger ghost-btn" ...>Delete Remote</button>
```

SCSS for glow hover:
```scss
// file-actions-bar.component.scss
.ghost-btn {
    transition: box-shadow 0.15s ease;

    &.btn-outline-success:hover:not(:disabled) {
        box-shadow: 0 0 8px rgba(63, 185, 80, 0.5);   // green glow
    }
    &.btn-outline-danger:hover:not(:disabled) {
        box-shadow: 0 0 8px rgba(248, 81, 73, 0.5);   // red glow
    }
    &.btn-outline-secondary:hover:not(:disabled) {
        box-shadow: 0 0 8px rgba(139, 148, 158, 0.4); // gray glow
    }
}
```

**Bootstrap `btn-outline-*` behavior:** In Bootstrap 5.3 dark mode (`data-bs-theme="dark"` already set on `<html>`), `btn-outline-success` renders with `#238636` or `#3fb950` border and transparent background. On hover, Bootstrap fills the background. The `ghost-btn` glow is additive via custom `box-shadow`.

**Note:** The `.actions` div inside `file.component.html` is `display: none` (critical for virtual scroll fixed row height). DASH-06 primarily targets `file-actions-bar.component.html`. If the planner decides to update the hidden inline actions for consistency, it is safe to do so as they don't render.

### Anti-Patterns to Avoid

- **Animating `height` or `width` on file rows:** The virtual scroll pattern requires fixed `82px` height on `:host`. Never change the height.
- **Using CSS `content` to render block characters in `::before`/`::after`:** Browser font rendering of block chars in pseudo-elements is inconsistent. Use a real DOM element with text content.
- **Modifying `content-visibility: auto` on `:host`:** This is deliberately set for scroll performance. Do not remove or override it.
- **Using Bootstrap `progress-bar-animated` CSS class as the progress indicator:** DASH-03 explicitly replaces the Bootstrap progress component — don't keep it as a fallback.
- **Angular `*ngIf` chains for status dots:** DASH-05 removes the 8-way `*ngIf` pattern. A single `[class]` binding on one element is the replacement — don't reintroduce multiple conditional DOM nodes.
- **`box-shadow` glow on `:host` when `content-visibility: auto` is active:** `content-visibility: auto` skips rendering of off-screen elements including their shadows. This is correct (off-screen rows don't need glow) and not a bug.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ghost outline buttons | Custom CSS outlined buttons with hover fill | Bootstrap `btn-outline-*` | Already in the bundle; handles disabled, focus, dark-mode states correctly |
| Glow animation on downloading | Custom keyframe definition | Existing `@keyframes green-pulse` in `styles.scss` | Already defined and tested in Phase 33 |
| Status color mapping | Switch/if-else in TypeScript returning color strings | CSS class via `[class]="'dot-' + file.status"` | Zero TS, automatically handles all enum values |
| Progress percentage clamping | Manual min/max in template | `Math.min(file.percentDownloaded, 100)` already in template (`min(file.percentDownloaded,100)`) | Already present — reuse the same pattern |

**Key insight:** Every visual effect in this phase (borders, dots, animation, ghost buttons, prompt) has a pure CSS solution using only what the project already imports. No new npm packages, no new Angular services.

## Common Pitfalls

### Pitfall 1: Left Border Increases Element Width, Disrupts Column Alignment
**What goes wrong:** Adding `border-left: 3px` to `:host` or `.file` changes the total width, making content cells misalign with the header row.
**Why it happens:** `box-sizing: border-box` means the border takes from the element's content width, but if the element is `100%` wide and the header has no matching border, column widths diverge by 3px.
**How to avoid:** Apply the border to `:host` using `border-left` (3px inward from left edge). The `#header` row in `file-list.component.html` does not have a matching left border — add `border-left: 3px solid transparent` to the header row as a spacer, OR apply `padding-left: 3px` to the header to match.
**Warning signs:** Filename/status/speed columns are visually offset between header and rows.

### Pitfall 2: `[class]="'dot-' + file.status"` Overwrites Existing Classes
**What goes wrong:** Using `[class]="expr"` replaces ALL classes on the element, including any statically-set ones.
**Why it happens:** `[class]` binding sets the `class` attribute directly, overriding the static `class="status-dot"`.
**How to avoid:** Use `[ngClass]` with an object, or use `[class.dot-downloading]`, etc. per status — but that recreates the 8-way pattern. Better: use a method that returns the class string, or set base class statically and add status class via `[class.dot-X]`.
**Recommended fix:** Use `class="status-dot"` statically and `[ngClass]="{'dot-' + file.status: true}"` — but that doesn't work with dynamic keys. Use a TypeScript getter instead:
```typescript
get statusDotClass(): string {
    return `status-dot dot-${this.file?.status ?? 'default'}`;
}
```
```html
<span [class]="statusDotClass"></span>
```
This sets the full class string including the base class.

### Pitfall 3: ASCII Bar Method Called Every Change Detection Cycle
**What goes wrong:** `getAsciiBar()` is a method call in the template. With `ChangeDetectionStrategy.Default`, it runs on every CD cycle. With `OnPush` (which `FileComponent` uses), it only runs when `file` input changes — safe.
**Why it happens:** Template method calls are re-evaluated on every change detection pass.
**How to avoid:** The component already uses `ChangeDetectionStrategy.OnPush` — this is safe. Alternatively, use a getter `get asciiBar(): string` or compute it in `ngOnChanges`. Either works.
**Warning signs:** Not applicable with OnPush, but if someone changes the CD strategy, performance degrades.

### Pitfall 4: `btn-outline-success` Dark Mode Color May Differ from Expected Green
**What goes wrong:** Bootstrap 5.3 `btn-outline-success` in `data-bs-theme="dark"` uses Bootstrap's own dark palette color for `$success` — which is `#238636` (muted green), not `#3fb950` (the terminal bright green).
**Why it happens:** Bootstrap's dark theme maps `$success` to its own dark-mode success color. The project overrides `$success: #238636` in `_bootstrap-variables.scss`, so the button border will be `#238636`, not `#3fb950`.
**How to avoid:** This is intentional — `btn-outline-success` with the project's palette gives a muted green outline. If the requirement needs the brighter `#3fb950` green (terminal primary), use `btn-outline-primary` instead (which uses `$primary: #3fb950`). Verify visually which green looks right.
**Warning signs:** Outline buttons look dimmer than the glow color.

### Pitfall 5: Glow `box-shadow` on `file-actions-bar` Clips at Container Edge
**What goes wrong:** If `file-actions-bar` has `overflow: hidden` on a parent, the glow `box-shadow` is clipped.
**Why it happens:** `box-shadow` is painted inside the element's stacking context and can be clipped by parent `overflow`.
**How to avoid:** Check `file-actions-bar.component.scss` parent containers — currently no `overflow: hidden` on the bar itself or its parent `#file-list`. Safe to use glow.
**Warning signs:** Button glow appears cut off on left or right edge.

### Pitfall 6: Fira Code Block Characters Rendering Depends on Font Load
**What goes wrong:** The ASCII bar renders as boxes or incorrect characters if Fira Code hasn't loaded yet (FOUT — flash of unstyled text).
**Why it happens:** Google Fonts CDN has a small load delay on first visit.
**How to avoid:** The `display=swap` parameter in the Google Fonts URL (already set in `index.html`) means the system fallback monospace font renders first. Fallback monospace fonts (Courier New, Menlo, Monaco) all support `█` and `░` Unicode block characters. No functional issue, only a brief visual font swap.
**Warning signs:** On slow connections, bar characters briefly appear in a different monospace font before Fira Code loads.

## Code Examples

Verified patterns from the actual codebase:

### Current ViewFile.Status Enum Values
```typescript
// Source: src/angular/src/app/services/files/view-file.ts
export enum Status {
    DEFAULT     = "default",
    QUEUED      = "queued",
    DOWNLOADING = "downloading",
    DOWNLOADED  = "downloaded",
    STOPPED     = "stopped",
    DELETED     = "deleted",
    EXTRACTING  = "extracting",
    EXTRACTED   = "extracted"
}
```

### Existing `green-pulse` Keyframe (Already in `styles.scss`)
```scss
// Source: src/angular/src/styles.scss
@keyframes green-pulse {
  0%, 100% { box-shadow: 0 0 4px rgba(0, 255, 65, 0.3); }
  50% { box-shadow: 0 0 12px rgba(0, 255, 65, 0.6); }
}
```

### Existing CSS Custom Properties for Status Colors
```scss
// Source: src/angular/src/app/common/_bootstrap-variables.scss
$primary: #3fb950;    // GitHub green — use for DOWNLOADING border + dot
$secondary: #8b949e;  // Muted gray — use for DELETED dot
$success: #238636;    // Muted green — use for DOWNLOADED border + dot
$danger: #f85149;     // GitHub red — use for STOPPED border + dot
$warning: #f0883e;    // Amber — use for QUEUED border + dot
$info: #58a6ff;       // Blue — use for EXTRACTING/EXTRACTED dot
```

### Existing `:host` Block (Must Preserve)
```scss
// Source: src/angular/src/app/pages/files/file.component.scss
:host {
    display: block;
    height: 82px;       // CRITICAL — do not change
    min-height: 82px;
    max-height: 82px;
    overflow: hidden;
    border-bottom: 1px solid var(--app-file-border-color);
    content-visibility: auto;
    contain-intrinsic-size: auto 82px;
}
```

### Existing File Search Input Structure
```scss
// Source: src/angular/src/app/pages/files/file-options.component.scss
#filter-search {
    flex-grow: 1;
    flex-basis: 100%;
    display: flex;
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
    position: relative;   // ← already set — prompt can be position: absolute

    img {
        position: absolute;
        left: 7px;
        top: 7px;          // ← was top: 7px for image; adjust for span with translateY(-50%)
        z-index: $zindex-file-search;
    }

    input {
        padding: 3px 15px 3px 30px;  // ← 30px left for icon; adjust to ~24px for > char
    }
}
```

### Existing Bootstrap Button Classes in Use
```html
<!-- Source: file-actions-bar.component.html -->
<button class="btn btn-primary">Queue</button>
<button class="btn btn-danger">Stop</button>
<button class="btn btn-secondary">Extract</button>
<button class="btn btn-danger">Delete Local</button>
<button class="btn btn-danger">Delete Remote</button>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SVG icon for search | Terminal `>` prompt character | Phase 35 | Purely CSS, no image request |
| SVG icons for file status (8 images) | Colored CSS dot | Phase 35 | Removes 8 image elements per row; simpler, theme-consistent |
| Bootstrap progress bar (animated stripe) | ASCII block character bar | Phase 35 | Font-rendered, Fira Code, no image dependency |
| Filled Bootstrap buttons | Ghost outline buttons with glow | Phase 35 | Terminal aesthetic; outline style is standard in dark hacker UIs |
| No row status indicator | Colored left border per status | Phase 35 | Immediate visual scan of file status without reading text |

**Deprecated/outdated in this phase:**
- `<img src="assets/icons/downloading.svg">` et al. in `file.component.html` — all 8 status SVG images removed
- `<img src="assets/icons/search.svg">` in `file-options.component.html` — replaced with `>` span
- `<div class="progress"><div class="progress-bar progress-bar-animated progress-bar-striped">` — replaced with `.ascii-bar`
- `btn btn-primary`, `btn btn-secondary` in action buttons — replaced with `btn-outline-*`

## Open Questions

1. **Left border + header alignment**
   - What we know: Adding `border-left: 3px` to file rows creates a 3px offset vs. the header row (which has no matching border).
   - What's unclear: Whether the planner wants to add a matching left border space to the header row or accept the slight visual offset.
   - Recommendation: Add `border-left: 3px solid transparent` to `#file-list #header` in `file-list.component.scss` to maintain alignment.

2. **Status border for non-primary statuses (DEFAULT, DELETED, EXTRACTING, EXTRACTED)**
   - What we know: DASH-02 specifies colors for downloading (green), downloaded (teal), queued (amber), stopped (red). It is silent on DEFAULT, DELETED, EXTRACTING, EXTRACTED.
   - What's unclear: Whether these four statuses should have a border or not.
   - Recommendation: DEFAULT and DELETED — transparent/no border. EXTRACTING — same teal as downloaded. EXTRACTED — same teal as downloaded. Treat extracting as "active" and extracted as "complete".

3. **DASH-06 scope: inline `.actions` in `file.component.html` vs. `file-actions-bar`**
   - What we know: The `.actions` div in `file.component.html` is `display: none` (required for virtual scroll). The visible action bar is `file-actions-bar.component.html`.
   - What's unclear: Whether to update the hidden inline actions for consistency.
   - Recommendation: Update both for consistency — the inline `.actions` may become visible in a future phase; keeping it up to date is low risk.

4. **ASCII bar width at mobile layout**
   - What we know: At mobile widths, `.content .size` is `flex-grow: 1` with no fixed width. The ASCII bar with 10 segments + brackets + "100%" is approximately 16 characters wide at Fira Code — roughly 100-130px.
   - What's unclear: Whether the bar truncates gracefully at very narrow widths.
   - Recommendation: Add `overflow: hidden; text-overflow: clip; white-space: nowrap` on `.ascii-bar` — already included in Pattern 3 above.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection:
  - `src/angular/src/app/pages/files/file.component.html` — current status SVG structure, progress bar, actions
  - `src/angular/src/app/pages/files/file.component.scss` — `:host` height constraints, existing SCSS patterns
  - `src/angular/src/app/pages/files/file.component.ts` — `ChangeDetectionStrategy.OnPush`, `ViewFile` imports
  - `src/angular/src/app/pages/files/file-options.component.html` — current search input structure
  - `src/angular/src/app/pages/files/file-options.component.scss` — `position: relative`, `z-index` usage
  - `src/angular/src/app/pages/files/file-actions-bar.component.html` — current button classes
  - `src/angular/src/app/pages/files/file-list.component.scss` — header row widths
  - `src/angular/src/app/common/_bootstrap-variables.scss` — color palette
  - `src/angular/src/app/common/_bootstrap-overrides.scss` — dark mode form control overrides
  - `src/angular/src/styles.scss` — `@keyframes green-pulse`, `.glow-green`, CSS custom properties
  - `src/angular/src/app/services/files/view-file.ts` — `ViewFile.Status` enum (all 8 values)
  - `src/angular/src/index.html` — `data-bs-theme="dark"` confirmed, Fira Code loaded via CDN
- Bootstrap 5.3 `btn-outline-*` — behavior verified via existing `btn-outline-danger` usage in `confirm-modal.component.html`

### Secondary (MEDIUM confidence)
- CSS `box-shadow` compositing — standard browser behavior, widely documented
- Unicode block characters `█` (U+2588) and `░` (U+2591) in monospace fonts — supported in all modern system monospace fonts and Fira Code

### Tertiary (LOW confidence)
- None — all findings backed by direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing Angular/Bootstrap/SCSS, confirmed in codebase
- Architecture: HIGH — all patterns verified from direct file inspection; no unknowns
- Pitfalls: HIGH — identified from direct inspection of SCSS constraints (82px height, `overflow: hidden`, `content-visibility`)

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable — no fast-moving dependencies; Angular 19 / Bootstrap 5.3 APIs are stable)
