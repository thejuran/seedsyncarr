#!/usr/bin/env bash
# test_run_tests_vars.sh
# 92-01-01 / E2EINFRA-01
# Behavioral tests: SERVER_UP and SCAN_DONE are initialized to ""
# BEFORE their respective END= polling loop lines in run_tests.sh.
#
# Run: bash src/docker/test/e2e/tests/test_run_tests_vars.sh
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/run_tests.sh"
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
# Helpers
# ---------------------------------------------------------------------------

# Returns the line number of the Nth occurrence of a pattern, or 0 if not found.
line_of_nth_match() {
    local file="$1"
    local pattern="$2"
    local occurrence="${3:-1}"
    grep -n "$pattern" "$file" | awk -F: "NR==$occurrence{print \$1}"
}

# ---------------------------------------------------------------------------
# Test 1: SERVER_UP="" exists in the file
# ---------------------------------------------------------------------------
if grep -q 'SERVER_UP=""' "$SCRIPT"; then
    ok "SERVER_UP is initialized to empty string"
else
    fail "SERVER_UP initialization not found in run_tests.sh"
fi

# ---------------------------------------------------------------------------
# Test 2: SCAN_DONE="" exists in the file
# ---------------------------------------------------------------------------
if grep -q 'SCAN_DONE=""' "$SCRIPT"; then
    ok "SCAN_DONE is initialized to empty string"
else
    fail "SCAN_DONE initialization not found in run_tests.sh"
fi

# ---------------------------------------------------------------------------
# Test 3: SERVER_UP="" appears BEFORE the first END=$((SECONDS+30)) line
#
# The requirement states the variable must be initialized before the loop
# so a post-loop check on an empty-string value (not an unset variable)
# correctly triggers the failure branch.
# ---------------------------------------------------------------------------
SERVER_UP_LINE=$(grep -n 'SERVER_UP=""' "$SCRIPT" | head -1 | cut -d: -f1)
FIRST_END_LINE=$(grep -n 'END=\$((SECONDS+30))' "$SCRIPT" | head -1 | cut -d: -f1)

if [[ -n "$SERVER_UP_LINE" && -n "$FIRST_END_LINE" && "$SERVER_UP_LINE" -lt "$FIRST_END_LINE" ]]; then
    ok "SERVER_UP=\"\" (line $SERVER_UP_LINE) appears before END=\$((SECONDS+30)) (line $FIRST_END_LINE)"
else
    fail "SERVER_UP=\"\" must appear before END=\$((SECONDS+30)): SERVER_UP_LINE=${SERVER_UP_LINE:-MISSING} FIRST_END_LINE=${FIRST_END_LINE:-MISSING}"
fi

# ---------------------------------------------------------------------------
# Test 4: SCAN_DONE="" appears BEFORE the first END=$((SECONDS+60)) line
# ---------------------------------------------------------------------------
SCAN_DONE_LINE=$(grep -n 'SCAN_DONE=""' "$SCRIPT" | head -1 | cut -d: -f1)
SECOND_END_LINE=$(grep -n 'END=\$((SECONDS+60))' "$SCRIPT" | head -1 | cut -d: -f1)

if [[ -n "$SCAN_DONE_LINE" && -n "$SECOND_END_LINE" && "$SCAN_DONE_LINE" -lt "$SECOND_END_LINE" ]]; then
    ok "SCAN_DONE=\"\" (line $SCAN_DONE_LINE) appears before END=\$((SECONDS+60)) (line $SECOND_END_LINE)"
else
    fail "SCAN_DONE=\"\" must appear before END=\$((SECONDS+60)): SCAN_DONE_LINE=${SCAN_DONE_LINE:-MISSING} SECOND_END_LINE=${SECOND_END_LINE:-MISSING}"
fi

# ---------------------------------------------------------------------------
# Test 5: SERVER_UP="" is inside the server-up section (before the scan section)
# Both loops must have their own initializer; not one shared init.
# Specifically: SERVER_UP init must appear before any SCAN_DONE init.
# ---------------------------------------------------------------------------
if [[ -n "$SERVER_UP_LINE" && -n "$SCAN_DONE_LINE" && "$SERVER_UP_LINE" -lt "$SCAN_DONE_LINE" ]]; then
    ok "SERVER_UP initialized (line $SERVER_UP_LINE) before SCAN_DONE initialized (line $SCAN_DONE_LINE)"
else
    fail "SERVER_UP must be initialized before SCAN_DONE in the file"
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
