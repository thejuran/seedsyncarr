---
phase: 122-safety-acceptance-and-logging-fixes
plan: 08
subsystem: infra
tags: [sandbox-restore, credential-hygiene, owner-checkpoint, safe01-verdict]
status: paused

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes (plan 07)
    provides: "D-07 extraction staging/auto-delete re-arm PASS on the fixed DEV_PIN; same capture dir reused by this plan's final teardown"
provides:
  - "Owner decision on rotating the exposed sandbox Sonarr key (declined this session; follow-up flagged for Plan 09)"
  - "seedsyncarr-test restored to its original IMAGE_PIN_L0 (1.7.6) pin, independently re-verified in a fresh session"
  - "A Rule 1 bug fix in the committed 122-teardown.sh (--final compose-file regex did not match a digest-only image reference)"
  - "SAFE-01 verdict table (all six required scenarios PASS) recorded in 122-SAFE01-EVIDENCE.md"
  - "119-VERIFICATION.md linked to the completed extraction/import evidence"
affects: ["122-09 (SAFE-02 reconciliation; picks up the owner-later rotation follow-up for ROADMAP)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  modified:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md
    - .planning/phases/119-safety-follow-ups-and-1-7-5-release/119-VERIFICATION.md
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh

key-decisions:
  - "Owner declined sandbox Sonarr key rotation this session (verbatim: \"I'll replace it myself later\", option owner-later). No rotation performed; the follow-up is recorded in the evidence file for Plan 09 to add to ROADMAP.md's Operator follow-ups, per the plan's own instruction for this choice."
  - "This SUMMARY is written with status: paused because Task 3 (owner review of the SAFE-01 verdict) is a blocking checkpoint that has not yet been answered. Task 1 and Task 2 are complete and committed; STATE.md/ROADMAP.md updates and the final metadata commit are deferred to the continuation agent after the owner replies."

patterns-established: []

requirements-completed: []

# Metrics
duration: ~9min (Tasks 1-2 only; Task 3 pending)
completed: null
---

# Phase 122 Plan 08: Sandbox Restore and SAFE-01 Verdict Summary (PAUSED at Task 3 checkpoint)

**Sandbox restored to its original 1.7.6 pin after fixing a Rule 1 bug in the teardown script's image-restore regex; SAFE-01 verdict recorded as PASSED (all six required scenarios); awaiting owner review before the plan closes.**

## Performance

- **Duration so far:** ~9 min (Tasks 1-2)
- **Started:** 2026-10-23T19:11:32Z
- **Paused at:** 2026-10-23T19:20:14Z (Task 3 checkpoint, awaiting owner reply)
- **Tasks:** 2 of 3 completed (Task 3 is a blocking checkpoint, not yet answered)
- **Files modified:** 3

## Accomplishments

- **Task 1 (owner decision):** Presented to the owner by the orchestrator before this execution; owner's verbatim reply was **"I'll replace it myself later"** (option `owner-later`). No rotation performed — `sonarr-v5`'s `<ApiKey>` and `seedsyncarr-test`'s `sonarr_api_key` were never read, written or printed this session. Recorded in the evidence file as a follow-up for Plan 09 to add to ROADMAP.md's "Operator follow-ups" section.
- **Task 2 (restore, verdict):**
  - Confirmed preflight: sandbox still on the fixed `DEV_PIN`; `rate_limit`/`delay_seconds`/`webhook_secret` already restored by 122-07's own non-`--final` teardown; zero synthetic material anywhere; production fingerprint unchanged from baseline
  - First `bash teardown.sh --final` run **FAILED** at the image-restore check — diagnosed live: the `--final` compose-file awk regex only matched a *tagged* image reference (`ghcr.io/thejuran/seedsyncarr:TAG`), but 122-11's re-pin left the compose line as a *digest-only* reference (`...seedsyncarr@sha256:...`), so the line was never rewritten and the sandbox stayed on `DEV_PIN`. This is a Rule 1 bug in the committed test-harness script (not product code); fixed the regex to match either form, verified with `bash -n` and `shellcheck` (clean), copied the fix to the NAS capture dir (`sha256sum`-confirmed byte-identical), and re-ran
  - Second and third `teardown.sh --final` runs both printed `SANDBOX_RESTORED ok` (idempotent, identical result)
  - Fresh-session (`ssh nas`) check confirmed: compose line and `docker inspect .Config.Image` both equal `IMAGE_PIN_L0` exactly (`ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0...`); `webhook_secret` length 0; `lftp.rate_limit=0`; `autodelete.delay_seconds=300`; zero `SSA122.*` material on the seedbox, under `/volume1/data/v5test/torrents`, or in the sandbox's `.seedsyncarr-extracting` staging dir
  - Production `seedsyncarr` fingerprint (`Id`, image, `StartedAt`) confirmed byte-identical to the Plan 04 baseline, read-only, never named by any write command
  - Wrote the "Plan 08" evidence section (rotation decision, both teardown attempts with the bug diagnosis, fresh-session readings, production comparison) and the "SAFE-01 verdict" table: all six required scenarios (D-06(a)-(e), D-07) plus the independent D-06(c) Foxtrot repeat are **PASS** → overall **SAFE-01: PASSED**
  - Appended a dated, additions-only note to `119-VERIFICATION.md` linking the completed extraction/import half to the evidence file
  - Removed the now-unneeded NAS capture dir (`safe01-122-20261023T165741Z`) after the evidence commit, per the plan's output spec (raw captures are not committed)

## Task Commits

1. **Task 1: Owner decision on rotating the sandbox Sonarr API key** — no separate commit (decision recorded in this SUMMARY only, per the plan's own instruction; nothing was changed on disk)
2. **Task 2: Final teardown, fresh-session restore check, production fingerprint, SAFE-01 verdict** — `ce17b12` (docs)
3. **Task 3: Owner review of the SAFE-01 verdict** — **PENDING** (blocking checkpoint; see below)

**Plan metadata:** not yet committed (plan not complete — pending Task 3)

## Files Created/Modified

- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` — appended "Plan 08: Sandbox key-rotation decision, final restore, production fingerprint, SAFE-01 verdict" (rotation outcome, both teardown attempts with the regex-bug diagnosis and fix, fresh-session readings, production comparison, SAFE-01 verdict table)
- `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-VERIFICATION.md` — appended a dated "Extraction/import half — completed by Phase 122" note (additions-only; existing content untouched)
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh` — fixed the `--final` compose-file regex to match both tagged and digest-only image references

## Decisions Made

See `key-decisions` in frontmatter. In summary: (1) owner declined rotation this session, recorded verbatim, follow-up flagged for Plan 09; (2) this SUMMARY is paused pending Task 3's owner review — STATE.md/ROADMAP.md updates and the plan-metadata commit will follow once the owner replies.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `teardown.sh --final`'s compose-file regex, which did not match a digest-only image reference**
- **Found during:** Task 2, first `teardown.sh --final` run.
- **Issue:** The `--final` image-pin restore used `awk` with the pattern `/^[[:space:]]*image:[[:space:]]*ghcr\.io\/thejuran\/seedsyncarr:/` to locate and rewrite the `seedsyncarr-test` compose image line. After 122-11's re-pin, that line read `image: ghcr.io/thejuran/seedsyncarr@sha256:e3941f97...` — a digest-only reference with `@` immediately after the repository name, never a `:`. The regex never matched, so the line was rewritten byte-identical (still `DEV_PIN`), and `compose up -d` "restored" the sandbox to the image it was already running. The script's own post-check caught this correctly (`CHECK image=restored FAIL`, `SANDBOX_RESTORED FAIL image_restore`) — not a silent miss, but a real block on this task's required D-02 outcome.
- **Fix:** Changed the regex to `/^[[:space:]]*image:[[:space:]]*ghcr\.io\/thejuran\/seedsyncarr[:@]/`, matching both a tagged (`:1.7.6`) and a digest-only (`@sha256:`) current reference. Applied to the committed file (`.planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh`), verified with `bash -n` and `shellcheck` (both clean), then copied to the NAS capture dir via `ssh ... cat >`, with `sha256sum` confirming the NAS copy was byte-identical to the local repo file before re-running.
- **Files modified:** `.planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh`
- **Verification:** Re-ran `teardown.sh --final` twice after the fix; both runs printed `SANDBOX_RESTORED ok` with `CHECK image=restored ok`, and a separate fresh `ssh nas` session independently confirmed the compose line and `docker inspect .Config.Image` both equal `IMAGE_PIN_L0` exactly.
- **Committed in:** `ce17b12` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1, test-harness script only — `.planning/phases/...122-teardown.sh` is a committed planning/test artifact, not product code under `src/`).
**Impact on plan:** The fix was required to complete this task's own D-02 restore requirement; it did not touch any `src/` code, did not affect any SAFE-01 live-check outcome (all of which had already completed in prior plans), and is now re-usable by any future phase that re-pins and restores this sandbox.

## Issues Encountered

- See the Rule 1 deviation above — the only issue this session, resolved without touching product code.

## User Setup Required

None — no external service configuration required this session. (Owner follow-up: the declined sandbox Sonarr key rotation is flagged for Plan 09 to add to ROADMAP.md's "Operator follow-ups"; no action needed from this plan.)

## Next Phase Readiness — BLOCKED ON TASK 3

**This plan is not complete.** Task 3 (owner review of the SAFE-01 verdict) is a blocking `checkpoint:human-verify` and has not been answered. A continuation agent must:
1. Receive the owner's reply ("approved" or stated concerns)
2. Record it verbatim in this SUMMARY (replacing `status: paused` with a completed state)
3. Run the STATE.md/ROADMAP.md updates and requirements marking (if the owner approves)
4. Create the final metadata commit

Until then:
- Sandbox `seedsyncarr-test` is restored to `IMAGE_PIN_L0` (`ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0...`), independently re-verified in a fresh session; the NAS capture dir has been removed
- Production `seedsyncarr` is confirmed byte-identical to its Plan 04 baseline throughout this plan
- The SAFE-01 verdict (all six scenarios PASS) is recorded in `122-SAFE01-EVIDENCE.md` and linked from `119-VERIFICATION.md`, awaiting the owner's review, not yet acted on further

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Paused: 2026-10-23 (Task 3 checkpoint)*

## Self-Check: PASSED (for Tasks 1-2 only; Task 3 not yet executed)

- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` (modified, contains the new "Plan 08" section and "SAFE-01 verdict" table)
- FOUND: `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-VERIFICATION.md` (modified, additions-only)
- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh` (modified, regex fix)
- FOUND commit `ce17b12` (`git log --oneline --all | grep ce17b12`)
- All teardown transcripts, fresh-session readings and the production fingerprint quoted above and in the evidence file were read directly from live `ssh nas` command output during this plan's execution, not inferred; the `SANDBOX_RESTORED ok` result was independently re-run twice after the regex fix, and the fresh-session restore check was run as a separate `ssh nas` call, not reused from the teardown script's own output.
