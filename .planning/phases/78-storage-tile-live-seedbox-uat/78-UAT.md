---
status: partial
phase: 78-storage-tile-live-seedbox-uat
source: [78-HUMAN-UAT.md]
started: 2026-04-21T18:50:50Z
updated: 2026-04-21T18:50:50Z
resolution: runtime-execution-on-disposable-seedbox
---

## Current Test

[test 0/6 — scaffold written; ready to execute]

## Tests

### 1. Remote Storage tile — capacity mode
expected: Remote Storage tile shows integer % + "of X.XX TB" + progress bar + "X.XX GB used" sub-line when SSH df succeeds.
result: pending

### 2. Local Storage tile — capacity mode
expected: Local Storage tile shows integer % + "of X.XX TB" + progress bar + "X.XX GB used" sub-line, driven by local `shutil.disk_usage` on the watched path.
result: pending

### 3. Tile fallback to tracked-bytes when capacity unavailable
expected: If the remote SSH df call fails (or local disk read errors), the affected tile silently falls back to the pre-existing tracked-bytes layout — no error banner, no blank UI, the other tile is unaffected.
result: pending

### 4. Threshold color shifts
expected: Progress-bar color follows thresholds — default (amber on Remote, secondary on Local) below 80%; warning (amber, stronger) at ≥80% and <95%; danger (red) at ≥95%. Boundary values flip exactly at 80 and 95.
result: pending

### 5. Per-tile independence
expected: The two tiles evaluate capacity independently — Remote can render capacity mode while Local falls back (or vice versa). One tile's fallback does not pull the other into fallback.
result: pending

### 6. Download Speed and Active Tasks tiles unchanged
expected: The other two tiles in the stats strip render identically to before Phase 74 — no layout shift, no new icons, no regression.
result: pending

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

[pending — filled at test-run completion]
