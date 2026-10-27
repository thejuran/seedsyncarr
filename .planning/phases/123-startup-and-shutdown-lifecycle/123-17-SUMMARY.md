---
phase: 123-startup-and-shutdown-lifecycle
plan: 17
subsystem: live-verification
tags: [gap-closure, gap-2, nas-sandbox, live-check, d-01, d-07, active-transfer, process-sampler, failure-gate]

# Dependency graph
requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "16"
    provides: "GAP2_CAPTURE_DIR, sampler-verified DEV_PIN_GAP2 sandbox, idle cycles I1/I2 both PASS with PROCS_RESULT=ok and the D-state hypothesis settled on idle restarts"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "13"
    provides: "Lftp.exit() bounded process-group SIGKILL-and-reap fallback, exit kill, describe_lftp_process diagnostic"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "14"
    provides: "123-proc-sampler.sh sample/verdict modes and restart-cycle.sh wiring that fails a cycle on a non-reaped lftp/children"
provides:
  - "Active-transfer restart cycles A1 (SSA123.Foxtrot.S01, first run, invalid mid-transfer proof) + A1r (SSA123.Hotel.S01 rerun, valid proof) and A2 (SSA123.Golf.S01) on DEV_PIN_GAP2, plus final idle cycle I3, all PASS"
  - "Live confirmation of the 123-13 D-state hypothesis during a genuine active-transfer restart (A2): lftp caught state=D at SIGKILL time with four live pget child processes present, reaped in 0.35s, PROCS_RESULT=ok"
  - "CHECK_STATUS_GAP2=PASS recorded in 123-LIFE-EVIDENCE.md, identical to GD2/state.env's CHECK_STATUS"
  - "Session teardown SANDBOX_RESTORED ok on first attempt; seedbox/sandbox/stage dir clean; production fingerprint unchanged; sandbox remains on DEV_PIN_GAP2 for 123-07's --final restore"
  - "Failure gate not triggered (CHECK_STATUS_GAP2=PASS); no owner decision required"
