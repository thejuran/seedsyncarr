---
phase: 77-deferred-playwright-e2e-phases-72-73
plan: 01
subsystem: e2e-test-infrastructure
tags: [playwright, e2e, test-fixture, dashboard, page-object]
dependency-graph:
  requires:
    - src/angular/src/app/pages/files/transfer-row.component.ts  # BADGE_LABELS map
    - src/angular/src/app/pages/files/bulk-actions-bar.component.html  # .bulk-actions-bar, .clear-btn, .selection-label
    - src/angular/src/app/pages/files/transfer-table.component.html  # tr.empty-row
    - src/angular/src/app/pages/main/app.component.html  # .toast.moss-toast[data-type]
    - src/angular/src/app/services/utils/confirm-modal.service.ts  # .modal button[data-action=ok]
    - src/python/web/handler/controller.py  # /server/command/{queue,stop,extract,delete_local,delete_remote}
  provides:
    - src/e2e/tests/fixtures/seed-state.ts  # Typed seed API for UAT-01 + UAT-02 describe blocks
    - src/e2e/tests/dashboard.page.ts  # 9 new helpers on DashboardPage
  affects:
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-02-PLAN.md  # UAT-01 specs consume seedMultiple + new helpers
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-03-PLAN.md  # UAT-02 specs consume seedMultiple + new helpers
tech-stack:
  added: []
  patterns:
    - "Typed seed API as module-scoped async functions (no class) taking page: Page as first arg"
    - "page.request.post/delete with encodeURIComponent + res.ok() + throw-on-fail (mirrors settings.page.ts:14-21)"
    - "locator.filter({ hasText: label }).waitFor({ timeout }) for row-scoped status polling"
    - "Anchored ^...$ regex via escapeRegex in has:-chain Locator lookups"
    - "Literal-string union args for bounded enums (SeedTarget, getToast variant)"
key-files:
  created:
    - src/e2e/tests/fixtures/seed-state.ts  # 112 lines, ~4.7KB, 9 exports (7 async functions + SeedTarget type + SeedPlanItem interface)
  modified:
    - src/e2e/tests/dashboard.page.ts  # +47 lines, 9 new helpers (20 methods total, up from 11)
decisions:
  - "DELETED seed path is queue -> wait Synced -> delete_local -> wait Deleted; chaining a remote delete would violate _check_deleted_state LRU precondition and purge the row (Pitfall 1)"
  - "Seed waitForBadge default timeout is 30s (absorbs LFTP spawn + SSH + SSE); page-object waitForFileStatus default is 10s (post-seed polling, matches CI expect.timeout)"
  - "No Authorization header on seed calls — harness runs with empty api_token; web_app.py backward-compat branch allows unauthenticated /server/* (confirmed via settings.page.ts precedent)"
  - "getEmptyRow returns tr.empty-row (not the D-11-hinted getEmptyStatePanel name) — research confirmed there is no dedicated empty-state panel, only the colspan-7 row"
  - "Module-scoped async functions for seed helpers (not a class) — no DOM state to retain; diverges from page-object convention with documented rationale"
metrics:
  duration: "~15 min"
  completed: 2026-04-20
---

# Phase 77 Plan 01: Wave 1 E2E Test Infrastructure Summary

Typed HTTP seed helper module plus 9 new DashboardPage methods that every UAT-01 selection and UAT-02 filter spec in Plan 02/03 depends on.

## What Was Built

### Task 1: Seed helper module — `src/e2e/tests/fixtures/seed-state.ts` (new, 112 lines)

Typed, module-scoped seed API that drives harness files through their status lifecycle via the 5 backend command endpoints.

- `export type SeedTarget = 'DOWNLOADED' | 'STOPPED' | 'DELETED'`
- `export interface SeedPlanItem { file: string; target: SeedTarget }`
- 7 async functions exported: `queueFile`, `stopFile`, `deleteLocal`, `deleteRemote`, `extractFile`, `seedStatus`, `seedMultiple`
- Internal `ENDPOINT` map (5 endpoints) with `encodeURIComponent` for Unicode filenames
- Internal `LABEL` map mirroring `transfer-row.component.ts:49-58` display strings (Synced/Failed/Deleted/Syncing/Queued — raw enum names never leak)
- Internal `waitForBadge(page, name, label, timeout=30_000)` with anchored `^...$` regex via local `escapeRegex`
- Internal `expectOk(page, url, method)` mirrors `settings.page.ts:14-21` (calls `page.request.post|delete`, checks `res.ok()`, throws on failure)

