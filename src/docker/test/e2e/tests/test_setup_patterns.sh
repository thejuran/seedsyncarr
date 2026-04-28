#!/usr/bin/env bash
# test_setup_patterns.sh
# 92-01-03 / E2EINFRA-03
# Behavioral tests: setup_seedsyncarr.sh implements the wait-for-down-then-up
# pattern after restart. Verifies correct ordering: WENT_DOWN polling loop
# comes before CAME_UP polling loop, and both are initialized before their
# respective while loops.
#
# Run: bash src/docker/test/e2e/tests/test_setup_patterns.sh
set -euo pipefail

SETUP="$(cd "$(dirname "$0")/.." && pwd)/configure/setup_seedsyncarr.sh"
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
# Test 1: WENT_DOWN=0 initializer exists
# ---------------------------------------------------------------------------
if grep -q 'WENT_DOWN=0' "$SETUP"; then
    ok "setup_seedsyncarr.sh initializes WENT_DOWN=0"
else
    fail "WENT_DOWN=0 not found in setup_seedsyncarr.sh"
fi

# ---------------------------------------------------------------------------
# Test 2: CAME_UP=0 initializer exists
# ---------------------------------------------------------------------------
if grep -q 'CAME_UP=0' "$SETUP"; then
    ok "setup_seedsyncarr.sh initializes CAME_UP=0"
else
    fail "CAME_UP=0 not found in setup_seedsyncarr.sh"
fi

# ---------------------------------------------------------------------------
# Test 3: wait-for-down loop — WENT_DOWN=0 appears BEFORE 'while' in down-loop
# The down-loop must have WENT_DOWN initialized before the while condition.
# We confirm: the WENT_DOWN=0 line is before any 'while' that follows it.
# ---------------------------------------------------------------------------
WENT_DOWN_LINE=$(grep -n 'WENT_DOWN=0' "$SETUP" | head -1 | cut -d: -f1)
# The first 'while' after WENT_DOWN=0
WHILE_AFTER_WENT_DOWN=$(awk "NR>$WENT_DOWN_LINE && /^\s*while\s*/{print NR; exit}" "$SETUP")

if [[ -n "$WENT_DOWN_LINE" && -n "$WHILE_AFTER_WENT_DOWN" && "$WENT_DOWN_LINE" -lt "$WHILE_AFTER_WENT_DOWN" ]]; then
    ok "WENT_DOWN=0 (line $WENT_DOWN_LINE) initialized before its while loop (line $WHILE_AFTER_WENT_DOWN)"
else
    fail "WENT_DOWN=0 must appear before the down-poll while loop: WENT_DOWN_LINE=${WENT_DOWN_LINE:-MISSING} WHILE=${WHILE_AFTER_WENT_DOWN:-MISSING}"
fi

# ---------------------------------------------------------------------------
# Test 4: wait-for-up loop — CAME_UP=0 appears BEFORE its while loop
# ---------------------------------------------------------------------------
CAME_UP_LINE=$(grep -n 'CAME_UP=0' "$SETUP" | head -1 | cut -d: -f1)
WHILE_AFTER_CAME_UP=$(awk "NR>$CAME_UP_LINE && /^\s*while\s*/{print NR; exit}" "$SETUP")

if [[ -n "$CAME_UP_LINE" && -n "$WHILE_AFTER_CAME_UP" && "$CAME_UP_LINE" -lt "$WHILE_AFTER_CAME_UP" ]]; then
    ok "CAME_UP=0 (line $CAME_UP_LINE) initialized before its while loop (line $WHILE_AFTER_CAME_UP)"
else
    fail "CAME_UP=0 must appear before the up-poll while loop: CAME_UP_LINE=${CAME_UP_LINE:-MISSING} WHILE=${WHILE_AFTER_CAME_UP:-MISSING}"
fi

# ---------------------------------------------------------------------------
# Test 5: WENT_DOWN polling loop comes BEFORE CAME_UP polling loop
# (down-then-up ordering: the script must first wait for the app to stop,
# then wait for it to come back, not the reverse)
# ---------------------------------------------------------------------------
if [[ -n "$WENT_DOWN_LINE" && -n "$CAME_UP_LINE" && "$WENT_DOWN_LINE" -lt "$CAME_UP_LINE" ]]; then
    ok "WENT_DOWN phase (line $WENT_DOWN_LINE) comes before CAME_UP phase (line $CAME_UP_LINE)"
else
    fail "WENT_DOWN must be checked before CAME_UP (down-then-up ordering violated): WENT_DOWN=${WENT_DOWN_LINE:-MISSING} CAME_UP=${CAME_UP_LINE:-MISSING}"
fi

# ---------------------------------------------------------------------------
# Test 6: A restart command is issued BEFORE the WENT_DOWN loop
# (the pattern requires a restart trigger before waiting for down)
# ---------------------------------------------------------------------------
RESTART_LINE=$(grep -n 'restart' "$SETUP" | grep -v '#' | head -1 | cut -d: -f1)
if [[ -n "$RESTART_LINE" && -n "$WENT_DOWN_LINE" && "$RESTART_LINE" -lt "$WENT_DOWN_LINE" ]]; then
    ok "restart command (line $RESTART_LINE) issued before WENT_DOWN poll (line $WENT_DOWN_LINE)"
else
    fail "A restart command must appear before WENT_DOWN polling loop: RESTART=${RESTART_LINE:-MISSING} WENT_DOWN=${WENT_DOWN_LINE:-MISSING}"
fi

# ---------------------------------------------------------------------------
# Test 7: The down-check polls by probing /server/status (behavioral contract)
# ---------------------------------------------------------------------------
if grep -q '/server/status' "$SETUP"; then
    ok "setup_seedsyncarr.sh polls /server/status as the liveness probe"
else
    fail "setup_seedsyncarr.sh must poll /server/status in the wait-for-down-then-up loops"
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
