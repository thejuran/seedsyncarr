---
phase: 122-safety-acceptance-and-logging-fixes
plan: 09
subsystem: infra
tags: [incident-records, reconciliation, read-only-production, owner-checkpoint]
status: paused

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes (plan 08)
    provides: "SAFE-01 verdict PASSED and owner-approved; sandbox restored to IMAGE_PIN_L0; owner declined sandbox Sonarr key rotation this session (follow-up for this plan's ROADMAP update)"
provides:
  - "Both open incident records (done-group-no-auto-delete.md, extract-staging-autodel-rearm.md) reconciled per-finding against SAFE-01 evidence and live, read-only production facts"
  - "Owner cleanup checklist delivered for both records, built from live production reads (Sonarr/Radarr API, NAS filesystem, production log)"
  - "ROADMAP.md Backlog carries extract-staging deferred items C-G by name; Operator follow-ups carries the declined sandbox key rotation"
affects: ["122-09 Task 3 (close rule, pending owner reply)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  modified:
    - .planning/debug/done-group-no-auto-delete.md
    - .planning/debug/extract-staging-autodel-rearm.md
    - .planning/ROADMAP.md

key-decisions:
  - "Task 1 only; this plan is PAUSED at Task 2, a blocking checkpoint:decision. Per the orchestrator's explicit instruction, this decision is not auto-answered under any circumstance (including auto-advance config) — it requires the owner's own reply."

patterns-established: []

requirements-completed: []

# Metrics
duration: ~6min (Task 1 only; Task 2/3 pending)
completed: null
---

# Phase 122 Plan 09: Reconcile Incident Records Against SAFE-01 Evidence Summary (PAUSED)

**Task 1 complete: both open incident records now carry per-finding "Reconciliation (Phase 122)" tables citing the Phase 119 fix commits and SAFE-01 evidence, plus an owner cleanup checklist built from live read-only production facts. Paused at Task 2 (owner checkpoint) before Task 3 (close rule) runs.**

## Performance

- **Duration:** ~6 min (Task 1 only)
- **Started:** 2026-10-23T19:34:20Z (session resume)
- **Paused:** 2026-10-23T19:43:45Z
- **Tasks:** 1 of 3 completed (Task 2 is the active checkpoint; Task 3 not started)
- **Files modified:** 3

## Accomplishments

- **Task 1 (read-only production inspection, per-finding tables, owner checklist, backlog carry-forward):**
  - Read-only production checks (NAS `seedsyncarr`, still 1.7.6; no write command issued; all commands and timestamps below are verbatim from this session):
    - `ls -ld`/`du -sb` at NAS host UTC `2026-10-23T19:37:42Z` (NAS local `14:37:42 -05`) on the exact Days of Hope, The Burbs and Obsession paths under `/volume1/data/torrents/`, and on `/volume1/data/torrents/.seedsyncarr-extracting` — all four returned "No such file or directory" (all absent)
    - `grep` of `/volume1/docker/seedsync/log/seedsyncarr.log` (covers 2026-08-27 onward, spans both incidents) for each root name, capturing first/last occurrences — Days of Hope's last line is the owner's own `Action.DELETE_LOCAL` command on 2026-10-16 22:03:32; The Burbs' last lines show extraction completing then the owner's own `Action.DELETE_LOCAL` ~19 min later on 2026-09-16 21:58:11
    - Sonarr GET `/api/v3/episode?seriesId=815` and `/api/v3/episodefile?seriesId=815` (key read into a shell variable, never printed): Days of Hope has all 4 episode files, total `8,007,628,364` B, exactly the original torrent's full size
    - Radarr GET `/api/v3/movie` (key read into a shell variable, never printed), filtered to The Burbs and Obsession: The Burbs movieFile is `38,482,836,588` B (exact original remux size); Obsession movieFile is `55,389,018,125` B (full-size, not the previously-truncated `54,676,946,944` B — but ~88 MB / 0.16% different from the `55,477,377,022` B originally recorded as the complete remote file, flagged transparently to the owner rather than smoothed over)
    - Read-only `controller.persist` check: `imported_children` still shows the historical pre-fix bookkeeping (Days of Hope part 4 only; Burbs root-level grandfather entry) — expected per the research note that this dict is historical, not a presence signal, and production has not yet received the 122-10 fix (ships in 1.8.0)
  - Built "## Reconciliation (Phase 122)" sections in both records:
    - `done-group-no-auto-delete.md`: rows for Case A (Days of Hope) and Case B (Obsession), both **verified fixed (evidence)**, citing Phase 119 Plan 05 (Case A) and Plans 04/06/07/08/12 (Case B) commits against the SAFE-01 D-06(a)-(e) PASS verdicts, `120-SON5-EVIDENCE.md` §SON5-02, and `119-HUMAN-UAT.md`
    - `extract-staging-autodel-rearm.md`: rows for Bug 1, Bug 2, A, B, H (all **verified fixed (evidence)**, commit `8142929` + D-07 live evidence or named unit tests) and C, D, E, F, G (**deferred**, carried to ROADMAP by name)
  - Filled `done-group-no-auto-delete.md`'s previously-empty `fix:`/`verification:`/`files_changed:` Resolution fields
  - Added a "Remaining operator cleanup" checklist to both records, built entirely from the live facts above — every item in both records came back **verified absent** or **verified present/full-size**, meaning the owner appears to have already done this cleanup (Days of Hope and Obsession on 2026-10-14/16; The Burbs same night as its 2026-09-16 incident), but per the plan's own close rule (D-12) this still requires the owner's explicit confirmation before either record can close
  - Set both records' frontmatter `status:` to `fixes_verified_cleanup_pending` and `updated:` to 2026-10-23
  - Added 5 "### Deferred: Extract-staging ..." entries to `ROADMAP.md`'s Backlog (items C-G, by name, each citing the source record)
  - Added the declined sandbox `sonarr-v5` API key rotation to `ROADMAP.md`'s "Operator follow-ups" (122-08 flagged this; owner's verbatim reply was "I'll replace it myself later")
  - Verified: `grep -c "Reconciliation (Phase 122)"` = 1 in each record; `grep -c "### Deferred: Extract-staging"` in ROADMAP.md = 5; `grep -n '^fix: ""\|^verification: ""'` on done-group = no matches; neither record's status is `resolved`, neither file moved; post-commit deletion/untracked-file checks both clean

