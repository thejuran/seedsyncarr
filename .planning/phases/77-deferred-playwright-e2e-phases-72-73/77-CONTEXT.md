# Phase 77: Deferred Playwright E2E (Phases 72 + 73) - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship 15 new Playwright E2E specs (5 UAT-01 selection + bulk-bar + 5 bulk-action
dispatch tests; 10 UAT-02 dashboard-filter + URL persistence tests) that
regression-guard every deferred v1.1.0 UI behavior from Phases 72 and 73.
Specs are CI-gated via the existing `make run-tests-e2e` Docker harness. The
FIX-01 union-behavior fix that shipped in Phase 76 is covered by at least one
of the new UAT-01 selection specs.

**Out of scope:** New UI features or selector churn (Angular DOM is frozen —
only the page object and specs evolve); backend / controller changes; fixes
to flakes surfaced in *other* suites; CSP violation detection in the main E2E
suite (that is Phase 79, TEST-02); changes to the existing 11 tests in
`dashboard.page.spec.ts` (they stay as-is per D-10 below); net-new Playwright
config or reporter work; rewriting the `make run-tests-e2e` Docker harness.

</domain>

<decisions>
## Implementation Decisions

### State seeding + fixture

- **D-01:** Non-DEFAULT statuses are reached by **runtime HTTP seed in
  `test.beforeAll()`**. The Docker fixture (`src/docker/test/e2e/remote/files/`,
  nine files) stays unchanged. Seed helper dispatches the backend command
  endpoints (`POST /server/command/queue/<name>`, `POST /server/command/stop/<name>`,
  `POST /server/command/extract/<name>`, `DELETE /server/command/delete_local/<name>`,
  `DELETE /server/command/delete_remote/<name>`) to drive files through
  their status lifecycle.
- **D-02:** Seeding runs **once per spec file via `test.beforeAll()`** — no
  per-test reset, no afterEach restore. Tests that mutate state sit at the
  end of each describe block (destructive-last ordering, see D-10).
- **D-03:** Wait for state transitions via Playwright `.locator().waitFor()`
  against the status badge in the transfer row. A page-object helper
  `waitForFileStatus(name, status, timeout)` polls the row's
  `td.cell-status .status-badge` until the rendered label matches. Timeout
  default 10s (matches CI `expect.timeout`); seed helper's total window
  should budget 2x a single LFTP cycle on the test harness.
- **D-04:** Seed code lives in a **new module** at
  `src/e2e/tests/fixtures/seed-state.ts`, not in the page object and not
  inlined in specs. Exports a typed API: `seedStatus(page, file, target)`,
  `seedMultiple(page, plan)`, and status-transition helpers
  (`queueFile`, `stopFile`, `deleteLocal`, `deleteRemote`, `extract`) keyed
  to the 5 backend command endpoints. Used by both the selection and filter
  describe blocks in `dashboard.page.spec.ts`.

### Destructive action coverage + FIX-01

- **D-05:** The 5 bulk-action specs (one per action: Queue, Stop, Extract,
  Delete Local, Delete Remote) assert **UI dispatch only**:
    1. After click: the relevant success toast is visible with correct text.
    2. Selection is cleared (`bulk-actions-bar` hidden; selection-label gone).
    3. Bulk bar no longer visible.
  They do **not** assert backend state transition end-to-end — that is the
  seed helper's concern and is covered implicitly by the UAT-02 filter
  specs (which rely on the seeded state landing correctly). The Delete Local
  confirmation modal (Phase 72 D-17) is acknowledged in the Delete specs:
  test clicks the confirm button via the `ConfirmModalService` modal selector.
- **D-06:** FIX-01 (DELETED + Queue union) is covered by **pre-seeding a
  DELETED file in `test.beforeAll()`**, not by chaining after an in-test
  Delete Local. The UAT-01 "FIX-01 union" spec selects the pre-seeded DELETED
  row (alone, and in a mixed selection with a DEFAULT row) and asserts:
  Queue button is enabled (`actionCounts.queueable >= 1`), Delete Remote is
  enabled, clicking Queue fires the re-queue dispatch and clears selection.
  No reliance on in-test mutation of the DELETED state.
