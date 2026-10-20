# SeedSync

## What This Is

SeedSyncarr is a file syncing tool that syncs files from a remote Linux server (like a seedbox) to a local machine using LFTP. Features a clean modern dark web UI (Deep Moss + Amber palette, system fonts, top nav bar, flat file rows), Sonarr/Radarr integration for automated post-download workflows, and real-time transfer status via SSE. Security-hardened with Bearer token API auth, HMAC webhook auth, CSP (hash-based via autoCsp), DNS rebinding prevention, credential redaction, SSRF protection, path traversal guards, rate-limited HTTP endpoints, and thread-safe concurrent operations.

## Core Value

Reliable file sync from seedbox to local with automated media library integration.

## Previous State

**v1.3.0 (2026-06-02)** — Test & Quality, Security, Deps & Backend Architecture Refactor. A 4-slice program (phases 97-109) shipped under one tag: (1) closed 8 test-coverage gaps and ratcheted CI coverage floors; (2) fixed 7 known bugs + security items — opt-in webhook fail-closed + rate-limiting, CR/LF log-injection sanitization, config-response normalization, auto-delete Timer shutdown guard, Angular ConfirmModal innerHTML→Renderer2 XSS fix, SSE same-tick subscription leak fix; (3) removed 3 end-of-life Angular deps (jQuery 4, Font Awesome 4.7, css-element-queries), migrated all icons to Phosphor, excluded mock fixtures from the production bundle; (4) behavior-preserving backend refactors — MP-logger spawn-safety, declarative Config secret discovery, web-handler dispatch dedup, and decomposition of the 1150-line Controller god-class into three cohesive collaborators (command_processor, auto_delete_manager, model_pipeline). Full suite green throughout; live pre-release walkthrough passed all flows.

**v1.2.0 (2026-04-28)** — Test & Quality Hardening. Fixed 68 test/quality/security items across 10 phases: 19 Python test defects (false coverage, resource leaks, race conditions), 7 Angular test issues (subscription leaks, fakeAsync, optional chaining), 9 E2E test + 5 infrastructure fixes, CI & Docker security hardening (least-privilege, SHA-pinned actions, SSH key-only auth, non-root sshd), 6 test coverage gaps filled (SSE, Logs/Settings E2E, webhook, DeleteRemoteProcess, ActiveScanner), rate limiting on all mutable endpoints, 628 Semgrep false positives eliminated.

**v1.1.2 (2026-04-24)** — Test Suite Audit. Audited all three test layers for stale/redundant tests inherited from original SeedSync. Zero stale tests found across all layers (72 Python files, 40 Angular specs, 7 E2E specs). HttpClientTestingModule migrated to provideHttpClient() in 6 spec files. Coverage baselines documented: Python 85.05%, Angular Statements 83.34%/Branches 69.01%/Functions 79.73%/Lines 84.21%. CI fully green (1262 Python, 599 Angular, 37 E2E on amd64+arm64).

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

**v1.1.2 (Shipped 2026-04-24):**

- ✓ Python test audit — zero stale tests across 72 files, coverage baseline 85.05% recorded — v1.1.2
- ✓ Angular test audit — zero stale tests across 40 spec files, HttpClientTestingModule migrated in 6 files — v1.1.2
- ✓ E2E test audit — zero stale specs across 7 Playwright files (37 tests), all selectors verified live — v1.1.2
- ✓ Full CI green after audit — 1262 Python, 599 Angular, 37 E2E on amd64+arm64 — v1.1.2
- ✓ Coverage baselines documented before and after (Python 85.05%, Angular 83.34%/69.01%/79.73%/84.21%) — v1.1.2

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

**v1.2.0 (Shipped 2026-04-28):**

