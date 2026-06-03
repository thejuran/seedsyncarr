# Roadmap: SeedSync -> SeedSyncarr

## Milestones

- v1.0 Unify UI Styling - Phases 1-5 (shipped 2026-02-03)
- v1.1 Dropdown & Form Migration - Phases 6-8 (shipped 2026-02-04)
- v1.2 UI Cleanup - Phase 9 (shipped 2026-02-04)
- v1.3 Polish & Clarity - Phases 10-11 (shipped 2026-02-04)
- v1.4 Sass @use Migration - Phases 12-14 (shipped 2026-02-08)
- v1.5 Backend Testing - Phases 15-19 (shipped 2026-02-08)
- v1.6 CI Cleanup - Phases 20-21 (shipped 2026-02-10)
- v1.7 Sonarr Integration - Phases 22-25 (shipped 2026-02-10)
- v1.8 Radarr + Webhooks - Phases 26-28 (shipped 2026-02-11)
- v2.0 Dark Mode & Polish - Phases 29-32 (shipped 2026-02-12)
- v3.0 Terminal UI Overhaul - Phases 33-38 (shipped 2026-02-17)
- v3.1 Harden & Fix - Phases 39-46 (shipped 2026-02-24)
- v3.2 Security Hardening II - Phases 47-49 (shipped 2026-02-26, phases 50-51 completed via M002)
- M001: Angular 21 Migration - 3 slices (shipped 2026-03-21, released as v3.2.0)
- M002: Finish v3.2 Security - 3 slices (shipped 2026-03-22)
- M003: UI Redesign -- Earthy Palette - 6 slices (shipped 2026-03-25)
- M004: Polish & Dependency Updates - 4 slices (shipped 2026-03-24)
- M005: Dashboard Polish & v3.3.0 - 2 slices (shipped 2026-03-24)
- M006: Triggarr-Style Layout + Deep Moss Palette - 3 slices (shipped 2026-03-25)
- M007: Settings Redesign & Multi-Select Polish - 2 slices (shipped 2026-03-26)
- M008: AutoQueue Migration, Token UI & Toast Polish - 2 slices (shipped 2026-03-27)
- M009: Full Codebase Deep Review Fixes - 4 slices (shipped 2026-03-28)
- M010: Screenshots, Docs & v4.0.0 Release - (shipped 2026-03-28, tagged v4.0.0)
- v4.0.3 Dependency Fixes & CI - Phase 52 (shipped 2026-04-08)
- v1.0.0 SeedSyncarr Rebrand - Phases 53-61 (shipped 2026-04-13)
- v1.1.0 UI Redesign — Triggarr Style - Phases 62-74 (shipped 2026-04-19; Phase 71 dropped)
- v1.1.1 Post-Redesign Cleanup & Outstanding Work - Phases 75-82 (shipped 2026-04-23)
- v1.1.2 Test Suite Audit - Phases 83-86 (shipped 2026-04-24)
- ✅ v1.2.0 Test & Quality Hardening - Phases 87-96 (shipped 2026-04-28)
- ✅ v1.3.0 — Slice 1 of 4: Test Coverage Gaps - Phases 97-100 (shipped 2026-05-31)
- ✅ v1.3.0 — Slice 2 of 4: Known Bugs + Security - Phases 101-103 (shipped 2026-06-01; no tag until slice 4)
- ✅ v1.3.0 — Slice 3 of 4: Frontend Deps + Dead Code - Phases 104-106 (shipped 2026-06-01; no tag until slice 4)
- ✅ v1.3.0 — Slice 4 of 4: Backend Architecture Refactor + Test Infra - Phases 107-109 (shipped 2026-06-02; v1.3.0 tag cut)
- 🚧 v1.4.0 — Launch-Hardening for Public Release - Phases 110-113 (in progress; branch `launch-hardening`, single `v1.4.0` tag cut at milestone end)

## Phases

<details>
<summary>v1.0 Unify UI Styling (Phases 1-5) - SHIPPED 2026-02-03</summary>

- [x] Phase 1: Bootstrap SCSS Setup (1/1 plans) - completed 2026-02-03
- [x] Phase 2: Color Variable Consolidation (2/2 plans) - completed 2026-02-03
- [x] Phase 3: Selection Color Unification (1/1 plans) - completed 2026-02-03
- [x] Phase 4: Button Standardization - File Actions (2/2 plans) - completed 2026-02-03
- [x] Phase 5: Button Standardization - Other Pages (2/2 plans) - completed 2026-02-03

See `.planning/milestones/v1.0-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.1 Dropdown & Form Migration (Phases 6-8) - SHIPPED 2026-02-04</summary>

- [x] Phase 6: Dropdown Migration (1/1 plans) - completed 2026-02-04
- [x] Phase 7: Form Input Standardization (1/1 plans) - completed 2026-02-04
- [x] Phase 8: Final Polish (2/2 plans) - completed 2026-02-04

See `.planning/milestones/v1.1-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.2 UI Cleanup (Phase 9) - SHIPPED 2026-02-04</summary>

- [x] Phase 9: Remove Obsolete Buttons (1/1 plans) - completed 2026-02-04

See `.planning/milestones/v1.2-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.3 Polish & Clarity (Phases 10-11) - SHIPPED 2026-02-04</summary>

- [x] Phase 10: Lint Cleanup (4/4 plans) - completed 2026-02-04
- [x] Phase 11: Status Dropdown Counts (1/1 plans) - completed 2026-02-04

See `.planning/milestones/v1.3-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.4 Sass @use Migration (Phases 12-14) - SHIPPED 2026-02-08</summary>

- [x] Phase 12: Shared Module Migration (1/1 plans) - completed 2026-02-08
- [x] Phase 13: Styles Entry Point (1/1 plans) - completed 2026-02-08
- [x] Phase 14: Validation (1/1 plans) - completed 2026-02-08

See `.planning/milestones/v1.4-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.5 Backend Testing (Phases 15-19) - SHIPPED 2026-02-08</summary>

- [x] Phase 15: Coverage Tooling & Shared Fixtures (1/1 plans) - completed 2026-02-08
- [x] Phase 16: Common Module Tests (1/1 plans) - completed 2026-02-08
- [x] Phase 17: Web Handler Unit Tests (2/2 plans) - completed 2026-02-08
- [x] Phase 18: Controller Unit Tests (2/2 plans) - completed 2026-02-08
- [x] Phase 19: Coverage Baseline & Validation (1/1 plans) - completed 2026-02-08

See `.planning/milestones/v1.5-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.6 CI Cleanup (Phases 20-21) - SHIPPED 2026-02-10</summary>

- [x] Phase 20: CI Workflow Consolidation (1/1 plans) - completed 2026-02-09
- [x] Phase 21: Test Runner Cleanup (1/1 plans) - completed 2026-02-10

See `.planning/milestones/v1.6-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.7 Sonarr Integration (Phases 22-25) - SHIPPED 2026-02-10</summary>

- [x] Phase 22: Configuration & Settings UI (2/2 plans) - completed 2026-02-10
- [x] Phase 23: API Client Integration (2/2 plans) - completed 2026-02-10
- [x] Phase 24: Status Visibility & Notifications (2/2 plans) - completed 2026-02-10
- [x] Phase 25: Auto-Delete with Safety (2/2 plans) - completed 2026-02-10

See `.planning/milestones/v1.7-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.8 Radarr + Webhooks (Phases 26-28) - SHIPPED 2026-02-11</summary>

- [x] Phase 26: Radarr Config & Shared *arr Settings UI (2/2 plans) - completed 2026-02-11
- [x] Phase 27: Webhook Import Detection (2/2 plans) - completed 2026-02-11
- [x] Phase 28: Fix Pre-existing Test Failures (1/1 plans) - completed 2026-02-11

See `.planning/milestones/v1.8-ROADMAP.md` for full details.

</details>

<details>
<summary>v2.0 Dark Mode & Polish (Phases 29-32) - SHIPPED 2026-02-12</summary>

- [x] Phase 29: Theme Infrastructure (2/2 plans) - completed 2026-02-11
- [x] Phase 30: SCSS Audit & Color Fixes (2/2 plans) - completed 2026-02-12
- [x] Phase 31: Theme Toggle UI (1/1 plans) - completed 2026-02-12
- [x] Phase 32: Cosmetic Fixes (1/1 plans) - completed 2026-02-12

See `.planning/milestones/v2.0-ROADMAP.md` for full details.

</details>

<details>
<summary>v3.0 Terminal UI Overhaul (Phases 33-38) - SHIPPED 2026-02-17</summary>

- [x] Phase 33: Foundation (3/3 plans) - completed 2026-02-17
- [x] Phase 34: Shell (2/2 plans) - completed 2026-02-17
- [x] Phase 35: Dashboard (3/3 plans) - completed 2026-02-17
- [x] Phase 36: Secondary Pages (2/2 plans) - completed 2026-02-17
- [x] Phase 37: Theme Cleanup (1/1 plans) - completed 2026-02-17
- [x] Phase 38: Terminal Polish & Traceability (1/1 plans) - completed 2026-02-17

