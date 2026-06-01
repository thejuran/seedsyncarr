# Phase 105: Font Awesome to Phosphor Migration — Pattern Map

**Mapped:** 2026-06-01
**Files analyzed:** 17 (11 source + 2 config + 4 specs)
**Analogs found:** 17 / 17 (all files have a Phosphor-pattern analog in-repo)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pages/files/dashboard-log-pane.component.html` | HTML template | request-response | `pages/about/about-page.component.html` | exact — same `<i class="ph ph-*">` static idiom |
| `pages/files/dashboard-log-pane.component.scss` | SCSS | — | `pages/logs/logs-page.component.scss` | role-match — same selector-rename pattern |
| `pages/files/stats-strip.component.html` | HTML template | request-response | `pages/about/about-page.component.html` | exact — static `ph ph-*` idiom |
| `pages/files/transfer-row.component.html` | HTML template | request-response | `pages/about/about-page.component.html` | exact — static `ph ph-*` idiom |
| `pages/files/transfer-table.component.html` | HTML template (mixed) | request-response | `pages/files/transfer-table.component.html` lines 33-35 | self-analog — already uses `ph-bold [class.ph-*]` |
| `pages/files/bulk-actions-bar.component.html` | HTML template | request-response | `pages/about/about-page.component.html` | exact — static `ph ph-*` idiom |
| `pages/logs/logs-page.component.html` | HTML template (conditional bindings) | event-driven | `pages/files/transfer-table.component.html` lines 33-35 | exact — `[class.ph-*]` conditional binding pattern |
| `pages/logs/logs-page.component.scss` | SCSS | — | `pages/files/dashboard-log-pane.component.scss` line 38 | role-match — same `.fa-*` → `.ph-*` rename |
| `pages/main/notification-bell.component.html` | HTML template | event-driven | `pages/about/about-page.component.html` | exact — static `ph ph-*` idiom |
| `pages/main/app.component.html` | HTML template (dynamic `[ngClass]`) | event-driven | `pages/files/transfer-table.component.html` lines 33-35 | exact — `[class.ph-*]` / `[ngClass]` with `ph` prefix |
| `pages/main/app.component.ts` | TS data file | — | self — NAV_ICONS string map | n/a (string literal swap) |
| `pages/settings/settings-page.component.html` | HTML template (dynamic binding + conditional) | request-response | `pages/files/transfer-table.component.html` lines 33-35 + `pages/about/about-page.component.html` | exact (both patterns present) |
| `pages/settings/settings-page.component.scss` | SCSS | — | `pages/logs/logs-page.component.scss` lines 149-158 | exact — same consolidation of `i.fa, i.ph` → `i.ph` |
| `pages/settings/option.component.html` | HTML template (dynamic + conditional) | request-response | `pages/files/transfer-table.component.html` lines 33-35 | exact — `[class.ph-*]` and interpolated prefix |
| `pages/settings/options-list.ts` | TS data file | — | `pages/main/app.component.ts` NAV_ICONS | exact — icon string literal swap |
| `src/angular/package.json` | config (dep removal) | — | Phase 104 pattern | config-only |
| `src/angular/angular.json` | config (stylesheet removal) | — | Phase 104 pattern | config-only |

**Spec files** (4, updated not created):

| Spec File | Role | Analog |
|-----------|------|--------|
| `tests/unittests/pages/files/stats-strip.component.spec.ts` | unit spec | self — inline template + DOM selector assertions |
| `tests/unittests/pages/files/dashboard-log-pane.component.spec.ts` | unit spec | self — inline template strings |
| `tests/unittests/pages/files/transfer-table.component.spec.ts` | unit spec | self — inline template + DOM selector assertions |
| `tests/unittests/pages/main/notification-bell.component.spec.ts` | unit spec | self — inline template strings |

---

## Pattern Assignments

---

### PATTERN A — Static `ph ph-*` icon idiom (canonical)

**Analog source:** `src/angular/src/app/pages/about/about-page.component.html`

This is the authoritative in-repo Phosphor pattern. Every direct `fa fa-*` replacement follows this form exactly.

**Regular weight** (lines 21, 59–72):
```html
<i class="ph ph-info"></i>
<i class="ph ph-github-logo"></i>
<i class="ph ph-book"></i>
<i class="ph ph-bug"></i>
<i class="ph ph-git-commit"></i>
```

**Fill weight** (line 79):
```html
<i class="ph-fill ph-scales"></i>
```

**Rule:** `<i class="fa fa-{x}">` → `<i class="ph ph-{mapped-x}">`. The two-class idiom (`ph` weight-prefix + `ph-{name}` icon-name) is mandatory. Never use a single class like `<i class="ph-bell">`.

---

### PATTERN B — `ph-bold` conditional `[class.ph-*]` idiom (in-repo: transfer-table)

**Analog source:** `src/angular/src/app/pages/files/transfer-table.component.html`

This file already mixes Phosphor conditional bindings alongside the remaining `fa-search` (line 13). The `ph-bold` + `[class.ph-caret-*]` block is the load-bearing reference for how `[class.ph-*]` conditional bindings look in this codebase.

**Bold-weight conditional binding** (lines 33-35, 80-82, 110-113):
```html
<i class="ph-bold"
   [class.ph-caret-down]="activeSegment !== 'active'"
   [class.ph-caret-up]="activeSegment === 'active'"></i>
