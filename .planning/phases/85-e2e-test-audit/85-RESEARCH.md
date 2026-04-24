# Phase 85: E2E Test Audit - Research

**Researched:** 2026-04-24
**Domain:** Playwright E2E spec staleness audit — 7 spec files, Playwright 1.48.x, Chromium
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| E2E-01 | Identify Playwright E2E specs with redundant or stale coverage | Full inventory of all 7 spec files and 37 test cases completed below; staleness determination by cross-referencing each spec against live Angular routes, components, and selectors |
| E2E-02 | Remove identified redundant E2E specs | Per-spec removal decision documented; removal protocol: delete individual `test()` blocks or full file if all cases are stale |
| E2E-03 | Verify all remaining E2E specs pass | Verification via `make run-tests-e2e` on amd64 in Docker; CI harness command documented |

</phase_requirements>

---

## Summary

Phase 85 is a bounded audit of 7 Playwright E2E spec files (37 total test cases) to identify and remove specs that either duplicate existing coverage or target UI patterns that no longer exist. The audit follows the same removal-only discipline as Phases 83 and 84: a spec is "stale" only if the UI surface it exercises has been deleted or the behavior is fully covered by a more specific spec.

**Primary finding: Zero stale specs exist by the Phase 83/84 D-01 definition.** Every spec file tests a live Angular route and live UI selectors. However, the audit reveals a meaningful coverage gap that the v1.1.1 E2E expansion left behind: no spec exercises the Logs page (`/logs`). The four app-level nav tests in `app.spec.ts` assert "Logs" appears in the nav, but no spec navigates to `/logs` and verifies anything about that page. This is a gap, not a staleness issue — it is out of scope per the audit mandate (no new tests written unless coverage drops).

**The `autoqueue.page.spec.ts` deserves scrutiny.** The spec exercises AutoQueue pattern CRUD, but the patterns add/remove buttons are conditionally disabled by `autoqueueEnabled && patternsOnly`. The E2E harness `setup_seedsyncarr.sh` sets `autoqueue/patterns_only/true` but does NOT set `autoqueue/enabled/true`. If `autoqueue.enabled` defaults to `None` (falsy), the "Add" and "Remove" buttons will be disabled in the harness, making `addPattern()` a no-op click on a disabled button. This is the only spec whose pass/fail status in the live CI harness is uncertain from static analysis alone — it requires a CI run to confirm.

**Primary recommendation:** Execute the staleness audit as a read-only pass, produce the zero-removal inventory table (parallel to Phase 84), run the E2E harness to confirm all specs pass, and document findings. Do not write new tests (Logs page gap is out of scope). If `autoqueue.page.spec.ts` fails due to the disabled-button problem, that is a pre-existing CI issue to document, not fix in this phase.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Spec staleness determination | Developer workstation | — | Static analysis: cross-reference spec selectors against live Angular HTML templates |
| E2E test execution / harness | Docker (amd64 + arm64) | — | `make run-tests-e2e` runs full Docker compose harness; no local run path without a live app instance |
| Spec pass/fail verification | Docker CI harness | — | `npx playwright test` inside Dockerfile; requires live app + remote SFTP container |
| CSP enforcement verification | CI harness (csp-listener fixture) | — | The csp-listener fixture fails any spec that triggers a CSP violation |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @playwright/test | ^1.48.0 (installed: 1.59.1 on npm registry) | E2E test framework | [VERIFIED: src/e2e/package.json + npm view] |
| typescript | ^5.3.0 | Type checking for specs | [VERIFIED: src/e2e/package.json] |
| ts-node | ^10.9.2 | TypeScript execution | [VERIFIED: src/e2e/package.json devDependencies] |
| @types/node | ^20.10.0 | Node.js type defs | [VERIFIED: src/e2e/package.json] |

### Infrastructure

| File | Purpose |
|------|---------|
| `src/e2e/playwright.config.ts` | Playwright config — baseURL, workers=1, fullyParallel=false, Chromium only |
| `src/e2e/urls.ts` | Route constants: `Paths.DASHBOARD`, `Paths.SETTINGS`, `Paths.ABOUT`, `Paths.LOGS` |
| `src/docker/test/e2e/Dockerfile` | node:22-slim, installs Playwright + Chromium, copies specs |
| `src/docker/test/e2e/compose.yml` | Orchestrates: `tests` (Playwright), `remote` (SFTP), `configure` (initial app config), `myapp` (app under test) |
| `src/docker/test/e2e/configure/setup_seedsyncarr.sh` | Configures app for testing: sets lftp, remote SSH, `autoqueue/patterns_only/true` |
| `src/docker/test/e2e/run_tests.sh` | Entry point: waits for server up + remote scan, then runs `npx playwright test` |

