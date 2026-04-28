#!/usr/bin/env bash
# test_compose_schema.sh
# 92-01-02 / E2EINFRA-02
# Behavioral tests: compose.yml has myapp healthcheck block and
# configure service uses condition: service_healthy (not service_started).
#
# Run: bash src/docker/test/e2e/tests/test_compose_schema.sh
set -euo pipefail

COMPOSE="$(cd "$(dirname "$0")/.." && pwd)/compose.yml"
PASS=0
FAIL=0
ERRORS=()

ok() {
    echo "PASS: $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "FAIL: $1"
    ERRORS+=("$1")
    FAIL=$((FAIL + 1))
}

# ---------------------------------------------------------------------------
# Helper: extract the block belonging to the FIRST top-level service key named
# $1 (e.g. "myapp"). Returns lines from the key until the next top-level
# service key (2-space-indented word followed by colon).
# ---------------------------------------------------------------------------
extract_service_block() {
    local service="$1"
    # Skip the header line itself; collect lines until the NEXT top-level service
    awk "
        /^  ${service}:/ { in_block=1; next }
        in_block && /^  [a-zA-Z]/ { exit }
        in_block { print }
    " "$COMPOSE"
}

# ---------------------------------------------------------------------------
# Test 1: compose.yml has a myapp: service section
# ---------------------------------------------------------------------------
MYAPP_LINE=$(grep -n '^\s\{2\}myapp:' "$COMPOSE" | head -1 | cut -d: -f1)
if [[ -n "$MYAPP_LINE" ]]; then
    ok "compose.yml has a 'myapp:' service section (line $MYAPP_LINE)"
else
    fail "compose.yml has no top-level 'myapp:' service section"
fi

# ---------------------------------------------------------------------------
# Test 2: myapp service block contains a healthcheck: stanza
# ---------------------------------------------------------------------------
MYAPP_BLOCK=$(extract_service_block "myapp")
if echo "$MYAPP_BLOCK" | grep -q 'healthcheck:'; then
    ok "myapp service block contains 'healthcheck:'"
else
    fail "myapp service block does not contain 'healthcheck:'"
fi

# ---------------------------------------------------------------------------
# Test 3: myapp healthcheck uses curl -sf against /server/status
# ---------------------------------------------------------------------------
if echo "$MYAPP_BLOCK" | grep -q 'curl -sf http://localhost:8800/server/status'; then
    ok "myapp healthcheck uses 'curl -sf http://localhost:8800/server/status'"
else
    fail "myapp healthcheck must use 'curl -sf http://localhost:8800/server/status'"
fi

# ---------------------------------------------------------------------------
# Test 4: myapp healthcheck has retries: 12
# ---------------------------------------------------------------------------
if echo "$MYAPP_BLOCK" | grep -q 'retries: 12'; then
    ok "myapp healthcheck has retries: 12"
else
    fail "myapp healthcheck must have 'retries: 12' (generous for arm64/QEMU)"
fi

# ---------------------------------------------------------------------------
# Test 5: myapp healthcheck has start_period: 10s
# ---------------------------------------------------------------------------
if echo "$MYAPP_BLOCK" | grep -q 'start_period: 10s'; then
    ok "myapp healthcheck has start_period: 10s"
else
    fail "myapp healthcheck must have 'start_period: 10s'"
fi

# ---------------------------------------------------------------------------
# Test 6: configure service depends_on myapp uses condition: service_healthy
# (not service_started)
# ---------------------------------------------------------------------------
CONFIGURE_BLOCK=$(extract_service_block "configure")
if echo "$CONFIGURE_BLOCK" | grep -q 'condition: service_healthy'; then
    ok "configure service depends_on uses 'condition: service_healthy'"
else
    fail "configure service must use 'condition: service_healthy' for myapp dependency"
fi

# ---------------------------------------------------------------------------
# Test 7: compose.yml does NOT contain service_started anywhere
# (previous incorrect condition must be fully removed)
# ---------------------------------------------------------------------------
if grep -q 'service_started' "$COMPOSE"; then
    fail "compose.yml still contains 'service_started' — must be fully removed"
else
    ok "compose.yml contains no 'service_started' references"
fi

# ---------------------------------------------------------------------------
# Test 8: myapp healthcheck block appears BEFORE configure service block
# (ordering: healthcheck must be defined before configure references it)
# ---------------------------------------------------------------------------
HC_LINE=$(grep -n 'curl -sf http://localhost:8800/server/status' "$COMPOSE" | head -1 | cut -d: -f1)
CONFIGURE_SVC_LINE=$(grep -n '^\s\{2\}configure:' "$COMPOSE" | head -1 | cut -d: -f1)

if [[ -n "$HC_LINE" && -n "$CONFIGURE_SVC_LINE" && "$HC_LINE" -lt "$CONFIGURE_SVC_LINE" ]]; then
    ok "myapp healthcheck (line $HC_LINE) defined before configure service (line $CONFIGURE_SVC_LINE)"
else
    fail "myapp healthcheck must appear before configure service in compose.yml: HC_LINE=${HC_LINE:-MISSING} CONFIGURE_SVC_LINE=${CONFIGURE_SVC_LINE:-MISSING}"
fi

# ---------------------------------------------------------------------------
# Test 9: remote service healthcheck is still intact (not accidentally removed)
# ---------------------------------------------------------------------------
REMOTE_BLOCK=$(extract_service_block "remote")
if echo "$REMOTE_BLOCK" | grep -q '/dev/tcp/localhost/1234'; then
    ok "remote service healthcheck (/dev/tcp/localhost/1234) is intact"
else
    fail "remote service healthcheck was accidentally removed from compose.yml"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "Results: $PASS passed, $FAIL failed"

if [[ $FAIL -gt 0 ]]; then
    echo "FAILED tests:"
    for e in "${ERRORS[@]}"; do
        echo "  - $e"
    done
    exit 1
fi

echo "ALL TESTS PASSED"
