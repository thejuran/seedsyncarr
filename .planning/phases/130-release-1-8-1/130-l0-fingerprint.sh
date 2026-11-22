#!/usr/bin/env bash
# Exact-restore proof (D-11) for the six Sonarr/Radarr fields of the Phase 130 Release
# 1.8.1 sandbox smoke (seedsyncarr-test, 127.0.0.1:8801 only; production is never named).
#
# Usage (on the NAS):
#   bash l0-fingerprint.sh precheck|capture|verify <capture-dir>
#
# Fields: sonarr.enabled, sonarr.sonarr_url, sonarr.sonarr_api_key,
#         radarr.enabled, radarr.radarr_url, radarr.radarr_api_key
# Each field is extracted with its own jq filter from one read of /server/config/get.
# The response is held in a shell variable only (never printed, never written to disk).
# A URL or key field that is present and null, or present and "", is fingerprinted as
# the literal EMPTY; any other value as the sha256 of its exact bytes (the enabled flags,
# which must be JSON booleans, via tostring).
#
#   precheck  Before anything changes: classifies the two key fields as EMPTY,
#             RESTORABLE (no surrounding whitespace and only printable ASCII without
#             space, the app's key rule) or NOT_RESTORABLE (the settings route would
#             trim or refuse it, so it could not be put back through the API).
#             Prints `L0_PRECHECK ok` (exit 0) or `L0_PRECHECK FAIL <fields>` (exit 1).
#             Writes nothing.
#   capture   Writes <capture-dir>/l0.fingerprint (mode 600, six field=fingerprint
#             lines). Refuses to overwrite an existing file (exit 2). Prints
#             `L0_CAPTURE ok fields=6` and `<field> EMPTY|SET` per field.
#   verify    Recomputes the six fingerprints and compares: `<field> SAME|DIFFERENT`
#             per field, then `L0_VERIFY ok` (exit 0) or `L0_VERIFY FAIL <fields>`
#             (exit 1). A missing, unreadable or malformed l0.fingerprint is
#             `L0_READ FAIL fingerprint_file` (exit 4).
#
# Fail-closed read contract (all modes): a failed or malformed read never looks like an
# empty setting. Any non-zero curl exit (even after an HTTP 200), a non-2xx status, a
# body that is not a JSON object, a missing section or field, a wrong type, or a key
# equal to **REDACTED** prints `L0_READ FAIL <reason>` and `L0_<MODE> FAIL read`, exits
# 4, prints no field line and no ok line, creates no file and changes no file.
#
# Never-print rule: no value, hash or length is ever printed. Tracing is never enabled.
#
# Local self-test hooks only (never set them on the NAS for the real smoke):
#   L0_TEST_JSON=<file>  read the config JSON from <file> instead of the API (a missing
#                        or unreadable file is `L0_READ FAIL transport`; no fallback).
#   L0_TEST_PORT=<port>  use 127.0.0.1:<port> instead of 8801 for the real request path
#                        (digits only, not 8800 or 8801; otherwise usage, exit 2).
# When either hook is set the first output line is `L0_TEST_HOOK active`.
set -euo pipefail

MODE="${1:-}"
D="${2:-}"

usage() {
  echo "usage: l0-fingerprint.sh precheck|capture|verify <capture-dir>" >&2
}

case "$MODE" in
  precheck|capture|verify) ;;
  *)
    usage
    exit 2
    ;;
esac

if [ -z "$D" ] || [ ! -d "$D" ]; then
  usage
  exit 2
fi

PORT=8801
TEST_JSON="${L0_TEST_JSON:-}"
TEST_PORT="${L0_TEST_PORT:-}"
if [ -n "${L0_TEST_PORT+x}" ]; then
  case "$TEST_PORT" in
    ''|*[!0-9]*)
      usage
      exit 2
      ;;
  esac
  if [ "$TEST_PORT" = "8800" ] || [ "$TEST_PORT" = "8801" ]; then
    usage
    exit 2
  fi
  PORT="$TEST_PORT"
fi

FP_FILE="$D/l0.fingerprint"
if [ "$MODE" = "capture" ] && { [ -e "$FP_FILE" ] || [ -L "$FP_FILE" ]; }; then
  echo "REFUSED l0.fingerprint already exists; not overwriting" >&2
  exit 2
fi

if [ -n "$TEST_JSON" ] || [ -n "${L0_TEST_PORT+x}" ]; then
  echo "L0_TEST_HOOK active"
