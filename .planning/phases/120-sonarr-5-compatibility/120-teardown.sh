#!/usr/bin/env bash
# Idempotent teardown for the Sonarr 5 sandbox capture (seedsyncarr-test + sonarr-v5).
#
# Usage (on the NAS):  bash teardown.sh [<capture-dir>]     (or env D=<capture-dir>)
# When neither is given, the capture dir defaults to the directory containing this
# script (it is copied into the capture dir as teardown.sh).
#
# Reads <capture-dir>/state.env (KEY=value lines; parsed, never sourced):
#   MODE                    A (per-torrent Deluge move), B (Sonarr-side override), OWNER
#   NID                     id of the temporary "son5-capture" notification (informational;
#                           deletion is by name so partial creates and reruns are covered)
#   DELUGE_CLIENT_ID        sonarr-v5 download client id of the Deluge entry
#   DELUGE_DOWNLOAD_DIR_L0  Deluge downloadDirectory recorded before any change
#   SINK_NAME               capture sink container name (default son5-webhook-sink)
# A missing key means nothing of that kind was created. A missing state.env is a FAIL
# (the Deluge state cannot be verified); so is MODE=A without DELUGE_DOWNLOAD_DIR_L0 and
# MODE=B without DELUGE_CLIENT_ID or downloadclient-orig.json.
# The script never removes, pauses or moves a torrent in Deluge.
#
# Only sandbox endpoints are used: seedsyncarr-test (localhost:8801) and sonarr-v5
# (localhost:8990). The API key is read from the sandbox config.xml only and is never
# printed. Output is status words, counts and HTTP codes only. Exit 0 iff the last
# line is "SANDBOX_RESTORED ok".
set -u

D="${1:-${D:-}}"
if [ -z "$D" ]; then
  D="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
fi
SSY="http://localhost:8801"
SON="http://localhost:8990/api/v3"
SANDBOX_CFG="/volume1/docker/v5test/sonarr/config.xml"
TARGET_URL="http://sonarr-v5:8989"
DOCKER="sudo /usr/local/bin/docker"
CAPTURE_NOTIF="son5-capture"
BASELINE_NOTIF_COUNT=1

FAILED=""
fail() { FAILED="${FAILED}${FAILED:+,}$1"; }

state_get() {
  # Last KEY=value wins; values are plain tokens/paths written by the capture scripts.
  [ -n "$D" ] && [ -f "$D/state.env" ] || return 0
  grep -E "^$1=" "$D/state.env" | tail -n 1 | cut -d= -f2-
}

MODE="$(state_get MODE)"
NID="$(state_get NID)"
DELUGE_CLIENT_ID="$(state_get DELUGE_CLIENT_ID)"
DELUGE_DOWNLOAD_DIR_L0="$(state_get DELUGE_DOWNLOAD_DIR_L0)"
SINK_NAME="$(state_get SINK_NAME)"
SINK_NAME="${SINK_NAME:-son5-webhook-sink}"
: "${NID:=}"

K="$(sed -n 's:.*<ApiKey>\(.*\)</ApiKey>.*:\1:p' "$SANDBOX_CFG" 2>/dev/null | head -n 1)"
if [ -z "$K" ]; then
  echo "SANDBOX_KEY missing"
fi

son_get() { curl -s --max-time 30 -H "X-Api-Key: $K" "$SON/$1"; }

# (1) seedsyncarr-test sonarr_url
cur="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // empty' 2>/dev/null)"
if [ "$cur" != "$TARGET_URL" ]; then
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d "{\"section\":\"sonarr\",\"key\":\"sonarr_url\",\"value\":\"$TARGET_URL\"}" \
    "$SSY/server/config/set"
  cur="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // empty' 2>/dev/null)"
fi
if [ "$cur" = "$TARGET_URL" ]; then
  echo "RESTORED sonarr_url ok"
else
  echo "RESTORED sonarr_url FAIL"
  fail sonarr_url
fi

# (2) Deluge download client
dl_dir() {
  # $1 = JSON of one downloadclient resource
  printf '%s' "$1" | jq -r '.fields[]? | select(.name=="downloadDirectory") | .value // empty' 2>/dev/null
}
deluge_resource() {
  if [ -n "$DELUGE_CLIENT_ID" ]; then
    son_get "downloadclient/$DELUGE_CLIENT_ID"
  else
    son_get "downloadclient" | jq -c '[.[] | select(.implementation=="Deluge")][0] // empty' 2>/dev/null
  fi
}
if [ -z "$D" ] || [ ! -f "$D/state.env" ]; then
  echo "DELUGE state.env missing in capture dir, cannot verify FAIL"
  fail deluge
