# Phase 62: Nav Bar Foundation - Research

**Researched:** 2026-04-14
**Domain:** Angular 21 component styling — backdrop-blur nav, active-link indicator, connection badge, notification bell dropdown
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Background uses ~80% opacity on forest-base with backdrop-blur (12px). CSS: `background: rgba(21, 26, 20, 0.80); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);`
- **D-02:** Bottom border changes from current `$gray-300` to forest-border (`#3e4a38`) to match the Deep Moss palette
- **D-03:** Brand text uses amber highlight on the "arr" suffix: "SeedSync" in primary text color + "arr" in amber accent (`--app-logo-color` / `#c49a4a`). No logo icon — stays text-only.
- **D-04:** Active nav link gets a 2px amber underline bar at the bottom, full width of the link text. Implemented via `::after` pseudo-element with `background: var(--app-logo-color)`.
- **D-05:** The indicator uses a fade in/out transition (opacity 0.15s ease) when switching between pages. Old link's bar fades out, new link's bar fades in.
- **D-06:** Right-aligned pill badge in the nav showing a colored dot + text. Connected state: green pulsing dot + "Connected" text in a semantic-success bordered pill. Disconnected state: red dot (no pulse) + "Disconnected" in a semantic-error bordered pill.
- **D-07:** Data source is the existing `ConnectedService.connected` Observable.
- **D-08:** Responsive: below ~640px, collapse the pill to dot-only (hide text, keep the status dot visible).
- **D-09:** Bell uses Font Awesome 4.7 `fa-bell` icon (icon font, not SVG). Amber badge dot appears when notifications are present. Hover changes bell color to amber.
- **D-10:** Clicking the bell opens a dropdown panel below it showing the notification list from `NotificationService`. Individual notifications can be dismissed from the panel.
- **D-11:** The existing inline Bootstrap alert bar (`HeaderComponent` / `#header`) is removed entirely. The bell dropdown replaces it as the single notification surface. All notification levels (DANGER, WARNING, INFO, SUCCESS) go through the bell.

### Claude's Discretion

- Exact pulse animation keyframes and timing
- Dropdown panel dismiss-all behavior (if warranted)
- Nav height adjustments if needed (currently 48px)
- Mobile hamburger behavior for nav links (preserve existing responsive approach)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NAV-01 | Nav bar uses backdrop blur with semi-transparent background | D-01: exact CSS values locked; backdrop-filter browser support confirmed; `-webkit-` prefix needed for Safari |
| NAV-02 | Active page link has amber underline indicator | D-04/D-05: `::after` pseudo-element pattern; `routerLinkActive="active"` already wired in template |
| NAV-03 | Connection status badge in nav with pulse animation | D-06/D-07/D-08: `ConnectedService.connected` Observable confirmed; CSS `@keyframes` pulse pattern from existing `styles.scss` provides a template |
| NAV-04 | Notification bell icon with badge dot in nav | D-09/D-10/D-11: FA 4.7 `fa-bell` confirmed in project; `NotificationService.notifications` Observable confirmed; `HeaderComponent` inline alert bar identified for removal |
</phase_requirements>

---

## Summary

Phase 62 upgrades the existing `#top-nav` in `app.component.html/scss` and fully refactors `HeaderComponent` (the inline alert bar) into a bell-icon dropdown panel. All four requirements are purely CSS/template/component changes — no new Angular services, no new npm packages, no backend changes.

The existing codebase already provides every data dependency needed. `ConnectedService.connected` is a `BehaviorSubject<boolean>` already provided in `appConfig` and exposed via `StreamServiceRegistry.connectedService`. `NotificationService.notifications` is an `Observable<Immutable.List<Notification>>` already injected into `HeaderComponent`. Font Awesome 4.7 is available globally. The Deep Moss CSS custom properties (`--app-logo-color`, `--app-header-bg`, `--app-muted-text`, etc.) are already defined in `styles.scss`.

The main complexity points are: (1) wiring `ConnectedService` into `AppComponent` (it is currently only in `HeaderComponent` via `StreamServiceRegistry`), (2) building a CSS-driven dropdown panel for the bell that layers correctly above page content (z-index management), and (3) ensuring the `HeaderComponent` refactor preserves all the server-status subscription logic while replacing its output surface from Bootstrap alerts to the bell-dropdown list.

**Primary recommendation:** Modify `app.component` in-place for nav visual upgrades (backdrop-blur, amber brand split, active indicator, connection badge, bell button). Refactor `HeaderComponent` template/SCSS to replace the `#header` alert bar with the bell dropdown panel; the TypeScript notification-subscription logic stays intact.

