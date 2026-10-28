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

## Release notes fact checks

**D-08 (Phase 121 token-exposure version range):** per the plan's Task 1 step 2, checked when the
unconditional token-attach logic was first released, rather than assuming "since v1.0.0" from
STATE.md's carried-forward note.

```
$ git show v1.0.0:src/angular/src/app/services/utils/auth.interceptor.ts
```

Output (relevant excerpt) confirms the file exists at `v1.0.0` and already contains the
unconditional attach logic:

```
export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const token = getApiToken();
    if (token) {
        const authReq = req.clone({
            setHeaders: {Authorization: `Bearer ${token}`}
        });
        return next(authReq);
    }
    return next(req);
};
```

**Result:** the unconditional attach (no `isOwnApiRequest` gate) was present at the `v1.0.0` tag
itself — the first released version already had it. Confirmed the CHANGELOG/release-notes wording
"Versions 1.0.0 through 1.7.6" is accurate (no earlier tag to check; `v1.0.0` is the oldest version
tag in the repo). No fallback to "1.7.6 and earlier" was needed.

**D-16 rollback `%` fact check (Task 2):** confirmed `git show v1.7.6:release-notes.md`'s existing
rollback caution ("remove any `%` from secrets you saved on 1.7.6 ... older versions read it but
fail") is about rolling back *from* 1.7.6 *to* 1.7.5-or-earlier (pre-119.1 fix), not about a
1.8.0-to-1.7.6 rollback. Checked whether 119.1-06's `%%`-escape fix (`Config.to_str` encodes every
`%` as `%%` on write; the unchanged `from_str` decodes it back) is part of the 1.7.6 release:

```
$ git merge-base --is-ancestor 8938695 v1.7.6 && echo "8938695 (119.1-06 GREEN) IS ancestor of v1.7.6"
8938695 (119.1-06 GREEN) IS ancestor of v1.7.6
```

Combined with the earlier rollback-safety finding (zero diff to `common/config.py` between
`v1.7.6` and `main`), 1.7.6 and 1.8.0 write and read `%` in secrets identically. The 1.8.0
release-notes.md rollback section states this fact plainly and does not add an extra numbered
step for it, per the plan's "include a step only if 1.7.6 needs one."

## Release gate (Task 3)

Hygiene: only command output, counts, names and conclusions are recorded below. No secret value
appears in this file.

### Full host suite

```
$ cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider \
    --ignore=tests/unittests/test_ssh/test_sshcp.py \
    --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py \
    --ignore=tests/unittests/test_system/test_scanner.py \
    --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py
1945 passed, 2 warnings, 106 subtests passed in 46.36s
```

0 failed. The four ignored files are the pre-existing host-only exclusions (ssh / multiprocessing
scanner / extract process timeouts on this macOS host); CI's dockerized `unittests-python` job
runs them and is the authority for those paths (see CI section below).

### Ruff 0.15.22 (whole tree)

```
$ <scratch>/ruff/bin/ruff --version
ruff 0.15.22
$ <scratch>/ruff/bin/ruff check src/python/
All checks passed!
```

### Packaging

`build`/`twine` installed in a scratch venv (mirroring CI's `pip install build twine`, same
pattern as 119.1-REL04):

```
$ cd src/python && rm -rf dist && <scratch>/pkg/bin/python -m build -q
Successfully built seedsyncarr-1.8.0.tar.gz and seedsyncarr-1.8.0-py3-none-any.whl
$ <scratch>/pkg/bin/twine check dist/*
Checking dist/seedsyncarr-1.8.0-py3-none-any.whl: PASSED with warnings
  WARNING long_description_content_type missing. defaulting to text/x-rst.
  WARNING long_description missing.
Checking dist/seedsyncarr-1.8.0.tar.gz: PASSED with warnings
  (same two warnings)
$ python3 ../../scripts/verify-python-package.py dist
PASS seedsyncarr-1.8.0-py3-none-any.whl members=85
INFO seedsyncarr-1.8.0-py3-none-any.whl files=85
PASS seedsyncarr-1.8.0.tar.gz members=84
TOTAL members=169
PACKAGE_OK
```

