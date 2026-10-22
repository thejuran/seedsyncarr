---
phase: 122-safety-acceptance-and-logging-fixes
plan: 05
subsystem: infra
tags: [nas-sandbox, synthetic-webhook, completion-gate, auto-delete, import-credit, model-builder]

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes (plan 04)
    provides: "DEV_PIN-pinned seedsyncarr-test, 122-teardown.sh, 122-webhook-post.sh, SAFE-01 evidence file scaffold"
provides:
  - "D-06(e)/(a)/(b) live PASS evidence (Waiting hold + one-shot release, early per-episode credit, arm-on-commit with a real 300s auto-delete)"
  - "D-06(c) live FAIL evidence: a reproducible defect where a deferred webhook notice for a still-transferring child can be incorrectly dropped ('Ignoring webhook import') instead of credited, due to a directory-state/size-aggregate race in model_builder.py"
  - "Diagnosis with exact code references and a proposed (unapplied) fix, awaiting owner decision at Task 3"
affects: ["122-06/07 (extraction, restart persistence)", "122-08 (SAFE-02 reconciliation)", "any future fix-in-phase gap work on this defect"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-stage NAS session scripts (preflight -> secret/rate-limit -> synthetic material -> poll/release -> poll/post -> poll/commit -> poll/delete -> evidence save -> teardown), each with its own trap-protected OK=1 exit convention, chained via the shared capture-dir state.env"
    - "Model-state polling via repeated short-lived /server/stream SSE connections (each yields a fresh model-init snapshot), parsed with a small reusable model_tools.py rather than ad hoc jq/python one-liners"

key-files:
  modified:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md

key-decisions:
  - "Ran two synthetic scenarios (SSA122.Alpha.S01 then SSA122.Alpha2.S01) because the first run's sibling sizes (48/160/200 MiB) finished transferring faster than any 2s-spaced webhook post could catch a child still incomplete, even with lftp.rate_limit set -- not a product defect, a test-harness sizing issue, fixed for round 2 by raising sibling sizes (300/800/1200 MiB)"
  - "Treated round 1's 'wait for commit' timeout as my own test-harness bug (wrong log sentinel), not a SAFE-01 failure -- the underlying product behavior in round 1's own log was fully correct end-to-end (early credit x3, arm-on-commit, real 300.004s auto-delete); fixed the sentinel before round 2 and documented the correct evidence directly from round 1's log"
  - "Round 2 surfaced a genuine, reproducible D-06(c) failure (a deferred webhook notice for a still-transferring child dropped via 'Ignoring webhook import' instead of being credited) -- diagnosed as a race between a directory's derived state (model_builder.py's _check_downloaded_state/_are_all_children_downloaded, purely children-state-driven) and its own separately-scanned local_size/remote_size aggregate; documented with a proposed fix but NOT applied, per D-03 and this plan's explicit 'no src/ changes' constraint"
  - "Did not attempt the plan's 'second miss = D-03 failure' framing for round 2, since round 2 DID catch E01 ready-while-siblings-transferring cleanly (the named retry condition never applied) -- the D-03 escalation here is for the D-06(c) defect itself, not an E01-catch miss"

patterns-established: []

requirements-completed: []

# Metrics
duration: ~75min
completed: 2026-10-22
status: gaps_found
---

# Phase 122 Plan 05: SAFE-01 Import and Auto-Delete Live Acceptance Summary

**Live-sandbox evidence for three of four D-06 import/auto-delete safeguards (Waiting hold + one-shot release, early per-episode credit, arm-on-commit with a genuine 300s auto-delete) all PASS; the fourth (deferral/revalidation) surfaced a real, reproducible defect where a deferred webhook notice for a still-transferring child is incorrectly dropped instead of credited — CHECK_STATUS=FAIL, routed to the Task 3 owner checkpoint per D-03, no source changes made.**

## Performance

- **Duration:** ~75 min (including two live NAS scenario runs, one ~6 min, one ~65 min including the 330s+ real auto-delete wait)
- **Started:** 2026-10-22T19:58:00Z (approx.)
- **Completed (this stopping point):** 2026-10-22T21:00:34Z
- **Tasks:** 2 of 3 completed (Task 1: run scenarios — complete, across two rounds; Task 2: write evidence — complete and committed; Task 3: checkpoint — **paused, awaiting owner decision**, per `<sequential_execution>`'s instruction to stop here since CHECK_STATUS is not PASS)
- **Files modified:** 1 (`122-SAFE01-EVIDENCE.md`)

## Accomplishments

- Confirmed `seedsyncarr-test` still on `DEV_PIN` (PR #134's staging image) before each run; production untouched throughout (no production container named by any command in this plan)
- **D-06(e) PASS:** both `SSA122.Alpha.S01` and `SSA122.Decoy.S01` held as `Completion hold for '<root>': No matching queue entry`; one-shot manual release (`?release_unverified=true`) queued only `SSA122.Alpha.S01`; the hold removal logged correctly as **"dropped"**, never "cleared" (D-16/D-17); `SSA122.Decoy.S01` never transferred
- **D-06(a) PASS:** three `Credited early import of '<child>' in '<root>' (root still transferring)` lines, all strictly before the root's commit
- **D-06(b) PASS:** `Scheduled auto-delete of 'SSA122.Alpha.S01' in 300 seconds` followed, **300.004 s later**, by `Auto-deleted local file 'SSA122.Alpha.S01'` — a real Timer firing, independently confirmed to precede this session's teardown by 15 minutes
- **D-06(c) FAIL:** two of three genuinely-incomplete-at-post-time child webhooks were correctly deferred then revalidated/credited later without being re-posted; the third (`SSA122.Alpha2.S01E04.mkv`, posted at 11% transferred) was permanently dropped via `Ignoring webhook import for 'SSA122.Alpha2.S01': not downloaded by SeedSyncarr (no transfer evidence)` 61 s later, and never recovered (`persist.imported_children` confirms it is permanently short one child)
- Diagnosed the root cause with exact file/line references (`controller.py:762-782`, `model_builder.py:505-547`) and proposed an unapplied, scoped fix for owner review — no code under `src/` was changed
- Full D-06 evidence (four scenario sections, numbered milestones, verbatim log blocks, both clocks, unit-test cross-references, and a cross-reference to `120-SON5-EVIDENCE.md` §SON5-02 for the real Sonarr-queue gate) committed to `122-SAFE01-EVIDENCE.md`

## Task Commits

1. **Task 1: Run scenarios (e), (a), (c), (b)** — no separate commit (no `files_modified` for this task per the plan; raw captures stayed in the NAS capture dir, cited verbatim in Task 2's commit)
2. **Task 2: Write the D-06 evidence sections with verdicts** - `1702f92` (docs)
3. **Task 3: D-03 failure review** - **paused at this checkpoint**, no commit yet (owner reply pending)

**Plan metadata:** not yet committed — plan is not complete (paused at Task 3's checkpoint).

## Files Created/Modified

- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` — added the "Plan 05: D-06 import/auto-delete scenarios" section: D-06(e)/(a)/(c)/(b) subsections each with numbered milestones, verbatim log blocks, both clocks, model-state proof, PASS/FAIL verdicts, unit-test cross-references, and a hygiene-scan note

(Raw captures — `log-SSA122.Alpha.S01-run1.txt`, `log-SSA122.Alpha2.S01-run2-fail.txt`, `model-a-*.json`, `model-a2-*.json`, `model-e-held.json`, `webhooks.log`, `state.env`, and the throwaway orchestration scripts `stage1.sh`/`stage2.sh`/`stage3.sh`/`round2.sh`/`model_tools.py` — live only in the NAS capture dir `/volume1/docker/v5test/results/safe01-122-20261022T195544Z`, per the plan's output spec; not committed to the repo.)

## Decisions Made

See `key-decisions` in frontmatter. In summary: two live runs were needed (a test-harness sizing fix after round 1, not a product issue), and round 2 surfaced a genuine D-06(c) defect that is now routed to the owner via Task 3's checkpoint rather than being fixed inline, per D-03 and this plan's "no `src/` changes" constraint.

## Deviations from Plan

### Auto-fixed Issues (test harness only — no product code touched)

**1. [Rule 3 - Blocking] Fixed an incorrect "root committed" wait sentinel in my own orchestration script**
- **Found during:** Task 1, round 1 (`SSA122.Alpha.S01`)
- **Issue:** My polling script waited specifically for the log line `Committing '<root>' to downloaded list on import evidence` as the signal that the root had been accepted. In this run, the root was actually accepted via a different, equally-valid path (`Import credit for '<root>' applied on commit`, since all three early credits plus the independent scanner-driven commit happened before any webhook event hit the `has_evidence` branch), so the literal "Committing..." line never appeared and my script timed out after 20 minutes and ran teardown — even though the underlying product had already completed the entire scenario correctly and successfully, including the real 300s auto-delete, within the first ~6 minutes.
- **Fix:** Re-pointed the wait condition at the universal "armed" signal (`Scheduled auto-delete of '<root>'`, which only ever follows one of the three possible acceptance lines), for round 2's script.
- **Files modified:** none under `src/` or `.planning/` — this was a throwaway NAS-side orchestration script (`stage3.sh` / `round2.sh`), not a committed artifact.
- **Verification:** Round 1's own log (already complete and correct) was used directly as evidence for D-06(a)/(b)/(e); round 2's corrected script reached its own "Scheduled auto-delete" checkpoint successfully.
- **Committed in:** not applicable (no repo file changed by this fix).

---

**Total deviations:** 1 auto-fixed (test-harness only, Rule 3), plus 1 genuine, unresolved product-level finding (D-06(c), routed to Task 3's checkpoint, not auto-fixed).
**Impact on plan:** The harness fix was necessary to complete Task 1 and is fully contained to a non-repo throwaway script. The D-06(c) finding is NOT a deviation auto-fix — per D-03 and the plan's explicit "no `src/` changes" constraint, it is diagnosed and documented only, with the proposed fix left for the owner to approve or reject at Task 3.

## Issues Encountered

- **Round 1 sibling sizes (48/160/200 MiB) transferred faster than expected even with `lftp.rate_limit=4194304` applied** (confirmed live: `rate_limit changed: 0 -> 4194304`) — likely because the rate limit applies per-connection/per-pget-segment rather than as a true aggregate cap across the four parallel file transfers. All four children finished within ~17s of release, so every webhook landed on an already-fully-transferred child (root still transferring), which is a valid demonstration of D-06(a) but never D-06(c)'s "child itself still incomplete" condition. Resolved for round 2 by raising sibling sizes to 300/800/1200 MiB.
- **The exact-secret scan (`grep -c -F -f secret ...`) could not be completed for either run as originally sequenced** — both runs' `fail_exit` paths ran `teardown.sh` (which deletes the session's `secret` file on restore) before reaching the evidence-save/secret-scan phase of my own script. Substituted a hygiene-word scan (`password|api_key|Authorization|X-Webhook-Signature`, zero hits in both runs) plus a code-level argument (the signing script never echoes the secret) — documented transparently in the evidence file rather than overclaiming an exact-match result that was never actually run. This is a test-harness gap, not a product-security gap: the actual secret value is never written to any of these files by design (confirmed by reading `webhook-post.sh`).
- **The genuine D-06(c) finding itself** — see Task 3 checkpoint below.

## User Setup Required

None — no external service configuration required.

## Task 3: Owner decision (2026-10-22)

Owner chose **"Fix in this phase (Recommended)"** for the D-06(c) failure. The orchestrator independently confirmed the diagnosis against `src/python/controller/controller.py` (evidence gate, ~lines 757-800): a deferred child notice is dropped when the directory root's state is no longer DOWNLOADING/QUEUED (all children individually DOWNLOADED) while the root's own `local_size < remote_size` and it is not yet in `downloaded_file_names`.

Route: `/bm:plan-phase 122 --gaps` → narrow RED-first fix (keep or credit the notice instead of dropping it for a root we are actively tracking), pushed to the same PR #134. CI produces a new staging image, the sandbox is re-pinned (new DEV_PIN), and Plan 05's scenarios are rerun on it before Plans 06-09. One PR per phase still applies.

## Next Phase Readiness

- **Blocked:** Task 3's checkpoint is open. Plans 06/07 (restart persistence, extraction) and Plan 08 (SAFE-02 reconciliation) should not proceed to close SAFE-01 as passed until the owner has responded to the D-06(c) finding below. Plans 06/07's own scenarios are independent of this specific defect and could in principle still run, but SAFE-01 as a whole cannot be marked passed while D-06(c) is open.
- Sandbox (`seedsyncarr-test`) is fully restored: `lftp.rate_limit=0`, `webhook_secret` empty, no synthetic material on the seedbox or under `/downloads`, confirmed via both teardown runs' `SANDBOX_RESTORED ok` and independent `ls`/`stat` checks.
- Production (`seedsyncarr`) was never named by any command this plan; untouched.

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Stopped at: Task 3 checkpoint (CHECK_STATUS=FAIL, D-06(c))*

## Self-Check: PASSED

- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` (modified, contains the new Plan 05 sections)
- FOUND commit `1702f92` (`git log --oneline --all | grep 1702f92`)
- Log lines quoted in the evidence file were read directly from the live sandbox app log (`/volume1/docker/v5test/seedsyncarr/log/seedsyncarr.log`) during this plan's execution, not inferred; the 300.004s auto-delete timing and the 15-minute gap before teardown were computed directly from those same log timestamps.
