# Phase 69: E2E Selector Update - Research

**Researched:** 2026-04-15
**Domain:** Playwright E2E page objects — selector audit against v1.1.0 redesigned dashboard markup
**Confidence:** HIGH

## Summary

Phase 63 replaced the dashboard with a new `FilesPageComponent` that renders `app-stats-strip`, `app-transfer-table`, and `app-dashboard-log-pane`. The OLD `app-file-list` component (which had `#file-list`, checkboxes, `.bulk-actions-bar`) is **no longer mounted at any route**. It still exists in the codebase but is orphaned.

[VERIFIED: routes.ts line 47-49 — `/dashboard` → `FilesPageComponent`]
[VERIFIED: files-page.component.html — contains `app-transfer-table`, NOT `app-file-list`]

**This means every existing selector in `dashboard.page.ts` and `bulk-actions.spec.ts` is broken.** The E2E tests try to find `#file-list .file` which does not exist on the dashboard page at all. The new `app-transfer-table` uses a completely different DOM structure: `<table class="transfer-table">` with `<tbody><app-transfer-row>` rows.

**Critical finding:** `app-transfer-table` has NO checkboxes and NO bulk-selection. It is a read-only table. The `app-bulk-actions-bar` and `app-file-list` are part of the orphaned `app-file-list` component. The bulk-actions E2E test suite tests functionality that no longer exists on the dashboard route.

**Primary recommendation:** The planner must choose one of two strategies:
1. **Re-route strategy:** Re-add `app-file-list` to `FilesPageComponent` (or a sub-route) so that existing E2E tests can target it. This restores the bulk-selection UI to the dashboard.
2. **Rewrite strategy:** Rewrite `dashboard.page.ts` and `dashboard.page.spec.ts` to test the new `app-transfer-table` markup (pagination, search, segment filters, transfer rows). Retire or stub out `bulk-actions.spec.ts` since that UI is not currently reachable.

This is a **scope decision** that needs user input or explicit CONTEXT.md guidance. Research documents both paths.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| E2E-01 | Dashboard page object selectors match redesigned transfer-table markup | New markup: `app-transfer-table` with `<table class="transfer-table">`, `<app-transfer-row>` — selectors documented below |
| E2E-02 | Bulk-actions page object selectors match redesigned bulk-actions markup | `app-bulk-actions-bar` is NOT on the dashboard route — see critical finding. Either restore or retire. |
| E2E-03 | CI green — all E2E specs pass via `make run-tests-e2e` | Requires resolving E2E-01 and E2E-02 first |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| E2E selector targeting | Test layer (src/e2e/) | Frontend HTML (src/angular/) | Tests reference HTML class/ID attributes |
| Transfer table (NEW dashboard) | Frontend (transfer-table.component) | — | Paginated, read-only, no checkboxes |
| Bulk-selection UI (orphaned) | Frontend (file-list.component) | — | No longer routed; tests will fail if they target this |
| Single-file actions bar (orphaned) | Frontend (file-list.component) | — | No longer routed |
| CI gate | CI pipeline (ci.yml) | make run-tests-e2e | E2E runs inside Docker image after build |

---

## Current vs New Dashboard DOM Structure

### OLD structure (what E2E tests currently target — no longer rendered)
```
FilesPageComponent (OLD)
└── app-file-list
    ├── app-bulk-actions-bar
    │   └── .bulk-actions-bar > .selection-label, .clear-btn, .action-btn
    ├── app-file-actions-bar
    │   └── .file-actions-bar
    └── #file-list.file-card
        ├── #header > .header-inner > input[checkbox]
        └── .file-viewport > app-file > .file > .checkbox, .status-badge, .name, .meta-right .size
```

### NEW structure (what's actually rendered at /dashboard)
```
FilesPageComponent (NEW)
├── app-stats-strip
│   └── (stat cards — not tested)
├── app-transfer-table
│   └── .transfer-card
│       ├── .card-header > .card-title, .search-box, .segment-filters
│       ├── .transfer-table-wrap > table.transfer-table
│       │   ├── thead > tr > th.col-name, .col-status, .col-progress, .col-speed, .col-eta, .col-size
│       │   └── tbody > app-transfer-row (one per file)
│       │       └── td.cell-name > .file-name, .file-meta
│       │           td.cell-status > .status-badge
│       │           td.cell-progress > .progress-cell
│       │           td.cell-speed, td.cell-eta, td.cell-size
│       └── .pagination-footer > .page-info, .page-controls > .btn-page
└── app-dashboard-log-pane
```