Both warnings are the same pre-existing, non-blocking warnings recorded in every prior release's
evidence (1.7.6, 1.7.5); nothing new.

### Release metadata

```
$ node scripts/verify-release-metadata.mjs 1.8.0
Release metadata matches 1.8.0:
- CHANGELOG.md has release section [1.8.0]
- release-notes.md links to CHANGELOG.md through the {{VERSION}} tag placeholder
- package.json version is 1.8.0
- src/angular/package.json version is 1.8.0
- src/angular/package-lock.json version is 1.8.0
- src/angular/package-lock.json packages[""].version is 1.8.0
$ grep -n '"version"' package-lock.json | head -3
3:  "version": "1.8.0",
8:      "version": "1.8.0",
14:      "version": "3.2.6",
$ grep -n '^version' src/python/pyproject.toml
7:version = "1.8.0"
47:version = "1.8.0"
```

### Dependabot re-check before push (D-04)

Observed 2026-10-28, immediately before pushing `release/1.8.0`:

```
$ gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '[.[]|select(.state=="open")]|length'
9
$ gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '[.[]|select(.state=="open")]|sort_by(.number)|.[]|{number,package:.dependency.package.name,severity:.security_advisory.severity}'
94 @modelcontextprotocol/server medium
96 @modelcontextprotocol/server high
97 follow-redirects high
98 follow-redirects high
99 vite medium
100 vite high
101 vite medium
103 vite low
104 vite medium
$ gh pr list --author app/dependabot --json number,title,createdAt
#141 mkdocs-material 9.7.7->9.8.0, #138 follow-redirects, #136 certifi, #135 vite,
#131 npm_and_yarn group (23 updates), #130 @modelcontextprotocol/server + @angular/cli,
#125 testfixtures, #117 puppeteer
```

**Expected:** the same 9 alerts and 8 PRs from the 126-01 snapshot (they close only after the
merge to `main`, not on this release branch). **Observed:** identical alert numbers/packages and
identical PR numbers/titles to the 126-01 snapshot. No NEW alert and no NEW PR appeared since
126-01. D-04 not triggered; nothing additional rolled in.

