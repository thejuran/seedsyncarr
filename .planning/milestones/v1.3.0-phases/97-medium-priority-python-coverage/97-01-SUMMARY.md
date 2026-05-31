---
phase: 97-medium-priority-python-coverage
plan: 01
subsystem: testing-infrastructure
tags: [coverage, baseline, ratchet, ci, python, angular]
requires: []
provides:
  - ".planning/milestones/v1.3.0-COVERAGE-BASELINE.md (Phase 100 ratchet anchor, RATCHET-02)"
affects:
  - "Phase 100 Plan 100-03 (CI threshold ratchet — reads this baseline's Before numbers)"
tech-stack:
  added: []
  patterns:
    - "Coverage measured via existing make targets only (host make coverage-python --cov; Karma Istanbul) — no config mutation"
    - "Throwaway reporter override in /tmp to extract numeric summary without touching committed karma.conf.js"
key-files:
  created:
    - ".planning/milestones/v1.3.0-COVERAGE-BASELINE.md"
  modified: []
decisions:
  - "Python baseline recorded PROVISIONAL (host-only) because the only --cov target is host make coverage-python; the containerized run-tests-python CMD has no --cov"
  - "No Karma global thresholds transcribed — karma.conf.js has none (only type/dir); recording their absence as a fact, creation deferred to Phase 100"
metrics:
  duration: ~12m
  completed: 2026-05-29
requirements: [RATCHET-01]
---

# Phase 97 Plan 01: v1.3.0 Coverage Baseline Summary

Captured and committed the milestone v1.3.0 coverage baseline against `main` HEAD
(`0f4c79e`) before any Phase-97 test lands — Python line coverage **85.19%** (host/provisional,
via `make coverage-python --cov`) and Angular **83.34% stmts / 69.01% branches / 79.73% funcs /
84.21% lines** (Karma/Istanbul) — recorded with the configured pytest `fail_under` floor (84),
the fact that no Karma `check.global` thresholds exist yet, and a Phase-100 obligation to
re-measure a container-inclusive Python "before" prior to ratcheting. RATCHET-01 closed.

## What Was Built

- **`.planning/milestones/v1.3.0-COVERAGE-BASELINE.md`** — the committed ratchet anchor for
  Phase 100 (RATCHET-02). Contains: provenance (git SHA `0f4c79e`, date, exact commands per
  language), a Python section with the raw `term-missing` TOTAL row and the 85.19% total plus
  a PROVISIONAL/host-only caveat, the verbatim `fail_under = 84` floor, an Angular section
  with the four Istanbul percentages and the explicit "no `check.global` thresholds configured"
  fact, a Phase-100 follow-up requirement, and the monotonic-ratchet note.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Measure current coverage on main HEAD | (measurement-only — no source files modified; numbers feed Task 2) | none |
| 2 | Write and commit the baseline file | `2177e44` | `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md` |

## Measured Numbers (verbatim)

**Python** (`make coverage-python` → `poetry run pytest --cov --cov-report=term-missing`):
```
Name                                    Stmts   Miss Branch BrPart  Cover   Missing
TOTAL                                    5428    722   1406    122    85%
Required test coverage of 84.0% reached. Total coverage: 85.19%
```
PROVISIONAL — host run; integration `test_lftp` suite errored/skipped (no lftp binary / sshd
on host). 1170 passed, 25 failed, 62 skipped, 40 errors. Coverage TOTAL is still emitted by
pytest-cov despite test failures; the failing/erroring host-env tests do not invalidate the
line/branch tallies of the code that executed. Container-inclusive total expected higher.

**Angular** (`ng test --code-coverage --browsers=ChromeHeadless`, all 599 tests passed):
```
Statements   : 83.34% ( 1682/2018 )
Branches     : 69.01% ( 461/668 )
Functions    : 79.73% ( 421/528 )
Lines        : 84.21% ( 1622/1926 )
```

**Configured floors:** pytest `fail_under = 84` (verbatim). Karma: NO `check.global` block exists.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provisioned locked project dependencies to run the coverage commands**
- **Found during:** Task 1
- **Issue:** The host environment had no installed venv for either project — the freshly
  created poetry venv lacked `pytest-cov` (so `pytest --cov` errored with
  "unrecognized arguments: --cov"), and `src/angular/node_modules` was absent (Karma could
  not run).
- **Fix:** Ran `poetry install` (Python) and `npm ci` (Angular) — both install **already
  committed, lockfile-pinned** dependencies (`poetry.lock` / `package-lock.json`).
  `pytest-cov` is a declared dev dependency (`pytest-cov = "^7.1.0"`). This is environment
  provisioning of existing locked deps, NOT a `poetry add`/`npm install <newpkg>` of an
  unverified package, so the Rule-3 package-install exclusion (slopsquat guard) does not apply.
- **Files modified:** None tracked (lockfiles unchanged; only the local venv / node_modules,
  which are gitignored).
- **Commit:** n/a (no repo changes)

**2. [Rule 3 - Blocking] Karma had no text/json summary reporter to read numbers from**
- **Found during:** Task 1
- **Issue:** The committed `karma.conf.js` `coverageReporter` emits only `html`, and the
  Angular builder did not write the HTML report to a readable on-disk path, so there was no
  numeric summary to transcribe. Plan forbids modifying `karma.conf.js`.
- **Fix:** Created a throwaway override config at `/tmp/karma.baseline.override.js` (outside
  the repo, cannot be committed) that wraps the committed config and adds Istanbul
  `text-summary` + `json-summary` reporters. The committed `karma.conf.js` was NOT touched
  and NO `check.global` thresholds were added.
- **Files modified:** None tracked.
- **Commit:** n/a

## Authentication Gates

None.

## Known Stubs

None — the baseline file contains real measured numbers in every required field (no literal
`TBD` in the Python/Angular number fields).

## Coverage-config Integrity

Verified across the whole plan: `git diff 0f4c79e HEAD -- src/python/pyproject.toml
src/angular/karma.conf.js` is empty — neither coverage-config file was modified. Generated
artifacts (`src/python/htmlcov`, `src/python/.coverage`, `src/angular/coverage/`) are all
gitignored and were not committed.

## Notes for Orchestrator

- Per the objective, STATE.md and ROADMAP.md were NOT modified by this executor. The ROADMAP
  "Coverage Ratchet — Before / After" table still shows `TBD (Phase 97 baseline)` placeholders
  in the Before column (ROADMAP.md lines 308-309). The orchestrator may transcribe these
  Before numbers from the baseline file: Python line `85.19%` (host/provisional, floor 84);
  Angular `83.34% / 69.01% / 79.73% / 84.21%` (no Karma threshold configured yet).

## Self-Check: PASSED

- Baseline file exists: FOUND `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md`
- Task 2 commit exists: FOUND `2177e44`
- Task 2 automated verify gate: PASSED (`numeric baseline OK`, `SHA + numeric baseline OK`)
- Task 1 verify gate (config untouched): PASSED