```

**Pattern for all `[class.fa-*]` → `[class.ph-*]` replacements:**
- The static prefix class on the `<i>` changes from `fa` to `ph`
- Each `[class.fa-{x}]` binding becomes `[class.ph-{mapped-x}]`
- Example (logs-page autoscroll toggle, line 35):
  ```html
  <!-- BEFORE -->
  <i class="fa" [class.fa-check-circle]="autoScroll" [class.fa-circle-o]="!autoScroll"></i>
  <!-- AFTER -->
  <i class="ph" [class.ph-check-circle]="autoScroll" [class.ph-circle]="!autoScroll"></i>
  ```
- Example (settings-page webhook copy, line 308):
  ```html
  <!-- BEFORE -->
  <i class="fa" [class.fa-check]="sonarrWebhookCopied" [class.fa-copy]="!sonarrWebhookCopied"></i>
  <!-- AFTER -->
  <i class="ph" [class.ph-check]="sonarrWebhookCopied" [class.ph-copy]="!sonarrWebhookCopied"></i>
  ```

---

### PATTERN C — Dynamic interpolated icon binding

**Analog source (current — FA form):**
- `src/angular/src/app/pages/settings/settings-page.component.html` line 4
- `src/angular/src/app/pages/settings/option.component.html` line 13

**Current FA form:**
```html
<!-- settings-page.component.html line 4 -->
<i class="fa {{icon}}"></i>
<!-- option.component.html line 13 -->
<span class="input-icon"><i class="fa {{icon}}"></i></span>
```

**After migration — only the static prefix class changes; the interpolation token is unchanged:**
```html
<i class="ph {{icon}}"></i>
<span class="input-icon"><i class="ph {{icon}}"></i></span>
```

The data strings in `options-list.ts` change from `"fa-*"` to `"ph-*"` (see Pattern E), so the combined rendered class becomes `ph ph-{name}` — valid Phosphor.

**Pitfall to avoid (Pitfall 2 from RESEARCH.md):** Never update only the template prefix without updating the data strings, or only the data strings without the template prefix. They must move together.

---

### PATTERN D — `[ngClass]` dynamic nav icon binding

**Analog source:** `src/angular/src/app/pages/main/app.component.html` line 21

**Current FA form:**
```html
<i class="fa" [ngClass]="navIcon(routeInfo.path)"></i>
```

**After migration:**
```html
<i class="ph" [ngClass]="navIcon(routeInfo.path)"></i>
```

The `navIcon()` method returns the icon portion only (e.g., `"fa-th-large"` → after migration `"ph-squares-four"`). The static prefix class (`fa` → `ph`) is on the element itself. Both must change.

---

### PATTERN E — TS icon data string literals

**Source files:** `src/angular/src/app/pages/settings/options-list.ts` and `src/angular/src/app/pages/main/app.component.ts`

**options-list.ts current (lines 19, 75, 101, 150, 170, 196, 222):**
```typescript
icon: "fa-server"
icon: "fa-search"
icon: "fa-tachometer"
icon: "fa-sliders"
icon: "fa-list"
icon: "fa-trash"
icon: "fa-file-archive-o"
```

**After migration:**
```typescript
icon: "ph-computer-tower"
icon: "ph-magnifying-glass"
icon: "ph-gauge"
icon: "ph-sliders-horizontal"
icon: "ph-list"
icon: "ph-trash"
icon: "ph-file-archive"
```

**app.component.ts NAV_ICONS current (lines 92-100):**
```typescript
private static readonly NAV_ICONS: Record<string, string> = {
    dashboard: "fa-th-large",
    settings: "fa-cog",
    logs: "fa-terminal",
    about: "fa-info-circle"
};
navIcon(path: string): string {
    return AppComponent.NAV_ICONS[path] ?? "fa-circle";
}
```

**After migration:**
```typescript
private static readonly NAV_ICONS: Record<string, string> = {
    dashboard: "ph-squares-four",
    settings: "ph-gear",
    logs: "ph-terminal",
    about: "ph-info"
};
navIcon(path: string): string {
    return AppComponent.NAV_ICONS[path] ?? "ph-circle";
}
```

The `IOptionsContext.icon` interface type (`string`) does not change. No interface modifications needed.

---

### PATTERN F — SCSS selector renaming

#### F1 — Single-selector rename (dashboard-log-pane)

**Source:** `src/angular/src/app/pages/files/dashboard-log-pane.component.scss` line 38

**Current:**
```scss
.log-pane__title {
  .fa-terminal {
    color: $primary;
  }
}
```

**After migration:**
```scss
.log-pane__title {
  .ph-terminal {
    color: $primary;
  }
}
```

#### F2 — Single-selector rename in BEM modifier (logs-page)

**Source:** `src/angular/src/app/pages/logs/logs-page.component.scss` lines 149-158

**Current:**
```scss
&--active .fa-check-circle {
    color: $success;
    font-size: 1.125rem;
}

