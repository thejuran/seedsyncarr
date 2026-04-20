---
phase: 76-multiselect-bulk-bar-action-union
plan: 02
subsystem: angular-view-file-service
tags: [root-cause, fix-01, d-02, d-03, wave-2, fix-applied]
status: "Task 3 complete — fix applied, Wave 1 RED now GREEN, full suite 596/596 passing"
requirements: [FIX-01]
dependency_graph:
  requires:
    - "76-01 RED characterization (view-file.service.spec.ts FIX-01 describe block)"
  provides:
    - "Root-cause note identifying D-02 candidate #1 as the bug site"
    - "Proposed minimal diff for view-file.service.ts (one file, two hunks in same file)"
  affects:
    - src/angular/src/app/services/files/view-file.service.ts (Wave 2 Task 3 target)
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - .planning/phases/76-multiselect-bulk-bar-action-union/76-02-SUMMARY.md
  modified: []
decisions:
  - "Root cause: view-file.service.ts createViewFile() — remoteSize > 0 guard on isQueueable (lines 348-351) silently zeros queueability for DELETED files when backend reports remote_size=null (normalized to 0 on lines 303-306)"
  - "isRemotelyDeletable at lines 364-369 carries the same shape and same bug; proposed fix addresses both predicates in one hunk pair (still a single file, matching D-03 minimal-edit scope)"
  - "Candidate #2 (pruneSelection) disqualified — grep confirms no production callers, only invoked from spec files"
  - "Candidate #3 (ngOnChanges cache-miss) disqualified — Wave 1 RED reproduces in a deterministic single-tick model push through view-file.service, never touches the bar"
  - "Candidate #4 (bar intersection) disqualified by Wave 1 Option A relocation — the bar faithfully forwards whatever eligibility flags the ViewFile carries; bug fires upstream of the bar"
metrics:
  duration: "~12 minutes (Task 1 analysis + Task 3 fix + full suite verification)"
  completed_date: "2026-04-20"
  tasks_completed: 2
  files_modified: 1
  tests_added: 0
---

# Phase 76 Wave 2 Summary

**Status:** Task 1 complete — root cause identified. Awaiting
`checkpoint:human-verify` before Task 3 applies the fix.

## Wave 1 Failure Output (verbatim)

Exact output from the Wave 1 run (reproduced from `76-01-SUMMARY.md` §Karma
Failure Output):

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

The only failure is the RED target `DELETED + remote_size=null`. The GREEN
control `DELETED + remote_size=1024` passes on the same code path,
pinning the trigger variable to `remote_size` being null specifically.

## Root Cause

**Candidate:** #1
**File:** `src/angular/src/app/services/files/view-file.service.ts`
**Region:** lines 297-351 (createViewFile transform; `isQueueable` guard at
348-351; size-normalization at 303-306). Secondary pattern site: lines
364-369 (`isRemotelyDeletable`).

`createViewFile()` transforms `ModelFile` → `ViewFile`. Lines 303-306
normalize a null `modelFile.remote_size` to `remoteSize = 0`, then
lines 348-351 compute `isQueueable` as `status ∈ {DEFAULT, STOPPED,
DELETED} && remoteSize > 0`. The size gate is sensible for
DEFAULT/STOPPED (nothing to queue if remote has no size) but **wrong
for DELETED**: DELETED is precisely the row whose remote metadata the
backend may drop — `remote_size=null` is the backend's "file was
deleted, size no longer cached" representation. Null-normalization
zeros it, the gate fails, every downstream consumer sees
`isQueueable=false`, and the Queue (Re-Queue from Remote) action is
hidden. The three other D-02 candidates are eliminated: #2
(`pruneSelection`) has no production caller — grep shows every hit
inside `file-selection.service.ts` itself or spec files; #3
(`ngOnChanges` cache miss) cannot apply — the RED reproduces in a
single deterministic `tick()` through the service with no bar
involvement; #4 (bar intersection) was disqualified by Wave 1's
Option A relocation — the bar faithfully forwards whatever flag the
ViewFile carries, and the RED fires before the bar is constructed.
**Minimal edit:** split the predicate so DELETED short-circuits past
the size gate while DEFAULT/STOPPED keep it. **Pattern echo:**
`isRemotelyDeletable` (lines 364-369) has the same
`DELETED-in-set && remoteSize > 0` shape and strands the "Delete
Remote" action under the same null-remote-size conditions. Wave 1
asserts only `isQueueable`, so strictly `isRemotelyDeletable` is
deferred (no failing test). The proposed fix addresses both because
the pattern and file are identical — still one-file per D-03 — but
Task 3 can drop the second hunk if the reviewer prefers the narrowest
diff.

## Proposed Fix

BEFORE (`src/angular/src/app/services/files/view-file.service.ts`, lines 348-369):

