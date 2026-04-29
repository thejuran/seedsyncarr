---
phase: 95-test-coverage-e2e
reviewed: 2026-04-28T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/e2e/tests/logs.page.ts
  - src/e2e/tests/logs.page.spec.ts
  - src/e2e/tests/settings-fields.spec.ts
  - src/e2e/tests/settings.page.ts
findings:
  critical: 0
  warning: 5
  info: 2
  total: 7
status: issues_found
---

# Phase 95: Code Review Report

**Reviewed:** 2026-04-28T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four E2E test files were reviewed: two Page Object Model classes (`logs.page.ts`, `settings.page.ts`) and two spec files (`logs.page.spec.ts`, `settings-fields.spec.ts`). Cross-file analysis included the `App` base class, `csp-listener` fixture, `seed-state` fixture, the Angular template sources, and the Python backend config handler to validate URL paths, HTTP methods, and selector correctness.

CSS selectors, URL paths, and HTTP methods are all verified correct against the actual source. The CSP fixture lifecycle is sound. The `setUseSshKey` boolean-to-string conversion is safe because `_strtobool` in config.py accepts lowercase `"true"` / `"false"`.

The primary issues are: silent error swallowing in `afterEach` cleanup with no diagnostic output, an API key in a URL path, and two unused page object methods that inflate the public surface without test coverage.

## Warnings

### WR-01: `afterEach` Silently Swallows All Restoration Errors

**File:** `src/e2e/tests/settings-fields.spec.ts:23-25`
**Issue:** All three `afterEach` cleanup calls use `.catch(() => {})`, which silently discards any restoration failure (network timeout, 4xx/5xx from the backend, etc.). If a restoration call fails, the next test begins with stale config values. The failure will surface as a spurious assertion error in the subsequent test, making the root cause invisible. The pattern was copied from `settings-error.spec.ts` where it guards a single cleanup call; here it guards three independent restorations, each of which can fail independently.

**Fix:** At minimum, log the failure so the test report makes the cleanup failure visible. Prefer re-throwing so Playwright marks the test as failed:

```typescript
test.afterEach(async () => {
    const restore = async (label: string, fn: () => Promise<void>) => {
        try {
            await fn();
        } catch (e) {
            console.error(`[afterEach] Failed to restore ${label}:`, e);
            // Re-throw so Playwright marks the hook as failed rather than the next test
            throw e;
        }
    };
    await restore('remoteAddress',    () => settingsPage.setRemoteAddress(originalAddress));
    await restore('sshKey',           () => settingsPage.setUseSshKey(originalSshKey));
    await restore('remoteScanInterval', () => settingsPage.setRemoteScanInterval(originalScanInterval));
});
```

---

### WR-02: API Key Passed as URL Path Segment — Appears in Server Access Logs

**File:** `src/e2e/tests/settings.page.ts:33-35`
**Issue:** `setSonarrApiKey` sends the Sonarr API key as a plain path component in a GET request to `/server/config/set/sonarr/sonarr_api_key/<key>`. The Python backend logs incoming requests (standard bottle/WSGI access log format), so every call to this helper records the raw API key in the server log file. Even though this is a test helper against a local harness, any log aggregation or CI log retention captures the credential in plaintext.

```
/server/config/set/sonarr/sonarr_api_key/fake-api-key-for-testing
```

The same issue affects `setSonarrUrl` — a URL is less sensitive, but both follow the same pattern. The `/server/config/set` endpoint is inherently GET-based (the backend registers it with `add_handler` which calls `self.get()`), so the credential exposure is a consequence of the API design, not something the test can fully fix. However, the test should not use real or realistic-looking credential strings:

**Fix:** Use an obviously-synthetic test credential that cannot be mistaken for a real key, and add a comment explaining the exposure:

```typescript
// NOTE: value appears in access logs — use synthetic strings only
await settingsPage.setSonarrApiKey('test-FAKE-not-real-0000');
```

For new test helpers in this file, prefer POST-based config endpoints if the backend ever provides them.

---

### WR-03: Unused `getConnectionDot()` Method

**File:** `src/e2e/tests/logs.page.ts:46-48`
**Issue:** `getConnectionDot()` is defined on `LogsPage` but is never called from `logs.page.spec.ts` or any other test file. Dead methods on page objects expand the public surface, mislead readers about what is tested, and can silently go stale as the DOM evolves.

