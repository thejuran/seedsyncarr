# Phase 93: CI & Docker Hardening - Research

**Researched:** 2026-04-27
**Domain:** GitHub Actions security hardening, Docker SSH container hardening
**Confidence:** HIGH

## Summary

This phase addresses ten security requirements across two domains: GitHub Actions CI
workflow (CISEC-01 through CISEC-04) and Docker test container SSH hardening
(DOCKSEC-01 through DOCKSEC-06). All requirements were verified by direct inspection
of `.github/workflows/ci.yml` and the test Dockerfiles — no guesswork needed.

The CI changes are low-risk and mechanical: restrict workflow-level permissions to
`contents: read`, add per-job write grants, pin three unpinned Actions to SHA hashes,
chain `publish-docker-image` into `publish-github-release`'s needs, and add
registry-based build cache to the `unittests-python` CI job.

The Docker changes require more care. The python test container has integration tests
that verify password-based SSH authentication (`test_password_auth`,
`test_copy_error_bad_password`, etc.). Disabling `PasswordAuthentication` in that
container (DOCKSEC-03) makes those tests fail with different errors. The plan must
include updating or removing those password-auth-specific tests as a prerequisite to
the Dockerfile change. The e2e remote container currently uses a static committed
public key (`src/docker/test/e2e/remote/id_rsa.pub`) and password auth via a
hardcoded credential; DOCKSEC-05 + DOCKSEC-02 together require switching to an
ephemeral SSH key pair and SSH-key-only auth for that container as well.

**Primary recommendation:** Tackle CI changes in one wave (pure YAML edits), Docker
hardening in a second wave (Dockerfile + test updates), and treat the password-auth
test cleanup as a required sub-task of DOCKSEC-03, not an afterthought.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CI permissions | CI/CD (GitHub Actions) | — | Workflow YAML is the control plane |
| SHA pinning | CI/CD (GitHub Actions) | — | Immutability is a YAML property |
| Job ordering (needs chain) | CI/CD (GitHub Actions) | — | Dependency graph declared in YAML |
| Docker build cache | CI/CD + Docker layer | — | Makefile passes flags; CI passes env |
| SSH container security | Docker build layer | Test Python code | Dockerfile controls sshd; tests use the container |
| Ephemeral SSH key pair | Docker build layer | Makefile (e2e) | Key generation happens at `docker build` time |
| Password auth tests | Test code | Docker build layer | Tests must match container auth config |

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| GitHub Actions YAML | — | CI workflow definition | Already in use |
| openssh-server | Debian bookworm default (~9.2) | sshd in test containers | Already in use |
| libcap2-bin | Debian bookworm | `setcap` for non-root port binding | Standard Debian capability tool |
| Docker Buildx | v3.12.0 (SHA: `8d2750c6...`) | Multi-arch builds + registry cache | Already in use |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `ssh-keygen` | — | Ephemeral key pair generation | Inside Dockerfile RUN steps |
| `passwd -l` | — | Lock a user's password (prevents password login) | DOCKSEC-01/02/03 |
| `setcap cap_net_bind_service=+ep` | — | Allow non-root process to bind port 22 | DOCKSEC-04 python container only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `setcap` for port 22 | Change python container port to 2222 | Port change requires updating 4+ test files; `setcap` is safer scope |
| `setcap` for port 22 | `CAP_NET_BIND_SERVICE` in compose `cap_add` | `setcap` on binary is container-native; compose capability is runtime-only |
| Inline key generation | Pre-generated key pair in Makefile before build | Makefile approach adds Makefile complexity; Dockerfile keygen is self-contained |

## Architecture Patterns

### System Architecture Diagram

```
GitHub Actions Workflow
│
├── [workflow-level] permissions: contents: read   ← CISEC-01
│
├── unittests-python ──────────────────────────────── CISEC-04
│   permissions: packages: write                   (add GHCR login + cache)
│   → make run-tests-python (with cache params)
│
├── unittests-angular / lint-* ── no extra perms needed
│
├── build-docker-image ── permissions: packages: write
│   → pushes staging image + cache to GHCR
│
├── e2etests-docker-image ── permissions: packages: read
│   → pulls staging image from GHCR
│
├── publish-docker-image ── permissions: packages: write   ← CISEC-03: add to needs
│   needs: [e2etests-docker-image]
│   → pushes release image
│
├── publish-github-release ── permissions: contents: write  ← CISEC-03 key change
│   needs: [e2etests-docker-image, publish-docker-image]   ← add publish-docker-image
│
├── publish-pypi ── permissions: id-token: write
│
├── publish-docker-image-dev ── permissions: packages: write
│
└── publish-docs ── permissions: contents: write
    (peaceiris/actions-gh-pages pushes to gh-pages branch)
```

