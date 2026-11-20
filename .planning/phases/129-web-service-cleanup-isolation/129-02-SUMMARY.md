---
phase: 129-web-service-cleanup-isolation
plan: 02
subsystem: web
tags: [shutdown, threading, paste, tdd]
requires:
  - "129-01 (WebAppJob.cleanup isolated steps, bounded join, daemon server thread)"
provides:
  - "MyWSGIRefServer.stop(): immediate, safe before, during and after startup"
  - "paste pool workers started as daemon threads (daemon_threads=True)"
  - "Filled 129-VALIDATION.md (nyquist_compliant: true)"
affects:
  - "Phase 130 release-image smoke test (D-08 live restart hand-off)"
tech-stack:
  added: []
  patterns:
    - "lock-guarded flag + snapshot-under-lock, act-outside-lock (file_operation_manager style)"
key-files:
  created: []
  modified:
    - src/python/web/web_app_job.py
    - src/python/tests/unittests/test_web/test_web_app_job.py
    - .planning/phases/129-web-service-cleanup-isolation/129-VALIDATION.md
decisions:
  - "stop() only sets paste's running flag and closes the listening socket; paste's own serve loop drains the worker pool on the server thread"
  - "server_close() is called only in run() when a stop arrived during startup (idle workers, server thread)"
metrics:
  duration: "~25 min"
  completed: 2026-11-19
  tasks: 3
  files: 3
---

# Phase 129 Plan 02: Race-free, Exit-safe Web Server Adapter Summary

`MyWSGIRefServer.stop()` now returns immediately (clears paste's running flag and closes the listening socket, never runs paste's pool teardown on the job thread), a lock-guarded stop-requested flag makes a stop before or during startup close the server instead of serving, and paste's workers are daemon threads so an unstopped server cannot hold the process open.

## RED (commit 4ad109ec)

Added class `TestMyWSGIRefServer` with nine tests (22 in the file). Run on the pre-change code: `8 failed, 14 passed, 3 warnings in 24.09s`; the run ended by itself.

| Test | Failure reason on pre-change code |
|------|-----------------------------------|
| test_process_exits_when_web_server_never_stopped | child hung for 20 s: paste's non-daemon workers kept the interpreter alive |
| test_stop_before_run_closes_instead_of_serving | `AttributeError: 'NoneType' object has no attribute 'server_close'` |
| test_stop_during_server_construction_closes_instead_of_serving | same AttributeError |
| test_real_server_stop_before_start_never_serves | same AttributeError |
| test_run_serves_with_daemon_threads | `AssertionError: None is not True : daemon_threads=True not passed to httpserver.serve` |
| test_stop_after_run_closes_server | `AssertionError: Expected 'server_close' to not have been called. Called 1 times.` |
| test_stop_right_after_publication_ends_serve_loop | same "to not have been called" |
| test_cleanup_returns_within_bound_with_stuck_requests | cleanup took 2.72 s (stop() joined each of five stuck workers for 0.5 s on the job thread) |

`test_real_server_stop_frees_port` and all 13 `TestWebAppJobCleanup` tests were green before the change (lock tests).

Verbatim failure lines (fail-before evidence for REL-07), each from its selector run alone:

```
E           AssertionError: process did not exit: web server threads kept the interpreter alive
--- process_exits: 1 failed, 21 deselected, 3 warnings in 20.19s
```

```
E       AssertionError: 2.7176908749970607 not less than 1.5 : cleanup exceeded the shutdown bound: 2.72s
--- stuck_requests: 1 failed, 21 deselected, 3 warnings in 2.87s
```

The plan's `red()` verify helper passed for all eight selectors (expected text, `1 failed`, no import or collection error); the lock selector reported `14 passed, 8 deselected`; whole-tree ruff `All checks passed!`. The pool-precondition assertions (5 workers, no idle worker) held; the red reason for stuck_requests was the timing assertion, as required.

## GREEN (commit a34191b6)

`src/python/web/web_app_job.py`, class `MyWSGIRefServer`:
- `import threading` added; `from threading import Thread` kept.
- `__init__`: `self.__stop_requested = False` and `self.__lock = threading.Lock()` with a comment naming the job thread and the server thread.
- `run()`: `httpserver.serve(..., handler=MyWSGIHandler, daemon_threads=True, **self.options)` into a local; under the lock it publishes `self.server` and snapshots the flag; outside the lock it either calls `server_close()` and returns (stop arrived during startup: idle workers, server thread) or calls `serve_forever()`.
- `stop()`: under the lock sets the flag and snapshots `self.server`; if None, logs debug "Web server not started yet; stop deferred to startup" and returns; otherwise logs "Stopping web server", then `server.running = False` and `server.socket.close()`. No `server_close()`, no `thread_pool.shutdown()`, no `shutdown()`.
- Class docstring updated (tolerates early stop, immediate stop, stop mechanism no longer follows the StackOverflow answer).

`WebAppJob`: comment-only change. The comment above `_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS` gained a "Web cleanup budget:" sentence stating the web service's share of shutdown is limited to about the join bound, leaving the rest of Docker's 10 s for the steps that follow; no claim that the final state save finishes in time.

