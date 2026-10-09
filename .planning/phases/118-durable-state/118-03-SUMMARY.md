---
phase: 118-durable-state
plan: 03
subsystem: release
tags: [release, version-bump, changelog, release-notes, rollback-runbook, metadata-gate]
requires:
  - phase: 118-durable-state
    provides: "118-02 atomic persist write fix (d208acb) and REL-01 gate-1 combined regression run"
provides:
  - "v1.7.4 release commit 9398e7b (six release files) ready for the 118-04 owner checkpoint"
  - "Evidence: release-metadata gate output, unchanged production tree since d208acb, NAS loader-check proof (informational)"
affects: [118-04, 118-05]
tech-stack:
  added: []
  patterns: ["Plain-language public release notes; rigorous operator checks live in the NAS deploy plan, not the public notes"]
key-files:
  created:
    - .planning/phases/118-durable-state/118-03-SUMMARY.md
  modified:
    - package.json
    - src/angular/package.json
    - src/angular/package-lock.json
    - src/python/pyproject.toml
    - CHANGELOG.md
    - release-notes.md
    - .planning/phases/118-durable-state/118-REL01-EVIDENCE.md
decisions:
  - "Owner decision 2026-10-09: public release notes are plain English; the loader-based backup check, FAILED/do-not-start block and sha256sum steps are dropped from release-notes.md and live only in Plan 118-05"
  - "Public rollback target is ghcr.io/thejuran/seedsyncarr:1.7.2 (1.7.3 never published); owner confirms at 118-04"
  - "Release-notes prose kept as one line per paragraph (existing file convention; GitHub Release bodies render single newlines as line breaks) rather than hard-wrapped"
metrics:
  duration: "~3 min wall clock (measured)"
  completed: 2026-10-09
  tasks: 2
  files: 7
requirements: [REL-01]
---

# Phase 118 Plan 03: v1.7.4 Release Commit Summary

All six version fields read 1.7.4. The never-tagged 1.7.3 CHANGELOG block is folded into `[1.7.4] - 2026-10-09`, with entries for Phases 116, 117 and 118. `release-notes.md` is rewritten in plain English, with the Stop change and a short backup and rollback runbook. The release-metadata gate passes locally (`verify` exit 0; `node --test` 21/21 pass). Nothing is pushed or tagged.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1+2 | `9398e7b` | chore(release): v1.7.4 — safety patch (import, transfer-state, durable-state). Covers the six release files; the plan specifies one commit for both tasks |
| 2 | `4fd57cd` | docs(118-03): record release-metadata gate, backup-check proof and unchanged production tree |

## What was verified (observed output)

- `npm run verify:release-metadata -- 1.7.4`: exit 0, all six checks listed. `npm run test:release-metadata`: tests 21, pass 21, fail 0.
- `grep -c '"version": "1.7.4"'`: 1 / 1 / 2 (package.json / angular package.json / lock). `pyproject.toml`: 2.
- CHANGELOG: line 7 is `## [1.7.4] - 2026-10-09`. No `[1.7.3]` heading remains. The 1.7.4 block contains `never tagged`, `more than one release`, `unavailable`, `Stop` and `atomic rename`.
- release-notes.md: 4 `###` sections and 1 `v{{VERSION}}/CHANGELOG.md` link. `volume1|ssh nas|@sha256:` = 0, `seedsyncarr:1.7.2` = 1, `1.7.3` = 1, `[AutoDelete]` = 1, `enabled = False` = 1. The file is 34 lines.
- `git show --stat 9398e7b` lists exactly the six release files.
- `git diff --stat d208acb 9398e7b -- src/python ':!src/python/tests'` shows only `src/python/pyproject.toml`, so the 118-02 regression run still covers the release SHA.

## Deviations from Plan

### Owner decision (overrides parts of Task 2)

**1. Public backup/rollback content simplified (owner decision, 2026-10-09)**
- **Found during:** Task 2, after the release notes and NAS proof were already done.
- **Change:** `release-notes.md` now has plain-English steps only:
  - **Before you upgrade:** stop the app, copy the three files, then upgrade. One sentence explains why.
  - **If you need to roll back:** stop the app and put the copies back. Make sure `[AutoDelete]` reads `enabled = False` in the restored `settings.cfg`. Start 1.7.2, and keep auto-delete off until imports are reconciled.
- **Removed:** the `docker run --entrypoint python3 … from_str` loader-check command, the FAILED/do-not-start block, the `sha256sum` record/compare steps and the separate grep-verify step.
- **Acceptance criteria waived as a result:** `--entrypoint python3`, `:/c:ro`, `from_str`, `controller.controller_persist`/`controller.auto_queue`, `FAILED` >= 2, `do not start`, `sha256sum` >= 2, `enabled = False` >= 2, the ordering checks for the stop-before-copy line and the re-check line, and the evidence requirement that the recorded command match the published one.
- **Kept checks:** the no-NAS-path/digest grep (0) and the metadata gate both still pass.
- **Unchanged:** the rigorous loader check stays in Plan 118-05. That plan was not touched.

**2. NAS scratch proof ran before the decision arrived**
- It ran in `/volume1/docker/seedsync-relnotes-check` against `ghcr.io/thejuran/seedsyncarr:1.7.2`.
  - Good set: three `OK` lines, exit 0.
  - Bad set: `FAILED (ConfigError)`, `FAILED (PersistError)` and `FAILED (PersistError)`, exit 1.
- The scratch dir was removed afterwards. No production path or container was touched.
- The result is recorded in the evidence file as informational. It validates the same loader approach 118-05 uses.

### Other

**3. Release-notes line wrapping**
- **Planned:** hard-wrapped prose.
- **Actual:** one line per paragraph, matching the existing file. CLAUDE.md says to follow existing conventions, and hard wraps would show up as forced line breaks in the GitHub Release body.

## Assumption Drift (advisory)

- **Found during:** Task 2.
- **Planned:** the public notes carry the loader-based check command.
- **Actual:** the owner limited the public notes to plain English (see Deviation 1).
- **Why:** the audience is non-engineer self-hosters.

## Known Stubs

None.

## Threat Flags

None. No new code surface; T-118-07 still holds (0 NAS paths or digests in the public notes). T-118-10 is mitigated by rollback step 3, which sets `[AutoDelete] enabled = False` in the restored file before 1.7.2 starts. T-118-11 is mitigated in the public notes by stop-before-copy and a non-empty check. The stronger loader check is now covered only by Plan 118-05, per the owner decision.

## Self-Check: PASSED

- FOUND: release-notes.md, CHANGELOG.md, 118-REL01-EVIDENCE.md (`## Release commit (Plan 118-03)`)
- FOUND commits: 9398e7b, 4fd57cd
