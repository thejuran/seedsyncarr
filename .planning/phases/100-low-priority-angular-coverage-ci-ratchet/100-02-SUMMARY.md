---
phase: 100-low-priority-angular-coverage-ci-ratchet
plan: "02"
subsystem: angular-auth-interceptor
tags: [angular, test, regression, auth, token-rotation, covlow-04]
dependency_graph:
  requires: []
  provides: [COVLOW-04 regression test]
  affects: [src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts]
tech_stack:
  added: []
  patterns: [HttpTestingController flush discipline, mirror-positive test pattern]
key_files:
  created: []
  modified:
    - src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts
decisions:
  - "No extra _resetAuthInterceptorCache() before first request — setupWithMeta already calls it at line 27 (RESEARCH Pitfall 4)"
  - "Test placed between the existing cache test and the POST test to group rotation behavior with cache behavior"
  - "Page-reload coupling comment is accurate: no in-app caller of _resetAuthInterceptorCache; rotation relies on full page reload"
metrics:
  duration: "4 minutes"
  completed: "2026-05-29T19:44:52Z"
  tasks_completed: 1
  files_modified: 1
---

# Phase 100 Plan 02: Token-Rotation Regression Test Summary

Token-rotation regression test via the `_resetAuthInterceptorCache` seam: first request carries `Bearer token-v1`; after meta tag mutation and a single mid-test cache reset, second request carries `Bearer token-v2` (COVLOW-04, D-03/D-04).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Token-rotation regression test via _resetAuthInterceptorCache seam | 8286956 | auth.interceptor.spec.ts (+32 lines) |

## What Was Built

A new `it()` block appended to the `authInterceptor` describe suite in `auth.interceptor.spec.ts`:

- **Test name:** `"should serve new token after _resetAuthInterceptorCache is called (token rotation)"`
- **Pattern:** Mirror positive of the existing `"should cache the token and not re-read meta tag on each request"` test (lines 94-114). The existing test proves stale-by-design (no reset → stale token). The new test is its mirror: with `_resetAuthInterceptorCache()` mid-test, the next request carries the NEW token.
- **Sequence:** `setupWithMeta("token-v1")` → req1 asserts `Bearer token-v1` → meta tag mutated to `"token-v2"` + `_resetAuthInterceptorCache()` once → req2 asserts `Bearer token-v2`.
- **COVLOW-04 satisfied:** The cache lifecycle is now fully documented by the test pair — stale-by-design (negative) + rotation succeeds (positive).

## Verification

```
Chrome Headless 148.0.0.0: Executed 7 of 7 SUCCESS (0.012 secs / 0.01 secs)
TOTAL: 7 SUCCESS
```

ESLint: exit 0 with `--max-warnings 0`.

## Acceptance Criteria Check

- [x] D-03: New `it()` calls `setupWithMeta("token-v1")`, then after the first request mutates meta to `"token-v2"` and calls `_resetAuthInterceptorCache()` exactly once
- [x] First assertion: `toBe("Bearer token-v1")`; second assertion: `toBe("Bearer token-v2")`
- [x] Both expectOne results flushed (`req1.flush("ok")`, `req2.flush("ok")`)
- [x] D-04: Code comment names the full-page-reload coupling; does NOT attribute a reload to `version-check.service.ts`
- [x] Meta-tag query result null-guarded before `setAttribute` (`if (meta) { ... }`)
- [x] Spec exits 0 — new test + all 6 existing tests green (7 total)
- [x] ESLint passes with `--max-warnings 0`
- [x] No production source files modified (D-09: additive test only)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Surface Scan

No new security surface introduced. The new test adds no production code. The existing auth interceptor's Bearer token mechanism is unchanged.

## Self-Check: PASSED

- [x] `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` — FOUND (157 lines, new it() at lines 116-146)
- [x] Commit 8286956 — FOUND (`git log --oneline | grep 8286956`)
- [x] 7 of 7 Angular tests pass for this spec
- [x] ESLint exit 0
