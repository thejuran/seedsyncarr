---
phase: 129-web-service-cleanup-isolation
reviewed: 2026-11-20T04:12:13Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/python/web/web_app_job.py
  - src/python/tests/unittests/test_web/test_web_app_job.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 129: Code Review Report

**Reviewed:** 2026-11-20T04:12:13Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the phase diff (`dc0aa172..HEAD -- src/python`): the step-isolated `WebAppJob.cleanup()` with a bounded join, the daemon server thread, and the new `MyWSGIRefServer` stop/run lock with `daemon_threads=True`. I checked the claims against the installed paste source (`paste/httpserver.py`: `ThreadPoolMixIn.serve_forever`, `server_close`, `ThreadPool.shutdown`, `kill_worker`) and bottle's `run()`.

The lock handshake is correct. `self.server` and `__stop_requested` are published and read under one lock, so a stop that arrives before or during `httpserver.serve()` construction is never lost, and a stop that arrives after publication but before `serve_forever()` makes the loop exit immediately (`running` is False). The cleanup steps are isolated correctly. The `is_alive()` guard covers both a thread that never started and one that already finished. The join is bounded.

One real defect remains. `stop()` closes the listening socket from the job thread while paste's serve loop may be between its `while self.running` check and the next `handle_request()`. In that window `handle_request()` raises `ValueError` on the closed socket. paste only catches `socket.timeout`, and bottle re-raises, so the server thread dies with an uncaught traceback at shutdown. I reproduced the exception directly: `handle_request()` on a closed paste server raises `ValueError: Invalid file descriptor: -1`.

The tests are deterministic where they can be (barriers and events, not sleeps). The real-server timing bounds are generous (1.0 s and 1.5 s against 0.05 s and 0.2 s joins). Three consecutive runs passed: 22/22 each, about 2.3 s. No convention findings: the shared convention checker returned an empty findings list.

## Warnings

### WR-01: stop() can race paste's serve loop and kill the server thread with an uncaught ValueError

**File:** `src/python/web/web_app_job.py:143` (serve loop), `src/python/web/web_app_job.py:160-161` (stop)
**Issue:** `stop()` runs on the job thread and does `server.running = False; server.socket.close()` without coordinating with the serve loop. paste's `ThreadPoolMixIn.serve_forever` is:

```python
while self.running:
    try:
        self.handle_request()
    except socket.timeout:
        pass
```

Suppose the server thread has just passed the `while self.running` check, for example right after a 1 s `handle_timeout()` return. If `stop()` closes the socket before the thread reaches `selector.register(self, ...)` inside `handle_request()`, then `self.fileno()` returns -1. The selector then raises `ValueError: Invalid file descriptor: -1` (verified against the installed paste and Python 3.12). Nothing catches it. paste only handles `socket.timeout`, the `finally` runs `thread_pool.shutdown()` and then re-raises, and `bottle.run` re-raises non-KeyboardInterrupt exceptions when there is no reloader. The thread ends through `threading.excepthook`, which prints an "Exception in thread ..." traceback to stderr during an otherwise clean shutdown or restart. The window is small, but it opens every time the loop wraps (once a second at idle), so it will turn up as intermittent shutdown noise in container logs. That noise is hard to tell apart from a real failure, which matters given the project's NAS log forensics workflow. No test covers this interleaving: `test_stop_right_after_publication_ends_serve_loop` mocks `serve_forever` entirely.
**Fix:** Treat socket errors raised after a requested stop as a normal exit in `run()`:

```python
try:
    server.serve_forever()
except (OSError, ValueError):
    # stop() closed the listening socket while the loop was between its
    # running check and the next accept; paste has already drained the pool
    # in its finally block.
    if server.running:
        raise
    self.logger.debug("Web server loop ended after stop()")
```

Add a test that closes the socket on a real server between the loop check and `handle_request()`. For example, wrap `server.handle_request` so that its first call runs `srv.stop()` before delegating. Assert that the thread exits without calling `threading.excepthook`.

## Info

### IN-01: Duplicated rationale comment on the join-timeout constant

**File:** `src/python/web/web_app_job.py:17-28`
**Issue:** There are two consecutive comment paragraphs. Both say the bound must leave room within docker's 10 s grace for the controller exit and final state save. The second looks like a revision that was appended instead of replacing the first.
**Fix:** Merge them into one paragraph: the budget breakdown (app flag, socket close, bounded join), why it stays under the 10 s grace, and why it is a class attribute (so tests can patch it).

