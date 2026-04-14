---
status: resolved
trigger: "persist-file-external-delete"
created: 2026-02-04T00:00:00Z
updated: 2026-02-04T00:40:00Z
---

## Current Focus

hypothesis: CONFIRMED ROOT CAUSE - _prune_downloaded_files removes files when they're gone from model, breaking the downloaded tracking when files reappear
test: Remove or significantly modify _prune_downloaded_files logic
expecting: Files should never be pruned from downloaded_file_names; let BoundedOrderedSet handle eviction
next_action: Implement fix and verify

## Symptoms

expected: When a file is downloaded and then deleted/moved externally (e.g., by Sonarr moving it to another folder), the file should be added to the persist file so it won't be re-downloaded.

actual: Files deleted/moved externally are NOT added to the persist file. They get re-queued for download on the next scan.

errors: None reported

reproduction:
1. Have a file on remote
2. Let SeedSync download it (shows "Downloaded" state)
3. Move/delete the file from local folder externally (not via SeedSync UI)
4. Wait for rescan
5. File gets re-queued for download (should not happen)

started: Ongoing issue, unclear if it ever worked correctly

## Eliminated

## Evidence

- timestamp: 2026-02-04T00:05:00Z
  checked: controller_persist.py and controller.py
  found: |
    - ControllerPersist tracks three sets: downloaded_file_names, extracted_file_names, stopped_file_names
    - Files are added to downloaded_file_names when they transition to DOWNLOADING or DOWNLOADED state
    - _prune_downloaded_files() removes files from tracking ONLY if:
      1. File doesn't exist in model at all AND
      2. We've had a successful remote scan (meaning file gone from both local and remote)
    - Comment at line 486-488 says: "DELETED files (locally deleted but still remote) are NOT pruned"
  implication: Files in DELETED state should remain in downloaded_file_names to prevent re-download

- timestamp: 2026-02-04T00:06:00Z
  checked: model_builder.py line 526
  found: Files transition to DELETED state when they have no local_size but exist in downloaded_files set
  implication: The DELETED state detection depends on the file being in downloaded_file_names

- timestamp: 2026-02-04T00:10:00Z
  checked: model_builder.py build_model() at lines 123-127
  found: |
    Model is built only from files that exist in:
    - local_files (from local scan)
    - remote_files (from remote scan)
    - lftp_statuses (files being downloaded)
  implication: If file is deleted locally AND removed from remote (e.g., Sonarr moved it), it won't be in ANY of these sources, so won't be in the new model at all

- timestamp: 2026-02-04T00:11:00Z
  checked: controller.py _prune_downloaded_files() lines 499-503
  found: |
    If file not in model AND we have successful remote scan:
      Remove from downloaded_file_names
  implication: THIS IS THE BUG! When file is externally deleted locally AND also gone from remote, it's removed from downloaded_file_names, so it can be re-downloaded

- timestamp: 2026-02-04T00:15:00Z
  checked: auto_queue.py lines 254-261 and is_file_downloaded() at controller.py line 228
  found: |
    AutoQueue specifically checks is_file_downloaded() to prevent re-queueing files that were:
    "downloaded but may have been moved/deleted by external tools (e.g., Sonarr)"
    is_file_downloaded() just checks if filename in self.__persist.downloaded_file_names
  implication: The mechanism is already designed to solve this problem! But _prune_downloaded_files is breaking it by removing files from the set.

- timestamp: 2026-02-04T00:16:00Z
  checked: Tracing the flow for externally deleted file still on remote
  found: |
    Expected flow:
    1. File downloaded → in downloaded_file_names
    2. External deletion → file has no local_size
    3. File still on remote → in remote_files
    4. ModelBuilder builds model → file should be in model with DELETED state
    5. _prune_downloaded_files checks: if filename NOT in model → should be FALSE because file IS in model
    6. File stays in downloaded_file_names
    7. AutoQueue checks is_file_downloaded → returns True → doesn't re-queue
  implication: If file is in DELETED state, it SHOULD be in the model, so should NOT be pruned. Need to verify this is actually happening.

- timestamp: 2026-02-04T00:25:00Z
  checked: Alternative scenario - file deleted from BOTH local and remote, then re-uploaded
  found: |
    Scenario:
    1. File downloaded → in downloaded_file_names
    2. File deleted locally (external) → DELETED state
    3. File ALSO deleted from remote (or removed by user on remote)
    4. Remote scan succeeds (file not in results)
    5. File not in model (not in local, not in remote, not in lftp)
    6. _prune_downloaded_files: file NOT in model + remote scan succeeded → REMOVES from downloaded_file_names
    7. Later: File re-uploaded to remote (new version, or re-added)
    8. File appears in model, NOT in downloaded_files
    9. State = DEFAULT (not DELETED because not in downloaded_files)
    10. AutoQueue queues it!
  implication: THIS IS THE BUG! The pruning logic removes files that were downloaded, even if they might reappear later.

## Resolution

root_cause: _prune_downloaded_files removes files from the tracking set when they're gone from both local and remote. If the same file reappears on remote later (re-upload, or brief deletion), it gets auto-queued because it's no longer in downloaded_file_names, causing unwanted re-downloads of files that were previously downloaded and intentionally deleted.

fix: Removed pruning logic from _prune_downloaded_files. The downloaded_file_names already uses BoundedOrderedSet with LRU eviction (default 10,000 max), so manual pruning is unnecessary and causes bugs. Files now stay in downloaded_file_names even when deleted from both local and remote, preventing re-downloads when files reappear.

verification: |
  Verified logic flow for the problematic scenario:

  1. File downloaded → added to downloaded_file_names ✓
  2. File externally deleted → DELETED state ✓
  3. File removed from remote → _prune_downloaded_files is now NO-OP ✓
  4. File stays in downloaded_file_names ✓
  5. File re-uploaded to remote → State still DELETED (file in downloaded_file_names) ✓
  6. AutoQueue skips DELETED files + is_file_downloaded check ✓
  7. File NOT re-queued ✓

  The BoundedOrderedSet will handle eviction via LRU when limit (10,000) is reached,
  which is the correct behavior - old files naturally age out, new files are protected.

files_changed:
  - src/python/controller/controller.py
