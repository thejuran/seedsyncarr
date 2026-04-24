# SeedSync

## What This Is

SeedSync is a file syncing tool that syncs files from a remote Linux server (like a seedbox) to a local machine using LFTP. Features a clean modern dark web UI (Deep Moss + Amber palette, system fonts, top nav bar, flat file rows), Sonarr/Radarr integration for automated post-download workflows, and real-time transfer status via SSE. Security-hardened with Bearer token API auth, HMAC webhook auth, CSP (hash-based via autoCsp), DNS rebinding prevention, credential redaction, SSRF protection, path traversal guards, and thread-safe concurrent operations.

## Core Value

Reliable file sync from seedbox to local with automated media library integration.

## Previous State

**v1.1.2 in progress (2026-04-24)** — Test Suite Audit. Phase 84 (Angular Test Audit) complete: zero stale tests across 40 spec files, 6 spec files migrated from deprecated HttpClientTestingModule to provideHttpClient API, 599/599 tests green, coverage baseline 83.34%/69.01%/79.73%/84.21%.

**v1.1.1 (2026-04-23)** — Post-Redesign Cleanup & Outstanding Work. Per-child import state tracking (GH #19 data-loss fix), multiselect bulk-bar union fix, 15 new Playwright E2E specs (37 total), live-seedbox UAT, CI noise elimination + CSP enforcement, Dependabot alert closed, arm64 Docker test support, WAITING_FOR_IMPORT dead enum removed, optional Fernet encryption at rest for 5 config secrets, retroactive v1.1.0 release notes + v1.1.1 release.

<details>
<summary>v1.1.0 (2026-04-19)</summary>

UI Redesign — Triggarr Style. All 4 pages ported from AIDesigner mockups (nav bar with backdrop blur, dashboard stats+table+log pane, settings masonry, terminal log viewer, about page); SCSS palette consolidated, clickable version badges, brand favicon; drill-down segment filters. Addendum (phases 72-74) restored per-file selection + 5-action bulk bar, extended dashboard filter to cover every torrent status with URL query-param persistence, and added disk-capacity awareness to storage tiles (local via `shutil.disk_usage`, remote via `df -B1` over SSH) with 80%/95% threshold color shifts.

</details>

<details>
<summary>v4.0.3 (released 2026-04-08)</summary>

Dependency security fixes (hono/node-server overrides) and CI verification.

</details>

<details>
<summary>v4.0.3 Dependency Fixes & CI (2026-04-08)</summary>

- Closed 6 Dependabot security alerts (#44-#49) via npm overrides for hono (^4.12.12) and @hono/node-server (^1.19.13)
- Verified CI lint (ruff + eslint) and release tag (:main) coverage already present
- Deep review: fixed unbounded >= constraints to ^ for supply chain safety

</details>

<details>
<summary>v4.0.0 Release (M010, 2026-03-28)</summary>

- Screenshots captured via Playwright, README + docs updated, version bumped to 4.0.0
- GitHub release created with categorized changelog, Docker `:latest` + Deb packages published

</details>

<details>
<summary>Full Codebase Deep Review (M009, 2026-03-28)</summary>

- 55 TuringMind review issues fixed: LFTP newline/CR/null injection, shlex.quote for remote_scanner, credential log redaction
- Concurrency: model reads under lock, dedicated __pending_auto_deletes lock, shallow copy parent ref fixes
- Frontend: SSE subscription lifecycle, view-file index updates, pexpect TIMEOUT handling, inner Observable teardown
- Code quality: bare except narrowing, BFS deque, log levels, Optional types, version file sync
- 1134 Python + 401 Angular tests passing, CI green

</details>

<details>
<summary>AutoQueue Migration, Token UI & Toast Polish (M008, 2026-03-27)</summary>

- AutoQueue page merged into Settings card with inline pattern CRUD
- API token reveal/hide/copy in Settings Security card (R017 complete)
- Triggarr-style toasts with type icons and slide-in animation (R040 complete)
- Stale gsd/* branches cleaned up

</details>

<details>
<summary>Settings Redesign & Multi-Select Polish (M007, 2026-03-26)</summary>

- Settings page: Triggarr-style card sections, labels-above-inputs, no accordion JS
- Dashboard multi-select: merged selection-banner into single unified bulk-actions-bar
- 401+ unit tests passing

</details>

<details>
<summary>Triggarr-Style Layout + Deep Moss Palette (M006, 2026-03-25)</summary>

- Deep Moss + Amber palette with WCAG AA contrast (4.5:1+)
- File list redesigned to flat single-line rows matching Triggarr
- Code review findings addressed, `:dev` image published, UAT passed

</details>

<details>
<summary>Dashboard Polish & v3.3.0 (M005, 2026-03-24)</summary>

- Dashboard column alignment and typography fixes at all responsive breakpoints

</details>

<details>
<summary>Polish & Dependency Updates (M004, 2026-03-24)</summary>

- R017 (API token in Settings) + R040 (toast restyle) addressed
- Immutable.js 4→5, TypeScript 5→6, 21 npm dependency updates from PR #161

</details>

<details>
<summary>UI Redesign — Earthy Palette (M003, 2026-03-25)</summary>

- Earthy palette: Jet Black, Deep Walnut, Olive Bark, Khaki Beige, Lavender
- Sidebar replaced with top nav bar, all terminal effects removed
- System font stack (no Google Fonts), text-only buttons, status dots, percentage progress
- Settings cards, clean About/Logs/AutoQueue pages, unused SVG assets removed

</details>

<details>
<summary>Finish v3.2 Security (M002, 2026-03-22)</summary>

- Bearer token auth on /server/* endpoints with auto-generation
- Host header validation (DNS rebinding prevention) with configurable allowlist
- Angular HTTP interceptor for transparent token injection
- Conditional config redaction for authenticated requests (CONF-04 fix)
- Angular autoCsp for hash-based CSP (no unsafe-inline)

</details>

<details>
<summary>Angular 21 Migration (M001, 2026-03-21)</summary>

- Angular 19→20→21 stepwise migration, 394 unit tests passing
- 3 high/critical Dependabot security alerts resolved
- TypeScript upgrade, zone.js and jQuery 3→4, dependabot ignores removed
- Full CI green (Python + Angular + Deb + Docker + E2E)

</details>

<details>
<summary>v3.1 and earlier (shipped by 2026-02-24)</summary>

- v3.1: Security hardening — RCE chain closed, credential redaction, 4 race conditions fixed, 6 crash bugs eliminated
- v3.0: Terminal UI Overhaul — dark-only with Fira Code, sidebar, ASCII progress, CRT overlay
- v2.0: Dark Mode & Polish — theme system, FOUC prevention, CSS variables
- v1.7-v1.8: Sonarr/Radarr integration with webhook-based import detection and auto-delete
- v1.0-v1.6: Bootstrap 5 migration, form/dropdown unification, Sass @use, backend testing, CI cleanup

</details>

## Requirements

### Validated

**v3.1 (Shipped 2026-02-24):**

- ✓ RSA key removed, SSH host key verification hardened (TOFU), pickle→JSON — v3.1
- ✓ Config API redacts credentials, LFTP passwords scrubbed from SSE logs — v3.1
- ✓ SSRF protection on *arr test endpoints, shell metacharacter escaping — v3.1
- ✓ HMAC webhook authentication, security headers on all responses — v3.1
- ✓ Thread-safe auto-delete, webhook imports, and ExtractDispatch queue — v3.1
- ✓ Crash prevention: exception propagation, None guards, SSE resilience, bounded timeouts — v3.1
- ✓ XSS sanitization, Observable pipe refactors, subscription leak fixes — v3.1
- ✓ Python 3.12+ compatibility (distutils replaced), pexpect argv, POST/DELETE mutations — v3.1
- ✓ Focus trap + ARIA labels for keyboard accessibility — v3.1
- ✓ CLAUDE.md updated, API response codes documented — v3.1
- ✓ 12 code review follow-up fixes (credential leak, log redaction, TOCTOU, timer cleanup) — v3.1

**v3.0 (Shipped 2026-02-17):**

- ✓ Fira Code font for all data displays (filenames, speeds, sizes, progress) — v3.0
- ✓ IBM Plex Sans for UI labels, buttons, and navigation — v3.0
- ✓ Deep dark backgrounds (#0d1117 base) with green accent palette — v3.0
- ✓ CRT scan-line overlay effect (subtle, low opacity) — v3.0
- ✓ Custom dark scrollbar styling — v3.0
- ✓ Sidebar as 56px icon rail, expands to 200px on hover — v3.0
- ✓ `>` prompt indicator on active route in sidebar — v3.0
- ✓ App version at bottom of sidebar — v3.0
- ✓ Mobile hamburger menu preserved — v3.0
- ✓ Search input with terminal prompt `>` prefix — v3.0
- ✓ Colored left border on file rows by status — v3.0
- ✓ ASCII-style block progress bars — v3.0
- ✓ Green glow effect on actively downloading rows — v3.0
- ✓ Colored dot + text for file status (no SVG icons) — v3.0
- ✓ Ghost-style action buttons with glow on hover — v3.0
- ✓ Terminal-style section headers in Settings — v3.0
- ✓ Monospace patterns in AutoQueue with green/red buttons — v3.0
- ✓ True terminal-style Logs (monospace, colored by level) — v3.0
- ✓ ASCII-art inspired About page — v3.0
- ✓ Theme toggle removed from Settings page — v3.0
- ✓ ThemeService simplified to dark-only — v3.0

**v2.0 (Shipped 2026-02-12):**

- ✓ Dark theme for entire UI (backgrounds, text, components) — v2.0
- ✓ Light theme preserved as current default — v2.0
- ✓ OS `prefers-color-scheme` auto-detection — v2.0
- ✓ Manual dark/light toggle in Settings page (Appearance section) — v2.0
- ✓ Toast/notification text references both Sonarr and Radarr — v2.0
- ✓ Auto-delete description references both Sonarr and Radarr — v2.0
- ✓ WAITING_FOR_IMPORT enum value for file status — v2.0

**v1.6 (Shipped 2026-02-10):**

- ✓ `:dev` Docker image published to GHCR on every master push (multi-arch) — v1.6
- ✓ `docker-publish.yml` removed — single CI workflow handles everything — v1.6
- ✓ Version tag publishing continues working on tag pushes — v1.6
- ✓ pytest cache warnings suppressed in Docker test runner — v1.6
- ✓ webob cgi deprecation warnings filtered from test output — v1.6

**v1.5 (Shipped 2026-02-08):**

- ✓ pytest-cov integration with coverage reporting and fail_under threshold — v1.5
- ✓ Unit tests for common module gaps (5 modules, 100% coverage) — v1.5
- ✓ Unit tests for web handler gaps (7 handlers, 69 tests) — v1.5
- ✓ Unit tests for controller.py and controller_job.py (106 tests) — v1.5
- ✓ Coverage 77% → 84%, 231 new tests — v1.5

**v1.4 (Shipped 2026-02-08):**

- ✓ Migrate all @import to @use/@forward across Angular SCSS files — v1.4
- ✓ Eliminate Sass @import deprecation warnings from build output — v1.4

**v1.3 (Shipped 2026-02-04):**

- ✓ Fix TypeScript strictness lint errors (62 issues) — v1.3
- ✓ Status dropdown shows file counts per status — v1.3

**v1.2 (Shipped 2026-02-04):**

- ✓ Details button removed — v1.2
- ✓ Pin button removed — v1.2

**v1.1 (Shipped 2026-02-04):**

- ✓ File options dropdowns use Bootstrap dropdown component — v1.1
- ✓ All text inputs use consistent Bootstrap form styling — v1.1
- ✓ Form focus states use app color scheme — v1.1
- ✓ Full E2E test suite passes — v1.1

**v1.0 (Shipped 2026-02-03):**

- ✓ Bootstrap SCSS infrastructure with customizable variables — v1.0
- ✓ All colors consolidated to Bootstrap theme variables — v1.0
- ✓ Selection highlighting unified with teal palette — v1.0
- ✓ All buttons standardized to Bootstrap semantic variants — v1.0

**v1.1.0 (Shipped 2026-04-19):**

- ✓ Nav bar with backdrop blur, amber active indicator, connection badge, notification bell — v1.1.0
- ✓ Dashboard stats strip (4 metric cards), transfer table (search, filters, progress, pagination) — v1.1.0
- ✓ Dashboard compact terminal log pane with severity coloring — v1.1.0
- ✓ Settings masonry layout, toggle switches, brand Sonarr/Radarr cards, floating save bar — v1.1.0
- ✓ Terminal log viewer with level filter, regex search, auto-scroll, export, status bar — v1.1.0
- ✓ About page identity card, system info, link cards, license footer — v1.1.0
- ✓ SCSS palette consolidated to shared aliases, brand favicon, clickable version badges — v1.1.0
- ✓ Drill-down segment filters (Active/Errors expand to individual statuses) — v1.1.0
- ✓ Per-file selection + 5-action card-internal bulk bar (Queue/Stop/Extract/Delete Local/Delete Remote) with shift-range + page-scoped header select-all — v1.1.0
- ✓ Dashboard filter covers every `ViewFile.Status` (Done parent + Pending sub) with URL query-param persistence and silent fallback on invalid values — v1.1.0
- ✓ Storage capacity tiles — `StorageStatus` on `Status` model, `shutil.disk_usage` local + `df -B1 <shlex.quote>` over SSH remote, `>1%` change gate, 80%/95% warning/danger thresholds — v1.1.0

**v1.1.1 (Shipped 2026-04-23):**

- ✓ Multiselect bulk-bar union fix — DELETED rows surface Queue + Delete Remote in mixed selections — v1.1.1
- ✓ Per-child import state tracking — auto-delete blocked on partial Sonarr imports (GH #19) — v1.1.1
- ✓ 15 Playwright E2E specs (selection+bulk-bar, dashboard-filter+URL-roundtrip), CI-gated amd64+arm64 — v1.1.1
- ✓ Storage tile live-seedbox UAT — 6 items validated against live infra — v1.1.1
- ✓ Dependabot alert #3 closed — basic-ftp ^5.3.0 override — v1.1.1
- ✓ CI noise elimination — zero pytest-cache/cgi warnings, CSP violation listener — v1.1.1
- ✓ arm64 Docker test build support — conditional rar install + class-level skip — v1.1.1
- ✓ WAITING_FOR_IMPORT dead enum removed (was never set by business logic) — v1.1.1
- ✓ Optional Fernet encryption at rest for 5 config secrets — v1.1.1
- ✓ Retroactive v1.1.0 release notes + v1.1.1 CHANGELOG + GitHub Releases — v1.1.1

### Active

**Current Milestone: v1.1.2 Test Suite Audit**

**Goal:** Identify and remove stale, redundant, or dead-path tests inherited from the original SeedSync repo — lean the test suite to only test current behavior.

**Progress:**
- Phase 83 complete — Python test audit: zero stale tests found, 85.05% coverage baseline recorded (2026-04-24)

**Target features:**
- Audit Python backend tests for stale/dead-path coverage of removed or rewritten functionality
- Audit Angular frontend tests for tests covering deleted components or superseded UI patterns
- Audit Playwright E2E tests for redundancy or stale selectors
- Remove or rewrite identified dead tests without regressing real coverage
- Verify coverage % holds or improves after cleanup

### Out of Scope

- Lidarr/Readarr support — defer to future milestone
- Bootstrap @import → @use migration — blocked until Bootstrap 6
- Angular→htmx/Tailwind rewrite — visual kinship via design patterns, not framework
- OAuth / multi-user auth — single-user self-hosted tool
- HTTPS termination — handled by reverse proxy
- Rate limiting — single-user tool, add at reverse proxy if needed
- New favicon/logo design — keep existing favicon.png

## Context

**Codebase state:**
- ~33k Python LOC, ~15.5k TypeScript LOC
- 1,262 Python tests, 84% coverage (fail_under enforced)
- 599 Angular unit tests passing
- 37 Playwright E2E specs (amd64+arm64), CI-gated
- Zero TypeScript lint errors
- Angular 21.x, TypeScript 6, Python 3.12+ compatible

**Technical notes:**
- Application SCSS uses @use/@forward; Bootstrap remains on @import (required by Bootstrap 5.3)
- Dark-only via hardcoded `data-bs-theme="dark"` on HTML element (no JS theme switching)
- Deep Moss + Amber earthy palette with WCAG AA contrast ratios
- System font stack (no Google Fonts dependency)
- Top nav bar (Triggarr-style), flat file rows, card-based Settings
- AutoQueue merged into Settings page
- `make run-tests-python` Docker build works on arm64 (Apple Silicon) — `rar` install gated by `dpkg --print-architecture`, rar-dependent tests skipped via class-level `skipIf`
- Per-child import state tracking prevents pack-wide auto-delete on Sonarr silent-rejects (GH #19)
- Optional Fernet encryption at rest for `api_token`, `webhook_secret`, `sonarr_api_key`, `radarr_api_key`, `remote_password` (opt-in via `[Encryption]` config section)
- Bearer token API auth (auto-generated, timing-safe comparison, meta tag injection)
- SSE and webhook endpoints exempt from Bearer auth (EventSource limitation / HMAC respectively)
- Hash-based CSP via Angular autoCsp (no unsafe-inline); Playwright CSP violation listener fails E2E on breaches
- DNS rebinding prevention via Host header allowlist
- Path traversal guards (realpath-based) on delete/extract endpoints
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options) on all API responses
- HMAC-SHA256 webhook authentication (empty secret = skip verification for backward compat)
- Config API redacts sensitive fields; SSE log stream scrubs passwords
- SSH uses StrictHostKeyChecking=accept-new (TOFU) with persistent known_hosts
- CI: lint job (ruff + eslint), unit tests, E2E (amd64+arm64), Docker + Deb builds

## Constraints

- **No functional regressions**: All existing features must continue working
- **Bootstrap 5 patterns**: Leverage Bootstrap classes where possible
- **Dark-only**: Dark-only UI with Deep Moss + Amber earthy palette
- **Visual kinship with Triggarr**: Same layout structure (top nav, card sections), differentiated by color palette

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use teal (secondary) for all selections | Teal is more distinctive than blue, already used in bulk selection | ✓ Good |
| Migrate to Bootstrap `btn` classes | Reduces custom CSS, leverages Bootstrap's states | ✓ Good |
| Keep @import for Bootstrap SCSS | Mixing @use/@import creates namespace conflicts | ✓ Good |
| CSS variables for Bootstrap theming | Easier maintenance, runtime flexibility vs SCSS overrides | ✓ Good |
| Bootstrap 5.3 data-bs-theme for dark mode | Native framework support, minimal custom CSS | ✓ Good |
| Hardcode data-bs-theme="dark" (v3.0) | App is dark-only, no runtime JS needed for theme switching | ✓ Good |
| ~~Google Fonts CDN~~ → System font stack | Removes external dependency, faster load (superseded by M003) | ✓ Good |
| ~~CRT overlay~~ → Removed in M003 | Terminal effects replaced with clean modern UI | ✓ Good |
| ~~Sidebar~~ → Top nav bar | Matches Triggarr's pattern for visual kinship (M003) | ✓ Good |
| Deep Moss + Amber earthy palette | WCAG AA contrast, visual differentiation from Triggarr | ✓ Good |
| Source-agnostic toast text ("Sonarr/Radarr") | System doesn't distinguish which *arr triggered import | ✓ Good |
| SSH TOFU (accept-new) over reject-all | Preserves first-connect usability while blocking MITM on reconnects | ✓ Good |
| Pickle→JSON for remote scanner | Eliminates RCE vector (CWE-502), same data fidelity | ✓ Good |
| Redact at serialization layer not storage | Internal code reads real values, API clients see **REDACTED** | ✓ Good |
| Empty webhook_secret skips HMAC | Backward compat for existing installs; configured = strict | ✓ Good |
| Security headers via after_request hook | Zero-touch, applies to all routes automatically | ✓ Good |
| Model lock two-window pattern | Lock only for data access, release before subprocess spawn | ✓ Good |
| Atomic extract() under single mutex | Eliminates TOCTOU race between duplicate check and insert | ✓ Good |
| POST/DELETE for mutation endpoints | Prevents browser prefetch/crawler side effects | ✓ Good |
| pexpect argv list over shell string | Eliminates shell metacharacter injection (CWE-88) | ✓ Good |
| Inline _strtobool over distutils | Zero new dependencies, Python 3.12+ compatible | ✓ Good |
| takeUntil/destroy$ for Angular cleanup | Uniform subscription management, no mixed patterns | ✓ Good |
| getMessage() for log redaction | Catches format-arg passwords that record.msg misses | ✓ Good |
| Text-only UI, no SVG icons | Clean minimal aesthetic; status dots for filter dropdowns | ✓ Good |
| AutoQueue merged into Settings | Reduces nav, all config in one place | ✓ Good |
| Major version bump to 4.0.0 | UI redesign + security hardening = breaking change scope | ✓ Good |
| Angular autoCsp for hash-based CSP | No server-side nonce logic needed; set-and-forget | ✓ Good |
| Bearer token auth with meta tag injection | Avoids circular fetch; transparent via Angular interceptor | ✓ Good |
| Host header allowlist for DNS rebinding | Minimal default (localhost); user adds reverse proxy hostname | ✓ Good |
| Keep bare except in config.py test handlers | CI mock prevents RequestException class resolution | ✓ Good |
| pexpect close uses explicit except, not finally | Preserves post-close attribute access for error reporting | ✓ Good |
| Remove WAITING_FOR_IMPORT enum value (TECH-02) | Placeholder since v2.0 (2026-02-12); never set by business logic; Phase 73 explicitly deferred wiring; re-add alongside future Sonarr Grab-event ingestion if prioritized | ✓ Good |

## Project Status

**Status:** v1.1.1 shipped (2026-04-23). All outstanding work from prior milestones closed.

29 milestones shipped (v1.0 through v4.0.3 as SeedSync, v1.0.0 rebrand + v1.1.0 UI redesign + v1.1.1 cleanup as SeedSyncarr).

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-23 after v1.1.1 milestone*
