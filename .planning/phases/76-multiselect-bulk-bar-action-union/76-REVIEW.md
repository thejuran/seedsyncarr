---
phase: 76-multiselect-bulk-bar-action-union
reviewed: 2026-04-20T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/angular/src/app/services/files/view-file.service.ts
  - src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts
  - src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 76: Code Review Report

**Reviewed:** 2026-04-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** clean

## Summary

Phase 76 (FIX-01 multiselect bulk-bar DELETED union) produced a small, focused
diff. The only production change is in `view-file.service.ts::createViewFile()`:
`isQueueable` and `isRemotelyDeletable` were refactored from a
`[...statuses].includes(status) && remoteSize > 0` shape into a short-circuit
`status === DELETED || ([non-DELETED statuses].includes(status) && remoteSize > 0)`
shape so that DELETED rows bypass the `remoteSize > 0` gate.

The refactor is semantically preserving for every non-DELETED status:

- DEFAULT, STOPPED, DOWNLOADED, EXTRACTED paths go through the exact same
  `includes(...) && remoteSize > 0` branch as before (their statuses were
  never the DELETED branch, so the new OR does not change their outcome).
- QUEUED, DOWNLOADING, EXTRACTING still return `false` (neither branch matches).
- DELETED is the only behavior change: it is now unconditionally `true` for
  both predicates, independent of `remoteSize`. This is the intended fix —
  the backend normalizes `remote_size` to `null` for freshly-deleted rows,
  which `createViewFile` then zeros at lines 303-306, previously forcing
  `isQueueable = false` and silently removing the Re-Queue action from the
  bulk bar.

The existing `isQueueable` / `isRemotelyDeletable` characterization vectors in
`view-file.service.spec.ts` (lines 275-296, 637-656) remain valid under the
new predicate shape — none of them rely on the DELETED+remoteSize-gated false
path, and the `[DELETED, null, 100] → true` vectors still pass (DELETED now
short-circuits true; the old shape passed through the gate with
remoteSize=100 > 0). No regression risk detected.

The Wave 1 characterization tests (view-file.service.spec.ts, 2 new `it`
blocks) and Wave 3 D-09 coverage tests (bulk-actions-bar.component.spec.ts,
3 new `it` blocks) are well-isolated: fixtures are created per-test via the
outer `beforeEach`, spies are installed on fresh `EventEmitter` instances,
and no module-level mutable state is reused. Test fixtures are internally
consistent with the eligibility flags they assert.

No critical, security, or correctness issues found. Two info-level
observations documented below.

## Info

### IN-01: Predicate shape duplicates the `DELETED` short-circuit

**File:** `src/angular/src/app/services/files/view-file.service.ts:348-369`
**Issue:** `isQueueable` and `isRemotelyDeletable` now both carry the same
`status === ViewFile.Status.DELETED || (...)` prefix. This is intentional
(the minimal-edit scope chosen in Wave 2) and correctly reflects the
domain rule "DELETED bypasses the remote-size gate." The duplication is
low-cost for two call sites and keeps the predicates readable; extracting
a helper (`isDeleted(status)`) or a shared `bypassesRemoteSize` flag would
be premature abstraction for v1. Noted only so future maintainers who add
a third size-gated predicate know the pattern.
**Fix:** No change required. If a third predicate gets the same
short-circuit, consider extracting a local helper at that time.

### IN-02: Test fixtures hand-author eligibility flags instead of deriving them

**File:** `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts:372-571`
**Issue:** The three new D-09 tests construct `ViewFile` instances by
directly setting `isQueueable`, `isRemotelyDeletable`, etc. as literal
booleans (e.g. line 378-383: `status: DELETED, isQueueable: true,
isRemotelyDeletable: true, ...`). This is correct for a bar-component
unit test — the bar's job is to faithfully forward whatever eligibility
flags the ViewFile carries, and the fixture values match what
`ViewFileService.createViewFile` would produce for those statuses under
the Wave 2 fix. However, the bar tests do not assert on the
status-to-flag mapping itself, which means if the service-side predicate
drifted (e.g. a future change making DELETED non-queueable again), these
bar tests would still pass with their hardcoded `isQueueable: true`. The
service-side characterization tests in `view-file.service.spec.ts`
(FIX-01 describe block, lines 1004-1074) already cover that mapping, so
the bar-level duplication is acceptable. Noted only as a coupling
observation.
**Fix:** No change required. The split (service asserts status→flag
mapping, bar asserts flag→action-set forwarding) is appropriate for unit
scope. If integration coverage is desired, consider a higher-level test
that wires the real `ViewFileService` into the bar.

---

_Reviewed: 2026-04-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
