---
phase: 77-deferred-playwright-e2e-phases-72-73
fixed_at: 2026-04-20T00:00:00Z
review_path: .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 77: Code Review Fix Report

**Fixed at:** 2026-04-20
**Source review:** `.planning/phases/77-deferred-playwright-e2e-phases-72-73/77-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (all Warnings; Info findings excluded — `--all` flag not set)
- Fixed: 3
- Skipped: 0

**Validation:** All fixes validated via `cd src/e2e && npx tsc --noEmit` (clean exit). Docker E2E harness execution is CI-only per phase constraints.

**Constraints honored:**
- D-10: No changes to any of the 11 tests in the `'Testing dashboard page'` describe block. Only the UAT-01 / UAT-02 `describe.serial` blocks, the page object, and the seed-state fixture were touched.
- D-21: `playwright.config.ts`, `package.json`, and retry counts untouched.

## Fixed Issues

### WR-03: `getSelectedCount` can return stale 0 when bar is transitioning

**Files modified:** `src/e2e/tests/dashboard.page.ts`
**Commit:** 1dbf2ec
**Applied fix:** Replaced the `isVisible()` snapshot + `textContent` regex approach with a direct DOM row-state count of checked row checkboxes (`.transfer-table tbody app-transfer-row td.cell-checkbox input.ss-checkbox:checked`). This matches the review's "more robust" suggestion — the count is derived from the authoritative source (actual selection state in row checkboxes) rather than the label text that races against the bulk bar's show/hide animation and Angular change detection. Works correctly in both transition windows the review identified (post-select before label update; post-dispatch before bar hide).

### WR-02: `seed-state.seedStatus` can race on STOPPED target

**Files modified:** `src/e2e/tests/fixtures/seed-state.ts`
**Commit:** 3904585
**Applied fix:** In the `STOPPED` branch, replaced the unconditional `waitForBadge(page, file, LABEL.DOWNLOADING)` with a race waiter that accepts either `DOWNLOADING` or `DOWNLOADED` as a terminal state for the first wait. After the race resolves, re-read the badge textContent; if it settled on `DOWNLOADED` the function throws a distinguishable error ("missed the transient DOWNLOADING window — stop is a no-op from this state; cannot reach STOPPED. Pick a larger fixture or re-queue."), surfacing the root cause instead of letting the subsequent `STOPPED` wait silently time out at 30s. Uses the same row-scoped Locator-chain shape as `waitForBadge` with `escapeRegex` for the file name.

### WR-01: Destructive Delete Remote in UAT-01 contaminates UAT-02 assumption

**Files modified:** `src/e2e/tests/dashboard.page.spec.ts`
**Commit:** cd2f2bb
**Applied fix:** Narrowed the harness-composition comment on the UAT-02 "status filter pending" spec (at the `rowCount >= 1` assertion). The old inline comment claimed a strict 6-file DEFAULT bucket, but UAT-01 mutates `áßç déÀ.mp4` (Delete Remote) and `testing.gif` (Queue/Stop), and UAT-02's `beforeAll` only re-seeds the three named fixtures (DELETED / DOWNLOADED / STOPPED). The test's actual assertion (`>= 1 row`) already tolerates the cross-block state leak; the comment now documents that tolerance explicitly and cites WR-01 for traceability. Chose the review's minimum-fix option (narrow the comment) over Option A (extend `beforeAll` re-seed plan — infeasible because `SeedTarget` has no `DEFAULT` restore variant) or Option B (pick a different Delete Remote target — would have required broader spec changes for marginal benefit given the existing assertion tolerance).

---

_Fixed: 2026-04-20_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
