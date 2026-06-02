#!/usr/bin/env bash
set -euo pipefail
# Force rebuild: 2026-01-21-v2

./wait-for-it.sh myapp:8800 -t 60 -s -- echo "Seedsync app is up (before configuring)" \
  || { echo "ERROR: myapp:8800 not available within timeout (before configuring)" >&2; exit 1; }

curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"general","key":"debug","value":"true"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set general/debug" >&2; exit 1; }
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"general","key":"verbose","value":"true"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set general/verbose" >&2; exit 1; }
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"lftp","key":"local_path","value":"/downloads"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/local_path" >&2; exit 1; }
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"lftp","key":"remote_address","value":"remote"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/remote_address" >&2; exit 1; }
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d "{\"section\":\"lftp\",\"key\":\"remote_username\",\"value\":\"${REMOTE_USERNAME:?REMOTE_USERNAME must be set}\"}" \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/remote_username" >&2; exit 1; }
# DOCKSEC-02/05: Use SSH key auth instead of password
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"lftp","key":"use_ssh_key","value":"true"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/use_ssh_key" >&2; exit 1; }
# Set remote_password to a non-dummy value so _detect_incomplete_config passes.
# The actual value is unused when use_ssh_key is true.
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"lftp","key":"remote_password","value":"unused-ssh-key-auth"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/remote_password" >&2; exit 1; }
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"lftp","key":"remote_port","value":"1234"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/remote_port" >&2; exit 1; }
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"lftp","key":"remote_path","value":"/home/remoteuser/files"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/remote_path" >&2; exit 1; }
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"autoqueue","key":"patterns_only","value":"true"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set autoqueue/patterns_only" >&2; exit 1; }
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"autoqueue","key":"enabled","value":"true"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set autoqueue/enabled" >&2; exit 1; }

curl -sSf -X POST "http://myapp:8800/server/command/restart" \
  || { echo "ERROR: failed to restart app" >&2; exit 1; }

# Wait for the app to go down before checking it comes back up
END=$((SECONDS+17))
WENT_DOWN=0
while [[ ${SECONDS} -lt ${END} ]]; do
  if ! curl -sf -o /dev/null "http://myapp:8800/server/status" 2>/dev/null; then
    WENT_DOWN=1
    break
  fi
  sleep 1
done
if [[ "${WENT_DOWN}" -eq 0 ]]; then
  echo "ERROR: app did not go down within 17s after restart" >&2
  exit 1
fi

# Wait for the app to come back up (jq check mirrors parse_status.py server_up)
CAME_UP=0
END_UP=$((SECONDS+60))
while [[ ${SECONDS} -lt ${END_UP} ]]; do
  STATUS=$(curl -sf "http://myapp:8800/server/status" 2>/dev/null) || { sleep 1; continue; }
  if echo "${STATUS}" | jq -e '.server.up == true' > /dev/null 2>&1; then
    CAME_UP=1
    break
  fi
  sleep 1
done
if [[ "${CAME_UP}" -eq 0 ]]; then
  echo "ERROR: myapp:8800 not ready within timeout (after configuring)" >&2; exit 1
fi
echo "Seedsync app is up (after configuring)"

echo
echo "Done configuring SeedSyncarr app"
