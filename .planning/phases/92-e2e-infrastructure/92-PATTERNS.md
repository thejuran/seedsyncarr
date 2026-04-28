# Phase 92: E2E Infrastructure - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 4 (3 modified, 1 verify-only)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/docker/test/e2e/run_tests.sh` | utility (test runner) | event-driven | `src/docker/test/e2e/configure/setup_seedsyncarr.sh` | role-match (same Bash polling idiom) |
| `src/docker/test/e2e/compose.yml` | config (service orchestration) | request-response | `src/docker/test/e2e/compose.yml` (remote service block) | exact (same file, same healthcheck pattern) |
| `src/docker/test/e2e/parse_status.py` | utility (JSON parser) | request-response | `src/docker/test/e2e/parse_status.py` (self — fix in place) | exact |
| `src/docker/test/e2e/configure/setup_seedsyncarr.sh` | utility (configure runner) | event-driven | `src/docker/test/e2e/run_tests.sh` | role-match (verify only, no edit) |

## Pattern Assignments

### `src/docker/test/e2e/run_tests.sh` — E2EINFRA-01 (variable init)

**Analog:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh`

The analog initializes loop control variables (`WENT_DOWN=0`, `CAME_UP=0`) before their while
loops. `run_tests.sh` must do the same for `SERVER_UP` and `SCAN_DONE`.

**Analog init-before-loop pattern** (`setup_seedsyncarr.sh` lines 35-36, 49-50):
```bash
# setup_seedsyncarr.sh — WENT_DOWN initialized before loop, CAME_UP initialized before loop
WENT_DOWN=0
while [[ ${SECONDS} -lt ${END} ]]; do
  ...
done

CAME_UP=0
END_UP=$((SECONDS+60))
while [[ ${SECONDS} -lt ${END_UP} ]]; do
  ...
done
```

**Current broken pattern in run_tests.sh** (lines 8-25):
```bash
# SERVER_UP is assigned only inside the loop body — unset if loop never executes
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

if [[ "${SERVER_UP}" != 'True' ]]; then   # SERVER_UP may be unset here
```

**Required fix — insert `SERVER_UP=""` before line 8 and `SCAN_DONE=""` before line 30:**
```bash
SERVER_UP=""
END=$((SECONDS+30))
while [ ${SECONDS} -lt ${END} ];
do
  SERVER_UP=$(...)
done
if [[ "${SERVER_UP}" != 'True' ]]; then   # always defined

SCAN_DONE=""
END=$((SECONDS+60))
while [ ${SECONDS} -lt ${END} ];
do
  SCAN_DONE=$(...)
done
if [[ "${SCAN_DONE}" != 'True' ]]; then   # always defined
```

**Do NOT change** the `sleep 2` at line 41 — it is a normal poll interval, not the race condition
referenced in E2EINFRA-03.

---

### `src/docker/test/e2e/compose.yml` — E2EINFRA-02 (myapp healthcheck + condition)

**Analog:** `src/docker/test/e2e/compose.yml` — `remote` service block (lines 17-30) already
uses the healthcheck pattern. The `myapp` service needs the same treatment.

**Existing healthcheck analog in same file** (lines 25-30):
```yaml
  remote:
    ...
    healthcheck:
      test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/1234'"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 5s
```

**Existing broken configure→myapp dependency** (lines 38-40):
```yaml
    depends_on:
      myapp:
        condition: service_started   # must become service_healthy
```

**Required additions to compose.yml:**

1. Add a `myapp:` section (Docker Compose merges it with the definition in
   `src/docker/stage/docker-image/compose.yml`):
```yaml
  myapp:
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8800/server/status"]
      interval: 5s
      timeout: 5s
      retries: 12
      start_period: 10s
```

2. Change `condition: service_started` to `condition: service_healthy` at line 40.

**Healthcheck command rationale:** `curl -sf` exits non-zero on HTTP error or connection refused,
exits 0 on HTTP 2xx — sufficient to signal application readiness. Use `retries: 12` and
`start_period: 10s` (more generous than `remote`) because arm64/QEMU Python startup is 2-4x slower.

**Merge behavior:** Docker Compose V2 deep-merges `myapp:` across `-f` files. The stage compose
defines `image` and `container_name`; the e2e compose adds `healthcheck`. Both apply.

---

### `src/docker/test/e2e/parse_status.py` — E2EINFRA-04 + E2EINFRA-05 (exceptions + `__main__`)

**Analog:** `src/docker/test/e2e/parse_status.py` (the file itself — fix in place)

**Current broken file** (lines 1-22):
```python
import sys
import json