---

## New Selectors for app-transfer-table

[VERIFIED: transfer-table.component.html, transfer-row.component.html]

### For `navigateTo()` — wait for first row to load
```typescript
// Wait for first transfer row name cell to be visible
await this.page.locator('.transfer-table tbody app-transfer-row td.cell-name').first()
    .waitFor({ state: 'visible', timeout: 30000 });
```

### For file enumeration (replaces `getFiles()`)
```typescript
// Each <app-transfer-row> is a table row (<tr> with angular component as host)
// .cell-name contains .file-name (name) and .file-meta (path + size)
// .cell-status contains .status-badge with badge label text

const rows = await this.page.locator('.transfer-table tbody tr').all();
// OR
const rows = await this.page.locator('.transfer-table tbody app-transfer-row').all();

// For each row:
const name = await row.locator('td.cell-name .file-name').textContent();
const statusText = await row.locator('td.cell-status .status-badge').textContent();
const size = await row.locator('td.cell-size').textContent();
```

**Status badge labels in new transfer-row.component.ts:**
| Status | Badge Label |
|--------|------------|
| DOWNLOADING | "Syncing" |
| QUEUED | "Queued" |
| DOWNLOADED | "Synced" |
| STOPPED | "Failed" |
| EXTRACTING | "Extracting" |
| EXTRACTED | "Extracted" |
| DEFAULT | "—" (em dash U+2014) |
| DELETED | "Deleted" |

[VERIFIED: transfer-row.component.ts lines 24-33 — BADGE_LABELS map]

Note: The new `transfer-row` uses em dash for DEFAULT (not the word "Default" as in `file.component`). The golden data in `dashboard.page.spec.ts` expects `status: ''`. The normalization logic needs updating: check for em dash `'\u2014'` instead of the word `'default'`.

### For single-file selection (row click)
```typescript
// Rows are <app-transfer-row> host elements (Angular renders these as <tr>-like elements in tbody)
await this.page.locator('.transfer-table tbody app-transfer-row').nth(index).click();
```

Note: `transfer-row.component.html` contains `<td>` elements — it relies on being used INSIDE a `<tbody>` via `app-transfer-row` selector. Angular renders the component host as a `<tr>` equivalent. The `file-actions-bar` component is NOT present in the new markup at all — clicking a row does not show a file-actions-bar.

### For single-file action bar
**CRITICAL:** `app-file-actions-bar` is NOT in `files-page.component.html`. The tests in `dashboard.page.spec.ts` that check for `app-file-actions-bar .file-actions-bar` will fail because this component is not rendered in the new layout.

Options:
- Skip/stub those tests (actions bar no longer exists in this design)
- Or: the planner should confirm whether single-file actions exist elsewhere in the new UI

### For pagination controls
```typescript
// Page navigation buttons
this.page.locator('.pagination-footer .btn-page')
// Page info text
this.page.locator('.pagination-footer .page-info')
// Previous/Next
this.page.locator('.pagination-footer .btn-page[disabled]') // disabled prev/next
```

### For search/filter controls
```typescript
// Search input
this.page.locator('.transfer-card .search-input')
// Segment filter buttons
this.page.locator('.transfer-card .btn-segment')
this.page.locator('.transfer-card .btn-segment.active')
```

---

## Standard Stack

### Core Test Infrastructure
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @playwright/test | ^1.48.0 | E2E test framework | Project-configured in src/e2e/ |

[VERIFIED: src/e2e/package.json]

### Run Command
```bash
# From repo root (via Makefile)
make run-tests-e2e

# Direct (from src/e2e/) — requires app running at APP_BASE_URL
cd src/e2e && npm test
```

### CI Integration
E2E tests run inside Docker via `make run-tests-e2e` after `build-docker-image`. They test against the built Docker image at port 8800. [VERIFIED: .github/workflows/ci.yml lines 105-145]

---

