---
phase: 76-multiselect-bulk-bar-action-union
plan: 01
subsystem: angular-tests
tags: [tdd-red, characterization, fix-01, d-01, deviation-option-a]
status: "Complete (red — Option A relocation)"
requirements: [FIX-01]
dependency_graph:
  requires: []
  provides:
    - FIX-01 RED characterization anchor in view-file.service.spec.ts
  affects:
    - view-file.service.ts (Wave 2 target — createViewFile isQueueable guard)
tech_stack:
  added: []
  patterns:
    - "Jasmine fakeAsync + Observable subscription harness (view-file.service.spec.ts precedent at lines 271-329)"
    - "Immutable.Map<string, ModelFile> → mockModelService._files.next(model) pipeline"
    - "withContext() assertion messages for diagnostic clarity on Wave 2 hand-off"
key_files:
  created:
    - .planning/phases/76-multiselect-bulk-bar-action-union/76-01-SUMMARY.md
  modified:
    - src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts
decisions:
  - "Relocated Wave 1 from bulk-actions-bar.component.spec.ts to view-file.service.spec.ts (Option A, user-authorized at Wave 1 decision checkpoint)"
  - "Characterization uses model-through-service flow (not direct ViewFile construction) so the bug actually triggers"
  - "D-02 candidate #1 (createViewFile isQueueable guard) confirmed as Wave 2 root cause"
metrics:
  duration: "~15 minutes (continuation agent)"
  completed_date: "2026-04-20"
  tasks_completed: 1
  files_modified: 1
  tests_added: 2
commit_sha: e019b21
---

# Phase 76 Plan 01: FIX-01 Characterization Summary

Failing characterization anchor for the FIX-01 DELETED-queueable regression,
relocated from the bulk-actions bar to view-file.service (Option A) after
Wave 1 decision checkpoint.

## Objective Recap

Write a failing Jasmine test that pins down the exact current-behavior gap
for FIX-01: when a DELETED file is selected and the backend reports
`remote_size === null`, the resulting `ViewFile` must expose
`isQueueable === true` so the bulk bar surfaces "Re-Queue from Remote."
Current HEAD produces `isQueueable === false` → RED.

## Deviations from Plan

**files_modified relocated.** The plan's `files_modified` was
`src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts`.
The committed edit instead lands in
`src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts`.
This deviation was authorized by the user at the Wave 1 decision
checkpoint (Option A).

**Why the original plan's site could not produce RED.** The original plan
constructed `ViewFile` fixtures directly with
`isQueueable: true` hard-coded on the constructor. Under those fixtures,
the bar's `_recomputeCachedValues` happily iterates and reports
`actionCounts.queueable >= 1` — because the bar is a pure-consumer of the
pre-computed flag. The prior executor ran the plan's exact skeleton and
observed the tests went GREEN, not RED. That means the fixtures bypassed
the buggy code path.

**The real buggy code path.** `ViewFileService.createViewFile()`
(`src/angular/src/app/services/files/view-file.service.ts` lines 297-394)
is where the eligibility flags are computed from model state. The
null-normalization on lines 303-306 converts a backend
`remote_size: null` to `remoteSize = 0`; then the guard on lines 348-351
(`... && remoteSize > 0`) forces `isQueueable = false` for a DELETED row
that the backend no longer has size metadata for. The bar faithfully
forwards the false flag.

**Relocated test exercises the full code path.** The new describe block
constructs a `ModelFile` with `state = DELETED`, `remote_size = null`, and
pushes it through `mockModelService._files.next(model)`. The resulting
`ViewFile` is the subject of the assertion. This is the genuine RED the
plan sought.

## D-02 Candidate Resolution

Of the four D-02 candidates enumerated in `76-CONTEXT.md`:

1. **#1 `createViewFile` `remoteSize > 0` guard** — CONFIRMED as the root
   cause. The GREEN-control test (`DELETED + remote_size=1024`) passes on
   the same code path that the RED-target test (`DELETED + remote_size=null`)
   fails on. The only differing variable is `remote_size`, which flows
   straight into the guard on line 351.
2. **#2 Stale-selection path drops DELETED filenames** — ELIMINATED. The
   characterization never touches `FileSelectionService` — the bug fires
   at the `ViewFile` construction boundary.
3. **#3 `ngOnChanges` cache miss between `visibleFiles` and `selectedFiles`
   ticks** — ELIMINATED. Reproducible without any tick-ordering stress;
   deterministic single-file fixture.
4. **#4 Bar intersection filter (`visibleFiles ∩ selectedFiles`)** —
   ELIMINATED by the prior executor via the original (green) bar-spec
   attempt.