- **D-07:** **No isolation / no route-intercept** for destructive actions.
  Real mutation runs against the harness. Tests are ordered so destructive
  specs sit at the end of each describe; a re-run starts from a freshly-
  seeded state via `beforeAll()`. Accepts state leak between sibling tests
  within a run as long as ordering is respected (matches Playwright
  `workers: 1, fullyParallel: false` constraints already in
  `playwright.config.ts`).
- **D-08:** Because Deletes actually mutate, the FIX-01 DELETED-row must
  exist **before** any destructive test runs. Seed plan in `beforeAll()`:
    1. Pick one fixture file (recommend `joke` — short name, low size) and
       force to DELETED via `DELETE /server/command/delete_local/joke` +
       `DELETE /server/command/delete_remote/joke`. Wait for status badge
       to show "Deleted". This row is the FIX-01 fixture for the entire
       spec file.
    2. Queue another file (`clients.jpg`) to reach DOWNLOADING; let it
       settle to DOWNLOADED (LFTP completion) for UAT-02 coverage.
    3. Seed additional statuses as UAT-02 specs require (EXTRACTED,
       STOPPED, QUEUED, EXTRACTING). Planner resolves exact mapping in
       research, but the DELETED + DOWNLOADED + DEFAULT triple is the
       minimum viable set for FIX-01 + "every status" goals.

### Spec file org + existing-test overlap

- **D-09:** All 15 new specs land in the **existing
  `src/e2e/tests/dashboard.page.spec.ts`**. No file split. Use
  `test.describe()` grouping: one describe block for UAT-01 selection +
  bulk-bar, one for UAT-02 filter + URL. The file grows from 11 to 26
  tests. Single source of truth for dashboard E2E; matches how Phase 72
  and 73 extended the same file.
- **D-10:** Existing 11 tests are **not** counted toward the 15. Net-new
  specs land on top, even where a scenario overlaps with an existing test
  (e.g., "bar visibility/hiding" exists at lines 39–47; UAT-01 adds a
  stricter variant that also asserts toast + clear). Existing tests stay
  untouched — they represent the already-shipped regression guards for
  Phase 72 and 73.
- **D-11:** **Extend the existing `DashboardPage` page object** at
  `src/e2e/tests/dashboard.page.ts`. No new harness classes
  (`SelectionHarness`, `FilterHarness`). New helpers land as methods on
  `DashboardPage`. Target helpers (at minimum):
    - `shiftClickFile(name)` — shift+click a row checkbox
    - `clickHeaderCheckbox()` — toggle "select all visible"
    - `getSelectedCount()` — read "N selected" label
    - `getStatusBadge(name)` — row status badge locator
    - `getEmptyStatePanel()` — empty-state panel locator (for zero-match filters)
    - `getToast(variant?)` — toast element by success/error/info
    - `getClearSelectionLink()` — "Clear" link in bulk bar (Phase 72 D-10)
    - `waitForFileStatus(name, status, timeout)` — status-badge polling
      (D-03)
    - `clickConfirmModalConfirm()` — confirm button in the Delete modal
      (Phase 72 D-17 `ConfirmModalService`)
- **D-12:** Page-object helper gaps are closed in a **single up-front
  plan** before any UAT-01/UAT-02 spec is written. The planner should
  treat the helper landing as Wave 1; spec waves consume the helpers.
  Avoids retroactive selector drift across the 15 tests.

### URL round-trip depth + UAT-02 mix

- **D-13:** UAT-02's 10 specs break down as **8 status-filter specs + 2
  URL round-trip specs**. The 8 status-filter specs: one per
  `ViewFile.Status` value (DEFAULT→Pending, DOWNLOADING→Syncing,
  QUEUED→Queued, EXTRACTING→Extracting, DOWNLOADED→Downloaded,
  EXTRACTED→Extracted, STOPPED→Failed, DELETED→Deleted). Each asserts
  (a) clicking the sub-button navigates to `?segment=<parent>&sub=<status>`,
  (b) the visible table rows are limited to files matching that status
  (uses seeded state from `beforeAll`), and (c) an empty-state or the
  expected row count is correctly rendered.
