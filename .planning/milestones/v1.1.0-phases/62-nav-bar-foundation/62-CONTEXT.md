# Phase 62: Nav Bar Foundation - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the existing top nav bar to Triggarr-level visual polish: backdrop blur with semi-transparent background, amber active link indicator, live connection status badge with pulse animation, and notification bell icon with dropdown panel. This is the shared foundation visible on every page.

</domain>

<decisions>
## Implementation Decisions

### Nav Bar Visual Style
- **D-01:** Background uses ~80% opacity on forest-base with backdrop-blur (12px). CSS: `background: rgba(21, 26, 20, 0.80); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);`
- **D-02:** Bottom border changes from current `$gray-300` to forest-border (`#3e4a38`) to match the Deep Moss palette
- **D-03:** Brand text uses amber highlight on the "arr" suffix: "SeedSync" in primary text color + "arr" in amber accent (`--app-logo-color` / `#c49a4a`). No logo icon — stays text-only.

### Active Link Indicator
- **D-04:** Active nav link gets a 2px amber underline bar at the bottom, full width of the link text. Implemented via `::after` pseudo-element with `background: var(--app-logo-color)`.
- **D-05:** The indicator uses a fade in/out transition (opacity 0.15s ease) when switching between pages. Old link's bar fades out, new link's bar fades in.

### Connection Status Badge
- **D-06:** Right-aligned pill badge in the nav showing a colored dot + text. Connected state: green pulsing dot + "Connected" text in a semantic-success bordered pill. Disconnected state: red dot (no pulse) + "Disconnected" in a semantic-error bordered pill.
- **D-07:** Data source is the existing `ConnectedService.connected` Observable.
- **D-08:** Responsive: below ~640px, collapse the pill to dot-only (hide text, keep the status dot visible).

### Notification Bell
- **D-09:** Bell uses Font Awesome 4.7 `fa-bell` icon (icon font, not SVG — consistent with project's FA 4.7 usage). Amber badge dot appears when notifications are present. Hover changes bell color to amber.
- **D-10:** Clicking the bell opens a dropdown panel below it showing the notification list from `NotificationService`. Individual notifications can be dismissed from the panel.
- **D-11:** The existing inline Bootstrap alert bar (`HeaderComponent` / `#header`) is removed entirely. The bell dropdown replaces it as the single notification surface. All notification levels (DANGER, WARNING, INFO, SUCCESS) go through the bell.

### Claude's Discretion
- Exact pulse animation keyframes and timing
- Dropdown panel dismiss-all behavior (if warranted)
- Nav height adjustments if needed (currently 48px)
- Mobile hamburger behavior for nav links (preserve existing responsive approach)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Artifacts
- `.aidesigner/runs/2026-04-14T03-20-41-363Z-seedsyncarr-dashboard-in-triggarr-st/design.html` — AIDesigner dashboard mockup with nav bar reference (lines 116-162 show the nav)

### Existing Code (modify in place)
- `src/angular/src/app/pages/main/app.component.html` — Current nav template (add blur, amber brand, connection badge, bell)
- `src/angular/src/app/pages/main/app.component.scss` — Current nav styles (update background, border, add indicator)
- `src/angular/src/app/pages/main/header.component.ts` — Current notification alerts (refactor to bell dropdown)
- `src/angular/src/app/pages/main/header.component.html` — Alert bar template (replace with bell dropdown panel)
- `src/angular/src/app/pages/main/header.component.scss` — Alert styles (replace with dropdown styles)

### Data Sources
- `src/angular/src/app/services/utils/connected.service.ts` — `ConnectedService.connected` Observable for status badge
- `src/angular/src/app/services/utils/notification.service.ts` — `NotificationService` for bell notifications
- `src/angular/src/app/services/utils/notification.ts` — `Notification` model with Level enum

### Palette & Variables
- `src/angular/src/styles.scss` — CSS custom properties (lines 87-105: `--app-header-bg`, `--app-logo-color`, `--app-muted-text`, etc.)
- `src/angular/src/app/routes.ts` — `ROUTE_INFOS` used for nav link generation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ConnectedService` — Already exposes `connected: Observable<boolean>` for live connection state
- `NotificationService` — Already manages `Immutable.List<Notification>` with show/hide/dismiss
- `Notification` model — Has Level enum (DANGER, WARNING, INFO, SUCCESS), text, dismissible flag, timestamp
- Font Awesome 4.7 — Already available in the project for `fa-bell` icon
- CSS custom properties — Full Deep Moss palette already defined in `styles.scss`

### Established Patterns
- Standalone components with explicit imports (Angular 21 pattern)
- `takeUntil(this.destroy$)` for subscription cleanup
- `routerLinkActive="active"` for active route detection (already in use)
- Toast notifications use Triggarr-style slide-in animation (app.component.scss)

### Integration Points
- Nav bar is rendered in `app.component.html` — shared across all pages via `<router-outlet>`
- `HeaderComponent` (`<app-header>`) is a child of AppComponent — sits between nav and router-outlet
- `StreamServiceRegistry` provides access to `ConnectedService` (already injected in HeaderComponent)

</code_context>

<specifics>
## Specific Ideas

- The "arr" amber highlight on the brand name matches Triggarr's pattern of accent-colored suffixes
- Connection badge should feel like Triggarr's status indicators — monospace font, bordered pill, semantic colors
- Bell dropdown should be a lightweight panel, not a Bootstrap modal — stays in nav context

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 62-nav-bar-foundation*
*Context gathered: 2026-04-14*
