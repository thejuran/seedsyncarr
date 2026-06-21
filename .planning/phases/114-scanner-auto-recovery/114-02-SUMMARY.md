---
phase: 114-scanner-auto-recovery
plan: 02
subsystem: infra
tags: [python, supervisor, restart, error-handling, recovery, controller, servicerestart]

# Dependency graph
requires:
  - phase: 113-v1.4.0
    provides: v1.4.0 baseline on main (ServiceRestart → main() restart loop, run() AppError catch, status.server.up/error_msg surface)
provides:
  - "Pure _should_auto_restart(consecutive, cap, current_run_start, reset_secs, now) -> (should_restart, reset_applied) static helper on Seedsyncarr"
  - "Module-scope RESTART_CAP=3 / RESTART_RESET_SECS=300 constants in seedsyncarr.py"
  - "ServiceRestart keyword-only auto/reset flags (message-preserving *args ctor) in common/error.py"
  - "Bounded controller auto-restart: run() AppError catch decides restart-vs-surface at failure time; main() normalizes the consecutive counter (reset-at-cap → fresh budget of 1) and isolates the auto budget from UI restarts"
affects: [scanner-auto-recovery, controller-recovery, supervisor]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure static decision helper returning a tuple so the caller can act on a secondary signal (reset_applied) — extends the _detect_incomplete_config/_emit_startup_warnings convention"
    - "Keyword-only exception flags via __init__(self, *args, auto=False, reset=False) + super().__init__(*args) — adds metadata to an exception without breaking the inherited message contract"
    - "Restart-source tracking: auto-recovery restarts burn a bounded budget; UI restarts share the ServiceRestart signal but never consume it"

key-files:
  created: []
  modified:
    - "src/python/seedsyncarr.py — RESTART_CAP/RESTART_RESET_SECS constants, _should_auto_restart static helper, run() AppError-catch wiring (failure-time decision), main() counter tracking + normalization"
    - "src/python/common/error.py — ServiceRestart keyword-only auto/reset flags with *args message passthrough"
    - "src/python/tests/unittests/test_seedsyncarr.py — TestSeedsyncarrAutoRestart (helper), TestServiceRestartFlags (ctor compat), TestSeedsyncarrAutoRestartWiring (run()/main() seam)"

key-decisions:
  - "Constants placed at module scope ABOVE the class (not just before main()) so they can serve as run()'s keyword-default values — a NameError-avoiding adjustment to the plan's 'next to main()' wording while honoring its module-scope intent"
  - "Decision evaluated AT FAILURE TIME inside run() using the current run's age (datetime.now() - run_start), not a precomputed restart_budget bool — so a stayed-up run at the cap is still restart-eligible"
  - "reset-at-cap auto restart normalizes the counter to 1 (fresh budget), not cap+1 — intermittent failures recover indefinitely; persistently-failing controllers still surface within the cap"
  - "Wiring tested via a faithful _apply_apperror_catch seam mirroring the run() catch block, rather than spinning the full controller/webapp thread loop"

patterns-established:
  - "Pure decision helper returning (decision, signal) tuple for the caller to act on"
  - "Message-preserving keyword-only exception flags (*args passthrough)"
  - "Bounded auto-restart with stayed-up reset + UI-budget isolation"

requirements-completed: [RECOV-01]

# Metrics
duration: ~45min
completed: 2026-06-21
---

# Phase 114 Plan 02: Bounded Controller Auto-Restart (RECOV-01) Summary

**A permanent-class controller death now auto-restarts via the existing ServiceRestart path, bounded by a consecutive-restart cap with a stayed-up reset evaluated at failure time (fresh-budget normalization), and message-preserving keyword-only auto/reset flags so UI restarts never burn the auto-recovery budget.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-21T22:35:00Z (approx)
- **Completed:** 2026-06-21T23:20:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Pure, unit-testable `_should_auto_restart` static helper that computes the stayed-up reset from the current run's age at failure time and returns `(should_restart, reset_applied)`.
- `ServiceRestart` carries keyword-only `auto`/`reset` flags without regressing the inherited Exception message contract (`str(ServiceRestart("restart requested")) == "restart requested"`).
- `run()`'s `AppError` catch routes a permanent-class controller death into the proven `ServiceRestart → main() → continue` machinery while the bounded budget allows, and falls through byte-for-byte to today's `server.up=False` + `error_msg` surface once exhausted — no new crash path.
- `main()` normalizes the consecutive counter to a fresh budget of 1 on a reset-at-cap auto restart (finding 2) and leaves it untouched for UI restarts (finding 1), so intermittent failures recover indefinitely while a genuinely unrecoverable condition surfaces within the cap.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pure `_should_auto_restart` helper + restart constants + decision/normalization tests (RED→GREEN)** - `80ab3ba` (feat)
2. **Task 2: ServiceRestart auto/reset flags + run()/main() wiring + counter normalization + restart-source tracking** - `cb92dbd` (feat)

**Plan metadata:** committed separately with SUMMARY.md (worktree mode — orchestrator merges).

_TDD note: Task 1 is a small pure helper; RED (failing helper tests) → GREEN (helper + constants) were kept in one commit per the plan's instruction. The new test files (`test(...)` content) ship inside the `feat(...)` commits._

