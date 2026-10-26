#!/usr/bin/env bash
# Repeatable restart-cycle harness for the Phase 123 live D-01 restart check,
# run against seedsyncarr-test only. One invocation is one restart cycle:
# pre-restart marker, restart, readiness, a new-remote-scan check, per-string
# window counts, and a PASS/FAIL verdict.
#
# Usage: bash restart-cycle.sh <capture-dir> <label> <idle|active>
#
# Writes <capture-dir>/log-cycle-<label>.txt (the app log window starting
# just after the pre-restart line-count marker) and
# <capture-dir>/cycle-<label>.env (facts and counts for this cycle), then
# appends CYCLE_<label>=PASS or CYCLE_<label>=FAIL:<reasons> to
# <capture-dir>/state.env.
#
# Exact strings counted in the window (fixed-string greps only, per the
# phase interfaces note):
#   "Scanner process(es) died unexpectedly"
#   "Could not terminate the child"
#   "Caught exception in job"
#   "Error stopping"
#   "Exited successfully"
#   "Starting SeedSyncarr"
#   "Scanner process(es) stopped during shutdown"
#   " - ERROR - "
#   "did not exit on force close"
#   "reaped after force close"
#
# PASS requires a clean restart exit code, a fresh start-up line, a ready
# status, a new remote scan, no rotation, and zero of the three shutdown-error
# strings. Exit 0 only on PASS.
# Prints status words and counts only -- no config values. Never names the
# production container.
#
# Recorded only (never a pass/fail criterion): EXITED_SUCCESSFULLY,
# STOPPED_DURING_SHUTDOWN, ERROR_LINES, RESTART_ELAPSED_S, LFTP_FORCE_KILL
# ("did not exit on force close") and LFTP_REAPED ("reaped after force
# close"). "Exited successfully" is logged only once the whole shutdown
# sequence completes, so it is absent whenever docker's stop timeout
# SIGKILLs the process first; the 1.7.6 baseline window shows the identical
# gap (BASELINE_EXITED_SUCCESSFULLY=0), so this is pre-existing and not a
# regression signal. RESTART_ELAPSED_S is an informational signal of
# whether the stop hit docker's 10 s timeout.
#
# Live process verdict (GAP-2): a sampler script, copied into the capture
# dir as <capture-dir>/proc-sampler.sh, watches the OLD container's
# processes across the restart and writes PROCS_RESULT to
# <capture-dir>/procs-<label>.env. PROCS_RESULT must be "ok"; a
# "FAIL:<r1>,<r2>" result adds "procs_<r1>", "procs_<r2>" etc. to
# FAIL_REASONS, and any "UNDETERMINED:*" result adds "procs_undetermined".
#
# This script always leaves a cycle outcome in <capture-dir>/state.env, on
# every exit path except SIGKILL:
#   CYCLE_<label>_STARTED=<utc>                             -- written before the restart
#   CYCLE_<label>=PASS | FAIL:<reasons> | INCOMPLETE:<step> -- the cycle's outcome
# INCOMPLETE:<step> is written by an EXIT trap when the script is interrupted
# (INT/TERM/HUP) or exits before a verdict is reached.
#
# Each step also prints "STEP <name> <utc>" as it starts, so a detached run's
# output file shows progress to a poller. Detached use:
#   nohup bash restart-cycle.sh <D> <label> <kind> > <D>/run-<label>.out 2>&1 < /dev/null &
# then poll <D>/state.env (outcome) and <D>/run-<label>.out (STEP lines)
# instead of waiting on the foreground process.
set -u

D="${1:-}"
LABEL="${2:-}"
KIND="${3:-}"

if [ -z "$D" ] || [ -z "$LABEL" ] || [ -z "$KIND" ]; then
  echo "usage: restart-cycle.sh <capture-dir> <label> <idle|active>" >&2
  exit 2
fi

STEP=init
VERDICT_WRITTEN=0

