# Phase 77: Deferred Playwright E2E (Phases 72 + 73) - Research

**Researched:** 2026-04-20
**Domain:** Playwright E2E test authoring against a Dockerized Angular+Bottle app with live backend mutations
**Confidence:** HIGH (codebase reads were definitive for every open question)

## Summary

Phase 77 ships 15 new Playwright specs inside the existing `src/e2e/tests/dashboard.page.spec.ts`, split into UAT-01 (selection + bulk bar, 5 specs) and UAT-02 (status filter + URL round-trip, 10 specs). All ambiguity identified during `/gsd-discuss-phase` has been resolved by direct inspection of the codebase. Key outcomes:

- **Bearer token auth is a non-issue in the test harness** — the configure container never sets `api_token`, and the backward-compat branch in `WebApp._check_host_and_auth` returns early when the token is empty. `page.request` calls carry no `Authorization` header today (see `settings.page.ts`) and work fine. No auth plumbing needed in the seed helper.
- **DELETED row survives** with `remote_size > 0` as long as the file (a) was tracked as downloaded before and (b) is no longer present locally. The canonical path is `DELETE /server/command/delete_local/<name>` against a file already in `DOWNLOADED`/`EXTRACTED` state. `delete_remote` must not be called — the row only enters `DELETED` while still in the remote listing; removing the remote listing will eventually purge the row.
- **Zero-match filter renders a single `tr.empty-row`** with a colspan-7 td containing "No files match the current filter". No dedicated empty-state panel.
- **Toast selector** is `.toast.moss-toast` in a top-end container, with `data-type` attribute in `{success, danger, warning, info}` and the text in `.toast-message`. Source text is `Localization.Bulk.SUCCESS_*` — partial match advised.
- **Confirm modal's OK button** is `button[data-action="ok"]` (Delete variants only).
- **URL shape** is literally `?segment=done` (parent-only) and `?segment=errors&sub=deleted` (parent+sub). The segment state machine lives in `transfer-table.component.ts` and hydrates from `ActivatedRoute.queryParamMap` — `page.reload()` exercises exactly that path.

**Primary recommendation:** Land Wave 1 (seed helper `src/e2e/tests/fixtures/seed-state.ts` + 9 new methods on `DashboardPage`) before any spec work. Seed flow is: (1) queue `clients.jpg` → wait DOWNLOADED → `delete_local` → wait DELETED (this is the FIX-01 fixture), (2) queue another small file and let it settle to DOWNLOADED, (3) stop a file for STOPPED. Skip seeding EXTRACTING/EXTRACTED entirely — no fixture is an archive (`patoolib` will reject all 9 files), so those two status specs either assert empty-state against ViewFile.Status="extracting"/"extracted" or are dropped (planner judges; leaning toward empty-state assertion since both parent buttons still need drill-down coverage under Done/Active).

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Runtime HTTP seed in `test.beforeAll()`. Docker fixture unchanged.
- **D-02:** Seed once per spec file (no per-test reset).
- **D-03:** `waitForFileStatus(name, status, timeout)` polls `td.cell-status .status-badge`; 10s default.
- **D-04:** Seed module at `src/e2e/tests/fixtures/seed-state.ts` with typed API.
- **D-05:** Bulk-action specs assert UI dispatch only (toast + selection clear + bar hide).
- **D-06:** FIX-01 covered by pre-seeded DELETED row; no in-test delete chain.
- **D-07:** No route-intercept — real mutation; destructive-last ordering.
- **D-08:** Seed plan includes `joke` → DELETED, `clients.jpg` → DOWNLOADED (and related status coverage).
- **D-09:** All 15 new specs land in existing `src/e2e/tests/dashboard.page.spec.ts`.
- **D-10:** Existing 11 tests untouched; new specs additive.
- **D-11:** Extend existing `DashboardPage`; new helpers land as methods.
- **D-12:** Page-object helper gaps close in a single Wave 1 before any spec work.
- **D-13:** UAT-02 = 8 status-filter specs + 2 URL round-trip specs.
- **D-14:** 2 round-trips: one parent (`?segment=done`) + one sub (`?segment=errors&sub=deleted`).
- **D-15:** Use `page.reload()`, not `page.goto()`.
- **D-16:** Back/forward navigation OUT OF SCOPE.
- **D-17:** No dedicated drill-down specs; folded into status-filter specs.
- **D-18:** Final count = 26 tests (11 existing + 15 new).
- **D-19:** UAT-01 item 4 may split into 5 per-action specs (planner discretion).
- **D-20:** Existing `make run-tests-e2e` harness picks up new specs via glob; no CI changes.
- **D-21:** No retry/reporter tuning; use `test.slow()` or helper waits for flakes.

### Claude's Discretion

- Exact file chosen to seed into DELETED (D-08 recommends `joke`; `clients.jpg` is an acceptable alternative — see rationale under Pitfalls).
- Exact page-object helper names (match existing camelCase conventions).
- UAT-01 item 4 packaging: one consolidated spec vs. 5 per-action specs (D-19).
- Ordering within each `describe` block beyond destructive-last.
- Whether to use `test.describe.serial()` to make the seed-once + destructive-last contract explicit.
- Toast text assertion precision: `toContainText` (recommended) vs. `toHaveText`.
- Empty-state assertion shape: verified here — use `tr.empty-row td` or assert `row count === 0`.

### Deferred Ideas (OUT OF SCOPE)

