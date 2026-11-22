#!/usr/bin/env bash
# Padded Sonarr/Radarr API key save for the Phase 130 Release 1.8.1 sandbox smoke
# (seedsyncarr-test, 127.0.0.1:8801 only).
#
# Purpose (D-10): send an Arr API key with stray whitespace around it through the same
# route the Settings page uses (POST /server/config/set), so the smoke can show that
# 1.8.1 saves it trimmed and the queue check then works.
#
# Usage (on the NAS):
#   bash padded-key-post.sh <capture-dir> <section> <key-option> <key-file>
#   <section> <key-option>  exactly "sonarr sonarr_api_key" or "radarr radarr_api_key"
#   <key-file>              0600, non-empty file holding the plain key
#
# The posted value is two spaces, the key, then a space and a tab. The JSON body is
# built by jq reading the key from stdin into a 0600 temp file inside <capture-dir>,
# removed on every exit path.
#
# Never-print rule: the key value never appears in argv, stdout, stderr or trace
# output. Tracing is never enabled. The only output is HTTP=<code> (or a usage/refusal
# message that names no value). Exit 0 on a 2xx answer, 1 otherwise, 2 on bad usage.
set -u

D="${1:-}"
SECTION="${2:-}"
KEY_OPTION="${3:-}"
KEY_FILE="${4:-}"

SSY="http://127.0.0.1:8801"

usage() {
  echo "usage: padded-key-post.sh <capture-dir> <sonarr|radarr> <sonarr_api_key|radarr_api_key> <key-file>" >&2
}

case "$SECTION $KEY_OPTION" in
  "sonarr sonarr_api_key"|"radarr radarr_api_key") ;;
  *)
    usage
    exit 2
    ;;
esac

if [ -z "$D" ] || [ ! -d "$D" ]; then
  echo "REFUSED capture dir missing" >&2
  exit 2
fi

if [ -z "$KEY_FILE" ] || [ ! -f "$KEY_FILE" ] || [ ! -s "$KEY_FILE" ]; then
  echo "REFUSED key file missing or empty" >&2
  exit 2
fi

mode="$(stat -c %a "$KEY_FILE" 2>/dev/null || stat -f %Lp "$KEY_FILE" 2>/dev/null || true)"
if [ "$mode" != "600" ]; then
  echo "REFUSED key file mode is not 600" >&2
  exit 2
fi

umask 077
BODY_FILE="$D/.padded-key-body.$$.json"
cleanup() { rm -f "$BODY_FILE"; }
trap cleanup EXIT
trap 'exit 1' INT TERM HUP

# jq 1.5 compatible (no --rawfile): read every stdin line raw and join them back.
if ! jq -nR --arg section "$SECTION" --arg key "$KEY_OPTION" \
    '{section:$section,key:$key,value:("  " + ([inputs]|join("\n")) + " \t")}' \
    < "$KEY_FILE" > "$BODY_FILE" 2>/dev/null; then
  echo "FAIL could not build request body" >&2
  exit 1
fi
chmod 0600 "$BODY_FILE"

code="$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' -X POST \
  -H "Content-Type: application/json" --data-binary "@${BODY_FILE}" \
  "$SSY/server/config/set" 2>/dev/null || true)"
echo "HTTP=${code:-000}"

case "$code" in
  2[0-9][0-9]) exit 0 ;;
  *) exit 1 ;;
esac
