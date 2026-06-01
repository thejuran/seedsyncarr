---
phase: 108-config-handler-refactors
plan: "02"
subsystem: web/handler
tags: [handler, controller, http, refactor, dedup, dispatch, tdd]

dependency_graph:
  requires: []
  provides:
    - _dispatch_command helper on ControllerHandler (single-action dispatch scaffold)
    - F4 single-action unit test coverage (failure + exact timeout body)
  affects:
    - src/python/web/handler/controller.py
    - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py

tech_stack:
  added: []
  patterns:
    - keyword-only guard parameter (*, guard=False) collapsing five handler scaffolds into one

key_files:
  created: []
  modified:
    - src/python/web/handler/controller.py
    - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py

decisions:
  - D-03: _dispatch_command backs five single-action handlers only; bulk loop stays byte-identical (not routed through helper)
  - F4: new single-action tests written FIRST against un-refactored handler, confirming they pin real behavior before extraction

metrics:
  duration: "~15 min"
  completed: "2026-06-01T22:21:18Z"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 2
  commits: 2
---

# Phase 108 Plan 02: ARCH-03 _dispatch_command Extraction Summary

**One-liner:** Extracted `_dispatch_command(action, file_name, success_msg, *, guard=False)` to collapse five near-identical 15-line handler scaffolds into one-liner delegates, with F4 test backfill proving the previously-uncovered failure path and exact timeout body.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1a (RED) | Backfill single-action failure + exact timeout body tests | b853a18 | test_controller_handler.py |
| 1b (GREEN) | Extract _dispatch_command; thin five handlers | 43ee518 | controller.py |

## What Was Built

### F4 Test Backfill (RED/baseline)

Added to `TestControllerHandlerSingleAction` in `test_controller_handler.py`:

- `test_single_action_timeout_body_is_exact`: asserts `response.body == "Operation timed out"` (exact equality, status 504) — replaces the prior substring-only `assertIn("timed out", ...)` weakness without removing the existing test.
- `test_single_action_failure_returns_callback_error_and_code_404`: asserts exact `callback.error` body (`"File not found"`) and exact `callback.error_code` status (404 — non-default).
- `test_single_action_failure_default_error_code_returns_400`: asserts exact body and 400 default propagation from `on_failure("Internal error")`.
- `test_single_action_guarded_delete_local_success`: pins the `guard=True` success path (delete_local delegate) — `response.body == "Requested local delete for file 'movie.mkv'"`.

All four tests passed against the un-refactored handler before extraction (they pin existing behavior, not speculative behavior).

### _dispatch_command Extraction (GREEN)

Added to `ControllerHandler` in `controller.py`:

```python
def _dispatch_command(
    self,
    action: "Controller.Command.Action",
    file_name: str,
    success_msg: str,
    *,
    guard: bool = False,
) -> HTTPResponse:
```

Execution ordering preserved verbatim (F-note — unquote-before-guard is load-bearing):
1. `file_name = unquote(file_name)` — BEFORE any guard call
2. `if guard: path_guard = self._check_path_safe(file_name); if path_guard: return path_guard`
3. Build `Controller.Command`, attach `WebResponseActionCallback`, call `self.__controller.queue_command(command)`
4. `if not callback.wait(timeout=self._ACTION_TIMEOUT): return HTTPResponse(body="Operation timed out", status=504)`
5. `if callback.success: return HTTPResponse(body=success_msg.format(file_name))`
6. `return HTTPResponse(body=callback.error, status=callback.error_code)`

Five handlers thinned to one-liner delegates:
- `__handle_action_queue` / `__handle_action_stop`: `_dispatch_command(..., guard=False)` (guard omitted — default)
- `__handle_action_extract` / `__handle_action_delete_local` / `__handle_action_delete_remote`: `_dispatch_command(..., guard=True)`

**Unchanged:** `add_routes`, `_ACTION_TIMEOUT`, `_VALID_ACTIONS`, `_GUARDED_ACTIONS`, `_check_path_safe`, `__handle_bulk_command`, `_process_bulk_commands` (D-03 — bulk deferred, byte-identical).

## Acceptance Criteria Verification

- `grep -c "_dispatch_command" controller.py` → **6** (one definition + five delegates) ✓
- `grep -c "def __handle_action_" controller.py` → **5** ✓
- `grep -n "guard=True" controller.py` → lines 125, 134, 143 (extract/delete_local/delete_remote only) ✓
- `unquote(file_name)` at line 92, `if guard:` at line 93 — unquote-before-guard preserved ✓
- `callback.wait` in `_dispatch_command` only (line 101); individual handlers contain no scaffold ✓
- `grep -n "Operation timed out" test_controller_handler.py` shows exact-equality assertion at line 96 ✓
- Bulk `_process_bulk_commands` still contains its own `self._check_path_safe` call and does NOT call `_dispatch_command` ✓
- `git diff` shows no edits to `__handle_bulk_command` or `_process_bulk_commands` ✓

## Test Results

- Unit suite: `56 passed, 3 warnings` (47 original + 5 new single-action + 4 integration)
- Full Python suite: `1339 passed, 62 skipped` — `fail_under >= 88` holds; no test deleted

## TDD Gate Compliance

RED gate: `test(108-02)` commit b853a18 — new tests pass against un-refactored handler (baseline proof)
GREEN gate: `feat(108-02)` commit 43ee518 — all tests pass against refactored handler
No REFACTOR gate commit needed — extracted helper is clean on first pass.

## Deviations from Plan

None — plan executed exactly as written. All five success criteria met, D-03 preserved, F4 backfill landed before extraction.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. `_dispatch_command` does not widen the attack surface — it consolidates existing dispatch logic without changing which actions reach the controller. Threat mitigations T-108-02-01 through T-108-02-05 are all satisfied:
- T-108-02-01 (path traversal regression): `guard=True` on extract/delete_local/delete_remote confirmed; unquote-before-guard ordering preserved; integration traversal tests green.
- T-108-02-02 (guard over-blocking queue/stop): queue/stop delegates pass `guard=False`; success/timeout/error shapes frozen by extended unit suite.
- T-108-02-03 (timeout handling): helper references `self._ACTION_TIMEOUT`; monkeypatch still works; exact 504 body pinned.
- T-108-02-04 (bulk path accidentally routed through helper): `_process_bulk_commands` byte-identical; confirmed by `grep` and `git diff`.
- T-108-02-05 (single-action FAILURE drift — previously uncovered): F4 tests now assert exact `callback.error` body + exact `callback.error_code` status; any future drift fails CI.

## Self-Check: PASSED

- FOUND: src/python/web/handler/controller.py
- FOUND: src/python/tests/unittests/test_web/test_handler/test_controller_handler.py
- FOUND: commit b853a18 (test backfill)
- FOUND: commit 43ee518 (extraction)
- Full suite: 1339 passed, 0 failures
