---
phase: 93-ci-docker-hardening
fixed_at: 2026-04-28T15:04:31Z
review_path: .planning/phases/93-ci-docker-hardening/93-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 93: Code Review Fix Report

**Fixed at:** 2026-04-28T15:04:31Z
**Source review:** .planning/phases/93-ci-docker-hardening/93-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: GitHub Actions expression injection via unquoted step outputs

**Files modified:** `.github/workflows/ci.yml`
**Commit:** 3aeae1a
**Applied fix:** Quoted all 8 unquoted `${{ steps.buildx.outputs.* }}` expressions in `run: echo` statements across 4 jobs (build-docker-image, e2etests-docker-image, publish-docker-image, publish-docker-image-dev) to prevent shell metacharacter injection.

### WR-01: Residual password set for seedsyncarrtest user in Python test Dockerfile

**Files modified:** `src/docker/test/python/Dockerfile`
**Commit:** 5063c62
**Applied fix:** Removed the `echo "seedsyncarrtest:seedsyncarrpass" | chpasswd` call from the useradd RUN instruction. Password auth is disabled in sshd_config and the account is locked via `passwd -l`, so setting a password hash was unnecessary attack surface. Added a DOCKSEC-03 comment explaining the rationale.

### WR-02: Unquoted `$@` in entrypoint.sh can cause word splitting

**Files modified:** `src/docker/test/python/entrypoint.sh`
**Commit:** 8a38e1b
**Applied fix:** Quoted the `$@` expansion in `exec $@` to `exec "$@"` to prevent word splitting when CMD arguments contain spaces or glob characters. The `echo "$@"` on the preceding line was already correctly quoted.

### WR-03: E2E SSH key generation silently ignores failures

**Files modified:** `Makefile`
**Commit:** e06699b
**Applied fix:** Replaced `ssh-keygen ... 2>/dev/null || true` with a conditional that only generates the key if it does not already exist (`if [ ! -f /tmp/e2e_test_key ]`). Genuine failures (disk full, missing binary) now propagate instead of being silently swallowed.

### WR-04: E2E remote Dockerfile build in compose.yml lacks SSH_PUBKEY build-arg

**Files modified:** `src/docker/test/e2e/compose.yml`
**Commit:** db1d9d3
**Applied fix:** Added a NOTE comment to the remote service definition clarifying that this service is pre-built by the Makefile (`run-tests-e2e`) which passes `--build-arg SSH_PUBKEY`, and should not be built via `docker compose` directly.

---

_Fixed: 2026-04-28T15:04:31Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