See `.planning/milestones/v3.0-ROADMAP.md` for full details.

</details>

<details>
<summary>v3.1 Harden & Fix (Phases 39-46) - SHIPPED 2026-02-24</summary>

- [x] Phase 39: Critical Security Chain (2/2 plans) - completed 2026-02-24
- [x] Phase 40: Credential & Endpoint Security (3/3 plans) - completed 2026-02-24
- [x] Phase 41: Thread Safety (2/2 plans) - completed 2026-02-24
- [x] Phase 42: Crash Prevention (3/3 plans) - completed 2026-02-24
- [x] Phase 43: Frontend Quality (3/3 plans) - completed 2026-02-24
- [x] Phase 44: Code Quality (5/5 plans) - completed 2026-02-24
- [x] Phase 45: Documentation & Accessibility (3/3 plans) - completed 2026-02-24
- [x] Phase 46: Code Review Fixes (4/4 plans) - completed 2026-02-24

See `.planning/milestones/v3.1-ROADMAP.md` for full details.

</details>

<details>
<summary>v3.2 Security Hardening II (Phases 47-51) - SHIPPED 2026-02-26 / 2026-03-22</summary>

- [x] Phase 47: Isolated Backend Hardening (3/3 plans) - completed 2026-02-25
- [x] Phase 48: Config and Webhook Layer (2/2 plans) - completed 2026-02-26
- [x] Phase 49: Path Traversal Guards (1/1 plans) - completed 2026-02-26
- [x] Phase 50: API Token Authentication (3/3 plans) - completed 2026-03-22 (via M002)
- [x] Phase 51: CSP Hardening (1/1 plans) - completed 2026-03-22 (via M002)

</details>

<details>
<summary>M001-M010 + v4.0.x Hotfixes (Phase 52) - SHIPPED 2026-03-21 to 2026-04-08</summary>

- [x] M001: Angular 21 Migration - 3 slices - completed 2026-03-21
- [x] M002: Finish v3.2 Security - 3 slices - completed 2026-03-22
- [x] M003: UI Redesign -- Earthy Palette - 6 slices - completed 2026-03-25
- [x] M004: Polish & Dependencies - 4 slices - completed 2026-03-24
- [x] M005: Dashboard Polish - 2 slices - completed 2026-03-24
- [x] M006: Deep Moss + Layout - 3 slices - completed 2026-03-25
- [x] M007: Settings Redesign - 2 slices - completed 2026-03-26
- [x] M008: AutoQueue + Token UI - 2 slices - completed 2026-03-27
- [x] M009: Deep Review Fixes - 4 slices - completed 2026-03-28
- [x] M010: Docs & v4.0.0 Release - completed 2026-03-28
- [x] Phase 52: Dependency Fixes & CI Validation (1/1 plans) - completed 2026-04-08

</details>

<details>
<summary>v1.0.0 SeedSyncarr Rebrand (Phases 53-61) - SHIPPED 2026-04-13</summary>

- [x] **Phase 53: New Repo & Atomic Rename** - completed 2026-04-08
- [x] **Phase 54: Archive Old Repo** - completed 2026-04-08
- [x] **Phase 55: Code Hardening** - completed 2026-04-08
- [x] **Phase 56: Test Quality** - completed 2026-04-08
- [x] **Phase 57: README & Community Health** - completed 2026-04-09
- [x] **Phase 58: Docs Site** - completed 2026-04-09
- [x] **Phase 59: Community Launch** - completed 2026-04-09
- [x] **Phase 60: Dependency Updates** - completed 2026-04-09
- [x] **Phase 61: Branding Integration** - completed 2026-04-13

</details>

<details>
<summary>v1.1.0 UI Redesign -- Triggarr Style (Phases 62-74) - SHIPPED 2026-04-19</summary>

- [x] Phase 62: Nav Bar Foundation (2/2 plans) - completed 2026-04-15
- [x] Phase 63: Dashboard -- Stats Strip & Transfer Table (2/2 plans) - completed 2026-04-15
- [x] Phase 64: Dashboard -- Log Pane (1/1 plans) - completed 2026-04-14
- [x] Phase 65: Settings Page (2/2 plans) - completed 2026-04-15
- [x] Phase 66: Logs Page (2/2 plans) - completed 2026-04-15
- [x] Phase 67: About Page (2/2 plans) - completed 2026-04-14
- [x] Phase 68: UI Polish (2/2 plans) - completed 2026-04-15
- [x] Phase 69: E2E Selector Update (1/1 plans) - completed 2026-04-15
- [x] Phase 70: Drilldown Segment Filters (2/2 plans) - completed 2026-04-15
- [ ] ~~Phase 71: push stable release~~ -- dropped (never planned)
- [x] Phase 72: Restore dashboard file selection and action bar (5/5 plans) - completed 2026-04-19
- [x] Phase 73: Dashboard filter for every torrent status (5/5 plans) - completed 2026-04-19
- [x] Phase 74: Storage capacity tiles (4/4 plans) - completed 2026-04-19

See `.planning/milestones/v1.1.0-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.1.1 Post-Redesign Cleanup & Outstanding Work (Phases 75-82) - SHIPPED 2026-04-23</summary>

- [x] Phase 75: Per-Child Import State (GH #19) (4/4 plans) - completed 2026-04-20
- [x] Phase 76: Multiselect Bulk-Bar Action Union (4/4 plans) - completed 2026-04-20
- [x] Phase 77: Deferred Playwright E2E (Phases 72+73) (4/4 plans) - completed 2026-04-21
- [x] Phase 78: Storage Tile Live-Seedbox UAT (2/2 plans) - completed 2026-04-21
- [x] Phase 79: Test Infra Cleanup (2/2 plans) - completed 2026-04-22
- [x] Phase 80: Small Cleanups (Dependabot + arm64 + enum) (3/3 plans) - completed 2026-04-22
- [x] Phase 81: Optional Fernet Encryption at Rest (3/3 plans) - completed 2026-04-22
- [x] Phase 82: Release Prep (Retro v1.1.0 Notes + v1.1.1 Tag) (4/4 plans) - completed 2026-04-23

See `.planning/milestones/v1.1.1-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.1.2 Test Suite Audit (Phases 83-86) - SHIPPED 2026-04-24</summary>

**Milestone Goal:** Identify and remove stale, redundant, or dead-path tests inherited from the original SeedSync repo -- lean the test suite to only test current behavior.

- [x] **Phase 83: Python Test Audit** - Identify and remove stale Python backend tests (completed 2026-04-24)
- [x] **Phase 84: Angular Test Audit** - Identify and remove stale Angular unit tests (completed 2026-04-24)
- [x] **Phase 85: E2E Test Audit** - Identify and remove redundant Playwright specs (completed 2026-04-24)
- [x] **Phase 86: Final Validation** - Full CI green and coverage baseline documented (completed 2026-04-24)

See `.planning/milestones/v1.1.2-ROADMAP.md` for full details.

</details>

<details>
<summary>✅ v1.2.0 Test & Quality Hardening (Phases 87-96) — SHIPPED 2026-04-28</summary>

- [x] Phase 87: Python Test Fixes -- Critical & Warning (2/2 plans) — completed 2026-04-25
- [x] Phase 88: Python Test Fixes -- Medium & Cleanup (3/3 plans) — completed 2026-04-25
- [x] Phase 89: Python Test Architecture (2/2 plans) — completed 2026-04-25
- [x] Phase 90: Angular Test Fixes (2/2 plans) — completed 2026-04-27
- [x] Phase 91: E2E Test Fixes & Platform (2/2 plans) — completed 2026-04-27
- [x] Phase 92: E2E Infrastructure (2/2 plans) — completed 2026-04-27
- [x] Phase 93: CI & Docker Hardening (3/3 plans) — completed 2026-04-28
- [x] Phase 94: Test Coverage -- Backend (2/2 plans) — completed 2026-04-28
- [x] Phase 95: Test Coverage -- E2E (2/2 plans) — completed 2026-04-28
- [x] Phase 96: Rate Limiting & Tooling (3/3 plans) — completed 2026-04-28

See `.planning/milestones/v1.2.0-ROADMAP.md` for full details.

</details>

<details>
<summary>✅ v1.3.0 — Slice 1 of 4: Test Coverage Gaps (Phases 97-100) — SHIPPED 2026-05-31</summary>

**Milestone Goal:** Close the 8 test coverage gaps catalogued in CONCERNS.md — 4 Medium-priority gaps get full path coverage, 4 Low-priority gaps get a targeted regression test. Trivial bugs found while testing (<10 net lines, no public-API or observable-behavior change) are fixed in the same plan; larger findings deferred to v1.4.0. Milestone ends with ratcheted CI coverage thresholds and before/after numbers recorded below.

