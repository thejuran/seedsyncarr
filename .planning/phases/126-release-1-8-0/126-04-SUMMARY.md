---
phase: 126-release-1-8-0
plan: 04
subsystem: release
tags: [release, dependabot, merge, tag, ghcr, pypi, github-release, wud-pause, owner-checkpoint]

# Dependency graph
requires:
  - phase: 126-03
    provides: release/1.8.0 branch pushed, PR #142 open with CI + CodeQL green, version metadata bumped to 1.8.0
provides:
  - "1.8.0 published: GHCR :1.8.0/:latest (multi-arch), GitHub release, PyPI 1.8.0"
  - "RELEASE_DIGEST=sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 (amd64+arm64) cross-checked by two independent methods"
  - "PR #142 (1.8.0 release) and PR #143 (setuptools/qs fix) merged to main with history kept; 0 open Dependabot alerts; all 10 rolled-in/follow-up PRs closed"
  - "v1.8.0 annotated tag on PR #143's merge commit; tag CI all green incl. both e2e architectures and all five publish jobs"
affects: [126-05, 126-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-04 stop-and-ask: a new runtime/shipped Dependabot alert discovered post-merge, pre-tag halts the plan for an explicit owner decision before any tag is created"
    - "Lockfile-only follow-up PR on a fresh branch off origin/main for post-merge dependency fixes, rebasing local-only docs commits afterward rather than cherry-picking around them"

key-files:
  created:
    - .planning/phases/126-release-1-8-0/126-04-SUMMARY.md
  modified:
    - .planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md
    - src/python/poetry.lock
    - src/angular/package-lock.json

key-decisions:
  - "Owner verbatim 'approve' (Task 1) authorized merge/tag as drafted; owner verbatim '1' (D-04 follow-up) authorized fixing both post-merge alerts (#106 qs, #107 setuptools) before tagging, not deferring or holding"
  - "setuptools bumped via poetry update (83.0.0 -> 84.2.1, exceeds the 84.1.0 fix target) rather than pinned exactly, matching the project's existing lockfile-regeneration pattern from 126-01"
  - "qs bumped via npm update (6.16.0 -> 6.16.2, exceeds the 6.16.1 fix target), transitive via karma -> body-parser, no package.json change needed"
  - "local-only 126-03/126-04 docs commits rebased onto the new origin/main after PR #143 merged, rather than cherry-picked, since both commits touch only .planning/ with no conflicts"

patterns-established:
  - "Post-merge-pre-tag Dependabot re-scan can surface alerts invisible on the release branch (GitHub only re-scans on merge to the default branch); the D-04 gate exists specifically for this window"

requirements-completed: [REL-05, REL-06]

# Metrics
duration: ~40min (this continuation; Task 1 and the first half of Task 2 ran in a prior session)
completed: 2026-10-28
---

# Phase 126 Plan 04: Release 1.8.0 Publish (owner approval through tag/publish) Summary

**1.8.0 published to GHCR (multi-arch), GitHub Releases and PyPI after a mid-plan D-04 stop for two post-merge Dependabot alerts was resolved by a follow-up PR (setuptools 84.2.1, qs 6.16.2), with RELEASE_DIGEST cross-checked and 0 open Dependabot alerts.**

## Performance

- **Duration:** ~40 min for this continuation (resuming from the Task 2 D-04 stop through Task 3 completion); Task 1 (owner approval packet) and the first half of Task 2 (merge of PR #142, wud pause, original 8-PR close-out) ran in a prior session, recorded in `126-REL-EVIDENCE.md`
- **Started (this continuation):** 2026-10-28T21:30:00Z (approx.)
- **Completed:** 2026-10-28T22:09:20Z
- **Tasks:** 3 of 3 (Task 1 and Task 2's first half were already complete before this continuation began)
- **Files modified:** 3 (2 lockfiles + the evidence doc, plus this summary)

## Accomplishments

- Recorded the owner's verbatim D-04 follow-up decision ("1" = fix both newly-discovered alerts, then tag) in `126-REL-EVIDENCE.md`
- Created `release/1.8.0-deps` off `origin/main`, bumped `setuptools` 83.0.0 -> 84.2.1 (`poetry update setuptools`, exceeds the GHSA-xmj3-9gf7-h52w fix threshold of 84.1.0) and `qs` 6.16.0 -> 6.16.2 (`npm update qs`, exceeds the GHSA-6pq8-jhm2-2vcw fix threshold of 6.16.1), both lockfile-only changes with no source or manifest changes beyond the lock
- Ran the full targeted check suite on both bumps: Python suite 1945 passed (matches baseline), CI-pinned ruff 0.15.22 clean whole-tree, `poetry check` exit 0, package build + `twine check` passed with the same pre-existing warnings, Angular `tsc`/`lint` clean, dockerized Karma 657/657 with unchanged coverage, `npm ls qs` confirms single resolved instance, `ng build` succeeded with unchanged bundle size — no break, D-02 not triggered
- Opened PR #143, waited for full CI green (12 non-skip checks incl. CodeQL x3 languages, Docker build, e2e amd64), merged with a merge commit (history kept, two parents confirmed)
- Rebased the local-only 126-03/126-04 docs commits onto the new `origin/main` cleanly (`.planning/`-only diff, no conflicts); local `main` stays unpushed per the plan
- Polled the Dependabot alert count post-merge: 2 -> 0 within 2 polls (4 minutes), confirmed stable with two further direct checks
- Re-verified production fingerprint unchanged and wud still `exited` immediately before tagging
- Created and pushed the annotated `v1.8.0` tag on PR #143's merge commit (`098ed81b`)
- Watched the tag CI run to completion: all jobs `success` including both e2e architectures (amd64 + arm64) and all five publish jobs (verify-release-metadata, e2etests-docker-image, publish-docker-image, publish-github-release, publish-pypi); `:dev` publish correctly `skipped` on a tag push
- Extracted the three `[chromium-token]` SEC-02 passing lines from the tag run's amd64 e2e log
- Resolved the GHCR index digest by two independent methods (buildx imagetools + anonymous GHCR token HEAD request) — they agree: `RELEASE_DIGEST=sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`, platforms linux/amd64 + linux/arm64
- Confirmed `:latest`'s per-platform image manifests are byte-identical to `:1.8.0`'s (only the top-level index digest differs, due to separately-written attestation manifests from the two push steps) — same documented pattern as 1.7.5/1.7.6, not a discrepancy
- Confirmed the GitHub release is live (not draft/prerelease), body links `blob/v1.8.0/CHANGELOG.md` with no `{{VERSION}}` placeholder
- Installed `seedsyncarr==1.8.0` cleanly from PyPI in a Python 3.12 venv (`INSTALL_EXIT=0`, `Version: 1.8.0`)
- Final re-check: wud `exited`, production `seedsyncarr` fingerprint identical to every prior check in this phase (`:1.7.6@sha256:da6196e0…`, same container ID, same `StartedAt`)

## Task Commits

This continuation resumed mid-Task-2 (the D-04 stop commit `3e798401` from the prior session is the starting point) and completed Task 2 and Task 3:

1. **Follow-up dependency fix (part of Task 2)** — `eaaca5e5` (chore) on `release/1.8.0-deps`: `src/python/poetry.lock`, `src/angular/package-lock.json`
2. **PR #143 merge to main** — `098ed81b` (merge commit, two parents)
3. **Task 2 completion: owner decision, PR #143, merge, local main rebase, D-01 close-out, tag push** — `6ba59257` (docs)
4. **Task 3: tag CI verification, GHCR digest, GitHub release, PyPI, RELEASE_DIGEST** — `ea807a4e` (docs)

**Plan metadata:** this SUMMARY.md commit (next)

_No TDD tasks in this plan (release/publish mechanics, not feature code); no test->feat->refactor cycle applies._

## Files Created/Modified

- `src/python/poetry.lock` - `setuptools` 83.0.0 -> 84.2.1 (lockfile-only; not added as a direct dependency)
- `src/angular/package-lock.json` - `qs` 6.16.0 -> 6.16.2 (lockfile-only; transitive via `karma -> body-parser`)
- `.planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md` - appended the D-04 follow-up decision, PR #143 roll-in/CI/merge record, local main rebase, D-01 close-out (0 alerts), tag push, tag CI verification, GHCR digest (two methods), GitHub release check, PyPI install, and final wud/production re-check
- `.planning/phases/126-release-1-8-0/126-04-SUMMARY.md` - this file

## Decisions Made

- Owner verbatim "approve" (Task 1, prior session) authorized publishing as drafted
- Owner verbatim "1" (this continuation's starting point) authorized fixing both newly-discovered alerts (#106 `qs`, #107 `setuptools`) in a follow-up PR before tagging, rather than deferring either or holding the release entirely
- Evidence-file updates for the resumed work were split into two commits (`6ba59257` for Task 2 completion, `ea807a4e` for Task 3) to preserve the plan's per-task commit granularity, matching the pattern already established in 126-01/126-03
- Local main's docs-only commits were rebased (not cherry-picked) onto the new `origin/main` after PR #143 merged, since they touch only `.planning/` and had no conflicts — simpler and preserves the original commit identity where possible

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PyPI clean-venv check used Python 3.12 instead of the shell's default `python3`**
- **Found during:** Task 3, PyPI install verification
- **Issue:** The host's default `python3` resolves to 3.14, outside `seedsyncarr`'s declared `>=3.11,<3.13` support range; `pip install seedsyncarr==1.8.0` under a 3.14 venv correctly refused with "Requires-Python" filtering (not a product bug — pip read the metadata correctly), but it blocked completing the check as the plan's interface recipe implies (a working install).
- **Fix:** Used the already-installed `/opt/homebrew/bin/python3.12` to create the clean venv instead. No package install, no version substitution — an existing interpreter already on the host, within the project's own declared support range.
- **Cost if wrong:** None — this only affects how the verification venv was built locally; it does not touch any shipped artifact, lockfile, or published package. If 3.12 somehow behaved differently from a "generic" interpreter in range, the install itself (`INSTALL_EXIT=0`, `Version: 1.8.0`) is the actual evidence, independent of which in-range interpreter ran it.
- **Files modified:** None (scratch venv only, outside the repo)
- **Commit:** N/A (no repo change)

---

**Total deviations:** 1 auto-fixed (1 blocking, environment-only)
**Impact on plan:** No scope creep, no product code touched. The plan's own "D-02/Rule 3" exclusions for package manager installs do not apply here (no new package was installed; an existing interpreter was selected to match the project's own stated support range).

## Issues Encountered

None beyond the documented deviation above. The D-04 stop itself (two new Dependabot alerts discovered after the PR #142 merge) was not an issue encountered during this continuation — it was already resolved by the owner's "1" decision recorded at the start of this continuation's prompt; this session executed that decision.

## User Setup Required

None - no external service configuration required. The owner's two verbatim replies ("approve" and "1") were the two checkpoint resolutions for this plan; both are now fully executed.

## Next Phase Readiness

- `RELEASE_DIGEST=sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7` (linux/amd64, linux/arm64) is ready for Plan 05's sandbox smoke (D-11): repin `seedsyncarr-test` to this exact digest
- GHCR `:1.8.0`/`:latest`, GitHub release, and PyPI `1.8.0` are all live and verified
- 0 open Dependabot alerts; all 8 originally-tracked PRs (126-01 roll-in) plus PR #143 (post-merge fix) are closed/merged
- wud remains `exited` — Plan 06 (per D-15) is responsible for restoring it after production verification, not this plan
- Production `seedsyncarr` is untouched throughout (`:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`, same container, same `StartedAt`)
- Local `main` carries the rebased 126-03/126-04 docs commits, not yet pushed — the owner directs when `.planning/` lands on `origin/main` (unrelated to the release artifacts, which are already fully published via the tag)

---
*Phase: 126-release-1-8-0*
*Completed: 2026-10-28*

## Self-Check: PASSED

- FOUND: .planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md
- FOUND: .planning/phases/126-release-1-8-0/126-04-SUMMARY.md
- FOUND: eaaca5e5 (chore: setuptools/qs lockfile bumps)
- FOUND: 098ed81b (merge commit: PR #143)
- FOUND: 6ba59257 (docs: Task 2 completion)
- FOUND: ea807a4e (docs: Task 3 publish verification)
- FOUND: 3e798401 (docs: prior-session D-04 stop commit)
- FOUND: v1.8.0 tag on origin (`git ls-remote --tags origin v1.8.0`)
- FOUND: v1.8.0 GitHub release (`gh release view v1.8.0 --json tagName`)
