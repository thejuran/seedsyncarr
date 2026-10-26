# Phase 123 LIFE-01 / LIFE-02 evidence

## Unit regressions (RED before GREEN)

| Plan | Test commit | Fix commit | Tests failing at RED |
|------|-------------|------------|-----------------------|
| 123-01 (Job setup-failure surfacing) | `647eef0` | `277257f` | `test_setup_exception_propagates`, `test_cleanup_executes_on_setup_error`, `test_setup_error_sets_shutdown_flag`, `test_setup_error_not_masked_by_cleanup_error`, `test_cleanup_error_surfaces_on_clean_run`, `test_setup_non_apperror_wrapped_in_controller_error`, `test_setup_failure_thread_runs_cleanup_and_surfaces`, `test_cleanup_without_setup_does_not_raise` (8 failed, 9 passed) |
| 123-02 (ScanManager / FileOperationManager partial-start + cleanup isolation) | `cbf6dcd` | `04eac94` | `test_partial_start_third_process_fails_stops_started`, `test_partial_start_second_process_fails_stops_started`, `test_partial_start_cleanup_error_does_not_mask_original`, `test_cleanup_isolation_terminate_error_continues`, `test_cleanup_isolation_join_error_continues`, `test_stop_cleanup_isolation_release_error_continues` (6 failed, 43 passed) |
| 123-03 (Controller.start() partial-failure cleanup) | `1908ed8` | `29dd4c4` | `test_partial_start_file_ops_fails_stops_started`, `test_partial_start_mp_logger_fails_stops_started`, `test_partial_start_scanner_fails_exits_lftp_only`, `test_partial_start_cleanup_error_does_not_mask_original`, `test_stop_without_start_is_safe` (5 failed, 45 passed) |
| 123-04 (shutdown-aware scanner health check, D-01) | `2c87bcf` | `c69559c` | `test_shutdown_aware_dead_scanners_after_request_do_not_raise`, `test_shutdown_aware_any_exitcode_after_request_does_not_raise`, `test_shutdown_aware_sigterm_death_rechecked_once_then_raises`, `test_shutdown_aware_sigterm_death_then_request_is_benign`, `test_note_shutdown_requested_delegates_to_scan_manager`, `test_note_shutdown_requested_does_not_touch_auto_delete_guard`, `test_signal_marks_shutdown_on_controller_then_raises`, `test_signal_note_failure_is_logged_and_still_raises` (8 failed, 110 passed) |

Each test commit (`git show --stat --format=`) lists only paths under `src/python/tests/`, confirmed directly in this plan's Gate 3 run.

## Gates

