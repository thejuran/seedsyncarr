---
phase: 125-lan-connection-tests
plan: 06
subsystem: release-process
tags: [lan-01, lan-02, d-09, d-11, d-12, nas-sandbox, live-recheck, digest-pin, restore, gap-closure, d-13, d-14]

# Dependency graph
requires:
  - phase: 125-05
    provides: "DEV_PIN_R2=ghcr.io/thejuran/seedsyncarr@sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45, the fixed-head staging image this plan deploys to the sandbox for the live recheck"
provides:
  - "125-livecheck.sh: NEGATIVE_CR01 step proving the CR-01 backslash payload is refused end to end on the real requests/urllib3 stack and real Docker DNS; restore-on-any-failure trap fix (OK=1 now requires CHECK_STATUS=PASS AND URL_RESTORED=1)"
  - "125-LAN-EVIDENCE.md 'Live re-check (D-09, D-11)' / 'Final restore (re-check)' / 'Fresh-session restore check (re-check)' / 'Production unchanged (re-check)' sections and the '## Phase 125 verdict (after gap closure)' table mapping LAN-01, LAN-02, D-06..D-14 and the full CR-01/WR-01..03/IN-01..03 review-closure table to evidence"
affects: [126-release-1.8.0]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EXIT trap gate narrowed to the single success condition (CHECK_STATUS=PASS && URL_RESTORED=1) so any post-deploy check failure -- not just a URL-restore failure -- triggers the automatic teardown.sh --final fallback"
    - "Two-negative restore: both NEGATIVE and NEGATIVE_CR01 set the refused sonarr_url before their own tc() read, with a single shared restore step running once after both, regardless of either outcome"

key-files:
  created:
    - .planning/phases/125-lan-connection-tests/125-06-SUMMARY.md
  modified:
    - .planning/phases/125-lan-connection-tests/125-livecheck.sh
    - .planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md

key-decisions:
  - "No harness-bug retry cycle was needed this round (unlike 125-03's attempt 1) -- the hardened livecheck.sh passed cleanly on its first live run, so Task 1's restore-on-any-failure trap fix was not itself exercised by a real failure path this session"
  - "D-12 (metadata-in-allowed-range) stays unit-proven only for this plan's live re-check, consistent with 125-01's D-02 row precedent -- neither fd00:ec2::254 nor 100.100.100.200 is the sandbox's Sonarr target, so there is no live scenario that would exercise it without fabricating an unrelated target"

requirements-completed: [LAN-01, LAN-02]

# Metrics
duration: ~45min (Tasks 1-3)
completed: 2026-10-28
---

# Phase 125 Plan 06: Gap-Closure Live Re-Check, Restore and Updated Verdict Summary

**Re-ran the hardened Test Connection guard's live sandbox check on the PR #140 staging image (DEV_PIN_R2): the container-name positive still succeeds, the cloud-metadata negative still refuses, and the new CR-01 backslash payload is refused end to end with the real requests/urllib3 stack and real Docker DNS -- sandbox restored to 1.7.6 and fresh-session verified, production byte-identical throughout. Owner approved the updated Phase 125 verdict.**

## Performance

- **Duration:** ~45 min (Task 1 script hardening + Task 2 single live NAS session, no retry needed + Task 3 owner review)
- **Completed:** 2026-10-28 (Tasks 1-3, all complete)
- **Tasks:** 3 of 3
- **Files modified:** 2 (`125-livecheck.sh`, `125-LAN-EVIDENCE.md`); 1 created (this summary)

## Accomplishments