- Back/forward browser navigation round-trip.
- Cold-load URL via `page.goto(capturedURL)` in a fresh context.
- `page.route()` intercept for destructive actions.
- Toast localization matrix.
- CSP violation detection (Phase 79, TEST-02).
- Per-action separate spec split beyond D-19.
- Extracting the existing 11 tests into a separate file.
- Per-test state reset / reusable reset endpoint.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UAT-01 | Playwright E2E suite covers per-file selection, shift-range select, page-scoped header select-all, bulk-actions-bar visibility/hiding, and each of the 5 bulk actions (Queue, Stop, Extract, Delete Local, Delete Remote). 5 specs from Phase 72 deferred scope, CI-gated via `make run-tests-e2e`. | `DashboardPage` already exposes `getRowCheckbox`, `getHeaderCheckbox`, `getActionBar`, `getActionButton` — new helpers needed: `shiftClickFile`, `getSelectedCount`, `getToast`, `clickConfirmModalConfirm`. FIX-01 anchor spec covered by D-06 pre-seeded DELETED fixture. Backend `/server/command/*` endpoints confirmed present. |
| UAT-02 | Playwright E2E suite covers dashboard filter across every `ViewFile.Status` value, URL query-param round-trip, drill-down segment expansion, and silent fallback on invalid filter values. 10 specs from Phase 73 deferred scope, CI-gated. | URL shape `?segment=<parent>[&sub=<status>]` verified in `transfer-table.component.ts`. 8 `ViewFile.Status` values + badge labels mapped (note: DOWNLOADED renders as "Synced", STOPPED as "Failed", DEFAULT as em-dash). Drill-down DOM (`.btn-segment--parent-expanded`, `.btn-sub`) confirmed. Empty-state is `tr.empty-row` with "No files match the current filter". |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP state seeding | Test runtime (Playwright) | Bottle backend (`/server/command/*`) | Seed helper uses `page.request` to drive lifecycle; backend owns mutation. |
| Selection state assertions | Browser (Angular component) | — | `FileSelectionService` + row checkbox DOM — pure client-tier concern. |
| Bulk action dispatch UI | Browser | API (for real mutation) | UI click fires toast + clears selection; actual mutation runs through API per D-07. |
| URL query-param round-trip | Browser (Angular Router) | — | `queryParamMap` hydration is Angular-only; no backend involvement. |
| Confirm modal interaction | Browser (`ConfirmModalService`) | — | DOM-level click against `button[data-action="ok"]`. |
| SSE status propagation (implicit) | Backend → Browser | — | `waitForFileStatus` polls the badge DOM, absorbs SSE latency. |

## Standard Stack

### Core (frozen — no version bumps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@playwright/test` | ^1.48.0 | E2E framework | [VERIFIED: `src/e2e/package.json`] Already in use; `workers: 1`, `fullyParallel: false` (stateful harness). |
| `typescript` | ^5.3.0 | Spec language | [VERIFIED: `src/e2e/package.json`] Matches existing page-object style. |
| `@types/node` | ^20.10.0 | Node typings | [VERIFIED: `src/e2e/package.json`] Test-only dependency. |

**No installation needed.** Phase 77 consumes the existing `src/e2e/` setup as-is.

### Playwright APIs (all used by new code)

