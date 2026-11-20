---
phase: 130-release-1-8-1
plan: 01
subsystem: release
tags: [release, pr-156-merge, release-branch, dependabot-triage, soupsieve, poetry-lock]
requires: []
provides:
  - "PR #156 merged to main (merge commit 9d89848c, history kept, bound to head d23f4bdc)"
  - "local branch release/1.8.1 (not pushed) = merged main + replayed Phase 130 planning commits + soupsieve commit"
  - "soupsieve 4.1.3 in src/python/poetry.lock (clears alerts #108, #109, #111, #112 once merged)"
  - "130-REL-EVIDENCE.md: merge record, branch record, Dependabot snapshot, paste/pytz triage, soupsieve roll-in and shipped-or-not evidence"
affects:
  - "130-02 onward (works on release/1.8.1; minimatch fix, version bump, notes)"
  - "130-04 (alert closure re-check after the release merge)"
tech-stack:
  added: []
  patterns:
    - "Poetry-only Python floor ([tool.poetry.dependencies] python) separate from [project] requires-python"
    - "gh pr merge --match-head-commit bound to the verified head"
key-files:
  created:
    - .planning/phases/130-release-1-8-1/130-REL-EVIDENCE.md
  modified:
    - src/python/pyproject.toml
    - src/python/poetry.lock
decisions:
  - "soupsieve resolved to 4.1.3 (newest allowed by poetry update) rather than exactly 4.0.0; both clear all four alerts"
  - "paste #146 and pytz #145 left out of 1.8.1: paste.session unused, pytz imported only by tests (decides the Docker image only)"
metrics:
  duration: "~6 min (22:30Z to 22:36Z)"
  completed: 2026-11-20
  tasks: 2
  files: 3
---

# Phase 130 Plan 01: PR #156 Merge, Release Branch and Soupsieve Roll-in Summary

Phase 129's PR #156 is merged with a two-parent merge commit bound to its verified head, `release/1.8.1` is cut locally from the merged main with the planning commits replayed, Dependabot is triaged (5 alerts, 7 PRs, no new runtime alert), and soupsieve moves 2.9.1 to 4.1.3 through a Poetry-only Python floor with green web suites, quick run and whole-tree ruff.

## Key values

| Item | Value |
|------|-------|
| `PLANNING_HEAD` | b84d1177e359dbacb0bcc1a8182f1bd0bcd8b69f |
| `PR_HEAD` | d23f4bdcd86130954939094a06912b3838aabd4b |
| #156 merge SHA (`MERGE_156`) | 9d89848c68e670a03c97331eca612f932003c933 (parents 74b7a6e4, d23f4bdc) |
| Pre-merge state | OPEN, MERGEABLE, CLEAN, 13 SUCCESS / 5 SKIPPED (publish) / 0 failing / 0 pending |
| Open alert count (after merge) | 5 (soupsieve #108, #109, #111, #112; minimatch #110) |
| Open Dependabot PRs | 7 (#154, #153, #151, #149, #147, #146, #145), matches the plan |
| Resolved soupsieve | 4.1.3 (lock header Poetry 2.3.4) |
| Python floor check | build base 3.11.13, runtime base 3.11.18, published 1.8.0 image 3.11.18 |
| Web suites | 564 passed, 0 failed |
| Quick regression run | 77 passed, 0 failed |
| Ruff 0.15.22 whole tree | All checks passed! |

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Merge PR #156, cut release/1.8.1, Dependabot snapshot and paste/pytz triage | f39f38a6 | 130-REL-EVIDENCE.md |
| 2 | Soupsieve to 4.x via Poetry Python floor, lock regen, shipped-or-not evidence, checks | fd810805 (manifest), d3bd42c9 (evidence) | pyproject.toml, poetry.lock, 130-REL-EVIDENCE.md |

Task 1 verify printed `T1_OK`; Task 2 verify printed `T2_OK`. After both: `git ls-remote --heads origin release/1.8.1` empty, `git tag -l v1.8.1` empty, remote PR branch still at `PR_HEAD`.

## Deviations from Plan

None - plan executed exactly as written. No D-02 or D-06 stop condition occurred. REL-07 and REL-08 were not marked complete (per execution constraints).

## Assumption Drift (advisory)

**1. soupsieve version 4.1.3 instead of the minimum 4.0.0**
- **Found during:** Task 2 step 3
- **Planned:** plan truths require ">= 4.0.0"; CONTEXT D-03 prefers "the smallest fixed version that passes CI", and the research names 4.0.0 as the smallest that clears all four alerts
- **Actual:** `poetry update soupsieve --lock` resolved the newest allowed release, 4.1.3
- **Why:** the plan's command (named-package update, no direct pin) picks the newest compatible version; adding soupsieve as a direct dependency to force 4.0.0 is forbidden by the plan
- **Cost if wrong:** low; soupsieve is test-only (not in the Docker image or a default pip install) and the web suites that load it pass. If CI in Plan 03 fails on it, D-06 applies.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: .planning/phases/130-release-1-8-1/130-REL-EVIDENCE.md
- FOUND: src/python/pyproject.toml (python = ">=3.11.5,<3.13")
- FOUND: src/python/poetry.lock (soupsieve 4.1.3)
- FOUND commits: f39f38a6, fd810805, d3bd42c9
