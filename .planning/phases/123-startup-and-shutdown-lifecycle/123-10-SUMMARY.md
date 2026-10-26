---
phase: 123-startup-and-shutdown-lifecycle
plan: 10
subsystem: ci-gate
tags: [gap-closure, phase-gate, push, draft-pr, ci, ghcr-digest, one-pr-per-phase]

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "08"
    provides: "Clock-bounded 10s SIGTERM scanner grace in ScanManager (GAP-1 unit-proven half)"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "09"
    provides: "Resumable restart-cycle harness with STARTED/INCOMPLETE markers and Exited-successfully demoted to recorded-only"
provides:
  - "Phase gates 1-9 (suite-vs-baseline, whole-tree ruff, RED-before-GREEN incl. 123-08, 16-file scope, gap-delta scope, untouched-wiring, criterion-3/4 regressions, log hygiene) passing over 123-01..04 + 123-08 together"
  - "123-08/123-09 pushed onto the existing draft PR #137; every PR CI check green on the new head SHA"
  - "Staging image digest resolved by two independent methods and recorded as DEV_PIN_GAP for 123-11/123-12's live restart re-check"
  - "123-LIFE-EVIDENCE.md 'Gap round (GAP-1)' section: gap, fix, rejected alternatives, RED/GREEN SHAs, D-02 split, harness-change justification, gates, build under test"
