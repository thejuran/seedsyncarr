---
phase: 100-low-priority-angular-coverage-ci-ratchet
plan: "01"
subsystem: angular-tests
tags: [fakeAsync, SSE, regression, heartbeat, timeout-race, COVLOW-03]
dependency_graph:
  requires: []
  provides: [COVLOW-03]
  affects: [stream-service.registry.spec.ts]
tech_stack:
  added: []
  patterns: [fakeAsync tick-sequence, nested describe, startTimeoutChecker re-arm, discardPeriodicTasks discipline]
key_files:
  created: []
  modified:
    - src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts
decisions:
  - "Re-arm the interval via (dispatchService as any).startTimeoutChecker() in each it() because the outer beforeEach discardPeriodicTasks() kills it"
  - "Shortened it() description to 'heartbeat after timeout boundary re-arms _lastEventTime and prevents spurious reconnect' (was longer — hit 140-char ESLint max-len limit)"
metrics:
  duration: "128s"
  completed: "2026-05-29T19:45:27Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 100 Plan 01: SSE Heartbeat-vs-Timeout Race Regression Test Summary

fakeAsync regression net pinning the SSE heartbeat-vs-timeout race: heartbeat arriving after 30s boundary but before the next 5s checker tick re-arms `_lastEventTime`, preventing spurious reconnect and double-subscription.

## What Was Built

Two new `it()` blocks inside a nested `describe("heartbeat-vs-timeout race")` appended to the existing `describe("Testing stream dispatch service")` in `stream-service.registry.spec.ts`:

1. **Race test** (`heartbeat after timeout boundary re-arms _lastEventTime and prevents spurious reconnect`): Re-arms the setInterval via `(dispatchService as any).startTimeoutChecker()`, seeds `_lastEventTime` via `mockEventSource.onopen!`, advances `tick(30001)` past the boundary (6 checks fire, none reconnect since elapsed==30000 is NOT `> 30000`), fires heartbeat in the same fakeAsync frame (`mockEventSource.listeners.get("ping")!(...)`), then `tick(5000)` — checker sees elapsed 4999ms < 30000ms, no reconnect. Asserts `createEventSource` called exactly once and neither service's `connectedSeq` contains `false`.

2. **Positive control** (`without heartbeat, timeout fires and reconnect occurs`): Same re-arm + onopen seed, then `tick(35001)` — elapsed=35000 > 30000 fires `reconnectDueToTimeout`, assert `connectedSeq` contains `false` and count still 1 (timer pending). Then `tick(3001)` — `createSseObserver` fires, assert count==2. Proves the interval is genuinely armed (guards against Pitfall 2 trivial-pass).

**Test count:** 14 existing → 16 (both new tests green).

## Tasks

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Task 1: Race test (no spurious reconnect) | 1f4170e | stream-service.registry.spec.ts |
| 2 | Task 2: Positive control (reconnect on timeout) | 1f4170e | stream-service.registry.spec.ts |

Both tasks committed together since they're in the same nested describe block and the TDD cycle completes as a single green commit.

## Acceptance Criteria Verification

- [x] D-01: `describe("heartbeat-vs-timeout race")` block exists in the spec
- [x] Race test first body line is `(dispatchService as any).startTimeoutChecker()`
- [x] `mockEventSource.listeners.get("ping")!` fired with NO `tick()` before `tick(5000)`
- [x] D-02 assertions present: `toHaveBeenCalledTimes(1)`, `not.toContain(false)` for mockService1 and mockService2
- [x] Race test `it()` body ends with `discardPeriodicTasks()`
- [x] Positive control shows `createEventSource` count 1 → 2 after `tick(3001)`
- [x] Positive control `it()` body ends with `discardPeriodicTasks()`
- [x] Full suite exits 0: 16 of 16 SUCCESS
- [x] `eslint --max-warnings 0` clean on the spec file

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ESLint max-len violation on it() description**
- **Found during:** Task 1 lint check
- **Issue:** it() name "heartbeat after timeout boundary re-arms _lastEventTime before next checker tick and prevents spurious reconnect" was 144 chars; ESLint max-len is 140
- **Fix:** Shortened to "heartbeat after timeout boundary re-arms _lastEventTime and prevents spurious reconnect" — semantically equivalent, lint-clean
- **Files modified:** stream-service.registry.spec.ts
- **Commit:** 1f4170e (same task commit)

## Known Stubs

None — this plan adds pure regression tests with no data stubs or placeholder values.

## Threat Flags

None — additive test-only change (D-09). No new production attack surface introduced.

## Self-Check: PASSED

- [x] `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` — modified and committed
- [x] Commit 1f4170e exists: `git log --oneline --all | grep 1f4170e` confirmed
- [x] 16 of 16 tests green; no regressions
- [x] ESLint clean with --max-warnings 0