| API | Purpose | Source |
|-----|---------|--------|
| `test.beforeAll()` | One-time seed per spec file (D-02) | [CITED: playwright.dev/docs/api/class-test#test-before-all] |
| `page.request.post/delete(url)` | HTTP seed against backend endpoints | [VERIFIED: `src/e2e/tests/settings.page.ts` already uses `page.request.get`] |
| `locator.waitFor({ state })` | Poll for status-badge text match (D-03) | [CITED: playwright.dev/docs/api/class-locator#locator-wait-for] |
| `expect(locator).toContainText()` | Partial match for toasts | [CITED: playwright.dev/docs/api/class-locatorassertions] |
| `expect(page).toHaveURL(regex)` | URL round-trip assertions (D-13, D-14) | [VERIFIED: used at dashboard.page.spec.ts:98] |
| `page.reload()` | Hydrate from query-params (D-15) | [CITED: playwright.dev/docs/api/class-page#page-reload] |
| `test.describe.serial()` | Optional — fails remaining tests if one fails, enforcing destructive-last | [CITED: playwright.dev/docs/api/class-test#test-describe-serial] |
| `test.slow()` | Per-test timeout extension if seed flakes (D-21) | [CITED: playwright.dev/docs/api/class-test#test-slow] |

## Architecture Patterns

### System Architecture Diagram

```
Playwright test runner
       |
       | (1) test.beforeAll(): await seedState(page, plan)
       v
Seed helper (src/e2e/tests/fixtures/seed-state.ts)
       |
       +--> page.request.post('/server/command/queue/<name>')     [QUEUE]
       +--> page.request.post('/server/command/stop/<name>')      [STOP]
       +--> page.request.delete('/server/command/delete_local/<name>') [DELETE_LOCAL]
       +--> page.request.delete('/server/command/delete_remote/<name>')[DELETE_REMOTE]
       +--> page.request.post('/server/command/extract/<name>')   [EXTRACT — not used, no archive fixtures]
       |
       v
Bottle backend (controller.py + controller/controller.py)
       |
       | Command queued -> Controller.__process_commands drains
       | FileOperationManager executes (LFTP spawn / local FS delete)
       | ModelBuilder re-derives state on next model diff tick
       |
       v
SSE stream -> Angular TransferTableComponent -> status-badge DOM updates
       ^
       | page-object helper polls:
       |   await getStatusBadge(name).filter({ hasText: expectedLabel }).waitFor(...)
       |
Playwright spec (dashboard.page.spec.ts)
       |
       +--> UAT-01 describe: selection, shift-range, header toggle, bulk bar, FIX-01
       +--> UAT-02 describe: 8 status filters + 2 URL round-trips
```

### Project Structure (additive only)

```
src/e2e/
├── tests/
│   ├── dashboard.page.spec.ts         # 11 existing + 15 new = 26 tests (D-18)
│   ├── dashboard.page.ts              # extend with 9 new helpers (D-11)
│   └── fixtures/
│       └── seed-state.ts              # NEW — typed seed API (D-04)
├── playwright.config.ts               # no changes (D-21)
├── package.json                       # no changes
└── urls.ts                            # no changes
```

### Pattern 1: `test.beforeAll` seed flow

**What:** Run seed once per spec file, wait for badge transitions, no afterEach cleanup (D-02, D-07).

**When to use:** Every new describe block in this phase.

**Example:**
```typescript
// Source: seeds modeled on src/python/web/handler/controller.py route list
import { test } from '@playwright/test';
import { DashboardPage } from './dashboard.page';
import { seedMultiple } from './fixtures/seed-state';

test.describe.serial('UAT-01: selection and bulk bar', () => {
    let dashboard: DashboardPage;

    test.beforeAll(async ({ browser }) => {
        // Use a dedicated context so page.request carries no stale auth state.
        const ctx = await browser.newContext();
        const page = await ctx.newPage();
        const dash = new DashboardPage(page);
        await dash.navigateTo();
        await seedMultiple(page, [
            { file: 'clients.jpg', target: 'DELETED' },  // FIX-01 fixture (D-06, D-08)
            { file: 'documentation.png', target: 'DOWNLOADED' },
            { file: 'illusion.jpg', target: 'STOPPED' },
        ]);
        await ctx.close();
    });

    test.beforeEach(async ({ page }) => {
        dashboard = new DashboardPage(page);
        await dashboard.navigateTo();
    });

    // ...specs...
});
```

[VERIFIED: pattern matches existing `src/e2e/tests/dashboard.page.spec.ts` line 9 `beforeEach`; adds `beforeAll` per D-02]

### Pattern 2: Status-badge polling (D-03)

**What:** Wait for a specific row's badge to show the expected label text.

**Example:**
```typescript
// Add as method on DashboardPage:
async waitForFileStatus(
    name: string,
    status: 'Syncing' | 'Queued' | 'Synced' | 'Failed' | 'Extracting' | 'Extracted' | 'Deleted' | '—',
    timeout: number = 10000,
): Promise<void> {
    const row = this.page.locator('.transfer-table tbody app-transfer-row', {
        has: this.page.locator('td.cell-name .file-name', { hasText: new RegExp(`^${this._escapeRegex(name)}$`) }),
    });
    await row.locator('td.cell-status .status-badge').filter({ hasText: status }).waitFor({ timeout });
}
```

[VERIFIED: label source is `transfer-row.component.ts:49-58` — note DOWNLOADED="Synced", STOPPED="Failed", DEFAULT="\u2014" (em-dash), not the raw enum strings]

### Pattern 3: Toast assertion (partial match)

**What:** Locate the toast container, assert type + partial text.

**Example:**
```typescript
getToast(variant?: 'success' | 'danger' | 'warning' | 'info'): Locator {
    const base = this.page.locator('.toast.moss-toast');
    if (variant) {
        return base.filter({ has: this.page.locator(`[data-type="${variant}"]`) });
        // or: return this.page.locator(`.toast.moss-toast[data-type="${variant}"]`);
    }
    return base;
}

// In spec:
await expect(dashboard.getToast('success')).toContainText('Queued 1 file');
```

[VERIFIED: `app.component.html:53-82` — container is `div.toast-container`, each toast has class `toast moss-toast toast-enter`, `[attr.data-type]="toast.type"`, inner `.toast-message`]

### Pattern 4: Empty-state / zero-match filter assertion

**Two equivalent options:**

```typescript
// Option A: assert row count is zero
await expect(this.page.locator('.transfer-table tbody app-transfer-row')).toHaveCount(0);

// Option B: assert the empty-row placeholder
await expect(this.page.locator('.transfer-table tbody tr.empty-row')).toBeVisible();
await expect(this.page.locator('tr.empty-row td')).toContainText('No files match');
```

[VERIFIED: `transfer-table.component.html:163-168` — `@empty` block renders `<tr class="empty-row"><td colspan="7"...>No files match the current filter</td></tr>`]

### Pattern 5: Confirm-modal click

```typescript
async clickConfirmModalConfirm(): Promise<void> {
    await this.page.locator('.modal button[data-action="ok"]').click();
}
```

[VERIFIED: `confirm-modal.service.ts:100-116` — modal is injected as `.modal` with `button[data-action="ok"]` and `button[data-action="cancel"]`]

### Anti-Patterns to Avoid

- **Don't chain `delete_local` + `delete_remote` to reach DELETED.** If both succeed, the file leaves the remote listing; on the next model refresh the row is purged, destroying the FIX-01 fixture. Seed with `delete_local` only, against a file in DOWNLOADED/EXTRACTED state. [VERIFIED: `model_builder.py:516-534` `_check_deleted_state` — requires `local_size is None` AND `name in downloaded_files` LRU; the row only persists while `remote_size` is still populated.]
- **Don't assume DELETE_LOCAL works on DEFAULT state in the harness.** The controller allows it (`__handle_delete_command` permits DEFAULT/DOWNLOADED/EXTRACTED) but a DEFAULT file has `local_size is None`, so the precondition `file.local_size is None` at line 1041 returns 404. You MUST queue → wait DOWNLOADED → delete_local to reach DELETED. [VERIFIED: `controller/controller.py:1032-1047`]
- **Don't match toast text exactly.** Use `toContainText`. `Localization.Bulk.SUCCESS_QUEUED` is a `(count) => string` — the rendered text depends on file count and pluralization.
- **Don't rely on `api.action` enum names for status labels.** `transfer-row.component.ts` maps internal status values to display labels — seed/query using the display labels ("Synced", "Failed", "Deleted", "Syncing", "Queued", "Extracting", "Extracted", "\u2014").
- **Don't use `page.goto(url)` for round-trip hydration.** D-15 requires `page.reload()` — it exercises the in-memory Router re-subscription path, which is what Phase 73 shipped. `goto` would start a fresh navigation and may paper over hydration bugs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth header on seed calls | Custom `Authorization: Bearer ...` wrapper | Nothing — `page.request` works bare | [VERIFIED: harness `setup_seedsyncarr.sh` never calls `/server/config/set/general/api_token/...`; backward-compat branch at `web_app.py:122-126` allows unauthenticated `/server/*` when `api_token` is empty] |
| Polling for status transitions | Custom `while (true) { await sleep(100); ... }` loop | Playwright `locator.filter({ hasText }).waitFor({ timeout })` | Built-in polling, auto-retries, has timeout semantics; matches the project's existing `waitForFunction` pattern at `dashboard.page.ts:25-35`. |
| Row lookup by filename | CSS nth-child or array indexing | `locator('app-transfer-row', { has: locator('td.cell-name .file-name', { hasText: regex }) })` | Order-dependent assertions already flagged as fragile (see `dashboard.page.spec.ts:34-36` sort workaround). [VERIFIED: existing pattern at `dashboard.page.ts:53-58`] |
| State reset between tests | Custom "reset" endpoint | Destructive-last ordering + `beforeAll` | D-07 locks this. Adding a reset endpoint is Phase-boundary scope creep. |
| Toast type disambiguation | innerText regex matching | `.toast.moss-toast[data-type="success"]` selector | The component renders `data-type` explicitly [VERIFIED: `app.component.html:59`]. |

**Key insight:** The E2E harness is unauthenticated and already accepts plain `page.request.*` calls; half the "how do we auth the seed helper" question evaporates on inspection. The other half of this phase is straightforward locator work against DOM surfaces that the Angular templates document clearly.

## Runtime State Inventory

Phase 77 is purely test-additive (no renames, no data migration, no string replacement). The section is included for completeness per the rename/refactor trigger, but every category is empty:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no production data touched; test harness seeds its own state on each run. | None |
| Live service config | None — the harness `api_token` config is never set; no live services involved. | None |
| OS-registered state | None — Playwright runs inside the Docker `tests` container; no host-side tasks/services registered. | None |
| Secrets/env vars | `APP_BASE_URL` (optional override in `playwright.config.ts:19`); `CI=true` in compose. Neither changes. | None |
| Build artifacts | None — no compiled artifacts carry phase-specific names. The `seedsyncarr/test/e2e` image is rebuilt by `make run-tests-e2e` on every run via `--force-recreate`. | None |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker + docker compose | `make run-tests-e2e` | ✓ | 24.x | — |
| `@playwright/test` | All specs | ✓ | ^1.48.0 | — |
| Chromium (via Playwright) | Test runner | ✓ | bundled by `npx playwright install --with-deps chromium` in Dockerfile | — |
| Bottle backend `/server/command/*` | Seed helper | ✓ | See `controller.py:66-72` | — |
| `make` target `run-tests-e2e` | CI gating | ✓ | `Makefile:113` | — |
| `STAGING_VERSION` env | Make target | ✓ | Set by CI; local dev uses most recent | — |
| `SEEDSYNCARR_ARCH` env | Make target | ✓ | `amd64` or `arm64` | — |

**Missing dependencies:** None.

## Common Pitfalls

### Pitfall 1: Seeding into DELETED without the DOWNLOADED precondition

**What goes wrong:** `DELETE /server/command/delete_local/joke` returns 404 with "File 'joke' does not exist locally" because `file.local_size is None`. Seed appears to succeed (wrong file → no 404), then the status-badge wait times out.

**Why it happens:** `_check_deleted_state` only sets DELETED when (a) `local_size is None`, (b) state is currently DEFAULT, AND (c) the file is in the `downloaded_files` LRU tracker. Until the file has been downloaded at least once, the LRU tracker doesn't know about it.

**How to avoid:** Seed sequence is strictly: `queue` → `waitForFileStatus(name, 'Synced')` (that is, DOWNLOADED label) → `delete_local` → `waitForFileStatus(name, 'Deleted')`. Not negotiable.

**Warning signs:** `delete_local` seed returns 404 in the Playwright log; status-badge never flips from em-dash.

[VERIFIED: `model_builder.py:516-534` + `controller/controller.py:1032-1047`]

### Pitfall 2: `clients.jpg` as the FIX-01 fixture — why `joke` (directory) is risky

**What goes wrong:** `joke` is a directory containing `joke.png`. The path-traversal guard (`_check_path_safe`) and LFTP's directory-download semantics change behavior vs. a single file. More importantly, `delete_local` on a directory cascades.

**Why it happens:** CONTEXT.md D-08 recommends `joke` but calls it "low size" — it's actually a directory. `clients.jpg` (40 KB, single JPEG) is a cleaner FIX-01 anchor.

**How to avoid:** Use `clients.jpg` as the primary FIX-01 DELETED fixture. It's a single file, already in the "should have a list of files" golden test at 40 KB, and downloads in one LFTP cycle. Reserve `joke` for any case that needs a directory fixture.

**Warning signs:** LFTP's mirror behavior on `joke` takes ~2× longer than on `clients.jpg` in the existing harness; CI flakes under D-21 tolerance grow.

### Pitfall 3: EXTRACTING / EXTRACTED states are unreachable

**What goes wrong:** Seed issues `POST /server/command/extract/crispycat` — the extract endpoint accepts it, but `Extract.is_archive()` returns `false` for the cat.mp4 inside (`patoolib.get_archive_format` returns None for non-archives). The command completes "successfully" from the HTTP layer but no extract status is recorded, so the row never enters EXTRACTING.

**Why it happens:** None of the 9 harness fixtures are archives (checked: .jpg, .png, .gif, .mp4 contents, bare directories). `patoolib` is the gate.

**How to avoid:** Treat UAT-02 specs for EXTRACTING and EXTRACTED as **empty-state filters**, not populated filters. Click Done → Extracted → assert `tr.empty-row` visible. Same for Active → Extracting. This still exercises the filter logic (the "every ViewFile.Status value" success criterion #2) — it just asserts zero matches instead of N matches.

**Warning signs:** Seed helper `extract` call returns 200, spec hangs waiting for "Extracting" badge.

[VERIFIED: `extract.py:19-28` + fixture inspection via `file(1)` — all 9 fixtures are image/video/directory, not archives]

### Pitfall 4: QUEUED is transient — file drains from the queue

**What goes wrong:** Seed issues `queue` and tries to wait for "Queued" badge. LFTP may pick up the file within ms of queueing (especially on the harness where only one LFTP slot is needed) and transition directly to DOWNLOADING. The "Queued" label is never observed.

**Why it happens:** QUEUED is the in-queue-but-not-yet-started state. On an idle harness, the queue drains immediately.

**How to avoid:** For the QUEUED status-filter spec, either (a) queue multiple files fast enough that one stays in QUEUED behind another DOWNLOADING one, or (b) treat QUEUED as an unreliable-observable status and assert empty-state (same fallback as EXTRACTING/EXTRACTED). Option (b) is safer and aligns with D-19's "spec style shifts to button-smoke" intent. Recommend (b).

**Warning signs:** Spec passes locally (slow machine) and fails in CI (fast worker).

### Pitfall 5: `page.reload()` preserving in-memory auth state

**What goes wrong:** Not a real risk today (harness has no token), but future-proof the seed helper: a fresh `browser.newContext()` has no meta-tag token cached, and the auth interceptor's `tokenRead` module-level cache is bypassed on full page reload.

**Why it happens:** The interceptor's cache lives in JS module scope — `page.reload()` tears down the module instance, triggering fresh meta-tag read on next HTTP call. This is correct behavior, but be aware that the first post-reload HTTP is *not* warm-cached.

**How to avoid:** No action needed for this phase. Flag this as context if Phase 81 (Fernet) or a future phase flips on the test-harness token.

[VERIFIED: `auth.interceptor.ts:7-17`]

### Pitfall 6: Selection is cleared on filter change (Phase 72 D-04)

**What goes wrong:** A UAT-01 spec selects files, then navigates to a filter to verify something — selection evaporates, bulk bar hides, subsequent assertions fail.

**Why it happens:** Phase 72 locked selection-on-filter-change to clear (D-04 in Phase 72 CONTEXT).

**How to avoid:** Within a single UAT-01 spec, don't cross filter boundaries. Seed the All view, run selection assertions there. If a spec needs to assert filtered-view selection, select after the filter applies.

**Warning signs:** `getActionBar()` assertion mid-spec fails after a filter click.

## Code Examples

### Seed helper skeleton (`src/e2e/tests/fixtures/seed-state.ts`)

```typescript
// Source: endpoint list verified at src/python/web/handler/controller.py:66-72
import type { Page } from '@playwright/test';

export type SeedTarget = 'DOWNLOADED' | 'STOPPED' | 'DELETED';

export interface SeedPlanItem {
    file: string;
    target: SeedTarget;
}

const ENDPOINT = {
    queue:         (n: string) => `/server/command/queue/${encodeURIComponent(n)}`,
    stop:          (n: string) => `/server/command/stop/${encodeURIComponent(n)}`,
    extract:       (n: string) => `/server/command/extract/${encodeURIComponent(n)}`,
    deleteLocal:   (n: string) => `/server/command/delete_local/${encodeURIComponent(n)}`,
    deleteRemote:  (n: string) => `/server/command/delete_remote/${encodeURIComponent(n)}`,
};

// Label map mirrors transfer-row.component.ts BADGE_LABELS
const LABEL = {
    DOWNLOADED: 'Synced',
    STOPPED: 'Failed',
    DELETED: 'Deleted',
    DOWNLOADING: 'Syncing',
    QUEUED: 'Queued',
} as const;

async function expectOk(page: Page, url: string, method: 'POST' | 'DELETE'): Promise<void> {
    const res = method === 'POST'
        ? await page.request.post(url)
        : await page.request.delete(url);
    if (!res.ok()) {
        throw new Error(`Seed call ${method} ${url} failed: ${res.status()} ${await res.text()}`);
    }
}

async function waitForBadge(page: Page, name: string, label: string, timeout = 30_000): Promise<void> {
    const row = page.locator('.transfer-table tbody app-transfer-row', {
        has: page.locator('td.cell-name .file-name', {
            hasText: new RegExp(`^${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`),
        }),
    });
    await row.locator('td.cell-status .status-badge').filter({ hasText: label }).waitFor({ timeout });
}

export async function queueFile(page: Page, name: string): Promise<void> {
    await expectOk(page, ENDPOINT.queue(name), 'POST');
}

export async function stopFile(page: Page, name: string): Promise<void> {
    await expectOk(page, ENDPOINT.stop(name), 'POST');
}

export async function deleteLocal(page: Page, name: string): Promise<void> {
    await expectOk(page, ENDPOINT.deleteLocal(name), 'DELETE');
}

export async function seedStatus(page: Page, file: string, target: SeedTarget): Promise<void> {
    if (target === 'DOWNLOADED') {
        await queueFile(page, file);
        await waitForBadge(page, file, LABEL.DOWNLOADED);
        return;
    }
    if (target === 'STOPPED') {
        await queueFile(page, file);
        await waitForBadge(page, file, LABEL.DOWNLOADING);  // must be mid-flight to stop
        await stopFile(page, file);
        await waitForBadge(page, file, LABEL.STOPPED);
        return;
    }
    if (target === 'DELETED') {
        // Pitfall 1: must reach DOWNLOADED before local delete will be accepted.
        await queueFile(page, file);
        await waitForBadge(page, file, LABEL.DOWNLOADED);
        await deleteLocal(page, file);
        await waitForBadge(page, file, LABEL.DELETED);
        return;
    }
    throw new Error(`Unknown seed target: ${target}`);
}

export async function seedMultiple(page: Page, plan: SeedPlanItem[]): Promise<void> {
    // Sequential — harness has workers: 1 and SSE/LFTP contention concerns.
    for (const item of plan) {
        await seedStatus(page, item.file, item.target);
    }
}
```

[VERIFIED: endpoints against `src/python/web/handler/controller.py:66-72`; labels against `src/angular/src/app/pages/files/transfer-row.component.ts:49-58`; auth-free harness against `src/docker/test/e2e/configure/setup_seedsyncarr.sh`]

### New `DashboardPage` helpers (extending `src/e2e/tests/dashboard.page.ts`)

```typescript
// Additions to src/e2e/tests/dashboard.page.ts — names match existing camelCase convention
async shiftClickFile(name: string): Promise<void> {
    await this.getRowCheckbox(name).click({ modifiers: ['Shift'] });
}

async clickHeaderCheckbox(): Promise<void> {
    await this.getHeaderCheckbox().click();
}

async getSelectedCount(): Promise<number> {
    const label = this.page.locator('app-bulk-actions-bar .selection-label');
    if (!(await label.isVisible())) return 0;
    const text = (await label.textContent()) ?? '';
    const match = text.match(/^(\d+)\s+selected$/);
    return match ? Number(match[1]) : 0;
}

getStatusBadge(fileName: string): Locator {
    const row = this.page.locator('.transfer-table tbody app-transfer-row', {
        has: this.page.locator('td.cell-name .file-name', {
            hasText: new RegExp(`^${this._escapeRegex(fileName)}$`),
        }),
    });
    return row.locator('td.cell-status .status-badge');
}

getEmptyRow(): Locator {
    return this.page.locator('.transfer-table tbody tr.empty-row');
}

getToast(variant?: 'success' | 'danger' | 'warning' | 'info'): Locator {
    return variant
        ? this.page.locator(`.toast.moss-toast[data-type="${variant}"]`)
        : this.page.locator('.toast.moss-toast');
}

getClearSelectionLink(): Locator {
    return this.page.locator('app-bulk-actions-bar button.clear-btn');
}

async waitForFileStatus(name: string, label: string, timeout: number = 10_000): Promise<void> {
    await this.getStatusBadge(name).filter({ hasText: label }).waitFor({ timeout });
}

async clickConfirmModalConfirm(): Promise<void> {
    await this.page.locator('.modal button[data-action="ok"]').click();
}
```

[VERIFIED: selector surfaces against `bulk-actions-bar.component.html`, `transfer-row.component.html`, `transfer-table.component.html`, `app.component.html`, `confirm-modal.service.ts`; method naming matches existing `dashboard.page.ts:53-93`]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `page.waitForTimeout(5000)` | `locator.filter({ hasText }).waitFor({ timeout })` | Playwright 1.20+ | Avoids flake; already project convention (`dashboard.page.ts:25-35`). |
| Fragile `nth-child` row lookups | `locator(container, { has: sub-locator })` chaining | Playwright 1.14+ | Existing project pattern (`dashboard.page.ts:53-58`). |
| Module-level global auth token in test files | `page.request` inherits browser context auth | Playwright 1.16+ | Not relevant for this phase (harness unauthenticated) but orthogonal to Phase 81 if it enables tokens. |

**Deprecated/outdated:** None in scope.

## Validation Architecture

Per Nyquist workflow (no explicit `nyquist_validation: false` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `@playwright/test` ^1.48.0 |
| Config file | `src/e2e/playwright.config.ts` |
| Quick run command | `cd src/e2e && npx playwright test dashboard.page.spec.ts` (inside container only; harness is Dockerized) |
| Full suite command | `make run-tests-e2e SEEDSYNCARR_ARCH=amd64 STAGING_VERSION=<ver>` |
| Local dev command | `make run-tests-e2e SEEDSYNCARR_ARCH=amd64 STAGING_VERSION=latest DEV=1` (exposes browser for debugging) |

### Phase Requirements → Test Map (D-11 / D-13 / D-14 / D-18)

**Final count:** 15 new tests (5 UAT-01 + 10 UAT-02). D-19 allows the bulk-action spec to split 1→5 (shifting to 19/30); recommendation below stays at 15/26.

#### UAT-01 (5 specs)

| Req | Describe | Spec Name | Assertion | Decisions Enforced |
|-----|----------|-----------|-----------|--------------------|
| UAT-01 | `UAT-01: selection and bulk bar` | `per-file selection accumulates and reflects count` | Select `clients.jpg` + `goose`; assert `selection-label` = "2 selected", bulk bar visible. | D-01, D-11 (`getSelectedCount`) |
| UAT-01 | same | `shift-range select extends selection to contiguous rows` | Click first row checkbox, shift-click third row checkbox; assert count = 3. | D-11 (`shiftClickFile`) |
| UAT-01 | same | `page-scoped header checkbox selects all visible rows only` | Click header checkbox; assert all visible row checkboxes checked AND selection-count matches page size (not totalCount). | D-11 (`clickHeaderCheckbox`) |
| UAT-01 | same | `bulk bar Clear link empties selection and hides bar` | Select 2 files; click `.clear-btn`; assert bar not visible, count=0. Consolidated "bulk bar visibility" spec. | D-05, D-11 (`getClearSelectionLink`) |
| UAT-01 + FIX-01 | same (destructive-last) | `FIX-01 union — DELETED + Queue re-queues from remote` | Select pre-seeded DELETED `clients.jpg`; assert Queue enabled, Delete Remote enabled. Mix with DEFAULT `goose`; assert union still allows Queue. Click Queue; assert success toast + selection cleared + bar hidden. | D-06, D-07, D-08, Phase 76 fix |

**Alternative per D-19** (planner discretion): split the bar visibility spec into 5 per-action specs (one each for Queue, Stop, Extract, Delete Local confirm-modal, Delete Remote confirm-modal). Final count becomes 9 UAT-01 + 10 UAT-02 = 19/30.

#### UAT-02 (10 specs)

| Req | Describe | Spec Name | Assertion | Decisions Enforced |
|-----|----------|-----------|-----------|--------------------|
| UAT-02 | `UAT-02: status filter and URL` | `Active → Pending (DEFAULT) filters rows to em-dash status` | Click Active; click Pending; assert only rows with DEFAULT status visible (those without a badge label). | D-13, D-17 |
| UAT-02 | same | `Active → Syncing (DOWNLOADING) — empty state when no transient` | Click Active → Syncing on a fully-seeded view; assert `tr.empty-row` visible (or rows if mid-transition). | D-13, D-17, Pitfall 4 |
| UAT-02 | same | `Active → Queued — empty state (unreliable observable)` | Pitfall 4 — assert empty-state. | D-13, D-19 |
| UAT-02 | same | `Active → Extracting — empty state (no archive fixtures)` | Pitfall 3 — assert empty-state. | D-13, D-19 |
| UAT-02 | same | `Done → Downloaded (DOWNLOADED) filters rows to "Synced" badge` | Click Done → Downloaded; assert only `clients.jpg` (and seeded DOWNLOADED siblings) visible. | D-13 |
| UAT-02 | same | `Done → Extracted — empty state (no archive fixtures)` | Pitfall 3 — assert empty-state. | D-13 |
| UAT-02 | same | `Errors → Failed (STOPPED) filters rows to "Failed" badge` | Click Errors → Failed; assert seeded STOPPED file visible. | D-13 |
| UAT-02 | same | `Errors → Deleted (DELETED) filters rows to "Deleted" badge` | Click Errors → Deleted; assert `clients.jpg` (FIX-01 fixture) visible. | D-13 |
| UAT-02 | same | `parent round-trip — Done persists across reload` | Click Done; assert URL `?segment=done`; `page.reload()`; assert Done active, expanded, Downloaded+Extracted sub-buttons visible. | D-14, D-15 |
| UAT-02 | same | `sub round-trip — Errors→Deleted persists across reload` | Click Errors → Deleted; assert URL `?segment=errors&sub=deleted`; `page.reload()`; assert Errors parent expanded, Deleted sub active, `clients.jpg` row visible. | D-14, D-15 |

Note: the existing "silent fallback on invalid filter values" spec at `dashboard.page.spec.ts:101-110` already covers the invalid-value case from UAT-02's success criterion; not duplicated.

### Sampling Rate

- **Per task commit:** `cd src/e2e && npx playwright test dashboard.page.spec.ts -g '<describe name>' --headed=false` — only runnable inside the test container; on dev host, approximate via `make run-tests-e2e DEV=1` with filters.
- **Per wave merge:** `make run-tests-e2e SEEDSYNCARR_ARCH=amd64 STAGING_VERSION=latest`
- **Phase gate:** Full `run-tests-e2e` green on both amd64 and arm64 before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `src/e2e/tests/fixtures/` directory does not exist — must be created.
- [ ] `src/e2e/tests/fixtures/seed-state.ts` — new file per D-04.
- [ ] 9 new methods on `DashboardPage` per D-11 — land in Wave 1 (before any UAT spec).
- [ ] No framework install needed — `@playwright/test` already in `src/e2e/package.json`.
- [ ] No CI change needed — `testMatch: '**/*.spec.ts'` already globs the edited file (D-20).

## Security Domain

> `security_enforcement` not explicitly disabled in `.planning/config.json`; treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Test-only change against harness that explicitly runs with empty `api_token` (backward-compat branch). No production auth path touched. |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes (minor) | `encodeURIComponent` on all file names passed to seed endpoints — matches controller's `unquote` expectation at `controller.py:79`. Already done in `settings.page.ts` precedent. |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for Playwright E2E specs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Spec leaks production token by reading a real meta tag | Information Disclosure | Harness never sets `api_token`; even if a future phase enables it, `page.request` inherits the browser context's headers — no need to read the meta tag manually. |
| Path traversal via fixture filename | Tampering | Backend has `_check_path_safe` at `controller.py:211-227`; all `delete_local`/`delete_remote`/`extract` calls are guarded. Seed helper uses only the 9 known-safe harness filenames. |
| Test pollutes production data | Repudiation/Tampering | Harness is Dockerized and teardown-fresh (`--force-recreate` per Makefile). No production concern. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | LFTP completes `clients.jpg` (40 KB) download within Playwright's 30s default timeout on both amd64 and arm64 harnesses. | Seed plan | If wrong, seed `beforeAll` times out; mitigation is to bump per-spec timeout via `test.setTimeout` — not a blocker. [ASSUMED] |
| A2 | QUEUED status is sufficiently transient on the harness that an observable spec is unreliable; empty-state fallback recommended. | Pitfall 4 | If wrong (CI is slow enough that QUEUED is observable), the QUEUED spec can be upgraded from empty-state to populated. Safe downgrade. [ASSUMED] |
| A3 | `test.describe.serial()` is the right primitive for forcing destructive-last ordering. Playwright's default within a describe is sequential when `workers: 1` + `fullyParallel: false`, so `serial()` is technically redundant but makes the contract explicit. | Pattern 1 | If wrong, ordering is still guaranteed by the config. Low risk; this is stylistic. [ASSUMED] |

**Note:** All critical questions raised in CONTEXT `<specifics>` were resolved via codebase reads (not assumed) — see "Open Questions" section below which is now empty.

## Open Questions

All 7 open questions from CONTEXT `<specifics>` are resolved:

1. **Seed-helper auth path** — RESOLVED. Harness never sets `api_token`; the backward-compat branch in `WebApp._check_host_and_auth` (web_app.py:122-126) allows all `/server/*` calls when the token is empty. `page.request` carries no `Authorization` header and works fine, matching existing precedent in `settings.page.ts`. [VERIFIED]
2. **DELETED row survival** — RESOLVED. Row survives with `remote_size > 0` iff we `delete_local` only (not both). State engine requires (a) `local_size is None`, (b) previously-downloaded (in LRU), (c) state was DEFAULT. Seed path: `queue` → wait DOWNLOADED → `delete_local` → wait DELETED. [VERIFIED: `model_builder.py:516-534`, `controller/controller.py:1032-1047`]
3. **EXTRACTING / QUEUED observability** — RESOLVED. EXTRACTING unreachable (no archive fixtures); QUEUED transient. Both collapse to empty-state specs per D-19. [VERIFIED: fixture inspection via `file(1)`; extract gating at `extract.py:19-28`]
4. **Page-object helper names + signatures** — RESOLVED. See "New `DashboardPage` helpers" code example above. [VERIFIED: matched against existing camelCase style in `dashboard.page.ts`]
5. **Empty-state selector** — RESOLVED. `tr.empty-row` with colspan-7 td "No files match the current filter". [VERIFIED: `transfer-table.component.html:163-168`]
6. **Toast selector + variant disambiguation** — RESOLVED. `.toast.moss-toast[data-type="{success|danger|warning|info}"]`, message in `.toast-message`. Text from `Localization.Bulk.SUCCESS_*`. [VERIFIED: `app.component.html:53-82`, `toast.service.ts`, `localization.ts:48-80`]
7. **URL shape** — RESOLVED. Parent-only: `?segment=done`. Parent+sub: `?segment=errors&sub=deleted`. [VERIFIED: `transfer-table.component.ts:360-380`]

## Project Constraints (from CLAUDE.md)

User's global `~/.claude/CLAUDE.md` is browser-automation focused (gsd-browser). No project-level `./CLAUDE.md` exists. Project memory file `feedback_design_spec_rigor.md` mandates identical AIDesigner HTML ports — **does not apply to Phase 77** since Phase 77 is test-only and does not modify the Angular template/HTML. Any spec that needs a UI change should block the phase.

## Sources

### Primary (HIGH confidence — direct codebase reads)

- `src/e2e/tests/dashboard.page.spec.ts` — existing 11 tests, describe structure
- `src/e2e/tests/dashboard.page.ts` — page object with 9 existing helpers
- `src/e2e/tests/app.ts` — base class (no page.request usage)
- `src/e2e/tests/settings.page.ts` — `page.request.get` precedent
- `src/e2e/playwright.config.ts` — `workers: 1, fullyParallel: false, retries: 2, timeout: 30000, expect.timeout: 10000`
- `src/e2e/package.json` — `@playwright/test ^1.48.0`
- `src/e2e/urls.ts` — actual path: `src/e2e/urls.ts` (not `src/e2e/tests/urls.ts` as CONTEXT `canonical_refs` suggested; minor doc correction)
- `src/docker/test/e2e/configure/setup_seedsyncarr.sh` — confirms no `api_token` set
- `src/docker/test/e2e/Dockerfile` — Playwright bundled chromium
- `src/docker/test/e2e/compose.yml` — 3-service compose
- `src/docker/test/e2e/run_tests.sh` — `npx playwright test` entrypoint
- `src/docker/test/e2e/remote/files/` — 9 fixture files (inspected, none are archives)
- `Makefile:113-188` — `make run-tests-e2e` target
- `src/python/web/handler/controller.py` — 5 command endpoints confirmed
- `src/python/web/web_app.py:58-141` — auth guard with backward-compat branch
- `src/python/controller/controller.py:1027-1065` — delete command state rules
- `src/python/controller/model_builder.py:516-534` — `_check_deleted_state` rules
- `src/python/controller/extract/extract.py:19-35` — archive validation via patoolib
- `src/python/model/file.py:21-28` — ModelFile.State enum
- `src/angular/src/app/pages/files/transfer-table.component.html` — segment filter DOM, `tr.empty-row`
- `src/angular/src/app/pages/files/transfer-table.component.ts:170-380` — hydration and URL write logic
- `src/angular/src/app/pages/files/transfer-row.component.html` — row DOM selectors
- `src/angular/src/app/pages/files/transfer-row.component.ts:49-79` — BADGE_LABELS, BADGE_CLASSES
- `src/angular/src/app/pages/files/bulk-actions-bar.component.html` — bar DOM selectors
- `src/angular/src/app/pages/main/app.component.html` — toast container DOM
- `src/angular/src/app/services/utils/toast.service.ts` — Toast type definition
- `src/angular/src/app/services/utils/confirm-modal.service.ts` — `button[data-action="ok"]` confirmed
- `src/angular/src/app/services/files/bulk-action-dispatcher.service.ts:40-100` — toast/notification dispatch
- `src/angular/src/app/services/utils/auth.interceptor.ts` — meta-tag token mechanism
- `src/angular/src/app/common/localization.ts` — Bulk.SUCCESS_* text source
- `src/angular/src/app/services/files/view-file.ts:90-107` — ViewFile.Status enum (8 values)

### Secondary (MEDIUM confidence — cited docs)

- Playwright test docs: `test.beforeAll`, `locator.waitFor`, `locator.filter`, `page.reload`, `test.describe.serial`, `test.slow` — all documented at playwright.dev/docs/api [CITED]

### Tertiary (LOW confidence)

- None — every claim in this research traced to direct codebase evidence or cited official Playwright docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions and APIs verified in `package.json`; no new dependencies.
- Architecture: HIGH — all seeding, DOM selectors, state transitions verified in source files.
- Pitfalls: HIGH — each pitfall backed by specific file:line references (controller.py, model_builder.py, extract.py, component.ts files).
- Seed semantics: HIGH — delete/queue/stop preconditions read directly from backend source.
- Label mapping: HIGH — BADGE_LABELS in `transfer-row.component.ts` is authoritative.

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (30 days for stable infrastructure — no UI changes expected per D-10, no backend changes expected in this phase)
