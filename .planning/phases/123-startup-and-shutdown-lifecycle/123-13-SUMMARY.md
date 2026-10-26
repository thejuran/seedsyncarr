---
phase: 123-startup-and-shutdown-lifecycle
plan: 13
subsystem: lftp
tags: [tdd, gap-closure, gap-2, d-01, lftp, pexpect, ptyprocess, process-group, reap, monotonic-clock]

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "12"
    provides: "Live gap-round evidence pinning GAP-2 (A1 +1.80s, A2 +1.65s after SIGTERM: Error stopping lftp / PtyProcessError Could not terminate the child) and the owner's fix-in-phase decision"
provides:
  - "Lftp.exit() reaps an lftp child that outlives pexpect's own force close, via a bounded (2.0s) process-group SIGKILL and poll, instead of letting PtyProcessError surface as Controller.exit()'s ERROR and leaking a zombie"
  - "exit kill (not exit) so a numbered job surviving to exit time can no longer move lftp into its documented nohup background fork, which a process-group signal could not otherwise reach"
  - "describe_lftp_process(pid): a never-raising /proc state-letter + child-count diagnostic used in the new WARNING/LftpError text"
  - "Injectable clock/waiter/kill_group/describe_process on Lftp.__init__ (production defaults time.monotonic/time.sleep/os.killpg/describe_lftp_process), following the 123-08 clock-injection convention"
