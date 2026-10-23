# Deferred items (Phase 122)

Out-of-scope discoveries surfaced incidentally during this phase's live acceptance work,
logged here per the executor's Scope Boundary rule (not fixed in this phase).

## `Could not terminate the child` on `seedsyncarr-test` restart (122-06)

**Found during:** 122-06, Task 1, the D-06(d) restart-persistence scenario (`sudo
/usr/local/bin/docker restart seedsyncarr-test`).

**Observed (app log, `log-bravo.txt`, capture dir
`/volume1/docker/v5test/results/safe01-122-20261023T165741Z`):**
```
2026-10-23 14:14:37,980 - ERROR - seedsyncarr.ScanManager (MainProcess/ControllerJob) - Scanner process(es) died unexpectedly: RemoteScanner, LocalScanner, ActiveScanner
2026-10-23 14:14:37,980 - ERROR - seedsyncarr.ControllerJob (MainProcess/ControllerJob) - Caught exception in job ControllerJob
...
controller.scan_manager.ScannerProcessDiedError: A scanner process stopped unexpectedly. Please check server logs for details.
2026-10-23 14:14:38,638 - ERROR - seedsyncarr.Controller (MainProcess/ControllerJob) - Error stopping lftp during controller exit
...
ptyprocess.util.PtyProcessError: Could not terminate the child.
...
pexpect.exceptions.ExceptionPexpect: Could not terminate the child.
2026-10-23 14:14:38,688 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Exited controller
2026-10-23 14:14:43,752 - INFO - seedsyncarr (MainProcess/MainThread) - Exited successfully
```

**Why out of scope here:** This is a shutdown-path behavior, not caused by any change in
this plan or this phase (122 touches the webhook/completion-gate/import-credit paths only).
It did not affect this plan's own checks — the controller still exited successfully ~5s later
and the container came back up cleanly with the credit intact (122-06-SUMMARY.md) — so it was
not auto-fixed per the Scope Boundary rule.

**Why it matters:** Phase 123 (Startup/shutdown gaps, per `PROJECT.md`'s v1.8.0 Reliability
milestone) is explicitly scoped to "a failure during partial scanner/component startup or
cleanup still cleans up started children and attempts cleanup of remaining components." This
is a live, reproducible instance of exactly that shape (lftp's pexpect-spawned child did not
terminate within `Lftp.exit()`'s force-close window on `SIGTERM`, the exception propagated
out of `Controller.exit()`'s `stop()` call) and is worth root-causing there rather than being
rediscovered from scratch.

**Status:** Not investigated further; not fixed; no regression test added. Carried forward
for Phase 123 triage.