### IN-02: Stop-before-start still binds the port and builds a full thread pool

**File:** `src/python/web/web_app_job.py:127-142`
**Issue:** When `stop()` has already been requested, `run()` still calls `httpserver.serve()`. That binds and listens on the port and starts the paste worker pool (10 threads by default). Only then does it check the flag and call `server_close()`. Any client connection that lands in the backlog in that window is reset. The flag cannot be checked only before `serve()`, because a stop during construction must still be honoured. An early check would still avoid binding at all in the common pre-start case.
**Fix:** Add a fast-path check before construction, and keep the existing post-publication check:

```python
with self.__lock:
    if self.__stop_requested:
        self.logger.debug("Web server stop requested before startup; not starting")
        return
server = httpserver.serve(...)
```

Note that this leaves `self.server` as None. `test_real_server_stop_before_start_never_serves` asserts `assertIsNotNone(srv.server)`, so update that test too.

### IN-03: Misleading "stop deferred to startup" debug log when run() already failed

**File:** `src/python/web/web_app_job.py:149-151`
**Issue:** If `httpserver.serve()` raised in `run()`, for example because the port was already in use, `self.server` stays None and the server thread has ended. A later `stop()` then logs "Web server not started yet; stop deferred to startup", but no startup will ever happen. Anyone reading logs during an outage would be misled about the server state.
**Fix:** Track a "run finished/failed" state under the same lock (set it in a `try/finally` around construction). When it is set, log "Web server never started; nothing to stop" instead.

### IN-04: Test-suite nits: tautological constant test and an ephemeral-port assumption

**File:** `src/python/tests/unittests/test_web/test_web_app_job.py:280-283`, `:497-501`
**Issue:** `test_join_timeout_constant_below_docker_grace` asserts `== 5.0` and then `< 10.0`. The second assertion can never fail on its own, so the test only pins a literal. `test_real_server_stop_before_start_never_serves` expects `create_connection` to the just-released ephemeral port to fail. If any other process on the CI host binds that port in the gap, the test fails spuriously. The chance is very small, but it is non-deterministic.
**Fix:** Drop the redundant `assertLess`, or document that the test exists to pin the value. For the port test, assert on the adapter's state instead (`srv.server.socket.fileno() == -1` and `serve_forever` was never entered, for example by spying on it), or accept `ConnectionRefusedError` only.

## Set aside (needs ruling)

### SA-01: Hung workers are force-killed and replaced on the orphaned server thread

**Where:** `src/python/web/web_app_job.py:143` (via paste `serve_forever` finally, then `ThreadPool.shutdown()`, then `kill_worker`)
**Why excluded:** This is pre-existing paste behaviour. The old `server_close()` path also ran `shutdown(60)`, which kills hung workers. The phase only moved where it runs, from the job thread to the server thread.
**Effect if left as is:** If a request is still in a handler at shutdown, the server thread joins each worker for 0.5 s and then injects `SystemExit` into hung workers. That can interrupt handler code in the middle of a mutation. Each kill also spawns a replacement daemon worker that blocks forever on the pool queue, because the SHUTDOWN tokens were already consumed. On an in-process `ServiceRestart`, those threads accumulate for the life of the process. On a full container stop the effect is harmless.
**Needs:** A ruling on whether in-process restarts with in-flight requests are common enough to pass `threadpool_options={"kill_thread_limit": 0}`, or an equivalent setting, and to accept a stuck thread instead of an async kill. Otherwise accept as is.

### SA-02: Port-bind failure at startup still leaves the job running without a web UI

**Where:** `src/python/web/web_app_job.py:47-54`, `:127`
**Why excluded:** This is pre-existing and not part of the cleanup or isolation scope. The daemon flag does not change it.
**Effect if left as is:** If the port is taken, for example during a fast in-process restart while the old server thread is still past its bounded join, `httpserver.serve()` raises on the daemon thread. The traceback goes to stderr through `threading.excepthook`, not to the app logger. `WebAppJob` keeps running with no web server, and the UI is silently unreachable.
**Needs:** A ruling on whether to surface server-thread startup failure to the job (for example, record the exception in `run()` and have `execute()` raise it so `Job.run` logs it and shuts down). Otherwise defer.

---

_Reviewed: 2026-11-20T04:12:13Z_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_
