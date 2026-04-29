---
phase: 92-e2e-infrastructure
reviewed: 2026-04-27T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/docker/test/e2e/run_tests.sh
  - src/docker/test/e2e/compose.yml
  - src/docker/test/e2e/parse_status.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 92: Code Review Report

**Reviewed:** 2026-04-27
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the three E2E Docker infrastructure files introduced or modified in phase 92. All three files represent meaningful improvements over their prior state: `parse_status.py` now has a `__main__` guard and a correctly-scoped exception tuple; `compose.yml` now adds a `myapp` healthcheck and upgrades the `configure` dependency condition to `service_healthy`; `run_tests.sh` correctly initializes sentinel variables before their polling loops.

No critical issues were found. Two warnings cover error-handling gaps in `run_tests.sh` that could make CI failures opaque: `curl -s` silently discards HTTP errors, and the script has no `set -euo pipefail` guard. Three info items cover minor correctness subtleties and style consistency.

---

## Warnings

### WR-01: `curl -s` silently discards HTTP errors in run_tests.sh

**File:** `src/docker/test/e2e/run_tests.sh:13` and `:36`

**Issue:** Both polling curl calls use `-s` (silent) without `-f` (fail on HTTP error). If `myapp` returns an HTTP 500 or any non-2xx status, curl exits 0 and emits the error body to stdout. `parse_status.py` then receives that error body, fails JSON decoding, and prints `False` — which causes the loop to keep waiting until timeout rather than surfacing the root cause. The 30-second and 60-second timeouts will fully exhaust before the failure is reported.

The configure analog (`setup_seedsyncarr.sh`) uses `-sSf` throughout, which exits non-zero on HTTP error. The run_tests.sh polling loop is intentionally tolerant (curl failure is expected while the server is starting), but the diagnostic output at line 49 (`python3 -m json.tool`) already handles the case where status is malformed — so `-f` is appropriate here too since it would still result in `False` from the `except` block.

**Fix:**
```bash
# Line 13 — change:
SERVER_UP=$(
    curl -s myapp:8800/server/status | \
      python3 ./parse_status.py server_up
)

# to:
SERVER_UP=$(
    curl -sf myapp:8800/server/status 2>/dev/null | \
      python3 ./parse_status.py server_up
)

# Line 36 — same change for SCAN_DONE poll:
SCAN_DONE=$(
    curl -sf myapp:8800/server/status 2>/dev/null | \
      python3 ./parse_status.py remote_scan_done
)
```

Adding `-f` means curl exits non-zero on HTTP error and sends nothing to stdout; `parse_status.py` receives empty stdin, triggers `json.JSONDecodeError`, and prints `False` — the loop continues as before, but without silently ingesting a misleading error body. The `2>/dev/null` suppresses curl's own stderr error messages during the startup polling window, which is the intent of the original `-s`.

---

### WR-02: Missing `set -euo pipefail` in run_tests.sh

**File:** `src/docker/test/e2e/run_tests.sh:1`

**Issue:** `run_tests.sh` uses `#!/bin/bash` without `set -euo pipefail`. The configure analog (`setup_seedsyncarr.sh` line 2) includes `set -euo pipefail` as its first executable line. Without these flags:

- `-e`: an unexpected command failure (e.g., `tput` not available in the container, `python3` not on PATH) will not abort the script — execution silently continues with an empty variable.
- `-u`: referencing an unset variable (e.g., if `SERVER_UP` or `SCAN_DONE` were accidentally removed from initialization) would produce an empty string instead of an error.
- `-o pipefail`: in the pipeline `curl ... | python3 ...`, if `curl` exits non-zero the pipeline still exits 0 because `python3` succeeds. With `pipefail`, the pipeline's exit code reflects the first non-zero exit.

`npx playwright test` at line 55 is the last command, so its exit code does propagate correctly — this is not affected. The risk is in earlier setup commands.

**Fix:**
```bash
#!/bin/bash
set -euo pipefail

red=$(tput setaf 1)
green=$(tput setaf 2)
reset=$(tput sgr0)
```

Note: switching to `$(...)` for `tput` (already done for all other command substitutions in the file) also eliminates the archaic backtick syntax on lines 3-5 as part of this change.

---

## Info

### IN-01: Backtick command substitution for tput (archaic syntax)

**File:** `src/docker/test/e2e/run_tests.sh:3-5`

**Issue:** Lines 3-5 use backtick command substitution:
```bash
red=`tput setaf 1`
green=`tput setaf 2`
reset=`tput sgr0`
```
All other command substitutions in the file use `$(...)`. Backtick syntax is POSIX-compatible but does not nest and is considered obsolete in Bash. Inconsistent with the rest of the file.

**Fix:** Use `$(...)` consistently, as is done for all other substitutions in this file:
```bash
red=$(tput setaf 1)
green=$(tput setaf 2)
reset=$(tput sgr0)
```

---

### IN-02: `parse_status.py` prints raw Python bool for `server_up`

**File:** `src/docker/test/e2e/parse_status.py:15`

**Issue:** For the `server_up` check, the code does:
```python
print(status['server']['up'])
```
If the JSON field is a Python boolean `True`, this prints `True` (capital T), which matches the shell check `== 'True'` in `run_tests.sh`. However, if the API ever returns the string `"true"` (lowercase, which is valid JSON), `print("true")` would output `true` (lowercase), and the shell check would fail — causing a spurious timeout. The `remote_scan_done` branch explicitly constructs a Python bool with `is not None`, making it immune to this. The `server_up` branch should do the same.

**Fix:**
```python
if check_type == 'server_up':
    print(bool(status['server']['up']))
```
`bool()` normalizes any truthy value to Python `True` so `print()` always outputs `True` when the server is up.

---

### IN-03: No `restart` policy on test services in compose.yml

**File:** `src/docker/test/e2e/compose.yml:1`

**Issue:** None of the services (`tests`, `remote`, `configure`) explicitly set `restart: no`. Docker Compose's default is no restart, so behavior is correct, but making it explicit documents the intent (single-run test containers should not auto-restart on failure). This is a convention issue, not a correctness bug.

**Fix:** Add to each test service:
```yaml
  tests:
    restart: no
    ...
  remote:
    restart: no
    ...
  configure:
    restart: no
    ...
```

---

_Reviewed: 2026-04-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
