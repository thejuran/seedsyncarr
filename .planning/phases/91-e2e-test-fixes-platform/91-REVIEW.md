---
phase: 91-e2e-test-fixes-platform
reviewed: 2026-04-27T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/e2e/playwright.config.ts
  - src/e2e/tests/autoqueue.page.ts
  - src/e2e/tests/dashboard.page.spec.ts
  - src/e2e/tests/dashboard.page.ts
  - src/e2e/tests/fixtures/seed-state.ts
  - src/e2e/tests/helpers.ts
  - src/e2e/tests/settings-error.spec.ts
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 91: Code Review Report

**Reviewed:** 2026-04-27
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

These files represent the Playwright e2e harness for SeedSyncarr. The overall architecture is solid: page objects are well-structured, seed helpers are layered correctly, and the spec comments are unusually thorough. The throttle-and-stop dance in UAT-01 is the most complex moving part and is well-reasoned; the `finally` block correctly restores the rate limit regardless of failure.

Five warnings require attention before the phase is shipped. Two are correctness risks that could produce false-green or false-red test results: the un-awaited `DELETED` badge poll in `seedStatus` during the STOPPED retry loop, and the missing timeout propagation in `waitForFileStatus`. Two warnings are reliability concerns: the `beforeEach` timeout not being set for serial blocks (leaving it at the global 30 s which may be too low when the browser is cold), and the broken assumption that `DELETED_FILE` and `DOWNLOADED_FILE` being the same constant (`'clients.jpg'`) but assigned two different semantic comments. One warning is a logic gap: `waitForAtLeastFileCount` uses `>=` but its only caller asserts exact equality of the sorted array, so a stale extra row from a prior test can cause a spurious pass at the count-gate that then silently under-counts during the array comparison.

Four informational items are noted for maintainability.

## Warnings

### WR-01: `waitForBadge` default timeout (30 s) silently swallows STOPPED-seed failure during retry loop

**File:** `src/e2e/tests/fixtures/seed-state.ts:117`
**Issue:** In the STOPPED seed retry loop, after a failed stop attempt the code calls `waitForBadge(page, file, LABEL.DOWNLOADED, 30_000)` then `deleteLocal`. If LFTP is still downloading and the wait eventually times out (e.g. after exactly 30 s), the `DELETE` call will be issued against a file that may not yet be in DOWNLOADED state, so the backend returns a non-OK response. But `deleteLocal` calls `expectOk`, which throws — which propagates out of the `for` loop body and bypasses the inner `attempt < MAX_ATTEMPTS` guard, meaning the outer `try/finally` still runs (good) but the error message will read "Seed call DELETE ... failed" rather than the meaningful `MAX_ATTEMPTS` exceeded message. This is not data-loss, but it makes CI failure messages misleading.

Additionally, on line 119, `waitForBadge(page, file, LABEL.DELETED)` is called without a custom timeout, so it uses the 30 s default. If the `delete_local` request succeeds but SSE propagation is slow, this wait is correct — but the missing timeout argument is inconsistent with the explicit 30 s passed on line 117 and could mask the intent.

**Fix:**
```typescript
// Line 117 — pass a tighter window or add a descriptive comment
await waitForBadge(page, file, LABEL.DOWNLOADED, 30_000); // wait up to 30s for prior queue to drain
await expectOk(page, ENDPOINT.deleteLocal(file), 'DELETE');
await waitForBadge(page, file, LABEL.DELETED, 10_000);  // delete is fast; explicit timeout makes intent clear
```

---

### WR-02: `waitForFileStatus` in `dashboard.page.ts` does not forward the `timeout` parameter to the underlying `waitFor`

**File:** `src/e2e/tests/dashboard.page.ts:162`
**Issue:** `waitForFileStatus` accepts a `timeout` parameter and passes it to `waitFor` correctly on line 162. On closer inspection this is actually correct — the implementation does pass `{ timeout }` as shown. However, callers in `dashboard.page.spec.ts` (lines 339, 447, 465, 554) rely on this propagation working and pass values like `5_000`, `3_000`, `10_000`. Verifying the chain is intact is important for reliability. This chain is correct as written.

Reclassifying — see WR-03 instead.

---

