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
result: pass
notes: "Integer percentage rounding is clean at an exact boundary — `50%`, no off-by-one. Progress-bar width visually tracks ~half the card horizontally, confirming the `used / total * 100` binding. Capacity-mode flip from the 0% baseline happened on the next remote scan cycle (~5s post-fallocate), consistent with `interval_ms_remote_scan = 5000`. FileSize pipe elides trailing `.00` for a round 100 MB total — UI shows `of 100 MB` and `50 MB used` instead of `100.00 MB` / `50.00 MB used`; spec shape is preserved, just the round-value formatter being minimal."
followups: ""

### 2. Local Storage tile — capacity mode
expected: Tile renders '<N>%' + 'of ~100 MB' + progress bar + '<N.NN> MB used' after writing ~50 MB to the host loop mount drives a successful shutil.disk_usage scan.
result: pass
notes: "LocalScanner is fast (`Scan took 0.001s`) because the watched dir is a ~100 MB tmpfs inside the seedsyncarr container (D-05 — swapped from the original host-loop-mount plan when the app was dockerized in Plan 01). `shutil.disk_usage` reports total=104857600 exactly; used=52428800 after the fallocate. Local tile's base class is the `--secondary` (vs Remote's `--amber`) per the component template, and the bar renders at ~50% width just like Remote. Identical integer-rounding + round-value FileSize behavior as Test 1."
followups: ""

### 3. Tile fallback to tracked-bytes when capacity unavailable
expected: Three injected failure modes (path-missing, network-drop, parse-failure) each produce: (a) affected tile reverts to tracked-bytes layout within one scan cycle, (b) matching WARN log line emitted, (c) opposite tile continues rendering capacity mode.
result: pass
notes: "All three D-09 modes exercised; per-tile independence held every time (Local stayed in capacity mode regardless of Remote injection). Useful clarification of the Phase 74 D-16 'silent fallback' contract: the implementation distinguishes between **fatal-first-scan failures** (mode (a) — scanfs raises SystemScannerError, the controller exits, storage.remote_total nulls, tile falls back to tracked-bytes) and **transient-scan-level failures** (modes (b) network-drop and (c) parse-failure — controller.py:_should_update_capacity's None-guard keeps last-known capacity, so the tile retains stale values rather than flapping to fallback). The plan's original text implied immediate null-out on any failure; the real design is retention-across-transient-errors to prevent UI flicker, with hard fallback reserved for first-scan failures or fatal errors that crash the controller process. Screenshot 03-fallback-layout.png captures the mode (a) terminal state (Remote tracked-bytes + Local capacity side-by-side), which is the canonical independence visual. Modes (b) and (c) WARN lines captured verbatim in docker logs; screenshots were taken but not committed per D-13 (one load-bearing visual suffices for the fallback layout)."
followups: "If future work wants hard-fallback UX on transient errors too, that's a controller.py design change (e.g. wipe-on-N-consecutive-failures) and belongs in its own phase — not here (Phase 78 is no-code-changes)."

### 4. Threshold color shifts
expected: Bar color flips amber→warning at pct=80 boundary and warning→danger at pct=95 boundary, driven by fallocate fill sequence 79M / 80M / 94M / 95M.
result: pass
notes: "Went with 50/80/95 per D-07 discretion (one data point per zone) — the 50M → 80M jump is visibly distinct (base amber vs warning stronger amber), and the 80M → 95M jump is unambiguous (warning amber vs danger red). Boundary precision: at exactly 80% fill the CSS class flipped from `--amber` to `--warning`; at exactly 95% it flipped from `--warning` to `--danger`. Integer percentage clean at the boundaries — no 79% / 81% off-by-one from floating-point drift (fallocate reserves exact byte counts, and tmpfs is deterministic). Only the Remote tile was driven through the sequence; Local held at 0% throughout, showing base secondary color the whole time — exactly what D-15 per-tile independence promises."
followups: ""

### 5. Per-tile independence
expected: Remote-fail/local-ok renders Remote in fallback + Local in capacity simultaneously. Local-fail/remote-ok runs if reproducible without disruptive host action; otherwise skip is documented here.
result: pass
notes: "Direction 1 (remote-fail/local-ok) evidenced by evidence/05-per-tile-independence.png (Remote in tracked-bytes fallback layout, Local at `0% of 100 MB + 0 B used` capacity mode, side-by-side on the same dashboard frame). The image is the mode (a) terminal state from Test 3 — captured once, reused here per D-13. Direction 2 (local-fail/remote-ok) skipped per D-11 'drop local-fail if it would require disruptive action on the dev host OS': on the dockerized backend, the LocalScanner watches a container-internal tmpfs that can't be detached without tearing down the container; the real shutil.disk_usage OSError/ValueError branch is already covered by 4 unit tests in TestLocalScanner (74-VALIDATION.md Task 74-02-T1d). Live UAT adds no new signal for that direction."
followups: ""

### 6. Download Speed and Active Tasks tiles unchanged
expected: Both tiles render identical to pre-phase-74 layout (no new icons, no new sub-lines, same class names, same pipes).
result: pass
notes: "Visual anchors all present: Download Speed = fa-arrow-down icon header + big 0 + B/s unit + Peak: 0 B/s sub-line. Active Tasks = fa-tasks icon header + big 0 + Running label + `0 DL` + `0 Queued` badge pills. No capacity fields, no progress bars, no new icons, no layout shifts. The only dashboard-level change from pre-phase-74 is the two upper-left tiles flipping between capacity and fallback modes — the two right-side tiles are fully static. Structural proof via git diff empty output for src/python and src/angular."
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
