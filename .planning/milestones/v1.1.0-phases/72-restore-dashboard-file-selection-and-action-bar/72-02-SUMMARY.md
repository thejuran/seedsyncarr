---
phase: 72-restore-dashboard-file-selection-and-action-bar
plan: "02"
subsystem: angular/pages/files
tags: [angular, cleanup, deletion, dead-code]
dependency_graph:
  requires: []
  provides: [clean-pages-files-directory]
  affects: [72-01-bulk-actions-bar-adaptation]
tech_stack:
  added: []
  patterns: [git-rm, pre-flight-grep, ng-build-verification]
key_files:
  created: []
  modified: []
  deleted:
    - src/angular/src/app/pages/files/file-actions-bar.component.ts
    - src/angular/src/app/pages/files/file-actions-bar.component.html
    - src/angular/src/app/pages/files/file-actions-bar.component.scss
    - src/angular/src/app/pages/files/file-list.component.ts
    - src/angular/src/app/pages/files/file-list.component.html
    - src/angular/src/app/pages/files/file-list.component.scss
    - src/angular/src/app/pages/files/file.component.ts
    - src/angular/src/app/pages/files/file.component.html
    - src/angular/src/app/pages/files/file.component.scss
    - src/angular/src/app/pages/files/file-options.component.ts
    - src/angular/src/app/pages/files/file-options.component.html
    - src/angular/src/app/pages/files/file-options.component.scss
    - src/angular/src/app/tests/unittests/pages/files/file-list.component.spec.ts
    - src/angular/src/app/tests/unittests/pages/files/file.component.spec.ts
decisions:
  - D-18: Delete file-actions-bar, file-list, file, file-options components; keep bulk-actions-bar (adapted in plan 01)
metrics:
  duration: ~6 minutes
  completed: 2026-04-19
  tasks_completed: 1
  tasks_total: 1
  files_changed: 14
---

# Phase 72 Plan 02: Delete obsolete component sets (D-18) Summary

Dead-code removal of the 4 obsolete pre-redesign component sets (file-actions-bar, file-list, file, file-options) and their 2 unit specs — confirmed zero active references, `ng build` exits 0, 489/489 unit specs green.

## Objective

Delete the four obsolete Angular component file-sets and their two specs that became dead code after the v1.1.0 Triggarr-style dashboard redesign (phases 62-71). Running this in wave 1 surfaces any residual imports before the new selection+action wiring lands in waves 2+.

## Task Completed

### Task 1: Pre-flight verification + deletion of 14 obsolete files

**Step 1 — Pre-flight grep result:** Zero matches. The exhaustive grep across `src/angular/src/**/*.{ts,html,scss}` for all reference patterns (FileListComponent, FileActionsBarComponent, FileOptionsComponent, app-file-list, app-file-actions-bar, app-file-options, file-list.component import, file.component import) found no active references outside the deletion set. Confirmed at time of authoring: `files-page.component.ts` only imports `StatsStripComponent`, `TransferTableComponent`, and `DashboardLogPaneComponent`; `app.config.ts` and `app.routes.ts` have zero references.

**Step 2 — Files deleted (14 total):**

| File | Component set |
|------|--------------|
| `src/angular/src/app/pages/files/file-actions-bar.component.ts` | file-actions-bar |
| `src/angular/src/app/pages/files/file-actions-bar.component.html` | file-actions-bar |
| `src/angular/src/app/pages/files/file-actions-bar.component.scss` | file-actions-bar |
| `src/angular/src/app/pages/files/file-list.component.ts` | file-list |
| `src/angular/src/app/pages/files/file-list.component.html` | file-list |
| `src/angular/src/app/pages/files/file-list.component.scss` | file-list |
| `src/angular/src/app/pages/files/file.component.ts` | file |
| `src/angular/src/app/pages/files/file.component.html` | file |
| `src/angular/src/app/pages/files/file.component.scss` | file |
| `src/angular/src/app/pages/files/file-options.component.ts` | file-options |
| `src/angular/src/app/pages/files/file-options.component.html` | file-options |
| `src/angular/src/app/pages/files/file-options.component.scss` | file-options |
| `src/angular/src/app/tests/unittests/pages/files/file-list.component.spec.ts` | spec |
| `src/angular/src/app/tests/unittests/pages/files/file.component.spec.ts` | spec |

**Step 3 — Preserved files (D-18 explicit keep):**

- `src/angular/src/app/pages/files/bulk-actions-bar.component.{ts,html,scss}` — untouched (plan 01 adapts these)
- `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` — untouched

**Step 4 — `ng build --configuration=development` exit code: 0**

Build emitted only pre-existing SCSS deprecation warnings from bootstrap/font-awesome node_modules — none from the deletion set. No TypeScript errors, no missing import errors.

**Step 5 — `ng test --watch=false --browsers=ChromeHeadless` exit code: 0**

All 489 specs passed. Zero failures, zero errors. The two deleted specs (file-list.component.spec.ts, file.component.spec.ts) tested behaviors that no longer exist and are not missed by any remaining spec.

## Post-deletion Directory State

`src/angular/src/app/pages/files/` now contains:
- bulk-actions-bar.component.{ts,html,scss}
- dashboard-log-pane.component.{ts,html,scss}
- files-page.component.{ts,html,scss}
- stats-strip.component.{ts,html,scss}
- transfer-row.component.{ts,html,scss}
- transfer-table.component.{ts,html,scss}

`src/angular/src/app/tests/unittests/pages/files/` now contains:
- bulk-actions-bar.component.spec.ts
- dashboard-log-pane.component.spec.ts
- stats-strip.component.spec.ts
- transfer-row.component.spec.ts
- transfer-table.component.spec.ts

## Stale E2E Comment (Non-blocking)

`src/e2e/tests/bulk-actions.spec.ts` contains a stale `// v1.1.0:` header comment that still references `app-file-list` and `app-bulk-actions-bar`. This file is permanently guarded by `test.skip(true, '...')` at line 8 — every test inside is an empty stub. The comment is informational text only; no imports, no selectors, no executable code. This was intentionally left as-is per the plan's explicit scope note. Cleanup is deferred to plan 05's E2E pass or a follow-up phase.

## Deviations from Plan

None — plan executed exactly as written. Pre-flight grep returned zero matches, deletion scope honored exactly, build and tests green.

## Self-Check

**Files gone:**
- `test ! -f src/angular/src/app/pages/files/file-actions-bar.component.ts` — PASS
- `test ! -f src/angular/src/app/pages/files/file-list.component.ts` — PASS
- `test ! -f src/angular/src/app/pages/files/file.component.ts` — PASS
- `test ! -f src/angular/src/app/pages/files/file-options.component.ts` — PASS

**Preserved:**
- `test -f src/angular/src/app/pages/files/bulk-actions-bar.component.ts` — PASS
- `test -f src/angular/src/app/pages/files/transfer-row.component.ts` — PASS
- `test -f src/angular/src/app/pages/files/transfer-table.component.ts` — PASS
- `test -f src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` — PASS

**Commits:**
- `103ace3` — `chore(72-02): delete 4 obsolete component sets and 2 specs (D-18)`

## Self-Check: PASSED