- **D-14:** The 2 URL round-trip specs reload and verify hydration. Shape
  is representative, not exhaustive: **one parent round-trip** (click a
  parent without a sub-status selected, e.g., Done; verify
  `?segment=done`; `page.reload()`; assert Done is active, expanded,
  Downloaded+Extracted rows visible) + **one sub round-trip** (click a
  sub, e.g., Errors→Deleted; verify `?segment=errors&sub=deleted`;
  `page.reload()`; assert Errors parent expanded + Deleted sub active +
  DELETED row visible). This is the minimum path that proves both the
  parent-only and the parent+sub hydration paths.
- **D-15:** "Reload" is **`page.reload()`**, not `page.goto(url)`. Tests
  the in-browser refresh path the Angular component hydrates from
  `ActivatedRoute.queryParamMap` on init. Cold-load via `page.goto()` is
  out of scope for this phase (sufficient coverage via the existing
  invalid-fallback test which does `page.goto('/dashboard?segment=garbage')`).
- **D-16:** **Back/forward browser navigation is out of scope**. Phase 73
  deferred it explicitly ("worth E2E-testing in a follow-up"). Do not add
  back/forward specs in Phase 77; leave as deferred.
- **D-17:** Drill-down expansion (parent collapse + sub selection)
  coverage comes from within the 8 status-filter specs + the 2 round-trip
  specs, not as dedicated additional specs. No separate "drill-down" spec
  required; the expansion assertion is folded into each status-filter
  test's setup (click parent, click sub). The **existing** "should expand
  Done segment" + "should reveal Pending sub" specs (lines 77–93 of the
  current file) remain as the focused drill-down regression guards.

### Spec count bookkeeping

- **D-18:** Final spec count in `dashboard.page.spec.ts` after Phase 77
  lands: **26 tests** (11 existing + 15 new). UAT-01 contributes 5:
    1. Per-file selection (multi-file click accumulates; bulk bar reacts)
    2. Shift-range select (shift+click extends range; verify N-count)
    3. Page-scoped header select-all (toggle header checkbox selects all
       visible rows; does not cross pagination)
    4. Bulk bar visibility + Clear link (strict: toast + clear + hide on
       each of the 5 actions; single consolidated spec)
    5. **FIX-01 union — DELETED + Queue** (per D-06, pre-seeded DELETED
       row; alone and mixed; asserts Queue enabled + dispatches)
  UAT-02 contributes 10 per D-13 + D-14 (8 status + 2 round-trip).
- **D-19:** If the planner discovers during research that UAT-01 item 4
  ("each of the 5 bulk actions") reads more naturally as 5 separate specs
  (one per action) instead of one consolidated spec, the count shifts to
  9 UAT-01 + 10 UAT-02 = 19 new, 30 total. CONTEXT intent: each action's
  dispatch is asserted at least once — planner picks the packaging that
  reads best. Note the requirement reads "5 new Phase 72 specs" but the
  success criterion #1 lists scenarios, not exact spec count — treat "5
  new specs" as a floor, not a ceiling, for UAT-01.

### CI gating