### Test Execution Commands

| Purpose | Command |
|---------|---------|
| CI E2E run (amd64) | `make run-tests-e2e STAGING_REGISTRY=... STAGING_VERSION=... SEEDSYNCARR_ARCH=amd64` |
| CI E2E run (arm64) | `make run-tests-e2e STAGING_REGISTRY=... STAGING_VERSION=... SEEDSYNCARR_ARCH=arm64` |
| Quick local (requires live app) | `cd src/e2e && npx playwright test` (with `APP_BASE_URL` set) |

**Note:** There is no local E2E run path without a live Docker app stack. The E2E suite requires the full Docker compose environment (app + remote container + configure container). `make run-tests-e2e` requires a pre-built `STAGING_VERSION` image. [VERIFIED: Makefile, compose.yml, run_tests.sh]

---

## Complete Staleness Audit

**This is the core research output.** All 7 spec files cross-referenced against live Angular routes, components, and HTML selectors on 2026-04-24.

### Spec File Inventory

| Spec File | Test Count | Routes Tested | Selectors Live? | Verdict |
|-----------|-----------|---------------|----------------|---------|
| `app.spec.ts` | 3 | `/` (root redirect) | `#top-nav .nav-link`, `.nav-link.active` — live in `header.component.html` | LIVE |
| `about.page.spec.ts` | 2 | `/about` | `.version-badge` — live in `about-page.component.html` | LIVE |
| `settings.page.spec.ts` | 1 | `/settings` | `.nav-link.active` — live in `header.component.html` | LIVE |
| `settings-error.spec.ts` | 1 | `/settings` | `fieldset`, `.test-result`, `text-danger` — live in `settings-page.component.html` | LIVE |
| `autoqueue.page.spec.ts` | 3 | `/settings` | `.pattern-section`, `.pattern-chip`, `.pattern-chip-text`, `.pattern-chip-remove`, `.pattern-add`, `.btn-pattern-add` — live in `settings-page.component.html` | LIVE (selectors exist; see Pitfall 1) |
| `csp-canary.spec.ts` | 1 | `/` | Uses `csp-listener` fixture; no app selectors | LIVE — MUST KEEP (Success Criterion 3) |
| `dashboard.page.spec.ts` | 26 | `/dashboard` | All dashboard selectors live: `.transfer-table`, `.segment-filters`, `app-bulk-actions-bar`, `app-transfer-row`, `.cell-name`, `.cell-status`, `.status-badge`, `.bell-btn`, `.bell-notif` | LIVE — MUST KEEP (Success Criterion 3) |

**Result: ZERO stale spec files.** [VERIFIED: cross-reference against Angular templates]

### Detailed Per-File Assessment

#### `app.spec.ts` (3 tests) — KEEP ALL
- `should have right title` — checks `page.title() === 'SeedSyncarr'`; the Angular app title is set in `index.html`; current title is "SeedSyncarr". [VERIFIED: live]
- `should have all the nav links` — asserts Dashboard, Settings, Logs, About; `header.component.html` renders exactly these 4 links. [VERIFIED: routes.ts, header.component]
- `should default to the dashboard page` — asserts root redirect lands on Dashboard active link; Angular routing default path is `/dashboard`. [VERIFIED: routes.ts]

Assessment: Not redundant — these are smoke-level navigation tests with no equivalent coverage elsewhere.

#### `about.page.spec.ts` (2 tests) — KEEP ALL
- `should have About nav link active` — nav active state check for About; not covered by app.spec.ts.
- `should have the right version` — asserts `.version-badge` matches `/^v\d+\.\d+\.\d+$/`; live selector. [VERIFIED: about-page.component.html]

Assessment: Not redundant — the version badge test is unique and the about nav test rounds out per-page navigation coverage.

#### `settings.page.spec.ts` (1 test) — KEEP
- `should have Settings nav link active` — minimal smoke test for /settings navigation.

Assessment: Not redundant in isolation; however overlaps with `settings-error.spec.ts` which also navigates to /settings. The nav-link-active check is light but not strictly duplicative since `settings-error.spec.ts` focuses on the Sonarr error state. Keep.