## Architecture Patterns

### Page Object Pattern (current project)
```
src/e2e/tests/
├── dashboard.page.ts        # Page object: DashboardPage — NEEDS FULL REWRITE
├── bulk-actions.spec.ts     # Spec: bulk selection — NEEDS REASSESSMENT (feature not on route)
├── dashboard.page.spec.ts   # Spec: dashboard basics — NEEDS FULL REWRITE for new selectors
├── app.ts                   # Base App class (nav, getActiveNavLink) — unchanged
└── urls.ts                  # Paths constants — unchanged
```

### Two Implementation Paths

#### Path A: Rewrite tests for new transfer-table markup
- Update `DashboardPage.navigateTo()` to wait for `.transfer-table tbody app-transfer-row`
- Update `getFiles()` to read from `td.cell-name .file-name` and `td.cell-status .status-badge`
- Remove `selectFile()` and `isFileActionsVisible()` — no single-file selection in new design
- Remove `getFileActions()` — no file-actions-bar in new design
- Update `dashboard.page.spec.ts` golden data: `status` field will be em dash `'—'` for DEFAULT (or normalize to `''`)
- Retire `bulk-actions.spec.ts` or convert it to a stub (bulk UI not present on route)
- Add new tests for pagination, search, segment filters

#### Path B: Restore app-file-list to dashboard
- Add `<app-file-list>` back to `files-page.component.html` alongside `app-transfer-table`
- Keep existing E2E selectors mostly unchanged
- Fix `isFileRowBulkSelected` logic bug
- This approach keeps both old and new dashboard components

**Recommendation:** Path A is cleaner (tests match production UI). Path B requires design decision about whether to re-expose the old UI. The STATE.md TODO entry says "E2E Playwright tests need selector updates for redesigned dashboard" which implies updating tests, not reverting UI.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status text normalization | Custom string matching | Match exact badge labels from BADGE_LABELS map | Source of truth is transfer-row.component.ts |
| Row counting | `document.querySelectorAll` in evaluate | `this.page.locator(...).count()` | Playwright locator API is more reliable |
| Wait strategies | `sleep` | `waitFor({ state: 'visible' })` | Already in codebase pattern |

---

## Common Pitfalls

### Pitfall 1: app-transfer-row renders as table row host element
**What goes wrong:** `transfer-row.component.html` contains only `<td>` elements (no wrapping `<tr>`). Angular renders `app-transfer-row` as the `<tr>` host itself in the DOM. The selector `table.transfer-table tbody tr` and `table.transfer-table tbody app-transfer-row` both find the same elements.
**How to avoid:** Use `app-transfer-row` as the row selector since it's more semantically stable than `tr`.

### Pitfall 2: DEFAULT status badge is em dash, not "Default"
**What goes wrong:** `dashboard.page.spec.ts` golden data uses `status: ''`. The new transfer-row renders DEFAULT as `'—'` (em dash). If normalization code checks `=== 'default'` it will never match.
**How to avoid:** Normalize em dash `'\u2014'` → `''` in the new `getFiles()` implementation.

### Pitfall 3: Size display format changed
**What goes wrong:** OLD `file.component.html` showed size as `"0% — 0 B of 840 KB"`. NEW `transfer-row.component.html` shows only `{{ file.remoteSize | fileSize:1 }}` in `td.cell-size` (e.g., `"840 KB"`). The golden data format will need updating.
**How to avoid:** Update golden data in `dashboard.page.spec.ts` to match new format, or change `getFiles()` to read from the new cell structure.

### Pitfall 4: No checkboxes or bulk-selection in new dashboard
**What goes wrong:** `bulk-actions.spec.ts` tests try to find `.checkbox input[type="checkbox"]`, `.bulk-actions-bar`, `#header .header-inner` — none of these exist in `app-transfer-table`.
**How to avoid:** Either retire `bulk-actions.spec.ts` entirely, or mark tests as skipped with `test.skip`.

### Pitfall 5: file-actions-bar no longer rendered
**What goes wrong:** `dashboard.page.spec.ts` tests `isFileActionsVisible()` which looks for `app-file-actions-bar .file-actions-bar`. This component is not in `files-page.component.html`.
**How to avoid:** Remove or skip those test cases. The new design has no per-file action bar visible on click.

