---
phase: 123-startup-and-shutdown-lifecycle
plan: 16
subsystem: live-verification
tags: [gap-closure, gap-2, nas-sandbox, live-check, d-07, re-pin, idle-cycles, process-sampler]

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "15"
    provides: "DEV_PIN_GAP2 (sha256:7f354c149f...), PR #137 CI run 410 green, gates 1-9 plus 5b passing over 123-01..04 + 123-08 + 123-13"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "14"
    provides: "123-proc-sampler.sh sample/verdict modes and restart-cycle.sh wiring that fails a cycle on a non-reaped lftp/children"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "12"
    provides: "GAP_CAPTURE_DIR with SESSION_TEARDOWN=ok and the clean sandbox/seedbox state this plan's preflight confirms"
provides:
  - "New gap-round-2 capture dir GAP2_CAPTURE_DIR=/volume1/docker/v5test/results/life01-123-gap2-20261026T212618Z (mode 700) with the 123-14 harness, teardown helper and model_tools.py, SHA-256-verified against the repo"
  - "Preflight confirming the GAP-1 round's session teardown held: clean seedbox/sandbox, rate limit restored, sandbox on DEV_PIN_GAP"
  - "Live sampler probe against the running DEV_PIN_GAP container: lftp confirmed as its own session leader (pgid==sid==pid)"
  - "seedsyncarr-test re-pinned from DEV_PIN_GAP to DEV_PIN_GAP2, inode-preserving compose edit, readiness proven, production untouched"
  - "Idle cycles I1 and I2 on DEV_PIN_GAP2: both PASS, both PROCS_RESULT=ok (lftp and its children actually reaped), both directly confirming the 123-13 D-state hypothesis live (state=D logged at the fallback, LFTP_STATES_SEEN=S,D)"
  - "123-LIFE-EVIDENCE.md '## Gap-round-2 live check (123-16/123-17)' subsection"
