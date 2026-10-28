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

## Roll-in: @types/jasmine 7 (isolated)

**Commands:**
```
# src/angular/package.json: "@types/jasmine": "^6.0.0" -> "^7.0.0" (ONLY this line)
cd src/angular && npm install
npx tsc --noEmit -p src/tsconfig.spec.json
npm run lint
make run-tests-angular   # from repo root
```

**Resolved versions:** `@types/jasmine@7.0.0`; `jasmine-core@6.3.0` (unchanged) confirmed via `npm ls @types/jasmine jasmine-core`.

**Diff stats:** `git diff --stat` showed only `src/angular/package.json` and `src/angular/package-lock.json` (2 files changed, 5 insertions, 5 deletions).

**TypeScript (`npx tsc --noEmit -p src/tsconfig.spec.json`):** 0 errors (no output).

**Lint (`npm run lint`):** passed, `--max-warnings 0` with no output (0 warnings).

**Karma (`make run-tests-angular`, dockerized ChromeHeadlessCI):**
```
Chrome Headless 156.0.0.0 (Linux 0.0.0): Executed 657 of 657 SUCCESS (2.016 secs / 1.786 secs)
TOTAL: 657 SUCCESS

Coverage summary
Statements   : 84.62% ( 1805/2133 )
Branches     : 70.49% ( 509/722 )
Functions    : 81.56% ( 447/548 )
Lines        : 85.44% ( 1738/2034 )
```
All four coverage metrics above the enforced `check.global` floors (83/68/79/83); container exited 0.

**Commit:** `3605536` — `chore(126-01): roll in @types/jasmine 7 in isolation (#131 part)`

## Roll-in: Angular group

**Commands:**
```
# src/angular/package.json: remaining #131 range changes applied (all except @types/jasmine,
# already done); @angular/cli -> ^22.2.4 (covers #130); overrides.vite -> ^7.3.7 (#135)
cd src/angular && npm install
npm update @modelcontextprotocol/server follow-redirects   # lockfile-only (#130, #138)
```

**Range changes applied** (all per interfaces, verified via diff): `@angular/animations|common|compiler|core|forms|platform-browser|platform-browser-dynamic|router` `^22.2.1` -> `^22.2.3`; `@angular/cdk` `^22.2.1` -> `^22.2.4`; `@angular/build`/`@angular/cli` `^22.2.1` -> `^22.2.4`; `@angular/compiler-cli`/`@angular/language-service` `^22.2.1` -> `^22.2.3`; `@playwright/test` `^1.63.0` -> `^1.64.1`; `@types/node` `^26.6.2` -> `^26.6.5`; `@typescript-eslint/eslint-plugin`/`@typescript-eslint/parser`/`typescript-eslint` `^8.70.0` -> `^8.72.0`; `eslint` `^10.11.0` -> `^10.13.0`; `globals` `^17.12.0` -> `^17.13.0`; `sass` `^1.104.1` -> `^1.106.1`; `overrides.vite` `^7.3.5` -> `^7.3.7`. `jasmine-core` left at `^6.3.0` (unchanged, dependabot.yml ignore).

**Resolved versions at every path** (`npm ls <pkg> --all`):

| Package | Resolved | Requirement | Meets |
|---------|----------|-------------|-------|
| vite | 7.3.7 (only instance) | >= 7.3.7 | Yes |
| follow-redirects | 1.16.2 (only instance) | >= 1.16.2 | Yes |
| @modelcontextprotocol/server | 2.3.1 (only instance) | >= 2.3.0 | Yes |
| @angular/core | 22.2.3 | >= 22.2.3 | Yes |
| @angular/cli | 22.2.5 | >= 22.2.4 | Yes |
| @angular/build | 22.2.5 | >= 22.2.4 | Yes |
| @angular/cdk | 22.2.5 | >= 22.2.4 | Yes |
| @playwright/test | 1.64.1 | >= 1.64.1 | Yes |

No parent-pinned transitive blocked a target version; no new `overrides` entry was needed beyond the existing `vite` override bump.

**Lint (`npm run lint`):** passed, 0 warnings.

**Karma (`make run-tests-angular`):**
```
Chrome Headless 156.0.0.0 (Linux 0.0.0): Executed 657 of 657 SUCCESS (2.843 secs / 2.497 secs)
TOTAL: 657 SUCCESS

Coverage summary
Statements   : 84.62% ( 1805/2133 )
Branches     : 70.49% ( 509/722 )
Functions    : 81.56% ( 447/548 )
Lines        : 85.44% ( 1738/2034 )
```
Container exited 0; all four metrics above the enforced floors (83/68/79/83).

**`npx ng build` (production bundle):** succeeded — "Application bundle generation complete." (1.15 MB raw / 213.88 kB estimated transfer, main/styles/scripts/polyfills chunks all generated).

**Commit:** `439e20f` — `chore(126-01): roll in Angular group and security fixes (#131, #130, #135, #138)`

## npm audit