```
Docker Test Containers
│
├── src/docker/test/python/Dockerfile
│   ├── Creates seedsyncarrtest user                        ← DOCKSEC-01: remove from root group
│   ├── PasswordAuthentication yes                          ← DOCKSEC-03: change to no + passwd -l
│   ├── ssh-keygen at build time (already done) ✓           ← DOCKSEC-05: already compliant
│   ├── sshd runs as root (entrypoint.sh)                   ← DOCKSEC-04: run as dedicated user
│   └── StrictHostKeyChecking no                            ← DOCKSEC-06: change to accept-new
│
└── src/docker/test/e2e/remote/Dockerfile
    ├── Uses STATIC id_rsa.pub committed to repo             ← DOCKSEC-05: generate at build time
    ├── remoteuser:remotepass (password in use for e2e)      ← DOCKSEC-02: disable password auth
    ├── sshd runs as root, port 1234                         ← DOCKSEC-04: run as remoteuser
    └── No StrictHostKeyChecking config in this container    (not a client; no change needed)
```

### Recommended Project Structure
No new directories needed. Changes are all edits to existing files:

```
.github/workflows/
└── ci.yml                       # permissions + SHA pins + needs chain + cache

src/docker/test/
├── python/
│   ├── Dockerfile               # DOCKSEC-01/03/04/06
│   └── entrypoint.sh            # DOCKSEC-04: start sshd as dedicated user
└── e2e/remote/
    └── Dockerfile               # DOCKSEC-02/04/05

src/python/tests/
├── unittests/test_ssh/
│   └── test_sshcp.py            # Remove password variant from _PARAMS or adapt
├── integration/test_lftp/
│   └── test_lftp_protocol.py    # Update/remove test_password_auth + test_error_bad_password
└── integration/test_controller/
    └── test_controller.py       # Update/remove test_password_auth

Makefile                         # CISEC-04: pass cache flags for python test build
```

### Pattern 1: Least-Privilege Workflow Permissions (CISEC-01)

**What:** Set `contents: read` at workflow level; add per-job overrides only for jobs that actually write.

**When to use:** All GitHub Actions workflows with a mix of read-only and write jobs.

```yaml
# Source: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token
permissions:
  contents: read      # workflow-level default

jobs:
  publish-docker-image:
    permissions:
      packages: write  # job-level override — only this job needs it
    ...

  publish-github-release:
    permissions:
      contents: write  # create GitHub Release
    ...

  publish-docs:
    permissions:
      contents: write  # peaceiris/actions-gh-pages pushes to gh-pages branch
    ...

  publish-pypi:
    permissions:
      id-token: write  # OIDC for PyPI
    ...

  unittests-python:
    permissions:
      packages: write  # push registry cache to GHCR (CISEC-04)
    ...
```

**Note:** `packages: read` is NOT needed for e2etests-docker-image because the
staging GHCR registry (`ghcr.io/thejuran/seedsyncarr`) is public (the CI currently
logs in without credentials verification). Verify before final plan — if the repo
package is private, `packages: read` must be added to e2etests-docker-image.
[ASSUMED — confirm GHCR package visibility]

### Pattern 2: SHA Pinning with Version Comments (CISEC-02)

**What:** Replace mutable tag references (e.g., `@v4`) with full 40-char SHA plus
a comment showing the human-readable version.

**When to use:** Every `uses:` line in every GitHub Actions workflow.

```yaml
# Source: https://docs.github.com/en/actions/reference/security/secure-use
# Before:
uses: actions/checkout@v4

# After:
uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
```

**Actions requiring SHA pinning in this project:**
| Action | Current | SHA (latest v4/v5) | Version |
|--------|---------|-------------------|---------|
| `actions/checkout` | `@v4` | `34e114876b0b11c390a56381ad16ebd13914f8d5` | v4.3.1 |
| `actions/setup-python` | `@v5` | `a26af69be951a213d495a4c3e4e4022e16d87065` | v5.6.0 |
| `actions/setup-node` | `@v4` | `49933ea5288caeca8642d1e84afbd3f7d6820020` | v4.4.0 |

