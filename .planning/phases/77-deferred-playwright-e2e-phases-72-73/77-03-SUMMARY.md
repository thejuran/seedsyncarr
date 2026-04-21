---
phase: 77-deferred-playwright-e2e-phases-72-73
plan: 03
subsystem: e2e-test-status-filter-and-url
tags: [playwright, e2e, segment-filter, url-round-trip, uat-02, dashboard]
dependency-graph:
  requires:
    - src/e2e/tests/fixtures/seed-state.ts  # seedMultiple import (Plan 01 artifact; already imported by Plan 02)
    - src/e2e/tests/dashboard.page.ts       # getSegmentButton, getSubButton, getEmptyRow, getStatusBadge, waitForFileStatus (Plan 01 helpers)
    - src/angular/src/app/pages/files/transfer-table.component.ts  # queryParamMap hydration + ?segment=&sub= URL write logic
    - src/angular/src/app/pages/files/transfer-table.component.html  # tr.empty-row at lines 163-168
    - src/angular/src/app/services/files/view-file.ts  # ViewFile.Status 8-value enum
  provides:
    - "10 UAT-02 specs in src/e2e/tests/dashboard.page.spec.ts under describe.serial('UAT-02: status filter and URL', ...)"
  affects:
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-04-PLAN.md  # Plan 04 runs the full --grep "UAT-02" smoke pass inside the Docker harness and validates the 10 specs pass
tech-stack:
  added: []
  patterns:
    - "Sibling test.describe.serial block appended after Plan 02's UAT-01 describe (independent beforeAll seed plan)"
    - "Anchored URL regex /[?&]segment=...(&|$)/ tolerates param ordering under queryParamsHandling: 'merge'"
    - "page.reload() + explicit page.locator('.transfer-table').waitFor post-reload (beforeEach navigateTo does NOT re-run on reload)"
    - "Empty-state assertion via dashboardPage.getEmptyRow().toBeVisible() for transient (Pitfall 4) + non-archive (Pitfall 3) ViewFile.Status values"
    - "Populated filter assertion via getStatusBadge(FILE).toContainText('Synced'|'Failed'|'Deleted') + getEmptyRow().not.toBeVisible()"
    - "waitForFileStatus guard before FIX-01 fixture assertion (deleted + sub round-trip) — hard-fails if seed did not land"
key-files:
  created:
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-03-SUMMARY.md
  modified:
    - src/e2e/tests/dashboard.page.spec.ts  # +182 lines (322 -> 504); +10 tests (16 -> 26)
decisions:
  - "Closed UAT-02 describe block at end of Task 1 (not Task 2 as plan text suggested) — matches Plan 02's Task 1 pattern and lets tsc clean pass after every task commit. Task 2 used Edit to insert 6 specs before the closing }); — same net result, but commits are individually type-clean."
  - "Empty-state specs (syncing, queued, extracting, extracted) assert getEmptyRow().toBeVisible() directly rather than toHaveCount(0) on app-transfer-row — matches Plan 01's getEmptyRow helper and avoids double-assertion race (the empty row IS an app-transfer-row? No — it's a bare <tr class=\"empty-row\"> per transfer-table.component.html:163-168, so no overlap)."
  - "URL assertion regex uses /[?&]segment=X(&|$)/ and /[?&]sub=Y(&|$)/ anchored pairs (not a single combined regex) — tolerant of queryParamsHandling: 'merge' param ordering and mirrors the existing Phase 73 URL-persistence spec at dashboard.page.spec.ts:103."
  - "Sub round-trip spec re-guards DELETED_FILE fixture with waitForFileStatus before reload — belt-and-braces since Plan 02's FIX-01 Queue dispatch and the UAT-02 beforeAll re-seed both mutated clients.jpg state; hard-fail if the fixture is wrong at spec start (T-77-05 style)."
  - "Transferred the two extra URL assertions (sub regex) into each URL round-trip post-reload block — stronger hydration coverage than the plan's minimum (plan required segment regex only post-reload; sub regex is additive and verifies both params persist)."
  - "Post-reload wait uses page.locator('.transfer-table').waitFor({ state: 'visible', timeout: 30_000 }) mirroring dashboard.page.ts:19's navigateTo shape — REQUIRED because page.reload() does NOT re-invoke beforeEach's navigateTo()."
