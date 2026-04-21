---
status: partial
phase: 78-storage-tile-live-seedbox-uat
source: [78-UAT.md]
started: 2026-04-21T18:50:50Z
updated: 2026-04-21T18:50:50Z
---

## Current Test

[awaiting Task 2 — Test 1 execution]

## Tests

### 1. Remote Storage tile — capacity mode
expected: Tile renders '<N>%' + 'of 100.00 MB' + amber bar (or warning/danger at boundary) + '<N.NN> MB used' after a `fallocate -l 50M /data/fill.img` inside the container drives a successful df scan.
result: pending
notes: ""
followups: ""

### 2. Local Storage tile — capacity mode
expected: Tile renders '<N>%' + 'of ~100 MB' + progress bar + '<N.NN> MB used' after writing ~50 MB to the host loop mount drives a successful shutil.disk_usage scan.
result: pending
notes: ""
followups: ""

### 3. Tile fallback to tracked-bytes when capacity unavailable
expected: Three injected failure modes (path-missing, network-drop, parse-failure) each produce: (a) affected tile reverts to tracked-bytes layout within one scan cycle, (b) matching WARN log line emitted, (c) opposite tile continues rendering capacity mode.
result: pending
notes: ""
followups: ""

### 4. Threshold color shifts
expected: Bar color flips amber→warning at pct=80 boundary and warning→danger at pct=95 boundary, driven by fallocate fill sequence 79M / 80M / 94M / 95M.
result: pending
notes: ""
followups: ""

### 5. Per-tile independence
expected: Remote-fail/local-ok renders Remote in fallback + Local in capacity simultaneously. Local-fail/remote-ok runs if reproducible without disruptive host action; otherwise skip is documented here.
result: pending
notes: ""
followups: ""

### 6. Download Speed and Active Tasks tiles unchanged
expected: Both tiles render identical to pre-phase-74 layout (no new icons, no new sub-lines, same class names, same pipes).
result: pending
notes: ""
followups: ""

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

[pending — filled at test-run completion]
