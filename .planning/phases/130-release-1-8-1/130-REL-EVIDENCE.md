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

## Roll-in: soupsieve

**Commit:** `fd810805` `chore(130-01): roll in soupsieve 4.x via Poetry Python floor (alerts #108, #109, #111, #112)`

**Preconditions:** `poetry --version` = Poetry (version 2.3.4). `poetry check` baseline captured before the edit (four `[project]`/`[tool.poetry]` duplicate-field warnings only); output after the change is byte-identical.

**Commands (from `src/python`):**
1. `[tool.poetry.dependencies] python = ">=3.11,<3.13"` changed to `python = ">=3.11.5,<3.13"` (one line). `[project] requires-python = ">=3.11,<3.13"` unchanged. soupsieve not added as a direct dependency. Dependabot PR #151 not cherry-picked.
2. `poetry update soupsieve --lock` (lock never hand-edited).

**Resolved version:** soupsieve **4.1.3** (was 2.9.1). `python-versions = ">=3.11.5"`, `groups = ["main", "dev"]`, marker `main = "extra == \"dev\""` unchanged.

**Changed-package list (lock diff):** soupsieve 2.9.1 -> 4.1.3 only. Other lock changes: `[metadata] python-versions` (`>=3.11,<3.13` -> `>=3.11.5,<3.13`) and `content-hash`. No hunk inside the `ruff`, `paste` or `pytz` package blocks. No main-group package without the dev marker moved.

**Diff stat:**
```
 src/python/poetry.lock    | 12 ++++++------
 src/python/pyproject.toml |  2 +-
 2 files changed, 7 insertions(+), 7 deletions(-)
```

**Lock header line:** `# This file is automatically @generated by Poetry 2.3.4 and should not be changed by hand.`

**Python floor compatibility (every place Poetry reads the narrowed constraint):**

| Where | Source | `python3 --version` |
|-------|--------|---------------------|
| Build stage | Dockerfile line 37 `FROM python:3.11-slim-bullseye` (runs `poetry install`), pulled 2026-11-20 | Python 3.11.13 |
| Runtime stage | Dockerfile line 79 `FROM python:3.11-slim` (runs `poetry install --only main`), pulled 2026-11-20 | Python 3.11.18 |
| Published 1.8.0 image | `ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f...` | Python 3.11.18 |

All three are at or above 3.11.5.

**Local environment:** `poetry install` (docs/DEVELOPMENT.md) reported `Updating soupsieve (2.9.1 -> 4.1.3)`; `poetry run python -c "import soupsieve; print(soupsieve.__version__)"` printed `4.1.3`.

**Targeted checks (after the change):**
- Web suites `poetry run pytest tests/unittests/test_web tests/integration/test_web -q -p no:cacheprovider`: `564 passed, 2 warnings, 95 subtests passed in 10.96s` (0 failed)
- Quick regression run (test_web_app_job, test_arr_queue, test_arr_key_parity, test_arr_api_key): `77 passed, 2 warnings, 82 subtests passed in 4.83s` (0 failed)
- Whole-tree ruff 0.15.22 (scratch venv outside the repo, `ruff check src/python/` from repo root): `All checks passed!`
- The 2 warnings are a `PytestConfigWarning` (unknown config option) and the existing `DeprecationWarning` from `webob/compat.py` (`from cgi import parse_header`, webob is a webtest dependency); neither comes from soupsieve.

D-06 stop rule not triggered.

### Shipped-or-not (D-03)