```typescript
        const isQueueable: boolean = [ViewFile.Status.DEFAULT,
                                    ViewFile.Status.STOPPED,
                                    ViewFile.Status.DELETED].includes(status)
                                    && remoteSize > 0;
        const isStoppable: boolean = [ViewFile.Status.QUEUED,
                                    ViewFile.Status.DOWNLOADING].includes(status);
        const isExtractable: boolean = [ViewFile.Status.DEFAULT,
                                    ViewFile.Status.STOPPED,
                                    ViewFile.Status.DOWNLOADED,
                                    ViewFile.Status.EXTRACTED].includes(status)
                                    && localSize > 0;
        const isLocallyDeletable: boolean = [ViewFile.Status.DEFAULT,
                                    ViewFile.Status.STOPPED,
                                    ViewFile.Status.DOWNLOADED,
                                    ViewFile.Status.EXTRACTED].includes(status)
                                    && localSize > 0;
        const isRemotelyDeletable: boolean = [ViewFile.Status.DEFAULT,
                                    ViewFile.Status.STOPPED,
                                    ViewFile.Status.DOWNLOADED,
                                    ViewFile.Status.EXTRACTED,
                                    ViewFile.Status.DELETED].includes(status)
                                    && remoteSize > 0;
```

AFTER (DELETED bypasses the size gate; other statuses unchanged):

```typescript
        const isQueueable: boolean = status === ViewFile.Status.DELETED
                                    || ([ViewFile.Status.DEFAULT,
                                         ViewFile.Status.STOPPED].includes(status)
                                        && remoteSize > 0);
        const isStoppable: boolean = [ViewFile.Status.QUEUED,
                                    ViewFile.Status.DOWNLOADING].includes(status);
        const isExtractable: boolean = [ViewFile.Status.DEFAULT,
                                    ViewFile.Status.STOPPED,
                                    ViewFile.Status.DOWNLOADED,
                                    ViewFile.Status.EXTRACTED].includes(status)
                                    && localSize > 0;
        const isLocallyDeletable: boolean = [ViewFile.Status.DEFAULT,
                                    ViewFile.Status.STOPPED,
                                    ViewFile.Status.DOWNLOADED,
                                    ViewFile.Status.EXTRACTED].includes(status)
                                    && localSize > 0;
        const isRemotelyDeletable: boolean = status === ViewFile.Status.DELETED
                                    || ([ViewFile.Status.DEFAULT,
                                         ViewFile.Status.STOPPED,
                                         ViewFile.Status.DOWNLOADED,
                                         ViewFile.Status.EXTRACTED].includes(status)
                                        && remoteSize > 0);
```

Net change: two predicates restructured as `DELETED || (other-statuses && size-gate)`.
Two hunks in one file; ~10 lines touched. No new imports, no new
symbols, no API change, no template/SCSS/DOM change.

**Narrower alternative** (if the reviewer wants the strictest
Wave-1-only scope — addresses only the asserted test): drop the
`isRemotelyDeletable` hunk; keep only the `isQueueable` hunk. The RED
test will flip to green either way. The two-hunk version is preferred
because `isRemotelyDeletable` is the "Delete Remote" eligibility flag
— the user-visible symptom of leaving it unfixed is that "Delete
Remote" is silently disabled for DELETED rows the backend no longer
sizes, which is the same FIX-01 class of bug. Flagged here so the
checkpoint reviewer can decide.

## Impact Scan

**Other specs/callers that exercise `isQueueable` and `isRemotelyDeletable`:**

- `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts` —
  test-vector tables at lines 271-329 (`isQueueable`) and 633-680
  (`isRemotelyDeletable`) + the two Wave 1 FIX-01 cases at line 1004+.
  The existing isQueueable vectors include `[DELETED, null, 100]` at
  line 283 (asserts `isQueueable=true`) — the fix MUST preserve this
  row. All existing `[DEFAULT, ...]` and `[STOPPED, ...]` vectors must
  also stay green because the DEFAULT/STOPPED branch is byte-preserved
  (size gate unchanged).
- `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` —
  consumes `isQueueable` / `isRemotelyDeletable` as direct boolean
  fixtures on hand-constructed ViewFiles; does NOT route through
  `createViewFile`, so is indifferent to this change.
- `src/angular/src/app/pages/files/bulk-actions-bar.component.ts` —
  single-pass eligibility loop (lines 99-117) branches on each flag;
  no semantic change (DELETED files will now flow through the
  `queueable.push` / `remotelyDeletable.push` branches, which is
  precisely the fix).
- `src/angular/src/app/services/files/view-file.ts` — type declaration
  only; no runtime coupling.

**Production callers of the affected `createViewFile` transform:** only
`ViewFileService` itself (same file). The transform runs on every
backend model push → one emission point, one code path.