**Already pinned (verified):**
| Action | SHA | Verified Version |
|--------|-----|-----------------|
| `docker/setup-qemu-action` | `c7c53464...` | v3.7.0 (latest v3) |
| `docker/setup-buildx-action` | `8d2750c6...` | v3.12.0 (latest v3) |
| `peaceiris/actions-gh-pages` | `4f9cc660...` | v4.0.0 (latest v4) |
| `pypa/gh-action-pypi-publish` | `cef22109...` | some v1.x pre-v1.14.0 [ASSUMED] |

`actions/checkout` appears 9 times in ci.yml — all must be updated.
`actions/setup-python` appears 3 times.
`actions/setup-node` appears 1 time.

[VERIFIED: GitHub API — SHA values confirmed against tag refs as of 2026-04-27]

### Pattern 3: Registry-Based Docker Build Cache (CISEC-04)

**What:** Pass `--cache-from` and `--cache-to` to the python test image build.

**When to use:** Any `docker build` in CI where the same base layers repeat.

```bash
# Source: https://docs.docker.com/build/ci/github-actions/cache/
docker build \
  --cache-from type=registry,ref=ghcr.io/${GITHUB_REPOSITORY,,}:cache-python-test \
  --cache-to   type=registry,ref=ghcr.io/${GITHUB_REPOSITORY,,}:cache-python-test,mode=max \
  -f src/docker/build/docker-image/Dockerfile \
  --target seedsyncarr_run_python_devenv \
  --tag seedsyncarr/run/python/devenv \
  .
```

Implementation approach: add a `PYTHON_TEST_CACHE_REGISTRY` variable to `Makefile`
`tests-python` target. When this variable is non-empty, append cache flags.
In the CI `unittests-python` job:
1. Add GHCR login step (same pattern as build-docker-image job)
2. Add `packages: write` permission (needed to push the cache tag)
3. Set `staging_registry` env var
4. Call `make run-tests-python PYTHON_TEST_CACHE_REGISTRY=${{ env.staging_registry }}`

### Pattern 4: Non-Root sshd in Python Test Container (DOCKSEC-04)

**What:** Run sshd as a dedicated non-root user in the python test container using
`setcap` to allow binding port 22 without root privilege.

**Why `setcap`:** Tests hardcode port 22 in 4+ files. Changing the port requires
updating `test_lftp_protocol.py`, `test_lftp.py`, `test_controller.py`, and
`test_sshcp.py` — exceeds phase scope. `setcap` keeps port 22, avoids test changes.

```dockerfile
# Source: https://man7.org/linux/man-pages/man8/setcap.8.html
# Install libcap2-bin for setcap
RUN apt-get install -y libcap2-bin

# Create dedicated sshd runner user
RUN useradd -r -s /usr/sbin/nologin -d /nonexistent sshdaemon

# Allow sshdaemon to bind privileged ports
RUN setcap cap_net_bind_service=+ep /usr/sbin/sshd

# Transfer ownership of sshd runtime dirs and host keys
RUN chown -R sshdaemon /var/run/sshd /etc/ssh/ssh_host_* \
    && chmod 700 /etc/ssh/ssh_host_*
```

Then in `entrypoint.sh`, replace `/usr/sbin/sshd -D &` with:
```bash
su-exec sshdaemon /usr/sbin/sshd -D &
```
(Or use `gosu` if `su-exec` is not available. Install via `apt-get install -y gosu`.)

### Pattern 5: Non-Root sshd in E2E Remote Container (DOCKSEC-04)

**What:** Run sshd as `remoteuser` in the e2e remote container. Port 1234 is
already non-privileged — no `setcap` needed.

```dockerfile
# Generate host keys before switching to remoteuser
RUN ssh-keygen -A && \
    chown remoteuser:remoteuser /etc/ssh/ssh_host_* && \
    chmod 700 /etc/ssh/ssh_host_* && \
    chown remoteuser:remoteuser /var/run/sshd

USER remoteuser

# sshd needs a writable PidFile — use /tmp
RUN echo "PidFile /tmp/sshd.pid" >> /etc/ssh/sshd_config

CMD ["/usr/sbin/sshd", "-D", "-e"]
```

### Pattern 6: Ephemeral SSH Key Generation (DOCKSEC-05)

**Python container (already compliant):** The Dockerfile already does:
```dockerfile
RUN ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa && \
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
```
This generates a fresh key pair every build. No change required for DOCKSEC-05 in
the python container.

**E2E remote container (NOT compliant):** Currently uses a static
`src/docker/test/e2e/remote/id_rsa.pub` committed to the repo. The private key is
gitignored. The current e2e test uses PASSWORD auth (not key auth at all).

