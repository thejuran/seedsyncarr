---
created: 2026-02-04T11:12
title: Fix AutoQueue re-queueing already-downloaded files
area: backend
files:
  - src/python/controller/controller.py:217
  - src/python/controller/auto_queue.py:209-212
---

## Problem

When external tools like Sonarr import and move/rename downloaded files, SeedSync's AutoQueue incorrectly re-queues files that were already successfully downloaded. This happens because:

1. SeedSync downloads a file from the seedbox to local staging
2. Sonarr detects the file, imports via hardlink, and may delete/move the original
3. AutoQueue scans and sees file exists on remote but not locally
4. AutoQueue re-queues the file unnecessarily

While SeedSync skips the actual transfer (detects file exists), this creates unnecessary log noise and potential race conditions.

**Root cause:** AutoQueue checks `is_file_stopped()` but not `is_file_downloaded()`.

Full details: `/Users/julianamacbook/Obsidian/Coding/SeedSync AutoQueue Fix to Prevent Re-Queueing Already-Downloaded Files.md`

## Solution

1. Add `is_file_downloaded()` method to `controller.py` that checks `__persist.downloaded_file_names`
2. Update AutoQueue filter in `auto_queue.py` (lines 209-212) to also skip files already in downloaded list

```python
# In auto_queue.py, update the filter:
files_to_queue = [
    (name, pattern) for name, pattern in files_to_queue_dict.items()
    if not self.__controller.is_file_stopped(name)
    and not self.__controller.is_file_downloaded(name)  # NEW
]
```
