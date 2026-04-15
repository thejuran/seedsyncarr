# Phase 67: About Page - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Redesign the About page to match the AIDesigner mockup — centered identity card with brand asset, system info table, link cards grid with hover-to-amber transitions, and a license/copyright footer. All visual elements use the Deep Moss + Amber palette and card-based layout established in prior phases.

</domain>

<decisions>
## Implementation Decisions

### System Info Data
- **D-01:** No new backend endpoint for this phase. System info table shows only data available at build time or from existing services.
- **D-02:** Rows to display: App Version (from package.json), Angular Version (build-time constant). Remaining mockup rows (Python version, OS, uptime, PID, config path) show static placeholder dashes or generic values (e.g., `~/.seedsyncarr` for config path) until a backend `/server/status` endpoint is added in a future phase.
- **D-03:** The system info table uses the mockup's key-value row layout: uppercase label left, monospace value right, with divider lines between rows and hover highlight.

### Identity Card
- **D-04:** App icon uses the actual SeedSyncarr brand favicon asset from `doc/brand/` (not the Phosphor arrows-merge icon from the mockup). Displayed in an amber-bordered rounded container matching the mockup layout.
- **D-05:** Brand text uses the established "SeedSync" + amber "arr" pattern from the nav bar (Phase 62 D-03).
- **D-06:** Tagline: "Sync files from your seedbox to your local media server — fast, automated, and integrated with Sonarr and Radarr." (from README, not mockup text).
- **D-07:** Version string shows the app version from package.json with "(Stable)" suffix. Build info line (commit hash, build date) included if available at build time, otherwise omitted.

### Link Cards
- **D-08:** Four link cards in a responsive grid: GitHub, Docs, Report Issue, Changelog.
- **D-09:** URLs: GitHub → `https://github.com/thejuran/seedsyncarr`, Docs → `https://thejuran.github.io/seedsyncarr/`, Report Issue → `https://github.com/thejuran/seedsyncarr/issues`, Changelog → `https://github.com/thejuran/seedsyncarr/releases`.
- **D-10:** All links open in new tabs (`target="_blank"`), consistent with current About page behavior.
- **D-11:** Each card uses a Phosphor icon (ph-github-logo, ph-book, ph-bug, ph-git-commit) with hover-to-amber color transition on both icon and text, matching the mockup.

### License & Copyright
- **D-12:** License badge shows "Apache License 2.0" (correcting the mockup's "MIT License").
- **D-13:** Copyright text — Claude's discretion to match LICENSE.txt content exactly.

### Claude's Discretion
- Exact fade-in-up animation timing for page load
- System info table row hover effect intensity
- Identity card ambient glow effect (the mockup has a subtle amber radial gradient behind the icon)
- Fork attribution note ("Based on SeedSync by Inderpreet Singh") — keep, restyle, or fold into copyright
- Responsive breakpoints for link cards grid (4-col on desktop, 2-col on mobile per mockup)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Spec
- `.aidesigner/runs/2026-04-14T03-35-42-278Z-seedsyncarr-about-page-triggarr-styl/design.html` — AIDesigner mockup (Tailwind) to be ported to Bootstrap 5 + SCSS

### Existing Code
- `src/angular/src/app/pages/about/about-page.component.html` — Current About page template (to be rewritten)
- `src/angular/src/app/pages/about/about-page.component.ts` — Current component (reads version from package.json)
- `src/angular/src/app/pages/about/about-page.component.scss` — Current styles (to be rewritten)

### Brand Assets
- `doc/brand/` — Canonical brand source PNGs (favicon, wordmarks)

### Prior Phase Patterns
- `.planning/phases/62-nav-bar-foundation/62-CONTEXT.md` — Nav bar decisions (D-01 through D-11), brand text pattern, palette tokens
- `.planning/phases/65-settings-page/65-CONTEXT.md` — Card-based layout patterns, Phosphor icon usage
- `.planning/phases/66-logs-page/66-CONTEXT.md` — Full-viewport layout with status bar pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AboutPageComponent` — Standalone Angular component, already wired into routing. Reads `appVersion` from package.json via `require()`.
- Deep Moss palette tokens in `_bootstrap-variables.scss` — `--app-logo-color`, `--app-muted-text`, `--app-separator-color`, etc.
- Phosphor Icons — already loaded project-wide (used in Phases 65, 66)

### Established Patterns
- Card layout with `bg-seed-card` borders, rounded corners, and shadow-sm (Settings Phase 65)
- Amber hover transitions on interactive elements (nav links Phase 62, link cards mockup)
- Monospace font for technical data (`font-family: var(--bs-font-monospace)`)

### Integration Points
- `app-routing.module.ts` — About page already routed at `/about`
- Nav bar — "About" link with amber active indicator (Phase 62)
- No new services needed — version data from package.json, all links are static

</code_context>

<specifics>
## Specific Ideas

- Brand favicon asset in the identity card instead of Phosphor icon — gives the page a polished branded feel
- README tagline preferred over mockup text — keeps messaging consistent across GitHub, docs site, and the app itself
- GitHub Releases for Changelog link — always current, no manual CHANGELOG.md maintenance

</specifics>

<deferred>
## Deferred Ideas

- Backend `/server/status` endpoint for live system info (Python version, OS, uptime, PID, config path) — future phase
- Build info injection (commit hash, build date) via environment variables at Docker build time — future enhancement

</deferred>

---

*Phase: 67-about-page*
*Context gathered: 2026-04-14*
