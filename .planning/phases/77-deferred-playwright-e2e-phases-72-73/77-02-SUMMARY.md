---
phase: 77-deferred-playwright-e2e-phases-72-73
plan: 02
subsystem: e2e-test-selection-and-bulk-bar
tags: [playwright, e2e, selection, bulk-bar, fix-01, uat-01]
dependency-graph:
  requires:
    - src/e2e/tests/fixtures/seed-state.ts  # seedMultiple import (Plan 01 artifact)
    - src/e2e/tests/dashboard.page.ts       # 9 new helpers (Plan 01 artifact)
    - src/angular/src/app/common/localization.ts  # Bulk.SUCCESS_* text source
    - src/python/web/handler/controller.py  # /server/command/* precondition contracts
  provides:
    - "5 UAT-01 specs in src/e2e/tests/dashboard.page.spec.ts under describe.serial('UAT-01: selection and bulk bar', ...)"
  affects:
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-03-PLAN.md  # Plan 03 (UAT-02) adds a sibling describe; clients.jpg DELETED fixture is re-seeded there independently
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-04-PLAN.md  # Plan 04 runs the full --grep "UAT-01" smoke pass against the Docker harness
tech-stack:
  added: []
  patterns:
    - "test.describe.serial() sibling block with test.beforeAll(seedMultiple(...))"
    - "Destructive-last ordering inside describe.serial (non-destructive specs first, bulk-action dispatch + FIX-01 Queue last)"
    - "dispatchAndAssert helper with 'success' | 'any' toastVariant branch (documents Extract weakening per Pitfall 3)"
    - "toContainText with count-tolerant regex (Queue|Re-queued|queued, Stop|stopped|Stopped, Delete|delete|removed|Removed)"
    - "waitForFileStatus('Syncing', 15_000) deterministic gate before Stop dispatch"
    - "Two-part FIX-01 spec: alone-selection assertion then clear + mixed-selection assertion before dispatch"
key-files:
  created: []
  modified:
    - src/e2e/tests/dashboard.page.spec.ts  # +211 lines (111 → 322); +5 tests (11 → 16)
decisions:
  - "Packaged UAT-01 item 4 per D-18 (consolidated 5-action dispatch spec) rather than D-19 split (5 per-action specs) — single narrative of 'selection leads to toast + clear + hide across actions' reads cleaner"
  - "Spec 4 Action 4 (Delete Local) targets documentation.png (DOWNLOADED) rather than illusion.jpg (STOPPED) — controller.py:1041 requires local_size not None; DOWNLOADED is the only seed target guaranteeing that precondition"
  - "Extract dispatch uses 'any' toastVariant (no archive fixtures in 9-file harness — RESEARCH Pitfall 3); coverage is button-smoke with inline doc note"
  - "FIX-01 spec placed AFTER bulk-bar spec — Queue re-dispatch against clients.jpg mutates DELETED → DOWNLOADING; Plan 03's UAT-02 describe re-seeds independently so no leak"
  - "Regex 'Queued|Re-queued|queued' matches Localization.Bulk.SUCCESS_QUEUED rendered text 'Queued N file(s) successfully' (verified against common/localization.ts:50-59)"
metrics:
  duration: "~4 min"
  completed: 2026-04-20
---

# Phase 77 Plan 02: Wave 2 UAT-01 Selection and Bulk Bar Summary