#### `settings-error.spec.ts` (1 test) — KEEP
- `should show error when Sonarr connection fails` — configures Sonarr with invalid URL, clicks "Test Connection", asserts `text-danger` class. Tests a live behavior (`clickTestSonarrConnection` → `/server/sonarr/test` API call → error state).

Assessment: Not redundant — no other spec tests the Sonarr connection error UI. The selector `fieldset` + `getByText('Sonarr URL')` + `.test-result` are all live. [VERIFIED: settings-page.component.html]

#### `autoqueue.page.spec.ts` (3 tests) — KEEP (WITH CAVEAT — see Pitfall 1)
- `should have Settings nav link active` — minor overlap with settings.page.spec.ts. Not stale.
- `should add and remove patterns` — exercises full CRUD cycle.
- `should list existing patterns in alphabetical order` — page.reload() + alphabetical sort assertion.

Assessment: Selectors are live. The AutoQueue pattern section (`pattern-section`, `pattern-chip`, `btn-pattern-add`) is rendered by `settings-page.component.html` lines 204-238. [VERIFIED: filesystem]. The CRITICAL CAVEAT is in Pitfall 1 below.

#### `csp-canary.spec.ts` (1 test) — KEEP (MANDATORY per Success Criterion 3)
- Injects a script from `evil.example.com`, asserts CSP violation is detected. Uses `test.use({ allowViolations: true })` so it does not self-fail.
- This spec verifies the `csp-listener` fixture itself works. If removed, all other specs lose their CSP violation guard verification. [VERIFIED: csp-listener.ts, Phase 84 deferred item]

#### `dashboard.page.spec.ts` (26 tests) — KEEP ALL (MANDATORY per Success Criterion 3)
This is the core E2E harness. 26 tests across 3 `describe` blocks:
- Top-level `describe` (9 tests): nav active, file list, action bar show/hide, action button set, Queue/Stop enable state for DEFAULT, Done/Active segment expand, URL persistence for Done filter, invalid segment URL sanitization.
- `UAT-01: selection and bulk bar` (5 tests): selection accumulation, shift-range select, header select-all, bulk bar 5-action dispatch + Extract disabled, FIX-01 DELETED union behavior.
- `UAT-02: status filter and URL` (12 tests): 4 populated filter assertions (Pending, Downloaded, Failed, Deleted), 4 empty-state assertions (Syncing, Queued, Extracting, Extracted), 2 URL round-trip tests (parent reload, sub reload).

All selectors verified live. [VERIFIED: settings-page.component.html, dashboard.page.ts, app-transfer-row, bulk-actions-bar.component]

---

## Architecture Patterns

### System Architecture Diagram

```
playwright.config.ts (baseURL, workers=1, Chromium)
      │
      ├── Spec files (*.spec.ts) import:
      │     ├── fixtures/csp-listener.ts   — extends base test fixture with CSP violation detection
      │     ├── fixtures/seed-state.ts     — seeds file states via HTTP API (queue/stop/delete)
      │     └── *.page.ts page objects     — encapsulate selectors and navigation
      │
      │   Each spec test runs inside Docker compose:
      │
      ▼
[tests container]  →  HTTP → [myapp container :8800]
                             ↑
                     [configure container]  (one-shot: setup_seedsyncarr.sh)
                             │
[myapp container]  →  SFTP → [remote container :1234]
                              (9 fixture files: clients.jpg, testing.gif, etc.)
      │
      │ E2E harness: run_tests.sh
      │   1. Wait for server up (curl /server/status)
      │   2. Wait for remote scan done
      │   3. npx playwright test
      │
      ▼
CI Result: pass (exit 0) or fail (exit non-0) → make run-tests-e2e exit code
```

### Recommended Project Structure (unchanged)
```
src/e2e/
├── tests/
│   ├── fixtures/
│   │   ├── csp-listener.ts     # CSP violation test fixture
│   │   └── seed-state.ts       # State seeding helpers
│   ├── app.ts                  # Base App page object
│   ├── about.page.ts           # About page object
│   ├── autoqueue.page.ts       # AutoQueue page object
│   ├── dashboard.page.ts       # Dashboard page object (most complex)
│   ├── settings.page.ts        # Settings page object
│   ├── app.spec.ts             # Root/nav smoke tests
│   ├── about.page.spec.ts      # About page tests
│   ├── autoqueue.page.spec.ts  # AutoQueue CRUD tests
│   ├── csp-canary.spec.ts      # CSP enforcement canary (MUST KEEP)
│   ├── dashboard.page.spec.ts  # Dashboard + UAT-01 + UAT-02 (MUST KEEP)
│   ├── settings-error.spec.ts  # Sonarr error state test
│   └── settings.page.spec.ts   # Settings nav smoke test
├── playwright.config.ts
├── tsconfig.json
└── urls.ts
```

