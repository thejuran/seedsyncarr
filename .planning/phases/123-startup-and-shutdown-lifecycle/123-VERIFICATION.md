---
phase: 123-startup-and-shutdown-lifecycle
verified: 2026-10-27T00:26:48Z
status: gaps_found
score: 7/7 must-haves verified
has_blocking_gaps: false
overrides_applied: 1
overrides:
  - must_have: "A clean startup and a clean shutdown behave exactly as before (no new sleeps, no lifecycle-framework rewrite)"
    reason: "Lftp.exit()'s post-close reap fallback needs exactly one bounded wait (EXIT_REAP_TIMEOUT_SECS=2.0s, polling every 0.05s via an injectable waiter defaulting to time.sleep) to reap an lftp child that outlives pexpect's own force-close kill sequence during an active transfer. Verified unreachable on a clean/idle shutdown (test_idle_close_succeeds_no_poll_no_signal_no_wait pins zero waiter/kill_group/isalive calls). The rejected alternative (unbounded os.waitpid) could hang the in-process RECOV-01 restart indefinitely if the child is stuck in uninterruptible I/O (state D), which this phase's own live evidence confirms actually happens."
    accepted_by: "thejuran"
    accepted_at: "2026-10-26T00:00:00Z"
gaps:
  - truth: "The D-01 SIGTERM/shutdown race fix in ScanManager._check_process_health() covers every shutdown signal the app handles, not just SIGTERM"
    status: partial
    severity: minor
    reason: "Code review finding WR-01 (123-REVIEW.md, committed after the owner's 123-07 verdict sign-off, so not yet seen or decided by the owner): scan_manager.py:312's grace-window check is `if all(process.exitcode == -signal.SIGTERM ...)`, SIGINT-only. Seedsyncarr installs the same handler for SIGTERM and SIGINT (seedsyncarr.py:118-119), and app_process.py resets scanner children's SIGINT to SIG_DFL too, so a process-group SIGINT (Ctrl-C on a foreground run, or `docker run -it`) hits the identical false-ERROR race D-01 was built to close. The project's actual restart paths (NAS production/sandbox docker-compose `restart`/`stop`, PR CI's Docker-image e2e tests) only ever deliver SIGTERM to the container, which is independently confirmed fixed by 123-04/123-08's unit tests and this phase's 17 live restart cycles (0 false scanner-died errors across all of them). No live or unit evidence shows the SIGINT path actually firing in this project's deployment model."
    artifacts:
      - path: "src/python/controller/scan_manager.py"
        issue: "Line 312 `all(process.exitcode == -signal.SIGTERM for _, process in dead)` does not also accept -signal.SIGINT, so a SIGINT-killed scanner set takes the unchanged ERROR + ScannerProcessDiedError path instead of the grace window"
    missing:
      - "Widen the grace-window exitcode check to `frozenset((-signal.SIGTERM, -signal.SIGINT))` per 123-REVIEW.md's suggested fix, with a test mirroring the existing all-SIGTERM grace test using exitcode=-signal.SIGINT"
      - "Owner decision: fix now, or accept as a backlog item (it does not reach any of this project's real docker-compose restart/stop paths) and record it in deferred-items.md alongside the other owner-reviewed backlog items"
---

# Phase 123: Startup and Shutdown Lifecycle Verification Report

