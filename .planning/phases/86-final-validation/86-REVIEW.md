---
phase: 86-final-validation
reviewed: 2026-04-24T21:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - src/docker/test/e2e/configure/setup_seedsyncarr.sh
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 86: Code Review Report

**Reviewed:** 2026-04-24T21:00:00Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed `src/docker/test/e2e/configure/setup_seedsyncarr.sh`, an E2E test harness script that configures the SeedSyncarr application via its HTTP API before test runs. The script is functional but lacks defensive error handling -- if any configuration step fails silently, tests will run against a misconfigured environment, producing false failures that are difficult to diagnose. No security issues were found; the hardcoded credentials are test-only values appropriate for an E2E harness.

## Warnings

### WR-01: Missing `set -e` allows silent failures

**File:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh:1`
**Issue:** The script does not use `set -e` (or `set -euo pipefail`). If `wait-for-it.sh` fails (app never comes up) or any `curl` command fails (network error, DNS resolution failure), execution continues to the next line. This means the restart command on line 15 could fire against a half-configured app, and the final `wait-for-it.sh` could succeed even though configuration is incomplete, leading to flaky E2E tests.
**Fix:** Add `set -euo pipefail` after the shebang line:
```bash
#!/bin/bash
set -euo pipefail
# Force rebuild: 2026-01-21-v2
```

### WR-02: No HTTP status validation on configuration curl calls

**File:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh:4-13`
**Issue:** All `curl -sS` calls check for transport-level errors (stderr output via `-S`) but do not validate HTTP response status codes. If the server returns a 4xx or 5xx error, `curl` still exits with code 0, and the script treats the configuration as successful. For example, if the config API endpoint path changes, every `curl` would get a 404 but the script would proceed to restart and report success.
**Fix:** Add `--fail` (or `-f`) to each curl invocation so curl returns a non-zero exit code on HTTP errors. Combined with WR-01 (`set -e`), this would halt the script on the first failed configuration call:
```bash
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
```

## Info

### IN-01: Relative path for `wait-for-it.sh` depends on working directory

**File:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh:3,17`
**Issue:** `./wait-for-it.sh` uses a relative path, which requires the container's working directory to be the same directory containing this script. This is typically set by the Dockerfile `WORKDIR` directive, but if the entrypoint or compose configuration changes the working directory, the script will fail with a confusing "not found" error.
**Fix:** Consider using `"$(dirname "$0")/wait-for-it.sh"` for robustness, or document the `WORKDIR` dependency:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/wait-for-it.sh" myapp:8800 -t 60 -- echo "Seedsync app is up (before configuring)"
```

---

_Reviewed: 2026-04-24T21:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
