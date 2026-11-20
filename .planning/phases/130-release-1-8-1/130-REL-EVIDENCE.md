# Phase 130: Release 1.8.1 Evidence

**Phase:** 130-release-1-8-1
**Branch:** release/1.8.1 (local only, not pushed)
**Base merge SHA:** 9d89848c68e670a03c97331eca612f932003c933 (PR #156 merge commit, `origin/main` at cut time)
**Started:** 2026-11-20

Only package names, versions, counts, test names and exception class names are recorded. No secret value appears in this file.

## PR #156 merge (D-01, D-02)

**Starting point (step 1):**
- Checked-out branch: `gsd/phase-129-web-service-cleanup-isolation`
- `PLANNING_HEAD`: `b84d1177e359dbacb0bcc1a8182f1bd0bcd8b69f` (passes the test: `git cat-file -e HEAD:.planning/phases/130-release-1-8-1/130-06-PLAN.md` succeeded)
- Tracked tree clean: `git status --porcelain --untracked-files=no` printed nothing (untracked `.planning/reconcile-ledger.json` and `.planning/reconcile-pending.json` left alone)
- `PR_HEAD`: `d23f4bdcd86130954939094a06912b3838aabd4b`
- Nothing was pushed to the PR branch. Remote `gsd/phase-129-web-service-cleanup-isolation` still at `d23f4bdcd86130954939094a06912b3838aabd4b` after the merge.

**D-02 pre-merge checks (step 2, then re-read immediately before the merge at 2026-11-20T22:33:23Z):**

| Check | Observed |
|-------|----------|
| state | OPEN |
| mergeable | MERGEABLE |
| mergeStateStatus | CLEAN |
| headRefOid | d23f4bdcd86130954939094a06912b3838aabd4b (= `PR_HEAD`, unchanged between first read and pre-merge re-read) |
| `gh pr checks 156` | 13 SUCCESS, 5 SKIPPED (publish jobs: Publish Docker Image, Publish Docker Image (:dev), Publish Documentation, Publish GitHub Release, Publish to PyPI; normal on a PR), 0 failing, 0 pending |
| `git merge-base --is-ancestor PR_HEAD PLANNING_HEAD` | succeeded |
| `git diff --name-only PR_HEAD PLANNING_HEAD` | 15 paths, all under `.planning/` (18 commits) |

**Merge (step 3):**
- Command: `gh pr merge 156 --merge --match-head-commit d23f4bdcd86130954939094a06912b3838aabd4b` (merge commit, history kept, no branch deletion)
- `MERGE_156` (from `gh pr view 156 --json mergeCommit`): `9d89848c68e670a03c97331eca612f932003c933`, mergedAt 2026-11-20T22:33:25Z, state MERGED
- Subject: `Merge pull request #156 from thejuran/gsd/phase-129-web-service-cleanup-isolation`
- Parents: `74b7a6e4b0ed11d9c0089e5eab49590085738a3d` (previous main) and `d23f4bdcd86130954939094a06912b3838aabd4b` (second parent = `PR_HEAD`)
- After `git fetch origin`: `origin/main` = `9d89848c68e670a03c97331eca612f932003c933` = `MERGE_156` (no extra commits)
- Side effect: the merge to main publishes `:dev` and docs as normal. Production and the sandbox do not use `:dev`.

**Release branch (step 4):**
- `git branch release/1.8.1 b84d1177e359dbacb0bcc1a8182f1bd0bcd8b69f` then `git rebase --onto origin/main d23f4bdcd86130954939094a06912b3838aabd4b release/1.8.1`: 18 planning commits replayed, no conflict
- Branch head after replay: `764976d5555f15557f757409c80750b43a0d8176`
- `git merge-base --is-ancestor origin/main HEAD`: succeeded
- `git diff --name-only origin/main HEAD`: only `.planning/` paths; per-commit check of all 18 replayed commits found 0 paths outside `.planning/`
- `git ls-remote --heads origin release/1.8.1`: empty (not pushed)

## Dependabot snapshot (start of 130-01)

Taken after the #156 merge, 2026-11-20, via `gh api repos/thejuran/seedsyncarr/dependabot/alerts` and `gh pr list --author app/dependabot`.

**Open alert count:** 5

**Open alert detail:**

| # | Package | Scope | Severity | First fixed |
|---|---------|-------|----------|-------------|
| 108 | soupsieve | runtime | medium | 2.10.0 |
| 109 | soupsieve | runtime | high | 4.0.0 |
| 110 | minimatch | development | medium | 11.0.1 |
| 111 | soupsieve | runtime | medium | 3.0.2 |
| 112 | soupsieve | runtime | high | 3.0.2 |

**Open Dependabot PR list:**

| PR | Created | Title |
|----|---------|-------|
| 154 | 2026-11-18 | chore(deps): bump the npm_and_yarn group across 1 directory with 23 updates |
| 153 | 2026-11-18 | chore(deps-dev): bump puppeteer from 25.16.0 to 25.17.0 in the root group |
| 151 | 2026-11-13 | chore(deps): bump soupsieve from 2.9.1 to 4.0 in /src/python in the pip group across 1 directory |
| 149 | 2026-11-11 | chore(deps-dev): bump mkdocs-material from 9.8.0 to 9.8.1 in /src/python |
| 147 | 2026-11-04 | chore(deps-dev): bump pytest from 9.1.1 to 9.2.0 in /src/python |
| 146 | 2026-11-04 | chore(deps): bump paste from 3.10.1 to 3.11.0 in /src/python |
| 145 | 2026-11-04 | chore(deps): bump pytz from 2026.5 to 2026.6 in /src/python |

**Comparison against the plan's interfaces list:** exact match. 5 open alerts (soupsieve #108, #109, #111, #112; minimatch #110) and 7 open Dependabot PRs (#154, #153, #151, #149, #147, #146, #145). No new runtime/shipped alert and no new Dependabot PR. D-07 owner item not triggered.

## Triage: left out (D-04, D-05 deferrals)

- **paste #146 (3.10.1 -> 3.11.0): left out.** Its "critical" advisory GHSA-vf89-fq68-57cx is in paste's session-cookie feature (`paste.session`). SeedSyncarr does not use that feature. Fresh `grep -rn "paste" src/python --include='*.py'` import lines:
  - `src/python/web/web_app_job.py:6: from paste import httpserver`
  - `src/python/web/web_app_job.py:7: from paste.translogger import TransLogger`
  - `src/python/tests/unittests/test_web/test_web_app_job.py:533: from paste import httpserver as paste_httpserver` (test)
  - `src/python/tests/unittests/test_web/test_web_app_job.py:591: from paste import httpserver as paste_httpserver` (test)
  - `grep -rnE "SessionMiddleware|paste\.session"`: no match.
  Rolling it in would also change the web server library that Phase 129's shutdown fix depends on, with no reachable benefit. There is no Dependabot alert for it.
- **pytz #145 (2026.5 -> 2026.6): left out.** A timezone data refresh. Fresh grep shows only test files import pytz: `tests/unittests/test_web/test_serialize/test_serialize_model.py:4` and `tests/unittests/test_web/test_serialize/test_serialize_status.py:4`. No runtime module imports it.
- **Scope of the paste and pytz decision:** it decides what the Docker image contains (the lock keeps Paste 3.10.1 and pytz 2026.5 there). People who install with pip are not pinned by the lock: the package metadata only sets lower bounds (`paste>=3.10.1`, `pytz>=2025.2`), and pip picks the newest allowed version for them, with or without this release.
- **#154 (Angular npm group), #153 (puppeteer), #149 (mkdocs-material), #147 (pytest): left open** per D-05 and the CONTEXT deferred list (dev/build tooling, no shipped change wanted in 1.8.1).
- **#151 (soupsieve 2.9.1 -> 4.0):** not merged or cherry-picked; superseded by the soupsieve roll-in below (D-03).
