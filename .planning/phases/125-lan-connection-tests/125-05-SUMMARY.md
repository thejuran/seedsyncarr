---
phase: 125-lan-connection-tests
plan: 05
subsystem: release-process
tags: [changelog, d-13, d-14, in-03, phase-gates, pr-140, ci, staging-digest, gap-closure]

# Dependency graph
requires:
  - phase: 125-04
    provides: "The parser-differential SSRF guard fix (b6d0902) and RED test commit (730d3c7) this plan gates and ships"
provides:
  - "CHANGELOG.md Unreleased entry made accurate after the 125-04 guard hardening (IN-03): D-10 content plus the malformed/ambiguous-URL refusal bullet, the D-13 plain-language upgrade note, the backslash parser-differential technical note, and the D-12/WR-03 cloud-metadata-in-allowed-range note"
  - "125-LAN-EVIDENCE.md 'Gap closure (D-11, D-12)' section: 125-04 RED-before-GREEN record and the full 125-05 five-gate rerun over it"
  - "PR #140 pushed with the 125-05 CHANGELOG commit, CI run 416 green on all 13 non-publish checks, PR description updated with a plain-terms review-follow-up paragraph"
  - "DEV_PIN_R2=ghcr.io/thejuran/seedsyncarr@sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45, the fixed-head staging image 125-06 deploys to the sandbox"
affects: [125-06, 126-release-1.8.0]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Same gate record format as 125-02, rerun over 125-04's commit pair instead of 125-01's"
    - "Digest resolution by two independent methods (docker buildx imagetools inspect; anonymous GHCR token + HEAD manifest request) that must agree, plus an equivalence guard immediately before the lookup confirming no later push landed"

key-files:
  created:
    - .planning/phases/125-lan-connection-tests/125-05-SUMMARY.md
  modified:
    - CHANGELOG.md
    - .planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md

key-decisions:
  - "CHANGELOG Security section ordered: D-13 plain upgrade note first, then the kept existing multicast/site-local bullet, then the backslash parser-differential technical note, then the D-12 cloud-metadata note — matches the plan's 'add ... first / then add / add a bullet' sequencing while keeping the original bullet in place"
  - "Rewrapped two Changed-section phrases ('Docker container', 'user name or password') and the Security D-13 bullet ('1.7.6' + 'upgrad') onto single physical lines so the plan's line-based grep acceptance checks pass; no change to content, only line-wrap position"

requirements-completed: []
# LAN-01/LAN-02 intentionally NOT marked complete here -- per project instructions,
# 125-06 is the remaining gap-closure plan and REQUIREMENTS.md stays untouched
# until it closes the phase.

# Metrics
duration: ~16min
completed: 2026-10-28
---

# Phase 125 Plan 05: CHANGELOG Accuracy, Gate Rerun, and Staging Digest Summary

**Rewrote the 1.8.0 draft CHANGELOG entry to describe the guard as it actually behaves after the 125-04 fix (D-11 through D-14, IN-03), reran all five phase gates over that fix, and shipped it on draft PR #140 with CI green, resolving DEV_PIN_R2 `sha256:76df9d9a...` as the fixed-head staging build for 125-06's live sandbox recheck.**

## Performance

- **Duration:** ~16 min (Task 1 commit `18de612` at 2026-10-27T23:55:50Z; CI run 416 completed ~2026-10-28T00:10Z, watched via background task)
- **Completed:** 2026-10-28
- **Tasks:** 3 of 3
- **Files modified:** 2 (`CHANGELOG.md`, `125-LAN-EVIDENCE.md`); 1 created (this summary)

## Accomplishments

- **IN-03 (D-10/D-11/D-12/D-13/D-14):** `CHANGELOG.md`'s `## [Unreleased]` section now states the guard's post-fix behavior accurately: the original D-10 `### Changed` content plus leading/trailing-space trimming and a second bullet for the malformed/ambiguous-URL refusals (spaces, backslashes, control/non-ASCII characters with `xn--` guidance, credentials, `?`/`#`, malformed hostnames); `### Security` now leads with a brief, plain D-13 disclosure that 1.7.6 and earlier could be tricked by a crafted URL into sending the request elsewhere and that upgrading fixes it, keeps the existing multicast/site-local bullet, adds the backslash parser-differential technical explanation, and adds the D-12/WR-03 note that `fd00:ec2::254` and `100.100.100.200` are blocked inside otherwise-allowed ranges (with `100.100.100.100` Tailscale MagicDNS unaffected) and that IPv6 transition forms are refused explicitly.
- **Gates (D-08) rerun over 125-04:** Gate 1 (suite) — 82.69s run, 21 failed/3 errors, the extracted 24-line `FAILED`/`ERROR` set is byte-identical to the documented environmental baseline (`diff` empty, `comm -23` empty). Gate 2 (lint) — whole-tree `ruff check src/python/` → `All checks passed!`. Gate 3 (RED before GREEN) — `test(125-04)` (`730d3c7`, test file only) precedes `fix(125-04)` (`b6d0902`, `config.py` only); `test(125-01)`/`fix(125-01)` ordering unchanged. Gate 4 (scope, D-06) — the `src/` diff since `BASE` is exactly the same 3 files as 125-02's gate run, `controller/` untouched, `_validate_url` has one definition and one call site. Gate 5 (D-07) — 0 new `logger.`/`api_key`/`X-Api-Key` lines in the fix commit.
- **PR #140 pushed and updated:** `git push` (no force) landed the Task 1 CHANGELOG commit on the existing draft PR; `NEW_HEAD_SHA` `18de612d` confirmed equal to the PR's `headRefOid` and confirmed to contain `fix(125-04)` as an ancestor. PR description updated (attribution line removed, a plain-language "Review follow-up" paragraph added describing the backslash bypass fix, the new refusal categories, the metadata-in-allowed-range block, and the CHANGELOG update, attribution line re-added last) while remaining draft throughout.
- **CI green, digest resolved:** CI run 416 (databaseId `40605742420`) completed `success` on all 13 non-publish checks (5 publish-* jobs skipped on `pull_request`, as expected). The equivalence guard just before the digest lookup confirmed the newest branch run and the PR's `headRefOid` both still equal `NEW_HEAD_SHA`. Both digest-resolution methods (`docker buildx imagetools inspect` and an anonymous GHCR token + HEAD manifest request) agreed exactly on `sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45` — 64 hex chars, distinct from both the pre-fix `DEV_PIN` (`162d4532...`) and the 1.7.6 production digest (`da6196e0...`). Recorded as `DEV_PIN_R2` in `125-LAN-EVIDENCE.md`.

