---
phase: 123-startup-and-shutdown-lifecycle
plan: 14
subsystem: testing
tags: [gap-closure, gap-2, harness, restart-cycle, process-sampler, lftp, orphan-check, awk, proc]

requires:
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "12"
    provides: "Gap-round live check (123-11/123-12) that found the D-01 lftp half still failing on active-transfer restarts (could_not_terminate, error_stopping); owner decision fix-in-phase"
  - phase: 123-startup-and-shutdown-lifecycle
    plan: "13"
    provides: "Lftp.exit() bounded process-group SIGKILL-and-reap fallback, exit kill, did not exit on force close / reaped after force close log texts (the fixed substrings this plan's harness counts)"
provides:
  - "123-proc-sampler.sh: sample mode (docker top + docker inspect + /proc/<pid>/stat polling) and verdict mode (awk-based lftp-gone verdict: PROCS_RESULT=ok|FAIL:<reasons>|UNDETERMINED:<why>, plus OLD_INIT/OLD_LFTP_PIDS/OLD_LFTP_CHILD_PIDS/OLD_GEN_SAMPLES/LFTP_STATES_SEEN/LFTP_ZOMBIE_SEEN/LFTP_GONE_UTC/BG_LFTP_SEEN/SAMPLES_TOTAL facts), proven against five synthetic fixtures and one sample-mode smoke test"
  - "123-restart-cycle.sh wired to start/stop the sampler around each restart and fail the cycle on a non-ok PROCS_RESULT (procs_<reason> / procs_undetermined), plus recorded-only LFTP_FORCE_KILL / LFTP_REAPED counts"
affects: ["123-15", "123-16", "123-17"]

tech-stack:
  added: []
  patterns: ["awk generation-id trick to track 'is this pid present in the last matching block' without relying on whole-array delete (POSIX-portable across macOS/BSD awk and the NAS's awk)", "bash parameter-expansion parsing of /proc/<pid>/stat (comm between first '(' and last ')'), mirroring the plan's own python-side describe_lftp_process parsing rule"]

key-files:
  created:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-proc-sampler.sh
  modified:
    - .planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh

key-decisions:
  - "LFTP_FORCE_KILL/LFTP_REAPED/PROCS_RESULT added to the second (counts) summary echo line rather than splitting across both lines, since that line already groups all log-derived counts/signals"
  - "The procs_verdict step's bash invocation of proc-sampler.sh verdict is left unredirected (not sent to /dev/null) so its PROCS_RESULT/fact lines are visible in the detached run's out file, consistent with this harness's STEP-progress-visibility convention"
  - "The sampler's own cleanup of stale .ready/.stop/procs-<label>.txt files at the start of sample mode is kept even though restart-cycle.sh also does this cleanup before launching it, so proc-sampler.sh stays independently testable/usable standalone"

requirements-completed: [LIFE-01, LIFE-02]

duration: ~20min
completed: 2026-10-26
---

# Phase 123 Plan 14: GAP-2 lftp process sampler and restart-cycle harness wiring Summary

