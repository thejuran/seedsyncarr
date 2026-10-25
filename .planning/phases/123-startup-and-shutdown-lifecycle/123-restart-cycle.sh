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
#
# PASS requires a clean restart exit code, a fresh start-up line, a ready
# status, a new remote scan, no rotation, zero of the three shutdown-error
# strings and at least one "Exited successfully". Exit 0 only on PASS.
# Prints status words and counts only -- no config values. Never names the
# production container.
set -u

D="${1:-}"
LABEL="${2:-}"
KIND="${3:-}"

if [ -z "$D" ] || [ -z "$LABEL" ] || [ -z "$KIND" ]; then
  echo "usage: restart-cycle.sh <capture-dir> <label> <idle|active>" >&2
  exit 2
fi

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
PRE_SCAN="$(curl -s --max-time 15 "$SSY/server/status" | jq -r '.controller.latest_remote_scan_time // "null"' 2>/dev/null)"
[ -n "$PRE_SCAN" ] || PRE_SCAN="null"

# Step 2: pre-restart log line-count marker and restart timestamp
M="$(wc -l < "$LOG" 2>/dev/null)"
M="${M:-0}"
RESTART_UTC="$(date -u +%FT%TZ)"

# Step 3: restart the sandbox container
# (the one and only lifecycle action this script performs):
# sudo /usr/local/bin/docker restart seedsyncarr-test
$DOCKER restart seedsyncarr-test >/dev/null 2>&1
RESTART_RC=$?

# Step 4: STARTING-POLL -- a fresh "Starting SeedSyncarr" line after the
# pre-restart marker, polled every 5s for up to 180s.
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
sleep 8

# Step 7: SCAN-POLL -- server.up true and a new remote scan, polled every
# 5s for up to 300s. Comparison against PRE_SCAN done with jq tonumber.
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
ROTATED=0
M_NOW="$(wc -l < "$LOG" 2>/dev/null)"
M_NOW="${M_NOW:-0}"
if [ "$M_NOW" -lt "$M" ]; then
  ROTATED=1
  add_fail rotated
fi

# Step 9: save the window (from just after the pre-restart marker)
WINDOW_FILE="$D/log-cycle-${LABEL}.txt"
tail -n +"$((M + 1))" "$LOG" 2>/dev/null > "$WINDOW_FILE"

# Step 10: counts over the window
SCANNER_DIED="$(count_str "Scanner process(es) died unexpectedly" "$WINDOW_FILE")"
COULD_NOT_TERMINATE="$(count_str "Could not terminate the child" "$WINDOW_FILE")"
CAUGHT_EXCEPTION_IN_JOB="$(count_str "Caught exception in job" "$WINDOW_FILE")"
ERROR_STOPPING="$(count_str "Error stopping" "$WINDOW_FILE")"
EXITED_SUCCESSFULLY="$(count_str "Exited successfully" "$WINDOW_FILE")"
STARTING_SEEN="$(count_str "Starting SeedSyncarr" "$WINDOW_FILE")"
STOPPED_DURING_SHUTDOWN="$(count_str "Scanner process(es) stopped during shutdown" "$WINDOW_FILE")"
ERROR_LINES="$(count_str " - ERROR - " "$WINDOW_FILE")"

# Step 11: write the per-cycle fact file
ENV_FILE="$D/cycle-${LABEL}.env"
{
  echo "LABEL=$LABEL"
  echo "KIND=$KIND"
  echo "RESTART_UTC=$RESTART_UTC"
  echo "M=$M"
  echo "RESTART_RC=$RESTART_RC"
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
} > "$ENV_FILE"

# Step 12: PASS/FAIL verdict
if [ "$RESTART_RC" -ne 0 ]; then add_fail restart_rc; fi
if [ "$SCANNER_DIED" -ne 0 ]; then add_fail scanner_died; fi
if [ "$COULD_NOT_TERMINATE" -ne 0 ]; then add_fail could_not_terminate; fi
if [ "$CAUGHT_EXCEPTION_IN_JOB" -ne 0 ]; then add_fail caught_exception_in_job; fi
if [ "$ERROR_STOPPING" -ne 0 ]; then add_fail error_stopping; fi
if [ "$EXITED_SUCCESSFULLY" -lt 1 ]; then add_fail exited_successfully; fi

echo "RESTART_RC=$RESTART_RC STARTING_OK=$STARTING_OK READY_OK=$READY_OK SCAN_OK=$SCAN_OK ROTATED=$ROTATED"
echo "SCANNER_DIED=$SCANNER_DIED COULD_NOT_TERMINATE=$COULD_NOT_TERMINATE CAUGHT_EXCEPTION_IN_JOB=$CAUGHT_EXCEPTION_IN_JOB ERROR_STOPPING=$ERROR_STOPPING EXITED_SUCCESSFULLY=$EXITED_SUCCESSFULLY STARTING_SEEN=$STARTING_SEEN STOPPED_DURING_SHUTDOWN=$STOPPED_DURING_SHUTDOWN ERROR_LINES=$ERROR_LINES"

if [ -z "$FAIL_REASONS" ]; then
  echo "CYCLE_${LABEL}=PASS" >> "$D/state.env"
  echo "CYCLE $LABEL PASS"
  exit 0
else
  echo "CYCLE_${LABEL}=FAIL:${FAIL_REASONS}" >> "$D/state.env"
  echo "CYCLE $LABEL FAIL $FAIL_REASONS"
  exit 1
fi