- **D-20:** "CI-gated via `make run-tests-e2e`" (REQUIREMENTS.md UAT-01,
  UAT-02) is satisfied by the **existing** Docker harness (`Makefile`
  lines 113–188). No new CI workflow file; no new make target. Planner
  verifies that the existing CI run picks up the new specs automatically
  (Playwright's `testMatch: '**/*.spec.ts'` already globs the file) and
  that the Docker build + run-through stays green on amd64 + arm64.
- **D-21:** No retry tuning, no Playwright reporter changes. Current
  config (`retries: 2` on CI, `timeout: 30000`, `expect.timeout: 10000`)
  stays. If a seed step or status-wait proves flaky on CI, the planner
  adjusts timeouts per-test via `test.slow()` or helper-level waits
  rather than bumping global config.

### Claude's Discretion

- Exact file chosen to seed into DELETED status (D-08 recommends `joke`;
  planner can pick a different file if naming collision or locale sort
  issues surface).
- Exact names of the new page-object helpers (D-11 lists targets by
  intent; planner matches existing naming conventions).
- Whether UAT-01 item 4 becomes one consolidated spec or 5 per-action
  specs (D-19).
- Ordering within each `describe` block beyond the destructive-last rule
  (D-07).
- Whether to use `test.describe.serial()` for the UAT-01/UAT-02 blocks to
  make the "destructive last + seed-only-in-beforeAll" contract explicit.
- Toast-text assertion precision — partial match (`toContainText`) vs
  exact (`toHaveText`). Recommend partial to reduce localization churn.
- Empty-state selector shape — planner reads the Angular template to
  find the existing empty-state panel (if any) or decides whether an
  empty-state is even rendered for zero-match filters. If no empty-state
  exists, the filter specs assert `row count = 0` instead.

### Folded Todos

_None — `gsd-sdk query todo.match-phase 77` was not run; no todos were
surfaced during the discuss-phase scout. Pending project todos (CSP
detection → Phase 79, test warnings → Phase 79, encryption → Phase 81,
rate limiting → remains OOS) are owned by other v1.1.1 phases._

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement + milestone context
- `.planning/REQUIREMENTS.md` §UAT-01 — 5 Phase 72 specs (selection,
  shift-range, page-select-all, bulk-bar visibility, 5 bulk actions),
  CI-gated via `make run-tests-e2e`.
- `.planning/REQUIREMENTS.md` §UAT-02 — 10 Phase 73 specs (every
  `ViewFile.Status`, URL query-param round-trip, drill-down expansion,
  silent fallback on invalid filter values), CI-gated.
- `.planning/ROADMAP.md` §"Phase 77: Deferred Playwright E2E (Phases
  72 + 73)" — goal, dependency on Phase 76, success criteria (#4 locks
  FIX-01 coverage into at least one selection spec).

### Upstream phase decisions this phase honors
- `.planning/milestones/v1.1.0-phases/72-restore-dashboard-file-selection-and-action-bar/72-CONTEXT.md`
  — Phase 72 D-04 (selection clears on filter change), D-07 (card-internal
  bar), D-10 (bulk-bar button order + labels), D-12 (eligibility counts),
  D-17 (ConfirmModalService for Delete), D-19 (5 restored E2E tests,
  no new specs in Phase 72 itself).
- `.planning/milestones/v1.1.0-phases/73-dashboard-filter-for-every-torrent-status/73-CONTEXT.md`
  — Phase 73 D-01 (8 statuses reachable), D-04 (All/Active/Done/Errors
  segments + sub-button layout), D-09 (URL query-param format
  `?segment=<seg>&sub=<status>`), D-10 (Router queryParamsHandling:
  'merge'), D-11 (invalid params → silent fallback to All + URL sanitized).
- `.planning/phases/76-multiselect-bulk-bar-action-union/76-CONTEXT.md`
  — Phase 76 D-04 (union contract: button enabled iff >=1 selected row
  eligible), D-09 (mixed-selection unit-test cases — the FIX-01
  characterization parallel to the E2E coverage here).

### Design contracts (frozen — no UI changes in this phase)
- `docs/superpowers/specs/2026-04-15-drilldown-segment-filters-design.md`
  — Drill-down state machine, SCSS tokens, class names. Phase 77 reads
  this to write correct locators against `.btn-segment`, `.btn-sub`,
  `.segment-divider`, `--parent-expanded`, `--parent-active`, `.accent-dot`.
- `.planning/milestones/v1.1.0-phases/72-restore-dashboard-file-selection-and-action-bar/variant-B-card-internal-bar.html`
  — AIDesigner mockup, the identical-port target for Phase 72's bar.
  Useful for locator reference if template changes happened since.

### E2E infrastructure to extend
- `src/e2e/tests/dashboard.page.spec.ts` — Existing 11 tests. All 15 new
  specs land here per D-09. Destructive-last ordering per D-07.
- `src/e2e/tests/dashboard.page.ts` — Page object. New helpers per D-11
  land here in a Wave 1 plan before any spec work.
- `src/e2e/tests/app.ts` — Base class for page objects; no change expected.
- `src/e2e/playwright.config.ts` — `workers: 1`, `fullyParallel: false`,
  `retries: 2` on CI, `timeout: 30000`, `expect.timeout: 10000`. No
  changes per D-21.
- `src/e2e/package.json` — `@playwright/test ^1.48.0`, TypeScript ^5.3.0.
  No version bumps in this phase.
- New file: `src/e2e/tests/fixtures/seed-state.ts` — per D-04.
- `src/e2e/tests/urls.ts` — `Paths.DASHBOARD` export used by all specs.

### Docker harness (read-only for this phase)
- `Makefile` §`run-tests-e2e` (lines 113–188) — Build + compose-up + run
  + log + exit-code flow. Playwright already registers the specs via
  glob; no change required per D-20.
- `src/docker/test/e2e/compose.yml` — 3-service compose (tests + remote
  + configure). No change.
- `src/docker/test/e2e/configure/setup_seedsyncarr.sh` — App init via
  curl calls to `/server/config/set/*`. No change.
- `src/docker/test/e2e/remote/files/` — 9 fixture files (`áßç déÀ.mp4`,
  `clients.jpg`, `crispycat`, `documentation.png`, `goose`,
  `illusion.jpg`, `joke`, `testing.gif`, `üæÒ`). Unchanged per D-01.

### Backend command endpoints used by the seed helper
- `src/python/web/handler/controller.py` §`__handle_action_*` + bulk
  handler (lines 70–253) — the 5 command endpoints. Seed helper uses
  `POST /server/command/queue/<name>`, `POST /server/command/stop/<name>`,
  `POST /server/command/extract/<name>`, `DELETE /server/command/delete_local/<name>`,
  `DELETE /server/command/delete_remote/<name>`. No backend change.
- `src/python/web/handler/controller.py` §`__handle_bulk_command` (line
  253) — `POST /server/command/bulk` batch endpoint. Optional; seed
  helper may prefer per-file calls for clarity.

### Angular DOM surface (locator targets)
- `src/angular/src/app/pages/files/bulk-actions-bar.component.html` —
  `.bulk-actions-bar`, `.selection-label`, `button.clear-btn`,
  `button.action-btn` (5 actions). Locator names already used in
  existing `dashboard.page.ts`.
- `src/angular/src/app/pages/files/transfer-row.component.html` —
  `td.cell-checkbox input.ss-checkbox`, `td.cell-name .file-name`,
  `td.cell-status .status-badge`, `td.cell-size`.
- `src/angular/src/app/pages/files/transfer-table.component.html` —
  `thead th.col-checkbox input.ss-checkbox` (header select-all),
  `.transfer-table`, `.segment-filters`.
- `src/angular/src/app/pages/files/transfer-table.component.ts` —
  Segment state machine; reference for what each filter click will
  produce in the rendered DOM.
- `src/angular/src/app/services/files/view-file.ts` §`ViewFile.Status`
  (lines 90–100) — 8-value enum. Phase 77's status-filter specs map 1:1.
- `src/angular/src/app/services/utils/confirm-modal.service.ts` — Modal
  for Delete Local / Delete Remote confirmation; locator needed per D-11.
- `src/angular/src/app/common/localization.ts` — Toast text source.
  Specs assert via partial match (D-19 Claude's Discretion).

### Project-level rules
- `.planning/PROJECT.md` — Constraints (dark-only, Deep Moss + Amber
  palette, no visual redesign). Phase 77 is test-only; no UI touches.
- `/Users/julianamacbook/.claude/projects/-Users-julianamacbook-seedsyncarr/memory/feedback_design_spec_rigor.md`
  — "Port AIDesigner HTML identically." Does not apply to E2E test code;
  applies only if a spec's assertion would require a UI change (it
  should not, for this phase).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`dashboard.page.spec.ts` (11 existing tests)** — Established
  `test.describe('Testing dashboard page', ...)` + `beforeEach` pattern
  that navigates via `dashboardPage.navigateTo()`. Phase 77 appends two
  new describe blocks (UAT-01, UAT-02) inside the same file.
- **`DashboardPage` page object** — Already has `getRowCheckbox`,
  `getHeaderCheckbox`, `getActionBar`, `getActionButton`,
  `getSegmentButton`, `getSubButton`, `selectFileByName`,
  `clearSelectionViaBar`, `waitForAtLeastFileCount`. New helpers per
  D-11 land as methods alongside these.
- **Backend command endpoints** — All 5 action endpoints plus a bulk
  endpoint exist, documented in `controller.py`. Zero backend work;
  the seed helper wraps them.
- **SSE-driven status badges** — `td.cell-status .status-badge` renders
  the canonical status string. Use as the polling target in D-03.
- **Segment filter DOM** — `.segment-filters` wraps parents +
  sub-buttons; existing helpers `getSegmentButton('All'|'Active'|'Done'|
  'Errors')` and `getSubButton(<name>)` already typed against the 8
  allowed sub-labels — ready for UAT-02 specs.

### Established Patterns
- **`test.beforeEach(async ({ page }) => { ... })`** — Existing tests
  instantiate `new DashboardPage(page)` + navigate. Phase 77 additions
  follow the same pattern; `beforeAll` is the new addition for seeding.
- **`test.describe(...)` grouping** — Currently one big describe for the
  entire dashboard file. Phase 77 nests two inner describes (UAT-01,
  UAT-02) under it, or adds two sibling top-level describes — planner
  picks.
- **Partial-text locator via `getByRole('button', { name, exact: true })`**
  — Used for action buttons and sub-buttons. Reuse in new specs.
- **Order-independent comparison** — "should have a list of files"
  (lines 19–37) sorts both expected and actual to dodge locale-sort
  divergence between amd64/arm64 Chromium. Pattern to preserve when
  asserting filter-scoped row lists.
- **`workers: 1, fullyParallel: false`** — Sequential execution.
  `beforeAll` seeding runs once per file; state persists across tests in
  the file. D-07's "destructive last" ordering is the only contract that
  makes this safe.

### Integration Points
- **Seed helper ↔ backend** — `seed-state.ts` issues
  `fetch(baseURL + '/server/command/...')` or uses Playwright's
  `request` fixture. `baseURL` is already set in `playwright.config.ts`
  (`http://myapp:8800` in CI; overridable via `APP_BASE_URL`). Seed
  helper accepts the Playwright `Page` and re-uses its implicit
  `request` context so headers + bearer auth are consistent.
- **Bearer auth on `/server/*`** — v1.1.0 landed Bearer token auth on
  `/server/*` endpoints (see PROJECT.md Key Decisions). The E2E harness
  today navigates to the UI which bootstraps the token via meta tag
  injection; the seed helper must obtain the same token (either
  `page.request` context inherits the auth, or the helper reads the
  meta tag after initial navigation). Planner validates in research.
- **SSE → UI propagation** — After a seed action, there is a real delay
  before SSE fires and the status badge updates. D-03's `waitForFileStatus`
  absorbs this; Phase 77 does not add any new SSE subscription logic.
- **ConfirmModalService** — Delete Local / Delete Remote flow opens a
  modal (Phase 72 D-17). Spec must `click` the Confirm button in the
  modal before the dispatch actually fires. New helper
  `clickConfirmModalConfirm()` per D-11.

### Known Constraints
- **arm64 Docker build of `run-tests-python` fails** (rar package) but
  `run-tests-e2e` is unaffected. This phase runs on both amd64 and arm64
  per CI matrix.
- **SSE/LFTP lead time** — LFTP spawn + fake-remote SSH setup is not
  instantaneous. Seed timeouts should budget ~5–10s per transition on
  the harness.
- **No CSP violation listener in main suite yet** — Phase 79 (TEST-02)
  adds it. Phase 77's specs do not emit inline scripts; should not
  trigger CSP violations.

</code_context>

<specifics>
## Specific Ideas

- **Seed plan at phase start (suggested, planner refines):** `joke` →
  DELETED (for FIX-01); `clients.jpg` → queued/downloaded cycle (for
  DOWNLOADING/DOWNLOADED coverage); another file → STOPPED; extract an
  archive (e.g., `crispycat` if it's treated as archive) → EXTRACTING →
  EXTRACTED. EXTRACTING/QUEUED may be transient-only on the harness; if
  they can't be observed reliably, D-19 applies and the button-smoke
  variant lands for those two statuses.
- **"FIX-01 union" spec is the anchor of UAT-01**, not an after-thought.
  It is the regression guard for the Phase 76 fix. Place it prominently
  in the UAT-01 describe block with clear naming (e.g.,
  "union — DELETED + Queue re-queues from remote").
- **URL round-trip simplicity over breadth:** User picked one
  parent-level + one sub-level round-trip (D-14). The 8 status-filter
  specs cover "URL write" implicitly on every click; adding more reload
  tests is redundant. The two explicit reload tests prove the
  hydration-from-query-params path; that is the contract that was
  added in Phase 73.
- **Toast assertion style** — Phase 44 shipped the Triggarr-style toasts
  (M008). Toast text comes from `Localization.Bulk.*`. Use
  `toContainText` not `toHaveText` so localization churn doesn't break
  the spec.
- **DELETED row survival after Delete Local + Delete Remote** — Critical
  open question. If the row is purged from the model after both deletes,
  the FIX-01 fixture dies with it. Planner's research step: dispatch
  both deletes manually against the dev harness, observe whether the row
  sticks around with status="DELETED" or vanishes. Fallback: seed only
  `delete_local` (not `delete_remote`) to reach DELETED while preserving
  `remote_size > 0`, which is exactly the FIX-01 setup ("DELETED with
  remote still available → Queue re-queues from remote").

</specifics>

<deferred>
## Deferred Ideas

- **Back/forward browser navigation round-trip** — Explicitly out per
  D-16. Phase 73 deferred idea; revisit in a future phase if filter-
  persistence is extended with e.g. search-query persistence.
- **Cold-load URL via `page.goto(capturedURL)` in a fresh context** —
  D-15 scopes to `page.reload()` only. Cold-load is implicitly covered
  by the existing invalid-fallback test (line 101–110). Full cold-load
  coverage would duplicate the 2 reload specs; defer to a future phase
  if hydration bugs surface.
- **page.route() intercept for destructive actions** — Considered in
  discussion, rejected per D-07. A future phase could re-introduce
  interception to make the selection specs fully hermetic and runnable
  outside the Docker harness, but that's a different scope (unit-ish
  E2E).
- **Toast localization matrix** — All specs match toast text via partial
  match. If the app gains i18n, a future phase can introduce a locale-
  aware toast helper. Out of scope.
- **CSP violation detection in these specs** — Phase 79 (TEST-02) owns
  that. Phase 77 stays narrow on the two UAT scopes.
- **Per-action separate spec split (9 UAT-01 specs total, 30 file
  tests)** — Possible evolution per D-19. If the planner judges that
  one-spec-per-action reads better, CONTEXT.md does not block the
  split; just note it in the plan.
- **Extracting the existing 11 tests into their own file** — Considered,
  rejected per D-09. Keeping one dashboard spec file is the current
  convention; refactor later if the file gets unwieldy (>40 tests).
- **Per-test state reset / reusable reset endpoint** — Out of scope.
  Phase 77 uses `beforeAll` + destructive-last ordering. Adding a reset
  endpoint is infra work that belongs in a separate phase.

### Reviewed Todos (not folded)

_None surfaced during this discussion._

</deferred>

---

*Phase: 77-deferred-playwright-e2e-phases-72-73*
*Context gathered: 2026-04-20*
