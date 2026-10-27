---
phase: 123-startup-and-shutdown-lifecycle
plan: 15
subsystem: ci-gate
tags: [gap-closure, gap-2, phase-gate, push, draft-pr, ci, ghcr-digest, one-pr-per-phase]

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "13"
    provides: "Lftp.exit() bounded process-group SIGKILL-and-reap fallback, exit kill (GAP-2 unit-proven half)"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "14"
    provides: "123-proc-sampler.sh and restart-cycle.sh wiring that fails a cycle on a non-reaped lftp/children (procs_<reason> rules)"
provides:
  - "Phase gates 1-9 plus new Gate 5b (suite-vs-baseline, whole-tree ruff, RED-before-GREEN incl. 123-13, 18-file scope, GAP-2-delta scope, untouched-wiring, criterion-3/4 regressions incl. the one owner-approved bounded wait, log hygiene) passing over 123-01..04, 123-08 and 123-13 together"
  - "123-13 pushed onto the existing draft PR #137; every PR CI check green on the new head SHA (run 410)"
  - "Staging image digest resolved by two independent methods and recorded as DEV_PIN_GAP2 for 123-16/123-17's live active-transfer restart re-check"
  - "123-LIFE-EVIDENCE.md 'Gap round 2 (GAP-2)' section: gap, diagnosis, fix, harness change, D-02 split, owner flag, gates, build under test"
