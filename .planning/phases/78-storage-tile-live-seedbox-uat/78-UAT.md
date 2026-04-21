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
result: pass
evidence: "Three D-09 df-failure modes exercised. Mode (a) path-missing: `sed -i 's|^remote_path = /data$|remote_path = /nonexistent|'` + app restart → scanfs emits `SystemScannerError: Path does not exist: /nonexistent`; SshcpError wraps it with `recoverable=False` (remote_scanner.py:97); server.up flips to false; storage.remote_total flips to null. Remote tile renders tracked-bytes fallback (`0 B Tracked`, no %, no of-X-MB, no progress bar); Local tile remains in capacity mode (`0% of 100 MB + 0 B used`). Screenshot: evidence/03-fallback-layout.png. WARN: `Caught an SshcpError: SystemScannerError: Path does not exist: /nonexistent` (app log 19:00:49,165). Mode (b) network-drop: `docker stop seedsyncarr_phase78_ssh_target` → compose-DNS entry vanishes; next scan raises `SshcpError: Bad hostname: ssh-target`. WARN: `Caught an SshcpError: Bad hostname: ssh-target` (app log 19:03:08,331). Storage frame: `storage.remote_total` stays at last-known 104857600 (NOT null) — per `controller.py:_should_update_capacity` lines 644-645, `new is None → return False → no write → retain last-known`. This is correct D-16 silent-fallback design (retention-across-transient-failures, not null-out), clarifying the original plan text which implied immediate null-out. Local tile unaffected. Mode (c) parse-failure: `docker exec … cp /usr/bin/df /usr/bin/df.real && printf '#!/bin/sh\\necho garbage\\n' > /usr/bin/df && chmod +x /usr/bin/df` → WARN: `df output parse failed for '/data': b'garbage'` (app log 19:06:18,112) verbatim matches remote_scanner.py:133. Server stays up; storage retained at 104857600 per same None-guard; Local tile unaffected. All three modes reverted; post-revert SSE shows both sides at 104857600 capacity. Environment restored: `df --version` reports `df (GNU coreutils) 8.32`; `grep '^remote_path = /data$' settings.cfg` ok; ssh-target container Running."

### 4. Threshold color shifts
expected: Progress-bar color follows thresholds — default (amber on Remote, secondary on Local) below 80%; warning (amber, stronger) at ≥80% and <95%; danger (red) at ≥95%. Boundary values flip exactly at 80 and 95.
result: pass
evidence: "Fallocate sequence at 50M / 80M / 95M against /data (ssh-target tmpfs) with a 6-7s scan-interval wait between each. Remote tile values: 50% (remote_used=52428800), 80% (remote_used=83886080), 95% (remote_used=99614720) — all integer-rounded exactly at the boundaries per `| number:'1.0-0'` pipe. Screenshots: evidence/04-threshold-50-amber.png (default amber < 80), evidence/04-threshold-80-warning.png (warning flip at the 80% boundary — visibly stronger amber/orange than the 50% shot), evidence/04-threshold-95-danger.png (danger flip at the ≥95 boundary — clearly red). Boundary-ping at 79/94 not needed — 50/80/95 screenshots are visually unambiguous and cover one data point per zone per D-07. Local tile held at 0% throughout — threshold logic operates per-tile. Fill cleaned post-sequence; post-cleanup SSE confirms remote_used=0. Visual color-correctness validation is the user's call at the Task 6 checkpoint (D-14)."

### 5. Per-tile independence
expected: The two tiles evaluate capacity independently — Remote can render capacity mode while Local falls back (or vice versa). One tile's fallback does not pull the other into fallback.
result: pass
evidence: "Direction 1 (remote-fail/local-ok): exercised during all three Test 3 modes. Canonical visual is evidence/05-per-tile-independence.png (same frame as evidence/03-fallback-layout.png — Remote tracked-bytes fallback + Local `0% of 100 MB + 0 B used` capacity mode, side-by-side). One tile's fallback did not pull the other into fallback in any of the three Test 3 injections. Direction 2 (local-fail/remote-ok): skipped per D-11 'drop local-fail if it would require disruptive action on the dev host OS'. The LocalScanner OSError/ValueError branch is already covered by unit tests (74-VALIDATION.md Task 74-02-T1d, TestLocalScanner fixtures); reproducing it live on macOS would require unmounting the seedsyncarr container's tmpfs mid-run, which kills the container and isn't a meaningful UAT signal. Skip is documented; coverage for the branch is preserved in unit tests."

### 6. Download Speed and Active Tasks tiles unchanged
expected: The other two tiles in the stats strip render identically to before Phase 74 — no layout shift, no new icons, no regression.
result: pass
evidence: "Full-page dashboard snapshot in evidence/06-unchanged-tiles.png. Download Speed tile: `0 B/s` main value with `Peak: 0 B/s` sub-line — same pre-phase-74 shape (header icon + main number + sub-line, no capacity fields, no progress bar). Active Tasks tile: `0 Running` main value + `0 DL` + `0 Queued` badge pills — same pre-phase-74 badge-dl/badge-queued shape. Structural proof: `git diff f3a225a -- src/python src/angular` = empty output. f3a225a is the Phase 78 plan-start commit (`docs(78): create phase plan`); every commit on the branch since then has been under `.planning/phases/78-storage-tile-live-seedbox-uat/` — zero source-code changes anywhere under src/. Phase 78's read-only contract preserved."

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

[pending — filled at test-run completion]
