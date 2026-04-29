---
phase: 95-test-coverage-e2e
fixed_at: 2026-04-28T00:00:00Z
review_path: .planning/phases/95-test-coverage-e2e/95-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 95: Code Review Fix Report

**Fixed at:** 2026-04-28T00:00:00Z
**Source review:** .planning/phases/95-test-coverage-e2e/95-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (WR-01 through WR-05; CR-* none; IN-* excluded per fix_scope)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### WR-01: `afterEach` Silently Swallows All Restoration Errors

**Files modified:** `src/e2e/tests/settings-fields.spec.ts`
**Commit:** 52dff57
**Applied fix:** Replaced the three independent `.catch(() => {})` calls with a shared `restore()` helper that wraps each call in `try/catch`, logs the failure label and error via `console.error`, then re-throws so Playwright marks the `afterEach` hook as failed rather than the subsequent test.

---

### WR-02: API Key Passed as URL Path Segment — Appears in Server Access Logs

**Files modified:** `src/e2e/tests/settings.page.ts`, `src/e2e/tests/settings-error.spec.ts`
**Commit:** 89717a4
**Applied fix:** Added a three-line warning comment above `setSonarrApiKey()` in `settings.page.ts` documenting that the value appears in access logs as a plain path segment (GET-only API constraint) and instructing callers to use obviously-synthetic strings. Updated the one call site in `settings-error.spec.ts` from `'fake-api-key-for-testing'` to `'test-FAKE-not-real-0000'` with an inline `// NOTE` comment.

---

### WR-03: Unused `getConnectionDot()` Method

**Files modified:** `src/e2e/tests/logs.page.ts`
**Commit:** 628e55b
**Applied fix:** Removed the `getConnectionDot()` method (3 lines) from `LogsPage`. The method was not referenced in any spec file. The trailing blank line inside the class was also cleaned up.

---

### WR-04: Unused `getSaveSettingsButton()` Method

**Files modified:** `src/e2e/tests/settings.page.ts`
**Commit:** 1014add
**Applied fix:** Removed the `getSaveSettingsButton()` method (4 lines including trailing blank line) from `SettingsPage`. No spec file references this method, and Angular's `OptionComponent` auto-saves via debounce, making an explicit save-button click unnecessary in current tests.

---

### WR-05: SSE Log Row Test Is Environment-Coupled With No Fallback

**Files modified:** `src/e2e/tests/logs.page.spec.ts`
**Commit:** 3a507d7
**Applied fix:** Added a `NOTE` comment to the "should render at least one log row from SSE" test explaining it requires a running Docker compose stack and does not work in stub/offline mode. Removed the duplicate `getLogRows().first().toBeVisible({ timeout: 15000 })` call from the "should display status bar with log count" test, replacing it with a direct `toContainText('logs indexed', { timeout: 15000 })` wait on the status bar right element — eliminating latency from the redundant row wait.

---

_Fixed: 2026-04-28T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
