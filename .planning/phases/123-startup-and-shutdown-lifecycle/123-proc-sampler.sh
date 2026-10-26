#!/usr/bin/env bash
# Live process sampler and lftp-gone verdict for the Phase 123 GAP-2 restart
# cycle. Watches the OLD (pre-restart) container generation's processes
# across a docker restart and proves whether the old lftp pid and its
# pre-restart children were actually reaped by the app before the old
# container's init process itself exited, instead of only inferring it from
# a quiet log.
#
# Usage:
#   bash proc-sampler.sh sample <capture-dir> <label>
#   bash proc-sampler.sh verdict <capture-dir> <label>
#
# sample mode: records, about every SAMPLER_INTERVAL_S (default 0.5s), the
# container's init host pid (docker inspect -f '{{.State.Pid}}') and, for
# every pid docker top lists, "pid ppid pgid sid state comm" read from host
# /proc/<pid>/stat. Sample 1 is taken first, then <capture-dir>/sampler-
# <label>.ready is touched. The loop stops when <capture-dir>/sampler-
# <label>.stop appears or SAMPLER_MAX_S (default 120) seconds pass. Output:
# <capture-dir>/procs-<label>.txt.
#
# Sample file format, one block per sample:
#   S <seq> <utc with ms, date -u +%FT%T.%3NZ> init=<host pid, 0 if not running>
#   P <pid> <ppid> <pgid> <sid> <state> <comm>   (one line per docker-top pid)
# comm is the text between the first "(" and the last ")" in /proc/<pid>/stat,
# spaces replaced by "_"; state/ppid/pgrp/session are the 1st-4th fields after
# that last ")". Pids whose stat cannot be read are skipped. Pids themselves
# come from the default `docker top` output: the header line is skipped, PID
# is column 2.
#
# verdict mode: reads <capture-dir>/procs-<label>.txt and decides whether the
# pre-restart ("OLD") lftp pid, and everything that depends on it, was gone
# from the OLD container generation before that generation's init process
# exited:
#   OLD_INIT       = init of sample 1.
#   old generation = samples whose init equals OLD_INIT, read only up to the
#                    first sample whose init differs (the new generation).
#   OLD_LFTP_PIDS       = pids with comm "lftp" in sample 1.
#   OLD_LFTP_CHILD_PIDS = pids in sample 1 whose ppid is an OLD_LFTP_PIDS pid.
#   LAST_OLD       = the last old-generation sample.
#   BG lftp        = an lftp-comm pid, in any old-generation sample, that was
#                    not present in sample 1 (a pid that appeared later).
# FAIL reasons, in this order, checked against LAST_OLD:
#   lftp_not_reaped     an OLD_LFTP_PIDS pid is still present (any state,
#                       including Z)
#   lftp_child_survived an OLD_LFTP_CHILD_PIDS pid is still present
#   lftp_backgrounded   a BG lftp pid is present
# UNDETERMINED reasons (checked in this order, first one wins):
#   no_presample     no sample 1, or its init is 0
#   no_lftp_before    OLD_LFTP_PIDS is empty
#   too_few_old_gen   fewer than 2 old-generation samples
# ok: none of the FAIL reasons fire and none of the UNDETERMINED reasons
# apply.
#
# Output: <capture-dir>/procs-<label>.env (also printed to stdout):
#   PROCS_RESULT=ok | FAIL:<reason>[,<reason>...] | UNDETERMINED:<why>
#   OLD_INIT, OLD_LFTP_PIDS, OLD_LFTP_CHILD_PIDS (pid:comm list),
#   OLD_GEN_SAMPLES, LFTP_STATES_SEEN (distinct state letters of the OLD
#   lftp pid(s) seen across old-generation samples -- e.g. S,D,Z -- the
#   live answer to the D-state hypothesis), LFTP_ZOMBIE_SEEN,
#   LFTP_GONE_UTC (first old-generation sample's time with no OLD lftp pid
#   present, or "none"), BG_LFTP_SEEN, SAMPLES_TOTAL.
#
# Overridable for local tests only (never on a real run):
#   SAMPLER_DOCKER (default "sudo /usr/local/bin/docker"), PROC_ROOT
#   (default /proc), SAMPLER_MAX_S (default 120), SAMPLER_INTERVAL_S
#   (default 0.5).
#
# This script only reads: docker top, docker inspect and /proc stat files.
# It never sends a signal, never writes app config, and never prints a
# config value. The only container it ever names is the sandbox container,
# seedsyncarr-test -- production is never touched or named.
set -u

