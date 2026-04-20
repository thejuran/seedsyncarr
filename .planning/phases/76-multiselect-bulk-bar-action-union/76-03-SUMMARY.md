---
phase: 76-multiselect-bulk-bar-action-union
plan: 03
subsystem: angular-bulk-actions-bar-spec
tags: [coverage, fix-01, d-09, wave-3, unit-tests]
status: Complete
requirements: [FIX-01]
dependency_graph:
  requires:
    - "76-02 GREEN fix (view-file.service.ts DELETED-bypass predicate edit)"
    - "76-01 Wave 1 characterization (view-file.service.spec.ts FIX-01 describe block)"
  provides:
    - "Three D-09 mixed-selection coverage tests exercising BulkActionsBarComponent's actionCounts + per-handler emit filtering"
    - "Permanent regression guard layer above Wave 1's createViewFile characterization — covers the bar's consumption of eligibility flags, which Wave 1's service-spec tests do not exercise"
  affects:
    - src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts
tech_stack:
  added: []
  patterns:
    - "Jasmine `jasmine.arrayContaining` + `.calls.mostRecent().args[0].length` count-assert idiom"
    - "Direct ViewFile construction with explicit eligibility flags (pure consumer test per 76-PATTERNS.md §'Test fixture — direct ViewFile construction')"
key_files:
  created:
    - .planning/phases/76-multiselect-bulk-bar-action-union/76-03-SUMMARY.md
  modified:
    - src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts
decisions:
  - "Describe-block label diverges from plan: 'FIX-01 DELETED union regression (D-09 coverage)' vs plan's 'FIX-01 DELETED union regression' — added '(D-09 coverage)' suffix to distinguish the bar-spec coverage layer from the view-file.service.spec.ts characterization layer (Wave 1 Option A relocation)"
  - "Tasks 1 and 2 merged into a single atomic commit — both edit the same file and the plan's acceptance criteria ties them to a single 'test(76): add D-09 mixed-selection coverage' commit message"
  - "Placement: after describe('Edge cases') and before describe('Variant B DOM contract') per 76-PATTERNS.md §'Describe-block organization precedent' lines 399-403"
metrics:
  duration: "~6 minutes (insert + verify 3 suites + commit)"
  completed_date: "2026-04-20"
  tasks_completed: 1
  files_modified: 1
  tests_added: 3
---

# Phase 76 Plan 03: Wave 3 D-09 Mixed-Selection Coverage Summary

