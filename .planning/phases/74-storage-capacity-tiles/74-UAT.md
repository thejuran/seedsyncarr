---
status: partial
phase: 74-storage-capacity-tiles
source: [74-01-SUMMARY.md, 74-02-SUMMARY.md, 74-03-SUMMARY.md, 74-04-SUMMARY.md]
started: 2026-04-20T02:50:00Z
updated: 2026-04-20T02:55:00Z
---

## Current Test

[testing paused — 6 items deferred until after next dev release]

## Tests

### 1. Remote Storage tile — capacity mode
expected: Remote Storage tile shows integer % + "of X.XX TB" + progress bar + "X.XX GB used" sub-line when SSH df succeeds.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 2. Local Storage tile — capacity mode
expected: Local Storage tile shows integer % + "of X.XX TB" + progress bar + "X.XX GB used" sub-line, driven by local `shutil.disk_usage` on the watched path.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 3. Tile fallback to tracked-bytes when capacity unavailable
expected: If the remote SSH df call fails (or local disk read errors), the affected tile silently falls back to the pre-existing tracked-bytes layout — no error banner, no blank UI, the other tile is unaffected.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 4. Threshold color shifts
expected: Progress-bar color follows thresholds — default (amber on Remote, secondary on Local) below 80%; warning (amber, stronger) at ≥80% and <95%; danger (red) at ≥95%. Boundary values flip exactly at 80 and 95.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 5. Per-tile independence
expected: The two tiles evaluate capacity independently — Remote can render capacity mode while Local falls back (or vice versa). One tile's fallback does not pull the other into fallback.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 6. Download Speed and Active Tasks tiles unchanged
expected: The other two tiles in the stats strip render identically to before Phase 74 — no layout shift, no new icons, no regression.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

## Summary

total: 6
passed: 0
issues: 0
pending: 0
skipped: 0
blocked: 6

## Gaps

[none — all 6 tests deferred, not failed]