---

## Standard Stack

### Core (all already in project — no new installs)
| Library / Feature | Version | Purpose | Status |
|-------------------|---------|---------|--------|
| Angular standalone components | 21 | Component model used throughout | [VERIFIED: app.config.ts, all component files] |
| `routerLinkActive` directive | Angular 21 | Active route class binding (already wired) | [VERIFIED: app.component.html line 11] |
| `AsyncPipe` | Angular 21 | Subscribe to Observables in templates | [VERIFIED: header.component.ts imports] |
| Font Awesome 4.7 | 4.7 | `fa-bell` icon class | [VERIFIED: CONTEXT.md D-09; project uses FA 4.7 globally] |
| CSS `backdrop-filter` | CSS3 | Blur effect behind nav | [VERIFIED: supported in all modern browsers; `-webkit-` prefix for Safari] |
| CSS `@keyframes` | CSS3 | Pulse animation for connected dot | [VERIFIED: existing pulse pattern in styles.scss lines 119-122] |
| `ConnectedService` | — | `connected: Observable<boolean>` for status badge | [VERIFIED: connected.service.ts] |
| `NotificationService` | — | `notifications: Observable<Immutable.List<Notification>>` | [VERIFIED: notification.service.ts] |
| `Notification` model | — | Level enum (DANGER/WARNING/INFO/SUCCESS), text, dismissible | [VERIFIED: notification.ts] |

### No New Dependencies Required
This phase is CSS + Angular template work only. No `npm install` step needed.

---

## Architecture Patterns

### Recommended Project Structure (files touched)
```
src/angular/src/app/pages/main/
├── app.component.html    # Add: brand "arr" split, connection badge, bell button
├── app.component.scss    # Add: backdrop-blur, border update, indicator, badge, bell styles
├── app.component.ts      # Add: ConnectedService injection, notifications$ stream
├── header.component.html # Replace: alert bar → bell dropdown panel
├── header.component.scss # Replace: alert styles → dropdown panel styles
└── header.component.ts   # Keep: all subscription logic; minor: no template changes needed
```

### Pattern 1: `AppComponent` handles nav — `HeaderComponent` handles bell dropdown panel

`AppComponent` owns the nav bar visually. Currently `HeaderComponent` (rendered as `<app-header>` inside `#top-header`) owns the alert bar. The refactor promotes notification rendering into the bell dropdown inside the nav, while `HeaderComponent`'s TypeScript subscription logic (server status, remote scan, remote error) stays unchanged.

Two approaches for the bell:

**Option A (Recommended): Bell stays in `app.component.html`, dropdown rendered by `HeaderComponent` repositioned.**
- Bell button goes in the nav (in `app.component.html` / `app.component.ts`)
- The `#top-header` div (where `<app-header>` lives) is removed or kept as an invisible host
- `HeaderComponent` exposes a `dropdownOpen` flag toggled by the bell's click
- Pros: Clean separation; `HeaderComponent` already has NotificationService injected
- Cons: Requires click coordination between `AppComponent` (bell button) and `HeaderComponent` (dropdown visibility)

**Option B (Simpler): Merge bell + dropdown fully into `AppComponent`.**
- Move `NotificationService` injection into `AppComponent`
- `HeaderComponent` keeps TypeScript subscription logic (server status notifications) but its template becomes empty or a no-op
- Bell button and dropdown panel both live in `app.component.html`
- Pros: Single component owns all nav elements; no cross-component event wiring
- Cons: `AppComponent` grows; `HeaderComponent` becomes a headless logic-only component

**Recommendation: Option B.** Simpler template ownership. `HeaderComponent` template becomes empty (or a comment); its `ngOnInit` subscription logic that feeds `NotificationService` is preserved untouched. `AppComponent` gains `NotificationService` injection and handles the bell open/close state.

### Pattern 2: `::after` pseudo-element for amber active indicator
[VERIFIED: design.html line 133; CONTEXT.md D-04]

```scss
// Source: CONTEXT.md D-04 + design.html reference
.nav-link {
    position: relative;

    &::after {
        content: '';
        position: absolute;
        bottom: -1px;       // sits on the nav border
        left: 0;
        width: 100%;
        height: 2px;
        background: var(--app-logo-color);  // #c49a4a amber
        opacity: 0;
        transition: opacity 0.15s ease;
    }

    &.active::after {
        opacity: 1;
    }
}
```

