# Phase 123: Startup and Shutdown Lifecycle - Research

**Researched:** 2026-10-25
**Domain:** Python process/thread lifecycle (multiprocessing children, pexpect-driven external process, signal handling) in a tini-supervised Docker container
**Confidence:** HIGH (gap inventory and the scanner-death root cause); MEDIUM (the exact lftp SIGKILL-escalation failure mechanism — mechanism is explained, trigger condition needs the D-07 live check)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Fix in this phase. Root-cause and fix why a normal restart logs `Error stopping lftp during controller exit` (`ptyprocess`/`pexpect` "Could not terminate the child") and `Scanner process(es) died unexpectedly: RemoteScanner, LocalScanner, ActiveScanner` / `ScannerProcessDiedError`. Done means a normal sandbox restart logs neither error and the app comes back up normally. Evidence and exact log lines: `.planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md` (first section) and 122-06's `log-bravo.txt` excerpt quoted there.
- **D-02:** The fix must be test-first like the LIFE fixes: a regression test that fails before and passes after, wherever the cause can be reproduced in unit tests. If part of the cause is only observable live (e.g. container SIGTERM delivery to child processes), the live restart check in D-07 is the proof, and the plan must state which part is unit-proven and which is live-proven.
- **D-03:** Conditional. Do not replace the `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` setup wait (`src/python/seedsyncarr.py`, tracked as DEFER-SHUTDOWN in `.planning/codebase/CONCERNS.md`) unless the D-01 investigation shows it causes or contributes to the restart errors. If linked, replace it as part of D-01 with a per-job "setup complete" signal and a bounded wait. This does not count as a "new sleep" (success criterion 4). If not linked, leave it and keep the existing backlog note. The research/plan must record which way it went and why.
- **D-04:** Keep today's behaviour and only add the cleanup. When a component fails partway through startup, stop and join everything that already started, then let the original failure surface unchanged. It goes into the existing bounded controller auto-restart (`ServiceRestart`, RECOV-01 / Phase 114) and, once that budget is exhausted, the existing `server.up=False` web-UI error. The web server keeps running.
- **D-05:** No degraded mode (never run with only some components started, which could make the app look healthy while scanning is off, a safety risk for auto-delete). No new "exit the whole container" behaviour.
- **D-06:** The original startup exception must not be masked by a secondary exception raised during the cleanup it triggers. Cleanup errors are logged; the original failure is what propagates.
- **D-07:** Injected-failure unit tests, RED-first, for each gap: a failure injected into the startup of each scanner process and of each controller component after earlier ones started (started children are stopped, the failure still surfaces), and into the cleanup of each component (the remaining components are still cleaned up, the first failure is logged). Plus a short live restart check on the NAS sandbox `seedsyncarr-test` on this phase's PR CI staging image pinned by digest: a few `docker restart` cycles, each must log no lftp/scanner shutdown errors and come back up normally (`/server/status` 200, scans resume). No live transfer/import tracking through a restart (Phase 122 D-06(d) already proved credit persistence). The sandbox is restored to its original pin afterwards with a fresh-session check; production is read-only fingerprint checks only.

### Claude's Discretion