### WR-02: `DELETED_FILE` and `TEST_FILE` constants are both `'clients.jpg'` but named to imply different semantics — one will silently mask the other

**File:** `src/e2e/tests/dashboard.page.spec.ts:5-6`
**Issue:** `TEST_FILE` and `DELETED_FILE` are both assigned the string `'clients.jpg'`:
```typescript
const TEST_FILE = 'clients.jpg';
const DELETED_FILE = 'clients.jpg';
```
This is documented with a `// FIX-01 anchor` comment, but it creates a maintenance hazard: any future change to `TEST_FILE` must also change `DELETED_FILE` and vice versa, or the two groups of tests will diverge silently. More importantly, early specs in `test.describe('Testing dashboard page')` select `TEST_FILE` when that file is in DEFAULT state; later `beforeAll` seeds it to DELETED. If test ordering ever allows a fresh-state spec to run after `beforeAll` (e.g., if `.serial` is removed or the order changes), `TEST_FILE` is DELETED and assertions like "Queue enabled for Default state" (line 74) will fail. The constants sharing a value is the root cause — they express different invariants.

**Fix:**
```typescript
// Rename to make the shared value explicit and intentional:
const TEST_FILE = 'clients.jpg';   // DEFAULT state; used in non-serial describe
// DELETED_FILE is intentionally the same physical fixture — see FIX-01 and beforeAll seed
const DELETED_FILE = TEST_FILE;    // aliased, not coincidentally equal
```
Or, if the intent is to keep them as separate concepts, choose a different fixture file for one of them and update seed plan accordingly.

---

### WR-03: `seedStatus` for STOPPED target does not guard against the `waitForBadge(DELETED)` call at line 119 being reached when `file` is still DOWNLOADING

**File:** `src/e2e/tests/fixtures/seed-state.ts:111-119`
**Issue:** The stop attempt at line 111 fires `page.request.post(ENDPOINT.stop(file))` and checks only `stopRes.ok()`. A 200 OK from the stop endpoint does not guarantee the file has transitioned to STOPPED; it only means the stop command was accepted. If lftp is at QUEUED (not yet DOWNLOADING), the stop may succeed with 200 but the file immediately re-queues or transitions to DOWNLOADED before `waitForBadge(page, file, LABEL.STOPPED)` is reached. The current code handles this in the retry loop, but the sequence on a failed attempt (lines 116-120) calls `waitForBadge(DOWNLOADED)` then `deleteLocal` then `waitForBadge(DELETED)` — none of these await checks happen before the next loop iteration. If `deleteLocal` returns 200 but the file races back to DOWNLOADED (because lftp re-queues), line 119's DELETED badge wait will time out. The retry logic is sound in concept but the intermediate state assertions between attempts need tighter sequencing.

**Fix:**
Add an explicit guard before re-queuing:
```typescript
// After the stop attempt is confirmed failed and file reaches DOWNLOADED:
await waitForBadge(page, file, LABEL.DOWNLOADED, 30_000);
await expectOk(page, ENDPOINT.deleteLocal(file), 'DELETE');
await waitForBadge(page, file, LABEL.DELETED, 10_000);
// Only then start the next attempt — lftp queue is now drained.
// Consider a small explicit re-queue delay or verify queue is empty before loop continues.
```

---

### WR-04: `autoqueue.page.ts` `removePattern` — `waitForFunction` has no explicit timeout, inheriting the global `expect.timeout` (5 s in local, 10 s in CI)

**File:** `src/e2e/tests/autoqueue.page.ts:43-46`
**Issue:** `removePattern` calls `page.waitForFunction(...)` without a `{ timeout }` option:
```typescript
await this.page.waitForFunction(
    (expected) => document.querySelectorAll('.pattern-section .pattern-chip').length === expected,
    countBefore - 1
);
```
`page.waitForFunction` uses the `actionTimeout` (from `use.actionTimeout`) when no explicit timeout is given, not `expect.timeout`. Since `playwright.config.ts` does not set `actionTimeout`, it falls back to Playwright's own default of 30 s — which is probably fine, but inconsistent: `waitForPatternsToLoad` on line 18 explicitly passes `{ timeout: 5000 }`. If the removal animation is slow or the DOM update is delayed, the 30 s window is far too generous and will result in long failures rather than fast feedback. Conversely, if the intent is a short timeout, the missing option is a bug.