- ✓ Fixed 19 Python test defects (false coverage, resource leaks, race conditions, mock confusion) — v1.2.0
- ✓ Consolidated Python test architecture (conftest→helpers, deduplicated base classes, integration test reclassification) — v1.2.0
- ✓ Fixed 7 Angular test issues (subscription leaks, fakeAsync cleanup, double-cast, optional chaining guards) — v1.2.0
- ✓ Fixed 9 E2E test + 5 infrastructure issues (Playwright APIs, CSP enforcement, arm64 Unicode, Docker health, restart race) — v1.2.0
- ✓ Hardened CI & Docker security (least-privilege permissions, SHA-pinned actions, SSH key-only auth, non-root sshd, ephemeral keys) — v1.2.0
- ✓ Filled 6 test coverage gaps (SSE streaming, Logs + Settings E2E, webhook integration, DeleteRemoteProcess, ActiveScanner) — v1.2.0
- ✓ Rate limiting on all mutable HTTP endpoints via reusable decorator — v1.2.0
- ✓ Tightened Semgrep rules, eliminated 628 false positives — v1.2.0

**v1.3.0 (Shipped 2026-05-31):**

- ✓ Full-path coverage for 3 Medium Python gaps: MultiprocessingLogger listener shutdown, SSRF `_validate_url` IPv4/IPv6 reserved ranges (+ pre-approved IPv6-mapped fix), LFTP JobStatusParser error-recovery counter — v1.3.0
- ✓ Full end-to-end XSS coverage for `confirm-modal.service.ts` escapeHtml (all metacharacters + 6 inputs + skipCount-exemption audit) — v1.3.0
- ✓ Targeted regression tests for 2 Low Python gaps: auto-delete enabled/dry-run toggle flipped during a live `threading.Timer` window; BoundedOrderedSet eviction-after-touch ordering — v1.3.0
- ✓ Targeted regression tests for 2 Low Angular gaps: SSE heartbeat-vs-timeout reconnection race (+ positive control); auth interceptor token-rotation via `_resetAuthInterceptorCache` seam — v1.3.0
- ✓ CI coverage ratchet: Python `fail_under` 84→88 (container-inclusive 89.27%), net-new Karma `check.global` (83/68/79/83) + Angular Dockerfile `--code-coverage` so the gate bites; before/after recorded in ROADMAP + RETROSPECTIVE — v1.3.0
- ✓ Ambiguous webhook import matches rejected (no credit/badge/auto-delete) and delete-time duplicate-video-basename guard that legacy coverage records cannot bypass; unique matches unchanged (IMPORT-01/02) — Validated in Phase 116: Import Safety (v1.7.4)
- ✓ LFTP parser never swallows another job's header; unparseable or timed-out status reported as unavailable (never "no jobs") with the error boundary unchanged; transfers submitted but not yet observed stay Queued and protected (incl. same-cycle command guard, Stop reconcile); remote/local stability measured only on successful-scan clocks with the UI "last scan" unchanged (XFER-01..05) — Validated in Phase 117: Transfer-State Safety (v1.7.4)
- ✓ Settings, controller persist and auto-queue persist written atomically (serialize first, same-dir 0600 temp, fsync, `os.replace` commit point, best-effort logged directory fsync) so a failed save leaves the previous file byte-for-byte intact (PERSIST-01/02); 1.7.4 release gate met — 42 regressions fail-before/pass-after, full suite + whole-tree ruff, digest-pinned smoke test with a real transfer, NAS deployed at `:1.7.4@sha256:682d…` with clean post-deploy scan (REL-01; PyPI publish deferred to 1.7.5 by owner) — Validated in Phase 118: Durable State (v1.7.4)
- ✓ LFTP status stays unavailable after a timed-out command until the command stream is verifiably resynchronized (XFER-06); pending auto-delete timer defers on a submitted-but-unobserved transfer (DEL-01); incomplete copies never exposed at an importable path, transfers gated on strong-identity arr-queue completion evidence with visible Waiting holds and a one-shot confirmed manual release (IMP-01/02); early per-episode import credit persisted while siblings transfer, whole-folder delete still gated on full coverage (IMP-03); PyPI packaging repaired and 1.7.5 published to Docker/GitHub/PyPI with digest smoke 8/8 (REL-02, REL-03 — NAS production deploy held by owner and carried to Phase 119.1) — Validated in Phase 119: Safety Follow-ups and 1.7.5 Release (v1.7.5)
- ✓ Container startup no longer prints settings.cfg (one 'Config ready at' line); debug dump redacts every secret_fields() option; an unreadable settings.cfg is fatal and value-free (no reset to defaults, no web server); '%' in a value saves and reloads unchanged with value-free serialization errors — RED-first sentinel tests in CI (SEC-01); 1.7.6 published to Docker/GitHub/PyPI with a security notice and the full 1.7.5 changes, exact-digest NAS smoke incl. count-only no-secrets check with 1.7.5 positive control, and deployed to NAS production at `:1.7.6@sha256:da6196e0…` with verified backups, scan/arr checks and wud restored; owner given the credential-rotation checklist (REL-03 NAS portion, REL-04) — Validated in Phase 119.1: Startup log secrets fix and 1.7.6 release (v1.7.5)

