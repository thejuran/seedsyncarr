---
phase: 112-defensive-guards-code-hardening
plan: 01
subsystem: infra
tags: [multiprocessing, spawn, pickling, threading, gitignore, hardening, python]

# Dependency graph
requires:
  - phase: 107-multiprocessing-logger
    provides: "multiprocessing_logger.py __getstate__/__setstate__ pattern used as analog"
provides:
  - "AppProcess.__getstate__/__setstate__ stripping threading.Thread for spawn-safe pickling"
  - ".gitignore entries for .orchestrator.json and .playwright-mcp/"
affects: [all-worker-processes, app-process-subclasses, ci-spawn-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "__getstate__/__setstate__ Thread-stripping pattern for Process subclasses under spawn"
    - "Generic isinstance(v, threading.Thread) sweep — strips subclass threads, retains Queue/Event"

key-files:
  created: []
  modified:
    - "src/python/common/app_process.py"
    - ".gitignore"

key-decisions:
  - "D-02 resolved: __getstate__/__setstate__ on AppProcess is required AND sufficient; get_context('spawn') alone does NOT fix the bug"
  - "D-03: No global set_start_method; fix is purely local to AppProcess pickle state"
  - "RESEARCH Pitfall 1 respected: Queue and Event are NOT stripped — they survive spawn boundary for Process subclasses and are required for propagate_exception()/terminate()"
  - "D-13: .orchestrator.json and .playwright-mcp/ added to AI-tooling block in .gitignore"

patterns-established:
  - "Thread-stripping __getstate__: copy __dict__, pop isinstance(v, threading.Thread) keys, return reduced state — do NOT strip Queue/Event for Process subclasses"

requirements-completed: [GUARD-04, GUARD-05]

# Metrics
duration: 25min
completed: 2026-06-02
---

# Phase 112 Plan 01: GUARD-04/05 Summary

**AppProcess spawn-safe via `__getstate__`/`__setstate__` stripping threading.Thread instances; .orchestrator.json and .playwright-mcp/ git-ignored**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-02T22:25:00Z
- **Completed:** 2026-06-02T22:50:30Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- GUARD-04: `test_process_with_long_running_thread_terminates_properly` (the red test) passes under macOS spawn start method — previously raised `TypeError: cannot pickle '_thread.lock' object`
- GUARD-04: All 9 AppProcess tests pass under both spawn (macOS default) and fork (Linux/CI default) with Queue/Event fully functional across the process boundary
- GUARD-05: `.orchestrator.json` and `.playwright-mcp/` are git-ignored in the AI-tooling block; neither appears as untracked in `git status`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add .gitignore entries for run artifacts (GUARD-05)** - `633ce9b` (chore)
2. **Task 2: Make AppProcess spawn-safe via __getstate__/__setstate__ (GUARD-04)** - `fc604e1` (feat)

## Files Created/Modified

- `src/python/common/app_process.py` — Added `__getstate__` (strips `threading.Thread` instances from pickle state via `isinstance` sweep) and `__setstate__` (restores via `__dict__.update`) to `AppProcess` class; placed after `propagate_exception`, before `run_init`
- `.gitignore` — Added `.orchestrator.json` (bare-filename pattern) and `.playwright-mcp/` (trailing-slash directory) to the "AI tooling (local only)" block after the `.mcp.json` entry

## Decisions Made

- Implemented `__getstate__`/`__setstate__` using the generic `isinstance(v, threading.Thread)` sweep (not hardcoded key names) so any subclass-added Thread is stripped without needing explicit knowledge of the key.
- Explicitly did NOT strip `_AppProcess__exception_queue` or `_terminate` (Queue/Event) per RESEARCH.md Pitfall 1 — these are required for `propagate_exception()` and `terminate()` to work cross-process.
- Did NOT call `set_start_method` anywhere (D-03) — the fix is purely behavioral via pickle state, platform default unchanged.
- Tests ran from the worktree `src/python` directory using the main repo's poetry venv (worktree has separate file; the `pythonpath = ["."]` in pyproject.toml resolves to the worktree's source correctly from that working directory).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Stale .pyc files caused __getstate__ to not be recognized**

- **Found during:** Task 2 verification
- **Issue:** Stale `app_process.cpython-312.pyc` (April 21) was loaded instead of the updated source, causing `AppProcess.__dict__` to not contain the new `__getstate__` method; diagnostic showed `object.__getstate__` being resolved instead of `AppProcess.__getstate__`
- **Fix:** Deleted stale `app_process.cpython-311.pyc` and `app_process.cpython-312.pyc` from `__pycache__`; confirmed tests were run from the worktree's `src/python` directory using the main repo's venv Python directly (not `poetry run` which defaults to main repo CWD)
- **Files modified:** (no source files changed — only stale pyc deleted)
- **Verification:** `AppProcess.__dict__` confirmed to contain `__getstate__`; `isinstance` check confirmed working; all 9 tests pass
- **Committed in:** fc604e1 (Task 2 commit — pyc deletion is not tracked by git)

---

**Total deviations:** 1 auto-fixed (1 blocking — stale pyc / test runner path issue)
**Impact on plan:** Purely a test execution environment issue; no source code change required. The implementation was correct; the diagnostic step just needed to use the worktree's source path.

## Issues Encountered

**Pre-existing coverage below 88%:** The plan's phase-level gate requires `fail_under >= 88`, but the baseline suite (main repo, before this change) was already at 86.85%. After the GUARD-04 fix, coverage is 86.86% — imperceptibly improved but still below threshold. This is a pre-existing condition not caused by this plan. My change turned 1 previously-erroring test green (+1 pass, -1 fail/error in the full suite). The coverage gap predates phase 112 and will need to be addressed by adding tests in other plans (GUARD-01/02/03/06 test additions in plans 112-02/03 are likely to help).

## Known Stubs

None — this plan adds no data-flow stubs or placeholder values.

## Threat Flags

None — both changes reduce attack surface (GUARD-05) or fix correctness (GUARD-04) without introducing new network endpoints, auth paths, or schema changes.

## Self-Check

### Verification commands run

- `git check-ignore .orchestrator.json .playwright-mcp/` — both matched at `.gitignore:27` and `.gitignore:28`
- `git status --short | grep -E '^\?\? \.(orchestrator|playwright-mcp)'` — returned nothing (PASS)
- `"$VENV/bin/pytest" tests/unittests/test_common/test_app_process.py -v` — 9 passed (from worktree)
- Fork parity: `mp.set_start_method('fork', force=True); pytest ...` — 9 passed
- `poetry run ruff check /path/to/worktree/src/python/common/app_process.py` — All checks passed!
- `git diff --stat tests/unittests/test_common/test_app_process.py` — 0 changed lines (test file unmodified)

### Commits exist

- `633ce9b` — chore(112-01): .gitignore GUARD-05
- `fc604e1` — feat(112-01): AppProcess __getstate__/__setstate__ GUARD-04

## Self-Check: PASSED

Both commits exist, both files modified as specified, all acceptance criteria met.

## Next Phase Readiness

- GUARD-04 and GUARD-05 complete; `AppProcess` is now spawn-safe for all existing and future subclasses
- Plans 112-02 and 112-03 (GUARD-01/02/03/06) are unblocked — they touch `seedsyncarr.py` and `delete_process.py` independently
- The pre-existing coverage gap (86.86% vs 88% target) should be addressed by the new tests added in 112-02/03

---
*Phase: 112-defensive-guards-code-hardening*
*Completed: 2026-06-02*
