---
phase: 123-startup-and-shutdown-lifecycle
plan: 11
subsystem: live-verification
tags: [gap-closure, nas-sandbox, live-check, d-07, re-pin, ssa123-teardown, idle-cycles]

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "10"
    provides: "DEV_PIN_GAP (sha256:991e4e1f...), PR #137 CI run 409 green, gates 1-9 passing over 123-01..04 + 123-08"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "06"
    provides: "Outstanding SSA123 session teardown and OLD_D capture dir (left incomplete at 123-06's stall)"
provides:
  - "123-06's outstanding SSA123 session teardown run to completion: SANDBOX_RESTORED ok, seedbox and sandbox verified clean"
  - "New gap capture dir GAP_CAPTURE_DIR=/volume1/docker/v5test/results/life01-123-gap-20261026T185841Z with the 123-09 harness, teardown helper and state.env"
  - "seedsyncarr-test re-pinned from OLD_DEV_PIN (sha256:b7b894fa...) to DEV_PIN_GAP (sha256:991e4e1f...), inode-preserving compose edit, readiness proven"
  - "Idle cycles I1 and I2 on DEV_PIN_GAP: 3 live restarts total (one accidental duplicate I1), all PASS with zero shutdown-error strings"
  - "123-LIFE-EVIDENCE.md '## Gap-round live check (123-11/123-12)' subsection"
affects: ["123-12 (active-transfer cycles I3, session teardown, failure gate)"]

# Tech tracking
tech-stack:
  added: []
  patterns: ["ssh detached-launch gotcha: on this NAS's remote shell, 'A && B &' does not detach B (blocks for B's full duration); 'A; B &' does — confirmed by minimal sleep reproduction and applied to every subsequent detached launch"]

key-files:
  created: []
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-11-SUMMARY.md

key-decisions:
  - "Old-session teardown run against OLD_CAPTURE_DIR (not the new GD) per the plan's instruction, since its state.env (RATE_LIMIT_L0, SYNTH_ROOTS) describes that session's changes; the new GD only records IMAGE_PIN_L0/OLD_DEV_PIN/DEV_PIN/OLD_CAPTURE_DIR plus this plan's own steps"
  - "The accidental duplicate I1 cycle (see Deviations) was kept rather than discarded: both runs are genuine live restarts on DEV_PIN_GAP and both passed cleanly, so discarding would throw away real evidence; the original run's files were preserved under an -orig suffix before the second run's write overwrote the canonical cycle-I1.env/log-cycle-I1.txt"

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: ~32min
completed: 2026-10-26
---

# Phase 123 Plan 11: Gap-round teardown, re-pin, and idle cycles Summary

**The outstanding 123-06 SSA123 teardown finished clean (`SANDBOX_RESTORED ok`), `seedsyncarr-test` was re-pinned from the pre-fix build to `DEV_PIN_GAP` (the GAP-1 clock-bounded SIGTERM grace fix), and three live idle `docker restart` cycles on the fixed build all passed with zero scanner/lftp shutdown-error strings — direct live confirmation that 123-08's fix eliminates the false "Scanner process(es) died unexpectedly" ERROR that fired on 3 of 5 pre-fix cycles.**

## Performance

- **Duration:** ~32 min
- **Tasks:** 3 of 3 completed
- **Files modified:** 1 (`123-LIFE-EVIDENCE.md`, append-only) plus this SUMMARY

## Accomplishments