Note: `routerLinkActive="active"` is already applied in `app.component.html` line 11. No TypeScript change needed for active detection.

### Pattern 3: Connection status pill
[VERIFIED: CONTEXT.md D-06/D-07/D-08; connected.service.ts]

In `AppComponent`:
- Inject `StreamServiceRegistry` (already available in appConfig DI)
- Expose `connected$ = this._streamServiceRegistry.connectedService.connected`
- Use `async` pipe in template: `*ngIf="connected$ | async as connected"`

```scss
// Pulse animation for connected dot
@keyframes status-pulse {
    0%, 100% {
        box-shadow: 0 0 0 0 rgba(35, 134, 54, 0.5);
    }
    50% {
        box-shadow: 0 0 0 4px rgba(35, 134, 54, 0);
    }
}
.status-dot.connected {
    animation: status-pulse 2s infinite;
}
```

Responsive collapse at 640px: hide `.status-text` via `@media (max-width: 640px)`.

### Pattern 4: Notification bell dropdown
[VERIFIED: CONTEXT.md D-09/D-10/D-11; notification.service.ts; notification.ts]

In `AppComponent`:
- Inject `NotificationService`
- Expose `notifications$ = this._notificationService.notifications`
- Track `bellOpen = false` boolean
- `dismiss(notif)` calls `this._notificationService.hide(notif)`

The dropdown must close on outside click. Standard Angular pattern: `@HostListener('document:click', ['$event'])` in `AppComponent` or a click-outside directive.

```scss
.bell-dropdown {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    width: 320px;
    background: var(--app-header-bg);
    border: 1px solid var(--app-separator-color);
    border-radius: 6px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    z-index: 500;  // above nav z-index
}
```

Bell button container needs `position: relative` for dropdown anchoring.

### Anti-Patterns to Avoid

- **Don't use Bootstrap `dropdown` JS**: The project avoids Bootstrap JS components for nav interactions. Pure CSS + Angular `[class.open]` binding is sufficient.
- **Don't put `backdrop-filter` on `.nav-inner`**: Apply it to `#top-nav` (the full-width sticky element), not the max-width inner container.
- **Don't use `*ngIf` structural directive for the dropdown (deprecated pattern)**: Use Angular 17+ `@if` control flow syntax, which the project already uses (see `app.component.html` lines 31-59).
- **Don't add `position: sticky` to `#top-header` after removing the alert bar content**: If `HeaderComponent` becomes headless, the sticky `#top-header` div should also be removed or collapsed to avoid a 0-height sticky element consuming z-index space.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Active route detection | Custom router subscription to set CSS class | `routerLinkActive="active"` (already in template) | Angular handles route matching including child routes |
| Connection state | Manual EventSource checks | `ConnectedService.connected` Observable (already exists) | SSE lifecycle already managed by `StreamDispatchService` |
| Notification state | Local component array | `NotificationService.notifications` Observable (already exists) | Priority sorting, deduplication already implemented |
| Outside-click close | Complex event propagation logic | `@HostListener('document:click', ['$event'])` + `stopPropagation` on bell | Standard Angular pattern, 10 lines |

---

## Common Pitfalls

### Pitfall 1: `backdrop-filter` requires `position: sticky` and correct z-index layering
**What goes wrong:** The backdrop blur renders on a `position: static` element — blur appears but content beneath it bleeds through or the blur clips to the wrong ancestor.
**Why it happens:** `backdrop-filter` only composites against content stacked *below* the element in paint order; requires the nav to be in a stacking context.
**How to avoid:** `#top-nav` already has `position: sticky; top: 0; z-index: $zindex-top-header + 1`. Adding `backdrop-filter` here is safe. Do not add `overflow: hidden` to `#top-nav` — that clips the backdrop-filter blur effect.
**Warning signs:** Blur appears as a solid box with no visible transparency to page content.

### Pitfall 2: Missing `-webkit-backdrop-filter` prefix breaks Safari
**What goes wrong:** The nav blur renders correctly in Chrome/Firefox but shows a fully opaque background in Safari.
**Why it happens:** Safari still requires the `-webkit-` prefix for `backdrop-filter`.
**How to avoid:** Always write both properties (D-01 already specifies this):
```css
backdrop-filter: blur(12px);
-webkit-backdrop-filter: blur(12px);
```