MODE="${1:-}"
D="${2:-}"
LABEL="${3:-}"

usage() {
  echo "usage: proc-sampler.sh sample|verdict <capture-dir> <label>" >&2
}

if [ -z "$MODE" ] || [ -z "$D" ] || [ -z "$LABEL" ]; then
  usage
  exit 2
fi

SAMPLER_DOCKER="${SAMPLER_DOCKER:-sudo /usr/local/bin/docker}"
PROC_ROOT="${PROC_ROOT:-/proc}"
SAMPLER_MAX_S="${SAMPLER_MAX_S:-120}"
SAMPLER_INTERVAL_S="${SAMPLER_INTERVAL_S:-0.5}"
CONTAINER="seedsyncarr-test"

proc_line() {
  local pid="$1"
  local stat_file="$PROC_ROOT/$pid/stat"
  [ -r "$stat_file" ] || return 0
  local raw rest comm after_last state ppid pgrp session
  raw="$(cat "$stat_file" 2>/dev/null)" || return 0
  [ -n "$raw" ] || return 0
  rest="${raw#*(}"
  [ "$rest" != "$raw" ] || return 0
  comm="${rest%)*}"
  after_last="${rest##*)}"
  comm="${comm// /_}"
  read -r state ppid pgrp session _ <<< "$after_last"
  [ -n "$state" ] || return 0
  echo "P $pid $ppid $pgrp $session $state $comm"
}

take_one_sample() {
  local seq="$1"
  local ts init_pid
  ts="$(date -u +%FT%T.%3NZ)"
  init_pid="$($SAMPLER_DOCKER inspect -f '{{.State.Pid}}' "$CONTAINER" 2>/dev/null)"
  [ -n "$init_pid" ] || init_pid=0
  echo "S $seq $ts init=$init_pid"
  $SAMPLER_DOCKER top "$CONTAINER" 2>/dev/null | tail -n +2 | awk '{print $2}' | while read -r pid; do
    [ -n "$pid" ] || continue
    proc_line "$pid"
  done
}

do_sample() {
  local samples_file="$D/procs-${LABEL}.txt"
  local ready_file="$D/sampler-${LABEL}.ready"
  local stop_file="$D/sampler-${LABEL}.stop"
  : > "$samples_file"
  rm -f "$ready_file" "$stop_file"
  local seq=0 start_s now_s
  start_s="$(date +%s)"
  while :; do
    seq=$((seq + 1))
    take_one_sample "$seq" >> "$samples_file"
    if [ "$seq" -eq 1 ]; then
      touch "$ready_file"
    fi
    if [ -f "$stop_file" ]; then
      break
    fi
    now_s="$(date +%s)"
    if [ "$((now_s - start_s))" -ge "$SAMPLER_MAX_S" ]; then
      break
    fi
    sleep "$SAMPLER_INTERVAL_S"
  done
}

