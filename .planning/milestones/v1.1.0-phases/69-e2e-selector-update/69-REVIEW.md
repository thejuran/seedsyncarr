---
phase: 69-e2e-selector-update
reviewed: 2026-04-15T12:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/e2e/tests/dashboard.page.ts
  - src/e2e/tests/dashboard.page.spec.ts
  - src/e2e/tests/bulk-actions.spec.ts
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 69: Code Review Report

**Reviewed:** 2026-04-15
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed three E2E test files: a page object (`dashboard.page.ts`), its spec (`dashboard.page.spec.ts`), and a bulk-actions spec (`bulk-actions.spec.ts`). The page object is clean and well-structured. The bulk-actions spec is entirely skipped with clear rationale for v1.1.0. One warning found in the dashboard spec where `DashboardPage` is redundantly re-instantiated inside individual tests despite `beforeEach` already constructing and navigating it. One info-level observation about CSS-class-based selectors that may be fragile.

## Warnings

### WR-01: Redundant DashboardPage re-instantiation in tests

**File:** `src/e2e/tests/dashboard.page.spec.ts:13,19`
**Issue:** The `beforeEach` hook (line 8-10) creates a `DashboardPage` and calls `navigateTo()`. However, the two active tests on lines 13 and 19 each create a *new* `DashboardPage` instance, discarding the one from `beforeEach`. This is functionally harmless because the underlying Playwright `Page` object is the same (so navigation state persists), but it creates confusion about which instance is authoritative and makes `beforeEach` partially wasted work.
**Fix:** Remove the redundant `new DashboardPage(page)` calls inside individual tests; use the instance from `beforeEach`:
```typescript
test('should have Dashboard nav link active', async () => {
    const activeLink = await dashboardPage.getActiveNavLink();
    expect(activeLink).toBe('Dashboard');
});

test('should have a list of files', async () => {
    const golden: FileInfo[] = [ /* ... */ ];
    await dashboardPage.waitForAtLeastFileCount(golden.length);
    const files = await dashboardPage.getFiles();
    expect(files).toEqual(golden);
});
```
Note: When removing the re-instantiation, also remove the `{ page }` destructuring from the test callback signature since `page` is no longer needed directly in those tests.

## Info

### IN-01: CSS-class-based selectors may be fragile

**File:** `src/e2e/tests/dashboard.page.ts:19,26,35,39-43`
**Issue:** All selectors use CSS classes (`.transfer-table`, `.cell-name`, `.file-name`, `.cell-status`, `.status-badge`, `.cell-size`). These are coupled to styling implementation and can break silently when CSS is refactored. This is a known pattern in the codebase and Phase 69 appears to be addressing selector updates, so this is noted for awareness rather than as an actionable fix.
**Fix:** Consider using `data-testid` attributes for E2E selectors to decouple tests from CSS class names. For example: `[data-testid="transfer-table"]`, `[data-testid="file-name"]`.

---

_Reviewed: 2026-04-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