fi

MODE_UPPER="PRECHECK"
[ "$MODE" = "capture" ] && MODE_UPPER="CAPTURE"
[ "$MODE" = "verify" ] && MODE_UPPER="VERIFY"

read_fail() {
  echo "L0_READ FAIL $1"
  echo "L0_${MODE_UPPER} FAIL read"
  exit 4
}

FIELDS="sonarr.enabled sonarr.sonarr_url sonarr.sonarr_api_key radarr.enabled radarr.radarr_url radarr.radarr_api_key"

if command -v sha256sum >/dev/null 2>&1; then
  hash_stdin() { sha256sum | cut -d' ' -f1; }
else
  hash_stdin() { shasum -a 256 | cut -d' ' -f1; }
fi

# jq over the body held in BODY; the body goes in on stdin via the builtin printf.
jqb() {
  printf '%s' "$BODY" | jq "$@"
}

# --- fingerprint file pre-read (verify) -------------------------------------------
# WANT[i] holds the recorded fingerprint of the i-th entry of FIELDS (indexed arrays
# only, so the script also runs under bash 3.2). The file must hold exactly the six
# fields, in FIELDS order, one field=fingerprint line each.
WANT=()
if [ "$MODE" = "verify" ]; then
  if [ ! -f "$FP_FILE" ] || [ ! -r "$FP_FILE" ]; then
    read_fail fingerprint_file
  fi
  if ! nlines="$(wc -l < "$FP_FILE" 2>/dev/null | tr -d ' ')"; then
    read_fail fingerprint_file
  fi
  if [ "$nlines" != "6" ]; then
    read_fail fingerprint_file
  fi
  i=0
  for f in $FIELDS; do
    i=$((i + 1))
    if ! line="$(sed -n "${i}p" "$FP_FILE" 2>/dev/null)"; then
      read_fail fingerprint_file
    fi
    name="${line%%=*}"
    val="${line#*=}"
    if [ "$name" != "$f" ] || [ "$name" = "$line" ] || [ -z "$val" ]; then
      read_fail fingerprint_file
    fi
    WANT+=("$val")
  done
fi

# --- (1)+(2) one read ---------------------------------------------------------------
BODY=""
if [ -n "$TEST_JSON" ]; then
  if [ ! -f "$TEST_JSON" ] || [ ! -r "$TEST_JSON" ]; then
    read_fail transport
  fi
  if ! BODY="$(cat "$TEST_JSON" 2>/dev/null)"; then
    read_fail transport
  fi
else
  if RESP="$(curl --silent --max-time 15 --write-out '\n%{http_code}' \
      "http://127.0.0.1:${PORT}/server/config/get" 2>/dev/null)"; then
    :
  else
    read_fail transport
  fi
  case "$RESP" in
    *$'\n'*) ;;
    *) read_fail transport ;;
  esac
  STATUS="${RESP##*$'\n'}"
  BODY="${RESP%$'\n'*}"
  case "$STATUS" in
    [0-9][0-9][0-9]) ;;
    *) read_fail transport ;;
  esac
  case "$STATUS" in
    2[0-9][0-9]) ;;
    *) read_fail "http_${STATUS}" ;;
  esac
fi

# --- (3) parsing --------------------------------------------------------------------
if TOP_TYPE="$(jqb -r 'type' 2>/dev/null)"; then
  :
else
  read_fail not_json
fi
if [ -z "$TOP_TYPE" ]; then
  read_fail not_json
fi
if [ "$TOP_TYPE" != "object" ]; then
  read_fail not_object
fi

# --- (4) presence -------------------------------------------------------------------
for sec in sonarr radarr; do
  if ! jqb -e --arg s "$sec" '(.[$s] | type) == "object"' >/dev/null 2>&1; then
    read_fail "missing:${sec}"
  fi
done
for f in $FIELDS; do
  sec="${f%%.*}"
  key="${f#*.}"
  if ! jqb -e --arg s "$sec" --arg k "$key" '.[$s] | has($k)' >/dev/null 2>&1; then
    read_fail "missing:${f}"
  fi
done