DOCKSEC-05 requires the key pair to be generated at build time. Since DOCKSEC-02
also disables password auth in the remote container, the e2e test must switch to SSH
key auth. The recommended approach:

1. In `run-tests-e2e` Makefile target: generate a temporary key pair before building
   the remote container.
2. Pass the public key as a `--build-arg` to the remote Dockerfile.
3. Mount the private key into the myapp staging container via a compose volume.
4. Update `setup_seedsyncarr.sh` to set `use_ssh_key=true` instead of
   `remote_password`.
5. Remove the static `src/docker/test/e2e/remote/id_rsa.pub` file.

```bash
# In Makefile run-tests-e2e target (before docker build):
ssh-keygen -t ed25519 -N "" -f /tmp/e2e_test_key
E2E_SSH_PUBKEY=$(cat /tmp/e2e_test_key.pub)
# Pass to remote container build:
$(DOCKER) buildx build \
  --build-arg SSH_PUBKEY="$E2E_SSH_PUBKEY" \
  ...
```

```dockerfile
# In remote/Dockerfile:
ARG SSH_PUBKEY
RUN mkdir -p /home/remoteuser/.ssh && \
    echo "${SSH_PUBKEY}" >> /home/remoteuser/.ssh/authorized_keys && \
    chown -R remoteuser:remoteuser /home/remoteuser/.ssh && \
    chmod 700 /home/remoteuser/.ssh && \
    chmod 600 /home/remoteuser/.ssh/authorized_keys
```

The private key at `/tmp/e2e_test_key` is mounted into the myapp container's
`/home/seedsync/.ssh/id_ed25519` via a compose volume override so the app can use it.

### Pattern 7: Disable Password Auth + Lock User Password (DOCKSEC-02/03)

```dockerfile
# Disable password authentication in sshd
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config && \
    echo "UsePAM no" >> /etc/ssh/sshd_config

# Lock the user's password (makes the password field invalid — no login via password)
RUN passwd -l seedsyncarrtest    # python container
RUN passwd -l remoteuser         # e2e remote container
```

### Pattern 8: Fix StrictHostKeyChecking (DOCKSEC-06)

**Python test container `/root/.ssh/config`:**

```dockerfile
# Before (current):
RUN echo "StrictHostKeyChecking no\nUserKnownHostsFile /dev/null\nLogLevel=quiet" > /root/.ssh/config

# After (DOCKSEC-06):
RUN echo "StrictHostKeyChecking accept-new\nUserKnownHostsFile /dev/null\nLogLevel=quiet" > /root/.ssh/config
```

`accept-new` accepts new host keys (needed since the container generates fresh keys
every build) but rejects changed keys. Using `/dev/null` for `UserKnownHostsFile` is
acceptable in this test-only container since we accept-new every time.

### Anti-Patterns to Avoid

- **Removing `UserKnownHostsFile /dev/null` from sshd config while keeping `accept-new`:** The known_hosts file would accumulate old keys from previous runs and fail after a rebuild. Keep `/dev/null` for the test container.
- **Changing `setcap` to compose `cap_add: NET_BIND_SERVICE`:** This only grants the capability to root user in the container; non-root processes still cannot bind. `setcap` on the binary is the correct approach.
- **Using `UsePrivilegeSeparation no` for non-root sshd:** This is deprecated in OpenSSH 9.x and removed in some distributions. Use the `sshdaemon` user approach instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Capability setting | Custom wrapper to set capabilities | `setcap cap_net_bind_service=+ep` via `libcap2-bin` | Standard Linux capability tool, single command |
| Non-root process spawn | Custom su wrapper | `su-exec` or `gosu` (available in Debian apt) | Battle-tested, correct signal handling |
| Docker build cache | Custom layer caching logic | `--cache-from/--cache-to type=registry` | Buildx built-in, mode=max caches all layers |
| SHA lookup | Manual git tag traversal | GitHub API `git/ref/tags/<tag>` | Returns commit SHA directly |

**Key insight:** The Docker SSH security patterns here are all single-command
solutions. Any multi-script approach to achieve what `setcap` + `passwd -l` does is
a red flag.

## Common Pitfalls

### Pitfall 1: sshd Host Key Ownership
**What goes wrong:** When sshd runs as a non-root user, it cannot read host keys owned by root (mode 600 root:root).
**Why it happens:** sshd drops to the daemon user before reading keys, but the keys were created by root.
**How to avoid:** After `ssh-keygen -A` (which generates all host keys as root), explicitly `chown sshdaemon /etc/ssh/ssh_host_*`.
**Warning signs:** sshd exits immediately at startup with "no hostkeys available".

