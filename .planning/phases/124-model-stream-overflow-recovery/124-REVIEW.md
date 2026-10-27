---
phase: 124-model-stream-overflow-recovery
reviewed: 2026-10-27T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/python/controller/controller.py
  - src/python/tests/helpers/model_stream_client.py
  - src/python/tests/helpers/wsgi_stream.py
  - src/python/tests/integration/test_web/test_handler/test_stream_model.py
  - src/python/tests/unittests/test_controller/test_controller_unit.py
  - src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py
  - src/python/tests/unittests/test_web/test_handler/test_stream_model_overflow.py
  - src/python/tests/unittests/test_web/test_stream_queue.py
  - src/python/web/handler/stream_model.py
  - src/python/web/utils.py
findings:
  critical: 0
  warning: 2
  info: 4
  convention: 1
  total: 7
status: issues_found
---

# Phase 124: Code Review Report

**Reviewed:** 2026-10-27
**Depth:** standard (phase diff `2ed7078..HEAD`)
**Files Reviewed:** 10
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

The resync design holds up. `Controller.resync_model_files` runs `discard_backlog()` and the snapshot inside a single `__model_lock` acquisition. Every listener producer (`StreamQueue.put` through `Model.add_file/remove_file/update_file`) runs under that same lock (ModelPipeline stores the same Lock object, D-03). So discard-plus-snapshot is atomic with respect to producers, and the dropped-count rebaseline happens inside the lock. Events produced after the snapshot are kept, and drops that happened before it are covered by it.

Questions checked from the brief:

- **Lock ordering / deadlock:** No problem found. `get_value()` runs only on the web stream thread, which never holds `__model_lock`. `_discard_backlog` → `StreamQueue.clear()` takes only the internal `queue.Queue` mutex. Producers take the same order (`__model_lock`, then the queue mutex), so no inversion. `__model_lock` is a non-reentrant `Lock`, but nothing on the resync path re-enters it. The lock is released if `discard_backlog` raises (tested).
- **Bounded memory:** One capped queue plus one transient snapshot list per resync. Serialization runs outside the lock. Nothing accumulates.
- **Test cleanup:** The handler/listener tests release listeners in `finally`/`tearDown`. The WSGI test cancels its Timer, calls `stop()` and `body.close()` in `finally`. The lock-blocking test uses a daemon thread whose `with lock:` is released even if an assertion fails.
- **Flakiness:** Timing is used only in the right direction (join timeout 0.3 s to assert the worker *is* blocked; a 1.5 s stop timer for a drain that needs only a few loop iterations). No flake risk found.

Verification: `ruff check src/python/` passes. The 5 affected test modules pass (217 passed, 6.8 s).

No blockers. The two warnings are (1) a documented guarantee the gate does not actually provide, and (2) a D-05 test whose final assertion proves nothing.

## Warnings

### WR-01: Gate check and dequeue are not atomic, so a stale post-gap event can go out before the resync, contrary to the comment

**File:** `src/python/web/handler/stream_model.py:81-107`
**Issue:** The comment says the gate "must run strictly before get_next_event() so the first value after a drop is never a stale backlog event." That guarantee does not hold. `get_dropped_count()` (line 88) is read without the lock, and `get_next_event()` (line 105) runs later. A producer on the controller thread can overflow the queue between the two calls: `put()` drops the oldest event E_k, then line 105 returns E_{k+1} to the browser, which never saw E_k. The tab briefly applies an event across a gap. The frontend then logs/ignores an UPDATED/REMOVED for an unknown file, or rejects a duplicate ADDED. The next `get_value()` sees the changed count and resyncs, so the tab still converges. The damage is transient (one bad event plus console noise), but the code's stated invariant is wrong, and future maintainers may rely on it.
**Fix:** Re-check after dequeuing, and send the resync in place of the possibly-stale event:
```python
event = self.model_listener.get_next_event()
if self.model_listener.get_dropped_count() != self._last_seen_dropped:
    # a drop raced the dequeue; `event` may follow a gap -- discard it, resync
    return self._resync()   # factor the existing resync block into a helper
if event is not None:
    return self.serialize.update_event(event)
return None
```
(Keep the pre-check too, or rely on this post-check alone.) If you would rather not change the code, at least correct the comment to say the gate is best-effort and convergence comes from the next call.

