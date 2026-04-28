---
phase: 93-ci-docker-hardening
verified: 2026-04-28T00:00:00Z
status: human_needed
score: 5/5
overrides_applied: 0
human_verification:
  - test: "Run make run-tests-python locally or review CI log from a recent run"
    expected: "Python unit tests pass with the hardened container (non-root sshd via gosu sshdaemon, key-only auth, testgroup instead of root group)"
    why_human: "Container build and pytest execution requires a live Docker environment; cannot verify runtime behavior with grep/static checks"
  - test: "Run make run-tests-e2e against a staged image, or review the latest CI run on main"
    expected: "E2E tests pass end-to-end using the ephemeral ED25519 key flow (ssh-keygen in Makefile → --build-arg SSH_PUBKEY → /home/seedsync/.ssh/id_ed25519 bind-mount)"
    why_human: "Full E2E flow requires a live Docker environment, a published staging image, and active port-1234 sshd in the remote container; cannot verify with static analysis"
---

# Phase 93: CI & Docker Hardening — Verification Report

**Phase Goal:** CI workflow follows least-privilege security and Docker test containers have no hardcoded credentials
**Verified:** 2026-04-28
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                             | Status     | Evidence                                                                                                                          |
|----|---------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------------------------------------------|
| 1  | Workflow-level permissions are `contents: read` with per-job write permissions added only where needed | ✓ VERIFIED | Lines 15-16 of ci.yml: `permissions: contents: read`. Write overrides on unittests-python (packages), build-docker-image (packages), publish-docker-image (packages), publish-docker-image-dev (packages), publish-github-release (contents), publish-docs (contents). e2etests-docker-image has `packages: read` (explicit, stricter-than-default — correct). No workflow-level `packages: write`. |
| 2  | All GitHub Actions are pinned to SHA hashes with version comments                                 | ✓ VERIFIED | Zero unpinned `actions/*` refs. 11x `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1`, 3x `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0`, 1x `actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0`. Already-pinned actions (docker/setup-qemu-action, docker/setup-buildx-action, peaceiris/actions-gh-pages, pypa/gh-action-pypi-publish) unchanged. |
| 3  | `publish-docker-image` job is in the `needs` chain of `publish-github-release`                   | ✓ VERIFIED | ci.yml line 243: `needs: [ e2etests-docker-image, publish-docker-image ]`                                                         |
| 4  | Test containers use SSH key-only auth (no hardcoded passwords, `PasswordAuthentication no`)       | ✓ VERIFIED | Python Dockerfile: `PasswordAuthentication no` via `sed -i` + `passwd -l seedsyncarrtest` + no `chpasswd`. E2E remote Dockerfile: `PasswordAuthentication no` + `passwd -l remoteuser` + no `chpasswd` + no `remotepass`. Static `id_rsa.pub` deleted. No `seedsyncarrpass` anywhere in test files. |
| 5  | Test containers generate ephemeral SSH key pairs at build time and run sshd as non-root          | ✓ VERIFIED | Python container: `sshdaemon` user created, `gosu sshdaemon /usr/sbin/sshd -D &` in entrypoint.sh, `setcap cap_net_bind_service=+ep /usr/sbin/sshd`, host key ownership transferred. E2E remote: `ssh-keygen -t ed25519` in Makefile generates fresh key each build; pubkey passed via `--build-arg SSH_PUBKEY`; `USER remoteuser` before CMD; host key ownership transferred to remoteuser. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                                                      | Expected                                                        | Status     | Details                                                                                  |
|---------------------------------------------------------------|-----------------------------------------------------------------|------------|------------------------------------------------------------------------------------------|
| `.github/workflows/ci.yml`                                    | Hardened CI workflow: least-privilege permissions, SHA-pinned actions | ✓ VERIFIED | 365 lines. `contents: read` at workflow level. All `actions/*` refs use 40-char SHA with version comment. PYTHON_TEST_CACHE_REGISTRY wired via env indirection. |
| `Makefile`                                                    | Conditional registry cache for tests-python; ephemeral SSH key gen for E2E | ✓ VERIFIED | `tests-python` target uses `CACHE_FLAGS` shell-conditional; `run-tests-e2e` generates ED25519 key at `/tmp/e2e_test_key` before docker build; `--build-arg SSH_PUBKEY` passed to remote Dockerfile. |
| `src/docker/test/python/Dockerfile`                          | Non-root sshd, no password auth, dedicated group               | ✓ VERIFIED | `libcap2-bin gosu` installed; `sshdaemon` user created; `PasswordAuthentication no` via sed; `passwd -l seedsyncarrtest`; `testgroup` instead of root group; `accept-new` host key checking; `setcap` + ownership transfer. |
| `src/docker/test/python/entrypoint.sh`                       | Starts sshd via gosu as sshdaemon user                         | ✓ VERIFIED | Line 7: `gosu sshdaemon /usr/sbin/sshd -D &`; `exec "$@"` properly quoted (WR-02 fix applied). |
| `src/docker/test/e2e/remote/Dockerfile`                      | Ephemeral SSH key via ARG, no password, non-root sshd          | ✓ VERIFIED | `ARG SSH_PUBKEY` with validation guard; no `chpasswd`/`remotepass`; `PasswordAuthentication no`; `passwd -l remoteuser`; host key ownership transferred; `USER remoteuser` before CMD; `PidFile /tmp/sshd.pid`. |
| `src/docker/test/e2e/compose.yml`                            | Ephemeral key bind-mount, no REMOTE_PASSWORD                   | ✓ VERIFIED | `myapp` service: bind mount `${E2E_SSH_KEY}` → `/home/seedsync/.ssh/id_ed25519` read-only; no `REMOTE_PASSWORD` env var in configure service. |
| `src/docker/test/e2e/configure/setup_seedsyncarr.sh`         | SSH key auth instead of password                               | ✓ VERIFIED | `curl .../use_ssh_key/true` present; no `remote_password` or `REMOTE_PASSWORD` curl calls. |
| `src/python/tests/unittests/test_ssh/test_sshcp.py`          | Password tests removed, keyauth-only                           | ✓ VERIFIED | No `seedsyncarrpass`, no `_TEST_PASSWORD`, no `test_copy_error_bad_password`, no `test_shell_error_bad_password`. Comment confirms password path intentionally untested. |
| `src/python/tests/integration/test_lftp/test_lftp_protocol.py` | Password auth tests removed                                  | ✓ VERIFIED | No `seedsyncarrpass`, no `_TEST_PASSWORD`, no `self.password = _TEST_PASSWORD`, no `test_password_auth`, no `test_error_bad_password`. |
| `src/python/tests/integration/test_controller/test_controller.py` | Password auth tests removed, `use_ssh_key` preserved      | ✓ VERIFIED | No `seedsyncarrpass`, no `remote_password`; `use_ssh_key: "True"` preserved at line 330. No `test_password_auth`, no `test_bad_remote_password_raises_exception`. |

