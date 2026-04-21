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
result: pass
evidence: "`docker exec seedsyncarr_phase78_ssh_target fallocate -l 50M /data/fill.img` → `df -B1 /data` reported `tmpfs 104857600 52428800 52428800 50% /data`. Next RemoteScanner cycle: `ssh … seeduser@ssh-target 'df -B1 /data'` (docker logs 18:59:01,771) completed RC=0 in 3.05s. SSE frame: `\"storage\":{…,\"remote_total\":104857600,\"remote_used\":52428800}`. Dashboard tile rendered integer `50%` + `of 100 MB` + amber progress bar (~50% width, class `stat-progress-fill--amber`) + `50 MB used` sub-line — matches the capacity-mode contract. Screenshot: evidence/01-remote-capacity.png. Format note: FileSizePipe elides trailing `.00` decimals for round values (100 MB, 50 MB), so plan's `100.00 MB` / `X.XX MB used` wording rendered as `100 MB` / `50 MB used` here — no spec deviation, just the FileSize formatter's round-value behavior."

### 2. Local Storage tile — capacity mode
expected: Local Storage tile shows integer % + "of X.XX TB" + progress bar + "X.XX GB used" sub-line, driven by local `shutil.disk_usage` on the watched path.
result: pass
evidence: "`docker exec seedsyncarr_phase78_app fallocate -l 50M /data/local/fill.img` → `df -B1 /data/local` reported `tmpfs 104857600 52428800 52428800 50% /data/local`. Next LocalScanner cycle: `Scan took 0.001s` (docker logs 18:59:04,943) — `shutil.disk_usage('/data/local')` returned total=104857600, used=52428800. Same SSE frame as Test 1: `\"storage\":{\"local_total\":104857600,\"local_used\":52428800,…}`. Dashboard tile rendered integer `50%` + `of 100 MB` + secondary-base progress bar (~50% width, class `stat-progress-fill--secondary`) + `50 MB used` sub-line. Screenshot: evidence/02-local-capacity.png (same frame as 01; both tiles visible side-by-side)."

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