else
case "$MODE" in
  B)
    if [ -f "$D/downloadclient-orig.json" ] && [ -n "$DELUGE_CLIENT_ID" ]; then
      want="$(jq -r '.fields[]? | select(.name=="downloadDirectory") | .value // empty' "$D/downloadclient-orig.json" 2>/dev/null)"
      have="$(dl_dir "$(deluge_resource)")"
      if [ "$have" != "$want" ]; then
        code="$(curl -s --max-time 30 -o /dev/null -w '%{http_code}' -X PUT \
          -H "X-Api-Key: $K" -H "Content-Type: application/json" \
          --data-binary "@$D/downloadclient-orig.json" \
          "$SON/downloadclient/$DELUGE_CLIENT_ID")"
        echo "DELUGE restore PUT http=$code"
        have="$(dl_dir "$(deluge_resource)")"
      fi
      if [ -n "$want" ] && [ "$have" = "$want" ]; then
        echo "RESTORED deluge downloadDirectory ok"
      else
        echo "RESTORED deluge downloadDirectory FAIL"
        fail deluge
      fi
    else
      echo "RESTORED deluge downloadDirectory FAIL (MODE=B but downloadclient-orig.json or DELUGE_CLIENT_ID missing)"
      fail deluge
    fi
    ;;
  OWNER)
    echo "REMINDER owner restores Deluge downloadDirectory"
    ;;
  *)
    if [ -n "$DELUGE_DOWNLOAD_DIR_L0" ]; then
      have="$(dl_dir "$(deluge_resource)")"
      if [ "$have" = "$DELUGE_DOWNLOAD_DIR_L0" ]; then
        echo "DELUGE per-torrent mode, no client change (downloadDirectory matches L0: yes)"
      else
        echo "DELUGE per-torrent mode, no client change (downloadDirectory matches L0: no)"
        fail deluge
      fi
    elif [ "$MODE" = "A" ]; then
      echo "DELUGE per-torrent mode FAIL (MODE=A but no L0 baseline recorded)"
      fail deluge
    else
      echo "DELUGE per-torrent mode, no client change (no L0 baseline recorded)"
    fi
    ;;
esac
fi

# (3) Notifications: delete every "son5-capture" entry by name, then verify.
notifs="$(son_get notification)"
if printf '%s' "$notifs" | jq -e 'type=="array"' >/dev/null 2>&1; then
  for id in $(printf '%s' "$notifs" | jq -r --arg n "$CAPTURE_NOTIF" '.[] | select(.name==$n) | .id'); do
    code="$(curl -s --max-time 30 -o /dev/null -w '%{http_code}' -X DELETE \
      -H "X-Api-Key: $K" "$SON/notification/$id")"
    echo "DELETED notification http=$code"
  done
  notifs="$(son_get notification)"
fi
if printf '%s' "$notifs" | jq -e 'type=="array"' >/dev/null 2>&1; then
  n_count="$(printf '%s' "$notifs" | jq 'length')"
  n_present="$(printf '%s' "$notifs" | jq --arg n "$CAPTURE_NOTIF" '[.[] | select(.name==$n)] | length')"
  [ "$n_present" -gt 0 ] && n_present=1
  echo "RESTORED notifications count=$n_count son5-capture-present=$n_present"
  if [ "$n_count" != "$BASELINE_NOTIF_COUNT" ] || [ "$n_present" != "0" ]; then
    fail notifications
  fi
  prod_hits="$(printf '%s' "$notifs" | jq '[.[] | .fields[]? | select(.name=="url") | (.value // "" | tostring)
      | select(contains("seedsyncarr:8800") or contains("//seedsyncarr/") or contains("//seedsyncarr:"))] | length')"
  if [ "$prod_hits" = "0" ]; then
    echo "NOTIF_URLS_OK"
  else
    echo "NOTIF_URLS_FAIL"
    fail notif_urls
  fi
else
  echo "RESTORED notifications FAIL (sonarr-v5 unreachable)"
  echo "NOTIF_URLS_FAIL"
  fail notifications
fi

# (4) Capture sink container
if $DOCKER ps -a --format '{{.Names}}' | grep -qx "$SINK_NAME"; then
  $DOCKER rm -f "$SINK_NAME" >/dev/null 2>&1
  if $DOCKER ps -a --format '{{.Names}}' | grep -qx "$SINK_NAME"; then
    echo "REMOVED sink FAIL"
    fail sink
  else
    echo "REMOVED sink"
  fi
else
  echo "REMOVED sink (absent)"
fi

# (5) Final read-back
final_url="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // empty' 2>/dev/null)"
if [ "$final_url" = "$TARGET_URL" ]; then
  echo "CHECK sonarr_url=$final_url"
else
  # Never print a non-default value: it may hold the Tailscale address.
  echo "CHECK sonarr_url=<non-default>"
  case ",$FAILED," in *,sonarr_url,*) ;; *) fail sonarr_url ;; esac
fi
if [ -z "$FAILED" ]; then
  echo "SANDBOX_RESTORED ok"
  exit 0
fi
echo "SANDBOX_RESTORED FAIL $FAILED"
exit 1