### Key Link Verification

| From                               | To                                            | Via                                            | Status     | Details                                                                                           |
|------------------------------------|-----------------------------------------------|------------------------------------------------|------------|---------------------------------------------------------------------------------------------------|
| `.github/workflows/ci.yml`         | `Makefile`                                    | `make run-tests-python PYTHON_TEST_CACHE_REGISTRY="$STAGING_REGISTRY"` | ✓ WIRED | ci.yml line 39 passes env var; Makefile `tests-python` consumes via `$(PYTHON_TEST_CACHE_REGISTRY)` shell conditional. |
| `Makefile` run-tests-e2e           | `src/docker/test/e2e/remote/Dockerfile`       | `ssh-keygen` → `--build-arg SSH_PUBKEY`        | ✓ WIRED    | Makefile lines 138-145: key generated, pubkey read, passed as `--build-arg SSH_PUBKEY="$${E2E_SSH_PUBKEY}"`. |
| `src/docker/test/e2e/compose.yml`  | `Makefile`                                    | `${E2E_SSH_KEY:?...}` bind mount               | ✓ WIRED    | compose.yml line 43 references `$E2E_SSH_KEY`; Makefile line 149 exports `E2E_SSH_KEY=$(E2E_SSH_KEY)`. |
| `src/docker/test/python/entrypoint.sh` | `src/docker/test/python/Dockerfile`       | `gosu sshdaemon` uses user created in Dockerfile | ✓ WIRED  | `sshdaemon` created in Dockerfile line 19; referenced in entrypoint.sh line 7. |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces security hardening changes to CI workflow, Dockerfiles, and shell scripts (no UI components or data-rendering code).

