#!/usr/bin/env bash
# D-09 live check for the Phase 125 LAN Test Connection fix on the NAS sandbox
# (seedsyncarr-test).
#
# Usage (on the NAS):  bash livecheck.sh <capture-dir>
#
# Reads <capture-dir>/state.env (written by the caller before this script runs):
#   IMAGE_PIN_L0   the sandbox's original image pin (required at preflight)
#   DEV_PIN        this phase's PR CI staging image, pinned by digest (required)
# This script appends further KEY=value lines to the same file as it runs
# (SONARR_URL_L0, SONARR_URL_SET, BEFORE_SUCCESS, BEFORE_OLD_MSG, POSITIVE,
# POSITIVE_VERSION, NEGATIVE, NEGATIVE_CR01, CHECK_STATUS) using the same
# last-value-wins contract as 125-teardown.sh.
#
# Sequence: preflight (nothing changed yet) -> fingerprint production (read-only) ->
# point sonarr_url at the Docker container name -> BEFORE check on the original image
# (informational) -> deploy DEV_PIN -> POSITIVE check (LAN-01) -> NEGATIVE check against
# a cloud-metadata address (LAN-02) -> NEGATIVE_CR01 check against the 125-REVIEW CR-01
# backslash payload (D-11), restoring sonarr_url immediately after both negatives ->
# re-check production is unchanged -> CHECK_STATUS.
#
# Only seedsyncarr-test and 127.0.0.1:8801 are changed. Production is only ever
# fingerprinted with a single read-only `docker inspect`, never started, stopped,
# recreated or reconfigured. The Sonarr API key is never read or printed; the
# test-connection response has no key in it, and config reads are limited to
# .sonarr.sonarr_url. Output is status words, HTTP codes, the Sonarr version and the
# refusal text only.
#
# Safety net: the EXIT trap runs `teardown.sh --final` on any exit except a fully
# passing check (CHECK_STATUS=PASS) with a verified sonarr_url restore. On that single
# success path, OK=1 so the trap steps aside and the explicit `teardown.sh --final` call
# (run separately, after this script exits) does the full image-pin restore and final
# verification. Any failure after the deploy step -- including a failed negative check --
# therefore restores the sandbox automatically via the trap.
set -u

D="${1:-}"
if [ -z "$D" ]; then
  echo "usage: bash livecheck.sh <capture-dir>" >&2
  exit 2
fi

SSY="http://127.0.0.1:8801"
COMPOSE_FILE="/volume1/docker/v5test/docker-compose.yml"
COMPOSE="sudo /usr/local/bin/docker compose -f $COMPOSE_FILE"
DOCKER="sudo /usr/local/bin/docker"
TARGET_URL="http://sonarr-v5:8989"
REFUSED_URL="http://169.254.169.254"
EXPECTED_REFUSAL="URL points to a link-local or cloud-metadata address, which is not allowed"
CR01_URL='http://169.254.169.254\@sonarr-v5:8989'
EXPECTED_CR01_REFUSAL="Invalid URL: it contains a space, backslash or other character that is not allowed"
APP_LOG="/volume1/docker/v5test/seedsyncarr/log/seedsyncarr.log"
PROD_NAME="seedsyncarr"

FAILED=""
fail() { FAILED="${FAILED}${FAILED:+,}$1"; }

state_get() {
  [ -n "$D" ] && [ -f "$D/state.env" ] || return 0
  grep -E "^$1=" "$D/state.env" | tail -n 1 | cut -d= -f2-
}
state_set() {
  [ -n "$D" ] || return 0
  printf '%s=%s\n' "$1" "$2" >> "$D/state.env"
}

IMAGE_PIN_L0="$(state_get IMAGE_PIN_L0)"
DEV_PIN="$(state_get DEV_PIN)"

get_sonarr_url() {
  curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // ""'
}
set_sonarr_url() {
  local value="$1" body
  body="$(jq -n --arg v "$value" '{section:"sonarr",key:"sonarr_url",value:$v}')"
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d "$body" "$SSY/server/config/set"
}
prod_fp() {
  $DOCKER inspect "$PROD_NAME" --format '{{.Id}} {{.Image}} {{.Config.Image}} {{.State.Status}} {{.State.StartedAt}}' 2>/dev/null
}
wait_status_200() {
  local i=0
  while [ "$i" -lt 24 ]; do
    code="$(curl -s --max-time 10 -o /dev/null -w '%{http_code}' "$SSY/server/status")"
    [ "$code" = "200" ] && return 0
    i=$((i + 1))
    sleep 5
  done
  return 1
}
# One GET of test-connection; writes the full response to <capture-dir>/<label>.json and
# prints exactly three lines (.success, .version or "", .error or "") -- nothing else --
# so callers can capture them by command substitution and read fixed line numbers. Using
# jq's `empty` here would suppress an absent field instead of emitting a blank line,
# shifting every field after it up by one line, so the fallback is an explicit "".
tc() {
  local label="$1" resp
  resp="$(curl -s --max-time 15 "$SSY/server/config/sonarr/test-connection")"
  printf '%s' "$resp" > "$D/${label}.json"
  echo "$resp" | jq -r '.success, (.version // ""), (.error // "")'
}