- [x] **Phase 97: Medium-Priority Python Coverage** - Baseline capture + full-path coverage for MP-logger, SSRF, LFTP parser (completed 2026-05-28)
- [x] **Phase 98: Medium-Priority Angular Coverage** - Full-path end-to-end XSS coverage for confirm-modal escapeHtml (completed 2026-05-29)
- [x] **Phase 99: Low-Priority Python Coverage** - Targeted regression tests for auto-delete toggle and BoundedOrderedSet eviction (completed 2026-05-29)
- [x] **Phase 100: Low-Priority Angular Coverage + CI Ratchet** - SSE timeout + auth interceptor regressions, then ratchet pytest + Karma thresholds (completed 2026-05-29)

### Coverage Ratchet — Before / After

Baseline anchor: `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md` (captured at start of Phase 97, against `main` HEAD).

| Layer | Threshold | Before | After |
|-------|-----------|--------|-------|
| Python (`fail_under` in `[tool.coverage.report]`) | line | 85.19% host/provisional (excludes real-lftp suite); floor 84; container-inclusive re-measure = 89.27% (Plan 100-03) | **89.27%** container-inclusive (1278 passed, 62 skipped); floor raised **84 → 88** (margin 1%, floor(89.27)−1=88, strictly > 84) |
| Angular (Karma `coverageReporter.check.global`) | statements / branches / functions / lines | 83.34% / 69.01% / 79.73% / 84.21% (no Karma global threshold before) | **84.14% / 69.46% / 80.49% / 84.99%** (post-100-01/02); floors set **83 / 68 / 79 / 83** (margin 1%, floor(measured)−1, first thresholds strictly > 0) |

*Filled in during Plan 97-baseline (before) and Plan 100-03 (after). The ratchet is monotonic — only increases.*

</details>

<details>
<summary>✅ v1.3.0 — Slice 2 of 4: Known Bugs + Security (Phases 101-103) — SHIPPED 2026-06-01</summary>

**Milestone Goal:** Fix the 7 approved Known-Bugs + Security items from CONCERNS.md buckets 2 + 3 (plus rolled-forward test-infra item INFRA-01) — close the webhook fail-open gap and the log-injection surface, add webhook rate-limiting and config-response normalization, harden auto-delete Timer lifecycle, eliminate the Angular `innerHTML` XSS sink and the SSE same-tick subscription leak. Several code paths already have slice-1 (v1.3.0) regression tests pinning current behavior — reuse them and land fixes test-first where feasible. **This slice cuts no git tag**; the single `v1.3.0` tag is cut only after slice 4 of the 4-slice program completes.

**GSD internal label:** `v1.3.0-s2`. Source: `.planning/codebase/CONCERNS.md` (Known Bugs + Security) + `.planning/REQUIREMENTS.md`.

- [x] **Phase 101: Webhook + Log-Injection Security Cluster** - Webhook fails closed without a secret, log-injection sanitizer audit, webhook rate-limiting, config-response normalization (BUG-02, SEC-01, SEC-03, SEC-02) (completed 2026-05-31)
- [x] **Phase 102: Controller Concurrency** - Auto-delete Timer in-flight shutdown guard (BUG-03). *(INFRA-01 deferred to a later v1.3.0 slice — a spawn-safe fix requires a production-module change to MultiprocessingLogger's queue context, which exceeds INFRA-01's "lowest priority; must not expand the milestone, test-only" constraint. See Phase 102 notes.)* (completed 2026-06-01)
- [x] **Phase 103: Angular Defects** - Replace ConfirmModal innerHTML sink with Renderer2 (incl. skipCount hardening), SSE registry same-tick subscription teardown (BUG-01, BUG-04) (completed 2026-06-01)

</details>

<details>
<summary>✅ v1.3.0 — Slice 3 of 4: Frontend Deps + Dead Code (Phases 104-106) — SHIPPED 2026-06-01</summary>

**Milestone Goal:** Remove three end-of-life / unmaintained Angular dependencies (jQuery 4, Font Awesome 4.7, css-element-queries) and move the development-only mock-model fixtures out of the production bundle via Angular `fileReplacements`. Every removal follows an audit → replace/confirm-unused → drop → verify-build-bundle-CI rhythm. No tag is cut; the single `v1.3.0` tag is cut only after slice 4 completes.

**GSD internal label:** `v1.3.0-s3`. Source: `.planning/codebase/CONCERNS.md` (Dependencies at Risk + Tech Debt) + `.planning/REQUIREMENTS.md`.

- [x] **Phase 104: Light Dependency Removals** - Confirm jQuery 4 and css-element-queries have no source usage, then drop both deps; bundle shrinks and Bootstrap interactions are unaffected (DEPS-01a, DEPS-01c) — completed 2026-06-01
- [x] **Phase 105: Font Awesome → Phosphor Migration** - Inventory every remaining `fa-*` icon class in templates, replace each with its Phosphor equivalent, then remove the font-awesome dep; no icon renders missing (DEPS-01b) (completed 2026-06-01)
- [x] **Phase 106: Mock-Fixture Bundle Hygiene** - Move `USE_MOCK_MODEL` toggle into `environment.ts`, relocate mock files out of `services/files/`, exclude via `fileReplacements`; production bundle contains none of the mock data (DEPS-02) (completed 2026-06-01)

</details>

✅ v1.3.0 — Slice 4 of 4: Backend Architecture Refactor + Test Infra (Phases 107-109) — SHIPPED 2026-06-02

**Milestone Goal:** Close the four backend architecture and test-infra items promoted from the CONCERNS.md Architecture/Maintainability and Tech Debt sections — fix the MP-logger spawn-context bug that blocks `spawn`-mode analog tests on macOS, make `Config` secret-field discovery declarative via `PROP(secret=True)`, deduplicate the five per-action bulk-handler scaffolds into a shared helper, and decompose the 1115-line `Controller` god-class into cohesive single-responsibility collaborators. All ARCH items are behavior-preserving; the existing test suite is the regression net throughout. This is the **final** slice of the 4-slice v1.3.0 program — the single `v1.3.0` tag is cut when this slice completes, preceded by the batched pre-release walkthrough.

**GSD internal label:** `v1.3.0-s4`. Source: `.planning/codebase/CONCERNS.md` (Architecture/Maintainability + Tech Debt) + `.planning/REQUIREMENTS.md`.

- [x] **Phase 107: MP-Logger Spawn Safety** - Production fix to `multiprocessing_logger.py` so the logger queue is created from a shared `spawn`-compatible context; three previously-failing spawn-context analog tests now pass on both macOS and Linux (INFRA-01) (completed 2026-06-01)
- [x] **Phase 108: Config + Handler Refactors** - Push `secret=True` into each `PROP` declaration so encrypt/decrypt/redact loops discover secrets dynamically (ARCH-02); extract a shared `_dispatch_command(...)` helper from the five duplicate per-action handlers (ARCH-03) (completed 2026-06-01)
- [x] **Phase 109: Controller Decomposition** - Decompose the `Controller` god-class into cohesive collaborators with single responsibilities; public surface and all caller contracts are preserved; existing test suite stays green throughout (ARCH-01) (completed 2026-06-02)

🚧 v1.4.0 — Launch-Hardening for Public Release (Phases 110-113) — IN PROGRESS

**Milestone Goal:** Make SeedSyncarr's public-facing surface — both the code a skeptical engineer reads and the presentation a visitor sees — bulletproof enough to withstand a technical Reddit (r/selfhosted) launch. The work is two largely-disjoint tracks plus one cross-cutting change: a bounded hostile-reader discovery pass that gates fix scope (SCAN), the `/server/config/set` GET→POST hard cutover (CFG — the one breaking HTTP-contract change, credentials no longer in URLs/logs), a defensive-guards/code-hardening cluster (GUARD — unsafe-default warnings, logged delete failures, the AppProcess spawn fix, repo hygiene), and a presentation/launch-readiness rebuild (LAUNCH — cynical-reader teardown + codex pass driving README/SECURITY.md/community-health/release-notes, screenshots at the walkthrough, repo-metadata drafted for manual application). Code substance is already strong (post-v1.3.0 audit found zero active functional bugs); the launch risk is presentation underselling real quality plus a few specific items a hostile reader would find.

**GSD internal label:** `v1.4.0`. Source: `.planning/codebase/CONCERNS.md` (Tech Debt + Security Considerations + Test Coverage Gaps) + the approved design spec + `.planning/REQUIREMENTS.md`.

