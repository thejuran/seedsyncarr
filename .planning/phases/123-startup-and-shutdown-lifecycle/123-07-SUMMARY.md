---
phase: 123-startup-and-shutdown-lifecycle
plan: 07
subsystem: infra
tags: [gap-closure, live-acceptance, nas-sandbox, final-restore, life01-verdict, owner-checkpoint, pr-deep-review]
status: complete

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: 17
    provides: "Gap-round-2 active-transfer cycles A1/A2 + A1r rerun, final idle cycle I3, CHECK_STATUS_GAP2=PASS, session teardown SANDBOX_RESTORED ok"
provides:
  - "Per-cycle restart evidence for the gap-round-2 build (DEV_PIN_GAP2) in 123-LIFE-EVIDENCE.md, with detector-window counts for every earlier build and pointers to the two failed historical rounds (123-06, GAP-1)"
  - "Sandbox seedsyncarr-test restored to IMAGE_PIN_L0 (1.7.6) via teardown.sh --final, independently re-verified in a fresh ssh session; production byte-identical before/after"
  - "Phase 123 verdict: requirement/decision table (LIFE-01, LIFE-02, SC1-4, D-01..D-07) mapped to evidence, '**Phase 123 live restart check: PASSED**'"
  - "Owner review of a PR #137 vibe-check deep review (5 reviewers, 0 findings >=70) plus the verdict; verbatim reply 'approve, backlog both items'; two findings logged to deferred-items.md rather than fixed in-phase"
