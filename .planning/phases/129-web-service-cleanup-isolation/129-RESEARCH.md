# Phase 129: Web-Service Cleanup Isolation - Research

**Researched:** 2026-11-19
**Domain:** Python threading shutdown, paste `httpserver` / bottle `ServerAdapter` lifecycle
**Confidence:** HIGH (key behaviours confirmed by running the installed paste 3.10.1 / bottle 0.13.4 in this repo's poetry venv)
**Revised:** 2026-11-19 after the Codex plan review (129-REVIEWS.md): the stop mechanism changed from paste's `server_close()` to "clear the running flag and close the listening socket"; Pitfall 7 corrected; experiments R1-R6 added; open questions resolved

## Summary

`WebAppJob.cleanup()` runs `app.stop()`, `server.stop()` and `server_thread.join()` in a row with no isolation, so a raise in the first step skips the other two. The isolation fix is a direct copy of the `Controller.exit()` pattern: one `try/except Exception: self.logger.exception(...)` per step. That part is small. The research effort went into the two harder owner decisions, D-04 (bounded wait) and D-05 (the thread must not keep Python alive), and the discretion question about paste's `serve_forever`.

Experiments on the installed library versions show the following. (1) `server_close()` on its own is enough to make paste's `serve_forever()` return, within about 1 s. Paste's thread-pool server sets a 1 s timeout on the listening socket and its loop checks a `running` flag that `server_close()` clears. **Do not add `shutdown()`.** socketserver's `BaseServer.shutdown()` deadlocks because paste overrides `serve_forever` and never sets the event that `shutdown()` waits on (confirmed: it never returns). (2) **Making only the server thread daemon is not enough for D-05.** paste's default thread pool starts 10 worker threads that are *non-daemon*. When `server.stop()` never ran or failed, or when a worker was stuck in a blocking call, the process hung at interpreter exit even though the server thread was daemon (observed: the process stayed alive until the 150 s harness kill). Passing `daemon_threads=True` to `httpserver.serve(...)` makes the workers daemon too. With both changes, the process exited immediately in every scenario tested. (3) There is a real partial-startup race. If `cleanup()` runs after `server_thread.start()` but before the thread has assigned `MyWSGIRefServer.server`, `stop()` raises `AttributeError` today. The thread then goes on to bind and serve forever. A small lock-protected "stop requested" flag in `MyWSGIRefServer` closes this race: `run()` checks the flag after creating the server and closes it instead of serving.

On the restart question in CONTEXT: once `server.stop()` succeeds, the listening socket is closed immediately (the revised `stop()` closes it directly), before any worker cleanup. The port is free for the next `setup()` even if the thread lingers. In the tests the rebind succeeded in every successful-stop scenario. The port stays held only when `server.stop()` failed or never reached the server, which the stop-requested flag addresses. In that case the D-04 warning plus the new server thread's bind traceback surface it. No retry is needed, and none is in scope.

**Primary recommendation:** Rewrite `WebAppJob.cleanup()` as three isolated steps (`app.stop()` is always attempted; `server.stop()` when a server exists; a bounded `join(timeout=_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS = 5.0)` when the thread is alive, followed by a WARNING if it is still alive). Create the thread with `daemon=True`. In `MyWSGIRefServer`, add `daemon_threads=True` to `httpserver.serve(...)` and a lock-guarded stop-requested flag that makes `stop()` a no-op when no server exists yet and makes `run()` close a server whose stop already arrived. Stop the server from the job thread by setting `server.running = False` and closing `server.socket`, and nothing else. Do not call paste's `server_close()` from `stop()`: it does those two things and then tears down the worker pool on the calling thread, which is not bounded (Pitfall 7, experiments R1-R3). Do not call `shutdown()`. *(Revised 2026-11-19; the original recommendation was to keep `server_close()`.)*

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Per-step isolation (carried forward from Phase 123, not re-asked)
- **D-01:** Each cleanup step runs in its own `try/except Exception` and failures are logged with `logger.exception` naming the step, mirroring `Controller.exit()` (`src/python/controller/controller.py` ~433-440) and `ScanManager._terminate_and_join` (`src/python/controller/scan_manager.py` ~170-191).
- **D-02:** `cleanup()` itself does not raise. This follows the `Job.cleanup` contract ("Must not raise; log errors instead", `src/python/common/job.py`). Failures are reported through the log, not by re-raising. An earlier setup or execute error is still the one `propagate_exception()` surfaces.
- **D-03:** Steps that do not apply are skipped without logging an error: server never created, thread never created or never started (`Thread.is_alive()`/`ident is None`), and a `MyWSGIRefServer` whose inner `self.server` is still `None` because the server thread has not reached `httpserver.serve(...)` yet. That last case is a partial startup, not a failure.

#### Stuck web server (owner decision)
- **D-04:** Waiting for the web-server thread is bounded. Wait up to a few seconds (planner picks the constant, around 5 s, and it must sit below Docker's default 10 s stop grace). If the thread is still alive, log a WARNING that the web server did not stop in time and let shutdown continue. Shutdown must never wait indefinitely on the web server.
- **D-05:** For D-04 to actually let the process exit, the web-server thread must not keep Python alive at interpreter exit. It is currently created as a non-daemon `Thread` (`web_app_job.py:29`), so a timed-out join alone would still hang at exit. The plan must address this (for example by creating the thread with `daemon=True`) and must prove it with a test.
- **D-06:** Unlike the scanner precedent (skip `join` when `terminate` failed), the bounded wait runs even when `server.stop()` failed, because a timeout makes the wait safe and gives the server a chance to finish on its own.

#### Proof (owner decision)
- **D-07:** This phase is proven by automated tests: an injected failure in each of the three steps (the other two still run and the failure is logged), the partial-startup cases from D-03, and the stuck-thread case from D-04/D-05 (cleanup returns within the bound and logs the warning). The `app.stop()` case must fail before the fix and pass after (success criterion 1). The tests must not wait the full real timeout; inject or patch the bound.
- **D-08:** No separate live sandbox deploy in this phase. The live restart check is part of Phase 130's release-image smoke test (restart the 1.8.1 image and confirm clean shutdown in the logs). Record this hand-off so Phase 130 picks it up.

### Claude's Discretion
- Exact timeout constant and where it lives (module constant vs `Constants`).
- Log wording, provided each message names the failing step and never includes request data or secrets.
- Whether `MyWSGIRefServer.stop()` also calls the paste server's `shutdown()` before `server_close()` so `serve_forever()` actually returns. Research must confirm what paste's `serve_forever` does when only `server_close()` is called.
- Test structure, extending `src/python/tests/unittests/test_web/test_web_app_job.py`.

### Deferred Ideas (OUT OF SCOPE)
None. Discussion stayed within phase scope.

Also out of scope (from CONTEXT Phase Boundary): Controller/ScanManager/FileOperationManager shutdown changes, main-thread shutdown in `seedsyncarr.py` beyond keeping the web job from blocking exit, and any new restart/recovery behaviour.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WEB-01 | When any one web-service cleanup step (`app.stop`, `server.stop`, `thread.join`) fails, the remaining steps still run and the failure is logged. | Pattern 1 (per-step isolation, copied from `Controller.exit()`); test map rows WEB-01a/b/c; baseline confirmed: an `app.stop()` raise today escapes `cleanup()` and skips both later steps (code lines 45-49). |
| WEB-02 | Cleanup after a partial startup (server never created, or thread never started) completes without raising; after any failure, cleanup attempts every applicable step and terminates cleanly, with tests showing it. | Pattern 2 (applicability guards: `is_alive()` covers unstarted and finished threads, since `join()` on an unstarted thread raises `RuntimeError`); Pattern 3 (stop-requested flag for the server-not-yet-assigned race); Pattern 4 (bounded join plus `daemon=True` plus `daemon_threads=True`); subprocess exit test. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` in the repo root. Applicable directives from the user's global CLAUDE.md, `CLAUDE.local.md` and project memory:
- Never log sensitive data. Log messages name the step only, with no request data, headers or secrets (also in CONTEXT discretion).
- Don't swallow exceptions silently: every `except Exception` must `logger.exception(...)`. This matches D-01.
- Ensure resources are released on every path. The listening socket must be closed on every stop path, including the race (Pattern 3).
- Follow existing codebase conventions over new patterns. Copy the `Controller.exit()` loop shape and the `_..._IN_SECS` class-constant naming (`ScanManager._SIGTERM_SHUTDOWN_GRACE_IN_SECS`).
- CI runs `ruff check src/python/` (whole tree, ruff 0.15.22 pinned in CI) as a gate separate from pytest. Run both when verifying.
- `CLAUDE.local.md`: the plan-phase Codex review runs alongside the plan checker. This is a workflow note for the orchestrator, not a code constraint.
- One PR per phase (memory).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Ordered, isolated shutdown steps | API / Backend (`WebAppJob.cleanup`, job thread) | — | The Job contract owns cleanup; `Job.run` invokes it |
| Stopping the HTTP listener and worker pool | API / Backend (`MyWSGIRefServer.stop/run`, paste server) | — | Only the adapter has the paste server reference |
| Bounding the wait and not blocking interpreter exit | API / Backend (thread creation in `setup`, `daemon_threads` in `run`) | Process (`seedsyncarr.py` `webapp_job.join()`) | `seedsyncarr.py` needs no change: its `join()` returns once `cleanup()` returns |
| Flagging SSE streams to stop | API / Backend (`WebApp.stop()` sets `_stop_flag`) | — | Unchanged; SSE generators poll the flag |

## Standard Stack

No new libraries. Phase uses only what is installed.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| paste (`paste.httpserver`) | 3.10.1 (poetry.lock) [VERIFIED: poetry.lock + installed venv] | HTTP server under bottle | Already in use; behaviour verified by experiment below |
| bottle | 0.13.4 [VERIFIED: installed venv `bottle.__version__`] | `bottle.run` + `ServerAdapter` | Already in use |
| `threading` (stdlib) | Python 3.11 runtime (Docker `python:3.11-slim`), 3.12 local | Thread, Lock, daemon flag | stdlib |

### Supporting (tests)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | ^9.0.3 | runner | all |
| pytest-timeout | ^2.3.1, global `timeout = 60` in pyproject | prevents a hung shutdown test from hanging CI | subprocess/real-thread tests stay well under 60 s |
| `unittest.mock` | stdlib | `MagicMock`, `patch`, `patch.object` | step-failure injection, constant patching |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed or added in this phase, so the slopcheck gate does not apply.
**Packages removed:** none. **Packages flagged:** none.

## Verified Library Behaviour (experiments, this session)

All run with the repo's poetry venv (`paste 3.10.1`, `bottle 0.13.4`, Python 3.12.12) using the real `MyWSGIRefServer`/`MyWSGIHandler` from `src/python/web/web_app_job.py`. Scripts are in the session scratchpad (`exp1.py`, `exp2.py`, `exp3.py`). [VERIFIED: local experiment]

| # | Scenario (current code unless noted) | Observed |
|---|---|---|
| E1 | Idle server, `server.stop()` (= `server_close()`) | `stop()` returns in about 0.00 s; server thread exits about 1.0 s later; no exception; port rebindable immediately |
| E2 | Open SSE-style stream whose generator ignores any stop flag, then `server.stop()` | paste pool shutdown force-kills the hung worker (async `SystemExit`, traceback printed by paste's handle_error); server thread exits in about 1.5 s; port rebindable |
| E3 | `server.stop()` called before the server thread has assigned `self.server` | `AttributeError: 'NoneType' object has no attribute 'server_close'`; the thread then binds and **serves forever** (still alive after 3 s) |
| E4 | `server.server.shutdown()` (socketserver `BaseServer.shutdown`) | **Never returns** (deadlock), so never call it |
| E5 | Server thread created `daemon=True`, server never stopped (models a failed `server.stop()`), main exits | **Process hung at exit** until the 150 s harness kill: paste's 10 pool workers are non-daemon |
| E6 | Worker blocked in a C call (`time.sleep(200)` in a handler), `server.stop()`, daemon server thread | `stop()` returned in 1.5 s and the server thread exited, but the **process hung at exit** (150 s): the "killed" worker is non-daemon and an async exception cannot interrupt a blocking C call |
| E7 | Prototype: `daemon=True` thread + `daemon_threads=True` in `httpserver.serve` + stop-requested flag | early stop: thread exits in 0.00 s, port free; idle: about 1.0 s; hung worker: about 0.5 s; never stopped: process exits immediately. No non-daemon threads left in any case |

Revision experiments (2026-11-19, after the Codex review; script `rev_exp.py` / `rev_exp2.py` in the session scratchpad; "stuck" means a request handler blocked on a `threading.Event`; `os._exit` was replaced by a recorder in every run) [VERIFIED: local experiment]:

| # | Scenario | `stop()` on the calling thread | Server thread ended | Other |
|---|---|---|---|---|
| R1 | Current `stop()` (= `server_close()`), 1 stuck request | 0.51 s | 1.0 s | port rebindable |
| R2 | Current `stop()`, 4 stuck requests | **2.01 s** | 2.5 s | port rebindable |
| R3 | Current `stop()`, 10 stuck requests | **5.04 s** | 5.5 s | with the 5 s join after it, this passes Docker's 10 s grace |
| R4 | Current `stop()`, one stuck worker already killed by paste (`thread_pool.kill_worker`, what paste's own hung-thread check does) and still alive | 0.00 s, **raises** `AttributeError: module 'atexit' has no attribute '_exithandlers'` | 0.8 s | paste's force-quit branch was entered; `os._exit` was not reached because the branch crashes first on Python 3 |
| R5 | Revised `stop()` (`running = False`, `socket.close()`), same scenarios: idle / 1 / 4 / 10 stuck / already-killed worker | **0.00 s** in every case, no exception | 1.0 s / 1.5 s / 3.0 s / 6.0 s / 0.8 s | port rebindable at once in every case; `os._exit` never reached |
| R6 | Revised adapter, `stop()` before the thread starts (`run()` then calls `server_close()` on the server thread) | 0.00 s | at once | no exception; `os._exit` never reached |

Also observed: `handle_request()` on an already closed listening socket raises `ValueError: Invalid file descriptor: -1`. If a stop lands in the instant between the loop's `while self.running` check and its next `handle_request()`, the server thread ends with that traceback on stderr (via `threading.excepthook`). This window exists with the current `server_close()` too (same two statements), it does not delay or fail shutdown, and it is not addressed in this phase.

Source reading that explains these [VERIFIED: installed `paste/httpserver.py`]:
- `serve(...)` defaults `use_threadpool=True`, giving `WSGIThreadPoolServer` with `threadpool_workers=10`. `daemon_threads` defaults to `None`, so `ThreadPool(daemon=None)` gives non-daemon workers, and the pool registers `atexit.register(self.shutdown)`. Python joins non-daemon threads *before* running atexit, so that handler cannot rescue a hang.
- `ThreadPoolMixIn.server_activate` sets `self.socket.settimeout(1)`. `serve_forever` loops `while self.running: handle_request()`, and in `finally` calls `thread_pool.shutdown()` (no force-quit).
- `ThreadPoolMixIn.server_close`: `running = False`, `socket.close()` (port released here), then `thread_pool.shutdown(60)` **on the calling thread**. `ThreadPool.shutdown(force_quit_timeout)`: queues one shutdown token per worker; joins each worker for 0.5 s and collects the ones still alive as hung; lists as zombies any thread killed earlier (`dying_threads`) that still exists; kills each hung worker (`kill_worker`: async `SystemExit`, removes it from `workers`, records it in `dying_threads`, and starts a replacement worker). Only when `force_quit_timeout` is non-zero does it go on: one `join(force_quit_timeout)` on the first worker still alive in `workers` (by now only replacements, which exit on a leftover token), and then, if any zombie was listed or a worker is still alive, the force-quit branch: strip the threading atexit callback, `atexit._run_exitfuncs()`, `os._exit(3)`. That branch reads `atexit._exithandlers`, which does not exist on Python 3, so it raises `AttributeError` before reaching `os._exit` (R4). *(Corrected 2026-11-19. The original text said the cost was "bounded at about 0.5 s per hung worker" and treated that as acceptable; 0.5 s per hung worker is exactly what is not bounded, see R2/R3 and Pitfall 7.)*
- `ThreadPoolMixIn.serve_forever`'s `finally` calls `thread_pool.shutdown()` with the default `force_quit_timeout=0`: same 0.5 s per hung worker and the same kills, but no 60 s join and no force-quit branch, and it runs on the server thread. With `daemon=True` the pool registers no atexit hook.

## Architecture Patterns

### System Architecture Diagram

```
seedsyncarr main thread
  | (exception: ServiceExit / ServiceRestart / SIGTERM path)
  v
webapp_job.terminate() --sets shutdown_flag--> WebAppJob thread (Job.run loop exits)
  |                                              |
  |                                              v
  |                                     WebAppJob.cleanup()   [never raises]
  |                                       step 1: app.stop()  --> WebApp._stop_flag=True --> SSE generators end
  |                                         (try/except -> logger.exception "...stopping web app")
  |                                       step 2: server.stop() [if server created]
  |                                         MyWSGIRefServer.stop: lock{stop_requested=True; s=self.server}
  |                                           s is None --> no-op (run() will see flag and close)
  |                                           s exists --> s.running=False; s.socket.close()  (port free; returns at once; NO pool teardown here)
  |                                         (try/except -> logger.exception "...stopping web server")
  |                                       step 3: bounded join [if thread alive]
  |                                         thread.join(timeout=5.0); still alive --> logger.warning "did not stop in time"
  |                                         (try/except -> logger.exception "...joining web server thread")
  v
webapp_job.join()  (returns because cleanup returned)
  v
persist() --> raise --> interpreter exit
  (server thread daemon=True and paste workers daemon_threads=True, so nothing non-daemon keeps the process alive)

Server thread: bottle.run --> MyWSGIRefServer.run
   httpserver.serve(start_loop=False, daemon_threads=True)
   lock{self.server=server; stop=stop_requested}
   stop? --> server.server_close(); return
   else  --> server.serve_forever()  (loop ends <=1 s after running=False; its finally then drains the
                                      pool on THIS thread, 0.5 s per stuck worker, no force-quit)
```

### Recommended Change Footprint
```
src/python/web/web_app_job.py                         # only production file touched
src/python/tests/unittests/test_web/test_web_app_job.py   # extended (mock-driven + real-server + subprocess tests)
```

### Pattern 1: Per-step isolation (WEB-01, D-01/D-02/D-06)
**What:** Each step is wrapped separately. Failures go to `logger.exception` naming the step. Nothing re-raises. The join step runs even if `server.stop()` failed.
**Source:** `Controller.exit()` at `src/python/controller/controller.py` (loop over `(component, stop)` with `logger.exception("Error stopping {} during controller exit")`) [VERIFIED: codebase].
```python
class WebAppJob(Job):
    # Must stay below Docker's default 10 s stop grace (D-04).
    _SERVER_THREAD_JOIN_TIMEOUT_IN_SECS = 5.0

    @overrides(Job)
    def cleanup(self):
        # Each step runs independently (WEB-01): a failure in one never
        # skips the others. Job.run may call this after a partial setup().
        try:
            self.__app.stop()
        except Exception:
            self.logger.exception("Error stopping web app during web service cleanup")

        if self.__server is not None:
            try:
                self.__server.stop()
            except Exception:
                self.logger.exception("Error stopping web server during web service cleanup")

        # Bounded wait runs even if server.stop() failed (D-06).
        thread = self.__server_thread
        if thread is not None and thread.is_alive():
            try:
                thread.join(timeout=self._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)
                if thread.is_alive():
                    self.logger.warning(
                        "Web server did not stop within {} seconds; continuing shutdown".format(
                            self._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS))
            except Exception:
                self.logger.exception("Error joining web server thread during web service cleanup")
```
Note: a tuple loop as in `Controller.exit()` fits steps 1 and 2. Step 3 has its own applicability and timeout logic, so three explicit blocks are clearer. Either shape satisfies D-01.

### Pattern 2: Applicability guards (WEB-02, D-03)
- Server never created: `self.__server is None`, so skip step 2 silently.
- Thread never created: `None`, skip. Thread created but `start()` never ran or raised: `is_alive()` is `False` (and `ident is None`), skip. This guard is required because `Thread.join()` on an unstarted thread raises `RuntimeError("cannot join thread before it is started")` [VERIFIED: local Python 3.12]. A thread that already finished (for example `bottle.run` died on a bind error) is also skipped, which is harmless.
- Use `is_alive()` rather than `ident is None` alone, because it covers unstarted and finished threads with one check.

### Pattern 3: Race-free stop in `MyWSGIRefServer` (D-03 inner-`None` case)
**Why:** E3 shows that today a stop that arrives before `run()` assigns `self.server` both raises and leaves a server running forever. With only a None-guard, the server would still start serving after cleanup. The bounded join would then time out with a misleading warning, and during `ServiceRestart` the stale server would keep the port (old `WebApp`/controller objects served, new `setup()` bind fails inside its thread).
```python
class MyWSGIRefServer(bottle.ServerAdapter):
    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger
        self.server = None
        self.__lock = threading.Lock()
        self.__stop_requested = False

    def run(self, handler):
        self.logger.debug("Starting web server")
        handler = TransLogger(handler, logger=self.logger, setup_console_handler=(not self.quiet))
        server = httpserver.serve(handler, host=self.host, port=str(self.port), start_loop=False,
                                  handler=MyWSGIHandler,
                                  daemon_threads=True,   # D-05: pool workers must not block interpreter exit
                                  **self.options)
        with self.__lock:
            self.server = server
            stop_requested = self.__stop_requested
        if stop_requested:
            # stop() arrived during startup; never start serving. server_close() is
            # allowed here only: nothing was accepted yet, all workers are idle, and
            # this is the server thread.
            server.server_close()
            return
        server.serve_forever()

    def stop(self):
        with self.__lock:
            self.__stop_requested = True
            server = self.server
        if server is None:
            # Partial startup (D-03): run() will see the flag and close the server.
            self.logger.debug("Web server not started yet; stop deferred to startup")
            return
        self.logger.debug("Stopping web server")
        # Everything paste's server_close() does except the worker-pool teardown.
        # paste's serve loop sees the flag within ~1 s and drains the pool on the
        # server thread; doing it here would cost 0.5 s per stuck request on the
        # job thread, before the bounded join starts (Pitfall 7).
        server.running = False
        server.socket.close()
```
The lock-and-flag shape was verified in E7 and the revised `stop()` body in R5/R6 [VERIFIED: local experiment]. `self.options` is empty in this codebase (`bottle.run` passes no extra kwargs), so `daemon_threads=True` does not collide. A defensive alternative is `self.options.setdefault(...)`, but that is unnecessary. Note that `MyWSGIRefServer.logger` is the *web access* logger (`context.web_access_logger`). That is existing behaviour; the debug lines stay on it.

### Pattern 4: Bounded join that actually lets the process exit (D-04/D-05)
Both are required:
1. `Thread(target=bottle.run, kwargs=..., daemon=True)` in `setup()`.
2. `daemon_threads=True` in `httpserver.serve(...)` (Pattern 3).
Without (2), E5/E6 prove the process still hangs whenever paste's pool was not shut down (failed `server.stop()`) or a worker is blocked in a C call.

### Anti-Patterns to Avoid
- **Calling `server.shutdown()` (socketserver) before `server_close()`:** it deadlocks with paste (E4). This answers the CONTEXT discretion question: no.
- **Calling paste's `server_close()` (or `thread_pool.shutdown(...)`) from `MyWSGIRefServer.stop()`:** it runs the worker-pool teardown on the job thread, 0.5 s per stuck request with no upper limit, before the bounded join, and can enter paste's force-quit branch (R1-R4, Pitfall 7). Do not wrap it in a helper thread or a timeout either; just do not do pool teardown on the job thread.
- **`daemon=True` on the server thread alone:** not enough (E5/E6).
- **Guarding `MyWSGIRefServer.stop()` with only `if self.server is None: return`:** this avoids the raise but leaves a server that starts after cleanup (E3).
- **`thread.join()` without a timeout:** violates D-04.
- **Re-raising from `cleanup()`, or making cleanup failures override setup errors:** violates D-02. `Job.run` already handles a cleanup raise defensively, but the new code must not rely on that.
- **Including request/handler data in log lines:** only step names.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stopping paste's accept loop | Custom select loop / `shutdown()` / own worker tracking | paste's own `running` flag plus closing `server.socket` (the first two statements of its `server_close()`); paste's `serve_forever` `finally` drains the pool | The loop and the pool teardown stay paste's; only the place where the teardown runs changes (server thread instead of job thread). *(Revised 2026-11-19; originally `server_close()`.)* |
| Killing paste worker threads at exit | Own tracking of worker threads | `daemon_threads=True` option of `httpserver.serve` | Built-in option; also removes paste's atexit hook |
| Timed wait | Polling loop with `time.sleep` | `Thread.join(timeout=...)` then `is_alive()` | stdlib idiom |

## Runtime State Inventory

Not a rename/refactor/migration phase. Omitted.

## Common Pitfalls

### Pitfall 1: Non-daemon paste worker threads
**What goes wrong:** The process does not exit after cleanup, even with a daemon server thread.
**Why:** paste `ThreadPool` workers default to non-daemon. Python joins them before atexit runs.
**How to avoid:** `daemon_threads=True`, plus a subprocess test (see Validation).
**Warning signs:** the container needs Docker's SIGKILL at 10 s, and the final `persist()` is lost (it runs after `webapp_job.join()`).

### Pitfall 2: Partial-startup race on `MyWSGIRefServer.server`
**What goes wrong:** A stop before `run()` assigns the server raises, and the server starts anyway (E3).
**How to avoid:** Lock-guarded stop-requested flag (Pattern 3). Test it deterministically by calling `stop()` before `run()` with `httpserver.serve` patched to return a mock, then asserting `server_close` was called and `serve_forever` was not.

### Pitfall 3: MagicMock truthiness in tests
**What goes wrong:** `thread.is_alive()` on a `MagicMock` returns a truthy `MagicMock`, so "still alive" branches fire unexpectedly. `job.logger` is `context.logger`, which with a `MagicMock` context is a mock that silently accepts any call.
**How to avoid:** **Superseded by 129-01 Task 1 (model liveness by behaviour):** do not use `is_alive.side_effect` lists; set `is_alive.return_value` and let a `join` side_effect flip it. The original text is kept below for history. Original: Always set `thread.is_alive.return_value` or `side_effect` (for example `[True, False]` for joined in time, `[True, True]` for timed out). Assert on `job.logger.exception` / `job.logger.warning` call counts and that the message names the step.

### Pitfall 4: Name-mangled private attributes
`self.__server` / `self.__server_thread` become `_WebAppJob__server` etc. Prefer driving tests through `setup()` with `patch("web.web_app_job.MyWSGIRefServer")` and `patch("web.web_app_job.Thread")`. Both are module-level names in `web_app_job.py` (`from threading import Thread`). This also lets a test assert `daemon=True` in the `Thread(...)` call kwargs. Set mangled attributes directly only when no setup path exists.

### Pitfall 5: Real waits in tests
D-07 forbids waiting the real 5 s. For mock-thread tests, `join` is a `MagicMock`, so there is no wait. Assert `join.assert_called_once_with(timeout=WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)`. For a real-thread "stuck" test, use `patch.object(WebAppJob, "_SERVER_THREAD_JOIN_TIMEOUT_IN_SECS", 0.05)` with a real `Thread` blocked on a `threading.Event`. Assert that cleanup returns in under about 1 s and logs the warning, then set the event in `finally` so the thread ends.

### Pitfall 6: Binding `0.0.0.0` in local tests
`WebAppJob.setup()` hardcodes `host="0.0.0.0"`. On macOS this can trigger a firewall prompt. Real-socket tests should construct `MyWSGIRefServer(logger, host="127.0.0.1", port=0)` directly. paste accepts port `"0"` because it does `int(port)` and binds an ephemeral port.

### Pitfall 7: `server_close()` tears down the worker pool on the caller (action required)
*(Corrected 2026-11-19 after the Codex plan review. The original entry rated this "low likelihood, informational ... no action needed"; that was wrong.)*
**What goes wrong:** `server_close()` calls `thread_pool.shutdown(60)` on whichever thread calls it. Called from `MyWSGIRefServer.stop()` that is the job thread, inside `WebAppJob.cleanup()` step 2, before the bounded join of step 3. It waits 0.5 s for each worker that is stuck in a request: measured 0.5 s with one, 2.0 s with four, 5.0 s with ten (R1-R3), and the pool can hold more than ten. The 5 s join bound does not cover this time, so stop plus join can pass Docker's 10 s grace and the final `persist()` is lost. If a worker that paste killed earlier is still alive (a request stuck in a blocking C call for longer than paste's 30-minute kill limit), the same call enters the force-quit branch, which is written to end the process with `os._exit(3)` and on Python 3 raises `AttributeError` instead (R4); with per-step isolation that shows up as a logged "Error stopping web server" for what is really a stuck request.
**What the Codex review got right and what the measurements adjust:** right that `stop()` is unbounded and that the join bound does not cover it. Adjusted: the 60 s join applies only to a worker still in the pool's list after the kills, which in practice is a replacement worker that exits at once, so the realistic cost is 0.5 s per stuck worker, not 60 s; and `os._exit(3)` is not reached on Python 3 (the branch crashes first). The conclusion is the same: the job thread must not run this teardown.
**How to avoid:** `stop()` sets `server.running = False` and closes `server.socket`, and returns (R5: 0.00 s in every scenario). paste's `serve_forever` `finally` then runs `thread_pool.shutdown()` with `force_quit_timeout=0` on the server thread: no 60 s join, no force-quit branch. That thread is daemon and is the one the 5 s bounded join waits on, so the total is app.stop (a flag) + an immediate socket close + at most 5 s. `server_close()` remains acceptable in one place only: `run()`'s stop-before-serve branch, on the server thread, where nothing has been accepted and every worker is idle (R6).
**Test:** a real server with a five-worker pool (`threadpool_workers=5` through the adapter's options) and all five workers stuck; `WebAppJob.cleanup()` must return within a shortened bound, log the warning, and never call `os._exit` (red on the current `stop()` at 2.5 s or more). Revised after the Codex round-2 review: with idle workers present, paste's `ThreadPool.shutdown` walks a list that exiting idle workers shrink under it, so "0.5 s per stuck worker" is a measurement, not a guarantee; with every worker stuck nothing leaves the list and the 2.5 s minimum is fixed (measured 2.52 s in four runs out of four; revised `stop()` 0.00 s). Four workers is not possible: paste asserts `spawn_if_under (5) <= nworkers`.

### Pitfall 8: Restart after a failed `server.stop()`
If `server.stop()` raises (WEB-01 injected case), the old listener may still hold the port. On `ServiceRestart` the new server thread's `httpserver.serve` would fail to bind *inside its thread*. `setup()` does not raise, and the traceback goes to stderr via `threading.excepthook`. Per CONTEXT this is surfaced (D-04 warning plus bind traceback), not retried. With a working `stop()` this does not occur, because the socket is closed first and at once.

## Code Examples

### Test: `app.stop()` failure still runs the other steps (success criterion 1, TDD red today)
```python
from unittest.mock import MagicMock, patch
import bottle
from web.web_app_job import WebAppJob

@patch("web.web_app_job.Thread")
@patch("web.web_app_job.MyWSGIRefServer")
def test_app_stop_failure_still_stops_server_and_joins(mock_server_cls, mock_thread_cls):
    web_app = MagicMock()
    web_app.stop.side_effect = RuntimeError("app stop failed")
    job = WebAppJob(context=MagicMock(), web_app=web_app)
    job.setup()
    server = mock_server_cls.return_value
    thread = mock_thread_cls.return_value
    # Superseded by 129-01 Task 1 (model liveness by behaviour): use is_alive.return_value = True
    # plus a join side_effect that sets it to False, not this call-count list.
    thread.is_alive.side_effect = [True, False]

    job.cleanup()  # must not raise (today: RuntimeError escapes, server.stop/join never called)

    server.stop.assert_called_once()
    thread.join.assert_called_once_with(timeout=WebAppJob._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)
    job.logger.exception.assert_called_once()
    assert "web app" in job.logger.exception.call_args[0][0]
```
On current code the `RuntimeError` escapes `cleanup()` before `server.stop()` or `join()` runs, so the test fails. That is the required red. The `daemon=True` assertion should be its own test: `assert mock_thread_cls.call_args.kwargs["daemon"] is True`.

### Test: D-05 process exit (subprocess, real paste server)
```python
import subprocess, sys, textwrap, os
SCRIPT = textwrap.dedent("""
    import logging, threading, bottle
    from web.web_app_job import MyWSGIRefServer
    app = bottle.Bottle()
    srv = MyWSGIRefServer(logging.getLogger("t"), host="127.0.0.1", port=0)
    t = threading.Thread(target=bottle.run, kwargs={"app": app, "server": srv, "quiet": True}, daemon=True)
    t.start()
    # (optionally wait until srv.server is set) then exit WITHOUT stopping: models a failed server.stop()
""")
def test_process_exits_when_web_server_never_stopped():
    src_python = <path to src/python>   # derive from __file__
    proc = subprocess.run([sys.executable, "-c", SCRIPT], cwd=src_python, timeout=20, capture_output=True)
    assert proc.returncode == 0
```
Today's code hangs this subprocess (E5), so the test fails via `subprocess.TimeoutExpired`, which is the red. Better still, run the real `WebAppJob` in the subprocess so the `daemon=True` thread creation is exercised too: build `WebAppJob` with a context whose `config.web.port = 0`. This binds `0.0.0.0` (Pitfall 6: acceptable in CI Docker, may prompt locally) and needs a `WebApp` stand-in with `stop()`/`process()` methods (a small `bottle.Bottle` subclass). The planner can choose. Either version must wait until `srv.server` is set before exiting, so the pool actually exists.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sequential unguarded cleanup | Per-step isolated cleanup | Phase 123 (Controller/ScanManager/FileOp) | Phase 129 brings WebAppJob in line |
| Unbounded `join()` | Bounded join + daemon threads | This phase | Shutdown can no longer hang on the web server |

**Deprecated/outdated:** the StackOverflow-derived `MyWSGIRefServer.stop()` (bare `self.server.server_close()`) predates the partial-startup handling.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python 3.11 (Docker runtime) behaves the same as the locally verified 3.12 for daemon threads, `join` on an unstarted thread, and paste `ThreadPool` | Verified Library Behaviour | Low. These semantics are long-standing. CI runs the tests on the Docker image, which will catch differences |
| A2 | 5.0 s join bound leaves enough headroom inside Docker's 10 s grace (main thread sleeps 0.5 s first; controller and web jobs shut down in parallel; `persist()` follows) | Pattern 1 | Low. If the controller exit is slow, the overall budget is the controller's, not this phase's |
| A3 | Nothing else in the codebase relies on the web server thread or paste workers being non-daemon (for example, to finish in-flight responses at exit) | Pattern 4 | Low. Cleanup's bounded join still gives in-flight work up to 5 s |

## Open Questions (RESOLVED)

1. **Should the D-05 subprocess test drive real `WebAppJob` (binds 0.0.0.0) or `MyWSGIRefServer` directly (127.0.0.1)?**
   - Recommendation: test `MyWSGIRefServer` directly in the subprocess for `daemon_threads`, and cover `daemon=True` with the unit assertion on the `Thread(...)` kwargs. Both are deterministic and need no firewall interaction.
   - **RESOLVED:** `MyWSGIRefServer` directly on 127.0.0.1 in the child process (129-02 Task 1, `test_process_exits_when_web_server_never_stopped`), plus the `Thread(...)` kwargs assertion for `daemon=True` (129-01 Task 1, `test_server_thread_created_as_daemon`). The one test that does drive a real `WebAppJob` against a real server (129-02 Task 1, `test_cleanup_returns_within_bound_with_stuck_requests`) replaces the adapter constructor so it still binds 127.0.0.1.
2. **Where does the server-thread bind-failure traceback go (stderr vs app log)?** `threading.excepthook` writes to stderr, which Docker captures. Whether it reaches the plain-file app log is outside this phase. Phase 130's restart smoke test (D-08) should look at container logs, not only the app log file.
   - **RESOLVED:** stderr. Phase 130's restart smoke test checks container logs (stderr) as well as the app log file; recorded as the D-08 hand-off in STATE.md Pending Todos ("Phase 129 D-08"), in 129-VALIDATION.md Manual-Only, and in the 129-02 SUMMARY instructions.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| poetry venv (paste, bottle, pytest) | tests | yes | Python 3.12.12, paste 3.10.1, bottle 0.13.4 | — |
| ruff | CI lint gate | yes | 0.15.9 local (CI pins 0.15.22) | — |
| Docker | CI python tests (`make run-tests-python`) | not required locally | — | local `poetry run pytest` |

Baseline: `tests/unittests/test_web` 473 passed in 1.42 s; `ruff check src/python/` reports "All checks passed!" [VERIFIED: run this session].

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ^9.0.3 + pytest-timeout (global 60 s), unittest-style classes accepted |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` (pythonpath ".") |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider` |
| Full suite command | `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider` plus, from the repo root, `ruff check src/python/` |
| CI parity | `make run-tests-python` (Docker, Python 3.11) and the `lint-python` job (`ruff check src/python/`) |

### Phase Requirements → Test Map
All tests go in `src/python/tests/unittests/test_web/test_web_app_job.py` (exists; currently 1 test).

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEB-01a | `app.stop()` raises, so `server.stop()` and the bounded join still run and `logger.exception` names "web app". **Red before the fix** (SC1) | unit (mocks) | `... test_web_app_job.py -k app_stop_failure` | extend |
| WEB-01b | `server.stop()` raises, so the join still runs (D-06), `app.stop()` ran, and the exception is logged | unit | `-k server_stop_failure` | extend |
| WEB-01c | `thread.join` raises, so `app.stop()`/`server.stop()` ran, the exception is logged, and cleanup returns | unit | `-k join_failure` | extend |
| WEB-01d | Combined: all three steps raise, so all three are attempted and logged, and cleanup does not raise | unit | `-k all_steps_fail` | extend |
| WEB-02a | Cleanup without setup (server and thread `None`): no raise, `app.stop` called, no exception logged | unit | existing `test_cleanup_without_setup_does_not_raise` (add `logger.exception.assert_not_called()`) | yes |
| WEB-02b | Thread created but never started (`Thread.start` raises in setup, or `is_alive()` is False): join not called, no error logged | unit | `-k thread_not_started` | extend |
| WEB-02c | `MyWSGIRefServer.stop()` before `run()` assigns the server: no raise; then `run()` (with `httpserver.serve` patched) calls `server_close` and not `serve_forever` | unit | `-k stop_before_run` | extend |
| WEB-02d | `httpserver.serve` is called with `daemon_threads=True`; `Thread(...)` is created with `daemon=True` | unit | `-k daemon` | extend |
| WEB-02e | Stuck thread: `is_alive` stays True after `join(timeout=...)`, so a WARNING is logged and cleanup returns. Mock join, no real wait. Plus one real-thread variant with the constant patched to 0.05 s, asserting elapsed time is below 1 s | unit | `-k stuck` | extend |
| WEB-02f | D-05 proof: a subprocess with a real `MyWSGIRefServer` (127.0.0.1, port 0) on a daemon thread, never stopped, exits within the timeout with returncode 0. **Red before the fix** (hangs, E5) | integration-style (subprocess, under 20 s timeout) | `-k process_exits` | extend |
| WEB-02g | Real-server clean stop: start a real `MyWSGIRefServer` on 127.0.0.1:0, `stop()`, thread exits within about 3 s, and the port can be rebound with `SO_REUSEADDR` | unit (real socket) | `-k real_server_stop` | extend |
| WEB-02h | Whole-cleanup bound: real `WebAppJob.cleanup()` against a real five-worker server with all five workers stuck returns within a shortened bound, logs the warning, never calls `os._exit`. **Red before the fix** (`stop()` takes at least 2.5 s; see Pitfall 7 test note) | integration-style (real socket, real threads) | `-k stuck_requests` | extend |
| WEB-02i | `stop()` while `httpserver.serve` is still constructing the server (event barrier): no raise; server closed, never serves | unit (patched paste, real thread) | `-k stop_during_server_construction` | extend |
| WEB-02j | `stop()` right after the server is published (event barrier at loop entry): running flag cleared and socket closed, `server_close` not called from `stop()` | unit (patched paste, real thread) | `-k stop_right_after_publication` | extend |
| LINT | Whole-tree lint | static | `ruff check src/python/` | n/a |

### Sampling Rate
- **Per task commit:** quick run command plus `ruff check src/python/`
- **Per wave merge:** full unittests plus ruff
- **Phase gate:** full suite green plus ruff before `/bm:verify-work`. The live restart check is handed off to Phase 130 (D-08).

### Wave 0 Gaps
- None for framework or fixtures. The test file exists. TDD: write WEB-01a and WEB-02f first and confirm they fail on current code (WEB-01a: `RuntimeError` escapes `cleanup()`; WEB-02f: `TimeoutExpired`), then implement.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no (no new input) | — |
| V6 Cryptography | no | — |
| V7 Error Handling and Logging | yes | `logger.exception` with step-name-only messages; no request data or secrets; nothing surfaced to HTTP clients |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shutdown hang leaves a stale server serving old state / holding the port | Denial of Service | Bounded join, daemon threads, race-free stop flag |
| Sensitive data in shutdown logs | Information Disclosure | Fixed message strings naming the step only |

## Sources

### Primary (HIGH confidence)
- Installed `paste/httpserver.py` 3.10.1 (`serve`, `ThreadPoolMixIn.serve_forever/server_close/server_activate`, `ThreadPool.__init__/shutdown/kill_worker`): read directly in the poetry venv
- Installed `bottle.py` 0.13.4 `run()`: re-raises non-KeyboardInterrupt exceptions when there is no reloader
- Local experiments E1-E7 (scratchpad scripts) against the repo's real `MyWSGIRefServer`
- Codebase: `web_app_job.py`, `web_app.py`, `common/job.py`, `controller.py` `exit()`, `scan_manager.py` `_terminate_and_join` and tests, `seedsyncarr.py` shutdown block, Phase 123 `deferred-items.md` (origin of this backlog item)

### Secondary / Tertiary
- None needed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, since nothing is new and versions were read from the lockfile and venv
- Architecture: HIGH, since the prototype was verified end to end (E7)
- Pitfalls: HIGH for E3-E6 (reproduced); HIGH for Pitfall 7 as corrected (source re-read plus R1-R6). The original Pitfall 7 rested on one experiment with a single stuck worker and missed that the cost grows with the number of stuck workers

**Research date:** 2026-11-19
**Valid until:** stable (pinned paste/bottle); re-check if paste is upgraded past 3.10.x