### Pattern 1: Staleness Determination (adapted from Phase 84 D-01)
**What:** A spec is stale if the Angular route it navigates to no longer exists, OR all UI selectors it uses are absent from the live HTML templates, OR it duplicates the exact same assertion already made by another spec.
**When to use:** Applied to all 7 spec files.
**Implementation:**
```typescript
// For each spec:
// 1. Extract the route(s) navigated to (Paths.DASHBOARD, etc.)
// 2. Verify route still exists in src/angular/src/app/routes.ts
// 3. Extract all CSS selectors used
// 4. grep for each selector in src/angular/src/app/**/*.component.html
// 5. If route is gone OR all selectors are absent → stale
// 6. If any selector duplicates another spec's assertion → evaluate redundancy
```

### Pattern 2: CSP Listener Fixture
**What:** All spec files import from `fixtures/csp-listener` not `@playwright/test` directly. The fixture auto-fails any test that triggers a CSP violation (unless `allowViolations: true`).
**When to use:** All specs already use this — do not change.
```typescript
// Source: csp-listener.ts [VERIFIED]
import { test, expect } from './fixtures/csp-listener';
// test.use({ allowViolations: true }); // only for csp-canary.spec.ts
```

### Pattern 3: State Seeding
**What:** UAT-01 and UAT-02 use `seedMultiple()` / `seedStatus()` from `fixtures/seed-state.ts` to drive files into specific states (DOWNLOADED, STOPPED, DELETED) before testing filter/selection behavior.
**When to use:** Any spec that needs files in non-DEFAULT states.
**Note:** The seed pipeline uses LFTP commands via HTTP API and polls SSE badge states. `STOPPED_SEED_RATE_LIMIT = '100'` (bytes/sec) throttles LFTP to allow stop to win the race.

### Anti-Patterns to Avoid
- **Removing based on quality:** A spec that is "simple" or tests obvious behavior is not stale by that alone. Only apply the staleness criteria.
- **Adding new tests in this phase:** The audit mandate is removal only. The Logs page coverage gap is acknowledged but out of scope.
- **Changing the Playwright version:** The package.json pins `^1.48.0`; the installed version in the E2E Docker image is determined by `npm install` at build time. Do not change the pin during this audit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Selector existence check | Custom AST parser | `grep -rn "selector" src/angular/src/app/**/*.html` | Shell grep is accurate for CSS class selectors in Angular templates |
| Route existence check | Custom Angular compiler | `cat src/angular/src/app/routes.ts` | Route file is a simple TypeScript list |
| Duplicate detection | Diff tool | Manual comparison of test assertions | 7 specs and 37 tests — manual review is tractable and accurate |

---

## Runtime State Inventory

Step 2.5: This is an audit/removal phase, not a rename/migration phase. No runtime state inventory is required.

---

## Common Pitfalls

### Pitfall 1: autoqueue.page.spec.ts May Be Broken by Disabled Buttons
**What goes wrong:** The `setup_seedsyncarr.sh` harness configures `autoqueue/patterns_only/true` but does NOT set `autoqueue/enabled/true`. In `settings-page.component.ts`, `autoqueueEnabled` is read from `config.autoqueue.enabled` (which defaults to `None` in Python). `None` is serialized as `null` in JSON. The Angular component sets `autoqueueEnabled = null` (falsy). The `btn-pattern-add` button has `[disabled]="!(commandsEnabled && newPattern && autoqueueEnabled && patternsOnly)"`. With `autoqueueEnabled = null`, the button is always disabled in the harness.

**Why it happens:** `setup_seedsyncarr.sh` predates the autoqueue merge into Settings. The original AutoQueue page may have had a different enable/disable flow.

**How to avoid:** Before declaring the spec stale or passing, run the CI harness and observe actual behavior. If the spec fails, document it as a pre-existing harness configuration bug (not introduced by this phase) and note it. **Do not fix the setup script in this phase** — that is out of scope. The spec selectors are live.

