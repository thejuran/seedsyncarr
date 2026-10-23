#!/usr/bin/env bash
# Signed synthetic Sonarr Download webhook poster for Phase 122 SAFE-01 sessions.
#
# Usage (on the NAS): bash webhook-post.sh <capture-dir> <root> <child-basename-or-root>
#   <capture-dir>  session dir holding a 0600 "secret" file (the HMAC key; never printed)
#   <root>         synthetic root name, must start with "SSA122."
#   <child>        child basename under <root>, or exactly <root> to post the root's own
#                  path as sourcePath (no child subpath)
#
# Builds {"eventType":"Download","episodeFile":{"sourcePath":"/data/torrents/<root>/<child>"},
# "isUpgrade":false,"instanceName":"Sonarr"} (sourcePath becomes "/data/torrents/<root>"
# when <child> equals <root>) into a 0600 file in <capture-dir>, with no trailing newline.
#
# The HMAC is computed by piping the secret file and then the body file into the sandbox
# container's own python3 (stdlib hmac/hashlib) over stdin -- the first stdin line is the
# key, everything after the first newline is the body -- so the secret is never placed in
# any command's argv and never appears in this script's output. Posts the signed body with
# curl, appends one line to <capture-dir>/webhooks.log, and prints only the HTTP code and
# response body.
set -u

D="${1:-}"
ROOT="${2:-}"
CHILD="${3:-}"

if [ -z "$D" ] || [ -z "$ROOT" ] || [ -z "$CHILD" ]; then
  echo "usage: webhook-post.sh <capture-dir> <root> <child-basename-or-root>" >&2
  exit 2
fi

case "$ROOT" in
  SSA122.*) ;;
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

if [ "$CHILD" = "$ROOT" ]; then
  SOURCE_PATH="/data/torrents/$ROOT"
else
  SOURCE_PATH="/data/torrents/$ROOT/$CHILD"
fi

umask 077
BODY_FILE="$D/.webhook-body.$$.json"
printf '{"eventType":"Download","episodeFile":{"sourcePath":"%s"},"isUpgrade":false,"instanceName":"Sonarr"}' \
  "$SOURCE_PATH" > "$BODY_FILE"
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
  --data-binary "@${BODY_FILE}" "$SSY/server/webhook/sonarr")"

TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
printf '%s %s %s\n' "$TS" "$CHILD" "$HTTP_CODE" >> "$D/webhooks.log"

echo "HTTP_CODE=$HTTP_CODE"
cat "$RESP_FILE"
echo

rm -f "$BODY_FILE" "$RESP_FILE"