on_exit() {
  touch "$D/sampler-${LABEL}.stop" 2>/dev/null
  if [ "$VERDICT_WRITTEN" != "1" ]; then
    echo "CYCLE_${LABEL}=INCOMPLETE:${STEP}" >> "$D/state.env"
    echo "CYCLE ${LABEL} INCOMPLETE ${STEP}"
  fi
}

trap 'exit 130' INT TERM HUP
trap on_exit EXIT

echo "CYCLE_${LABEL}_STARTED=$(date -u +%FT%TZ)" >> "$D/state.env"

step() {
  STEP="$1"
  echo "STEP $1 $(date -u +%FT%TZ)"
}

SSY="http://127.0.0.1:8801"
LOG="/volume1/docker/v5test/seedsyncarr/log/seedsyncarr.log"
DOCKER="sudo /usr/local/bin/docker"

count_str() {
  # Safe fixed-string counting (122-12 lesson): never `|| echo 0`; a
  # no-match grep -c prints "0" itself, this just guards an empty read.
  local s="$1" f="$2" c
  c=$(grep -c -F -- "$s" "$f" 2>/dev/null)
  c=${c:-0}
  printf '%s' "$c"
}

FAIL_REASONS=""
add_fail() { FAIL_REASONS="${FAIL_REASONS}${FAIL_REASONS:+,}$1"; }

# Step 1: pre-restart remote scan time (may be null)
step pre_scan
PRE_SCAN="$(curl -s --max-time 15 "$SSY/server/status" | jq -r '.controller.latest_remote_scan_time // "null"' 2>/dev/null)"
[ -n "$PRE_SCAN" ] || PRE_SCAN="null"

# Step 2: pre-restart log line-count marker and restart timestamp
step marker
M="$(wc -l < "$LOG" 2>/dev/null)"
M="${M:-0}"
RESTART_UTC="$(date -u +%FT%TZ)"

# Step 2.5: start the live process sampler (GAP-2) before the restart
step sampler_start
rm -f "$D/sampler-${LABEL}.ready" "$D/sampler-${LABEL}.stop" "$D/procs-${LABEL}.txt"
bash "$D/proc-sampler.sh" sample "$D" "$LABEL" > "$D/run-sampler-${LABEL}.out" 2>&1 &
SAMPLER_PID=$!
SAMPLER_READY=0
for _ in $(seq 1 20); do
  if [ -f "$D/sampler-${LABEL}.ready" ]; then
    SAMPLER_READY=1
    break
  fi
  sleep 0.5
done
[ "$SAMPLER_READY" = "1" ] || add_fail procs_sampler_not_ready

# Step 3: restart the sandbox container
# (the one and only lifecycle action this script performs):
# sudo /usr/local/bin/docker restart seedsyncarr-test
step restart
RESTART_START_S="$(date +%s)"
$DOCKER restart seedsyncarr-test >/dev/null 2>&1
RESTART_RC=$?
RESTART_END_S="$(date +%s)"
RESTART_ELAPSED_S="$((RESTART_END_S - RESTART_START_S))"

# Stop the sampler now that the restart has returned, and wait (bounded at
# 10 s) for it to exit so it never outlives this cycle.
touch "$D/sampler-${LABEL}.stop"
for _ in $(seq 1 20); do
  kill -0 "$SAMPLER_PID" 2>/dev/null || break
  sleep 0.5
done

# Step 4: STARTING-POLL -- a fresh "Starting SeedSyncarr" line after the
# pre-restart marker, polled every 5s for up to 180s.
step starting_poll
STARTING_OK=0
for _ in $(seq 1 36); do
  if tail -n +"$((M + 1))" "$LOG" 2>/dev/null | grep -q -F -- "Starting SeedSyncarr"; then
    STARTING_OK=1
    break
  fi
  sleep 5
done
[ "$STARTING_OK" = "1" ] || add_fail starting

