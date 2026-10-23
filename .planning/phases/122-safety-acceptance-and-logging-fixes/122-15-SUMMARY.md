---
phase: 122-safety-acceptance-and-logging-fixes
plan: 15
subsystem: ci-gate
tags: [gap-closure, phase-gate, push, ci, ghcr-digest, one-pr-per-phase]
gap_closure: true

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes
    plan: 13
    provides: "WR-02/WR-03 D-06(c) grace-window narrowing + credit-reason fix, RED-GREEN, local gates green"
  - phase: 122-safety-acceptance-and-logging-fixes
    plan: 14
    provides: "CR-01 API-key-leak fix and WR-01 status rate-limit logger fix, RED-GREEN-GREEN, local gates green"
provides:
  - "Phase gates (suite-vs-baseline, whole-tree ruff, RED-before-GREEN, scope, D-14 secret-leak grep) passing over both 122-13 and 122-14 together"
  - "122-13/122-14 pushed to draft PR #134; every PR CI check green on the new head SHA"
  - "New staging image digest resolved by two independent methods and recorded as the new DEV_PIN, superseding sha256:e3941f97..."
affects: ["122-16 (live LOG-01/D-06(c) rerun on this new DEV_PIN)", "122-17 (closes SAFE-01/LOG-01 for this gap-closure cycle)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  modified:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md

key-decisions: []

patterns-established: []

requirements-completed: []

# Metrics
duration: ~14min
completed: 2026-10-23
---

# Phase 122 Plan 15: Gate, Push to PR #134, and Re-pin to New Staging Digest Summary

**Gated 122-13 and 122-14 together (suite-vs-baseline, whole-tree ruff, RED-before-GREEN, scope, D-14 secret-leak grep), pushed to draft PR #134 (CI run 404 green on every check), and resolved the new staging image's digest (`sha256:f8204207...`) by two independent methods, recording it as the new DEV_PIN for 122-16's sandbox rerun.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-10-23T23:26:33Z
- **Completed:** 2026-10-23T23:40:49Z
- **Tasks:** 2 of 2 completed
- **Files modified:** 1 (`122-SAFE01-EVIDENCE.md`, one appended section)

## Gates

**Precondition:** `git branch --show-current` → `gsd/phase-122-safety-acceptance-and-logging-fixes`; `git status --porcelain` → empty. Confirmed before any gate ran.

### Gate 1 — Full unit-suite failure set is a subset of the 122-03 baseline

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q`

Result:
```
21 failed, 1798 passed, 2 warnings, 3 errors, 77 subtests passed in 81.10s (0:01:21)
```

`comm -23 current baseline` (current failure/error lines minus the exact 24-line 122-03-SUMMARY.md baseline), sorted, stripped of trailing " - reason" text:

```
(empty)
```

Empty output confirms the current 24-line failure/error set (21 FAILED + 3 ERROR) is identical to the 122-03 baseline set — no new failure introduced by 122-13 or 122-14. All 24 lines are the documented environment-bound failures (`test_extract_process.py` x6, `test_scanner_process.py` x3 FAILED + 3 ERROR, `test_sshcp.py` x10, `test_scanner.py::test_scan_file_with_latin_chars` x1). **Gate 1: PASS.**

### Gate 2 — Whole-tree ruff

Command: `ruff check src/python/` (from repo root; the `poetry` wrapper has no `pyproject.toml` at repo root, so the standalone `ruff` on PATH was used, matching CI's pinned 0.15.22 invocation)

Result:
```
All checks passed!
```

**Gate 2: PASS.**

### Gate 3 — RED-before-GREEN commit order

Command: `git log --format="%h %s" --reverse ebecf8c..HEAD`

```
da867a5 docs(122): create gap-closure plans 13-17 for code-review findings
56ffced test(122-14): reproduce API key leak via InvalidHeader and detached status rate-limit logger (CR-01, WR-01)
b4081ac fix(122-14): never log Arr API key from Test Connection; validate key before request (CR-01)
5400cc0 fix(122-14): route status rate-limit warning to app logger; make rate_limit logger required (WR-01)
0172558 docs(122-14): complete API-key leak and status rate-limit logger gap closure plan
166c3e5 test(122-13): narrow post-transfer pending-notice window and fix credit wording (WR-02, WR-03)
43c8c57 fix(122-13): bound post-transfer notice window to 120 s, discard on stop/delete-local, accurate credit reason (WR-02, WR-03)
848a41d test(122-13): seed __last_transferring_at in the hand-rolled webhook-import test double
a56a1f8 docs(122-13): complete WR-02/WR-03 post-transfer grace-window and credit-reason gap-closure plan
```

`test(122-14)` (`56ffced`) precedes both `fix(122-14)` commits (`b4081ac`, `5400cc0`). `test(122-13)` (`166c3e5`) precedes `fix(122-13)` (`43c8c57`).

`git show --stat --format= 166c3e5` lists only `test_import_credit.py` (test file only). `git show --stat --format= 56ffced` lists only `test_config_handler.py`, `test_controller_handler.py`, `test_status_handler.py`, `test_rate_limit.py`, `test_web_app_builder_logging.py` (all test files only). No non-test src file in either test commit.

Note: `848a41d` (`test(122-13): seed __last_transferring_at in the hand-rolled webhook-import test double`) is a supplementary Rule-3 test-double fix that lands chronologically after `fix(122-13)`, documented in 122-13-SUMMARY.md as a necessary fix to an existing test double broken by the GREEN change — not a violation of RED-before-GREEN for the behavioral commits. **Gate 3: PASS.**

### Gate 4 — Scope diff (src/ files changed since BASE)

BASE = parent of the earlier test commit (`56ffced`, 122-14's RED commit) = `da867a5`.

Command: `git diff --name-only da867a5..HEAD -- src/`, sorted:

```
src/python/controller/controller.py
src/python/tests/unittests/test_controller/test_controller.py
src/python/tests/unittests/test_controller/test_import_credit.py
src/python/tests/unittests/test_web/test_handler/test_config_handler.py
src/python/tests/unittests/test_web/test_handler/test_controller_handler.py
src/python/tests/unittests/test_web/test_handler/test_status_handler.py
src/python/tests/unittests/test_web/test_rate_limit.py
src/python/tests/unittests/test_web/test_web_app_builder_logging.py
src/python/web/handler/config.py
src/python/web/handler/status.py
src/python/web/rate_limit.py
src/python/web/web_app_builder.py
```

12 files: exactly the plan's 11-file `<interfaces>` list plus `src/python/tests/unittests/test_controller/test_controller.py` — the plan's own note calls this file "an expected in-scope test file in the changed-file scope check" (122-13's Rule-3 fix, commit `848a41d`). No extra or missing file beyond that documented exception. **Gate 4: PASS.**

### Gate 5 — No new secret-leak logging site

Command: `grep -rn "logger.exception\|exc_info" src/python/web/handler src/python/web/rate_limit.py src/python/controller/arr_queue.py | wc -l`

Result: `0`. **Gate 5: PASS.**

### Gate summary

| Gate | Result |
|---|---|
| 1 — suite failure subset of baseline | PASS (21 failed + 3 errors, `comm -23` empty) |
| 2 — whole-tree ruff | PASS (`All checks passed!`) |
| 3 — RED-before-GREEN | PASS (`test(122-13)` < `fix(122-13)`; `test(122-14)` < both `fix(122-14)` commits) |
| 4 — scope (src/ diff since BASE) | PASS (12 files = 11 expected + 1 documented test-double exception) |
| 5 — no `logger.exception`/`exc_info` in scope | PASS (0 matches) |

## Task 2: Push to PR #134, CI, Digest Resolution

- Pushed `gsd/phase-122-safety-acceptance-and-logging-fixes` (no force): `7fac2ba..a56a1f8`. NEW_HEAD_SHA `a56a1f8a12be232e5dfe8067a3db715df1f45255`, confirmed equal to `gh pr view 134 --json headRefOid -q .headRefOid` both immediately after the push and again immediately before the digest lookup — no later push occurred.
- CI run https://github.com/thejuran/seedsyncarr/actions/runs/40039769263 (run_number 404), conclusion **success**, headSha matching NEW_HEAD_SHA. `gh pr checks 134` exit 0 — every required check passed (Analyze x3, Angular/Python unit tests, Build Docker Image, CodeQL, E2E on Docker Image, both Lint jobs, package/release-metadata verification); all five `Publish *` jobs correctly `skipping` (pull_request event).
- Digest resolved by two independent methods, identical result: `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:404` → `sha256:f8204207ef199f183f6230b74bd8967397732a5919570b09dcec7dc3f2341689`; anonymous GHCR bearer-token HEAD lookup on `/v2/.../manifests/404` → same digest. Differs from the superseded `sha256:e3941f97...` pin.
- Appended "Re-pin after 122-13/122-14 fixes (build under test for Plans 16-17)" to `122-SAFE01-EVIDENCE.md` with the why/equivalence-guard rationale, PR URL + NEW_HEAD_SHA, both plans' commit SHAs/subjects, the gate summary table, the CI run URL/number/per-check table, both digest-lookup outputs, the new `DEV_PIN=...` line, and the superseded-pin record.
- No new PR was opened (`gh pr list --head gsd/phase-122-safety-acceptance-and-logging-fixes --json number -q '.[].number'` → `134` only); no merge; no `gh pr ready`; no force push.

## Task Commits

1. **Task 1: Phase gates over 122-13 and 122-14** — no commit (gate-only; results recorded above under "Gates", same pattern as 122-03's Task 1)
2. **Task 2: Push to PR #134, wait for CI green, resolve and record new DEV_PIN** — committed together with this plan's metadata (no separate source change beyond the evidence file)

**Plan metadata:** this commit (`docs(122-15): record gates, PR #134 CI run and new staging digest after CR-01/WR-01..03 fixes`)

## Files Created/Modified

- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` — appended "Re-pin after 122-13/122-14 fixes (build under test for Plans 16-17)" section (why, build-under-test facts, gate summary, CI check list, two-method digest resolution, new/superseded DEV_PIN)
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-15-SUMMARY.md` — this file

## Decisions Made

None beyond what the plan specified — gate thresholds, push target, and digest-lookup methods were all fixed by the plan and 122-11's precedent; no judgment calls required.

## Deviations from Plan

None — plan executed exactly as written. Gate 4's scope diff produced 12 files (11 plan-listed + `test_controller.py`), which the plan's own `<interfaces>` note anticipates and names as an expected in-scope exception, so this is not treated as a deviation.

## Issues Encountered

None. The CI "Build Docker Image" job completed in 2m22s this run (likely layer-cache reuse), much faster than the ~27 min seen in Plans 03/11 — no action needed, the run still conclusively passed all checks including the Docker-image E2E tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- A digest-pinned image (`ghcr.io/thejuran/seedsyncarr@sha256:f8204207...`) containing the CR-01/WR-01/WR-02/WR-03 fixes is built, green on every CI check, and recorded as the new DEV_PIN.
- 122-16 should deploy this new DEV_PIN to `seedsyncarr-test` (production untouched, same trap-protected procedure as Plans 04/11) and rerun LOG-01 and the D-06(c) scenario live, since the equivalence guard means the Plan 06/07/11/12 evidence on the previous pin no longer covers this shipping code.
- 122-17 closes this second gap-closure cycle.
- Branch `gsd/phase-122-safety-acceptance-and-logging-fixes` / PR #134 remains open and draft; no merge, no new PR, no `gh pr ready` call made by this plan.

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-23*
