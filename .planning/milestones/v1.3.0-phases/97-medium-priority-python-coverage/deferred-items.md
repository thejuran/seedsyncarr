# Phase 97 — Deferred / Out-of-Scope Items

## Pre-existing test failures (NOT caused by phase-97 work)

### test_multiprocessing_logger.py — 3 analog tests fail on macOS (spawn start method)

- **Found during:** 97-02 execution (running the existing suite as a baseline).
- **Tests:** `test_main_logger_receives_records`, `test_children_names`, `test_logger_levels`.
- **Symptom:** `AttributeError: Can't get local object 'TestMultiprocessingLogger.<...>.<locals>.process_1'`
  raised by `multiprocessing/reduction.py` when pickling the `Process` target.
- **Root cause:** These tests pass a local-closure function (`process_1`) as a
  `multiprocessing.Process` target. macOS Python 3.12 defaults to the `spawn` start
  method, which pickles the target; local closures are not picklable. On Linux/CI the
  default is `fork`, where local closures work — all 8 tests pass under `fork`
  (verified: `mp.set_start_method('fork', force=True)` → `8 passed`).
- **Scope decision:** Pre-existing, platform-specific, in tests this plan did not author.
  Out of scope per the executor SCOPE BOUNDARY rule. The 5 new 97-02 tests avoid the
  issue entirely by driving records in-process (no child-process spawn).
- **Suggested fix (future):** promote `process_1` to a module-level function (or set
  `fork` explicitly in the test) so the analogs run cross-platform. Not required for
  COVMED-01 closure. Candidate for v1.4.0.
