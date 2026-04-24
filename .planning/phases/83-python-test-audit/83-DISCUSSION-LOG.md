# Phase 83: Python Test Audit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 83-python-test-audit
**Areas discussed:** Staleness criteria, Coverage safety net, Inventory format, Removal granularity

---

## Staleness Criteria

| Option | Description | Selected |
|--------|-------------|----------|
| Dead code only | Only remove tests where the code under test has been deleted or completely rewritten. If the production function still exists and the test exercises it, keep it. | ✓ |
| Dead code + meaningless | Also remove tests that pass but test nothing useful — e.g., tests that only assert a mock was called with no real logic, or tests for trivially obvious behavior. | |
| Dead code + redundant | Also remove tests that duplicate coverage of the same code path — e.g., two tests that both hit the same handler with the same inputs and assert the same thing. | |

**User's choice:** Dead code only
**Notes:** User asked why option 1 was recommended over 2 or 3. After hearing the tradeoff analysis (safety/speed vs judgment overhead vs review time), confirmed dead-code-only as the right scope for this milestone.

---

## Coverage Safety Net

| Option | Description | Selected |
|--------|-------------|----------|
| Remove then verify | Remove all identified stale tests in one pass, then run coverage to confirm threshold holds. If it drops below 84%, investigate which removals caused it and decide per-case. | ✓ |
| Pre-analyze per file | Before removing anything, run coverage analysis to identify which test files contribute to the 84% threshold. Only remove tests that contribute zero unique coverage. | |
| Incremental batches | Remove tests in small batches (e.g., per test module), run coverage after each batch. Slower but catches threshold issues early. | |

**User's choice:** Remove then verify (Recommended)
**Notes:** None

---

## Inventory Format

| Option | Description | Selected |
|--------|-------------|----------|
| Table per file | A markdown table: test file path, test count removed, reason (e.g., 'tests module X deleted in v3.0'). Compact, scannable, reviewable. | ✓ |
| Grouped by reason | Group removed tests by why they're stale (e.g., 'removed module', 'rewritten handler', 'superseded by new impl'). Good for pattern analysis. | |
| Inline in commit messages | No separate inventory file — document each removal in the git commit message. Keeps history in git, but harder to review as a whole. | |

**User's choice:** Table per file (Recommended)
**Notes:** None

---

## Removal Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Method-level | Remove individual stale test methods. If all methods in a file are stale, delete the whole file. Orphaned helpers/fixtures cleaned up if nothing imports them. | ✓ |
| File-level only | Only remove entire test files where every test is stale. Leave mixed files untouched even if some methods are dead. Simpler but less thorough. | |
| Method-level, skip helpers | Remove stale test methods but leave test helpers and fixtures alone even if orphaned. Minimizes blast radius at the cost of leftover dead code in test infra. | |

**User's choice:** Method-level (Recommended)
**Notes:** None

---

## Claude's Discretion

None — all areas had explicit user decisions.

## Deferred Ideas

None — discussion stayed within phase scope.