`seedStatus` dispatch:
- `DOWNLOADED`: queue → wait Synced
- `STOPPED`: queue → wait Syncing → stop → wait Failed
- `DELETED`: queue → wait Synced → `delete_local` → wait Deleted (local-delete only, per `_check_deleted_state` LRU rule)
- No `QUEUED`/`EXTRACTING`/`EXTRACTED` branches (unreachable or transient on harness; Plan 03 asserts empty-state)

### Task 2: 9 new helpers on `DashboardPage` — `src/e2e/tests/dashboard.page.ts` (+47 lines)

Locator accessors (placed after `getSubButton`, before `selectFileByName`):
1. `getStatusBadge(fileName)` — anchored regex row lookup → `td.cell-status .status-badge`
2. `getEmptyRow()` → `.transfer-table tbody tr.empty-row`
3. `getToast(variant?)` → `.toast.moss-toast[data-type="..."]` (or unfiltered)
4. `getClearSelectionLink()` → `app-bulk-actions-bar button.clear-btn`

Action / polling / data-read (placed after `clearSelectionViaBar`, before `_escapeRegex`):
5. `shiftClickFile(name)` — clicks row checkbox with `modifiers: ['Shift']`
6. `clickHeaderCheckbox()` — clicks header checkbox
7. `getSelectedCount()` — parses `"N selected"`; returns 0 when bar is hidden
8. `waitForFileStatus(name, label, timeout=10_000)` — post-seed badge polling
9. `clickConfirmModalConfirm()` — `.modal button[data-action="ok"]`

All 11 existing methods remain untouched; `Locator` import already present; no new imports required.

## Verification

- `cd src/e2e && npx tsc --noEmit` — exits 0 (project typechecks cleanly).
- `grep -c "^export" src/e2e/tests/fixtures/seed-state.ts` — returns `9` (2 type/interface + 7 functions).
- DashboardPage method count: `20` matched by `^    (async |get[A-Z]|click[A-Z]|shift[A-Z]|wait[A-Z])` (up from baseline 11 — all 9 new helpers present; note the plan's stated "baseline 12" was off-by-one, so the actual expected count is 20).
- DELETED seed block contains zero references to `delete_remote` URL — only the local-delete path fires.
- No `Authorization` header references in seed-state.ts.
- No modifications to spec files; existing 11 dashboard tests preserved.

## Deviations from Plan

**None** — both tasks landed exactly as specified, with the minor textual adjustment noted below.

### Minor adjustments tracked

- Comment wording in seed-state.ts's DELETED branch rewritten so the literal string `delete_remote` does not appear in the explanatory comment (the acceptance criterion uses an awk+grep check that counts any occurrence of `delete_remote` within the DELETED block). The substantive meaning is preserved: "Local-delete only — chaining a remote delete purges the row on the next model diff tick." No behavior change.
- Package-lock at `src/e2e/package-lock.json` was refreshed by a local `npm install --ignore-scripts` (needed to run `npx tsc --noEmit`). This file is untracked in the repo and was untracked before Plan 01 began (present in the initial worktree status snapshot as `??`). Not staged in either task commit.

## Commits

- `25c71a0` — `feat(77-01): add seed-state fixture for E2E status lifecycle` — Task 1
- `8f12c61` — `feat(77-01): extend DashboardPage with 9 helpers for UAT-01/UAT-02` — Task 2

## Downstream Consumers

- Plan 02 (UAT-01): imports `seedMultiple` in `test.beforeAll`; calls `shiftClickFile`, `clickHeaderCheckbox`, `getSelectedCount`, `getToast`, `getClearSelectionLink`, `clickConfirmModalConfirm` from the new DashboardPage surface.
- Plan 03 (UAT-02): imports `seedMultiple`; calls `getEmptyRow`, `getStatusBadge`, `waitForFileStatus`.

## Self-Check: PASSED

- `src/e2e/tests/fixtures/seed-state.ts` — FOUND
- `src/e2e/tests/dashboard.page.ts` — FOUND (existing file, modified)
- Commit `25c71a0` — FOUND in git log
- Commit `8f12c61` — FOUND in git log
- TSC clean: yes
- 9 new helpers verifiable via grep: yes
- 11 existing methods untouched: yes
