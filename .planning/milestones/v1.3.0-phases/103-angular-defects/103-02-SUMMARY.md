---
phase: 103-angular-defects
plan: 02
subsystem: api
tags: [angular, rxjs, sse, eventemitter, subscription, lifecycle, fakeAsync]

# Dependency graph
requires:
  - phase: 103-angular-defects-01
    provides: "BUG-01 ConfirmModal innerHTML fix (independent parallel plan — no hard dep)"
provides:
  - "reconnectDueToTimeout() with leading _currentSubscription teardown mirroring createSseObserver entry teardown"
  - "BUG-04 same-tick reconnect collision regression test discriminating on duplicate disconnect side-effect"
affects: [103-angular-defects]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subscription entry teardown: unsubscribe + null _currentSubscription at every reconnect-arming method entry, not only at createSseObserver"

key-files:
  created: []
  modified:
    - src/angular/src/app/services/base/stream-service.registry.ts
    - src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts

key-decisions:
  - "BUG-04 fix is two-line unsubscribe at top of reconnectDueToTimeout() — _reconnectPending boolean not needed (RESEARCH late-audit conclusion)"
  - "RED discriminator is the duplicate false count in connectedSeq (==2 before fix, ==1 after), not createEventSource count (==2 on both sides because both paths clear-and-re-arm the single timer)"
  - "BUG-04 test placed as a sibling describe after heartbeat-vs-timeout race, inside Testing stream dispatch service outer describe"

patterns-established:
  - "Subscription entry teardown pattern: any method that arms a reconnect timer must unsubscribe _currentSubscription before doing so, mirroring createSseObserver lines 181-182"

requirements-completed: [BUG-04]

# Metrics
duration: 10min
completed: 2026-06-01
---

# Phase 103 Plan 02: BUG-04 SSE Same-Tick Subscription Teardown Summary

**Two-line unsubscribe fix in reconnectDueToTimeout() closes the orphaned-subscription gap where a stale RxJS error handler could deliver duplicate disconnect notifications after an idle-timeout reconnect**

## Performance

- **Duration:** 10 min
- **Started:** 2026-06-01T02:32:34Z
- **Completed:** 2026-06-01T02:43:23Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Confirmed the BUG-04 gap: `reconnectDueToTimeout()` closed `_currentEventSource` but left `_currentSubscription` live for the 3000ms retry window; a stale `onerror` fired through the un-unsubscribed subscription, delivering a second `notifyDisconnected()` to every registered service
- Added `describe("BUG-04 same-tick reconnect collision")` regression test with the correct RED discriminator (duplicate `false` count in `connectedSeq` == 2 before fix, asserted as 1)
- Inserted `this._currentSubscription?.unsubscribe(); this._currentSubscription = null;` at the top of `reconnectDueToTimeout()`, mirroring the identical entry teardown already in `createSseObserver()` lines 181-182
- Full Angular Karma suite passes: 615/615, coverage floors all hold (stmts 84.05% >= 83%, branches 69.31% >= 68%, fns 80.49% >= 79%, lines 84.9% >= 83%)
- Slice-1 heartbeat-vs-timeout race tests preserved byte-for-byte

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — BUG-04 same-tick collision regression test** - `3751941` (test)
2. **Task 2: GREEN — unsubscribe _currentSubscription at top of reconnectDueToTimeout()** - `74beb81` (fix)

**Plan metadata:** *(SUMMARY commit — see final commit)*

_Note: TDD tasks have two commits (test RED → fix GREEN)_

## TDD Gate Compliance

- RED gate: commit `3751941` — `test(103-02): RED — BUG-04 same-tick reconnect collision regression test`. Test FAILED for the correct reason: `Expected 2 to be 1.` at `connectedSeq.filter(v => v === false).length` — the stale subscription's error handler ran and pushed a second `false`.
- GREEN gate: commit `74beb81` — `fix(103-02): BUG-04 unsubscribe _currentSubscription at top of reconnectDueToTimeout()`. Full suite 615/615 SUCCESS.

## Files Created/Modified

- `src/angular/src/app/services/base/stream-service.registry.ts` — Added 5 lines (comment + 2-line teardown + blank line) at the top of `reconnectDueToTimeout()`. No other changes. No IStreamService / StreamServiceRegistry / factory / provider touched.
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` — Added `describe("BUG-04 same-tick reconnect collision")` sibling block (53 lines) after the `heartbeat-vs-timeout race` describe (line 262). Slice-1 tests at lines 209-262 untouched.

## Decisions Made

- **Unsubscribe vs. _reconnectPending:** The RESEARCH.md late-audit conclusion (lines 396-418) concludes `this._currentSubscription?.unsubscribe()` at the top of `reconnectDueToTimeout()` is the minimal correct fix. The `_reconnectPending` boolean was the D-07 fallback and was not needed — the unsubscribe alone suppresses the duplicate disconnect.
- **RED discriminator design:** The `createEventSource` call count is 2 on BOTH sides of the fix (both reconnect paths clear-and-re-arm the single `_reconnectTimer`, so the second path's `clearTimeout` cancels the first, and only one `createSseObserver` fires). Asserting `== 3` would be a false RED signal. The real discriminator is the duplicate `notifyDisconnected()` side-effect captured in `connectedSeq.filter(v => v === false).length`.
- **Test placement:** New sibling `describe` block (not `it()` inside `heartbeat-vs-timeout race`) — cleaner naming boundary for a distinct failure mode.

## Deviations from Plan

None — plan executed exactly as written. The two-line fix and the regression test match the spec precisely. The `_reconnectPending` boolean was explicitly excluded per RESEARCH supersession note; the unsubscribe approach succeeded alone.

## Issues Encountered

- Docker `make run-tests-angular` must be run from the **worktree root**, not from the main repository root (`/Users/julianamacbook/seedsyncarr`). Running from the main repo silently used the main repo's unmodified source files, causing all runs to report 614/614 SUCCESS (the new test was absent). Switching to the worktree's `make` correctly mounted the worktree's `src/angular/src` as the volume, producing the expected 615 tests with 1 FAILED (RED) then 615/615 (GREEN).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- BUG-04 is fully mitigated: the single-subscription invariant is now enforced at every reconnect-arming entry point
- Slice-1 SSE regression suite preserved; new BUG-04 collision regression test permanently guards against re-introduction
- Phase 103 Plan 01 (BUG-01 ConfirmModal innerHTML fix) is the remaining plan in this phase

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: `src/angular/src/app/services/base/stream-service.registry.ts`
- FOUND: `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts`
- FOUND: `.planning/milestones/v1.3.0-phases/103-angular-defects/103-02-SUMMARY.md`
- FOUND: commit `3751941` (RED test)
- FOUND: commit `74beb81` (GREEN fix)
- `_currentSubscription?.unsubscribe()` at lines 146 (reconnectDueToTimeout) and 187 (createSseObserver) — exactly 2 occurrences
- `_reconnectPending` occurrences: 0
- `describe("BUG-04 same-tick reconnect collision")` block present in spec

---
*Phase: 103-angular-defects*
*Completed: 2026-06-01*