**Risk of breaking existing behavior:** **LOW.** The edit widens the
queueable/remotely-deletable set (DELETED + null-remote-size newly
flips from `false` to `true`); it does not narrow or relocate any
existing `true` case. The DEFAULT and STOPPED branches retain the
`remoteSize > 0` gate byte-for-byte. The only vector that changes
outcome is the previously-unmodeled `[DELETED, *, null]` cell, which
Wave 1 introduced as the RED target. Phase 72's 489+ Angular specs
that pass DELETED fixtures either set `isQueueable` directly (no code
path), or use `remote_size=100` (already green). Downstream
consequence: a DELETED row with no remote-size metadata will now show
"Queue" (Re-Queue from Remote) and "Delete Remote" as enabled actions
in the bulk bar — per D-04 union contract, this is the intended
Phase 76 behavior. Backend dispatch (`BulkCommandService`, unchanged
per D-08) independently validates every action it receives, so a stale
DELETED row that is no longer present on the remote will fail
per-file with the existing partial-success toast path — not a new
surface, not a new threat.

## Task 3: Fix Applied

**File changed:** `src/angular/src/app/services/files/view-file.service.ts`
**Lines changed:** 10 insertions, 10 deletions (net 0; structural restructure of two predicates)
**Hunks:** 2 (`isQueueable` at lines 348-351, `isRemotelyDeletable` at lines 364-369)
**FIX-01 tests:** PASS — Wave 1 RED (`DELETED + remote_size=null must be queueable`) is now GREEN; GREEN control (`DELETED + remote_size>0 is queueable`) stays GREEN
**Full Angular suite:** 596 passing, 0 failing (was 595 passing, 1 failing before fix)
**DOM/visual diff:** none — `bulk-actions-bar.component.html` and `bulk-actions-bar.component.scss` byte-identical to HEAD
**git diff --stat:** exactly ONE production file changed (`view-file.service.ts`)
**Approval basis:** two-hunk version approved in checkpoint resume signal

### Verification Commands

```
$ git diff -- src/angular/src/app/pages/files/bulk-actions-bar.component.html
(empty)
$ git diff -- src/angular/src/app/pages/files/bulk-actions-bar.component.scss
(empty)
$ git diff --stat
 .../src/app/services/files/view-file.service.ts      | 20 ++++++++++----------
 1 file changed, 10 insertions(+), 10 deletions(-)
```

### Full Diff (for the record)

```diff
diff --git a/src/angular/src/app/services/files/view-file.service.ts b/src/angular/src/app/services/files/view-file.service.ts
index 1441241..8de65f9 100644
--- a/src/angular/src/app/services/files/view-file.service.ts
+++ b/src/angular/src/app/services/files/view-file.service.ts
@@ -345,10 +345,10 @@ export class ViewFileService implements OnDestroy {
             }
         }
 
-        const isQueueable: boolean = [ViewFile.Status.DEFAULT,
-                                    ViewFile.Status.STOPPED,
-                                    ViewFile.Status.DELETED].includes(status)
-                                    && remoteSize > 0;
+        const isQueueable: boolean = status === ViewFile.Status.DELETED
+                                    || ([ViewFile.Status.DEFAULT,
+                                         ViewFile.Status.STOPPED].includes(status)
+                                        && remoteSize > 0);
         const isStoppable: boolean = [ViewFile.Status.QUEUED,
                                     ViewFile.Status.DOWNLOADING].includes(status);
         const isExtractable: boolean = [ViewFile.Status.DEFAULT,
@@ -361,12 +361,12 @@ export class ViewFileService implements OnDestroy {
                                     ViewFile.Status.DOWNLOADED,
                                     ViewFile.Status.EXTRACTED].includes(status)
                                     && localSize > 0;
-        const isRemotelyDeletable: boolean = [ViewFile.Status.DEFAULT,
-                                    ViewFile.Status.STOPPED,
-                                    ViewFile.Status.DOWNLOADED,
-                                    ViewFile.Status.EXTRACTED,
-                                    ViewFile.Status.DELETED].includes(status)
-                                    && remoteSize > 0;
+        const isRemotelyDeletable: boolean = status === ViewFile.Status.DELETED
+                                    || ([ViewFile.Status.DEFAULT,
+                                         ViewFile.Status.STOPPED,
+                                         ViewFile.Status.DOWNLOADED,
+                                         ViewFile.Status.EXTRACTED].includes(status)
+                                        && remoteSize > 0);
 
         return new ViewFile({
             name: modelFile.name,
```

### Karma Output (FIX-01 describe block)

```
FIX-01 DELETED isQueueable regression
  ✓ DELETED + remote_size=null must be queueable (RED target)
  ✓ DELETED + remote_size>0 is queueable (GREEN control)

Chrome Headless 147.0.0.0 (Mac OS 10.15.7): Executed 23 of 23 SUCCESS (0.026 secs / 0.022 secs)
TOTAL: 23 SUCCESS
```

Full-suite totals:
```
Chrome Headless 147.0.0.0 (Mac OS 10.15.7): Executed 596 of 596 SUCCESS (1.033 secs / 0.974 secs)
TOTAL: 596 SUCCESS
```
