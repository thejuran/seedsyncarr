---
status: resolved
trigger: "Hold.The.Dream.S01.WEB-DL.AAC.2.0.H264-SWAN not syncing for ~20 minutes until manual restart triggered"
created: 2026-05-05
updated: 2026-05-05
---

# Debug Session: hold-the-dream-not-syncing

## Symptoms

- **Expected behavior:** New file `Hold.The.Dream.S01.WEB-DL.AAC.2.0.H264-SWAN` on remote should be auto-queued within ~30 seconds of appearing (remote scan interval is 30000ms)
- **Actual behavior:** File was not synced for approximately 20 minutes until user triggered a manual re-scan (restart action)
- **Error messages:** None visible in the restart log. After restart, file was successfully auto-queued and started downloading.
- **Timeline:** File appeared on remote ~20 min before manual restart. Brand new file (never previously downloaded). After restart, correctly picked up on first remote scan cycle.
- **Reproduction:** Not reliably reproducible — intermittent. User also notes Fight Club was "stopped" and had just extracted around the same time.
- **Additional context:** The restart log shows ActiveScanner WARNING "Path does not exist: /downloads/Hold.The.Dream..." which is expected (local path doesn't exist yet for a new remote-only file).

## Key Files

- src/python/controller/model_builder.py:55-60 (set_remote_files cache invalidation)
- src/python/controller/model_builder.py:100-104 (has_changes check)
- src/python/controller/model_builder.py:135-152 (cache TTL — 30 min)
- src/python/controller/scan/scanner_process.py:85-113 (scan loop)
- src/python/controller/scan/remote_scanner.py:83-139 (remote scan execution)
- src/python/ssh/sshcp.py (SSH execution with pexpect)
- src/python/controller/controller.py:430-435 (_feed_model_builder - BUG LOCATION)
- src/python/controller/scan_manager.py:137-186 (propagate_exceptions + health check)

## Resolution

### Root Cause

Two related defects that together allow the scanner to go silent for extended periods:

**Bug 1 (data loss on transient error):** `Controller._feed_model_builder()` did not check `ScannerResult.failed` before feeding scan results to the model builder. When a recoverable SSH error occurred, the scanner returned `ScannerResult(files=[], failed=True)`. The controller fed `files=[]` to `ModelBuilder.set_remote_files()`, which replaced the known remote file list with an empty dict — effectively wiping all remote files from the model. On the next successful scan, files would reappear, but this created a window where new files could be missed or the model cache would persist with stale (empty) data.

**Bug 2 (silent process death):** `ScanManager.propagate_exceptions()` only checked the exception queue for errors reported by child processes. If a scanner process was killed externally (OOM, SIGKILL, segfault), no exception would be placed on the queue, and the controller would continue running indefinitely without receiving any new scan results. The model would remain cached until its 30-minute TTL expired.

### Fix Applied

1. **controller.py** (`_feed_model_builder`): Added `and not remote_scan.failed` guard to all three scan result checks. Failed scans are now skipped — the model builder retains the last known-good file list instead of being fed empty data.

2. **scan_manager.py** (`propagate_exceptions` + `_check_process_health`): Added `is_alive()` health check for all scanner processes after checking the exception queue. If any process has died without reporting an exception, raises `ScannerProcessDiedError` so the controller thread terminates cleanly (triggering the app's existing restart/error handling).

3. **Tests:** Added 6 new unit tests (3 for failed scan skipping, 3 for health check behavior). Updated 3 existing tests to explicitly set `failed=False` on their mocks.

### Verification

All 1231 unit tests pass (62 skipped). New tests confirm:
- Failed scans do not feed empty data to model builder
- Dead processes are detected and raise ScannerProcessDiedError
- Health check is skipped when manager is not started (avoids false positives)

## Evidence

- timestamp: 2026-05-05 restart log
  content: "After restart, 238 new files discovered including Hold.The.Dream — proves file was on remote but not being picked up by prior running instance"
- timestamp: 2026-05-05 restart log  
  content: "Remote scan took 11.58s, healthy SSH connection, scanfs already installed (md5 match)"
- timestamp: 2026-05-05 user report
  content: "File was missing for approximately 20 minutes. Fight Club was also stopped and had just extracted around the same time"
- timestamp: 2026-05-05 code analysis
  content: "controller.py:430 - _feed_model_builder did not check .failed flag, feeding empty file lists to model builder on transient SSH errors"
- timestamp: 2026-05-05 code analysis
  content: "scan_manager.py:137 - propagate_exceptions had no is_alive() check, silent process death goes undetected indefinitely"
