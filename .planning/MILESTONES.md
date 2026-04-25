# Project Milestones: SeedSync

## v1.1.2 Test Suite Audit (Shipped: 2026-04-24)

**Phases completed:** 4 phases, 6 plans, 10 tasks
**Git range:** 65 commits, 177 files changed, +8,381/-27,052 lines
**Timeline:** 2026-04-24

**Delivered:** Audited all three test layers (Python, Angular, E2E) for stale/redundant tests inherited from the original SeedSync repo. Found zero stale tests across all layers — the prior rebrand and redesign milestones had already cleaned them. Migrated deprecated HttpClientTestingModule API, fixed E2E harness autoqueue config, and documented coverage baselines.

**Key accomplishments:**

- Independent staleness audit confirms zero stale Python tests across 72 test files; coverage at 85.05% above 84% fail_under threshold
- Independent staleness audit of 40 Angular spec files confirms zero stale tests; ng test green 599/599; coverage baseline Statements 83.34% / Branches 69.01% / Functions 79.73% / Lines 84.21%
- 6 Angular spec files migrated from deprecated HttpClientTestingModule to provideHttpClient()/provideHttpClientTesting(), eliminating all HttpClientTestingModule deprecation warnings; karma.conf.js angularCli key verified as silently ignored; ng test green 599/599 post-migration
- Independent staleness audit of all 7 Playwright spec files (37 tests) confirms zero stale specs — every spec targets live Angular routes and live UI selectors; zero removals made; CSP canary and dashboard specs preserved per mandate
- Enable autoqueue/enabled/true in E2E harness so autoqueue.page.spec.ts pattern section is visible, and track arm64 Unicode sort failures as pending todo per D-08
- CI pipeline fully green (1262 Python tests, 599 Angular tests, 37 E2E specs on both architectures), coverage baselines documented in ROADMAP.md, v1.1.2 Test Suite Audit milestone shipped

Known deferred items at close: 9 (see STATE.md Deferred Items)

---

## v1.1.1 Post-Redesign Cleanup & Outstanding Work (Shipped: 2026-04-23)

**Phases completed:** 8 phases, 26 plans
**Git range:** 331 commits, 305 files changed, +48,231/-4,342 lines
**Timeline:** 2026-04-19 to 2026-04-23

**Delivered:** Closed all outstanding work from prior milestones — a critical auto-delete data-loss bug, multiselect regression, deferred E2E and UAT, CI noise cleanup, a Dependabot alert, opt-in encryption at rest, and retroactive release notes — without introducing new user-facing features.

**Key accomplishments:**