```typescript
getConnectionDot(): Locator {
    return this.page.locator('.status-dot');
}
```

**Fix:** Remove the method, or add a test that exercises it (e.g., assert the status dot is visible in the status bar). The connection dot is a meaningful UI signal worth asserting.

---

### WR-04: Unused `getSaveSettingsButton()` Method

**File:** `src/e2e/tests/settings.page.ts:114-116`
**Issue:** `getSaveSettingsButton()` is defined but never referenced in `settings-fields.spec.ts`, `settings-error.spec.ts`, or `settings.page.spec.ts`. The floating save bar tests in `settings-fields.spec.ts` assert on the floating bar's text but never click the explicit save button. If the button's selector goes stale (e.g., class rename), no test will catch it.

```typescript
getSaveSettingsButton(): Locator {
    return this.page.locator('.btn-save-settings');
}
```

**Fix:** Remove the method if the button is not part of any tested flow (Angular's `OptionComponent` auto-saves via debounce, making an explicit save button click unnecessary). If the button is intentionally in scope for a future test, add a `// TODO` referencing the planned spec.

---

### WR-05: SSE Log Row Test Is Environment-Coupled With No Fallback

**File:** `src/e2e/tests/logs.page.spec.ts:47-53`
**Issue:** "should render at least one log row from SSE" relies on the live Docker compose stack emitting at least one log entry within 15 seconds after page load. There is no seed fixture, no mock, and no synthetic log injection. The test will produce a timeout failure in any environment where the harness is idle (fresh start with no pending scan activity, slow CI runners, or stub environments). The 15-second timeout is generous but still fundamentally couples test reliability to infrastructure behavior.

The companion test at line 55-61 ("should display status bar with log count") duplicates the same dependency — it waits for `getLogRows().first()` again before asserting `logsIndexed`.

**Fix:** For the smoke assertion, consider a hybrid approach: wait up to 15 seconds, but if no rows appear, assert that the log container is at least rendered (empty state), rather than treating zero-rows as a hard failure. Alternatively, document in a `test.skip` condition when the harness is in stub mode:

```typescript
test('should render at least one log row from SSE', async () => {
    // Organic logs from the running harness are acceptable for this assertion.
    // If this times out, verify the Docker compose stack is running with
    // active scan cycles (this test does not run in stub/offline mode).
    await expect(logsPage.getLogRows().first()).toBeVisible({ timeout: 15000 });
});
```

At minimum, the duplicate wait in the "status bar" test (line 59) should be extracted to a shared helper or replaced by waiting for the status text directly, since `getLogRows().first().toBeVisible()` has already been asserted in the prior test (sequential execution) — the second wait just adds latency.

---

## Info

### IN-01: Inconsistent Test Callback Signature — Unused `page` Fixture Parameter

**File:** `src/e2e/tests/logs.page.spec.ts:12`
**Issue:** The test "should have Logs nav link active" declares `async ({ page })` but does not use `page` directly in the test body — it accesses `logsPage` (set in `beforeEach`). All other tests in the same `describe` block correctly use `async ()`. This inconsistency is harmless (the `page` fixture is already active via `beforeEach`) but confuses readers into thinking this test requires special page-fixture behavior.

**Fix:**
```typescript
test('should have Logs nav link active', async () => {
    const activeLink = await logsPage.getActiveNavLink();
    expect(activeLink).toBe('Logs');
});
```

---

### IN-02: Describe-Scope Mutable Page Object Variables Are Parallelization-Unsafe

**File:** `src/e2e/tests/logs.page.spec.ts:5`, `src/e2e/tests/settings-fields.spec.ts:5`
**Issue:** Both spec files declare the page object at `describe` scope as a `let` variable and mutate it in `beforeEach`:

```typescript
let logsPage: LogsPage;
test.beforeEach(async ({ page }) => {
    logsPage = new LogsPage(page);
    ...
});
```

This pattern is safe today (`workers: 1`, `fullyParallel: false`), but becomes a race condition if workers are ever increased. Each test should ideally bind its page object within the test or `beforeEach` scope. This is an established Playwright anti-pattern noted in the official docs ("avoid test fixtures as closures").

**Fix:** For now, no change is required given the locked `workers: 1` config. Add a comment on the `let` declaration to make the constraint explicit:

```typescript
// NOTE: workers: 1 required — this mutable closure is not parallel-safe
let logsPage: LogsPage;
```

---

_Reviewed: 2026-04-28T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