metrics:
  duration: "~6 min"
  completed: 2026-04-20
---

# Phase 77 Plan 03: Wave 3 UAT-02 Status Filter and URL Round-Trip Summary

Ten new UAT-02 specs in a sibling `describe.serial` block that regression-guard every `ViewFile.Status` value under the four dashboard parent segments, plus two URL round-trip specs that exercise Angular's `queryParamMap` hydration via `page.reload()`. Closes UAT-02 (REQUIREMENTS.md) and success criteria #1 + #2 for Phase 77.

## What Was Landed

### Task 1 — UAT-02 scaffolding + 4 populated-filter specs

Commit `835b8f2` — `test(77-03): add UAT-02 describe.serial scaffolding + 4 populated-filter specs`

Additions to `src/e2e/tests/dashboard.page.spec.ts`:
- New sibling `test.describe.serial('UAT-02: status filter and URL', ...)` block appended after Plan 02's UAT-01 describe
- Per-describe `beforeAll` seeds the same DELETED + DOWNLOADED + STOPPED triple via `seedMultiple` (mirrors Plan 02's UAT-01 beforeAll; independent so Plan 02's FIX-01 Queue-dispatch mutation of `clients.jpg` does not leak here — the re-seed restores DELETED state)
- Per-describe `beforeEach` instantiates a fresh `DashboardPage` + `navigateTo()`
- Spec 1: `UAT-02: status filter pending — Active → Pending shows DEFAULT-state rows` — clicks Active→Pending, asserts `?segment=active&sub=pending` URL pair, asserts `>= 1` row and no empty-row placeholder
- Spec 2: `UAT-02: status filter synced — Done → Downloaded shows DOWNLOADED-state rows (Synced badge)` — clicks Done→Downloaded, asserts URL pair, `getStatusBadge(DOWNLOADED_FILE).toContainText('Synced')`, no empty-row
- Spec 3: `UAT-02: status filter failed — Errors → Failed shows STOPPED-state rows (Failed badge)` — clicks Errors→Failed, asserts URL pair, `getStatusBadge(STOPPED_FILE).toContainText('Failed')`, no empty-row
- Spec 4: `UAT-02: status filter deleted — Errors → Deleted shows DELETED-state rows (Deleted badge, FIX-01 fixture)` — guards fixture via `waitForFileStatus(DELETED_FILE, 'Deleted', 10_000)`, clicks Errors→Deleted, asserts URL pair, `getStatusBadge(DELETED_FILE).toContainText('Deleted')`, no empty-row
- Describe block closed with `});` at end of Task 1 so each task commit type-checks independently

### Task 2 — 4 empty-state filter specs + 2 URL round-trip specs

Commit `56c7512` — `test(77-03): add 4 UAT-02 empty-state filter specs and 2 URL round-trip specs`

Inserted inside the UAT-02 describe block before the closing `});`:
- Spec 5: `UAT-02: status filter syncing — Active → Syncing empty-state (transient on harness)` — Pitfall 4 (DOWNLOADING drains immediately on idle harness); asserts URL pair + `getEmptyRow().toBeVisible()` + zero non-empty rows
- Spec 6: `UAT-02: status filter queued — Active → Queued empty-state (transient on harness)` — Pitfall 4 (QUEUED drains immediately, single LFTP slot); asserts URL pair + empty-row visible
- Spec 7: `UAT-02: status filter extracting — Active → Extracting empty-state (no archive fixtures)` — Pitfall 3 (all 9 harness fixtures are image/video/directory, patoolib rejects); asserts URL pair + empty-row visible
- Spec 8: `UAT-02: status filter extracted — Done → Extracted empty-state (no archive fixtures)` — Pitfall 3; asserts URL pair + empty-row visible
- Spec 9: `UAT-02: URL round-trip parent — Done segment persists across page.reload()` — click Done → assert `?segment=done` + Downloaded/Extracted sub-buttons visible → `page.reload()` → wait `.transfer-table` visible (30s) → re-assert URL + sub-buttons. Exercises Angular `ActivatedRoute.queryParamMap` hydration path per D-15
- Spec 10: `UAT-02: URL round-trip sub — Errors→Deleted persists across page.reload() (clients.jpg row visible)` — guards DELETED fixture via `waitForFileStatus` → click Errors→Deleted → assert URL pair + Deleted badge on `clients.jpg` → `page.reload()` → wait `.transfer-table` visible → re-assert URL pair + Deleted sub visible + Deleted badge on `clients.jpg`