**Warning signs:** Playwright `addPattern()` calls `page.locator('.pattern-add input').fill(pattern)` (this works) then clicks `.btn-pattern-add` (this is a no-op on a disabled button). The pattern never appears, and `page.locator('.pattern-section .pattern-chip-text:has-text("${pattern}")').waitFor()` times out.

**Classification:** If the spec currently fails in CI, it is a pre-existing defect, not a staleness issue. The staleness audit verdict is still LIVE (selectors exist, route exists). Document the failure separately.

### Pitfall 2: settings.page.spec.ts Appears Redundant but Is Not
**What goes wrong:** `settings.page.spec.ts` has only 1 test: `should have Settings nav link active`. `autoqueue.page.spec.ts` has the same check (`should have Settings nav link active`). This looks like duplication.
**Why it happens:** Both navigate to `/settings` but test different aspects of the settings page.
**How to avoid:** Per the staleness definition, both tests are LIVE. The "nav link active" check is not truly unique — it is covered by `autoqueue.page.spec.ts`. However, removing `settings.page.spec.ts` would require an explicit redundancy determination under D-01 rules. Given the phase mandate is conservative (removal only for stale or fully-duplicated tests), the safest call is to keep both. The planner can document this as a candidate for removal if the criteria are explicitly loosened.

### Pitfall 3: No Local E2E Execution Path
**What goes wrong:** Attempting to run `npx playwright test` locally without the Docker app stack fails immediately — there is no app serving at `http://myapp:8800`.
**Why it happens:** The E2E suite requires the full Docker compose environment.
**How to avoid:** Use `make run-tests-e2e` with a pre-built staging image. Verification of E2E specs can ONLY be done via the full Docker CI harness. Plan tasks accordingly — the verification step requires Docker + a built image.

### Pitfall 4: arm64 E2E Requires a Push to Main or Tag
**What goes wrong:** arm64 E2E tests only run in CI on `push` to `main` or on release tag pushes — not on PR runs. Local arm64 verification is not possible without the staging image.
**Why it happens:** The CI matrix is gated: `github.event_name == 'push' && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v'))`. [VERIFIED: ci.yml]
**How to avoid:** For the Phase 85 plan, amd64 verification via `make run-tests-e2e` is the primary check. arm64 verification happens automatically on the next main push (Phase 86 final validation).

### Pitfall 5: CSP Canary Must Use `allowViolations: true`
**What goes wrong:** The `csp-canary.spec.ts` intentionally injects a script from `evil.example.com` to fire a CSP violation. If `allowViolations: false` (the default), the `csp-listener` fixture would fail the test AFTER the assertion, even if the CSP was correctly detected.
**Why it happens:** The fixture's cleanup code runs `expect(cspViolations).toEqual([])` unless `allowViolations: true`.
**How to avoid:** Do not change `test.use({ allowViolations: true })` in `csp-canary.spec.ts`. This is the correct, intentional behavior. [VERIFIED: csp-listener.ts line 65-67]

---

## Code Examples

### Checking if a Selector Exists in Live Templates
```bash
# Source: [VERIFIED: used during research]
# Run from repo root:
grep -rn "pattern-section\|pattern-chip\|btn-pattern-add" \
  src/angular/src/app/**/*.component.html
# If output exists → selector is live → spec is not stale
```

### Verifying Route Existence
```bash
# Source: [VERIFIED: src/angular/src/app/routes.ts]
grep -n "path" src/angular/src/app/routes.ts
# Expected: "dashboard", "settings", "logs", "about"
```

### Running E2E Verification (requires built staging image)
```bash
# Source: [VERIFIED: Makefile run-tests-e2e target]
# Must have STAGING_REGISTRY and STAGING_VERSION set (from CI build)
make run-tests-e2e \
  STAGING_REGISTRY=ghcr.io/thejuran/seedsyncarr \
  STAGING_VERSION=<CI_RUN_NUMBER> \
  SEEDSYNCARR_ARCH=amd64
```

