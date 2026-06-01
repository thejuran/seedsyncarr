# Phase 105: Font Awesome to Phosphor Migration — Research

**Researched:** 2026-06-01
**Domain:** Angular icon library migration (Font Awesome 4.7 → @phosphor-icons/web 2.1.2)
**Confidence:** HIGH — all mappings verified against installed `node_modules/@phosphor-icons/web/src/regular/style.css`; all source files read directly.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Claude produces a complete fa→ph mapping table for all ~39 distinct `fa-*` classes. Obvious 1:1 mappings are auto-applied. The ~8 ambiguous icons are proposed with rationale and paused for user sign-off before replacement code lands.
- **D-02:** Migrated icons default to regular `ph` weight. Do not introduce new `ph-bold`/`ph-fill` weights the app didn't already have for that icon. Existing deliberate bold/fill in already-migrated templates stay as-is.
- **D-03:** The 4 unit specs that reference FA classes are updated faithfully to the exact Phosphor class the component now renders — both `querySelector` assertions and inline host-template strings. No loosening to library-agnostic assertions. Karma floors (stmts/branches/fns/lines 83/68/79/83) must hold or rise.
- **D-04:** Visual verification follows the Phase 104 rhythm: dev-server manual smoke test after the production build is green. Surfaces to cover: dashboard stats strip, transfer rows, bulk-actions bar, settings page (incl. dynamic `{{icon}}` binding + conditional toggles), logs page, dashboard log pane, notification bell.
- **D-05:** All five edit layers are in scope: `.html` direct classes; `options-list.ts` data strings; dynamic `<i class="fa {{icon}}">` bindings; conditional `[class.fa-*]` toggle bindings; `.scss` selectors keyed on `.fa-*`.
- **D-06:** Only after all usages migrated and build + smoke test green: remove `font-awesome` from `src/angular/package.json`, remove both `font-awesome/css/font-awesome.css` lines from `angular.json` (build + test/serve), regenerate `package-lock.json` via `npm install`.
- **D-07:** Before/after production bundle-size delta (Phase 104 D-02 pattern) showing FA CSS + font files left the bundle and total size ≤ Phase 104 baseline.

### Claude's Discretion

- Exact final Phosphor class for each non-ambiguous icon (the obvious 1:1 set in D-01).
- Commit granularity within the phase — planner's call, but the `font-awesome` drop should be its own clean closing commit per the audit→migrate→drop→verify rhythm.
- The precise mechanism for capturing bundle stats (build-output table vs `stats.json`).
- Whether to also run the full Karma suite during verification in addition to the targeted specs (recommended).

### Deferred Ideas (OUT OF SCOPE)

- Mock-fixture bundle hygiene (DEPS-02) — Phase 106.
- Backend dependency hardening.
- Adding `data-testid`/aria hooks for icons.
- Playwright screenshot-diff harness for icon regression.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPS-01b | Angular app no longer depends on Font Awesome 4.7; every `fa-*` usage inventoried and replaced with `@phosphor-icons/web` equivalent; FA dep removed; no icon renders missing or visually regressed; only one icon library ships. | Full mapping table (Section 1), migration surface map (Section 2), verification mechanics (Section 3). |
</phase_requirements>

---

## Summary

`@phosphor-icons/web` **2.1.2** is already installed and wired in `angular.json`. The migration completes an in-progress transition: Phosphor is already used in `about-page`, `settings-page` (Sonarr/Radarr card headers), and `transfer-table`; roughly 85 remaining `fa-` strings span ~12 source files across 6 edit layers.

All 39 distinct `fa-*` icon classes have been verified against the installed `node_modules/@phosphor-icons/web/src/regular/style.css`. Every proposed `ph-*` class name in this document was confirmed to exist in that file before being recorded here. Five icons proposed in CONTEXT.md D-01 as ambiguous (`fa-server`, `fa-tachometer`, `fa-floppy-o`, `fa-hdd-o`, `fa-file-archive-o`) have close Phosphor equivalents that exist in the installed package and are recommended below with rationale. Three remain genuinely judgment-call ambiguous (`fa-circle-o-notch`+`fa-spin`, `fa-th-large`, `fa-file-code-o`) and are flagged for user sign-off.

The key complexity is not the 1:1 class swaps — it is the **dynamic-binding layer**: `app.component.ts` NAV_ICONS map and `options-list.ts` contain `"fa-*"` strings that are interpolated at runtime into `<i class="fa {{icon}}">`. Both the static prefix (`fa`) and the data strings must change together to form valid Phosphor classes (`ph` + `ph-*`). The spinner `fa-spin` animation modifier has no equivalent in Phosphor's CSS — a one-line `@keyframes` spin rule must be added (suggested: `dashboard-log-pane.component.scss` or `styles.scss`).

**Primary recommendation:** Migrate all six layers in a single large commit per component cluster, then close with a separate atomic commit that drops the FA dep and the two `angular.json` entries — mirroring the Phase 104 audit→migrate→drop→verify rhythm.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Icon rendering | Browser / Client | — | Pure CSS font + class-binding; no server involvement |
| Icon library stylesheet loading | Frontend (Angular build) | — | `angular.json` styles array loaded at build time |
| Dynamic icon class assembly | Frontend (Angular template) | TS data layer | `{{icon}}` binding resolves at runtime in the browser; source data strings live in `options-list.ts` |
| Test assertions on icon classes | Test layer (Karma) | — | Unit specs assert on rendered DOM class names |

---

## 1. Authoritative FA→Phosphor Mapping Table

All `ph-*` class names verified to exist in the installed `@phosphor-icons/web` 2.1.2 regular CSS (`node_modules/@phosphor-icons/web/src/regular/style.css`).
[VERIFIED: node_modules/@phosphor-icons/web/src/regular/style.css]

### 1a. Confident Mappings (39 classes)