&:not(.action-btn--active) {
    .fa-circle-o {
        color: $textsec;
    }
    color: $textsec;
}
```

**After migration:**
```scss
&--active .ph-check-circle {
    color: $success;
    font-size: 1.125rem;
}

&:not(.action-btn--active) {
    .ph-circle {
        color: $textsec;
    }
    color: $textsec;
}
```

Note: `fa-circle-o` maps to `ph-circle` (not `ph-circle-o` — Phosphor drops the `-o` suffix).

#### F3 — `i.fa, i.ph` consolidation (settings-page)

**Source:** `src/angular/src/app/pages/settings/settings-page.component.scss`

Three occurrences of `i.fa, i.ph` (lines 47, 271, 306) — remove the `i.fa,` dead selector, keep `i.ph`:

**Current (line 47):**
```scss
i.fa, i.ph {
    font-size: 1rem;
    color: var(--app-muted-text);
}
```

**After migration:**
```scss
i.ph {
    font-size: 1rem;
    color: var(--app-muted-text);
}
```

Same consolidation applies at lines 271 (Sonarr `i.fa, i.ph { color: #00c2ff; }`) and 306 (Radarr `i.fa, i.ph { color: #ffc230; }`).

#### F4 — `i.fa` only → `i.ph` (settings-page autodelete card)

**Source:** `src/angular/src/app/pages/settings/settings-page.component.scss` line 334

**Current:**
```scss
i.fa { color: $danger; }
```

**After migration:**
```scss
i.ph { color: $danger; }
```

#### F5 — `.fa-check` → `.ph-check` in button selectors (settings-page)

**Source:** lines 132 and 560

**Current:**
```scss
.webhook-copy-btn .fa-check { color: $check-green; }   /* line 132 */
.fa-check { color: $check-green; }                      /* line 560 — inside token-action-btn block */
```

**After migration:**
```scss
.webhook-copy-btn .ph-check { color: $check-green; }
.ph-check { color: $check-green; }
```

#### F6 — `ph-spin` animation rule (new addition — dashboard-log-pane.component.scss)

No existing analog in-repo (Phosphor does not ship a spin utility). Add at the end of `dashboard-log-pane.component.scss`:

```scss
// Phosphor does not ship a spin animation class; provide one locally.
@keyframes ph-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.ph-spin {
  animation: ph-spin 1s linear infinite;
  display: inline-block; // required for transform to apply on inline elements
}
```

This must be added BEFORE the FA dep is removed from `angular.json`; validate the spinner animates on dev server first.

---

### Per-file pattern map

#### `pages/files/dashboard-log-pane.component.html`

Apply Pattern A (static `ph ph-*`) to all four FA usages:

| Line | Current | After |
|------|---------|-------|
| 4 | `<i class="fa fa-terminal">` | `<i class="ph ph-terminal">` |
| 8 | `<i class="fa fa-copy">` | `<i class="ph ph-copy">` |
| 11 | `<i class="fa fa-expand">` | `<i class="ph ph-arrows-out">` |
| 18 | `<i class="fa fa-circle-o-notch fa-spin">` | `<i class="ph ph-circle-notch ph-spin">` |

#### `pages/files/dashboard-log-pane.component.scss`

Apply Pattern F1 (line 38) + Pattern F6 (new `ph-spin` block at end of file).

#### `pages/files/stats-strip.component.html`

Apply Pattern A to all eight FA usages:

| Line(s) | Current | After |
|---------|---------|-------|
| 5, 7 | `fa fa-cloud` | `ph ph-cloud` |
| 46, 48 | `fa fa-database` | `ph ph-database` |
| 87, 89 | `fa fa-arrow-down` | `ph ph-arrow-down` |
| 101, 103 | `fa fa-tasks` | `ph ph-list-checks` |

#### `pages/files/transfer-row.component.html`

Apply Pattern A to line 18:

| Line | Current | After |
|------|---------|-------|
| 18 | `<i class="fa fa-arrow-down">` | `<i class="ph ph-arrow-down">` |

#### `pages/files/transfer-table.component.html`

Apply Pattern A to line 13 only (the rest of the file already uses Phosphor):

| Line | Current | After |
|------|---------|-------|
| 13 | `<i class="fa fa-search search-icon">` | `<i class="ph ph-magnifying-glass search-icon">` |

#### `pages/files/bulk-actions-bar.component.html`

Apply Pattern A to all six FA usages:

| Line | Current | After |
|------|---------|-------|
| 19 | `fa fa-play` | `ph ph-play` |
| 24 | `fa fa-stop` | `ph ph-stop` |
| 29 | `fa fa-file-archive-o` | `ph ph-file-archive` |
| 35 | `fa fa-trash` | `ph ph-trash` |
| 40 | `fa fa-cloud` | `ph ph-cloud` |
| 40 | `fa fa-ban action-overlay` | `ph ph-prohibit action-overlay` |

#### `pages/logs/logs-page.component.html`

Apply Pattern A for static icons; Pattern B for conditional binding:

| Line | Current | After |
|------|---------|-------|
| 21 | `<i class="fa fa-search search-icon">` | `<i class="ph ph-magnifying-glass search-icon">` |
| 35 | `<i class="fa" [class.fa-check-circle]="autoScroll" [class.fa-circle-o]="!autoScroll">` | `<i class="ph" [class.ph-check-circle]="autoScroll" [class.ph-circle]="!autoScroll">` |
| 44 | `fa fa-trash` | `ph ph-trash` |
| 49 | `fa fa-download` | `ph ph-download` |
| 99 | `fa fa-clock-o` | `ph ph-clock` |

#### `pages/logs/logs-page.component.scss`

Apply Pattern F2 (lines 149 and 155).

#### `pages/main/notification-bell.component.html`

Apply Pattern A to all six FA usages:

| Line | Current | After |
|------|---------|-------|
| 4 | `fa fa-bell` | `ph ph-bell` |
| 22 | `fa fa-check-circle` | `ph ph-check-circle` |
| 23 | `fa fa-exclamation-circle` | `ph ph-warning-circle` |
| 24 | `fa fa-exclamation-triangle` | `ph ph-warning` |
| 25 | `fa fa-info-circle` | `ph ph-info` |
| 31 | `fa fa-times` | `ph ph-x` |

#### `pages/main/app.component.html`

Apply Pattern D (line 21 — prefix only):

| Line | Current | After |
|------|---------|-------|
| 21 | `<i class="fa" [ngClass]="navIcon(routeInfo.path)">` | `<i class="ph" [ngClass]="navIcon(routeInfo.path)">` |
| 37 | `<i class="fa fa-cog">` | `<i class="ph ph-gear">` |

#### `pages/main/app.component.ts`

Apply Pattern E (NAV_ICONS map, lines 92-101). See Pattern E above for full before/after.

#### `pages/settings/settings-page.component.html`

Apply Pattern A (section header static icons), Pattern B (conditional bindings), Pattern C (dynamic binding at line 4), and inline `[icon]` attribute literals:

**Dynamic binding (line 4)** — Pattern C:
```html
<!-- BEFORE --> <i class="fa {{icon}}">
<!-- AFTER  --> <i class="ph {{icon}}">
```

**Inline `[icon]` attribute literals (lines 91, 95, 99)**:
```html
<!-- BEFORE --> [icon]="'fa-folder-open-o'"  →  [icon]="'ph-folder-open'"
<!-- BEFORE --> [icon]="'fa-hdd-o'"           →  [icon]="'ph-hard-drive'"
<!-- BEFORE --> [icon]="'fa-file-code-o'"     →  [icon]="'ph-file-code'"
```

**Static section header icons** — Pattern A:
Line 32: `fa fa-sliders` → `ph ph-sliders-horizontal`
Line 56: `fa fa-server` → `ph ph-computer-tower`
Line 106: `fa fa-search` → `ph ph-magnifying-glass`
Line 141: `fa fa-tachometer` → `ph ph-gauge`
Line 175: `fa fa-list` → `ph ph-list`
Line 389: `fa fa-trash` → `ph ph-trash`
Line 421: `fa fa-shield` → `ph ph-shield`
Line 443: `fa fa-refresh` → `ph ph-arrows-clockwise`
Line 457: `fa fa-check-circle floating-save-icon--success` → `ph ph-check-circle floating-save-icon--success`
Line 471: `fa fa-floppy-o` → `ph ph-floppy-disk`

**Conditional bindings** — Pattern B:
Line 308: `<i class="fa" [class.fa-check]="sonarrWebhookCopied" [class.fa-copy]="!sonarrWebhookCopied">` → `<i class="ph" [class.ph-check]="sonarrWebhookCopied" [class.ph-copy]="!sonarrWebhookCopied">`
Line 377: same pattern for `radarrWebhookCopied`
Line 434: `<i class="fa" [class.fa-eye]="!tokenRevealed" [class.fa-eye-slash]="tokenRevealed">` → `<i class="ph" [class.ph-eye]="!tokenRevealed" [class.ph-eye-slash]="tokenRevealed">`
Line 438: `<i class="fa" [class.fa-check]="tokenCopied" [class.fa-copy]="!tokenCopied">` → `<i class="ph" [class.ph-check]="tokenCopied" [class.ph-copy]="!tokenCopied">`

#### `pages/settings/settings-page.component.scss`

Apply Patterns F3 (lines 47, 271, 306), F4 (line 334), F5 (lines 132, 560).

#### `pages/settings/option.component.html`

Apply Pattern C (line 13 — prefix only) and Pattern B (line 68 — conditional binding):

```html
<!-- Line 13 BEFORE --> <span class="input-icon"><i class="fa {{icon}}"></i></span>
<!-- Line 13 AFTER  --> <span class="input-icon"><i class="ph {{icon}}"></i></span>

<!-- Line 68 BEFORE --> <i class="fa" [class.fa-eye]="!passwordVisible" [class.fa-eye-slash]="passwordVisible">
<!-- Line 68 AFTER  --> <i class="ph" [class.ph-eye]="!passwordVisible" [class.ph-eye-slash]="passwordVisible">
```

#### `pages/settings/options-list.ts`

Apply Pattern E. See Pattern E above for all seven string literal swaps (lines 19, 75, 101, 150, 170, 196, 222).

---

## Shared Patterns

### Phosphor static icon idiom (apply to all static `fa fa-*` replacements)
**Source:** `src/angular/src/app/pages/about/about-page.component.html` lines 21, 59–72, 79
```html
<i class="ph ph-{name}"></i>          <!-- regular weight -->
<i class="ph-fill ph-{name}"></i>     <!-- fill weight (existing usages only — don't introduce new) -->
<i class="ph-bold ph-{name}"></i>     <!-- bold weight (existing usages only — don't introduce new) -->
```

### Phosphor conditional binding idiom (apply to all `[class.fa-*]` replacements)
**Source:** `src/angular/src/app/pages/files/transfer-table.component.html` lines 33-35
```html
<i class="ph"
   [class.ph-{icon-a}]="condition"
   [class.ph-{icon-b}]="!condition"></i>
```
The static class on the `<i>` is the weight prefix (`ph`, `ph-bold`, or `ph-fill`). The conditional classes supply the icon name.

### Dynamic interpolated icon idiom (apply to all `<i class="fa {{...}}">` replacements)
**Source:** `settings-page.component.html:4` and `option.component.html:13` (to-be-migrated to)
```html
<i class="ph {{icon}}"></i>
```
Requires corresponding data-string migration in `options-list.ts` (all icon values from `"fa-*"` to `"ph-*"`).

---

## No Analog Found

None. All patterns are covered by in-repo Phosphor usages or by the to-be-migrated FA forms (which are their own reference). The spinner `ph-spin` animation has no in-repo analog but RESEARCH.md Section 4 provides the exact CSS block to add.

---

## Pre-Code Checkpoint Required

Per D-01 and RESEARCH.md Section 5, **8 ambiguous icon mappings require explicit user sign-off before any replacement code lands**. The planner must insert a `checkpoint:human-verify` task as the first step — before any source edit. The proposals (from RESEARCH.md Section 1b):

| # | FA class | Proposed Phosphor | Where used |
|---|----------|-------------------|------------|
| Q1 | `fa-tachometer` | `ph-gauge` | settings-page:141, options-list.ts:101 |
| Q2 | `fa-floppy-o` | `ph-floppy-disk` | settings-page:471 |
| Q3 | `fa-hdd-o` | `ph-hard-drive` | settings-page:95 |
| Q4 | `fa-file-archive-o` | `ph-file-archive` | bulk-actions-bar:29, settings-page:206, options-list.ts:222 |
| Q5 | `fa-circle-o-notch` + `fa-spin` | `ph-circle-notch` + custom `.ph-spin` CSS | dashboard-log-pane:18 |
| Q6 | `fa-th-large` | `ph-squares-four` | app.component.ts:93 |
| Q7 | `fa-sliders` | `ph-sliders-horizontal` | settings-page:32, options-list.ts:150 |
| Q8 | `fa-file-code-o` | `ph-file-code` | settings-page:99 |

---

## Spec File Pattern

All 4 spec files use `overrideTemplate` with inline HTML strings. The pattern for each is identical: update the inline template copy to match the real component template post-migration, then update any `querySelector(".fa-*")` DOM assertions.

**Transfer-table spec example** (lines 25 and 202):
```typescript
// Inline template — BEFORE
<i class="fa fa-search search-icon">
// Inline template — AFTER
<i class="ph ph-magnifying-glass search-icon">

// DOM assertion — BEFORE
fixture.nativeElement.querySelector(".fa-search")
// DOM assertion — AFTER
fixture.nativeElement.querySelector(".ph-magnifying-glass")
```

**Stats-strip spec example** (lines 182, 190, 198, 206, 242):
```typescript
// BEFORE
el.querySelector(".stat-icon.fa-cloud")
el.querySelector(".stat-icon.fa-database")
el.querySelector(".stat-icon.fa-arrow-down")
el.querySelector(".stat-icon.fa-tasks")
// AFTER
el.querySelector(".stat-icon.ph-cloud")
el.querySelector(".stat-icon.ph-database")
el.querySelector(".stat-icon.ph-arrow-down")
el.querySelector(".stat-icon.ph-list-checks")
```

The dashboard-log-pane and notification-bell specs have no DOM class-name assertions to update — only their inline template strings change.

---

## Metadata

**Analog search scope:** `src/angular/src/app/pages/` (all subdirectories)
**Files read:** about-page.component.html, settings-page.component.html (lines 1-60, 300-330, 425-455), transfer-table.component.html, dashboard-log-pane.component.html, stats-strip.component.html, bulk-actions-bar.component.html, logs-page.component.html (lines 1-60), logs-page.component.scss (lines 140-189), notification-bell.component.html, app.component.html (lines 1-45), app.component.ts (lines 87-104), option.component.html (lines 1-73), options-list.ts (lines 1-50), dashboard-log-pane.component.scss, settings-page.component.scss (lines 44-51, 125-135, 265-285, 300-320, 330-350, 555-565)
**Pattern extraction date:** 2026-06-01