# Step 5: READY-POLL -- HTTP 200 from /server/status, polled every 5s for
# up to 120s.
step ready_poll
READY_OK=0
for _ in $(seq 1 24); do
  code="$(curl -s --max-time 10 -o /dev/null -w '%{http_code}' "$SSY/server/status" 2>/dev/null)"
  if [ "$code" = "200" ]; then
    READY_OK=1
    break
  fi
  sleep 5
done
[ "$READY_OK" = "1" ] || add_fail ready

# Step 6: harness settle (122-16 readiness-race lesson)
step settle
sleep 8

# Step 7: SCAN-POLL -- server.up true and a new remote scan, polled every
# 5s for up to 300s. Comparison against PRE_SCAN done with jq tonumber.
step scan_poll
SCAN_OK=0
POST_SCAN="null"
for _ in $(seq 1 60); do
  status_json="$(curl -s --max-time 10 "$SSY/server/status" 2>/dev/null)"
  up="$(printf '%s' "$status_json" | jq -r '.server.up // false' 2>/dev/null)"
  cur_scan="$(printf '%s' "$status_json" | jq -r '.controller.latest_remote_scan_time // "null"' 2>/dev/null)"
  [ -n "$cur_scan" ] || cur_scan="null"
  if [ "$up" = "true" ] && [ "$cur_scan" != "null" ]; then
    if [ "$PRE_SCAN" = "null" ]; then
      SCAN_OK=1
      POST_SCAN="$cur_scan"
      break
    fi
    newer="$(jq -n --arg a "$cur_scan" --arg b "$PRE_SCAN" '($a|tonumber) > ($b|tonumber)' 2>/dev/null)"
    if [ "$newer" = "true" ]; then
      SCAN_OK=1
      POST_SCAN="$cur_scan"
      break
    fi
  fi
  sleep 5
done
[ "$SCAN_OK" = "1" ] || add_fail scan

# Step 8: rotation guard
step rotation
ROTATED=0
M_NOW="$(wc -l < "$LOG" 2>/dev/null)"
M_NOW="${M_NOW:-0}"
if [ "$M_NOW" -lt "$M" ]; then
  ROTATED=1
  add_fail rotated
fi

# Step 9: save the window (from just after the pre-restart marker)
step window
WINDOW_FILE="$D/log-cycle-${LABEL}.txt"
tail -n +"$((M + 1))" "$LOG" 2>/dev/null > "$WINDOW_FILE"

# Step 10: counts over the window
step counts
SCANNER_DIED="$(count_str "Scanner process(es) died unexpectedly" "$WINDOW_FILE")"
COULD_NOT_TERMINATE="$(count_str "Could not terminate the child" "$WINDOW_FILE")"
CAUGHT_EXCEPTION_IN_JOB="$(count_str "Caught exception in job" "$WINDOW_FILE")"
ERROR_STOPPING="$(count_str "Error stopping" "$WINDOW_FILE")"
EXITED_SUCCESSFULLY="$(count_str "Exited successfully" "$WINDOW_FILE")"
STARTING_SEEN="$(count_str "Starting SeedSyncarr" "$WINDOW_FILE")"
STOPPED_DURING_SHUTDOWN="$(count_str "Scanner process(es) stopped during shutdown" "$WINDOW_FILE")"
ERROR_LINES="$(count_str " - ERROR - " "$WINDOW_FILE")"
LFTP_FORCE_KILL="$(count_str "did not exit on force close" "$WINDOW_FILE")"
LFTP_REAPED="$(count_str "reaped after force close" "$WINDOW_FILE")"

# Step 10.5: lftp-gone verdict from the live process sampler (GAP-2)
step procs_verdict
bash "$D/proc-sampler.sh" verdict "$D" "$LABEL"
PROCS_RESULT="$(grep -F "PROCS_RESULT=" "$D/procs-${LABEL}.env" 2>/dev/null | tail -n 1 | cut -d= -f2-)"
case "$PROCS_RESULT" in
  ok) ;;
  FAIL:*)
    reasons="${PROCS_RESULT#FAIL:}"
    old_ifs="$IFS"
    IFS=','
    for r in $reasons; do
      add_fail "procs_${r}"
    done
    IFS="$old_ifs"
    ;;
  *)
    add_fail procs_undetermined
    ;;