affects: ["123-07 (Phase 123 final verdict, --final sandbox restore)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Growth-gated single-ssh-call active-transfer launch: poll (bounded, 15 attempts) for two 4s-apart model snapshots that are both state=downloading, strictly increasing local size, and within the 5%-60% band, before launching the restart in the same ssh call -- corrects a gap in this plan's own first capture script"

key-files:
  created: []
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md

key-decisions:
  - "A1's first attempt (SSA123.Foxtrot.S01) was not counted as active-transfer proof because its two pre-restart snapshots, 4s apart, read an identical local size (52.9%, flat) -- within band but not proving motion. Rather than claim the restart as proof of a mid-transfer cycle, it was retried once as A1r using a new synthetic root (SSA123.Hotel.S01, 4800 MiB) per the plan's harness-miss retry rule, preserving the original A1 files unmodified for transparency."
  - "A1r's outcome (PASS, genuine growing/in-band proof) is what counts toward CHECK_STATUS_GAP2, per the plan's 'label or its single r rerun' counting rule."
  - "The live root-cause verdict states plainly that A1r's fallback was 'not exercised in this run' (lftp exited cleanly despite genuine active transfer) rather than claiming this as evidence against the D-state hypothesis, which A2 independently confirmed live during an active-transfer restart."

requirements-completed: [LIFE-01, LIFE-02]

# Metrics
duration: ~45min (harness/NAS execution span measured via file mtimes: prod-before-s2b.txt to run-session-teardown.out = ~26min; remainder is plan/context reading and evidence/summary writing)
completed: 2026-10-26
---

# Phase 123 Plan 17: Gap-Round-2 Active-Transfer Cycles, Live Root Cause, Session Teardown Summary

**Both GAP-2 active-transfer restart cycles ran live on DEV_PIN_GAP2 (A2 on SSA123.Golf.S01 passed with the 123-13 fallback genuinely firing -- lftp caught in `state=D` with four live pget children, reaped in 0.35s; A1's first attempt on SSA123.Foxtrot.S01 produced an invalid (flat) mid-transfer snapshot pair and was retried once as A1r on SSA123.Hotel.S01, which passed with valid growing/in-band proof), the final idle cycle I3 passed clean, `CHECK_STATUS_GAP2=PASS` was recorded, and the session teardown printed `SANDBOX_RESTORED ok` on its first attempt with production untouched.**

## Performance

- **Duration:** ~45 min (NAS/harness execution span measured directly from file mtimes: `prod-before-s2b.txt` to `run-session-teardown.out` = ~26 min; remainder is plan/context reading at the start and evidence/SUMMARY writing at the end)
- **Tasks:** 2 of 2 auto tasks completed; Task 3 (failure-gate checkpoint) skipped per its own instruction because `CHECK_STATUS=PASS`
- **Files modified:** 1 (`123-LIFE-EVIDENCE.md`, append-only) plus this SUMMARY

## Accomplishments

- Set up the gap-round-2 active-transfer session: `SEEDBOX_22_OPEN=1`, `RATE_LIMIT_L0=0` read and `RATE_LIMIT_SET=1` (4194304 B/s), `SYNTH_ROOTS=SSA123.Foxtrot.S01,SSA123.Golf.S01` written before any file existed, both 2400 MiB files staged under `/home/jules1651/ssa123-stage` (detached `head -c` writes on the seedbox, polled, then `mv`'d into `/home/jules1651/v5test/`), both roots held (`Completion hold for '<root>': No matching queue entry`) within ~75s of staging
- Ran A1 (SSA123.Foxtrot.S01): released (HTTP 200), restart launched with two 4s-apart pre-restart snapshots that both read local=1,331,396,608/2,516,582,400 (52.9%, in band but **flat**, not increasing) -- the launch script omitted the plan's own required growth gate (see Deviations). The resulting restart itself passed cleanly (`PROCS_RESULT=ok`, zero D-01 strings) but its own `LFTP_STATES_SEEN=S` only / `LFTP_FORCE_KILL=0` independently confirm lftp was not genuinely mid-transfer at restart time, so it is not counted as this plan's active-transfer proof
- Ran A2 (SSA123.Golf.S01): released (HTTP 200); a corrected growth-gated single-ssh-call script found valid proof on its second polling attempt (local 167,742,430 -> 334,399,335 bytes, 6.7% -> 13.3%, increasing, in band) and launched immediately. A2 **passed and genuinely triggered the 123-13 fallback**: `Lftp process 69 did not exit on force close (state=D child processes=?); sending SIGKILL to its process group`, reaped `in 0.35s (group kill sent: yes)`; the sampler independently confirms `LFTP_STATES_SEEN=S,D`, four live `sh`-comm pget children present pre-restart, all reaped (`PROCS_RESULT=ok`, zero survivors, zero zombies, zero backgrounded lftp)
- Retried A1 as A1r (SSA123.Hotel.S01, 4800 MiB, per the plan's harness-miss retry rule): released (HTTP 200), valid growing/in-band proof found on the first polling attempt (642,351,104 -> 764,116,992 bytes, 12.8% -> 15.2%). A1r passed; lftp exited cleanly on its own without needing the fallback (`LFTP_STATES_SEEN=S` only) despite being a genuinely proven mid-transfer restart -- explicitly recorded as "not exercised in this run," not as evidence against the D-state hypothesis
- Confirmed no SSA123 root was downloading, ran the final idle cycle I3: passed clean, zero D-01 strings, no fallback needed
- Computed `CHECK_STATUS=PASS` (I1, I2, A2, I3 first-attempt PASS; A1 counted via its A1r rerun's PASS) and appended it to `GD2/state.env`
- Ran the session teardown (`GD2/teardown.sh GD2`, session mode, no `--final`): passed on its first attempt, ending `SANDBOX_RESTORED ok` (rate limit restored, 3 synthetic roots removed, webhook secret already clear, server/status and webhook Test both ok); the separate clean check confirmed no `SSA123.` material anywhere (seedbox, stage dir, sandbox torrents dir), `rate_limit=0` matching `RATE_LIMIT_L0`, and `seedsyncarr-test` still on `DEV_PIN_GAP2`
- Appended the gap-round-2 active-cycle table, the active-transfer proof narrative, "### lftp outcome (D-01 lftp half, gap round 2)", "### Live root cause (GAP-2)" (with the (a)/(b)/(c) hypothesis verdict), "### Recorded-only signals", the SIGTERM-to-Exited-controller gap table, the gap-round-2 verdict, the production/teardown results, and a Deviations subsection to `123-LIFE-EVIDENCE.md` (append-only, confirmed via `git diff ... | grep -c '^-[^-]'` -> `0`), containing exactly one `CHECK_STATUS_GAP2=PASS` line
- Production `seedsyncarr` fingerprint confirmed byte-identical before and after all of this plan's NAS work (`PROD_UNCHANGED_S2B`); production was never restarted, edited, or otherwise touched

## Task Commits

This plan follows the same single-evidence-commit pattern as 123-11/123-12/123-15/123-16 (the plan's own Task 2 action text specifies the one commit point, after all NAS work and the evidence append are verified):

1. **Task 1: Active setup and active cycles A1/A2 (+A1r retry)** -- no separate commit (NAS-only + evidence prep)
2. **Task 2: I3, CHECK_STATUS, live root cause, teardown, evidence, commit** -- committed together with this plan's metadata
3. **Task 3: Failure gate** -- skipped (CHECK_STATUS=PASS); recorded below as "Failure gate not triggered (PASS)"

**Plan metadata:** `docs(123-17): active and final idle restart cycles on the GAP-2 build, live lftp root cause, session teardown`

## Files Created/Modified

- `.planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md` (modified, append-only) -- A1/A2/A1r/I3 cycle table, active-transfer proof, lftp outcome re-measurement, live root-cause verdict, recorded-only signals, `CHECK_STATUS_GAP2=PASS`, production/teardown results, Deviations
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-17-SUMMARY.md` (this file)

NAS-only artifacts (not committed, capture dir mode 0700): `cycle-A1.env`, `cycle-A2.env`, `cycle-A1r.env`, `cycle-I3.env`, `procs-A1.env`, `procs-A2.env`, `procs-A1r.env`, `procs-I3.env`, `log-cycle-A1.txt`, `log-cycle-A2.txt`, `log-cycle-A1r.txt`, `log-cycle-I3.txt`, `run-A1.out`, `run-A2.out`, `run-A1r.out`, `run-I3.out`, `run-sampler-{A1,A2,A1r,I3}.out`, `model-{foxtrot,golf,hotel}-{pre-1,pre-2,post}.json`, `run-session-teardown.out`, `prod-before-s2b.txt`, `prod-after-s2b.txt`, updated `state.env`.

## Decisions Made

See `key-decisions` in the frontmatter above: A1's first attempt excluded from active-transfer proof (flat snapshot pair) and retried as A1r on a new root per the harness-miss rule; A1r's PASS counted toward `CHECK_STATUS_GAP2` per the "label or its single `r` rerun" rule; A1r's un-exercised fallback stated plainly as "not exercised," never claimed as evidence against the D-state hypothesis already confirmed live by A2.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug / Rule 3 - Blocking] Missing pre-launch growth gate in the first active-cycle capture script (A1/Foxtrot)**
- **Found during:** Task 1 (A1 active-transfer setup)
- **Issue:** The single-`ssh`-call script used to capture A1's two pre-restart model snapshots and launch the restart cycle implemented the plan's "save pre-1, wait 4s, save pre-2" steps and printed both readings, but did not implement the plan's own required "check that local increased" gate before launching -- it launched unconditionally regardless of what the snapshots showed. The two snapshots read an identical local size (1,331,396,608 bytes, 52.9%, in band but flat across the 4s gap), and the restart was launched anyway.
- **Fix:** Every subsequent active-cycle capture script (A2, A1r) wraps the snapshot pair in a bounded poll loop (up to 15 attempts) that only proceeds to launch once a pair of 4s-apart readings is both `state=downloading`, strictly increasing in `local`, and within the 5%-60% band. A2's loop needed 2 attempts to find a valid pair; A1r's found one on its first attempt. The flawed A1 run's outcome (`LFTP_STATES_SEEN=S` only, `LFTP_FORCE_KILL=0`, i.e. lftp was not actually mid-transfer when SIGTERM arrived) independently confirms the flat snapshot pair was a true signal, not a measurement artifact -- validating the fix rather than contradicting it.
- **Files modified:** none (harness/operational script only, run via ad hoc ssh calls, not committed to the repo; no product or plan file changed)
- **Verification:** A2 and A1r both produced genuine, defensible growing/in-band snapshot pairs before launching, confirmed in 123-LIFE-EVIDENCE.md's "Active-transfer proof" narrative
- **Committed in:** n/a (no file changes to commit; documented here and in the evidence file's own Deviations subsection)

**2. [Rule 3 - Blocking] A1 harness-miss retry on a new synthetic root (SSA123.Hotel.S01)**
- **Found during:** Task 1, after A1's restart completed and its process-verdict data showed the fallback was never reached
- **Issue:** A1's first attempt could not be counted as proof of an active-transfer restart (see above), and the plan requires `at most one RELEASED_<root>=1 per root`, so `SSA123.Foxtrot.S01` could not simply be released and retried a second time
- **Fix:** Applied the plan's own harness-miss retry rule: appended `SSA123.Hotel.S01` to `SYNTH_ROOTS`, staged it at 4800 MiB, released it once, and ran the corrected growth-gated capture script, which found valid proof on its first attempt and launched `A1r`, which passed
- **Files modified:** none (NAS/seedbox operations only)
- **Verification:** A1r's snapshot pair (642,351,104 -> 764,116,992 bytes, 12.8% -> 15.2%, increasing, in band) and `CYCLE_A1r=PASS` in `GD2/state.env`
- **Committed in:** n/a (NAS-only; the retry's result is recorded in the evidence file's committed append)

---

**Total deviations:** 2 auto-fixed (1 harness bug in this plan's own ad hoc capture script, 1 consequent harness-miss retry using the plan's own designed retry path)
**Impact on plan:** None on the plan's truthfulness or on CHECK_STATUS_GAP2's correctness -- the flawed A1 attempt is fully disclosed and excluded from the active-transfer proof claim rather than silently counted; A2 (which required no retry) independently delivered the phase's single most important remaining live proof: the D-state hypothesis confirmed during a genuine active-transfer restart, with four live pget children reaped cleanly within the 123-13 bound.

## Issues Encountered

- An early seedbox `ssh` call using bare `nyx.usbx.me` (no explicit user) failed with "Permission denied (publickey,password)" because the NAS's own SSH client has no default-user mapping for that host; corrected to the explicit `jules1651@nyx.usbx.me` form used by `123-teardown.sh` and all subsequent seedbox calls, with no state written by the failed attempt and no retry-count impact.
- The model-progress read path (`/server/stream`'s `model-init` SSE event, parsed via `GD2/model_tools.py`) updates on the app's own `interval_ms_downloading_scan` (1000ms) cadence, which occasionally produced a flat reading across a 4s window even during a genuine active transfer (seen transiently in A2's first polling attempt). The growth-gated loop (see Deviations #1) absorbs this by re-polling rather than treating one flat pair as decisive on its own, except for A1's un-gated first attempt, which is the harness bug this plan fixed for its own subsequent cycles.

## User Setup Required

None -- no external service configuration required. This plan is NAS/sandbox-only (no new code, no deploy to production).

## Failure Gate (Task 3)

Failure gate not triggered (PASS). `CHECK_STATUS=PASS` / `CHECK_STATUS_GAP2=PASS` was computed from I1, I2 (123-16, both PASS on first attempt), A2 (PASS on first attempt), I3 (PASS on first attempt), and A1 counted via its A1r rerun (PASS). Per the plan's Task 3 instruction, no owner decision was required and no code was changed in this plan.

## Next Phase Readiness

- `GD2/state.env` now has `CHECK_STATUS=PASS` and `SESSION_TEARDOWN=ok`, plus every cycle's `_STARTED`/outcome line (I1, I2, A1, A1r, A2, I3), ready for 123-07 to read
- `123-LIFE-EVIDENCE.md`'s "## Gap-round-2 live check (123-16/123-17)" subsection is now complete: capture dir, preflight, sampler probe, re-pin, idle cycles (123-16) plus active cycles, live root cause, `CHECK_STATUS_GAP2=PASS`, and the teardown/clean-check results (123-17)
- The live D-02 split closes both halves of GAP-2 for this phase: the scanner-grace fix (GAP-1, confirmed across 11 live restarts in 123-11/12/16/17) and the lftp bounded-reap fallback (GAP-2, confirmed on this plan's A2 with a genuine `state=D` catch during an active transfer, reaped in 0.35s, zero survivors)
- The sandbox remains on `DEV_PIN_GAP2`, healthy, and torn down for this session (`SANDBOX_RESTORED ok`) but not yet restored to the 1.7.6 production pin -- 123-07 must run the `--final` restore
- Production `seedsyncarr` fingerprint confirmed byte-identical across this plan's NAS work; never restarted, edited, or otherwise touched
- The sandbox Sonarr API key was never read, printed, or rotated by this plan
- No blockers for 123-07; the phase's live-check evidence is now complete and truthful, with every PASS backed by direct command output (app log lines, sampler verdicts, model snapshots) rather than inference

## Known Stubs

None.

## Threat Flags

None -- all NAS surface touched in this plan (synthetic root staging/release/stop, sandbox restart cycles, session teardown) is covered by this plan's own `<threat_model>` (T-123-70..75), already addressed: only `seedsyncarr-test` and the v5test compose file were ever named; production read only via the single read-only inspect command with an empty fingerprint diff confirmed for this session; only `SSA123.`-prefixed names were created, released, stopped, or removed, with `SYNTH_ROOTS` written before each root's creation; every active-transfer claim is backed by two snapshots 4s apart showing genuine growth within the 5%-60% band, taken in the same `ssh` call that launches the cycle (A1's first attempt, which failed this proof, was excluded from the claim rather than silently counted); every restart cycle required `PROCS_RESULT=ok` in addition to a quiet log before counting as PASS; every detached launch's duration was recorded and no `STARTED`-without-outcome label was ever relaunched; no secret was set, read, or printed.

## Self-Check: PASSED

- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-LIFE-EVIDENCE.md" ]` -> FOUND
- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-17-SUMMARY.md" ]` -> FOUND
- NAS: `GD2/state.env` contains `CHECK_STATUS=PASS`, `SESSION_TEARDOWN=ok`, `CYCLE_A1=PASS`, `CYCLE_A2=PASS`, `CYCLE_A1r=PASS`, `CYCLE_I3=PASS` -> FOUND (confirmed directly via `grep` over ssh)
- NAS: `run-session-teardown.out` last line -> `SANDBOX_RESTORED ok` (confirmed directly)
- NAS: `diff prod-before-s2b.txt prod-after-s2b.txt` -> empty, `PROD_UNCHANGED_S2B` printed
- NAS: `sudo /usr/local/bin/docker inspect seedsyncarr-test --format '{{.Config.Image}}'` -> `ghcr.io/thejuran/seedsyncarr@sha256:7f354c149f2df586e7045ca47e971448b57dc1459a1a450f7a12aca885471a0c` (matches `DEV_PIN_GAP2` exactly)
- `git diff -- 123-LIFE-EVIDENCE.md | grep -c '^-[^-]'` -> `0` (append-only confirmed); `grep -c "CHECK_STATUS_GAP2=" 123-LIFE-EVIDENCE.md` -> `1`

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*