affects: ["123-17 (active-transfer cycles A1/A2, I3, session teardown, failure gate)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md

key-decisions:
  - "GAP2_CAPTURE_DIR created fresh rather than reused, since the resume-rule check (ls -d life01-123-gap2-2*) found no existing dir at plan start"
  - "The DEV_PIN_GAP baseline window observed during the re-pin (COULD_NOT_TERMINATE=3, ERROR_STOPPING=1) was recorded as informational only, per the plan's own framing of the M0 window as a detector sample, not a pass/fail gate for this plan's cycles"

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: ~33min
completed: 2026-10-26
---

# Phase 123 Plan 16: Gap-Round-2 Capture Dir, Preflight, Sampler Probe, Re-pin, Idle Cycles Summary

**A new GAP-2 capture dir was created and SHA-256-verified against the repo harness, preflight confirmed the GAP-1 round's clean state, a live sampler probe confirmed lftp is its own session leader on the running DEV_PIN_GAP container, the sandbox was re-pinned by digest to DEV_PIN_GAP2 with production untouched, and two idle `docker restart` cycles both passed with `PROCS_RESULT=ok` -- directly confirming on a live idle restart (not just inferring from a quiet log) that the 123-13 bounded process-group-SIGKILL-and-reap fallback actually reaps lftp out of a `state=D` (uninterruptible I/O) condition.**

## Performance

- **Duration:** ~33 min
- **Tasks:** 3 of 3 completed
- **Files modified:** 1 (`123-LIFE-EVIDENCE.md`, append-only) plus this SUMMARY

## Accomplishments

- Created `GAP2_CAPTURE_DIR=/volume1/docker/v5test/results/life01-123-gap2-20261026T212618Z` (mode 700, required an explicit `chmod 700` after `mkdir` -- `umask 077` alone did not yield 700 under the Synology inherited ACL, same as 123-11's finding), copied the 123-14 harness (`restart-cycle.sh`, `proc-sampler.sh`) plus `teardown.sh` and `model_tools.py`, and confirmed every copied script's SHA-256 matches the repo file exactly (`c747233b...`, `f9177e7b...`, `ba643f6a...`)
- Preflight confirmed the GAP-1 round (123-12) left a clean state: `PREV_CAPTURE_DIR/state.env` has `SESSION_TEARDOWN=ok`; the sandbox was still on `DEV_PIN_GAP`; no `SSA123.`-prefixed name on the seedbox or in the sandbox torrents dir; `/home/jules1651/ssa123-stage` absent; `lftp.rate_limit=0` matching `RATE_LIMIT_L0`; `/server/status` 200. `PREFLIGHT=ok` recorded. Production fingerprint unchanged since the last gap round (`prod-before-s0.txt` byte-identical to `PREV_CAPTURE_DIR`'s `prod-after-s2b.txt`)
- Ran a live sampler probe (`SAMPLER_MAX_S=3 bash proc-sampler.sh sample GD2 PROBE`) against the running `DEV_PIN_GAP` container before any restart: 5 sample blocks, each with a non-zero `init=2493`, each containing exactly one `lftp`-comm process line (`pid=3198 ppid=3187 pgid=3198 sid=3198 state=S`); `pgid == sid == pid` confirms lftp is its own session leader live, not just in the pexpect/ptyprocess source. `SAMPLER_PROBE=ok` recorded
- Re-pinned `seedsyncarr-test` from `DEV_PIN_GAP` (`sha256:991e4e1f...`) to `DEV_PIN_GAP2` (`sha256:7f354c149f...`) with an inode-preserving compose edit (`INODE_BEFORE=101505523` == `INODE_AFTER`), a full image pull (~9 min, no cached layers for the final several), readiness proven by a fresh `Starting SeedSyncarr` app-log line, HTTP 200, and an 8s settle; `.Config.Image` confirmed equal to `DEV_PIN_GAP2` exactly, image id `sha256:c55ad0d2...`. The `DEV_PIN_GAP` build's own shutdown during the recreate was recorded informationally: `COULD_NOT_TERMINATE=3`, `ERROR_STOPPING=1` (expected of the pre-GAP-2-fix build, which has no fallback to reap a stuck lftp)
- Ran idle cycles I1 and I2 on `DEV_PIN_GAP2`: both `PASS`, both `PROCS_RESULT=ok` (the live sampler confirms lftp and its children were actually reaped, not just a quiet log), both `LFTP_FORCE_KILL=1`/`LFTP_REAPED=1` (the 123-13 fallback path fired on both, even though both restarts were idle), and both log lines explicitly show `state=D` at the fallback warning -- directly settling the 123-13 D-state hypothesis live, and showing it is not confined to active-transfer restarts
- Appended "## Gap-round-2 live check (123-16/123-17)" to `123-LIFE-EVIDENCE.md` (append-only, confirmed via `git diff ... | grep -c '^-[^-]'` -> `0`) with the capture dir, preflight, sampler probe, re-pin facts, per-cycle table, shutdown-sequence timings (dual clock), the D-state settlement note, and production-unchanged results for s0, s1 and s2a

## Task Commits

This plan follows the same single-evidence-commit pattern as 123-11/123-15 (the plan's own Task 3 action text specifies the one commit point, after all NAS work and the evidence append are verified):

1. **Task 1: Create GD2, preflight, sampler probe** -- no separate commit (NAS-only + evidence prep)
2. **Task 2: Re-pin seedsyncarr-test to DEV_PIN_GAP2** -- no separate commit (NAS-only)
3. **Task 3: Idle cycles I1/I2, evidence subsection, commit** -- committed together with this plan's metadata

**Plan metadata:** `docs(123-16): re-pin sandbox to the GAP-2 build, sampler probe, idle restart cycles`

## Files Created/Modified

- `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (modified, append-only) -- "Gap-round-2 live check (123-16/123-17)" subsection: capture dir, preflight, sampler probe, re-pin, idle-cycle table, D-state settlement note, production-unchanged results
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-16-SUMMARY.md` (this file)

NAS-only artifacts (not committed, capture dir mode 0700): `restart-cycle.sh`, `proc-sampler.sh`, `teardown.sh`, `model_tools.py`, `repin.sh`, `state.env`, `prod-before-s0.txt`, `prod-after-s1.txt`, `prod-before-s2a.txt`, `prod-after-s2a.txt`, `procs-PROBE.txt`, `procs-PROBE.env`, `log-repin-baseline.txt`, `cycle-I1.env`, `cycle-I2.env`, `procs-I1.env`, `procs-I2.env`, `log-cycle-I1.txt`, `log-cycle-I2.txt`, `run-repin.out`, `run-I1.out`, `run-I2.out`, `run-sampler-I1.out`, `run-sampler-I2.out`.

## Decisions Made

- `GAP2_CAPTURE_DIR` was created fresh (the resume-rule check for an existing `life01-123-gap2-2*` dir found none at plan start)
- The `DEV_PIN_GAP` shutdown window observed during the re-pin (`COULD_NOT_TERMINATE=3`, `ERROR_STOPPING=1`) was recorded as informational only, consistent with the plan's own framing of the M0 window as a detector sample of the *old* build, not a pass/fail gate for this plan's own cycles (which run against `DEV_PIN_GAP2`)

## Deviations from Plan

### Auto-fixed Issues

None required -- no code or harness changes were needed; the 123-14 harness and the 123-13 fix worked exactly as designed against the live sandbox.

### Assumption Drift (advisory)

**1. The re-pin launch's ssh return time was 1.54s, slightly over the plan's "confirm it returned in under 1s" guidance**
- **Found during:** Task 2 (re-pin launch)
- **Planned:** the corrected `;`-joined detached pattern should return "well under 1s"
- **Actual:** the `repin.sh` launch call measured 1.54s wall time (`time ssh ...`); both idle-cycle launches (I1 0.16s, I2 0.17s) returned well under 1s
- **Why:** attributed to ssh connection-setup/handshake overhead on this particular call rather than a failed detach -- a failed detach (the `&&`-before-`nohup` bug from 123-11) would have blocked for the full ~9-14 min pull+restart duration, not 1.54s. Confirmed non-blocking by the very next poll, which found the backgrounded `compose pull` already progressing with `REPIN_STARTED` written and the process detached from the ssh session
- **Impact:** none -- no double-launch occurred (state.env shows exactly one `REPIN_STARTED=` line and one `REPIN=ok` line), and the slower return did not cause any premature relaunch

---

**Total deviations:** 0 auto-fixed; 1 advisory (non-blocking) assumption-drift note on launch-return timing
**Impact on plan:** None on correctness or scope. All three live-proof claims (preflight clean, sampler session-leader confirmation, re-pin facts, PROCS_RESULT=ok on both idle cycles) were verified by direct command output, not inferred.

## Issues Encountered

- The `repin.sh` re-pin (full image pull across ~25 layers, most already cached except the final ~10 new layers from the GAP-2 build) took about 9 minutes of wall time; handled entirely via short bounded polls (`tail`, `grep`) rather than one blocking call, per the stall-prevention protocol. No single poll exceeded the 2-minute guidance.
- `ps aux` on the NAS host briefly showed two `proc-sampler.sh sample ... I1` process entries during I1's restart window; investigated and attributed to the sampler's internal `docker top | awk | while read` pipeline forking a subshell for its final stage (a normal bash pipeline-execution artifact, not a double launch) -- confirmed via `state.env` that exactly one `CYCLE_I1_STARTED=` line exists, so no double restart occurred.

## User Setup Required

None -- no external service configuration required. This plan is NAS/sandbox-only (no new code, no deploy to production).

## Next Phase Readiness

- `GAP2_CAPTURE_DIR` (`/volume1/docker/v5test/results/life01-123-gap2-20261026T212618Z`) holds `state.env` with `IMAGE_PIN_L0`, `OLD_DEV_PIN`, `DEV_PIN`, `PREV_CAPTURE_DIR`, `PREFLIGHT=ok`, `SAMPLER_PROBE=ok`, `REPIN=ok`, `CYCLE_I1=PASS`, `CYCLE_I2=PASS` -- ready for 123-17 to resume from per the resume rule (skip any marker already `ok`/`PASS`)
- `seedsyncarr-test` is live on `DEV_PIN_GAP2`, healthy, and not yet torn down -- exactly the state 123-17 needs to run the active-transfer cycles (A1, A2), the final idle cycle I3, the session teardown (`--final`, restoring `IMAGE_PIN_L0`), and the failure gate
- Production `seedsyncarr` fingerprint confirmed byte-identical across all three sessions in this plan (s0, s1, s2a) -- no drift, never restarted or edited
- The sandbox Sonarr API key was never read, printed or rotated by this plan
- Both idle cycles already show direct live confirmation that the GAP-2 lftp fix works and that the D-state hypothesis holds; 123-17's active-transfer cycles are what originally exposed the GAP-2 bug and are the higher-value remaining proof

## Known Stubs

None.

## Threat Flags

None -- all NAS surface touched in this plan (capture dir creation, preflight, sampler probe, re-pin, idle restarts) is covered by this plan's own `<threat_model>` (T-123-65..69), already addressed: only `seedsyncarr-test` and the v5test compose file were ever named; production read only via the single read-only inspect command with an empty fingerprint diff required per session (confirmed for s0, s1, s2a); `IMAGE_PIN_L0` carried forward and checked against the literal 1.7.6 digest; every step left a marker in `GD2/state.env`; no secret was set, read, or printed; the copied harness scripts' SHA-256 matched the repo exactly before any use.

## Self-Check: PASSED

- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md" ]` -> FOUND
- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-16-SUMMARY.md" ]` -> FOUND
- NAS: `GD2/state.env` contains `PREFLIGHT=ok`, `SAMPLER_PROBE=ok`, `REPIN=ok`, `CYCLE_I1=PASS`, `CYCLE_I2=PASS` -> FOUND (confirmed directly via `grep` over ssh)
- NAS: `sudo /usr/local/bin/docker inspect seedsyncarr-test --format '{{.Config.Image}}'` -> `ghcr.io/thejuran/seedsyncarr@sha256:7f354c149f2df586e7045ca47e971448b57dc1459a1a450f7a12aca885471a0c` (matches `DEV_PIN_GAP2` exactly)

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*