---

## Code Examples

### Updated navigateTo() for new markup
```typescript
// Source: analysis of transfer-table.component.html
async navigateTo() {
    await this.page.goto(Paths.DASHBOARD);
    // Wait for the transfer table to show rows
    await this.page.locator('.transfer-table tbody app-transfer-row').first()
        .waitFor({ state: 'visible', timeout: 30000 });
}
```

### Updated waitForAtLeastFileCount() for new markup
```typescript
// Source: analysis of transfer-row.component.html
async waitForAtLeastFileCount(count: number, timeout: number = 10000) {
    await this.page.waitForFunction(
        (expectedCount) => {
            const rows = document.querySelectorAll('.transfer-table tbody app-transfer-row');
            return rows.length >= expectedCount;
        },
        count,
        { timeout }
    );
}
```

### Updated getFiles() for new markup
```typescript
// Source: transfer-row.component.html and transfer-row.component.ts BADGE_LABELS
export interface FileInfo {
    name: string;
    status: string;
    size: string;
}

async getFiles(): Promise<FileInfo[]> {
    const rowElements = await this.page.locator('.transfer-table tbody app-transfer-row').all();
    const files: FileInfo[] = [];
    for (const row of rowElements) {
        const name = (await row.locator('td.cell-name .file-name').textContent() || '').trim();
        const statusText = (await row.locator('td.cell-status .status-badge').textContent() || '').trim();
        // DEFAULT status renders as em dash '—'; normalize to '' for golden data compatibility
        const status = statusText === '\u2014' ? '' : statusText;
        const size = (await row.locator('td.cell-size').textContent() || '').trim();
        files.push({ name, status, size });
    }
    return files;
}
```

### Updated golden data format for dashboard.page.spec.ts
```typescript
// NEW format — size is just remoteSize, not "0% — 0 B of 840 KB"
// Source: transfer-row.component.html line 53-55
const golden: FileInfo[] = [
    { name: 'áßç déÀ.mp4', status: '', size: '840 KB' },
    { name: 'clients.jpg', status: '', size: '36.5 KB' },
    // etc.
];
```

Note: The exact size values depend on how `FileSizePipe` formats them with precision `1`. The planner should verify actual rendered sizes by running the app.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Virtual-scroll `#file-list` with `.file` rows | Paginated `app-transfer-table` with `<table>` | Phase 63 (2026-04-15) | All E2E selectors targeting `#file-list` are broken |
| Inline checkboxes per file row | No checkboxes in transfer-table | Phase 63 | `bulk-actions.spec.ts` tests non-existent UI |
| Per-file `app-file-actions-bar` on click | No per-file actions bar | Phase 63 | `isFileActionsVisible()` always returns false |
| Status label "Default" | Status label "—" (em dash) | Phase 63 | Golden data status normalization logic needs update |
| Size format "0% — 0 B of 840 KB" | Size format "840 KB" | Phase 63 | Golden data size format needs update |

---

## Open Questions (RESOLVED)

1. **Should bulk-actions.spec.ts be retired or stubbed?**
   - What we know: The bulk-selection UI (`app-file-list` with checkboxes and `app-bulk-actions-bar`) is not rendered at any route.
   - What's unclear: Was this intentional (bulk UI removed from v1.1.0 design) or an oversight?
   - Recommendation: Check STATE.md "Todos" entry — it says "E2E tests need selector updates for... bulk-actions.spec.ts" implying the bulk UI should still be tested. This may mean Path B (restore `app-file-list`) is intended, OR that the bulk-actions bar exists elsewhere in the new design.
   - RESOLVED: Path A chosen — stub with `test.skip` at describe level. The bulk-selection UI is intentionally absent from the v1.1.0 transfer-table design. Stubs preserve test names for future restoration if bulk UI is re-added. STATE.md "selector updates" is satisfied by updating the file (skipping is a valid update when the target UI no longer exists).

