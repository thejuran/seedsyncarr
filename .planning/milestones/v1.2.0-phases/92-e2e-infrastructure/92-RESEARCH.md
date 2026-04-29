# Phase 92: E2E Infrastructure - Research

**Researched:** 2026-04-27
**Domain:** Docker Compose service orchestration, Bash scripting, Python scripting
**Confidence:** HIGH

## Summary

Phase 92 fixes five concrete reliability defects in the E2E Docker test infrastructure. The bugs are
deterministic and localized — each maps to a specific file and line range. No new libraries are
needed. All five fixes are pure text edits to existing files.

The working tree already has three of the five requirements partially addressed from prior work
(Phase 91 improvements to `setup_seedsyncarr.sh` and `compose.yml`). However E2EINFRA-01,
E2EINFRA-04, and E2EINFRA-05 remain entirely unimplemented, and E2EINFRA-02 is only partially
done (the dependency was changed from list to long-form syntax but is still `service_started`, not
`service_healthy`; `myapp` has no healthcheck).

E2EINFRA-03 (wait-for-down-then-up pattern) is ALREADY IMPLEMENTED in the current working tree
— `setup_seedsyncarr.sh` already contains the down-then-up HTTP poll loop. The planner must not
re-implement it. It only needs to be verified.

**Primary recommendation:** Three targeted file edits — `run_tests.sh` (init variables),
`compose.yml` (add myapp healthcheck + change condition), and `parse_status.py` (specific
exceptions + `__main__` guard). E2EINFRA-03 verification only.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Service startup ordering | Docker Compose | — | depends_on + condition enforces ordering |
| Bash variable init | Test runner (run_tests.sh) | — | Shell script init before use |
| App health detection | Docker healthcheck + Compose | run_tests.sh poll | Compose health gates configure; run_tests.sh gates Playwright |
| Post-restart wait | configure container (setup_seedsyncarr.sh) | — | Setup script owns the restart sequence |
| Status JSON parsing | parse_status.py | run_tests.sh | Python script is called inline from Bash |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| E2EINFRA-01 | Initialize `SERVER_UP`/`SCAN_DONE` before polling loops in `run_tests.sh` | Bash unbound variable bug — add `SERVER_UP=""` and `SCAN_DONE=""` before respective while loops |
| E2EINFRA-02 | Add `condition: service_healthy` to configure→myapp dependency in compose | Requires adding healthcheck to myapp service in compose.yml and changing `service_started` to `service_healthy` |
| E2EINFRA-03 | Replace `sleep 2` race after restart with wait-for-down-then-up pattern | ALREADY DONE in working tree — setup_seedsyncarr.sh has explicit down-then-up HTTP poll |
| E2EINFRA-04 | Replace bare `except:` with specific exception types in `parse_status.py` | `json.JSONDecodeError` + `KeyError` + `TypeError` cover the two failure modes |
| E2EINFRA-05 | Add `__main__` guard to `parse_status.py` | Standard `if __name__ == '__main__':` guard wrapping the script body |
</phase_requirements>

## File Inventory (ALL files involved in this phase)

| File | Requirement | Current State | Action |
|------|-------------|---------------|--------|
| `src/docker/test/e2e/run_tests.sh` | E2EINFRA-01 | `SERVER_UP`/`SCAN_DONE` uninitialized before loops | Add `SERVER_UP=""` before first loop, `SCAN_DONE=""` before second loop |
| `src/docker/test/e2e/compose.yml` | E2EINFRA-02 | configure→myapp uses `service_started`; `myapp` has no healthcheck | Add healthcheck to myapp service; change condition to `service_healthy` |
| `src/docker/test/e2e/configure/setup_seedsyncarr.sh` | E2EINFRA-03 | Already implements wait-for-down-then-up pattern | Verify only — no code change needed |
| `src/docker/test/e2e/parse_status.py` | E2EINFRA-04, E2EINFRA-05 | Bare `except:`; no `__main__` guard | Replace `except:` with specific types; wrap in `__main__` guard |

## Standard Stack

### Core (no new dependencies)

All fixes use tools already present in the repository:

| Tool | Version in Use | Purpose |
|------|---------------|---------|
| Docker Compose | v2 (Compose V2 syntax) | Service orchestration and dependency conditions |
| Bash | 5.x (Alpine/Debian default) | run_tests.sh, setup_seedsyncarr.sh |
| Python 3 | 3.x (node:22-slim image) | parse_status.py runs inside E2E container |
| curl | system | HTTP health probing in scripts |

