# Phase 126 Plan 01: Dependabot Roll-In Evidence

**Phase:** 126-release-1-8-0
**Branch:** release/1.8.0
**Base SHA:** 36867467cce493e89ddd30e6c7f6b6f00ec1c6d6 (local `main`, ahead of `origin/main` only by `.planning/` commits)
**Started:** 2026-10-28T19:51:36Z

Only package names, versions, counts, test names and exception class names are recorded. No secret value appears in this file.

## Dependabot snapshot (start of 126-01)

Queried live via `gh api` / `gh pr list` at session start (2026-10-28).

**Open alert count:** 9

**Open alert detail:**

| # | Package | Scope | Severity |
|---|---------|-------|----------|
| 104 | vite | development | medium |
| 103 | vite | development | low |
| 101 | vite | development | medium |
| 100 | vite | development | high |
| 99 | vite | development | medium |
| 98 | follow-redirects | development | high |
| 97 | follow-redirects | development | high |
| 96 | @modelcontextprotocol/server | development | high |
| 94 | @modelcontextprotocol/server | development | medium |

**Open Dependabot PR list:**

| PR | Title |
|----|-------|
| 141 | chore(deps-dev): bump mkdocs-material from 9.7.7 to 9.8.0 in /src/python |
| 138 | chore(deps): bump follow-redirects from 1.16.0 to 1.16.2 in /src/angular |
| 136 | chore(deps): bump certifi from 2026.1.4 to 2026.10.19 in /src/python in the pip group across 1 directory |
| 135 | chore(deps-dev): bump vite from 7.3.5 to 7.3.7 in /src/angular |
| 131 | chore(deps): bump the npm_and_yarn group across 1 directory with 23 updates |
| 130 | chore(deps): bump @modelcontextprotocol/server and @angular/cli in /src/angular |
| 125 | chore(deps-dev): bump testfixtures from 12.3.0 to 12.4.0 in /src/python |
| 117 | chore(deps-dev): bump puppeteer from 25.11.0 to 25.16.0 in the root group across 1 directory |

**Comparison against interfaces list (126-01-PLAN.md):** exact match — 9 open alerts (vite x5, follow-redirects x2, @modelcontextprotocol/server x2), 8 open Dependabot PRs (#136, #141, #125, #117, #135, #138, #130, #131). No new runtime/shipped-dependency alert outside the eight PRs; no additional Dependabot PR has appeared. D-04 condition not triggered.

## Roll-in: Python

**Commands:**
```
cd src/python && poetry update certifi mkdocs-material testfixtures
```

**Resolved versions:**

| Package | Before | After | Target (PR) | Meets target |
|---------|--------|-------|--------------|--------------|
| certifi | 2026.1.4 | 2026.10.23 | 2026.10.19 (#136) | Yes (exceeds) |
| mkdocs-material | 9.7.7 | 9.8.0 | 9.8.0 (#141) | Yes |
| testfixtures | 12.3.0 | 12.4.0 | 12.4.0 (#125) | Yes |

**Diff stats:** `git diff --stat` shows only `src/python/poetry.lock` (1 file changed, 19 insertions, 19 deletions). No hunk inside the `name = "ruff"` block (`git diff src/python/poetry.lock | grep -A5 'name = "ruff"'` empty).

**Python quick suite tail:**
```
1945 passed, 2 warnings, 106 subtests passed in 46.41s
```
(2 pre-existing warnings are an unrelated pytest config option and a webob `cgi` deprecation notice, not introduced by this bump.)

**Ruff (CI pin 0.15.22, whole-tree `src/python/`):**
```
All checks passed!
```

**mkdocs build** (`poetry run mkdocs build --site-dir <scratchpad>/site`):
```
INFO    -  Documentation built in 0.19 seconds
```
Build succeeded (the two "not included in nav" INFO lines are pre-existing and unrelated).

**Commit:** `de888a9` — `chore(126-01): roll in certifi, mkdocs-material, testfixtures (#136, #141, #125)`

## Roll-in: root (puppeteer)

**Commands:**
```
# root package.json: "puppeteer": "^25.11.0" -> "^25.16.0"
npm install
```

**Resolved versions:**

| Package | Before | After | Target (PR) | Meets target |
|---------|--------|-------|--------------|--------------|
| puppeteer | 25.11.0 | 25.16.0 | 25.16.0 (#117) | Yes |

**Diff stats:** `git diff --stat` showed only `package.json` and `package-lock.json` (2 files changed, 55 insertions, 55 deletions). Root `version` field confirmed unchanged at `1.7.6` (version bump is Plan 03).

**Test:** `npm run test:release-metadata` (root's only test script):
```
ℹ tests 21
ℹ pass 21
ℹ fail 0
```

**Commit:** `e02884f` — `chore(126-01): roll in puppeteer 25.16.0 (#117)`

### D-02 stop

Not triggered. All targeted checks passed for both the Python and root roll-ins.