# --- (5) types ----------------------------------------------------------------------
for f in $FIELDS; do
  sec="${f%%.*}"
  key="${f#*.}"
  case "$key" in
    enabled)
      if ! jqb -e --arg s "$sec" '(.[$s].enabled | type) == "boolean"' >/dev/null 2>&1; then
        read_fail "type:${f}"
      fi
      ;;
    *_url)
      if ! jqb -e --arg s "$sec" --arg k "$key" '(.[$s][$k] | type) as $t | $t == "string" or $t == "null"' >/dev/null 2>&1; then
        read_fail "type:${f}"
      fi
      ;;
    *_api_key)
      if [ "$MODE" != "precheck" ]; then
        if ! jqb -e --arg s "$sec" --arg k "$key" '(.[$s][$k] | type) as $t | $t == "string" or $t == "null"' >/dev/null 2>&1; then
          read_fail "type:${f}"
        fi
      fi
      ;;
  esac
done

# --- (6) redaction ------------------------------------------------------------------
for f in sonarr.sonarr_api_key radarr.radarr_api_key; do
  sec="${f%%.*}"
  key="${f#*.}"
  if jqb -e --arg s "$sec" --arg k "$key" '.[$s][$k] == "**REDACTED**"' >/dev/null 2>&1; then
    read_fail "redacted:${f}"
  fi
done

# --- read validated; per-mode work --------------------------------------------------

# Prints EMPTY or the sha256 of the field's exact bytes (never echoed by the caller).
fingerprint() {
  local sec="$1" key="$2"
  if jqb -e --arg s "$sec" --arg k "$key" '.[$s][$k] == null or .[$s][$k] == ""' >/dev/null 2>&1; then
    printf '%s' "EMPTY"
    return 0
  fi
  jqb -j --arg s "$sec" --arg k "$key" '.[$s][$k] | tostring' | hash_stdin
}

if [ "$MODE" = "precheck" ]; then
  bad=""
  for f in sonarr.sonarr_api_key radarr.radarr_api_key; do
    sec="${f%%.*}"
    key="${f#*.}"
    if jqb -e --arg s "$sec" --arg k "$key" '.[$s][$k] == null or .[$s][$k] == ""' >/dev/null 2>&1; then
      verdict="EMPTY"
    elif jqb -e --arg s "$sec" --arg k "$key" '
        .[$s][$k] as $v
        | ($v | type) == "string"
          and ($v | length) > 0
          and (($v | sub("^\\s+"; "") | sub("\\s+$"; "") | length) == ($v | length))
          and (($v | explode | map(select(. < 33 or . > 126)) | length) == 0)
      ' >/dev/null 2>&1; then
      verdict="RESTORABLE"
    else
      verdict="NOT_RESTORABLE"
      bad="${bad}${bad:+ }${f}"
    fi
    echo "${f} ${verdict}"
  done
  if [ -z "$bad" ]; then
    echo "L0_PRECHECK ok"
    exit 0
  fi
  echo "L0_PRECHECK FAIL ${bad}"
  exit 1
fi

HAVE=()
for f in $FIELDS; do
  if ! fp="$(fingerprint "${f%%.*}" "${f#*.}")"; then
    read_fail "hash:${f}"
  fi
  if [ -z "$fp" ]; then
    read_fail "hash:${f}"
  fi
  HAVE+=("$fp")
done

if [ "$MODE" = "capture" ]; then
  lines=""
  i=0
  for f in $FIELDS; do
    lines="${lines}${f}=${HAVE[$i]}"$'\n'
    i=$((i + 1))
  done
  umask 077
  if ! ( set -o noclobber; printf '%s' "$lines" > "$FP_FILE" ) 2>/dev/null; then
    echo "REFUSED l0.fingerprint already exists; not overwriting" >&2
    exit 2
  fi
  chmod 600 "$FP_FILE"
  echo "L0_CAPTURE ok fields=6"
  i=0
  for f in $FIELDS; do
    if [ "${HAVE[$i]}" = "EMPTY" ]; then
      echo "${f} EMPTY"
    else
      echo "${f} SET"
    fi
    i=$((i + 1))
  done
  exit 0
fi

# verify
diff_list=""
i=0
for f in $FIELDS; do
  idx=$i
  i=$((i + 1))
  if [ "${HAVE[$idx]}" = "${WANT[$idx]}" ]; then
    echo "${f} SAME"
  else
    echo "${f} DIFFERENT"
    diff_list="${diff_list}${diff_list:+ }${f}"
  fi
done
if [ -z "$diff_list" ]; then
  echo "L0_VERIFY ok"
  exit 0
fi
echo "L0_VERIFY FAIL ${diff_list}"
exit 1
