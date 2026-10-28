---
phase: 125-lan-connection-tests
plan: 02
subsystem: release-process
tags: [changelog, release-notes, ci, pr, ghcr, digest-pin]

# Dependency graph
requires:
  - phase: 125-lan-connection-tests
    plan: 01
    provides: "the gated LAN-01/LAN-02 fix (f82e256) and RED test commit (8a69fdf) this plan verifies and ships"
provides:
  - "CHANGELOG.md Unreleased section recording the LAN Test Connection behaviour change as the 1.8.0 minor-version driver"
  - "125-LAN-EVIDENCE.md: full phase-gate record (suite-vs-baseline, whole-tree ruff, RED-before-GREEN, scope, log hygiene) plus the PR/CI/digest build-under-test record"
  - "One open draft PR (#140) on gsd/phase-125-lan-connection-tests with all CI checks green"
  - "DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3, the staging image 125-03 deploys to the sandbox"
affects: [125-03, 126-release-1.8.0]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase gate record: suite-vs-fixed-baseline via comm -23, whole-tree ruff as a separate gate, RED-before-GREEN commit order, exact src/ scope diff, grep-based log/secret hygiene check"
    - "Digest resolution by two independent methods (docker buildx imagetools inspect; anonymous GHCR token + HEAD manifest request) that must agree before recording DEV_PIN"

key-files:
  created:
    - .planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md
    - .planning/phases/125-lan-connection-tests/125-02-SUMMARY.md
  modified:
    - CHANGELOG.md

key-decisions:
  - "Gate 1 completed normally in 85.02s with no timeout; the documented --ignore rerun path for test_extract_process.py/test_scanner_process.py was not needed this run"
  - "No existing PR for the branch, so a new draft PR (#140) was created against main, title 'Phase 125: LAN connection tests (LAN-01, LAN-02)'"

patterns-established: []

requirements-completed: [LAN-01, LAN-02]

# Metrics
duration: ~19min
completed: 2026-10-27
---

# Phase 125 Plan 02: Release Notes, Phase Gates, and CI Staging Digest Summary

**Recorded the 1.8.0 draft CHANGELOG entry for the LAN Test Connection change, passed all five phase gates over 125-01's fix, and shipped it on draft PR #140 with all CI checks green, resolving DEV_PIN `sha256:162d4532...` as the staging build for 125-03's live sandbox check.**

## Performance

- **Duration:** ~19 min (first commit `3022056` at 2026-10-27T15:30:48-04:00; CI run 415 ran 19:34:04Z→19:46:26Z UTC, ~12m22s wall time, watched via background task)
- **Completed:** 2026-10-27
- **Tasks:** 3 of 3
- **Files modified:** 1 (`CHANGELOG.md`); 2 created (`125-LAN-EVIDENCE.md`, this summary)

## Accomplishments

- D-10: `CHANGELOG.md` now has a `## [Unreleased]` section above `## [1.7.6] - 2026-10-15` stating these are the 1.8.0 draft notes and the Test Connection change is the minor-version driver, with the required `### Changed` and `### Security` bullets
- D-08: all five phase gates passed over 125-01 — suite failures are the exact 24-line documented baseline (`comm -23` empty), whole-tree `ruff check src/python/` is clean, `test(125-01)` precedes `fix(125-01)` with each commit touching only its expected files, the `src/` diff is exactly the three expected files with `controller/` untouched, and the new code adds zero `logger.`/`api_key`/`X-Api-Key` lines
- D-06: confirmed `_validate_url` has exactly one definition and one call site, both in `web/handler/config.py`, with no other production reference
- Pushed the phase branch and opened the single draft PR (#140, base `main`); CI run 415 passed all 13 non-publish checks (publish-* skipped on `pull_request`, as expected)
- Resolved the staging digest by two independent methods (`docker buildx imagetools inspect` and an anonymous GHCR token + HEAD manifest request) that agreed exactly, recording `DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3` — distinct from the 1.7.6 production digest — as the build 125-03 will deploy to the sandbox

## Task Commits

1. **Task 1: CHANGELOG 1.8.0 draft entry for the LAN behaviour change (D-10)** - `3022056` (docs)
2. **Task 2: Phase gates over 125-01** - no separate commit (evidence file left uncommitted per plan instruction; completed by Task 3's commit below)
3. **Task 3: Push, open/reuse the single draft PR, wait for CI green, resolve DEV_PIN** - committed together with this summary (see **Plan metadata** below; the hash is necessarily self-referential since this file is part of that same commit)

**Plan metadata:** `6fac07f` (`docs(125-02): record phase gates, PR CI run and staging digest`) — this commit contains both `125-LAN-EVIDENCE.md`'s "Build under test" section and this summary.

_Note: Task 2 produced `125-LAN-EVIDENCE.md` without committing it (per the plan's explicit "Do not commit yet; Task 3 completes the file" instruction); Task 3 appended the "Build under test" section and committed the completed file together with this summary in one local commit, which is intentionally not pushed so the PR head stays equal to the digest's build._

## Files Created/Modified

- `CHANGELOG.md` - added `## [Unreleased]` section (1.8.0 draft) with `### Changed` and `### Security` bullets for the LAN Test Connection behaviour change
- `.planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md` - (new) full gate record (suite baseline, ruff, RED/GREEN order, scope, log hygiene) plus the PR/CI/digest build-under-test section
- `.planning/phases/125-lan-connection-tests/125-02-SUMMARY.md` - (new) this file

## Decisions Made

- Gate 1's full suite run completed normally in 85.02s with no timeout, so the plan's documented `--ignore` rerun fallback for `test_extract_process.py`/`test_scanner_process.py` was not exercised this run; the 24-line failure/error set matched the fixed baseline exactly.
- No open, closed, or merged PR existed for `gsd/phase-125-lan-connection-tests` before this plan, so a new draft PR (#140) was created per the plan's "none exists" branch, rather than reusing one.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `git push` to origin surfaced GitHub's standing Dependabot summary ("10 vulnerabilities" on the default branch, 1 critical/4 high/4 moderate/1 low; `gh api .../dependabot/alerts` filtered to open state shows 9). This is routine push output, not something this plan's scope covers — Dependabot review is explicitly Phase 126's release-gate responsibility (PROJECT.md "Release 1.8.0 (126: Dependabot review incl. 999.4, ...)"). Noting it here for visibility; no action taken in this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Roadmap criterion 4 (release-notes note) is satisfied: the 1.8.0 draft CHANGELOG entry is in place for Phase 126 to finalize (rename `[Unreleased]` to `[1.8.0] - <date>`).
- 125-03 can proceed directly to the live sandbox check using `DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3`, with the expected restore pin `IMAGE_PIN_L0=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` recorded in `125-LAN-EVIDENCE.md`.
- PR #140 stays open and draft; nothing was merged or marked ready. The local `docs(125-02)` evidence/summary commit is intentionally unpushed so the PR head (`3022056...`) still matches the exact build CI tested and the digest was resolved from.

## Self-Check: PASSED

Verified on disk and in git history:

- `FOUND: CHANGELOG.md`
- `FOUND: .planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md`
- `FOUND: .planning/phases/125-lan-connection-tests/125-02-SUMMARY.md`
- `FOUND: 3022056` (docs, Task 1 CHANGELOG commit)
- `FOUND: 6fac07f` (docs, Task 3 evidence+summary commit)
- `FOUND: 3ba9bb5` (docs, summary self-reference fix)

---
*Phase: 125-lan-connection-tests*
*Completed: 2026-10-27*
