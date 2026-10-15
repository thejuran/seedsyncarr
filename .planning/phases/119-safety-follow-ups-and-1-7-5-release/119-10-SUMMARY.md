---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 10
subsystem: release
tags: [release, tag, ghcr, pypi, smoke-test, nas, owner-checkpoint]
requires: [119-09]
provides:
  - "v1.7.5 tag, GHCR :1.7.5 (multi-arch), GitHub Release, PyPI 1.7.5"
  - "Full REL-03 smoke evidence on the published :1.7.5 digest (8/8 PASS)"
  - "Owner deploy-gate decision: HOLD (superseded by Phase 119.1 / 1.7.6)"
affects: [119-11 (superseded), Phase 119.1 (to be inserted)]
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - .planning/phases/119-safety-follow-ups-and-1-7-5-release/119-10-SUMMARY.md
  modified:
    - .planning/phases/119-safety-follow-ups-and-1-7-5-release/119-REL03-EVIDENCE.md
    - .planning/phases/119-safety-follow-ups-and-1-7-5-release/deferred-items.md
decisions:
  - "Owner HOLD on the 1.7.5 production deploy: ship 1.7.6 that stops printing settings.cfg to the container log first, deploy 1.7.6 instead, then rotate the seedbox password and both arr API keys"
  - "Production stays on :1.7.4 and wud stays stopped until the 1.7.6 deploy is verified; 1.7.5 stays published (not retracted)"
  - "Plan 119-11 is superseded by Phase 119.1 and will not be executed; REL-03 stays open until the 1.7.6 NAS deploy"
metrics:
  completed: 2026-10-15
  tasks: 3
  files: 3
---

# Phase 119 Plan 10: Tag, publish and smoke 1.7.5 Summary

1.7.5 was merged (PR #127, merge commit kept), tagged and published to GHCR, GitHub Releases and PyPI; the exact published `:1.7.5` digest passed all eight smoke checks on the NAS scratch setup. The owner then **held** the production deploy because a pre-existing entrypoint bug prints the full `settings.cfg` (secrets included) to the container log at every start.

## Status

Complete. Task 3 outcome: **owner hold — deploy superseded by 1.7.6 in Phase 119.1.**

## Tasks

| Task | Name | Commit | Notes |
| ---- | ---- | ------ | ----- |
| 1 | wud suspension, merge, tag, CI publish, PyPI check | 0928017, 7ebfac9 (merge), 5cfcc63, 0b81316 | wud exited before first push; tag CI green; PyPI 1.7.5 installs in a clean venv (REL-02 complete) |
| 2 | Smoke test on the published `:1.7.5` digest | b272406 | 8/8 PASS (one cosmetic re-hold blip logged in deferred-items.md) |
| 3 | Owner go-ahead for production deploy | (this docs commit) | **HOLD**, recorded verbatim in 119-REL03-EVIDENCE.md "Deploy gate" |

## Owner decision (verbatim, 2026-10-15)

> HOLD the production deploy of 1.7.5. Reason: the container prints the full settings.cfg (including the seedbox password and Sonarr/Radarr API keys, plaintext because encryption is off) to the docker container log at every start (pre-existing since v1.0.0, not a 1.7.5 regression). The owner chose to ship a 1.7.6 that stops printing secrets FIRST, then deploy 1.7.6 instead of 1.7.5, then rotate the seedbox password and both arr API keys. Production stays on :1.7.4; wud stays STOPPED until the 1.7.6 deploy is verified. 1.7.5 remains published (Docker/GitHub/PyPI) — not retracted.

## End state

- Production `seedsyncarr`: `:1.7.4@sha256:682d129d…` (unchanged by this plan).
- wud: stopped (exited 2026-10-15T11:33:41Z); all NAS auto-updates paused until the 1.7.6 deploy is verified.
- Scratch dir `/volume1/docker/seedsync-smoke-1.7.5` retained (scratch credentials only); smoke containers and network removed.
- 1.7.5 published on GHCR, GitHub Releases and PyPI; not retracted.
- REL-02 complete; REL-03 remains unchecked (NAS-verification clause pending the 1.7.6 deploy).
- Nothing pushed to `main` after the release merge/tag by this continuation (a push to main publishes `:dev`; owner decides).

## Verification (observed)

- Prior commits 0928017, 7ebfac9, 5cfcc63, 0b81316, b272406 confirmed present (`git cat-file -t` → commit).
- Task 1/2 evidence (job conclusions, digest, PyPI install, smoke outputs) is in 119-REL03-EVIDENCE.md, recorded when those tasks ran.
- Task 3: no NAS command was run in this continuation (owner instruction); production/wud state is taken from the smoke teardown record in the evidence file, not re-observed.

## Deviations from Plan

None in the executed tasks. Task 3 ended in a hold instead of "deploy", which the plan allowed.

## Known Stubs

None.

## Next

- **Plan 119-11 (NAS deploy of 1.7.5) will NOT be executed**; it is superseded by Phase 119.1.
- Insert **Phase 119.1**: stop printing secrets in the container startup log (with a regression test), release 1.7.6, deploy 1.7.6 to the NAS (digest pin, backups, rollback to 1.7.4), restore wud after the deploy is verified, then rotate the seedbox password and both arr API keys.

## Self-Check: PASSED

- FOUND: 119-10-SUMMARY.md, 119-REL03-EVIDENCE.md (Deploy gate section), deferred-items.md (Outcome section)
- FOUND commits: 0928017, 7ebfac9, 5cfcc63, 0b81316, b272406
