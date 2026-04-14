---
phase: 42-crash-prevention
plan: 01
subsystem: backend
tags: [python, exception-handling, queue, eta, crash-fix]

# Dependency graph
requires: []
provides:
  - Fixed propagate_exception: removes redundant outer raise so re_raise() controls traceback (CRASH-01)
  - Fixed WebhookManager.process: catches queue.Empty specifically instead of bare except (CRASH-03)
  - Fixed _estimate_root_eta: guards against None remote_size before arithmetic (CRASH-02)
affects: [app-process, webhook-manager, model-builder]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bare except replaced with specific exception type (queue.Empty) to avoid masking real bugs"
    - "None guard on all operands before arithmetic in estimation methods"

key-files:
  created: []
  modified:
    - src/python/common/app_process.py
    - src/python/controller/webhook_manager.py
    - src/python/controller/model_builder.py
    - src/python/tests/unittests/test_common/test_app_process.py
    - src/python/tests/unittests/test_controller/test_model_builder.py

key-decisions:
  - "exc.re_raise() already raises internally — outer raise was redundant and could mask traceback if re_raise() ever returned None"
  - "WebhookManager bare except masked SystemExit/KeyboardInterrupt/programming errors; except Empty is the correct specific exception"
  - "remote_size None guard placed after transferred_size guard, matching the existing guard pattern in _estimate_root_eta"

patterns-established:
  - "Specific except clauses over bare except for TOCTOU race patterns in queue draining"

requirements-completed: [CRASH-01, CRASH-02, CRASH-03]

# Metrics
duration: 15min
completed: 2026-02-23
---

# Phase 42 Plan 01: Crash Prevention Summary

**Three reachable Python crash paths eliminated: redundant raise in propagate_exception, TypeError from None remote_size in ETA estimation, and bare except masking real exceptions in WebhookManager queue drain**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-23T00:00:00Z
- **Completed:** 2026-02-23T00:15:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- CRASH-01: Removed redundant `raise exc.re_raise()` — `re_raise()` raises itself internally; outer raise was confusing and potentially dangerous
- CRASH-02: Added None guard for `remote_size` in `_estimate_root_eta` before the subtraction on line 458 — prevents TypeError when remote scanner hasn't returned size yet
- CRASH-03: Changed bare `except:` in `WebhookManager.process` to `except Empty:` — bare except masks SystemExit, KeyboardInterrupt, and programming bugs
- Added `test_exception_propagates_with_traceback` to verify traceback originates in `run_loop`
- Added `test_build_estimated_eta_remote_size_none` to verify no TypeError when remote_size is None while file is DOWNLOADING

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix propagate_exception redundant raise and WebhookManager bare except** - `5210436` (fix)
2. **Task 2: Guard _estimate_root_eta against None remote_size** - `d2e4bef` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/python/common/app_process.py` - Removed redundant outer `raise` from `propagate_exception` (CRASH-01)
- `src/python/controller/webhook_manager.py` - Added `Empty` import; replaced bare `except:` with `except Empty:` (CRASH-03)
- `src/python/controller/model_builder.py` - Added `if model_file.remote_size is None: return` guard in `_estimate_root_eta` (CRASH-02)
- `src/python/tests/unittests/test_common/test_app_process.py` - Added `test_exception_propagates_with_traceback`
- `src/python/tests/unittests/test_controller/test_model_builder.py` - Added `test_build_estimated_eta_remote_size_none`

## Decisions Made
- `exc.re_raise()` already raises (calls `raise self.ee.with_traceback(self.tb)`) — the outer `raise` was unreachable on success and would produce `raise None` (TypeError) if `re_raise()` returned unexpectedly. Removed to make control flow explicit.
- `remote_size` None guard placed immediately after the existing `transferred_size` None guard, maintaining the guard-then-compute pattern already in use in `_estimate_root_eta`.
- `Empty` imported alongside `Queue` from the `queue` module — minimal change, no import reorganization needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `test_process_with_long_running_thread_terminates_properly` is a pre-existing failure on macOS (spawn context cannot pickle `_thread.lock`). Confirmed failing before our changes, out of scope per deviation rules. Logged to deferred-items.

## Next Phase Readiness
- All three crash bugs fixed with tests
- Ready for 42-02 and 42-03 plans (already committed separately)

---
*Phase: 42-crash-prevention*
*Completed: 2026-02-23*

## Self-Check: PASSED

- src/python/common/app_process.py: FOUND
- src/python/controller/webhook_manager.py: FOUND
- src/python/controller/model_builder.py: FOUND
- 42-01-SUMMARY.md: FOUND
- Task 1 commit 5210436: FOUND
- Task 2 commit d2e4bef: FOUND