OK=0
trap 'exit 130' INT TERM HUP
trap '[ "$OK" = 1 ] || bash "$D/teardown.sh" --final' EXIT

# --- Preflight: nothing changed yet ---
COMPOSE_IMG_LINE="$(grep -E '^[[:space:]]*image:[[:space:]]*ghcr\.io/thejuran/seedsyncarr[:@]' "$COMPOSE_FILE" | head -n 1 | sed -E 's/^[[:space:]]*image:[[:space:]]*//')"
CUR_IMAGE="$($DOCKER inspect seedsyncarr-test --format '{{.Config.Image}}' 2>/dev/null)"
if [ -z "$IMAGE_PIN_L0" ] || [ "$COMPOSE_IMG_LINE" != "$IMAGE_PIN_L0" ] || [ "$CUR_IMAGE" != "$IMAGE_PIN_L0" ]; then
  echo "PREFLIGHT FAIL compose=$COMPOSE_IMG_LINE running=$CUR_IMAGE expected=$IMAGE_PIN_L0"
  OK=1
  echo "LIVECHECK FAIL preflight"
  exit 1
fi
echo "PREFLIGHT ok"

if [ -z "$DEV_PIN" ]; then
  echo "DEV_PIN missing FAIL"
  OK=1
  echo "LIVECHECK FAIL dev_pin_missing"
  exit 1
fi

prod_fp > "$D/prod-before.txt"

SONARR_URL_L0="$(get_sonarr_url)"
state_set SONARR_URL_L0 "$SONARR_URL_L0"

if [ "$SONARR_URL_L0" != "$TARGET_URL" ]; then
  state_set SONARR_URL_SET 1
  set_sonarr_url "$TARGET_URL"
  have="$(get_sonarr_url)"
  if [ "$have" = "$TARGET_URL" ]; then
    echo "SET sonarr_url target ok"
  else
    echo "SET sonarr_url target FAIL"
    fail url_set_target
  fi
fi

# --- BEFORE (informational, still on IMAGE_PIN_L0) ---
before_out="$(tc before)"
BEFORE_SUCCESS="$(printf '%s\n' "$before_out" | sed -n '1p')"
BEFORE_ERROR="$(printf '%s\n' "$before_out" | sed -n '3p')"
BEFORE_OLD_MSG=0
case "$BEFORE_ERROR" in
  *private/reserved*) BEFORE_OLD_MSG=1 ;;
esac
state_set BEFORE_SUCCESS "$BEFORE_SUCCESS"
state_set BEFORE_OLD_MSG "$BEFORE_OLD_MSG"
echo "BEFORE success=$BEFORE_SUCCESS old_msg=$BEFORE_OLD_MSG"

# --- Deploy DEV_PIN ---
M0="$(wc -l < "$APP_LOG" 2>/dev/null)"; M0="${M0:-0}"

tmp="$D/.compose.yml.tmp.$$"
before_inode="$(stat -c %i "$COMPOSE_FILE" 2>/dev/null)"
awk -v pin="$DEV_PIN" '
  /^[[:space:]]*image:[[:space:]]*ghcr\.io\/thejuran\/seedsyncarr[:@]/ && !done { sub(/image:.*/, "image: " pin); done=1 }
  { print }
' "$COMPOSE_FILE" > "$tmp"
cat "$tmp" > "$COMPOSE_FILE"
rm -f "$tmp"
after_inode="$(stat -c %i "$COMPOSE_FILE" 2>/dev/null)"
echo "INODE before=$before_inode after=$after_inode"
if [ "$before_inode" != "$after_inode" ]; then
  echo "INODE mismatch FAIL"
  fail inode_mismatch
fi

$COMPOSE pull seedsyncarr-test
$COMPOSE up -d seedsyncarr-test

ready=0
i=0
while [ "$i" -lt 36 ]; do
  if tail -n "+$((M0 + 1))" "$APP_LOG" 2>/dev/null | grep -q "Starting SeedSyncarr"; then
    ready=1
    break
  fi
  i=$((i + 1))
  sleep 5
done
if [ "$ready" = "1" ]; then
  echo "DEPLOY starting-line ok"
else
  echo "DEPLOY starting-line FAIL"
  fail starting_line
fi

if wait_status_200; then
  echo "WAIT server/status ok"
else
  echo "WAIT server/status FAIL"
  fail server_status
fi
sleep 8

DEPLOYED_IMAGE="$($DOCKER inspect seedsyncarr-test --format '{{.Config.Image}}' 2>/dev/null)"
DEPLOYED_IMAGE_ID="$($DOCKER inspect seedsyncarr-test --format '{{.Image}}' 2>/dev/null)"
echo "DEPLOY image=$DEPLOYED_IMAGE id=$DEPLOYED_IMAGE_ID"
if [ "$DEPLOYED_IMAGE" != "$DEV_PIN" ]; then
  echo "DEPLOY image mismatch FAIL"
  fail dev_pin_mismatch
fi