- Ran the 123-06 SSA123 session teardown to completion against `OLD_CAPTURE_DIR`, ending `SANDBOX_RESTORED ok`; confirmed the seedbox and sandbox were already clean of `SSA123.`-prefixed material, `lftp.rate_limit` restored to `0`, and recorded `OLD_TEARDOWN=ok` / `SEEDBOX_CLEAN=ok` in the new gap capture dir
- Created `GAP_CAPTURE_DIR=/volume1/docker/v5test/results/life01-123-gap-20261026T185841Z` (mode 700; the parent directory's inherited ACL required an explicit `chmod 700` after `mkdir`, since `umask 077` alone did not produce 700 under that ACL), with the 123-09 harness (`restart-cycle.sh`), `teardown.sh` and `model_tools.py` copied in and verified byte-identical in line count to the repo originals
- Re-pinned `seedsyncarr-test` from `OLD_DEV_PIN` (`sha256:b7b894fa...`) to `DEV_PIN_GAP` (`sha256:991e4e1f...`) with an inode-preserving compose edit (`INODE_BEFORE=101505523` == `INODE_AFTER`), readiness proven by a fresh `Starting SeedSyncarr` app-log line after the pre-deploy marker, HTTP 200, and an 8 s settle; `.Config.Image` confirmed to equal `DEV_PIN_GAP` exactly
- Ran idle cycles I1 and I2 on `DEV_PIN_GAP` (plus one accidental duplicate I1 — see Deviations): all three live restarts logged the clean `Scanner process(es) stopped during shutdown` INFO path with zero `Scanner process(es) died unexpectedly`, `Could not terminate the child`, `Caught exception in job`, or `Error stopping`
- Appended "## Gap-round live check (123-11/123-12)" to `123-LIFE-EVIDENCE.md` (append-only, confirmed via `git diff ... | grep -c '^-[^-]'` -> `0`) with the teardown/clean-check results, re-pin facts, per-cycle table and timings, and production-unchanged results for all three sessions (s0, s1, s2a)
- Discovered and documented a real ssh detached-launch gotcha on this NAS: `cd "$GD" && nohup ... &` does not detach (blocks for the backgrounded command's full duration on this remote shell), while `cd "$GD"; nohup ... &` does (confirmed by a minimal `sleep` reproduction); every detached launch after the discovery used the `;`-joined form and confirmed sub-second return before polling separately

## Task Commits

This plan follows the same single-evidence-commit pattern as 123-06/123-09/123-10 (the plan's own Task 3 action text specifies the one commit point, after all NAS work and the evidence append are verified):

1. **Task 1: Gap capture dir + outstanding 123-06 SSA123 teardown** — no separate commit (NAS-only + evidence prep)
2. **Task 2: Re-pin seedsyncarr-test to DEV_PIN_GAP** — no separate commit (NAS-only)
3. **Task 3: Idle cycles I1/I2, evidence subsection, commit** — committed together with this plan's metadata

**Plan metadata:** `docs(123-11): clean 123-06 leftovers, re-pin sandbox to the GAP-1 build, idle restart cycles`

## Files Created/Modified

- `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (modified, append-only) — "Gap-round live check (123-11/123-12)" subsection: teardown, clean check, re-pin, idle-cycle table, production-unchanged results, deviation note
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-11-SUMMARY.md` (this file)

NAS-only artifacts (not committed, capture dir mode 0700): `restart-cycle.sh`, `teardown.sh`, `model_tools.py`, `repin.sh`, `state.env`, `prod-before-s0.txt`, `prod-after-s1.txt`, `prod-before-s2a.txt`, `prod-after-s2a.txt`, `log-old-teardown.txt`, `log-repin-baseline.txt`, `cycle-I1.env` / `cycle-I1-orig.env`, `cycle-I2.env`, `log-cycle-I1.txt` / `log-cycle-I1-orig.txt`, `log-cycle-I2.txt`, `run-old-teardown.out`, `run-repin.out`, `run-I1.out`, `run-I2.out`.

## Decisions Made

- The old-session teardown ran against `OLD_CAPTURE_DIR` (123-06's original capture dir), not the new `GD`, because its `state.env` carries the session-specific `RATE_LIMIT_L0`/`SYNTH_ROOTS` facts the teardown logic needs; `GD`'s own `state.env` only tracks this plan's steps (`OLD_TEARDOWN`, `SEEDBOX_CLEAN`, `REPIN`, `CYCLE_I1`, `CYCLE_I2`)
- Kept both I1 runs (original + accidental duplicate) as evidence rather than discarding the duplicate, since both are genuine live restarts on `DEV_PIN_GAP` that passed cleanly; preserved the original run's env/log files under an `-orig` suffix before the duplicate's write overwrote the canonical filenames

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `umask 077` did not produce a 700-mode capture dir under the parent's inherited ACL**
- **Found during:** Task 1 (capture dir creation)
- **Issue:** `mkdir` under `umask 077` produced mode 777 because the parent `/volume1/docker/v5test/results` directory carries an inherited Synology ACL that overrides the process umask
- **Fix:** Added an explicit `chmod 700 "$GD"` immediately after `mkdir`, verified via `stat -c %a` before proceeding
- **Files modified:** none (NAS-only operational step)
- **Verification:** `stat -c %a "$GD"` -> `700`

**2. [Rule 1 - Bug] Detached NAS launches using `A && B &` did not actually detach**
- **Found during:** Task 2 (re-pin launch) and Task 3 (I1 launch)
- **Issue:** The plan's detached-launch pattern (`cd <GD> && nohup bash <script> <args> > out 2>&1 < /dev/null & echo LAUNCHED`) blocked for the full duration of the backgrounded command on this NAS's remote shell, rather than returning immediately. This was confirmed with a minimal reproduction (`ssh nas "cd $GD && nohup sleep 15 ... & echo LAUNCHED"` took the full 15s; the same command with `cd $GD;` instead of `cd $GD &&` returned in ~0.2s). As a direct consequence, the first I1 launch attempt was auto-backgrounded by the Bash tool's own 120s local timeout while still genuinely running attached on the remote end; believing it had not started, a second I1 cycle was launched before the first one's `CYCLE_I1=PASS` was noticed in `state.env`, producing a real extra `docker restart seedsyncarr-test` on the sandbox (not production)
- **Fix:** Switched every subsequent detached launch (I2 onward, and the re-pin launch was already far enough along when discovered that it was left to finish naturally since it was correctly making progress and eventually wrote `REPIN=ok`) to the `;`-joined form (`cd <GD>; nohup ... &`), confirmed by `time` to return in well under 1s before polling separately in short bounded calls, per the plan's stall-prevention requirement
- **Files modified:** none (NAS-only operational step; no repo script was changed, since `restart-cycle.sh`/`teardown.sh`/`repin.sh` themselves are correct — the bug was in how the executor invoked them over ssh)
- **Impact:** Three idle restarts occurred on `seedsyncarr-test` instead of two (one extra `docker restart`, sandbox only); the original I1 run's evidence files were preserved as `cycle-I1-orig.env`/`log-cycle-I1-orig.txt` before being overwritten; both I1 runs passed cleanly, so no evidence was lost or contradicted. Production was never touched by this deviation.

---

**Total deviations:** 2 auto-fixed (1 blocking/environmental, 1 blocking/operational)
**Impact on plan:** Neither affected correctness of the D-07 live proof; the duplicate I1 run strengthens rather than weakens the evidence (a third clean live restart on the fixed build). No scope creep, no product code touched.

## Issues Encountered

- The repin.sh and first restart-cycle.sh launches took longer than typical (repin ~14 min due to a full image pull across ~25 layers; the idle cycles' `docker restart` itself took 124-146s wall time per `RESTART_ELAPSED_S`, longer than the 123-06 era's cycles) — handled entirely via short bounded polls (`tail`, `grep`) as the plan's stall-prevention protocol requires; no single blocking call exceeded the tool's own 120s auto-background threshold except the two affected by the `&&`/`;` detachment bug documented above, and neither caused the executor to stall (both were polled around and resolved).

## User Setup Required

None — no external service configuration required. This plan is NAS/sandbox-only (no new code, no deploy to production).

## Next Phase Readiness

- The gap capture dir (`GAP_CAPTURE_DIR=/volume1/docker/v5test/results/life01-123-gap-20261026T185841Z`) holds `state.env` with `IMAGE_PIN_L0`, `OLD_DEV_PIN`, `DEV_PIN`, `OLD_TEARDOWN=ok`, `SEEDBOX_CLEAN=ok`, `REPIN=ok`, `CYCLE_I1=PASS` (x2), `CYCLE_I2=PASS` — ready for 123-12 to resume from, per the resume rule (skip any marker already `ok`/`PASS`).
- `seedsyncarr-test` is live on `DEV_PIN_GAP`, healthy, and not yet torn down — exactly the state 123-12 needs to run the active-transfer cycles (A1, A2), I3, the session teardown (`--final`, restoring `IMAGE_PIN_L0`), and the D-03-style failure gate.
- Production `seedsyncarr` fingerprint is confirmed byte-identical across all three sessions in this plan (s0, s1, s2a) — no drift, never restarted or edited.
- The sandbox Sonarr API key was never read, printed or rotated by this plan.

## Known Stubs

None.

## Threat Flags

None — all NAS/seedbox surface touched in this plan (teardown, re-pin, idle restarts) is covered by this plan's own `<threat_model>` (T-123-41..45), which was already addressed: production named only via the single read-only inspect command with an empty fingerprint diff required per session (confirmed for s0, s1, s2a); seedbox cleanup only ever named `SSA123.`-prefixed entries, all already absent; `IMAGE_PIN_L0` carried forward and checked against the literal 1.7.6 digest; every step left a marker in `GD/state.env`; no secret was set or read.

## Self-Check: PASSED

- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md" ]` -> FOUND
- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-11-SUMMARY.md" ]` -> FOUND
- NAS: `GD/state.env` contains `OLD_TEARDOWN=ok`, `SEEDBOX_CLEAN=ok`, `REPIN=ok`, `CYCLE_I1=PASS`, `CYCLE_I2=PASS` -> FOUND (confirmed directly via `grep` over ssh)
- NAS: `sudo /usr/local/bin/docker inspect seedsyncarr-test --format '{{.Config.Image}}'` -> `ghcr.io/thejuran/seedsyncarr@sha256:991e4e1f28b90c6020c911a65c4814314aa5860682df8aa9e389e365d7872da6` (matches `DEV_PIN_GAP` exactly)

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*