### Pitfall 2: /var/run/sshd Directory Ownership
**What goes wrong:** sshd cannot create its PID file or privilege separation directory.
**Why it happens:** `/var/run/sshd` is owned by root:root with mode 0755 by default in Debian; non-root sshd cannot write to it.
**How to avoid:** `RUN chown sshdaemon /var/run/sshd` in Dockerfile before switching user.
**Warning signs:** sshd exits with "Missing privilege separation directory: /var/run/sshd" or "Permission denied".

### Pitfall 3: /etc/ssh/sshd_config Append vs Replace
**What goes wrong:** `echo "PasswordAuthentication no" >> /etc/ssh/sshd_config` appends a line but an earlier `PasswordAuthentication yes` line still takes precedence (last match wins in some sshd versions; first match wins in others).
**Why it happens:** The python Dockerfile currently appends `PasswordAuthentication yes`. Simply appending `no` creates a conflict.
**How to avoid:** Use `sed -i` to replace the existing line rather than appending.
**Warning signs:** sshd still accepts passwords after the change.

### Pitfall 4: `setcap` Effect on Docker Layers
**What goes wrong:** `setcap` is applied to the binary but a later RUN step copies or reinstalls openssh-server, wiping the capability.
**Why it happens:** `apt-get upgrade` or re-installation of packages resets file capabilities.
**How to avoid:** Apply `setcap` in the last step that touches `/usr/sbin/sshd`, or in a dedicated final RUN step.
**Warning signs:** Non-root sshd fails to bind port 22 with "Permission denied".

### Pitfall 5: Password-Auth Tests Break Without Corresponding Code Updates
**What goes wrong:** Disabling `PasswordAuthentication` in the python test container causes 5+ existing tests to fail or error differently than expected.
**Why it happens:** `test_password_auth`, `test_error_bad_password`, `test_copy_error_bad_password`, `test_shell_error_bad_password` all depend on password auth being available.
**How to avoid:** Update or remove these tests in the SAME wave as the Dockerfile change. Do not commit the Dockerfile change without the test updates — CI will go red.
**Warning signs:** CI `unittests-python` fails on the password-auth test names.

### Pitfall 6: E2E Remote Dockerfile ADD of Static id_rsa.pub Must Be Removed
**What goes wrong:** Old static `id_rsa.pub` file is still `ADD`ed into the Dockerfile even after switching to ephemeral key generation via `--build-arg`.
**Why it happens:** Forgetting to remove the `ADD` line and the static file.
**How to avoid:** Remove `ADD src/docker/test/e2e/remote/id_rsa.pub /home/remoteuser/user_id_rsa.pub` and the file itself.
**Warning signs:** Build succeeds but uses old static key, ignoring the ephemeral one.

### Pitfall 7: GitHub Release Published Before Docker Image (CISEC-03)
**What goes wrong:** A GitHub release references a Docker image tag that doesn't exist yet in GHCR because `publish-github-release` ran in parallel with `publish-docker-image`.
**Why it happens:** Both jobs currently have `needs: [ e2etests-docker-image ]` — they run in parallel.
**How to avoid:** Add `publish-docker-image` to `publish-github-release`'s `needs` list.
**Warning signs:** Release notes say "see Docker image `ghcr.io/.../latest`" but the tag doesn't exist yet at release time.

### Pitfall 8: Workflow-Level `contents: read` Breaks Jobs That Need `contents: write`
**What goes wrong:** `publish-github-release` (needs `contents: write`) and `publish-docs` (needs `contents: write`) fail with permission errors after restricting workflow-level permissions.
**Why it happens:** The workflow-level `permissions: contents: read` sets the baseline; jobs without an override inherit it.
**How to avoid:** Add `permissions: contents: write` at the job level for `publish-github-release` and `publish-docs`.
**Warning signs:** `gh release create` fails with 403; peaceiris/actions-gh-pages fails with push permission error.

## Code Examples

### CISEC-01/02 Combined Workflow Example (Partial)

