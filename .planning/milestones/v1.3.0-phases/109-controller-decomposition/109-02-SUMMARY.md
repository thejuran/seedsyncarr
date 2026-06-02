---
phase: 109-controller-decomposition
plan: 02
subsystem: controller
tags: [python, refactor, decomposition, auto-delete, thread-safety, god-class]

requires:
  - phase: 109-01
    provides: controller.py baseline (1058 lines) after CommandProcessor extraction

provides:
  - AutoDeleteManager collaborator in controller/auto_delete_manager.py with BFS pack-guard + coverage-check logic
  - Thinned controller.py delegating BFS/coverage decision to AutoDeleteManager while keeping WR-02 lock harness on Controller
  - AutoDeleteManager export from controller/__init__.py

affects:
  - 109-03 (model_pipeline extraction — controller.py is now ~975 lines, not 1058)

tech-stack:
  added: []
  patterns:
    - "AutoDeleteManager construction-injection pattern: receives already-constructed persist + file_op_manager from Controller.__init__; single-underscore fields only (avoids _AutoDeleteManager__x mangling breaking identity with _Controller__x)"
    - "run_bfs_and_coverage(file, file_name, deletable_states) -> Tuple[bool, str, Optional[Set]]: returns (skip, reason, on_disk_videos); caller holds __model_lock; no lock acquired in collaborator (D-03)"
    - "Logger identity: AutoDeleteManager stores self.logger = logger (not getChild) so log calls route to the same MagicMock the test suite checks via self.controller.logger.info.call_args_list"

key-files:
  created:
    - src/python/controller/auto_delete_manager.py
  modified:
    - src/python/controller/controller.py
    - src/python/controller/__init__.py

key-decisions:
  - "D-01 traceability: auto_delete_manager.py is the wave-2 (thread-safety-critical) collaborator seam"
  - "D-03 traceability: no lock injected or created in AutoDeleteManager; Controller.__execute_auto_delete owns ALL lock acquisition and release"
  - "D-04 traceability: WR-02 ordering preserved verbatim — __model_lock THEN __auto_delete_lock nested; imported_children.pop under __model_lock; exit() takes ONLY __auto_delete_lock; delete_local outside all locks"
  - "D-05 traceability: AutoDeleteManager constructed in Controller.__init__ so patch('controller.controller.X') targets still bind; no manager constructed in collaborator"
  - "D-06 traceability: this is plan 2 of 3 sequential plans; full suite green before 109-03"
  - "Logger routing: self.logger = logger (not logger.getChild) in AutoDeleteManager — MagicMock.getChild() returns a new unrelated MagicMock in tests, breaking self.controller.logger.info assertions"
  - "Return contract: (True, 'bfs_limit', None) signals caller to pop imported_children (terminal skip); other True returns are retriable skips; False return means proceed with delete"

patterns-established:
  - "Single-underscore injected state only in collaborators that share state with Controller (D-03: avoids mangling conflicts)"
  - "Constants that are only used by extracted logic move WITH that logic to the collaborator (no back-reference needed)"
  - "BFS-limit pop stays on Controller inside __model_lock — the collaborator signals the reason via return value; Controller handles the mutation"

requirements-completed: [ARCH-01]

duration: ~30min
completed: 2026-06-02
---

# Phase 109 Plan 02: Controller Decomposition (AutoDeleteManager) Summary

**Extracted the auto-delete BFS pack-guard + coverage-check logic from Controller into a new `AutoDeleteManager` collaborator, thinning controller.py from 1058 to ~975 lines while preserving all WR-02 thread-safety invariants verbatim and keeping the full test suite (1343 unit+integration tests) green without modification.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-06-02T01:45:00Z
- **Completed:** 2026-06-02T02:15:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `src/python/controller/auto_delete_manager.py` (178 lines, well under 350-line ceiling) with `run_bfs_and_coverage(file, file_name, deletable_states)` implementing the BFS traversal, pack guard, coverage guard, and partial-import check
- Moved `_VIDEO_EXTENSIONS` and `_AUTO_DELETE_BFS_NODE_LIMIT` module-level constants from controller.py into auto_delete_manager.py (only used by BFS logic; no test references them by module path)
- Replaced 65+ lines of inline BFS/coverage logic in `__execute_auto_delete` with a single delegation call; the lock harness (`with __model_lock:` → delegation → `with __auto_delete_lock:` → `imported_children.pop`) remains exactly in place on Controller
- `__schedule_auto_delete` and `__execute_auto_delete` both STAY on Controller (grep confirms `count = 2`)
- WR-02 docstring blocks at lines 931-949 (final-commit comment) and exit() lock-ordering docstring at lines 243-254 remain verbatim and unchanged
- Removed now-unused `import os`, `LftpError`, and `LftpJobStatusParserError` imports from controller.py (clean-up after the BFS block and handle methods moved in prior plans)
- Full Docker test suite: **1343 passed, 62 skipped (expected), 0 failed** — `make run-tests-python` exits 0, `fail_under >= 88` satisfied

## Task Commits

1. **Task 1: Create AutoDeleteManager collaborator** - `0f73584` (feat)
2. **Task 2: Wire AutoDeleteManager into Controller** - `5e2b7a3` (feat)

## Files Created/Modified