## Current State

v1.7.5 Safety Release shipped 2026-10-15 (Phases 119, 119.1; tagged `v1.7.5` and `v1.7.6`). `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0…` runs on NAS production; Phase 119 browser UAT passed 2026-10-18 on the 1.7.6 sandbox. v1.7.7 Sonarr 5 Compatibility: Phase 120 complete 2026-10-20 — SeedSyncarr 1.7.6 verified live against Sonarr 5.0.0.2701 (Test Connection, queue hold/release, import webhook) and pinned by live sanitized CI fixtures; owner approved "verified; no release needed" (no 1.7.7 tag). Milestone close pending; Reliability begins at Phase 121.

## Current Milestone: v1.7.7 Sonarr 5 Compatibility

**Goal:** Prove SeedSyncarr works unchanged with Sonarr 5 on the NAS sandbox, and lock that in with regression tests built from real Sonarr 5 responses.

**Target features:**
- Live sandbox check: `seedsyncarr-test` (1.7.6) against the existing `sonarr-v5` container (Sonarr 5.0.0.2701, NAS port 8990). Production Sonarr and SeedSyncarr untouched.
- Test Connection, download-queue completion evidence, and the import webhook each verified against Sonarr 5, including the negative cases (Test webhook marks nothing; missing entry, API error or unrelated completed download never releases a hold).
- Sanitized captured Sonarr 5 fixtures (version and scenario recorded) exercised in CI without the NAS.
- Conditional release: only if a compatibility fix is needed, ship and deploy 1.7.7 by release tag; otherwise close as "verified; no release needed".

**Key context:** Source review 2026-10-20 of Sonarr `develop` @7ccafd3 (commit of 2026-10-18) shows the three v3 endpoints/payloads SeedSyncarr uses — `GET /api/v3/system/status`, `GET /api/v3/queue/details` (`outputPath`, `downloadId`, `status`, `sizeleft`), and the `Download` webhook (`episodeFile.sourcePath`) — still exist unchanged. Sonarr 5 lists v3 as deprecated, so moving to API v5 is backlog 999.5, not this milestone. Radarr unchanged. Owner decisions 2026-10-20: fix-and-release if broken, sandbox only, label v1.7.7.

## Next Milestone Goals

Reliability (from Phase 121): complete the five ordered, bounded outcomes in ROADMAP.md. Preserve delivered Phase 119 import/deletion safeguards and existing per-component controller cleanup. Performance and Usability remains conditional on demonstrated benefit.


## Previous Milestone: v1.7.5 Safety Release (Shipped 2026-10-15, tagged v1.7.5 + v1.7.6)

**Goal:** Close the carried-forward safety gaps from v1.7.4 and the two 2026-10 Done-group incidents (an incomplete file imported into the library; early per-episode import notices discarded), and ship 1.7.5 to Docker/GitHub/PyPI with the tested image verified on the NAS.