## Task Commits

1. **Task 1: Make the CHANGELOG [Unreleased] entry accurate (IN-03, D-10, D-11, D-12, D-13, D-14)** - `18de612` (docs)
2. **Task 2: Phase gates over 125-04** - no separate commit (evidence appended to `125-LAN-EVIDENCE.md` without committing, per the plan's explicit "Do not commit yet; Task 3 completes the file" instruction)
3. **Task 3: Push to PR #140, wait for CI green, resolve DEV_PIN_R2** - committed together with this summary (see **Plan metadata** below)

**Plan metadata:** committed in the same local commit as this summary (`docs(125-05): record gap-closure gates, PR CI run and staging digest`) — the hash is necessarily self-referential since this file is part of that commit; it is intentionally **not pushed**, so the PR head stays equal to the exact build CI tested and the digest was resolved from.

## Files Created/Modified

- `CHANGELOG.md` - rewrote the `## [Unreleased]` `### Changed`/`### Security` bullets so the 1.8.0 draft notes match the guard's actual post-125-04 behavior (IN-03/D-11/D-12/D-13/D-14)
- `.planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md` - (append-only) added "## Gap closure (D-11, D-12)" with the 125-04 RED/GREEN record, the five 125-05 gate results, and the "Build under test (125-05)" PR/CI/digest record
- `.planning/phases/125-lan-connection-tests/125-05-SUMMARY.md` - (new) this file

## Decisions Made

- Ordered the `### Security` bullets as: D-13 plain-language disclosure first, then the pre-existing multicast/site-local bullet (kept, not removed), then the backslash parser-differential technical explanation, then the D-12 metadata-in-allowed-range note — satisfies the plan's "add a brief plain-language bullet first ... then add a bullet with the plain technical context ... add a bullet [for metadata]" sequencing while honoring "keep the existing multicast/site-local bullet."
- Rewrapped the line breaks around three phrases (`Docker container`, `user name or password`, and the `1.7.6`/`upgrad` co-occurrence in the D-13 bullet) so each required phrase/pair lands on a single physical line — the plan's verify command greps line-by-line, so a phrase split across a markdown wrap would otherwise read as absent even though the rendered prose is identical. No prose content changed, only where the line wraps.
- Reused PR #140 (no second PR), kept it draft throughout, and did not force-push — consistent with the "one PR per phase" project instruction and D-11's "re-run CI and a short sandbox re-check" framing.

## Deviations from Plan

None - plan executed exactly as written. Both gate reruns and the digest resolution matched the plan's predicted format on the first attempt; the only adjustments were presentational (CHANGELOG line-wrap positions, caught and fixed before committing via the plan's own acceptance greps).

## Issues Encountered

- `git push` surfaced GitHub's standing Dependabot summary (10 vulnerabilities on the default branch: 1 critical/4 high/4 moderate/1 low) as routine push output. Out of this plan's scope — Dependabot review is Phase 126's release-gate responsibility (same note as 125-02). No action taken here.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The 1.8.0 draft release notes are now accurate for everything closed through 125-04 (D-10 through D-14, IN-01, IN-03). Phase 126 can finalize them (rename `[Unreleased]` to `[1.8.0] - <date>`) once the phase closes.
- 125-06 can proceed directly to the live sandbox recheck using `DEV_PIN_R2=ghcr.io/thejuran/seedsyncarr@sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45`, with the expected restore pin `IMAGE_PIN_L0=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` recorded in `125-LAN-EVIDENCE.md`.
- PR #140 stays open and draft; nothing was merged, marked ready, tagged, released, or deployed. The local `docs(125-05)` evidence/summary commit is intentionally unpushed so the PR head (`18de612d`) still matches the exact build CI tested and the digest was resolved from.
- `REQUIREMENTS.md` is untouched; LAN-01/LAN-02 completion is deferred to 125-06, the plan that closes the phase.

## Self-Check: PASSED

All claimed files exist on disk and both commit hashes referenced from this plan's own work (`18de612`) plus the inherited 125-04 hashes (`730d3c7`, `b6d0902`) are present in `git log --oneline --all` (verified below).

---
*Phase: 125-lan-connection-tests*
*Completed: 2026-10-28*