- `src/python/controller/auto_delete_manager.py` — New collaborator with `run_bfs_and_coverage()`. No Lock construction, no manager construction, no runtime import from controller module (circular import avoided), no `imported_children.pop`, no `delete_local` call. `sanitize_log_value()` guards on all log sites touching `file_name` and `child.name` (CWE-117). Single-underscore injected state only (`self._context`, `self._persist`, `self._file_op_manager`, `self.logger`).
- `src/python/controller/controller.py` — Added `from .auto_delete_manager import AutoDeleteManager` import; removed `import os` and unused lftp imports; removed `_VIDEO_EXTENSIONS` / `_AUTO_DELETE_BFS_NODE_LIMIT` constants; constructed `self.__auto_delete_mgr` in `__init__` after all six manager instances are built (D-05); replaced inline BFS/coverage block with single delegation call inside `with self.__model_lock:`; all WR-02 lock ordering, docstrings, and `imported_children.pop` / `delete_local` positions unchanged.
- `src/python/controller/__init__.py` — Added `from .auto_delete_manager import AutoDeleteManager as AutoDeleteManager` export.

## Decisions Made

- Stored `self.logger = logger` (not `logger.getChild("AutoDeleteManager")`) in AutoDeleteManager. `MagicMock.getChild()` returns a new unrelated MagicMock, so a child logger would be invisible to `self.controller.logger.info.call_args_list` in test assertions. Using the parent logger directly preserves the observable routing the test expects (the log hierarchy is semantically equivalent at production log-sink level).
- BFS-limit case returns `(True, "bfs_limit", None)` signal; Controller handles `imported_children.pop` locally (this is a WR-02 mutation that must stay inside `with self.__model_lock:`). All other skip cases return `(True, "unsafe_child"/"partial_coverage", None)` — retriable, no pop needed.
- Passed `deletable_states` tuple as a parameter to `run_bfs_and_coverage` rather than re-defining it in the collaborator. This avoids any question of whether the collaborator's copy matches the caller's authoritative set, and removes any dependency on `ModelFile.State` enum values being defined in the collaborator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Logger routing via getChild broke test log assertions**
- **Found during:** Task 2 regression gate (1 failure in 102 auto_delete tests)
- **Issue:** `AutoDeleteManager.__init__` used `logger.getChild("AutoDeleteManager")` per the PATTERNS.md convention. In tests, `MagicMock.getChild()` returns a new unrelated MagicMock, so `run_bfs_and_coverage`'s "partial import" log call routed to a MagicMock that `self.controller.logger.info.call_args_list` could not observe — causing `TestAutoDeleteCoverageGuard.test_execute_skips_dir_when_one_video_child_missing` to fail.
- **Fix:** Changed `self.logger = logger.getChild("AutoDeleteManager")` to `self.logger = logger` in `AutoDeleteManager.__init__`. The production log-sink hierarchy is equivalent; only the MagicMock routing in tests differs.
- **Files modified:** `src/python/controller/auto_delete_manager.py`
- **Commit:** `5e2b7a3` (part of Task 2 commit)

**2. [Rule 1 - Bug] Unused imports left by prior and current plan moves**
- **Found during:** Task 2 pre-commit hook (ruff lint)
- **Issue:** After removing the BFS inline block (which used `os.path.splitext`), `import os` became unused. Additionally, `LftpError` and `LftpJobStatusParserError` had already become unused when the `__handle_*_command` methods moved to `CommandProcessor` in 109-01 but were only caught now.
- **Fix:** Removed `import os` and narrowed the lftp import to `from lftp import LftpJobStatus`.
- **Files modified:** `src/python/controller/controller.py`
- **Commit:** `5e2b7a3`

## Known Stubs

None — this is a pure code-structure refactor. No UI rendering paths, no hardcoded values, no placeholder data.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This is a behavior-preserving move-only refactor. The CWE-117 log-injection mitigations (T-109-02-01) travel WITH `run_bfs_and_coverage` — every log call touching `file_name` or `child.name` keeps its `sanitize_log_value()` guard. The WR-02 lock-ordering (T-109-02-02) is preserved verbatim on Controller.

---

## Self-Check

**Created files:**
- `src/python/controller/auto_delete_manager.py` — FOUND (178 lines)
- `.planning/milestones/v1.3.0-phases/109-controller-decomposition/109-02-SUMMARY.md` — this file

**Commits:**
- `0f73584` — FOUND (feat: create AutoDeleteManager collaborator)
- `5e2b7a3` — FOUND (feat: wire AutoDeleteManager into Controller)

**Structural checks:**
- Two dunder lifecycle defs on Controller: `grep -cE 'def __schedule_auto_delete|def __execute_auto_delete' controller/controller.py` → 2
- Delegation present: `grep -c 'self.__auto_delete_mgr.run_bfs_and_coverage' controller/controller.py` → 1
- AutoDeleteManager constructed in controller.py: `grep -c 'AutoDeleteManager(' controller/controller.py` → 1
- No double-underscore instance attrs in collaborator: `grep -nE 'self\.__[a-z]' controller/auto_delete_manager.py` → 0 results (only comment line)
- No Lock/Timer/delete_local/imported_children.pop in collaborator: confirmed
- auto_delete_manager.py line count: 178 <= 350
- WR-02 docstrings intact: confirmed via `grep -n 'WR-02' controller/controller.py`
- Lock count unchanged: 2 Lock() calls in controller.py (__model_lock + __auto_delete_lock)
- Files changed: only src/python/controller/ (confirmed via `git diff --name-only`)
- No test files modified: confirmed

**Regression gate:**
- `make run-tests-python`: 1343 passed, 62 skipped, 0 failed — EXIT 0

## Self-Check: PASSED

*Phase: 109-controller-decomposition*
*Completed: 2026-06-02*
