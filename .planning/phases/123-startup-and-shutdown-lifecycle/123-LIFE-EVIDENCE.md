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
