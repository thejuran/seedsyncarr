---
phase: 116-import-safety
plan: 03
subsystem: controller (auto-delete)
tags: [python, auto-delete, coverage-guard, terminal-skip, regression, cwe-117]
requires: [116-01, 116-02]
provides:
  - Delete-time duplicate-basename guard in AutoDeleteManager.run_bfs_and_coverage (video files only, case-insensitive)
  - New terminal skip reason "duplicate_basename"
  - _AUTO_DELETE_TERMINAL_SKIPS constant in controller.py
  - REL-01 gate-1 GREEN evidence and validation sign-off
affects: [118]
tech-stack:
  added: []
  patterns:
    - "BFS frontier carries (node, '/'-joined relative path) tuples; paths are identity/display keys, not filesystem paths"
    - "Terminal skip codes live in one frozenset; the controller branches on membership"
key-files:
  created: []
  modified:
    - src/python/controller/auto_delete_manager.py
    - src/python/controller/controller.py
    - .planning/phases/116-import-safety/116-REL01-EVIDENCE.md
    - .planning/phases/116-import-safety/116-VALIDATION.md
decisions:
  - "D-06: duplicate_basename is a terminal skip. Duplicate basenames are a structural property of a settled pack and never clear with time, so re-arming 24 times would only add log noise. A later webhook still re-arms, and the guard runs again on that firing."
  - "Guard log level is WARNING, matching bfs_limit (terminal skips warn; retriable skips log INFO)."
metrics:
  duration: ~35 min (most of it in the full-suite gate)
  completed: 2026-10-08
  tasks: 3
  files: 4
---

# Phase 116 Plan 03: Delete-time duplicate-basename guard Summary

Auto-delete now refuses to remove a pack when two or more distinct video files in it share a basename, compared case-insensitively. Example: `Disc1/movie.mkv` and `Disc2/movie.mkv`. Import coverage is tracked per basename, so one imported `movie.mkv` cannot prove that both copies were imported. The guard runs before `imported_children` is read. That means a legacy pre-1.7.4 record that already reads as "fully covered" cannot bypass it (D-07), and neither can a pack with no per-root entry at all (the D-14 grandfather path). Only video extensions count. Repeated `.srt` and `.nfo` names never block a delete (D-05a). The skip is terminal: one WARNING, no Timer re-arm, the re-arm counter is cleared, and `imported_children[root]` is popped. The pack stays on disk for manual removal. That is the accepted cost under D-04: it uses disk space but never loses media.

## What was built

- **auto_delete_manager.py**
  - The BFS frontier now carries `(child, rel_path)` and seeds it with `(c, c.name)`.
  - Video leaves add `rel_path` to `video_paths[lower_basename]`, next to the existing `on_disk_videos.add`.
  - Node-limit accounting is unchanged, because the BFS visits the same nodes.
  - New guard sits after the `unsafe_child` return and before `imported_children.get(...)`. It collects basenames with more than one path, sorts the paths, sanitizes each one and the root name with `sanitize_log_value`, and caps the list at 5 with `(+N more)`. It then logs:
    `Auto-delete skipped for '<root>': N video basename(s) appear at more than one path in this release (<paths>); per-file import coverage cannot be proven. Local copy left in place for manual removal`
    and returns `(True, "duplicate_basename", None)`.
  - The docstring and the `_AUTO_DELETE_BFS_NODE_LIMIT` comment now list both terminal skips. `full_path` is not used, and there is no second extension allowlist.
- **controller.py**
  - Adds `_AUTO_DELETE_TERMINAL_SKIPS = frozenset({"bfs_limit", "duplicate_basename"})`.
  - `__execute_auto_delete` now branches on `reason in _AUTO_DELETE_TERMINAL_SKIPS` instead of `reason == "bfs_limit"`.
  - The docstring's terminal-skip list now includes duplicate video basenames. `_AUTO_DELETE_DEFER_REASONS` is unchanged.

## Verification (observed)

- Task 1: `test_auto_delete.py` gave `131 passed`. Whole-tree ruff: `All checks passed!`. Greps: the `dupes =` guard is at line 171, before `imported_children.get` at line 197. `full_path` count is 0. `_VIDEO_EXTENSIONS` count is 4, the same as before.
- Task 2: the six-file quick run gave `337 passed, 12 warnings in 1.05s`. Whole-tree ruff: `All checks passed!`. `_AUTO_DELETE_TERMINAL_SKIPS` count is 2. `reason == "bfs_limit"` count is 0.
- Task 3: all 8 targeted RED regressions now pass (`8 passed, 146 deselected`). The PASSED lines are recorded in `116-REL01-EVIDENCE.md`.
- Full host suite, run in two parts (see the note below):
  - All non-baseline files: `1401 passed, 57 warnings in 42.27s`. 0 failed, 0 errors.
  - The four baseline files: `test_sshcp.py` 11 failed; `test_scanner_process.py` 3 failed + 3 errors; `test_system/test_scanner.py` 1 failed; `test_extract_process.py` 6 tests hang, and pytest-timeout would count those as 6 failures.
  - **Total: 21 failed / 3 errors, all in the four pre-existing baseline files. That equals the baseline, with no new failures.**
- Whole-tree ruff (final): `All checks passed!`

**Full-suite hang (reported, not skipped):** `poetry run pytest` on this host resolves to the pipx pytest 9.0.3 at `~/.local/bin/pytest`. That install has no `pytest_timeout`, and the poetry venv has no pytest, so the 60 s per-test timeout in `pyproject.toml` is ignored. The single-command full run hung for more than 10 min on `tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_calls_start_dispatch` (test #631 of 1442). I killed it and split the gate as above. Every `test_extract_process.py` test hangs the same way, so this is pre-existing and unrelated to this plan. No package was installed. CI (`unittests-python` + `lint-python`) remains the authoritative gate.

## Deviations from Plan

None in product code.

Execution notes:
- The worktree started on an older base (`f8c94e9`). It was reset to the required base `bd2e21f` before any work, as the worktree branch check requires.
- The plan's `<verify>` commands point at the main checkout path (`/Users/julianamacbook/seedsyncarr/src/python`). To test this plan's code, every verify ran against the worktree's `src/python` instead.
- Tasks 1 and 2 were committed separately to follow the per-task commit protocol. The plan text named only one combined `feat(116-03)` commit, and that message was used for Task 2.

- One open item for host verification: install `pytest-timeout` into the environment that `poetry run pytest` actually uses. That makes the single-command full run finish (about 76 s according to research) instead of hanging on `test_extract_process.py`. This was not done because package installs are out of scope for an executor.

## Known Stubs

None.

## Threat Flags

None. The new WARNING sanitizes the root and every path (T-116-02). The terminal skip prevents the 24x re-arm log flood, and the path list is capped at 5 (T-116-03). Node-limit accounting is unchanged (T-116-05).

## Self-Check: PASSED

- FOUND: src/python/controller/auto_delete_manager.py, src/python/controller/controller.py, .planning/phases/116-import-safety/116-REL01-EVIDENCE.md, .planning/phases/116-import-safety/116-VALIDATION.md
- FOUND commits: d6abe63 (Task 1), 905746d (Task 2), 3632a58 (Task 3)