Five new UAT-01 specs in a sibling `describe.serial` block that regression-guard per-file selection, shift-range, page-scoped header select-all, the consolidated 5-action bulk dispatch contract, and the FIX-01 union anchor (Phase 76 SC#4).

## What Was Landed

### Task 1 — UAT-01 scaffolding + 3 non-destructive specs

Commit `e8a5863` — `test(77-02): add UAT-01 describe.serial scaffolding + 3 non-destructive specs`

Additions to `src/e2e/tests/dashboard.page.spec.ts`:
- `import { seedMultiple } from './fixtures/seed-state'`
- Top-level constants: `DELETED_FILE = 'clients.jpg'`, `DOWNLOADED_FILE = 'documentation.png'`, `STOPPED_FILE = 'illusion.jpg'`, `DEFAULT_FILE = 'goose'`
- New sibling `test.describe.serial('UAT-01: selection and bulk bar', ...)` block with per-describe `beforeAll` (seeds DELETED + DOWNLOADED + STOPPED fixtures once) and `beforeEach` (fresh DashboardPage nav)
- Spec 1: `UAT-01: per-file selection accumulates and bulk bar reacts` — three incremental selections, label asserts `'1 selected'`, `'2 selected'`, count reaches 3
- Spec 2: `UAT-01: shift-range select extends selection to contiguous rows` — anchor + shift-click; tolerant `>= 2` count assertion (PATTERNS line 34-36 warns about locale-sort divergence between amd64/arm64 Chromium)
- Spec 3: `UAT-01: page-scoped header checkbox selects all visible rows` — header click → `selected == visibleRowCount` and `>= 9`; toggle off hides bar

### Task 2 — Consolidated 5-action dispatch + FIX-01 union (destructive-last)

Commit `cc48864` — `test(77-02): add consolidated bulk-bar dispatch spec and FIX-01 union spec`

Appended to the UAT-01 describe block:
- Spec 4: `UAT-01: bulk bar visibility — all 5 actions dispatch, clear selection, and hide bar` — inline `dispatchAndAssert` helper with `'success' | 'any'` toastVariant branch. Action/file/variant mapping table documented at spec top (lines 187-216). All 5 actions dispatched:
  - Action 1 Queue on `testing.gif` (DEFAULT) → success
  - Action 2 Stop on `testing.gif` (re-queued → waited for `'Syncing'` badge via `waitForFileStatus` with 15s timeout) → success
  - Action 3 Extract on `documentation.png` (DOWNLOADED) → any-variant (non-archive fixture per Pitfall 3; button-smoke only, documented inline)
  - Action 4 Delete Local on `documentation.png` (DOWNLOADED; `clickConfirmModalConfirm` called after click) → success
  - Action 5 Delete Remote on `áßç déÀ.mp4` (DEFAULT; `clickConfirmModalConfirm` called after click) → success
- Spec 5: `UAT-01: FIX-01 union — DELETED row allows Queue (re-queue from remote), alone and mixed with DEFAULT` — three-part spec:
  - Part A: `waitForFileStatus(DELETED_FILE, 'Deleted', 10_000)` gate, then select-alone, assert `getActionButton('Queue')).toBeEnabled()` and `getActionButton('Delete Remote')).toBeEnabled()`
  - Part B: clear selection, then select `DELETED_FILE + DEFAULT_FILE`, assert count = 2 and Queue still enabled
  - Part C: dispatch Queue; assert success toast (`toContainText(/Queued|Re-queued|queued/)`), action bar hidden, selected count = 0

Order inside UAT-01 describe after both tasks (top to bottom): per-file → shift-range → page-select-all → bulk-bar dispatch → FIX-01 union. FIX-01 is destructive-last because its Queue dispatch re-queues `clients.jpg` back to DOWNLOADING and destroys the DELETED fixture; Plan 03's UAT-02 block seeds independently via its own `beforeAll`, so the FIX-01 mutation cannot leak across describes.

## Verification

- `cd src/e2e && npx tsc --noEmit` — exits 0.
- File length: 322 lines (baseline 111; delta +211 lines — matches 5 new specs + describe scaffolding + dispatchAndAssert helper + mapping-table comment block).
- Existing `describe('Testing dashboard page', ...)` block preserved verbatim — 11 tests match via `awk 'NR==1,/^}\);$/' ... | grep -cE "^    test\('"` → 11.
- UAT-01 describe block tests — exactly 5 via `awk '/describe.serial..UAT-01/,0' ... | grep -cE "^    test\('UAT-01: "` → 5.
- Full-harness Playwright run `npx playwright test tests/dashboard.page.spec.ts --grep "UAT-01"` is deferred to Plan 04 (planner-sanctioned per plan line 465 "verification deferred to Plan 04 smoke if harness not running locally") — the executor does not have a Docker harness running in this worktree. Plan 04 will validate the 5 specs pass with 0 retries under `workers: 1, fullyParallel: false` and the `describe.serial()` wrapper.

## Toast Keyword Regex — Validation

Verified against `src/angular/src/app/common/localization.ts:50-59`:

| Action | `Localization.Bulk.SUCCESS_*` string (rendered) | Plan regex | Matches? |
|--------|-------------------------------------------------|------------|----------|
| Queue | `Queued N file[s] successfully` | `/Queued\|Re-queued\|queued/` | yes (`Queued`) |
| Stop | `Stopped N file[s] successfully` | `/Stop\|stopped\|Stopped/` | yes (`Stop` + `Stopped`) |
| Extract | `Extracted N file[s] successfully` | `/.*/` (any-variant) | yes (tautological — any toast) |
| Delete Local | `Deleted N local file[s] successfully` | `/Delete\|delete\|removed\|Removed/` | yes (`Delete` + `Deleted`) |
| Delete Remote | `Deleted N remote file[s] successfully` | `/Delete\|delete\|removed\|Removed/` | yes (`Delete` + `Deleted`) |

No regex adjustments were needed vs. the plan. `Re-queued` does not appear in `Bulk.SUCCESS_QUEUED` but is kept as a tolerant fallback for any future wording revision — harmless because `toContainText` only needs one branch to match.

## Deviations from Plan

**None — plan executed exactly as written.** The plan anticipated every edge case (locale-sort fragility, Pitfall 3 Extract weakening, controller.py:1041 precondition for Delete Local, FIX-01 destructive-last ordering, Syncing gate for Stop). Two very minor textual additions that do not change behavior:

1. Added `void page;` at the end of FIX-01 spec (line 315) to silence a potential TS6133 "unused parameter" warning on the `{ page }` destructure. The `page` parameter is retained in the signature for consistency with the other 3 specs that use it, and to keep future fixture-expansion low-friction (a Part D that reads a row-level DOM element via `page.locator` could land without a signature change). TypeScript check passes either way — this is a belt-and-suspenders add.
2. Package-lock at `src/e2e/package-lock.json` was refreshed by a local `npm install --ignore-scripts` (needed to run `npx tsc --noEmit` in the fresh worktree). This file is untracked in the repo and was untracked before Plan 02 began (present in the initial worktree status snapshot as `??`). Not staged in either task commit.

## Commits

- `e8a5863` — `test(77-02): add UAT-01 describe.serial scaffolding + 3 non-destructive specs` — Task 1
- `cc48864` — `test(77-02): add consolidated bulk-bar dispatch spec and FIX-01 union spec` — Task 2

## Downstream Consumers

- Plan 03 (UAT-02): appends a sibling `test.describe.serial('UAT-02: ...')` block that also imports `seedMultiple` and runs a separate `beforeAll` seed. Plan 02's destruction of the DELETED fixture at the end of Spec 5 does not leak into Plan 03.
- Plan 04 (integration smoke): runs the full `npx playwright test --grep "UAT-01"` inside the Docker harness as the final verification of this plan's 5 specs.

## Threat Flags

None. Test-additive; no production code or dependencies changed. Mitigations for `T-77-04` (destructive-action leak) and `T-77-05` (drifted DELETED fixture) are both in place:
- `T-77-04`: `describe.serial()` wrapper causes remaining specs in the block to fail-fast if an earlier spec fails; destructive-last ordering guarantees DELETED fixture survives through Spec 4; `beforeAll` is per-describe so sibling describes seed independently.
- `T-77-05`: Spec 5 opens with `waitForFileStatus(DELETED_FILE, 'Deleted', 10_000)` — hard-fails if the fixture is not in DELETED state at spec start.

## Self-Check: PASSED

- `src/e2e/tests/dashboard.page.spec.ts` — FOUND (modified: 322 lines, +211 from 111 baseline)
- Commit `e8a5863` — FOUND in git log
- Commit `cc48864` — FOUND in git log
- TSC clean: yes (`cd src/e2e && npx tsc --noEmit` exits 0)
- 5 UAT-01 test() calls inside describe.serial block: verified
- Existing 11 tests in 'Testing dashboard page' describe untouched: verified
- No unexpected file deletions: verified (`git diff --diff-filter=D --name-only HEAD~2 HEAD` returns empty)