### Behavioral Spot-Checks

| Behavior                                    | Command                                                                                           | Result                    | Status  |
|---------------------------------------------|---------------------------------------------------------------------------------------------------|---------------------------|---------|
| `id_rsa.pub` static key deleted             | `test ! -f src/docker/test/e2e/remote/id_rsa.pub`                                                | File not found            | ✓ PASS  |
| No unpinned `actions/*` refs in ci.yml      | `grep 'uses: actions/' .github/workflows/ci.yml \| grep -v '@[a-f0-9]\{40\}'`                   | Empty output              | ✓ PASS  |
| No `seedsyncarrpass` in test files          | `grep -r "seedsyncarrpass" src/python/tests/`                                                     | No matches                | ✓ PASS  |
| No `REMOTE_PASSWORD` in compose.yml         | `grep REMOTE_PASSWORD src/docker/test/e2e/compose.yml`                                            | No matches                | ✓ PASS  |
| `publish-github-release` needs chain        | `grep -A6 'publish-github-release:' .github/workflows/ci.yml \| grep publish-docker-image`       | Match found               | ✓ PASS  |
| Container runtime verification (Python)     | Requires live Docker (`make run-tests-python`)                                                    | Cannot test statically    | ? SKIP  |
| E2E ephemeral key flow                      | Requires live Docker + staged image (`make run-tests-e2e`)                                        | Cannot test statically    | ? SKIP  |

### Requirements Coverage

| Requirement  | Source Plan | Description                                                                                    | Status      | Evidence                                                                           |
|--------------|-------------|------------------------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------|
| CISEC-01     | 93-01       | Restrict workflow-level permissions to `contents: read`, per-job write only where needed      | ✓ SATISFIED | ci.yml lines 15-16; per-job permissions on 6 write-requiring jobs                 |
| CISEC-02     | 93-01       | Pin GitHub Actions to SHA hashes with version comments                                         | ✓ SATISFIED | 15 pins total; zero unpinned `actions/*` refs                                      |
| CISEC-03     | 93-01       | Add `publish-docker-image` to `publish-github-release` needs chain                            | ✓ SATISFIED | ci.yml line 243: `needs: [ e2etests-docker-image, publish-docker-image ]`          |
| CISEC-04     | 93-01       | Registry-based Docker build cache for Python test images in CI                                 | ✓ SATISFIED | Makefile `tests-python` conditional cache flags; ci.yml passes `PYTHON_TEST_CACHE_REGISTRY` |
| DOCKSEC-01   | 93-02       | Remove test user from root group — create dedicated group                                      | ✓ SATISFIED | Python Dockerfile: `groupadd testgroup`; `usermod -a -G testgroup seedsyncarrtest`; no root group |
| DOCKSEC-02   | 93-03       | Disable PasswordAuthentication in E2E remote container                                         | ✓ SATISFIED | E2E Dockerfile: `PasswordAuthentication no` via sed; `passwd -l remoteuser`; no `chpasswd` |
| DOCKSEC-03   | 93-02       | Disable PasswordAuthentication in Python test container                                        | ✓ SATISFIED | Python Dockerfile: `PasswordAuthentication no` via sed; `passwd -l seedsyncarrtest` |
| DOCKSEC-04   | 93-02, 93-03 | Run sshd as non-root in test containers                                                       | ✓ SATISFIED | Python: `sshdaemon` + gosu + setcap; E2E remote: `USER remoteuser` + host key ownership |
| DOCKSEC-05   | 93-03       | Generate ephemeral SSH key pair at Docker build time                                           | ✓ SATISFIED | Makefile `ssh-keygen -t ed25519` + `--build-arg SSH_PUBKEY`; static `id_rsa.pub` deleted |
| DOCKSEC-06   | 93-02       | Change `StrictHostKeyChecking no` to `accept-new` in Python test container                    | ✓ SATISFIED | Python Dockerfile line 28: `StrictHostKeyChecking accept-new` via printf                |