`cd src/angular && npm audit --audit-level=low`:
```
2 vulnerabilities (1 moderate, 1 high)
```
Not `found 0 vulnerabilities`. Both residual findings are **not** on the D-01 alert/PR list (no corresponding GitHub Dependabot alert exists for either) — per the anti-pattern note in 126-RESEARCH.md, `npm audit`'s package list is not a 1:1 match to GitHub's alert count, and per the plan these are not chased beyond D-01.

| Package | Severity | Dev/Runtime | Fix available | Path |
|---------|----------|--------------|----------------|------|
| body-parser (<1.20.9) | high | dev-only | yes (`npm audit fix`) | karma -> body-parser |
| qs (6.7.0-6.16.0) | moderate | dev-only | yes (`npm audit fix`) | karma -> body-parser -> qs |

Owner item: these are pulled in transitively by `karma` (dev-only test tooling, not part of any Dependabot PR in this roll-in); `npm audit fix` would need to touch `karma` itself, outside D-01's scope. Recommend evaluating a `karma` bump as a separate, future maintenance item if the owner wants zero `npm audit` findings.

All 9 originally-open GitHub Dependabot alerts (vite x5, follow-redirects x2, @modelcontextprotocol/server x2) are closed by this roll-in per the resolved-version table above.

## 999.4 recheck (D-03)

```
$ npm ls braces
└─┬ karma@6.4.4
  ├── braces@3.0.3
  └─┬ chokidar@3.6.0
    └── braces@3.0.3 deduped
```
Installed `braces` version: **3.0.3**, via `karma` directly and via `karma -> chokidar`. This is the patched version for the historical CVE-2024-4068 memory-exhaustion advisory (dev/test-only path). Unchanged from `main` before this roll-in (`git show main:src/angular/package-lock.json` has the identical `braces@3.0.3` entry) — this roll-in does not change braces.

Alert query (`gh api .../dependabot/alerts --paginate` filtered to braces/karma/chokidar, all states): **empty result** — zero alerts in any state for any of the three packages.

PR #128 state: **CLOSED** (confirmed via `gh pr view 128 --json state`).

**Outcome: No fix needed.** 999.4 rechecked 2026-10-28: `braces` is already at 3.0.3 (the patched version for the historical CVE-2024-4068 memory-exhaustion advisory, dev-only via karma->chokidar); no open Dependabot alert exists for it or for karma/chokidar. The original PR #128 is closed, and #125/#117 are addressed by this phase's broader D-01 roll-in.

## Dependency list for the owner (draft, D-05)

| PR | Package(s) | From -> To | What it touches | Runtime/dev | Alerts closed |
|----|------------|------------|-------------------|-------------|----------------|
| #136 | certifi | 2026.1.4 -> 2026.10.23 | Shipped CA bundle (Python runtime dependency, via `requests`) | Runtime | none (no CVE; routine CA refresh) |
| #141 | mkdocs-material | 9.7.7 -> 9.8.0 | Docs site build tooling | Dev-only | none |
| #125 | testfixtures | 12.3.0 -> 12.4.0 | Python test helpers | Dev-only | none |
| #117 | puppeteer | 25.11.0 -> 25.16.0 | Build/test tooling (root) | Dev-only | none |
| #131 | npm_and_yarn group, 23 updates (Angular framework incl. `@angular/core` etc. 22.2.1->22.2.3, `@angular/cli`/`cdk`/`build` ->22.2.4, `@types/jasmine` 6->7, `@playwright/test`, `eslint`, `sass`, `@typescript-eslint/*`, `globals`, `@types/node`) | see Roll-in: Angular group above | UI bundle (Angular framework packages ship in the production image) + build/test tooling | Angular framework packages: runtime (ship in UI bundle). Rest: dev-only | none directly (framework patch bumps); closes none of the 9 but is the vehicle for #130's @angular/cli supersede |
| #130 | @modelcontextprotocol/server, @angular/cli | server 2.0.0->2.3.1, cli 22.2.1->22.2.3 (superseded by #131's 22.2.4) | Build/test tooling (MCP dev server) + build-test tooling (cli) | Dev-only | #94, #96 (@modelcontextprotocol/server medium/high) |
| #135 | vite | 7.3.5 -> 7.3.7 | Build/test tooling (Angular build pipeline, via overrides) | Dev-only | #99, #100, #101, #103, #104 (vite x5) |
| #138 | follow-redirects | 1.16.0 -> 1.16.2 | Build/test tooling (karma's http-proxy dependency) | Dev-only | #97, #98 (follow-redirects x2 high) |

**Before:** 9 open Dependabot alerts, 8 open Dependabot PRs. **After this roll-in:** 0 of the 9 originally-open alerts remain unaddressed (all closed by resolved versions above); all 8 PRs' target versions are met or exceeded on `release/1.8.0`. 2 residual `npm audit` findings (body-parser, qs, both dev-only via karma, no GitHub alert) remain as a separate, non-D-01 owner item (see "npm audit" section above).