**Phase Goal:** A failure partway through startup or cleanup never leaves started children running or skips the cleanup of later components
**Requirements:** LIFE-01, LIFE-02
**Verified:** 2026-10-27T00:26:48Z
**Status:** gaps_found (one minor, non-blocking gap; routes to backlog per `has_blocking_gaps: false`)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All truths below were checked against the actual source diff (`git diff origin/main...HEAD -- src/`), the actual test files (collected and executed, not just read), and — for the live-restart claims — independently cross-checked against GitHub (`gh pr view/checks`), GHCR (`docker buildx imagetools inspect`) and a live, read-only SSH query of the NAS sandbox/production containers, not merely SUMMARY.md/evidence-file narration.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1/LIFE-01 — A failure injected into startup after some children started stops/cleans up those children and the original failure still surfaces | VERIFIED | `controller.py:354-375` (`Controller.start()`), `scan_manager.py:133-147` (`ScanManager.start()`) both track `started` and stop everything already started + lftp before re-raising the **same** exception object. Confirmed by running `TestControllerStartPartialFailure` and `test_partial_start_{second,third}_process_fails_stops_started` — all pass (`302 passed` across the phase's 10 modified/added test files). Diff shows the "before" state had no try/except at all (bare `self.__scan_manager.start()` / `self.setup()`), confirming this is a real fix, not a pre-existing behavior pinned by a trivial test. |
| 2 | SC2/LIFE-02 — A failure during cleanup of one component does not skip cleanup of the remaining components; the first error is logged, not swallowed | VERIFIED | `scan_manager.py:170-192` (`_terminate_and_join`), `file_operation_manager.py:118-144` (`stop()`), `controller.py:433-440` (`exit()`'s per-component `try/except Exception: logger.exception` loop, pre-existing and unchanged) all isolate failures per-step. `TestControllerExitIsolation`, `test_cleanup_isolation_terminate_error_continues`, `test_cleanup_isolation_join_error_continues`, `test_stop_cleanup_isolation_release_error_continues` all pass. |
| 3 | SC3 — Existing per-component controller cleanup, auto-delete shutdown guards and lock ordering are unchanged; existing tests stay green | VERIFIED | `git diff origin/main...HEAD -- src/python/controller/controller.py` shows `Controller.exit()` (lines 407-442) is **untouched** — only `start()` gained the partial-start loop and a new `note_shutdown_requested()` method was added after `exit()`. `auto_delete_manager.py` has zero diff. Independently ran `test_auto_delete.py` + `test_auto_delete_rearm.py`: `161 passed, 0 failed`, matching the evidence file's claim exactly. |
| 4 | SC4 — A clean startup/shutdown behave exactly as before: no new sleeps, no lifecycle-framework rewrite | PASSED (override) | `git diff origin/main...HEAD -- src/python \| grep "^+" \| grep "sleep("` returns exactly one hit, which is a comment in a test file, not code. The two `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` DEFER-SHUTDOWN lines in `seedsyncarr.py` are present and untouched. The sole new wait is the injectable `waiter: Callable[[float], None] = time.sleep` default parameter in `Lftp.__init__` (`lftp.py:96`), reached only from `__reap_after_failed_close()` after pexpect's own force-close already raised — see override above, owner-approved in `123-13-PLAN.md`'s `<owner_decision>` block ("Allow it (Recommended)"). No new lifecycle class/abstraction was introduced; the fix mirrors `Controller.exit()`'s existing per-component try/except pattern throughout. |
| 5 | D-01 (owner-folded scope) — A normal `docker restart`/`stop` logs neither `Scanner process(es) died unexpectedly` nor `Could not terminate the child`, and the app comes back up normally | VERIFIED | Unit: `test_sigterm_death_handler_late_1_55s_resolves_as_shutdown` (10.0s monotonic-clock grace, `scan_manager.py:249-335`) and `test_child_exits_only_after_group_sigkill_is_reaped_without_error` (`lftp.py:558-620`) both pass. Live: `123-LIFE-EVIDENCE.md`'s gap-round-2 table shows 6/6 restart cycles (I1, I2, A1, A2, A1r, I3) with `SCANNER_DIED=0`, `COULD_NOT_TERMINATE=0`, `ERROR_STOPPING=0`, `PROCS_RESULT=ok`, `CHECK_STATUS=PASS`. Independently re-checked right now via `ssh nas`: sandbox `seedsyncarr-test` is currently pinned to `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0...` (the claimed `--final` restore pin, confirmed live, not just read from the evidence file) and production `seedsyncarr`'s `StartedAt` (`2026-10-23T07:04:18Z`) predates this phase's work entirely, confirming production was never touched. |
| 6 | D-04/D-05/D-06 — A startup failure stops/joins what started then surfaces through the existing bounded RECOV-01 auto-restart, with no degraded mode and no new exit-the-container path; the original exception is never masked by a cleanup exception | VERIFIED | `ControllerJob.setup()` wraps non-`AppError` exceptions in `ControllerError(AppError)` (`controller_job.py:25-32`), routed to the pre-existing `except AppError` main-loop path — confirmed `ControllerError` subclasses `AppError` (`controller.py:83`). `Job.run()`'s cleanup except-block only sets `exc_info` `if self.exc_info is None` (`job.py:59-64`), and `test_setup_error_not_masked_by_cleanup_error`/`test_partial_start_cleanup_error_does_not_mask_original` pass. No code path exits the process or runs with a subset of components started. |
| 7 | Requirements LIFE-01 and LIFE-02 are satisfied, with the owner's sign-off recorded | VERIFIED | `REQUIREMENTS.md` lines 22-23/75-76 mark both `[x]` / "Complete", mapped only to Phase 123, no orphans. `git show 0d9fcc8` (`docs(123-07): record owner sign-off`) and `123-LIFE-EVIDENCE.md`'s "## Owner review" section record the owner's verbatim reply "approve, backlog both items" after a PR #137 vibe-check deep review (5 reviewers, 0 findings ≥70). |

**Score:** 7/7 truths verified (1 via a pre-existing, owner-approved override)

### Minor Gap Found During This Verification (not previously surfaced to the owner)

| # | Item | Severity | Why not blocking |
|---|------|----------|-------------------|
| 1 | WR-01 (123-REVIEW.md): the D-01 SIGTERM grace window in `scan_manager.py:312` does not also treat `-signal.SIGINT` deaths as the same shutdown race, even though the app's signal handler (`seedsyncarr.py:118-119`) and the scanner children's signal reset (`app_process.py:67-68`) both apply to SIGINT too | minor | Only reachable via a process-group SIGINT (interactive Ctrl-C / `docker run -it`), not this project's actual restart path (NAS production/sandbox `docker restart`/`stop` via docker-compose, which always sends SIGTERM). 17 live restart cycles across this phase show 0 false scanner-died errors on the real path. `123-REVIEW.md` was committed (`0ab2365`) **after** the owner's 123-07 verdict sign-off (`0d9fcc8`), so this specific finding has not yet been shown to the owner — unlike the two PR #137 deep-review items the owner already reviewed and said "approve, backlog both items" to. |

This gap is recorded in the frontmatter `gaps:` with `severity: minor` and `has_blocking_gaps: false`, so it auto-routes to backlog (`/bm:add-backlog`) rather than a follow-up phase. Recommend adding it to `deferred-items.md` alongside the other two owner-reviewed, backlogged findings once the owner has had a chance to see it (it postdates their sign-off).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/python/common/job.py` | `setup()`/`cleanup()` wrapped so failures surface and never silently mask each other | VERIFIED | Diff confirms try/except added around both (previously bare calls); `exc_info is None` guard present (D-06) |
| `src/python/controller/controller_job.py` | Non-`AppError` start failures re-raised as `ControllerError` chained from the original | VERIFIED | `raise ControllerError(...) from exc`; `ControllerError` is an `AppError` subclass |
| `src/python/controller/controller.py` | `start()` per-component partial-start cleanup; `exit()` byte-identical; new `note_shutdown_requested()` | VERIFIED | Diff isolates the change to `start()` plus a new method; `exit()` (lines 407-442) has zero diff |
| `src/python/controller/scan_manager.py` | Per-process started tracking, per-process terminate/join isolation, shutdown-aware + SIGTERM-grace health check | VERIFIED | `start()`/`_terminate_and_join()`/`_check_process_health()` all match must-have text; `_SIGTERM_SHUTDOWN_GRACE_IN_SECS = 10.0` present |
| `src/python/controller/file_operation_manager.py` | Per-wrapper reservation-release isolation in `stop()` | VERIFIED | `stop()` wraps each `reservation.release()` independently; `logger.exception` on failure, sanitized root name |
| `src/python/common/multiprocessing_logger.py` | `stop()` never-started guard | VERIFIED | `if self.__listener.ident is None: return` |
| `src/python/web/web_app_job.py` | `cleanup()` None-guards for a `setup()` that never assigned the server/thread | VERIFIED | `if self.__server is not None` / `if self.__server_thread is not None` |
| `src/python/lftp/lftp.py` | Bounded SIGKILL-to-group-and-reap fallback after a failed pexpect force close; `exit kill` | VERIFIED | `EXIT_REAP_TIMEOUT_SECS = 2.0`, `__reap_after_failed_close()`, `exit kill` sendline all present and match must-have text |
| `src/python/seedsyncarr.py` | Signal handler marks shutdown on the live controller before raising `ServiceExit`; DEFER-SHUTDOWN sleeps unchanged | VERIFIED | `self.__controller.note_shutdown_requested()` called inside a try/except in `signal()`; both `sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` lines present, zero diff |
| 9 regression test files (`test_job.py`, `test_controller_job.py`, `test_controller.py`, `test_scan_manager.py`, `test_file_operation_manager.py`, `test_multiprocessing_logger.py`, `test_lftp_exit.py`, `test_web_app_job.py`, `test_seedsyncarr.py`) | Injected-failure RED-first regression tests | VERIFIED | All named tests from must-haves (`test_partial_start_scanner_fails_exits_lftp_only`, `test_idle_close_succeeds_no_poll_no_signal_no_wait`, `test_sigterm_death_handler_late_1_55s_resolves_as_shutdown`, `test_child_exits_only_after_group_sigkill_is_reaped_without_error`, `TestWebAppJobCleanup`, `TestControllerStartPartialFailure`, `TestControllerExitIsolation`) collected and pass; `test(123-NN)` commits precede `fix(123-NN)` commits for NN = 01,02,03,04,08,13, and every RED commit touches only `src/python/tests/` |
| `.planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh`, `123-proc-sampler.sh`, `123-teardown.sh` | Live-restart evidence-gathering harness | VERIFIED | All three exist, `bash -n` passes on all three (syntax valid); content matches the documented STARTED/INCOMPLETE/PROCS_RESULT behavior described in must-haves |
| `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` | Per-cycle live evidence, `--final` restore record, Phase 123 verdict | VERIFIED | Contains `## Phase 123 verdict`, `CHECK_STATUS=PASS`, `SANDBOX_RESTORED ok`, `DEV_PIN_GAP2=...7f354c14...` — independently cross-checked (see Key Links) |
| `.planning/phases/123-startup-and-shutdown-lifecycle/deferred-items.md` | Out-of-scope findings for backlog review | VERIFIED | Contains `Controller.__init__` eager-lftp-spawn note, `persist()` masking note, DEFER-SHUTDOWN verdict, the two owner-reviewed PR #137 deep-review backlog items — does **not** yet contain WR-01 (see gap above, found by this verification) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `Job.run()` setup except-block | `Job.propagate_exception()` | `self.exc_info = sys.exc_info()` | VERIFIED | Confirmed in diff and by passing `test_setup_exception_propagates` |
| `ScanManager.start()` except-block | `ScanManager._terminate_and_join()` | cleanup of the already-started subset, then bare `raise` | VERIFIED | Confirmed in code and by passing `test_partial_start_{second,third}_process_fails_stops_started` |
| `Controller.start()` except-block | `self.__lftp_manager.exit` + already-started components' `stop()` | per-component try/except mirroring `Controller.exit()` | VERIFIED | Confirmed in code (`controller.py:366-373`) and by `test_partial_start_scanner_fails_exits_lftp_only` |
| `Seedsyncarr.signal()` | `Controller.note_shutdown_requested()` | `self.__controller` set in `run()` after `Controller(...)` is built | VERIFIED | Confirmed in diff (`seedsyncarr.py`) |
| `Lftp.exit()` finally-block | `pexpect` `close(force=True)` → `__reap_after_failed_close()` | `except pexpect.exceptions.ExceptionPexpect` | VERIFIED | Confirmed in code (`lftp.py:542-546`) and by passing `test_child_exits_only_after_group_sigkill_is_reaped_without_error` |
| `GD2/state.env` `CHECK_STATUS` | Phase 123 verdict | `GAP2_CAPTURE_DIR` line in `123-LIFE-EVIDENCE.md` | VERIFIED | Evidence file states `CHECK_STATUS=PASS`; independently re-confirmed live via `ssh nas` that the sandbox is now restored to the claimed final pin and production is untouched |
| PR #137 head SHA | CI run (Build Docker Image, Python/Angular unit tests, etc.) | `pull_request` event on push | VERIFIED | `gh pr checks 137` run independently during this verification: all 13 non-skipped checks report `pass` on run `40401640233`/`40401634114` (run_number 410), matching the evidence file exactly; `gh pr view 137` confirms `headRefOid=4074b0c6...`, `isDraft=true`, `state=OPEN` |
| `ghcr.io/thejuran/seedsyncarr:410` | `DEV_PIN_GAP2` digest | `buildx imagetools inspect` | VERIFIED | Ran `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:410` independently: `Digest: sha256:7f354c149f2df586e7045ca47e971448b57dc1459a1a450f7a12aca885471a0c`, byte-identical to the evidence file's `DEV_PIN_GAP2` |

### Data-Flow Trace (Level 4)

Not applicable. This phase's artifacts are backend lifecycle-control logic (process start/stop ordering), a shell-script restart-evidence harness, and planning/evidence documents — none render dynamic data to a user-facing surface, so there is no UI data-flow to trace.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full unit suite matches the documented 24-line macOS-environment baseline | `cd src/python && python -m pytest tests/unittests -q` (fresh venv, independent of the executor's environment) | `21 failed, 1851 passed, 1 warning, 3 errors, 77 subtests passed` — the exact 24 failure/error lines are `test_extract_process.py` (6), `test_scanner_process.py` (3 FAILED + 3 ERROR), `test_sshcp.py` (10/11), `test_scanner.py::test_scan_file_with_latin_chars` (1); none touch this phase's `src/` diff | PASS |
| Whole-tree ruff is clean | `cd src/python && ruff check .` | `All checks passed!` | PASS |
| The 9 phase-modified/added test files plus the two auto-delete regression suites all pass | `python -m pytest <10 files> -q` | `302 passed` / `161 passed` (auto-delete) | PASS |
| Named regression tests from must-haves actually exist and are collected | `pytest --collect-only -q \| grep <11 test names>` | All 11 found (`test_partial_start_scanner_fails_exits_lftp_only`, `TestControllerStartPartialFailure::*`, `TestControllerExitIsolation::*`, `test_sigterm_death_handler_late_1_55s_resolves_as_shutdown`, `test_idle_close_succeeds_no_poll_no_signal_no_wait`, `test_child_exits_only_after_group_sigkill_is_reaped_without_error`, `TestWebAppJobCleanup::test_cleanup_without_setup_does_not_raise`) | PASS |
| RED-before-GREEN commit ordering (123-01..04, 08, 13) | `git log --oneline --reverse -- src/python \| grep -E "^[a-f0-9]+ (test\|fix)\(123-(01\|02\|03\|04\|08\|13)\)"` | `test(123-NN)` precedes `fix(123-NN)` for every NN; each RED commit's `--stat` touches only `src/python/tests/...` paths | PASS |
| Scope: non-test `src/` diff vs `origin/main` is exactly the 18 files declared across the phase (16 for LIFE-01/02/D-01-scanner + lftp.py/test_lftp_exit.py for GAP-2) | `git diff origin/main...HEAD --stat -- src/` | 9 production files + 9 test files = 18, matching the plans' declared file lists exactly | PASS |
| PR #137 CI is green on the claimed head SHA | `gh pr checks 137` | 13/13 non-skipped checks `pass` | PASS |
| GHCR digest for the shipping image matches the recorded `DEV_PIN_GAP2` | `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:410` | `sha256:7f354c14...` matches exactly | PASS |
| NAS sandbox is currently restored to the claimed final pin; production untouched | `ssh nas 'sudo /usr/local/bin/docker inspect seedsyncarr-test --format {{.Config.Image}}; sudo /usr/local/bin/docker inspect seedsyncarr --format "{{.Config.Image}} {{.State.StartedAt}}"'` | sandbox = `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0...` (claimed `IMAGE_PIN_L0`); production = same 1.7.6 digest with `StartedAt=2026-10-23T07:04:18Z` (predates this phase) | PASS |

### Probe Execution

SKIPPED — no `scripts/*/tests/probe-*.sh` convention exists in this project; this phase used its own `123-restart-cycle.sh`/`123-proc-sampler.sh` live-restart harness on the NAS sandbox instead, whose claimed outcomes are verified above under Key Links and Behavioral Spot-Checks (including an independent, this-session, read-only re-check of the current NAS container state).

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| LIFE-01 | 123-01, 123-02, 123-03 | Already-started children cleaned up when startup fails partway, demonstrated by an injected-failure test | SATISFIED | `TestControllerStartPartialFailure`, `test_partial_start_{second,third}_process_fails_stops_started`, all passing; code confirmed to be a genuine before/after fix (bare calls → tracked partial-start loops) |
| LIFE-02 | 123-02, 123-03 | Cleanup of one component failing does not skip cleanup of the remaining components; existing per-component controller cleanup, auto-delete shutdown guards and lock ordering preserved | SATISFIED | `TestControllerExitIsolation`, `test_cleanup_isolation_*`; `Controller.exit()` zero-diff; `test_auto_delete.py`/`test_auto_delete_rearm.py` = 161 passed |

No orphaned requirements: `REQUIREMENTS.md`'s traceability table maps only LIFE-01/LIFE-02 to Phase 123, and every plan's `requirements:` frontmatter field declares only these two IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/python/controller/scan_manager.py` | 312 | SIGTERM-only exitcode check in the shutdown-grace branch (WR-01) | Warning (minor, see Gap above) | SIGINT-killed scanners (interactive/Ctrl-C only, not this project's docker-compose restart path) still hit the pre-fix false-ERROR race |
| `src/python/web/web_app_job.py` | 29-35, 48-49 | `__server_thread is not None` guard does not cover a constructed-but-unstarted thread whose `.start()` itself raised (IN-01) | Info | Advisory only; `__server.stop()` already fails first on the `None` inner server today, which is the already-backlogged `WebAppJob.cleanup()` isolation item |
| `src/python/common/job.py` | 37, 63-64, 79-81 | Cross-thread check-then-set on `exc_info` without a lock (IN-02) | Info | Latent race; today does no harm because `ControllerJob.cleanup()` → `Controller.exit()` never raises |
| `src/python/controller/file_operation_manager.py` | 142-145 | `__extract_process.terminate()`/`.join()` unguarded, unlike `ScanManager`'s per-process isolation (IN-03) | Info | `Controller.exit()`'s per-component catch still prevents this from leaking across components; matches the must-have's narrower scope (reservation-release isolation only) |
| `src/python/lftp/lftp.py` | 571-575, 606-611 | Reap fallback treats any `ExceptionPexpect` from `isalive()` the same as ECHILD, reporting success (IN-04) | Info | Could mask a non-ECHILD error as "already reaped"; narrower than the stated "surfaces honestly" goal |

No 🛑 Blocker-level anti-patterns and no unreferenced `TBD`/`FIXME`/`XXX` debt markers found in any phase-modified file.

### Human Verification Required

None. All claims in this phase (code-level behavior, test existence/passing, commit ordering, PR/CI state, GHCR digest, and current NAS container state) were independently verified via tooling in this session rather than deferred to a human — see Behavioral Spot-Checks and Key Links above.

### Gaps Summary

The phase goal is achieved: LIFE-01 and LIFE-02 are both real, test-proven fixes (confirmed by reading the before/after diff, not just the test names), `Controller.exit()` and the auto-delete guards are provably byte-identical and still pass their full regression suites, the one new sleep is a pre-existing owner-approved exception to success criterion 4, and the D-01 restart-error root causes (the scanner SIGTERM race and the lftp reap race) are fixed and confirmed live across 17 restart cycles plus an independent, this-session, read-only check of the NAS sandbox's current (restored) state and production's (untouched) state.

One minor, non-blocking gap was found during this verification that had not yet been surfaced to the owner: WR-01, a real but narrowly-scoped latent bug where the D-01 SIGTERM grace window does not also cover SIGINT. It cannot occur on this project's actual deployment/restart path (docker-compose `restart`/`stop`, always SIGTERM), so it does not block the phase goal, but it postdates the owner's 123-07 sign-off and deserves an explicit decision (fix now vs. backlog) rather than being silently absorbed. Recommend routing it to the backlog via `/bm:add-backlog` and, once the owner has seen it, adding it to `deferred-items.md` alongside the other two already-reviewed PR #137 deep-review findings.

---

_Verified: 2026-10-27T00:26:48Z_
_Verifier: Claude (bm-verifier)_