- Per-child import state tracking prevents pack-wide auto-delete on Sonarr silent-rejects; per-child state persisted across restarts with bounded eviction (GH #19 fix, Phase 75)
- Multiselect bulk-bar union fix — DELETED files now surface Queue/Delete Remote in mixed selections; 5 FIX-01 regression tests across 2 spec files (Phase 76)
- 15 new Playwright E2E specs — 5 selection+bulk-bar, 10 dashboard-filter+URL-roundtrip; CI-gated on amd64+arm64 (37 total specs, Phase 77)
- Storage capacity tiles validated against live seedbox — local disk, remote SSH df, thresholds, graceful fallback; all 6 UAT items passed (Phase 78)
- CI noise elimination — zero pytest-cache/cgi warnings; CSP violation listener fails E2E on policy breaches with permanent canary spec (Phase 79)
- Dependabot alert #3 closed (basic-ftp ^5.3.0), arm64 Docker test build support, WAITING_FOR_IMPORT dead enum removed (Phase 80)
- Optional Fernet encryption at rest for 5 config secrets — keyfile with 0600 permissions, transparent decrypt, backward-compatible plaintext installs (Phase 81)
- Retroactive v1.1.0 release notes + v1.1.1 release — both versions tagged, CHANGELOG entries, Docker+Deb+GitHub Releases published (Phase 82)

Known deferred items at close: 6 (see STATE.md Deferred Items)

---

## v1.1.0 UI Redesign — Triggarr Style (Shipped: 2026-04-19)

**Phases completed:** 12 phases (62-70, 72-74; Phase 71 dropped), 30 plans total

**Delivered:** Port AIDesigner design artifacts into the Angular codebase, bringing all 4 pages to Triggarr-level visual polish with the earthy Deep Moss palette, plus a post-release addendum restoring per-file selection + bulk actions, extending the filter to cover every torrent status, and adding disk-capacity awareness to the storage tiles.

**Key accomplishments:**

- Nav bar with backdrop blur, amber active indicator, live connection badge, and notification bell dropdown replacing the inline Bootstrap alert bar (Phase 62)
- Dashboard 4-card stats strip + transfer table with search, All/Active/Errors segment filters, status badges (Syncing/Queued/Synced/Failed), animated striped progress bars, bandwidth/ETA columns, and client-side pagination (Phase 63)
- Inline terminal log pane at the bottom of the dashboard with colored severity levels (Phase 64)
- Settings CSS Grid two-column masonry with 10 icon-headed cards, pill-shaped toggle switches replacing checkboxes, brand-colored Sonarr/Radarr/AutoDelete cards with webhook copy buttons, and a floating save confirmation bar (Phase 65)
- Full-viewport terminal log viewer with level filter, regex search, auto-scroll, clear, export, and live status bar — 21 unit tests covering all LOGS requirements (Phase 66)
- About page identity card, system info table, link cards grid with hover-to-amber transitions, and license footer — 552/552 tests green, human-verified visual fidelity (Phase 67)
- SCSS palette consolidation to shared aliases, clickable version badges linking to changelog, brand favicon in nav, `version.ts` migration (Phase 68)
- E2E page-object selectors rewritten for the redesigned dashboard/bulk-actions markup (Phase 69)
- Drill-down segment filters replacing flat All/Active/Errors — Active and Errors expand to individual statuses (Syncing/Queued/Extracting and Failed/Deleted) (Phase 70)
- Per-file checkbox selection + 5-action card-internal bulk bar (Queue/Stop/Extract/Delete Local/Delete Remote) using AIDesigner Variant B; shift-range + page-scoped header select-all; FileSelectionService signal-driven `isSelected`; 4 obsolete component sets deleted (file-actions-bar, file-list, file, file-options); 5 Playwright E2E tests rewritten (Phase 72)
- Dashboard filter extended to cover every `ViewFile.Status` — Done parent (DOWNLOADED ∪ EXTRACTED), Pending sub under Active; URL query-param persistence with silent fallback on invalid values; 17 new unit tests + 3 E2E (Phase 73)
- Storage capacity tiles — `StorageStatus` component on `Status` model, `shutil.disk_usage` local + `df -B1 <shlex.quote>` over existing SSH session remote; `>1%` change gate with per-side independence; Bootstrap `warning`/`danger` semantic tokens for 80%/95% thresholds; backend 82/82 + 12 new frontend component tests (Phase 74)

**Stats (addendum 72-74):**

- 58 source files changed (+3,145 / −3,348 LOC)
- 102 commits
- Single-day execution (2026-04-19)
- Git range: `9435aa0` → `e8ccb9f`

**Deferred items (infra-gated, accepted — not gaps):**

- 15 Playwright E2E tests behind `make run-tests-e2e` (docker-compose): 5 for Phase 72 + 10 for Phase 73; CI-gated.
- 6 runtime UAT tests for Phase 74 requiring a live seedbox; SSH `df` unfakeable in E2E harness per locked design spec. Structural coverage via unit tests at 79/80/94/95 boundaries accepted. Gated on next dev release.

**Audit:** `v1.1.0-MILESTONE-AUDIT.md` status `passed` (re-audited 2026-04-19 after verification gap closure).

**Tag:** v1.1.0

**Archive:** `.planning/milestones/v1.1.0-ROADMAP.md`, `.planning/milestones/v1.1.0-REQUIREMENTS.md`, `.planning/milestones/v1.1.0-phases/`.

---

## v2.0.1 Hotfix: Webhook Child File Matching (Shipped: 2026-02-14)

**Delivered:** Fixed webhook import matching to work with child files (episodes inside show directories), not just root-level model names.

**Key accomplishments:**

- BFS traversal of model file tree to build comprehensive name-to-root lookup for webhook matching
- Child file names (e.g., episode files) now correctly map back to their root directory for import tagging and auto-delete
- No-match webhook log upgraded from DEBUG to WARNING for visibility when imports fail to match
- 5 new unit tests covering child file matching at WebhookManager and Controller levels (545 total passing)

**Stats:**

- 4 files changed (+135 lines, -32 lines)
- UAT: 2 passed, 1 skipped (not practical to trigger no-match in production)
- 2 days (debug 2026-02-12, UAT 2026-02-14)

**Git range:** `4a83863` → `066c405`
**Tag:** v2.0.1

---

## v2.0 Dark Mode & Polish (Shipped: 2026-02-12)

**Delivered:** True dark/light theme system with OS preference detection, FOUC prevention, theme toggle UI in Settings, and cosmetic fixes for *arr text references.

**Phases completed:** 29-32 (6 plans total)

**Key accomplishments:**

- Signal-based ThemeService with localStorage persistence, multi-tab sync, and OS prefers-color-scheme detection
- FOUC prevention via inline script in `<head>` applying saved theme before first paint
- Custom CSS variables (`--app-*`) for light/dark themes with Bootstrap 5.3 `data-bs-theme` integration
- All 25 hardcoded SCSS colors migrated to runtime theme-aware CSS variables across 7 components
- Appearance section in Settings with Light/Dark/Auto button group (full ARIA accessibility, responsive layout)
- Updated *arr text to "Sonarr/Radarr" and added WAITING_FOR_IMPORT enum across full serialization pipeline

**Stats:**

- 44 files changed (+4,902 lines, -113 lines)
- 4 phases, 6 plans
- 2 days (2026-02-11 to 2026-02-12)

**Git range:** `ad35d2e` → `db1115c`

**What's next:** Run `/gsd:new-milestone` to start next milestone (Lidarr/Readarr support, or other features).

---

## v1.8 Radarr + Webhooks (Shipped: 2026-02-11)

**Delivered:** Radarr integration alongside Sonarr with shared *arr Settings UI, webhook-based import detection replacing polling, and all pre-existing test failures resolved.

**Phases completed:** 26-28 (5 plans total)

**Key accomplishments:**

- Radarr config (URL, API key, enable toggle, test connection) mirroring Sonarr pattern
- Shared *arr Integration Settings UI with independent Sonarr and Radarr subsections
- Webhook POST endpoints replacing 60s polling for instant import detection
- WebhookManager with thread-safe Queue for cross-thread communication (web → controller)
- SonarrManager polling code removed entirely (webhook-only architecture)
- Webhook URL display in Settings for easy Sonarr/Radarr configuration
- 23 new unit tests (10 WebhookManager + 13 WebhookHandler), 381/381 Angular tests passing

**Stats:**

- 21 code files changed (+874 lines, -493 lines)
- 3 phases, 5 plans
- Same-day completion (2026-02-11)

**Git range:** `c5b71a9` → `6c1d514`

**What's next:** Run `/gsd:new-milestone` to start next milestone (dark mode, Lidarr/Readarr, or other features).

---

## v1.7 Sonarr Integration (Shipped: 2026-02-10)

**Delivered:** Sonarr integration for automated post-download workflow — import detection via queue polling, status badges and toast notifications in UI, and auto-delete of local files with 6-layer safety system.

**Phases completed:** 22-25 (8 plans total)

**Key accomplishments:**

- Sonarr API integration with configurable connection settings and test endpoint in Settings UI
- Queue polling with import detection via queue disappearance and state change signals
- Import status badges ("Imported") in file list with toast notifications via SSE
- Auto-delete of local files after Sonarr import with configurable delay (default 60s)
- 6-layer safety system: local-only deletion, dry-run mode, hot-toggle, missing file handling, clean shutdown, daemon threads
- 38+ new unit tests, 9 UAT tests passed, 12/12 requirements satisfied

**Stats:**

- 32 code files changed (+1,475 lines, -24 lines)
- 4 phases, 8 plans
- Same-day completion (2026-02-10)

**Git range:** `c3d369f` → `b356607`

**What's next:** Run `/gsd:new-milestone` to start next milestone (Radarr integration, dark mode, or other features).

---

## v1.6 CI Cleanup (Shipped: 2026-02-10)

**Delivered:** Consolidated duplicate Docker CI workflows into a single master.yml pipeline and cleaned up test runner warning noise.

**Phases completed:** 20-21 (2 plans total)

**Key accomplishments:**

- Consolidated Docker publishing into single CI workflow (master.yml), gated on e2e test passage
- Eliminated duplicate docker-publish.yml that bypassed test gating
- `:dev` image auto-published on master push (multi-arch: amd64 + arm64)
- Suppressed pytest cache warnings and webob/cgi deprecation warnings in test output

**Stats:**

- 11 files changed (+706 lines, -72 lines)
- 2 phases, 2 plans, 4 tasks
- 1 day (2026-02-09 to 2026-02-10)

**Git range:** `eab6146` → `c3d369f`

**What's next:** Quality project complete. All 7 milestones shipped.

---

## v1.5 Backend Testing (Shipped: 2026-02-08)

**Delivered:** Comprehensive Python backend test coverage — 231 new tests across common modules, web handlers, and controller, with pytest-cov tooling and enforced 84% coverage threshold.

**Phases completed:** 15-19 (8 plans total)

**Key accomplishments:**

- Added pytest-cov tooling with coverage config, shared conftest.py fixtures, and `make coverage-python` target
- Unit tests for all 5 common modules achieving 100% coverage (constants, context, error, localization, types)
- Unit tests for all 7 untested web handlers (AutoQueue, Config, Server, Status, HeartbeatStream, ModelStream, StatusStream)
- Comprehensive controller unit tests: 106 tests covering init, lifecycle, commands, model pipeline, and ControllerJob
- Coverage improved from 77% to 84% (+314 statements covered, +231 tests)
- Enforced `fail_under = 84` threshold preventing future regression

**Stats:**

- 19 files changed (+2,315 lines)
- 14 new test files, 1 conftest.py
- 5 phases, 8 plans
- Same-day completion (2026-02-08)

**Git range:** `56463ad` → `03869bc`

**What's next:** Quality project complete. All UI polish and backend testing milestones shipped.

---

## v1.4 Sass @use Migration (Shipped: 2026-02-08)

**Delivered:** Migrated all application SCSS from deprecated @import to modern @use/@forward module system, proactively preparing for Dart Sass 3.0.

**Phases completed:** 12-14 (3 plans total)

**Key accomplishments:**

- Transformed `_common.scss` to @forward aggregation module with namespaced variable access
- Transformed `_bootstrap-overrides.scss` to @use with `bv.` and `fn.` namespaces
- Updated `styles.scss` to @use for application modules (hybrid architecture with Bootstrap @import)
- Eliminated all application SCSS deprecation warnings (zero from src/app/ paths)
- All 381 unit tests pass, zero visual regressions
- Only 3 SCSS files modified across entire migration — minimal blast radius

**Stats:**

- 3 SCSS files modified
- 44 insertions, 23 deletions
- 3 phases, 3 plans
- 2 days (2026-02-07 to 2026-02-08)

**Git range:** `d17c957` → `1001fdf`

**What's next:** UI Polish project complete. All Sass tech debt resolved.

---

## v1.3 Polish & Clarity (Shipped: 2026-02-04)

**Delivered:** Fixed 62 TypeScript lint errors and added file counts to status dropdown for at-a-glance clarity.

**Phases completed:** 10-11 (5 plans total)

**Key accomplishments:**

- Eliminated all TypeScript lint errors (`npm run lint` exits clean)
- All functions have explicit return types (~152 annotated)
- Zero `any` types in application code (~49 replaced)
- Non-null assertions replaced with optional chaining (~47 fixed)
- Status dropdown shows file counts per status (e.g., "Downloaded (5)")
- On-demand count refresh when dropdown opens

**Stats:**

- 77 files modified
- 3,946 insertions, 320 deletions
- 2 phases, 5 plans
- Same-day completion (2026-02-04)

**Git range:** `1cc4a97` → `921a63b`

**What's next:** Project complete. Future work could include dark mode toggle or Sass @use migration.

---

## v1.2 UI Cleanup (Shipped: 2026-02-04)

**Delivered:** Removed obsolete Details and Pin buttons from file options bar, simplifying UI to only functional controls.

**Phases completed:** 9 (1 plan total)

**Key accomplishments:**

- Removed Details button and all associated showDetails state
- Removed Pin button and all associated pinFilter state
- Simplified file options bar to only functional controls (search, status filter, sort)
- File options bar now always static positioning

**Stats:**

- 18 files modified
- 329 insertions, 344 deletions (net -15 LOC cleanup)
- 1 phase, 1 plan, 2 tasks
- Same-day completion

**Git range:** `a07b2e7` → `9426e66`

**What's next:** UI refinement complete. Run `/gsd:new-milestone` to start next milestone.

---

## v1.1 Dropdown & Form Migration (Shipped: 2026-02-04)

**Delivered:** Complete UI styling unification with Bootstrap-native dropdowns, consistent form inputs with teal focus states, and dark theme across all components.

**Phases completed:** 6-8 (4 plans total)

**Key accomplishments:**

- Migrated file dropdowns to Bootstrap's native component with dark theme styling
- Unified form inputs with teal focus rings across Settings, AutoQueue, and Files pages
- Implemented close-on-scroll behavior preventing orphaned dropdown menus
- Removed 150+ lines of custom SCSS placeholders in favor of CSS variable theming
- Verified 387 unit tests pass with visual QA approval at desktop and tablet widths
- Zero unused SCSS code confirmed via comprehensive audit

**Stats:**

- 24 files created/modified
- ~2,900 lines changed (mostly .planning documentation)
- 3 phases, 4 plans, 11 tasks
- 1 day (same-day completion)

**Git range:** `8d57357` → `03b3315`

**What's next:** Project styling unification complete. Future work could include dark mode toggle or full @use migration.

---

## v1.0 Unify UI Styling (Shipped: 2026-02-03)

**Delivered:** Unified Bootstrap 5 SCSS architecture across SeedSync's Angular frontend with consistent colors, selection highlighting, and button styling.

**Phases completed:** 1-5 (8 plans total)

**Key accomplishments:**

- Established Bootstrap SCSS infrastructure with two-layer customization system
- Consolidated all colors to Bootstrap variables with zero hardcoded hex values
- Unified selection highlighting using teal (secondary) color palette with visual hierarchy
- Standardized all buttons to Bootstrap semantic variants with 40px sizing
- Removed legacy custom %button SCSS placeholder entirely

**Stats:**

- 18 files created/modified
- 282 lines added, 234 deleted
- 5 phases, 8 plans, ~20 tasks
- 1 day from start to ship

**Git range:** `feat(01-01)` → `refactor(05-02)`

**What's next:** v1.1 Dropdown & Form Migration

---

## v3.0 Terminal UI Overhaul (Shipped: 2026-02-17)

**Delivered:** Complete Terminal/Hacker aesthetic redesign — dark-only UI with Fira Code + IBM Plex Sans fonts, matrix-green accents, ASCII progress bars, collapsible icon-rail sidebar, CRT scan-line overlay, and theme system cleanup.

**Phases completed:** 33-38 (12 plans total)

**Key accomplishments:**

- Replaced Bootstrap color system with Terminal/Hacker palette (Fira Code + IBM Plex Sans, #0d1117 dark base, #00ff41/#3fb950 green accents, CRT scan-line overlay)
- Restructured sidebar to 56px collapsible icon-rail expanding to 200px on hover, with `>` prompt indicator on active route and version display
- Redesigned file dashboard with ASCII progress bars (`[████░░░░] 67%`), colored status borders, green glow on downloading rows, and ghost-style action buttons
- Applied terminal aesthetic to all secondary pages: Settings terminal headers, AutoQueue monospace patterns, colored log levels, ASCII art About page
- Removed light/auto theme system entirely — deleted ThemeService, theme types, and all dead code for dark-only simplification
- Fixed CSS variable typo and completed full requirements traceability (21/21 satisfied)

**Stats:**

- 32 files changed (+530 lines, -1,235 lines, net -705 LOC)
- 6 phases, 12 plans, 21 requirements satisfied
- 4 days (2026-02-14 to 2026-02-17)

**Git range:** `v2.0.1` → `HEAD`

**What's next:** Run `/gsd:new-milestone` to start next milestone (Lidarr/Readarr support, or other features).

---

## v3.1 Harden & Fix (Shipped: 2026-02-24)

**Delivered:** Comprehensive security hardening, race condition fixes, crash prevention, and code quality improvements across Python backend and Angular frontend — addressing all 68 findings from deep code review.

**Phases completed:** 39-46 (8 phases, 25 plans)

**Key accomplishments:**

- Closed critical RCE attack chain — removed committed RSA key, hardened SSH host verification (TOFU), replaced pickle with JSON deserialization
- Sealed credential exposure — redacted secrets from config API, scrubbed passwords from SSE log stream, added SSRF protection, HMAC webhook auth, and security headers
- Fixed 4 race conditions — model lock on auto-delete/webhook imports, atomic queue operations in ExtractDispatch with copy-under-lock pattern
- Eliminated 6 crash bugs — exception propagation, None guards, SSE unknown event handling, bounded 30s action timeouts
- Hardened Angular frontend — XSS sanitization, Observable pipe refactors, subscription leak fixes (takeUntil/destroy$), focus trap accessibility
- Python 3.12+ compatibility — replaced distutils, shell injection prevention via pexpect argv, POST/DELETE for mutation endpoints
- Code review follow-up (Phase 46) — 12 additional fixes: webhook_secret redaction, getMessage() log scrubbing, atomic extract(), focus trap full Tab interception, timer cleanup, RestService helper extraction

**Stats:**

- 131 files changed (+11,242 lines, -461 lines)
- 90 commits
- 44 requirements satisfied (10 security, 4 thread safety, 6 crash, 7 frontend, 13 code quality, 4 docs/a11y)
- 2 days (2026-02-23 to 2026-02-24)

**Git range:** `ab15f80` → `ab1759d`

---

## v3.2 Security Hardening II — Partial (Shipped: 2026-02-26, phases 47-49 only)

**Delivered:** Config file permissions, restart POST migration, SSH log redaction, extended config redaction, webhook payload cap, startup security warnings, path traversal guards. Remaining security work (API token auth, DNS rebinding, CSP hardening) completed in M002 after Angular 21 migration.

**Phases completed:** 47-49 (6 plans total)

**Key accomplishments:**

- Config files written with 0600 permissions, existing configs tightened on startup
- Restart endpoint migrated to POST (CSRF prevention)
- SSH topology redacted from log streams (sftp:// and user@host patterns)
- Extended config API redaction (remote_address, remote_username, remote_path)
- Webhook payload size cap (1MB, 413 before body read)
- Startup warnings for missing webhook_secret, missing API token, 0.0.0.0 binding
- Path traversal guards (realpath-based) on delete_local, delete_remote, extract endpoints

**Stats:**

- 3 phases, 6 plans
- 2 days (2026-02-25 to 2026-02-26)

**Note:** Phases 50-51 (API token auth, CSP hardening) completed as M002 after Angular 21 migration.

---

## M001: Angular 21 Migration (Shipped: 2026-03-21, released as v3.2.0)

**Delivered:** Angular 19→20→21 stepwise migration with all security alerts resolved and CI fully green.

**Key accomplishments:**

- Angular 19→20→21 stepwise migration, 394 unit tests passing
- Resolved 3 high/critical Dependabot security alerts (serialize-javascript RCE, 2x webpack SSRF)
- TypeScript upgrade, zone.js and jQuery 3→4 migration
- Removed all dependabot ignore rules
- Full CI green (Python + Angular + Deb + Docker + E2E)

**Slices:** 3

**Tag:** v3.2.0

---

## M002: Finish v3.2 Security (Shipped: 2026-03-22)

**Delivered:** Completed remaining v3.2 security work — API token authentication, DNS rebinding prevention, CSP hardening, and CONF-04 fix.

**Key accomplishments:**

- Bearer token auth on /server/* endpoints with auto-generation via secrets.token_urlsafe(32)
- Angular HTTP interceptor for transparent token injection via meta tag
- Host header validation (DNS rebinding prevention) with configurable allowlist
- Conditional config redaction — authenticated requests get unredacted values (CONF-04)
- Angular autoCsp for hash-based CSP (no unsafe-inline)

**Slices:** 3

---

## M003: UI Redesign — Earthy Palette (Shipped: 2026-03-25)

**Delivered:** Complete visual redesign from terminal/hacker dark theme to clean modern dark UI matching Triggarr's design language.

**Key accomplishments:**

- Earthy palette: Jet Black (#13262f), Deep Walnut (#583e23), Olive Bark (#73683b), Khaki Beige (#b0a084), Lavender (#e9e6ff)
- Sidebar replaced with Triggarr-style top nav bar with text links
- All terminal effects removed (CRT, ASCII art, blinking cursors, prompts, glows)
- System font stack (no Google Fonts), text-only buttons, status dots, percentage progress
- Settings redesigned from accordion to clean card sections
- Clean About/Logs/AutoQueue pages, unused SVG assets + logo.png removed

**Slices:** 6

---

## M004: Polish & Dependency Updates (Shipped: 2026-03-24)

**Delivered:** Deferred polish items and major dependency updates.

**Key accomplishments:**

- API token display in Settings (read-only, copyable)
- Toast notifications restyled to earthy palette
- Immutable.js 4→5, TypeScript 5→6, 21 npm dependency updates from PR #161
- Full CI green

**Slices:** 4

---

## M005: Dashboard Polish & v3.3.0 Release (Shipped: 2026-03-24)

**Delivered:** Dashboard column alignment and typography fixes.

**Key accomplishments:**

- Dashboard column headers aligned with file row data at all responsive breakpoints
- Consistent font sizing hierarchy

**Slices:** 2

---

## M006: Triggarr-Style Layout + Deep Moss Palette (Shipped: 2026-03-25)

**Delivered:** Readability fix with proper contrast ratios and flat-row file list redesign.

**Key accomplishments:**

- Deep Moss + Amber palette with WCAG AA contrast (4.5:1+ for all text)
- File list redesigned to flat single-line rows matching Triggarr
- Code review findings addressed, `:dev` image published, UAT passed

**Slices:** 3

---

## M007: Settings Redesign & Multi-Select Polish (Shipped: 2026-03-26)

**Delivered:** Triggarr-style Settings page and consolidated multi-select bar.

**Key accomplishments:**

- Settings: card sections with labels-above-inputs, no accordion JS
- All 9 settings sections visible without collapse
- Dashboard multi-select bar consolidated to single unified component
- 401+ unit tests passing

**Slices:** 2

---

## M008: AutoQueue Migration, Token UI & Toast Polish (Shipped: 2026-03-27)

**Delivered:** AutoQueue merged into Settings, API token reveal/hide, Triggarr-style toasts.

**Key accomplishments:**

- AutoQueue page deleted — pattern management now in Settings AutoQueue card
- API token visible in Settings Security card with reveal/hide/copy (R017 complete)
- Triggarr-style toasts with type icons and slide-in animation (R040 complete)
- Stale gsd/* branches cleaned up, CI green

**Slices:** 2

---

## M009: Full Codebase Deep Review Fixes (Shipped: 2026-03-28)

**Delivered:** All 55 issues from TuringMind deep review fixed — security, concurrency, frontend, code quality.

**Key accomplishments:**

- Security: LFTP escape() rejects newline/CR/null, shlex.quote for remote_scanner, credential log redaction
- Concurrency: model reads under lock, dedicated __pending_auto_deletes lock, shallow copy parent ref fixes
- Frontend: SSE subscription lifecycle, view-file index updates, pexpect TIMEOUT handling, inner Observable teardown
- Code quality: bare except narrowing, BFS deque, log levels, Optional types, version file sync
- 1,134 Python + 401 Angular tests passing, CI green, UAT passed

**Slices:** 4

---

## M010: Screenshots, Docs & v4.0.0 Release (Shipped: 2026-03-28)

**Delivered:** Fresh screenshots, documentation updates, and v4.0.0 major release.

**Key accomplishments:**

- Screenshots captured via headless Playwright from live instance
- README.md and docs site updated with new screenshots
- Version bumped to 4.0.0 (major: UI redesign + security hardening scope)
- GitHub release v4.0.0 with categorized changelog
- Docker `:latest` + Deb packages published for amd64/arm64

**Tag:** v4.0.0 (subsequently v4.0.1, v4.0.2 for CI/dependency fixes)

---

## v4.0.1 Hotfix (Shipped: ~2026-03-29)

**Delivered:** Override lodash to ^4.18.0 for security alerts #39/#40.

**Tag:** v4.0.1

---

## v4.0.2 Hotfix (Shipped: ~2026-04-01)

**Delivered:** CI lint job (ruff + eslint), `:main` tag restricted to stable releases, vite security override.

**Tag:** v4.0.2

---