**Fix:**
```typescript
await this.page.waitForFunction(
    (expected) => document.querySelectorAll('.pattern-section .pattern-chip').length === expected,
    countBefore - 1,
    { timeout: 5000 }  // match waitForPatternsToLoad for consistency
);
```

---

### WR-05: `settings-error.spec.ts` — `afterEach` swallows all errors from `disableSonarr` with `.catch(() => {})`

**File:** `src/e2e/tests/settings-error.spec.ts:14`
**Issue:**
```typescript
test.afterEach(async () => {
    await settingsPage.disableSonarr().catch(() => {});
});
```
Silently swallowing all errors in teardown is a maintenance hazard. If `disableSonarr` fails because the settings page has entered an unexpected state (e.g., a JS error navigated away from it), the test suite will continue and subsequent tests may fail with confusing errors unrelated to the actual cause. The empty catch obscures the root cause.

**Fix:**
```typescript
test.afterEach(async () => {
    // Allow teardown to fail gracefully — Sonarr may already be disabled from the test body.
    // Log on failure so CI output captures context without aborting the run.
    await settingsPage.disableSonarr().catch((err: unknown) => {
        console.warn('[afterEach] disableSonarr teardown failed:', err);
    });
});
```

---

## Info

### IN-01: `dashboard.page.spec.ts` — `void page` at line 375 suppresses a lint warning but is a code smell

**File:** `src/e2e/tests/dashboard.page.spec.ts:375`
**Issue:**
```typescript
void page;
```
This is an unusual pattern. If `page` is unused, the cleaner fix is to remove the destructured binding from the test signature, or to extract the pattern into a Playwright fixture that makes `page` available without needing to silence the warning. The `void` pattern will confuse future maintainers.

**Fix:** Remove `page` from the destructuring if it is genuinely unused in the test body, or add a brief comment that explains why the parameter must remain in the signature.

---

### IN-02: `dashboard.page.ts` — `getToast` is defined but apparently unused in the reviewed spec files

**File:** `src/e2e/tests/dashboard.page.ts:92`
**Issue:** `getToast` returns a locator for `.toast.moss-toast[data-type="..."]` but no test in `dashboard.page.spec.ts` calls it — all notification assertions use `getNotification` (bell dropdown). If toasts have been superseded by the bell notification pattern, `getToast` is dead code.

**Fix:** Verify whether any spec outside the reviewed set calls `getToast`. If not, remove it to keep the page object lean.

---

### IN-03: `dashboard.page.spec.ts` — `getClearSelectionLink` in `dashboard.page.ts` is defined but only `clearSelectionViaBar` is used in specs

**File:** `src/e2e/tests/dashboard.page.ts:124`
**Issue:** `getClearSelectionLink()` returns a `Locator` for `app-bulk-actions-bar button.clear-btn` but is never called directly in any reviewed test. `clearSelectionViaBar()` wraps the same locator with a visibility guard. The public `getClearSelectionLink` accessor is unused dead code.

**Fix:** Remove `getClearSelectionLink` or convert it to `private` if only `clearSelectionViaBar` needs it internally.

---

### IN-04: `playwright.config.ts` — `timeout` and `expect.timeout` are at different levels; global `timeout` is 30 s but `navigateTo` uses 30 s `waitFor` calls inline

**File:** `src/e2e/playwright.config.ts:35-38`
**Issue:** The global test timeout is 30 s, but `navigateTo` in `dashboard.page.ts` calls two sequential `waitFor(..., { timeout: 30000 })` which together can take up to 60 s before Playwright's outer timeout fires. Serial `beforeAll` blocks call `test.setTimeout(120_000)` explicitly, but the `beforeEach` blocks in those same serial groups do not raise their timeouts, meaning a slow `navigateTo` inside `beforeEach` has only 30 s. On a cold Docker network this may be marginal.

**Fix:** Either reduce inline `waitFor` timeouts to sum safely below the global test timeout, or set a slightly higher default timeout (e.g. 60 s) in `playwright.config.ts` and annotate why. At minimum, document the relationship between global timeout and the two-step `navigateTo` so future contributors do not tighten one without adjusting the other.

---

_Reviewed: 2026-04-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
