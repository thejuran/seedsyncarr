---
phase: 77-deferred-playwright-e2e-phases-72-73
reviewed: 2026-04-20T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/e2e/tests/dashboard.page.spec.ts
  - src/e2e/tests/dashboard.page.ts
  - src/e2e/tests/fixtures/seed-state.ts
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 77: Code Review Report

**Reviewed:** 2026-04-20
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Phase 77 adds a new `seed-state` fixture module (113 lines), extends `DashboardPage` with 9 helpers, and appends two `test.describe.serial` blocks (15 new specs total) to the existing `dashboard.page.spec.ts`. The implementation is generally high quality: TypeScript types are precise (discriminated `SeedTarget` union, `as const` label map, explicit `Promise<void>` returns), selector strategy reuses the established anchored-regex Locator-chain from the original page object, and inline commentary documents the backend contracts it depends on (controller.py line refs, RESEARCH Pitfalls, D-IDs).

No critical issues were found — no hardcoded secrets, no dangerous function usage, no injection surface (the sole dynamic URL construction goes through `encodeURIComponent`), and no crashing null-dereference patterns. The warnings below flag correctness/test-isolation gaps that could produce flakes or false passes; the info items note stylistic/duplication opportunities.

The overall style aligns well with the pre-existing 11 specs (beforeEach `navigateTo`, Locator helpers, `getByRole({ exact: true })`). The two main consistency concerns are (1) the locator accessor for `.selection-label` is inlined in three places instead of using a page-object helper, and (2) the new `seedMultiple` beforeAll in UAT-02 re-runs a 15-30s pipeline that duplicates UAT-01's seed work without any checkpoint to detect the "already-seeded" case.

## Warnings

### WR-01: Destructive Delete Remote in UAT-01 contaminates UAT-02 assumption

**File:** `src/e2e/tests/dashboard.page.spec.ts:284`
**Issue:** The "all 5 actions" spec dispatches `Delete Remote` on `'áßç déÀ.mp4'`. Per the controller contract that file's row will be mutated (remote_size cleared; likely DELETED). UAT-02 Task 1 spec "status filter pending" at line 361 asserts the DEFAULT bucket still contains `'áßç déÀ.mp4'` — quoting from the inline comment: *"6 of 9 harness files: 'áßç déÀ.mp4', 'crispycat', 'goose', 'joke', 'testing.gif', 'üæÒ'"*. Because UAT-01 runs first (file lexical order in Playwright's serial scheduler and `describe.serial` only guarantees ordering within a block, not across blocks), UAT-02 may inherit a harness where `áßç déÀ.mp4` is no longer in DEFAULT. The spec tolerates this (it only asserts `>= 1 row`), but the comment is now misleading and a future tightening would fail.

Additionally, UAT-02's `beforeAll` only re-seeds `DELETED_FILE`, `DOWNLOADED_FILE`, `STOPPED_FILE` — it does **not** restore `'áßç déÀ.mp4'` or `'testing.gif'`, both of which UAT-01 mutates (Queue → Syncing → Stop on testing.gif; Delete Remote on áßç déÀ.mp4).

**Fix:**
```ts
// Option A: add these fixtures to UAT-02's beforeAll re-seed plan, OR
// Option B: restrict UAT-01's Delete Remote target to a file NOT referenced
//          by any UAT-02 spec (e.g. a dedicated ephemeral fixture), OR
// Option C: isolate the two describe.serial blocks with distinct projects or
//          explicit pretest teardown that calls a /server/command/reset endpoint.
// At minimum, drop the harness-composition comment at line 361 or narrow it:
//   "DEFAULT bucket contains at least one row (exact composition depends on
//    UAT-01 destructive run order)."
```

### WR-02: `seed-state.seedStatus` can race on STOPPED target (waitForBadge uses locator-visible, not state-stable)

**File:** `src/e2e/tests/fixtures/seed-state.ts:84-90`
**Issue:** For `target === 'STOPPED'`, the pipeline is: POST queue → wait for `Syncing` badge → POST stop → wait for `Failed` badge. The DOWNLOADING window is inherently narrow on the test harness (per inline Pitfall 4 comment at line 414: *"DOWNLOADING is transient — LFTP drains the queue on an idle harness within ms"*). If LFTP drains the file to DOWNLOADED before `waitForBadge(page, file, LABEL.DOWNLOADING)` sees the transient badge, that `waitFor` will time out at the default 30s even though the stop endpoint call that follows would still be meaningful (stop is a no-op on DOWNLOADED, but the subsequent `waitForBadge(..., LABEL.STOPPED)` will never resolve). This is a latent flake source: the small test files (clients.jpg = 40 KB, illusion.jpg = 80 KB) are most at risk.