## Task Commits

1. **Task 1: Read-only production inspection, per-finding tables, filled fields, owner checklist, backlog carry-forward** — `27fb1ac` (docs)
2. **Task 2: Owner confirms production cleanup status per record** — PAUSED, checkpoint:decision, not yet answered
3. **Task 3: Apply the close rule and update ROADMAP operator follow-ups and STATE** — not started (blocked on Task 2)

## Files Created/Modified

- `.planning/debug/done-group-no-auto-delete.md` — added "Reconciliation (Phase 122)" section (Case A/B tables + cleanup checklist), filled `fix`/`verification`/`files_changed`, status → `fixes_verified_cleanup_pending`
- `.planning/debug/extract-staging-autodel-rearm.md` — added "Reconciliation (Phase 122)" section (Bug 1/2, A/B/H/C/D/E/F/G table + cleanup checklist), status → `fixes_verified_cleanup_pending`
- `.planning/ROADMAP.md` — 5 new Backlog "### Deferred: Extract-staging ..." entries; 1 new Operator follow-up (sandbox key rotation)

## Decisions Made

Task 1 followed the plan as specified; all findings/status/checklist content is derived directly from live, read-only production reads and the existing SAFE-01 evidence file, not inferred.

## Deviations from Plan

None — plan executed exactly as written for Task 1. No Rule 1-4 triggers encountered: all production commands were read-only exactly as the plan's threat model requires (T-122-35), and no architectural or ambiguous decision arose.

## Assumption Drift (advisory)

None material. One thing worth flagging transparently (not a drift, a live fact): the Obsession movie file's current size (`55,389,018,125` B) differs by ~88 MB (0.16%) from the `55,477,377,022` B the original debug session recorded as the complete remote file. This is recorded plainly in both the reconciliation table and the owner checklist rather than rounded off as an exact match.

## Issues Encountered

None.

## User Setup Required

None for Task 1. Task 2 is itself the required owner input — see "CHECKPOINT REACHED" in this session's response for the exact question and checklist.

## Next Phase Readiness

**This plan is PAUSED, not complete.** Task 1 is done and committed. Task 2 is a blocking `checkpoint:decision` that must not be auto-answered — it is awaiting the owner's reply (see the structured checkpoint message). Task 3 (apply the close rule, update ROADMAP/STATE) cannot run until that reply is received. No code changes, no record moves, no STATE.md changes have been made yet.

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Paused: 2026-10-23 (awaiting owner reply to Task 2)*

## Self-Check: PASSED (Task 1 only)

- FOUND: `.planning/debug/done-group-no-auto-delete.md` (modified, contains "Reconciliation (Phase 122)")
- FOUND: `.planning/debug/extract-staging-autodel-rearm.md` (modified, contains "Reconciliation (Phase 122)")
- FOUND: `.planning/ROADMAP.md` (modified, 5 "### Deferred: Extract-staging" entries + 1 new Operator follow-up)
- FOUND commit `27fb1ac` (`git log --oneline --all | grep 27fb1ac`)
- Every production command, timestamp and API result quoted above was read directly from live `ssh nas` / Sonarr / Radarr output during this session, not inferred from the original 2026-10-14/2026-09-16 debug records.