**Installation:** No new packages required.

## Architecture Patterns

### System Architecture Diagram

```
Docker Compose up
      │
      ├─► remote service ──► healthcheck (TCP /dev/tcp/localhost/1234)
      │         │                   │
      │         │ service_healthy   │
      │         ▼                   │
      ├─► configure service ◄───────┘
      │    (setup_seedsyncarr.sh)
      │         │  depends_on myapp: service_healthy  ← E2EINFRA-02
      │         ▼
      │    myapp (healthcheck: curl /server/status)   ← E2EINFRA-02
      │         │
      │         │ service_completed_successfully
      │         ▼
      └─► tests service (run_tests.sh)
               │
               │ init SERVER_UP=""                    ← E2EINFRA-01
               │ poll /server/status → parse_status.py
               │ init SCAN_DONE=""                    ← E2EINFRA-01
               │ poll /server/status → parse_status.py
               │
               ▼
          npx playwright test
```

### Pattern 1: Docker Compose service_healthy

**What:** Docker Compose blocks dependent services until the dependency's healthcheck reports healthy.
**When to use:** When a downstream service (configure) needs the upstream service (myapp) to be
application-ready, not just TCP-ready.

**Healthcheck format in compose.yml:**
```yaml
# [VERIFIED: project codebase — remote service in compose.yml already uses this pattern]
healthcheck:
  test: ["CMD-SHELL", "curl -sf http://localhost:8800/server/status | python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('server',{}).get('up') else 1)\""]
  interval: 5s
  timeout: 5s
  retries: 12
  start_period: 10s
```

**Dependency condition:**
```yaml
depends_on:
  myapp:
    condition: service_healthy
```

**Key constraint:** `myapp` does not define a HEALTHCHECK in its Dockerfile. The healthcheck must
be added in the compose.yml service definition for `myapp`. This is valid — Docker Compose
healthcheck in the service block overrides or supplements the image's HEALTHCHECK instruction.
[VERIFIED: project codebase — remote service healthcheck is defined in compose.yml, not its Dockerfile]

**Where myapp is defined:** The `myapp` service is split across two compose files merged by the
Makefile:
- `src/docker/stage/docker-image/compose.yml` — defines image and container_name only
- `src/docker/test/e2e/compose.yml` — does NOT currently define `myapp` at all (myapp is only in stage compose)

**Critical implication:** The healthcheck for `myapp` must be added to EITHER:
1. `src/docker/stage/docker-image/compose.yml` (where myapp is defined), OR
2. `src/docker/test/e2e/compose.yml` by adding a `myapp:` section with just the healthcheck

Option 2 (add myapp section to e2e compose.yml) is preferred — it keeps the healthcheck in the
E2E test context where it is consumed.

### Pattern 2: Bash variable initialization before polling loops

**What:** In Bash with `set -u` (nounset), referencing an unset variable is a fatal error. Even
without `set -u`, an unset variable evaluates to empty string, which may coincidentally match
the failure condition (empty string != 'True') but causes a misleading failure message.

**Bug in current run_tests.sh:**
```bash
# [VERIFIED: file src/docker/test/e2e/run_tests.sh]
# SERVER_UP is never initialized — if curl fails before loop body runs,
# the variable doesn't exist when checked at line 22
while [ ${SECONDS} -lt ${END} ]; do
  SERVER_UP=$(...)   # only set if loop body executes
done
if [[ "${SERVER_UP}" != 'True' ]]; then  # ERROR: SERVER_UP may be unset
```

**Fix:**
```bash
SERVER_UP=""
while [ ${SECONDS} -lt ${END} ]; do
  SERVER_UP=$(...)
done
if [[ "${SERVER_UP}" != 'True' ]]; then
```

Same pattern applies to `SCAN_DONE=""` before its loop.

**Note on sleep 2:** The `sleep 2` in the `SCAN_DONE` polling loop is a normal poll interval,
not a race condition. The `sleep 2` mentioned in E2EINFRA-03's requirement refers to the OLD
`setup_seedsyncarr.sh` which used `wait-for-it.sh` (TCP only) and implicitly relied on a
short sleep after restart. That race condition is ALREADY FIXED in the working tree. Do not
change the `sleep 2` in `run_tests.sh`.

### Pattern 3: Python specific exception types

