# Deferred items (Phase 123)

Out-of-scope discoveries surfaced incidentally during this phase's unit and live work,
logged here per the executor's Scope Boundary rule (not fixed in this phase).

## Controller.__init__ spawns lftp before start() (RESEARCH Open Question 2)

**Found during:** 123-RESEARCH.md, Open Question 2 (research phase, before any 123-NN plan
was written).

**Observed:** `Controller.__init__` unconditionally and eagerly constructs `LftpManager`
(and therefore `Lftp`), which immediately spawns the lftp pty process at construction time,
before `Controller.start()` is ever called. If `Controller.__init__` itself raises *after*
`LftpManager`'s constructor has run but *before* `__init__` finishes (e.g. a later
collaborator's constructor raising), the already-spawned lftp pty process is leaked with no
handle to close it, since the partially-constructed `Controller` object is never
returned/usable.

**Why out of scope here:** This is a leak only if `__init__` itself raises after `LftpManager`
is built -- a narrower, constructor-time edge case than LIFE-01/LIFE-02's `start()`-time
scope. CONTEXT.md's "Specific Ideas" section names `ScanManager.start()`/`Controller.start()`
only, not `Controller.__init__`. 123-01..04 and 123-08/123-13 already close every `start()`
-time partial-failure gap (including exiting lftp only, 123-03's
`test_partial_start_scanner_fails_exits_lftp_only`); nothing in this phase's scope touches
`__init__`'s construction order.

**Why it matters:** `Controller.__init__`'s current construction order means a later
collaborator constructor raising (unlikely today -- most of `__init__`'s later steps build
plain Python objects unlikely to raise, per the research) would leak a live lftp process with
no cleanup path. Worth a small, contained fix (e.g. a try/except around the remaining
`__init__` body that closes `LftpManager` on failure) if `__init__` ever grows a step that can
plausibly raise.

**Status:** Not investigated further; not fixed; no regression test added. Backlog candidate.

## Seedsyncarr.run shutdown-path persist() can mask the original exception (RESEARCH Pitfall 4)

**Found during:** 123-RESEARCH.md, Pitfall 4 (research phase).

**Observed:** `Seedsyncarr.run()`'s top-level `except Exception:` block calls `self.persist()`
(which can raise `OSError`/`PersistError` writing three files to disk) with no inner guard,
*after* the original shutdown-triggering exception was caught but *before* the bare `raise`
that is supposed to re-propagate it. If `persist()` raises, the original exception is masked
by the persist-time exception, exactly the general risk D-06 proves the phase's other
cleanup paths do not have.

**Why out of scope here:** Flagged in RESEARCH.md as a **lower-confidence, secondary
finding** -- likely outside this phase's primary `Controller`/`ScanManager`/
`FileOperationManager` scope per CONTEXT.md's specifics. No existing test exercises
`Seedsyncarr.run()`'s shutdown-path `persist()` call failing, and no occurrence of it was
observed live across any of this phase's 123-06/123-11/123-12/123-16/123-17 restart cycles
(17 live restarts total, zero persist-time exceptions in any shutdown window).

**Why it matters:** The fix is small and mirrors a pattern this phase already applies
everywhere else (D-06's `if self.exc_info is None: ...` guard, `Controller.exit()`'s
per-component `try/except Exception: self.logger.exception(...)` loop): wrap the shutdown
-path `persist()` call in its own `try/except Exception: self.logger.exception(...)` so a
persist failure during shutdown is logged but never replaces the original exception.

**Status:** Not investigated further; not fixed; no regression test added. Backlog candidate
for the next time `seedsyncarr.py`'s shutdown path is touched.

## DEFER-SHUTDOWN sleep kept (D-03)

**Verdict:** Kept, no code change. Both `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)`
call sites in `src/python/seedsyncarr.py` are byte-for-byte unchanged across every commit in
this phase (123-01..04, 123-08, 123-13), confirmed repeatedly by this phase's own Gate 5
(`grep -c` -> `2`; `grep "^+" | grep -c "sleep("` -> `0` on every gate run from 123-05 through
123-15).

**Evidence pointer:** `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md`,
"## D-03 decision (DEFER-SHUTDOWN sleep kept)". The kernel delivers the container's
process-group SIGTERM to the forked scanner children instantaneously and independently of
anything running on the python main thread -- no amount of shortening, lengthening or
removing the 0.5s sleep could change whether that direct kernel-level signal kills them. The
2026-10-23 14:14:37-38 sandbox log excerpt (122-06, quoted in RESEARCH.md's architecture
diagram) shows the `ControllerJob` thread self-detecting the dead scanners and running
`Controller.exit()` to completion in well under 1 second -- before the main thread's 0.5s
DEFER-SHUTDOWN sleep path had even reached its own `terminate()` call. The self-triggered
path, not the sleep-gated path, is what actually ran `Lftp.exit()` in the originally observed
failing case, so the sleep was never the mechanism producing either restart error (D-01's
scanner half or lftp half) in the first place.

