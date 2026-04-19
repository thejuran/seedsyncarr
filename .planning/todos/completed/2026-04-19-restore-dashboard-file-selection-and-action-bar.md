---
created: 2026-04-19T15:43:29.931Z
title: Restore dashboard file selection and action bar
area: ui
files:
  - src/angular/src/app/pages/files/files-page.component.html
  - src/angular/src/app/pages/files/transfer-row.component.ts
  - src/angular/src/app/pages/files/transfer-table.component.ts
  - src/angular/src/app/pages/files/file-actions-bar.component.ts
  - src/e2e/tests/dashboard.page.spec.ts
---

## Problem

The v1.1.0 Triggarr-style UI redesign (shipped 2026-04-15, phases 62–71) dropped the file selection + per-file action flow from the dashboard. Selecting a row in the new transfer table does nothing.

**What was lost:** 5 actions that used to live on row selection — Queue, Stop, Extract, Delete Local, Delete Remote (see `file-actions-bar.component.ts:20-24`).

**Current state:**
- `files-page.component.html` renders only `<app-stats-strip>`, `<app-transfer-table>`, `<app-dashboard-log-pane>`.
- `TransferRowComponent` has `@Input file` only — no click handler, no selection state, no event outputs.
- `TransferTableComponent` has no selection model — just search/filter/pagination.
- Orphaned components still in tree but not rendered: `file-list.component.*`, `file.component.*`, `file-actions-bar.component.*`, `file-options.component.*`.
- `src/e2e/tests/dashboard.page.spec.ts:34-53` deliberately `.skip()`s 5 tests with comment: "v1.1.0: app-file-actions-bar removed from dashboard — transfer-table is read-only".

**Why it happened:** AIDesigner Triggarr mockup was ported visually; functional parity with the old selection+action flow wasn't preserved.

## Solution

Decision confirmed: **Option 1 — Restore**.

Likely approaches:

- Add selection state to `TransferTableComponent` (single-select model — most users operate on one file at a time).
- Wire click handler on `TransferRowComponent`, emit selected ViewFile.
- Reintroduce an action bar: either adapt the orphaned `FileActionsBarComponent` (already has proper `isQueueable`/`isStoppable`/etc. guards and event emitters) or design inline per-row action buttons that match Triggarr visual language.
- Re-enable the 5 skipped E2E tests in `dashboard.page.spec.ts` and update selectors to the new DOM.
- Once restored, delete the truly obsolete orphans (`file-list`, `file.component`, `file-options`) to avoid confusion.

**Scoping note:** Could slot into v1.2.0 alongside the 2026-04-17 "filter for every torrent status" todo — both are dashboard UX with overlapping code paths (TransferTableComponent + TransferRowComponent).
