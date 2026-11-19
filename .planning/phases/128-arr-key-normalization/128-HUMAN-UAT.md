---
status: partial
phase: 128-arr-key-normalization
source: [128-VERIFICATION.md]
started: 2026-11-19T11:35:09Z
updated: 2026-11-19T11:35:09Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Linux CI gate for the phase branch
expected: Push gsd/phase-128-arr-key-normalization (or open the phase PR); the Python CI job runs full pytest and whole-tree ruff with both passing and total coverage >= 88% (local Mac measured 86.47% only because CI-only modules test_extract, test_scan, test_lftp and test_sshcp cannot run locally; phase base was 86.39%).
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
