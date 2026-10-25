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

## `ExtractDispatch.__coalesce_extractions` does not recognize modern RAR volume naming (122-07)

**Found during:** 122-07, Task 1, building the D-07 multi-part RAR test archive.

**Observed:** `__coalesce_extractions` (`src/python/controller/extract/dispatch.py`) only
filters the legacy WinRAR volume-continuation extension pattern `^\.r\d{2,}$` (e.g. `.r00`,
`.r01`) so that only the first volume (plain `.rar`) is queued as "an archive to extract"
for a task. RAR 5.0+ (the only creation format available from the `rar` CLI tested live on
the seedbox, RAR 7.11) uses the new-style `.partN.rar` naming for **every** volume,
including the first, so every volume file independently passes `Extract.is_archive()`
(extension-based format detection via `patoolib.get_archive_format`) and none are filtered.
A task built from a modern multi-volume RAR therefore runs one fully redundant
extraction-and-publish pass **per volume** (confirmed live: a `Replacing existing ... with
the newly extracted copy` warning on the second pass of a 2-volume archive, see
`122-SAFE01-EVIDENCE.md` §D-07 item 7). `unrar` itself is tolerant of this (pointing it at
any volume finds the sibling volumes and extracts the complete, correct output every time),
so this is not a correctness or safety defect — the staging-then-publish invariant holds on
every redundant pass — but it is pure wasted work that scales with volume count, and it
narrows the margin between a chosen `delay_seconds` and the 24-deferral auto-delete re-arm
budget on an unusually slow extraction.

**Why out of scope here:** Pre-existing gap in `__coalesce_extractions`, not introduced or
worsened by anything in this phase; this plan's constraint is live acceptance evidence only,
no code changes. Worked around for this plan's own timing margin by choosing a 2-volume
archive (not the ~11 volumes a smaller split would produce) rather than by touching product
code.

**Why it matters:** A real-world release packed with a modern RAR tool and many small
volumes (the original Burbs incident used an unspecified tool; a user re-running `rar` today
would default to this behavior) would multiply extraction time by the volume count for no
benefit. Worth a small, contained fix extending the coalesce filter to recognize
`.part\d+\.rar$` (keep only the lowest-numbered part, or `.rar` with no `.partN` infix) the
next time extraction code is touched.

**Status:** Not investigated further; not fixed; no regression test added. Carried forward
as a Phase 123 (or later maintenance) candidate.
