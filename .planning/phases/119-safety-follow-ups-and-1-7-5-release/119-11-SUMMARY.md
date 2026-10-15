---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 11
subsystem: release
status: superseded
tags: [release, nas, deploy, superseded]
requires: [119-10]
provides:
  - "Nothing — plan not executed (owner HOLD 2026-10-15)"
affects: [Phase 119.1]
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - .planning/phases/119-safety-follow-ups-and-1-7-5-release/119-11-SUMMARY.md
  modified: []
decisions:
  - "Plan 119-11 (NAS production deploy of 1.7.5) is SUPERSEDED and was not executed: the owner held the 1.7.5 deploy at the 119-10 checkpoint because the container prints settings.cfg secrets to its log at startup (pre-existing since v1.0.0). The deploy moves to Phase 119.1, which fixes the log, releases 1.7.6 and deploys 1.7.6 instead."
metrics:
  completed: 2026-10-15
  tasks: 0
  files: 0
---

# Phase 119 Plan 11: NAS deploy of 1.7.5 — SUPERSEDED (not executed)

## Outcome

Not executed, by owner decision (2026-10-15, recorded verbatim in `119-REL03-EVIDENCE.md` → "Deploy gate (Plan 119-10 Task 3): HOLD").

- Production remains on `:1.7.4@sha256:682d129d…`; the wud auto-updater remains STOPPED.
- 1.7.5 remains published (Docker `:1.7.5@sha256:b061d95a…`, GitHub Release, PyPI) and passed the full smoke list on the NAS scratch setup (119-10).
- The NAS scratch setup `/volume1/docker/seedsync-smoke-1.7.5` is retained for reference.

## Where this work went

Phase 119.1 "Startup log secrets fix and 1.7.6 release" (inserted after Phase 119):

1. SEC-01 — stop printing configuration secrets to the container log at startup (regression test first).
2. REL-04 — release 1.7.6 through the 1.7.5 gates.
3. REL-03 (NAS portion, carried) — deploy 1.7.6 to production by digest with this plan's procedure: verified backups + loader check, digest pin, scan recovery, arr reachability, wud restored last, rollback runbook to 1.7.4.
4. Remind the owner to rotate the seedbox password and both Sonarr/Radarr API keys after deploy.

## Deviations

None — the plan was intentionally not started.

## Self-Check

- `119-11-PLAN.md` unchanged.
- REQUIREMENTS.md REL-03 remains unchecked (closes in Phase 119.1).