affects: ["REQUIREMENTS.md (LIFE-01, LIFE-02)", "STATE.md position/decisions", "ROADMAP.md phase-123 progress"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md
    - .planning/phases/123-startup-and-shutdown-lifecycle/deferred-items.md

key-decisions:
  - "Task 3 resumed 2026-10-26 as a continuation agent: Tasks 1-2 (restart-cycle evidence, final sandbox restore, Phase 123 verdict) were already committed in a prior session (70f47cb, 7cd365b) and were verified present on the branch, not redone."
  - "Before approving, the owner ran a vibe-check deep review of PR #137 (5 reviewers: bugs/architecture on Opus, security, impact, language-python; 0 findings scored >=70; 9 filtered as sub-threshold/duplicates; impact verdict 'shippable as-is'). Owner's verbatim reply: 'approve, backlog both items', naming (1) WebAppJob.cleanup() lacking the per-step isolation this phase added elsewhere, and (2) ControllerJob.execute() non-AppError failures bypassing the RECOV-01 auto-restart (deliberate setup-only scope per D-04/D-05). Both logged to deferred-items.md as backlog items (not fixed in-phase), plus a low-confidence Lftp.exit() double-failure masking sub-note under the existing bounded-wait item."
  - "Per the plan's own Task 3 acceptance criteria, requirements-completed is set to [LIFE-01, LIFE-02] because the reply is approve-equivalent AND the verdict already reads '**Phase 123 live restart check: PASSED**'."

patterns-established: []

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: Tasks 1-2 completed in a prior session (see commits 70f47cb, 7cd365b); this session (Task 3: owner review + write-up) ~15min
completed: 2026-10-26
---

# Phase 123 Plan 07: Final Verdict, Sandbox Restore, and Owner Sign-off Summary

**Closed Phase 123 on the owner's verbatim "approve, backlog both items": the gap-round-2 restart evidence and Phase 123 verdict (PASSED) were already committed, the sandbox is restored to 1.7.6, and a pre-approval PR #137 deep review's two findings are logged to the backlog instead of fixed in-phase — LIFE-01/LIFE-02 are complete.**

## Performance

- **Tasks 1-2 completed:** prior session (commits `70f47cb`, `7cd365b`)
- **Task 3 (this session) started:** 2026-10-26 (continuation agent spawn)
- **Task 3 (this session) completed:** 2026-10-26
- **Tasks:** 3 of 3 completed
- **Files modified:** 2 (`123-LIFE-EVIDENCE.md`, `deferred-items.md`) + this SUMMARY

## Accomplishments

- **Task 1 (restart-cycle evidence + deferred findings, prior session):** Appended "## Restart cycles on the Phase 123 build (gap round 2, 123-16/123-17)" to `123-LIFE-EVIDENCE.md` with one `### Cycle` subsection per gap-round-2 cycle (I1, I2, A1, A2, A1r, I3), the detector-window counts for the three earlier builds (1.7.6, OLD_DEV_PIN/123-04, DEV_PIN_GAP/123-08), and "### D-01 lftp half" comparing the gap-round-2 counts against every earlier round. Created `deferred-items.md` with the out-of-scope findings (`Controller.__init__` eager lftp spawn, `Seedsyncarr.run` shutdown-path `persist()` masking risk, the kept DEFER-SHUTDOWN sleep, the pre-existing missing `Exited successfully` line, and the GAP-2 bounded-wait owner flag). Committed `70f47cb`.
- **Task 2 (final sandbox restore, fresh-session check, production fingerprint, verdict, prior session):** Ran `teardown.sh --final`, confirmed `SANDBOX_RESTORED ok`, independently re-verified `.Config.Image` == `IMAGE_PIN_L0` and an empty production-fingerprint diff in a second `ssh nas` session. Appended "## Phase 123 verdict" mapping LIFE-01, LIFE-02, SC1-4, D-01 (both halves), D-02, D-03, D-04/D-05, D-06 and D-07 to their evidence, concluding "**Phase 123 live restart check: PASSED**" (basis: gap-round-2 `CHECK_STATUS` = PASS, every one of the six cycle rows PASS). Committed `7cd365b`.
- **Task 3 (owner review, this session):** Verified both prior commits exist on `gsd/phase-123-startup-and-shutdown-lifecycle` (`git log --oneline`). Before replying, the owner ran a vibe-check deep review of PR #137 (5 reviewers: bugs/architecture on Opus, security, impact, language-python; 0 findings scored >=70; 9 filtered as sub-threshold/duplicates; impact verdict "shippable as-is"). Two findings were surfaced and the owner chose to backlog both rather than fix in-phase:
  1. `WebAppJob.cleanup()` (`src/python/web/web_app_job.py`) lacks the per-step isolation this phase added to `ScanManager`/`FileOperationManager`/`Controller`: if `self.__app.stop()` raises, `self.__server.stop()` and `self.__server_thread.join()` are skipped (and `MyWSGIRefServer.stop()` can itself raise `AttributeError` when its inner server is still `None`).
  2. Only `ControllerJob.setup()` failures are wrapped into `ControllerError` for the RECOV-01 auto-restart; a non-`AppError` raised later from `Controller.process()` (`ControllerJob.execute()`) still ends the process instead of auto-restarting — the deliberate setup-only scope per D-04/D-05, not a regression.

  The owner's reply, recorded exactly as given: **"approve, backlog both items"**. Appended "## Owner review (Phase 123 verdict)" to `123-LIFE-EVIDENCE.md` (append-only, `git diff` shows 0 removed lines) recording the deep-review context, the two findings, and the verbatim reply. Added two new sections to `deferred-items.md` (`WebAppJob.cleanup() lacks per-step isolation` and `ControllerJob.execute() non-AppError failures bypass RECOV-01 auto-restart`) in the existing Found during / Observed / Why out of scope / Status format, plus a low-confidence sub-note under the existing "GAP-2 bounded wait in Lftp.exit()" item about a possible `Lftp.exit()` double-failure masking shape (3 of 5 deep-review reviewers, none scoring >=70). Committed `0d9fcc8`.

## Task Commits

1. **Task 1: Write the per-cycle restart evidence and the deferred findings** — `70f47cb` (docs, prior session)
2. **Task 2: Final sandbox restore (--final), fresh-session check, production fingerprint, Phase 123 verdict** — `7cd365b` (docs, prior session)
3. **Task 3: Owner review of the Phase 123 verdict** — owner replied verbatim **"approve, backlog both items"**. No code or sandbox change was made in this task. The owner sign-off and the two deep-review findings were recorded in `0d9fcc8` (docs, this session).

**Plan metadata:** committed separately below (STATE.md/ROADMAP.md update).

## Files Created/Modified

- `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` — appended "## Restart cycles on the Phase 123 build (gap round 2, 123-16/123-17)", "### Detector check", "### D-01 lftp half" (Task 1); "### Final teardown (`teardown.sh --final`)", "### Fresh-session restore check", "### Production unchanged", "## Phase 123 verdict" and its subsections (Task 2); "## Owner review (Phase 123 verdict)" (Task 3). All three commits append-only (`git diff HEAD~1 | grep -c "^-[^-]"` = 0 on each).
- `.planning/phases/123-startup-and-shutdown-lifecycle/deferred-items.md` — created with five out-of-scope findings (Task 1); appended a low-confidence `Lftp.exit()` double-failure masking sub-note plus two new backlogged findings from the PR #137 deep review (Task 3).

## Decisions Made

See `key-decisions` in frontmatter. In summary: this was a continuation agent resuming at the Task 3 checkpoint. Tasks 1-2 were confirmed already complete and committed, not redone. The owner reviewed the Phase 123 verdict after running an independent vibe-check deep review of PR #137, which found no findings above the scoring threshold but surfaced two lower-priority items; the owner's decision was to backlog both rather than block the phase on them. Per the plan's Task 3 acceptance criteria, `requirements-completed` is set to `[LIFE-01, LIFE-02]`.

## Deviations from Plan

None in this task. The plan's Task 3 action was to present the verdict, pause, and record the reply verbatim — this executor did exactly that; the two deep-review findings were recorded per the resume instructions (logged to deferred-items.md as items 7/8, not auto-fixed), consistent with Rule 4 (architectural/product scope — a future phase decision, not this phase's correctness requirement) rather than Rules 1-3.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. Owner action (review the Phase 123 verdict, including the pre-approval deep review of PR #137) is complete: verbatim reply **"approve, backlog both items"**.

## Next Phase Readiness

- Plan 123-07 is complete. LIFE-01 and LIFE-02 are closed: `requirements-completed: [LIFE-01, LIFE-02]`, owner-approved on the build that will ship (`DEV_PIN_GAP2`, `sha256:7f354c149f...`), with the Phase 123 live restart check reading **PASSED**.
- The sandbox (`seedsyncarr-test`) is back on `IMAGE_PIN_L0` (1.7.6), fresh-session verified. Production (`seedsyncarr`) is confirmed byte-identical throughout this plan.
- Branch `gsd/phase-123-startup-and-shutdown-lifecycle` / PR #137 is unchanged except for this plan's docs-only commits; no merge, no new PR, no `gh pr ready`, no push. Merging PR #137 stays a separate owner decision after full phase verification.
- Two findings from the PR #137 deep review are now in `deferred-items.md` for backlog triage: `WebAppJob.cleanup()`'s missing per-step isolation, and `ControllerJob.execute()`'s non-`AppError` failures bypassing RECOV-01 auto-restart.
- Owner follow-ups (unchanged, carried forward): rotate the sandbox `sonarr-v5` API key (declined 2026-10-23, `owner-later`); remove the `Hacks.S04E01` test torrent from sandbox Deluge once seed time is met.

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Status: complete — owner-approved 2026-10-26*

## Self-Check: PASSED

- FOUND: `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (contains "Phase 123 live restart check: PASSED" exactly once, and "Owner review (Phase 123 verdict)" with the verbatim reply)
- FOUND: `.planning/phases/123-startup-and-shutdown-lifecycle/deferred-items.md` (contains the two new backlogged findings plus the `Lftp.exit()` double-failure masking sub-note)
- FOUND commit `70f47cb` (`git log --oneline --all | grep 70f47cb`)
- FOUND commit `7cd365b` (`git log --oneline --all | grep 7cd365b`)
- FOUND commit `0d9fcc8` (`git log --oneline --all | grep 0d9fcc8`)
- `git diff HEAD~1 -- .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md | grep -c "^-[^-]"` = 0 for the owner-review commit (append-only, verified directly, not assumed)
- The owner's verbatim reply "approve, backlog both items" is recorded above exactly as given to this executor, with no rewording. `requirements-completed: [LIFE-01, LIFE-02]` is set because both of the plan's own Task 3 conditions hold (reply is approve-equivalent; "## Phase 123 verdict" already states "**Phase 123 live restart check: PASSED**", confirmed by direct grep against the evidence file, not inferred).
- Tasks 1-2's claims (restart-cycle evidence, final sandbox restore, Phase 123 verdict) rest on the prior session's own commits (`70f47cb`, `7cd365b`), confirmed present on this branch by `git log --oneline` at the start of this continuation; they were not re-verified line-by-line in this session beyond confirming the commits exist, per the continuation-agent instruction not to redo completed tasks.
