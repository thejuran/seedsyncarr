---
phase: 100-low-priority-angular-coverage-ci-ratchet
plan: "03"
subsystem: ci-coverage-ratchet
tags: [coverage, ratchet, karma, pytest-cov, ci, angular, python]
dependency_graph:
  requires: [100-01, 100-02]
  provides: [RATCHET-02, v1.3.0-milestone-close]
  affects: [src/angular/karma.conf.js, src/docker/test/angular/Dockerfile, src/python/pyproject.toml]
tech_stack:
  added: []
  patterns:
    - Container-inclusive Python coverage measurement (COVERAGE_FILE=/tmp/.coverage redirect)
    - Dual-patch: check.global + --code-coverage Dockerfile flag in same commit
    - Monotonic ratchet: floor(container-inclusive measured) - 1
key_files:
  created: []
  modified:
    - src/angular/karma.conf.js
    - src/docker/test/angular/Dockerfile
    - src/python/pyproject.toml
    - .planning/ROADMAP.md
    - .planning/RETROSPECTIVE.md
    - .planning/PROJECT.md
decisions:
  - "Python fail_under raised 84 → 88 (container-inclusive 89.27%, margin 1%, floor 88 strictly > 84)"
  - "Angular check.global set stmts 83 / branches 68 / fns 79 / lines 83 (floor(measured)-1, first-ever Karma thresholds)"
  - "Dual-patch: karma.conf.js + Dockerfile --code-coverage flag in same commit to prevent silent no-op gate"
metrics:
  duration: "~35 minutes"
  completed: "2026-05-29"
  tasks_completed: 3
  files_modified: 6
requirements_closed: [RATCHET-02]
---

# Phase 100 Plan 03: CI Coverage Ratchet Summary

**One-liner:** Karma `check.global` gate (stmts 83/branches 68/fns 79/lines 83) + Python `fail_under` 84→88, derived from container-inclusive re-measure (89.27% Python, 84.14%/69.46%/80.49%/84.99% Angular post-100-01/02).

## Tasks Completed

| Task | Name | Commit | Key Outcome |
|------|------|--------|-------------|
| 1 | Re-measure post-99 coverage (container-inclusive) | (no files changed) | Python 89.27% container-inclusive; Angular stmts 84.14% / branches 69.46% / fns 80.49% / lines 84.99%; floors computed: Python 88, Angular 83/68/79/83 |
| 2 | Patch three config files in one commit | dfbab2e | karma.conf.js check.global + text-summary; Dockerfile --code-coverage; pyproject.toml fail_under 88; both gates verified passing |
| 3 | Record before/after + floor decision | 0ff788b | ROADMAP Coverage Ratchet table filled; v1.3.0 RETROSPECTIVE entry; PROJECT.md Key Decisions rows |

## Coverage Numbers

### Python (container-inclusive — ratchet source)
- **Before (baseline anchor):** 85.19% host/provisional (excludes real-lftp integration suite); floor 84
- **Re-measured container-inclusive (Phase 100):** 89.27% (1278 passed, 62 skipped, real-lftp suite included)
- **New floor (fail_under):** 88 = floor(89.27) − 1; margin 1%; computed floor 88 strictly > prior floor 84

### Angular (post-100-01/02)
- **Before (baseline anchor):** Stmts 83.34% / Branches 69.01% / Functions 79.73% / Lines 84.21% (no Karma threshold existed)
- **Measured post-100-01/02:** Stmts 84.14% / Branches 69.46% / Functions 80.49% / Lines 84.99%
- **New floors (check.global):** statements 83 / branches 68 / functions 79 / lines 83 (floor(measured) − 1; first-ever Karma thresholds; all strictly > prior floor of 0)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Ordering Note

Task 1 (measurement) and Task 2 (patching) were partially interleaved per the plan's own note ("if you measure Angular via the Docker route you may interleave with Task 2 — that is fine since both land in the same commit"). The Dockerfile was patched first to enable `--code-coverage` collection, then Angular coverage was measured, then the final threshold values were confirmed equal to what was already written in karma.conf.js (83/68/79/83). All three Task 2 files landed in one commit (dfbab2e) as required by D-06.

## Gate Verification

| Gate | Command | Result |
|------|---------|--------|
| Angular (check.global) | `make run-tests-angular` | Exit 0; text-summary block printed (gate non-silent); stmts 84.14% ≥ 83, branches 69.46% ≥ 68, fns 80.49% ≥ 79, lines 84.99% ≥ 83 |
| Python (fail_under=88) | container-inclusive docker compose run | "Required test coverage of 88.0% reached. Total coverage: 89.27%" — exit 0 |
| --code-coverage in Dockerfile | `grep -c -- "--code-coverage" src/docker/test/angular/Dockerfile` | 1 |
| check: in karma.conf.js | `grep "check:" src/angular/karma.conf.js` | present |
| fail_under > 84 | `grep "fail_under" src/python/pyproject.toml` | fail_under = 88 |
| TBD cells gone | `grep -c "TBD (Phase 100)" .planning/ROADMAP.md` | 0 |
| v1.3.0 in RETROSPECTIVE | `grep -c "v1.3.0" .planning/RETROSPECTIVE.md` | 3 |

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All changes are CI configuration files and planning documentation. T-100-03 and T-100-03-W mitigated: the dual-patch (check.global + --code-coverage) ensures the gate is non-silent and non-fatal (emitWarning omitted, defaults false).

## Self-Check: PASSED

- src/angular/karma.conf.js: modified (check.global block + text-summary reporter) — exists ✓
- src/docker/test/angular/Dockerfile: modified (--code-coverage in CMD) — exists ✓
- src/python/pyproject.toml: modified (fail_under = 88) — exists ✓
- .planning/ROADMAP.md: TBD cells filled — 0 TBD remaining ✓
- .planning/RETROSPECTIVE.md: v1.3.0 entry added ✓
- .planning/PROJECT.md: floor/margin decision rows added ✓
- Task 2 commit dfbab2e: exists ✓
- Task 3 commit 0ff788b: exists ✓
- All three Task 2 files in one commit: confirmed (dfbab2e touches exactly karma.conf.js + Dockerfile + pyproject.toml) ✓
- Python fail_under 88 strictly > 84: ✓
- Angular floors all > prior floor of 0: ✓