**A new `123-proc-sampler.sh` harness script directly samples the OLD container's processes across a restart (docker top + /proc/<pid>/stat) and awk-verdicts whether the pre-restart lftp pid and its children were actually reaped before the old container's init exited -- settling the D-state hypothesis from 123-13 live instead of only inferring it from a quiet log -- and `123-restart-cycle.sh` now starts/stops it around every restart and fails the cycle on a non-ok verdict, plus records the 123-13 fallback's "did not exit on force close" / "reaped after force close" log counts.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `123-proc-sampler.sh` `sample <D> <label>` mode: records, about every `SAMPLER_INTERVAL_S` (default 0.5s), the container's init host pid (`docker inspect -f '{{.State.Pid}}'`) and, for every pid `docker top` lists, `pid ppid pgid sid state comm` parsed from `/proc/<pid>/stat` (comm = text between first `(` and last `)`, spaces -> `_`; state/ppid/pgrp/session = the 1st-4th fields after that last `)`), until a stop file appears or `SAMPLER_MAX_S` (default 120s) elapses. Sample 1 is taken first and the ready marker is touched right after.
- `123-proc-sampler.sh` `verdict <D> <label>` mode: a POSIX-awk program (no gawk-only features) that tracks the "old" container generation (samples sharing sample 1's init pid, read only up to the first sample whose init differs), the pre-restart lftp pid(s) and their pre-restart children (from sample 1 only), and any lftp-comm pid appearing later that wasn't in sample 1 (a "backgrounded" candidate). It emits `PROCS_RESULT=ok | FAIL:lftp_not_reaped[,lftp_child_survived][,lftp_backgrounded] | UNDETERMINED:no_presample|no_lftp_before|too_few_old_gen`, plus the recorded facts (`OLD_INIT`, `OLD_LFTP_PIDS`, `OLD_LFTP_CHILD_PIDS` with comm, `OLD_GEN_SAMPLES`, `LFTP_STATES_SEEN`, `LFTP_ZOMBIE_SEEN`, `LFTP_GONE_UTC`, `BG_LFTP_SEEN`, `SAMPLES_TOTAL`), both to `<D>/procs-<label>.env` and stdout.
- `123-restart-cycle.sh` gained a `sampler_start` step (launches the sampler in the background before `docker restart`, polls up to 10s for its ready marker, `add_fail procs_sampler_not_ready` on timeout without aborting the cycle) and a `procs_verdict` step (runs the sampler's verdict mode after the existing log-window counts, reads `PROCS_RESULT` from the `.env` file with a fixed-string grep -- never sourced -- and maps `FAIL:<r1>,<r2>` to `add_fail procs_<r1>`/`procs_<r2>` and any `UNDETERMINED:*` to `procs_undetermined`).
- `on_exit` now also touches the sampler's stop file on every exit path (clean verdict, INT/TERM/HUP, or an unhandled error), and the restart step itself stops the sampler and waits (bounded at 10s, polling `kill -0`) right after `docker restart` returns, so a background sampler never outlives a cycle beyond its own 120s cap.
- `LFTP_FORCE_KILL` (`did not exit on force close`) and `LFTP_REAPED` (`reaped after force close`) are counted over the same log window as the existing strings and recorded in `cycle-<label>.env` and the summary echo line, exactly as the 123-13 fallback's own log texts.
- Every existing step, count and pass/fail rule (`restart_rc`, `scanner_died`, `could_not_terminate`, `caught_exception_in_job`, `error_stopping`) is unchanged -- confirmed by the diff (only additions plus the edited header/echo lines) and by individually grepping each `add_fail <rule>` count (all still 1).

## Task Commits

1. **Task 1: Write 123-proc-sampler.sh (sample + verdict) and prove the verdict against five local fixtures** - `6266cb3` (docs)
2. **Task 2: Wire the sampler and the lftp fallback counts into 123-restart-cycle.sh** - `45b4ed9` (docs)

## Files Created/Modified

- `.planning/phases/123-startup-and-shutdown-lifecycle/123-proc-sampler.sh` (created) - sample/verdict harness script, read-only (docker top, docker inspect, /proc stat reads)
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh` (modified) - sampler_start/procs_verdict steps, sampler-stop on every exit path, LFTP_FORCE_KILL/LFTP_REAPED counts

## Verification (all commands actually run; outputs observed, not assumed)

### Task 1 -- syntax and production-name check

```
$ bash -n 123-proc-sampler.sh && echo SYNTAX_OK && grep -c -F "PROCS_RESULT=" 123-proc-sampler.sh
SYNTAX_OK
2
$ grep -c -F "seedsyncarr " 123-proc-sampler.sh
0
```

### Task 1 -- bash parameter-expansion comm-parsing check (parens-in-comm edge case)

Checked the `${raw#*(}` / `${rest%)*}` / `${rest##*)}` parsing against a synthetic `/proc/<pid>/stat` line whose comm itself contains parens (mirrors the 123-13 `describe_lftp_process` fixture, `"4242 (lftp (x)) D 1 4242 4242 0 -1"`):

```
comm=[lftp_(x)]
after_last=[ D 1 4242 4242 0 -1]
state=D ppid=1 pgrp=4242 session=4242
```

### Task 1 -- five synthetic fixture verdicts (printed by the script itself)

**F1 (gone)** -- sample 1: tini 900, python 901, lftp 950 (ppid 901), ssh 960 (ppid 950); samples 2-3 same init 900, lftp 950 state S then D; sample 4 init 900 without 950/960; sample 5 init 0; sample 6 init 1900:

```
PROCS_RESULT=ok
OLD_INIT=900
OLD_LFTP_PIDS=950
OLD_LFTP_CHILD_PIDS=960:ssh
OLD_GEN_SAMPLES=4
LFTP_STATES_SEEN=S,D
LFTP_ZOMBIE_SEEN=0
LFTP_GONE_UTC=2026-10-26T19:16:10.600Z
BG_LFTP_SEEN=0
SAMPLES_TOTAL=6
```

Expected `ok`, `LFTP_STATES_SEEN` containing S and D, `LFTP_GONE_UTC` equal to sample 4's time (`2026-10-26T19:16:10.600Z`) -- matched exactly.

**F2 (zombie left)** -- like F1, but 950 is state Z (not absent) in the last old-generation sample:

```
PROCS_RESULT=FAIL:lftp_not_reaped
OLD_INIT=900
OLD_LFTP_PIDS=950
OLD_LFTP_CHILD_PIDS=960:ssh
OLD_GEN_SAMPLES=4
LFTP_STATES_SEEN=S,D,Z
LFTP_ZOMBIE_SEEN=1
LFTP_GONE_UTC=none
BG_LFTP_SEEN=0
SAMPLES_TOTAL=6
```

Expected `FAIL:lftp_not_reaped`, `LFTP_ZOMBIE_SEEN=1` -- matched exactly.

**F3 (child left)** -- 950 gone, 960 still present in the last old-generation sample:

```
PROCS_RESULT=FAIL:lftp_child_survived
OLD_INIT=900
OLD_LFTP_PIDS=950
OLD_LFTP_CHILD_PIDS=960:ssh
OLD_GEN_SAMPLES=4
LFTP_STATES_SEEN=S,D
LFTP_ZOMBIE_SEEN=0
LFTP_GONE_UTC=2026-10-26T19:18:10.600Z
BG_LFTP_SEEN=0
SAMPLES_TOTAL=6
```

Expected `FAIL:lftp_child_survived` -- matched exactly.

**F4 (backgrounded)** -- 950 gone, a new lftp pid 970 (ppid 900) present in the last old-generation sample:

```
PROCS_RESULT=FAIL:lftp_backgrounded
OLD_INIT=900
OLD_LFTP_PIDS=950
OLD_LFTP_CHILD_PIDS=960:ssh
OLD_GEN_SAMPLES=4
LFTP_STATES_SEEN=S,D
LFTP_ZOMBIE_SEEN=0
LFTP_GONE_UTC=2026-10-26T19:19:10.600Z
BG_LFTP_SEEN=1
SAMPLES_TOTAL=6
```

Expected `FAIL:lftp_backgrounded`, `BG_LFTP_SEEN=1` -- matched exactly.

**F5 (too few)** -- only sample 1 (with lftp present), then init 0:

```
PROCS_RESULT=UNDETERMINED:too_few_old_gen
OLD_INIT=900
OLD_LFTP_PIDS=950
OLD_LFTP_CHILD_PIDS=
OLD_GEN_SAMPLES=1
LFTP_STATES_SEEN=S
LFTP_ZOMBIE_SEEN=0
LFTP_GONE_UTC=none
BG_LFTP_SEEN=0
SAMPLES_TOTAL=2
```

Expected `UNDETERMINED:too_few_old_gen` -- matched exactly.

All five fixture files and their `.env` outputs were built and run in the session scratchpad (`/private/tmp/.../scratchpad/123-14/`), never on the NAS; no docker or ssh was touched for this check.

### Task 1 -- sample-mode smoke (fake docker, fake proc root)

Fake `docker` CLI: `inspect` always prints `900`; `top` prints a header plus pids 900 (tini), 901 (python3), 950 (lftp). Fake `/proc` root: `900/stat`, `901/stat`, `950/stat` with matching comm names.

```
$ SAMPLER_DOCKER=<fake> PROC_ROOT=<fakeproc> SAMPLER_MAX_S=2 SAMPLER_INTERVAL_S=0.5 \
  bash 123-proc-sampler.sh sample <tmpD> T1
$ ls <tmpD>/sampler-T1.ready        # exists (empty file)
$ cat <tmpD>/procs-T1.txt
S 1 2026-10-26T20:52:17.3NZ init=900
P 900 1 900 900 S tini
P 901 900 901 900 S python3
P 950 901 950 900 S lftp
S 2 2026-10-26T20:52:18.3NZ init=900
... (4 sample blocks total within the 2s SAMPLER_MAX_S window)
```

4 `S ` header lines (>= 2 required) and a `P 950 ... lftp` line in every block -- matched. The literal `.3NZ` in the timestamp is the documented macOS-`date`-has-no-`%3N` limitation called out in the plan (the verdict never parses the time field, only copies it; the NAS uses GNU date).

### Task 1 -- final acceptance checks

```
$ git log -1 --format=%s
docs(123-14): process sampler proving lftp and its children are gone before the old container stops (GAP-2 harness)
$ git diff --diff-filter=D --name-only HEAD~1 HEAD   # (empty -- no deletions)
```

### Task 2 -- syntax and wiring checks

```
$ bash -n 123-restart-cycle.sh && echo SYNTAX_OK
SYNTAX_OK
$ grep -c -F -e "proc-sampler.sh" -e "LFTP_FORCE_KILL" -e "LFTP_REAPED" -e "procs_undetermined" 123-restart-cycle.sh
12
$ grep -c -F "add_fail could_not_terminate" 123-restart-cycle.sh   -> 1
$ grep -c -F "add_fail error_stopping" 123-restart-cycle.sh        -> 1
$ grep -c -F "add_fail scanner_died" 123-restart-cycle.sh          -> 1
$ grep -c -F "add_fail caught_exception_in_job" 123-restart-cycle.sh -> 1
$ grep -c -F "add_fail restart_rc" 123-restart-cycle.sh            -> 1
$ grep -c -F "sampler-\${LABEL}.stop" 123-restart-cycle.sh         -> 3  (on_exit, sampler_start cleanup, post-restart stop)
```

### Task 2 -- diff-only-additions check

```
$ git diff HEAD~1 -- 123-restart-cycle.sh | grep "^-[^-]"
-# STOPPED_DURING_SHUTDOWN, ERROR_LINES and RESTART_ELAPSED_S. "Exited
-# successfully" is logged only once the whole shutdown sequence completes, so
-# it is absent whenever docker's stop timeout SIGKILLs the process first; the
-# 1.7.6 baseline window shows the identical gap (BASELINE_EXITED_SUCCESSFULLY=0),
-# so this is pre-existing and not a regression signal. RESTART_ELAPSED_S is an
-# informational signal of whether the stop hit docker's 10 s timeout.
-echo "SCANNER_DIED=$SCANNER_DIED COULD_NOT_TERMINATE=$COULD_NOT_TERMINATE CAUGHT_EXCEPTION_IN_JOB=$CAUGHT_EXCEPTION_IN_JOB ERROR_STOPPING=$ERROR_STOPPING EXITED_SUCCESSFULLY=$EXITED_SUCCESSFULLY STARTING_SEEN=$STARTING_SEEN STOPPED_DURING_SHUTDOWN=$STOPPED_DURING_SHUTDOWN ERROR_LINES=$ERROR_LINES"
```

Only the rewrapped header paragraph and the second summary echo line were removed (both rewritten with the new fields added) -- no `add_fail <rule>` line was removed, confirming every existing pass/fail rule stayed byte-identical in behavior.

```
$ git diff --stat HEAD~1 -- 123-restart-cycle.sh
1 file changed, 67 insertions(+), 7 deletions(-)
```

### Task 2 -- procs_verdict mapping logic replayed by hand against fixture F2's env file

```
$ cat procs-F2.env | grep PROCS_RESULT
PROCS_RESULT=FAIL:lftp_not_reaped
```

Running the exact `grep -F "PROCS_RESULT=" | tail -n 1 | cut -d= -f2-` + `case`/`IFS=','` mapping logic from 123-restart-cycle.sh's `procs_verdict` step against this file:

```
PROCS_RESULT=[FAIL:lftp_not_reaped]
FAIL_REASONS=[procs_lftp_not_reaped]
```

Yields `procs_lftp_not_reaped`, exactly as required.

### Task 2 -- final acceptance checks

```
$ git log -1 --format=%s
docs(123-14): restart cycle fails when lftp or its children outlive the app; record lftp fallback counts (GAP-2 harness)
$ git diff --diff-filter=D --name-only HEAD~1 HEAD   # (empty -- no deletions)
```

## Decisions Made

- `LFTP_FORCE_KILL`/`LFTP_REAPED`/`PROCS_RESULT` were added to the second (counts) summary echo line, not split across both lines, since that line is already the natural home for all log-derived counts and signals.
- The `procs_verdict` step's invocation of `proc-sampler.sh verdict` is left unredirected so its printed facts land in the detached run's `run-<label>.out`, matching this harness's existing STEP-progress-visibility convention (no new silent step).
- `proc-sampler.sh`'s own stale-file cleanup at the start of sample mode is kept (even though `123-restart-cycle.sh` also does this before launching it), so the sampler stays independently runnable/testable without the restart harness.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched the `<interfaces>` contract precisely; the five fixture verdicts and the sample-mode smoke test all matched their expected outputs on the first run with no adjustment needed to the awk verdict logic or the sample-mode bash.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. This plan is local-only (no NAS, no docker, no ssh), as required by the orchestrator amendment and parallel-execution constraints. No sandbox or production container was touched.

## Next Phase Readiness

`123-proc-sampler.sh` and the updated `123-restart-cycle.sh` are committed locally and ready for the live gap round (123-16/123-17), which can now capture a direct, log-independent proof that lftp and its pre-restart children were actually reaped before the old container stopped -- including the lftp state letters seen during shutdown, settling the D-state hypothesis from 123-13 -- and will fail the cycle with `procs_lftp_not_reaped` / `procs_lftp_child_survived` / `procs_lftp_backgrounded` / `procs_undetermined` if the live reap does not hold up, independent of whatever the app log shows.

---
*Phase: 123-startup-and-shutdown-lifecycle*
*Completed: 2026-10-26*

## Self-Check: PASSED

- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-proc-sampler.sh" ]` -> FOUND
- `[ -f ".planning/phases/123-startup-and-shutdown-lifecycle/123-restart-cycle.sh" ]` -> FOUND
- `git log --oneline --all | grep -q "6266cb3"` -> FOUND
- `git log --oneline --all | grep -q "45b4ed9"` -> FOUND