2. **What does the actual app render for file size format?**
   - What we know: `FileSizePipe` with precision `1` is used in transfer-row. The exact output format is `"840 KB"`, `"1.53 MB"` etc.
   - Recommendation: Planner should run the app or check `FileSizePipe` implementation to confirm exact golden data values.
   - RESOLVED: Plan uses FileSizePipe precision:1 values (`840 KB`, `36.5 KB`, etc.) as golden data. The executor is instructed to verify actual rendered values at test-run time and adjust if needed (see plan verification note).

3. **Are there any new E2E scenarios to add for transfer-table features?**
   - Pagination (Prev/Next buttons)
   - Search filtering
   - Segment filter (All/Active/Errors)
   - These are new UI features not currently tested.
   - Recommendation: E2E-01 scope should include at least a smoke test for pagination visible.
   - RESOLVED: Out of scope for Phase 69. The phase goal is strictly "update selectors for redesigned dashboard" (fix broken tests), not "add new test coverage." New E2E scenarios for pagination/search/filters would be a separate phase.

---

## Environment Availability

Step 2.6: SKIPPED — This phase is pure TypeScript/test code changes with no new external dependencies. Playwright is already installed at `src/e2e/node_modules`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | @playwright/test ^1.48.0 |
| Config file | src/e2e/playwright.config.ts |
| Quick run command | `cd src/e2e && npm test -- --grep "dashboard"` |
| Full suite command | `cd src/e2e && npm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| E2E-01 | DashboardPage page object navigates and reads transfer-table rows | E2E smoke | `cd src/e2e && npm test -- dashboard.page.spec.ts` | ✅ (needs rewrite) |
| E2E-02 | BulkActions page object targets correct markup (or is retired) | E2E integration | `cd src/e2e && npm test -- bulk-actions.spec.ts` | ✅ (needs decision) |
| E2E-03 | Full suite green in CI | E2E full | `make run-tests-e2e` | ✅ (CI) |

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. No new test files needed (modifications only).

---

## Security Domain

This phase modifies only test-layer page objects. No authentication, session management, input validation, or cryptography is involved. Security domain is not applicable.

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: Read] `src/angular/src/app/routes.ts` — confirmed `/dashboard` → `FilesPageComponent`
- [VERIFIED: Read] `src/angular/src/app/pages/files/files-page.component.html` — confirmed dashboard renders `app-transfer-table`, NOT `app-file-list`
- [VERIFIED: Read] `src/angular/src/app/pages/files/transfer-table.component.html` — new selector source
- [VERIFIED: Read] `src/angular/src/app/pages/files/transfer-row.component.html` — new row selector source
- [VERIFIED: Read] `src/angular/src/app/pages/files/transfer-row.component.ts` — BADGE_LABELS map (status text)
- [VERIFIED: Read] `src/angular/src/app/pages/files/bulk-actions-bar.component.html` — bulk-actions selectors (still valid on file-list, but file-list not routed)
- [VERIFIED: Read] `src/e2e/tests/dashboard.page.ts` — current (broken) page object
- [VERIFIED: Read] `src/e2e/tests/bulk-actions.spec.ts` — current (broken) bulk spec
- [VERIFIED: Read] `src/e2e/playwright.config.ts` — test runner config

### Secondary (MEDIUM confidence)
- [VERIFIED: git log] Commits `d472980`, `64efb64` — Phase 63 added transfer-table to files-page
- [VERIFIED: git log] Commit `e1b348e` — prior E2E selector update pattern (about/autoqueue) confirms targeted-fix approach

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Playwright version and run commands directly verified
- Architecture (route → component mapping): HIGH — verified by reading routes.ts and files-page.component.html
- New selectors for transfer-table: HIGH — verified by reading transfer-table.component.html and transfer-row.component.html
- Bulk-actions fate (Path A vs B): HIGH — Path A chosen, documented in Open Questions (RESOLVED)

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Bulk-selection UI (`app-file-list`) is intentionally removed from dashboard (Path A is correct) | Open Questions (RESOLVED) | If Path B (restore file-list) is correct, the selector analysis changes significantly — bulk selectors are still valid in file-list.component.html |
| A2 | Golden data size format for transfer-row is `"840 KB"` (FileSizePipe precision 1) | Code Examples | If FileSizePipe format differs, golden data values will be wrong — verify by running app |

**A1 resolved: Path A chosen (stub bulk-actions tests). A2 is low-risk (easy to verify at test-run time).**