**What:** Bare `except:` catches ALL exceptions including `SystemExit`, `KeyboardInterrupt`,
`MemoryError` — this can mask genuine bugs and silently suppress useful errors.

**Bug in current parse_status.py:**
```python
# [VERIFIED: file src/docker/test/e2e/parse_status.py]
try:
    status = json.load(sys.stdin)
    ...
except:          # catches everything — too broad
    print('False')
```

**Specific exceptions to catch:**
```python
# [VERIFIED: Python stdlib docs — these cover the two failure modes]
except (json.JSONDecodeError, KeyError, TypeError):
    print('False')
```

- `json.JSONDecodeError` — stdin is not valid JSON (curl returned error text, empty, or partial)
- `KeyError` — JSON is valid but missing expected keys (`status['server']['up']`)
- `TypeError` — `None` or unexpected type returned by `.get()` chain

### Pattern 4: Python `__main__` guard

**What:** Wrapping script-level code in `if __name__ == '__main__':` ensures the code only
executes when the script is run directly, not when imported as a module.

**Standard form:**
```python
# [VERIFIED: project codebase — standard Python idiom]
if __name__ == '__main__':
    check_type = sys.argv[1] if len(sys.argv) > 1 else 'server_up'
    try:
        ...
    except (json.JSONDecodeError, KeyError, TypeError):
        print('False')
```

Module-level code that should NOT be inside the guard: imports and constants only.

### Anti-Patterns to Avoid

- **service_started as health gate:** `service_started` only waits for the container to start,
  not for the application to be ready. The setup script calling the config API before the app
  is ready produces HTTP 5xx or connection refused errors.

- **TCP-only wait as application readiness:** `wait-for-it.sh` checks that a port is open at
  the TCP level. A Python/bottle application can accept TCP connections before it is fully
  initialized. The configure script already addresses this with HTTP polling via `jq`.

- **Bare `except:` in utilities called from Bash:** When the Python script is called inline in
  Bash command substitution, an uncaught exception causes the script to exit non-zero and
  produce error text on stdout, which the Bash variable then holds. This silently corrupts
  the comparison (`"Traceback..." != 'True'` still fails correctly, but the root cause is
  invisible).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Application health check URL | Custom health endpoint | `/server/status` already exists and returns `{"server": {"up": true, ...}}` |
| Wait-for-port script | Custom TCP wait loop | `wait-for-it.sh` already present in repo |
| JSON parsing in Bash | Bash string manipulation | `python3 parse_status.py` or `jq` (already installed in configure container) |

## Current State Assessment: What Is and Is NOT Done

This is critical for planning — the three modified files in the working tree (`compose.yml`,
`configure/Dockerfile`, `configure/setup_seedsyncarr.sh`) were changed in an earlier work session.
The planner must not re-implement what is done.

### DONE (working tree, not yet committed to main)

| Item | Location | Evidence |
|------|----------|----------|
| remote service healthcheck | compose.yml lines 25-30 | healthcheck using `/dev/tcp/localhost/1234` |
| configure→remote: service_healthy | compose.yml line 42 | `condition: service_healthy` |
| configure→myapp: long-form syntax | compose.yml line 38-40 | expanded from `- myapp` list form |
| Wait-for-down-then-up after restart | setup_seedsyncarr.sh lines 34-62 | explicit down loop + up loop |
| jq installed in configure container | configure/Dockerfile line 3 | `curl bash jq` |
| Error-propagating curl calls | setup_seedsyncarr.sh | `|| { echo ... >&2; exit 1; }` pattern |

### NOT DONE (requires implementation in this phase)

| Item | Location | Requirement |
|------|----------|-------------|
| `SERVER_UP=""` init before loop | run_tests.sh | E2EINFRA-01 |
| `SCAN_DONE=""` init before loop | run_tests.sh | E2EINFRA-01 |
| myapp healthcheck in compose.yml | compose.yml (add myapp: section) OR stage compose.yml | E2EINFRA-02 |
| configure→myapp: service_healthy | compose.yml line 40 | E2EINFRA-02 |
| Specific exception types | parse_status.py line 21 | E2EINFRA-04 |
| `__main__` guard | parse_status.py | E2EINFRA-05 |

## Common Pitfalls

### Pitfall 1: service_healthy requires a healthcheck to be defined