### Playwright Config Key Settings
```typescript
// Source: src/e2e/playwright.config.ts [VERIFIED]
export default defineConfig({
  fullyParallel: false,   // Sequential — stateful tests share server state
  workers: 1,             // Single worker — LFTP contention makes parallel unsafe
  retries: process.env.CI ? 2 : 0,  // 2 retries in CI for flaky state transitions
  use: {
    baseURL: process.env.APP_BASE_URL || 'http://myapp:8800',
  },
  timeout: 30000,
});
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate AutoQueue page (`/autoqueue` route) | AutoQueue merged into Settings (`/settings`) | v1.1.0 (Phase 70) | `autoqueue.page.spec.ts` navigates to `Paths.SETTINGS` — selectors now live in `settings-page.component.html` |
| `import { test, expect } from '@playwright/test'` | `import { test, expect } from './fixtures/csp-listener'` | Phase 79 (commit 8d28c94) | All 6 non-canary specs now auto-fail on CSP violations |
| Separate FileComponent/FileListComponent | TransferRowComponent / TransferTableComponent | v1.1.0 (Phase 72) | Old file-list tests were removed; current dashboard specs target `app-transfer-row`, `.transfer-table` |

**Deprecated/outdated:**
- No separate AutoQueue route: `autoqueue` was removed from `routes.ts` when AutoQueue merged into Settings. `autoqueue.page.ts` navigates to `Paths.SETTINGS`, not a defunct path. [VERIFIED: routes.ts]
- `#version` selector: replaced by `.version-badge` in `about.page.ts` during v1.1.0 redesign (commit e1b348e). [VERIFIED: git log]

---

## Coverage Gap (Out of Scope)

**Logs page (`/logs`) has zero E2E coverage.** The `app.spec.ts` asserts "Logs" appears in the nav, but no spec navigates to `/logs` or verifies anything about `LogsPageComponent`. `Paths.LOGS` exists in `urls.ts` but no `logs.page.spec.ts` exists.

Per the audit mandate (REQUIREMENTS.md Out of Scope: "Writing new tests for uncovered code — Only if coverage drops below fail_under"), this gap is **not addressed in Phase 85**. Document and defer.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `autoqueue.enabled` defaults to `None` (null) in the harness, making the add/remove buttons disabled | Pitfall 1, autoqueue spec assessment | Medium — if the harness does set enabled=true somewhere (e.g., persisted state from a previous run), the tests would pass. Verify by running the E2E harness. |
| A2 | The autoqueue pattern CRUD tests currently fail in CI due to the disabled button issue | Pitfall 1 | Medium — if they currently pass, there is no issue. The audit result is still LIVE regardless. |

**All other claims verified:** Route existence (routes.ts), selector existence (grep on component HTML templates), fixture code (csp-listener.ts, seed-state.ts), CI workflow conditions (ci.yml), Makefile targets (Makefile), Docker compose structure (compose.yml), Playwright config (playwright.config.ts).

---

## Open Questions

1. **Does `autoqueue.page.spec.ts` currently pass or fail in CI?**
   - What we know: The harness sets `patterns_only=true` but not `enabled=true`; the button is conditionally disabled by `autoqueueEnabled`
   - What's unclear: Whether the harness has additional state (persisted config from a prior run) that sets enabled=true, or whether Playwright's click on a disabled button triggers the Angular event despite the `[disabled]` binding
   - Recommendation: The first task should run the CI harness (`make run-tests-e2e`) and capture output to determine current pass/fail status before making any decisions

2. **Should `settings.page.spec.ts` (1 test: nav active check) be classified as redundant to `autoqueue.page.spec.ts` (same check)?**
   - What we know: Both specs have `should have Settings nav link active`; they are in separate describe blocks; the D-01 definition focuses on "deleted production code" not "duplicated assertion"
   - What's unclear: Whether the phase mandate allows removing purely duplicated assertions even when the production code is live
   - Recommendation: Keep both for now (conservative interpretation of audit scope); the planner may choose to explicitly remove the 1 redundant test from `settings.page.spec.ts` as a mild cleanup if the mandate is read more broadly

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | `make run-tests-e2e` | [ASSUMED — was present for Phase 83 E2E; not checked this session] | — | None — E2E requires Docker |
| Node.js / npm | Playwright test runner | ✓ | npm present in src/e2e/ | — |
| Playwright Chromium | Test browser | ✓ (in Docker image) | 1.59.1 (npm registry current) | — |
| Pre-built staging image | `make run-tests-e2e` | Requires CI build | — | Build locally with `make docker-image ...` |

**Missing dependencies with no fallback:**
- A pre-built staging Docker image is required to run `make run-tests-e2e`. If one does not exist locally, it must be built first (`make docker-image STAGING_REGISTRY=... STAGING_VERSION=...`).

**Missing dependencies with fallback:**
- None (Docker is assumed available; E2E has no local-only run path)