- Exact shape of the cleanup-on-partial-start code (e.g. per-component try blocks mirroring `Controller.exit()`'s existing pattern, or tracking which components started). It must follow the pattern already in `Controller.exit()` rather than introduce a new lifecycle abstraction.
- Whether `ScanManager.stop()`/`_terminate_and_join_all()` and `FileOperationManager.stop()` get per-process independent cleanup, provided the remaining processes are always terminated and joined and the first error is logged.
- Which component's startup/cleanup gaps exist beyond those already spotted (research confirms the full list, including `ControllerJob`, `FileOperationManager`, the mp logger and the top-level job start in `seedsyncarr.py`).
- Bounded timeouts for any new join/terminate waits (no unbounded hangs at shutdown).

### Deferred Ideas (OUT OF SCOPE)

- Modern RAR `.partN.rar` volumes extracted once per volume (`ExtractDispatch.__coalesce_extractions`). Not a lifecycle issue; stays out of Phase 123.
- DEFER-SHUTDOWN replacement if the D-01 investigation shows it is unrelated to the restart errors (D-03). **Research verdict below: not linked — stays a backlog note, sleep is kept.**
- Phase 122 re-review follow-ups WR-04 (Arr key normalization) and IN-04/IN-05 (post-transfer window edge cases): already in the ROADMAP Backlog; not part of Phase 123.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIFE-01 | When startup of the scanner or another component fails partway, already-started children are cleaned up, demonstrated by an injected-failure test | Full gap inventory below (`ScanManager.start()`, `Controller.start()`, `Job.run()`'s unguarded `setup()`) with exact injection points and existing test patterns to extend (`test_scan_manager.py`, `test_job.py`, `test_controller_job.py`) |
| LIFE-02 | When cleanup of one component fails, cleanup is still attempted for the remaining components, demonstrated by an injected-failure test; existing per-component controller cleanup, auto-delete shutdown guards and lock ordering are preserved | `Controller.exit()`'s top-level per-component loop already satisfies this; gaps are one level down, inside `ScanManager._terminate_and_join_all()` and `FileOperationManager.stop()`'s reservation-release loop. Existing regression suite identified (`test_auto_delete.py` shutdown/lock-order tests) that must stay green |
</phase_requirements>

## Summary

The restart errors from Phase 122 (D-01) and the generic LIFE-01/02 gaps are related but **mechanically distinct**, and the research below separates them cleanly so the plan doesn't conflate a "missing try/except" bug with an "OS signal race" bug.

**The LIFE-01/02 gaps are ordinary missing-exception-safety bugs**, fully reproducible in unit tests with mocks/fakes — no real process spawning needed:
- `ScanManager.start()` and `Controller.start()` only set their `__started` flag at the very end, so a failure partway through startup leaves earlier-started children running and silently un-cleaned (their respective `stop()`/`exit()` becomes a no-op because `__started` is still `False`).
- `common/job.py`'s `Job.run()` wraps `execute()` in a `try/except` that captures `exc_info` and calls `cleanup()`, but **does not wrap `setup()` at all**. A `setup()` failure (i.e. `Controller.start()` raising) propagates straight out of the thread's `run()` method uncaught: `cleanup()` never runs (so `Controller.exit()` is never called — any already-started children are leaked), `exc_info` is never set (so `propagate_exception()` is a no-op forever), and the main loop never learns the controller died. **This is the central, most severe gap for LIFE-01's "the failure still surfaces" criterion** — it affects `ControllerJob` and, as shared base-class infrastructure, `WebAppJob` too.
- One level below `Controller.exit()` (which already does per-component independent cleanup correctly — the reusable pattern CONTEXT.md points to), `ScanManager._terminate_and_join_all()` and `FileOperationManager.stop()`'s per-wrapper reservation-release loop are **not** internally fault-isolated: one raising `terminate()`/`join()`/`release()` skips the rest.

**The D-01 restart errors are a genuine OS-level signal race, not a missing try/except**, and are only partially unit-provable:
- The entrypoint runs the app under `tini -g` (verified live via `docker inspect seedsyncarr-test`, and in `src/docker/build/docker-image/entrypoint.sh`). `-g` makes tini deliver the container's SIGTERM to the **entire process group** of its direct child (the python process), per tini's own documentation.
- The scanner/extract/delete child processes (`AppProcess` subclasses) are plain `multiprocessing.Process` objects using the OS-default start method, which is **fork** on Linux — fork does not create a new process group, so these children share the python process's group and receive the SIGTERM directly. `AppProcess.run()` then explicitly resets `SIGTERM`/`SIGINT` to `SIG_DFL` in each child (a deliberate, documented fix for a join-deadlock problem), so each child's default reaction to that direct SIGTERM is **immediate termination with no cleanup** — before the app's own orderly `ScanManager.stop()` ever gets a chance to run.
- `ScanManager._check_process_health()` — called every ~0.5s from `ControllerJob`'s own execute loop — has no way to know a shutdown is already in progress. On the very next cycle after the OS kills the scanners, it correctly observes they're dead and (today) treats that as an unexpected failure: logs an ERROR and raises `ScannerProcessDiedError`. This is **not a logic bug in the health check** — it is working exactly as designed; the design just doesn't account for "the process group just got SIGTERM'd by the container."
- The `lftp` child is **not** hit by this same direct signal: `pexpect.spawn()` → `ptyprocess.PtyProcess.spawn()` uses `pty.fork()` (`os.forkpty()`), whose child calls `setsid()` to acquire the controlling tty — this makes lftp the leader of a brand-new session/process group, different from the python process's group, so tini's group-wide kill does not reach it directly. lftp is still alive when `Controller.exit()` → `Lftp.exit()` → `self.__process.close(force=True)` runs; `ptyprocess`'s own escalating `SIGHUP→SIGCONT→SIGINT→SIGKILL` sequence (0.1s between each) is what then sometimes fails to observe death in time, raising `PtyProcessError('Could not terminate the child.')`.
- Live log forensics (below) show the scanner-death error on **every single observed restart** (deterministic — matches the always-true OS-race explanation), while the lftp "could not terminate" error appears on only **one of ~20** observed restarts, and that one restart happened 7 seconds after an active transfer had just been credited as "still transferring" — a plausible but not yet proven correlation (active in-flight transfer at SIGTERM time) that the D-07 live check should specifically probe.
- **D-03 verdict: the DEFER-SHUTDOWN sleep is NOT linked to these errors.** The OS delivers the process-group SIGTERM to the forked scanner children at the kernel level, instantaneously and independently of anything the python main thread does; shortening, lengthening, or removing the 0.5s sleep cannot change whether that direct signal kills them. Live log timestamps additionally show the `ControllerJob` thread self-detecting the dead scanners and running `Controller.exit()` to completion in under ~1 second, before the main thread's 0.5s DEFER-SHUTDOWN sleep has even elapsed — the self-triggered path, not the sleep-gated path, is what's actually running `Lftp.exit()` in the failing case. Per D-03, the sleep is kept as-is; the existing DEFER-SHUTDOWN backlog note stays unchanged.

**Primary recommendation:** Fix the LIFE-01/02 gaps with the mechanical, fully-unit-testable changes (track which components started and clean them up independently in `Controller.start()`/`ScanManager.start()`; wrap `Job.run()`'s `setup()` call the same way `execute()` is already wrapped; fault-isolate `ScanManager._terminate_and_join_all()` and `FileOperationManager.stop()`'s per-wrapper loop). For D-01, make the scanner health check "shutdown-aware" (the smallest lever available — e.g. `ControllerJob.execute()` or `ScanManager.propagate_exceptions()` treating a dead-scanner observation as benign, not an error, once the job's own `shutdown_flag` is set) so a normal restart no longer logs a false-alarm ERROR/exception and routes cleanup through the ordinary path instead of racing it — then prove the restart is clean with the D-07 live check, which is also the only way to confirm whether this removes or merely narrows the intermittent lftp failure.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scanner process lifecycle (start/stop 3 `AppProcess` children) | Backend process layer (`ScanManager`) | OS/container (signal delivery via `tini -g`) | Pure in-process-tree lifecycle management; the container's signal-forwarding policy is an external constraint this tier must tolerate, not something it controls |
| Controller component orchestration (scan manager, file-op manager, mp logger, lftp manager) | Backend process layer (`Controller`) | Job/thread layer (`ControllerJob`) | `Controller` owns construction/start/exit of its collaborators; `ControllerJob` is a thin `Job` adapter that just calls `start()`/`process()`/`exit()` |
| Job thread lifecycle (setup/execute/cleanup, exception capture) | Backend process layer (`common/job.py: Job`) | — | Shared base class for both `ControllerJob` and `WebAppJob`; the setup()-exception gap found here is infrastructure, not specific to the controller |
| Top-level process supervision, signal handling, bounded auto-restart | Backend service entrypoint (`seedsyncarr.py: Seedsyncarr`/`main()`) | OS/container (SIGTERM delivery, tini reaping) | Owns the main thread's signal handler, the `ServiceExit`/`ServiceRestart` control flow and RECOV-01's bounded auto-restart; depends on `Job.propagate_exception()` correctly surfacing child failures |
| External process (lftp) lifecycle | Backend process layer (`LftpManager`/`Lftp`) | OS/container (process-group vs. session isolation via `setsid()`) | `Lftp.exit()` already force-closes on graceful-exit failure; the open question is runtime timing of lftp's own termination under `SIGKILL`, not missing cleanup code |
| Container signal/init handling | OS/container (`tini -g`, entrypoint.sh) | — | Out of this phase's code-change scope (D-01 does not propose touching the entrypoint); documented here because it is the causal trigger the rest of the phase must account for |

## Standard Stack

No new third-party packages are needed for this phase. All fix candidates reuse libraries already in the dependency tree:

| Library | Version (installed, verified) | Purpose in this phase | Why no change needed |
|---------|------|---------|--------------|
| `pexpect` / `ptyprocess` | Installed in `src/python/poetry.lock`; resolved venv path confirms `ptyprocess` is present at `.../site-packages/ptyprocess/ptyprocess.py` [VERIFIED: local venv inspection] | Drives `Lftp`'s pty-spawned `/usr/bin/lftp` process; its `close(force=True)`/`terminate(force=True)` is the exact call raising `PtyProcessError` | Already in use; the gap is a timing/signal-isolation issue, not a missing feature of the library |
| `tini` | Pinned via `apt` in the Dockerfile build stage (`src/docker/build/docker-image/Dockerfile:96`); exact version not re-verified this session | Container PID 1 / zombie reaper / `-g` signal-group forwarder | Already in use; D-01 does not propose changing the entrypoint or tini invocation |
| Python stdlib `multiprocessing`, `threading`, `signal` | stdlib | Scanner/extract/delete child processes; `Job`'s `shutdown_flag`; signal handler registration | No new dependency; fixes are code-level changes to existing usage |

**Installation:** None — no `pip`/`poetry add` needed this phase.

**Version verification:** Not applicable (no new packages). If a future plan task wants to confirm the exact `tini`/`pexpect`/`ptyprocess` versions shipped in the image under test, run:
```bash
# tini version baked into the image
ssh nas 'sudo /usr/local/bin/docker exec seedsyncarr-test tini --version'
# pexpect/ptyprocess versions in the poetry lock
grep -A2 '^name = "ptyprocess"' src/python/poetry.lock
grep -A2 '^name = "pexpect"' src/python/poetry.lock
```

## Package Legitimacy Audit

Not applicable — this phase installs no new external packages. `slopcheck`/registry verification is skipped per the package-legitimacy protocol's own scope ("whenever this phase installs external packages"); none are installed here.

**Packages removed due to slopcheck [SLOP] verdict:** none (no packages evaluated)
**Packages flagged as suspicious [SUS]:** none (no packages evaluated)

## Architecture Patterns

### D-01 root cause: signal-delivery race diagram

```
docker restart seedsyncarr-test
        │
        │ SIGTERM to container PID 1
        ▼
   tini (-g flag, verified live via `docker inspect`:
         Entrypoint=.../entrypoint.sh, no StopSignal/Init override)
        │
        │ "-g": kill(-pgid, SIGTERM)  [CITED: github.com/krallin/tini README,
        │        "Process group killing"]
        │        -- delivered to EVERY process sharing the python
        │        process's process group, at the kernel level,
        │        effectively simultaneously --
        │
        ├──────────────► python main process (pid == pgid, group leader)
        │                     │
        │                     │ Seedsyncarr.signal() handler fires
        │                     │ raise ServiceExit()  (interrupts whatever
        │                     │ the main thread was doing, e.g. the
        │                     │ 0.5s MAIN_THREAD_SLEEP_INTERVAL_IN_SECS
        │                     │ wait in the request loop)
        │                     ▼
        │              run()'s `except Exception:` block:
        │              log "Exiting Seedsyncarr"
        │              sleep 0.5s (DEFER-SHUTDOWN)        <- NOT the cause,
        │              controller_job.terminate()             see D-03 verdict
        │              webapp_job.terminate()
        │              controller_job.join() / webapp_job.join()
        │
        ├──────────────► RemoteScanner/LocalScanner/ActiveScanner
        │                (multiprocessing.Process, forked -> SAME
        │                 process group; AppProcess.run() reset
        │                 SIGTERM/SIGINT to SIG_DFL at process start)
        │                     │
        │                     ▼
        │              process terminates IMMEDIATELY (SIG_DFL default
        │              action), with NO chance to run any cleanup --
        │              this happens on roughly the same kernel
        │              timescale as the main process receiving SIGTERM,
        │              i.e. essentially instantly, long before any
        │              python-level orderly shutdown code has run
        │
        └──────────X────► lftp (pexpect.spawn -> pty.fork()/os.forkpty();
                            the pty child calls setsid(), becoming the
                            leader of a NEW session/process group)
                            -- NOT reached by tini's group-wide kill --
                            lftp stays alive, oblivious to the restart,
                            until something inside the app talks to it

Meanwhile, independently, on the ControllerJob THREAD (not interrupted
by the SIGTERM; running its own ~0.5s execute() loop):

   ControllerJob.execute()
     -> Controller.process()
        -> __propagate_exceptions()
           -> ScanManager.propagate_exceptions()
              -> _check_process_health()
                 -- finds Remote/Local/ActiveScanner already dead
                    (killed directly by the OS signal above) --
                 -> logs ERROR "Scanner process(es) died unexpectedly"
                 -> raises ScannerProcessDiedError
     (Job.run()'s except-block catches it, sets exc_info + shutdown_flag,
      calls cleanup() RIGHT HERE -- NOT triggered by and NOT waiting for
      the main thread's terminate()/join() sequence above)
        -> ControllerJob.cleanup() -> Controller.exit()
           -> for component in (lftp, scanner, file_ops, mp_logger):
                try: stop()  # lftp.exit() runs FIRST
                except: log "Error stopping {component}"
              -> Lftp.exit(): kill_all(); sendline("exit");
                 finally: self.__process.close(force=True)
                   -> ptyprocess escalates SIGHUP/SIGCONT/SIGINT/SIGKILL,
                      0.1s apart; if lftp is still alive after SIGKILL+0.1s
                      (observed correlated with an active in-flight
                      transfer in the one live occurrence captured),
                      raises PtyProcessError('Could not terminate the
                      child.') -- logged, loop continues to scanner/
                      file_ops/mp_logger (already-correct per-component
                      isolation in Controller.exit())
```

**Three independent shutdown triggers converge on the same restart**, which is why the sequence is hard to reason about from the code alone: (1) the main thread's own SIGTERM handler, (2) the OS directly killing the scanner children via the process-group signal, and (3) the `ControllerJob` thread self-detecting (2) and short-circuiting its own cleanup ahead of (1)'s orderly path. The smallest, safest lever is making (3) shutdown-aware so it stops firing a false alarm — trying to "outrace" (2) from Python is not possible (kernel-level signal delivery to the forked children cannot be beaten by any python-level code path), and the main thread's own SIGTERM-handling sequence (1) is already working as intended.

**Live verification performed this session (read-only, no restarts):**
```
$ ssh nas 'sudo /usr/local/bin/docker inspect seedsyncarr-test --format \
  "Entrypoint={{json .Config.Entrypoint}} Init={{.HostConfig.Init}} \
   StopSignal={{.Config.StopSignal}} StopTimeout={{.Config.StopTimeout}}"'
Entrypoint=["/usr/local/bin/entrypoint.sh"] Init=<nil> StopSignal= StopTimeout=<nil>
```
Confirms the running container has no `--init`/`StopSignal`/`StopTimeout` override — it relies entirely on `entrypoint.sh`'s own `exec gosu "${PUID}:${PGID}" tini -g -- "$@"` for SIGTERM delivery, exactly as the script says. [VERIFIED: live `docker inspect`]

Grepping the sandbox's existing app log (`/volume1/docker/v5test/seedsyncarr/log/seedsyncarr.log`, read-only) for the two error strings across its full retained history found the scanner-death error on **every** restart observed (2026-10-12, 10-15, 10-22 ×3, 10-23 ×~12) and the lftp-termination error on exactly **one** of those — 2026-10-23 14:14:38, ~7s after a webhook credited `SSA122.Bravo3.S01E01.mkv` as "root still transferring" (an active in-flight transfer at SIGTERM time). The immediately preceding restart at 14:10:08 (file `STOP`ped and idle beforehand) got the scanner-death error but no lftp error. [VERIFIED: live log excerpt, read-only `grep`/`sed`]

### Recommended fix shape (Claude's Discretion — presented as the leading, smallest-footprint candidate)

1. **`common/job.py` — `Job.run()`:** wrap `self.setup()` the same way `execute()` is already wrapped (catch `Exception`, set `self.exc_info`, set `self.shutdown_flag`, still proceed to `self.cleanup()`). This is the one change every LIFE-01 "the failure still surfaces" test depends on — without it, no amount of cleanup logic inside `Controller.start()` ever reaches `propagate_exception()`/the main loop.
   ```python
   # common/job.py — current (gap)
   self.logger.debug("Calling setup for {}".format(self.name))
   self.setup()
   self.logger.debug("Finished setup for {}".format(self.name))

   # Proposed shape (mirrors the existing execute() except-block below it)
   self.logger.debug("Calling setup for {}".format(self.name))
   try:
       self.setup()
   except Exception:
       self.exc_info = sys.exc_info()
       self.logger.exception("Caught exception in setup for {}".format(self.name))
       self.shutdown_flag.set()
       self.cleanup()
       self.logger.debug("Finished cleanup for {}".format(self.name))
       self.logger.debug("Thread {} stopped".format(self.name))
       return
   self.logger.debug("Finished setup for {}".format(self.name))
   ```
   **Caution found during research:** this change makes `cleanup()` reachable after a `setup()` that never fully ran. `ControllerJob.cleanup()` is already safe today (`Controller.exit()` guards on `self.__started`), but `WebAppJob.cleanup()` is **not** — it unconditionally calls `self.__server.stop()` and `self.__server_thread.join()`, both of which are `None` until `setup()` finishes assigning them. No currently-reachable `WebAppJob.setup()` statement realistically raises before both are assigned (this is a defensive/latent gap, not a reproducing bug like the controller-side ones), but since `Job` is shared infrastructure, add a `None`-guard there too so the shared fix doesn't introduce a new failure mode.

2. **`Controller.start()` / `ScanManager.start()`:** track which components/processes actually started (not just a single `__started` boolean flipped at the end) and, on a later failure, stop/join only what started, in a per-component `try`/`except Exception: self.logger.exception(...)` loop mirroring `Controller.exit()`'s existing tuple-of-(name, callable) pattern — then **re-raise the original exception unchanged** (D-06: do not let a cleanup failure mask it).

3. **`ScanManager._terminate_and_join_all()` / `FileOperationManager.stop()`:** fault-isolate each process's `terminate()`+`join()` (and each wrapper's `reservation.release()`) the same way `Controller.exit()` already isolates its four components — first exception logged, remaining processes/wrappers still get their turn.

4. **D-01 specifically — make the scanner health check shutdown-aware.** The smallest-footprint version touches only `ControllerJob.execute()`:
   ```python
   # controller/controller_job.py — current
   @overrides(Job)
   def execute(self):
       self.__controller.process()
       self.__auto_queue.process()

   # Candidate shape
   @overrides(Job)
   def execute(self):
       if self.shutdown_flag.is_set():
           return
       self.__controller.process()
       self.__auto_queue.process()
   ```
   This alone only helps if `shutdown_flag` is already set by the time `execute()` runs — which requires the signal handler to set it synchronously rather than only via the delayed main-loop `terminate()` call, so would need pairing with a small change in `Seedsyncarr.signal()` to set both jobs' `shutdown_flag` immediately. Even then this narrows, but does not provably eliminate, the race (the OS can still kill a scanner mid-`execute()`, one cycle before `shutdown_flag` is observed). The more robust alternative — making `ScanManager._check_process_health()`/`propagate_exceptions()` itself accept an "is shutting down" signal and demote the dead-scanner observation from ERROR+raise to INFO/no-op when shutdown is already requested — is more invasive (threads a new piece of state from `Job` down into `ScanManager`) but closes the race regardless of which thread observes the dead processes first. **This tradeoff is a planning decision; both candidates are unit-testable (inject "shutdown already requested" + dead scanner mocks, assert no ERROR/no raise) and D-07's live check is what actually proves whether either one makes the lftp error go away too**, since lftp's own termination timing is a separate mechanism (see Summary).

### Existing reusable pattern: `Controller.exit()`

```python
# controller/controller.py — ALREADY correct at this level; the pattern
# every new per-component cleanup loop in this phase should mirror
for component, stop in (("lftp", self.__lftp_manager.exit),
                        ("scanner", self.__scan_manager.stop),
                        ("file operations", self.__file_op_manager.stop),
                        ("multiprocessing logger", self.__mp_logger.stop)):
    try:
        stop()
    except Exception:
        self.logger.exception("Error stopping {} during controller exit".format(component))
```
This already satisfies LIFE-02 at the `Controller.exit()` level and is why the observed sandbox restart still logged "Exited controller" / "Exited successfully" even after the lftp failure — the loop correctly moved on to scanner/file-ops/mp-logger cleanup afterward. The LIFE-02 gaps are one level **below** this loop (inside `ScanManager`/`FileOperationManager`), not in it.

### Anti-Patterns to Avoid

- **Trying to "win the race" against the OS signal from Python.** No python-level timing change (shorter/longer sleeps, reordering `terminate()`/`join()` calls, etc.) can run faster than the kernel delivering `SIGTERM` to the forked children via `killpg()` — that delivery is already instantaneous relative to anything in the interpreter. The fix must change what the app *does* when it observes an already-shutting-down process, not try to out-sprint the signal.
- **A single `__started` boolean for a multi-step startup sequence.** Both `ScanManager.start()` and `Controller.start()` use this pattern today; it is exactly why a partial failure's already-started children are never cleaned up (the guard that would call `stop()`/`exit()` is false). Track per-component/per-process started state instead.
- **Letting a new cleanup step's own exception replace the original failure.** `Controller.exit()`'s existing `try/except Exception: self.logger.exception(...)` per component already avoids this; any new partial-start cleanup must use the same shape and re-raise the *original* caught exception afterward, unchanged (D-06).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting "has a shutdown already been requested" from inside a worker thread/process-health check | A new polling thread, a new lock, a bespoke signal/flag protocol | The `Job`'s existing `shutdown_flag` (`threading.Event`), threaded through as a plain read, or the existing `Controller.__shutdown_event` pattern already used for the auto-delete guard (BUG-03/D-03's unrelated-but-analogous shutdown flag) | Two purpose-built, already-tested shutdown-signaling primitives exist in this codebase; adding a third would be the "new lifecycle abstraction" the CONTEXT.md discretion note explicitly rules out |
| Terminating a child process "for real" with a bounded timeout | A custom signal-escalation ladder (SIGTERM → wait → SIGKILL) | `AppProcess.terminate()` (already does exactly this, bounded at ~1s) for multiprocessing children; `ptyprocess.PtyProcess.close(force=True)`/`terminate(force=True)` (already does SIGHUP→SIGCONT→SIGINT→SIGKILL, 0.1s apart) for the lftp pty child | Both already exist and are exercised by the current code; the gap is callers not isolating each other's failures, not a missing termination primitive |
| Per-component independent cleanup-with-logging | A generic "lifecycle manager"/"component registry" abstraction | The existing `for component, stop in (...): try: stop() except Exception: self.logger.exception(...)` tuple pattern in `Controller.exit()`, copied verbatim into the one or two new call sites that need it | CONTEXT.md explicitly forbids introducing a new lifecycle abstraction; the existing tuple pattern is already proven, tested indirectly via `test_auto_delete.py`, and trivially copyable |

**Key insight:** every fix needed in this phase is a small, mechanical extension of a pattern the codebase already uses successfully in at least one place (`Controller.exit()`'s per-component loop, `Job.run()`'s `execute()`-exception handling, `AppProcess.terminate()`'s bounded escalation). There is no missing capability here — only inconsistent application of existing capabilities across sibling code paths.

## Common Pitfalls

### Pitfall 1: Fixing `Controller.start()`'s partial-failure cleanup without also fixing `Job.run()`

**What goes wrong:** A plan that only adds per-component cleanup tracking inside `Controller.start()` (so it internally stops what it started before re-raising) will clean up the leaked processes correctly, but the exception raised by `ControllerJob.setup()` still propagates out of `Job.run()` uncaught — the thread dies silently, `exc_info` is never set, and the main loop never learns anything failed. LIFE-01's "the failure still surfaces" criterion is **not** satisfiable without also touching `common/job.py`.
**Why it happens:** `Job.run()` only wraps `execute()` in a try/except; `setup()` is called bare.
**How to avoid:** Fix `Job.run()` first (or in the same plan wave); write the regression test at the `Job`/`ControllerJob` level (a fake job whose `setup()` raises, asserting `propagate_exception()` re-raises it and `cleanup_run` is `True`), not only at the `Controller.start()` unit level.
**Warning signs:** A test that mocks `ControllerJob`/`Controller` directly and asserts `exit()`/`stop()` were called will pass even with this gap present, because it never exercises the real `Job.run()` thread loop. Use a real `Job` subclass (like the existing `DummyFailingJob` in `test_job.py`) for at least one test, not only mocks.

### Pitfall 2: Treating the lftp "Could not terminate the child" error as the same bug as the scanner-death error

**What goes wrong:** Applying the scanner's "skip the error during shutdown" fix to lftp too, assuming it's the same race. It isn't — lftp is in a different process group (its pty child calls `setsid()`), so it is never directly signaled by `tini -g`; the live evidence shows the lftp failure correlates with an *active in-flight transfer*, not with every restart. A fix that silences the lftp error unconditionally (rather than fixing the underlying timing) could hide a genuine future problem (e.g. a real stuck lftp process that should be investigated).
**Why it happens:** Both errors show up in the same restart-triggered log burst, making them look like one event.
**How to avoid:** Keep the two fixes conceptually and in the test suite separate: the scanner fix is about suppressing a false-alarm exception during an already-requested shutdown; the lftp fix (if any is needed beyond "the existing Controller.exit() per-component catch already contains the blast radius") is about confirming via the D-07 live check whether an active-transfer-at-shutdown-time scenario needs a longer per-signal wait budget in `ptyprocess` terms, or whether it's simply an acceptable, already-logged-and-contained edge case.
**Warning signs:** A plan task description that says "fix the restart errors" as a single undifferentiated unit, with one test covering both.

### Pitfall 3: A new partial-start cleanup path calling `stop()`/`exit()` on a component that was never started

**What goes wrong:** `MultiprocessingLogger.stop()` calls `self.__listener.join()` unconditionally — but the listener `threading.Thread` is only ever `.start()`-ed by `MultiprocessingLogger.start()`. Joining a thread that was never started raises `RuntimeError: cannot join thread before it is started`. If `Controller.start()`'s new partial-cleanup logic blindly calls `stop()` on every component regardless of whether it reached `start()`, this fires exactly when `mp_logger.start()` (the *last* step in `Controller.start()`'s current ordering) was never reached because an earlier step failed.
**Why it happens:** Unlike `ScanManager.stop()` (`if not self.__started: return`) and `FileOperationManager.stop()` (guards the extract-process stop, though not the reservation-release loop before it), `MultiprocessingLogger.stop()` has no "never started" guard at all.
**How to avoid:** Either (a) only call `stop()`/`exit()` on components confirmed to have started (the per-component tracking from the recommended fix shape above naturally does this), or (b) add a "safe to call even if never started" guard to `MultiprocessingLogger.stop()` as a small defensive fix. Verify this specifically with a unit test: construct a `MultiprocessingLogger`, call `stop()` without ever calling `start()`, assert no exception.
**Warning signs:** A new RED test for "`Controller.start()` fails before `mp_logger.start()`, verify started components are cleaned up" that turns GREEN for the wrong reason, or crashes with `RuntimeError` instead of cleanly reaching the assertion.

### Pitfall 4: Masking the original startup/shutdown exception with a cleanup-time exception (D-06)

**What goes wrong:** Anywhere a cleanup step is added inside an `except`/`finally` block without its own inner `try/except`, a failure during that cleanup step replaces the exception Python propagates, hiding the original cause. The codebase already has one existing instance of this exact risk outside the places CONTEXT.md names explicitly: `Seedsyncarr.run()`'s top-level `except Exception:` block calls `self.persist()` (which can raise `OSError`/`PersistError` writing three files to disk) with no inner guard, *after* the original shutdown-triggering exception was caught but *before* the bare `raise` that's supposed to re-propagate it — if `persist()` raises, the original exception is masked.
**Why it happens:** Natural to write cleanup code as a flat sequence of calls inside the handler without separately protecting each one.
**How to avoid:** Every new cleanup call added during this phase should sit inside its own `try/except Exception: self.logger.exception(...)` (mirroring `Controller.exit()`'s pattern), never bare inside a handler that's also responsible for re-raising something else.
**Warning signs:** None of the existing tests exercise `Seedsyncarr.run()`'s shutdown-path `persist()` call failing; this is a **lower-confidence, secondary finding** (likely out of this phase's primary `Controller`/`ScanManager`/`FileOperationManager` scope per CONTEXT.md's specifics, but flagged per D-06's general principle for the planner to decide whether it's worth a small, separate fix here or a backlog note).

## Code Examples

### Existing test pattern to extend for the `Job.run()` `setup()` gap
```python
# tests/unittests/test_common/test_job.py — EXISTING pattern (execute() only)
# Source: src/python/tests/unittests/test_common/test_job.py
class DummyFailingJob(Job):
    def setup(self):
        self.cleanup_run = False

    def execute(self):
        raise DummyError()

    def cleanup(self):
        self.cleanup_run = True

class TestJob(unittest.TestCase):
    def test_exception_propagates(self):
        context = MagicMock()
        job = DummyFailingJob("DummyFailingJob", context)
        job.start()
        job.join(timeout=5.0)
        self.assertFalse(job.is_alive(), "Job thread did not complete within timeout")
        with self.assertRaises(DummyError):
            job.propagate_exception()
```
A mirrored `DummySetupFailingJob` (raises in `setup()` instead of `execute()`) with the same two assertions (`propagate_exception()` re-raises; `cleanup_run is True`) is the RED-first regression test for the `Job.run()` fix — it fails today because `cleanup_run` stays `False` and `propagate_exception()` raises nothing (since `exc_info` was never set).

### Existing test pattern for per-process cleanup isolation
```python
# tests/unittests/test_controller/test_scan_manager.py — EXISTING pattern
# (asserts ALL THREE processes get terminate()+join(), happy path only)
@patch('controller.scan_manager.ScannerProcess')
@patch('controller.scan_manager.ActiveScanner')
@patch('controller.scan_manager.LocalScanner')
@patch('controller.scan_manager.RemoteScanner')
def test_stop_terminates_and_joins_all_processes(
        self, mock_remote_scanner, mock_local_scanner,
        mock_active_scanner, mock_scanner_process):
    mock_process = MagicMock()
    mock_scanner_process.return_value = mock_process
    manager = ScanManager(self.mock_context, self.mock_mp_logger)
    manager.start()
    manager.stop()
    self.assertEqual(mock_process.terminate.call_count, 3)
    self.assertEqual(mock_process.join.call_count, 3)
```
The LIFE-02 regression test for `_terminate_and_join_all()` extends this by giving each of the three mocked processes a *distinct* `MagicMock` (via `side_effect`, as already done in `test_pop_latest_results_returns_results_from_all_scanners` in the same file) and making ONE of them raise on `terminate()`, then asserting the other two still got `terminate()`+`join()` and the manager's `logger.exception`/`logger.error` was called once (first error logged, not swallowed).

### Existing lock-ordering/shutdown-guard tests that must stay green (success criterion 3)
```python
# tests/unittests/test_controller/test_auto_delete.py — DO NOT regress
class TestAutoDeleteShutdown(BaseAutoDeleteTestCase):
    def test_exit_cancels_all_pending_timers(self): ...
    def test_exit_without_pending_timers(self): ...

# Lock-order / BUG-03 / WR-02 guard tests in the same file:
#   test_a_entry_guard_no_delete_when_shutdown_set_before_invoke
#   test_b_final_commit_guard_no_delete_when_shutdown_set_mid_callback
#   test_c_positive_control_delete_fires_when_no_shutdown
#   test_d_criterion1_no_timer_armed_after_exit
```
These access `Controller`'s name-mangled private state directly (e.g. `self.controller._Controller__shutdown_event.set()`, `self.controller._Controller__started = True`) — the established test style in this codebase (also noted as a known DEFER-TESTHARDEN pattern). New LIFE-01/02 tests should follow the same name-mangled-access style for consistency, not introduce a different testing approach.

## State of the Art

Not applicable in the usual "library version drift" sense — this is a bug-fix phase in first-party code using long-stable stdlib/`pexpect`/`tini` mechanisms. No deprecated APIs or upstream behavior changes are involved.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The exact `tini` version baked into the current sandbox image was not re-verified this session (only its `-g`/no-override invocation was confirmed live) | Standard Stack, Architecture Patterns | Low — the `-g` process-group-kill behavior cited is from tini's own README and has been stable across tini's release history; a version check is a one-command confirmation if the planner wants it, not a blocker |
| A2 | The correlation between the lftp termination failure and an active in-flight transfer at SIGTERM time is drawn from a single observed instance (n=1) against ~20 clean restarts in the retained sandbox log | Summary, Architecture Patterns, Pitfall 2 | Medium — if the correlation doesn't hold under the D-07 live check's deliberate active-transfer-at-restart test, the planner needs a fallback (e.g. treat the lftp failure as an already-contained, acceptable edge case rather than something requiring a targeted fix) |
| A3 | `WebAppJob.setup()`'s `MyWSGIRefServer(...)` construction and `Thread(...)` construction are assumed not to realistically raise before `self.__server`/`self.__server_thread` are assigned, based on reading `bottle.ServerAdapter.__init__` usage and `threading.Thread.__init__`'s normal contract, not from an exhaustive proof | Pitfall 1, recommended fix shape | Low — even if wrong, the proposed defensive `None`-guard in `WebAppJob.cleanup()` costs nothing and closes the gap either way |

**If this table is empty:** N/A — see above.

## Open Questions (RESOLVED)

1. **Does the chosen D-01 fix shape (shutdown-aware health check vs. shutdown-aware `execute()` early-return vs. both) also eliminate the intermittent lftp "Could not terminate the child" error, or only the deterministic scanner-death error?**
   - What we know: the scanner-death error is a direct, deterministic consequence of the OS signal hitting the forked children; the lftp error's mechanism (why `ptyprocess`'s SIGKILL-escalation sometimes fails to observe death within ~0.4s) is explained structurally (lftp is NOT directly signaled, so whatever delays it is internal — possibly an active transfer/network teardown) but not proven to be fixed by making the controller's OWN exit path calmer/later.
   - What's unclear: whether simply reaching `Lftp.exit()` a little later (via the ordinary, non-panicked shutdown path instead of the self-triggered one) gives lftp enough extra time to have already wound down a transfer on its own, or whether the ~0.4s SIGKILL-escalation budget itself needs lengthening regardless of when it's invoked.
   - **RESOLVED (planning):** deferred to the D-07 live check in 123-06/07 (idle + active-transfer cycles); a persisting lftp error is a failure checkpoint to the owner.
   - Recommendation: Treat the two as separately provable by D-07's live check — run restart cycles both idle and with an active transfer in flight, and record whether the lftp error still appears in the active-transfer case after the scanner-death fix lands. If it still appears, that's new evidence the lftp side needs its own (still small, evidence-backed) follow-up — possibly out of this phase if `Controller.exit()`'s existing per-component catch is judged sufficient containment (the container still restarts cleanly either way, per every observed log).

2. **Should `Controller.__init__`'s eager, unconditional construction of `LftpManager`/`Lftp` (which immediately spawns the lftp pty process at construction time, before `Controller.start()` is ever called) be brought into LIFE-01's scope?**
   - What we know: if `Controller.__init__` itself raises *after* `LftpManager`'s constructor has run but *before* `__init__` finishes (e.g. a later collaborator's constructor raising), the already-spawned lftp pty process is leaked with no handle to close it, since the partially-constructed `Controller` object is never returned/usable.
   - What's unclear: how likely this is in practice (most of `Controller.__init__`'s later steps construct plain Python objects unlikely to raise) and whether CONTEXT.md's "another component" language in D-04 was meant to reach constructor-time failures, not just `start()`-time ones.
   - **RESOLVED (planning):** out of scope for Phase 123; recorded for the backlog in 123-07's deferred-items.md.
   - Recommendation: Flag for planner judgment; CONTEXT.md's "Specific Ideas" section only names `ScanManager.start()`/`Controller.start()`, not `Controller.__init__`, suggesting this is a lower-priority, narrower edge case appropriate for a backlog note unless the planner wants it folded in cheaply (e.g. nothing dies is actually at risk here that `Controller.exit()` doesn't already protect once the object exists — the risk window is specifically "exception during `__init__` itself").

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| NAS sandbox `seedsyncarr-test` (SSH via `ssh nas`, Docker via `sudo /usr/local/bin/docker`) | D-07 live restart check | ✓ (confirmed live this session) | Image `sha256:5b801f83...` (1.7.6, per `docker inspect .Image`) | None needed — required for D-07 |
| `tini -g` entrypoint configuration | D-01 root-cause reproduction | ✓ (confirmed live via `docker inspect`: no `StopSignal`/`Init` override, entrypoint matches `entrypoint.sh`) | n/a (not re-checked this session, see Assumption A2) | None needed |
| App log with file-logging enabled (`--logdir /config/log`) | Live evidence gathering (this research) and D-07's "no lftp/scanner shutdown errors" check | ✓ (confirmed; `seedsyncarr.log` present and readable at `/volume1/docker/v5test/seedsyncarr/log/`) | n/a | None needed |
| `pexpect`/`ptyprocess` in the local dev venv (for any local repro/experimentation) | Understanding `close(force=True)`'s exact escalation sequence | ✓ (confirmed local venv path) | Not re-verified against `poetry.lock`'s pinned version this session | None needed — library source already read for the mechanism |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — everything needed for both the unit-provable and live-provable halves of this phase is already available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (with `pytest-timeout`, `pytest-cov`); config in `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Config file | `src/python/pyproject.toml` (`timeout = 60`, `cache_dir = "/tmp/.pytest_cache"`); coverage gate `[tool.coverage.report] fail_under = 88` |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_common/test_job.py tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_controller_job.py tests/unittests/test_controller/test_file_operation_manager.py tests/unittests/test_controller/test_auto_delete.py -q` |
| Full suite command | `make run-tests-python` (Dockerized; matches CI's `Python unit tests` job) plus `ruff check src/python/` (CI's separate `Lint (Python)` job — **not** covered by the full suite command, must be run independently per the repo's established CI-gate convention) |

**Known environmental baseline (macOS-local only, not regressions):** `test_sshcp.py`, `test_scanner.py` (latin chars), `test_scanner_process.py`, `test_extract_process.py` fail locally on macOS per CONTEXT.md's carried-forward note. Since `test_scanner_process.py` is in this baseline, new LIFE-01/02 tests should inject fakes (mocked `ScannerProcess`/`AppOneShotProcess`, as `test_scan_manager.py` and `test_file_operation_manager.py` already do) rather than depend on real multiprocessing spawn — this also keeps the tests fast and platform-independent, matching D-07's "unit-proven where the cause can be reproduced in unit tests" instruction.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIFE-01 | `ScanManager.start()` partial failure (2nd/3rd process raises) stops/joins already-started processes, exception still propagates | unit | `poetry run pytest tests/unittests/test_controller/test_scan_manager.py -k partial_start -x` | ❌ Wave 0 (new test class/methods) |
| LIFE-01 | `Controller.start()` partial failure (e.g. `file_op_manager.start()` raises after `scan_manager.start()` succeeded) stops the already-started component, exception still propagates unmasked | unit | `poetry run pytest tests/unittests/test_controller/test_controller.py -k partial_start -x` | ❌ Wave 0 (new test class) |
| LIFE-01 | `Job.run()`'s `setup()` failure sets `exc_info`, sets `shutdown_flag`, and runs `cleanup()` (the cross-cutting fix both `ControllerJob` and `WebAppJob` depend on) | unit | `poetry run pytest tests/unittests/test_common/test_job.py -k setup -x` | ❌ Wave 0 (new `DummySetupFailingJob` + test methods, extending the existing `test_job.py`) |
| LIFE-02 | `ScanManager._terminate_and_join_all()`: one process's `terminate()`/`join()` raising does not skip the other two; first error logged | unit | `poetry run pytest tests/unittests/test_controller/test_scan_manager.py -k cleanup_isolation -x` | ❌ Wave 0 (new test, extends existing `test_stop_terminates_and_joins_all_processes` pattern) |
| LIFE-02 | `FileOperationManager.stop()`: one wrapper's `reservation.release()` raising does not skip releasing the rest or stopping `extract_process` | unit | `poetry run pytest tests/unittests/test_controller/test_file_operation_manager.py -k stop_cleanup_isolation -x` | ❌ Wave 0 (new test, extends existing `test_stop_releases_outstanding_reservations` pattern) |
| LIFE-02 (regression gate) | `Controller.exit()`'s existing per-component loop, auto-delete shutdown guards and lock ordering are unchanged | unit (existing, must stay green) | `poetry run pytest tests/unittests/test_controller/test_auto_delete.py -x` | ✅ `tests/unittests/test_controller/test_auto_delete.py` |
| D-01 (unit-provable half) | Scanner health-check observing a dead scanner while a shutdown is already requested does not log ERROR / raise `ScannerProcessDiedError` | unit | `poetry run pytest tests/unittests/test_controller/test_scan_manager.py -k shutdown_aware -x` (or `test_controller_job.py`, depending on where the fix lands) | ❌ Wave 0 (new test, exact location depends on chosen fix shape — see Open Question 1) |
| D-01 (live-provable half) | A real `docker restart` on `seedsyncarr-test` (PR CI staging digest) logs neither "Scanner process(es) died unexpectedly" nor "Could not terminate the child", across both an idle restart and a restart with an active in-flight transfer; `/server/status` 200 and scans resume after each | manual-only (sandbox, D-07) | `sudo /usr/local/bin/docker restart seedsyncarr-test` (×N cycles) + `grep` the resulting log for the two error strings + `curl .../server/status` | N/A — procedure, not a test file; reuses `122-teardown.sh`'s restore pattern |

### Sampling Rate
- **Per task commit:** targeted quick-run command for the file(s) touched (see table above), plus `ruff check src/python/` on the whole tree (CI's separate gate).
- **Per wave merge:** `make run-tests-python` (full Dockerized suite) + whole-tree `ruff check src/python/`.
- **Phase gate:** full suite + ruff green, PLUS the D-07 live restart check on the sandbox before `/bm:verify-work` closes LIFE-01/LIFE-02.

### Wave 0 Gaps
- [ ] New test methods in `tests/unittests/test_common/test_job.py` covering a `setup()`-raising `Job` subclass (extends the existing `DummyFailingJob` pattern with a `DummySetupFailingJob`)
- [ ] New test methods in `tests/unittests/test_controller/test_scan_manager.py` covering (a) partial-start cleanup and (b) `_terminate_and_join_all()` fault isolation
- [ ] New test class/methods in `tests/unittests/test_controller/test_controller.py` covering `Controller.start()` partial-failure cleanup (no existing `TestControllerStart`/`TestControllerExit` class currently exists in this file — the only `Controller.exit()` coverage today lives in `test_auto_delete.py`'s `TestAutoDeleteShutdown`, which is timer-focused, not component-cleanup-focused)
- [ ] New test methods in `tests/unittests/test_controller/test_file_operation_manager.py` covering `stop()`'s reservation-release-loop fault isolation
- [ ] A small, explicit test for `MultiprocessingLogger.stop()` called without a prior `start()` (confirms Pitfall 3's guard, if added)
- [ ] D-07's live restart procedure script/checklist (can reuse/extend `122-teardown.sh`'s restore-and-verify pattern) — not a pytest file, but should be written down as a repeatable procedure before execution, per D-02/D-07

*(No framework install needed — pytest, pytest-timeout and pytest-cov are already configured and in use.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not touched by this phase |
| V3 Session Management | No | Not touched by this phase |
| V4 Access Control | No | Not touched by this phase |
| V5 Input Validation | No | No new external input surface; all data involved (process exit codes, signal delivery, internal exceptions) originates from the OS/process tree, not from user/HTTP input |
| V6 Cryptography | No | Not touched by this phase |
| V7 Error Handling / Logging (ASVS V7-adjacent; included because it's directly relevant here) | Yes | Per the user's global CLAUDE.md rule ("never log sensitive data... never expose stack traces to end users"): all exception logging touched by this phase (`logger.exception(...)` in `Controller.exit()`'s existing pattern and any new per-component/per-process cleanup loops) logs internally to the app logger only — never surfaced to the web UI/API response — and none of the exceptions involved (`ScannerProcessDiedError`, `PtyProcessError`, generic startup/cleanup exceptions) carry secrets (they describe process state, not config/credential values), so no new sanitization need is introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A crash loop from a half-cleaned-up startup (leaked scanner processes accumulating across repeated failed starts) | Denial of Service (resource exhaustion) | LIFE-01's fix (stop already-started children on a later startup failure) is itself the mitigation; combined with the existing RECOV-01 bounded auto-restart (`RESTART_CAP=3`), this prevents unbounded process accumulation across repeated controller restarts |
| An attacker-controlled external signal source (not applicable here — SIGTERM originates from the container orchestrator, not from untrusted input) | — | N/A — the signal path investigated in this phase is entirely operator/orchestrator-controlled (`docker restart`/`docker stop`), not reachable from any HTTP/webhook surface |

## Sources

### Primary (HIGH confidence)
- `src/python/common/job.py`, `src/python/controller/{controller.py,scan_manager.py,file_operation_manager.py,controller_job.py}`, `src/python/common/{app_process.py,multiprocessing_logger.py}`, `src/python/lftp/lftp.py`, `src/python/controller/lftp_manager.py`, `src/python/seedsyncarr.py`, `src/python/common/constants.py`, `src/python/common/error.py`, `src/python/web/web_app_job.py` — read directly this session
- `/Users/julianamacbook/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12/lib/python3.12/site-packages/ptyprocess/ptyprocess.py` — `spawn`/`close`/`terminate`/`kill`/`isalive`/`wait` read directly, confirming `pty.fork()`/`os.forkpty()` usage and the exact SIGHUP→SIGCONT→SIGINT→SIGKILL escalation that raises `PtyProcessError`
- `src/docker/build/docker-image/entrypoint.sh`, `src/docker/build/docker-image/Dockerfile` — `tini -g` invocation and rationale comment read directly
- Live `docker inspect seedsyncarr-test` (read-only, via `ssh nas` + `sudo /usr/local/bin/docker`) — confirmed `Entrypoint`, no `Init`/`StopSignal`/`StopTimeout` override
- Live `grep`/`sed` over `/volume1/docker/v5test/seedsyncarr/log/seedsyncarr.log` (read-only) — confirmed the scanner-death error on every observed restart and the lftp-termination error correlating with one active-transfer restart
- `.planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md`, `.planning/codebase/CONCERNS.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/phases/123-startup-and-shutdown-lifecycle/123-CONTEXT.md` — read directly
- `tests/unittests/test_common/test_job.py`, `tests/unittests/test_controller/{test_scan_manager.py,test_controller_job.py,test_file_operation_manager.py,test_controller.py,test_auto_delete.py}` — read directly to confirm existing coverage and test style

### Secondary (MEDIUM confidence)
- [tini README — "Process group killing"](https://github.com/krallin/tini) (via WebSearch, cross-checked against the maintainer's own GitHub issue comments #104 and #157 describing `-g`'s `kill(-pgid, signal)` semantics and that tini only waits on its direct child before exiting) — used to confirm the `-g` signal-forwarding mechanism cited in the root-cause analysis

### Tertiary (LOW confidence)
- The specific correlation between the lftp termination failure and an "active in-flight transfer at SIGTERM time" is drawn from a single matching live log instance (n=1) against ~20 clean restarts — flagged in the Assumptions Log (A2) and Open Question 1 for D-07 to confirm or refute with a deliberate live test.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new packages
- Architecture (LIFE-01/02 gap inventory): HIGH — every gap traced to a specific line/method via direct code reading, with existing-test-coverage confirmation that none are currently tested
- Architecture (D-01 scanner-death root cause): HIGH — fully explained mechanistically (code + library source + tini docs) and confirmed deterministic via live log evidence across ~15+ restarts
- Architecture (D-01 lftp-termination root cause): MEDIUM — mechanism for why lftp is *not* directly signaled is HIGH confidence (verified via `pty.fork()`/`os.forkpty()` session semantics); the exact trigger for why its own SIGKILL escalation occasionally fails within budget is a live-only question (n=1 evidence, correlation not causation)
- Pitfalls: HIGH for Pitfalls 1–3 (each traced to a specific code path and confirmed absent from existing test coverage); MEDIUM for Pitfall 4 (real gap, but likely secondary/out-of-primary-scope per CONTEXT.md)

**Research date:** 2026-10-25
**Valid until:** 30 days (stable, first-party-code bug-fix domain; re-verify if `tini`/`pexpect`/`ptyprocess` versions change in the image, or if the sandbox's `seedsyncarr-test` digest pin changes before this phase executes)
