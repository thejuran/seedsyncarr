---
phase: 130-release-1-8-1
plan: 02
subsystem: release
tags: [release, dependabot-triage, minimatch, package-legitimacy, bundle-identity, owner-checkpoint]
requires:
  - "130-01 (release/1.8.1 branch, Dependabot snapshot, soupsieve roll-in)"
provides:
  - "Package legitimacy record for @isaacs/nonrecursive-glob-match 1.1.0 (no provenance attestation, no repository URL)"
  - "Owner decision PKG_DECISION=decline; minimatch alert #110 left open with reason"
  - "Bundle identity proof: release/1.8.1 production build sha256-identical to 1.8.0 /app/html (21 files, BUNDLE_IDENTICAL)"
  - "Draft plain-terms owner dependency list (D-07) for the pre-tag checkpoint"
affects:
  - "130-03 onward (version bump runs on an Angular tree unchanged from 1.8.0)"
  - "130-04 (expected open alert count after merge is 1: minimatch #110)"
tech-stack:
  added: []
  patterns:
    - "Resolve exact transitive version in a scratch lock copy, then npm view <pkg>@<exact> before any install"
key-files:
  created:
    - .planning/phases/130-release-1-8-1/130-02-SUMMARY.md
  modified:
    - .planning/phases/130-release-1-8-1/130-REL-EVIDENCE.md
decisions:
  - "Owner declined @isaacs/nonrecursive-glob-match 1.1.0 (no provenance attestation at any version); minimatch alert #110 stays open for a later release"
metrics:
  duration: "about 15 min of active work across the owner wait (2026-11-20 22:37Z to 2026-11-22)"
  completed: 2026-11-22
  tasks: 2
  files: 1
---

# Phase 130 Plan 02: Minimatch Package Gate, Bundle Identity and Owner Dependency List Summary

The minimatch fix needs a new helper package, `@isaacs/nonrecursive-glob-match` 1.1.0. It turned out to have no provenance attestation and no source repository in its registry record, so the owner declined it and alert #110 stays open. The unchanged release branch builds a UI bundle that is sha256-identical, file by file, to the published 1.8.0 image (21/21 files). The plain-terms dependency list for the pre-tag checkpoint is drafted.

## Owner reply (verbatim)

> Decline (Recommended)

`PKG_DECISION=decline`. The owner picked this in an AskUserQuestion dialog and the orchestrator relayed it. It was acted on because decline is the plan's safe default: nothing is installed and no repository file changes.

## Key values

| Item | Value |
|------|-------|
| Resolved helper version | `@isaacs/nonrecursive-glob-match` 1.1.0, integrity `sha512-GPm/Dbvk5RLmhRnxXIa7nTpK0xtl4E0wj0MslsuNiJ1FIROU+2+9lgUC/dgF7Ey4QCWhfEsgxilMRMCdHPfDfw==` (registry and scratch lock match; downloaded tarball hash matches) |
| Minimatch the fix would have brought | 11.0.9 (not installed) |
| Minimatch in the tree | 10.2.6 (eslint path, left by decision); 3.1.5 (karma, karma-coverage, glob) |
| Lint | `npm run lint` exit 0, eslint v10.13.0 |
| Bundle proof | 21 files vs 21 files, `diff` exit 0, `BUNDLE_IDENTICAL` |
| Alert count | 5 before; expected 1 after the release merges (#110) |

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Owner check of the new helper package (exact version) | f79ef1ad (facts), 52d75b72 (owner decision) | 130-REL-EVIDENCE.md |
| 2 | Minimatch skip, lint, bundle identity proof, draft dependency list | be1f6c13 | 130-REL-EVIDENCE.md |

Task 1 verify printed `PACKET_READY` (tree clean under `src/angular/` at the checkpoint). Task 2 verify printed `T2_OK` (decline path). After both tasks: `git ls-remote --heads origin release/1.8.1` printed nothing, `git tag -l v1.8.1` printed nothing, and `"overrides"` appears once in `src/angular/package.json`, the same as on `origin/main`. No `chore(130-02)` lockfile commit exists because of the decline.

## Deviations from Plan

**1. [Rule 3 - Blocking] Task 1 evidence committed in two commits**
- **Found during:** Task 1
- **Issue:** The plan has one commit holding both the facts and the decision. The facts were ready before the owner replied, and the agent stopped at the checkpoint in between.
- **Fix:** Committed the facts first (f79ef1ad) so no uncommitted evidence edit sat across the wait, then committed the decision under the plan's message (52d75b72).
- **Cost if wrong:** None; this is history shape only.
- **Commit:** f79ef1ad, 52d75b72

**2. [Rule 1 - Bug] Closing sentence wording**
- **Found during:** Task 2 step 7
- **Issue:** The required sentence says "these two updates", but only soupsieve was rolled in.
- **Fix:** Changed it to "A normal pip install is unaffected by this update." The scope and the first sentence are unchanged.
- **Cost if wrong:** Small; the owner can edit the wording at the pre-tag checkpoint.
- **Commit:** be1f6c13

**3. `npm audit signatures` not run.** The plan requires it only on the approve path, to check the new package. The lockfile is unchanged from 1.8.0.

REL-07 and REL-08 were not marked complete, as the execution constraints require. The D-06 stop rule did not trigger.

## Assumption Drift (advisory)

**1. Provenance attestation on the helper package**
- **Found during:** Task 1
- **Planned:** RESEARCH said "SLSA provenance attestation present" for `@isaacs/nonrecursive-glob-match`.
- **Actual:** No version (1.0.0 to 1.1.0) has `dist.attestations`, and the registry attestation endpoint returns Not found. minimatch 11.0.9 itself does have one. A public GitHub repo with tag v1.1.0 exists, but the registry record doesn't link to it.
- **Why:** The research probably carried minimatch's attestation over to the helper.
- **Cost if wrong:** The approve path would have stopped at step 4 anyway. With the decline, nothing is affected.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: .planning/phases/130-release-1-8-1/130-REL-EVIDENCE.md (PKG_VERSION, PKG_INTEGRITY, PKG_DECISION=decline, BUNDLE_IDENTICAL, D-07 list)
- FOUND commits: f79ef1ad, 52d75b72, be1f6c13