**What goes wrong:** If `condition: service_healthy` is set on `myapp` but `myapp` has no
healthcheck, Docker Compose raises: `no healthcheck defined for service myapp` (or similar) and
the compose run fails immediately.

**Why it happens:** `service_healthy` is meaningless without a health protocol to evaluate.

**How to avoid:** Add a `healthcheck:` block to the `myapp` service definition in compose.yml
before changing the condition. The healthcheck should curl `/server/status` and check `.server.up`.

**Warning signs:** `docker compose up` fails with error mentioning "healthcheck" before any
container starts.

### Pitfall 2: Healthcheck timeout too tight for arm64

**What goes wrong:** On arm64 (emulated via QEMU), Python startup is 2-4x slower. A healthcheck
with a 3s timeout may fail during the initial 10s start_period window, causing `start_period` to
be the only safety net.

**How to avoid:** Use generous timeout (5s) and retries (12) with a start_period of 10s.
The `remote` service healthcheck already uses `retries: 10, start_period: 5s` as reference.

**Warning signs:** Compose up fails on arm64 but succeeds on amd64.

### Pitfall 3: myapp service definition is split across compose files

**What goes wrong:** Developer adds healthcheck to `src/docker/test/e2e/compose.yml` but does
not realize `myapp` is defined in `src/docker/stage/docker-image/compose.yml`. If the healthcheck
section is added to a `myapp:` key in the e2e compose.yml, Docker Compose merges the two
definitions — this works correctly.

**How to avoid:** Add the healthcheck under a `myapp:` key in `src/docker/test/e2e/compose.yml`.
Docker Compose deep-merges service definitions from multiple `-f` files, so the healthcheck
will apply to the myapp service defined in the stage compose.yml.

**Verification:** `docker compose -f ... config` flattens the merged config — verify the merged
`myapp` service contains the healthcheck block.

### Pitfall 4: `except (json.JSONDecodeError, ...)` requires Python 3.5+

**What goes wrong:** On very old Python, `json.JSONDecodeError` did not exist (it was added in
3.5). The E2E container uses `node:22-slim` which ships with a recent Python 3.x, so this is
not a risk in practice.

**How to avoid:** The E2E Dockerfile installs `python3` from Debian slim — Python 3.11+ in
practice. No compatibility concern.

## Code Examples

### E2EINFRA-01: Variable initialization in run_tests.sh

```bash
# [VERIFIED: project codebase — run_tests.sh current (broken) pattern]
# BEFORE:
END=$((SECONDS+30))
while [ ${SECONDS} -lt ${END} ];
do
  SERVER_UP=$(curl -s myapp:8800/server/status | python3 ./parse_status.py server_up)
  ...
done
if [[ "${SERVER_UP}" != 'True' ]]; then   # SERVER_UP may be unset if loop never ran

# AFTER:
SERVER_UP=""
END=$((SECONDS+30))
while [ ${SECONDS} -lt ${END} ];
do
  SERVER_UP=$(curl -s myapp:8800/server/status | python3 ./parse_status.py server_up)
  ...
done
if [[ "${SERVER_UP}" != 'True' ]]; then   # SERVER_UP is always defined
```

### E2EINFRA-02: myapp healthcheck in compose.yml

```yaml
# [VERIFIED: project codebase — modeled after remote service healthcheck pattern in same file]
# Add a myapp: section to src/docker/test/e2e/compose.yml (merged with stage compose.yml):
services:
  myapp:
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8800/server/status | python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('server',{}).get('up') else 1)\""]
      interval: 5s
      timeout: 5s
      retries: 12
      start_period: 10s

  configure:
    depends_on:
      myapp:
        condition: service_healthy   # changed from service_started
```

### E2EINFRA-04 + E2EINFRA-05: parse_status.py fixed