affects: ["123-16/123-17 (live restart re-check that an active-transfer restart no longer logs Error stopping lftp / Could not terminate the child, confirming the D-state hypothesis via the new diagnostic log)", "123-15 (Gate 5b must list this plan's one owner-approved bounded wait and no other new sleep)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Clock injection for deterministic time-bounded tests, matching 123-08/arr_queue.py/completion_gate.py: constructor param clock: Callable[[], float] = time.monotonic; tests use a module-level _FakeClock class with a mutable .now (never a lambda, ruff E731)"
    - "Bounded fallback-after-library-failure: when a well-behaved library call (pexpect's own force-close-and-signal sequence) fails, fall back to one extra reap poll, then an explicit signal, then a clock-bounded poll loop with an injected waiter -- never an unbounded blocking call (os.waitpid(pid, 0) was rejected for exactly this reason)"
    - "Never-raising /proc diagnostic helper (describe_lftp_process): every failure mode (OSError, ValueError, IndexError) degrades to '?' per field rather than propagating, since the diagnostic itself must never become a new failure point"

key-files:
  created: []
  modified:
    - src/python/lftp/lftp.py
    - src/python/tests/unittests/test_lftp/test_lftp_exit.py

key-decisions:
  - "Owner-approved exception to success criterion 4 (verbatim 'Allow it (Recommended)'): the one bounded wait in Lftp.exit()'s post-close reap fallback (EXIT_REAP_TIMEOUT_SECS=2.0, EXIT_REAP_POLL_INTERVAL_SECS=0.05, injectable waiter defaulting to time.sleep) is the only new sleep allowed in this phase. It is reached only when pexpect's own close(force=True) has already raised, never on a clean shutdown (pinned by test_idle_close_succeeds_no_poll_no_signal_no_wait)."
  - "Rejected alternative: a blocking os.waitpid(pid, 0) with no wait primitive at all. Rejected because it is unbounded if the child stays in uninterruptible I/O (state D) -- it could hang the in-process controller restart (RECOV-01) indefinitely, which is worse than a documented, bounded wait."
  - "exit kill instead of exit: lftp's documented behaviour is to move itself to nohup background (a detached fork into a new session) if asked to exit while jobs are still running. That fork could not be reached by a process-group signal at all, which would make this plan's fix incomplete for that case even though it was not observed live."
  - "D-02 split: the idle no-op, the fallback reap with and without a group kill, the 2.0s bound and the honest raise, ProcessLookupError tolerance, unchanged propagation of graceful failures, exit kill, and the /proc diagnostic parser are unit-proven here with fakes (no real processes, no real sleeps, no real signals). That a real active-transfer restart now logs no Error stopping lftp / Could not terminate the child, that the lftp pid and its children are gone before the old container stops, and the actual process state letter at the fallback (settling the D-state hypothesis) are live-proven only in 123-16/123-17."

requirements-completed: [LIFE-02]

# Metrics
duration: ~24min (RED 16:49:16-04:00 to GREEN 16:53:39-04:00 git-commit timestamps; elapsed time also includes reading plan/context/gap-evidence files, installing poetry dev dependencies in this worktree, and running verification suites before and after each commit)
completed: 2026-10-26
---

# Phase 123 Plan 13: Bounded lftp Force-Kill Reap Fallback (GAP-2) Summary

**`Lftp.exit()` now falls back to a bounded (2.0s) process-group SIGKILL-and-reap when pexpect's own `close(force=True)` fails to kill an actively-transferring lftp in time, and sends `exit kill` instead of `exit` so a surviving job can never move lftp into an unreachable background fork -- closing the lftp half of D-01/GAP-2 (`PtyProcessError: Could not terminate the child.`) seen on both active-transfer restarts in 123-12.**

## Performance

- **Duration:** ~24 min between RED and GREEN commit timestamps (16:49:16-04:00 to 16:53:39-04:00); wall time also included reading the plan/context/evidence files, correcting this worktree's branch base (see Issues Encountered), installing this worktree's poetry dev dependencies (not yet installed), and running the full verification suite before and after each commit
- **Tasks:** 2 (RED test commit, GREEN fix commit)
- **Files modified:** 2 (1 test file across both tasks, 1 source file in Task 2)

## Diagnosis (settled from source, observed directly in this worktree's venv -- pexpect 4.9.0, ptyprocess 0.7.0)

- `Lftp.exit()` (`src/python/lftp/lftp.py`, pre-fix lines 451-463) called pexpect `spawn.close(force=True)` (confirmed at `pexpect/pty_spawn.py:317-331` in this venv: `self.flush(); with _wrap_ptyprocess_err(): self.ptyproc.close(force=force)`), which calls `PtyProcess.close(force=True)` (confirmed at `ptyprocess/ptyprocess.py:393-409`). That method closes the pty fd, sleeps `self.delayafterclose` (`ptyprocess.py:173`, `= 0.1`), then if `isalive()` still reports the child, calls `terminate(force=True)` (`ptyprocess.py:622-660`, sending SIGHUP/SIGCONT/SIGINT/SIGKILL with `self.delayafterterminate = 0.1` -- `ptyprocess.py:176` -- after each) and raises `PtyProcessError('Could not terminate the child.')` (`ptyprocess.py:405-406`) only if the child is still unreaped after that sequence. pexpect's `_wrap_ptyprocess_err` context manager (`pty_spawn.py:19-25`) re-raises this as `ExceptionPexpect` before `self.closed` is set, so nothing reaps the child afterwards.
- Rejected: "tini's group SIGTERM hit lftp". `pty.fork()` makes lftp the leader of its own session and process group, and `tini -g` signals only python's group; lftp never sees the container SIGTERM, and even if it did it would die sooner, not later.
- Rejected as the cause of the error: "a zombie ptyprocess doesn't reap". `isalive()` calls `waitpid`, which reaps a zombie and returns `False`; a zombie cannot produce this error. It is, though, the leak the error leaves behind -- after the raise, the SIGKILLed lftp becomes a zombie nothing reaps until python exits, which is harmless on a container restart but accumulates across the in-process controller restart (RECOV-01).
- Rejected as the cause: "lftp's children keep the pty open". `isalive()` tracks only the lftp pid; children holding the pty cannot keep that pid alive.
- Remaining cause (unit-unprovable, hence the new diagnostic log rather than a unit assertion): lftp is SIGKILLed but has not finished dying 100ms later, which the live evidence shows happens only during an active transfer. A SIGKILLed process becomes reapable only once its in-kernel exit completes; a process blocked in uninterruptible I/O (state D) or tearing down many sockets/dirty pages can take longer than 100ms. The fix logs the `/proc/<pid>/stat` state letter and child count at the moment of the fallback (`describe_lftp_process`); 123-16/123-17's live run is what actually confirms the D-state hypothesis.
- Related risk found while diagnosing, not yet observed live: lftp's documented `exit` behaviour, if a job is still running at exit time, is to move itself to background (nohup mode) via a fork that `setsid()`s into a new session before the parent `_exit(0)`s. A job surviving `kill all` at `exit` time would leave a detached lftp in a new session that no process-group kill could reach. `exit kill` ("kills all numbered jobs before exiting") closes that path.

## Accomplishments

- `Lftp.exit()` now sends `exit kill` instead of `exit`.
- `Lftp.exit()`'s `finally` block wraps `self.__process.close(force=True)` in a `try/except pexpect.exceptions.ExceptionPexpect`, calling the new private `__reap_after_failed_close()` only on that path; a clean close takes none of the new code (pinned by `test_idle_close_succeeds_no_poll_no_signal_no_wait`, which asserts zero waiter calls, zero `kill_group` calls, zero post-close `isalive()` calls, and no INFO/WARNING log).
- `__reap_after_failed_close()`: one `isalive()` poll first (reaps a child that has since died, logging INFO "group kill sent: no" with no signal sent); otherwise logs a WARNING with the `describe_lftp_process` diagnostic, sends `SIGKILL` to the child's own process group (safe because the pid is confirmed unreaped, so group `<pid>` can only be lftp's own session/process group from `pty.fork()`), tolerates `ProcessLookupError` (a concurrent reaper already won), logs any other `OSError` by `errno` name and keeps polling, then polls on the injected monotonic clock at `EXIT_REAP_POLL_INTERVAL_SECS` (0.05s) until reaped (INFO "group kill sent: yes") or `EXIT_REAP_TIMEOUT_SECS` (2.0s) elapses, at which point it raises `LftpError` so a real leak surfaces as `Controller.exit()`'s existing ERROR rather than being hidden.
- Added the module-level `describe_lftp_process(pid, proc_root="/proc")`, which never raises: it reads the state letter after the last `)` in `<proc_root>/<pid>/stat` and the whitespace-separated pid count in `<proc_root>/<pid>/task/<pid>/children`, falling back to `?` per field on any `OSError`/`ValueError`/`IndexError`.
- `Lftp.__init__` gained keyword-only `clock`, `waiter`, `kill_group`, `describe_process` parameters with production defaults (`time.monotonic`, `time.sleep`, `os.killpg`, `describe_lftp_process`); `LftpManager` (which constructs `Lftp` with keyword-only arguments) needed no change.
- No `sleep(` call was added anywhere in product code; the only reference to `time.sleep` is the `waiter` parameter's default value in the constructor signature, never called directly.

