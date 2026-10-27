---
phase: 125-lan-connection-tests
plan: 03
subsystem: release-process
tags: [lan-01, lan-02, nas-sandbox, live-check, d-09, digest-pin, restore]

# Dependency graph
requires:
  - phase: 125-lan-connection-tests
    plan: 02
    provides: "DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3, the staging image this plan deployed to the sandbox"
provides:
  - "125-livecheck.sh and 125-teardown.sh: committed, reusable sandbox scripts for the D-09 live check and idempotent restore"
  - "Live D-09 proof: container-name Test Connection succeeds on DEV_PIN with the Sonarr version, the same URL fails with the old message on 1.7.6, and the cloud-metadata address is refused with the new exact message"
  - "125-LAN-EVIDENCE.md: full live-check narrative, final restore, fresh-session verification, production-unchanged record and the Phase 125 verdict table (LAN-01/LAN-02/SC1-4/D-01..D-10)"
affects: [126-release-1.8.0]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EXIT-trapped live-check script with OK-guarded teardown fallback (trap '[ \"$OK\" = 1 ] || bash teardown.sh --final' EXIT), mirroring the 122/123 sandbox runbook"
    - "jq field extraction must use `// \"\"`, never `// empty`, when reading positional fixed-line output -- `empty` suppresses the line entirely instead of emitting blank, shifting every later field up by one line"

key-files:
  created:
    - .planning/phases/125-lan-connection-tests/125-livecheck.sh
    - .planning/phases/125-lan-connection-tests/125-teardown.sh
  modified:
    - .planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md

key-decisions:
  - "After the first live attempt's harness bug surfaced (NEGATIVE misread as FAIL despite a correct underlying response), restored the sandbox to IMAGE_PIN_L0 via that attempt's own teardown.sh --final, then ran a full fresh retry in a new capture dir rather than patching state in place -- keeps the evidence trail auditable per attempt"

patterns-established: []

requirements-completed: [LAN-01, LAN-02]

# Metrics
duration: ~55min
completed: 2026-10-27
---

# Phase 125 Plan 03: LAN Test Connection Live Check, Sandbox Restore and Phase 125 Verdict Summary

**Live D-09 proof on the NAS sandbox: the Phase 120 container-name Test Connection failure reproduces exactly on 1.7.6, then succeeds with Sonarr version 5.0.0.2800 on this PR's digest-pinned image, while a cloud-metadata destination is refused with the new exact message -- sandbox restored to 1.7.6 and fresh-session verified, production byte-identical throughout.**

## Performance

- **Duration:** ~55 min (Task 1 script authoring + Task 2 two live NAS sessions, including one harness-bug retry cycle), plus Task 3 owner checkpoint
- **Completed:** 2026-10-27
- **Tasks:** 3 of 3 (Task 3 owner checkpoint closed this session)
- **Files modified:** 1 (`125-LAN-EVIDENCE.md`); 3 created (`125-livecheck.sh`, `125-teardown.sh`, this summary)

## Accomplishments