**Orphaned requirements:** None — all 10 requirements from the traceability table map to plans 93-01, 93-02, or 93-03.

**Note:** REQUIREMENTS.md traceability table shows all 10 requirements as `Pending` (unchecked `- [ ]`) despite the implementation being complete. This is a documentation state gap — the checkboxes and traceability table status column should be updated to `Complete` / `[x]`. This does not affect code correctness.

### Anti-Patterns Found

| File                                        | Line | Pattern                    | Severity     | Impact                      |
|---------------------------------------------|------|----------------------------|--------------|-----------------------------|
| (none found in any modified file)           | —    | —                          | —            | —                           |

No TODO/FIXME/PLACEHOLDER comments found. No hardcoded credentials found. No `PasswordAuthentication yes` found in either Dockerfile.

### Human Verification Required

#### 1. Python unit tests pass with hardened container

**Test:** Run `make run-tests-python` (or review the latest CI run on main branch that follows commit 333f326/7c97fe0)
**Expected:** All Python unit tests pass. The sshd in the container starts successfully as `sshdaemon` via `gosu`, key-only SSH connections from the test suite succeed, and the removed password-auth tests no longer appear in the run.
**Why human:** Container build and pytest execution requires a live Docker environment. Static analysis confirms all hardening directives are present in the Dockerfile and the password-auth tests are absent from the test files, but cannot verify that `gosu sshdaemon /usr/sbin/sshd -D` successfully starts, binds port 22, and accepts key-auth connections at runtime.

#### 2. E2E tests pass with ephemeral SSH key flow

**Test:** Run `make run-tests-e2e STAGING_VERSION=<run_number> STAGING_REGISTRY=... SEEDSYNCARR_ARCH=amd64` (or review latest CI E2E run following commit 747a756)
**Expected:** E2E tests pass end-to-end. The Makefile generates a fresh ED25519 key pair at `/tmp/e2e_test_key`, the remote container builds with the pubkey baked in via `--build-arg SSH_PUBKEY`, the private key is mounted read-only into `myapp` at `/home/seedsync/.ssh/id_ed25519`, the configure service calls `use_ssh_key/true`, and the E2E Playwright tests complete successfully.
**Why human:** Full E2E flow requires a live Docker environment, a published staging image, and active sshd on port 1234 in the remote container. Static analysis confirms all four files are correctly wired (Makefile ssh-keygen → remote Dockerfile ARG SSH_PUBKEY → compose.yml bind mount → setup_seedsyncarr.sh use_ssh_key/true), but runtime correctness of the SSH key flow and lftp connection cannot be verified without running the stack.

### Gaps Summary

No blocking gaps identified. All five observable truths are verified by static analysis of the actual files. The two human verification items are runtime correctness checks that cannot be completed programmatically — they do not indicate missing implementation, but confirm the implementation works end-to-end in a live environment.

Minor documentation gap: REQUIREMENTS.md checkboxes for all 10 phase-93 requirements remain `- [ ]` (unchecked) despite implementation being complete. This should be updated to reflect completion but does not affect the implementation.

---

_Verified: 2026-04-28_
_Verifier: Claude (gsd-verifier)_