| FA4 class | Phosphor class | HTML idiom | Weight | Confidence | Notes |
|-----------|----------------|------------|--------|------------|-------|
| `fa-arrow-down` | `ph-arrow-down` | `<i class="ph ph-arrow-down">` | regular | Confident | Exact name match |
| `fa-bell` | `ph-bell` | `<i class="ph ph-bell">` | regular | Confident | Exact name match |
| `fa-check` | `ph-check` | `<i class="ph ph-check">` | regular | Confident | Exact name match |
| `fa-check-circle` | `ph-check-circle` | `<i class="ph ph-check-circle">` | regular | Confident | Exact name match; used as static class AND in conditional bindings |
| `fa-circle` | `ph-circle` | `<i class="ph ph-circle">` | regular | Confident | In Phosphor, `ph-circle` is the outline variant |
| `fa-circle-o` | `ph-circle` | `<i class="ph ph-circle">` | regular | Confident | Both FA `fa-circle-o` (outline) and `fa-circle` (filled) map to `ph-circle` regular; see Section 1b for toggle distinction |
| `fa-clock-o` | `ph-clock` | `<i class="ph ph-clock">` | regular | Confident | FA "-o" suffix means outline; Phosphor regular is outline |
| `fa-cloud` | `ph-cloud` | `<i class="ph ph-cloud">` | regular | Confident | Exact name match |
| `fa-cog` | `ph-gear` | `<i class="ph ph-gear">` | regular | Confident | Industry-standard rename; confirmed in D-01 |
| `fa-copy` | `ph-copy` | `<i class="ph ph-copy">` | regular | Confident | Exact name match |
| `fa-database` | `ph-database` | `<i class="ph ph-database">` | regular | Confident | Exact name match |
| `fa-download` | `ph-download` | `<i class="ph ph-download">` | regular | Confident | Exact name match |
| `fa-exclamation-circle` | `ph-warning-circle` | `<i class="ph ph-warning-circle">` | regular | Confident | Phosphor uses "warning" not "exclamation"; same visual intent (circled alert) |
| `fa-exclamation-triangle` | `ph-warning` | `<i class="ph ph-warning">` | regular | Confident | FA triangle-exclamation = Phosphor `ph-warning` (triangle caution icon) |
| `fa-expand` | `ph-arrows-out` | `<i class="ph ph-arrows-out">` | regular | Confident | Confirmed in D-01; expand/fullscreen intent |
| `fa-eye` | `ph-eye` | `<i class="ph ph-eye">` | regular | Confident | Exact name match |
| `fa-eye-slash` | `ph-eye-slash` | `<i class="ph ph-eye-slash">` | regular | Confident | Exact name match |
| `fa-folder-open-o` | `ph-folder-open` | `<i class="ph ph-folder-open">` | regular | Confident | Confirmed in D-01; "-o" suffix drops in Phosphor |
| `fa-info-circle` | `ph-info` | `<i class="ph ph-info">` | regular | Confident | Phosphor `ph-info` is the circled-i; equivalent intent |
| `fa-list` | `ph-list` | `<i class="ph ph-list">` | regular | Confident | Exact name match |
| `fa-play` | `ph-play` | `<i class="ph ph-play">` | regular | Confident | Exact name match |
| `fa-plus-circle` | `ph-plus-circle` | `<i class="ph ph-plus-circle">` | regular | Confident | Exact name match |
| `fa-refresh` | `ph-arrows-clockwise` | `<i class="ph ph-arrows-clockwise">` | regular | Confident | Confirmed in D-01; refresh/reload intent |
| `fa-search` | `ph-magnifying-glass` | `<i class="ph ph-magnifying-glass">` | regular | Confident | Confirmed in D-01; industry-standard rename |
| `fa-shield` | `ph-shield` | `<i class="ph ph-shield">` | regular | Confident | Exact name match |
| `fa-stop` | `ph-stop` | `<i class="ph ph-stop">` | regular | Confident | Exact name match |
| `fa-tasks` | `ph-list-checks` | `<i class="ph ph-list-checks">` | regular | Confident | Confirmed in D-01; tasks/checklist intent |
| `fa-terminal` | `ph-terminal` | `<i class="ph ph-terminal">` | regular | Confident | Exact name match |
| `fa-times` | `ph-x` | `<i class="ph ph-x">` | regular | Confident | Confirmed in D-01; close/dismiss intent |
| `fa-trash` | `ph-trash` | `<i class="ph ph-trash">` | regular | Confident | Exact name match |
| `fa-ban` | `ph-prohibit` | `<i class="ph ph-prohibit">` | regular | Confident | Confirmed in D-01; no-entry circle/slash intent. NOTE: `ph-ban` does not exist in v2.1.2; `ph-prohibit` is the correct class. |

### 1b. Ambiguous / Judgment-Call Mappings (8 icons — require user sign-off per D-01)

These are the CONTEXT.md D-01 flagged set. Each proposed class was verified to exist in the installed package.

