---
phase: 113-presentation-launch-readiness
plan: 01
subsystem: docs
tags: [readme, security-md, contributing, code-of-conduct, changelog, license, presentation]

requires:
  - phase: 110-hostile-reader-discovery-pass
    provides: HR-05 finding (LICENSE.txt→LICENSE rename) folded to this phase
  - phase: 111-config-set-endpoint-migration
    provides: shipped config-set POST-only behavior the docs describe accurately
  - phase: 112-defensive-guards-code-hardening
    provides: shipped startup warnings, delete-failure logging, opt-in fail-closed webhook the docs describe accurately
provides:
  - First-draft README targeted rewrite (owned-axis one-liner, fork-relationship note, security selling point)
  - SECURITY.md security-posture section (code-accurate, opt-in knobs)
  - Freshened CONTRIBUTING.md (dev setup, test/lint commands, PR flow)
  - CODE_OF_CONDUCT.md (Contributor Covenant 2.1)
  - CHANGELOG.md [1.4.0] entry (Keep a Changelog format) + compare-link footers
  - LICENSE.txt renamed to LICENSE with all user-facing links repointed
affects: [113-03-codex-pass, 113-04-finalize]

tech-stack:
  added: []
  patterns:
    - "Doc claims verified per-claim against shipped source before assertion (no claim from pattern memory)"
    - "Rate-limiting described only for the five actually-decorated endpoints; *arr-URL guard described as IP-resolution guard, not outbound-webhook/SSRF-library"

key-files:
  created:
    - CODE_OF_CONDUCT.md
  modified:
    - README.md
    - SECURITY.md
    - CONTRIBUTING.md
    - CHANGELOG.md
    - ACKNOWLEDGMENTS.md
    - LICENSE (renamed from LICENSE.txt)

key-decisions:
  - "LICENSE rename + repo-wide link fix (README:18, README:118, ACKNOWLEDGMENTS:34) so GitHub detects the license"
  - "README one-liner leads with the owned axis: Sonarr-driven + HMAC-verified safe auto-delete"
  - "Fork note credits ipsingh06/SeedSync origin, acknowledges other forks generically, no sole-fork claim, no outbound-push advantage-framing"
  - "SECURITY.md posture section states protections matter-of-factly; rate-limit scope and IP-resolution-guard wording verified against source"

patterns-established:
  - "These are FIRST DRAFTS — finalized in Plan 04 after the teardown (Plan 02) and codex content pass (Plan 03) critiques land"

requirements-completed: [LAUNCH-02, LAUNCH-04, LAUNCH-05, LAUNCH-06]

duration: ~12min (across an interrupted initial run + continuation)
completed: 2026-06-02
---

# Phase 113 Plan 01: First-Draft Docs + LICENSE Rename Summary

**First drafts of README/SECURITY.md/CONTRIBUTING.md/CODE_OF_CONDUCT.md/CHANGELOG[1.4.0], plus the LICENSE.txt→LICENSE rename with all user-facing links repointed — claim-accurate to the code shipped in Phases 111-112.**

## Performance

- **Duration:** ~12 min (initial run interrupted by an environmental content filter; completed across a continuation)
- **Completed:** 2026-06-02
- **Tasks:** 3 (all complete)
- **Files modified:** 6 (5 docs + 1 rename) + 1 created (CODE_OF_CONDUCT.md)

## Accomplishments
- Renamed `LICENSE.txt` → `LICENSE` and repointed every user-facing link (README badge line 18, README prose line 118, ACKNOWLEDGMENTS.md line 34); zero `LICENSE.txt` references remain in README/ACKNOWLEDGMENTS.
- README targeted rewrite (draft): sharpened one-liner to the owned axis (Sonarr-driven + HMAC-verified safe auto-delete), added the fork-relationship note (credits ipsingh06/SeedSync origin, generic "other active forks" acknowledgment, no sole-fork claim, no outbound-push bravado), pulled the security posture up as a stated selling point.
- SECURITY.md (draft): kept + honesty-passed the reporting policy, added a concise "Security posture" section — protections stated plainly, rate-limiting scoped to the five actually-decorated endpoints, the *arr-connection-URL guard described honestly as an IP-resolution guard.
- CONTRIBUTING.md (draft): freshened with real dev setup, test/lint commands, and PR flow.
- CODE_OF_CONDUCT.md: added Contributor Covenant 2.1 with the GitHub private security-advisory channel as the enforcement contact.
- CHANGELOG.md: added a `## [1.4.0]` entry (Keep a Changelog format matching the existing [1.3.0] entry) summarizing the config-set POST migration, defensive guards, and presentation rebuild; added compare-link footers for [1.4.0] and the previously-missing [1.3.0].

## Task Commits

1. **Task 1: LICENSE rename + repo-wide link fix** - `f529ed0` (chore)
2. **Task 2: README targeted rewrite (first draft)** - `50328e9` (docs)
3. **Task 3: SECURITY.md posture + CONTRIBUTING.md freshen (first drafts)** - `71e56f8` (docs)
4. **Task 3 (cont.): CHANGELOG [1.4.0] entry + footers** - `401c3c8` (docs)
5. **Task 3 (cont.): CODE_OF_CONDUCT.md** - `949d5b3` (docs)

## Files Created/Modified
- `LICENSE` - renamed from LICENSE.txt (Apache 2.0 content unchanged)
- `README.md` - targeted rewrite draft; LICENSE links fixed
- `ACKNOWLEDGMENTS.md` - LICENSE link repointed (line 34)
- `SECURITY.md` - added "Security posture" section
- `CONTRIBUTING.md` - freshened dev workflow
- `CODE_OF_CONDUCT.md` - new (Contributor Covenant 2.1)
- `CHANGELOG.md` - [1.4.0] entry + compare-link footers

## Decisions Made
- All security/feature claims were verified against the shipped source cited in the plan's per-claim source map before being written; no claim was asserted from pattern memory. Rate-limiting is described only for the five decorated endpoints (never "all mutable endpoints"); the *arr-URL guard is described as an IP-resolution guard, not outbound-webhook validation or a full SSRF library.

## Deviations from Plan

The initial executor run and a first continuation were both cut off mid-execution by an external content-filtering policy while drafting the security-posture prose (an environmental constraint on the subagent output stream, not a problem with the work). The orchestrator completed the remaining non-security items (CHANGELOG [1.4.0] entry, CODE_OF_CONDUCT.md) and this SUMMARY directly in the worktree, preserving all prior commits. No scope change; all three plan tasks and their acceptance criteria are satisfied.

## Issues Encountered
- Content-filter interruptions (described above) — resolved by completing the small non-security remainder inline rather than re-dispatching subagents into the same constraint.

## User Setup Required
None — no external service configuration required for this plan. (Screenshot capture and repo-metadata application are handled in Plan 04 / at the walkthrough.)

## Next Phase Readiness
- Drafts are ready for the cynical-reader teardown (Plan 02, already complete) and the codex content pass (Plan 03) to critique.
- Plan 04 finalizes these drafts after both critiques land.

---
*Phase: 113-presentation-launch-readiness*
*Completed: 2026-06-02*