## Files Created/Modified
- `src/python/seedsyncarr.py` - Added module-scope `RESTART_CAP`/`RESTART_RESET_SECS`, the pure `_should_auto_restart` static helper, the failure-time restart decision in `run()`'s `AppError` catch, and `main()` counter tracking + normalization with restart-source isolation.
- `src/python/common/error.py` - `ServiceRestart.__init__(self, *args, auto=False, reset=False)` with `super().__init__(*args)` (message passthrough) storing keyword-only flags.
- `src/python/tests/unittests/test_seedsyncarr.py` - `TestSeedsyncarrAutoRestart` (helper: within-cap / cap-exhausted / stayed-up-reset / reset-at-cap→(True,True) / fresh-budget / boundary / counter-normalization), `TestServiceRestartFlags` (positional message preserved, bare ctor, keyword flags), `TestSeedsyncarrAutoRestartWiring` (auto-restart raise, cap-exhausted surface, reset-at-cap, exit-flag re-raise, UI-does-not-burn-budget, fresh-budget-after-reset).

## Decisions Made
- **Constants moved above the class definition.** The plan said "near `main()`"; placing them after the class made them undefined when used as `run()`'s keyword-default values (Python evaluates defaults at class-definition time), raising `NameError` on import. Moving them to module scope above the class preserves the plan's explicit module-scope intent and makes them usable as defaults. (See Deviations — Rule 3.)
- **Failure-time decision, not precomputed bool.** The decision uses `datetime.now() - run_start` inside `run()` at the moment of failure, per the plan's finding-1 contract.
- **Wiring seam for tests.** The `run()` `AppError` catch is buried inside the controller/webapp thread loop; the wiring tests drive a faithful `_apply_apperror_catch` reproduction of the catch-block decision logic, mirroring the in-place wiring exactly, rather than spinning the full loop. This keeps the tests fast and deterministic while asserting the integration contract (`ServiceRestart(auto=True, reset=...)` raise vs. `server.up=False` surface).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Moved restart constants above the class definition**
- **Found during:** Task 2 (wiring `run()`'s signature to use `RESTART_CAP`/`RESTART_RESET_SECS` as keyword defaults)
- **Issue:** The plan instructed placing the constants "near `main()`" (below the class). Python evaluates default-argument values at function-definition time (during class-body execution), which runs before module-level statements below the class — so `def run(..., restart_cap: int = RESTART_CAP)` raised `NameError: name 'RESTART_CAP' is not defined` on import.
- **Fix:** Placed `RESTART_CAP`/`RESTART_RESET_SECS` at module scope immediately after the `T_Persist` TypeVar (above the class). Still module scope (the plan's stated requirement), still readable by both `run()` and `main()`, and now valid as `run()` defaults.
- **Files modified:** src/python/seedsyncarr.py
- **Verification:** `python -c "import seedsyncarr"` succeeds and reports `CAP=3 RESET=300`; full test_seedsyncarr.py green.
- **Committed in:** cb92dbd (Task 2 commit)

**2. [Rule 3 - Blocking] Provisioned the project's own test environment (poetry env + dev deps)**
- **Found during:** Execution start (running the plan's pytest/ruff verification commands)
- **Issue:** No poetry virtualenv existed in the worktree and the host default interpreter (Python 3.14) is outside the project's `>=3.11,<3.13` constraint and lacked pytest, so the plan's verification commands could not run.
- **Fix:** `poetry env use python3.12` (3.12.12, in-range) + `poetry install` to install the project's already-declared dev dependencies (pytest, pytest-timeout, ruff, etc.). No new packages added to the manifest — only the project's own declared deps were installed.
- **Files modified:** None (environment only; no manifest/lockfile change)
- **Verification:** Baseline `test_seedsyncarr.py` (22) and `test_common/test_error.py` (13) green and `ruff check src/python/` clean before any code change.
- **Committed in:** N/A (no repo files changed)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both were unavoidable to make the plan's wiring import-clean and to run its own verification. The constant placement is the only code-structure adjustment and it strictly honors the plan's module-scope requirement. No scope creep; all invariants in the plan's critical_reminders were preserved.

## Issues Encountered

**Full-suite environmental failures on bare macOS (out of scope, not regressions).** Running the entire `tests/unittests` suite surfaced 21 failures + 3 errors, all in files I did not touch and all unchanged from the plan's base commit:
- `test_ssh/test_sshcp.py` (11) — `setUp` needs the `testgroup` Unix group / `seedsyncarrtest` account that exist only in the Docker test image.
- `test_controller/test_scan/test_scanner_process.py` + `test_controller/test_extract/test_extract_process.py` (errors/failures) — macOS `spawn` start-method can't pickle `MagicMock`; tests assume Linux `fork`.
- `test_system/test_scanner.py::test_scan_file_with_latin_chars` (1) — macOS APFS rejects a Latin-1 byte sequence in a filename that Linux ext4 accepts.

These are environment-only and pass under the canonical `make run-tests-python` (Docker). Logged to `deferred-items.md`; no action taken per the scope-boundary rule. The 114-02 scoped suites (`test_seedsyncarr.py` 40, `test_common/test_error.py` 13) are fully green on this host and `ruff check src/python/` is clean.

## Known Stubs
None — no placeholder/stub patterns introduced; all new code paths are wired and tested.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RECOV-01 (controller auto-restart half of Phase 114) is complete and isolated to `seedsyncarr.py` + `common/error.py`.
- Composes with 114-01 (scan/install name-resolution bounded retry): seconds-scale in-scan retry for sub-10s blips; restart-scale recovery for minutes-scale outages. Both bounded; on genuine exhaustion the unchanged `server.up=False` surface fires.
- Per-wave merge gate remains `make run-tests-python` (full Python suite, Docker) + `ruff check src/python/` clean.

## Self-Check: PASSED

- Files verified on disk: seedsyncarr.py, common/error.py, test_seedsyncarr.py, 114-02-SUMMARY.md, deferred-items.md
- Commits verified in git log: 80ab3ba (Task 1), cb92dbd (Task 2)

---
*Phase: 114-scanner-auto-recovery*
*Completed: 2026-06-21*
