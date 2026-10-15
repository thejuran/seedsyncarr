---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 07
subsystem: model / controller / web-serialize
tags: [hold-visibility, model, sse, serialize, imp-02, lifecycle-reset, regression-red-first]
requires:
  - "119-04: CompletionGate.holds / CompletionGate.invalidate (drop + fence)"
  - "119-05: Controller._discard_pending_notices (pending notices + lifecycle generation)"
  - "119-06: Controller owns self.__completion_gate; test base patches CompletionGate"
provides:
  - "ModelFile.hold_reason: Optional[str] (frozen-checked, part of __eq__, not persisted)"
  - "ModelBuilder.set_hold_reasons(Mapping[str,str]): change-detected; applied only to DEFAULT roots"
  - "ModelPipeline(completion_gate=..., on_lifecycle_reset=...) + _notify_lifecycle_reset"
  - "Controller._on_root_lifecycle_reset(name, cause): gate invalidate + pending-notice discard"
  - "SSE file JSON key \"hold_reason\" (one of the five reason codes, or null)"
affects: [119-08]
tech-stack:
  added: []
  patterns:
    - "per-cycle level-triggered sync of gate holds into the builder (mirrors set_submitted_files)"
    - "single owner callback for per-root lifecycle resets, invoked under the model lock, lock-free inside"
key-files:
  created: []
  modified:
    - src/python/model/file.py
    - src/python/controller/model_builder.py
    - src/python/controller/model_pipeline.py
    - src/python/controller/controller.py
    - src/python/web/serialize/serialize_model.py
    - src/python/tests/unittests/test_model/test_file.py
    - src/python/tests/unittests/test_controller/test_model_builder.py
    - src/python/tests/unittests/test_controller/test_controller_unit.py
    - src/python/tests/unittests/test_web/test_serialize/test_serialize_model.py
decisions:
  - "hold_reason is a root-only attribute; children always serialize null"
  - "Lifecycle resets go through one Controller callback; the pipeline never calls the gate directly"
metrics:
  duration: "~25 min"
  completed: 2026-10-15
  tasks: 2
  files: 9
---

# Phase 119 Plan 07: Hold visibility through the model/SSE pipeline Summary

When the completion gate holds an automatic transfer, the root now carries its reason code (`hold_reason`). The code travels through the ModelBuilder, the model diff and the SSE JSON. The root keeps the code only while its built state is DEFAULT, and a change to the reason produces a model diff. The same-name re-grab reset and the removal of a root now both run one controller callback. That callback fences the gate's cached proof and discards the root's pending import notices.

## What changed

**Task 1: model attribute and builder setter** (`907ada9` RED, `8f126a4` GREEN)
- `ModelFile.hold_reason`: `None` by default. The setter accepts only `str` or `None` (anything else raises `TypeError`) and refuses to change a frozen file. The new private field joins `__eq__` automatically, so a new reason or a cleared hold produces an UPDATED diff.
- `ModelBuilder.set_hold_reasons(Mapping)`: copies the input and drops the cached model only when the mapping changes. `clear()` resets it. In `build_model`, the reason is applied after `_determine_final_state` and only when the root's state is `DEFAULT`, so a QUEUED, DOWNLOADING or DOWNLOADED root never carries a reason. Reasons for names not in the model are ignored, and children are never tagged.

**Task 2: pipeline feed, lifecycle callback, serializer** (`e28a0a0` RED, `a17e680` GREEN)
- `ModelPipeline` takes two new optional arguments, `completion_gate` and `on_lifecycle_reset`. Every cycle, `feed_model_builder` calls `set_hold_reasons(self._completion_gate.holds)` right after `set_submitted_files`.
- `_notify_lifecycle_reset(name, cause)` is called in two places:
  - the "New lifecycle detected" branch of `_prune_downloaded_files`, with cause `"new lifecycle after long absence"`
  - the `REMOVED` branch of `apply_model_diff`, with cause `"root removed from model"`

  When no callback is set, it only writes a DEBUG log.
- `Controller._on_root_lifecycle_reset(name, cause)` calls `self.__completion_gate.invalidate(name, cause)` and then `self._discard_pending_notices(name, cause)`. It runs with `__model_lock` already held and does not acquire that lock itself. A test checks this by calling it from another thread while the test holds the lock, with a 2 s join timeout.
- Controller passes `completion_gate=self.__completion_gate` and `on_lifecycle_reset=self._on_root_lifecycle_reset` to `ModelPipeline`.
- `SerializeModel` writes `"hold_reason"` next to `import_status`, for roots and children alike.

## Verification (observed)

- Task 1 RED: 10 failed, 76 passed. The equality test passed even before the change, because assigning an undeclared attribute also lands in `__dict__`. It is kept as a regression guard. GREEN: **86 passed**. `ruff check .`: All checks passed.
- Task 2 RED: 7 failed, 175 passed. The 3 tests for a pipeline built without a callback pass before and after the change and serve as regression guards. GREEN (serialize + controller_unit + model_builder): **244 passed**. `ruff check .`: All checks passed.
- Acceptance greps:
  - `set_hold_reasons(self._completion_gate.holds)` = 1
  - `_notify_lifecycle_reset(` (non-comment lines) = 3
  - `_completion_gate.invalidate(` in the pipeline = 0
  - `completion_gate=self.__completion_gate` in the controller = 2
  - `on_lifecycle_reset=self._on_root_lifecycle_reset` = 1
  - `"hold_reason"` in the serializer = 1
- **Full unit suite**, with the 4 conventional `--ignore`s: **1674 passed, 19 subtests passed, 0 failed**. That is 119-06's 1651 plus the 23 new tests.
- Whole `tests/` tree, including integration: 1724 passed, 62 skipped, **40 errors**. All 40 are in `tests/integration/test_lftp/` and fail with `KeyError: getgrnam(): name not found: 'testgroup'`. These fixtures need a local `testgroup` OS group that this host lacks. The errors come from the environment, are unrelated to this plan, and are not counted as failures.

## Deviations from Plan

**1. [Rule 1 - Test bug] The serializer test insertion split `test_full_path`**
- **Found during:** Task 2 GREEN.
- **Issue:** The `test_hold_reason` method was inserted inside `test_full_path`, which still had two assertions after the anchor line. Those assertions ended up in the new test and raised `IndexError`.
- **Fix:** Moved the two `full_path` assertions back into `test_full_path`. Fixed before the GREEN commit (`a17e680`).

**2. [Rule 1 - Test robustness] The lock-safety test runs the callback in a thread with a timeout**
- `__model_lock` is a plain `Lock`. If a future change made the callback acquire it, a direct call from inside `with lock:` would hang the test suite instead of failing it. The test now runs the callback in a daemon thread and fails if `join(timeout=2)` leaves the thread alive.

Worktree setup: the worktree started at `f6ff78a` (v1.7.4 merge). Per the branch-check instructions, I reset it to the expected base `5dae83d` before starting any work.

## TDD Gate Compliance

`test(119-07)` RED commits (`907ada9`, `e28a0a0`) come before their `feat(119-07)` GREEN commits (`8f126a4`, `a17e680`).

## Known Stubs

None.

## Threat Flags

None. `hold_reason` carries only the gate's fixed reason codes (T-119-26). It is applied only to DEFAULT roots (T-119-27). Both lifecycle reset paths go through the single callback (T-119-52).

## Self-Check: PASSED

- All 9 modified files exist. Commits 907ada9, 8f126a4, e28a0a0 and a17e680 are present in `git log`.