affects: ["123-11 (live restart re-check consumes DEV_PIN_GAP)", "123-12 (sandbox restore afterward)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md

key-decisions:
  - "BASE for scope/diff gates recomputed as git merge-base origin/main HEAD, resolving to the same a56a1f8 as 123-05 (origin/main has not advanced past the commit that produced that merge-base since 123-05 ran)"
  - "PR #137 was reused (not reopened); gh pr list confirmed exactly one OPEN draft PR for the branch before pushing, per the orchestrator's one-PR-per-phase amendment"
  - "The docs(123-10) commit carrying this SUMMARY and the LIFE-EVIDENCE.md update is kept local, not pushed, so the PR head stays equal to NEW_HEAD_SHA_GAP (ff527dc) and therefore to the digest's build, exactly as 123-05 did for DEV_PIN"

patterns-established: []

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: ~35min
completed: 2026-10-26
---

# Phase 123 Plan 10: Gap-Round Phase Gate, PR Push, and Staging Digest Summary

**All nine gates (the original seven plus two gap-delta scope gates) pass over 123-01..04 and 123-08 together; the branch is pushed to the existing draft PR #137 (reused, not reopened) with every CI check green on the new head; the staging image digest is resolved by two independent methods and recorded as `DEV_PIN_GAP=ghcr.io/thejuran/seedsyncarr@sha256:991e4e1f...` for 123-11/123-12's live restart re-check.**

## Performance

- **Duration:** ~35 min (includes a ~14 min CI wait for the Docker build/E2E jobs, run 40379266127 2026-10-26T18:36:47Z to 18:50:57Z)
- **Tasks:** 2 of 2 completed
- **Files modified:** 1 (`123-LIFE-EVIDENCE.md`, append-only) plus this SUMMARY

## Task 1: Phase gates over 123-01..04 + 123-08

**Precondition:** `git branch --show-current` -> `gsd/phase-123-startup-and-shutdown-lifecycle`; `git status --porcelain -- src/` -> empty. `git fetch origin`; BASE = `git merge-base origin/main HEAD` = `a56a1f8a12be232e5dfe8067a3db715df1f45255` (same as 123-05).

### Gate 1 — Full unit-suite failure set vs. 122-03 baseline

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q`

Result:
```
21 failed, 1840 passed, 2 warnings, 3 errors, 77 subtests passed in 83.04s (0:01:23)
```

`comm -23 current baseline` (sorted current FAILED/ERROR lines minus the exact 24-line 122-03-SUMMARY.md baseline): `(empty)`. All 24 lines matched the documented environmental baseline exactly. **Gate 1: PASS.**

### Gate 2 — Whole-tree ruff

Command: `ruff check src/python/` (repo root) -> `All checks passed!` **Gate 2: PASS.**

### Gate 3 — RED before GREEN (incl. 123-08)

```
git log --format="%h %s" --reverse a56a1f8..HEAD | grep -E "^[a-f0-9]+ (test|fix)\(123-0[1-4,8]\)"
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
```
`test(123-NN)` precedes `fix(123-NN)` for NN = 01, 02, 03, 04, 08. `git show --stat --format=` for each test commit (including `17387a6`) lists only paths under `src/python/tests/` (confirmed directly: `17387a6` touches only `test_scan_manager.py`). **Gate 3: PASS.**

### Gate 4 — Scope diff (src/ files changed since BASE)

Command: `git diff --name-only a56a1f8..HEAD -- src/ | sort` -> 16 files, identical to the 123-05 16-file list (the gap fix touches two files already in that set: `scan_manager.py` and `test_scan_manager.py`). `wc -l` prints 16; direct diff against the expected sorted list is empty. **Gate 4: PASS.**

### Gate 5 — No new sleeps (success criterion 4)

```
git diff a56a1f8..HEAD -- src/python ':(exclude)src/python/tests' | grep "^+" | grep -c "sleep("
```
-> `0`
```
grep -c "time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)" src/python/seedsyncarr.py
```
-> `2` (both DEFER-SHUTDOWN sleep call sites kept). **Gate 5: PASS.**

### Gate 6 — Success criterion 3 (exit(), auto-delete, lock ordering unchanged)

`Controller.exit()` text extracted at BASE and HEAD via `sed -n '/^    def exit(self):/,/^    def get_model_files/p'`, diffed: `(empty — byte-identical)`.
```
cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_auto_delete_rearm.py -p no:cacheprovider -q
```
-> `161 passed, 1 warning in 0.86s` (0 failed).
```
grep -c "__shutdown_event.set()" src/python/controller/controller.py
```
-> `3` at both BASE and HEAD. **Gate 6: PASS.**

### Gate 7 — Log hygiene (gap delta only)

```
git diff 0cae08127d9403063960ace2e109c52542245af7..HEAD -- src/python ':(exclude)src/python/tests' | grep "^+" | grep -E "logger\.(info|error|warning|exception|debug)"
```
The only new log call in the gap delta is one `logger.debug(...)` in `ScanManager._check_process_health()`'s SIGTERM-grace branch, interpolating only scanner process names and the `_SIGTERM_SHUTDOWN_GRACE_IN_SECS` constant. No config values, passwords, tokens or keys. **Gate 7: PASS.**

### Gate 8 — Gap delta scope (new)

```
git diff --name-only 0cae08127d9403063960ace2e109c52542245af7..HEAD -- src/ | sort
```
```
src/python/controller/scan_manager.py
src/python/tests/unittests/test_controller/test_scan_manager.py
```
Exactly the two expected files. **Gate 8: PASS.**

### Gate 9 — Untouched wiring (new)

```
git diff 0cae08127d9403063960ace2e109c52542245af7..HEAD -- src/python/controller/controller.py src/python/seedsyncarr.py src/python/common/job.py src/python/common/constants.py
```
`(empty)`. **Gate 9: PASS.**

### Quick suite (123-VALIDATION.md)

```
cd src/python && timeout 300 poetry run pytest tests/unittests/test_common/test_job.py tests/unittests/test_controller/test_scan_manager.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_controller_job.py tests/unittests/test_controller/test_file_operation_manager.py tests/unittests/test_controller/test_auto_delete.py -p no:cacheprovider -q
```
-> `250 passed, 1 warning in 2.05s`.

## Task 2: Push, PR body update, CI, digest, evidence file

- `gh pr list --head gsd/phase-123-startup-and-shutdown-lifecycle --state all --json number,state,isDraft` -> exactly PR **137**, OPEN, draft. Reused (no new PR opened), per the orchestrator's one-PR-per-phase amendment.
- Pushed (no force): `git push origin gsd/phase-123-startup-and-shutdown-lifecycle` -> fast-forward `0cae081..ff527dc`.
- Updated the PR description: read the existing body, inserted a "Gap round" paragraph before the attribution line (plain-English summary of the 10s clock-bounded grace and the harness's Exited-successfully demotion), added one gap-round test-plan checkbox, applied with `gh pr edit 137 --body-file <scratchpad>`. Body still ends with the Claude Code attribution line.
- **NEW_HEAD_SHA_GAP:** `ff527dc9037f93eca2772c44fe4dace3838f90f5`, confirmed equal to `gh pr view 137 --json headRefOid -q .headRefOid` immediately after the PR-body edit and again both immediately before and immediately after the digest lookup (no later push occurred).
- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/40379266127 (run_number **409**), headSha matching NEW_HEAD_SHA_GAP, conclusion **success**. Watched via `gh run watch 40379266127 --exit-status` in the Bash tool's background mode (completed exit code 0, ~14 min).
- `gh pr checks 137` exit 0. All thirteen non-publish checks pass (Analyze x3, CodeQL, Angular/Python unit tests, both Lint jobs, Verify Python package, Verify/Release metadata verifier tests, Build Docker Image, End-to-end tests on Docker Image); five `Publish *` jobs `skipping` as expected on a `pull_request` event.
- `git merge-base --is-ancestor 1ffc601 ff527dc9037f93eca2772c44fe4dace3838f90f5` -> exit 0 (fix(123-08) is an ancestor of NEW_HEAD_SHA_GAP).
- **Digest resolution**, two independent methods, identical result:
  - `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:409` -> `Digest: sha256:991e4e1f28b90c6020c911a65c4814314aa5860682df8aa9e389e365d7872da6`
  - Anonymous GHCR bearer-token HEAD on `/v2/thejuran/seedsyncarr/manifests/409` -> `docker-content-digest: sha256:991e4e1f28b90c6020c911a65c4814314aa5860682df8aa9e389e365d7872da6`
  - **DEV_PIN_GAP=ghcr.io/thejuran/seedsyncarr@sha256:991e4e1f28b90c6020c911a65c4814314aa5860682df8aa9e389e365d7872da6** — differs from the 123-05 DEV_PIN (`sha256:b7b894fa...`), the 1.7.6 production digest (`sha256:da6196e0...`) and the Phase 122 pin (`sha256:f8204207...`).
- Appended the "## Gap round (GAP-1)" section to `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (append-only — `git diff | grep -c "^-[^-]"` -> `0`): the gap, the fix (123-08) with rejected alternatives and RED/GREEN SHAs/test names, the D-02 split for the gap round, the harness-change (123-09) justification, the gates 1-9 table, and the build-under-test facts.
- No `gh pr ready`, no merge, no force push. `gh pr list --head gsd/phase-123-startup-and-shutdown-lifecycle --json number -q '.[].number'` -> `137` only.

## Task Commits

Both tasks were gate/evidence-only (no source changes); this plan's docs commit (below) carries the evidence-file append and this SUMMARY, following the same no-separate-Task-1-commit pattern as 123-05.

1. **Task 1: Phase gates over 123-01..04 + 123-08** — no commit (gate-only; results recorded above)
2. **Task 2: Push, PR #137 update, CI, digest, evidence file** — committed together with this plan's metadata

**Plan metadata:** `docs(123-10): record gap-round gates, PR CI run and staging digest`

## Files Created/Modified

- `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (modified, append-only) — "Gap round (GAP-1)" section: gap, fix, rejected alternatives, D-02 split, harness-change justification, gates 1-9, build-under-test facts and DEV_PIN_GAP
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-10-SUMMARY.md` (this file)

## Decisions Made

- BASE recomputed exactly as the plan's `<interfaces>` prescribes (`git merge-base origin/main HEAD`); it resolved to the same `a56a1f8` as 123-05, confirming `origin/main` has not moved past that point.
- PR #137 was reused rather than reopened or recreated: `gh pr list` confirmed exactly one OPEN draft PR for the branch before any push, satisfying the plan's precondition.
- The docs(123-10) commit is kept local (not pushed), matching 123-05's pattern, so the PR head SHA used for CI and the digest lookup (`ff527dc`) stays the exact build pinned as DEV_PIN_GAP.

## Deviations from Plan

None - plan executed exactly as written. All 9 gates passed on the first run; no Rule 1-4 auto-fixes were needed. CI passed on the first run with no re-push.

## Issues Encountered

None blocking. CI run 409 took ~14 minutes (Build Docker Image 5m3s, E2E tests 3m46s), within the plan's expected range; polled with short bounded `gh run view`/`gh pr checks` calls plus one `gh run watch --exit-status` background task rather than a single blocking call, per the executor's watchdog guidance.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- A digest-pinned image (`ghcr.io/thejuran/seedsyncarr@sha256:991e4e1f...`) containing all four Phase 123 LIFE-01/LIFE-02 fixes plus the GAP-1 clock-bounded SIGTERM grace fix is built, green on every CI check, and recorded as DEV_PIN_GAP.
- 123-11 can now deploy this DEV_PIN_GAP to `seedsyncarr-test` and re-run the live `docker restart` cycles (idle and active-transfer) to confirm the false "Scanner process(es) died unexpectedly" ERROR no longer fires, closing GAP-1's live-provable half.
- 123-12 restores the sandbox to its original 1.7.6 pin afterward.
- Branch `gsd/phase-123-startup-and-shutdown-lifecycle` / PR #137 stays open and draft; no merge, no `gh pr ready`, no force push performed by this plan.
- The outstanding session-teardown item from 123-06 (SSA123 seedbox staging not yet verified clean) remains open for 123-11/123-12, unaffected by this plan.

## Known Stubs

None.

## Threat Flags

None — all surface touched in this plan (GHCR digest lookups, PR push/body edit) is covered by this plan's own `<threat_model>` (T-123-37..40), already addressed: digest read only after CI for NEW_HEAD_SHA_GAP went green and after a no-later-push equivalence check, by two independent methods that matched; bearer token held in a shell variable, unset immediately after use, never echoed; only the digest header printed; only a plain push to the existing draft PR, no force/ready/merge; Gates 8-9 proved the gap delta is confined to the two `scan_manager` files with no diff in the untouched wiring files.

## Self-Check: PASSED

- FOUND: `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md`
- FOUND: `.planning/phases/123-startup-and-shutdown-lifecycle/123-10-SUMMARY.md`
- FOUND commits referenced: `647eef0`, `277257f`, `cbf6dcd`, `04eac94`, `1908ed8`, `29dd4c4`, `2c87bcf`, `c69559c`, `17387a6`, `1ffc601`
- PR #137 confirmed OPEN and draft, head `ff527dc9037f93eca2772c44fe4dace3838f90f5` (`gh pr view 137`)

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*
