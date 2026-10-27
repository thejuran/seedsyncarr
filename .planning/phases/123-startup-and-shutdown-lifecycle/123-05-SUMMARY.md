---
phase: 123-startup-and-shutdown-lifecycle
plan: 05
subsystem: ci-gate
tags: [phase-gate, push, draft-pr, ci, ghcr-digest, one-pr-per-phase]

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "01"
    provides: "Job.run() setup()-failure surfacing (LIFE-01)"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "02"
    provides: "ScanManager/FileOperationManager partial-start + cleanup isolation (LIFE-01, LIFE-02)"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "03"
    provides: "Controller.start() partial-failure cleanup (LIFE-01, LIFE-02)"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "04"
    provides: "Shutdown-aware scanner health check, D-01 unit-provable half (LIFE-02)"
provides:
  - "Phase gates 1-7 (suite-vs-baseline, whole-tree ruff, RED-before-GREEN, scope, sleep count, criterion-3 exit()/auto-delete regression, log hygiene) passing over 123-01..04 together"
  - "123-01..04 pushed as one draft PR (#137); every PR CI check green on the new head SHA"
  - "Staging image digest resolved by two independent methods and recorded as DEV_PIN for 123-06/07's live restart check"
affects: ["123-06 (live D-01 restart check consumes this DEV_PIN)", "123-07 (sandbox restore afterward)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md

key-decisions:
  - "BASE for scope/diff gates computed as git merge-base origin/main HEAD per the plan's interfaces note, resolving to a56a1f8 (a Phase 122 commit pre-dating the PR #134 merge commit d82c4ae that now sits on origin/main) rather than d82c4ae itself -- the phase-123 branch's own history diverges from d82c4ae's second parent, so the merge-base formula (not visual inspection of the merge commit) is authoritative, exactly as the plan specifies"
  - "No new PR needed to be opened mid-task; gh pr list for this branch returned empty, so Task 2 pushed and created exactly one new draft PR (#137) rather than reusing an existing one"

patterns-established: []

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: ~55min
completed: 2026-10-25
---

# Phase 123 Plan 05: Phase Gate, Draft PR, and Staging Digest Summary

**All seven phase gates pass over 123-01..04 together on the branch; the branch is pushed to a new single draft PR (#137) with every CI check green; the staging image digest is resolved by two independent methods and recorded as `DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:b7b894fa...` for 123-06's live restart check.**

## Performance

- **Duration:** ~55 min (includes a ~13 min CI wait for the Docker build/E2E jobs)
- **Started:** 2026-10-25T18:29:03Z
- **Completed:** 2026-10-25 (this summary)
- **Tasks:** 2 of 2 completed
- **Files modified:** 1 (`123-LIFE-EVIDENCE.md`, new file) plus this SUMMARY

## Task 1: Phase gates over 123-01..04

**Precondition:** `git branch --show-current` → `gsd/phase-123-startup-and-shutdown-lifecycle`; `git status --porcelain -- src/` → empty. `git fetch origin`; BASE = `git merge-base origin/main HEAD` = `a56a1f8a12be232e5dfe8067a3db715df1f45255`.

### Gate 1 — Full unit-suite failure set vs. 122-03 baseline

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q`

Result:
```
21 failed, 1833 passed, 2 warnings, 3 errors, 77 subtests passed in 82.39s (0:01:22)
```

`comm -23 current baseline` (current failure/error lines minus the exact 24-line 122-03-SUMMARY.md baseline, both sorted, trailing " - reason" text stripped):
```
(empty)
```

All 24 lines matched the documented environmental baseline exactly: `test_extract/test_extract_process.py` (6), `test_scan/test_scanner_process.py` (3 FAILED + 3 ERROR), `test_ssh/test_sshcp.py` (10), `test_system/test_scanner.py::test_scan_file_with_latin_chars` (1). **Gate 1: PASS.**

### Gate 2 — Whole-tree ruff

Command: `ruff check src/python/` (repo root)

Result: `All checks passed!` **Gate 2: PASS.**

### Gate 3 — RED before GREEN

```
git log --format="%h %s" --reverse a56a1f8..HEAD | grep -E "^[a-f0-9]+ (test|fix)\(123-0[1-4]\)"
```
```
647eef0 test(123-01): setup failures must surface and run cleanup; cleanup errors must not mask them
1908ed8 test(123-03): partial controller start must stop started components; pin exit() per-component isolation
cbf6dcd test(123-02): partial scanner start must stop started processes; one failing cleanup must not skip the rest
04eac94 fix(123-02): stop already-started scanner processes on a failed start and isolate per-process cleanup
29dd4c4 fix(123-03): stop already-started controller components and lftp when Controller.start fails partway
277257f fix(123-01): surface Job setup failures through propagate_exception and route controller start failures to RECOV-01
2c87bcf test(123-04): dead scanners during a requested shutdown must not log ERROR or raise
c69559c fix(123-04): treat scanner deaths after a requested shutdown as an expected stop (D-01)
```
`test(123-NN)` precedes `fix(123-NN)` for all four plans (01: `647eef0` < `277257f`; 02: `cbf6dcd` < `04eac94`; 03: `1908ed8` < `29dd4c4`; 04: `2c87bcf` < `c69559c`).

`git show --stat --format=` for each test commit listed only paths under `src/python/tests/`:
- `647eef0`: `test_job.py`, `test_controller_job.py`, `test_web_app_job.py`
- `cbf6dcd`: `test_file_operation_manager.py`, `test_scan_manager.py`
- `1908ed8`: `test_multiprocessing_logger.py`, `test_controller.py`
- `2c87bcf`: `test_controller.py`, `test_scan_manager.py`, `test_seedsyncarr.py`

**Gate 3: PASS.**

### Gate 4 — Scope diff (src/ files changed since BASE)

Command: `git diff --name-only a56a1f8..HEAD -- src/ | sort`

```
src/python/common/job.py
src/python/common/multiprocessing_logger.py
src/python/controller/controller.py
src/python/controller/controller_job.py
src/python/controller/file_operation_manager.py
src/python/controller/scan_manager.py
src/python/seedsyncarr.py
src/python/tests/unittests/test_common/test_job.py
src/python/tests/unittests/test_common/test_multiprocessing_logger.py
src/python/tests/unittests/test_controller/test_controller.py
src/python/tests/unittests/test_controller/test_controller_job.py
src/python/tests/unittests/test_controller/test_file_operation_manager.py
src/python/tests/unittests/test_controller/test_scan_manager.py
src/python/tests/unittests/test_seedsyncarr.py
src/python/tests/unittests/test_web/test_web_app_job.py
src/python/web/web_app_job.py
```

16 files — a direct `diff` against the plan's 16-file expected list (sorted) produced no differences. **Gate 4: PASS.**

### Gate 5 — No new sleeps (success criterion 4)

```
git diff a56a1f8..HEAD -- src/python ':(exclude)src/python/tests' | grep "^+" | grep -c "sleep("
```
→ `0`

```
grep -c "time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)" src/python/seedsyncarr.py
```
→ `2` (both DEFER-SHUTDOWN sleep call sites kept, per D-03 — see 123-LIFE-EVIDENCE.md's D-03 section)

**Gate 5: PASS.**

### Gate 6 — Success criterion 3 (exit(), auto-delete, lock ordering unchanged)

`Controller.exit()` text extracted at BASE and HEAD via `sed -n '/^    def exit(self):/,/^    def get_model_files/p'`, diffed:
```
(empty — byte-identical)
```

```
cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_auto_delete_rearm.py -p no:cacheprovider -q
```
→ `161 passed, 1 warning in 0.88s` (0 failed)

```
grep -c "__shutdown_event.set()" src/python/controller/controller.py
```
→ `3` at both BASE (via `git show BASE:...`) and HEAD.

**Gate 6: PASS.**

### Gate 7 — Log hygiene

```
git diff a56a1f8..HEAD -- src/python ':(exclude)src/python/tests' | grep "^+" | grep -E "logger\.(info|error|warning|exception|debug)"
```

New log calls (non-test src only), reviewed directly:
- `Job.run()`: `"Caught exception in setup for {}"` / `"Caught exception in cleanup for {}"` / `"Finished setup for {}"` / `"Finished cleanup for {}"` (component/job name only)
- `Controller.start()`'s failure path: `"Controller start failed at {}; stopping lftp and {} already-started component(s)"` / `"Error stopping {} after a failed controller start"` (component name, count only)
- `FileOperationManager.stop()`: `"Released root reservation for '{}' on stop"` / `"Error releasing root reservation for '{}' on stop"` — both use `sanitize_log_value(wrapper.reservation.name)`
- `ScanManager.start()`'s failure path: `"Scanner start failed at {}; stopping {} already-started process(es) after a failed scanner start"` (process name, count)
- `ScanManager._terminate_and_join()`: `"Error terminating {} process"` / `"Error joining {} process"` (process name)
- `ScanManager._check_process_health()`'s three branches: `"Scanner process(es) stopped during shutdown: {}"` (INFO) / `"Scanner process(es) ended by SIGTERM: {}; re-checking next cycle"` (DEBUG) / `"Scanner process(es) died unexpectedly: {}"` (ERROR, unchanged path) — all interpolate only process names and exit codes
- `Seedsyncarr.signal()`: `"Error marking shutdown requested on the controller"` (no interpolation)

None interpolates config values, passwords, tokens or keys. The one root-name line (`FileOperationManager.stop()`'s reservation-release pair) uses `sanitize_log_value`. **Gate 7: PASS.**

## Task 2: Push, draft PR, CI, digest, evidence file

- `gh pr list --head gsd/phase-123-startup-and-shutdown-lifecycle --state all` returned empty — no existing PR to reuse.
- Pushed (no force): `git push -u origin gsd/phase-123-startup-and-shutdown-lifecycle` → new branch on origin.
- Opened exactly one draft PR: **https://github.com/thejuran/seedsyncarr/pull/137**, title "Phase 123: startup and shutdown lifecycle (LIFE-01, LIFE-02)", base `main`, body covering the partial-startup/cleanup-isolation/false-restart-error behavior changes, the unchanged `exit()`/auto-delete/DEFER-SHUTDOWN items, and ending with the Claude Code attribution line.
- **NEW_HEAD_SHA:** `0cae08127d9403063960ace2e109c52542245af7`, confirmed equal to `gh pr view 137 --json headRefOid -q .headRefOid` immediately after PR creation and again immediately before/after the digest lookup (no later push occurred).
- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/40221779333 (run_number **407**), headSha matching NEW_HEAD_SHA, conclusion **success**. Watched via `gh run watch 40221779333 --exit-status` in the Bash tool's background mode (completed exit code 0, ~13 min).
- `gh pr checks 137` exit 0. Thirteen required checks pass (Analyze x3, CodeQL, Angular/Python unit tests, both Lint jobs, Verify Python package, Verify/Release metadata verifier tests, Build Docker Image, End-to-end tests on Docker Image); five `Publish *` jobs `skipping` as expected on a `pull_request` event.
- `git merge-base --is-ancestor c69559c 0cae08127d9403063960ace2e109c52542245af7` → exit 0 (fix(123-04) is an ancestor of NEW_HEAD_SHA).
- **Digest resolution**, two independent methods, identical result:
  - `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:407` → `sha256:b7b894fa88b371eac4456389b7b7c78f26fb9f61f6501dae9729d1d584ed9f22`
  - Anonymous GHCR bearer-token HEAD on `/v2/thejuran/seedsyncarr/manifests/407` → `docker-content-digest: sha256:b7b894fa88b371eac4456389b7b7c78f26fb9f61f6501dae9729d1d584ed9f22`
  - **DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:b7b894fa88b371eac4456389b7b7c78f26fb9f61f6501dae9729d1d584ed9f22** — differs from both the 1.7.6 production digest (`sha256:da6196e0...`) and the Phase 122 pin (`sha256:f8204207...`).
- Created `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` with the full gate table, D-02 unit/live split, D-03 decision, and Build-under-test section.
- No `gh pr ready`, no merge, no force push. `gh pr list --head gsd/phase-123-startup-and-shutdown-lifecycle --json number -q '.[].number'` → `137` only.

## Task Commits

Both tasks were gate/evidence-only (no source changes); this plan's docs commit (below) carries the evidence file and this SUMMARY, following the same no-separate-Task-1-commit pattern as 122-15.

1. **Task 1: Phase gates over 123-01..04** — no commit (gate-only; results recorded above)
2. **Task 2: Push, PR #137, CI, digest, evidence file** — committed together with this plan's metadata

**Plan metadata:** `docs(123-05): record phase gates, PR CI run and staging digest`

## Files Created/Modified

- `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (new) — gate summary, D-02 split, D-03 decision, build-under-test facts and DEV_PIN
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-05-SUMMARY.md` (this file)

## Decisions Made

- BASE for the scope/diff gates was computed exactly as the plan's `<interfaces>` prescribes (`git merge-base origin/main HEAD`), resolving to `a56a1f8` rather than `origin/main`'s own HEAD (`d82c4ae`, the PR #134 merge commit) — the phase-123 branch's ancestry diverges from the merge commit's own history, so the merge-base formula is the authoritative BASE, not a visual read of `origin/main`'s tip.
- No existing PR was found for this branch, so Task 2 created a brand-new single draft PR (#137) rather than reusing one, consistent with the plan's "create if none exists" instruction.

## Deviations from Plan

None - plan executed exactly as written. All 7 gates passed on the first run; no Rule 1-4 auto-fixes were needed. CI passed on the first run with no re-push.

## Issues Encountered

None blocking. The CI "Build Docker Image" job completed in 2m29s (cache reuse), and the overall CI run completed in well under the plan's ~30-minute expectation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- A digest-pinned image (`ghcr.io/thejuran/seedsyncarr@sha256:b7b894fa...`) containing all four Phase 123 LIFE-01/LIFE-02 fixes is built, green on every CI check, and recorded as DEV_PIN.
- 123-06 can now deploy this DEV_PIN to `seedsyncarr-test` and run the live `docker restart` check (idle and active-transfer cycles) to close D-01's live-provable half.
- 123-07 restores the sandbox to its original 1.7.6 pin afterward.
- Branch `gsd/phase-123-startup-and-shutdown-lifecycle` / PR #137 stays open and draft; no merge, no `gh pr ready`, no force push performed by this plan.

## Known Stubs

None.

## Threat Flags

None — all surface touched in this plan (GHCR digest lookups, PR creation) is covered by this plan's own `<threat_model>` (T-123-17..20), already addressed: token held in a shell variable and unset immediately after use, never echoed; only the digest header printed; only the phase branch pushed, no force/ready/merge; equivalence guard run both before and after the digest lookup.

## Self-Check: PASSED

- FOUND: `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md`
- FOUND: `.planning/phases/123-startup-and-shutdown-lifecycle/123-05-SUMMARY.md`
- FOUND commits: `647eef0`, `277257f`, `cbf6dcd`, `04eac94`, `1908ed8`, `29dd4c4`, `2c87bcf`, `c69559c`
- PR #137 confirmed OPEN and draft (`gh pr view 137`)

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-25*
