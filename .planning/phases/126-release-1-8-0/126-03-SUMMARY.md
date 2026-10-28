---
phase: 126-release-1-8-0
plan: 03
subsystem: release-ops
tags: [release, version-bump, changelog, release-notes, security-md, rollback-runbook, ci-gate, release-pr]

# Dependency graph
requires:
  - phase: 126-01
    provides: release/1.8.0 branch with every open Dependabot PR rolled in
  - phase: 126-02
    provides: sandbox smoke harness scripts (used by the next plan, not this one)
provides:
  - 1.8.0 version bump across every site 1.7.6 set (package.json, both lockfiles,
    src/angular/package.json, src/python/pyproject.toml)
  - CHANGELOG.md [1.8.0] entry (Security/Changed/Fixed order) and a fully rewritten
    release-notes.md with a 1.7.6 rollback runbook
  - SECURITY.md IP-resolution guard bullet corrected to describe Phase 125's actual
    allow-private/refuse-link-local behavior
  - release/1.8.0 pushed; PR #142 open into main with all 8 CI gate jobs and CodeQL
    green on the final commit, including 3/3 [chromium-token] e2e passes
  - 126-REL-EVIDENCE.md release-gate section (suite, ruff, packaging, metadata,
    pre-push Dependabot recheck, CI/CodeQL URLs, chromium-token lines)