### Pitfall 3: `#top-header` becomes a height-stealing ghost element
**What goes wrong:** After removing the alert bar from `HeaderComponent`, the `#top-header` div (sticky, `top: 48px`, has `background-color`) remains a visible blank strip between the nav and page content.
**Why it happens:** The div has its own background and sticky positioning; it renders as an empty strip even with no children.
**How to avoid:** Either (a) remove the `#top-header` wrapper from `app.component.html` entirely if `HeaderComponent` produces no visible output, or (b) conditionally show it only when notifications are present. The `ResizeObserver` in `app.component.ts` that watches `topHeader` ref must also be adjusted.
**Warning signs:** Blank green strip visible between nav and page content.

### Pitfall 4: Dropdown z-index conflicts with sticky header
**What goes wrong:** Bell dropdown is clipped by the nav's own stacking context or appears behind page content.
**Why it happens:** `#top-nav` has `z-index: $zindex-top-header + 1` (= 201). The dropdown must be a child of the nav's stacking context, not a sibling at a lower z-index.
**How to avoid:** Put the bell button and dropdown inside `#top-nav` in the template. The dropdown's own `z-index: 500` is relative within the nav's stacking context and will be composited correctly.

### Pitfall 5: `ConnectedService` injection path in `AppComponent`
**What goes wrong:** Attempting to inject `ConnectedService` directly into `AppComponent` without going through `StreamServiceRegistry` causes a duplicate instance or DI error.
**Why it happens:** `ConnectedService` is registered directly as a provider in `appConfig` AND via `StreamServiceRegistryProvider`. Injecting it directly into `AppComponent` gives the same singleton instance — this is fine. However, the conventional pattern in this codebase is to inject `StreamServiceRegistry` and access `.connectedService` from it (see `header.component.ts` line 39).
**How to avoid:** Inject `StreamServiceRegistry` in `AppComponent` constructor and use `_streamServiceRegistry.connectedService.connected` — consistent with `HeaderComponent` pattern.

### Pitfall 6: `@if` control flow and `async` pipe for notifications
**What goes wrong:** Using `*ngIf` instead of `@if` for the bell dropdown or notification list — this works but is inconsistent with Angular 17+ control flow syntax already used in the file.
**Why it happens:** Mixed syntax compiles but creates maintenance confusion.
**How to avoid:** Use `@if` / `@for` control flow blocks, `async` pipe via local variable pattern:
```html
@if (notifications$ | async; as notifs) {
  @if (notifs.size > 0) { ... }
}
```

---

## Code Examples

### 1. Brand name amber split (app.component.html)
```html
<!-- Source: CONTEXT.md D-03; design.html line 123 -->
<div class="nav-brand">
  <span class="brand-text">SeedSync<span class="brand-arr">arr</span></span>
  <span class="brand-version">v{{version}}</span>
</div>
```

```scss
// app.component.scss
.brand-text {
    font-weight: 700;
    font-size: 1.15rem;
    color: var(--app-selection-text-emphasis);  // primary text

    .brand-arr {
        color: var(--app-logo-color);  // amber #c49a4a
    }
}
```

### 2. Backdrop blur nav (app.component.scss)
```scss
// Source: CONTEXT.md D-01, D-02
#top-nav {
    background: rgba(21, 26, 20, 0.80);  // forest-base at 80%
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid #3e4a38;    // forest-border (was $gray-300)
    position: sticky;
    top: 0;
    z-index: $zindex-top-header + 1;
}
```

### 3. Active link amber underline (app.component.scss)
```scss
// Source: CONTEXT.md D-04, D-05
.nav-link {
    position: relative;

    &::after {
        content: '';
        position: absolute;
        bottom: -1px;
        left: 0;
        width: 100%;
        height: 2px;
        background: var(--app-logo-color);
        opacity: 0;
        transition: opacity 0.15s ease;
    }

    &.active::after {
        opacity: 1;
    }
}
```

### 4. Connection status badge (app.component.html)
```html
<!-- Source: CONTEXT.md D-06, D-08; design.html lines 149-152 -->
@if (connected$ | async; as isConnected) {
  <div class="connection-badge" [class.connected]="isConnected" [class.disconnected]="!isConnected">
    <span class="status-dot"></span>
    <span class="status-text">{{ isConnected ? 'Connected' : 'Disconnected' }}</span>
  </div>
}
```