**CI gates every code phase (110-112) must hold:** Python `fail_under` ≥ 88; Angular Karma `check.global` floors stmts/branches/fns/lines 83/68/79/83; full suite green on amd64 + arm64. **No release/tag/version work happens inside any phase** — the single `v1.4.0` tag is a milestone-end orchestrator/maintainer action on branch `launch-hardening` after the NAS walkthrough, CI green, and maintainer sign-off.

- [x] **Phase 110: Hostile-Reader Discovery Pass** - Bounded "what would a skeptical r/selfhosted engineer flag" audit producing a triaged, severity-ranked findings artifact; each finding marked fold-into-fix-phase (with target) or parked (with rationale); gates fix scope for phases 111-112 (SCAN-01, SCAN-02) (completed 2026-06-02)
- [x] **Phase 111: Config-Set Endpoint Migration** - The one breaking change: `/server/config/set` GET→POST hard cutover (JSON body), legacy GET path fully removed, Angular `ConfigService` + E2E setup/page-objects updated, on-disk config format unchanged (CFG-01, CFG-02, CFG-03, CFG-04) (completed 2026-06-02)
- [x] **Phase 112: Defensive Guards & Code Hardening** - Unsafe-default startup warnings (non-loopback bind w/o api_token; webhook w/o secret), logged delete-path failures (replace `ignore_errors=True`), AppProcess spawn-context fix (failing test goes green), `.gitignore` for run artifacts, legacy `~/.seedsync` fallback warning (GUARD-01..06) — 3 plans (1 wave) (completed 2026-06-02)
- [ ] **Phase 113: Presentation & Launch Readiness** - Cynical-reader teardown + codex adversarial pass driving a README / SECURITY.md / community-health / release-notes rebuild; Playwright screenshots captured at the milestone-end walkthrough; repo-metadata text drafted for manual maintainer application (LAUNCH-01..06) — 4 plans (3 waves)

## Phase Details

### Phase 101: Webhook + Log-Injection Security Cluster

**Goal**: The webhook endpoint and the backend log surface are hardened — an operator can opt in (new flag, default off) to make an unconfigured webhook secret fail closed instead of accepting unauthenticated calls (default behavior unchanged for backward compat), every remote-/user-supplied string is sanitized before it reaches a log line, the webhook endpoint is rate-limited like other mutable endpoints, and the config GET response no longer leaks secret-present vs unset beyond the explicit boolean flag.
**Depends on**: Phase 100 (slice 1 complete — green CI, ratcheted coverage floors)
**Requirements**: BUG-02, SEC-01, SEC-03, SEC-02
**Success Criteria** (what must be TRUE):

  1. **BUG-02 (opt-in fail-closed, highest priority — must NOT break backward compat):** A new config flag (default **off**) gates fail-closed behavior. With the flag **on** and no secret configured, a POST to the webhook endpoint is rejected with **503** before the body is parsed. With the flag **off** (default), existing behavior is preserved exactly — no secret → HMAC skipped + loud startup warning (honors the `Empty webhook_secret skips HMAC` decision). With a secret configured, valid HMAC requests still succeed unchanged. Existing config files load with no new required field. The flag + required-secret expectation are surfaced to the operator (startup warning / docs).
  2. Every backend log site that interpolates remote-/webhook-/user-supplied strings (controller.py, lftp/job_status_parser.py, controller/webhook_manager.py, and any other audited site) passes the value through a CR/LF/control-char sanitizer — a crafted filename containing `\r\n` can no longer forge a second log line (CWE-117) (SEC-01).
  3. The webhook endpoint is wrapped with the same v1.2.0 sliding-window rate-limit middleware used on other mutable endpoints, tuned to legitimate *arr callback frequency; over-limit calls get a generic 429 (SEC-03).
  4. The config GET response shape is identical whether a given secret is set or unset, apart from the existing explicit boolean flag — no length, key-presence, or value-shape difference distinguishes the two (SEC-02).
  5. **Cross-cutting (COMPAT):** no breaking changes on upgrade — existing config files load unchanged (no new required fields), and status codes/response shapes for already-supported paths are unchanged. CI green on amd64 + arm64 (Python + Angular + E2E); Python `fail_under` ≥ 88 holds or rises; security fixes log no sensitive data and return generic client errors with detail logged server-side. No release/tag/version work in this phase.

**Plans**: 6 plans (3 waves)
- [x] 101-01-PLAN.md — SEC-01: shared `sanitize_log_value()` CWE-117 helper in `common/types.py` (CR/LF + control chars) + unit tests (wave 1, leaf dependency)
- [x] 101-02-PLAN.md — BUG-02 + SEC-03: opt-in `webhook_require_secret` fail-closed 503 (guard outside rate_limit, before body parse) + first-run default, per-route rate-limit (60/60s → 429), startup warning (wave 1)
- [x] 101-03-PLAN.md — SEC-02: config GET response always serializes secret value fields as `""` on both auth paths (wave 1)
- [x] 101-04-PLAN.md — SEC-01: apply `sanitize_log_value()` at the webhook/command cluster (webhook_manager ×2, controller.py:790/792/760/975/1075) (wave 2, depends on 101-01)
- [x] 101-05-PLAN.md — SEC-01: apply `sanitize_log_value()` at the auto-delete timer cluster (controller.py:229/820/841/848/866/876/897/926/948) + model-layer (model.py:81/97/112) (wave 3, depends on 101-04)
- [x] 101-06-PLAN.md — SEC-01: apply `sanitize_log_value()` at the lftp cluster (lftp.py kill 356/362/365 + __run_command output 126/129/144/147/148, job_status_parser.py:724/725) (wave 2, depends on 101-01) — lftp sites brought in-scope after adversarial-review round 2

### Phase 102: Controller Concurrency

**Goal**: The auto-delete `threading.Timer` lifecycle is safe across controller shutdown — pending timers are tracked and cancelled, and a callback that has already fired no-ops when shutdown is in progress so no deletion (and no persist-state mutation) runs against a half-torn-down model.
**Depends on**: Phase 101
**Requirements**: BUG-03 (INFRA-01 deferred — see note below)
**Success Criteria** (what must be TRUE):

  1. Every auto-delete `threading.Timer` is registered when scheduled and cancelled on controller shutdown; after shutdown completes, no pending auto-delete Timer remains armed (BUG-03). *(Already shipped in Phase 101 Plan 05 — verified by test in this phase, no new production code.)*
  2. A Timer callback that fires while shutdown is in progress detects the shutdown flag and no-ops — it performs no model read, no persist-state mutation, and no `delete_local` dispatch against a torn-down model. The shutdown signal (a dedicated `threading.Event`) is **set under `__auto_delete_lock`**, and the callback's final guard + `imported_children.pop` + `delete_local` decision is **serialized on the same lock**, so "shutdown begins before dispatch ⇒ no dispatch" holds strictly (no preempt-after-check race). The existing slice-1 auto-delete toggle/dry-run regression tests still pass (BUG-03).
  3. **Cross-cutting (COMPAT):** no breaking changes on upgrade — existing config files and on-disk persist formats load unchanged. CI green on amd64 + arm64 (Python); Python `fail_under` ≥ 88 holds or rises; no concurrency fix logs sensitive data; generic client errors with server-side detail. No release/tag/version work in this phase.

> **INFRA-01 deferred (decision 2026-05-31).** Adversarial review (codex, confirmed by a live repro) found the MP-logger spawn-safe fix cannot be done test-only: the `MultiprocessingLogger` queue is created in the default (fork) context, and handing a fork-context queue to a `spawn` child raises `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context`. A correct fix requires creating the queue from a shared `spawn` context — a **production-module change** that violates INFRA-01's "lowest priority; include only if it does not expand the milestone" constraint (REQUIREMENTS.md) and the test-only intent (D-08). INFRA-01 is therefore deferred to a later v1.3.0 slice where a production change to `MultiprocessingLogger` is in scope. Phase 102 still delivers its primary requirement, BUG-03.

**Plans**: 1 plan (1 wave)
- [x] 102-01-PLAN.md — BUG-03: add a dedicated `threading.Event` in-flight shutdown guard to `__execute_auto_delete`, with the final guard + persist-pop + `delete_local` serialized under `__auto_delete_lock` and the event set under the same lock in `exit()` (test-first red→green, reusing the real-Timer Event-gated harness); criterion #1 timer-cancel-on-exit verified by test only (already shipped) (wave 1)

### Phase 103: Angular Defects

