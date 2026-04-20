---
status: partial
phase: 76-multiselect-bulk-bar-action-union
source: [76-VERIFICATION.md]
started: 2026-04-20T18:40:00Z
updated: 2026-04-20T18:40:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Dashboard smoke — single DELETED selection
expected: Bulk-actions bar appears with Queue (re-queue from remote) and Delete Remote buttons enabled; Stop, Extract, Delete Local disabled. Clicking Queue initiates a re-download from remote.
result: [pending]

### 2. Dashboard smoke — DELETED + DOWNLOADING mix
expected: Bar shows Queue enabled (1 eligible), Stop enabled (1 eligible), Delete Remote enabled (2 eligible), Extract and Delete Local disabled. Clicking Queue dispatches only against the DELETED row's filename; clicking Stop dispatches only against the DOWNLOADING row's filename.
result: [pending]

### 3. Visual parity — rendered bar pre/post Phase 76
expected: Pixel-identical. Queue label stays literal "Queue", button icons/order/spacing/colors unchanged. No count badges, no new tooltips. (D-06/D-07 visual freeze.)
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