BASE for scope/diff gates: `git merge-base origin/main HEAD` = `a56a1f8a12be232e5dfe8067a3db715df1f45255` (resolved after `git fetch origin`; `origin/main` HEAD is `d82c4ae`, the PR #134 merge commit).

| Gate | Result |
|------|--------|
| 1 — full unit-suite failure set subset of the 122-03 baseline | PASS — `21 failed, 1833 passed, 2 warnings, 3 errors, 77 subtests passed in 82.39s (0:01:22)`; `comm -23 current baseline` empty (24/24 lines identical to the documented environment baseline: `test_extract_process.py` x6, `test_scanner_process.py` 3 FAILED + 3 ERROR, `test_sshcp.py` x10, `test_scanner.py::test_scan_file_with_latin_chars` x1) |
| 2 — whole-tree ruff | PASS — `ruff check src/python/` → `All checks passed!` |
| 3 — RED before GREEN | PASS — `test(123-01)` `647eef0` < `fix(123-01)` `277257f`; `test(123-02)` `cbf6dcd` < `fix(123-02)` `04eac94`; `test(123-03)` `1908ed8` < `fix(123-03)` `29dd4c4`; `test(123-04)` `2c87bcf` < `fix(123-04)` `c69559c`; each test commit touches only `src/python/tests/` paths |
| 4 — scope (src/ diff since BASE) | PASS — `git diff --name-only BASE..HEAD -- src/` sorted equals exactly the 16 declared files across 123-01..04 (`wc -l` = 16, diff against expected list empty) |
| 5 — no new sleeps (criterion 4) | PASS — `git diff BASE..HEAD -- src/python ':(exclude)src/python/tests' \| grep "^+" \| grep -c "sleep("` → `0`; `grep -c "time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)" src/python/seedsyncarr.py` → `2` (both DEFER-SHUTDOWN sleeps kept, D-03) |
| 6 — criterion 3 (exit(), auto-delete, lock ordering unchanged) | PASS — `sed`-extracted `Controller.exit()` text at BASE vs HEAD: empty diff (byte-identical); `test_auto_delete.py` + `test_auto_delete_rearm.py`: `161 passed` (0 failed); `grep -c "__shutdown_event.set()" src/python/controller/controller.py` → `3` at both BASE and HEAD |
| 7 — log hygiene | PASS — new non-test log calls listed (`Job.run()`'s setup/cleanup exception logs, `Controller.start()`'s per-component failure logs, `FileOperationManager.stop()`'s reservation-release logs, `ScanManager`'s terminate/join/health-check logs, `Seedsyncarr.signal()`'s shutdown-marking log) reviewed directly: none interpolates config values, passwords, tokens or keys; the one root-name line (`FileOperationManager.stop()`'s reservation-release debug/exception pair) uses `sanitize_log_value(wrapper.reservation.name)` |

## D-02 split (unit-proven vs live-proven)

**Unit-proven (123-01..04, this phase's gates):**
- `Job.run()`'s `setup()` call now mirrors the existing `execute()` except-block: a `setup()` failure sets `exc_info`, sets `shutdown_flag`, and still runs `cleanup()` exactly once; a `cleanup()` failure never masks an earlier setup/execute failure (D-06 guard `if self.exc_info is None: ...`) (123-01).
- `ControllerJob.setup()` re-raises `AppError` unchanged and wraps any other exception in `ControllerError(...) from exc`, routing non-`AppError` startup failures into the existing RECOV-01 `except AppError` main-loop path (123-01).
- `WebAppJob.cleanup()` is safe to call after a `setup()` that raised before assigning the server/server-thread (123-01).
- `ScanManager.start()` tracks which of the three scanner processes actually started and stops/joins only that subset, via a fault-isolated `_terminate_and_join()` helper, before re-raising the original exception unmasked (123-02).
- `FileOperationManager.stop()`'s reservation-release loop fault-isolates each wrapper's `reservation.release()` so one failing release never skips the rest or the extract-process stop (123-02).
- `Controller.start()` tracks started components (plus lftp) and runs an `exit()`-style per-component cleanup loop on a later failure, then re-raises the original exception unmasked; `Controller.exit()` itself verified byte-identical (123-03).
- `MultiprocessingLogger.stop()` gained a never-started guard (`Thread.ident is None`), closing the `RuntimeError: cannot join thread before it is started` gap a blind partial-start cleanup could trigger (123-03).
- `ScanManager.note_shutdown_requested()` + the shutdown-aware three-branch `_check_process_health()`: dead scanners observed after a requested shutdown log INFO and never raise; an all-SIGTERM death with no request yet gets exactly one extra health-check cycle before the unchanged ERROR + `ScannerProcessDiedError` path fires; `Controller.note_shutdown_requested()` delegates to `ScanManager` with no lock and leaves `__shutdown_event` untouched; `Seedsyncarr.signal()` marks shutdown on the live controller (if any) before raising `ServiceExit`, with its own failure guarded and logged (123-04).
- The unchanged genuine-death ERROR path, `Controller.exit()`'s per-component loop, both DEFER-SHUTDOWN sleep call sites, and the auto-delete shutdown guard/lock ordering are all exercised as regression pins across 123-01..04 and this plan's Gates 5/6.

**Live-proven only (123-06/07 — not claimed here):**
- That `tini -g` actually delivers the container's SIGTERM to the process group and that the forked scanner children die with exitcode `-15` on a real `docker restart`.
- That a real restart, after this fix, logs neither "Scanner process(es) died unexpectedly" nor raises `ScannerProcessDiedError` — the actual elimination of the Phase 122 restart error on the shipping build.
- The lftp "Could not terminate the child" error: a separate mechanism (lftp's pty child calls `setsid()`, so `tini -g`'s process-group SIGTERM never reaches it directly); no lftp code was touched in 123-01..04; 123-06/07's restart cycles (idle and active-transfer) are its only proof.

## D-03 decision (DEFER-SHUTDOWN sleep kept)

**Kept, no code change.** Both `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` call sites in `src/python/seedsyncarr.py` are byte-for-byte unchanged across 123-01..04, confirmed again by this plan's Gate 5 (`grep -c` → `2`; `grep "^+" | grep -c "sleep("` → `0`). The existing DEFER-SHUTDOWN backlog note in `.planning/codebase/CONCERNS.md` stays as is.

Evidence (RESEARCH.md): the kernel delivers the container's process-group SIGTERM to the forked scanner children instantaneously and independently of anything running on the python main thread — no amount of shortening, lengthening, or removing the 0.5s sleep can change whether that direct kernel-level signal kills them. The 2026-10-23 14:14:37-38 sandbox log excerpt (RESEARCH.md's architecture diagram) shows the `ControllerJob` thread self-detecting the dead scanners and running `Controller.exit()` to completion in well under 1 second — before the main thread's 0.5s DEFER-SHUTDOWN sleep path had even reached its own `terminate()` call. The self-triggered path, not the sleep-gated path, is what actually ran `Lftp.exit()` in the originally observed failing case, so the sleep was never the mechanism producing either restart error in the first place.

## Build under test

- **PR:** https://github.com/thejuran/seedsyncarr/pull/137 (draft, base `main`, head `gsd/phase-123-startup-and-shutdown-lifecycle`)
- **NEW_HEAD_SHA:** `0cae08127d9403063960ace2e109c52542245af7`
- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/40221779333 (run_number 407), conclusion **success**, headSha matches NEW_HEAD_SHA
- **Per-check conclusions** (`gh pr checks 137`): Analyze (actions) pass 41s; Analyze (javascript-typescript) pass 56s; Analyze (python) pass 55s; CodeQL pass 2s; Angular unit tests pass 2m6s; Lint (Angular) pass 18s; Lint (Python) pass 8s; Python unit tests pass 5m0s; Verify Python package pass 21s; Verify release metadata pass 4s; Release metadata verifier tests pass 11s; Build Docker Image pass 2m29s; End-to-end tests on Docker Image (amd64) pass 4m47s; Publish Docker Image / Publish Docker Image (:dev) / Publish Documentation / Publish GitHub Release / Publish to PyPI all `skipping` (pull_request event, expected — not merge/tag)
- **Digest lookup 1 (buildx):** `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:407` → `Digest: sha256:b7b894fa88b371eac4456389b7b7c78f26fb9f61f6501dae9729d1d584ed9f22`
- **Digest lookup 2 (anonymous GHCR token HEAD):** `docker-content-digest: sha256:b7b894fa88b371eac4456389b7b7c78f26fb9f61f6501dae9729d1d584ed9f22` (identical to lookup 1)
- **Equivalence guard:** confirmed immediately before and immediately after both digest lookups that `git rev-parse HEAD` and `gh pr view 137 --json headRefOid -q .headRefOid` both still equal `0cae08127d9403063960ace2e109c52542245af7` — no later push occurred
- `DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:b7b894fa88b371eac4456389b7b7c78f26fb9f61f6501dae9729d1d584ed9f22`
- Differs from the 1.7.6 production digest (`sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`) and from the Phase 122 pin (`sha256:f8204207ef199f183f6230b74bd8967397732a5919570b09dcec7dc3f2341689`)
- Sandbox's expected restore pin: `IMAGE_PIN_L0=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`

## Sandbox re-pin (123-06)

Capture dir (NAS, mode 0700, not committed): `/volume1/docker/v5test/results/life01-123-20261025T185719Z`.
Sandbox `seedsyncarr-test` re-pinned from the 1.7.6 pin (`IMAGE_PIN_L0`) to DEV_PIN (`.Config.Image` = DEV_PIN, image id `sha256:c9f26006…`). App-log clock is America/New_York (UTC-4 on 2026-10-25), so log `15:19:47` = `19:19:47Z`.

| Cycle | Kind | Restart (UTC) | Scanner ERROR | lftp "Could not terminate" | "stopped during shutdown" INFO | "Exited successfully" | Result |
|-------|------|---------------|---------------|----------------------------|--------------------------------|-----------------------|--------|
| I1 | idle | 19:19:38Z | 1 (19:19:47.355Z, SIGTERM caught 19:19:48.901Z, +1.55 s) | 0 | 0 | 0 | FAIL |
| I2 | idle | 19:22:09Z | 0 | 0 | 1 (SIGTERM caught 19:22:15.890Z first) | 1 | pass (window); no CYCLE_I2 line was written to state.env |
| A1 | active (SSA123.Alpha.S01) | — | 1 | 0 | 0 | 0 | FAIL |
| A2 | active (SSA123.Bravo.S01) | 19:30:54Z | 1 (19:30:58.639Z, SIGTERM caught 19:30:59.307Z, +0.67 s) | 3 (after the scanner-error exit path) | 0 | 0 | FAIL |
| I3 | idle | 19:33:28Z | 0 | 0 | 0 | 0 | FAIL (exited_successfully only) |

CHECK_STATUS=FAIL (state.env).

Diagnosis: the 123-04 one-cycle SIGTERM recheck (`ScanManager._check_process_health()`) assumes the main thread's SIGTERM handler (`Seedsyncarr.signal()` → `note_shutdown_requested()`) runs within milliseconds of tini's group SIGTERM. Live, it ran 0.67–1.55 s after the scanners died, longer than one 0.5 s ControllerJob cycle, so the grace expired and the ERROR + ScannerProcessDiedError fired (I1, A1, A2). When the handler ran first (I2) the new INFO path worked as designed. The lftp error in A2 followed the scanner-error exit path. The missing "Exited successfully" (I3) also appears in the 1.7.6 baseline (`BASELINE_EXITED_SUCCESSFULLY=0`), so it is pre-existing, not a Phase 123 regression.

Production fingerprint: unchanged across both sessions (`PROD_UNCHANGED_S1`, `PROD_UNCHANGED_S2`).
Session teardown: NOT run. The executor stalled before the teardown step. No `SSA123.` name under `/volume1/data/v5test/torrents`; seedbox staging is not yet verified clean. The sandbox remains on DEV_PIN and healthy, pending the gap round.

Owner decision (123-06 Task 3, 2026-10-26): "Fix in this phase (Recommended)" (= option `fix-in-phase`). Route: `/bm:plan-phase 123 --gaps`.

## Gap round (GAP-1)

### Gap

123-06's live sandbox restart check found that the 123-04 one-cycle SIGTERM recheck lost the race against the real main-thread shutdown-signal handler on 3 of 5 restart cycles (I1, A1, A2): the handler ran 0.67-1.55 s after the scanners died, longer than the single 0.5 s `ControllerJob` cycle the recheck allowed, so the false "Scanner process(es) died unexpectedly" ERROR and `ScannerProcessDiedError` still fired. Owner decision (123-06 Task 3, 2026-10-26): fix in this phase (route `/bm:plan-phase 123 --gaps`), rather than deferring GAP-1 past Phase 123.

### Fix (123-08)

`ScanManager` now takes an injected monotonic clock (`clock: Callable[[], float] = time.monotonic`, matching the existing `arr_queue.py` / `completion_gate.py` clock-injection pattern) and replaces the one-cycle boolean recheck latch with a deadline measured from the first sighting of an all-SIGTERM death: `__sigterm_first_seen: Optional[float]` is set once, and every later check within `now - first_seen < _SIGTERM_SHUTDOWN_GRACE_IN_SECS` (10.0 s) returns without logging or raising. The window is 10.0 s because that is docker's own default `stop` timeout — the handler either runs inside that window, or docker SIGKILLs the container when the window ends, so the false-positive ERROR is bounded to zero on any real `docker stop`/`docker restart` either way. The deadline is fixed at the first sighting and is not extended by a second scanner dying SIGTERM later inside the same window (`test_sigterm_grace_measured_from_first_sighting`).

**Documented detection-delay cost:** a genuine SIGTERM-only death with no shutdown request now surfaces up to 10 s plus one `ControllerJob` cycle later than before this change (previously, one 0.5 s cycle). Every other kind of death (SIGKILL/OOM's exitcode `-9`, a non-zero exit, or a mix that includes a non-SIGTERM code) is unaffected and still raises on the same check it is first seen, unchanged (`test_sigterm_grace_then_non_sigterm_death_raises_immediately`, `test_nonzero_exit_raises_on_first_check`).

**Rejected alternatives:**
- `signal.pthread_sigmask` blocking SIGTERM in worker threads — rejected because forked children inherit the forking thread's signal mask, and the scanner processes are forked from the `ControllerJob` thread, so blocking SIGTERM there would be inherited by those same children and would break `AppProcess.terminate()`, which relies on sending them SIGTERM. It also cannot cover threads created by libraries outside this code's control (the web server, multiprocessing feeders, `Timer` threads).
- Children handling SIGTERM themselves — rejected as a wider change to child-process signal-handling semantics than this gap needs, and it would not by itself fix the parent-side race (the parent still has to distinguish an expected stop from a genuine death).

**RED/GREEN:** RED `17387a6` (`test(123-08)`, only `src/python/tests/unittests/test_controller/test_scan_manager.py`, 9 failed / 24 passed) → GREEN `1ffc601` (`fix(123-08)`, only `src/python/controller/scan_manager.py`, 133 passed / 0 failed across the touched suites). RED test names: `test_sigterm_grace_defaults`, `test_sigterm_death_not_reported_within_grace_across_many_cycles`, `test_sigterm_death_handler_late_1_55s_resolves_as_shutdown`, `test_sigterm_death_handler_late_0_67s_resolves_as_shutdown`, `test_sigterm_death_raises_when_grace_elapses`, `test_sigterm_grace_measured_from_first_sighting`, `test_sigterm_grace_then_non_sigterm_death_raises_immediately`, `test_nonzero_exit_raises_on_first_check`, `test_shutdown_aware_sigterm_death_then_request_is_benign` (modified to pass `clock=`).

### D-02 split (gap round)

**Unit-proven (123-08, fake clock, no real processes or sleeps):** the 10.0 s grace window itself and that nothing is reported within it across many intervening cycles; the exact live I1 (+1.55 s) and A2 (+0.67 s) handler-latency timings from the sandbox re-pin table above, replayed as deterministic regression tests; the bounded surfacing of a genuine SIGTERM-only death once the window elapses; that the deadline is fixed at first sighting and not extended; that any non-SIGTERM death still raises immediately, unchanged.

**Live-proven only (123-11/123-12 — not claimed here):** that a real `docker restart`/`docker stop` on the DEV_PIN_GAP build below logs neither the false "Scanner process(es) died unexpectedly" ERROR nor raises `ScannerProcessDiedError`, across repeated idle and active-transfer cycles, closing the 3-of-5 FAIL result from the sandbox re-pin table above; that the 10 s window never collides with docker's own stop-timeout-then-SIGKILL behavior on the real NAS sandbox; the lftp "Could not terminate the child" half (no lftp code was touched by 123-08).

### Harness change (123-09)

`123-restart-cycle.sh`'s "Exited successfully" line moved from a PASS/FAIL criterion to recorded-only (`EXITED_SUCCESSFULLY` is still counted and written to `cycle-<label>.env`, just no longer a fail reason). Justification: that line is logged only after the full shutdown sequence completes, so it is absent whenever docker's 10 s stop timeout has to SIGKILL the process instead — this is the same gap D-01's done criterion is about (a normal restart should log no error and come back up, not necessarily log every possible completion message), and the pre-existing 1.7.6 production baseline already shows this exact gap (`BASELINE_EXITED_SUCCESSFULLY=0`), confirmed again live by I3 in the sandbox re-pin table above (`"Exited successfully"` column = 0, yet I3's only recorded failure reason was `exited_successfully`, not a real shutdown error). Every D-01 shutdown-error criterion that actually gates a cycle's pass/fail (`scanner_died`, `could_not_terminate`, `caught_exception_in_job`, `error_stopping`, `restart_rc`) is unchanged, still hard pass/fail. The harness also gained a `CYCLE_<label>_STARTED=<utc>` marker written before each restart and an `INCOMPLETE:<step>` EXIT-trap outcome, so a cycle that is interrupted (SIGTERM/SIGINT/SIGHUP, or the executor stalling as it did in 123-06) is always visible in `state.env` as started-without-verdict rather than silently missing, plus `RESTART_ELAPSED_S` recording docker restart wall time for each cycle.

### Gates (gap round)

| Gate | Result |
|------|--------|
| 1 — full unit-suite failure set subset of the 122-03 baseline | PASS — `21 failed, 1840 passed, 2 warnings, 3 errors, 77 subtests passed in 83.04s`; `comm -23 current baseline` empty (24/24 lines identical to the documented environment baseline) |
| 2 — whole-tree ruff | PASS — `ruff check src/python/` → `All checks passed!` |
| 3 — RED before GREEN (incl. 123-08) | PASS — `test(123-NN)` precedes `fix(123-NN)` for NN = 01, 02, 03, 04, 08 (`17387a6` < `1ffc601` for 08); every test commit (incl. `17387a6`) touches only `src/python/tests/` paths |
| 4 — scope (src/ diff since BASE, 16-file list) | PASS — `git diff --name-only BASE..HEAD -- src/` sorted equals exactly the 16 declared files (`wc -l` = 16) |
| 5 — no new sleeps (criterion 4) | PASS — 0 new `sleep(` lines in non-test src/python vs BASE; `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` count in `seedsyncarr.py` = 2 (both DEFER-SHUTDOWN sleeps kept) |
| 6 — criterion 3 (exit(), auto-delete unchanged) | PASS — `Controller.exit()` byte-identical BASE vs HEAD; `test_auto_delete.py` + `test_auto_delete_rearm.py` = 161 passed, 0 failed; `__shutdown_event.set()` count = 3 at both BASE and HEAD |
| 7 — log hygiene (gap delta) | PASS — the only new log call in the gap delta is one `logger.debug(...)` in `ScanManager._check_process_health()`, interpolating only scanner process names and the grace-window constant; no config values or secrets |
| 8 — gap delta scope (vs 123-05 PR head `0cae081`) | PASS — `git diff --name-only 0cae081..HEAD -- src/` prints exactly `src/python/controller/scan_manager.py` and `src/python/tests/unittests/test_controller/test_scan_manager.py` |
| 9 — untouched wiring (controller.py/seedsyncarr.py/job.py/constants.py vs `0cae081`) | PASS — empty diff |

Quick suite (`123-VALIDATION.md`): `cd src/python && timeout 300 poetry run pytest tests/unittests/test_common/test_job.py tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_controller_job.py tests/unittests/test_controller/test_file_operation_manager.py tests/unittests/test_controller/test_auto_delete.py -p no:cacheprovider -q` → `250 passed, 1 warning in 2.05s`.

### Build under test (gap round)

- **PR:** https://github.com/thejuran/seedsyncarr/pull/137 (draft, base `main`, head `gsd/phase-123-startup-and-shutdown-lifecycle`)
- **NEW_HEAD_SHA_GAP:** `ff527dc9037f93eca2772c44fe4dace3838f90f5`
- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/40379266127 (run_number **409**), conclusion **success**, headSha matches NEW_HEAD_SHA_GAP
- **Per-check conclusions** (`gh pr checks 137`): Analyze (actions) pass 42s; Analyze (javascript-typescript) pass 54s; Analyze (python) pass 51s; Angular unit tests pass 2m22s; Build Docker Image pass 5m3s; CodeQL pass 3s; End-to-end tests on Docker Image (amd64) pass 3m46s; Lint (Angular) pass 16s; Lint (Python) pass 6s; Python unit tests pass 5m10s; Verify Python package pass 21s; Verify release metadata pass 4s; Release metadata verifier tests pass 7s; Publish Docker Image / Publish Docker Image (:dev) / Publish Documentation / Publish GitHub Release / Publish to PyPI all `skipping` (pull_request event, expected)
- **Digest lookup 1 (buildx):** `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:409` → `Digest: sha256:991e4e1f28b90c6020c911a65c4814314aa5860682df8aa9e389e365d7872da6`
- **Digest lookup 2 (anonymous GHCR token HEAD):** `docker-content-digest: sha256:991e4e1f28b90c6020c911a65c4814314aa5860682df8aa9e389e365d7872da6` (identical to lookup 1)
- **Equivalence guard:** confirmed immediately before and immediately after both digest lookups that `git rev-parse HEAD` and `gh pr view 137 --json headRefOid -q .headRefOid` both still equal `ff527dc9037f93eca2772c44fe4dace3838f90f5` — no later push occurred; `git merge-base --is-ancestor 1ffc601 ff527dc9037f93eca2772c44fe4dace3838f90f5` exits 0 (fix(123-08) is an ancestor of NEW_HEAD_SHA_GAP)
- `DEV_PIN_GAP=ghcr.io/thejuran/seedsyncarr@sha256:991e4e1f28b90c6020c911a65c4814314aa5860682df8aa9e389e365d7872da6`
- `OLD_DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:b7b894fa88b371eac4456389b7b7c78f26fb9f61f6501dae9729d1d584ed9f22` (what the sandbox is on now)
- Differs from the 123-05 DEV_PIN (`sha256:b7b894fa...`), the 1.7.6 production digest (`sha256:da6196e0...`) and the Phase 122 pin (`sha256:f8204207...`)

## Gap-round live check (123-11/123-12)

`GAP_CAPTURE_DIR=/volume1/docker/v5test/results/life01-123-gap-20261026T185841Z` (mode 0700, not committed). `OLD_CAPTURE_DIR=/volume1/docker/v5test/results/life01-123-20261025T185719Z`.

Clock offset used throughout: the app log is America/New_York local time (EDT, UTC-4 on 2026-10-26, before the 2026-11-01 US DST change). Every quoted log line below is paired with its NAS UTC equivalent (local + 4h).

### Outstanding 123-06 session teardown (seedbox verified clean)

The SSA123 session teardown left open by 123-06 was run against `OLD_CAPTURE_DIR` (`bash OLD_D/teardown.sh OLD_D`, session mode, no `--final`), detached and polled. Output (`run-old-teardown.out`):

```
RESTORED rate_limit ok (not set this session)
RESTORED delay_seconds ok (not set this session)
REMOVED synth roots count=2 refused=0
RESTORED webhook_secret ok (not set this session)
WAIT server/status ok
CHECK webhook/sonarr Test http=200
SANDBOX_RESTORED ok
```

Pre-check (before running teardown) already showed the seedbox and sandbox were clean — the data-removal work was effectively done earlier, but the formal `SANDBOX_RESTORED ok` marker and `OLD_TEARDOWN=ok` record from 123-06 were missing until this run:
- Seedbox `/home/jules1651/v5test` listing: no `SSA123.`-prefixed name
- Seedbox `/home/jules1651/ssa123-stage`: absent
- Sandbox `/volume1/data/v5test/torrents`: no `SSA123.`-prefixed name (contains only `Hacks.S01.XviD-AFG`, `Hacks.S03E07.1080p.BluRay.x264-BRAVERY`)
- `/server/config/get` `.lftp.rate_limit` = `0`, equal to `OLD_D`'s `RATE_LIMIT_L0=0`
- `seedsyncarr-test` `.Config.Image` = `OLD_DEV_PIN` (`sha256:b7b894fa...`) at check time
- `/server/status` returned 200

`OLD_TEARDOWN=ok` and `SEEDBOX_CLEAN=ok` recorded in `GD/state.env`. The post-teardown app-log window (`MT=6664` marker, `log-old-teardown.txt`) held only the two `Action.STOP` commands for the already-absent SSA123 roots and the webhook Test event — zero of any restart-related string, because this teardown step runs `compose start` (a no-op on an already-running container, not a restart) rather than a lifecycle restart.

Production fingerprint before this plan's work (`prod-before-s0.txt`) was byte-identical to `OLD_D`'s last recorded production fingerprint (`prod-after-s2.txt`): no drift.

### Re-pin: OLD_DEV_PIN -> DEV_PIN_GAP

Preflight confirmed both the compose `seedsyncarr-test` image line and `.Config.Image` equal `OLD_DEV_PIN` before any edit. Compose-file inode preserved across the edit: `INODE_BEFORE=101505523`, `INODE_AFTER=101505523` (identical — inode-preserving awk-to-temp-then-cat edit confirmed).

Readiness transcript:
- Pre-deploy marker `M0=6669`
- `compose pull seedsyncarr-test` then `compose up -d seedsyncarr-test`: container recreated (`Recreate` -> `Recreated` -> `Starting` -> `Started`)
- Fresh `Starting SeedSyncarr` app-log line observed at `2026-10-26 15:15:27,167` local (`2026-10-26T19:15:27Z`), after the `M0` marker — `STARTING_OK=1`
- `/server/status` HTTP 200 immediately after — `READY_OK=1`
- 8 s settle, then `.Config.Image` verified equal to `DEV_PIN_GAP` exactly; `.Image` (image id) = `sha256:e85e11af8bf441bd7fa08d22d71f6ecc1db06256d6d1c2a811b0694837d42e7e`

The `M0` window (the OLD_DEV_PIN build's shutdown, an informational detector sample, not gating) showed: `SCANNER_DIED=0`, `COULD_NOT_TERMINATE=0`, `CAUGHT_EXCEPTION_IN_JOB=0`, `ERROR_STOPPING=0`, `EXITED_SUCCESSFULLY=0`, `STARTING_SEEN=1`, `STOPPED_DURING_SHUTDOWN=1`, `ERROR_LINES=0`. This particular OLD_DEV_PIN shutdown happened to win the race (handler ran before the scanners were checked, same as I2 in the 123-06 table) — consistent with the previously documented probabilistic 3-of-5 failure rate on that build, not a contradiction of it.

`prod-after-s1.txt` was byte-identical to `prod-before-s1.txt` (`PROD_UNCHANGED_S1`).

### Idle cycles I1, I2 on DEV_PIN_GAP

| Cycle | Kind | Restart (UTC) | RESTART_ELAPSED_S | SCANNER_DIED | COULD_NOT_TERMINATE | CAUGHT_EXCEPTION_IN_JOB | ERROR_STOPPING | STOPPED_DURING_SHUTDOWN | EXITED_SUCCESSFULLY (recorded only) | Result |
|-------|------|----------------|--------------------|--------------|----------------------|--------------------------|-----------------|---------------------------|--------------------------------------|--------|
| I1 (first run) | idle | 19:16:09Z | 124 | 0 | 0 | 0 | 0 | 1 | 0 | PASS |
| I1 (rerun, see Deviations) | idle | 19:20:38Z | 146 | 0 | 0 | 0 | 0 | 1 | 1 | PASS |
| I2 | idle | 19:24:02Z | 143 | 0 | 0 | 0 | 0 | 1 | 0 | PASS |

Each row's `SIGTERM caught` -> `stopped during shutdown` (INFO) -> `Exited controller` sequence, with both clocks:

- I1 (first run): SIGTERM `2026-10-26 15:16:15,700` (`19:16:15.700Z`); stopped-during-shutdown `15:16:16,047` (`19:16:16.047Z`, +0.35s); Exited controller `15:16:16,854` (`19:16:16.854Z`). No scanner-died ERROR.
- I1 (rerun): SIGTERM `15:20:47,925` (`19:20:47.925Z`); stopped-during-shutdown `15:20:48,055` (`19:20:48.055Z`, +0.13s); Exited controller `15:20:48,901`; Exited successfully `15:21:02,080`. No scanner-died ERROR.
- I2: SIGTERM `15:24:10,473` (`19:24:10.473Z`); stopped-during-shutdown `15:24:10,873` (`19:24:10.873Z`, +0.40s); Exited controller `15:24:11,704`. No scanner-died ERROR.

All three restarts on `DEV_PIN_GAP` logged the clean `Scanner process(es) stopped during shutdown` INFO path (the 123-04/123-08 expected-stop path) and zero of `Scanner process(es) died unexpectedly`, `Could not terminate the child`, `Caught exception in job`, or `Error stopping` — the false alarm that fired on 3 of 5 cycles pre-fix (123-06) did not reproduce on any of these three live restarts post-fix.

`prod-before-s2a.txt` and `prod-after-s2a.txt` were byte-identical (`PROD_UNCHANGED_S2A`).

### Deviations (this section)

- **Duplicate I1 launch (harness/operational, no product impact).** The first attempt to launch `restart-cycle.sh ... I1` used a `cd "$GD" && nohup ... &` shell form; on this NAS's remote command shell, a `&&`-joined command immediately followed by `&` does not actually detach (confirmed by a minimal `sleep` reproduction: the `&&` form blocks for the full duration, a `;`-joined form returns in ~0.2s). The executor's tool call was therefore auto-backgrounded by its own 120s local timeout while the remote I1 cycle was still genuinely running attached; believing the launch had not yet started, a second `I1` cycle was launched (correctly detached, with `;`) before realizing the first had already completed and recorded `CYCLE_I1=PASS`. Both runs are real, both are clean idle restarts with zero shutdown-error strings on `DEV_PIN_GAP` (see table above); the original run's window/env files were preserved as `cycle-I1-orig.env` / `log-cycle-I1-orig.txt` before the second run overwrote `cycle-I1.env` / `log-cycle-I1.txt`. All subsequent detached launches (I2, and onward) used the `;`-joined form and confirmed sub-second return before polling separately, per the plan's stall-prevention requirement. Production was not touched by this deviation; only `seedsyncarr-test` restarted an extra time.

### Active cycles A1 (SSA123.Delta.S01), A2 (SSA123.Echo.S01) and final idle cycle I3 on DEV_PIN_GAP

| Cycle | Kind | Restart (UTC) | RESTART_ELAPSED_S | SCANNER_DIED | COULD_NOT_TERMINATE | CAUGHT_EXCEPTION_IN_JOB | ERROR_STOPPING | STOPPED_DURING_SHUTDOWN | EXITED_SUCCESSFULLY (recorded only) | Result |
|-------|------|---------------|--------------------|--------------|----------------------|--------------------------|-----------------|---------------------------|--------------------------------------|--------|
| A1 | active (SSA123.Delta.S01) | 19:38:01Z | 150 | 0 | 3 | 0 | 1 | 0 | 0 | FAIL:could_not_terminate,error_stopping |
| A2 | active (SSA123.Echo.S01) | 19:44:27Z | 131 | 0 | 3 | 0 | 1 | 1 | 0 | FAIL:could_not_terminate,error_stopping |
| I3 | idle | 19:49:36Z | 137 | 0 | 0 | 0 | 0 | 1 | 1 | PASS |

Shutdown sequence per cycle, both clocks:

- A1: SIGTERM `2026-10-26 15:38:12,292` (`19:38:12.292Z`); no `Scanner process(es) stopped during shutdown` line appears in this window (see note below); `Error stopping lftp during controller exit` `15:38:14,093` (`19:38:14.093Z`, +1.801s); Exited controller `15:38:14,405` (+2.113s). Zero scanner-died ERROR.
- A2: SIGTERM `15:44:33,587` (`19:44:33.587Z`); stopped-during-shutdown `15:44:33,998` (+0.411s); `Error stopping lftp during controller exit` `15:44:35,232` (+1.645s); Exited controller `15:44:35,332` (+1.745s). Zero scanner-died ERROR.
- I3: SIGTERM `15:49:46,006` (`19:49:46.006Z`); stopped-during-shutdown `15:49:46,331` (+0.325s); Exited controller `15:49:47,282` (+1.276s); Exited successfully `15:50:00,072` (+14.066s). Zero scanner-died ERROR, zero lftp error.

Note on A1's missing "stopped during shutdown" line: `Controller.exit()` (`src/python/controller/controller.py:433-440`) stops components in a fixed order -- lftp first, then scanner. That INFO line is logged only inside `ScanManager._check_process_health()` (`src/python/controller/scan_manager.py:307`), which runs on the `ControllerJob`'s periodic health-check cycle, not inside `ScanManager.stop()` itself. In A1, lftp's `exit()` call blocked for ~1.8s on the same thread before raising, so no intervening health-check cycle observed the dead scanners before `stop()` directly terminated and joined them -- a timing artifact of this recorded-only signal, not a correctness gap: `SCANNER_DIED` stayed 0 in both A1 and A2, i.e. the GAP-1 fix held in every active-transfer cycle regardless of whether this INFO line happened to fire.

**Active-transfer proof:**

- Delta (A1): released `2026-10-26 15:36:29,385` local (`19:36:29.385Z`), http 200 (`RELEASED_SSA123.Delta.S01=1`). `model-delta-pre-1.json`: downloading, local=979,988,071 / remote=2,516,582,400 (38.9%). `model-delta-pre-2.json` (+4s): downloading, local=1,237,909,504 / remote=2,516,582,400 (49.2%, increasing). Restart launched immediately after the second snapshot, in the same `ssh` call. Post-restart: held again -- `Completion hold for 'SSA123.Delta.S01': No matching queue entry` logged `15:42:26,220` local (`19:42:26.220Z`); `model-delta-post.json` confirms `hold=no_queue_entry`, local frozen at 1,378,025,472 (no further growth observed over three 5s-spaced polls beforehand).
- Echo (A2): released `2026-10-26 15:43:47,554` local (`19:43:47.554Z`), http 200 (`RELEASED_SSA123.Echo.S01=1`). `model-echo-pre-1.json`: downloading, local=328,164,513 / remote=2,516,582,400 (13.0%). `model-echo-pre-2.json` (+4s): downloading, local=488,632,558 / remote=2,516,582,400 (19.4%, increasing). Restart launched immediately after, in the same `ssh` call. Post-restart: held again -- `Completion hold for 'SSA123.Echo.S01': No matching queue entry` logged `15:48:57,645` local (`19:48:57.645Z`); `model-echo-post.json` confirms `hold=no_queue_entry`, local frozen at 681,443,328.

### lftp re-measurement (D-01 lftp half)

| Cycle | COULD_NOT_TERMINATE | ERROR_STOPPING |
|-------|----------------------|-----------------|
| A1 (GAP-1, SSA123.Delta.S01) | 3 | 1 |
| A2 (GAP-1, SSA123.Echo.S01) | 3 | 1 |
| A2 (123-06, pre-fix, SSA123.Bravo.S01) | 3 (after the scanner-error exit path) | not separately recorded in 123-06's table |

Reading: both GAP-1 active cycles show the same `COULD_NOT_TERMINATE=3` count seen in 123-06's A2, but now with `SCANNER_DIED=0` on both -- the lftp `Could not terminate the child` / `Error stopping lftp during controller exit` failure is unchanged by the GAP-1 scanner-grace fix (123-08) and remains a separate, already-isolated mechanism: `Controller.exit()`'s per-component loop catches the exception, logs it, and proceeds to stop the remaining components and exit cleanly regardless (`RESTART_RC=0`, `STARTING_OK=1`, `READY_OK=1`, `SCAN_OK=1` on both A1 and A2 -- the container always came back up and resumed scanning).

### Recorded-only signals

| Cycle | EXITED_SUCCESSFULLY | RESTART_ELAPSED_S |
|-------|----------------------|--------------------|
| I1 (first run) | 0 | 124 |
| I1 (rerun) | 1 | 146 |
| I2 | 0 | 143 |
| A1 | 0 | 150 |
| A2 | 0 | 131 |
| I3 | 1 | 137 |

`BASELINE_EXITED_SUCCESSFULLY=0` (1.7.6, recorded during this session's re-pin window as `BASELINE_REPIN_EXITED_SUCCESSFULLY`) -- 4 of 6 gap-round cycles also read 0, consistent with the pre-existing gap documented at 123-09 (the line logs only after the full shutdown sequence completes, so it is absent whenever docker's 10s stop timeout would otherwise SIGKILL the process first). None of these readings affected any cycle's PASS/FAIL, per the 123-09 harness change.

SIGTERM -> `Scanner process(es) stopped during shutdown` gap, where present, across every cycle in the gap round:

| Cycle | Gap |
|-------|-----|
| I1 (first run) | +0.347s |
| I1 (rerun) | +0.130s |
| I2 | +0.400s |
| A1 | not present (see note above) |
| A2 | +0.411s |
| I3 | +0.325s |

Every observed gap is well inside the 10.0s GAP-1 grace window (123-08); the window comfortably absorbs the handler-latency variance seen live (0.13s-1.55s across all of 123-06/123-11/123-12).

### Gap-round verdict

`CHECK_STATUS=FAIL:A1:could_not_terminate,error_stopping,A2:could_not_terminate,error_stopping` (state.env).

Production: `prod-before-s2b.txt` and `prod-after-s2b.txt` byte-identical (`PROD_UNCHANGED_S2B`); production `seedsyncarr` was never restarted, edited or otherwise touched anywhere in this plan.

Session teardown: `run-session-teardown.out` (session mode, not `--final`):

```
RESTORED rate_limit ok
RESTORED delay_seconds ok (not set this session)
REMOVED synth roots count=2 refused=0
RESTORED webhook_secret ok (not set this session)
WAIT server/status ok
CHECK webhook/sonarr Test http=200
SANDBOX_RESTORED ok
```

Clean check (separate call, after teardown): no `SSA123.`-prefixed name under seedbox `/home/jules1651/v5test`; `/home/jules1651/ssa123-stage` absent; no `SSA123.`-prefixed name under `/volume1/data/v5test/torrents`; `.lftp.rate_limit` = `0` (equal to `RATE_LIMIT_L0`); `seedsyncarr-test` `.Config.Image` still equals `DEV_PIN_GAP` exactly. The sandbox stays on `DEV_PIN_GAP`; 123-07 restores `IMAGE_PIN_L0` (1.7.6) with `--final`.

Diagnosis (for the failure gate): every scanner and exception check passed cleanly in all five cycles of this gap round (I1 x2, I2, A1, A2, I3 all show `SCANNER_DIED=0`, `CAUGHT_EXCEPTION_IN_JOB=0`) -- the GAP-1 fix (123-08) is confirmed live: the false "Scanner process(es) died unexpectedly" ERROR that fired on 3 of 5 pre-fix cycles (123-06) did not reproduce in any of the 6 live restarts across 123-11/123-12. The only failing checks are `could_not_terminate` / `error_stopping`, both on active-transfer cycles (A1, A2), both from `Lftp.exit()` (`src/python/lftp/lftp.py:463`, via `pexpect`/`ptyprocess`) timing out while a transfer is in flight -- a mechanism no 123-01..04/123-08 commit touched (confirmed again by gate 9's untouched-wiring diff in the gap-round gates table above). `Controller.exit()`'s per-component loop (controller.py:433-440) isolates the failure: it is caught, logged, and the remaining components (scanner, file operations, multiprocessing logger) still stop cleanly, the container still restarts (`RESTART_RC=0`) and still comes back up scanning (`STARTING_OK=1`, `READY_OK=1`, `SCAN_OK=1` on both A1 and A2). "Exited successfully" is recorded only (123-09) and was not the reason for either FAIL (A1/A2's actual fail reasons are `could_not_terminate,error_stopping`, not `exited_successfully`).


### Gap-round failure gate (123-12 Task 3)

CHECK_STATUS=FAIL:A1:could_not_terminate,error_stopping,A2:could_not_terminate,error_stopping. GAP-1 (false scanner ERROR) is closed live: SCANNER_DIED=0 and CAUGHT_EXCEPTION_IN_JOB=0 in all six restarts (I1 x2, I2, A1, A2, I3). The remaining failure is the D-01 lftp half: `Error stopping lftp during controller exit` / `PtyProcessError: Could not terminate the child.` on both active-transfer restarts (`Lftp.exit()` -> pexpect/ptyprocess close(force=True)). It is contained by `Controller.exit()`'s per-component isolation, and the app restarts and scans normally.

Owner decision (2026-10-26): "Fix in this phase (Recommended)" (= option `fix-in-phase`). Route: `/bm:plan-phase 123 --gaps` (GAP-2: lftp shutdown on an active transfer). 123-07 must not mark the live check passed while this is open.