**Goal**: The confirmation modal renders without any raw `innerHTML` sink — content is built structurally via `Renderer2` (or a standalone Angular component) so escaping is structural rather than string-concatenation dependent (folding in the deferred `skipCount` type-erasure hardening) — and the SSE stream-service registry never leaves an orphaned subscription when a reconnect fires in the same tick as a timeout.
**Depends on**: Phase 102
**Requirements**: BUG-01, BUG-04
**Success Criteria** (what must be TRUE):

  1. `ConfirmModalService` builds modal content with no raw `innerHTML` assignment — content nodes are created via `Renderer2`/`createText` or a structural Angular component; the slice-1 escapeHtml XSS regression suite still passes (no behavioral regression for existing callers) (BUG-01).
  2. The `skipCount` interpolation is hardened — the value is coerced via `Number()` and/or escaped so a `toString()`-overriding object can no longer inject markup through the `skipMessage` path; the slice-1 skipCount runtime-boundary probe still passes (BUG-01 fold-in).
  3. When a reconnect fires in the same tick as a timeout in the stream-service registry, the prior EventSource/subscription is torn down before its replacement is created — exactly one active subscription remains, no orphan; the slice-1 SSE heartbeat-vs-timeout race regression test still passes (BUG-04).
  4. **Cross-cutting (COMPAT):** no breaking changes to existing UI behavior or observable component APIs. CI green on amd64 + arm64 (Angular + E2E); Karma `check.global` floors (stmts/branches/fns/lines 83/68/79/83) hold or rise; no client-visible behavior regression in confirm-modal or SSE reconnect. No release/tag/version work in this phase.

**Plans**: TBD

**UI hint**: yes

### Phase 104: Light Dependency Removals

**Goal**: jQuery 4 and css-element-queries are confirmed unused in Angular source and removed from `package.json`; the production bundle no longer ships either library and all Bootstrap-driven UI interactions remain fully functional.
**Depends on**: Phase 103 (slice 2 complete — green CI, all Angular floors held)
**Requirements**: DEPS-01a, DEPS-01c
**Success Criteria** (what must be TRUE):

  1. A grep/audit of `src/angular/src/` confirms zero direct `import`/`require` of `jquery`, `$`, or `jQuery`, and zero use of `ResizeObserver`-based API from `css-element-queries` — confirming both are exclusively transitive and can be removed without a replacement (DEPS-01a, DEPS-01c).
  2. `jquery` and `css-element-queries` are removed from `src/angular/package.json`; `npm install` resolves cleanly with no peer-dependency warnings attributable to these removals; `ng build --configuration production` completes without error (DEPS-01a, DEPS-01c).
  3. The production bundle (`ng build` output) contains no `jquery` chunk and no `css-element-queries` chunk — confirmed by inspecting build stats or `grep` over the dist directory; total bundle size is equal to or smaller than the pre-removal baseline (DEPS-01a, DEPS-01c).
  4. All Bootstrap-driven interactions — dropdowns, modals, and collapses used in the dashboard, settings, and nav — render and function correctly in a dev-server smoke test; no console errors referencing jQuery or missing dependencies (DEPS-01a).
  5. CI is green on amd64 + arm64 (Angular unit + E2E; Python unaffected but stays green); Karma `check.global` floors (stmts/branches/fns/lines 83/68/79/83) hold or rise; Python `fail_under` ≥ 88 unchanged. No release/tag/version work in this phase.

**Plans**: 2 plans (2 waves)
- [x] 104-01-PLAN.md — DEPS-01a + DEPS-01c: audit zero-usage + capture pre-removal bundle baseline, then drop jquery and css-element-queries from package.json as two atomic commits (D-03), regenerating package-lock.json (wave 1)
- [x] 104-02-PLAN.md — DEPS-01a + DEPS-01c: production build + before/after bundle delta (D-02) + dist residual-string grep + Karma floors + manual Bootstrap-interaction smoke test (D-01) (wave 2, depends on 104-01)

**UI hint**: yes

### Phase 105: Font Awesome to Phosphor Migration

**Goal**: Every `fa-*` icon class usage in Angular templates is replaced with its `@phosphor-icons/web` equivalent, the `font-awesome` 4.7 package is removed from `package.json`, and no icon renders missing or visually degraded — only one icon library ships in the production bundle.
**Depends on**: Phase 104
**Requirements**: DEPS-01b
**Success Criteria** (what must be TRUE):

  1. A complete inventory of all `fa-*` class usages in `src/angular/src/` templates (`.html` files and inline templates in `.ts` files) is documented; every usage is mapped to an explicit Phosphor equivalent before any code change lands (DEPS-01b).
  2. Every former `fa-*` class is replaced with its Phosphor equivalent (`ph ph-*` or `ph-bold ph-*` as appropriate); a grep over the built dist and source confirms zero remaining `fa-` class strings in production-relevant files (DEPS-01b).
  3. `font-awesome` is removed from `src/angular/package.json`; `npm install` and `ng build --configuration production` complete cleanly; the Font Awesome CSS and font files are absent from the production bundle (DEPS-01b).
  4. A visual smoke test (dev server or screenshot comparison) confirms every icon location that previously rendered an `fa-*` icon now renders a visible Phosphor icon of comparable intent — no blank squares, no missing glyphs, no layout shifts (DEPS-01b).
  5. CI is green on amd64 + arm64 (Angular unit + E2E); Karma `check.global` floors (stmts/branches/fns/lines 83/68/79/83) hold or rise; Python `fail_under` ≥ 88 unchanged; production bundle size is equal to or smaller than the Phase 104 baseline. No release/tag/version work in this phase.

**Plans**: 4 plans (3 waves)
- [x] 105-01-PLAN.md — D-01: complete 39-class fa→ph mapping table + 8-ambiguous-icon user sign-off checkpoint (gates ambiguous-icon code) + D-07 BEFORE bundle baseline (wave 1, leaf, autonomous:false) — completed 2026-06-01
- [x] 105-02-PLAN.md — DEPS-01b: migrate the files cluster (dashboard-log-pane/stats-strip/transfer-row/transfer-table/bulk-actions-bar) incl. the net-new .ph-spin CSS rule + corrected ph-prohibit + 3 specs (wave 2, depends 105-01)
- [x] 105-03-PLAN.md — DEPS-01b: migrate the settings/logs/main clusters across all 5 edit layers, keeping coordinated dynamic-binding edits (options-list.ts + {{icon}} prefix; NAV_ICONS + [ngClass]) together, incl. corrected ph-computer-tower + notification-bell spec (wave 2, depends 105-01)
- [x] 105-04-PLAN.md — DEPS-01b: D-06 closing act — drop font-awesome from package.json + both angular.json styles lines + lock regen, AFTER build + dist/source residual grep + D-07 bundle delta + Karma floors + D-04 dev-server smoke test (wave 3, depends 105-02+105-03, autonomous:false)

**UI hint**: yes

### Phase 106: Mock-Fixture Bundle Hygiene

**Goal**: The development-only mock-model fixture data is fully excluded from the production bundle — `USE_MOCK_MODEL` becomes a build-time environment flag, the fixture files move to a non-service directory, and Angular `fileReplacements` ensures the mock data is tree-shaken from production output while the dev-mode toggle still works when the env flag is set.
**Depends on**: Phase 105
**Requirements**: DEPS-02
**Success Criteria** (what must be TRUE):

  1. `USE_MOCK_MODEL` is removed as a hardcoded class field from `view-file.service.ts` and replaced with an import from `src/angular/src/environments/environment.ts`; `environment.prod.ts` sets the flag to `false` (DEPS-02).
  2. `mock-model-files.ts` and `screenshot-model-files.ts` are relocated out of `services/files/` (e.g. to `src/angular/src/app/tests/fixtures/`) and imported only behind the environment-flag branch; `src/angular/angular.json` includes a `fileReplacements` entry that swaps in a stub or omits the fixture files entirely in the production configuration (DEPS-02).
  3. A production build (`ng build --configuration production`) produces a dist that contains none of the mock data — confirmed by grepping for a distinctive string from `mock-model-files.ts` (e.g. a mock filename literal) in the bundled JS output (DEPS-02).
  4. A development build (`ng build` or `ng serve` without `--configuration production`) with the env flag enabled correctly renders mock file rows in the dashboard, confirming the dev-mode path still functions end-to-end (DEPS-02).
  5. CI is green on amd64 + arm64 (Angular unit + E2E); Karma `check.global` floors (stmts/branches/fns/lines 83/68/79/83) hold or rise; Python `fail_under` ≥ 88 unchanged; production bundle size is measurably smaller than the Phase 105 baseline (mock data removed). No release/tag/version work in this phase.

**Plans**: 2 plans (2 waves)
- [x] 106-01-PLAN.md — DEPS-02 mechanism + autonomous proof: add `useMockModel` env flag (both env files), repoint `view-file.service.ts` to `environment.useMockModel`, `git mv` `mock-model-files.ts` → `tests/fixtures/`, add empty prod stub, second `angular.json` production `fileReplacements` entry, delete dead `screenshot-model-files.ts`; then AFTER prod build + bundle delta + dist absence-grep (`A Really Cool Video About Cats`) + Karma floors (wave 1)
- [x] 106-02-PLAN.md — DEPS-02 COMPAT half: dev-mode smoke-test checkpoint — `ng serve` with `useMockModel: true` renders mock rows from the relocated fixture (wave 2, depends 106-01, autonomous:false)