```yaml
# Source: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token
permissions:
  contents: read    # workflow-level default — all jobs start here

jobs:
  unittests-python:
    name: Python unit tests
    runs-on: ubuntu-latest
    permissions:
      packages: write  # CISEC-04: push registry cache to GHCR
    steps:
      - name: Checkout
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1  ← CISEC-02
      - name: Log into GitHub Container Registry
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login https://ghcr.io -u ${{ github.actor }} --password-stdin
      - name: Set staging registry env variable
        run: echo "staging_registry=ghcr.io/${GITHUB_REPOSITORY,,}" >> $GITHUB_ENV
      - name: Run Python unit tests
        run: make run-tests-python PYTHON_TEST_CACHE_REGISTRY=${{ env.staging_registry }}

  publish-github-release:
    name: Publish GitHub Release
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    needs: [ e2etests-docker-image, publish-docker-image ]   # ← CISEC-03 change
    permissions:
      contents: write   # ← CISEC-01 job-level write
    steps:
      ...
```

### DOCKSEC-03/04/06 Python Dockerfile Changes

```dockerfile
# Source: verified via direct Dockerfile inspection + DOCKSEC requirements
# Install capability tool + su-exec
RUN apt-get update && \
    apt-get install -y openssh-server unrar libcap2-bin gosu ...

# Create dedicated sshd runner (no shell, no home)
RUN useradd -r -s /usr/sbin/nologin -d /nonexistent sshdaemon

# Allow sshdaemon to bind port 22
RUN setcap cap_net_bind_service=+ep /usr/sbin/sshd

# DOCKSEC-03: disable password auth, lock user password
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?UsePAM.*/UsePAM no/' /etc/ssh/sshd_config
RUN passwd -l seedsyncarrtest

# DOCKSEC-06: accept-new instead of no
RUN printf "StrictHostKeyChecking accept-new\nUserKnownHostsFile /dev/null\nLogLevel=quiet\n" > /root/.ssh/config

# DOCKSEC-04: transfer sshd runtime ownership to sshdaemon
RUN chown sshdaemon /var/run/sshd && \
    chown sshdaemon:sshdaemon /etc/ssh/ssh_host_* && \
    chmod 700 /etc/ssh/ssh_host_*
```

### entrypoint.sh Change (DOCKSEC-04)

```bash
# Source: standard gosu/su-exec pattern for non-root daemon startup
# Before:
/usr/sbin/sshd -D &
# After:
gosu sshdaemon /usr/sbin/sshd -D &
```

### DOCKSEC-01: Remove seedsyncarrtest from root group

```dockerfile
# Before:
RUN usermod -a -G root seedsyncarrtest

# After (DOCKSEC-01): create dedicated group instead
RUN groupadd testgroup && \
    usermod -a -G testgroup seedsyncarrtest

# The container's primary user (root, running pytest) must also be in testgroup
# so temp dirs created by pytest get the correct group-writable bits.
# One approach: change pytest's effective GID in entrypoint.sh:
# After:
# gosu sshdaemon /usr/sbin/sshd -D &
# exec newgrp testgroup -- "$@"
# But this requires sgid setup.
#
# Simpler: use RUN usermod -a -G testgroup root (root joins testgroup)
RUN usermod -a -G testgroup root
```

**Warning:** `chmod_from_to(..., 0o775)` in tests will set group bits that only work
if the pytest process's effective GID is `testgroup`. Verify that pytest inside the
container runs with GID of testgroup, not GID 0.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pin Actions to tag (`@v4`) | Pin to full SHA with comment (`@sha # v4.3.1`) | After March 2025 supply-chain attack on tj-actions/changed-files | Prevents tag mutation attacks |
| Run sshd as root | Run sshd as dedicated non-root user | SSH CIS Benchmark current | Limits blast radius of sshd compromise |
| Allow password auth in test containers | Key-only auth even in test containers | OWASP/ASVS V2.7 current | Removes hardcoded password from container image |
| `StrictHostKeyChecking no` | `StrictHostKeyChecking accept-new` | OpenSSH 7.6+ | Protects against MITM while allowing new hosts |

**Deprecated/outdated:**
- `UsePrivilegeSeparation no`: Removed in OpenSSH 9.x in some distros. Use user-based separation instead.
- Inline SSH private keys in Dockerfiles: Always use `--build-arg` or volumes; never commit.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | GHCR staging registry is public (no `packages: read` needed for e2etests-docker-image pull) | Architecture Patterns, Pattern 1 | If private: e2etests-docker-image docker pull fails with 401 — fix by adding `packages: read` per-job perm |
| A2 | `pypa/gh-action-pypi-publish@cef22109...` is a legitimate v1.x commit (pinned but below v1.14.0) | Standard Stack | If stale: possible security exposure for PyPI publish — consider updating SHA to v1.14.0 equivalent |
| A3 | `gosu` is the preferred su-exec alternative (available via `apt-get install -y gosu` in Debian Bookworm) | Don't Hand-Roll | If not available: use `su-exec` (may need to install from source) or `runuser` |
| A4 | The `testgroup` GID approach is sufficient to replace root-group dependency without changing test code | Code Examples, DOCKSEC-01 | If root's group membership affects pytest temp dir ownership differently: may need `newgrp` in entrypoint or `chown` in tests |