**Why out of scope for a code change:** D-03 is conditional on the sleep causing or
contributing to the restart errors; the investigation above shows it does not.

**Status:** Not changed. The existing `.planning/codebase/CONCERNS.md` DEFER-SHUTDOWN
backlog note stays as is, unchanged by this phase.

## `Exited successfully` often missing after a docker restart (pre-existing)

**Observed:** The app log's `Exited successfully` line is logged only after the full shutdown
sequence completes. It is absent in the 1.7.6 production baseline window
(`BASELINE_REPIN_EXITED_SUCCESSFULLY=0`, OLD_D/log-repin-baseline.txt, 123-06 capture dir) and
in a majority of this phase's own restart cycles: 4 of 6 in the GAP-1 round (I1 first run,
I2, A1, A2 all read 0; only I1's rerun and I3 read 1) and 5 of 6 in gap round 2 (only I1
rerun-equivalent -- actually all six of I1/I2/A1/A2/A1r/I3 in gap round 2 read
`EXITED_SUCCESSFULLY=0`; see "### Recorded-only signals" under both the 123-16/123-17 and
this plan's "## Restart cycles" sections). The likely cause is docker's 10s `stop` timeout
ending the container's main process before the final log line is reached, which is the same
"handler ran late" shape D-01's own GAP-1 grace window is about.

**Why out of scope here:** Pre-existing, not introduced or worsened by this phase. The 123-09
harness change already made this line recorded-only, not a pass/fail criterion (every cycle's
PASS/FAIL in this phase rests on `scanner_died`/`could_not_terminate`/
`caught_exception_in_job`/`error_stopping`/`restart_rc`/`procs_<reason>`, never on this
line), so it does not affect any verdict in this phase.

**Evidence pointer:** `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md`,
"### Harness change (123-09)" and the "Recorded-only signals" tables under "## Gap-round-2
live check (123-16/123-17)" and "## Restart cycles on the Phase 123 build (gap round 2,
123-16/123-17)" (per-cycle `EXITED_SUCCESSFULLY` and `RESTART_ELAPSED_S` values).

**Status:** Not investigated further; not fixed; no regression test added. Backlog candidate
if a future phase wants every restart to log a definitive completion line within docker's
stop-timeout window.

## GAP-2 bounded wait in Lftp.exit() (owner flag, success criterion 4)

**What it is:** The one `time.sleep` waiter default in `Lftp.__init__`
(`waiter: Callable[[float], None] = time.sleep`), the single bounded wait (at most 2.0
seconds total, polling every 0.05 seconds) added to `Lftp.exit()`'s post-close reap fallback
(123-13). It runs only when lftp has already refused to die after pexpect's own kill
sequence (SIGHUP, SIGCONT, SIGINT, SIGKILL, each with its own 0.1s check) has already failed
and raised -- which, per this phase's full live evidence (123-06, 123-11/12, 123-16/17),
happens only during active transfers (and, as of gap round 2's idle cycles I1/I2, also
occasionally on an idle restart). A normal clean shutdown never reaches this wait at all
(`test_idle_close_succeeds_no_poll_no_signal_no_wait` pins zero waiter/`kill_group`/`isalive`
calls on a clean close).

**Why it is recorded here rather than silently absorbed:** Phase 123's success criterion 4 is
"no new sleeps, no lifecycle-framework rewrite." This one bounded wait is an explicit,
owner-approved exception to that criterion (123-13-PLAN.md `<owner_decision>`, verbatim:
"Allow it (Recommended)"), confirmed as the only new sleep anywhere in the GAP-2 delta by
Gate 5b (123-15). It is listed here, separate from the phase verdict table, so the owner can
see it in the backlog/concerns view alongside the other DEFER-SHUTDOWN sleep note, not just
buried in a gate result.

**Rejected alternative:** An unbounded blocking `os.waitpid(pid, 0)` with no wait primitive at
all -- rejected because it could hang the in-process controller restart (RECOV-01)
indefinitely if the child stays in uninterruptible I/O (state D), which this phase's gap
-round-2 live evidence (I1, I2, A2) confirms actually happens.

**Status:** Shipped as part of 123-13's fix, not deferred. Recorded here for backlog
visibility only; no further action proposed.

**Deep-review sub-note (informational, low confidence):** PR #137's vibe-check deep review
(2026-10-26) also flagged, via 3 of its 5 reviewers at low confidence, a possible
double-failure masking shape in `Lftp.exit()`: if the post-close reap fallback itself raises
(e.g. the bounded wait above still times out and `LftpError` is raised) while an earlier
exception from the same shutdown sequence is already in flight, the later exception could
mask the earlier one at the call site, the same general shape D-06 guards against elsewhere
in this phase. None of the findings in this sub-note scored >=70 and all were filtered as
sub-threshold by the review's own scoring; it is recorded here for visibility alongside the
bounded-wait note, not as a separate action item.

## WebAppJob.cleanup() lacks per-step isolation (PR #137 deep review, owner-reviewed, backlogged)