affects: ["123-16 (live active-transfer restart re-check consumes DEV_PIN_GAP2)", "123-17 (sandbox restore afterward)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md

key-decisions:
  - "BASE for scope/diff gates recomputed as git merge-base origin/main HEAD, resolving to the same a56a1f8 as 123-05/123-10 (origin/main has not advanced past that commit)"
  - "PR #137 was reused (not reopened); gh pr list confirmed exactly one OPEN draft PR for the branch before pushing, per the orchestrator's one-PR-per-phase amendment"
  - "One early full-suite run showed 23 failed (2 extra transient failures in test_app_process.py, a known timing-sensitive thread/process test) before the normalized baseline comparison; re-running produced the exact documented 21 failed/3 errors with comm -23 empty both raw and name-normalized, so the transient run was treated as environment flakiness, not a regression, and not relied on for the gate verdict"
  - "This plan's own docs(123-15) commit is kept local, not pushed, so the PR head stays equal to NEW_HEAD_SHA_GAP2 (4074b0c) and therefore to the digest's build, exactly as 123-05/123-10 did for DEV_PIN/DEV_PIN_GAP"

patterns-established: []

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: ~30min (includes a ~12 min CI wait for run 410, 2026-10-26T21:07:18Z to 21:19:32Z)
completed: 2026-10-26
---

# Phase 123 Plan 15: Gap-Round-2 Phase Gate, PR Push, and Staging Digest Summary

**All nine gates plus the new Gate 5b pass over 123-01..04, 123-08 and 123-13 together; the branch is pushed to the existing draft PR #137 (reused, not reopened) with every CI check green on the new head (run 410); the staging image digest is resolved by two independent methods and recorded as `DEV_PIN_GAP2=ghcr.io/thejuran/seedsyncarr@sha256:7f354c149f...` for 123-16/123-17's live active-transfer restart re-check.**

## Performance

- **Duration:** ~30 min (includes a ~12 min CI wait for the Docker build/E2E/unit-test jobs, run 40401640233, 2026-10-26T21:07:18Z to 21:19:32Z)
- **Tasks:** 2 of 2 completed
- **Files modified:** 1 (`123-LIFE-EVIDENCE.md`, append-only) plus this SUMMARY

## Task 1: Phase gates over 123-01..04 + 123-08 + 123-13

**Precondition:** `git branch --show-current` -> `gsd/phase-123-startup-and-shutdown-lifecycle`; `git status --porcelain -- src/` -> empty. `git fetch origin`; BASE = `git merge-base origin/main HEAD` = `a56a1f8a12be232e5dfe8067a3db715df1f45255` (same as 123-05/123-10).

### Gate 1 — Full unit-suite failure set vs. 122-03 baseline

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q`

An initial run showed `23 failed, 1849 passed, 2 warnings, 3 errors` — 2 extra failures in `tests/unittests/test_common/test_app_process.py` (`test_cleanup_called_after_loop`, `test_run_once_called_once`) not present in the documented 24-line baseline. A second and third re-run both reproduced the documented result exactly:

```
21 failed, 1851 passed, 2 warnings, 3 errors, 77 subtests passed in 83.72s (0:01:23)
```

Both the raw sorted failure/error line list and a name-normalized list (stripping pytest's inconsistent `- <ErrorType>...` truncation suffix on long lines) were diffed against the exact 24-line 122-03-SUMMARY.md baseline via `comm -23`/`comm -13`: both directions empty on the normalized comparison. The `test_app_process.py` pair is a known timing-sensitive thread/process test not touched by this plan's `src/` diff (confirmed below in Gate 4/8/9); treated as one-off environment flakiness, not a regression, and the final clean re-run is what this plan's "done" claim rests on. **Gate 1: PASS.**

### Gate 2 — Whole-tree ruff

Command: `ruff check src/python/` (repo root) -> `All checks passed!` **Gate 2: PASS.**

### Gate 3 — RED before GREEN (incl. 123-13)

```
git log --format="%h %s" --reverse a56a1f8..HEAD | grep -E "^[a-f0-9]+ (test|fix)\(123-(0[1-4]|08|13)\)"
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
17387a6 test(123-08): SIGTERM-killed scanners get a time-bounded grace, not one cycle (GAP-1)
1ffc601 fix(123-08): bound the SIGTERM scanner grace by a monotonic-clock window, not one cycle (GAP-1)
01045b8 test(123-13): lftp exit reaps a child that survives pexpect's force close, bounded, idle path unchanged (GAP-2)
e03e3bd fix(123-13): reap an lftp child that outlives pexpect's force close with a bounded process-group SIGKILL; exit kill (GAP-2)
```
`test(123-NN)` precedes `fix(123-NN)` for NN = 01, 02, 03, 04, 08, 13. `git show --stat --format=` for each test commit (including `17387a6` and `01045b8`) lists only paths under `src/python/tests/`. **Gate 3: PASS.**

### Gate 4 — Scope diff (src/ files changed since BASE)

Command: `git diff --name-only a56a1f8..HEAD -- src/ | sort` -> 18 files, identical to the 123-10 16-file list plus `src/python/lftp/lftp.py` and `src/python/tests/unittests/test_lftp/test_lftp_exit.py`. `wc -l` prints 18. **Gate 4: PASS.**

### Gate 5 — No new sleeps (success criterion 4)

```
git diff a56a1f8..HEAD -- src/python ':(exclude)src/python/tests' | grep "^+" | grep -c -F "sleep("
```
-> `0`
```
grep -c -F "time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)" src/python/seedsyncarr.py
```
-> `2` (both DEFER-SHUTDOWN sleep call sites kept). **Gate 5: PASS.**

### Gate 5b — Exactly one new owner-flagged bounded wait (new)

```
git diff a56a1f8..HEAD -- src/python ':(exclude)src/python/tests' | grep "^+" | grep -v -F "#" | grep -F "time.sleep"
```
-> exactly one line:
```
+                 waiter: Callable[[float], None] = time.sleep,
```
The `waiter` default parameter in `Lftp.__init__` — the one owner-approved exception to success criterion 4 (123-13-PLAN.md `<owner_decision>`, "Allow it (Recommended)"). **Gate 5b: PASS.**

### Gate 6 — Success criterion 3 (exit(), auto-delete, lock ordering unchanged)

`Controller.exit()` text extracted at BASE and HEAD via `sed -n '/^    def exit(self):/,/^    def get_model_files/p'`, diffed: `(empty — byte-identical)`.
```
cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_auto_delete_rearm.py -p no:cacheprovider -q
```
-> `161 passed, 1 warning in 1.14s` (0 failed).
```
grep -c "__shutdown_event.set()" src/python/controller/controller.py
```
-> `3` at both BASE and HEAD. **Gate 6: PASS.**

### Gate 7 — Log hygiene (GAP-2 delta only)

```
git diff ff527dc9037f93eca2772c44fe4dace3838f90f5..HEAD -- src/python ':(exclude)src/python/tests' | grep "^+" | grep -E "logger\.(info|error|warning|exception|debug)"
```
Six new log calls, all in `Lftp.__reap_after_failed_close()`/`__poll_isalive()`: two `logger.warning` (status-unavailable, did-not-exit-on-force-close), two `logger.info` (reaped, with/without group kill), one `logger.warning` (process-group SIGKILL OSError by errno name). Each interpolates only `pid`, the `describe_lftp_process` diagnostic string (state letter + child count), elapsed seconds, or the errno name. `logger.error`/`logger.exception` count: `0`. "Could not terminate the child" / "Error stopping" substring count in any added log call: `0`. **Gate 7: PASS.**

### Gate 8 — GAP-2 delta scope (new)

```
git diff --name-only ff527dc9037f93eca2772c44fe4dace3838f90f5..HEAD -- src/ | sort
```
```
src/python/lftp/lftp.py
src/python/tests/unittests/test_lftp/test_lftp_exit.py
```
Exactly the two expected files. **Gate 8: PASS.**

### Gate 9 — Untouched wiring (new)

```
git diff ff527dc9037f93eca2772c44fe4dace3838f90f5..HEAD -- src/python/controller/controller.py src/python/controller/lftp_manager.py src/python/controller/scan_manager.py src/python/seedsyncarr.py src/python/common/job.py src/python/common/constants.py
```
`(empty)`. **Gate 9: PASS.**

### Quick suite

```
cd src/python && timeout 300 poetry run pytest tests/unittests/test_lftp/ tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_auto_delete.py -p no:cacheprovider -q
```
-> `397 passed, 1 warning in 1.45s`.

## Task 2: Push, PR body update, CI, digest, evidence file

- `gh pr list --head gsd/phase-123-startup-and-shutdown-lifecycle --state all --json number,state,isDraft` -> exactly PR **137**, OPEN, draft. Reused (no new PR opened), per the orchestrator's one-PR-per-phase amendment.
- Pushed (no force): `git push origin gsd/phase-123-startup-and-shutdown-lifecycle` -> fast-forward `ff527dc..4074b0c`.
- Updated the PR description: read the existing body, inserted a "Gap round 2" paragraph before the attribution line (plain-English summary of the bounded process-group SIGKILL-and-reap fallback and `exit kill`), added one GAP-2 test-plan checkbox, applied with `gh pr edit 137 --body-file <scratchpad>`. Body still ends with the Claude Code attribution line.
- **NEW_HEAD_SHA_GAP2:** `4074b0c681136f7ab0223eb90d87cc44948fe0c2`, confirmed equal to `gh pr view 137 --json headRefOid -q .headRefOid` immediately after the PR-body edit and again both immediately before and immediately after the digest lookup (no later push occurred).
- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/40401640233 (run_number **410**), headSha matching NEW_HEAD_SHA_GAP2, conclusion **success**. Watched via `gh run watch 40401640233 --exit-status` in the Bash tool's background mode (completed exit code 0, ~12 min).
- `gh pr checks 137` exit 0. All thirteen non-publish checks pass (Analyze x3, CodeQL, Angular/Python unit tests, both Lint jobs, Verify Python package, Verify/Release metadata verifier tests, Build Docker Image, End-to-end tests on Docker Image); five `Publish *` jobs `skipping` as expected on a `pull_request` event.
- `git merge-base --is-ancestor e03e3bd 4074b0c681136f7ab0223eb90d87cc44948fe0c2` -> exit 0 (fix(123-13) is an ancestor of NEW_HEAD_SHA_GAP2).
- **Digest resolution**, two independent methods, identical result:
  - `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:410` -> `Digest: sha256:7f354c149f2df586e7045ca47e971448b57dc1459a1a450f7a12aca885471a0c`
  - Anonymous GHCR bearer-token HEAD on `/v2/thejuran/seedsyncarr/manifests/410` -> `docker-content-digest: sha256:7f354c149f2df586e7045ca47e971448b57dc1459a1a450f7a12aca885471a0c`
  - **DEV_PIN_GAP2=ghcr.io/thejuran/seedsyncarr@sha256:7f354c149f2df586e7045ca47e971448b57dc1459a1a450f7a12aca885471a0c** — differs from DEV_PIN (`sha256:b7b894fa...`), DEV_PIN_GAP (`sha256:991e4e1f...`), the 1.7.6 production digest (`sha256:da6196e0...`) and the Phase 122 pin (`sha256:f8204207...`).
- Appended the "## Gap round 2 (GAP-2)" section to `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (append-only — `git diff | grep -c "^-[^-]"` -> `0`): the gap, the diagnosis (settled vs live-pending, pexpect/ptyprocess file:line refs, rejected hypotheses, remaining cause, the leak, the background-fork risk), the fix (123-13) with RED/GREEN SHAs and test names, the harness change (123-14), the D-02 split, the owner flag on success criterion 4, the gates 1-9 plus 5b table, and the build-under-test facts.
- No `gh pr ready`, no merge, no force push. `gh pr list --head gsd/phase-123-startup-and-shutdown-lifecycle --json number -q '.[].number'` -> `137` only.

## Task Commits

Both tasks were gate/evidence-only (no source changes); this plan's docs commit (below) carries the evidence-file append and this SUMMARY, following the same no-separate-Task-1-commit pattern as 123-05/123-10.

1. **Task 1: Phase gates over 123-01..04 + 123-08 + 123-13** — no commit (gate-only; results recorded above)
2. **Task 2: Push, PR #137 update, CI, digest, evidence file** — committed together with this plan's metadata

**Plan metadata:** `docs(123-15): record gap-round-2 gates, PR CI run and staging digest`

## Files Created/Modified

- `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (modified, append-only) — "Gap round 2 (GAP-2)" section: gap, diagnosis, fix, harness change, D-02 split, owner flag, gates 1-9 plus 5b, build-under-test facts and DEV_PIN_GAP2
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-15-SUMMARY.md` (this file)

## Decisions Made

- BASE recomputed exactly as the plan's `<interfaces>` prescribes (`git merge-base origin/main HEAD`); it resolved to the same `a56a1f8` as 123-05/123-10, confirming `origin/main` has not moved past that point.
- PR #137 was reused rather than reopened or recreated: `gh pr list` confirmed exactly one OPEN draft PR for the branch before any push, satisfying the plan's precondition.
- The one transient Gate 1 run (2 extra `test_app_process.py` failures) was not treated as a regression: it was outside this plan's `src/` diff (confirmed by Gates 4/8/9), and a clean re-run reproduced the documented baseline exactly on both the raw and name-normalized `comm` comparison.
- The docs(123-15) commit is kept local (not pushed), matching 123-05/123-10's pattern, so the PR head SHA used for CI and the digest lookup (`4074b0c`) stays the exact build pinned as DEV_PIN_GAP2.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, test-infrastructure] Treated a one-off flaky Gate 1 run as environment noise, not a regression, after a clean re-run matched the documented baseline exactly**
- **Found during:** Task 1, Gate 1
- **Issue:** The first full-suite run showed `23 failed` (2 extra failures in `tests/unittests/test_common/test_app_process.py::TestAppProcess::test_cleanup_called_after_loop` and `TestAppOneShotProcess::test_run_once_called_once`) instead of the documented 21. Neither test file is touched by this plan's `src/` diff (confirmed by Gates 4/8/9), and both are known timing-sensitive thread/process tests.
- **Fix:** Re-ran the full suite twice more; both re-runs reproduced the exact documented `21 failed, 1851 passed, 2 warnings, 3 errors` result. Built a name-normalized comparison (stripping pytest's inconsistent long-line truncation suffix) against the 24-line baseline and confirmed empty `comm -23`/`comm -13` in both directions.
- **Files modified:** None (no project files changed; gate verification only).
- **Verification:** Final clean run's failure/error set matches the documented 122-03-SUMMARY.md baseline exactly, normalized comparison empty both ways.
- **Committed in:** n/a (no file changes to commit; recorded in this SUMMARY and the Gates table above)

---

**Total deviations:** 1 auto-handled (test-infrastructure flakiness, not a code fix)
**Impact on plan:** No production or test code was changed by this plan; the flaky run was investigated and shown to be environment noise rather than a regression caused by this plan's (zero) changes to source.

## Issues Encountered

None blocking. CI run 410 took ~12 minutes (Build Docker Image 2m52s, Python unit tests 5m9s, E2E tests 4m0s, run concurrently), within the expected range; polled with short bounded `gh run view` calls plus one `gh run watch --exit-status` background task rather than a single blocking call, per the executor's watchdog guidance.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- A digest-pinned image (`ghcr.io/thejuran/seedsyncarr@sha256:7f354c149f...`) containing all four Phase 123 LIFE-01/LIFE-02 fixes, the GAP-1 clock-bounded SIGTERM grace fix, and the GAP-2 bounded lftp process-group reap fix is built, green on every CI check, and recorded as DEV_PIN_GAP2.
- 123-16 can now deploy this DEV_PIN_GAP2 to `seedsyncarr-test` and re-run the live active-transfer `docker restart` cycles, using 123-14's new process sampler to directly confirm lftp and its children are reaped before the old container stops (closing GAP-2's live-provable half and settling the D-state hypothesis from 123-13's diagnosis).
- 123-17 restores the sandbox to its prior pin afterward.
- Branch `gsd/phase-123-startup-and-shutdown-lifecycle` / PR #137 stays open and draft; no merge, no `gh pr ready`, no force push performed by this plan.

## Known Stubs

None.

## Threat Flags

None — all surface touched in this plan (GHCR digest lookups, PR push/body edit) is covered by this plan's own `<threat_model>` (T-123-60..64), already addressed: digest read only after CI for NEW_HEAD_SHA_GAP2 went green and after a no-later-push equivalence check, by two independent methods that matched; bearer token held in a shell variable, never echoed; only the digest header printed; only a plain push to the existing draft PR, no force/ready/merge; Gates 8-9 proved the GAP-2 delta is confined to the two lftp files with no diff in the untouched wiring files; Gate 5b proved exactly one new bounded wait exists and it matches the owner-approved exception.

## Self-Check: PASSED

- FOUND: `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md`
- FOUND: `.planning/phases/123-startup-and-shutdown-lifecycle/123-15-SUMMARY.md`
- FOUND commits referenced: `647eef0`, `277257f`, `cbf6dcd`, `04eac94`, `1908ed8`, `29dd4c4`, `2c87bcf`, `c69559c`, `17387a6`, `1ffc601`, `01045b8`, `e03e3bd`
- PR #137 confirmed OPEN and draft, head `4074b0c681136f7ab0223eb90d87cc44948fe0c2` (`gh pr view 137`)

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*