**If this table is empty:** All claims were verified or cited.

## Open Questions

1. **Does e2e myapp container have a default SSH key at `/home/seedsync/.ssh/`?**
   - What we know: myapp uses `/root/.ssh/config` with `StrictHostKeyChecking accept-new`; `run_as_user` creates home at `/home/seedsync`
   - What's unclear: Where exactly the SSH private key would be placed for key-based auth in e2e
   - Recommendation: Inspect the `run_as_user` + `seedsyncarr.py` SSH key loading logic to confirm the home dir path before implementing DOCKSEC-05 e2e changes

2. **Does disabling `PasswordAuthentication` in the python container require updating test_controller.py::test_password_auth, test_lftp_protocol.py::test_password_auth, and test_sshcp.py password variants?**
   - What we know: Yes — these tests explicitly use password auth and will fail differently or completely when it's disabled
   - What's unclear: Whether the requirement author intends to keep password-auth tests (testing app behavior) or remove them
   - Recommendation: The planner should treat test updates as required sub-tasks of DOCKSEC-03, not optional cleanup

3. **Is `pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b` the current recommended SHA or should it be updated to latest v1?**
   - What we know: It's pinned (compliant with CISEC-02) but below v1.14.0 (latest release)
   - Recommendation: Keep existing SHA for this phase (CISEC-02 only requires pinning, not updating); note as tech debt

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `libcap2-bin` (apt) | DOCKSEC-04 python container | Debian Bookworm apt | — | `apt-get install` at build time |
| `gosu` (apt) | DOCKSEC-04 entrypoint | Debian Bookworm apt | — | `su-exec` (compile from source) |
| `ssh-keygen` | DOCKSEC-05 | Available in `openssh-client` | — | Already in base image |
| GHCR registry push | CISEC-04 | ✓ (already used by other jobs) | — | — |
| GitHub Actions | All CISEC | ✓ | — | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python unit/integration tests) |
| Config file | none — default discovery via `pytest -v -p no:cacheprovider` |
| Quick run command | `make run-tests-python` |
| Full suite command | `make run-tests-python` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CISEC-01 | Workflow permissions restricted to `contents: read` at workflow level | manual (YAML lint) | `grep "contents: write\|packages: write" .github/workflows/ci.yml` (should only appear at job level) | N/A |
| CISEC-02 | All actions pinned to SHA | manual (YAML lint) | `grep "uses:" .github/workflows/ci.yml \| grep -v "@[a-f0-9]\{40\}"` (should return empty) | N/A |
| CISEC-03 | publish-github-release needs publish-docker-image | manual (YAML inspection) | `grep -A3 "publish-github-release:" .github/workflows/ci.yml \| grep needs` | N/A |
| CISEC-04 | Python test image cache used in CI | manual (CI log inspection) | check CI logs for "CACHED" in Python build step | N/A |
| DOCKSEC-01 | seedsyncarrtest not in root group | unit | `docker run --rm seedsyncarr/test/python id seedsyncarrtest` | ❌ Wave 0 |
| DOCKSEC-02 | remote container PasswordAuthentication no | unit | `docker run --rm seedsyncarr/test/e2e/remote grep PasswordAuthentication /etc/ssh/sshd_config` | ❌ Wave 0 |
| DOCKSEC-03 | python container PasswordAuthentication no | unit | `docker run --rm seedsyncarr/test/python grep PasswordAuthentication /etc/ssh/sshd_config` | ❌ Wave 0 |
| DOCKSEC-04 | sshd runs as non-root | integration | `make run-tests-python` (tests still pass confirms sshd works as non-root) | ✅ (existing tests) |
| DOCKSEC-05 | Ephemeral key pair generated at build time | unit | verify no static id_rsa.pub in e2e remote; python already compliant | ❌ Wave 0 |
| DOCKSEC-06 | StrictHostKeyChecking accept-new | unit | `docker run --rm seedsyncarr/test/python grep StrictHostKeyChecking /root/.ssh/config` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] Dockerfile smoke-test script — confirms security settings are applied (can be inline shell in CI)

