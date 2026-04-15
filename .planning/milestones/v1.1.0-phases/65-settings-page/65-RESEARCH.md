# Phase 65: Settings Page - Research

**Researched:** 2026-04-14
**Domain:** Angular 21 UI — settings page visual upgrade, CSS toggle switches, masonry layout, floating save bar
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Card headers are pixel-exact to AIDesigner spec. Dark header bar (`bg-row` / `#1a2019` background, `border-b border-edge`), FA 4.7 icon. Icon map:
- General Options → `fa-sliders`
- Remote Server (LFTP) → `fa-server`
- File Discovery Polling → `fa-search`
- Archive Operations → `fa-file-archive-o`
- LFTP Connection Limits → `fa-tachometer`
- AutoQueue Engine → `fa-list`
- Sonarr → `fa-television`
- Radarr → `fa-film`
- Post-Import Pruning (Auto-Delete) → `fa-trash`
- API & Security → `fa-shield`

**D-02:** Card header text: uppercase tracking, `text-xs` size, `font-semibold`, `text-sec` color.

**D-03:** All boolean settings render as pill-shaped toggle switches. Match mockup dimensions: `w-9 h-5` (36x20px) for primary toggles, `w-7 h-4` (28x16px) for inline/compact toggles.

**D-04:** Toggle states: OFF = `bg-muted border-edge` with `text-sec`-colored circle. ON = `bg-amber/10 border-amber/50` with amber circle. Focus ring: `ring-amber/50`.

**D-05:** Toggle CSS implementation technique is Claude's discretion (pure CSS on existing checkbox or new component).

**D-06:** Keep existing auto-save behavior (individual field saves via `ConfigService.set()` with 1s debounce). No batch save migration.

**D-07:** Add floating bar at bottom-right: `bg-card/90 backdrop-blur-xl border-edge` container with "Unsaved Changes" text and amber "Save Settings" button. Bar appears when changes are pending (during debounce), shows "Changes saved" after save completes.

**D-08:** The existing `#commands` section with the "Restart" button is replaced by integrating restart into the floating bar or as a separate action within it.

**D-09:** Sonarr card — brand blue: header bg `#1b232e`, border `#2b3a4a`, accent `#00c2ff`. Left border accent `border-l-2 border-[#00c2ff]/30`. Toggle ON uses `#00c2ff`.

**D-10:** Radarr card — brand gold: header bg `#2b2210`, border `#4a3415`, accent `#ffc230`. Left border accent `border-l-2 border-[#ffc230]/30`. Toggle ON uses `#ffc230`.

**D-11:** Sonarr/Radarr cards render side-by-side in a sub-grid (`grid-cols-2`) on desktop, stacked on mobile.

**D-12:** Post-Import Pruning card uses red accent (`#c45b5b`) for icon, header text tint, toggle ON state. When disabled: `opacity-60` and `pointer-events-none` on card body.

### Claude's Discretion

- Exact CSS implementation technique for toggle switches (pure CSS vs component)
- Card ordering within each column (follow mockup layout)
- Copy-to-clipboard button styling for webhook URLs
- Transition animations on floating bar appearance
- Responsive breakpoint adjustments if needed
- Whether to add the "API & Security" card (currently has a Security card with API token — may just need icon/header upgrade)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SETT-01 | Settings page uses two-column masonry grid on desktop | Existing flex layout → upgrade to CSS grid with `align-items: start`; responsive breakpoint already at `$medium-min-width` (601px) |
| SETT-02 | All 10 settings sections rendered as card components with icon headers | 8 sections currently exist in template + options-list; card header restructure adds dark header bar + FA 4.7 icon per D-01 |
| SETT-03 | Boolean settings use styled toggle switches instead of checkboxes | OptionComponent Checkbox type → restyle with pure CSS toggle using `sr-only` + sibling `div` pattern from mockup |
| SETT-04 | AutoQueue card includes inline pattern list with add/remove | Pattern CRUD already implemented in template and AutoQueueService — visual upgrade only |
| SETT-05 | Sonarr/Radarr cards show read-only webhook URL with copy button | Webhook URL display already exists in template; add copy-to-clipboard button (pattern same as existing `onCopyToken()`) |
| SETT-06 | Floating save button bar appears at bottom-right | New `position: fixed` element; pending-state tracking via new component property watching debounce activity |
</phase_requirements>