**UI hint**: yes

### Phase 107: MP-Logger Spawn Safety

**Goal**: The `MultiprocessingLogger` queue is created from a shared `spawn`-compatible multiprocessing context so the logger works correctly on both `fork` (Linux default) and `spawn` (macOS default) start methods, and the three previously-failing spawn-context analog tests pass on both platforms.
**Depends on**: Phase 106 (slice 3 complete — green CI, all floors held)
**Requirements**: INFRA-01
**Success Criteria** (what must be TRUE):

  1. `python/common/multiprocessing_logger.py` creates its internal queue via a shared `spawn`-compatible `multiprocessing` context (e.g. `multiprocessing.get_context("spawn").Queue()` or equivalent), so a queue handed to a `spawn`-started child no longer raises `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context` (INFRA-01).
  2. The three `MultiprocessingLogger` analog tests that previously required skipping or failed on macOS (spawn context) now run and pass without modification to the test code; the fix is entirely in the production module (INFRA-01).
  3. Existing `fork`-based logging behavior is unchanged — the Python test suite (including all existing `MultiprocessingLogger` tests) still passes on Linux (fork default); no test is deleted or skipped to accommodate the fix (INFRA-01, COMPAT).
  4. **Cross-cutting (COMPAT):** no change to observable logging output, log levels, log destinations, or any public `MultiprocessingLogger` API. CI green on amd64 + arm64; Python `fail_under` ≥ 88 holds or rises (3 previously-uncounted tests now counted; coverage holds or increases); Angular and E2E suites unaffected. No release/tag/version work in this phase.

**Plans**: 1 plan (1 wave)
- [x] 107-01-PLAN.md — INFRA-01: create the MultiprocessingLogger queue from a stored spawn-compatible context (get_context("spawn").Queue) and promote the three analog tests' process_1 closures to module-scope spawn targets launched via that context (wave 1, autonomous)

### Phase 108: Config + Handler Refactors

**Goal**: `Config` secret-field discovery is fully declarative — each secret field carries `secret=True` in its `PROP` declaration and the encrypt/decrypt loops iterate property metadata instead of a hand-maintained tuple — and the five per-action HTTP handlers share a single `_dispatch_command(...)` scaffold eliminating the duplicated boilerplate.