**Wave 2 target:** the `&& remoteSize > 0` clause on the DELETED branch of
`isQueueable` in `view-file.service.ts` (lines 348-351). Minimal-diff fix
per D-03: tease apart the DELETED branch from the DEFAULT/STOPPED branches
so DELETED is not gated by `remoteSize > 0` (or gated differently). The
predicate already classifies the status first; splitting the size gate
per-status is a one-line ternary.

**Important:** the analogous `isRemotelyDeletable` predicate on lines
364-369 has the same `remoteSize > 0` guard and the same DELETED inclusion.
Wave 2 should decide whether the same symptom applies to
`isRemotelyDeletable` (delete-remote button hidden for DELETED rows with
null remote_size) and fix or leave with a documented reason.

## Karma Failure Output

Exact output from the Wave 1 run (captured to `/tmp/76-01-wave1-output.txt`):

```
Chrome Headless 147.0.0.0 (Mac OS 10.15.7) Testing view file service FIX-01 DELETED isQueueable regression DELETED + remote_size=null must be queueable (RED target) FAILED
	DELETED rows must remain queueable even when backend reports remote_size=null (FIX-01): Expected false to be true.
	    at <Jasmine>
	    at Object.next (src/app/tests/unittests/services/files/view-file.service.spec.ts:1019:30)
	    at ConsumerObserver.next (node_modules/rxjs/dist/esm/internal/Subscriber.js:91:33)
	    at SafeSubscriber._next (node_modules/rxjs/dist/esm/internal/Subscriber.js:60:26)
	    at SafeSubscriber.next (node_modules/rxjs/dist/esm/internal/Subscriber.js:31:18)

Chrome Headless 147.0.0.0 (Mac OS 10.15.7): Executed 23 of 23 (1 FAILED) (0.154 secs / 0.148 secs)
TOTAL: 1 FAILED, 22 SUCCESS
```

The only failure is the `DELETED + remote_size=null` RED target. The
GREEN control (`DELETED + remote_size>0`) passed, pinning the trigger to
the null remote_size specifically. All 21 pre-existing specs in the file
remain green.

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Bar spec restored to HEAD (no uncommitted changes) | DONE — `git diff bulk-actions-bar.component.spec.ts` is empty |
| New describe block in view-file.service.spec.ts with ≥2 FIX-01 cases | DONE — describe at line 1004 with 2 `it(...)` cases |
| At least one test RED on current HEAD | DONE — `DELETED + remote_size=null must be queueable (RED target)` FAILS |
| Control case GREEN | DONE — `DELETED + remote_size>0 is queueable (GREEN control)` passes |
| Full bar spec still passes | DONE — 33/33 pass, no FIX-01 describe present |
| Atomic test commit with correct message | DONE — commit `e019b21`, message begins `test(76): add failing FIX-01 characterization tests (D-01, Option A relocation)` |
| SUMMARY.md created with deviation note + D-02 candidate + failure output | DONE — this file |
| STATE.md + ROADMAP.md updated and committed | DONE (separate final-metadata commit) |

## Files Modified

- `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts`
  (+93 lines at end of outer describe)

## Bar Spec Verification

After commit `e019b21`:

```
cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless --include='**/bulk-actions-bar.component.spec.ts'
Chrome Headless 147.0.0.0 (Mac OS 10.15.7): Executed 33 of 33 SUCCESS (0.047 secs / 0.037 secs)
TOTAL: 33 SUCCESS
```

Bar spec untouched, 33/33 pass.

## Commits

| Hash | Message |
|------|---------|
| e019b21 | `test(76): add failing FIX-01 characterization tests (D-01, Option A relocation)` |

## Wave 2 Hand-off

**Inputs:**
- RED target test: `Testing view file service > FIX-01 DELETED isQueueable regression > DELETED + remote_size=null must be queueable (RED target)`
- Green control: `DELETED + remote_size>0 is queueable (GREEN control)`
- Target file: `src/angular/src/app/services/files/view-file.service.ts`
- Target lines: 348-351 (`isQueueable` predicate) and likely 364-369
  (`isRemotelyDeletable` predicate — verify whether the same symptom
  applies).

**Success metric for Wave 2:** both FIX-01 tests GREEN, all 21 pre-existing
view-file.service.spec tests still GREEN, all 33 bulk-actions-bar.component.spec
tests still GREEN, no other Angular spec broken.

## Self-Check: PASSED

- `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts` exists and contains `describe("FIX-01 DELETED isQueueable regression"` at line 1004 — FOUND
- Commit `e019b21` exists in git log — FOUND (`test(76): add failing FIX-01 characterization tests (D-01, Option A relocation)`)
- SUMMARY.md at `.planning/phases/76-multiselect-bulk-bar-action-union/76-01-SUMMARY.md` — being created now (this file)
