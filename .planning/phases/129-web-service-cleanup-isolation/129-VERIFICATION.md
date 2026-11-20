---
phase: 129-web-service-cleanup-isolation
verified: 2026-11-20T04:20:31Z
status: human_needed
score: 13/14 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
human_verification:
  - test: "Open the pull request for branch gsd/phase-129-web-service-cleanup-isolation and confirm the Linux CI run is green (full Python test suite, coverage threshold 88, whole-tree ruff)."
    expected: "All CI checks pass, including the five test modules that cannot run on the macOS dev machine (test_extract_process.py, test_scanner_process.py, test_sshcp.py, test_system/test_scanner.py, tests/integration/test_lftp/)."
    why_human: "No pull request exists for this branch yet, so there is no CI result to read. Those five modules hang or fail locally for environment reasons (multiprocessing spawn, no local sshd/lftp), so the plan's 'full unit suite is green' truth cannot be shown in full on this machine. None of them imports the web package, and the phase changed only web/web_app_job.py and its test file, so a phase-caused failure there is not expected."
---

# Phase 129: Web-Service Cleanup Isolation Verification Report

**Phase Goal:** A failure in one web-service shutdown step never skips the remaining steps, matching the per-step isolation already present elsewhere in the lifecycle code
**Verified:** 2026-11-20T04:20:31Z (HEAD 4f50327c)
**Status:** human_needed
**Re-verification:** No (initial verification)

## Summary

The phase goal is achieved in the code. All four roadmap success criteria were checked against the code and by running it, not taken from the SUMMARY files. One plan-level must-have (full unit suite green) is only partly demonstrable on this machine and needs the Linux CI result from the pull request, which does not exist yet. That is the single open item.

Evidence gathered in this verification, independently of the SUMMARY claims:

- Read `src/python/web/web_app_job.py` and its test file in full.
- Ran the phase test file: 25 passed, 4 subtests passed, 2.36 s.
- Reproduced fail-before on the pre-fix code in scratch copies: at 982e4518, 11 failed / 2 passed (including `RuntimeError: app stop failed` escaping `cleanup()`); at 4ad109ec, 7 failed / 14 passed with the 20 s process-exit test left out.
- Confirmed the tests were not weakened after the red commits: the only lines removed from the test file since 982e4518 are two import lines that were replaced by wider imports.
- Ran my own end-to-end check, not part of the phase's tests: a real `WebAppJob` thread with a real paste server and an `app.stop()` that raises. Result below under Behavioral Spot-Checks.
- Ran unit plus integration suites once with the five environment-bound modules excluded: 2064 passed, 62 skipped, 0 failed, 57.30 s.
- `ruff check .` from `src/python`: All checks passed.

## Goal Achievement

### Observable Truths

Roadmap success criteria (the contract):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | With a failure injected into `app.stop()`, `server.stop()` and `thread.join()` still run and the failure is logged; regression test fails before the fix, passes after | VERIFIED | `cleanup()` lines 62-65 wrap `app.stop()` in its own try/except with `logger.exception`. `test_app_stop_failure_still_stops_server_and_joins` passes at HEAD and fails at 982e4518 with `RuntimeError: app stop failed` (reproduced here). End-to-end check: real job thread ended, port closed, one logged error `Error stopping web app during web service cleanup`. |
| SC2 | With a failure injected into `server.stop()` or `thread.join()`, the other steps still run and the failure is logged | VERIFIED | Lines 67-71 and 76-86 are separate try/except blocks. `test_server_stop_failure_still_joins_thread`, `test_join_failure_is_logged_and_cleanup_returns`, `test_all_steps_fail_all_attempted_and_logged` pass at HEAD; all three failed at 982e4518. |
| SC3 | Cleanup handles an uninitialized server and an unstarted thread without raising, and still attempts every applicable step | VERIFIED | `if self.__server is not None` guard (line 67); `thread is not None and thread.is_alive()` guard (line 80). Tests: `test_cleanup_without_setup_does_not_raise`, `test_server_not_created_skips_server_and_join`, `test_thread_not_started_skips_join`, `test_thread_already_finished_skips_join`. Adapter-level partial startup: `stop()` returns quietly when `self.server is None` (lines 160-162) and `run()` then closes instead of serving (lines 131-139); `test_stop_before_run_closes_instead_of_serving`, `test_stop_during_server_construction_closes_instead_of_serving`, `test_real_server_stop_before_start_never_serves`. |
| SC4 | After any failure, cleanup attempts every applicable step and terminates cleanly; tests show clean termination for per-step-failure and partial-startup scenarios | VERIFIED | Join is bounded (`join(timeout=5.0)`, line 81) with a warning if the thread is still alive; server thread and paste workers are daemon. `test_stuck_real_thread_returns_within_bound`, `test_cleanup_returns_within_bound_with_stuck_requests` (real five-worker server, all workers stuck), `test_process_exits_when_web_server_never_stopped` (child process) all pass. No unbounded `.join()` remains in the file (grep count 0). |