```scss
// Source: CONTEXT.md D-06; design.html pulse pattern lines 100-105
.connection-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-family: $font-family-monospace;
    font-weight: 500;

    &.connected {
        background: rgba(35, 134, 54, 0.15);
        border: 1px solid rgba(35, 134, 54, 0.3);
        color: $success;
    }

    &.disconnected {
        background: rgba(248, 81, 73, 0.15);
        border: 1px solid rgba(248, 81, 73, 0.3);
        color: $danger;
    }
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    .connected & {
        background: $success;
        animation: status-pulse 2s infinite;
    }

    .disconnected & {
        background: $danger;
    }
}

@keyframes status-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(35, 134, 54, 0.5); }
    50% { box-shadow: 0 0 0 4px rgba(35, 134, 54, 0); }
}

// Responsive: hide text below 640px
@media (max-width: 640px) {
    .connection-badge .status-text { display: none; }
    .connection-badge { padding: 4px 6px; }
}
```

### 5. Bell button with badge (app.component.html)
```html
<!-- Source: CONTEXT.md D-09; design.html lines 154-157 -->
<div class="bell-wrapper" (click)="toggleBell($event)">
  <button class="bell-btn" [class.has-notifications]="(notifications$ | async)?.size > 0" aria-label="Notifications">
    <i class="fa fa-bell"></i>
    @if ((notifications$ | async)?.size > 0) {
      <span class="bell-badge-dot"></span>
    }
  </button>

  @if (bellOpen) {
    <div class="bell-dropdown" (click)="$event.stopPropagation()">
      <!-- notification list -->
    </div>
  }
</div>
```

### 6. `AppComponent` TypeScript additions
```typescript
// Source: CONTEXT.md D-07, D-10; connected.service.ts; notification.service.ts
// Add to constructor params:
private _streamServiceRegistry: StreamServiceRegistry,
private _notificationService: NotificationService,

// Add to class body:
connected$: Observable<boolean>;
notifications$: Observable<Immutable.List<Notification>>;
bellOpen = false;

// In constructor body:
this.connected$ = this._streamServiceRegistry.connectedService.connected;
this.notifications$ = this._notificationService.notifications;

// New methods:
toggleBell(event: Event): void {
    event.stopPropagation();
    this.bellOpen = !this.bellOpen;
}

@HostListener('document:click')
closeBell(): void {
    this.bellOpen = false;
}

dismissNotification(notif: Notification): void {
    this._notificationService.hide(notif);
}
```

### 7. `HeaderComponent` after refactor
The template becomes empty (or a comment marker). TypeScript logic is preserved unchanged — the three `ngOnInit` subscriptions that call `NotificationService.show/hide` must remain. Only the `header.component.html` changes (replace alert bar with empty template).

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is not a rename/refactor/migration phase. It is a UI component upgrade. No stored data, databases, or registered OS state is affected.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Angular CLI (`ng`) | Build/serve | Confirmed present (project active) | — | — |
| Font Awesome 4.7 | `fa-bell` icon | ✓ | 4.7 | — |
| CSS `backdrop-filter` | NAV-01 blur effect | ✓ Browser native | Modern browsers + `-webkit-` for Safari | — |
| `ConnectedService` | NAV-03 badge | ✓ | In appConfig providers | — |
| `NotificationService` | NAV-04 bell | ✓ | In appConfig providers | — |

No missing dependencies. No install step required.

---

## Validation Architecture

