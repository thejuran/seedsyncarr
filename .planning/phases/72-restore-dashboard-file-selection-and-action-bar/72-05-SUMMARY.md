---
phase: 72-restore-dashboard-file-selection-and-action-bar
plan: 05
status: complete
decisions: [D-19]
tasks_completed: 2
files_modified:
  - src/e2e/tests/dashboard.page.ts
  - src/e2e/tests/dashboard.page.spec.ts
---

# 72-05 Summary — E2E Playwright restore (D-19)

## 5 restored test names

1. `should show and hide action buttons on select`
2. `should show action buttons for most recent file selected`
3. `should have all the action buttons`
4. `should have Queue action enabled for Default state`
5. `should have Stop action disabled for Default state`

All five were `test.skip()` stubs with a `v1.1.0: app-file-actions-bar
removed` rationale comment; they are now real `test()` bodies that drive the
restored dashboard via the new page-object helpers.

## Total test count in dashboard.page.spec.ts

Exactly **7** (2 pre-existing + 5 restored). No new tests beyond the 5
originals per D-19 ("No new E2E tests beyond restoring the originals").
Deferred to a follow-up phase: select-all header click, shift-click range,
cross-status eligibility permutations, destructive-action confirmation modal.

## New page-object methods on DashboardPage

Added to `src/e2e/tests/dashboard.page.ts`:

- `getRowCheckbox(fileName: string): Locator` — anchored-regex row match
  against `td.cell-name .file-name`, returns the `td.cell-checkbox
  input.ss-checkbox` locator
- `getHeaderCheckbox(): Locator` — the page-scoped select-all at
  `thead th.col-checkbox input.ss-checkbox`
- `getActionBar(): Locator` — the inner `.bulk-actions-bar` div (the bar's
  `@if (hasSelection)` means the host tag exists even when hidden, so the
  locator targets the inner div for correct visibility assertions)
- `getActionButton(name): Locator` — `getByRole('button', {name, exact:
  true})` scoped to `app-bulk-actions-bar`, name-typed to the 5 action
  labels
- `selectFileByName(fileName): Promise<void>` — clicks the row checkbox
- `clearSelectionViaBar(): Promise<void>` — clicks the bar's `.clear-btn`
  if visible (no-op otherwise)
- `_escapeRegex(s): string` — defensively escapes special chars in file
  names for the anchored-regex match

## TEST_FILE constant

Added `const TEST_FILE = 'clients.jpg';` at file scope immediately after
the imports and before `test.describe(...)`. Referenced 7 times across the
5 restored tests (tests 1, 3, 4, 5 each reference it once; test 2
references it twice via `selectFileByName(TEST_FILE)` and an immediately
following second selection of the literal `'goose'`). If the E2E dataset
rotates this file name, only the constant needs updating.

## Runtime verification status

The `src/e2e/tsconfig.json` TypeScript compilation passes cleanly with
zero errors. Static acceptance checks verified:

- `grep -c "test.skip(" ...` → `0`
- `grep -cE "^[[:space:]]*test\(" ...` → `7`
- `grep -c "TEST_FILE" ...` → `7`
- `grep -c "app-file-actions-bar" ...` → `0`
- `grep -c "selectFileByName" ...` → `7`

**Runtime Playwright execution was NOT run as part of this plan's
execution step.** The full E2E suite requires the Docker test backend
(`make run-tests-e2e`, which depends on `STAGING_VERSION`,
`SEEDSYNCARR_ARCH`, and a pulled staging image — see Makefile:113-137).
This harness is not set up in the dev environment and is separately
documented as arm64-fragile in STATE.md tech-debt ("`make
run-tests-python` Docker build fails on arm64 — `rar` package
amd64-only; CI unaffected"). The restored tests are expected to be
validated by CI on the next push.

The selectors used were produced by plans 01/03/04 and are enforced by
component-level unit-spec acceptance criteria (bulk-actions-bar: 33
specs; transfer-row: 22 specs; transfer-table: 42 specs — all green in
Karma). Any drift between unit-level DOM and E2E selectors would surface
in CI and localize to the single-line page-object helper rather than 5
separate test bodies.

## Selector surprises encountered

None at static-analysis time. Noted for future reference:

- `getActionBar()` targets the inner `.bulk-actions-bar` div rather than
  the `app-bulk-actions-bar` host because the bar uses an internal
  `@if (hasSelection)` guard — the host element remains in the DOM but
  the inner div is conditionally rendered. Asserting visibility on the
  host would always be truthy.
- `TEST_FILE` is `clients.jpg`; its DEFAULT status makes it queueable
  but not stoppable, which tests 4 and 5 rely on. If the E2E dataset
  rotates to a file whose status differs, tests 4 and 5 will need
  parallel updates, not just the constant.

## D-19 compliance confirmation

- 5 skipped tests restored: ✓
- No new tests added beyond the 5 originals: ✓
- Page-object helpers reusable by future phases: ✓ (the new helpers
  cover row checkbox, header checkbox, bar visibility, and 5 named
  action buttons — future phases adding select-all-header or
  shift-click tests can reach for `getHeaderCheckbox()` directly)
- Dataset coupling localized: ✓ (`TEST_FILE` constant)
