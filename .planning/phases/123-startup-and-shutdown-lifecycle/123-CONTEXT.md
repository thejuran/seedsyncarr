# Phase 123: Startup and Shutdown Lifecycle - Context

**Gathered:** 2026-10-25
**Status:** Ready for planning

<domain>
## Phase Boundary

A failure partway through startup or cleanup never leaves started children running or skips the cleanup of later components (LIFE-01, LIFE-02). Small, evidence-backed repairs to specific gaps. No lifecycle-framework rewrite and no new sleeps (ROADMAP success criterion 4). The existing per-component controller cleanup, the auto-delete shutdown guards (`__shutdown_event` set under `__auto_delete_lock`) and the established lock ordering are preserved unchanged and their existing tests stay green (success criterion 3).

By owner decision (D-01), scope also includes root-causing and fixing the errors every normal `seedsyncarr-test` restart logged during Phase 122: lftp "Could not terminate the child" and "Scanner process(es) died unexpectedly". These are the same failure class and are in the phase domain.

</domain>

<decisions>
## Implementation Decisions

### Restart errors seen in Phase 122 (folded in)
- **D-01:** Fix in this phase. Root-cause and fix why a normal restart logs `Error stopping lftp during controller exit` (`ptyprocess`/`pexpect` "Could not terminate the child") and `Scanner process(es) died unexpectedly: RemoteScanner, LocalScanner, ActiveScanner` / `ScannerProcessDiedError`. Done means a normal sandbox restart logs neither error and the app comes back up normally. Evidence and exact log lines: `.planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md` (first section) and 122-06's `log-bravo.txt` excerpt quoted there.
- **D-02:** The fix must be test-first like the LIFE fixes: a regression test that fails before and passes after, wherever the cause can be reproduced in unit tests. If part of the cause is only observable live (e.g. container SIGTERM delivery to child processes), the live restart check in D-07 is the proof, and the plan must state which part is unit-proven and which is live-proven.

### Fixed shutdown wait (DEFER-SHUTDOWN)
- **D-03:** Conditional. Do not replace the `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` setup wait (`src/python/seedsyncarr.py`, tracked as DEFER-SHUTDOWN in `.planning/codebase/CONCERNS.md`) unless the D-01 investigation shows it causes or contributes to the restart errors. If linked, replace it as part of D-01 with a per-job "setup complete" signal and a bounded wait. This does not count as a "new sleep" (success criterion 4). If not linked, leave it and keep the existing backlog note. The research/plan must record which way it went and why.

### Behaviour after a startup failure
- **D-04:** Keep today's behaviour and only add the cleanup. When a component fails partway through startup, stop and join everything that already started, then let the original failure surface unchanged. It goes into the existing bounded controller auto-restart (`ServiceRestart`, RECOV-01 / Phase 114) and, once that budget is exhausted, the existing `server.up=False` web-UI error. The web server keeps running.
- **D-05:** No degraded mode (never run with only some components started, which could make the app look healthy while scanning is off, a safety risk for auto-delete). No new "exit the whole container" behaviour.
- **D-06:** The original startup exception must not be masked by a secondary exception raised during the cleanup it triggers. Cleanup errors are logged; the original failure is what propagates.

### How it is proven
- **D-07:** Injected-failure unit tests, RED-first, for each gap: a failure injected into the startup of each scanner process and of each controller component after earlier ones started (started children are stopped, the failure still surfaces), and into the cleanup of each component (the remaining components are still cleaned up, the first failure is logged). Plus a short live restart check on the NAS sandbox `seedsyncarr-test` on this phase's PR CI staging image pinned by digest: a few `docker restart` cycles, each must log no lftp/scanner shutdown errors and come back up normally (`/server/status` 200, scans resume). No live transfer/import tracking through a restart (Phase 122 D-06(d) already proved credit persistence). The sandbox is restored to its original pin afterwards with a fresh-session check; production is read-only fingerprint checks only.