The existing 30s default absorbs LFTP spawn latency but assumes DOWNLOADING is observable. There is no fallback branch, no `Promise.race` against a terminal state, and no diagnostic message distinguishing "never entered DOWNLOADING" from "backend is down".

**Fix:**
```ts
if (target === 'STOPPED') {
    await expectOk(page, ENDPOINT.queue(file), 'POST');
    // Race DOWNLOADING vs DOWNLOADED — if we missed the transient window,
    // the file is already Synced and stop won't reach STOPPED.
    const row = page.locator('.transfer-table tbody app-transfer-row', {
        has: page.locator('td.cell-name .file-name', {
            hasText: new RegExp(`^${escapeRegex(file)}$`),
        }),
    });
    await row.locator('td.cell-status .status-badge')
        .filter({ hasText: new RegExp(`^(${LABEL.DOWNLOADING}|${LABEL.DOWNLOADED})$`) })
        .waitFor({ timeout: 30_000 });
    await expectOk(page, ENDPOINT.stop(file), 'POST');
    await waitForBadge(page, file, LABEL.STOPPED);
    return;
}
```
If the race resolves on DOWNLOADED, fail fast with a clear error instead of timing out on STOPPED, e.g. by re-reading the badge text after the race and throwing if it's already `Synced`.

### WR-03: `getSelectedCount` can return stale 0 when bar is transitioning

**File:** `src/e2e/tests/dashboard.page.ts:120-128`
**Issue:** `getSelectedCount` uses `await label.isVisible()` (a synchronous-snapshot check), then reads `textContent` and regex-matches `^(\d+)\s+selected$`. Two race windows:

1. Between `selectFileByName` click and the `await expect(…).toHaveText('1 selected')` assertion, Angular's change detection cycle may not have updated the label text yet. The spec at line 147 calls `getSelectedCount()` *before* the `toHaveText` assertion, so if the label is still showing the old value (or is mid-transition to visible), the helper returns 0 or the stale count. This is why lines 147-148 combine both — but the pattern is fragile and future copies may drop the `toHaveText` assertion, silently weakening the check.
2. After a dispatch clears the selection, line 251 asserts `toBe(0)` — but if the bar's hide animation hasn't completed, `isVisible()` may still return `true` and the regex will match the old "1 selected" text, returning 1 instead of 0.

**Fix:** Make the helper wait on a stable condition before reading:
```ts
async getSelectedCount(): Promise<number> {
    const label = this.page.locator('app-bulk-actions-bar .selection-label');
    // Allow the bar's visibility state to stabilize; visible means text is authoritative.
    const isVisible = await label.isVisible().catch(() => false);
    if (!isVisible) return 0;
    // Wait for the label to settle into the "N selected" shape before reading.
    await label.waitFor({ state: 'visible' });
    const text = (await label.textContent()) ?? '';
    const match = text.trim().match(/^(\d+)\s+selected$/);
    return match ? Number(match[1]) : 0;
}
```
Or — more robust — derive the count from the DOM row state (`.transfer-table tbody app-transfer-row.selected` or checked-checkbox count), which does not depend on the bulk bar's animation timing.

## Info

### IN-01: `.selection-label` selector duplicated inline in three specs

**File:** `src/e2e/tests/dashboard.page.spec.ts:56, 148, 152` (also pre-existing line 59)
**Issue:** `page.locator('app-bulk-actions-bar .selection-label')` is repeated inline with a `toHaveText` assertion. The page object already has `getSelectedCount` for numeric access but no locator accessor for the label itself. Adding `getSelectionLabel(): Locator` would make assertions like `toHaveText('2 selected')` DRY and align with the existing `getActionBar`/`getActionButton` style.
**Fix:**
```ts
// In dashboard.page.ts:
getSelectionLabel(): Locator {
    return this.page.locator('app-bulk-actions-bar .selection-label');
}
// In specs:
await expect(dashboardPage.getSelectionLabel()).toHaveText('2 selected');
```

### IN-02: UAT-02 `beforeAll` duplicates UAT-01's seed plan (15-30s pipeline cost, no checkpoint)

