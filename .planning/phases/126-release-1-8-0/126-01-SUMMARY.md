---
phase: 126-release-1-8-0
plan: 01
subsystem: deps
tags: [release, dependabot, lockfile-regeneration, supply-chain, angular, python, 999.4]

# Dependency graph
requires:
  - phase: 125-lan-connection-tests
    provides: merged main with all of 121-125 (PR #140 merged 2026-10-28)
provides:
  - release/1.8.0 local branch with every open Dependabot PR rolled in via lockfile regeneration
  - 126-REL-EVIDENCE.md (Dependabot snapshot, per-group roll-in record, npm audit, 999.4 recheck, owner dependency table draft)
affects: [126-02, 126-03, 126-04, 126-05, 126-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lockfile regeneration (poetry update <names> / npm install + npm update <names>) instead of cherry-picking overlapping Dependabot PR commits"
    - "Isolate a major-version type-only bump (@types/jasmine 6->7) and verify it alone before combining with the rest of a dependency group"

key-files:
  created:
    - .planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md
  modified:
    - src/python/poetry.lock
    - package.json
    - package-lock.json
    - src/angular/package.json
    - src/angular/package-lock.json

key-decisions:
  - "Evidence-file updates committed separately from each dependency bump (docs(126-01) commits) so every chore(126-01) commit stays scoped to exactly its manifest/lockfile files"
  - "2 residual npm audit findings (body-parser, qs, both pulled in transitively by dev-only karma) left unfixed as a non-D-01 owner item per the plan's 'do not chase beyond the D-01 list' instruction"

patterns-established:
  - "Lockfile regeneration over cherry-pick for overlapping Dependabot PRs on the same manifest"

requirements-completed: [REL-05]

# Metrics
duration: 12min
completed: 2026-10-28
---

# Phase 126 Plan 01: Dependabot Roll-In Evidence Summary

**All 8 open Dependabot PRs rolled into `release/1.8.0` via lockfile regeneration across 3 commit groups (Python, root puppeteer, isolated @types/jasmine, Angular group), closing all 9 open GitHub Dependabot alerts with every targeted suite green and no D-02 stop triggered.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-10-28T19:51:36Z
- **Completed:** 2026-10-28T20:03:30Z
- **Tasks:** 3 completed
- **Files modified:** 6 (5 manifest/lockfiles + 1 evidence doc)

## Accomplishments

- Snapshotted the Dependabot state (9 open alerts, 8 open PRs) at the start and confirmed it matched the plan's interfaces exactly — no new runtime alert, no new PR (D-04 not triggered)
- Rolled in certifi (2026.1.4 -> 2026.10.23), mkdocs-material (9.7.7 -> 9.8.0), testfixtures (12.3.0 -> 12.4.0) via `poetry update`; Python quick suite 1945 passed, whole-tree ruff 0.15.22 clean, mkdocs docs build succeeded, ruff's `poetry.lock` block untouched
- Rolled in puppeteer (25.11.0 -> 25.16.0) at the repo root; `npm run test:release-metadata` 21/21 passed, root `version` field confirmed still `1.7.6`
- Verified `@types/jasmine` 6->7 in isolation before combining with the rest of #131: 0 TypeScript errors, 0 lint warnings, dockerized Karma 657/657 SUCCESS with coverage above the enforced floors; `jasmine-core` confirmed unchanged at `^6.3.0`
- Rolled in the rest of the Angular `npm_and_yarn` group (#131) plus the three security-alert PRs (#130, #135, #138): every target version met or exceeded (vite 7.3.7, follow-redirects 1.16.2, @modelcontextprotocol/server 2.3.1, @angular/cli 22.2.5, @angular/build 22.2.5, @angular/cdk 22.2.5, @playwright/test 1.64.1); lint, dockerized Karma (657/657) and `ng build` all green
- `npm audit --audit-level=low` run and recorded: 2 residual dev-only findings (body-parser, qs, both via karma's dependency chain) with no corresponding GitHub alert — recorded as a non-D-01 owner item, not chased
- 999.4 (braces/karma) rechecked: `braces@3.0.3` unchanged from `main`, zero Dependabot alerts in any state for braces/karma/chokidar, PR #128 closed — outcome "No fix needed"
- Drafted the owner dependency table (D-05) with all 8 PRs, what each touches, runtime/dev scope, and which alerts each closes, for the Plan 04 pre-tag checkpoint

## Task Commits

Each roll-in group was committed atomically, with evidence-file updates as separate `docs(126-01)` commits so the `chore(126-01)` commits stay scoped to exactly their manifest/lockfile files:

1. **Task 1a: Python roll-in (#136, #141, #125)** - `de888a9c` (chore)
2. **Task 1b: Root puppeteer roll-in (#117)** - `e02884f7` (chore)
   - evidence (snapshot + both Task 1 roll-ins) - `d787afc6` (docs)
3. **Task 2: @types/jasmine 7 in isolation (#131 part)** - `3605536b` (chore)
   - evidence - `72b2d5d6` (docs)
4. **Task 3: Angular group + security fixes (#131, #130, #135, #138)** - `439e20fb` (chore)
   - evidence (Angular roll-in, npm audit, 999.4, owner table) - `613a25ce` (docs)

**Plan metadata:** this SUMMARY.md commit (next)

_No TDD tasks in this plan (dependency roll-in, not feature code); no test→feat→refactor cycle applies._

## Files Created/Modified

- `src/python/poetry.lock` - certifi, mkdocs-material, testfixtures bumped to target versions; ruff block untouched
- `package.json` - root `puppeteer` devDependency `^25.11.0` -> `^25.16.0`
- `package-lock.json` - root lockfile regenerated for puppeteer
- `src/angular/package.json` - `@types/jasmine` 6->7, full `npm_and_yarn` group (#131) range changes, `@angular/cli` ->22.2.4 (#130), `overrides.vite` ->7.3.7 (#135)
- `src/angular/package-lock.json` - Angular lockfile regenerated for the full group plus `@modelcontextprotocol/server` and `follow-redirects` lockfile-only bumps (#130, #138)
- `.planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md` - created; full roll-in record (snapshot, per-group evidence, npm audit, 999.4 recheck, owner dependency table draft)

## Decisions Made

- Evidence-file writes were split into their own `docs(126-01)` commits, separate from each `chore(126-01)` dependency bump commit, so every bump commit's `git show --stat` lists only its manifest/lockfile files (matches the plan's acceptance criteria for commit scoping) while still producing exactly 4 `chore(126-01)` commits total across the plan
- The 2 residual `npm audit` findings (body-parser, qs) are left as a recorded owner item rather than fixed, because neither has a corresponding GitHub Dependabot alert and both are pulled in transitively by `karma` (not part of any PR in the D-01 list); fixing them would require bumping `karma` itself, which is out of this plan's scope per "do not chase them beyond the D-01 list"

## Deviations from Plan

None - plan executed exactly as written. All three tasks' automated `<verify>` commands passed (T1_OK, T2_OK, T3_OK) with real command output observed, not assumed.

**Environment note (non-deviation, no product impact):** this session's interactive shell aliases `grep` to a `ugrep -G` wrapper that treats a mid-pattern `^` (e.g. in `"^25.16.0"`) as an anchor rather than a literal character, causing some of the plan's literal-string `grep` verify snippets to false-negative when run through that wrapper. Re-running the identical checks through `/usr/bin/grep` (true BSD grep) confirmed every verify command's real exit code was 0 with the expected output (T1_OK/T2_OK/T3_OK). No file content was changed because of this; it is purely a shell tooling quirk local to this interactive session, not something a plain `grep` (as CI or a non-aliased shell would run it) exhibits.

## Issues Encountered

None. Every targeted check (Python suite, ruff, mkdocs build, release-metadata test, tsc, eslint, dockerized Karma x2, `ng build`, `npm audit`) ran to completion with real pass/fail output; no D-02 stop condition was triggered.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `release/1.8.0` (local only, not pushed) now carries all 8 Dependabot PRs' target versions across the Python and Angular/root ecosystems, with every targeted suite green
- `126-REL-EVIDENCE.md` holds the full roll-in record, the npm audit owner item, the 999.4 "no fix needed" outcome, and a draft owner dependency table ready for Plan 04's pre-tag checkpoint
- Remaining Plan 01 scope (REL-05) is fully done: no D-02 stop packet to carry forward
- Open items for later plans: the 2 residual `npm audit` findings (body-parser/qs via karma) should be surfaced to the owner alongside the dependency table, not silently dropped

---
*Phase: 126-release-1-8-0*
*Completed: 2026-10-28*

## Self-Check: PASSED

- FOUND: .planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md
- FOUND: .planning/phases/126-release-1-8-0/126-01-SUMMARY.md
- FOUND: de888a9c (chore: Python roll-in)
- FOUND: e02884f7 (chore: puppeteer roll-in)
- FOUND: d787afc6 (docs: evidence for Task 1)
- FOUND: 3605536b (chore: @types/jasmine isolated)
- FOUND: 72b2d5d6 (docs: evidence for Task 2)
- FOUND: 439e20fb (chore: Angular group roll-in)
- FOUND: 613a25ce (docs: evidence for Task 3)