### Sampling Rate
- **Per task commit:** `make run-tests-python` (confirms sshd+pytest still work)
- **Per wave merge:** `make run-tests-python && make run-tests-angular`
- **Phase gate:** Full suite green before `/gsd-verify-work`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | SSH key-only auth; disable password auth |
| V3 Session Management | no | n/a (SSH session, not HTTP) |
| V4 Access Control | yes | Least-privilege workflow permissions; non-root sshd |
| V5 Input Validation | no | n/a (YAML/Dockerfile config changes) |
| V6 Cryptography | yes | ed25519 ephemeral key pair; never hardcoded keys |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Supply-chain action compromise (tag mutation) | Tampering | SHA pin all Actions (CISEC-02) |
| Over-privileged GITHUB_TOKEN used by compromised step | Elevation of privilege | Least-privilege permissions (CISEC-01) |
| Password brute-force via SSH in test container | Authentication bypass | Disable PasswordAuthentication (DOCKSEC-02/03) |
| Hardcoded SSH credential in Docker image | Information disclosure | `passwd -l` + key-only auth |
| Root-group membership broadens SSH user blast radius | Elevation of privilege | Dedicated group (DOCKSEC-01) |
| sshd running as root amplifies container escape impact | Elevation of privilege | Non-root sshd (DOCKSEC-04) |
| MITM via changed host key accepted silently | Spoofing | `accept-new` not `no` (DOCKSEC-06) |

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `.github/workflows/ci.yml` — all jobs, permissions, action references
- Direct file inspection: `src/docker/test/python/Dockerfile` — sshd setup, user config
- Direct file inspection: `src/docker/test/e2e/remote/Dockerfile` — static key, password auth, CMD
- Direct file inspection: `src/python/tests/unittests/test_ssh/test_sshcp.py` — password auth tests
- Direct file inspection: `src/python/tests/integration/test_lftp/test_lftp_protocol.py` — password auth tests
- GitHub API `api.github.com/repos/*/git/ref/tags/*` — SHA verification for all actions
- [Docker build cache backends documentation](https://docs.docker.com/build/ci/github-actions/cache/) — cache-from/cache-to registry syntax

### Secondary (MEDIUM confidence)
- [GitHub Actions controlling permissions docs](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token) — permissions syntax
- [StepSecurity: pinning GitHub Actions](https://www.stepsecurity.io/blog/pinning-github-actions-for-enhanced-security-a-complete-guide) — SHA pin rationale
- [GoLinuxCloud: run sshd as non-root](https://www.golinuxcloud.com/run-sshd-as-non-root-user-without-sudo/) — non-root sshd patterns

### Tertiary (LOW confidence)
- None — all critical claims were verified against codebase or official docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against GitHub API and direct Dockerfile inspection
- Architecture: HIGH — all Dockerfiles and CI YAML directly inspected
- Pitfalls: HIGH — derived from observed code patterns in the actual files

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (stable domain — SHA values may shift slightly with new action releases but the approach remains the same)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CISEC-01 | Restrict workflow-level permissions to `contents: read`, add per-job write permissions only where needed | Per-job permissions matrix documented in Architecture Patterns |
| CISEC-02 | Pin GitHub Actions to SHA hashes with version comments | SHA values verified via GitHub API; 3 unpinned actions identified |
| CISEC-03 | Add `publish-docker-image` to `publish-github-release` needs chain | Current needs chain verified; fix is a single YAML line addition |
| CISEC-04 | Add registry-based Docker build cache for Python test images in CI | `--cache-from/--cache-to type=registry` syntax documented; Makefile + CI changes scoped |
| DOCKSEC-01 | Remove test user from root group — create dedicated group if needed | root group dependency in tests analyzed; testgroup approach with root membership documented |
| DOCKSEC-02 | Lock SSH password and disable PasswordAuthentication in remote test container | Current remote Dockerfile inspected; PasswordAuthentication change + passwd -l approach documented |
| DOCKSEC-03 | Lock SSH password and disable PasswordAuthentication in Python test container | Password-auth test breakage analyzed; affected test files identified (5 tests across 3 files) |
| DOCKSEC-04 | Run sshd as non-root in test containers | setcap approach for python (port 22), remoteuser approach for e2e remote (port 1234) documented |
| DOCKSEC-05 | Generate ephemeral SSH key pair at Docker build time | Python container already compliant; e2e remote needs Makefile keygen + --build-arg pattern |
| DOCKSEC-06 | Change StrictHostKeyChecking no to accept-new in Python test container | Single sed/echo change in python Dockerfile identified |
</phase_requirements>
