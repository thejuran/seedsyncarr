# Phase 129: Web-Service Cleanup Isolation - Context

**Gathered:** 2026-11-19
**Status:** Ready for planning

<domain>
## Phase Boundary

`WebAppJob.cleanup()` (`src/python/web/web_app_job.py`) runs its three shutdown steps (`app.stop()`, `server.stop()`, `server_thread.join()`) so that a failure in any one step never skips the others, every failure is logged, and cleanup after a partial startup (server never created, thread never started, or server thread started but not yet listening) completes without raising. Shutdown must also terminate: a web server that will not stop can no longer hold the app open indefinitely. Requirements WEB-01 and WEB-02.

Out of scope: changing the Controller, ScanManager or FileOperationManager shutdown (already isolated in Phase 123), the main-thread shutdown sequence in `seedsyncarr.py` beyond what is needed to keep the web job from blocking exit, and any new restart or recovery behaviour.

</domain>

<decisions>
## Implementation Decisions

### Per-step isolation (carried forward from Phase 123, not re-asked)
- **D-01:** Each cleanup step runs in its own `try/except Exception` and failures are logged with `logger.exception` naming the step, mirroring `Controller.exit()` (`src/python/controller/controller.py` ~433-440) and `ScanManager._terminate_and_join` (`src/python/controller/scan_manager.py` ~170-191).
- **D-02:** `cleanup()` itself does not raise. This follows the `Job.cleanup` contract ("Must not raise; log errors instead", `src/python/common/job.py`). Failures are reported through the log, not by re-raising. An earlier setup or execute error is still the one `propagate_exception()` surfaces.
- **D-03:** Steps that do not apply are skipped without logging an error: server never created, thread never created or never started (`Thread.is_alive()`/`ident is None`), and a `MyWSGIRefServer` whose inner `self.server` is still `None` because the server thread has not reached `httpserver.serve(...)` yet. That last case is a partial startup, not a failure.

### Stuck web server (owner decision)
- **D-04:** Waiting for the web-server thread is bounded. Wait up to a few seconds (planner picks the constant, around 5 s, and it must sit below Docker's default 10 s stop grace). If the thread is still alive, log a WARNING that the web server did not stop in time and let shutdown continue. Shutdown must never wait indefinitely on the web server.
- **D-05:** For D-04 to actually let the process exit, the web-server thread must not keep Python alive at interpreter exit. It is currently created as a non-daemon `Thread` (`web_app_job.py:29`), so a timed-out join alone would still hang at exit. The plan must address this (for example by creating the thread with `daemon=True`) and must prove it with a test.
- **D-06:** Unlike the scanner precedent (skip `join` when `terminate` failed), the bounded wait runs even when `server.stop()` failed, because a timeout makes the wait safe and gives the server a chance to finish on its own.

### Proof (owner decision)
- **D-07:** This phase is proven by automated tests: an injected failure in each of the three steps (the other two still run and the failure is logged), the partial-startup cases from D-03, and the stuck-thread case from D-04/D-05 (cleanup returns within the bound and logs the warning). The `app.stop()` case must fail before the fix and pass after (success criterion 1). The tests must not wait the full real timeout; inject or patch the bound.
- **D-08:** No separate live sandbox deploy in this phase. The live restart check is part of Phase 130's release-image smoke test (restart the 1.8.1 image and confirm clean shutdown in the logs). Record this hand-off so Phase 130 picks it up.

### Claude's Discretion
- Exact timeout constant and where it lives (module constant vs `Constants`).
- Log wording, provided each message names the failing step and never includes request data or secrets.
- Whether `MyWSGIRefServer.stop()` also calls the paste server's `shutdown()` before `server_close()` so `serve_forever()` actually returns. Research must confirm what paste's `serve_forever` does when only `server_close()` is called.
- Test structure, extending `src/python/tests/unittests/test_web/test_web_app_job.py`.

</decisions>

<specifics>
## Specific Ideas

- Confirmed 2026-11-18 at roadmap time: an injected `app.stop()` failure today skips both `server.stop()` and `thread.join()`.
- In-process restart (`ServiceRestart`, `src/python/seedsyncarr.py`) reruns the jobs in the same process. If a web-server thread outlives its bounded wait during a restart, it may still hold the web port, and the next `setup()` would fail to bind. Research should confirm whether that can happen once `server.stop()` works correctly. If it can, it should be surfaced clearly (the logged D-04 warning plus the existing bind error), not silently retried. New recovery behaviour is out of scope.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and scope
- `.planning/REQUIREMENTS.md` - WEB-01, WEB-02
- `.planning/ROADMAP.md` section "Phase 129: Web-Service Cleanup Isolation" - success criteria 1-4

### Code under change
- `src/python/web/web_app_job.py` - `WebAppJob.setup/cleanup`, `MyWSGIRefServer.run/stop`
- `src/python/web/web_app.py` - `WebApp.stop()` (sets `_stop_flag`)
- `src/python/common/job.py` - `Job.run` cleanup contract and `propagate_exception`
- `src/python/seedsyncarr.py` - main-thread shutdown (`terminate()` then `join()` on jobs) and `ServiceRestart`

### Isolation pattern to mirror (Phase 123)
- `src/python/controller/controller.py` - `Controller.exit()` per-component try/except loop
- `src/python/controller/scan_manager.py` - `_terminate_and_join` per-process isolation
- `.planning/phases/123-*/` - Phase 123 context and plans (LIFE-01/LIFE-02), if present on disk

### Tests
- `src/python/tests/unittests/test_web/test_web_app_job.py` - existing cleanup-without-setup test

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Controller.exit()` loop over `(component, stop)` pairs with `logger.exception` per failure: the shape to copy for the three web steps.
- Existing `test_cleanup_without_setup_does_not_raise` test with `MagicMock` web app and context.

### Established Patterns
- Cleanup never raises; errors go to `logger.exception` (Job contract, Phase 123).
- Bounded waits use explicit constants and monotonic clocks (Phase 123: 10 s scanner grace, 2.0 s lftp reap).
- CI runs whole-tree `ruff check src/python/` separately from pytest; run both.

### Integration Points
- `Job.run()` calls `cleanup()` after setup/execute, including after a setup that raised partway.
- `seedsyncarr.py` calls `webapp_job.terminate()` then `webapp_job.join()`. That join only returns once `cleanup()` returns, so a bounded cleanup bounds this join too.

</code_context>

<deferred>
## Deferred Ideas

None. Discussion stayed within phase scope.

</deferred>

---

*Phase: 129-web-service-cleanup-isolation*
*Context gathered: 2026-11-19*