| FA4 class | Recommended Phosphor class | HTML idiom | Weight | Confidence | Rationale |
|-----------|---------------------------|------------|--------|------------|-----------|
| `fa-tachometer` | `ph-gauge` | `<i class="ph ph-gauge">` | regular | Ambiguous | `ph-gauge` is the standard speedometer/dashboard icon in Phosphor. `ph-tachometer` does not exist. Used as section header icon for "LFTP Connection Limits" and in `options-list.ts`. Intent is "performance limits / speed settings." |
| `fa-floppy-o` | `ph-floppy-disk` | `<i class="ph ph-floppy-disk">` | regular | Ambiguous | `ph-floppy-disk` is the save/disk icon in Phosphor. `ph-floppy-o` does not exist; Phosphor drops the "-o" suffix. Used in "Save Settings" button. |
| `fa-hdd-o` | `ph-hard-drive` | `<i class="ph ph-hard-drive">` | regular | Ambiguous | `ph-hard-drive` represents local storage/disk. `ph-hdd-o` does not exist. Used as icon for "Local Directory" field in option component. |
| `fa-file-archive-o` | `ph-file-archive` | `<i class="ph ph-file-archive">` | regular | Ambiguous | `ph-file-archive` exists and represents an archive/zip file. `ph-file-zip` also exists. `ph-file-archive` is the closer semantic match for "Archive Operations" section header and "Extract" button. Both are valid; recommended `ph-file-archive` for semantic fidelity. |
| `fa-circle-o-notch` + `fa-spin` | `ph-circle-notch` + custom spin CSS | `<i class="ph ph-circle-notch ph-spin">` | regular | Ambiguous | `ph-circle-notch` exists and is a partial/notched circle (the loading arc icon). `fa-spin` is a CSS animation class provided by FA's stylesheet — **Phosphor 2.1.2 does NOT provide a `ph-spin` class**. A custom `@keyframes spin` + `.ph-spin` rule must be added to the project (see Section 4). |
| `fa-th-large` | `ph-squares-four` | `<i class="ph ph-squares-four">` | regular | Ambiguous | `ph-squares-four` is a 2x2 grid icon, closest to FA's `fa-th-large` (large grid/dashboard view). `ph-grid-four` and `ph-grid-nine` also exist; `ph-squares-four` best matches the "large tiles" intent. Used in `app.component.ts` NAV_ICONS as the dashboard nav icon. |
| `fa-sliders` | `ph-sliders-horizontal` | `<i class="ph ph-sliders-horizontal">` | regular | Ambiguous | Both `ph-sliders` and `ph-sliders-horizontal` exist. FA `fa-sliders` renders vertical sliders. Phosphor `ph-sliders` is also vertical; `ph-sliders-horizontal` is more common for "settings/equalizer" in modern UIs. Used as "General Options" section header and in `options-list.ts`. Recommend `ph-sliders-horizontal` for the horizontal equalizer appearance, but `ph-sliders` works equally. |
| `fa-file-code-o` | `ph-file-code` | `<i class="ph ph-file-code">` | regular | Ambiguous | `ph-file-code` exists. `ph-file-code-o` does not exist; Phosphor drops the "-o" suffix. Used as icon for "Server Script Path" option input field. Intent is "script file / code file." |

### 1c. Toggle-State Fill vs. Outline Convention

The logs-page autoscroll toggle uses `[class.fa-check-circle]="autoScroll" [class.fa-circle-o]="!autoScroll"` — two visually distinct states.

- **Active (autoScroll true):** `fa-check-circle` → `ph-check-circle` (regular outline; distinct check-in-circle)
- **Inactive (autoScroll false):** `fa-circle-o` → `ph-circle` (regular outline plain circle)

These are already visually distinct in Phosphor regular weight — `ph-check-circle` has a checkmark, `ph-circle` is a plain circle. The SCSS rules in `logs-page.component.scss` that color them must also update (`.fa-check-circle` → `.ph-check-circle`, `.fa-circle-o` → `.ph-circle`).

**Important:** The `fa-circle` class (not `fa-circle-o`) appears only in `app.component.ts` as a fallback return value (`return AppComponent.NAV_ICONS[path] ?? "fa-circle"`). This is a catch-all for unknown routes. Map to `ph-circle` (regular). Since `navIcon()` returns only the icon portion of the class string, the fallback also needs `"ph-circle"`.

### 1d. Spinner Animation — Special Case

The `fa-spin` modifier is used exactly once:

```html
<!-- dashboard-log-pane.component.html:18 -->
<i class="fa fa-circle-o-notch fa-spin"></i>
```

After migration:

```html
<i class="ph ph-circle-notch ph-spin"></i>
```

Phosphor 2.1.2 provides NO `ph-spin` animation class. The `.fa-spin` animation was sourced entirely from Font Awesome's CSS. Once FA CSS is removed, the spinner will freeze unless a replacement spin rule is added. **A `@keyframes` + `.ph-spin` CSS rule must be added to the project.** Recommended location: `dashboard-log-pane.component.scss` (scoped) or `styles.scss` (global, reusable). The keyframes already used by Bootstrap's `spinner-border` are in scope but class-scoped to Bootstrap — a separate `.ph-spin` rule is needed.

Proposed addition (one-time, ~6 lines):

```scss
// Required: Phosphor does not ship a spin animation class
@keyframes ph-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.ph-spin {
  animation: ph-spin 1s linear infinite;
}
```

---

## 2. Migration Surface Map

Complete inventory of every location requiring edits. All line numbers are from the files read during this research session. [VERIFIED: direct file reads]

### 2a. HTML Templates (Direct `fa fa-*` classes)