- **Task 1 (D-11 harness hardening):** `125-livecheck.sh` gained a `NEGATIVE_CR01` step that sets `sonarr_url` to the exact 125-REVIEW CR-01 backslash payload (`http://169.254.169.254\@sonarr-v5:8989`) and requires the exact locked refusal `"Invalid URL: it contains a space, backslash or other character that is not allowed"`, added to the `CHECK_STATUS` gate; the restore step now runs once after both negatives regardless of either's outcome. Separately, the EXIT trap's `OK=1` gate was narrowed from "URL restored" alone to `CHECK_STATUS=PASS && URL_RESTORED=1`, so a genuine check failure after the deploy step (the exact defect class that bit 125-03's attempt 1) now always triggers `teardown.sh --final` automatically instead of silently leaving the sandbox on the dev pin. Verified locally before committing: `bash -n` on both scripts, a scratchpad simulation of the `tc()` error-only line-3 parsing, and a scratchpad simulation of the OK gate across all four `(CHECK_STATUS, URL_RESTORED)` combinations.
- **Task 2 (live re-check, D-09/D-11):** Ran the full check on `DEV_PIN_R2` (`sha256:76df9d9a...`) in a fresh capture dir (`/volume1/docker/v5test/results/lan01-125r2-20261028T001748Z`). `POSITIVE PASS` (`success=true version=5.0.0.2800`) against `http://sonarr-v5:8989` -- the 125-04 guard rewrite did not break LAN-01. `NEGATIVE PASS` against `http://169.254.169.254` with the exact locked LAN-02 message. `NEGATIVE_CR01 PASS` against the backslash payload with the exact locked CR-01 message -- the live, real-stack proof that the parser-differential SSRF bypass closed by `fix(125-04)` holds outside the unit-test harness. `sonarr_url` restored and read-back verified. `teardown.sh --final` ended `SANDBOX_RESTORED ok`; a second, independent `ssh nas` session confirmed `.Config.Image`, the compose line, `sonarr_url` and `/server/status` 200 all match the pre-check baseline exactly. Production `seedsyncarr` fingerprinted before, during and after (all three byte-identical, matching 125-03's recorded `StartedAt` with zero drift) -- never started, stopped, recreated or reconfigured.
- Appended the "## Phase 125 verdict (after gap closure)" table (LAN-01, LAN-02, SC2, SC4, D-06 through D-14) and a full review-closure table (CR-01, WR-01, WR-02, WR-03, IN-01, IN-02, IN-03) to `125-LAN-EVIDENCE.md`, each row citing the 125-04 test names, the 125-05 gate reruns/CHANGELOG commit, or this plan's live result. Concluded **"Phase 125 live re-check: PASSED"**.

## Task Commits

1. **Task 1: Add the CR-01 payload negative and restore-on-any-failure to the LAN sandbox live check** - `bd6a98c` (docs)
2. **Task 2: Run the re-check on DEV_PIN_R2, final restore, fresh-session check, evidence and updated verdict** - `4fb05a2` (docs)
3. **Task 3: Owner review of the updated Phase 125 verdict** - committed together with this summary update (see below)

## Files Created/Modified

- `.planning/phases/125-lan-connection-tests/125-livecheck.sh` - added `CR01_URL`/`EXPECTED_CR01_REFUSAL` constants, the `NEGATIVE_CR01` check step, `NEGATIVE_CR01` in the `CHECK_STATUS` condition, and narrowed the EXIT-trap `OK=1` gate to `CHECK_STATUS=PASS && URL_RESTORED=1`
- `.planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md` - (append-only) added "### Live re-check (D-09, D-11)", "### Final restore (re-check)", "### Fresh-session restore check (re-check)", "### Production unchanged (re-check)" under the existing "## Gap closure (D-11, D-12)" section, and a new top-level "## Phase 125 verdict (after gap closure)" with both the updated-item table and the review-closure table
- `.planning/phases/125-lan-connection-tests/125-06-SUMMARY.md` - (new) this file

## Live Re-Check Results (DEV_PIN_R2)

| Check | Result | Response |
|---|---|---|
| BEFORE (informational, on `IMAGE_PIN_L0`) | `success=false old_msg=1` | `{"success": false, "error": "URL resolves to a private/reserved IP address"}` |
| POSITIVE (LAN-01) | `PASS` | `{"success": true, "version": "5.0.0.2800"}` |
| NEGATIVE (LAN-02) | `PASS` | `{"success": false, "error": "URL points to a link-local or cloud-metadata address, which is not allowed"}` |
| NEGATIVE_CR01 (D-11) | `PASS` | `{"success": false, "error": "Invalid URL: it contains a space, backslash or other character that is not allowed"}` |
| sonarr_url restore | `RESTORED sonarr_url ok` | read back equals `http://sonarr-v5:8989` |
| Production diff (before/after) | empty | byte-identical fingerprints |
| `CHECK_STATUS` | `PASS` | last line `LIVECHECK PASS`, exit 0 |

**Final restore:** `bash teardown.sh --final` ended `SANDBOX_RESTORED ok` (inode preserved, image re-pinned to `IMAGE_PIN_L0`, status 200 confirmed).

**Fresh-session check (new, independent `ssh nas` call):** `.Config.Image` = `IMAGE_PIN_L0` exactly; compose `seedsyncarr-test` line = `IMAGE_PIN_L0`; `.sonarr.sonarr_url` = `http://sonarr-v5:8989`; `GET /server/status` = `200`; production fingerprint (`prod-final.txt`) byte-identical to `prod-before.txt`.

**Production unchanged:** `prod-before.txt`, `prod-after.txt` and `prod-final.txt` all identical: `2feb4073db71... sha256:5b801f83... ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0... running 2026-10-23T07:04:18.591254939Z` -- matches 125-03's recorded value exactly.

## Owner reply

Owner reply, verbatim, 2026-10-28: "approved"

The owner reviewed, before replying: a positive check against `http://sonarr-v5:8989` succeeding with Sonarr `5.0.0.2800`; `http://169.254.169.254` refused with the link-local/cloud-metadata message; the CR-01 payload `http://169.254.169.254\@sonarr-v5:8989` refused with the invalid-character message; the sandbox restored to the 1.7.6 pin and original Sonarr URL; production untouched; PR #140 still draft. The orchestrator independently re-verified in a separate `ssh nas` session: `seedsyncarr-test` and `seedsyncarr` both report `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0...`, and production `StartedAt` `2026-10-23T07:04:18.591254939Z` is unchanged. The owner was told one CHANGELOG `### Security` bullet names the backslash character and did not ask to change it.

## Decisions Made

- Used `ssh nas 'cat > ...' < file` (not `scp`) to place both scripts, sha256-verified byte-identical before running -- same workaround as 125-03 for this environment's SSH/scp limitation.
- Re-read `seedsyncarr-test .Config.Image` in a fresh `ssh nas` call immediately before writing `state.env`, confirming no drift from `IMAGE_PIN_L0` since 125-05, per the plan's explicit "else stop and report" instruction.
- No harness-bug retry was needed this round; Task 1's trap fix (restore-on-any-failure) was exercised only in its scratchpad simulation, not by a real live failure, since the hardened check passed on its first live attempt.

## Deviations from Plan

None - plan executed exactly as written for Tasks 1 and 2. The live re-check passed on the first attempt with no harness defects, no product-code changes, and no out-of-scope findings.

## Assumption Drift (advisory)

None material. One informational note: the project's general app-log-clock convention ("NAS host clock + 1h") did not match this session's observed offset between the app-log timestamp (`2026-10-27 20:18:58`) and the NAS host clock (~`2026-10-28 00:18` UTC) for the two informational `- ERROR -` log lines; the actual offset (~4h) matches what 125-03's evidence already recorded for the same log pair pattern, so this is a pre-existing documented discrepancy in the general convention note, not a new finding, and does not affect any pass/fail criterion (the log counts are informational only).

## Issues Encountered

- None. The live check, final restore, and fresh-session verification all passed on the first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three tasks are complete and committed. The owner has reviewed and approved the updated Phase 125 verdict (gap closure).
- `REQUIREMENTS.md`, `STATE.md` and `ROADMAP.md` are updated by this continuation to mark LAN-01/LAN-02 complete and advance plan progress; the phase itself is not marked complete in ROADMAP.md (the orchestrator runs verification first).
- PR #140 remains open and draft (`headRefOid` unchanged at `18de612d...`); nothing was merged.

## Self-Check

- `FOUND: .planning/phases/125-lan-connection-tests/125-livecheck.sh`
- `FOUND: .planning/phases/125-lan-connection-tests/125-LAN-EVIDENCE.md`
- `FOUND: bd6a98c` (docs, Task 1 commit) -- confirmed in `git log --oneline --all`
- `FOUND: 4fb05a2` (docs, Task 2 commit) -- confirmed in `git log --oneline --all`
- NAS state independently re-verified in a fresh `ssh nas` session after `teardown.sh --final`: `.Config.Image` == `IMAGE_PIN_L0`, compose line == `IMAGE_PIN_L0`, `sonarr_url` == `http://sonarr-v5:8989`, `/server/status` == 200, production fingerprint diff empty against `prod-before.txt`
- Owner reply recorded verbatim in this file and in `125-LAN-EVIDENCE.md`

---
*Phase: 125-lan-connection-tests*
*Tasks 1-3 completed: 2026-10-28*
*Phase 125 gap closure: owner-approved*