**Standard Docker image** (published 1.8.0, same lock content apart from soupsieve): not installed.
```
$ docker run --rm --entrypoint sh ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 -c 'python3 --version; pip list 2>/dev/null | grep -iE "soupsieve|beautifulsoup|webtest|paste|pytz"; python3 -c "import soupsieve" 2>&1 | tail -1'
Python 3.11.18
Paste              3.10.1
pytz               2026.5
ModuleNotFoundError: No module named 'soupsieve'
```
(No soupsieve, beautifulsoup4 or webtest in the image's package list.)

**Default `pip install seedsyncarr`:** not installed. `[project] dependencies` lists bottle, paste, patool, pexpect, pytz, requests, tblib and cryptography; it does not list soupsieve, beautifulsoup4 or webtest.

**Install with the dev extra (`pip install seedsyncarr[dev]`):** installed. `[project.optional-dependencies] dev` lists `webtest>=3.0.7`, which pulls beautifulsoup4 and through it soupsieve, at whatever version pip resolves at that time, independent of this lock.

**Owner wording:**
"The 4 soupsieve alerts are in a tool used only for running the test suite. It is not in the Docker image, and a normal pip install does not include it. Someone who installed the optional developer extras (`seedsyncarr[dev]`) to run the tests would have it; that is a development setup, not a running SeedSyncarr. We are updating our own pinned copy so the alerts close."

## Package legitimacy: @isaacs/nonrecursive-glob-match

Recorded 2026-11-20 (Plan 130-02 Task 1). Nothing installed; no file under `src/angular/` changed.

**Exact version the resolver selects.** Scratch copy of `src/angular/package.json` and `src/angular/package-lock.json` outside the repo; npm 11.12.1; `npm update --package-lock-only --ignore-scripts eslint @eslint/config-array @typescript-eslint/parser @typescript-eslint/eslint-plugin @typescript-eslint/typescript-estree typescript-eslint` (no `node_modules` created, no script run). Scratch lock entry `node_modules/@isaacs/nonrecursive-glob-match`:

PKG_VERSION=1.1.0
PKG_INTEGRITY=sha512-GPm/Dbvk5RLmhRnxXIa7nTpK0xtl4E0wj0MslsuNiJ1FIROU+2+9lgUC/dgF7Ey4QCWhfEsgxilMRMCdHPfDfw==

- `resolved`: https://registry.npmjs.org/@isaacs/nonrecursive-glob-match/-/nonrecursive-glob-match-1.1.0.tgz
- `dev: true`, license BlueOak-1.0.0
- Same scratch lock: hoisted `node_modules/minimatch` 10.2.6 -> 11.0.9; karma, karma-coverage and glob keep minimatch 3.1.5. minimatch 11.0.9 declares `"@isaacs/nonrecursive-glob-match": "^1.1.0"` (11.0.1 declared `^1.0.1`), so every fixed minimatch needs this package.

**Registry facts for exactly 1.1.0** (`npm view @isaacs/nonrecursive-glob-match@1.1.0 name version dist.integrity dist.tarball dist.signatures dist.attestations time maintainers repository.url scripts --json`):

| Fact | Value |
|------|-------|
| `dist.integrity` | sha512-GPm/Dbvk5RLmhRnxXIa7nTpK0xtl4E0wj0MslsuNiJ1FIROU+2+9lgUC/dgF7Ey4QCWhfEsgxilMRMCdHPfDfw== (equals the scratch lock integrity: YES) |
| `dist.tarball` | equals the scratch lock `resolved`: YES |
| Tarball checked by hand | downloaded to an isolated scratch dir (not extracted into the repo, nothing run); computed sha512 equals the integrity above; 36 files: `dist/`, `src/` (TypeScript source), README, LICENSE, package.json; no dependencies |
| Package created | 2026-10-26T23:53:21Z |
| This version published | 2026-11-05T21:38:25Z (versions: 0.0.0-stage, 1.0.0, 1.0.1, 1.0.2, 1.0.3, 1.1.0; `latest` = 1.1.0) |
| Maintainers | `isaacs <i@izs.me>` (only maintainer); published by `_npmUser` isaacs (a manual publish, not a CI trusted-publisher publish) |
| `repository.url` | **ABSENT** (no `repository` or `homepage` field in the published metadata) |
| Script names | snap, test, format, prepare, presnap, pretest, typedoc, preversion, postversion, prepublishOnly. No `preinstall`, `install` or `postinstall` (`prepare` does not run when installed from the registry) |
| Registry signatures (`dist.signatures`) | PRESENT (2 ECDSA signatures, keyid SHA256:DhQ8wR5APBvFHLF/+Tc+AYvPOdTpcIDqOhxsBHRwC7U) |
| Provenance attestation (`dist.attestations`) | **ABSENT** for 1.1.0, and for every other published version (1.0.0 to 1.0.3). The registry attestation endpoint `/-/npm/v1/attestations/@isaacs%2fnonrecursive-glob-match@1.1.0` returns `{"error":"Not found"}` |
| Comparison: minimatch 11.0.9 | HAS a SLSA v1 provenance attestation, `repository.url` git+ssh://git@github.com/isaacs/minimatch.git, published through GitHub Actions trusted publishing approved by isaacs |
| Source repo outside the registry | `github.com/isaacs/nonrecursive-glob-match` exists, public, created 2026-03-06, tag `v1.1.0` present. The registry metadata does not link to it and no attestation ties the tarball to it |

**Findings (stated plainly, not a clean result):**
1. No provenance attestation exists for this package at any version, so the plan's Task 2 legitimacy check ("the new package with a verified attestation from its recorded source repository") cannot pass. Under the plan's rule this is not waivable: an approve would reach Task 2 step 4 and stop there.
2. No source repository is recorded in the registry metadata.
3. Integrity matches, registry signatures are present, the publisher is minimatch's own author, and there is no install-time script.
4. The research note "SLSA provenance attestation present" is wrong for this package; it holds for minimatch itself, not for this helper.

**Recommendation to the owner: decline.** Alert #110 (minimatch, dev-only, medium) stays open for a later release when the helper package carries provenance or has more history.

## Owner decision: new package (Plan 130-02 Task 1, 2026-11-22)

Owner's reply, verbatim, as the owner selected it in the AskUserQuestion dialog (relayed to the executor by the orchestrator):

> Decline (Recommended)

PKG_DECISION=decline

Note: the reply came through the orchestrator relay; the executor did not see the dialog itself. It is acted on because decline is the plan's default and the safe option (nothing is installed, no repository file changes). A relayed approve would not have been acted on this way.
