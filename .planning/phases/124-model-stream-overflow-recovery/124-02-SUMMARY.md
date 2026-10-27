---
phase: 124-model-stream-overflow-recovery
plan: 02
subsystem: api
tags: [tdd, strm-02, stream-queue, model-lock, atomic-resync]

# Dependency graph
requires:
  - phase: 124-01
    provides: Recorded STRM-01 reproduction and the "proceed to STRM-02 fix" verdict
provides:
  - "StreamQueue.clear() -- discards a listener's backlog without touching dropped_count"
  - "Controller.resync_model_files(discard_backlog) -- runs a caller-supplied callback and takes the model snapshot inside one __model_lock acquisition (D-03)"
  - "D-05 bounded-buffering proof at the queue level (5000 puts into maxsize=1000 never exceeds maxsize)"
affects: [124-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lock-bridge method: Controller.resync_model_files takes a Callable[[], None], not a web-layer type, so controller/ keeps zero imports from web/"

key-files:
  created: []
  modified:
    - src/python/web/utils.py
    - src/python/controller/controller.py
    - src/python/tests/unittests/test_web/test_stream_queue.py
    - src/python/tests/unittests/test_controller/test_controller_unit.py

key-decisions:
  - "StreamQueue.put() left unchanged; the DEFER-STREAMQUEUE producer-side lock is not folded in (D-05) -- put()/clear() for the model stream are already serialized by __model_lock, since every model mutation that notifies listeners runs inside it"
  - "resync_model_files is typed Callable[[], None], not WebResponseModelListener/StreamQueue, preserving controller/ having zero imports from web/"

patterns-established:
  - "Controller.resync_model_files(discard_backlog): with self.__model_lock: discard_backlog(); return self.__get_model_files() -- the same atomic-snapshot shape as get_model_files_and_add_listener, swapping add_listener for an injected no-arg callback"

requirements-completed: [STRM-02]

# Metrics
duration: ~30min
completed: 2026-10-27
---

# Phase 124 Plan 02: StreamQueue.clear() and Controller.resync_model_files Summary

**Built and proved the two primitives STRM-02's fix needs -- `StreamQueue.clear()` and `Controller.resync_model_files(discard_backlog)` -- with RED-then-GREEN tests proving D-03 atomicity (real lock, real thread) and D-05 bounded buffering; no user-visible behavior change yet (that lands in 124-03).**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-10-27T10:10:00Z (approx.)
- **Completed:** 2026-10-27T10:37:13Z
- **Tasks:** 2 completed
- **Files modified:** 4 (2 production, 2 test)

## Accomplishments
- `StreamQueue.clear()` added to `src/python/web/utils.py`, using the same non-blocking `get(block=False)`/`except Empty` idiom as `get_next_event()`; `dropped_count` is untouched and `put()` was not modified.
- `Controller.resync_model_files(discard_backlog)` added to `src/python/controller/controller.py` directly after `get_model_files_and_add_listener`, running the caller's callback and taking the model snapshot inside one `__model_lock` acquisition. No try/except -- the `with` block releases the lock on every path, including when `discard_backlog` raises.
- Proved D-03 atomicity with real-lock, real-thread tests: a concurrent `resync_model_files` call blocks while `__model_lock` is externally held and completes (reflecting every mutation made before release, none made after) once it is released; a real `WebResponseModelListener`'s backlog is discarded by the resync and a file added immediately afterward produces exactly one new queued event.
- Proved D-05 bounded buffering at the queue level: 5000 `put()` calls into a `maxsize=1000` queue never push `get_queue_size()` above `get_maxsize()`, checked after every put.
- Confirmed `controller/` still has zero imports from `web/` (`grep -rnE "^(from|import) web" src/python/controller/` prints nothing).

## Task Commits

Each task was committed atomically:

1. **Task 1: RED tests for clear(), bounded stall, and resync_model_files atomicity** - `8be4c21` (test)
2. **Task 2: GREEN implement StreamQueue.clear() and Controller.resync_model_files** - `d638cd9` (feat)

**Plan metadata:** this SUMMARY.md commit (below)

## Files Created/Modified
- `src/python/web/utils.py` - added `StreamQueue.clear()`
- `src/python/controller/controller.py` - added `Controller.resync_model_files(discard_backlog)`
- `src/python/tests/unittests/test_web/test_stream_queue.py` - `test_clear_discards_backlog`, `test_clear_does_not_affect_dropped_count`, `test_clear_on_empty_queue`, `test_put_after_clear`, `test_queue_never_exceeds_maxsize_under_sustained_stall` (D-05)
- `src/python/tests/unittests/test_controller/test_controller_unit.py` - `TestResyncModelFiles` (6 tests covering D-03 atomicity, the real-listener discard+later-event case, listener-list non-mutation, and exception propagation/lock release)

## RED Results

Precondition checked first: `124-01-SUMMARY.md`'s verdict line reads "no existing recovery guarantee for the model stream; proceed to STRM-02 fix (124-02, 124-03)" -- proceeded as planned.

Mutation-under-lock premise (D-03's foundation), confirmed via:
```
grep -rn "\.add_file(\|\.remove_file(\|\.update_file(" src/python/controller/model_pipeline.py src/python/controller/controller.py
src/python/controller/model_pipeline.py:160:            model.update_file(new_file)
src/python/controller/model_pipeline.py:364:                self._model.add_file(diff.new_file)
src/python/controller/model_pipeline.py:366:                self._model.remove_file(diff.old_file.name)
src/python/controller/model_pipeline.py:369:                self._model.update_file(diff.new_file)
```
All three calls live inside `ModelPipeline.apply_model_diff`, whose docstring states "Must be called holding the model lock." Its sole caller, `build_and_apply_model`, wraps the diff+apply in `with self._model_lock:` (`model_pipeline.py:399-404`), and that docstring states explicitly: "All model mutations are performed while holding self._model_lock -- the SAME Lock object as Controller.__model_lock (D-03, single-underscore storage)." Every Controller-model mutation site therefore runs under `__model_lock` -- the premise `resync_model_files`'s atomicity guarantee depends on.

RED pytest run (before any production edit):
```
cd src/python && poetry run pytest tests/unittests/test_web/test_stream_queue.py tests/unittests/test_controller/test_controller_unit.py -k "clear or Resync" -q
...
FAILED tests/unittests/test_web/test_stream_queue.py::TestStreamQueue::test_clear_discards_backlog
FAILED tests/unittests/test_web/test_stream_queue.py::TestStreamQueue::test_clear_does_not_affect_dropped_count
FAILED tests/unittests/test_web/test_stream_queue.py::TestStreamQueue::test_clear_on_empty_queue
FAILED tests/unittests/test_web/test_stream_queue.py::TestStreamQueue::test_put_after_clear
FAILED tests/unittests/test_controller/test_controller_unit.py::TestResyncModelFiles::test_discard_exception_propagates_and_releases_lock
FAILED tests/unittests/test_controller/test_controller_unit.py::TestResyncModelFiles::test_discard_runs_while_model_lock_held
FAILED tests/unittests/test_controller/test_controller_unit.py::TestResyncModelFiles::test_resync_blocks_until_model_lock_released
FAILED tests/unittests/test_controller/test_controller_unit.py::TestResyncModelFiles::test_resync_calls_discard_and_returns_current_files
FAILED tests/unittests/test_controller/test_controller_unit.py::TestResyncModelFiles::test_resync_does_not_change_listeners
FAILED tests/unittests/test_controller/test_controller_unit.py::TestResyncModelFiles::test_resync_with_real_listener_discards_backlog_and_keeps_later_events
10 failed, 3 passed, 172 deselected, 3 warnings in 0.36s
```
Exit code was exactly `1`. Every failure was `AttributeError: 'StreamQueue' object has no attribute 'clear'` or `AttributeError: 'Controller' object has no attribute 'resync_model_files'` -- no `ERROR`, `ImportError`, `ModuleNotFoundError`, `NameError`, or `SyntaxError` lines. `test_queue_never_exceeds_maxsize_under_sustained_stall` was run separately and passed as expected (the existing bound already holds):
```
poetry run pytest tests/unittests/test_web/test_stream_queue.py -k sustained_stall -q
1 passed, 14 deselected, 2 warnings in 0.09s
```
`git log --oneline -2` after the RED commit showed `test(124-02): add failing tests...` as the latest commit, strictly before any edit to `web/utils.py` or `controller.py`.

## DEFER-STREAMQUEUE Decision

Per the plan and D-05: `StreamQueue.put()` was **not** touched. `clear()` and `put()` for the model stream are already mutually serialized by `__model_lock` in practice -- every model mutation (`add_file`/`remove_file`/`update_file`) that calls `listener.file_added/removed/updated` (which calls `put()`) runs inside `__model_lock` (see RED Results above), and `resync_model_files` calls `clear()` inside that same lock. No additional lock inside `StreamQueue` itself is needed for this phase's correctness; the pre-existing `DEFER-STREAMQUEUE` producer-side non-atomicity (concurrent `put()` calls from multiple unrelated producers, unrelated to this resync path) remains out of scope, as planned.

## GREEN Verification

```
cd src/python && poetry run pytest tests/unittests/test_web/test_stream_queue.py tests/unittests/test_controller/ -q \
  --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py \
  --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py
972 passed, 37 warnings, 19 subtests passed in 37.90s
```
Full local suite (excluding local-environment-only exclusions, see below):
```
poetry run pytest --cov --cov-report=term-missing -q \
  --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py \
  --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py \
  --ignore=tests/unittests/test_ssh/test_sshcp.py \
  --ignore=tests/integration \
  --deselect=tests/unittests/test_system/test_scanner.py::TestSystemScanner::test_scan_file_with_latin_chars
Required test coverage of 88.0% reached. Total coverage: 89.97%
1863 passed, 1 deselected, 1 warning, 77 subtests passed in 55.77s
```
Whole-tree ruff:
```
ruff check src/python/
All checks passed!
```
No-web-import guard:
```
grep -rnE "^(from|import) web" src/python/controller/
(no output)
```
Acceptance-criteria greps:
```
grep -c "def resync_model_files(self, discard_backlog: Callable\[\[\], None\]) -> List\[ModelFile\]:" src/python/controller/controller.py  -> 1
grep -c "def clear(self) -> None" src/python/web/utils.py  -> 1
git diff HEAD~1 -- src/python/web/utils.py | grep -A5 "def put"  -> (no output; put() unchanged)
```

### Local-environment exclusions (NOT claimed passing)

Two categories of pre-existing, macOS-host-only failures were excluded from the local full-suite run above -- neither touches any file this plan modified, and both are infrastructure/platform gaps, not regressions from this change:

1. **Known multiprocessing hang** (per the executor's known-issue note): `tests/unittests/test_controller/test_extract/test_extract_process.py` and `tests/unittests/test_controller/test_scan/test_scanner_process.py` hang on this macOS host (confirmed: a bounded `timeout 90` run reproduced the exact same hang point at ~64% progress, exit 124). These pass in Docker (`make run-tests-python`) per the executor's baseline note; not rerun in Docker in this plan (no production code in scope touches scanning/extraction).
2. **Newly observed, same class of gap (macOS host, no Docker fixtures)**: all 11 tests in `tests/unittests/test_ssh/test_sshcp.py` and 1 test in `tests/unittests/test_system/test_scanner.py` (`test_scan_file_with_latin_chars`) fail locally -- the former with `KeyError: "getgrnam(): name not found: 'testgroup'"` (a Unix group created only inside the Docker test container, per `docker/test/python/compose.yml`), the latter with `OSError: [Errno 92] Illegal byte sequence` (APFS rejects the Latin-1 byte sequence the test constructs; this is Linux-container-only filesystem behavior). `tests/integration/` was also excluded wholesale for the same "requires the Docker test container" reason (confirmed via `Makefile`'s `run-tests-python`/`tests-python` targets, which build and run inside `docker/test/python/compose.yml`). None of these files were read or modified by this plan; they are unrelated to `StreamQueue`/`Controller`/model-stream code.

These exclusions are recorded here, not claimed as passing, per the executor's instruction to never chase or claim results for this known local-environment gap. The targeted and CI-faithful (whole-tree ruff, no-web-import) checks above are unaffected by this exclusion.

## Decisions Made
- See `key-decisions` in frontmatter: `StreamQueue.put()` left unchanged (DEFER-STREAMQUEUE); `resync_model_files` typed `Callable[[], None]` to preserve the `controller/` -> `web/` import direction.
- `test_resync_with_real_listener_discards_backlog_and_keeps_later_events` imports `WebResponseModelListener` from `web.handler.stream_model` inside the test body only (test code may import `web`; production `controller.py` may not) -- matches the plan's explicit instruction.

## Deviations from Plan

None - plan executed exactly as written. One environment-setup action was required but is not a plan deviation: `poetry install` (full, not `--no-root`) was run once in this fresh worktree virtualenv to install the `pytest-cov` dev dependency, which was missing (same class of fresh-worktree setup gap as 124-01's "Issues Encountered" note).

## Issues Encountered
- This worktree's Poetry virtualenv was missing `pytest-cov` (a dev-group dependency) even after the `--no-root` install noted in 124-01; running a full `poetry install` resolved it. Not a plan deviation -- worktree environment setup, consistent with 124-01's prior note about this fresh virtualenv.
- The local full-suite coverage/ruff gates surfaced two categories of pre-existing macOS-host-only failures unrelated to this plan's files (see "Local-environment exclusions" above); documented, not fixed (out of scope — Rule-1 scope boundary: these files were not touched by this plan).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `StreamQueue.clear()` and `Controller.resync_model_files(discard_backlog)` exist, are covered by RED-then-GREEN tests, and satisfy D-03 (atomic) and D-05 (bounded) at the primitive level.
- 124-03 is unblocked: it can wire `ModelStreamHandler.get_value()` to detect a drop via `get_dropped_count()` delta and call `self.controller.resync_model_files(self.model_listener.clear)` to emit a fresh `model-init` resync, per RESEARCH.md's Code Examples.
- No user-visible behavior change in this plan -- STRM-02 is not yet closed; that requires 124-03's wiring.
- No blockers.

## Self-Check: PASSED

All modified files confirmed present on disk:
- `src/python/web/utils.py` - FOUND (contains `def clear(self) -> None`)
- `src/python/controller/controller.py` - FOUND (contains `def resync_model_files`)
- `src/python/tests/unittests/test_web/test_stream_queue.py` - FOUND
- `src/python/tests/unittests/test_controller/test_controller_unit.py` - FOUND

Both task commits confirmed present in `git log`:
- `8be4c21` - test(124-02): add failing tests for StreamQueue.clear and atomic resync_model_files - FOUND
- `d638cd9` - feat(124-02): add StreamQueue.clear and atomic Controller.resync_model_files (STRM-02 D-03) - FOUND

RED strictly before GREEN confirmed: `8be4c21` committed before `d638cd9` in `git log` order.

---
*Phase: 124-model-stream-overflow-recovery*
*Completed: 2026-10-27*