### WR-02: The D-05 "at most one pending snapshot" test asserts an unrelated attribute

**File:** `src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py:213-228` (`test_resync_pending_state_is_bounded`)
**Issue:** D-05 requires a test proving that at most one snapshot is pending. The test's last assertion, `self.assertIsNone(self.handler.initial_model_files)`, with the comment "No handler attribute holds a list of snapshots -- a single bool", checks the initial-model slot. That slot was already `None` after `setUp` consumed the first `model-init`. It says nothing about resync state, so the test would still pass if someone later replaced `_resync_pending` with a growing list of snapshots. The queue-size assertions are real. The "one pending" half of D-05 is actually covered by `test_multiple_drops_coalesce_into_one_resync` (one `resync_model_files` call), not by this test.
**Fix:** Assert the real state after the overflows and after delivery, e.g. `self.assertIs(False, self.handler._resync_pending)` and `self.mock_controller.resync_model_files.assert_called_once()`. Alternatively, drop the misleading assertion and its comment and point to the coalesce test.

## Info

### IN-01: `_resync_pending` is dead state, and it is cleared before the resync succeeds

**File:** `src/python/web/handler/stream_model.py:48, 88-93`
**Issue:** `_resync_pending` is set to `True` and cleared within the same `get_value()` call, so it is never `True` between calls. It looks like a carried "pending" flag but adds nothing beyond `dropped_count != _last_seen_dropped`. It is also cleared at line 92 *before* `resync_model_files` / `serialize.model` run. If serialization raised after `_discard_backlog` had already cleared the backlog and rebaselined, the snapshot would be lost and no retry would be queued. In practice the exception escapes `__web_stream`, the stream closes, and EventSource reconnects with a fresh `model-init`, so the tab still recovers.
**Fix:** Remove the flag and branch directly on the count delta. Or, if it stays, clear it only after `serialize.model(files)` has produced the value.

### IN-02: The `_drain` loops have no iteration cap, so a regression hangs the suite instead of failing

**File:** `src/python/tests/unittests/test_web/test_handler/test_stream_model_overflow.py:86-98`
**Issue:** `while True: value = self.handler.get_value(); if value is None: break`. If a regression made the gate resync on every call (e.g. the rebaseline is lost), `get_value()` never returns `None` and the test hangs until the CI job times out. It should fail with a clear message instead.
**Fix:** Bound it: `for _ in range(5000): ...` followed by `else: self.fail("get_value() never drained")`.

### IN-03: The rate-limit test's no-leak assertion is close to vacuous

**File:** `src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py:230-238`
**Issue:** `assertNotIn("f1", message)` only rules out file names starting with `f1`. It would not catch a leak of `f2...`, `snap.txt`, or any other model content. The count assertion (2 records over 101 resyncs) is the meaningful part.
**Fix:** Assert the exact message shape, e.g. `assertRegex(message, r"^Model stream resynced after queue overflow: \d+ resyncs, \d+ events dropped total$")`.

### IN-04: The WSGI convergence test stubs `resync_model_files` on an unspecced MagicMock

**File:** `src/python/tests/integration/test_web/test_handler/test_stream_model.py:88-89` (with `tests/integration/test_web/test_web_app.py:21`)
**Issue:** `BaseTestWebApp` builds `self.controller = MagicMock()` without `spec=Controller`. So `self.controller.resync_model_files.side_effect = ...` would keep "working" even if the production method were renamed or its signature changed. The unit suite uses `MagicMock(spec=Controller)` and does catch this, so the risk is limited to this test drifting from the real contract.
**Fix:** Optional: `self.controller.resync_model_files = MagicMock(spec=Controller.resync_model_files, side_effect=...)`, or add `assert hasattr(Controller, "resync_model_files")` at the top of the test.

## Conventions

### CV-01: Import relativity (tool finding, false positive)

**File:** `src/python/web/utils.py:1`
**Deviation:** `py-import-relativity is absolute` (reported by `verify conventions --check`).
**Convention:** `py-import-relativity should be relative`.
**Fix:** None needed. `utils.py` imports only stdlib modules (`logging`, `queue`, `typing`), which cannot be relative, and this phase did not change those lines. Recorded for completeness; advisory only, non-blocking.

---

_Reviewed: 2026-10-27_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_