esac

# Step 11: write the per-cycle fact file
step env
ENV_FILE="$D/cycle-${LABEL}.env"
{
  echo "LABEL=$LABEL"
  echo "KIND=$KIND"
  echo "RESTART_UTC=$RESTART_UTC"
  echo "M=$M"
  echo "RESTART_RC=$RESTART_RC"
  echo "RESTART_ELAPSED_S=$RESTART_ELAPSED_S"
  echo "STARTING_OK=$STARTING_OK"
  echo "READY_OK=$READY_OK"
  echo "SCAN_OK=$SCAN_OK"
  echo "PRE_SCAN=$PRE_SCAN"
  echo "POST_SCAN=$POST_SCAN"
  echo "ROTATED=$ROTATED"
  echo "SCANNER_DIED=$SCANNER_DIED"
  echo "COULD_NOT_TERMINATE=$COULD_NOT_TERMINATE"
  echo "CAUGHT_EXCEPTION_IN_JOB=$CAUGHT_EXCEPTION_IN_JOB"
  echo "ERROR_STOPPING=$ERROR_STOPPING"
  echo "EXITED_SUCCESSFULLY=$EXITED_SUCCESSFULLY"
  echo "STARTING_SEEN=$STARTING_SEEN"
  echo "STOPPED_DURING_SHUTDOWN=$STOPPED_DURING_SHUTDOWN"
  echo "ERROR_LINES=$ERROR_LINES"
  echo "LFTP_FORCE_KILL=$LFTP_FORCE_KILL"
  echo "LFTP_REAPED=$LFTP_REAPED"
  echo "PROCS_RESULT=$PROCS_RESULT"
} > "$ENV_FILE"

# Step 12: PASS/FAIL verdict
step verdict
if [ "$RESTART_RC" -ne 0 ]; then add_fail restart_rc; fi
if [ "$SCANNER_DIED" -ne 0 ]; then add_fail scanner_died; fi
if [ "$COULD_NOT_TERMINATE" -ne 0 ]; then add_fail could_not_terminate; fi
if [ "$CAUGHT_EXCEPTION_IN_JOB" -ne 0 ]; then add_fail caught_exception_in_job; fi
if [ "$ERROR_STOPPING" -ne 0 ]; then add_fail error_stopping; fi

echo "RESTART_RC=$RESTART_RC RESTART_ELAPSED_S=$RESTART_ELAPSED_S STARTING_OK=$STARTING_OK READY_OK=$READY_OK SCAN_OK=$SCAN_OK ROTATED=$ROTATED"
echo "SCANNER_DIED=$SCANNER_DIED COULD_NOT_TERMINATE=$COULD_NOT_TERMINATE CAUGHT_EXCEPTION_IN_JOB=$CAUGHT_EXCEPTION_IN_JOB ERROR_STOPPING=$ERROR_STOPPING EXITED_SUCCESSFULLY=$EXITED_SUCCESSFULLY STARTING_SEEN=$STARTING_SEEN STOPPED_DURING_SHUTDOWN=$STOPPED_DURING_SHUTDOWN ERROR_LINES=$ERROR_LINES LFTP_FORCE_KILL=$LFTP_FORCE_KILL LFTP_REAPED=$LFTP_REAPED PROCS_RESULT=$PROCS_RESULT"

if [ -z "$FAIL_REASONS" ]; then
  VERDICT_WRITTEN=1
  echo "CYCLE_${LABEL}=PASS" >> "$D/state.env"
  echo "CYCLE $LABEL PASS"
  exit 0
else
  VERDICT_WRITTEN=1
  echo "CYCLE_${LABEL}=FAIL:${FAIL_REASONS}" >> "$D/state.env"
  echo "CYCLE $LABEL FAIL $FAIL_REASONS"
  exit 1
fi