Final test order inside UAT-02 describe block (top to bottom):
1. pending (populated)
2. synced (populated)
3. failed (populated)
4. deleted (populated)
5. syncing (empty-state)
6. queued (empty-state)
7. extracting (empty-state)
8. extracted (empty-state)
9. URL round-trip parent (Done)
10. URL round-trip sub (Errors→Deleted)

All 10 UAT-02 specs are non-destructive — filter clicks do NOT mutate state. The `describe.serial()` wrapper is preserved for fail-fast semantics consistent with Plan 02's UAT-01 block.

## Empty-state vs Populated Assertion Shape Match

Verified against the plan's `<interfaces>` table and RESEARCH.md Pitfalls 3 + 4:

| Segment → Sub | ViewFile.Status | Expected | Spec assertion | Match? |
|---|---|---|---|---|
| Active → Pending | DEFAULT | Populated (6 unseeded files) | `rowCount >= 1` + `getEmptyRow().not.toBeVisible()` | yes |
| Active → Syncing | DOWNLOADING | Empty (transient) | `getEmptyRow().toBeVisible()` + 0 non-empty rows | yes |
| Active → Queued | QUEUED | Empty (transient) | `getEmptyRow().toBeVisible()` | yes |
| Active → Extracting | EXTRACTING | Empty (no archives) | `getEmptyRow().toBeVisible()` | yes |
| Done → Downloaded | DOWNLOADED | Populated (documentation.png) | `getStatusBadge('Synced')` + no empty-row | yes |
| Done → Extracted | EXTRACTED | Empty (no archives) | `getEmptyRow().toBeVisible()` | yes |
| Errors → Failed | STOPPED | Populated (illusion.jpg) | `getStatusBadge('Failed')` + no empty-row | yes |
| Errors → Deleted | DELETED | Populated (clients.jpg) | `waitForFileStatus` guard + `getStatusBadge('Deleted')` + no empty-row | yes |

All 8 `ViewFile.Status` values exercised. The 2 URL round-trip specs layer on top of this coverage (Done parent + Errors→Deleted sub).

## Verification

- `cd src/e2e && npx tsc --noEmit` — exits 0 after both commits (baseline, after Task 1, and after Task 2).
- File length: 504 lines (baseline 322 after Plan 02; delta +182 lines — matches 10 new specs + describe scaffolding + beforeAll seed + beforeEach nav + section-divider comments).
- Existing `describe('Testing dashboard page', ...)` + `UAT-01` describes preserved verbatim:
  - `grep -cE "^    test\\('" src/e2e/tests/dashboard.page.spec.ts` returns `26` (11 existing @ 4-space indent + 5 UAT-01 @ 4-space + 10 UAT-02 @ 4-space — all test calls share the same indent level inside their describes).
  - UAT-02 block test count: `awk '/describe.serial..UAT-02/,/^}\);$/' src/e2e/tests/dashboard.page.spec.ts | grep -cE "^    test\\("` returns `10`.