**Target features:**
- LFTP command-boundary resync after a timeout — a delayed prompt or stale output cannot become a trusted empty job list (promotes 999.2).
- Explicit submitted-but-unobserved guard in the auto-delete timer, with safe defer/re-arm (promotes 999.3).
- PyPI packaging repair and verified distribution (Dependabot #93 only as relevant).
- Incomplete-import prevention (Obsession, 2026-10-13): an unverified copy stays unavailable for Sonarr/Radarr import until completion checks pass; size/mtime are supporting evidence only; arr-queue release identification must be reliable and absence from the queue is not completion; arr unavailable → visible hold/retry, never an unsafe copy after a timeout. Separate plan and tests.
- Early per-episode import credit (Days of Hope, 2026-10-09): notices for demonstrably complete episodes are credited and persisted while siblings transfer; whole-folder deletion stays gated on transfer completion and full video coverage; restart recovery tested; ambiguous-filename protections retained. Separate plan and tests.

**Key context:** Diagnosis in `.planning/debug/done-group-no-auto-delete.md`. Broad research skipped; planning must verify the specific Sonarr/Radarr queue/API semantics needed to establish completion — the incident diagnosis establishes the problem, not every detail of the solution. Release gate: targeted regressions fail-before/pass-after, full suite + whole-tree ruff + release CI, release-image smoke (startup, real transfer, settings persistence, restart), Docker/GitHub/PyPI publication, and NAS verification of the tested image including a successful scan after any startup scanner error.

## Previous Milestone: v1.7.4 Safety Patch (Shipped 2026-10-09, tagged v1.7.4)

**Goal:** Protect users from incorrect deletion and transfer-state decisions. Ship promptly as patch release 1.7.4.

**Target features:**
- Deletion safety: a webhook import whose file name matches more than one distinct model path (across releases, case-only differences, or repeated basenames within one release) is rejected — no import record, no coverage credit, no auto-delete.
- Transfer-state safety: the LFTP status parser never consumes the next job's header; an unparseable status is reported as *unavailable* (last-known transfer state preserved, existing error boundary unchanged) rather than "no jobs"; remote and local stability clocks advance only on successful scans.
- Durable state: `Persist.to_file` (settings.cfg, controller persist, auto-queue persist) writes atomically — temp file, fsync, `os.replace` commit point, directory fsync — so a failed save never corrupts the previous valid file.

**Key context:** Root causes confirmed in code during brainstorming (design spec `docs/superpowers/specs/2026-10-08-safety-patch-design.md`). `name_to_root` in `Controller.__check_webhook_imports` is last-writer-wins; `PgetJobParser.parse_header` pops the line after `sftp` unconditionally; `Lftp.status()` returns `[]` on tolerated parse errors; `latest_remote_scan_time`/`latest_local_scan_time` advance on failed scans; `Persist.to_file` truncates in place. Release gate: each regression fails before and passes after its fix, full suite + ruff, release-image smoke test, NAS deploy of `:1.7.4` with scanner recovery confirmed by a subsequent successful scan.

## Previous Milestone: v1.4.1 Scanner Auto-Recovery (Shipped 2026-06-22, tagged v1.5.0)

**Goal:** The seedbox scanner survives transient DNS/network blips and recovers from controller death on its own, instead of silently freezing the file list for days until a manual container restart.

**Target features:**
- Transient name-resolution failures (`Could not resolve hostname` / `Name or service not known` / a momentary `Bad hostname`) are reclassified as recoverable, so the scanner retries with backoff instead of dying.
- Bounded-retry guard: a genuinely wrong/persistently-unresolvable hostname or bad credentials still stops and surfaces to the user after a capped number of retries — no infinite-retry masking of real config errors.
- Controller auto-restart safety net: if the controller dies from a permanent-class error, it recovers via the existing `ServiceRestart` path instead of staying down (`server.up=False`) indefinitely.

**Key context:** Second "scanner dies, no recovery" incident (root-caused 2026-06-19; see resolved debug session `seedbox-files-not-showing`; prior variant `hold-the-dream-not-syncing`). On 2026-06-19 a transient DNS failure resolving `moon.usbx.me` raised `SshcpError('Bad hostname')`, classified as permanent/non-recoverable; it propagated to `seedsyncarr.py run()` (caught as `AppError` with `args.exit=False`), marking the controller down without restarting it. Web server stayed up so the UI looked fine, but the file list was frozen ~2 days. The fix wires together infrastructure that **already exists** in `src/python/` (`sshcp.py` PERMANENT/TRANSIENT patterns + `_is_transient_ssh_error`; `remote_scanner.py` recoverable classification; `scanner_process.py` ScannerError; `scan_manager.py` health-check; `common/error.py` `ServiceRestart`) — no new mechanisms invented.

## Previous Milestone: v1.4.0 Launch-Hardening for Public Release (Shipped 2026-06-03)

**Goal:** Make SeedSyncarr's public-facing surface — both the code a skeptical engineer reads and the presentation a visitor sees — bulletproof enough to withstand a technical Reddit (r/selfhosted) launch.

**Target features:**
- Hostile-reader code discovery pass (bounded; only high-visibility findings fold in)
- `/server/config/set` GET→POST hard cutover (credentials no longer in URLs/logs)
- Unsafe-default startup warnings (non-loopback bind without `api_token`; webhooks without secret)
- Delete-path hardening (replace `shutil.rmtree(ignore_errors=True)` with logged error handling)
- AppProcess spawn-context fix (the currently-failing `test_app_process.py` goes green)
- `.gitignore` fix (`.orchestrator.json`, `.playwright-mcp/`) + legacy `~/.seedsync` fallback warning
- Presentation rebuild: README, SECURITY.md, community-health files, release notes — driven by a cynical-reader teardown + a codex adversarial pass; Playwright screenshots captured at walkthrough; repo-metadata text drafted for manual application

**Key context:** Code substance is already strong (post-v1.3.0 audit found zero active functional bugs; ~89% Python coverage; hardened security surface). The launch risk is (a) presentation underselling real quality and (b) a few specific items a hostile reader would find. The config-set GET→POST is a breaking HTTP-contract change → v1.4.0 (minor; no external consumers + lockstep frontend means 2.0.0 would over-signal). Branch-isolated workflow (`launch-hardening`); NAS walkthrough on the branch; merge + tag v1.4.0 only after CI green + maintainer sign-off. Full decisions/scope in the design spec (was `.planning/MILESTONE-CONTEXT.md`).

## Previous Milestone: v1.3.0 Test Coverage Gaps (Shipped 2026-05-31)

**Goal:** Close the 8 test coverage gaps catalogued in CONCERNS.md — 4 Medium-priority gaps get full path coverage, 4 Low-priority gaps get a targeted regression test. Trivial bugs found while testing (<10 lines, no public-API or observable-behavior change) are fixed in the same plan; larger findings deferred to the next v1.3.0 slice (Known Bugs + Security). Milestone ends with ratcheted CI coverage thresholds.

**Target features:**
- Medium Python coverage: MultiprocessingLogger shutdown, SSRF IPv6/reserved-range, LFTP JobStatusParser ValueError recovery
- Medium Angular coverage: confirm-modal escapeHtml end-to-end XSS
- Low Python regression: auto-delete dry-run/enabled toggle under live Timer, BoundedOrderedSet eviction-after-touch
- Low Angular regression: SSE timeout reconnection race, auth.interceptor token-missing/rotation
- Cross-cutting: coverage baseline capture, CI threshold ratchet (pytest --cov-fail-under + Karma global), before/after numbers in ROADMAP.md

### Active

- [x] Sonarr 5 compatibility verified live on the sandbox and pinned by CI fixtures (SON5-01..05) — v1.7.7 (Validated in Phase 120: Sonarr 5 Compatibility; verified, no release needed)


<!-- v1.7.4 (shipped 2026-10-09) — Safety Patch. Three Python phases: deletion safety → transfer-state safety → durable state. -->

v1.7.4 closes five defects that can cause incorrect deletion or transfer-state decisions: ambiguous webhook import matches, the LFTP parser consuming the next job's header, status-unavailable collapsing to "no jobs", stability established from failed scans, and non-atomic state/config writes. All 10 requirements validated (see Validated above; archive `.planning/milestones/v1.7.4-REQUIREMENTS.md`).

<!-- v1.4.1 (shipped 2026-06-22) — Scanner Auto-Recovery. -->

v1.4.1 makes the seedbox scanner self-heal instead of silently freezing the file list for days. Three behaviors: (1) reclassify transient name-resolution failures (`Could not resolve hostname` / `Name or service not known` / a momentary `Bad hostname`) as recoverable so the scanner retries with backoff rather than dying; (2) a bounded-retry guard so a genuinely wrong/persistently-unresolvable hostname or bad credentials still stops and surfaces to the user after a capped number of retries — never an infinite-retry loop that masks real config errors; (3) a controller auto-restart safety net so a permanent-class controller death recovers via the existing `ServiceRestart` path instead of staying down (`server.up=False`) forever. Reuses infrastructure already present in `src/python/` — no new mechanisms. See `.planning/REQUIREMENTS.md`.

<!-- v1.4.0 (shipped 2026-06-03) — Launch-Hardening for Public Release. Code + presentation tracks + the config-set GET→POST cutover. -->
v1.4.0 hardened SeedSyncarr's public face for a Reddit launch: bounded hostile-reader discovery pass, the `/server/config/set` GET→POST hard cutover (credentials no longer in URLs/logs), unsafe-default startup warnings, delete-path hardening, the AppProcess spawn-context fix, `.gitignore`/`~/.seedsync`-fallback items, and a README/SECURITY.md/community-health/release-notes presentation rebuild. Tagged `v1.4.0`.

### Out of Scope

- Lidarr/Readarr support — defer to future milestone
- Bootstrap @import → @use migration — blocked until Bootstrap 6
- Angular→htmx/Tailwind rewrite — visual kinship via design patterns, not framework
- OAuth / multi-user auth — single-user self-hosted tool
- HTTPS termination — handled by reverse proxy
- New favicon/logo design — keep existing favicon.png
- webob/cgi upstream fix — blocked on upstream webob 2.0 release (PR #466 open)
- Shutdown-readiness Event (replace fixed `time.sleep` in `seedsyncarr.py` shutdown) — real robustness gain but invisible to a launch reader; deferred (v1.4.0 scope decision)
- `StreamQueue.put` non-atomic drop-oldest — latent, well-mitigated, documented edge-case; deferred (v1.4.0 scope decision)
- Test-hardening backlog (`.planning/backlog/TEST-HARDENING-REVIEW.md`, A-01..A-06) — test-infra niceties invisible to a launch reader; deferred (v1.4.0 scope decision)
- Path-mapping redesign for webhook imports — v1.7.4 conservatively rejects ambiguous matches instead (Safety Patch scope decision)
- Persistence migration / backup system / load-side recovery changes — v1.7.4 only makes writes atomic (Safety Patch scope decision)
- NAS local-build QEMU issue — deploy-environment limitation, not a code defect; CI multi-arch publish works

## Context

**Codebase state:**
- ~35.5k Python LOC, ~20k TypeScript LOC
- 1,278 Python tests, 89.27% container-inclusive coverage (fail_under=88 enforced); 614 Angular tests (Karma check.global 83/68/79/83 enforced)
- 599 Angular unit tests passing
- 45+ Playwright E2E specs (amd64+arm64), CI-gated
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
- Rate limiting on all mutable HTTP endpoints via sliding-window decorator (config/set 60/60s, test-connection 5/60s, status 60/60s)
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
| Reject ambiguous webhook import matches instead of path-mapping (v1.7.4) | Conservative: a basename matching 2+ distinct model paths can never arm auto-delete; full path mapping is a larger change | ✓ Good |
| LFTP status unavailable = `None`, never `[]` (v1.7.4) | "No jobs" and "couldn't tell" must be distinct so protection survives parse failures; error boundary kept exactly | ✓ Good |
| Atomic `Persist.to_file` via same-dir temp + `os.replace` (v1.7.4) | A failed save must never destroy the last valid settings/persist; relies on `/config` being a directory mount (documented setup) | ✓ Good |
| Ship 1.7.4 via Docker/GitHub despite PyPI publish failure (v1.7.4) | Safety fixes reach NAS users promptly; packaging fix deferred to 1.7.5 | ✓ Good (PyPI restored in 1.7.5) |
| Hold the 1.7.5 NAS deploy; ship 1.7.6 with the startup-log secrets fix instead (v1.7.5) | The 1.7.5 smoke test surfaced a pre-existing secrets-in-startup-log leak; deploying a build that prints credentials was not acceptable | ✓ Good |
| Completion needs arr-queue evidence; holds are visible with a one-shot confirmed manual release (v1.7.5) | Stable size and mtime let an ~800 MB-short file import (Obsession incident); an unavailable arr must hold, never release | ✓ Good (UI visual check pending) |
| Persist per-episode import credit while siblings transfer (v1.7.5) | Early Sonarr notices were discarded, so folder coverage could never pass (Days of Hope incident); whole-folder delete stays gated | ✓ Good |
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
| Closure-based sliding-window rate limiter | Per-decorator Lock + timestamp list; no global state; thread-safe without shared data structures | ✓ Good |
| Conftest fixtures → importable helpers module | pytest conftest discovery scope didn't reach all test directories; explicit imports are reliable | ✓ Good |
| SHA-pinned GitHub Actions with version comments | Prevents supply chain attacks via tag mutation; comment preserves human readability | ✓ Good |
| SSH key-only auth in test containers | Eliminates hardcoded passwords from Dockerfiles; ephemeral ED25519 keys generated at build time | ✓ Good |
| Non-root sshd via gosu + setcap | Reduces container attack surface; sshd binds port 22 via CAP_NET_BIND_SERVICE | ✓ Good |
| WSGI iterator harness for SSE tests | Direct web_app() invocation avoids HTTP stack; enables streaming assertions without real server | ✓ Good |
| Python `fail_under` raised 84 → 88 (Plan 100-03, RATCHET-02) | Container-inclusive re-measure (real-lftp suite inside Docker) = 89.27%; floor = floor(89.27) − 1 = 88; margin 1%; computed floor 88 strictly > prior floor 84; the host-only provisional number (85.19%) was excluded — container-inclusive is the authoritative ratchet source | ✓ Good |
| Angular Karma `check.global` set stmts 83 / branches 68 / fns 79 / lines 83 (Plan 100-03, RATCHET-02) | Post-100-01/02 measured: stmts 84.14% / branches 69.46% / fns 80.49% / lines 84.99%; floor = floor(measured) − 1 per metric; margin 1%; first-ever Karma global thresholds (prior floor = 0 for all); `--code-coverage` flag added to Dockerfile CMD in same commit so gate is non-silent (text-summary confirms coverage collected) | ✓ Good |

## Project Status

**Status:** v1.7.7 Sonarr 5 Compatibility verified (Phase 120 complete; no release needed); 1.7.6 runs on the NAS. Then: Reliability milestone (Phase 121+).

31 milestones shipped (v1.0 through v4.0.3 as SeedSync, v1.0.0 rebrand + v1.1.0 UI redesign + v1.1.1 cleanup + v1.1.2 test audit + v1.2.0 test hardening as SeedSyncarr).

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
*Last updated: 2026-10-20 after Phase 120 completion (Sonarr 5 verified; no release needed)*