- D-09 live-checked end to end: on `IMAGE_PIN_L0` (1.7.6), Test Connection to the Docker container name `http://sonarr-v5:8989` fails with the old "private/reserved" message (reproducing Phase 120 D-02); on `DEV_PIN` (this PR's digest), the identical URL succeeds and reports Sonarr version `5.0.0.2800` (LAN-01)
- LAN-02 live-confirmed: `http://169.254.169.254` is refused on `DEV_PIN` with the exact locked message "URL points to a link-local or cloud-metadata address, which is not allowed"
- Sandbox `sonarr_url` restored to its original value immediately after the negative check (read-back verified) and the image pin restored to `IMAGE_PIN_L0` via `teardown.sh --final` (`SANDBOX_RESTORED ok`), re-verified in a second, independent `ssh nas` session (image, compose line, `sonarr_url`, `/server/status` 200)
- Production `seedsyncarr` fingerprinted three times (before, after, final fresh session) and found byte-identical every time, matching `123-LIFE-EVIDENCE.md`'s recorded `StartedAt` exactly -- zero drift
- Found and fixed a harness bug (Rule 1) in `125-livecheck.sh`'s `tc()` helper during the first live attempt (see Deviations), then successfully reran the full check on a clean retry
- Wrote the Phase 125 verdict mapping LAN-01, LAN-02, SC1-4 and D-01 through D-10 to their unit and live evidence, concluding **"Phase 125 live check: PASSED"**
- Owner reviewed the verdict and the restore proof and replied verbatim "approved"; the orchestrator independently re-verified the restore in a separate `ssh nas` session before presenting it (see "Owner reply" below)

## Task Commits

1. **Task 1: Write and commit the live-check and teardown scripts** - `9abc12a` (docs)
2. **Task 1 (deviation fix, during Task 2's live run):** `d642a59` (fix) -- harness-only jq fallback bug, see Deviations
3. **Task 2: Run the live check on DEV_PIN, final restore, fresh-session check, evidence and verdict** - `7f2490a` (docs)
4. **Task 3: Owner review of the Phase 125 verdict** - owner reply and verdict closure recorded in this commit (docs, committed after this summary)

**Plan metadata:** Task 2's evidence and this summary's initial content were committed together as `docs(125-03): record LAN Test Connection live check, sandbox restore and Phase 125 verdict` (`7f2490a`). Task 3's owner-approval record is a separate follow-up commit.

## Files Created/Modified

- `.planning/phases/125-lan-connection-tests/125-livecheck.sh` - trapped D-09 live check: preflight, production fingerprint, URL-to-target, BEFORE (informational), DEV_PIN deploy, POSITIVE (LAN-01), NEGATIVE (LAN-02) with immediate URL restore, log counts, production re-fingerprint, CHECK_STATUS
- `.planning/phases/125-lan-connection-tests/125-teardown.sh` - idempotent `sonarr_url` and `--final` image-pin restore with the `SANDBOX_RESTORED` contract
- `.planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md` - appended "## Live check (D-09)" (both attempts), "### Final restore", "### Fresh-session restore check", "### Production unchanged" and "## Phase 125 verdict"

## Decisions Made

- Used `ssh nas 'cat > ...' < file` to place both scripts on the NAS instead of `scp`, which closed the connection in this session; checksums (`sha256sum`) confirmed byte-identical transfer before any script ran.
- After the harness bug surfaced mid-session (first capture dir left correctly restored on `sonarr_url`, but still on `DEV_PIN`'s image), restored fully to `IMAGE_PIN_L0` via that capture dir's own `teardown.sh --final` before starting a fresh capture dir for the retry, rather than reusing the contaminated `state.env`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `tc()`'s jq fallback used `empty` instead of `""`, shifting fixed-line output**
- **Found during:** Task 2, first live attempt (capture dir `lan01-125-20261027T195659Z`)
- **Issue:** `125-livecheck.sh`'s `tc()` helper printed `.success, (.version // empty), (.error // empty)` via `jq -r`. jq's `empty` filter emits **no output value** for a missing field (not a blank line), so on any response missing `.version` (both the `before` and `negative` checks), the `.error` text silently moved from the expected line 3 to line 2. The script's fixed-line reads (`sed -n '3p'`) then captured nothing, so `NEGATIVE` was reported `FAIL` and `BEFORE_OLD_MSG` was misread as `0`, even though the raw JSON responses captured to `before.json`/`negative.json` were already exactly correct (`{"success": false, "error": "URL points to a link-local or cloud-metadata address, which is not allowed"}` for the negative case).
- **Fix:** Changed both fallbacks (and the earlier `sonarr_url` read) from `// empty` to `// ""`, which always emits an explicit empty string in place of a missing field, keeping every field at its fixed line position regardless of which keys are present. Verified locally against both response shapes (version-only and error-only) before reuse.
- **Files modified:** `.planning/phases/125-lan-connection-tests/125-livecheck.sh`
- **Verification:** Local bash reproduction of both response shapes confirmed exactly 3 lines at fixed positions after the fix; the retry run on the NAS then reported `NEGATIVE PASS` with the full exact error text and `BEFORE success=false old_msg=1`.
- **Committed in:** `d642a59` (`fix(125-03): use jq's "" fallback instead of empty in tc() field extraction`)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 harness bug; no product code touched)
**Impact on plan:** The underlying `_validate_url` fix (125-01) was correct throughout -- this was purely a test-harness parsing bug in the new sandbox script. No impact on LAN-01/LAN-02 correctness; one additional live-check cycle (restore, retry, re-restore) was required.

## Issues Encountered

- `scp` to the NAS closed the connection immediately in this session (exit 255, "Connection closed"); worked around with `ssh nas 'cat > path' < localfile`, checksum-verified. Not a product issue; noted here in case a future plan hits the same SSH/scp environment limitation.
- The first live attempt's app-log window showed 2 `- ERROR -` lines ("Scanner process(es) died unexpectedly: LocalScanner" / "Caught exception in job ControllerJob") during the container recreate -- the known, pre-existing Phase 123 D-01-scanner-half restart pattern. Informational only, out of this phase's scope, reproduced identically in the successful retry (also 2 lines, same pair).

## User Setup Required

None - no external service configuration required.

## Owner reply

> approved

Owner typed "approved" on 2026-10-27 after reviewing: 1.7.6 failed Test Connection on `http://sonarr-v5:8989` (the old problem); the PR build succeeded against the identical URL and reported Sonarr version `5.0.0.2800`; `http://169.254.169.254` was refused with the locked message "URL points to a link-local or cloud-metadata address, which is not allowed"; the sandbox was restored to 1.7.6 and its original Sonarr URL; production was untouched. The orchestrator independently re-verified the restore in a separate `ssh nas` session before presenting the verdict: `seedsyncarr-test` and `seedsyncarr` both report `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`; production `StartedAt` `2026-10-23T07:04:18.591254939Z` unchanged, matching `123-LIFE-EVIDENCE.md`. Verbatim reply and review context also recorded in `125-LAN-EVIDENCE.md` under "## Owner review (Task 3)".

## Next Phase Readiness

- D-09 is fully live-proven: LAN-01 and LAN-02 both pass on the exact PR CI staging image, the sandbox is back on `IMAGE_PIN_L0` and fresh-session verified, and production is confirmed byte-identical throughout.
- Task 3 (owner checkpoint) is closed: the owner reviewed the Phase 125 verdict and replied "approved" (see "Owner reply" above). Phase 125 is owner-approved; PR #140 remains draft and unmerged, per the one-PR-per-phase convention -- merge is a separate owner decision, not part of this plan.
- One pre-existing, non-blocking item carried from 125-02: `125-LAN-EVIDENCE.md` line 127 (Gate 5's own command text, `grep -cE "logger\.|api_key|X-Api-Key"`) still literally contains the substring `X-Api-Key` as part of describing the detection command itself, not an actual key value. This predates this plan (committed in 125-02) and is preserved under the evidence file's append-only rule; the narrower acceptance check (`grep -ciE "x-api-key|apikey"`) on the whole file therefore reads `1`, not `0`. No real key value appears anywhere in the file -- confirmed by direct inspection of every `*_SUCCESS`/`*_ERROR`/`*.json` value recorded in this plan's new content.

## Self-Check: PASSED

Verified on disk and in git history:

- `FOUND: .planning/phases/125-lan-connection-tests/125-livecheck.sh`
- `FOUND: .planning/phases/125-lan-connection-tests/125-teardown.sh`
- `FOUND: .planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md`
- `FOUND: 9abc12a` (docs, Task 1 scripts commit)
- `FOUND: d642a59` (fix, harness jq-fallback bug)
- `FOUND: 7f2490a` (docs, Task 2 evidence/verdict commit)
- NAS state independently re-verified in a fresh `ssh nas` session: `.Config.Image` == `IMAGE_PIN_L0`, compose line == `IMAGE_PIN_L0`, `sonarr_url` == `http://sonarr-v5:8989`, `/server/status` == 200, production fingerprint diff empty against the pre-check baseline
- Owner reply "approved" recorded verbatim in both this summary ("## Owner reply") and `125-LAN-EVIDENCE.md` ("## Owner review (Task 3)")

---
*Phase: 125-lan-connection-tests*
*Completed: 2026-10-27*