---

## Validation Architecture

> `workflow.nyquist_validation` is absent from `.planning/config.json` — treating as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright 1.48.x (@playwright/test) |
| Config file | `src/e2e/playwright.config.ts` |
| Quick run command | `make run-tests-e2e STAGING_REGISTRY=... STAGING_VERSION=... SEEDSYNCARR_ARCH=amd64` |
| Full suite command | Same (Playwright runs all 7 spec files in one pass, single worker) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| E2E-01 | All 7 spec files audited for staleness | static analysis | `grep -rn <selector> src/angular/src/app/**/*.html` | N/A (scripted audit) |
| E2E-02 | Zero stale specs removed (or stale specs removed) | code edit | n/a | N/A |
| E2E-03 | All remaining specs pass CI harness | E2E regression | `make run-tests-e2e STAGING_ARCH=amd64 ...` | ✅ (7 spec files) |

### Sampling Rate
- **Per task commit:** Static analysis only (no automated run per commit — E2E requires Docker build)
- **Per wave merge:** `make run-tests-e2e SEEDSYNCARR_ARCH=amd64 ...`
- **Phase gate:** Full E2E harness green before `/gsd-verify-work`

### Wave 0 Gaps
None — no new test files needed. The audit only touches existing spec files.

---

## Security Domain

Phase 85 is a test audit phase — no production code changes. The CSP canary spec (`csp-canary.spec.ts`) is the E2E-layer security enforcement mechanism and MUST remain. The `csp-listener` fixture failing-by-default on CSP violations is the V5 input validation equivalent at the UI layer.

| ASVS Category | Applies | Control |
|---------------|---------|---------|
| V5 Input Validation | yes (via CSP canary) | `csp-listener` fixture + `csp-canary.spec.ts` |
| All others | no | No production code changed in this phase |

---

## Sources

### Primary (HIGH confidence)
- `src/e2e/tests/*.spec.ts` — all 7 spec files read directly [VERIFIED: filesystem]
- `src/e2e/tests/*.page.ts` — all 6 page objects read directly [VERIFIED: filesystem]
- `src/e2e/tests/fixtures/*.ts` — both fixture files read directly [VERIFIED: filesystem]
- `src/e2e/playwright.config.ts` — Playwright configuration [VERIFIED: filesystem]
- `src/e2e/package.json` — dependency versions [VERIFIED: filesystem]
- `src/angular/src/app/routes.ts` — live routes: dashboard, settings, logs, about [VERIFIED: filesystem]
- `src/angular/src/app/pages/settings/settings-page.component.html` — pattern-section selectors confirmed live [VERIFIED: grep]
- `src/angular/src/app/pages/settings/settings-page.component.ts` — `autoqueueEnabled` logic [VERIFIED: filesystem]
- `src/docker/test/e2e/configure/setup_seedsyncarr.sh` — harness config: patterns_only=true, enabled NOT set [VERIFIED: filesystem]
- `src/docker/test/e2e/compose.yml` — E2E compose structure [VERIFIED: filesystem]
- `src/docker/test/e2e/Dockerfile` — node:22-slim, Playwright install [VERIFIED: filesystem]
- `src/docker/test/e2e/run_tests.sh` — `npx playwright test` entry point [VERIFIED: filesystem]
- `.github/workflows/ci.yml` lines 110-155 — arm64 matrix gating, `make run-tests-e2e` [VERIFIED: filesystem]
- `Makefile` lines 113-185 — `run-tests-e2e` target logic [VERIFIED: filesystem]
- `git log --follow` — autoqueue.page.ts updated in commit e1b348e (selector rename), 8d28c94 (csp-listener import) [VERIFIED: git]
- `npm view @playwright/test version` → 1.59.1 [VERIFIED: npm registry]

### Tertiary (LOW confidence)
- A1, A2 in Assumptions Log — autoqueue enabled/disabled behavior in harness — unverified without a CI run

---

## Metadata

**Confidence breakdown:**
- Spec staleness audit results: HIGH — direct selector cross-reference against live HTML templates for all 7 spec files
- autoqueue button behavior in harness: LOW — inferred from setup script + component logic; not confirmed by CI run
- E2E execution path (Docker): HIGH — Makefile, compose.yml, Dockerfile, run_tests.sh all read
- CI arm64 gating: HIGH — ci.yml matrix conditions read directly

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable stack; 30-day window)