| File | Line(s) | Current class(es) | Replacement | Notes |
|------|---------|-------------------|-------------|-------|
| `pages/files/dashboard-log-pane.component.html` | 4 | `fa fa-terminal` | `ph ph-terminal` | Title icon |
| `pages/files/dashboard-log-pane.component.html` | 8 | `fa fa-copy` | `ph ph-copy` | Copy logs button |
| `pages/files/dashboard-log-pane.component.html` | 11 | `fa fa-expand` | `ph ph-arrows-out` | Expand link |
| `pages/files/dashboard-log-pane.component.html` | 18 | `fa fa-circle-o-notch fa-spin` | `ph ph-circle-notch ph-spin` | Spinner — requires new `ph-spin` CSS rule |
| `pages/files/stats-strip.component.html` | 5,7 | `fa fa-cloud` | `ph ph-cloud` | Watermark + stat-icon (both instances) |
| `pages/files/stats-strip.component.html` | 46,48 | `fa fa-database` | `ph ph-database` | Watermark + stat-icon (both instances) |
| `pages/files/stats-strip.component.html` | 87,89 | `fa fa-arrow-down` | `ph ph-arrow-down` | Watermark + stat-icon (both instances) |
| `pages/files/stats-strip.component.html` | 101,103 | `fa fa-tasks` | `ph ph-list-checks` | Watermark + stat-icon (both instances) |
| `pages/files/transfer-row.component.html` | 18 | `fa fa-arrow-down` | `ph ph-arrow-down` | Download status icon in table row |
| `pages/files/transfer-table.component.html` | 13 | `fa fa-search search-icon` | `ph ph-magnifying-glass search-icon` | Search box icon |
| `pages/files/bulk-actions-bar.component.html` | 19 | `fa fa-play` | `ph ph-play` | Queue button icon |
| `pages/files/bulk-actions-bar.component.html` | 24 | `fa fa-stop` | `ph ph-stop` | Stop button icon |
| `pages/files/bulk-actions-bar.component.html` | 29 | `fa fa-file-archive-o` | `ph ph-file-archive` | Extract button icon |
| `pages/files/bulk-actions-bar.component.html` | 35 | `fa fa-trash` | `ph ph-trash` | Delete Local button icon |
| `pages/files/bulk-actions-bar.component.html` | 40 | `fa fa-cloud` + `fa fa-ban action-overlay` | `ph ph-cloud` + `ph ph-prohibit action-overlay` | Delete Remote: two stacked icons (cloud + prohibit overlay) |
| `pages/logs/logs-page.component.html` | 21 | `fa fa-search search-icon` | `ph ph-magnifying-glass search-icon` | Search field icon |
| `pages/logs/logs-page.component.html` | 44 | `fa fa-trash` | `ph ph-trash` | Clear button |
| `pages/logs/logs-page.component.html` | 49 | `fa fa-download` | `ph ph-download` | Export button |
| `pages/logs/logs-page.component.html` | 99 | `fa fa-clock-o` | `ph ph-clock` | Status bar timestamp icon |
| `pages/main/notification-bell.component.html` | 4 | `fa fa-bell` | `ph ph-bell` | Bell button icon |
| `pages/main/notification-bell.component.html` | 22 | `fa fa-check-circle` | `ph ph-check-circle` | Success notification icon |
| `pages/main/notification-bell.component.html` | 23 | `fa fa-exclamation-circle` | `ph ph-warning-circle` | Danger notification icon |
| `pages/main/notification-bell.component.html` | 24 | `fa fa-exclamation-triangle` | `ph ph-warning` | Warning notification icon |
| `pages/main/notification-bell.component.html` | 25 | `fa fa-info-circle` | `ph ph-info` | Default notification icon |
| `pages/main/notification-bell.component.html` | 31 | `fa fa-times` | `ph ph-x` | Dismiss button icon |
| `pages/main/app.component.html` | 37 | `fa fa-cog` | `ph ph-gear` | Settings nav button (direct class) |
| `pages/settings/settings-page.component.html` | 4 | `fa {{icon}}` | `ph {{icon}}` | Dynamic template binding — prefix only changes; data string migrated in 2b |
| `pages/settings/settings-page.component.html` | 32 | `fa fa-sliders` | `ph ph-sliders-horizontal` | General Options header icon |
| `pages/settings/settings-page.component.html` | 56 | `fa fa-server` | `ph ph-computer-tower` | Remote Server header icon |
| `pages/settings/settings-page.component.html` | 106 | `fa fa-search` | `ph ph-magnifying-glass` | File Discovery header icon |
| `pages/settings/settings-page.component.html` | 141 | `fa fa-tachometer` | `ph ph-gauge` | LFTP Connection Limits header icon |
| `pages/settings/settings-page.component.html` | 175 | `fa fa-list` | `ph ph-list` | AutoQueue header icon |
| `pages/settings/settings-page.component.html` | 389 | `fa fa-trash` | `ph ph-trash` | Post-Import Pruning header icon |
| `pages/settings/settings-page.component.html` | 421 | `fa fa-shield` | `ph ph-shield` | API & Security header icon |
| `pages/settings/settings-page.component.html` | 443 | `fa fa-refresh` | `ph ph-arrows-clockwise` | Regenerate Token button |
| `pages/settings/settings-page.component.html` | 457 | `fa fa-check-circle floating-save-icon--success` | `ph ph-check-circle floating-save-icon--success` | Save confirmed indicator |
| `pages/settings/settings-page.component.html` | 471 | `fa fa-floppy-o` | `ph ph-floppy-disk` | Save Settings button |
| `pages/settings/option.component.html` | 13 | `fa {{icon}}` | `ph {{icon}}` | Dynamic icon binding in option text input — prefix only changes |
| `pages/settings/option.component.html` | 68 | `fa` prefix class | `ph` prefix class | Conditional binding host class — see 2c |

### 2b. Dynamic Icon Data Strings (options-list.ts + app.component.ts)

These TypeScript files contain string literals that are interpolated into `<i class="fa {{icon}}">`. Both the template static prefix and the data strings must migrate together.

**`pages/settings/options-list.ts`** — `icon` property on each `IOptionsContext`:

| Line | Current string | Replacement string | Used in template |
|------|----------------|-------------------|-----------------|
| 19 | `"fa-server"` | `"ph-computer-tower"` | `settings-page.component.html:4` |
| 75 | `"fa-search"` | `"ph-magnifying-glass"` | `settings-page.component.html:4` |
| 101 | `"fa-tachometer"` | `"ph-gauge"` | `settings-page.component.html:4` |
| 150 | `"fa-sliders"` | `"ph-sliders-horizontal"` | `settings-page.component.html:4` |
| 170 | `"fa-list"` | `"ph-list"` | `settings-page.component.html:4` |
| 196 | `"fa-trash"` | `"ph-trash"` | `settings-page.component.html:4` |
| 222 | `"fa-file-archive-o"` | `"ph-file-archive"` | `settings-page.component.html:4` |

Note: `OPTIONS_CONTEXT_SERVER` (icon: `"fa-server"`) is defined but its template usage is the explicit `<ng-template>` outlet `*ngTemplateOutlet="optionsList;context:OPTIONS_CONTEXT_SERVER"` is NOT called in the current `settings-page.component.html` (the Remote Server card uses inline markup, not the template). However, the data string still contains `"fa-server"` and must be changed to avoid any residual `fa-` string in source.

**`pages/main/app.component.ts`** — `NAV_ICONS` map + fallback (lines 92–100):

The `navIcon()` method returns a string like `"fa-cog"` that gets applied via `[ngClass]` to an `<i class="fa">` element. Both the template's static `fa` class and the data strings must change.

| Current key:value | Replacement key:value |
|-------------------|-----------------------|
| `dashboard: "fa-th-large"` | `dashboard: "ph-squares-four"` |
| `settings: "fa-cog"` | `settings: "ph-gear"` |
| `logs: "fa-terminal"` | `logs: "ph-terminal"` |
| `about: "fa-info-circle"` | `about: "ph-info"` |
| `?? "fa-circle"` (fallback) | `?? "ph-circle"` |

