#!/usr/bin/env bash
# Signed synthetic Sonarr/Radarr webhook poster for Phase 126 Release 1.8.0 smoke sessions.
#
# Usage (on the NAS):
#   bash webhook-post.sh <capture-dir> <source> <eventType> <root> <child-or-root>
#   <capture-dir>  session dir holding a 0600 "secret" file (the HMAC key; never printed)
#   <source>       "sonarr" or "radarr" (anything else: exit 2, nothing posted)
#   <eventType>    "Download" or "Test" (anything else: exit 2, nothing posted)
#   <root>         synthetic root name, must start with "SSA126." (exit 2 otherwise)
#   <child>        child basename under <root>, or exactly <root> to post the root's own
#                  path as sourcePath (no child subpath); ignored for a Test event body
#                  but still required and still prefix-checked
#
# Download body:
#   sonarr: {"eventType":"Download","episodeFile":{"sourcePath":"/data/torrents/<root>[/<child>]"},
#            "isUpgrade":false,"instanceName":"Sonarr"}
#   radarr: {"eventType":"Download","movieFile":{"sourcePath":"/data/torrents/<root>[/<child>]"},
#            "isUpgrade":false,"instanceName":"Radarr"}
# Test body (either source): {"eventType":"Test","instanceName":"<Sonarr|Radarr>"}
#
# POSTs to /server/webhook/<source>. The HMAC is computed by piping the secret file and
# then the body file into the sandbox container's own python3 (stdlib hmac/hashlib) over
# stdin -- the first stdin line is the key, everything after the first newline is the
# body -- so the secret is never placed in any command's argv and never appears in this
# script's output. Appends one line to <capture-dir>/webhooks.log and prints only the
# HTTP code and response body.
set -u

D="${1:-}"
SOURCE="${2:-}"
EVENT_TYPE="${3:-}"
ROOT="${4:-}"
CHILD="${5:-}"

usage() {
  echo "usage: webhook-post.sh <capture-dir> <sonarr|radarr> <Download|Test> <root> <child-or-root>" >&2
}

if [ -z "$D" ] || [ -z "$SOURCE" ] || [ -z "$EVENT_TYPE" ] || [ -z "$ROOT" ] || [ -z "$CHILD" ]; then
  usage
  exit 2
fi

case "$SOURCE" in
  sonarr|radarr) ;;
  *)
    echo "REFUSED source (must be sonarr or radarr): $SOURCE" >&2
    exit 2
    ;;
esac

case "$EVENT_TYPE" in
  Download|Test) ;;
  *)
    echo "REFUSED eventType (must be Download or Test): $EVENT_TYPE" >&2
    exit 2
    ;;
esac

case "$ROOT" in
  SSA126.*) ;;
  *)
    echo "REFUSED root (bad prefix): $ROOT" >&2
    exit 2
    ;;
esac

SECRET_FILE="$D/secret"
if [ ! -f "$SECRET_FILE" ]; then
  echo "FAIL missing $SECRET_FILE" >&2
  exit 1
fi

SSY="http://127.0.0.1:8801"
DOCKER="sudo /usr/local/bin/docker"

if [ "$SOURCE" = "sonarr" ]; then
  INSTANCE_NAME="Sonarr"
else
  INSTANCE_NAME="Radarr"
fi

umask 077
BODY_FILE="$D/.webhook-body.$$.json"

if [ "$EVENT_TYPE" = "Test" ]; then
  printf '{"eventType":"Test","instanceName":"%s"}' "$INSTANCE_NAME" > "$BODY_FILE"
else
  if [ "$CHILD" = "$ROOT" ]; then
    SOURCE_PATH="/data/torrents/$ROOT"
  else
    SOURCE_PATH="/data/torrents/$ROOT/$CHILD"
  fi
  if [ "$SOURCE" = "sonarr" ]; then
    printf '{"eventType":"Download","episodeFile":{"sourcePath":"%s"},"isUpgrade":false,"instanceName":"%s"}' \
      "$SOURCE_PATH" "$INSTANCE_NAME" > "$BODY_FILE"
  else
    printf '{"eventType":"Download","movieFile":{"sourcePath":"%s"},"isUpgrade":false,"instanceName":"%s"}' \
      "$SOURCE_PATH" "$INSTANCE_NAME" > "$BODY_FILE"
  fi
fi
chmod 0600 "$BODY_FILE"

# Normalize to exactly one newline between key and body regardless of whether the secret
# file itself ends in a trailing newline (command substitution strips any trailing
# newlines from $(cat ...), so printf re-adds exactly one).
SIG="$( { printf '%s\n' "$(cat "$SECRET_FILE")"; cat "$BODY_FILE"; } | \
  $DOCKER exec -i seedsyncarr-test python3 -c '
import sys, hmac, hashlib
data = sys.stdin.buffer.read()
nl = data.find(b"\n")
key = data[:nl]
body = data[nl + 1:]
print(hmac.new(key, body, hashlib.sha256).hexdigest())
' )"

if [ -z "$SIG" ]; then
  echo "FAIL hmac computation produced no signature" >&2
  rm -f "$BODY_FILE"
  exit 1
fi

RESP_FILE="$D/.webhook-response.$$.json"
HTTP_CODE="$(curl -s --max-time 15 -o "$RESP_FILE" -w '%{http_code}' \
  -X POST -H "Content-Type: application/json" -H "X-Webhook-Signature: ${SIG}" \
  --data-binary "@${BODY_FILE}" "$SSY/server/webhook/$SOURCE")"

TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
printf '%s %s %s %s %s\n' "$TS" "$SOURCE" "$EVENT_TYPE" "$CHILD" "$HTTP_CODE" >> "$D/webhooks.log"

echo "HTTP_CODE=$HTTP_CODE"
cat "$RESP_FILE"
echo

rm -f "$BODY_FILE" "$RESP_FILE"