affects: [126-04, 126-05, 126-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fact-check version-exposure claims against git history (git show <tag>:<path>) before writing a security disclosure, rather than trusting a carried-forward STATE.md note"
    - "Verify a rollback caveat against git ancestry (git merge-base --is-ancestor) instead of assuming an old release note's caution still applies"

key-files:
  created:
    - .planning/phases/126-release-1-8-0/126-03-SUMMARY.md
  modified:
    - package.json
    - package-lock.json
    - src/angular/package.json
    - src/angular/package-lock.json
    - src/python/pyproject.toml
    - CHANGELOG.md
    - release-notes.md
    - SECURITY.md
    - .planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md

key-decisions:
  - "D-08 fact check: git show v1.0.0:.../auth.interceptor.ts confirms the unconditional token-attach logic was present at the v1.0.0 tag itself, so the CHANGELOG/release-notes wording 'Versions 1.0.0 through 1.7.6' is accurate as written, with no need for the plan's 'X and earlier' fallback phrasing"
  - "D-16 % rollback caveat: confirmed via git merge-base --is-ancestor that 119.1-06's %%-escape fix (GREEN commit 8938695) is an ancestor of v1.7.6, and common/config.py is byte-identical between v1.7.6 and main, so 1.7.6 and 1.8.0 handle a %-containing secret identically — no extra rollback step needed for %, stated as a plain fact instead of an action step"
  - "Used a scratch venv (pip install build twine) to run the packaging gate locally, mirroring CI's own 'pip install build twine' step exactly rather than adding build/twine as poetry dev dependencies"
  - "Did not re-commit/re-push a third evidence-file update documenting the evidence-commit's own triggered CI run (which would recursively trigger a fourth run); instead recorded that second run's green result in this SUMMARY, matching the 119.1-REL04 precedent of recording a re-triggered run's result in the plan SUMMARY rather than looping further evidence commits"

patterns-established:
  - "Fact-check security-disclosure version ranges against git tag history before writing, not from a carried-forward note"

requirements-completed: []  # REL-05/REL-06 contributed to but not checked off in REQUIREMENTS.md yet — see Decisions Made

# Metrics
duration: 38min
completed: 2026-10-28
---

# Phase 126 Plan 03: Release 1.8.0 Gate (version bump, notes, PR, CI/CodeQL green) Summary

**1.8.0 version bump across all 7 metadata sites, CHANGELOG/release-notes/SECURITY.md finalized with a fact-checked token-exposure disclosure and a 1.7.6 rollback runbook, release/1.8.0 pushed and PR #142 opened with all 8 CI gate jobs plus CodeQL green (including 3/3 real-browser [chromium-token] passes) on the final commit — nothing merged or tagged.**

## Performance

- **Duration:** 38 min
- **Started:** 2026-10-28T20:33:00Z
- **Completed:** 2026-10-28T21:11:00Z
- **Tasks:** 3 completed
- **Files modified:** 9 (7 version/content files + 1 evidence doc, updated across 2 commits + 1 SUMMARY commit)

## Accomplishments

- Bumped 1.7.6 → 1.8.0 at all 7 version sites (`package.json`, root `package-lock.json` `.version` + `packages[""].version`, `src/angular/package.json`, `src/angular/package-lock.json` both fields, `src/python/pyproject.toml` `[project]` + `[tool.poetry]`); confirmed zero remaining `1.7.6` occurrences in any of the 5 files
- Finalized `CHANGELOG.md`'s `[Unreleased]` draft as `## [1.8.0] - 2026-10-28` in Security → Changed → Fixed order (D-07): kept the Phase 125 Security/Changed bullets verbatim, added the fact-checked Phase 121 token-exposure bullet (SEC-02), and added one Fixed line each for Phases 122 (LOG-01/LOG-02), 123 (LIFE-01/LIFE-02) and 124 (STRM-01/STRM-02); verified the `## [1.7.6]` entry and everything below it is untouched
- Fact-checked the Phase 121 exposure range directly against git history (`git show v1.0.0:src/angular/.../auth.interceptor.ts`) rather than trusting the carried-forward STATE.md note — confirmed the unconditional token-attach logic was present at the `v1.0.0` tag itself, so "Versions 1.0.0 through 1.7.6" is accurate
- Corrected `SECURITY.md`'s IP-resolution guard bullet (stale since Phase 125) to describe the actual allow-private/refuse-link-local `_validate_url` behavior, verified line-by-line against `src/python/web/handler/config.py`; diff is exactly one line removed, one added
- Fully rewrote `release-notes.md` for 1.8.0: lead paragraph, "What changed in 1.8.0" (Security facts first, then Changed, then Fixed), "Do this after updating" (Test Connection + optional token rotation), "Should you update?", "Before you upgrade", and a rollback runbook to 1.7.6 that drops the 1.7.6-era "rotate again" caution, states the `%`-in-secrets non-issue as a verified fact (not an unnecessary extra step), and documents the Test Connection container-name caveat on a 1.7.6 rollback
- Ran the full release gate: full host Python suite (1945 passed, 0 failed), whole-tree ruff 0.15.22 (`All checks passed!`), packaging (`seedsyncarr-1.8.0` wheel/sdist, `twine check` passed with warnings, `PACKAGE_OK`), and `node scripts/verify-release-metadata.mjs 1.8.0` (all 6 checks pass)
- Re-ran the Dependabot alert/PR query immediately before pushing (D-04): identical 9 open alerts and 8 open PRs to the 126-01 snapshot — no new runtime alert, nothing additional rolled in
- Pushed `release/1.8.0` and opened PR #142 into `main`; CI run green on all 8 gate jobs (publish jobs correctly skipped on a PR) plus CodeQL (`Analyze (actions)`, `Analyze (javascript-typescript)`, `Analyze (python)` all pass); grepped the e2e job log directly and confirmed the 3 `[chromium-token]` tests passing in a real Chromium instance
- Committed the release-gate evidence to `126-REL-EVIDENCE.md`, which (as expected) started a second CI run on the new PR head — also green on all 8 gate jobs and CodeQL, with the same 3 `[chromium-token]` lines reconfirmed
- Confirmed `origin/main` unchanged (still `123b26f`, the Phase 125 merge commit) and that no `v1.8.0` tag exists locally or remotely — nothing merged or tagged by this plan

## Task Commits

1. **Task 1: Version bump to 1.8.0, CHANGELOG [1.8.0], SECURITY.md correction** - `c171598a` (chore)
2. **Task 2: Rewrite release-notes.md for 1.8.0 with the rollback runbook to 1.7.6** - `f71b3e28` (docs)
3. **Task 3: Release gate evidence, push release branch, open the release PR, CI + CodeQL green** - `8d949eae` (docs)

**Plan metadata:** this SUMMARY.md commit (next)

_No TDD tasks in this plan (release-engineering metadata and gate evidence, not application behavior); no test→feat→refactor cycle applies._

## Files Created/Modified

- `package.json` - root version 1.7.6 → 1.8.0
- `package-lock.json` - root `.version` and `packages[""].version` 1.7.6 → 1.8.0
- `src/angular/package.json` - version 1.7.6 → 1.8.0
- `src/angular/package-lock.json` - `.version` and `packages[""].version` 1.7.6 → 1.8.0
- `src/python/pyproject.toml` - `[project]` and `[tool.poetry]` version 1.7.6 → 1.8.0
- `CHANGELOG.md` - `[Unreleased]` finalized as `[1.8.0] - 2026-10-28`, reordered Security/Changed/Fixed, Phase 121/122/123/124 facts added
- `release-notes.md` - fully rewritten for 1.8.0 with the 1.7.6 rollback runbook
- `SECURITY.md` - IP-resolution guard bullet corrected to match Phase 125's shipped behavior
- `.planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md` - D-08/D-16 fact-check records, full release-gate evidence (suite, ruff, packaging, metadata, Dependabot pre-push recheck, CI/CodeQL URLs, chromium-token lines, branch/tag safety check)

## Decisions Made

- D-08 and D-16 fact checks were run against git history directly (`git show v1.0.0:...`, `git merge-base --is-ancestor ...`) rather than trusting carried-forward prose in STATE.md/RESEARCH.md, per the plan's explicit instruction to verify before writing a security disclosure or rollback caveat
- Packaging tooling (`build`, `twine`) was installed into a throwaway scratch venv rather than added to `pyproject.toml`'s dev dependencies, mirroring CI's own `pip install build twine` step exactly and matching the 119.1-REL04 precedent of using a scratch venv for this gate
- The evidence-commit's own re-triggered CI run (40768065324) was verified green but its result was recorded in this SUMMARY rather than a third commit to `126-REL-EVIDENCE.md`, to avoid recursively triggering further CI runs on every evidence-documentation commit — matching 119.1-REL04's own documented precedent ("its result is recorded in 119.1-03-SUMMARY.md")
- Did NOT run `requirements mark-complete` for REL-05/REL-06 despite both appearing in this plan's frontmatter `requirements:` field: REL-05's own text requires the Dependabot review to hold "before the version bump/tag" (the tag push is Plan 04), and REL-06 requires 1.8.0 to be published/smoke-tested/deployed (Plans 04-06), none of which happened in this plan. REQUIREMENTS.md's REL-05/REL-06 checkboxes are left `[ ]` Pending, matching the precedent already set by 126-01 (which also listed `requirements: [REL-05]` in its PLAN frontmatter and `requirements-completed: [REL-05]` in its own SUMMARY, yet REQUIREMENTS.md's REL-05 checkbox is still unchecked today) — checking them off now would misrepresent not-yet-completed publish/smoke/deploy work as done

