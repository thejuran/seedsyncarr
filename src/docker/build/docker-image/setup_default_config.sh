#!/bin/bash

# exit on first error
set -e

CONFIG_DIR="/config"
SETTINGS_FILE="${CONFIG_DIR}/settings.cfg"
SCRIPT_PATH="/app/python/seedsyncarr.py"

# This script's output goes to the container log. It must never print a value
# read from settings.cfg (the file holds passwords, API keys and tokens).

if [ -f "${SETTINGS_FILE}" ]; then
    CONFIG_STATE="existing config kept"
else
    CONFIG_STATE="default config generated"
fi

# Generate default config. All app output is discarded: an error message from
# parsing the config could quote a settings value.
python ${SCRIPT_PATH} \
    -c ${CONFIG_DIR} \
    --html / \
    --scanfs / \
    --exit > /dev/null 2>&1 || true

# Replace the first-run placeholder only while it is still present, so an
# existing config is left untouched and does not trip `set -e`.
if grep -qF 'local_path = <replace me>' "${SETTINGS_FILE}" 2>/dev/null; then
    echo "Setting local_path to /downloads"
    sed -i 's/local_path = <replace me>/local_path = \/downloads\//' "${SETTINGS_FILE}"
fi

echo "Config ready at ${SETTINGS_FILE} (${CONFIG_STATE})"