---

## Summary

Phase 65 is a visual-only upgrade to the existing Angular settings page. All backing logic (ConfigService auto-save, AutoQueueService CRUD, connection testing, API token copy) is already implemented and must not change. The work is entirely in the Angular templates and SCSS.

The pixel-exact target is the AIDesigner mockup at `.aidesigner/runs/2026-04-14T03-43-48-899Z-seedsyncarr-settings-v2-all-sections/design.html`, which uses Tailwind CSS + Phosphor Icons. Every Tailwind class must be translated to Bootstrap 5 SCSS equivalents, and every Phosphor icon must be replaced with its FA 4.7 mapping (D-01).

The two most architecturally significant changes are: (1) the toggle switch restyle — the `OptionComponent` must replace the plain Bootstrap `form-check-input` checkbox with a CSS-only pill toggle without breaking the debounced `ngModelChange` binding; and (2) the floating save bar — a new `position: fixed` element that tracks pending-save state via a new component property.

**Primary recommendation:** Work in three sequential groups — (1) SCSS variables + card header template/SCSS, (2) toggle switch in OptionComponent, (3) Sonarr/Radarr/AutoDelete/webhook card content + floating bar.

---

## Standard Stack

No new packages. All work uses the existing project stack.

### Core (already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular | 21.x | Component framework | Project standard |
| Bootstrap 5 | 5.3.x | Grid, utilities, form base | Project standard |
| Font Awesome 4.7 | 4.7 | Icons | Project standard — Phosphor NOT used |
| SCSS | project-current | Component styles | Project standard |

### Key Project Variables (verified in `_bootstrap-variables.scss` and `styles.scss`)

| Variable | Value | Role |
|----------|-------|------|
| `$forest-row` | `#1a2019` | Card header bg (`bg-row` in mockup) |
| `$forest-card` | `#222a20` | Card body bg |
| `$forest-border` / `$moss-border` | `#3e4a38` | `border-edge` in mockup |
| `$forest-muted` | `#2c3629` | Toggle OFF bg (`bg-muted`) |
| `--app-muted-text` / `$secondary` | `#9aaa8a` | `text-sec` |
| `$primary` | `#c49a4a` | Amber accent |
| `--app-header-bg` | `#222a20` | Current card bg (already correct) |
| `--app-file-border-color` | `#3e4a38` | Card border |
| `$semantic-error` | `#c45b5b` | Auto-Delete danger accent |

**Installation:** None required.

---

## Architecture Patterns

### Existing Structure (verified by reading source)

```
src/angular/src/app/pages/settings/
├── settings-page.component.html    # template — restructure card headers, add floating bar
├── settings-page.component.scss    # styles — add toggle, card header, floating bar styles
├── settings-page.component.ts      # controller — add pending-save tracking
├── option.component.html           # toggle template change here
├── option.component.scss           # toggle CSS here
├── option.component.ts             # NO changes needed
└── options-list.ts                 # NO changes needed
```

### Pattern 1: Card Header Restructure

**What:** Replace plain `<h3 class="settings-card-header">` with a two-element header: dark bar div + content row with icon + label.

**Current HTML pattern:**
```html
<div class="settings-card">
  <h3 class="settings-card-header">{{header}}</h3>
  <div class="settings-card-body">
```

**Target HTML pattern (translated from mockup):**
```html
<div class="settings-card">
  <div class="settings-card-header">
    <i class="fa fa-sliders text-sec"></i>
    <span>GENERAL OPTIONS</span>
  </div>
  <div class="settings-card-body">
```

**Target SCSS:**
```scss
.settings-card-header {
  background: #1a2019;           // $forest-row
  border-bottom: 1px solid #3e4a38; // $moss-border
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.75rem;            // text-xs
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--app-muted-text);  // text-sec

  i.fa {
    font-size: 1rem;
    color: var(--app-muted-text);
  }
}
```

