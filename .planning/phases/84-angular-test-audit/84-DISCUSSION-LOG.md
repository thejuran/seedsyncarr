# Phase 84: Angular Test Audit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 84-angular-test-audit
**Areas discussed:** Staleness criteria for Angular, CI warning cleanup scope, CSP detection integration, Coverage safety net

---

## Staleness Criteria for Angular

### Q1: Staleness rule

| Option | Description | Selected |
|--------|-------------|----------|
| Same strict rule (Recommended) | Stale = production code deleted or completely rewritten. Renamed components count as deleted if the old class/file no longer exists. Simple, consistent with Phase 83. | ✓ |
| Broader: include superseded patterns | Also flag tests for UI patterns that were architecturally replaced (e.g., sidebar nav tests, old layout tests) even if some underlying service still exists. | |
| You decide | Claude picks the best approach based on what the codebase scout reveals. | |

**User's choice:** Same strict rule (Recommended)
**Notes:** Consistent with Phase 83 D-01/D-02.

### Q2: Spec file layout

| Option | Description | Selected |
|--------|-------------|----------|
| Leave as-is (Recommended) | This audit is about removing stale tests, not reorganizing. Both locations work and the specs exercise live code. | ✓ |
| Consolidate to tests/unittests/ | Move the 3 co-located specs into the centralized test directory for consistency. Minor scope expansion. | |

**User's choice:** Leave as-is (Recommended)
**Notes:** No reorganization — audit scope only.

---

## CI Warning Cleanup Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Deprecation warnings only (Recommended) | Fix warnings emitted during `ng test --watch=false` output — deprecated APIs, obsolete TestBed patterns, Jasmine deprecations. Minimal scope. | |
| All console noise | Also suppress/fix console.error/warn calls from components during tests, Karma config deprecations, and any other noise in test output. | ✓ |
| You decide | Claude assesses the actual warning output and fixes what's reasonable without expanding scope. | |

**User's choice:** All console noise
**Notes:** Broader than recommended — user wants clean test output.

### Q: Ordering

| Option | Description | Selected |
|--------|-------------|----------|
| After removal (Recommended) | Remove stale tests first (some warnings may disappear with them), then clean up remaining warnings. | ✓ |
| Before removal | Clean warnings first to get a clear baseline, then remove stale tests. | |
| Same pass | Handle both in a single sweep. | |

**User's choice:** After removal (Recommended)

---

## CSP Detection Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to Phase 85 (Recommended) | CSP detection is a Playwright/browser concern. Phase 85 (E2E Test Audit) is the right home. | ✓ |
| Keep in Phase 84 | Handle it here alongside the Angular warning cleanup. | |

**User's choice:** Defer to Phase 85 (Recommended)
**Notes:** Originally folded into Phase 84 but deferred as it's fundamentally an E2E/Playwright concern.

---

## Coverage Safety Net

| Option | Description | Selected |
|--------|-------------|----------|
| Record baseline, no threshold (Recommended) | Run `ng test --code-coverage` before and after. Document the numbers for reviewability but don't enforce a minimum. | ✓ |
| Skip coverage tracking | The "dead code only" rule means no live coverage is lost. Don't spend time on coverage reports. | |
| Establish a threshold | Set a fail_under for Angular and enforce it going forward. Scope expansion. | |

**User's choice:** Record baseline, no threshold (Recommended)

---

## Claude's Discretion

No areas deferred to Claude's discretion in this phase.

## Deferred Ideas

- **CSP violation detection** — deferred to Phase 85 (E2E Test Audit)