## Deviations from Plan

None - plan executed exactly as written. All three tasks' automated `<verify>` commands were run and their real output observed (T1_OK, T2_OK, T3_OK), not assumed.

**Second CI run (non-deviation, expected per the plan's own parenthetical):** committing `126-REL-EVIDENCE.md` triggered a second CI run (40768065324) on the PR head, as the plan anticipated ("record the final run if a new run was triggered; it must also be green"). That run was independently verified green on all 8 gate jobs plus CodeQL, with the same 3 `[chromium-token]` lines reconfirmed in its own job log — recorded above and in Accomplishments, not in a third evidence-file commit (see Decisions Made).

## Issues Encountered

None. Every gate command (pytest, ruff, build, twine, verify-python-package.py, verify-release-metadata.mjs, the Dependabot API queries, both CI runs, both e2e log greps) ran to completion with real output observed; no D-02 stop condition was triggered (no Dependabot update broke anything in this plan — that risk was already retired in 126-01).

## User Setup Required

None - no external service configuration required. The release PR was opened and watched to green entirely via `gh` CLI automation; no manual CI step was needed.

## Next Phase Readiness

- PR [#142](https://github.com/thejuran/seedsyncarr/pull/142) is open into `main`, head `8d949eae`, with every CI gate and CodeQL check green (verified twice, across two consecutive pushes) and no failing or pending check per `gh pr checks 142`
- `126-REL-EVIDENCE.md` carries the full release-gate record (suite, ruff, packaging, metadata, pre-push Dependabot recheck, CI run URLs, CodeQL run URL, the three `[chromium-token]` passing lines, and the branch/tag safety check) ready for the owner's pre-tag checkpoint
- `origin/main` is unchanged (`123b26f`) and no `v1.8.0` tag exists locally or remotely — the next plan's owner checkpoint (merge/tag) has a clean, fully-gated PR to review
- No blockers carried forward

---
*Phase: 126-release-1-8-0*
*Completed: 2026-10-28*

## Self-Check: PASSED

- FOUND: package.json
- FOUND: package-lock.json
- FOUND: src/angular/package.json
- FOUND: src/angular/package-lock.json
- FOUND: src/python/pyproject.toml
- FOUND: CHANGELOG.md
- FOUND: release-notes.md
- FOUND: SECURITY.md
- FOUND: .planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md
- FOUND: .planning/phases/126-release-1-8-0/126-03-SUMMARY.md
- FOUND: c171598a (chore: version bump, changelog, SECURITY.md)
- FOUND: f71b3e28 (docs: release-notes.md rewrite)
- FOUND: 8d949eae (docs: release gate evidence)