### Claude's Discretion
- Exact shape of the cleanup-on-partial-start code (e.g. per-component try blocks mirroring `Controller.exit()`'s existing pattern, or tracking which components started). It must follow the pattern already in `Controller.exit()` rather than introduce a new lifecycle abstraction.
- Whether `ScanManager.stop()`/`_terminate_and_join_all()` and `FileOperationManager.stop()` get per-process independent cleanup, provided the remaining processes are always terminated and joined and the first error is logged.
- Which component's startup/cleanup gaps exist beyond those already spotted (research confirms the full list, including `ControllerJob`, `FileOperationManager`, the mp logger and the top-level job start in `seedsyncarr.py`).
- Bounded timeouts for any new join/terminate waits (no unbounded hangs at shutdown).

</decisions>

<specifics>
## Specific Ideas

Gaps already spotted in the code during discussion (research must confirm and complete the list):
- `ScanManager.start()` (`src/python/controller/scan_manager.py:87`) starts three scanner processes in sequence and sets `__started = True` only at the end. If the second or third `start()` raises, the earlier processes keep running, and `stop()` is a no-op because `__started` is False.
- `Controller.start()` (`src/python/controller/controller.py:340`) starts scan manager, file-op manager and mp logger, then sets `__started = True`. If a later one fails, earlier ones keep running and `Controller.exit()` does nothing because `__started` is False.
- `ScanManager._terminate_and_join_all()` terminates and joins sequentially with no per-process protection; one raising skips the rest.
- `Controller.exit()` already runs each component's cleanup independently with logged exceptions. This is the in-repo pattern to follow (LIFE-02 preserves it).

Owner priorities: no stray processes after failed restarts, and clean logs on a normal restart so real problems stand out.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` (Phase 123 section): goal and the four success criteria, incl. "no new sleeps, no lifecycle-framework rewrite"
- `.planning/REQUIREMENTS.md`: LIFE-01, LIFE-02 and the out-of-scope row "Lifecycle-framework rewrite"

### Restart errors to fix (D-01)
- `.planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md`: first section, "`Could not terminate the child` on `seedsyncarr-test` restart (122-06)", with the verbatim log excerpt and why it belongs to Phase 123
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-06-SUMMARY.md`: the restart scenario that produced it

### Known shutdown concern (D-03)
- `.planning/codebase/CONCERNS.md`: "Deferred shutdown sequencing in main loop (DEFER-SHUTDOWN)" and the auto-delete lock-ordering/shutdown-guard notes (BUG-03, WR-02) that must stay unchanged

### Prior live-check procedure to reuse (D-07)
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-11-SUMMARY.md` and `122-16-SUMMARY.md`: pinning the sandbox to the PR CI staging image by digest, the re-pin readiness race and its fix, production fingerprint checks
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh`: restore/teardown helper (`--final` restores the original pin)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Controller.exit()` per-component cleanup loop (`src/python/controller/controller.py`, the `for component, stop in (...)` block with `try/except Exception: self.logger.exception(...)`): the pattern to mirror for independent cleanup.
- `Lftp.exit()` (`src/python/lftp/lftp.py:451`): already force-closes the pexpect process (`self.__process.close(force=True)`) when graceful exit fails. This is the starting point for the D-01 root cause.
- Bounded controller auto-restart: `Seedsyncarr._should_auto_restart` and `ServiceRestart` in `src/python/seedsyncarr.py` (RECOV-01, Phase 114). This is where a surfaced startup failure lands (D-04).

### Established Patterns
- Lock ordering: `__model_lock` THEN `__auto_delete_lock`; `exit()` takes only `__auto_delete_lock`; `__shutdown_event` set inside that lock first. Must not change (success criterion 3).
- RED-first TDD with `test(123-NN)` before `fix(123-NN)` commits; CI runs `ruff check src/python/` separately from pytest, so build-verify with whole-tree ruff too.
- Known macOS-local pytest failures (`test_sshcp.py`, `test_scanner.py` latin chars, `test_scanner_process.py`, `test_extract_process.py`) are environmental; compare against that baseline rather than treating them as regressions. Note that scanner-process tests are among them, so new lifecycle tests should not depend on real process spawning where a fake process can be injected.

### Integration Points
- `src/python/controller/scan_manager.py`: `start()`, `stop()`, `_terminate_and_join_all()`
- `src/python/controller/controller.py`: `start()`, `exit()`
- `src/python/controller/file_operation_manager.py`: `start()` (line ~108), `stop()` (line ~118)
- `src/python/controller/controller_job.py`: job setup/cleanup around controller start/exit
- `src/python/seedsyncarr.py`: top-level job start, main loop, shutdown wait (DEFER-SHUTDOWN), signal handling
- `src/python/lftp/lftp.py`: `exit()`

</code_context>

<deferred>
## Deferred Ideas

- Modern RAR `.partN.rar` volumes extracted once per volume (`ExtractDispatch.__coalesce_extractions`). Logged in `122-.../deferred-items.md` second section. Not a lifecycle issue; stays out of Phase 123. Candidate for the ROADMAP backlog if not already there.
- DEFER-SHUTDOWN replacement if the D-01 investigation shows it is unrelated to the restart errors (D-03). Stays a backlog note.
- Phase 122 re-review follow-ups WR-04 (Arr key normalization) and IN-04/IN-05 (post-transfer window edge cases): already in the ROADMAP Backlog; not part of Phase 123.

</deferred>

---

*Phase: 123-startup-and-shutdown-lifecycle*
*Context gathered: 2026-10-25*