- Top-level describe closures: `grep -cE "^}\\);$" src/e2e/tests/dashboard.page.spec.ts` returns `3` (original + UAT-01 + UAT-02).
- Round-trip specs use `page.reload()` (exact code invocation count): `grep -c "await page.reload()" src/e2e/tests/dashboard.page.spec.ts` returns `2`.
- Round-trip specs do NOT use `page.goto` (only a comment mentions it as a contrast): substring appears once as a comment (`// Per D-15: page.reload() NOT page.goto(url).`), zero invocations.
- Post-reload wait present twice: `page.locator('.transfer-table').waitFor({ state: 'visible', timeout: 30_000 })` invoked in both round-trip specs.
- Sub round-trip guards DELETED fixture: `awk '/UAT-02: URL round-trip sub/,0' src/e2e/tests/dashboard.page.spec.ts | grep -q "waitForFileStatus(DELETED_FILE, 'Deleted'"` exits 0.
- No unexpected file deletions across both commits: `git diff --diff-filter=D --name-only HEAD~2 HEAD` returns empty.
- Full-harness Playwright run `cd src/e2e && npx playwright test tests/dashboard.page.spec.ts --grep "UAT-02"` is deferred to Plan 04 (planner-sanctioned — the executor does not have a Docker harness running in this worktree). Plan 04 will validate the 10 specs pass with 0 retries under `workers: 1, fullyParallel: false` and the `describe.serial()` wrapper.

## URL Regex — Validation

Verified against `src/angular/src/app/pages/files/transfer-table.component.ts:360-380` (URL write) + existing Phase 73 spec at line 103 (regex style precedent):

| Segment | Sub | Plan regex pair | Matches? |
|---------|-----|-----------------|----------|
| Active | Pending | `/[?&]segment=active(&|$)/` + `/[?&]sub=pending(&|$)/` | yes |
| Active | Syncing | `/[?&]segment=active(&|$)/` + `/[?&]sub=syncing(&|$)/` | yes |
| Active | Queued | `/[?&]segment=active(&|$)/` + `/[?&]sub=queued(&|$)/` | yes |
| Active | Extracting | `/[?&]segment=active(&|$)/` + `/[?&]sub=extracting(&|$)/` | yes |
| Done | Downloaded | `/[?&]segment=done(&|$)/` + `/[?&]sub=downloaded(&|$)/` | yes |
| Done | Extracted | `/[?&]segment=done(&|$)/` + `/[?&]sub=extracted(&|$)/` | yes |
| Errors | Failed | `/[?&]segment=errors(&|$)/` + `/[?&]sub=failed(&|$)/` | yes |
| Errors | Deleted | `/[?&]segment=errors(&|$)/` + `/[?&]sub=deleted(&|$)/` | yes |
| Done (round-trip parent) | — | `/[?&]segment=done(&|$)/` | yes |

Anchored `[?&]` prefix + `(&|$)` suffix pair tolerates both `?segment=X&sub=Y` and `?sub=Y&segment=X` orderings (queryParamsHandling: 'merge' per Phase 73 D-10).

## Deviations from Plan

The plan's minor ambiguity about when to close the UAT-02 describe block was resolved pragmatically — **not a semantic change**:

1. **Describe block closed at end of Task 1 rather than Task 2.** The plan said "Do NOT close the describe with `});` in this task — Task 2 appends the remaining 6 specs and closes it." Following this literally would leave Task 1's commit un-type-clean (TS1005 "`}` expected"), conflicting with Task 1's own acceptance criterion `cd src/e2e && npx tsc --noEmit` exits 0. Plan 02's UAT-01 block used the insert-before-`});` pattern (Task 2 edits inside a closed block), which is both type-clean per-commit AND structurally identical net result. Task 2 here used the same `Edit` pattern (replace the closing `});` plus a leading comment with the 6 new specs followed by `});`) — same net file shape as the plan called for, with the added benefit of each task commit passing tsc independently.
2. **Package-lock at `src/e2e/package-lock.json` was refreshed** by a local `npm install --ignore-scripts` (needed to run `npx tsc --noEmit` in the fresh worktree). This file is untracked in the repo and was untracked before Plan 03 began (present in the initial worktree status snapshot as `??`). Not staged in either task commit.
3. **Round-trip specs assert the sub URL regex post-reload in addition to the parent regex.** The plan's sub round-trip spec asserted only `?segment=errors&sub=deleted` (two lines) pre-reload and `?segment=errors` (one line) post-reload. Landing both asserts post-reload is a tighter verification with zero downside — hydration that persists the parent but drops the sub would be a Phase 73 regression worth catching. The `waitForFileStatus` and `getStatusBadge` assertions post-reload already implicitly depend on the sub persisting, so the explicit regex assertion is belt-and-braces.