## Task Commits

1. **Task 1 (RED): fake-process tests for the bounded lftp force-kill fallback, idle regression and `exit kill`** - `01045b8` (test)
2. **Task 2 (GREEN): bounded process-group SIGKILL and reap after a failed force close, `exit kill`, /proc diagnostic** - `e03e3bd` (fix)

_No refactor commit was needed._

## RED Results (Task 1, commit `01045b8`)

Command: `cd src/python && timeout 300 poetry run pytest tests/unittests/test_lftp/ -p no:cacheprovider -q`

Result: **ImportError at module collection** (the whole file errored out, which the plan accepts as RED):
```
ERROR tests/unittests/test_lftp/test_lftp_exit.py
ImportError: cannot import name 'describe_lftp_process' from 'lftp.lftp'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```
Confirmed, separately, that every pre-existing test file in `tests/unittests/test_lftp/` still passed on its own (the collection error in one file otherwise aborts the whole pytest session before any other test runs): `pytest tests/unittests/test_lftp/ -p no:cacheprovider -q --ignore=tests/unittests/test_lftp/test_lftp_exit.py` -> **148 passed**.

Acceptance-criteria checks, all confirmed:
- `git log -1 --format=%s` -> `test(123-13): ...`; `git show --stat --format= HEAD` -> only `src/python/tests/unittests/test_lftp/test_lftp_exit.py`
- `grep -c "def test_" src/python/tests/unittests/test_lftp/test_lftp_exit.py` -> `11`
- `grep -c -F "sleep(" ...test_lftp_exit.py` -> `0`; `grep -c -F "os.killpg" ...test_lftp_exit.py` -> `0`
- Whole-tree ruff (`poetry run ruff check .` from `src/python/`) -> `All checks passed!`

## GREEN Results (Task 2, commit `e03e3bd`)

Command: `cd src/python && timeout 300 poetry run pytest tests/unittests/test_lftp/ tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_controller.py -p no:cacheprovider -q`

Result: **233 passed, 0 failed, 0 errors.**

Whole-tree lint: `ruff check src/python/` (via `poetry run ruff check .`) -> `All checks passed!`

