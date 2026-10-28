---
phase: 126-release-1-8-0
plan: 06
subsystem: infra
tags: [release, nas-production, docker, digest-pin, backups, rollback, wud, dependabot]

# Dependency graph
requires:
  - phase: 126-05
    provides: smoke-tested 1.8.0 digest (RELEASE_DIGEST), sandbox image ID, owner go-ahead "deploy"
provides:
  - Production seedsyncarr pinned to the exact smoked ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 digest
  - Four pre-upgrade backups (compose + three state files) with sha256 sums and dual-image loader-check PASS evidence
  - A written, verified rollback runbook targeting :1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
  - Owner confirmation of the production deploy, recorded verbatim
  - Closed-out release state in STATE.md (Phase 126 complete, v1.8.0 Reliability milestone fully delivered)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: ["inode-preserving compose edit (sed to temp file + cat back) to keep wud labels and watch behavior intact across a manual digest pin"]

key-files:
  created:
    - .planning/phases/126-release-1-8-0/126-DEPLOY-EVIDENCE.md
    - .planning/phases/126-release-1-8-0/126-06-SUMMARY.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Sonarr/Radarr Test Connection verification used GET instead of the plan's assumed POST, matching the app's actual route registration (web_app.add_handler, not add_post_handler); no product code changed"
  - "D-16 rollback was not triggered — production recovered cleanly on every signal (clean stop, dual-image loader PASS, image ID match, successful scan 31s after start, both arrs reachable, zero error/unavailable lines over a 309s steady-state window)"
  - "Full v1.8.0 milestone archival (ROADMAP shipped marker, milestone archive files) is left for a separate owner-directed step; this plan only marks Phase 126 and REL-06 complete, per its own scope"

requirements-completed: [REL-06]

# Metrics
duration: 7m22s (Task 1 to Task 3 commits; owner-confirmation checkpoint pause in between)
completed: 2026-10-28
---

# Phase 126 Plan 06: Production Deploy by Digest Summary

**Production seedsyncarr upgraded 1.7.6 -> 1.8.0 by exact smoked digest with four checksummed backups, dual-image loader verification, a clean post-deploy recovery, and owner confirmation; v1.8.0 Reliability milestone fully delivered (13/13 requirements).**

## Performance

- **Duration:** ~7m22s of recorded task-commit activity (Task 1 at 19:22:22-04:00 through Task 3 at 19:29:44-04:00), with a checkpoint pause for the owner's confirmation reply between Task 1 and Task 2
- **Started:** 2026-10-28T18:07:57-05:00 (DEPLOY_START, 126-DEPLOY-EVIDENCE.md)
- **Completed:** 2026-10-28T19:29:44-04:00
- **Tasks:** 3 (Task 1 auto; Task 2 checkpoint:human-verify; Task 3 auto)
- **Files modified:** 2 (`126-DEPLOY-EVIDENCE.md`, `STATE.md`) across the 3 task commits, plus `ROADMAP.md`/`REQUIREMENTS.md` in the final metadata commit

## Accomplishments
- Deployed the exact smoked `ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7` digest to NAS production with four sha256-recorded pre-upgrade backups and a passing dual-image (1.7.6 + 1.8.0) read-only loader check
- Confirmed clean recovery: CLEAN_STOP (1.9s SIGTERM-to-exit), new container image ID matched the smoked sandbox image ID exactly, `downloaded_files=96` carried over intact, first remote scan succeeded 31s after start with no warm-up error, both Sonarr (4.0.20.3014) and Radarr (6.4.4.10685) returned Test Connection success, and a 309s steady-state window showed zero `unavailable`/`Traceback`/`ERROR` lines with 0 restarts
- Verified zero secret values in both the production container log and the plain-file logs (count-only extractor, N=3 values, 0 matches in each)
- Restored wud last and re-fingerprinted production and the sandbox 195s later, confirming wud made no changes to either (both already on the newest numeric tag)
- Recorded the owner's verbatim "confirmed" reply, closing D-17 and REL-06
- Closed out release state: 0 open Dependabot alerts, 0 open Dependabot PRs (none opened after the `v1.8.0` tag), STATE.md corrected to show Phase 126 complete and the v1.8.0 Reliability milestone (Phases 121-126, 13/13 requirements) fully delivered

## Task Commits

Each task was committed atomically:

1. **Task 1: Production deploy by digest with backups, loader checks, recovery verification, rollback rule, wud restored last** - `ad8c8f08` (docs) — completed in the prior session
2. **Task 2: Owner confirmation of the production deploy (D-17)** - `c2eda9de` (docs) — owner verbatim "confirmed" appended to the evidence file
3. **Task 3: Close-out — final Dependabot check, STATE.md correction and phase status** - `5490cb7a` (docs)

**Plan metadata:** (this commit, docs: complete plan metadata)

