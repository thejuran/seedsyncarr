---
phase: 41-thread-safety
plan: 02
subsystem: controller/extract
tags: [thread-safety, queue-mutex, copy-under-lock, listeners]
dependency_graph:
  requires: []
  provides: [THRD-03, THRD-04]
  affects: [src/python/controller/extract/dispatch.py]
tech_stack:
  added: []
  patterns: [copy-under-lock, context-manager-lock, queue.mutex]
key_files:
  created: []
  modified:
    - src/python/controller/extract/dispatch.py
    - src/python/tests/unittests/test_controller/test_extract/test_dispatch.py
decisions:
  - "Queue mutex pattern: all __task_queue.queue accesses wrapped in with self.__task_queue.mutex — prevents data races with concurrent worker thread"
  - "Copy-under-lock for listeners: snapshot taken inside with self.__listeners_lock, iterated outside — prevents RuntimeError from list modification during iteration"
  - "add_listener uses context manager (with) instead of acquire/release — idiomatic and exception-safe"
  - "TOCTOU window in extract() accepted: duplicate check under mutex then put() has a narrow race, but worst case is double extraction which matches prior behavior"
metrics:
  duration_seconds: 212
  completed_date: "2026-02-24"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 41 Plan 02: Thread-Safe ExtractDispatch Queue Mutex and Listener Lock Summary

Thread-safe queue iteration in ExtractDispatch via copy-under-lock under Queue.mutex, and context manager lock pattern with copy-under-lock for listener notification.

## What Was Built

Fixed two thread-safety issues in `ExtractDispatch`:

**THRD-03: Queue iteration under mutex**

All three locations where `__task_queue.queue` (the internal deque) was accessed directly are now wrapped in `with self.__task_queue.mutex`:
- `status()`: copies queue under mutex, iterates snapshot outside
- `extract()`: checks for duplicates under mutex before put()
- `__worker()`: peeks queue length and reads first task under mutex; re-checks queue under mutex after each task completes

**THRD-04: Context manager lock + copy-under-lock for listeners**

- `add_listener()`: replaced `acquire()/release()` with `with self.__listeners_lock`
- `__worker()` notification: replaced `acquire()/release()` + iteration while holding lock with `with self.__listeners_lock` + copy-under-lock, iterating snapshot outside the lock

**New tests (3):**

- `test_status_returns_consistent_snapshot`: blocks extraction with a threading.Event barrier, calls status() 20 times under concurrent modifications, verifies no exceptions and all results are valid ExtractStatus instances
- `test_extract_duplicate_check_is_safe`: submits a file once to queue it, then calls extract() concurrently from 5 threads to test the duplicate check path; verifies no exceptions
- `test_listener_notification_allows_concurrent_add`: first listener's callback calls `add_listener()` during notification — verifies no RuntimeError (copy-under-lock ensures iteration over snapshot, not live list)

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

21 tests total (18 original + 3 new) — all pass.

```
21 passed in 20.22s
```

## Self-Check: PASSED

Files created/modified:
- FOUND: src/python/controller/extract/dispatch.py
- FOUND: src/python/tests/unittests/test_controller/test_extract/test_dispatch.py
- FOUND: .planning/phases/41-thread-safety/41-02-SUMMARY.md

Commits:
- FOUND: 713825d (fix: thread-safe queue access and listener lock)
- FOUND: 5e2a62c (test: thread-safety tests)