> **Scope amendments (2026-06-01, user-approved during plan-phase review):**
> - **Redact path descoped from ARCH-02.** The API-response *redaction* path (`web/serialize/serialize_config.py` `_SENSITIVE_FIELDS`) is an **independent, intentional superset** of the 5-field encrypt set — it also redacts the Lftp connection fields `remote_address`/`remote_username`/`remote_path`, which are NOT encrypted-at-rest and NOT secrets. Coupling redaction to the `secret=True` encryption metadata would either drop those 3 from redaction (info-disclosure regression) or wrongly encrypt them. Redaction (info-disclosure) and encryption-at-rest are deliberately kept as separate concerns. ARCH-02 therefore covers the **encrypt + decrypt** declarative discovery only; `_SENSITIVE_FIELDS` stays as-is. Criteria #1/#2 below are amended accordingly.
> - **Bulk loop descoped from ARCH-03 (per CONTEXT D-03).** `_dispatch_command` backs the five single-action handlers only; `_process_bulk_commands` stays byte-identical (its parallel-queue / per-file-timeout / partial-failure semantics must not change). CONCERNS.md lists bulk sharing the helper as optional. Criterion #4 below is amended accordingly.
**Depends on**: Phase 107
**Requirements**: ARCH-02, ARCH-03
**Success Criteria** (what must be TRUE):

  1. Each of the five secret fields (`api_token`, `webhook_secret`, `sonarr_api_key`, `radarr_api_key`, `remote_password`) has `secret=True` in its `PROP` declaration; the `_SECRET_FIELD_PATHS` hand-maintained tuple (or equivalent) is removed; the encrypt and decrypt code paths discover secret fields dynamically from property metadata and cover exactly the same set of fields as before — no field is silently added or dropped (ARCH-02). *(Redaction is out of scope per the goal's scope amendment — `_SENSITIVE_FIELDS` is an independent superset and stays as-is.)*
  2. A new secret field can be added by declaring it `secret=True` in its `PROP` without touching any other file; the encrypt/decrypt paths pick it up automatically — verified by adding a temporary `secret=True` field in a test and confirming the dynamic discovery API surfaces it and it round-trips through Fernet encryption (ARCH-02).
  3. Existing plaintext and Fernet-encrypted config files load, round-trip, and redact identically before and after the refactor — no on-disk format change, no behavioral change for any currently-encrypted field (ARCH-02, COMPAT).
  4. A shared `_dispatch_command(action, file_name, success_msg, *, guard=False)` helper (or equivalent) is extracted in `web/handler/controller.py` and used by all five `__handle_action_*` methods; the duplicated 15-line scaffold is gone from each individual handler (ARCH-03). *(The bulk-action loop is explicitly deferred per the goal's scope amendment / CONTEXT D-03 — `_process_bulk_commands` stays byte-identical and does NOT route through the helper.)*
  5. Every single-action and bulk-action endpoint (`/server/command/queue`, `/stop`, `/extract`, `/delete_local`, `/delete_remote`, and their `/bulk` equivalents) returns the same success/partial-failure HTTP response shapes and status codes as before the refactor — confirmed by the existing integration test suite staying green (ARCH-03, COMPAT). CI green on amd64 + arm64; Python `fail_under` ≥ 88 holds or rises; no test deleted. No release/tag/version work in this phase.

**Plans**: 2 plans (1 wave — independent, disjoint files, both autonomous)
- [x] 108-01-PLAN.md — ARCH-02: extend `InnerConfig.PropMetadata` with a `secret` flag, mark the five secret PROPs `secret=True`, build a dynamic `secret_fields()` discovery API (3-tuple `(attr, field, ini_section)`, section derived structurally from the owning subclass), repoint config.py encrypt/decrypt loops + seedsyncarr.py startup hook, delete `_SECRET_FIELD_PATHS` (no alias); new auto-discovery test + Fernet round-trip suite stays green (wave 1, autonomous)
- [x] 108-02-PLAN.md — ARCH-03: extract `_dispatch_command(action, file_name, success_msg, *, guard=False)` in `web/handler/controller.py`, collapse the five `__handle_action_*` scaffolds to one-line delegates (guard=True for extract/delete_local/delete_remote), leave the bulk path byte-identical; existing single-action + integration suites pass unmodified (wave 1, autonomous)

### Phase 109: Controller Decomposition

**Goal**: The `Controller` god-class (`python/controller/controller.py`, ~1115 lines) is decomposed into cohesive single-responsibility collaborators — the public surface the rest of the app depends on (constructor, `start`/`exit`, command entry points, the model the web layer reads) is preserved unchanged, and the full pre-refactor test suite stays green throughout.
**Depends on**: Phase 108
**Requirements**: ARCH-01
**Success Criteria** (what must be TRUE):

  1. The `controller` package contains clearly-named collaborator modules (e.g. a command-dispatch module, an auto-delete lifecycle module, a model/scan pipeline coordinator) each with a single coherent responsibility; no single new module exceeds ~350 lines; `controller.py` itself is thinned to a facade or coordinator that delegates to these collaborators (ARCH-01).
  2. The public API the web layer depends on is preserved exactly: the `Controller` constructor signature, `start()`, `exit()`, all command entry-point method names, and the model-access interface (`get_model_files()` or equivalent) are unchanged — no file outside the `controller` package requires modification (ARCH-01, COMPAT).
  3. The full pre-refactor Python test suite passes without modification or deletion — no test is changed to accommodate the decomposition; all existing `Controller` integration and unit tests continue to exercise the same observable behaviors as before (ARCH-01, COMPAT).
  4. Thread-safety invariants are preserved — the `__model_lock`, `__auto_delete_lock`, and the documented "release lock before subprocess spawn" contract are maintained across the decomposition; no new lock acquisition ordering is introduced that could create a deadlock (ARCH-01).
  5. **Cross-cutting (COMPAT):** no user-observable behavior change, no HTTP-contract change, no on-disk config/persist format change. CI green on amd64 + arm64 (Python primary; Angular + E2E unaffected but must stay green); Python `fail_under` ≥ 88 holds or rises; no test deleted. No release/tag/version work in this phase — the single `v1.3.0` tag is a milestone-end action for the orchestrator after the batched pre-release walkthrough.

**Plans**: 3 plans (3 waves — sequential per D-06; all touch controller.py)
- [x] 109-01-PLAN.md — ARCH-01: extract `command_processor.py` (the four `__handle_*_command` bodies → `CommandProcessor.handle()`); `__process_commands` stays on Controller and delegates after releasing `__model_lock` (wave 1, autonomous)
- [x] 109-02-PLAN.md — ARCH-01: extract `auto_delete_manager.py` (BFS pack-guard + coverage logic → `run_bfs_and_coverage`); `__schedule_auto_delete` + `__execute_auto_delete` stay on Controller as the lock harness, WR-02 ordering preserved verbatim (wave 2, depends_on 109-01, autonomous)
- [x] 109-03-PLAN.md — ARCH-01: extract `model_pipeline.py` (scan→build→diff→apply stages → `ModelPipeline.update_model`); `__update_model` thins to a delegate, accessors + `_should_update_capacity` + `_update_controller_status` + `__check_webhook_imports` stay on Controller; coordinator thinned toward ~350 lines (wave 3, depends_on 109-02, autonomous)

### Phase 110: Hostile-Reader Discovery Pass

**Goal**: A maintainer has a triaged, severity-ranked findings artifact that captures what a skeptical r/selfhosted engineer reviewing the public repo would flag — produced by a bounded discovery pass over the entry points, the project's existing tooling under launch framing, and the highest-traffic source files — with every finding explicitly marked "fold into a v1.4.0 fix phase" (with target phase) or "parked" (with one-line rationale). This phase **gates the fix scope** for Phases 111-112: it runs first so any genuinely high-visibility findings inform those phases before they are planned in detail.
**Depends on**: Phase 109 (v1.3.0 shipped — clean main, branch `launch-hardening` cut from it)
**Requirements**: SCAN-01, SCAN-02
**Success Criteria** (what must be TRUE):

  1. A written findings artifact exists that lists, organized by severity, what a skeptical engineer reviewing the public repo would flag — produced by reading the entry points (`seedsyncarr.py`, the web app, the Angular shell), running the project's existing tooling under launch framing (ruff whole-tree, Semgrep/Shield, dependency audit), and skimming the highest-traffic source files (SCAN-01).
  2. Each finding in the artifact carries an explicit disposition: either "fold into a v1.4.0 fix phase" naming the target phase (111 CFG or 112 GUARD), or "parked" with a one-line rationale — so scope decisions are traceable rather than implicit (SCAN-02).
  3. The pass is bounded — it does not turn into an open-ended refactor hunt; findings that are real but low-visibility for a launch reader are parked with rationale (e.g. the already-deferred shutdown-readiness Event, StreamQueue non-atomic drop), consistent with the milestone's explicit Out-of-Scope and Future-Requirements decisions (SCAN-02, D-3).
  4. The artifact's fold-in list is reconciled against the already-scoped GUARD/CFG requirements: any high-visibility finding not already covered by a v1.4.0 requirement is surfaced to the maintainer as a scope decision (add to a fix phase, or park) before Phases 111-112 are planned (SCAN-02).

**Plans**: 1 plan (1 wave)
- [x] 110-01-PLAN.md — SCAN-01 + SCAN-02: run the read-only audit tool suite (ruff whole-tree, Semgrep/Shield + gitleaks, pip-audit, npm audit) + the AppProcess red test, read entry points/high-traffic files/README under launch framing, confirm the six pre-named fix items, and synthesize `110-FINDINGS.md` (severity rollup + per-finding FOLD/PARK disposition); maintainer findings checkpoint (autonomous:false)

> **Gating note:** This phase has a findings checkpoint (autonomous:false is appropriate) — the maintainer reviews the triaged artifact and confirms the fold-in vs parked dispositions before Phases 111-112 are planned in detail. No production code changes land in this phase; it produces the discovery artifact only.

### Phase 111: Config-Set Endpoint Migration

**Goal**: The `/server/config/set` endpoint is migrated from the credential-leaking `GET /server/config/set/{section}/{key}/{value}` path-segment form to a `POST` with a JSON body (`{section, key, value}`) — a **hard cutover** (the GET path is fully removed, not deprecated-but-live) — so credential values no longer travel in URLs, server access logs, browser history, or reverse-proxy logs. The change spans the backend handler, the Angular `ConfigService`, and the E2E setup script + page objects. This is the one breaking HTTP-contract change in v1.4.0; the on-disk persisted config format is unchanged.
**Depends on**: Phase 110 (findings dispositions confirmed — any config-surface finding folded in here is known before planning)
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04
**Success Criteria** (what must be TRUE):

  1. A client sets a config value by sending a `POST` to `/server/config/set` with a JSON body (`{section, key, value}`); credential values no longer appear as URL path segments anywhere — confirmed by inspecting server access logs, and by the absence of value-bearing path segments in the route (CFG-01).
  2. The legacy `GET /server/config/set/{section}/{key}/{value}` route no longer exists — a request to it returns a not-found / method-not-allowed response; the credential-leaking path is fully removed, not deprecated-but-live (CFG-02).
  3. The Settings page saves configuration successfully end-to-end against the new POST endpoint — the Angular `ConfigService` (`src/angular/src/app/services/settings/config.service.ts`) and the E2E setup script (`src/docker/test/e2e/configure/setup_seedsyncarr.sh`) + page objects (`src/e2e/tests/settings.page.ts`) all use POST, and a saved setting round-trips and persists across a reload (CFG-03).
  4. Existing on-disk config files (plaintext and Fernet-encrypted) load unchanged after the migration — there is no config-format change and no user migration step for saved settings; the migration is purely the HTTP transport (CFG-04).
  5. **Cross-cutting (COMPAT + CI):** the POST endpoint reuses the existing config/set rate-limit (60/60s) and any existing auth/redaction behavior; CI is green on amd64 + arm64 (Python + Angular + E2E — the E2E setup must complete against the new endpoint); Python `fail_under` ≥ 88 holds or rises; Karma `check.global` floors 83/68/79/83 hold or rise. No release/tag/version work in this phase.

**Plans**: 3 plans (2 waves)

Plans:
- [x] 111-01-PLAN.md — Backend contract: POST /server/config/set handler + GET route removal + migrated Python tests (wave 1; CFG-01/02/04)
- [x] 111-02-PLAN.md — Angular client: RestService.post body + ConfigService.set POST + migrated spec (wave 2; CFG-01/03)
- [x] 111-03-PLAN.md — E2E: setup-script curls + Playwright page objects/fixtures to POST (wave 2; CFG-01/03)

**UI hint**: yes

### Phase 112: Defensive Guards & Code Hardening

**Goal**: The remaining "a hostile reader will notice this" code items are closed — the app stops being *quietly* unsafe (loud startup warnings for insecure-by-silence defaults), a silently-swallowed local-delete failure now leaves a log signal, the currently-failing `AppProcess` spawn-context test goes green via a production fix, and two cheap repo-hygiene tells are fixed. All default *behavior* stays backward-compatible — these guards add visibility and a test fix, not breaking changes. Any high-visibility finding folded in from Phase 110 that fits this cluster lands here.
**Depends on**: Phase 110 (findings dispositions confirmed); independent of Phase 111
**Requirements**: GUARD-01, GUARD-02, GUARD-03, GUARD-04, GUARD-05, GUARD-06
**Success Criteria** (what must be TRUE):

  1. When the server binds to a non-loopback interface with no `api_token` configured, the operator sees a prominent startup warning that API endpoints are unauthenticated; and when the webhook endpoint is reachable with no `webhook_secret` set and `webhook_require_secret` off, the operator sees a prominent startup warning that webhooks are unauthenticated — in both cases the default behavior is unchanged, the unsafe posture is simply no longer silent (GUARD-01, GUARD-02).
  2. When a local delete (`shutil.rmtree`) partially fails, the failure is logged with context rather than silently swallowed — `ignore_errors=True` is replaced with explicit error handling so a failed delete leaves an observable signal in the logs; the delete-path tests assert the logged-failure signal (GUARD-03).
  3. The full Python test suite passes under both `fork` and `spawn` start methods — the previously-failing `test_app_process.py::test_process_with_long_running_thread_terminates_properly` now passes with **no test deleted or skipped**, because `AppProcess` creates its `Queue()`/`Event()` from a spawn-compatible multiprocessing context (same fix pattern as the shipped INFRA-01 MP-logger fix) (GUARD-04).
  4. Tooling/run artifacts (`.orchestrator.json`, `.playwright-mcp/`) are git-ignored so a repo browser never sees stray local artifacts and they cannot be accidentally committed — `git check-ignore` returns success for both (GUARD-05).
  5. When startup falls back to the legacy `~/.seedsync` config directory because the configured `--config_dir` is absent, the operator sees a loud one-time warning (or the fallback is gated behind an explicit opt-in) rather than silently loading a pre-fork config (GUARD-06).
  6. **Cross-cutting (COMPAT + CI):** no default-behavior change beyond added warnings/logging and the test fix; existing config files and on-disk persist formats load unchanged. CI green on amd64 + arm64; Python `fail_under` ≥ 88 holds or rises (GUARD-04 brings a previously-failing test green; coverage holds or increases); no test deleted or skipped. No release/tag/version work in this phase.

**Plans**: 3 plans (1 wave — all file-disjoint, fully parallel)
- [x] 112-01-PLAN.md — GUARD-04 (AppProcess `__getstate__`/`__setstate__` spawn-safe pickling; red test goes green under spawn + fork) + GUARD-05 (`.gitignore` `.orchestrator.json` + `.playwright-mcp/`) (wave 1)
- [x] 112-02-PLAN.md — GUARD-01 (`[SECURITY]` prominence prefix) + GUARD-02 (accept-any-caller warning suppressed in fail-closed `require_secret=True` state) + GUARD-06 (legacy `~/.seedsync` fallback warning emitted through the configured logger via Option A flag-threading), test-first (wave 1)
- [x] 112-03-PLAN.md — GUARD-03 (replace `ignore_errors=True` with `try/except OSError` + `logger.exception` + `sanitize_log_value`, best-effort preserved; new `TestDeleteLocalProcess` failure-path test), test-first (wave 1)

### Phase 113: Presentation & Launch Readiness

**Goal**: The project's public-facing surface is rebuilt so its genuine quality is evident in 30 seconds to a skeptical r/selfhosted visitor — a cynical-reader teardown plus a codex adversarial pass produce the hostile critique first, then a README / SECURITY.md / community-health / release-notes rewrite addresses it. Playwright screenshots are captured at the milestone-end walkthrough against the NAS-deployed branch build (not during phase execution), and copy-paste-ready repo-metadata text is drafted for the maintainer to apply manually. This track is independent of the code phases (110-112) and is sequenced last for a clean single-threaded execution order.
**Depends on**: Phase 112 (sequenced last; presentation reflects the hardened code from 111-112, so the README/SECURITY.md claims are accurate to the shipped state)
**Requirements**: LAUNCH-01, LAUNCH-02, LAUNCH-03, LAUNCH-04, LAUNCH-05, LAUNCH-06
**Success Criteria** (what must be TRUE):

  1. A maintainer can read a written "cynical r/selfhosted reader" teardown of the current presentation (README, positioning, first impression), and a codex adversarial pass over the drafted README/docs flags technical-claims accuracy, broken/incomplete install steps, and unsupported assertions — both critiques captured **before** the rewrite is finalized (LAUNCH-01).
  2. A visitor reading the README understands what SeedSyncarr is within seconds — a clear one-line description, an above-the-fold screenshot, an honest feature list, accurate install/quickstart instructions, the security posture stated plainly as a selling point, and a short note on the relationship to the original SeedSync fork (LAUNCH-02).
  3. The repo includes a `SECURITY.md` with a vulnerability-reporting policy and a short honest threat-model note (what is protected and what the opt-in security knobs are for), plus accurate community-health files — `CONTRIBUTING.md`, issue templates, a PR template, and a correct `LICENSE` — so their absence does not read as "not a serious project" (LAUNCH-04, LAUNCH-05).
  4. A clean v1.4.0 release-notes entry exists so the releases page is presentable, and copy-paste-ready GitHub repo-metadata text (About description, topics/tags, homepage link) is drafted for the maintainer to apply manually (LAUNCH-06).
  5. **Walkthrough-deferred (LAUNCH-03):** the README/docs screenshots showing the redesigned UI are captured via Playwright **at the milestone-end walkthrough against the NAS-deployed branch build** — not during phase execution — and any staged state is flagged so nothing misrepresents real behavior. **Manual maintainer actions outside phase execution:** applying the drafted repo-metadata (part of LAUNCH-06) and the actual git push / publish are done by the maintainer, not inside this phase.

**Plans**: 4 plans (3 waves)
- [x] 113-01-PLAN.md — First-draft README/SECURITY/CONTRIBUTING/CoC/CHANGELOG (claim-accurate to shipped code) + mechanical LICENSE.txt→LICENSE rename + README badge/link fix (wave 1)
- [x] 113-02-PLAN.md — Cynical-reader teardown artifact (113-TEARDOWN.md) of the current presentation (wave 1, parallel)
- [x] 113-03-PLAN.md — Codex adversarial content pass over the drafts (113-CODEX-PASS.md) (wave 2, depends on 113-01)
- [ ] 113-04-PLAN.md — Finalize docs addressing both critiques + wire 3 canonical screenshot refs (capture deferred to walkthrough) + repo-metadata draft (113-REPO-METADATA.md) (wave 3, depends on 113-01/02/03)

**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-5. UI Styling | v1.0 | 8/8 | Complete | 2026-02-03 |
| 6-8. Dropdown & Form | v1.1 | 4/4 | Complete | 2026-02-04 |
| 9. UI Cleanup | v1.2 | 1/1 | Complete | 2026-02-04 |
| 10-11. Polish & Clarity | v1.3 | 5/5 | Complete | 2026-02-04 |
| 12-14. Sass @use | v1.4 | 3/3 | Complete | 2026-02-08 |
| 15-19. Backend Testing | v1.5 | 8/8 | Complete | 2026-02-08 |
| 20-21. CI Cleanup | v1.6 | 2/2 | Complete | 2026-02-10 |
| 22-25. Sonarr | v1.7 | 8/8 | Complete | 2026-02-10 |
| 26-28. Radarr + Webhooks | v1.8 | 5/5 | Complete | 2026-02-11 |
| 29-32. Dark Mode | v2.0 | 6/6 | Complete | 2026-02-12 |
| 33-38. Terminal UI | v3.0 | 12/12 | Complete | 2026-02-17 |
| 39-46. Harden & Fix | v3.1 | 25/25 | Complete | 2026-02-24 |
| 47-51. Security Hardening II | v3.2/M002 | 10/10 | Complete | 2026-03-22 |
| M001-M010 Slices | M001-M010 | 29 slices | Complete | 2026-03-28 |
| 52. Dependency Fixes & CI | v4.0.3 | 1/1 | Complete | 2026-04-08 |
| 53-61. SeedSyncarr Rebrand | v1.0.0 | 14/14 | Complete | 2026-04-13 |
| 62-74. UI Redesign | v1.1.0 | 30/30 | Complete | 2026-04-19 |
| 75-82. Post-Redesign Cleanup | v1.1.1 | 22/22 | Complete | 2026-04-23 |
| 83-86. Test Suite Audit | v1.1.2 | 6/6 | Complete | 2026-04-24 |
| 87-96. Test & Quality Hardening | v1.2.0 | 23/23 | Complete | 2026-04-28 |
| 97-100. Test Coverage Gaps (Slice 1) | v1.3.0 | 10/10 | Complete | 2026-05-31 |
| 101-103. Known Bugs + Security (Slice 2) | v1.3.0-s2 | 9/9 (101: 6/6, 102: 1/1, 103: 2/2) | Complete | 2026-06-01 |
| 104. Light Dependency Removals (Slice 3) | v1.3.0-s3 | 2/2 | Complete | 2026-06-01 |
| 105. Font Awesome to Phosphor (Slice 3) | v1.3.0-s3 | 4/4 | Complete   | 2026-06-01 |
| 106. Mock-Fixture Bundle Hygiene (Slice 3) | v1.3.0-s3 | 2/2 | Complete   | 2026-06-01 |
| 107. MP-Logger Spawn Safety (Slice 4) | v1.3.0-s4 | 1/1 | Complete   | 2026-06-01 |
| 108. Config + Handler Refactors (Slice 4) | v1.3.0-s4 | 2/2 | Complete   | 2026-06-01 |
| 109. Controller Decomposition (Slice 4) | v1.3.0-s4 | 3/3 | Complete   | 2026-06-02 |
| 110. Hostile-Reader Discovery Pass | v1.4.0 | 1/1 | Complete   | 2026-06-02 |
| 111. Config-Set Endpoint Migration | v1.4.0 | 3/3 | Complete   | 2026-06-02 |
| 112. Defensive Guards & Code Hardening | v1.4.0 | 3/3 | Complete   | 2026-06-02 |
| 113. Presentation & Launch Readiness | v1.4.0 | 3/4 | In Progress|  |

---

*Last updated: 2026-06-02 — Milestone v1.4.0 (Launch-Hardening for Public Release) roadmap appended: Phases 110-113 derived from the 18 v1.4.0 requirements (SCAN-01/02, CFG-01..04, GUARD-01..06, LAUNCH-01..06). Two disjoint tracks (code + presentation) plus the cross-cutting config-set GET→POST cutover. Phase 110 (SCAN) gates fix scope and runs first; 111 (CFG) is the one breaking change; 112 (GUARD) clusters the defensive fixes incl. the AppProcess spawn fix; 113 (LAUNCH) is the presentation rebuild, sequenced last. Branch `launch-hardening`; single `v1.4.0` tag is a milestone-end maintainer action after the NAS walkthrough + CI green + sign-off.*