do_verdict() {
  local samples_file="$D/procs-${LABEL}.txt"
  local env_file="$D/procs-${LABEL}.env"
  [ -f "$samples_file" ] || : > "$samples_file"
  awk '
    function addr(r, name) { if (r == "") return name; return r "," name }
    function process_sample(   i, pid, ppid, comm, state) {
      if (have_sample1 == 0) {
        have_sample1 = 1
        sample1_init = cur_init
        for (i = 1; i <= n_cur; i++) {
          if (cur_comm[i] == "lftp") {
            n_lftp_pids++
            lftp_pid[n_lftp_pids] = cur_pids[i]
            is_lftp_pid[cur_pids[i]] = 1
          }
        }
        for (i = 1; i <= n_cur; i++) {
          if (is_lftp_pid[cur_ppid[i]] == 1) {
            n_child_pids++
            child_pid[n_child_pids] = cur_pids[i]
            child_comm[n_child_pids] = cur_comm[i]
          }
        }
      }
      if (old_gen_done == 1) return
      if (cur_init != sample1_init) {
        old_gen_done = 1
        return
      }
      n_old_gen++
      any_old_lftp_present = 0
      for (i = 1; i <= n_cur; i++) {
        pid = cur_pids[i]; comm = cur_comm[i]; state = cur_state[i]
        pid_last_seen_gen[pid] = n_old_gen
        if (is_lftp_pid[pid] == 1) {
          any_old_lftp_present = 1
          if (states_seen_str == "") {
            states_seen_str = state
          } else if (states_seen_str !~ ("(^|,)" state "(,|$)")) {
            states_seen_str = states_seen_str "," state
          }
          if (state == "Z") zombie_seen = 1
        }
        if (comm == "lftp" && is_lftp_pid[pid] != 1) {
          is_bg_pid[pid] = 1
          bg_seen = 1
        }
      }
      if (lftp_gone_found == 0 && any_old_lftp_present == 0 && n_lftp_pids > 0) {
        lftp_gone_found = 1
        lftp_gone_utc = cur_utc
      }
    }
    function emit(res,   olp, ocp, i) {
      olp = ""
      for (i = 1; i <= n_lftp_pids; i++) olp = (olp == "") ? lftp_pid[i] : olp "," lftp_pid[i]
      ocp = ""
      for (i = 1; i <= n_child_pids; i++) ocp = (ocp == "") ? (child_pid[i] ":" child_comm[i]) : (ocp "," child_pid[i] ":" child_comm[i])
      printf "PROCS_RESULT=%s\n", res
      printf "OLD_INIT=%s\n", sample1_init
      printf "OLD_LFTP_PIDS=%s\n", olp
      printf "OLD_LFTP_CHILD_PIDS=%s\n", ocp
      printf "OLD_GEN_SAMPLES=%d\n", n_old_gen
      printf "LFTP_STATES_SEEN=%s\n", states_seen_str
      printf "LFTP_ZOMBIE_SEEN=%d\n", zombie_seen
      printf "LFTP_GONE_UTC=%s\n", lftp_gone_utc
      printf "BG_LFTP_SEEN=%d\n", bg_seen
      printf "SAMPLES_TOTAL=%d\n", total_samples
    }
    function finalize(   i, reasons) {
      if (have_sample1 == 0 || sample1_init == 0) {
        emit("UNDETERMINED:no_presample")
        return
      }
      if (n_lftp_pids == 0) {
        emit("UNDETERMINED:no_lftp_before")
        return
      }
      if (n_old_gen < 2) {
        emit("UNDETERMINED:too_few_old_gen")
        return
      }
      reasons = ""
      for (i = 1; i <= n_lftp_pids; i++) {
        if (pid_last_seen_gen[lftp_pid[i]] == n_old_gen) { reasons = addr(reasons, "lftp_not_reaped"); break }
      }
      for (i = 1; i <= n_child_pids; i++) {
        if (pid_last_seen_gen[child_pid[i]] == n_old_gen) { reasons = addr(reasons, "lftp_child_survived"); break }
      }
      for (i in is_bg_pid) {
        if (pid_last_seen_gen[i] == n_old_gen) { reasons = addr(reasons, "lftp_backgrounded"); break }
      }
      if (reasons == "") emit("ok"); else emit("FAIL:" reasons)
    }
    BEGIN {
      have_sample1 = 0
      sample1_init = 0
      old_gen_done = 0
      n_old_gen = 0
      n_lftp_pids = 0
      n_child_pids = 0
      lftp_gone_found = 0
      lftp_gone_utc = "none"
      zombie_seen = 0
      bg_seen = 0
      states_seen_str = ""
      total_samples = 0
      cur_seq = 0
      n_cur = 0
    }
    /^S / {
      if (cur_seq != 0) process_sample()
      n_cur = 0
      cur_seq = $2
      cur_utc = $3
      split($4, initparts, "=")
      cur_init = initparts[2] + 0
      total_samples++
      next
    }
    /^P / {
      n_cur++
      cur_pids[n_cur] = $2
      cur_ppid[n_cur] = $3
      cur_state[n_cur] = $6
      cur_comm[n_cur] = $7
      next
    }
    END {
      if (cur_seq != 0) process_sample()
      finalize()
    }
  ' "$samples_file" | tee "$env_file"
}

case "$MODE" in
  sample)
    do_sample
    ;;
  verdict)
    do_verdict
    ;;
  *)
    usage
    exit 2
    ;;
esac