**Note on `git push`'s banner:** the `git push -u origin release/1.8.0` output included GitHub's
standard advisory banner ("GitHub found 10 vulnerabilities on thejuran/seedsyncarr's default
branch (1 critical, 4 high, 4 moderate, 1 low)"). This banner is a cached, repo-wide dependency-
graph summary and does not match the live Dependabot alerts API output above (9 open alerts, 0
critical) queried immediately before and after the push. Per this project's established pattern
(RESEARCH.md "Don't Hand-Roll": the alerts API is ground truth, not a banner/audit tool), the `gh
api .../dependabot/alerts` query is authoritative; it was re-run after the push with the identical
9-alert result. No new alert was found by direct inspection.

### Merge check

```
$ git log origin/main..release/1.8.0 --oneline
```
Matches the planning commits from `main` (phase-126 context/research/plan docs) plus the
126-01/126-02/126-03 commits — confirmed before pushing.

### CI

Head tested: the full `release/1.8.0` branch head after the Task 1/2 commits (`f71b3e2`) and
through the evidence commit below. Branch pushed with `git push -u origin release/1.8.0`. PR
[#142](https://github.com/thejuran/seedsyncarr/pull/142) opened into `main`
(`gh pr create --base main --head release/1.8.0 --title "Release 1.8.0 — reliability" --body-file
<scratchpad>/pr-body-126.md`, body = `release-notes.md` with `{{VERSION}}` replaced by `1.8.0`
plus the Claude Code attribution line).

- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/40765512411 — conclusion
  `success` (`gh run watch 40765512411 --exit-status` exited 0).
- **CodeQL run:** https://github.com/thejuran/seedsyncarr/actions/runs/40765508739 — conclusion
  `success` (`Analyze (actions)`, `Analyze (javascript-typescript)`, `Analyze (python)` all `pass`
  per `gh pr checks 142`).

Per-job conclusions (`gh run view 40765512411 --json jobs --jq '.jobs[]|{name,conclusion}'`):

| Job | Conclusion |
|-----|------------|
| Lint (Python) | success |
| Release metadata verifier tests | success |
| Lint (Angular) | success |
| Verify release metadata | success |
| Python unit tests | success |
| Angular unit tests | success |
| Verify Python package | success |
| Build Docker Image | success |
| End-to-end tests on Docker Image (amd64) | success |
| Publish Docker Image / Publish to PyPI / Publish Docker Image (:dev) / Publish Documentation / Publish GitHub Release | skipped (PR, not a tag push — expected) |

`gh pr checks 142` confirms no failing or pending check: every check is `pass` except the five
`skipping` publish jobs.

### e2e [chromium-token] proof (SEC-02 browser proof on this tree)

`gh run view 40765512411 --log --job 123094438859 | grep chromium-token`:

```
  ✓  53 [chromium-token] › tests/auth-token.spec.ts:47:9 › API token configured (SEC-02) › rejects /server/ requests without the token (147ms)
  ✓  54 [chromium-token] › tests/auth-token.spec.ts:55:9 › API token configured (SEC-02) › sends the token to /server/* but never to api.github.com (607ms)
  ✓  55 [chromium-token] › tests/auth-token.spec.ts:85:9 › API token configured (SEC-02) › authenticated write flow works with the token (580ms)
```

All three pass in a real Chromium instance against the CI-built staging image.

### Branch/tag safety check

```
$ gh pr view release/1.8.0 --json state,headRefName --jq '{state,headRefName}'
{"state":"OPEN","headRefName":"release/1.8.0"}
$ git ls-remote --heads origin main
123b26fcfd41247637435c0e9b501d1a252a8597	refs/heads/main
$ git tag -l v1.8.0
(empty)
$ git ls-remote --tags origin v1.8.0
(empty)
```

`origin/main` is unchanged from the SHA recorded at Phase 126 start (123b26f, the Phase 125 merge
commit). No `v1.8.0` tag exists locally or on the remote. Nothing merged, nothing tagged.

## Owner decision (Plan 126-04 Task 1, 2026-10-28)

Verbatim (2026-10-28): "approve"

Interpretation: approve publishing 1.8.0 **as drafted** — no changes to release notes, CHANGELOG,
SECURITY.md or the dependency set. Authorizes: merge PR #142 keeping history, pause wud, tag
`v1.8.0` (publishes the Docker image as `1.8.0` and `latest`, a GitHub release, and PyPI 1.8.0).
The pre-approval packet (readiness/CI/CodeQL status, CHANGELOG/release-notes verbatim, the D-05
dependency table with before/after alert counts, the 999.4 outcome, the SECURITY.md correction,
the sandbox check plan and its Radarr-depth limitation, the wud pause plan, and the irreversibility
notice) was assembled and presented in the prior session per 126-04-PLAN.md Task 1; this plan
resumes at Task 2 with the verbatim reply above. Not "hold" and not "approve-with-changes", so no
amendment commit and no release-date change were needed.

## Dependabot re-check at tag time (D-04) — pre-merge

Observed 2026-10-28T21:1x UTC, before `gh pr merge`:

```
$ gh api repos/thejuran/seedsyncarr/dependabot/alerts --paginate --jq '[.[]|select(.state=="open")]|length'
9
$ gh api repos/thejuran/seedsyncarr/dependabot/alerts --paginate --jq '[.[]|select(.state=="open")]|sort_by(.number)|.[]|{number,package:.dependency.package.name,severity:.security_advisory.severity}'
94 @modelcontextprotocol/server medium
96 @modelcontextprotocol/server high
97 follow-redirects high
98 follow-redirects high
99 vite medium
100 vite high
101 vite medium
103 vite low
104 vite medium
$ gh pr list --author app/dependabot --json number,title,createdAt   (8 PRs: #141, #138, #136, #135, #131, #130, #125, #117 — same as 126-01/126-03 snapshot)
```

Identical to the 126-01 and 126-03 snapshots: same 9 alert numbers/packages, same 8 PR
numbers/titles. No new runtime/shipped alert at this checkpoint. D-04 not triggered here —
proceeded to merge. (A new runtime alert appeared later, during the post-merge Dependabot
close-out poll below — see "Dependabot close-out (D-01) — STOP".)

## wud pause (D-15)

Before stopping, read-only:

```
$ ssh nas "sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}} {{.State.FinishedAt}}'"
running 2026-10-23T06:54:01.328839126Z
$ ssh nas "sudo /usr/local/bin/docker inspect wud --format '{{range .Config.Env}}{{println .}}{{end}}'" | cut -d= -f1 | grep -i trigger
WUD_TRIGGER_DOCKERCOMPOSE_LOCAL_DRYRUN
WUD_TRIGGER_DOCKERCOMPOSE_V5TEST_FILE
WUD_TRIGGER_DOCKERCOMPOSE_V5TEST_DRYRUN
WUD_TRIGGER_DOCKERCOMPOSE_LOCAL_PRUNE
WUD_TRIGGER_DOCKERCOMPOSE_LOCAL_FILE
WUD_TRIGGER_DOCKERCOMPOSE_V5TEST_PRUNE
$ ssh nas "sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Id}} {{.Config.Image}} {{.State.StartedAt}} {{.State.Status}}'"
2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e 2026-10-23T07:04:18.591254939Z running
```

Production fingerprint (pre-merge): container `2feb4073…`, image
`ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0…`, `StartedAt` `2026-10-23T07:04:18Z`, `running`.

```
$ ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose stop wud'
Container wud  Stopping
Container wud  Stopped
$ ssh nas "sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}} {{.State.FinishedAt}}'"
exited 2026-10-28T21:20:36.156826683Z
```

wud confirmed `exited`. Production `seedsyncarr` was not touched by this step.

## Merge and tag

`gh pr view release/1.8.0 --json state,mergeable,mergeStateStatus` before merge: `OPEN`,
`MERGEABLE`, `CLEAN`. `gh pr checks release/1.8.0`: all 15 non-skip checks `pass` (8 CI gate jobs +
CodeQL × 3 languages + 3 duplicate-named jobs already counted above), 5 publish jobs correctly
`skipping` on a PR.

```
$ gh pr merge 142 --merge --subject "Merge 1.8.0 release (#142)"
$ gh pr view 142 --json state,mergeCommit,mergedAt
{"mergeCommit":"0583fc2024bea0d9fccf1919a8d77064b81bee28","mergedAt":"2026-10-28T21:20:48Z","state":"MERGED"}
$ git log -1 --format=%P 0583fc2024bea0d9fccf1919a8d77064b81bee28
123b26fcfd41247637435c0e9b501d1a252a8597 8d949eaea6c496f15597164a241e5b72061dc519
```

Two parents (`123b26f` previous `origin/main`, `8d949eae` the release head) — merge commit, history
kept, per D-14. `git checkout main && git pull --ff-only`: local `main` (`36867467`, confirmed an
ancestor of the merge commit via `git merge-base --is-ancestor`) fast-forwarded cleanly to
`0583fc20`. The local-only `126-03` plan-completion commit `e9e84660` (SUMMARY.md + STATE/ROADMAP
updates, committed after PR #142's evidence push and never pushed, per 126-03-SUMMARY.md's own
"Plan metadata: this SUMMARY.md commit (next)" note) was cherry-picked cleanly onto the new `main`
(`d79be69c`) so the 126-03 plan-completion record is not orphaned off history; its diff base
(`8d949eae`) matched `main`'s post-merge tree for the touched files exactly, so the cherry-pick had
zero conflicts. **Tag not yet pushed** — see the stop below.

## Dependabot close-out (D-01) — STOPPED: new runtime alert found (D-04)

Poll 1, immediately after the merge (2026-10-28T21:22:17Z):

```
$ gh api repos/thejuran/seedsyncarr/dependabot/alerts --paginate --jq '[.[]|select(.state=="open")]|length'
2
```

Down from 9 (expected, as GitHub's dependency-graph re-scan of `main` picked up the merged
roll-ins), but not yet 0. Detail:

```
$ gh api repos/thejuran/seedsyncarr/dependabot/alerts --paginate --jq '[.[]|select(.state=="open")]|sort_by(.number)|.[]|{number,package:.dependency.package.name,scope:.dependency.scope,severity:.security_advisory.severity,ghsa:.security_advisory.ghsa_id}'
{"number":106,"package":"qs","scope":"development","severity":"medium","ghsa":"GHSA-6pq8-jhm2-2vcw"}
{"number":107,"package":"setuptools","scope":"runtime","severity":"low","ghsa":"GHSA-xmj3-9gf7-h52w"}
```

Both `created_at: 2026-10-28T21:21:5{4,5}Z` — brand new, not part of the 126-01/126-03/pre-merge
9-alert snapshot (vite ×5, follow-redirects ×2, `@modelcontextprotocol/server` ×2, all now closed
by the merge). Poll 2 at `2026-10-28T21:24:25Z` (2 min later): identical, still 2, stable (not a
mid-scan transient).

**#106 `qs` (CVE-2026-110816, medium, `qs.stringify({arrayFormat:'comma'})` uncaught `TypeError`
DoS)** — `scope: development`, manifest `src/angular/package-lock.json`, pulled in transitively via
`karma` (same dev-only test-tooling path as the residual `body-parser`/`qs` `npm audit` findings
already recorded in 126-01-EVIDENCE.md's "npm audit" section). Published 2026-10-27, one day before
this snapshot — newly indexed by GitHub, not newly introduced by this release. Per the plan's D-04
language, a non-runtime one is "recorded and left open", not a stop trigger by itself.

**#107 `setuptools` (GHSA-xmj3-9gf7-h52w, low, Windows-only legacy-wheel `install_as_egg` path
-traversal via `namespace_packages.txt`)** — `scope: runtime`, manifest `src/python/poetry.lock`,
`relationship: transitive`, locked at `83.0.0` (vulnerable range `>=38.2.2,<84.1.0`; fixed at
`84.1.0`). Confirmed genuinely shipped, not just a build-time artifact: `paste` (a direct `main`
dependency per `pyproject.toml`) declares `setuptools = "*"` in its own `[package.dependencies]`
(`src/python/poetry.lock`), and the Dockerfile's runtime stage runs
`poetry install --only main` (`src/docker/build/docker-image/Dockerfile`), which installs the
`main` group — `setuptools` is tagged `groups = ["main", "dev"]`, so it lands in the running
container's site-packages. Published 2026-10-23, five days before this snapshot and one day
before the 126-01 snapshot — it did not exist as an advisory when 126-01/126-03 took their
snapshots; this is the first point in the phase it could have been seen.

Reachability assessment (not a decision, informational only): the vulnerable code path is
`setuptools.wheel.Wheel(...).install_as_egg()`'s legacy-wheel installer, exploitable only on
**Windows** (the advisory's PoC path-joins an absolute Windows drive-qualified path) and only when
installing an attacker-crafted wheel via that legacy path. SeedSyncarr's runtime image is
`python:3.11-slim` (Linux) and never installs wheels at runtime (the Dockerfile installs
dependencies only at build time via `poetry install --only main`; the running container doesn't
invoke pip/setuptools wheel installation at all). `reachability.verdict` from GitHub's own API is
`"disabled"` (undetermined), not `"reachable"`. This is evidence for the owner's judgment, not a
basis for the executor to roll in or defer unilaterally.

**This is exactly the D-04 condition** ("If a NEW runtime/shipped security alert appears between
this review and the tag push, raise it to the owner. Don't add it silently") and the plan's Task 2
step 3/6 stop rule ("If any open alert is on a runtime/shipped dependency not addressed by 1.8.0,
STOP: record it and return to the owner (roll in or defer); do not proceed" / "a security/runtime
one follows the D-04 stop rule"). **Stopping here, before any tag push.** No tag has been created
or pushed; GHCR/PyPI/GitHub-release publication has not started. The merge (PR #142 → `main`) and
the wud pause already happened under the Task 1 "approve" authorization and are not rolled back
(merging is not itself irreversible in the same way tagging/publishing is, and wud staying stopped
is safe); only the tag push and everything downstream of it are held for this decision.

### Original 8 rolled-in PRs — mechanical close-out (independent of the stop above)

This part of D-01 does not depend on the owner's setuptools/qs decision (it only confirms the
already-merged, already-CI-verified roll-ins from 126-01 are reflected as closed PRs), so it was
completed now rather than left pending:

```
$ for n in 136 141 125 117 135 138 130 131; do gh pr view $n --json state --jq .state; done
(before closing) 136 OPEN, 141 CLOSED, 125 OPEN, 117 CLOSED, 135 OPEN, 138 CLOSED-by-dependabot?, 130 CLOSED, 131 CLOSED
```

4 auto-closed by Dependabot itself within ~5 minutes of the merge (#141 mkdocs-material, #117
puppeteer, #130 `@modelcontextprotocol/server`+`@angular/cli`, #131 npm_and_yarn group). 4 did not
auto-close within that window; confirmed each one's resolved version on `main` meets or exceeds its
PR's target before closing manually:

| PR | Package | Target | Resolved on main | Meets |
|----|---------|--------|-------------------|-------|
| #136 | certifi | 2026.10.19 | 2026.10.23 | Yes (exceeds) |
| #125 | testfixtures | 12.4.0 | 12.4.0 | Yes |
| #135 | vite | 7.3.7 | 7.3.7 | Yes |
| #138 | follow-redirects | 1.16.2 | 1.16.2 | Yes |

```
$ gh pr close 136 --comment "Rolled into 1.8.0 via #142 (resolved version on main is >= this PR's target)."
$ gh pr close 125 --comment "Rolled into 1.8.0 via #142 (resolved version on main is >= this PR's target)."
$ gh pr close 135 --comment "Rolled into 1.8.0 via #142 (resolved version on main is >= this PR's target)."
$ gh pr close 138 --comment "Rolled into 1.8.0 via #142 (resolved version on main is >= this PR's target)."
```

Final states, all 8: #136 CLOSED, #141 CLOSED, #125 CLOSED, #117 CLOSED, #135 CLOSED, #138 CLOSED,
#130 CLOSED, #131 CLOSED. All eight original rolled-in PRs are closed. The only remaining blocker
to tagging is the owner's decision on alerts #106 (qs) and #107 (setuptools), above.

### Status at end of this session

- PR #142 **merged** to `main` (merge commit `0583fc2024bea0d9fccf1919a8d77064b81bee28`, history kept)
- wud **stopped** (`exited`), production **unchanged** (`seedsyncarr` still `2feb4073…` on `:1.7.6@sha256:da6196e0…`)
- All 8 originally-tracked Dependabot PRs **closed**
- Open Dependabot alerts: **2** (both new since the 126-03 snapshot — #106 `qs` dev-scope, #107
  `setuptools` runtime-scope) — **not 0**, blocking the tag per D-01/D-04
- **No `v1.8.0` tag created or pushed.** Nothing published to GHCR/PyPI/GitHub Releases.
- Awaiting owner decision: (a) roll in a `setuptools` bump to >=84.1.0 before tagging (small,
  mechanical lockfile change, re-run CI, then resume this plan), (b) defer both alerts (accepted as
  a release-notes-free known issue, given setuptools' low severity and the Windows-only/no-runtime-
  wheel-install reachability gap, with `qs` already following the existing dev-only-residual
  pattern) and proceed straight to tagging, or (c) hold entirely.

## Owner decision on #106/#107 (D-04 follow-up, 2026-10-28)

Verbatim: **"1"** — interpretation: option (a), "Fix both, then tag". Authorizes a small follow-up
PR that bumps `setuptools` to >=84.1.0 and `qs` to >=6.16.1 on a new branch off `origin/main`,
merged before the tag is pushed.

## Follow-up dependency fix: setuptools + qs (D-04, pre-tag)

**Branch:** `release/1.8.0-deps`, created from `origin/main` at the PR #142 merge commit
(`0583fc2024bea0d9fccf1919a8d77064b81bee28`).

**setuptools (#107):** `cd src/python && poetry update setuptools` -> `83.0.0` -> `84.2.1`
(exceeds the `84.1.0` fix target). `git diff --stat` shows only `src/python/poetry.lock` (1 file,
5 insertions, 5 deletions). `setuptools` confirmed NOT added to `pyproject.toml` as a direct
dependency (`grep -n setuptools src/python/pyproject.toml` empty) — it remains transitive via
`paste`.

**qs (#106):** `cd src/angular && npm update qs` -> `6.16.0` -> `6.16.2` (exceeds the `6.16.1` fix
target). `npm ls qs`: `karma@6.4.4 -> body-parser@1.20.8 -> qs@6.16.2` (only instance). `git diff
--stat` shows only `src/angular/package-lock.json` (1 file, 3 insertions, 3 deletions).

### Targeted checks (both bumps, before commit)

```
$ cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider \
    --ignore=tests/unittests/test_ssh/test_sshcp.py \
    --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py \
    --ignore=tests/unittests/test_system/test_scanner.py \
    --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py
1945 passed, 2 warnings, 106 subtests passed in 47.05s
```
Matches the 126-01/126-03 baseline exactly (same pre-existing 2 warnings).

```
$ <scratch>/ruff/bin/ruff --version
ruff 0.15.22
$ <scratch>/ruff/bin/ruff check src/python/
All checks passed!
```

```
$ cd src/python && poetry check
Warning: [project.name] and [tool.poetry.name] are both set. The latter will be ignored.
Warning: [project.version] and [tool.poetry.version] are both set. The latter will be ignored.
Warning: [project.description] and [tool.poetry.description] are both set. The latter will be ignored.
Warning: [project.authors] and [tool.poetry.authors] are both set. The latter will be ignored.
EXIT=0
```
Same pre-existing dual `[project]`/`[tool.poetry]` metadata warnings as every prior release check
(not introduced by this change); exit 0.

```
$ cd src/python && rm -rf dist && <scratch>/pkg/bin/python -m build -q
Successfully built seedsyncarr-1.8.0.tar.gz and seedsyncarr-1.8.0-py3-none-any.whl
$ <scratch>/pkg/bin/twine check dist/*
Checking dist/seedsyncarr-1.8.0-py3-none-any.whl: PASSED with warnings
  WARNING long_description_content_type missing. defaulting to text/x-rst.
  WARNING long_description missing.
Checking dist/seedsyncarr-1.8.0.tar.gz: PASSED with warnings
  (same two warnings)
```
Same two pre-existing, non-blocking warnings recorded in every prior release's evidence.

```
$ cd src/angular && npx tsc --noEmit -p src/tsconfig.spec.json
(0 errors, no output)
$ npm run lint
> eslint "src/**/*.ts" --max-warnings 0
(0 warnings)
$ make run-tests-angular   (dockerized ChromeHeadlessCI)
Chrome Headless 156.0.0.0 (Linux 0.0.0): Executed 657 of 657 SUCCESS (2.355 secs / 2.078 secs)
TOTAL: 657 SUCCESS
Statements   : 84.62% ( 1805/2133 )
Branches     : 70.49% ( 509/722 )
Functions    : 81.56% ( 447/548 )
Lines        : 85.44% ( 1738/2034 )
```
Identical pass count and coverage to the 126-01 baseline; container exited 0; all four metrics
above the enforced floors (83/68/79/83).

```
$ npx ng build
Application bundle generation complete. [3.817 seconds]
Initial total: 1.15 MB raw / 213.89 kB estimated transfer
```
Matches the 126-01 baseline bundle size (213.88 kB then, 213.89 kB now — rounding only).

No break on either bump; D-02 stop not triggered.

**Commit:** `eaaca5e5` — `chore(deps): setuptools 84.1.0, qs 6.16.1 for 1.8.0` (2 files: `src/python/poetry.lock`, `src/angular/package-lock.json`, no source files touched).

### PR #143 and CI

`git push -u origin release/1.8.0-deps`; opened
[PR #143](https://github.com/thejuran/seedsyncarr/pull/143) into `main`, title "chore(deps):
setuptools 84.1.0, qs 6.16.1 for 1.8.0", body ending in the Claude Code attribution line.

**CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/40773098908 — conclusion
`success`. **CodeQL run:** https://github.com/thejuran/seedsyncarr/actions/runs/40773095375 —
conclusion `success` (`Analyze (actions)`, `Analyze (javascript-typescript)`, `Analyze (python)`
all `pass`).

Per-job conclusions:

| Job | Conclusion |
|-----|------------|
| Lint (Python) | success |
| Lint (Angular) | success |
| Release metadata verifier tests | success |
| Verify release metadata | success |
| Verify Python package | success |
| Angular unit tests | success |
| Python unit tests | success |
| Build Docker Image | success |
| End-to-end tests on Docker Image (amd64) | success |
| CodeQL (actions / javascript-typescript / python) | success |
| Publish Docker Image / Publish to PyPI / Publish Docker Image (:dev) / Publish Documentation / Publish GitHub Release | skipping (PR, not a tag push — expected) |

`gh pr view 143 --json state,mergeable,mergeStateStatus`: `OPEN`, `MERGEABLE`, `CLEAN`. Merged with
history kept: `gh pr merge 143 --merge --subject "Merge dependency fixes for 1.8.0 (#143)"`.

```
$ gh pr view 143 --json state,mergeCommit,mergedAt
{"mergeCommit":{"oid":"098ed81bbe34106646fee2b260c872c48b95ce00"},"mergedAt":"2026-10-28T21:51:24Z","state":"MERGED"}
$ git log -1 --format=%P 098ed81bbe34106646fee2b260c872c48b95ce00
0583fc2024bea0d9fccf1919a8d77064b81bee28 eaaca5e5bae39a2285f59db92b7b66d646e39ed8
```
Two parents (previous `origin/main` `0583fc20`, the `release/1.8.0-deps` head `eaaca5e5`) — merge
commit, history kept.

### Local main rebase

The local-only `126-03`/`126-04` docs commits (`d79be69c`, `c8723ec0`) were rebased from the old
`origin/main` (`0583fc20`) onto the new `origin/main` (`098ed81b`) — clean, no conflicts (they
touch only `.planning/`):

```
$ git checkout main && git rebase origin/main
Successfully rebased and updated refs/heads/main.
$ git log --oneline -3
3e798401 docs(126-04): record owner approval, merge, Dependabot close-out; STOP before tag (D-04)
539822c4 docs(126-03): complete release 1.8.0 gate plan
098ed81b Merge dependency fixes for 1.8.0 (#143)
$ git diff --stat origin/main main
 .planning/ROADMAP.md                               |   6 +-
 .planning/STATE.md                                 |  13 +-
 .../phases/126-release-1-8-0/126-03-SUMMARY.md     | 156 ++++++++++++++++
 .../phases/126-release-1-8-0/126-REL-EVIDENCE.md   | 205 +++++++++++++++++++++
 4 files changed, 371 insertions(+), 9 deletions(-)
```
Only `.planning/` files; local `main` not pushed (`ahead 2` of `origin/main`), per the plan's
instruction that these docs commits ride the owner's next planning push, not this release.

## Dependabot close-out (D-01) — resumed, 0 reached

Poll after the #143 merge (GitHub's re-scan of `main`):

```
poll 1 at 2026-10-28T21:52:10Z: open=2
poll 2 at 2026-10-28T21:54:10Z: open=0
```
Confirmed stable (not a mid-scan transient) with two further direct checks 15s apart, both `open=0`.
**Open Dependabot alerts: 0.** D-01 satisfied.

`node scripts/verify-release-metadata.mjs 1.8.0` re-run on the rebased local `main` (content
identical to `098ed81b` for all non-`.planning` files, confirmed by the rebase diff-stat above):
passes, all 6 checks.

## Tag (D-14)

Pre-tag re-check: production fingerprint unchanged (`2feb4073…` on `:1.7.6@sha256:da6196e0…`,
`running`); wud `exited`.

```
$ git tag -a v1.8.0 -m "SeedSyncarr 1.8.0 — reliability release" 098ed81bbe34106646fee2b260c872c48b95ce00
$ git cat-file -t v1.8.0
tag
$ git rev-parse v1.8.0^{commit}
098ed81bbe34106646fee2b260c872c48b95ce00
$ git push origin v1.8.0
 * [new tag]           v1.8.0 -> v1.8.0
```
Annotated tag on the merge commit of PR #143 (which itself sits on the merge commit of PR #142).

