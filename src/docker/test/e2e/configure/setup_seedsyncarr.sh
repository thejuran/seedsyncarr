#!/bin/bash
set -euo pipefail
# Force rebuild: 2026-01-21-v2
./wait-for-it.sh myapp:8800 -t 60 -- echo "Seedsync app is up (before configuring)"
curl -sSf "http://myapp:8800/server/config/set/general/debug/true"; echo
curl -sSf "http://myapp:8800/server/config/set/general/verbose/true"; echo
curl -sSf "http://myapp:8800/server/config/set/lftp/local_path/%252Fdownloads"; echo
curl -sSf "http://myapp:8800/server/config/set/lftp/remote_address/remote"; echo
curl -sSf "http://myapp:8800/server/config/set/lftp/remote_username/remoteuser"; echo
curl -sSf "http://myapp:8800/server/config/set/lftp/remote_password/remotepass"; echo
curl -sSf "http://myapp:8800/server/config/set/lftp/remote_port/1234"; echo
curl -sSf "http://myapp:8800/server/config/set/lftp/remote_path/%252Fhome%252Fremoteuser%252Ffiles"; echo
curl -sSf "http://myapp:8800/server/config/set/autoqueue/patterns_only/true"; echo
curl -sSf "http://myapp:8800/server/config/set/autoqueue/enabled/true"; echo

curl -sSf -X POST "http://myapp:8800/server/command/restart"; echo

./wait-for-it.sh myapp:8800 -t 60 -- echo "Seedsync app is up (after configuring)"

echo
echo "Done configuring SeedSyncarr app"