**Found during:** PR #137 vibe-check deep review (2026-10-26), bugs/architecture reviewer
(Opus). Surfaced to the owner at the Phase 123 verdict checkpoint (123-07, Task 3); owner
reply verbatim: "approve, backlog both items".

**Observed:** `WebAppJob.cleanup()` (`src/python/web/web_app_job.py`) does not have the
per-step isolation this phase added to `ScanManager`/`FileOperationManager`/`Controller`'s
cleanup paths: if `self.__app.stop()` raises, `self.__server.stop()` and
`self.__server_thread.join()` are skipped entirely rather than each being attempted and
logged independently. Compounding this, `MyWSGIRefServer.stop()` can itself raise
`AttributeError` when its inner server reference is still `None` (e.g. if `cleanup()` runs
before the server ever finished starting).

**Why out of scope here:** This phase's scope (per CONTEXT.md's "Specific Ideas") named
`ScanManager`/`Controller`/`FileOperationManager` cleanup paths, not `WebAppJob`. No live
restart cycle in this phase (17 total) observed `WebAppJob.cleanup()` raising or skipping a
step; the finding is static-analysis-derived, not reproduced live.

**Why it matters:** The fix mirrors a pattern this phase already applies everywhere else --
wrap each stop step (`self.__app.stop()`, `self.__server.stop()`,
`self.__server_thread.join()`) in its own `try/except Exception: self.logger.exception(...)`,
and guard `MyWSGIRefServer.stop()` against a `None` inner server before calling it.

**Status:** Not fixed in this phase (owner decision, 2026-10-26: "backlog both items"); no
regression test added. Backlog candidate.

## ControllerJob.execute() non-AppError failures bypass RECOV-01 auto-restart (PR #137 deep review, owner-reviewed, backlogged)

**Found during:** PR #137 vibe-check deep review (2026-10-26), bugs/architecture reviewer
(Opus). Surfaced to the owner at the Phase 123 verdict checkpoint (123-07, Task 3); owner
reply verbatim: "approve, backlog both items".

**Observed:** This phase's D-04/D-05 fix wraps non-`AppError` exceptions into `ControllerError`
only in `ControllerJob.setup()`, routing them to the existing RECOV-01 `except AppError`
main-loop auto-restart path. A non-`AppError` exception raised later, from
`Controller.process()` via `ControllerJob.execute()`, is not wrapped the same way -- it still
reaches the main loop as a plain (non-`AppError`) exception and ends the process instead of
triggering RECOV-01's auto-restart.

**Why out of scope here:** This is the deliberate, scoped behavior from D-04/D-05 (startup
-failure handling), not a regression -- `ControllerJob.setup()` is exactly where LIFE-01/LIFE-02
apply. Extending auto-restart coverage to `execute()`-time non-`AppError` failures is a
broader behavior change (new error-routing surface outside this phase's declared scope) and
is explicitly named in the plan's own `<done>` text as a future product decision, not a gap in
this phase's fix.

**Why it matters:** An unexpected non-`AppError` failure during normal operation (not
startup) today still ends the process rather than auto-restarting, same as before this phase.
Whether that should change is a product decision about how broadly RECOV-01 should apply, not
a bug in the current fix.

**Status:** Not fixed in this phase (owner decision, 2026-10-26: "backlog both items"); by
design, not a code gap. Backlog candidate for a future phase if the owner wants RECOV-01's
coverage extended beyond setup-time failures.

## One flaky `test_app_process.py` run during the gap-round-2 phase gate (123-15)

**Found during:** 123-15, Task 1, Gate 1 (full unit-suite failure set vs. the 122-03
baseline).

**Observed:** An initial full-suite run showed `23 failed, 1849 passed, 2 warnings, 3 errors`
-- 2 extra failures in `tests/unittests/test_common/test_app_process.py`
(`TestAppProcess::test_cleanup_called_after_loop`,
`TestAppOneShotProcess::test_run_once_called_once`) beyond the documented 24-line baseline.
Two immediate re-runs both reproduced the exact documented `21 failed, 1851 passed, 2
warnings, 3 errors` result, with both a raw and a name-normalized `comm -23`/`comm -13`
comparison against the baseline coming back empty in both directions on the clean re-runs.

**Why out of scope here:** Neither failing test is touched by this phase's `src/` diff
(confirmed by 123-15's Gates 4/8/9, which show the phase's changes are confined to
`src/python/controller/scan_manager.py` and `src/python/lftp/lftp.py` plus their test
files). `test_app_process.py` is a known timing-sensitive thread/process test, consistent
with this phase's already-documented environment-only failure list (`test_sshcp.py`,
`test_scanner.py::test_scan_file_with_latin_chars`, `test_scanner_process.py`,
`test_extract_process.py`). The clean re-run, not the flaky run, is what 123-15's gate
verdict and this phase's "done" claim rest on.

**Status:** Not investigated further as a code issue; not fixed; treated as one-off
environment flakiness. Recorded here per the phase-close objective's instruction to mention
it, for awareness if `test_app_process.py` flakes again in a future phase's gate run.