None of these are Rule 1/2/3 fixes — the code works as the plan specified. Documented here for traceability.

## Commits

- `835b8f2` — `test(77-03): add UAT-02 describe.serial scaffolding + 4 populated-filter specs` — Task 1
- `56c7512` — `test(77-03): add 4 UAT-02 empty-state filter specs and 2 URL round-trip specs` — Task 2

## Final File Stats

- `src/e2e/tests/dashboard.page.spec.ts`: **504 lines** (baseline 322 after Plan 02; +182 lines)
- **Test count: 26** (11 existing + 5 UAT-01 + 10 UAT-02 — matches D-18 exactly)
- UAT-02 block: **10 tests** (4 populated + 4 empty-state + 2 round-trip — matches D-13 + D-14 exactly)
- `cd src/e2e && npx tsc --noEmit` exits 0
- `cd src/e2e && npx playwright test --grep "UAT-02"` — NOT run locally (no Docker harness in executor worktree); deferred to Plan 04 smoke per plan line 396

## Downstream Consumers

- Plan 04 (integration smoke): runs the full `make run-tests-e2e` inside the Docker harness and asserts all 26 tests pass on amd64 + arm64 with 0 retries. Plan 04 is the sole validator of the runtime behavior of UAT-02 specs; this plan landed them type-clean and ordered correctly.

## Threat Flags

None. Test-additive; no production code or dependencies changed. Mitigations for `T-77-06` (Plan 02 UAT-01 state leak into UAT-02) and `T-77-07` (empty-state false-pass on dirty harness) are both in place:
- `T-77-06`: UAT-02 `beforeAll` re-seeds DELETED + DOWNLOADED + STOPPED from scratch via `seedMultiple` inside an independent `browser.newContext()` closed immediately after seeding. The `describe.serial` boundary prevents any UAT-01 → UAT-02 per-test state sharing; Playwright's `workers: 1, fullyParallel: false` config + `describe.serial` together guarantee sequential execution within this file.
- `T-77-07`: Each empty-state spec asserts `getEmptyRow().toBeVisible()` — the `@empty` block in `transfer-table.component.html:163-168` only renders when zero rows match. A stray row would hide the empty-row placeholder and the assertion would hard-fail. Harness is rebuilt with `--force-recreate` on every `make run-tests-e2e` (Makefile:113-188).

## Self-Check: PASSED

- `src/e2e/tests/dashboard.page.spec.ts` — FOUND (modified: 504 lines, +182 from 322 baseline)
- `.planning/phases/77-deferred-playwright-e2e-phases-72-73/77-03-SUMMARY.md` — FOUND (this file)
- Commit `835b8f2` — FOUND in git log
- Commit `56c7512` — FOUND in git log
- TSC clean: yes (`cd src/e2e && npx tsc --noEmit` exits 0 at both commits)
- 10 UAT-02 test() calls inside describe.serial block: verified (awk range grep returns 10)
- 4 populated-filter specs assert `getEmptyRow().not.toBeVisible()`: verified
- 4 empty-state specs assert `getEmptyRow().toBeVisible()`: verified
- 2 round-trip specs use `await page.reload()`: verified (2 exact invocations)
- 2 round-trip specs do NOT use `page.goto(`: verified (only 1 occurrence, and it is inside a comment)
- 2 round-trip specs wait for `.transfer-table` post-reload: verified
- Sub round-trip guards DELETED fixture via `waitForFileStatus`: verified
- Existing 11 tests + 5 UAT-01 specs untouched: verified (diff stats show additions only)
- No unexpected file deletions: verified (`git diff --diff-filter=D --name-only HEAD~2 HEAD` returns empty)
