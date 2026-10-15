---
phase: 118-durable-state
plan: 04
subsystem: release
tags: [release, owner-checkpoint, merge, tag, ci, ghcr, wud]
requires:
  - phase: 118-durable-state
    provides: "118-03 release commit 9398e7b plus owner-approved notes wording eece2e3"
provides:
  - "Annotated tag v1.7.4 (object 8ef7a22) on merge commit f6ff78a == origin/main"
  - "Public ghcr.io/thejuran/seedsyncarr:1.7.4 (and :latest), GitHub Release v1.7.4"
  - "DIGEST=sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595 and NAS_IMAGE_ID=sha256:0e33b030b41004f077d05742286b5599506f27e171b624b6c5122d59811c6d45 for Plan 118-05"
  - "wud stopped (exited) on the NAS for the whole release window"
affects: [118-05]
tech-stack:
  added: []
  patterns: ["Suspend the NAS auto-updater (wud) and verify it exited before the first push of a release"]
key-files:
  created:
    - .planning/phases/118-durable-state/118-04-SUMMARY.md
  modified:
    - .planning/phases/118-durable-state/118-REL01-EVIDENCE.md
decisions:
  - "Owner approved 1.7.4 as drafted (2026-10-09): (a) public rollback target 1.7.2; (b) CHANGELOG 1.7.3 fold kept; (c) coverage 86.36% informational; (d) wud semver tag filter applied in 118-05 before wud restarts; (e) inode-preserving compose edit with ls -i check"
  - "Owner decision after the tag CI PyPI failure (2026-10-09): ship 1.7.4 through Docker and GitHub only; the PyPI packaging fix plus Dependabot #93 (source-map-js >= 1.2.2) ship as 1.7.5; the v1.7.4 tag is not moved and the PyPI job is not re-run"
  - "wud stays stopped until Plan 118-05 restores it"
  - "The post-merge .planning evidence commits stay local on main (each push to main publishes a new numbered staging image)"
metrics:
  duration: "~50 min wall clock (approval 08:28 to digest record 08:52 NAS time, plus the checkpoint)"
  completed: 2026-10-09
  tasks: 3
  files: 1
requirements: [REL-01]
---

# Phase 118 Plan 04: Publish v1.7.4 Summary

**v1.7.4 is published as `ghcr.io/thejuran/seedsyncarr:1.7.4` (index digest `sha256:682d129d…`) and as GitHub Release v1.7.4, from an annotated tag on the history-preserving merge `f6ff78a`. wud was stopped and verified before the first push. Only the PyPI upload failed: PyPI rejected the wheel's `./`-prefixed archive paths, nothing was uploaded, and the owner deferred the fix to 1.7.5.**

## Tasks

| # | Task | Result | Commit |
|---|------|--------|--------|
| 1 | Owner approval checkpoint (D-02) | Packet presented. Reply: `approve-as-drafted`, with (a)-(e) all confirmed | `b652e57` (recorded in Task 2) |
| 2 | Stop wud, push main, merge `--no-ff`, tag, push tag | Production pre-checked as `:357 running`. wud stopped at 08:30:13 -0500 and `exited` twice, 10 s apart. `f8c94e9..c734c10` pushed, then the merge `f6ff78a` pushed, then tag `v1.7.4` pushed. Task 2 verify printed `TAG_OK` | `e86d7df`, `aeac94f` |
| 3 | Tag CI and image digest | Run 37937393805 conclusion `failure`, in `Publish to PyPI` only. All 12 other jobs ran green; the `:dev` job was skipped. Release is live and not a draft, with the CHANGELOG link. `:1.7.4` pulled on the NAS; DIGEST and NAS_IMAGE_ID recorded | `9dd629d`, `4e425e6` |

Observed verification:

- **Task 1:** the verify grep returned `1`.
- **Task 2:** the verify printed `TAG_OK`. `git cat-file -t v1.7.4` printed `tag`, and `v1.7.4^{}` equals `origin/main`, both `f6ff78a`. The commit count went from 1427 to 1547, with no squash. `git log --oneline f8c94e9..origin/main -- .planning/` counts 87 commits.
- **Task 3:**
  - The plan's automated check fails on its first clause, because `gh run list` shows `failure` for v1.7.4. That is the accepted deviation below.
  - The remaining clauses pass. `isDraft` is `false`. The evidence has exactly one `seedsyncarr@sha256:` line, plus a `DIGEST=` line and a `NAS_IMAGE_ID=` line.
  - wud is `exited`.

## Deviations from Plan

### Accepted deviation (owner decision)

**1. Tag CI not fully green: PyPI publish failed**
- **Found during:** Task 3
- **Issue:** PyPI returned `400 Invalid distribution file. Archive member path is not normalized: './.gitignore'`. A local rebuild of the wheel from `v1.7.4` shows every member listed as `./…`. That comes from `packages = ["."]` under the hatch build config in `src/python/pyproject.toml`, built with an unpinned `build`/hatchling in CI. Neither file changed since v1.7.2, which published fine, so this is a newer PyPI or hatchling behavior and not release code.
- **Outcome:** PyPI rejected the first file, so nothing was uploaded and PyPI still ends at 1.7.2. All test, lint, e2e (amd64 and arm64), metadata, Docker publish, GitHub Release and docs jobs are green.
- **Owner decision:** option (a). Ship 1.7.4 through Docker and GitHub. The fix goes into 1.7.5. The tag stays where it is, and the PyPI job is not re-run.
- **Commits:** `9dd629d`, `4e425e6` (evidence only)

### Process deviation

**2. Evidence commits not pushed to `origin/main`**
- The plan's Task 3 ends with `git push origin main`. At the owner's direction, `aeac94f`, `9dd629d`, `4e425e6` and this summary commit stay local on `main`.
- Reason: they are `.planning`-only, and any push to `main` publishes a new numbered staging image. `origin/main` stays at `f6ff78a`, which is the tag commit.

## Follow-up: 1.7.5 (backlog)

- **PyPI packaging fix:** stop `./`-prefixed archive members. Replace `packages = ["."]` with explicit package directories or a normalized include, and pin the builder in the `publish-pypi` job. Confirm by building the wheel and sdist locally and checking that no member starts with `./`.
- **Dependabot alert #93:** `source-map-js >= 1.2.2`.
- **Then:** publish 1.7.5 to PyPI, Docker and GitHub. PyPI goes from 1.7.2 straight to 1.7.5.

## Handoff to Plan 118-05

- **Image reference:** `ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595`. The image is already pulled on the NAS; its platform ID is `sha256:0e33b030…6d45` (amd64).
- **NAS rollback point:** `:357` @ `sha256:87ca66959391846d11fa1d0539601f18faba2294d880934041f8fc040a6d4e9f`.
- **wud:** `exited` since 2026-10-09 08:30 -0500. Restore it only in 118-05, after applying (d) `wud.tag.include=^\d+\.\d+\.\d+$`.
- **Production:** untouched, still `ghcr.io/thejuran/seedsyncarr:357 running`.

## Known Stubs

None.

## Threat Flags

None. The only new surface is the published artifacts, which the plan's threat model covers.

## Self-Check: PASSED

- **Files:** `118-REL01-EVIDENCE.md` contains the `## Owner approval (Plan 118-04, D-02)`, `## wud suspension (Plan 118-04`, `## Merge and tag (Plan 118-04)` and `## Tag and CI (Plan 118-04)` sections, plus the DIGEST and NAS_IMAGE_ID lines.
- **Commits:** `b652e57`, `e86d7df`, `f6ff78a`, `aeac94f`, `9dd629d` and `4e425e6` all exist on `main`.