# Parse seedsyncarr status JSON from stdin
# Usage:
#   echo '{"server":{"up":true},...}' | python3 parse_status.py server_up
#   echo '{"controller":{"latest_remote_scan_time":"..."},...}' | python3 parse_status.py remote_scan_done

check_type = sys.argv[1] if len(sys.argv) > 1 else 'server_up'

try:
    status = json.load(sys.stdin)
    if check_type == 'server_up':
        print(status['server']['up'])
    elif check_type == 'remote_scan_done':
        # Check if remote scan has completed at least once
        scan_time = status.get('controller', {}).get('latest_remote_scan_time')
        print(scan_time is not None)
    else:
        print('False')
except:          # E2EINFRA-04: too broad — catches SystemExit, KeyboardInterrupt, etc.
    print('False')
# E2EINFRA-05: no __main__ guard — module-level code runs on import
```

**Required fixed form** (complete file replacement):
```python
import sys
import json

# Parse seedsyncarr status JSON from stdin
# Usage:
#   echo '{"server":{"up":true},...}' | python3 parse_status.py server_up
#   echo '{"controller":{"latest_remote_scan_time":"..."},...}' | python3 parse_status.py remote_scan_done

if __name__ == '__main__':
    check_type = sys.argv[1] if len(sys.argv) > 1 else 'server_up'

    try:
        status = json.load(sys.stdin)
        if check_type == 'server_up':
            print(status['server']['up'])
        elif check_type == 'remote_scan_done':
            # Check if remote scan has completed at least once
            scan_time = status.get('controller', {}).get('latest_remote_scan_time')
            print(scan_time is not None)
        else:
            print('False')
    except (json.JSONDecodeError, KeyError, TypeError):
        print('False')
```

**Exception type rationale:**
- `json.JSONDecodeError` — stdin is not valid JSON (curl returned error text, empty, or partial)
- `KeyError` — JSON is valid but missing expected key (`status['server']['up']`)
- `TypeError` — `None` or unexpected type returned by `.get()` chain

**`__main__` guard:** `imports` and `constants` stay at module level; all executable logic moves
inside the `if __name__ == '__main__':` block.

---

### `src/docker/test/e2e/configure/setup_seedsyncarr.sh` — E2EINFRA-03 (verify only)

**No code change required.** The wait-for-down-then-up pattern is already implemented at lines
34-62. The planner must add a verification step only, not a code edit step.

**Already-implemented pattern** (lines 34-62):
```bash
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
```

---

## Shared Patterns

### Bash: init-before-loop
**Source:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh` lines 35, 49
**Apply to:** `run_tests.sh` (E2EINFRA-01)
```bash
VARNAME=""      # or VARNAME=0 for integer sentinel
END=$((SECONDS+N))
while [[ ${SECONDS} -lt ${END} ]]; do
  VARNAME=$(...)
  ...
done
if [[ "${VARNAME}" != 'True' ]]; then   # always safe to reference
```

### Bash: error-propagating curl calls
**Source:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh` lines 8-28
**Apply to:** Any new curl calls (none added in this phase, but follow this pattern if any are added)
```bash
curl -sSf "http://myapp:8800/..." \
  || { echo "ERROR: description" >&2; exit 1; }
```

### Docker Compose: healthcheck block
**Source:** `src/docker/test/e2e/compose.yml` lines 25-30 (`remote` service)
**Apply to:** `myapp` service addition in `compose.yml` (E2EINFRA-02)
```yaml
healthcheck:
  test: ["CMD-SHELL", "<check command>"]
  interval: 5s
  timeout: 5s
  retries: 12
  start_period: 10s
```

### Docker Compose: service_healthy dependency condition
**Source:** `src/docker/test/e2e/compose.yml` line 42 (`configure→remote`)
**Apply to:** `configure→myapp` dependency (E2EINFRA-02)
```yaml
depends_on:
  myapp:
    condition: service_healthy
```

### Python: specific exception types
**Source:** `src/docker/test/e2e/parse_status.py` (target state)
**Apply to:** `parse_status.py` (E2EINFRA-04)
```python
except (json.JSONDecodeError, KeyError, TypeError):
    print('False')
```

---

## No Analog Found

All files in this phase have direct analogs in the codebase. No file requires falling back to
RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `src/docker/` (all subdirectories)
**Files scanned:** 7 (run_tests.sh, compose.yml × 3, setup_seedsyncarr.sh × 2, parse_status.py,
  setup_default_config.sh, entrypoint.sh, angular/compose.yml)
**Pattern extraction date:** 2026-04-27
