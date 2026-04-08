#!/bin/bash

red=`tput setaf 1`
green=`tput setaf 2`
reset=`tput sgr0`

# Wait for server to be up
END=$((SECONDS+30))
while [ ${SECONDS} -lt ${END} ];
do
  SERVER_UP=$(
      curl -s myapp:8800/server/status | \
        python3 ./parse_status.py server_up
  )
  if [[ "${SERVER_UP}" == 'True' ]]; then
    break
  fi
  echo "E2E Test is waiting for SeedSyncarr server to come up..."
  sleep 1
done

if [[ "${SERVER_UP}" != 'True' ]]; then
  echo "${red}E2E Test failed to detect SeedSyncarr server${reset}"
  exit 1
fi

echo "${green}E2E Test detected that SeedSyncarr server is UP${reset}"

# Wait for remote scan to complete (files need to be scanned before dashboard tests can run)
END=$((SECONDS+60))
while [ ${SECONDS} -lt ${END} ];
do
  SCAN_DONE=$(
      curl -s myapp:8800/server/status | \
        python3 ./parse_status.py remote_scan_done
  )
  if [[ "${SCAN_DONE}" == 'True' ]]; then
    break
  fi
  echo "E2E Test is waiting for remote scan to complete..."
  sleep 2
done

if [[ "${SCAN_DONE}" != 'True' ]]; then
  echo "${red}E2E Test failed: remote scan did not complete${reset}"
  # Show status for debugging
  curl -s myapp:8800/server/status | python3 -m json.tool
  exit 1
fi

echo "${green}E2E Test detected that remote scan is complete${reset}"

npx playwright test
