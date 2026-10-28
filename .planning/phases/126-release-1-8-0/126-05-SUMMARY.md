---
phase: 126-release-1-8-0
plan: 05
subsystem: release
tags: [release, nas-sandbox, smoke-test, exact-digest, sonarr-v4, radarr, webhook, auto-delete, no-secrets, token-probe, owner-checkpoint, credential-hygiene]

# Dependency graph
requires:
  - phase: 126-02
    provides: sandbox smoke harness (teardown.sh, webhook-post.sh, extract_secrets.py, token-probe.mjs) proven with a positive control
  - phase: 126-04
    provides: "1.8.0 published; RELEASE_DIGEST=sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7 cross-checked"
provides:
  - "All eleven D-12a smoke checks PASS on the exact published 1.8.0 digest against sonarr-v4 and Radarr on seedsyncarr-test"
  - "Owner's verbatim go-ahead ('deploy') for the production deploy, recorded before any production change"
  - "Sandbox no longer holds a copy of production Radarr's URL/API key on disk (owner-sanctioned addendum)"
affects: [126-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Value-free arr-key restore via jq -nR '[inputs]|join(\"\\n\")' (jq 1.5-compatible, no --rawfile) instead of a single `input`, so an empty original key restores correctly instead of raising jq's 'break' on EOF"
    - "Count-only / sha256-only credential comparison pattern extended to direct on-disk settings.cfg edits, not just the config API, so a raw file cleanup can still be proven correct without ever printing the value"
    - "Blank Radarr fields on disk are the application's own documented default (disabled) state (seedsyncarr.py's default-config generator), confirmed via source read before relying on it, rather than inventing an ad hoc placeholder"

key-files:
  created:
    - .planning/phases/126-release-1-8-0/126-05-SUMMARY.md
  modified:
    - .planning/phases/126-release-1-8-0/126-SMOKE-EVIDENCE.md
    - .planning/phases/126-release-1-8-0/126-teardown.sh

key-decisions:
  - "Owner verbatim 'deploy' (Task 3) authorizes the production deploy; Plan 126-06 performs it, not this plan"
  - "Owner-sanctioned addendum: clear the sandbox's on-disk copy of production Radarr's URL/key rather than leave it as a residual limitation, since the orchestrator flagged it and the owner raised no objection"
  - "REL-06 is NOT marked complete by this plan: its ROADMAP/REQUIREMENTS definition includes the production deploy and a confirmed post-deploy scan, which only Plan 126-06 delivers"

patterns-established:
  - "An owner-sanctioned out-of-plan cleanup task, performed between a plan's blocking checkpoint and its close-out, is recorded as its own evidence section and its own atomic commit rather than folded silently into the checkpoint commit"

requirements-completed: []

# Metrics
duration: ~25min total (Tasks 1-2 smoke work ran in a prior session, ~2h11m per their own timestamps; this continuation covering Task 3 and the cleanup addendum ran ~25min)
completed: 2026-10-28
---

# Phase 126 Plan 05: NAS Sandbox Smoke Test (exact digest) Summary

**All eleven D-12a smoke checks PASS on the exact published `1.8.0` digest against `sonarr-v4` and Radarr on `seedsyncarr-test`; owner replied verbatim "deploy"; the sandbox's on-disk copy of production Radarr's credentials was then cleared at the owner's sanction.**

## Performance

- **Duration:** Tasks 1-2 (smoke checks) ran in a prior session, 2026-10-28 18:20-18:42 UTC per their own in-evidence timestamps (restart marker 22:20:16Z through teardown's final fresh-session read-back). This continuation (Task 3 + the cleanup addendum) ran 2026-10-28T22:50Z-23:02Z UTC, approx. 25 min.
- **Started (this continuation):** 2026-10-28T22:50:00Z (approx.)
- **Completed:** 2026-10-28T23:02:07Z
- **Tasks:** 3 of 3 (Task 1 and Task 2 were already complete before this continuation began), plus one owner-sanctioned addendum task
- **Files modified:** 2 (`126-SMOKE-EVIDENCE.md`, `126-teardown.sh`'s jq-1.5 fix landed in Task 1's commit from the prior session)

## Accomplishments

- Confirmed the Task 3 checkpoint packet was ready: `## Smoke verdict summary` present in evidence, production still on the 1.7.6 digest at the moment of the check
- Appended the owner go-ahead packet summary and the owner's verbatim reply, `"deploy"`, to `126-SMOKE-EVIDENCE.md`, with production re-confirmed unchanged at that moment
- Investigated the sandbox's residual "`radarr_api_key` left set" limitation (documented in Task 2's evidence) at the orchestrator's flagged, owner-unobjected request:
  - Read `src/python/common/config.py` and `src/python/seedsyncarr.py` to confirm blank `radarr_url`/`radarr_api_key` on disk is the application's own documented disabled-Radarr default (`Checkers.null`/`Converters.null`, no non-empty validation; `arr_queue.py` only reads these fields when `radarr.enabled` is `True`), before relying on it
  - Confirmed `BEFORE_COMPARE=SAME` by sha256: the sandbox's on-disk `radarr_api_key` was a byte-for-byte copy of production Radarr's `config.xml` `<ApiKey>`
  - Stopped `seedsyncarr-test` only, backed up `settings.cfg` (0600, timestamped, same directory), performed an inode-preserving awk-to-temp-then-`cat`-back edit blanking `radarr_url` and `radarr_api_key` in the `[Radarr]` section (`enabled` line untouched, confirmed still `False`), restarted
  - Confirmed the sandbox came back up (`status: up=true`, image unchanged at the 1.8.0 digest) and that `AFTER_COMPARE=DIFFERENT` by sha256 (the on-disk key no longer matches production's)
  - Deleted the backup file (it held a copy of the production key) immediately after the after-comparison
  - Verified production's `seedsyncarr` and `radarr` containers were never stopped, started, or exec'd into — only `radarr`'s mounted `config.xml` was read from the host filesystem, for the hash comparison

## Task Commits

This continuation resumed after Tasks 1-2's commits from the prior session and completed Task 3 plus the cleanup addendum:

1. **Task 1: Repin sandbox to 1.8.0, restart/transfer/Sonarr-v4/Radarr/webhook/cleanup** (prior session) - `f21ab90a` (docs)
2. **Task 2: 1.8.0 spot checks, teardown, verdict** (prior session) - `0d74370e` (docs)
3. **Task 3: Owner go-ahead recorded** (this continuation) - `705d88f1` (docs)
4. **Owner-sanctioned addendum: sandbox Radarr credential cleanup** (this continuation) - `9b32824c` (docs)

**Plan metadata:** this SUMMARY.md commit (next)

_No TDD tasks in this plan (NAS smoke/evidence recording and a config-hygiene cleanup, not feature code); no test->feat->refactor cycle applies._

## Files Created/Modified

- `.planning/phases/126-release-1-8-0/126-SMOKE-EVIDENCE.md` - appended `## Owner go-ahead` (verbatim reply) and `## Sandbox Radarr credential cleanup` (owner-sanctioned addendum, counts/booleans only, no secret values)
- `.planning/phases/126-release-1-8-0/126-05-SUMMARY.md` - this file
- (On the NAS, not in this repo) `/volume1/docker/v5test/seedsyncarr/settings.cfg` - `[Radarr]` `radarr_url`/`radarr_api_key` blanked; a timestamped backup was made and then deleted after the after-comparison confirmed the change

## Decisions Made

- Owner verbatim "deploy" (Task 3) authorizes the production deploy; this plan does not perform it — Plan 126-06 does
- The sandbox's on-disk copy of production Radarr's URL/key was cleared rather than left as the documented residual limitation, since the orchestrator flagged the risk to the owner and proceeded unobjected
- Blank (not a placeholder) was used for the cleared fields, because the source code confirms blank `radarr_url`/`radarr_api_key` with `enabled=False` is the application's own documented disabled-Radarr default state, not an invented value
- REL-06 is intentionally NOT marked complete by this plan's state update: `REQUIREMENTS.md`'s REL-06 definition includes "deployed to NAS production... with a successful post-deploy scan confirming recovery," which is Plan 126-06's work, not this plan's

## Deviations from Plan

None beyond what Tasks 1-2 already documented in their own evidence sections (the jq 1.5 `--rawfile` incompatibility fix and the three teardown.sh Rule 1 bugs, all committed in the prior session's Task 1/Task 2 commits). The sandbox Radarr credential cleanup was an explicit owner-sanctioned addendum from the continuation prompt, not a deviation under Rules 1-4 (it was pre-authorized, not discovered-and-auto-fixed mid-task).

## Issues Encountered

None. The cleanup's only open question — whether blanking `radarr_url`/`radarr_api_key` on disk could crash startup — was resolved by reading the config loader source before acting (`Checkers.null`/`Converters.null`, and the app's own default-config generator using the identical blank+disabled state), rather than guessing.

## User Setup Required

None - no external service configuration required. The owner's two verbatim replies for this plan ("deploy" for Task 3, and no objection to the flagged cleanup) are both now fully executed.

## Next Phase Readiness

- Eleven-of-eleven D-12a smoke checks PASS on `ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`; sandbox wiring restored (with the `radarr_url`/`webhook_secret` inert no-restore-to-empty exceptions documented in Task 2, and `radarr_api_key` now additionally cleared by this plan's addendum)
- Owner go-ahead "deploy" recorded; Plan 126-06 is clear to perform the production deploy by digest per D-15/D-16/D-17
- Sandbox `seedsyncarr-test` is up, on the 1.8.0 digest, Radarr disabled with no credential of production's on disk
- Production `seedsyncarr` and `radarr` fingerprints unchanged throughout this plan (never stopped, started, or exec'd into)
- REL-06 remains open in REQUIREMENTS.md pending Plan 126-06's production deploy and confirmed post-deploy scan

---
*Phase: 126-release-1-8-0*
*Completed: 2026-10-28*

## Self-Check: PASSED

- FOUND: .planning/phases/126-release-1-8-0/126-SMOKE-EVIDENCE.md
- FOUND: .planning/phases/126-release-1-8-0/126-05-SUMMARY.md
- FOUND: .planning/phases/126-release-1-8-0/126-teardown.sh
- FOUND: f21ab90a (docs: Task 1 smoke core checks, prior session)
- FOUND: 0d74370e (docs: Task 2 spot checks/teardown/verdict, prior session)
- FOUND: 705d88f1 (docs: Task 3 owner go-ahead)
- FOUND: 9b32824c (docs: sandbox Radarr credential cleanup addendum)