Plan must-haves beyond the roadmap criteria:

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5 | 129-01: all three steps raising, all attempted, three failures logged in step order, no raise | VERIFIED | `test_all_steps_fail_all_attempted_and_logged` compares the logged message list to the three literals in order. |
| 6 | 129-01: join bound constant is 5.0 and below 10.0; warning text `Web server did not stop within 5.0 seconds; continuing shutdown` | VERIFIED | Line 26, lines 83-84; `test_stuck_thread_logs_warning_and_returns` pins the text by equality. |
| 7 | 129-01: web-server thread created with `daemon=True` | VERIFIED | Line 50; `test_server_thread_created_as_daemon`. |
| 8 | 129-02: `httpserver.serve` called with `daemon_threads=True` | VERIFIED | Line 126; `test_run_serves_with_daemon_threads`. |
| 9 | 129-02: process with a never-stopped real server exits by itself with return code 0 | VERIFIED | `test_process_exits_when_web_server_never_stopped` passes at HEAD. My end-to-end check also showed no non-daemon threads left after shutdown. |
| 10 | 129-02: real server stops through `stop()` (running flag plus socket close only); thread ends within 3 s; port can be bound again | VERIFIED | Lines 171-172; `server_close()` appears once in non-comment code, inside `run()` only; `.shutdown()` count 0. `test_real_server_stop_frees_port`, `test_stop_after_run_closes_server`. |
| 11 | 129-02: with all five workers stuck, `cleanup()` returns under 1.5 s with a 0.2 s bound, warns once, logs no error, never calls `os._exit` | VERIFIED | `test_cleanup_returns_within_bound_with_stuck_requests` passes at HEAD and failed at 4ad109ec (reproduced here). |
| 12 | 129-02: stop during server construction closes and never serves; stop right after publication ends the loop via flag and socket close | VERIFIED | Both event-barrier tests pass at HEAD; both failed at 4ad109ec. |
| 13 | 129-02 D-07: phase gate on the combined branch (every validation selector selects a passing test, full unit suite green, whole-tree ruff clean) | UNCERTAIN (unverifiable_runtime) | Ruff clean; all 14 selector names exist as tests and pass; 2064 passed with five environment-bound modules excluded. The literal "full unit suite green" needs Linux CI, and no pull request exists for this branch yet. |
| 14 | 129-02 D-08: live restart check recorded as a hand-off to Phase 130; no deploy in this phase | VERIFIED | `.planning/STATE.md` line 150 holds the "Phase 129 D-08" hand-off; `129-VALIDATION.md` Manual-Only table names Phase 130. Not a gap for this phase, by decision D-08. |