# --- POSITIVE (LAN-01) ---
positive_out="$(tc positive)"
POS_SUCCESS="$(printf '%s\n' "$positive_out" | sed -n '1p')"
POS_VERSION="$(printf '%s\n' "$positive_out" | sed -n '2p')"
POSITIVE=FAIL
case "$POS_SUCCESS/$POS_VERSION" in
  true/5.*) POSITIVE=PASS ;;
esac
state_set POSITIVE "$POSITIVE"
state_set POSITIVE_VERSION "$POS_VERSION"
echo "POSITIVE $POSITIVE success=$POS_SUCCESS version=$POS_VERSION"
[ "$POSITIVE" = "PASS" ] || fail positive

# --- NEGATIVE (LAN-02) ---
state_set SONARR_URL_SET 1
set_sonarr_url "$REFUSED_URL"
have="$(get_sonarr_url)"
if [ "$have" != "$REFUSED_URL" ]; then
  echo "SET sonarr_url refused FAIL"
  fail url_set_refused
fi

negative_out="$(tc negative)"
NEG_SUCCESS="$(printf '%s\n' "$negative_out" | sed -n '1p')"
NEG_ERROR="$(printf '%s\n' "$negative_out" | sed -n '3p')"
NEGATIVE=FAIL
if [ "$NEG_SUCCESS" = "false" ] && [ "$NEG_ERROR" = "$EXPECTED_REFUSAL" ]; then
  NEGATIVE=PASS
fi
state_set NEGATIVE "$NEGATIVE"
echo "NEGATIVE $NEGATIVE success=$NEG_SUCCESS error=$NEG_ERROR"
[ "$NEGATIVE" = "PASS" ] || fail negative

# --- NEGATIVE_CR01 (D-11: 125-REVIEW CR-01 backslash payload) ---
state_set SONARR_URL_SET 1
set_sonarr_url "$CR01_URL"
have="$(get_sonarr_url)"
if [ "$have" != "$CR01_URL" ]; then
  echo "SET sonarr_url cr01 FAIL"
  fail url_set_cr01
fi

negative_cr01_out="$(tc negative_cr01)"
NEGCR01_SUCCESS="$(printf '%s\n' "$negative_cr01_out" | sed -n '1p')"
NEGCR01_ERROR="$(printf '%s\n' "$negative_cr01_out" | sed -n '3p')"
NEGATIVE_CR01=FAIL
if [ "$NEGCR01_SUCCESS" = "false" ] && [ "$NEGCR01_ERROR" = "$EXPECTED_CR01_REFUSAL" ]; then
  NEGATIVE_CR01=PASS
fi
state_set NEGATIVE_CR01 "$NEGATIVE_CR01"
echo "NEGATIVE_CR01 $NEGATIVE_CR01 success=$NEGCR01_SUCCESS error=$NEGCR01_ERROR"
[ "$NEGATIVE_CR01" = "PASS" ] || fail negative_cr01

# Restore sonarr_url immediately, regardless of either negative's outcome.
set_sonarr_url "$SONARR_URL_L0"
have="$(get_sonarr_url)"
if [ "$have" = "$SONARR_URL_L0" ]; then
  echo "RESTORED sonarr_url ok"
  state_set SONARR_URL_SET 0
  URL_RESTORED=1
else
  echo "RESTORED sonarr_url FAIL"
  fail sonarr_url_restore
  URL_RESTORED=0
fi

# --- Informational log counts in the window after M0 ---
window="$(tail -n "+$((M0 + 1))" "$APP_LOG" 2>/dev/null)"
c_err="$(printf '%s\n' "$window" | grep -c -F ' - ERROR - ' 2>/dev/null)"; c_err="${c_err:-0}"
c_unexp="$(printf '%s\n' "$window" | grep -c -F 'Unexpected error testing' 2>/dev/null)"; c_unexp="${c_unexp:-0}"
echo "LOGCOUNT error=$c_err unexpected_error_testing=$c_unexp"

# --- Production fingerprint re-check ---
prod_fp > "$D/prod-after.txt"
if diff -q "$D/prod-before.txt" "$D/prod-after.txt" >/dev/null 2>&1; then
  echo "PROD fingerprint unchanged"
else
  echo "PROD fingerprint CHANGED FAIL"
  fail prod_changed
fi

# --- CHECK_STATUS ---
CHECK_STATUS=PASS
if [ "$POSITIVE" != "PASS" ] || [ "$NEGATIVE" != "PASS" ] || [ "$NEGATIVE_CR01" != "PASS" ] || [ "$URL_RESTORED" != "1" ] || [ "$DEPLOYED_IMAGE" != "$DEV_PIN" ] || [ -n "$FAILED" ]; then
  CHECK_STATUS=FAIL
fi
state_set CHECK_STATUS "$CHECK_STATUS"

if [ "$CHECK_STATUS" = "PASS" ] && [ "$URL_RESTORED" = "1" ]; then
  OK=1
fi

if [ "$CHECK_STATUS" = "PASS" ]; then
  echo "LIVECHECK PASS"
  exit 0
fi
echo "LIVECHECK FAIL $FAILED"
exit 1