Added three `it(...)` mixed-selection cases covering D-09's required union
scenarios to `bulk-actions-bar.component.spec.ts`. Each case verifies
both action counts AND per-handler emit filtering, closing Requirement #4
from the phase success criteria ("Unit tests cover the union logic for at
least three representative mixed selections").

## New Tests (all PASS)

| # | Test Name | Status |
|---|-----------|--------|
| 1 | `All-DELETED union: Queue + Delete Remote enabled; Stop/Extract/DeleteLocal disabled (FIX-01 D-09 case 1)` | PASS |
| 2 | `DELETED + DOWNLOADING union: Queue (1) + Stop (1) + DeleteRemote (2); Extract/DeleteLocal disabled (FIX-01 D-09 case 2)` | PASS |
| 3 | `DELETED + DOWNLOADED + STOPPED union: Queue (2), Extract (1), DeleteLocal (2), DeleteRemote (3); Stop disabled (FIX-01 D-09 case 3)` | PASS |

All three tests assert:

1. Every `actionCounts.X` field is correct.
2. Each click handler (`onQueueClick`, `onStopClick`, `onExtractClick`,
   `onDeleteLocalClick`, `onDeleteRemoteClick`) emits only the eligible
   filenames (per-row dispatch filtering per D-04 + D-08).
3. Handlers with zero eligible rows do NOT emit (guard `if (files.length > 0)`).

## FIX-01 Describe Block Inventory

| File | Describe Block | Count | Provenance |
|------|----------------|-------|------------|
| `bulk-actions-bar.component.spec.ts` | `FIX-01 DELETED union regression (D-09 coverage)` | 3 | Wave 3 (this plan) |
| `view-file.service.spec.ts` | `FIX-01 DELETED isQueueable regression` | 2 | Wave 1 (Option A relocation) |

Total FIX-01-tagged coverage: **5 tests across 2 specs**, covering both the
eligibility-flag layer (service spec) and the bar-consumer aggregation layer
(bar spec).

## Test Count Delta

| Scope | Before Wave 3 | After Wave 3 | Delta |
|-------|---------------|--------------|-------|
| `bulk-actions-bar.component.spec.ts` | 33 passing | 36 passing | +3 |
| `view-file.service.spec.ts` (Wave 1 — still green) | 23 passing | 23 passing | 0 |
| Full Angular suite | 596 passing, 0 failing | **599 passing, 0 failing** | **+3** |

## Commit

- `68990d8` — `test(76-03): add D-09 mixed-selection coverage (all-DELETED, DELETED+DOWNLOADING, DELETED+DOWNLOADED+STOPPED)` — 207 insertions, 0 deletions, single file

## Verification Commands & Output

### Bar spec (target — all 36 green)

```
$ cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless \
    --include='**/bulk-actions-bar.component.spec.ts'
...
  FIX-01 DELETED union regression (D-09 coverage)
    [+] All-DELETED union: Queue + Delete Remote enabled; Stop/Extract/DeleteLocal disabled (FIX-01 D-09 case 1)
    [+] DELETED + DOWNLOADING union: Queue (1) + Stop (1) + DeleteRemote (2); Extract/DeleteLocal disabled (FIX-01 D-09 case 2)
    [+] DELETED + DOWNLOADED + STOPPED union: Queue (2), Extract (1), DeleteLocal (2), DeleteRemote (3); Stop disabled (FIX-01 D-09 case 3)
  Variant B DOM contract
    ...
TOTAL: 36 SUCCESS
```

### Service spec (Wave 1 — still green)

```
$ cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless \
    --include='**/view-file.service.spec.ts'
...
  FIX-01 DELETED isQueueable regression
    [+] DELETED + remote_size=null must be queueable (RED target)
    [+] DELETED + remote_size>0 is queueable (GREEN control)
TOTAL: 23 SUCCESS
```

### Full suite (no regressions)

```
$ cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless
...
Chrome Headless 147.0.0.0 (Mac OS 10.15.7): Executed 599 of 599 SUCCESS
TOTAL: 599 SUCCESS
```

### Grep-verifiable acceptance

```
$ grep -c 'FIX-01 D-09 case' src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts
3
$ grep -n 'FIX-01 DELETED union regression' src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts
371:    describe("FIX-01 DELETED union regression (D-09 coverage)", () => {
$ git diff --name-only HEAD~1 HEAD
src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts
```

## Deviations from Plan

### Deviation 1 — Wave 1 Relocation Cascade (prompt context, not a Wave 3 decision)

**Found during:** Plan context-load (prompt included `wave1_relocation_context`)
**Issue:** The plan assumes Wave 1 added a `describe("FIX-01 DELETED union regression", ...)` block to `bulk-actions-bar.component.spec.ts`. Per the Wave 1 Option A relocation (documented in `76-01-SUMMARY.md` and `76-02-SUMMARY.md`), that Wave 1 describe block lives in `view-file.service.spec.ts`, not the bar spec. The bar spec had no FIX-01 describe block to append to.
**Fix:** Created the describe block fresh in the bar spec instead of appending. Its contents are the three D-09 cases alone (no Wave 1 characterization tests). This matches the intent of plan Task 1's action paragraph ("Locate the existing describe... block") gracefully — the bar spec now has its own FIX-01 block, parallel to the service spec's FIX-01 block.
**Files modified:** `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts`
**Commit:** `68990d8`

### Deviation 2 — Describe Label Suffix

**Found during:** Wave 3 execution (when creating the fresh describe block per Deviation 1)
**Issue:** Two FIX-01 describe blocks now exist (one per spec file) — same regression, different concerns. A bare `describe("FIX-01 DELETED union regression", ...)` label in the bar spec is indistinguishable from the service spec's label in karma output.
**Fix:** Labeled the bar-spec block `FIX-01 DELETED union regression (D-09 coverage)` and the service-spec block retains its Wave 1 label `FIX-01 DELETED isQueueable regression`. Karma output now clearly distinguishes the two layers.
**Files modified:** Same (one file, one line).
**Commit:** Same (`68990d8`).

### Deviation 3 — Plan Acceptance Criterion Restated

**Plan's Task 2 acceptance criterion:** `All 5 tests inside FIX-01 describe block pass (2 Wave 1 + 1 Task 1 + 2 Task 2)`.
**Revised for Wave 3 reality:** `All 3 tests inside FIX-01 describe block in bar spec pass (0 Wave 1 + 3 Wave 3). Wave 1's 2 characterization tests live in view-file.service.spec.ts per Option A relocation, still green (23/23).`
**Net assertion:** 3 new tests + 2 Wave 1 tests = 5 FIX-01-tagged tests across 2 spec files — the plan's intent (5 total FIX-01 coverage tests) is honored.

### Deviation 4 — Tasks Merged into One Commit

**Plan structure:** Tasks 1 and 2 separately (Task 1 = All-DELETED case; Task 2 = cases 2 + 3).
**Execution:** One atomic commit with all three cases. Both tasks edit the same file and plan Task 2's action paragraph specifies the final commit message covering all three cases: `test(76): add D-09 mixed-selection coverage (all-DELETED, DELETED+DOWNLOADING, DELETED+DOWNLOADED+STOPPED)`. Splitting them would have required an interim commit message the plan never specifies.
**Impact:** None — coverage content, test count, and commit message all match the plan's specified single-message outcome.

No Rule 1 (bug), Rule 2 (missing critical functionality), Rule 3 (blocking issue), or Rule 4 (architectural) deviations applied — the only deviations above are from the Wave 1 relocation cascade and a minor label disambiguation, both of which match the prompt's `wave1_relocation_context` guidance.

## Authentication Gates

None. Unit-test addition only; no network, no secrets, no auth surface.

## Deferred Issues

None. All acceptance criteria met on first pass.

## Threat Flags

None. This plan adds only unit-test code — no new network paths, user inputs,
persisted data, or auth changes. Matches the plan's `<threat_model>` disposition
(T-76-03-01 = accept, N/A).

## Self-Check: PASSED

- Created file exists: `.planning/phases/76-multiselect-bulk-bar-action-union/76-03-SUMMARY.md` (this file)
- Modified file exists: `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts`
- Commit exists: `68990d8` (verified via `git log --oneline`)
- All 3 new tests PASS in isolation (bar spec 36/36)
- All 2 Wave 1 tests still PASS (service spec 23/23)
- Full Angular suite 599/599 SUCCESS (delta +3 vs Wave 2 close at 596/596)
- `git diff --name-only HEAD~1 HEAD` returns exactly one file
- No untracked files created by this plan's execution
