---
status: partial
phase: 73-dashboard-filter-for-every-torrent-status
source: [73-VERIFICATION.md]
started: 2026-04-19T23:59:07Z
updated: 2026-04-19T23:59:07Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Playwright e2e suite — Done expand, Pending reveal, URL round-trip
expected: All 10 tests in `src/e2e/tests/dashboard.page.spec.ts` pass under a live docker-compose stack (`make run-tests-e2e`). The 3 new tests from plan 73-05 are:
  - `should expand Done segment to reveal Downloaded and Extracted subs`
  - `should reveal Pending sub under Active`
  - `should persist Done filter via URL query param (D-09)`
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