**Source:** [VERIFIED: read from design.html line 65 — `bg-row border-b border-edge px-5 py-3 flex items-center gap-3`]

### Pattern 2: CSS Toggle Switch (OptionComponent)

**What:** Replace the Bootstrap `form-check-input` checkbox with a hidden `<input type="checkbox" class="sr-only">` plus a sibling `<div>` styled as a pill toggle. The `ngModel` binding stays on the checkbox input; CSS pseudo-selectors style the div.

**Target HTML (in option.component.html, Checkbox branch):**
```html
@if (type == OptionType.Checkbox) {
  <div class="form-toggle">
    <label class="toggle-label">
      <input
        type="checkbox"
        class="toggle-input"
        [disabled]="value == null"
        [ngModel]="value"
        (ngModelChange)="onChange($event)" />
      <div class="toggle-track"></div>
    </label>
    <div class="toggle-text">
      <span class="name">{{label}}</span>
      @if (description) {
        <span class="description">{{description}}</span>
      }
    </div>
  </div>
}
```

**Target SCSS (primary toggle, 36x20px):**
```scss
.form-toggle {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 16px;

  .toggle-label {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .toggle-input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
    // sr-only equivalent
  }

  .toggle-track {
    width: 36px;   // w-9
    height: 20px;  // h-5
    background: #2c3629;       // $forest-muted / bg-muted
    border: 1px solid #3e4a38; // $moss-border / border-edge
    border-radius: 9999px;
    position: relative;
    transition: background 0.2s, border-color 0.2s;

    &::after {
      content: '';
      position: absolute;
      top: 2px;
      left: 2px;
      width: 16px;    // h-4 = after circle
      height: 16px;
      background: #9aaa8a;  // text-sec colored circle (OFF state)
      border-radius: 50%;
      transition: transform 0.2s, background 0.2s;
    }
  }

  .toggle-input:checked + .toggle-track {
    background: rgba(196, 154, 74, 0.10);  // amber/10
    border-color: rgba(196, 154, 74, 0.50); // amber/50

    &::after {
      transform: translateX(16px); // translate-x-full (36-20=16px)
      background: #c49a4a;          // amber
    }
  }

  .toggle-input:focus + .toggle-track {
    box-shadow: 0 0 0 2px rgba(196, 154, 74, 0.25);
  }

  .toggle-input:disabled + .toggle-track {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .toggle-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
}
```

**Compact toggle variant (28x16px) — used inline in card rows:**
```scss
.toggle-track--compact {
  width: 28px;    // w-7
  height: 16px;  // h-4
  &::after {
    width: 12px;   // h-3
    height: 12px;
  }
  .toggle-input:checked + & {
    &::after { transform: translateX(12px); }
  }
}
```

**Source:** [VERIFIED: read from design.html — `w-9 h-5 bg-muted border border-edge rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-text-sec after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber/10 peer-checked:border-amber/50 peer-checked:after:bg-amber`]

### Pattern 3: Masonry Two-Column Grid