`workflow.nyquist_validation` key is absent from `.planning/config.json` — treated as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Karma + Jasmine |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `cd src/angular && ng test --watch=false --browsers=ChromeHeadless` |
| Full suite command | `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NAV-01 | Nav backdrop-filter CSS applied | Visual/manual | Manual browser inspection | ❌ Not applicable to unit test |
| NAV-02 | Active link `::after` has opacity 1 when `.active` class present | CSS-only | Manual visual inspection | ❌ Not applicable to unit test |
| NAV-03 | Connection badge shows correct state from `connected$` | unit | `ng test --include=**/app.component.spec.ts` | ❌ Wave 0 |
| NAV-04 | Bell badge dot visible when notifications.size > 0 | unit | `ng test --include=**/app.component.spec.ts` | ❌ Wave 0 |

**Note:** NAV-01 and NAV-02 are CSS-only visual effects. Automated unit tests cannot assert rendered pixel-level CSS. These are verified via manual browser inspection or e2e screenshot comparison.

### Sampling Rate
- **Per task commit:** `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI --include=**/app.component.spec.ts`
- **Per wave merge:** `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/angular/src/app/pages/main/app.component.spec.ts` — covers NAV-03 (connected badge state) and NAV-04 (bell badge presence). Must test `connected$` Observable binding and `notifications$` size-to-badge logic.

---

## Security Domain

This phase is UI-only (CSS + Angular template). No new HTTP endpoints, no user input processing, no auth changes, no cryptography, no data storage. ASVS categories do not apply to this phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Font Awesome 4.7 is globally available as a CSS icon font (no per-component import needed) | Standard Stack | If FA 4.7 is scoped only to specific components, `fa-bell` may not render in `app.component.html`; fix: add FA import to `app.component.scss` or load globally |
| A2 | `StreamServiceRegistry` can be injected into `AppComponent` without circular dependency | Code Examples #6 | If DI graph creates a circular dependency, the alternative is injecting `ConnectedService` directly (it is a root provider in appConfig) |

**If A2 is a concern:** `ConnectedService` is listed directly in `appConfig.providers`, so direct injection into `AppComponent` is safe as an alternative to going through `StreamServiceRegistry`.

---

## Open Questions

1. **Should `#top-header` / `<app-header>` be removed entirely from `app.component.html`?**
   - What we know: After D-11, `HeaderComponent` produces no visible DOM output (template becomes empty). The `#top-header` div has sticky positioning and its own background — it becomes a ghost strip.
   - What's unclear: Whether `HeaderComponent` should become a headless service-wrapper (still rendered, no template output) or if the `<app-header>` element should be removed from the template entirely and `HeaderComponent` converted to a pure service or merged into `AppComponent`.
   - Recommendation: Remove `#top-header` and `<app-header>` from `app.component.html`. Keep `HeaderComponent` as a standalone component with an empty template, rendered nowhere — OR move its subscription logic into `AppComponent` directly (simplest). **The planner should decide which approach to take.**

2. **`ResizeObserver` on `topHeader` ref after removal**
   - What we know: `AppComponent.ngAfterViewInit` sets up a `ResizeObserver` on `@ViewChild('topHeader')` to track header height for `DomService.setHeaderHeight`. If `#top-header` is removed, this ref becomes undefined.
   - What's unclear: Whether any page component uses the header height value from `DomService`.
   - Recommendation: Investigate `DomService.setHeaderHeight` usage before removing `#top-header`. If unused by any page, remove the `ResizeObserver` block and the `#topHeader` ref. If used, keep `#top-header` as an invisible 0-height element or set a fixed height.

---

## Sources

### Primary (HIGH confidence — verified by direct code inspection)
- `src/angular/src/app/pages/main/app.component.html` — current nav template structure
- `src/angular/src/app/pages/main/app.component.scss` — current nav SCSS, z-index variables, toast animation patterns
- `src/angular/src/app/pages/main/app.component.ts` — component class, DI, existing subscriptions
- `src/angular/src/app/pages/main/header.component.ts/html/scss` — full HeaderComponent (template, subscriptions, styles)
- `src/angular/src/app/services/utils/connected.service.ts` — `connected: Observable<boolean>` API
- `src/angular/src/app/services/utils/notification.service.ts` — `notifications: Observable<Immutable.List<Notification>>` API
- `src/angular/src/app/services/utils/notification.ts` — `Notification` model and `Level` enum
- `src/angular/src/app/services/base/stream-service.registry.ts` — `StreamServiceRegistry.connectedService` accessor
- `src/angular/src/app/app.config.ts` — full DI provider list confirming `ConnectedService`, `NotificationService` are root providers
- `src/angular/src/app/common/_common.scss` — `$small-max-width`, `$zindex-top-header`, `$gray-300`, `$moss-border`
- `src/angular/src/app/common/_bootstrap-variables.scss` — `$success`, `$danger`, `$primary`, palette values
- `src/angular/src/styles.scss` — CSS custom properties (`--app-logo-color`, `--app-header-bg`, etc., lines 85-107)
- `.aidesigner/runs/2026-04-14T03-20-41-363Z-seedsyncarr-dashboard-in-triggarr-st/design.html` — Nav reference (lines 116-162), pulse animation (lines 100-105)
- `.planning/phases/62-nav-bar-foundation/62-CONTEXT.md` — All locked decisions D-01 through D-11

### Secondary (MEDIUM confidence)
- CSS `backdrop-filter` browser compatibility — standard CSS3 feature; `-webkit-` prefix required for Safari [ASSUMED based on well-known browser compatibility, not freshly verified via MDN in this session]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in actual project files
- Architecture patterns: HIGH — based on existing code patterns in the codebase
- Pitfalls: HIGH — derived from actual code analysis (z-index values, existing sticky setup, ResizeObserver ref)
- CSS values: HIGH — pulled from actual `_bootstrap-variables.scss` and `styles.scss`

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable Angular/CSS domain, slow-moving)