The template at `app.component.html:21` reads `<i class="fa" [ngClass]="navIcon(routeInfo.path)">`. After migration this becomes `<i class="ph" [ngClass]="navIcon(routeInfo.path)">` — just the static prefix class changes; the dynamic part is covered by the data string migration above.

**`pages/settings/settings-page.component.html`** — inline `[icon]` attribute bindings (these are string literals passed to `app-option`'s `[icon]` input, rendered in `option.component.html`):

| Line | Current `[icon]="..."` | Replacement |
|------|------------------------|-------------|
| 91 | `[icon]="'fa-folder-open-o'"` | `[icon]="'ph-folder-open'"` |
| 95 | `[icon]="'fa-hdd-o'"` | `[icon]="'ph-hard-drive'"` |
| 99 | `[icon]="'fa-file-code-o'"` | `[icon]="'ph-file-code'"` |

### 2c. Conditional `[class.fa-*]` Bindings

| File | Line | Current binding | Replacement |
|------|------|-----------------|-------------|
| `pages/logs/logs-page.component.html` | 35 | `[class.fa-check-circle]="autoScroll"` | `[class.ph-check-circle]="autoScroll"` |
| `pages/logs/logs-page.component.html` | 35 | `[class.fa-circle-o]="!autoScroll"` | `[class.ph-circle]="!autoScroll"` |
| `pages/logs/logs-page.component.html` | 35 | Static prefix `fa` host class | `ph` |
| `pages/settings/settings-page.component.html` | 308 | `[class.fa-check]="sonarrWebhookCopied"` | `[class.ph-check]="sonarrWebhookCopied"` |
| `pages/settings/settings-page.component.html` | 308 | `[class.fa-copy]="!sonarrWebhookCopied"` | `[class.ph-copy]="!sonarrWebhookCopied"` |
| `pages/settings/settings-page.component.html` | 308 | Static prefix `fa` | `ph` |
| `pages/settings/settings-page.component.html` | 377 | `[class.fa-check]="radarrWebhookCopied"` | `[class.ph-check]="radarrWebhookCopied"` |
| `pages/settings/settings-page.component.html` | 377 | `[class.fa-copy]="!radarrWebhookCopied"` | `[class.ph-copy]="!radarrWebhookCopied"` |
| `pages/settings/settings-page.component.html` | 377 | Static prefix `fa` | `ph` |
| `pages/settings/settings-page.component.html` | 434 | `[class.fa-eye]="!tokenRevealed"` | `[class.ph-eye]="!tokenRevealed"` |
| `pages/settings/settings-page.component.html` | 434 | `[class.fa-eye-slash]="tokenRevealed"` | `[class.ph-eye-slash]="tokenRevealed"` |
| `pages/settings/settings-page.component.html` | 434 | Static prefix `fa` | `ph` |
| `pages/settings/settings-page.component.html` | 438 | `[class.fa-check]="tokenCopied"` | `[class.ph-check]="tokenCopied"` |
| `pages/settings/settings-page.component.html` | 438 | `[class.fa-copy]="!tokenCopied"` | `[class.ph-copy]="!tokenCopied"` |
| `pages/settings/settings-page.component.html` | 438 | Static prefix `fa` | `ph` |
| `pages/settings/option.component.html` | 68 | `[class.fa-eye]="!passwordVisible"` | `[class.ph-eye]="!passwordVisible"` |
| `pages/settings/option.component.html` | 68 | `[class.fa-eye-slash]="passwordVisible"` | `[class.ph-eye-slash]="passwordVisible"` |
| `pages/settings/option.component.html` | 68 | Static prefix `fa` | `ph` |

### 2d. SCSS Selectors Keyed on `.fa-*`

| File | Selector to Change | Replacement | Context |
|------|--------------------|-------------|---------|
| `pages/files/dashboard-log-pane.component.scss` | `.fa-terminal` (line 38) | `.ph-terminal` | Colors the terminal icon in the log pane title amber |
| `pages/logs/logs-page.component.scss` | `&--active .fa-check-circle` (line 149) | `&--active .ph-check-circle` | Colors the autoscroll active state green |
| `pages/logs/logs-page.component.scss` | `.fa-circle-o` (line 155) | `.ph-circle` | Colors the autoscroll inactive state secondary text color |
| `pages/settings/settings-page.component.scss` | `i.fa, i.ph` (line 47) | `i.ph` (remove `i.fa,`) | Consolidate — both fonts have the same sizing rule; FA no longer needed here |
| `pages/settings/settings-page.component.scss` | `i.fa, i.ph` (line 271, Sonarr card) | `i.ph` | Same consolidation in Sonarr brand color block |
| `pages/settings/settings-page.component.scss` | `i.fa, i.ph` (line 306, Radarr card) | `i.ph` | Same consolidation in Radarr brand color block |
| `pages/settings/settings-page.component.scss` | `i.fa { color: $danger; }` (line 334, autodelete card) | `i.ph { color: $danger; }` | Autodelete danger color |
| `pages/settings/settings-page.component.scss` | `.webhook-copy-btn .fa-check` (line 132) | `.webhook-copy-btn .ph-check` | Copy confirmation color (check-green) |
| `pages/settings/settings-page.component.scss` | `.token-action-btn .fa-check` (line 560) | `.token-action-btn .ph-check` | Token copy confirmation color (check-green) |
| `pages/settings/settings-page.component.scss` | `.floating-save-icon--success` (line 612) — no fa selector but applied to `<i class="fa fa-check-circle">` | Icon class changes; CSS rule targets `.floating-save-icon--success` directly, no change needed | Confirm the CSS selector does not reference `.fa-check-circle` directly |

### 2e. Unit Spec Files (4 specs — per D-03)

All 4 specs use inline template overrides (`overrideTemplate`), so both the inline template string AND any DOM selector assertions must update.

**`tests/unittests/pages/files/dashboard-log-pane.component.spec.ts`**

Inline template `LOG_PANE_TEMPLATE` (lines 11–47) contains:
- Line 16: `<i class="fa fa-terminal">` → `<i class="ph ph-terminal">`
- Line 19: `<i class="fa fa-copy">` → `<i class="ph ph-copy">`
- Line 22: `<i class="fa fa-expand">` → `<i class="ph ph-arrows-out">`
- Line 29: `<i class="fa fa-circle-o-notch fa-spin">` → `<i class="ph ph-circle-notch ph-spin">`

No DOM `querySelector` in this spec asserts on FA class names directly (the spinner visibility test queries `.log-pane__spinner`, not the icon class).

**`tests/unittests/pages/files/stats-strip.component.spec.ts`**

Inline template `STATS_STRIP_TEMPLATE` (lines 8–114) contains all fa classes (cloud, database, arrow-down, tasks) — update to ph equivalents.

DOM assertions that query FA class names:
- Line 182: `el.querySelector(".stat-icon.fa-cloud")` → `.stat-icon.ph-cloud`
- Line 190: `el.querySelector(".stat-icon.fa-database")` → `.stat-icon.ph-database`
- Line 198: `el.querySelector(".stat-icon.fa-arrow-down")` → `.stat-icon.ph-arrow-down`
- Line 206: `el.querySelector(".stat-icon.fa-tasks")` → `.stat-icon.ph-list-checks`
- Line 242: `el.querySelector(".stat-icon.fa-arrow-down")` → `.stat-icon.ph-arrow-down` (in peak-speed test)

**`tests/unittests/pages/files/transfer-table.component.spec.ts`**

Inline template `TEST_TEMPLATE` (lines 21–82) contains:
- Line 25: `<i class="fa fa-search search-icon">` → `<i class="ph ph-magnifying-glass search-icon">`

DOM assertions:
- Line 202: `fixture.nativeElement.querySelector(".fa-search")` → `.ph-magnifying-glass`

**`tests/unittests/pages/main/notification-bell.component.spec.ts`**

Inline template override (lines 31–64) contains:
- Line 35: `<i class="fa fa-bell">` → `<i class="ph ph-bell">`
- Line 55: `<i class="fa fa-times">` → `<i class="ph ph-x">`

No FA class-name assertions in this spec (tests assert on `.bell-wrapper`, `.bell-btn`, `.bell-badge-dot`, `.bell-dropdown`, `.bell-empty`, `.bell-notif-text`, `.bell-notif-dismiss`).

### 2f. angular.json — Remove Font Awesome Stylesheet Entries

Two lines (one in build styles, one in test/serve styles):

```
Line 38:  "node_modules/font-awesome/css/font-awesome.css"   ← REMOVE
Line 107: "node_modules/font-awesome/css/font-awesome.css"   ← REMOVE
```

Phosphor's three stylesheets on lines 39–41 (build) and 108–110 (test/serve) stay unchanged.

### 2g. package.json — Drop font-awesome Dependency

```
src/angular/package.json: remove "font-awesome": "^4.7.0" from dependencies
```

Then run `npm install` in `src/angular/` to regenerate `package-lock.json`.

---

## 3. Verification Mechanics

### 3a. Residual FA Detection — grep commands

After migration and before the FA dep drop, verify source files are clean:

```bash
# Zero fa- class strings in production-relevant Angular source
grep -r "fa fa-\|\"fa-\|'fa-\|class=\"fa\b\|class='fa\b" \
  src/angular/src/app \
  --include="*.html" --include="*.ts" --include="*.scss" \
  --exclude-dir=node_modules

# Zero font-awesome references in angular.json
grep "font-awesome" src/angular/angular.json

# Zero font-awesome in package.json
grep "font-awesome" src/angular/package.json
```

After the FA dep drop and `npm install`, verify the built `dist/` is clean:

```bash
# Build first
cd src/angular && ng build --configuration production

# Check dist for residual fa- class strings
grep -r "fa-\|font-awesome" dist/ --include="*.js" --include="*.css" | grep -v "sonarr\|radarr\|safari\|alfa\|bufferSize\|default\|surface\|sonar"

# Confirm no Font Awesome font files in dist
find dist/ -name "FontAwesome*" -o -name "fontawesome*" -o -name "fa-*" 2>/dev/null | grep -v node_modules
```

The `grep` exclusion in the dist scan above filters common false-positive substrings containing "fa-" (like `sonarr`, `safari`) — review any remaining matches manually.

### 3b. Bundle-Size Delta (Phase 104 D-02 pattern)

```bash
# BEFORE: capture while FA still in package.json (before dep removal step)
cd src/angular
ng build --configuration production 2>&1 | grep -E "Initial|Lazy|kb|kB|MB"

# AFTER: capture after npm install (FA removed)
ng build --configuration production 2>&1 | grep -E "Initial|Lazy|kb|kB|MB"
```

Expected delta: Font Awesome ships `font-awesome.css` (~37 kB) plus 4 font files (woff, woff2, ttf, svg, eot — typically ~200–400 kB total). The bundle should shrink by at least the CSS + font transfer.

### 3c. Karma Floor Reminder

Run after all source edits (before the dep drop commit):

```bash
cd src/angular
npx karma start --single-run 2>&1 | tail -40
```

Floors that must hold or rise: `stmts 83% / branches 68% / fns 79% / lines 83%`.

Key concern: the 4 updated spec files must still pass. Run targeted specs first:

```bash
# Run targeted specs only (fast feedback)
npx karma start --single-run --include "**/stats-strip.component.spec.ts,**/dashboard-log-pane.component.spec.ts,**/transfer-table.component.spec.ts,**/notification-bell.component.spec.ts"
```

---

## 4. Pitfalls and Risks

### Pitfall 1: `ph-spin` missing from Phosphor CSS

**What goes wrong:** The spinner `<i class="fa fa-circle-o-notch fa-spin">` loses its rotation animation when FA's CSS is removed, because `fa-spin` lives entirely in `font-awesome.css`. Phosphor provides no equivalent animation utility class.

**How to avoid:** Add a `@keyframes ph-spin` + `.ph-spin` rule BEFORE removing FA from `angular.json`. Validate the spinner animates on the dev server before the dep drop commit.

**Warning signs:** Static spinner icon in the dashboard log pane during smoke test.

### Pitfall 2: Dynamic Binding Layer — Mismatched Prefix

**What goes wrong:** Updating only the `options-list.ts` icon strings (`"fa-server"` → `"ph-server"`) without also updating the template prefix class from `fa` to `ph` (or vice versa) results in a rendered element with `class="fa ph-server"` or `class="ph fa-server"` — neither is a valid icon.

**How to avoid:** Always update the static prefix class in the template AND the data string together. The two templates with dynamic bindings are:
- `settings-page.component.html:4` — `<i class="fa {{icon}}">` → `<i class="ph {{icon}}">`
- `option.component.html:13` — `<i class="fa {{icon}}">` → `<i class="ph {{icon}}">`

And the `app.component.html:21` nav loop — `<i class="fa" [ngClass]="navIcon(...)">` → `<i class="ph" [ngClass]="navIcon(...)">`.

**Warning signs:** Icons rendering as text/ligature garbage or blank boxes in settings section headers or the nav bar.

### Pitfall 3: `ph-server` Does Not Exist

**What goes wrong:** Mapping `fa-server` → `ph-server` (intuitive name) would produce a broken icon because `ph-server` is not in Phosphor 2.1.2. The correct class is `ph-computer-tower`.

**How to avoid:** The mapping table above uses `ph-computer-tower` (verified to exist). Do not use `ph-server`.

**Warning signs:** Blank "Remote Server" section header icon in settings.

### Pitfall 4: `ph-ban` Does Not Exist

**What goes wrong:** Mapping `fa-ban` → `ph-ban` (intuitive name) would fail. The correct Phosphor class is `ph-prohibit`.

**How to avoid:** The mapping table uses `ph-prohibit` (verified to exist). The `fa-ban action-overlay` usage in `bulk-actions-bar.component.html` must use `ph-prohibit action-overlay`.

### Pitfall 5: SCSS Selector Consolidation — `i.fa, i.ph`

**What goes wrong:** `settings-page.component.scss` already pairs `i.fa, i.ph` in several rules (the migration is mid-flight). After removing FA, leaving `i.fa, i.ph` is harmless but adds dead code. More critically, the autodelete card has `i.fa { color: $danger; }` which would stop applying if not migrated to `i.ph`.

**How to avoid:** Replace `i.fa, i.ph` → `i.ph` and `i.fa { ... }` → `i.ph { ... }` in all SCSS files during the migration commit.

### Pitfall 6: `fa-circle` Fallback in app.component.ts

**What goes wrong:** `return AppComponent.NAV_ICONS[path] ?? "fa-circle"` — if the fallback is not updated, an unknown route will render `<i class="ph fa-circle">` which is not a valid icon.

**How to avoid:** Update the fallback to `"ph-circle"`. Since the template prefix also changes from `fa` to `ph`, the rendered class will be `ph ph-circle` for any unknown route.

### Pitfall 7: Spec Inline Templates Are Full Copies

**What goes wrong:** All 4 spec files that reference FA use `overrideTemplate` with inline copies of the template. These copies are NOT auto-updated when the real template changes — they must be updated manually. Forgetting to update the spec inline copy will cause Karma to test the old FA version of the template, silently passing even though the real component now renders Phosphor.

**How to avoid:** Update the inline template strings in the 4 spec files in the same commit as the real template changes. Cross-check each spec's inline template against the real component template after the migration.

### Pitfall 8: `fa-` False Positives in grep

**What goes wrong:** The production dist bundle may contain strings like `"sonarr-fa..."`, `"safari..."`, `"default..."` that match a naive `fa-` grep, causing false alarm or missed real hits.

**How to avoid:** Use the specific grep pattern `"fa fa-\|node_modules/font-awesome"` for the source check, and review dist grep hits manually for context.

---

## 5. Open Questions / Ambiguous Icons (User Sign-Off Required per D-01)

Before any replacement code lands, the following 8 mapping proposals require explicit user confirmation. They are tracked here; the planner must insert a `checkpoint:human-verify` task before any code change that touches these icons.

| # | FA4 icon | Usage location | Proposed Phosphor | Rationale | Action needed |
|---|----------|---------------|-------------------|-----------|---------------|
| Q1 | `fa-tachometer` | Settings "LFTP Connection Limits" header + `options-list.ts:101` | `ph-gauge` | Speedometer/rate-of-flow concept; closest available | Confirm `ph-gauge` or substitute |
| Q2 | `fa-floppy-o` | Settings "Save Settings" button (`settings-page.component.html:471`) | `ph-floppy-disk` | Save icon, Phosphor drops "-o" suffix | Confirm `ph-floppy-disk` |
| Q3 | `fa-hdd-o` | Settings "Local Directory" option input icon (`settings-page.component.html:95`) | `ph-hard-drive` | Local storage/disk; Phosphor drops "-o" suffix | Confirm `ph-hard-drive` |
| Q4 | `fa-file-archive-o` | Bulk actions bar "Extract" button + Archive Operations header + `options-list.ts:222` | `ph-file-archive` | Archive file icon; `ph-file-zip` also exists — which is preferred? | Confirm `ph-file-archive` vs `ph-file-zip` |
| Q5 | `fa-circle-o-notch` + `fa-spin` | Dashboard log pane spinner (`dashboard-log-pane.component.html:18`) | `ph-circle-notch` + custom `.ph-spin` CSS animation rule | Loading arc icon + spin animation that must be added to the project | Confirm `ph-circle-notch` + approve adding spin CSS rule to `dashboard-log-pane.component.scss` |
| Q6 | `fa-th-large` | Nav bar "dashboard" icon (`app.component.ts:93`) | `ph-squares-four` | 2×2 grid squares; `ph-grid-four` and `ph-grid-nine` also exist | Confirm `ph-squares-four` vs `ph-grid-four` |
| Q7 | `fa-sliders` | Settings "General Options" header + `options-list.ts:150` | `ph-sliders-horizontal` | Horizontal sliders/equalizer; `ph-sliders` (vertical) is the alternate | Confirm `ph-sliders-horizontal` vs `ph-sliders` |
| Q8 | `fa-file-code-o` | Settings "Server Script Path" option input icon (`settings-page.component.html:99`) | `ph-file-code` | Script/code file; Phosphor drops "-o" suffix | Confirm `ph-file-code` |

**Recommended user action:** Review the 8 proposals above and reply with confirms or alternates before the planner generates code-change tasks.

---

## Standard Stack

This phase introduces no new dependencies. The working stack is already fully in place.

| Component | Version | Notes |
|-----------|---------|-------|
| `@phosphor-icons/web` | 2.1.2 (resolved) | Already installed; regular/bold/fill already wired in `angular.json` |
| `font-awesome` | 4.7.0 | Being removed; present until D-06 closing commit |
| Angular | (existing project version) | No Angular version change |

**No packages to install.** This is a removal-only phase on the dependency side.

---

## Package Legitimacy Audit

No new packages are installed in this phase. The phase removes `font-awesome` and produces no new additions. Package legitimacy gate: N/A.

---

## Architecture Patterns

### Dynamic Icon Binding — Before and After

**Before (FA):**
```html
<!-- settings-page.component.html, option.component.html -->
<i class="fa {{icon}}"></i>
<!-- icon data string: "fa-server", "fa-search", etc. -->
```

```typescript
// options-list.ts
icon: "fa-server"   // rendered as class="fa fa-server"
```

**After (Phosphor):**
```html
<i class="ph {{icon}}"></i>
<!-- icon data string: "ph-computer-tower", "ph-magnifying-glass", etc. -->
```

```typescript
// options-list.ts
icon: "ph-computer-tower"   // rendered as class="ph ph-computer-tower"
```

The idiom is identical — only the prefix class (`fa` → `ph`) and the data string (`fa-*` → `ph-*`) change. The `IOptionsContext.icon` type remains `string` with no interface change.

### Spinner Animation — Pattern to Add

Since Phosphor provides no rotation utility, one small CSS addition is required. The recommended location is `dashboard-log-pane.component.scss` (scoped, avoids polluting global styles):

```scss
// dashboard-log-pane.component.scss — add at end of file
// Phosphor does not ship a spin animation class; provide one locally.
@keyframes ph-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.ph-spin {
  animation: ph-spin 1s linear infinite;
  display: inline-block;  // required for transform to apply on inline elements
}
```

Alternatively, if a second spinner is ever added elsewhere, move the rule to `styles.scss` global section. For this phase, scoped is sufficient — only one spinner exists.

---

## Validation Architecture

Nyquist validation is enabled (config.json has no `workflow.nyquist_validation: false`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Karma + Jasmine (existing) |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `cd src/angular && npx karma start --single-run` |
| Full suite command | `cd src/angular && npx karma start --single-run` (same — all unit tests) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Spec Files |
|--------|----------|-----------|-------------------|-----------|
| DEPS-01b | `fa-*` classes replaced in rendered DOM | unit | `npx karma start --single-run` | stats-strip.spec, dashboard-log-pane.spec, transfer-table.spec, notification-bell.spec |
| DEPS-01b | Icon selectors in specs match new Phosphor classes | unit | `npx karma start --single-run` | All 4 spec files |
| DEPS-01b | No regression in existing component logic | unit | `npx karma start --single-run` | All 611 tests must pass |
| DEPS-01b | No missing icons in production build | smoke | dev-server manual inspection | N/A (manual) |
| DEPS-01b | FA absent from dist | grep/manual | `grep -r "font-awesome" dist/` | N/A |

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. The 4 spec files exist and will be updated (not created) as part of this phase.

---

## Environment Availability

This phase is code/config-only changes to the Angular source. External tool dependencies:

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | `npm install` for lock regen | Yes (project active) | existing | — |
| Angular CLI (`ng`) | `ng build --configuration production` | Yes (existing) | existing | — |
| Karma | Unit test suite | Yes (existing) | existing | — |

No missing dependencies.

---

## Security Domain

This phase makes no changes that affect authentication, authorization, input validation, or cryptography. FA icon classes are static strings in HTML templates — no user input is interpolated. The icon library change introduces no new attack surface. ASVS categories V2, V3, V4, V6 do not apply. V5 (Input Validation) does not apply because icon classes are compile-time constants, not runtime user input.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ph-computer-tower` is the correct Phosphor equivalent for `fa-server` (rack/server concept) | Mapping Table | Icon could render but convey wrong meaning; user may prefer `ph-hard-drives` or `ph-desktop-tower` |
| A2 | `ph-warning-circle` is the correct equivalent for `fa-exclamation-circle` (circled alert) | Mapping Table | Same visual intent — risk is minimal; both are "alert in a circle" |
| A3 | `ph-warning` (triangle) is the correct equivalent for `fa-exclamation-triangle` | Mapping Table | Exact semantic match; risk is negligible |
| A4 | Adding `.ph-spin` CSS to `dashboard-log-pane.component.scss` is acceptable scope | Section 4 / Spinner | If user wants global spin utility, prefer `styles.scss` instead |

All other claims are VERIFIED by direct reads of the installed `node_modules/@phosphor-icons/web/src/regular/style.css` and the actual source files.

---

## Sources

### Primary (HIGH confidence)
- `/Users/julianamacbook/seedsyncarr/src/angular/node_modules/@phosphor-icons/web/src/regular/style.css` — all 39 icon class names verified line by line
- `/Users/julianamacbook/seedsyncarr/src/angular/node_modules/@phosphor-icons/web/src/fill/style.css` — ph-fill ph-circle and ph-fill ph-check-circle verified
- All source `.html`, `.ts`, `.scss` files in `src/angular/src/app/` — read directly
- All 4 unit spec files — read directly
- `src/angular/angular.json` — FA stylesheet line numbers verified
- `src/angular/src/app/pages/settings/options-list.ts` — data strings verified
- `src/angular/src/app/pages/main/app.component.ts` — NAV_ICONS map verified

### Metadata

**Confidence breakdown:**
- Mapping table: HIGH — every class name verified against installed package CSS
- Migration surface: HIGH — every file read directly with line numbers
- Pitfalls: HIGH — grounded in observed code patterns
- Spinner animation: HIGH — confirmed absence of ph-spin in Phosphor CSS, confirmed FA provides fa-spin

**Research date:** 2026-06-01
**Valid until:** No expiry for installed-package research (packages are pinned); valid as long as `@phosphor-icons/web` version does not change.