**What:** Upgrade existing `flex` two-column layout to CSS Grid with `align-items: start` for true masonry-style (cards don't force equal column heights).

**Current SCSS:** `display: flex; flex-direction: column` (mobile) / `flex-direction: row` (desktop), each `.settings-column` at `width: 50%`.

**Target SCSS:**
```scss
.settings-columns {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  align-items: start;
  padding: 16px;

  @media (min-width: $medium-min-width) {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

The two `.settings-column` divs remain as grid children. Sonarr/Radarr sub-grid inside:
```scss
.arr-cards-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;

  @media (min-width: $medium-min-width) {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

**Source:** [VERIFIED: design.html line 35-36 — `.masonry-grid { display: grid; grid-template-columns: repeat(1, minmax(0, 1fr)); gap: 1.5rem; align-items: start; }`]

### Pattern 4: Sonarr/Radarr Brand Cards

**What:** Each *arr card gets brand-specific header bg, border, accent, and toggle ON color. Card body gets a `border-l-2` left accent. Toggle enable/disable is in the card header row.

**Sonarr header:**
```scss
.settings-card--sonarr {
  border-color: #2b3a4a;
  border-left: 2px solid rgba(0, 194, 255, 0.30);

  .settings-card-header {
    background: #1b232e;
    border-bottom-color: #2b3a4a;
    i.fa { color: #00c2ff; }
  }
}
```

**Radarr header:**
```scss
.settings-card--radarr {
  border-color: #4a3415;
  border-left: 2px solid rgba(255, 194, 48, 0.30);

  .settings-card-header {
    background: #2b2210;
    border-bottom-color: #4a3415;
    i.fa { color: #ffc230; }
  }
}
```

**Source:** [VERIFIED: design.html line 73 — `bg-[#1b232e] border-b border-[#2b3a4a]` / `bg-[#2b2210] border-b border-[#4a3415]`]

### Pattern 5: Floating Save Bar

**What:** Fixed-position element at bottom-right. Two states: (1) pending — shows "Unsaved Changes" with amber Save button; (2) saved — shows "Changes saved" briefly then hides.

**Template:**
```html
@if (hasPendingChanges || saveConfirmed) {
  <div class="floating-save-bar">
    <div class="floating-save-inner">
      <div class="floating-save-text">
        @if (saveConfirmed) {
          <span class="save-status-label">Changes saved</span>
        } @else {
          <span class="save-status-label">Unsaved Changes</span>
          <span class="save-status-sub">Settings will auto-save</span>
        }
      </div>
      <button class="btn btn-primary floating-save-btn"
        [disabled]="!commandsEnabled"
        (click)="onCommandRestart()">
        <i class="fa fa-floppy-o"></i> Save Settings
      </button>
    </div>
  </div>
}
```

**SCSS:**
```scss
.floating-save-bar {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1050;

  .floating-save-inner {
    background: rgba(34, 42, 32, 0.90); // card/90
    backdrop-filter: blur(16px);
    border: 1px solid #3e4a38;
    border-radius: 12px;
    padding: 12px 16px 12px 20px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }

  .floating-save-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .save-status-label {
    font-size: 0.875rem;
    font-weight: 600;
  }

  .save-status-sub {
    font-size: 0.75rem;
    color: var(--app-muted-text);
  }

  .floating-save-btn {
    font-weight: 700;
    padding: 8px 20px;
    white-space: nowrap;
  }
}
```

**Controller additions** (in `settings-page.component.ts`):
```typescript
public hasPendingChanges = false;
public saveConfirmed = false;
private saveConfirmedTimer: ReturnType<typeof setTimeout> | null = null;

// Called from onSetConfig after successful save:
private onSaveComplete(): void {
  this.hasPendingChanges = false;
  this.saveConfirmed = true;
  this._cdr.markForCheck();
  if (this.saveConfirmedTimer) clearTimeout(this.saveConfirmedTimer);
  this.saveConfirmedTimer = setTimeout(() => {
    this.saveConfirmed = false;
    this._cdr.markForCheck();
  }, 2500);
}

// Called when onChange fires (debounce in OptionComponent starts):
// Wire: OptionComponent emits changeEvent only AFTER debounce completes
// So hasPendingChanges = true when any option fires onChange immediately
// This requires intercepting the intermediate state — see Pitfall 2 below
```

**Source:** [VERIFIED: design.html line 79 — `fixed bottom-6 right-6 z-50`, `bg-card/90 backdrop-blur-xl border border-edge`]

### Pattern 6: Webhook Copy Button

**What:** The existing webhook URL `<code>` display gets a copy button inline. Follow the existing `onCopyToken()` pattern — use `navigator.clipboard.writeText()` with a 2s visual confirmation.

**Template addition:**
```html
<div class="webhook-url-row">
  <input type="text" readonly class="form-control form-control-sm webhook-url-input font-mono"
    [value]="'http://<seedsyncarr-address>:' + ((config | async)?.get('web')?.get('port')) + '/server/webhook/sonarr'" />
  <button class="btn btn-sm btn-secondary webhook-copy-btn"
    (click)="onCopyWebhook('sonarr')"
    [title]="sonarrWebhookCopied ? 'Copied!' : 'Copy URL'">
    <i class="fa" [class.fa-check]="sonarrWebhookCopied" [class.fa-copy]="!sonarrWebhookCopied"></i>
  </button>
</div>
```

**Source:** [VERIFIED: design.html line 73 — `readonly` input + copy button with `ph-copy` icon, inline flex with `border-l border-edge`]

### Pattern 7: Auto-Delete Card Disabled State

**What:** When `autodelete.enabled` is false, the card body shows `opacity-60` and `pointer-events: none`. The enable toggle is in the card header row (matching AutoQueue Engine pattern).

**SCSS:**
```scss
.settings-card--autodelete {
  .settings-card-header {
    i.fa { color: #c45b5b; }
    .settings-card-header-title { color: rgba(196, 91, 91, 0.90); }
  }

  .settings-card-body--disabled {
    opacity: 0.60;
    pointer-events: none;
  }
}
```

**Source:** [VERIFIED: design.html line 74 — `opacity-60 grayscale-[50%] pointer-events-none`]

### Anti-Patterns to Avoid

- **Don't use Bootstrap's `.form-switch`:** Bootstrap's switch uses `role=switch` and specific sizing that won't match the `w-9 h-5` spec. Use pure custom CSS.
- **Don't remove `ngModel` from the checkbox:** The debounce logic in `OptionComponent` uses `(ngModelChange)`. Keep the hidden checkbox as the real input.
- **Don't batch-save:** D-06 locks individual auto-save. The floating bar is visual only; clicking it triggers restart (D-08), not a different save mechanism.
- **Don't make `settings-card-header` a `<h3>` anymore:** Change it to a `<div>` to avoid semantic heading constraints on styling.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS toggle switch | Custom checkbox component | Pure CSS sibling selector on existing `<input>` | OptionComponent already has debounce wiring; just restyle the checkbox branch |
| Clipboard copy | Custom execCommand fallback | `navigator.clipboard.writeText()` | Already used in `onCopyToken()` — proven pattern |
| Pending-save detection | Intercept debounce internals | Simple boolean flag set on `changeEvent` emit | OptionComponent only emits after debounce completes; set `hasPendingChanges = true` on emit, `false` on save completion |

**Key insight:** The settings controller already has all the state and methods. This phase adds SCSS and small template structural changes — not new services, not new Angular patterns.

---

## Common Pitfalls

### Pitfall 1: Toggle Translate Distance Mismatch

**What goes wrong:** The circle overshoots or undershoots when toggled ON.
**Why it happens:** `translateX` must equal `track-width - circle-diameter - (2 * top-offset)`. For primary toggle: 36px − 16px − 4px = 16px. For compact: 28px − 12px − 4px = 12px.
**How to avoid:** Use exact pixel math. Primary: `translateX(16px)`. Compact: `translateX(12px)`.
**Warning signs:** Circle clips the right edge or leaves visible gap.

### Pitfall 2: Floating Bar "Pending" State — When to Show

**What goes wrong:** The floating bar either never appears (if tracking only post-debounce emits) or appears permanently.
**Why it happens:** `OptionComponent` emits `changeEvent` only AFTER the 1-second debounce. By the time the bar appears, the save has already fired. The pending window is the 1-second debounce interval.
**How to avoid:** Track pending state correctly — set `hasPendingChanges = true` when the save API call goes out, clear it in the `onSetConfig` success handler. This means the bar shows "Unsaved Changes" during the network round-trip (brief but visible), then transitions to "Changes saved" for 2.5 seconds.
**Warning signs:** Bar shows "Unsaved Changes" permanently after any edit.

### Pitfall 3: `ChangeDetectionStrategy.OnPush` + setTimeout

**What goes wrong:** The "Changes saved" text doesn't disappear after the 2.5s timer because `markForCheck()` is not called inside the timeout callback.
**Why it happens:** `OnPush` only checks on input changes or explicit `markForCheck()`. `setTimeout` callbacks are outside Angular's zone by default in some configurations.
**How to avoid:** Always call `this._cdr.markForCheck()` inside the `setTimeout` callback (pattern already used in `onCopyToken()`).
**Warning signs:** "Changes saved" text remains after 2.5 seconds.

### Pitfall 4: Card Header Template Change Breaks `ng-template` Reuse

**What goes wrong:** The `optionsList` `ng-template` currently renders the header as `{{header}}` text. Adding FA icons requires each card to have a different icon class.
**How to avoid:** Either (a) extend `IOptionsContext` to include an `icon` field, or (b) abandon the generic `ng-template` for the icon-bearing cards and inline each card's header. Option (b) is simpler and already required for custom cards (AutoQueue, *arr, Security).
**Warning signs:** All cards show the same icon.

### Pitfall 5: `fieldset[disabled]` Overrides Pointer Events

**What goes wrong:** Auto-Delete card body `pointer-events: none` conflicts with the existing `fieldset[disabled]` pattern used for Sonarr/Radarr.
**Why it happens:** `pointer-events: none` on a parent is redundant when `fieldset[disabled]` already disables children — but the autodelete card doesn't use a fieldset.
**How to avoid:** Bind `[class.settings-card-body--disabled]="!autodeleteEnabled"` driven by the config subscription (same pattern as `autoqueueEnabled`).
**Warning signs:** Auto-Delete body remains interactive when enable toggle is OFF.

### Pitfall 6: Sonarr/Radarr Toggle Color Override Scope

**What goes wrong:** Applying Sonarr blue toggle color via a parent class modifier in `settings-page.component.scss` doesn't reach the toggle CSS inside `option.component.scss`.
**Why it happens:** Angular View Encapsulation. `OptionComponent`'s styles are scoped with a `_ngcontent` attribute. Parent component cannot pierce encapsulation with regular CSS.
**How to avoid:** Use `::ng-deep` in the parent SCSS ONLY for brand-color overrides, scoped within `.settings-card--sonarr ::ng-deep .toggle-input:checked + .toggle-track`. Or: expose toggle color as a CSS custom property on the card that the toggle reads.
**Warning signs:** Toggle stays amber in Sonarr/Radarr cards.

---

## Code Examples

### IOptionsContext Icon Extension (for ng-template approach)

```typescript
// options-list.ts — extend interface
export interface IOptionsContext {
  header: string;
  id: string;
  icon: string;  // FA 4.7 icon class e.g. 'fa-sliders'
  options: IOption[];
}

// Usage in template:
// <i class="fa {{context.icon}}"></i>
```

### ng-template with Icon (settings-page.component.html)

```html
<ng-template #optionsList let-header="header" let-options="options" let-id="id" let-icon="icon">
  <div class="settings-card">
    <div class="settings-card-header">
      <i class="fa {{icon}}"></i>
      <span>{{header | uppercase}}</span>
    </div>
    <div class="settings-card-body">
      ...
    </div>
  </div>
</ng-template>
```

### Pending Save Tracking in SettingsPageComponent

```typescript
// settings-page.component.ts additions
public hasPendingChanges = false;
public saveConfirmed = false;
private _saveConfirmTimer: ReturnType<typeof setTimeout> | null = null;
public autodeleteEnabled = false;

// Modified onSetConfig:
onSetConfig(section: string, option: string, value: string | number | boolean): void {
  this.hasPendingChanges = true;
  this._cdr.markForCheck();

  this._configService.set(section, option, value).pipe(takeUntil(this.destroy$)).subscribe({
    next: reaction => {
      if (reaction.success) {
        this.hasPendingChanges = false;
        this.saveConfirmed = true;
        this._cdr.markForCheck();
        if (this._saveConfirmTimer) clearTimeout(this._saveConfirmTimer);
        this._saveConfirmTimer = setTimeout(() => {
          this.saveConfirmed = false;
          this._cdr.markForCheck();
        }, 2500);
        // ...existing notification logic
      } else {
        this.hasPendingChanges = false;
        this._cdr.markForCheck();
        // ...existing error handling
      }
    }
  });
}
```

### Webhook Copy Button (component property + method)

```typescript
// New properties in SettingsPageComponent:
public sonarrWebhookCopied = false;
public radarrWebhookCopied = false;

onCopyWebhook(arr: 'sonarr' | 'radarr'): void {
  const port = /* read from config */;
  const url = `http://<seedsyncarr-address>:${port}/server/webhook/${arr}`;
  navigator.clipboard.writeText(url).then(() => {
    if (arr === 'sonarr') {
      this.sonarrWebhookCopied = true;
      this._cdr.markForCheck();
      setTimeout(() => { this.sonarrWebhookCopied = false; this._cdr.markForCheck(); }, 2000);
    } else {
      this.radarrWebhookCopied = true;
      this._cdr.markForCheck();
      setTimeout(() => { this.radarrWebhookCopied = false; this._cdr.markForCheck(); }, 2000);
    }
  });
}
```

---

## Section Inventory: 10 Cards Mapping

The mockup shows 10 sections. The existing code has 8 `OPTIONS_CONTEXT_*` entries + inline custom sections. Mapping:

| Mockup Section | Existing Code Source | Status |
|---------------|---------------------|--------|
| General Options | `OPTIONS_CONTEXT_OTHER` (Debug, Port) | EXISTS — rename header, add icon |
| Remote Server (LFTP) | `OPTIONS_CONTEXT_SERVER` | EXISTS — add icon, restructure header |
| File Discovery Polling | `OPTIONS_CONTEXT_DISCOVERY` | EXISTS — add icon |
| Archive Operations | `OPTIONS_CONTEXT_EXTRACT` | EXISTS — add icon |
| LFTP Connection Limits | `OPTIONS_CONTEXT_CONNECTIONS` | EXISTS — add icon |
| AutoQueue Engine | Inline custom card (has pattern CRUD) | EXISTS — add icon, left border, move enable toggle to header |
| Sonarr | Inline in *arr Integration card | EXISTS — split into separate card, brand-color header |
| Radarr | Inline in *arr Integration card | EXISTS — split into separate card, brand-color header |
| Post-Import Pruning | `OPTIONS_CONTEXT_AUTODELETE` | EXISTS — add icon, red accent, disabled body state |
| API & Security | Inline Security card (API token) | EXISTS — add `fa-shield` icon, upgrade header |

**Key insight:** The existing template has Sonarr and Radarr combined under "*arr Integration". They must be split into two independent cards placed side-by-side in a sub-grid (D-11). This is a template restructure, not new functionality.

**Column layout (from mockup):**

Left column:
1. General Options (small card — 2 toggles)
2. Remote Server / LFTP (large card)
3. File Discovery Polling
4. Archive Operations (small card)
5. LFTP Connection Limits

Right column:
1. AutoQueue Engine (with pattern list)
2. Sonarr + Radarr (side-by-side sub-grid)
3. Post-Import Pruning / Auto-Delete
4. API & Security

This matches the existing column assignment in the template (left: SERVER, AutoQueue, EXTRACT, *arr, AUTODELETE; right: CONNECTIONS, DISCOVERY, OTHER, Security). The column ordering should be adjusted to match the mockup — move *arr and autodelete to right column.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Karma + Jasmine (Angular default, `ng test`) |
| Config file | `src/angular/angular.json` (test target configured) |
| Quick run command | `cd src/angular && ng test --include='**/settings*' --watch=false` |
| Full suite command | `cd src/angular && ng test --watch=false` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SETT-01 | Two-column grid renders on desktop viewport | Manual visual / e2e | `cd src/angular && npx playwright test --grep "settings"` | ❌ Wave 0 |
| SETT-02 | 10 cards present with icon headers | unit — DOM inspection | `cd src/angular && ng test --include='**/settings-page*' --watch=false` | ❌ Wave 0 |
| SETT-03 | Toggle switch renders (not checkbox) | unit — DOM class check | same spec file | ❌ Wave 0 |
| SETT-04 | Pattern list shows add/remove | unit — existing AutoQueue logic already tested; visual is manual | manual | N/A |
| SETT-05 | Webhook copy button copies to clipboard | unit — mock clipboard | same spec file | ❌ Wave 0 |
| SETT-06 | Floating bar appears/disappears | unit — component state | same spec file | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd src/angular && ng test --watch=false 2>&1 | tail -5`
- **Per wave merge:** `cd src/angular && ng test --watch=false`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `src/angular/src/app/tests/unittests/pages/settings/settings-page.component.spec.ts` — covers SETT-02, SETT-03, SETT-05, SETT-06
- [ ] Playwright e2e for SETT-01 (visual column layout) — if e2e suite exists at project root

---

## Environment Availability

Step 2.6: SKIPPED — Phase 65 is a pure Angular template/SCSS change with no external dependencies beyond the existing Angular dev server. No new services, CLIs, or databases required.

---

## Runtime State Inventory

Step 2.5: SKIPPED — Phase 65 is a visual upgrade, not a rename/refactor/migration. No stored data, service configs, or OS-level registrations involve settings page layout.

---

## Open Questions

1. **Column ordering alignment with mockup**
   - What we know: Current template has *arr Integration and AUTODELETE in the left column; mockup shows AutoQueue + *arr + AutoDelete in the right column.
   - What's unclear: Does the planner need to reorder cards across columns or just match icon/header styling?
   - Recommendation: Follow mockup column layout exactly per CONTEXT.md "pixel-exact match" directive.

2. **Floating bar "Save Settings" button behavior (D-07 vs D-08)**
   - What we know: D-06 says keep auto-save. D-07 says bar is visual confirmation. D-08 says "Restart" button integrates into floating bar.
   - What's unclear: Does clicking "Save Settings" in the floating bar trigger `onCommandRestart()` (as D-08 implies) or is it purely decorative?
   - Recommendation: Wire "Save Settings" to `onCommandRestart()` per D-08. The bar appearance tracks pending debounce state (D-07).

3. **AutoQueue enable toggle in card header**
   - What we know: Mockup shows the AutoQueue enable toggle in the header row (right side), not as a body option.
   - What's unclear: This requires moving the `autoqueue.enabled` option out of `OPTIONS_CONTEXT_AUTOQUEUE.options` and into the card header template.
   - Recommendation: Inline the enable toggle directly in the AutoQueue card header template (separate from the `ng-template` generic pattern). Mark this as a known template restructure in the plan.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `::ng-deep` is the right approach for brand-color toggle overrides in Sonarr/Radarr cards | Architecture Patterns (Pitfall 6) | If the project has strict `::ng-deep` prohibition, must expose CSS custom property instead — minor rework | [ASSUMED] |
| A2 | The existing Karma/Jasmine test runner (`ng test`) works without additional config | Validation Architecture | If test runner is broken (e.g., Chrome not available in env), Wave 0 spec creation may need headless config | [ASSUMED] |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: design.html] — Direct read of AIDesigner mockup, all CSS classes and layout patterns extracted verbatim
- [VERIFIED: settings-page.component.html/scss/ts] — Direct read of all existing settings source files
- [VERIFIED: option.component.html/scss/ts] — Direct read of OptionComponent
- [VERIFIED: _bootstrap-variables.scss, styles.scss] — Direct read of all palette variables

### Secondary (MEDIUM confidence)
- [CITED: Angular docs] — `ChangeDetectionStrategy.OnPush` + `markForCheck()` pattern, well-established
- [CITED: CSS specification] — CSS sibling selector for custom checkbox/toggle is a standard pattern

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code verified by direct file read
- Architecture: HIGH — mockup classes read verbatim, SCSS translations are direct mappings
- Pitfalls: HIGH — derived from actual code structure (OnPush, View Encapsulation, debounce timing)

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable project — no external packages changing)