**File:** `src/e2e/tests/dashboard.page.spec.ts:327-343`
**Issue:** Both describe.serial blocks run the identical 3-item seed plan in independent `beforeAll` hooks. UAT-02's block comment correctly explains why (UAT-01 mutates state), but the pipeline is `queue → waitForBadge(Synced) → deleteLocal → waitForBadge(Deleted)` for each of 3 files, sequentially — easily 30-60s of wall clock in CI. A pre-check that reads the current badges and skips the full seed when state already matches target would halve the block startup cost.
**Fix:** Add an early-return branch to `seedStatus`:
```ts
export async function seedStatus(page: Page, file: string, target: SeedTarget): Promise<void> {
    // If the row already displays the target label, skip the pipeline.
    const current = page.locator('.transfer-table tbody app-transfer-row', {
        has: page.locator('td.cell-name .file-name', { hasText: new RegExp(`^${escapeRegex(file)}$`) }),
    }).locator('td.cell-status .status-badge');
    const currentText = (await current.textContent().catch(() => ''))?.trim() ?? '';
    if (currentText === LABEL[target]) return;
    // ...existing pipeline...
}
```

### IN-03: `void page;` suppression in UAT-01 FIX-01 spec signals unused parameter

**File:** `src/e2e/tests/dashboard.page.spec.ts:287, 320`
**Issue:** The spec callback destructures `{ page }` but never uses `page` — the `void page;` at line 320 is a workaround for the `noUnusedParameters` lint. The cleaner fix is to drop the destructure entirely (as nine of the ten existing specs above do when they don't need `page`).
**Fix:**
```ts
test('UAT-01: FIX-01 union — DELETED row allows Queue (re-queue from remote), alone and mixed with DEFAULT', async () => {
    // ...body unchanged, no `void page;` needed
});
```

### IN-04: `getSubButton` return type collides with `getByText` semantics

**File:** `src/e2e/tests/dashboard.page.ts:76-78`
**Issue:** The helper uses `.btn-sub` → `getByText(name, { exact: true })`. Sub-buttons for different parent segments share some names (e.g. `Queued` appears under Active, `Extracted` under Done). On a freshly loaded dashboard where multiple segments have been expanded in earlier specs (segment state persists via URL), `getByText` may return a locator resolving to >1 element. The current specs happen to click only one parent at a time, so this doesn't surface, but the helper's type signature suggests single-button access and will strict-mode-fail if multiple sub-button groups are ever visible simultaneously.
**Fix:** Scope to the currently active parent, e.g. `.segment-filters .segment-group.active button.btn-sub`, or accept the parent name as a second argument.

### IN-05: UAT-02 empty-state specs tolerate false positives on test environments that DO have archives

**File:** `src/e2e/tests/dashboard.page.spec.ts:431-451`
**Issue:** The Extracting/Extracted empty-state specs assert `getEmptyRow()` is visible and rely on Pitfall 3 (*"all 9 harness fixtures are image/video/directory"*). If the harness fixture set ever grows to include an archive (a perfectly reasonable future change), these two specs will silently flip from "asserts emptiness" to "flakes randomly depending on extraction timing" — there's no guard that verifies the assumption.
**Fix:** Either add a positive assertion that the dashboard currently has zero archive-like fixtures (e.g. check there is no `.zip`/`.tar`/`.rar` in `getFiles()` output), or comment these specs as `test.fixme` with a harness-composition check.

### IN-06: `DELETED_FILE` shadows `TEST_FILE` (both `'clients.jpg'`)

**File:** `src/e2e/tests/dashboard.page.spec.ts:5-6`
**Issue:** `TEST_FILE` and `DELETED_FILE` are both bound to `'clients.jpg'`. The inline comment explains why (FIX-01 anchor, rejected 'joke' as a directory), but having two constants for the same string across 5 describe-block references makes refactors error-prone: a future change that swaps `DELETED_FILE` without also swapping `TEST_FILE` (used by non-serial specs that don't need DELETED state) would silently break the assumption. The original 11 specs use `TEST_FILE` expecting DEFAULT state; if UAT-01's `beforeAll` runs before them (Playwright does not guarantee file-order execution across projects), those 11 specs start seeing a DELETED row instead of DEFAULT.
**Fix:** Either (a) alias explicitly — `const DELETED_FILE = TEST_FILE;` with a comment that they are the same row, or (b) pick a distinct file for FIX-01 (though the research note says `'joke'` was rejected). At minimum, add a comment at `TEST_FILE` declaration warning that its state is mutated by UAT-01's beforeAll seed and the original 11 specs may need to be isolated into their own describe.serial block to guarantee ordering.

---

_Reviewed: 2026-04-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