A broader regression check (`pytest tests/unittests/test_controller/ -p no:cacheprovider -q`, outside the plan's required command) showed **952 passed, 9 failed, 3 errors**; every failure was in `test_extract_process.py` and `test_scanner_process.py`, which the phase's established macOS-local baseline (123-CONTEXT.md, "Known Patterns") already documents as environment-only (real process spawning does not work the same way in this sandbox). Not relied on for this plan's "done" claim -- the plan's own prescribed verification command (233 passed / 0 failed, above) is what backs this plan's completion.

Acceptance-criteria checks, all confirmed:
- `grep -c -F "EXIT_REAP_TIMEOUT_SECS = 2.0" src/python/lftp/lftp.py` -> `1`; `grep -c -F 'sendline("exit kill")' src/python/lftp/lftp.py` -> `1`
- `git log -2 --format=%s` -> `fix(123-13): ...` on top of `test(123-13): ...`
- `git diff --name-only HEAD~2..HEAD -- src/` -> exactly `src/python/lftp/lftp.py` and `src/python/tests/unittests/test_lftp/test_lftp_exit.py`
- `git diff HEAD~1 -- src/python/lftp/lftp.py | grep "^+" | grep -c -F "sleep("` -> `0`; the same diff filtered to lines without `#` and grepped for `time.sleep` -> `1` (the `waiter` default only)
- `git diff HEAD~1 -- src/python/lftp/lftp.py | grep "^+" | grep -c -F "Could not terminate"` -> `0` (the exit() docstring does mention ptyprocess's exact exception text for documentation, but it is wrapped across two lines, so no single added diff line contains the full substring; no log call or exception message interpolates it); `grep -c -F "logger.error"` on the same diff -> `0`
- `git diff HEAD~2 -- src/python/controller/ src/python/seedsyncarr.py` -> empty (both files untouched)
- This file contains the heading "Owner flag: success criterion 4" (below)

## Owner flag: success criterion 4

One bounded wait (at most 2.0 seconds total, polling every 0.05 seconds) was added to `Lftp.exit()`. It runs only when lftp has already refused to die after pexpect's own kill sequence (SIGHUP, SIGCONT, SIGINT, SIGKILL, each with its own 0.1s check) has already failed and raised -- which, per the 123-12 live evidence, only happened during active transfers, never on an idle restart. A normal shutdown never reaches this wait at all; `test_idle_close_succeeds_no_poll_no_signal_no_wait` pins that the waiter is never called, `kill_group` is never called, and `isalive()` is never polled after a clean close. The alternative without any wait -- a blocking `os.waitpid(pid, 0)` -- was rejected because it is unbounded if the child stays in uninterruptible I/O (state D): it could hang the in-process controller restart (RECOV-01) indefinitely, which is a worse outcome than a documented, bounded wait that, if exceeded, still raises `LftpError` so the leak surfaces honestly. The owner approved exactly this one bounded wait in advance (123-13-PLAN.md `<owner_decision>`, verbatim: "Allow it (Recommended)"); no other new sleep exists anywhere in this plan's changes.

## Files Created/Modified

- `src/python/lftp/lftp.py` -- added `describe_lftp_process()`; added `EXIT_REAP_TIMEOUT_SECS`/`EXIT_REAP_POLL_INTERVAL_SECS` class constants; `__init__` gained keyword-only `clock`/`waiter`/`kill_group`/`describe_process` parameters; `exit()` now sends `exit kill` and wraps `close(force=True)` in a try/except that calls the new `__reap_after_failed_close()`/`__poll_isalive()` private methods on a failed close; docstrings rewritten to document the GAP-2 mechanism.
- `src/python/tests/unittests/test_lftp/test_lftp_exit.py` -- new file: `_FakeLftpProcess`, `_FakeClock`, `_FakeWaiter`, `_FakeKillGroup` test doubles and 11 tests covering the idle no-op, `exit kill`, the fallback reap with and without a group kill, the bounded raise, `ProcessLookupError` tolerance, status-unavailable warning, graceful-failure propagation, absence of harness detector strings, the public constants, and `describe_lftp_process`.

## Decisions Made

See `key-decisions` in the frontmatter above (the owner-approved bounded wait, the rejected unbounded-`waitpid` alternative, `exit kill`'s rationale, and the D-02 split).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a floating-point off-by-one in the GREEN verification run, caused by the test fixture, not the production fix**
- **Found during:** Task 2 (GREEN), running `test_child_never_dies_raises_lftp_error_after_bounded_wait`
- **Issue:** `_FakeClock` (written in Task 1/RED) defaulted its starting value to `1000.0`. Repeated binary floating-point addition of `0.05` onto that larger base accumulates more rounding error per step than starting from `0.0` does (verified: summing `0.05` forty times onto `1000.0` lands at `1001.9999999999982`, not `1002.0`). That made the fallback's poll loop take 41 waits instead of the intended `ceil(2.0 / 0.05) = 40` before crossing the deadline, failing the test's `assertLessEqual(len(waiter.calls), 40)` -- a bug in the test double's choice of starting value, not in `Lftp.__reap_after_failed_close()`'s logic or bound.
- **Fix:** Changed `_FakeClock`'s default `start` from `1000.0` to `0.0` (summing `0.05` forty times onto `0.0` lands at `2.000000000000001`, matching real `time.monotonic()`/`time.sleep()` behaviour where OS scheduling rounds actual elapsed time up, not down). Documented the reasoning in the class docstring.
- **Files modified:** `src/python/tests/unittests/test_lftp/test_lftp_exit.py`
- **Verification:** Re-ran `pytest tests/unittests/test_lftp/ tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_controller.py` -> 233 passed, 0 failed.
- **Committed in:** `e03e3bd` (Task 2/GREEN commit, alongside `lftp.py`; documented there rather than amending the RED commit, since the project's git-safety rules reserve amending for explicit user requests)

**2. [Rule 3 - Blocking] Installed this worktree's poetry dev dependencies before the RED run**
- **Found during:** Task 1 (RED), first verification attempt
- **Issue:** `poetry run pytest` in this freshly-created worktree resolved to a global pipx-installed `pytest` (`/Users/julianamacbook/.local/bin/pytest`), not this project's pinned `pytest 9.1.1`/`pytest-timeout` combination, because the poetry virtualenv's dev dependencies (including `pytest`) had not yet been installed in this worktree.
- **Fix:** Ran `poetry install --with dev` in `src/python/`, which installed `pytest`, `pytest-cov`, `pytest-timeout`, and the project's other dev dependencies into the worktree's own virtualenv; `poetry run which pytest` then correctly resolved to the venv's binary.
- **Files modified:** none (environment setup only; no project files changed)
- **Verification:** The ImportError-based RED result (above) was then observed from the correct, project-pinned test runner.
- **Committed in:** n/a (no file changes to commit)

---

**Total deviations:** 2 auto-fixed (1 test-fixture bug, 1 blocking environment setup)
**Impact on plan:** Both were necessary to produce a trustworthy RED/GREEN result in this worktree; neither changed the production fix's logic, bound, or the public log/exception text specified in the plan's interfaces.

## Issues Encountered

- This worktree's branch HEAD did not initially match the orchestrator-supplied base commit: `git merge-base HEAD 0932061...` resolved to `a56a1f8...` (a Phase 122 pre-merge ancestor), and `0932061` was confirmed NOT an ancestor of the worktree's starting HEAD (`d82c4ae`, PR #134's merge commit onto `main`). Per the mandatory `<worktree_branch_check>` step, the branch namespace was confirmed to be a valid per-agent branch (`worktree-agent-ad3906469e1b6503d`, not a protected ref) first, then `git reset --hard 093206122fb1efd8bf05896c2e941b4eec08a5d8` was run, correcting the worktree to the expected phase-123 gap-closure base before any plan file was read or edited. (This same situation, with the same resolution, is documented in 123-08-SUMMARY.md for a prior worktree spawn.)
- See the "Deviations from Plan" poetry-install note above for the second environment-setup issue encountered in this worktree.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GAP-2's unit-provable half (D-01, the lftp side) is closed: a child that survives pexpect's own force close is now killed by process group and reaped within a bounded 2.0s window without a false `Error stopping lftp` / `Could not terminate the child` ERROR, or the failure surfaces honestly via `LftpError` if it genuinely never dies. The idle (clean shutdown) path is byte-for-byte unchanged, pinned by regression test.
- `exit kill` removes the one related risk found during diagnosis (lftp's documented background-fork-on-exit behaviour) before it was ever observed live, so 123-14's live sampler should find no detached lftp surviving the app.
- 123-16/123-17 can now re-run the live active-transfer `docker restart` cycles on a build containing this fix to confirm: (a) no `Error stopping lftp` / `Could not terminate the child` on a real restart, (b) the lftp pid and its children are gone before the old container stops, and (c) the actual `/proc` state letter logged at the fallback, settling the D-state hypothesis left open in this plan's diagnosis.
- 123-15's Gate 5b should list exactly the one owner-approved bounded wait documented above (`EXIT_REAP_TIMEOUT_SECS`/`EXIT_REAP_POLL_INTERVAL_SECS` in `Lftp.__reap_after_failed_close()`) and no other new sleep from this plan.
- No blockers identified for dependent plans in this wave. Plan 123-14 (proc sampler and restart-cycle harness) ran concurrently in a sibling worktree on disjoint files; no overlap with this plan's two files.

## Self-Check: PASSED

- FOUND: src/python/lftp/lftp.py
- FOUND: src/python/tests/unittests/test_lftp/test_lftp_exit.py
- FOUND commit: 01045b8 (test(123-13))
- FOUND commit: e03e3bd (fix(123-13))

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*
