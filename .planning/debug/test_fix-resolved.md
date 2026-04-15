# Test Plan for persist-file-external-delete Fix

## Scenario: File externally deleted, then re-uploaded to remote

### Before Fix
1. File "show.mkv" downloaded → added to downloaded_file_names
2. Sonarr moves file externally → file deleted locally
3. File still on remote → State: DELETED ✓
4. File also deleted from remote (user cleanup)
5. _prune_downloaded_files runs → removes "show.mkv" from downloaded_file_names ✗
6. Later: Same file re-uploaded to remote
7. File NOT in downloaded_file_names → State: DEFAULT
8. AutoQueue queues it again ✗ BUG

### After Fix
1. File "show.mkv" downloaded → added to downloaded_file_names
2. Sonarr moves file externally → file deleted locally
3. File still on remote → State: DELETED ✓
4. File also deleted from remote (user cleanup)
5. _prune_downloaded_files runs → NO-OP (files never pruned) ✓
6. Later: Same file re-uploaded to remote
7. File STILL in downloaded_file_names → State: DELETED ✓
8. AutoQueue skips it (is_file_downloaded returns True) ✓ FIXED

## Verification Points

1. ✓ downloaded_file_names uses BoundedOrderedSet (automatic LRU eviction)
2. ✓ _prune_downloaded_files is now a no-op
3. ✓ AutoQueue checks is_file_downloaded before queueing
4. ✓ DELETED state requires file in downloaded_file_names
5. ✓ Files persist in downloaded_file_names even when completely gone

## Edge Cases Handled

1. File deleted locally, still on remote → DELETED state, not queued ✓
2. File deleted from both, then reappears → Still DELETED, not queued ✓
3. 10,000+ files downloaded → Oldest evicted by BoundedOrderedSet ✓
4. Remote scan fails → File state preserved ✓