Observed after the change:
- test file: `22 passed, 3 warnings in 2.37s`
- `-k stuck_requests` three times: `1 passed` each, 1.13 s each
- `-k process_exits`: `1 passed ... in 0.30s`
- `tests/unittests/test_web`: `494 passed, 4 warnings, 54 subtests passed in 3.89s`
- `ruff check src/python/`: `All checks passed!`
- Acceptance greps: daemon_threads=True 1, threading.Lock() 1, `with self.__lock:` 2, `__stop_requested` 3, `.shutdown()` 0, `server_close()` 1 (line 107, inside `run`), `server.running = False` 1, `server.socket.close()` 1, "Web cleanup budget:" 1, "Total cleanup budget"/"still runs" 0, `from threading import Thread` 1.

## REFACTOR

None needed.

## Gate outputs (Task 3)

- `ruff check src/python/`: `All checks passed!`
- Unit suite: see "Deviations" for how it was run. Unit suite minus the four known environmental modules: `1996 passed, 58 warnings, 179 subtests passed in 51.14s`.
- `tests/integration/test_web`: `65 passed, 4 warnings, 37 subtests passed in 7.22s`
- All fourteen validation selectors run alone: each selected at least one test and exited 0 (`daemon` 2, `stuck` 3, `real_server_stop` 2, others 1).
- Three consecutive runs of test_web_app_job.py: `22 passed` each, pytest-reported 2.41 s, 2.41 s, 2.50 s (wall 3.48 s, 3.32 s, 3.50 s).
- `grep -c "Phase 129 D-08" .planning/STATE.md`: 1 (line 150).

## Commits

- 4ad109ec test(129-02): add failing tests for web server stop race, unbounded stop and process exit
- a34191b6 feat(129-02): make web server stop race-free and its worker threads daemon
- 692b58f1 docs(129-02): record phase gate and validation sign-off

## Hand-off to Phase 130 (D-08)

No live deploy was done in Phase 129. Phase 130's release-image smoke test restarts the 1.8.1 image and confirms a clean shutdown in the logs: none of the three "Error ... during web service cleanup" lines, no "Web server did not stop within" warning, and no bind error after restart, reading container logs (stderr) as well as the app log file. The fail-before/pass-after evidence for WEB is the quoted red lines in 129-01-SUMMARY.md and this SUMMARY plus the green gate run.

STATE.md line on record (unchanged by this plan): "Phase 129 D-08 (hand-off to Phase 130): no live deploy in Phase 129. Phase 130's release-image smoke test must restart the 1.8.1 image and confirm a clean web-service shutdown in the logs: none of the three `Error ... during web service cleanup` lines, no `Web server did not stop within` warning, and no bind error after restart. Check container logs (stderr) as well as the app log file, because a server-thread bind failure is written to stderr."

## Notes for the owner

- The web server's threads are now background threads. On shutdown the app waits up to 5 seconds for the web server and then exits regardless; a browser request still in flight at that moment is cut off instead of delaying the exit.
- Telling the web server to stop is now immediate (it closes the listening port and returns). Before, it could take about half a second for every stuck browser request. The web server finishes winding down in the background, and the 5-second wait is the only time shutdown spends on it. This limits the web server's share of shutdown and leaves the rest of Docker's 10-second allowance for the steps that follow (stopping the controller, the final state save). It is not a guarantee that those later steps finish in time; this phase neither changes nor measures them.

### Known and unchanged

If a stop lands in the instant between two passes of the web server's accept loop, the server thread can end with a "ValueError: Invalid file descriptor" traceback on stderr. This was already possible before this phase, it does not delay or fail shutdown, and Phase 130 should not read it as a bind error.

## Deviations from Plan

**1. [Rule 3 - Blocking] Full unit suite gate run with the four environmental modules separated**
- **Found during:** Task 3
- **Issue:** `poetry run pytest tests/unittests` on this macOS machine hung for over 5 minutes (the rest of the suite takes 51 s). The local pytest lacks the pytest-timeout plugin (`Unknown config option: timeout`), so the configured 60 s cap does not apply locally, and `test_extract_process.py` hangs (multiprocessing spawn).
- **Fix:** Stopped the hung run; ran the suite with the four known environmental modules ignored (`1996 passed`), and each of those four alone under a 90 s cap: test_extract_process.py hung to the cap (exit 124), test_scanner_process.py `1 failed, 1 error`, test_sshcp.py `1 failed`, test_scanner.py `1 failed, 3 passed` (all with `-x`). None imports the web package; recorded as pre-existing/environmental in 129-VALIDATION.md per the project notes. No test file was modified.
- **Cost if wrong:** if one of those four failures is not environmental, Linux CI on the PR would surface it; the full-suite "exits 0" acceptance item is not demonstrated locally.
- **Files modified:** 129-VALIDATION.md
- **Commit:** 692b58f1

Process notes: the worktree started at 74b7a6e4 rather than the expected base ef1ec127, so it was reset to ef1ec127 per the branch check before any work. Tests ran on the pipx pytest interpreter (the worktree's poetry virtualenv has no project packages; `poetry run pytest` resolves to it and it has the project dependencies); `poetry install` was not needed. REQUIREMENTS.md was not updated; marking WEB-02 is left to the orchestrator after the wave.

## Known Stubs

None.

## Threat Flags

None. No production input surface was added; test listeners bind 127.0.0.1:0 only and the child process uses a fixed argument list.

## Self-Check: PASSED

- FOUND: src/python/web/web_app_job.py, src/python/tests/unittests/test_web/test_web_app_job.py, .planning/phases/129-web-service-cleanup-isolation/129-VALIDATION.md
- FOUND commits: 4ad109ec, a34191b6, 692b58f1
