---
phase: 93-ci-docker-hardening
reviewed: 2026-04-28T12:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - .github/workflows/ci.yml
  - Makefile
  - src/docker/test/e2e/compose.yml
  - src/docker/test/e2e/configure/setup_seedsyncarr.sh
  - src/docker/test/e2e/remote/Dockerfile
  - src/docker/test/python/Dockerfile
  - src/docker/test/python/entrypoint.sh
  - src/python/tests/integration/test_controller/test_controller.py
  - src/python/tests/integration/test_lftp/test_lftp_protocol.py
  - src/python/tests/unittests/test_ssh/test_sshcp.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 93: Code Review Report

**Reviewed:** 2026-04-28T12:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the CI workflow, Makefile, Docker test infrastructure, and Python test files that comprise the CI and Docker hardening phase. The security hardening work (DOCKSEC-01 through DOCKSEC-06) is well-executed: password authentication is disabled, SSH key-based auth is used throughout, non-root users run services, and ephemeral keys are generated for E2E tests. However, there is one critical shell injection vector in the CI workflow, several warnings around residual credentials and missing error handling in shell scripts, and a few informational items.

## Critical Issues

### CR-01: GitHub Actions expression injection via unquoted step outputs

**File:** `.github/workflows/ci.yml:103-105`
**Issue:** The workflow uses `${{ steps.buildx.outputs.name }}` and `${{ steps.buildx.outputs.platforms }}` directly in `run:` blocks without quoting. While these specific values from the Buildx action are unlikely to be attacker-controlled, this pattern is a known expression injection vector in GitHub Actions. If the output ever contained shell metacharacters (e.g., from a compromised action or unexpected output), they would be interpreted by the shell. This same pattern is repeated at lines 139-141, 177-179, and 267-269.
**Fix:** Quote the expressions or use environment variables:
```yaml
- name: Show buildx builder instance name
  run: echo "${{ steps.buildx.outputs.name }}"
- name: Show buildx available platforms
  run: echo "${{ steps.buildx.outputs.platforms }}"
```
Or better yet, since these are purely informational echo statements, consider removing them entirely to reduce attack surface.

## Warnings

### WR-01: Residual password set for seedsyncarrtest user in Python test Dockerfile

**File:** `src/docker/test/python/Dockerfile:36`
**Issue:** Line 36 runs `echo "seedsyncarrtest:seedsyncarrpass" | chpasswd` to set a password, and then line 42 runs `passwd -l seedsyncarrtest` to lock it. While the lock prevents password-based login via SSH (which is also disabled in sshd_config), the password hash still exists in `/etc/shadow`. If any other authentication mechanism inside the container checks password hashes (e.g., `su`, PAM modules for local services), the known password could be exploited. The DOCKSEC-03 comment on line 41 acknowledges this, but the `chpasswd` call on line 36 is now unnecessary since SSH key-only auth is enforced.
**Fix:** Remove the `chpasswd` line entirely since password auth is disabled and the account is locked:
```dockerfile
RUN useradd --create-home -s /bin/bash seedsyncarrtest
# Skip chpasswd -- DOCKSEC-03: password auth disabled, account locked
RUN passwd -l seedsyncarrtest
```

### WR-02: Unquoted `$@` in entrypoint.sh can cause word splitting

**File:** `src/docker/test/python/entrypoint.sh:11-12`
**Issue:** Lines 11-12 use `echo $@` and `exec $@` without quoting. If the CMD arguments contain spaces or glob characters, word splitting will cause incorrect behavior. For example, a command like `pytest -k "test name with spaces"` would be split incorrectly.
**Fix:** Quote the variable expansion:
```bash
echo "$@"
exec "$@"
```

### WR-03: E2E SSH key generation silently ignores failures

**File:** `Makefile:137`
**Issue:** The command `ssh-keygen -t ed25519 -N "" -f /tmp/e2e_test_key -q 2>/dev/null || true` suppresses all errors via `2>/dev/null || true`. If key generation fails for any reason (disk full, permissions, missing ssh-keygen binary), the build continues with a missing or stale key, leading to confusing SSH authentication failures downstream that would be hard to debug.
**Fix:** Allow the keygen to fail only if the key already exists (which is the intended behavior), but report other failures:
```makefile
if [ ! -f /tmp/e2e_test_key ]; then \
    ssh-keygen -t ed25519 -N "" -f /tmp/e2e_test_key -q; \
fi
```

### WR-04: E2E remote Dockerfile build in compose.yml lacks SSH_PUBKEY build-arg

**File:** `src/docker/test/e2e/compose.yml:17-25`
**Issue:** The `remote` service definition in compose.yml specifies a build context and Dockerfile but does not pass the `SSH_PUBKEY` build argument that the Dockerfile expects (line 17 of `remote/Dockerfile`). The Makefile `run-tests-e2e` target correctly passes `--build-arg SSH_PUBKEY` when building with `docker buildx build` directly (Makefile line 143), but if someone runs `docker compose build` using only the compose.yml file, the `SSH_PUBKEY` arg will be empty, resulting in an empty `authorized_keys` file and SSH authentication failures. The compose.yml `remote` service build section should either pass the arg or document that it is only built via the Makefile.
**Fix:** Add the build arg to compose.yml or add a comment clarifying the intended build path:
```yaml
remote:
    image: seedsyncarr/test/e2e/remote
    container_name: seedsyncarr_test_e2e_remote
    # NOTE: This service is pre-built by the Makefile (run-tests-e2e) which
    # passes --build-arg SSH_PUBKEY. Do not build via docker compose directly.
```

## Info

### IN-01: E2E ephemeral SSH key is not cleaned up

**File:** `Makefile:137-138`
**Issue:** The ephemeral SSH key pair generated at `/tmp/e2e_test_key` and `/tmp/e2e_test_key.pub` is never cleaned up after the E2E test completes. The `tearDown` function (line 159) only stops compose services. While `/tmp` is typically cleaned on reboot and these are test keys with no passphrase, explicit cleanup is good hygiene, especially on CI runners that may be reused.
**Fix:** Add cleanup to the tearDown function:
```makefile
function tearDown {
    $(DOCKER_COMPOSE) \
        $${COMPOSE_FLAGS} \
        stop
    rm -f /tmp/e2e_test_key /tmp/e2e_test_key.pub
}
```

### IN-02: Duplicate call to `__wait_for_initial_model` in test

**File:** `src/python/tests/integration/test_controller/test_controller.py:1557-1561`
**Issue:** In `test_command_extract_remote_only_fails`, `self.__wait_for_initial_model()` is called twice consecutively (lines 1558 and 1561). The second call is redundant since the first already waits for the model to be populated. This appears to be a copy-paste artifact.
**Fix:** Remove the duplicate call:
```python
    def test_command_extract_remote_only_fails(self):
        self.controller = Controller(self.context, self.controller_persist, self.webhook_manager)
        self.controller.start()
        # wait for initial scan
        self.__wait_for_initial_model()

        # Ignore the initial state
```

### IN-03: Missing `set -u` (nounset) in entrypoint.sh

**File:** `src/docker/test/python/entrypoint.sh:4`
**Issue:** The script uses `set -e` but not `set -u` (nounset) or `set -o pipefail`. The setup script (`setup_seedsyncarr.sh`) correctly uses `set -euo pipefail`. For consistency across the test infrastructure, the entrypoint should also use the stricter settings.
**Fix:**
```bash
set -euo pipefail
```

---

_Reviewed: 2026-04-28T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
