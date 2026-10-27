#!/usr/bin/env bash
# Idempotent restore helper for the Phase 125 LAN Test Connection sandbox session
# (seedsyncarr-test).
#
# Usage (on the NAS):  bash teardown.sh [--final] [<capture-dir>]   (or env D=<capture-dir>)
# When neither is given, the capture dir defaults to the directory containing this
# script (it is copied into the capture dir as teardown.sh).
#
# Reads <capture-dir>/state.env (KEY=value lines; parsed, never sourced), last value wins:
#   IMAGE_PIN_L0    original seedsyncarr-test image pin, recorded before any deploy
#   DEV_PIN         the digest-pinned PR staging image this session deployed
#   SONARR_URL_L0   seedsyncarr-test's sonarr_url value recorded before any change
#   SONARR_URL_SET  1 if sonarr_url was changed this session and needs restoring
# A missing key means nothing of that kind was changed this session, and that restore
# step is a no-op (printed as "ok (not set this session)").
#
# --final additionally restores the sandbox image pin to IMAGE_PIN_L0 (inode-preserving
# compose edit, then `compose pull` + `compose up -d`) and requires the restored image to
# be verified; without --final the container is only `compose start`-ed if not running.
#
# Scope: only seedsyncarr-test and 127.0.0.1:8801 are touched. Production is never
# touched or named anywhere in this script. The Sonarr API key is never read or printed;
# output is status words, counts and HTTP codes only.
#
# Idempotent: running this script twice in a row is safe -- every restore step first
# checks the live/restored value and only acts if it differs, and every step ends with
# a verifying read-back rather than trusting the write.
set -u

FINAL=0
POSITIONAL=()
for a in "$@"; do
  if [ "$a" = "--final" ]; then
    FINAL=1
  else
    POSITIONAL+=("$a")
  fi
done

D="${POSITIONAL[0]:-${D:-}}"
if [ -z "$D" ]; then
  D="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
fi

SSY="http://127.0.0.1:8801"
COMPOSE_FILE="/volume1/docker/v5test/docker-compose.yml"
COMPOSE="sudo /usr/local/bin/docker compose -f $COMPOSE_FILE"
DOCKER="sudo /usr/local/bin/docker"

FAILED=""
fail() { FAILED="${FAILED}${FAILED:+,}$1"; }

state_get() {
  [ -n "$D" ] && [ -f "$D/state.env" ] || return 0
  grep -E "^$1=" "$D/state.env" | tail -n 1 | cut -d= -f2-
}
state_set() {
  # Append KEY=value; state_get's last-value-wins read picks this up on any later call.
  [ -n "$D" ] || return 0
  printf '%s=%s\n' "$1" "$2" >> "$D/state.env"
}

IMAGE_PIN_L0="$(state_get IMAGE_PIN_L0)"
SONARR_URL_L0="$(state_get SONARR_URL_L0)"
SONARR_URL_SET="$(state_get SONARR_URL_SET)"

get_sonarr_url() {
  curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // empty'
}
set_sonarr_url() {
  local value="$1" body
  body="$(jq -n --arg v "$value" '{section:"sonarr",key:"sonarr_url",value:$v}')"
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d "$body" "$SSY/server/config/set"
}

# (1) image pin: --final rewrites the compose line and recreates the container;
# otherwise the container is only started if it is not already running.
if [ "$FINAL" = "1" ]; then
  if [ -n "$IMAGE_PIN_L0" ]; then
    tmp="$D/.compose.yml.tmp.$$"
    before_inode="$(stat -c %i "$COMPOSE_FILE" 2>/dev/null)"
    awk -v pin="$IMAGE_PIN_L0" '
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
  else
    echo "IMAGE_PIN_L0 missing, cannot restore --final pin FAIL"
    fail image_pin_missing
  fi
else
  running="$($DOCKER inspect seedsyncarr-test --format '{{.State.Running}}' 2>/dev/null)"
  if [ "$running" != "true" ]; then
    $COMPOSE start seedsyncarr-test
  fi
fi

# (2) wait for /server/status 200
ok_status=0
for _ in $(seq 1 24); do
  code="$(curl -s --max-time 10 -o /dev/null -w '%{http_code}' "$SSY/server/status")"
  if [ "$code" = "200" ]; then
    ok_status=1
    break
  fi
  sleep 5
done
if [ "$ok_status" = "1" ]; then
  echo "WAIT server/status ok"
else
  echo "WAIT server/status FAIL"
  fail server_status
fi

# (3) sonarr_url restore
if [ "$SONARR_URL_SET" = "1" ] && [ -n "$SONARR_URL_L0" ]; then
  have="$(get_sonarr_url)"
  if [ "$have" != "$SONARR_URL_L0" ]; then
    set_sonarr_url "$SONARR_URL_L0"
    have="$(get_sonarr_url)"
  fi
  if [ "$have" = "$SONARR_URL_L0" ]; then
    echo "RESTORED sonarr_url ok"
    state_set SONARR_URL_SET 0
  else
    echo "RESTORED sonarr_url FAIL"
    fail sonarr_url
  fi
else
  echo "RESTORED sonarr_url ok (not set this session)"
fi

# (4) --final image restore verification
if [ "$FINAL" = "1" ]; then
  img="$($DOCKER inspect seedsyncarr-test --format '{{.Config.Image}}' 2>/dev/null)"
  if [ "$img" = "$IMAGE_PIN_L0" ]; then
    echo "CHECK image=restored ok"
  else
    echo "CHECK image=restored FAIL"
    fail image_restore
  fi
fi

if [ -z "$FAILED" ]; then
  echo "SANDBOX_RESTORED ok"
  exit 0
fi
echo "SANDBOX_RESTORED FAIL $FAILED"
exit 1
