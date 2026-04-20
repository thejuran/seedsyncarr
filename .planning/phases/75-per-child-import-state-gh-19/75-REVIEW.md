---
phase: 75-per-child-import-state-gh-19
reviewed: 2026-04-20T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/python/controller/controller_persist.py
  - src/python/controller/webhook_manager.py
  - src/python/controller/controller.py
  - src/python/tests/unittests/test_controller/test_controller_persist.py
  - src/python/tests/unittests/test_controller/test_webhook_manager.py
  - src/python/tests/unittests/test_controller/test_controller_unit.py
  - src/python/tests/unittests/test_controller/test_auto_delete.py
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 75: Code Review Report

**Reviewed:** 2026-04-20
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

The phase-75 data-loss fix (GH #19, FIX-02) is well scoped and the implementation follows the decisions captured in `75-CONTEXT.md`. The core invariants land correctly:

- `ControllerPersist.imported_children` uses a backing `OrderedDict` with both per-root `BoundedOrderedSet` maxlen (500) and a global root-key cap (`max_tracked_files`), with eviction logging on both paths.
- JSON serialisation is backward compatible: missing `imported_children` key defaults to an empty dict.
- `WebhookManager.process()` cleanly widens to `List[Tuple[str, str]]`, with `matched_name` preserving webhook casing and `root_name` retaining canonical casing.
- The new coverage guard in `__execute_auto_delete` runs AFTER the state guard and pack guard, reuses the same BFS over descendants, lowercases consistently on both write and read sides, and grandfathers legacy roots per D-14.
- Tests cover the canonical regression scenarios (D-19) plus the persist rehydration round-trip (D-20) and the webhook-tuple migration.

Two warnings and five info-level findings follow. None are critical, but the warnings deserve attention before release — in particular WR-01, which describes a scenario where the webhook-title fallback chain can poison `imported_children[root]` and block auto-delete indefinitely on real-world packs.

## Warnings

### WR-01: Webhook `releaseTitle` fallback poisons `imported_children[root]` and blocks auto-delete

**File:** `src/python/controller/controller.py:767` (interaction with `src/python/web/handler/webhook.py:_extract_sonarr_title`)
**Issue:**
`_extract_sonarr_title` (webhook.py lines 131-161) uses a fallback chain: `episodeFile.sourcePath (basename) -> release.releaseTitle -> series.title`. When Sonarr's payload is missing `episodeFile.sourcePath`, the webhook enqueues the pack/release name itself (e.g. `Big.Train.S02.WEB-DL...`) as the "file name."

In `WebhookManager.process()`, that name lower-cases to the ROOT key in `name_to_root`, so:
- `root_name = "Big.Train.S02.WEB-DL..."`
- `matched_name = "Big.Train.S02.WEB-DL..."` (same string, different casing possible)

Then in `__check_webhook_imports` line 767, `add_imported_child(root_name, matched_name.lower())` stores the **root name itself** as a "child" in `imported_children[root]`. When the Timer fires, the coverage guard (controller.py lines 896-916) iterates `on_disk_videos` = actual episode basenames (`big.train.s02e01.mkv`, `...e02.mkv`, …) and compares against `imported_children[root]` = `{"big.train.s02.web-dl..."}`. Every episode is reported as "missing" and the pack is skipped **forever** (no safety timeout per D-12).

D-14's grandfather clause does NOT kick in because the key IS present — just populated with a useless value. Pre-phase-75 behaviour would have auto-deleted (since only `imported_file_names` was consulted); post-phase-75 introduces a silent regression for the `releaseTitle`/`series.title` fallback paths.

This aligns with GH #19's "err on the side of not losing data" stance but represents a user-visible behaviour change that is not covered by any test, is not called out in any decision, and has no log line that explains the actual cause ("partial import" is misleading when the "imported child" is really the root).

**Fix:** Two viable options:

Option A (preferred, smallest change) — in `__check_webhook_imports`, skip the `add_imported_child` call when `matched_name.lower() == root_name.lower()`, since a root-level match carries no per-child information:

```python
# D-05 / D-07: record root always; record per-child only when the
# webhook identifies a distinct child basename.
self.__persist.imported_file_names.add(root_name)
if matched_name.lower() != root_name.lower():
    self.__persist.add_imported_child(root_name, matched_name.lower())
self.logger.info(
    "Recorded webhook import: '{}' (child: '{}')".format(root_name, matched_name)
)
self._set_import_status(self.__model, root_name)
```

This keeps D-14 grandfather active for `releaseTitle`-fallback roots (no key → proceed) and continues to populate `imported_children` only for real per-child webhooks.

Option B — in `WebhookManager.process()`, emit `matched_name = None` when the webhook string matched the root key and propagate the `Optional[str]`. More invasive, touches the public return shape again.

Add a unit test that exercises a `releaseTitle`-style fallback webhook (matched_name == root) on a multi-episode pack and confirms the Timer-fire still auto-deletes (because grandfather applies). Without the fix, the test would assert `delete_local.assert_not_called()`, documenting the regression.

### WR-02: `imported_children.pop` is skipped when `delete_local` raises

**File:** `src/python/controller/controller.py:920-926`
**Issue:**
The post-delete cleanup sequence is:

```
self.__file_op_manager.delete_local(file)           # 920
self.logger.info("Auto-deleted local file '{}'".format(file_name))  # 921
with self.__model_lock:
    self.__persist.imported_children.pop(file_name, None)  # 926
```

`delete_local` dispatches a subprocess — ordinarily non-blocking, but the call itself can raise (FileOperationManager can throw during process spawn, the model lock acquisition can be interrupted by a signal-raising exception in the Timer thread, etc.). If anything raises between line 920 and line 926, the `imported_children[root]` entry leaks indefinitely: the next Timer-fire for the same root (after a rearm) will compare fresh on-disk videos against the stale per-child set, producing either a false partial-import skip or a false full-coverage delete depending on overlap.

The related log on line 921 also fires BEFORE cleanup completes, so a leaked entry looks "successfully deleted" in logs but isn't fully reconciled in persist. This is a low-probability but real persist-drift bug.

**Fix:** Wrap the dispatch+cleanup in try/finally so the persist cleanup runs regardless of dispatch outcome, OR move the `pop` above the `delete_local` call (the entry is semantically "done" the moment we commit to dispatching). The simpler fix:

```python
# Clear per-child entry BEFORE dispatching delete -- the decision to
# delete is final at this point, and failures in delete_local should
# not leave stale imported_children state behind for the rearm path.
with self.__model_lock:
    self.__persist.imported_children.pop(file_name, None)
# delete_local is safe outside lock -- it spawns a subprocess.
self.__file_op_manager.delete_local(file)
self.logger.info("Auto-deleted local file '{}'".format(file_name))
```

Note that this reorders mutation relative to D-04's "on successful __execute_auto_delete (delete actually dispatched)" wording — "dispatched" is the current interpretation of "successful," and inverting the ordering preserves that intent while removing the drift window. Alternatively, keep order and use try/finally.

## Info

### IN-01: Unused `Dict` import in `controller_persist.py`

**File:** `src/python/controller/controller_persist.py:4`
**Issue:** `from typing import Dict, Optional` — `Dict` is not referenced anywhere in the module. The docstring on line 58 mentions `Dict[str, BoundedOrderedSet[str]]` conceptually, but the actual annotation on line 63 uses `"collections.OrderedDict[str, BoundedOrderedSet[str]]"`.

**Fix:** Drop `Dict` from the import list: `from typing import Optional`.

### IN-02: `imported_children_root_count` exposed in stats but not registered with `MemoryMonitor`

**File:** `src/python/controller/controller.py:144-180` (init block), `src/python/controller/controller_persist.py:123` (stats output)
**Issue:** `ControllerPersist.get_eviction_stats()` exposes `imported_children_evictions` and `imported_children_root_count` (phase-75 additions), but neither is registered with `MemoryMonitor` alongside the other bounded-collection counters (`downloaded_evictions`, `extracted_evictions`, `stopped_evictions`, `imported_evictions`). Operators reading the memory-monitor log will see every other bounded collection but will not see whether `imported_children` is accumulating roots or evictions.

`test_init_creates_memory_monitor` (test_controller_unit.py line 119) still asserts exactly 9 data sources — so adding two more registrations will require updating that assertion.

**Fix:** In `Controller.__init__`, register the two new data sources:

```python
self.__memory_monitor.register_data_source(
    'imported_children_root_count',
    lambda: len(self.__persist.imported_children)
)
self.__memory_monitor.register_data_source(
    'imported_children_evictions',
    lambda: sum(bset.total_evictions for bset in self.__persist.imported_children.values())
)
```

and update the test's count assertion from 9 to 11.

### IN-03: No test coverage for the global root-key eviction branch in `add_imported_child`

**File:** `src/python/controller/controller_persist.py:80-91` (code), `src/python/tests/unittests/test_controller/test_controller_persist.py:267-281` (test gap)
**Issue:** `test_imported_children_eviction_per_root` covers the per-root `BoundedOrderedSet` eviction, but the outer `popitem(last=False)` branch (lines 82-88) — which evicts the oldest root when `len(self.imported_children) >= self._max_tracked_files` — has no test. The debug log it emits would also go unverified.

**Fix:** Add:

```python
def test_imported_children_root_cap_eviction(self):
    """Global root-key cap evicts oldest root when max_tracked_files exceeded."""
    persist = ControllerPersist(max_tracked_files=3)
    for i in range(4):
        persist.add_imported_child("root{}".format(i), "ep.mkv")
    self.assertEqual(3, len(persist.imported_children))
    self.assertNotIn("root0", persist.imported_children)
    self.assertIn("root3", persist.imported_children)
```

### IN-04: `test_to_str` asserts `imported == []` but not `imported_children == {}`

**File:** `src/python/tests/unittests/test_controller/test_controller_persist.py:37-38`
**Issue:** The existing `test_to_str` test asserts the `imported` key appears as an empty list in the serialized output but does not assert the `imported_children` key appears as an empty dict. `test_imported_children_in_to_str` only validates the populated case. An accidental regression where `to_str` omits `imported_children` when empty would slip past.

**Fix:** Add one line at the end of `test_to_str`:

```python
self.assertTrue("imported_children" in dct)
self.assertEqual({}, dct["imported_children"])
```

### IN-05: Log on line 921 ("Auto-deleted local file") fires before subprocess completes

**File:** `src/python/controller/controller.py:920-921`
**Issue:** `delete_local` is a subprocess-dispatch call (comment on lines 917-919 says so explicitly), so "Auto-deleted" in the log is actually "Auto-delete dispatched." If the subprocess later fails (permissions, filesystem error), operators reading logs see a clean "Auto-deleted" line followed by an unrelated error elsewhere, which hampers diagnosis. Not a correctness bug — FileOperationManager is expected to surface subprocess errors on its own — but the wording is misleading and inconsistent with the "dispatched" framing used elsewhere in the file (e.g. D-04 decision text says "delete actually dispatched").

**Fix:** Rephrase to match the PR-18 skip-log style and dispatch semantics:

```python
self.logger.info("Auto-delete dispatched for local file '{}'".format(file_name))
```

---

_Reviewed: 2026-04-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
