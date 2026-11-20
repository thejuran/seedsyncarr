---
phase: 130
reviewers: [codex]
reviewed_at: 2026-11-20T05:28:23Z
plans_reviewed: [130-01-PLAN.md, 130-02-PLAN.md, 130-03-PLAN.md, 130-04-PLAN.md, 130-05-PLAN.md, 130-06-PLAN.md]
---

# Cross-AI Plan Review — Phase 130

## Codex Review (round 1)

## Summary

The six plans provide strong release sequencing, regression traceability, digest verification and rollback preparation. They largely honor D-01–D-20, but need revision before execution: production queue verification can be waived while REL-08 is still marked complete; the placeholder’s “never transfers” guarantee lacks necessary preconditions; and sandbox restoration is incomplete for some allowed starting states. Several verification steps also provide weaker evidence than their acceptance criteria claim. This review checked repository code, CI and the reused teardown; it did not independently refresh external dependency advisories or inspect NAS state.

## Strengths

- **130-01:** Keeps Phase 129’s merge separate, preserves history and explicitly prevents unrelated runtime dependency movement.
- **130-02:** Confines the minimatch fix to the lockfile and compares the resulting UI against a published artifact.
- **130-03:** Connects existing ARR/WEB regressions to recorded fail-before evidence and correctly makes Linux CI authoritative over the limited macOS run.
- **130-04:** Separates publication approval from deployment approval, pauses wud and resolves the release digest through two methods.
- **130-05:** Exercises both container shutdown and in-process restart, including stderr where port-bind failures appear.
- **130-06:** Includes stopped-state backups, compatibility checks in both images, exact-image verification and explicit rollback criteria.

## Concerns

- **HIGH — 130-05 Task 3; 130-06 Task 1, steps 7–12: Passive checks do not satisfy REL-08.**  
  Both plans explicitly acknowledge that Test Connection does not exercise the queue request, yet permit completion on that evidence. Plan 06 also permits an inconclusive approved probe to fall back to passive checks, while its later ambiguity rule says to stop and ask. Owner deployment approval should not silently redefine the locked requirement for a successful production queue check.

- **HIGH — 130-06 Task 1, step 7: The production placeholder is not guaranteed to remain held.**  
  The plan checks auto-queue but does not require enabled Arr targets before creating the file. [`CompletionGate._run()`](/Users/julianamacbook/seedsyncarr/src/python/controller/completion_gate.py:194) returns `not_required` when no integration is enabled. A synthetic name also does not mathematically guarantee no matching queue record. Moreover, “any verdict that is not unavailable” is insufficient natural evidence: `still_downloading` or `ambiguous_match` can be returned before every Arr’s freshness is checked.

- **HIGH — 130-03 Task 2; 130-05 Tasks 1–2: Restoration does not cover every setting the smoke may change.**  
  The smoke can enable Sonarr, but the reused teardown has no Sonarr-enabled capture or restore mechanism. It also explicitly leaves originally empty URLs/keys populated while reporting `ok`; the plan repairs only the expected empty Radarr pair. Mixed Radarr states—such as a populated URL with an empty key—and initially empty Sonarr fields are not handled. Thus D-11 can fail despite a successful second teardown run. See the [existing teardown](/Users/julianamacbook/seedsyncarr/.planning/phases/126-release-1-8-0/126-teardown.sh:209).

- **MEDIUM — 130-03 Task 3; 130-04 Task 3: Two changed filenames do not prove a version-only bundle change.**  
  Arbitrary application changes could exist inside `main-*.js` while only it and `index.html` differ. Research proposed content normalization, but the plans dropped that check. Also, a renamed main bundle appears as removed and added paths in a literal file-manifest comparison; “exactly two differing entries” needs a defined pairing algorithm.

- **MEDIUM — 130-01 Task 1; 130-04 Task 2: Merge checks are not bound to the approved head.**  
  `gh pr merge ... --merge` lacks `--match-head-commit`. A head change between verification and merge could merge unreviewed content. Plan 04 also lacks a final explicit check of the current head and required checks immediately before merging. Recording whatever SHA happens to be `origin/main` afterward is weaker than recording the PR’s actual `mergeCommit`.

- **MEDIUM — 130-04 Task 2: The evidence-edit and branch-switch sequence is fragile.**  
  This task modifies `130-REL-EVIDENCE.md`, then switches to local `main` and pulls, committing evidence only afterward. Those uncommitted changes can block checkout or fast-forward when the incoming merge changes the same file. The plan needs a deliberate way to preserve the approval record while transitioning branches.

- **MEDIUM — 130-02 Tasks 1–2: Package approval is not tied to the resolved artifact.**  
  `npm view` without an exact version examines the current default version; the later resolver may select something different. The plan records `npm audit signatures` output but does not define failure handling for invalid signatures or unexpected provenance. If this checkpoint is retained, its approval must identify the actual version and integrity subsequently installed.

- **MEDIUM — 130-06 Task 1, rollback: Restarting wud can undermine rollback.**  
  After rollback, 1.8.1 remains published and newer than 1.8.0. The normal success path’s rationale—both containers already run the newest release—no longer applies. The plan allows wud to restart without proving its triggers cannot reapply the failed release.

- **MEDIUM — 130-01 Task 2; 130-02 Task 2; 130-04 owner packet: Dependency exposure wording is too absolute.**  
  “Users were never exposed” exceeds the evidence. The repository explicitly advertises a `dev` extra containing webtest, through which soupsieve can be installed. Also, PyPI runtime dependencies are independently resolved from lower-bounded metadata, including `paste>=3.10.1`; the Docker lock does not fix pip users to Paste 3.10.1. Distinguish the standard Docker image, default pip installation and development installations.

- **LOW — 130-03 Task 2; 130-05 Task 1: Some acceptance criteria cannot literally pass.**  
  The copied teardown prints status, image and cleanup-count lines even with an empty capture directory, so “every line must read `ok (not set this session)`” is impossible. Shellcheck is simultaneously a must-have and optional. Several checks search for evidence headings rather than verifying the underlying outcome.

## Suggestions

- Require actual production queue evidence before marking REL-08 complete. If unavailable, leave verification pending or obtain an explicit requirement amendment.
- Before creating a probe, verify enabled Arr targets, candidate eligibility and absence of a matching queue record. Use a unique session name and guaranteed cleanup on interruption.
- Capture and restore every changed field independently, including Sonarr enabled and empty credentials. Verify exact restored values, not merely “different from production.”
- Pair old/new main bundles, normalize only the version literal and its index reference, then require byte equality.
- Bind merges to verified head SHAs and obtain the tag target from the merged PR record.
- Define a clean branch-transition procedure for approval evidence and a rollback-specific wud policy.
- Keep the six-wave structure, but remove redundant test reruns and replace brittle textual checks with a smaller set of executable assertions.

## Risk Assessment

**HIGH as written**, primarily because the production probe and restoration paths can violate their safety claims, and the completion path can mark REL-08 satisfied without a production queue request. With those corrected, overall risk should fall to **MEDIUM**, appropriate for an otherwise well-controlled release involving live credentials, production state and irreversible publication.
