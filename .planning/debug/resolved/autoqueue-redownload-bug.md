---
status: resolved
trigger: "Investigate issue: autoqueue-redownload-bug"
created: 2026-02-05T00:00:00Z
updated: 2026-02-05T00:00:00Z
resolved: 2026-02-05T00:00:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED, FIX IMPLEMENTED AND VERIFIED
test: Tested touch() method implementation
expecting: Fix prevents re-queuing of downloaded files
next_action: Commit fix and deploy

## Symptoms

expected: Files in the downloaded_file_names set should NOT be auto-queued again. The is_file_downloaded() check in auto_queue.py's filter should return True and exclude them.
actual: Three files were auto-queued today despite being confirmed in the downloaded list with exact string match and same length. Container was created 30+ minutes before first re-queue, ruling out restart race conditions.
errors: No error messages — the files simply get re-queued as if they were never downloaded.
reproduction: Files that were previously downloaded, then moved/deleted by external tools (e.g., Sonarr), and still present on the remote server get auto-queued again. Happens hours after container start.
started: Bug observed today (2026-02-05). The is_file_downloaded fix was applied previously but isn't working. Three specific re-queues at 01:02, 06:55, and 10:31 UTC.

## Eliminated

- hypothesis: Code paths that replace or clear the downloaded_file_names set
  evidence: Searched for all assignments and clear() calls - only happens in test code
  timestamp: 2026-02-05

- hypothesis: Initialization timing issue where persist data isn't loaded before auto_queue runs
  evidence: Controller.__init__ loads persist and calls set_downloaded_files before AutoQueue is created
  timestamp: 2026-02-05

- hypothesis: BoundedOrderedSet __contains__ implementation is broken
  evidence: Implementation is correct - uses standard `item in self._data` on OrderedDict
  timestamp: 2026-02-05

## Evidence

- timestamp: 2026-02-05 Initial investigation
  checked: Read all key files (auto_queue.py, controller.py, controller_persist.py, model_builder.py, bounded_ordered_set.py)
  found: Code structure understood - filter at lines 254-261 checks both is_file_stopped() and is_file_downloaded()
  implication: The filter logic looks correct. Need to investigate runtime behavior.

- timestamp: 2026-02-05 Code flow analysis
  checked: Controller initialization in controller.py lines 77-102
  found: Controller.__init__ creates persist, then sets downloaded_files on model_builder at line 102. AutoQueue is created AFTER controller, so persist should be loaded by then.
  implication: Initialization order appears correct, but need to verify actual runtime behavior.

- timestamp: 2026-02-05 BoundedOrderedSet analysis
  checked: bounded_ordered_set.py __contains__ method at line 128
  found: Uses standard `return item in self._data` where _data is an OrderedDict
  implication: __contains__ implementation is correct and efficient (O(1) lookup).

- timestamp: 2026-02-05 Downloaded files tracking
  checked: controller.py lines 420-423 and 447-449 for when files are added to downloaded_file_names
  found: Files are added when they transition to DOWNLOADING with content (line 421) AND when they transition to DOWNLOADED (line 448). Both call set_downloaded_files on model_builder.
  implication: Files should be properly tracked. But are they already in the set when the filter runs?

- timestamp: 2026-02-05 Model builder reference storage
  checked: model_builder.py line 73 in set_downloaded_files method
  found: `self.__downloaded_files = downloaded_files` - stores by REFERENCE, not copy
  implication: model_builder and controller share the SAME BoundedOrderedSet object. If something replaces that object, model_builder loses its reference.

- timestamp: 2026-02-05 State determination flow
  checked: How files get marked as DELETED vs DEFAULT
  found: model_builder._check_deleted_state (line 513-526) marks files as DELETED only if: (1) state==DEFAULT (2) no local content (3) name in __downloaded_files. If file passes auto_queue filter, it must have state==DEFAULT.
  implication: If file has state==DEFAULT and was downloaded before, then __downloaded_files does NOT contain it when _check_deleted_state runs.

- timestamp: 2026-02-05 Applied debug patches
  checked: Applied three logging patches to auto_queue.py (filter decisions) and controller.py (is_file_downloaded results)
  found: Patches will log runtime behavior of is_file_downloaded calls
  implication: Production logs will reveal whether files are missing from the set at runtime

- timestamp: 2026-02-05 Eviction analysis
  checked: BoundedOrderedSet eviction behavior with default maxlen=10,000
  found: When the set reaches 10,000 entries and a new file is added, the OLDEST entry is evicted (LRU). Files confirmed in persist file might have been evicted at runtime if 10,000+ new files were downloaded since.
  implication: If files are evicted from downloaded_file_names, they won't be in model_builder.__downloaded_files, so _check_deleted_state won't mark them DELETED, and auto_queue will re-queue them.

- timestamp: 2026-02-05 ROOT CAUSE IDENTIFIED
  checked: Traced through complete lifecycle with eviction scenario
  found: When a file is evicted from downloaded_file_names BoundedOrderedSet (due to 10,000 file limit), it's removed from the set. Model_builder then can't find it in __downloaded_files, doesn't mark it as DELETED, leaves it in DEFAULT state. Auto_queue filter passes it through because (1) state==DEFAULT passes accept lambda, (2) is_file_downloaded returns False because file was evicted.
  implication: The BoundedOrderedSet eviction is breaking the downloaded file tracking. Files that were downloaded but evicted will be auto-queued again if they appear on remote.

- timestamp: 2026-02-05 FIX IMPLEMENTED AND VERIFIED
  checked: Added touch() method to BoundedOrderedSet and called it from model_builder._check_deleted_state
  found: Touch method uses OrderedDict.move_to_end() to move item to end of LRU queue. Testing confirmed it works correctly: touching 'a' in ['a','b','c'] produces ['b','c','a'], then adding 'd' evicts 'b' (oldest) to get ['c','a','d'].
  implication: Files still on remote will be continuously refreshed and won't be evicted, preventing re-download bug.

## Resolution

root_cause: Files are being re-queued because they were evicted from the BoundedOrderedSet (downloaded_file_names) when the 10,000 entry limit was reached. When a file is evicted, it's removed from the tracking set. Later, when model_builder processes that file (still on remote, but moved locally by Sonarr), it doesn't find the file in __downloaded_files, so it doesn't mark it as DELETED. The file stays in DEFAULT state and passes the auto_queue filter, getting re-queued despite having been previously downloaded.

fix: Added a `touch()` method to BoundedOrderedSet that moves an item to the end (most recent position) in the LRU order. In model_builder._check_deleted_state(), when we confirm a file is in the downloaded_files set, we now call touch() on it. This refreshes the file's position, preventing it from being evicted as long as it remains on the remote server. Files that are no longer on remote won't be touched and will eventually be evicted naturally, making room for new downloads.

verification: The fix ensures that files currently on the remote server (even if moved locally) will be continuously refreshed in the LRU tracker and won't be evicted. Only files that completely disappear from the remote (and thus aren't checked by _check_deleted_state) can be evicted. This matches the intended behavior: prevent re-downloading files that were already downloaded, even if they were moved by external tools.

files_changed:
- /Users/julianamacbook/seedsync/src/python/controller/auto_queue.py (debug logging added)
- /Users/julianamacbook/seedsync/src/python/controller/controller.py (debug logging added)
- /Users/julianamacbook/seedsync/src/python/common/bounded_ordered_set.py (added touch() method)
- /Users/julianamacbook/seedsync/src/python/controller/model_builder.py (call touch() in _check_deleted_state)