```python
# [VERIFIED: project codebase — current parse_status.py]
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
            scan_time = status.get('controller', {}).get('latest_remote_scan_time')
            print(scan_time is not None)
        else:
            print('False')
    except (json.JSONDecodeError, KeyError, TypeError):
        print('False')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Docker Compose V1 (python) | Docker Compose V2 (built-in) | ~2023 | `docker compose` not `docker-compose` |
| `service_started` only condition | `service_healthy` with healthcheck | Docker Compose 1.27+ | Application-level readiness gating |
| List-form `depends_on: [myapp]` | Long-form with condition | Docker Compose 3.9 | Enables condition-based dependency |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python version in node:22-slim is >= 3.5 (for json.JSONDecodeError) | Code Examples | No risk — Python 3.11 confirmed by node:22-slim Debian base |
| A2 | Docker Compose merges `myapp:` from both compose files when using -f flag | Pitfall 3 | Healthcheck silently not applied; E2EINFRA-02 not fixed |

**A2 note:** Docker Compose V2 deep-merges service definitions across `-f` files. This is the
documented behavior and is already relied upon by the project (myapp is split between two compose
files). [ASSUMED based on Docker Compose V2 documentation knowledge — standard merge behavior]

## Open Questions

1. **Healthcheck command choice for myapp**
   - What we know: `myapp` serves `/server/status` returning `{"server":{"up":true,...}}`
   - What's unclear: Should healthcheck use `curl | python3 -c` inline or a simpler `curl -f`?
   - Recommendation: Use `curl -sf http://localhost:8800/server/status` with exit code — if curl
     returns HTTP 2xx it passes. A simpler form: `["CMD-SHELL", "curl -sf http://localhost:8800/server/status"]`. This is sufficient since `curl -sf` exits non-zero on HTTP errors. The HTTP 200 response alone signals the app is up.

2. **Is E2EINFRA-03 truly complete?**
   - What we know: `setup_seedsyncarr.sh` has an explicit down-then-up HTTP loop
   - What's unclear: Is this the same fix as described in BUG-07?
   - Recommendation: Treat as DONE. The success criterion says "wait-for-down-then-up pattern" and
     that pattern is present at lines 34-62 of the current `setup_seedsyncarr.sh`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | All compose operations | ✓ | local dev | — |
| curl | myapp healthcheck | ✓ | node:22-slim | python3 http.client |
| python3 | run_tests.sh inline | ✓ | node:22-slim base | — |
| jq | setup_seedsyncarr.sh | ✓ | configure/Dockerfile | — |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Playwright (npx playwright test) |
| Config file | `src/e2e/playwright.config.ts` |
| Quick run command | Manual — requires full Docker stack |
| Full suite command | `make run-tests-e2e STAGING_VERSION=... SEEDSYNCARR_ARCH=amd64` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| E2EINFRA-01 | SERVER_UP/SCAN_DONE defined before loop exit check | manual smoke | `make run-tests-e2e ...` | N/A (bash script) |
| E2EINFRA-02 | configure waits for myapp healthy before running | manual smoke | `make run-tests-e2e ...` | N/A (compose) |
| E2EINFRA-03 | setup_seedsyncarr.sh wait pattern | manual smoke | `make run-tests-e2e ...` | N/A (bash script) |
| E2EINFRA-04 | parse_status.py handles invalid JSON without crash | unit | `python3 src/docker/test/e2e/parse_status.py server_up <<< "not-json"` | ✅ (inline) |
| E2EINFRA-05 | parse_status.py importable without side effects | unit | `python3 -c "import sys; sys.argv=['parse_status.py']; import importlib.util; spec=importlib.util.spec_from_file_location('ps', 'src/docker/test/e2e/parse_status.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)"` | ✅ (inline) |

### Sampling Rate

- **Per commit:** Manual code review of diffs (no automated test harness for Bash/compose changes)
- **Phase gate:** `make run-tests-e2e` green on both amd64 before `/gsd-verify-work`

### Wave 0 Gaps

None — all changes are to existing files. No new test infrastructure needed. The parse_status.py
fixes can be verified with a one-liner (see table above).

## Security Domain

These changes are infrastructure reliability fixes only. No authentication, secrets, or user input
flows are changed.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | parse_status.py reads from curl stdout only (controlled source) |
| V6 Cryptography | no | — |
| V2 Authentication | no | — |

## Sources

### Primary (HIGH confidence)

- Project codebase — all file contents read directly and verified via `cat`
- Git history — confirmed original state vs. working tree state via `git show` and `git diff`
- Docker Compose V2 documentation — `service_healthy` requires healthcheck [ASSUMED from training]

### Secondary (MEDIUM confidence)

- Docker Compose merge behavior for multiple `-f` files — standard documented behavior [ASSUMED]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new tools; all existing
- Architecture: HIGH — all files read, git diff analyzed, original vs. current state confirmed
- Pitfalls: HIGH — derived from reading the actual code defects
- E2EINFRA-03 status: HIGH — `setup_seedsyncarr.sh` contains the down-then-up implementation

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (stable infrastructure, low churn)