## Files Created/Modified
- `.planning/phases/126-release-1-8-0/126-DEPLOY-EVIDENCE.md` - Full deploy evidence: preconditions, stop classification, backups + sha256, dual-image loader PASS, compose diff, image-ID/digest match, recovery (scan/arr/steady-state), no-secrets check, rollback-not-triggered rationale, rollback runbook, deploy verdict, owner confirmation, final Dependabot state
- `.planning/STATE.md` - Phase 126 marked complete; progress 7/7 phases, 52/52 plans, 100%; production/sandbox digest, wud status and rollback target recorded; stale Phase 122/123 session-continuity wording replaced with the current true state; Operator Next Steps corrected

## Decisions Made
- Verification command correction only (GET vs POST for Test Connection) — see Deviations below; no behavior change to the application
- Rollback policy (D-16) evaluated and not triggered — all recovery signals were clean, nothing ambiguous
- Milestone-level archival (ROADMAP ✅ shipped marker, archive files under `milestones/`) deliberately left out of this plan's scope — it corrects Phase 126 and REL-06 truthfully without inventing a milestone-close workflow the plan didn't ask for

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Sonarr/Radarr Test Connection endpoints are GET, not POST**
- **Found during:** Task 1, step 1f (arr reachability check)
- **Issue:** The plan's interface recipe specified `POST /server/config/sonarr/test-connection` and `/server/config/radarr/test-connection`. Both returned `405 Method Not Allowed` on POST. Reading `src/python/web/handler/config.py` showed both routes are registered with `web_app.add_handler` (GET), not `add_post_handler` (POST) — the plan's recipe text didn't match the actual route registration.
- **Fix:** Called both endpoints with GET instead. Both returned `{"success": true, "version": "..."}`. No product code was touched; only the verification command was corrected to match the application's actual API.
- **Cost if wrong:** None to production — this only affects how the verification command was phrased in the evidence file. The actual check (both arrs reachable with a version response) still ran and passed; the returned version strings (4.0.20.3014, 6.4.4.10685) are independent confirmation the app reached both services successfully.
- **Files modified:** None (verification command only)
- **Committed in:** `ad8c8f08` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3, verification-command-only, no product or config change).
**Impact on plan:** No scope creep; the deploy proceeded exactly as planned once the correct HTTP method was used.

## Issues Encountered
None in the deploy itself. One pre-existing tooling quirk noted during close-out (not caused by this plan, not fixed, logged for transparency): the GSD SDK's `state.*` frontmatter sync counts a Backlog heading (`### Phase 999.6: ...` under `## Backlog`) as if it were a milestone phase when deriving `progress.total_phases`, inflating it to 7 against 6 real v1.8.0 phase directories and showing `percent: 86` in STATE.md's frontmatter even though every real phase (121-126) and all 52 plans are summarized. ROADMAP.md's own explicit phase checklist (the source the Roadmaps page actually uses per PLANNING-FORMAT.md when present) correctly shows Phase 126 ticked `[x]` and the Progress table row `6/6 Complete`, so this does not mislead the page. Out of scope to fix here (pre-existing SDK behavior, not this project's code or `.planning/` content).

## User Setup Required
None - no external service configuration required by this plan. (The Phase 121 token-rotation and credential-rotation items remain open operator follow-ups, tracked in STATE.md's Pending Todos and Operator Next Steps — they are not part of REL-06's done-when criteria.)

## Known Stubs
None. No hardcoded empty values, placeholder text, or unwired data sources were introduced by this plan — it is documentation and a live NAS deploy, no application code changed.

## Threat Flags

None. This plan's threat model (T-126-28..33) was fully addressed by the deploy procedure itself (digest pin, backups + loader check, wud-last sequencing, count-only secret check, AutoDelete rollback caution, owner confirmation); no new network endpoint, auth path, file-access pattern, or schema change was introduced.

## Next Phase Readiness
- v1.8.0 Reliability milestone is fully delivered: all 6 phases (121-126) complete, all 13 requirements (SEC-02, SAFE-01/02, LIFE-01/02, STRM-01/02, LAN-01/02, LOG-01/02, REL-05/06) complete, production running the exact tested `:1.8.0` digest with owner confirmation on record.
- No blockers. Remaining items are operator-paced, not release gates: rotate the production `api_token` (Phase 121 pending-todo), confirm credential rotation (seedbox password, Sonarr/Radarr keys), and remove the sandbox test torrent once seed time is met.
- Post-tag `.planning` docs commits remain local on `main` and are not pushed — pushing `main` would publish the `:dev` image tag; the owner decides when to push.
- No next milestone has been started or implied by this plan; STATE.md explicitly says so rather than inventing one.

---
*Phase: 126-release-1-8-0*
*Completed: 2026-10-28*

## Self-Check: PASSED

- FOUND: `.planning/phases/126-release-1-8-0/126-DEPLOY-EVIDENCE.md`
- FOUND: `.planning/phases/126-release-1-8-0/126-06-SUMMARY.md`
- FOUND: commit `ad8c8f08` (Task 1)
- FOUND: commit `c2eda9de` (Task 2)
- FOUND: commit `5490cb7a` (Task 3)