**Score:** 13/14 truths verified (4/4 roadmap success criteria)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/python/web/web_app_job.py` | Isolated three-step `cleanup()`, bounded join, daemon thread, lock-guarded stop flag, daemon paste workers | VERIFIED | 172 lines, read in full. Contains `_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS = 5.0`, `daemon=True`, `daemon_threads=True`, `__stop_requested`, `threading.Lock()`. Wired: `seedsyncarr.py` constructs `WebAppJob` (line 177), starts it (197), terminates it (256) and joins it (261); `Job.run` calls `cleanup()` (`common/job.py` line 57). |
| `src/python/tests/unittests/test_web/test_web_app_job.py` | Step-failure, partial-startup, stuck-thread, daemon, adapter race, real-server and process-exit tests | VERIFIED | 660 lines, 25 tests, all collected and passing. Contains `test_app_stop_failure_still_stops_server_and_joins` and `test_process_exits_when_web_server_never_stopped`. Tests drive the public lifecycle; no name-mangled attribute access. |
| `.planning/phases/129-web-service-cleanup-isolation/129-VALIDATION.md` | Filled verification map and sign-off | VERIFIED | `nyquist_compliant: true`, status complete, Phase 130 hand-off row present. Its "22 tests" figure predates the three tests added by the WR-01 fix (file now has 25); cosmetic. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `WebAppJob.cleanup` | `Thread.join` | bounded join guarded by `is_alive()` | WIRED | Lines 80-81 |
| `WebAppJob.setup` | `threading.Thread` | `daemon=True` | WIRED | Lines 44-50 |
| `Job.run` | `WebAppJob.cleanup` | `self.cleanup()` after setup/execute, including a failed setup | WIRED | `common/job.py` lines 33-39 and 56-57 |
| `MyWSGIRefServer.stop` | `MyWSGIRefServer.run` | stop flag and server reference under one lock | WIRED | Lines 128-130, 150-151, 157-159 |
| `MyWSGIRefServer.run` | `paste.httpserver.serve` | `daemon_threads=True` | WIRED | Lines 124-127 |
| `MyWSGIRefServer.stop` | paste server | `running = False` then `socket.close()` | WIRED | Lines 171-172; lock not held across either call |
| `WebAppJob.cleanup` | `MyWSGIRefServer.stop` | step 2 of cleanup | WIRED | Line 69 |

### Data-Flow Trace (Level 4)

Not applicable. The phase changes shutdown control flow; no artifact renders dynamic data.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase test file passes | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -v -p no:cacheprovider` | 25 passed, 4 subtests passed, 2.36 s | PASS |
| SC1 fails before the fix | Same file run against a scratch copy of 982e4518 | 11 failed, 2 passed; `RuntimeError: app stop failed` | PASS (red confirmed) |
| 129-02 tests fail before the fix | Same file run against a scratch copy of 4ad109ec, `-k "not process_exits"` | 7 failed, 14 passed | PASS (red confirmed) |
| Real job thread, real server, `app.stop()` raising (verifier's own script, run through `Job.start()` / `terminate()` / `join()`) | scratch script with `PYTHONPATH=. poetry run python` | job thread ended in 1.00 s; logged `Error stopping web app during web service cleanup`; no warning; `job.exc_info` None; port refused connections afterwards; no non-daemon threads left | PASS |
| Unit plus integration suites, environment-bound modules excluded | `poetry run pytest tests/unittests tests/integration -q -p no:cacheprovider --ignore=...` (five ignores) | 2064 passed, 62 skipped, 0 failed, 57.30 s | PASS |
| Whole-tree lint | `ruff check .` from `src/python` | All checks passed | PASS |

### Probe Execution

The plans declare probes as inline commands, not probe scripts. Each was run here.

| Probe | Result | Status |
|-------|--------|--------|
| Phase test file exits 0 | 25 passed | PASS |
| Non-comment `logger.exception` count in `web_app_job.py` is 3 | 3 | PASS |
| Non-comment `.join()` count is 0 | 0 | PASS |
| Non-comment `.shutdown()` count is 0 | 0 | PASS |
| Non-comment `server_close()` count is 1 (inside `run`) | 1, line 138 | PASS |
| `-k stuck_requests` exits 0 | passed within the file run | PASS |
| `grep -c 'Phase 129 D-08' .planning/STATE.md` at least 1 | 1 | PASS |
| `ruff check src/python/` exits 0 | All checks passed | PASS |
| `poetry run pytest tests/unittests` exits 0 | Not runnable in full on macOS (see human verification) | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WEB-01 | 129-01 | When any one cleanup step (`app.stop`, `server.stop`, `thread.join`) fails, the remaining steps still run and the failure is logged | SATISFIED | Truths SC1, SC2, 5 |
| WEB-02 | 129-01, 129-02 | Cleanup after partial startup completes without raising; after any failure, cleanup attempts every applicable step and terminates cleanly, with tests showing it | SATISFIED | Truths SC3, SC4, 6-12 |

Both IDs named for this phase are claimed by a plan and covered. `REQUIREMENTS.md` maps no other ID to Phase 129, so there are no orphaned requirements.

Bookkeeping note for the orchestrator: `REQUIREMENTS.md` still shows WEB-01 and WEB-02 unchecked (lines 31-32) and "Pending" in the traceability table (lines 71-72). Both summaries say marking was left to the orchestrator.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers in either modified file | - | - |

No stubs, no empty handlers, no bare `except`, no swallowed exception without a log line. The `except (OSError, ValueError)` in `run()` (lines 142-154) re-raises unless a stop was requested and logs at debug level otherwise; `test_socket_error_without_stop_propagates` guards against over-swallowing.

Open code-review items, left open by decision and not goal-blocking:

| Item | What it means | Severity |
|------|---------------|----------|
| IN-02 | A stop that arrives before startup still briefly binds the port and builds the worker pool before closing | Info |
| IN-03 | Debug line "stop deferred to startup" can mislead when the server had already failed to start | Info |
| IN-04 | One redundant assertion; one test assumes a just-released ephemeral port stays unused | Info |
| SA-01, SA-02 | Pre-existing behaviour (paste force-kills hung workers; a port-bind failure at startup leaves the job running without a web UI). Product decisions, outside this phase's scope | Info |

### Human Verification Required

### 1. Linux CI green on the pull request

**Test:** Open the pull request for `gsd/phase-129-web-service-cleanup-isolation` and read the CI result.
**Expected:** All checks pass: full Python test suite, coverage threshold 88, whole-tree ruff.
**Why human:** No pull request exists for this branch yet. Five test modules cannot run on this macOS machine for environment reasons, so the full-suite and coverage gates can only be confirmed by CI. None of those modules imports the web package, and the phase changed only `web/web_app_job.py` and its test file.

Not counted here, by decision D-08: the live NAS restart check belongs to Phase 130's release-image smoke test.

### Gaps Summary

No gaps. The goal and all four roadmap success criteria are verified in the code and by execution. The one unresolved must-have is a gate that depends on Linux CI, which has not run because the pull request has not been opened.

---

_Verified: 2026-11-20T04:20:31Z_
_Verifier: Claude (bm-verifier)_
