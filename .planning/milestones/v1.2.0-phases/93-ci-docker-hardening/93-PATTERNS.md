# Phase 93: CI & Docker Hardening - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 8 files to modify (no new files created)
**Analogs found:** 8 / 8 (all files are self-analogs — changes are edits within existing files)

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `.github/workflows/ci.yml` | config/CI | event-driven | `.github/workflows/ci.yml` itself | self (in-place edit) |
| `src/docker/test/python/Dockerfile` | config/container | batch | `src/docker/test/e2e/remote/Dockerfile` | role-match |
| `src/docker/test/python/entrypoint.sh` | config/entrypoint | event-driven | `src/docker/test/python/entrypoint.sh` itself | self (in-place edit) |
| `src/docker/test/e2e/remote/Dockerfile` | config/container | batch | `src/docker/test/python/Dockerfile` | role-match |
| `src/docker/test/e2e/compose.yml` | config/compose | event-driven | `src/docker/stage/docker-image/compose.yml` | role-match |
| `Makefile` | config/build | batch | `Makefile` itself | self (in-place edit) |
| `src/python/tests/unittests/test_ssh/test_sshcp.py` | test | request-response | `src/python/tests/integration/test_lftp/test_lftp_protocol.py` | role-match |
| `src/python/tests/integration/test_lftp/test_lftp_protocol.py` | test | request-response | `src/python/tests/unittests/test_ssh/test_sshcp.py` | role-match |
| `src/python/tests/integration/test_controller/test_controller.py` | test | request-response | `src/python/tests/integration/test_lftp/test_lftp_protocol.py` | role-match |
| `src/docker/test/e2e/configure/setup_seedsyncarr.sh` | config/script | request-response | `src/docker/test/e2e/configure/setup_seedsyncarr.sh` itself | self (in-place edit) |

---

## Pattern Assignments

### `.github/workflows/ci.yml` (config/CI, event-driven)

**Analog:** `.github/workflows/ci.yml` (self — mechanical YAML edits)

**Current workflow-level permissions (lines 15-17) — to be replaced:**
```yaml
permissions:
  contents: write
  packages: write
```

**Target permissions pattern (CISEC-01):**
```yaml
permissions:
  contents: read    # workflow-level default — all jobs start here
```

**Current unpinned action references — all 13 occurrences to replace (CISEC-02):**
```yaml
# Every checkout in the file (9 occurrences at lines 26, 37, 48, 65, 87, 124, 160, 201, 245, 280):
uses: actions/checkout@v4

# setup-python (lines 51, 224, 283):
uses: actions/setup-python@v5

# setup-node (line 69):
uses: actions/setup-node@v4
```

**SHA-pinned replacements (CISEC-02):**
```yaml
uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0
```

**Already-pinned actions — do NOT change:**
```yaml
uses: docker/setup-qemu-action@c7c53464625b32c7a7e944ae62b3e17d2b600130 # v3
uses: docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f # v3
uses: peaceiris/actions-gh-pages@4f9cc6602d3f66b9c108549d475ec49e8ef4d45e # v4
uses: pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b # release/v1
```

**Current publish-github-release needs chain (lines 196-196) — CISEC-03 change:**
```yaml
# Before:
needs: [ e2etests-docker-image ]

# After:
needs: [ e2etests-docker-image, publish-docker-image ]
```

**publish-github-release also needs a job-level permissions block (CISEC-01):**
```yaml
publish-github-release:
  name: Publish GitHub Release
  if: startsWith(github.ref, 'refs/tags/v')
  runs-on: ubuntu-latest
  needs: [ e2etests-docker-image, publish-docker-image ]
  permissions:
    contents: write    # required for gh release create
```

**publish-docs needs job-level permissions block (CISEC-01):**
```yaml
publish-docs:
  name: Publish Documentation
  ...
  permissions:
    contents: write    # peaceiris/actions-gh-pages pushes to gh-pages branch
```

**unittests-python job additions (CISEC-04) — copy GHCR login + cache from build-docker-image job (lines 99-108):**
```yaml
# From build-docker-image job — copy this exact pattern:
- name: Log into GitHub Container Registry
  run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login https://ghcr.io -u ${{ github.actor }} --password-stdin
- name: Set staging registry env variable
  run: echo "staging_registry=ghcr.io/${GITHUB_REPOSITORY,,}" >> $GITHUB_ENV

# Then replace the existing run-tests-python step with:
- name: Run Python unit tests
  run: make run-tests-python PYTHON_TEST_CACHE_REGISTRY=${{ env.staging_registry }}
```

**unittests-python job-level permissions (CISEC-01 + CISEC-04):**
```yaml
unittests-python:
  name: Python unit tests
  runs-on: ubuntu-latest
  permissions:
    packages: write    # CISEC-04: push registry cache tag to GHCR
```

**Jobs that need NO job-level permissions override (they inherit `contents: read`):**
- `unittests-angular` — only reads/runs tests
- `lint-python` — only reads
- `lint-angular` — only reads
- `e2etests-docker-image` — only pulls (GHCR staging registry is public per A1)
- `publish-docker-image` — already has no explicit permissions block; needs `packages: write`
- `publish-docker-image-dev` — needs `packages: write`
- `publish-pypi` — already has `id-token: write` (keep as-is)

---

### `src/docker/test/python/Dockerfile` (config/container, batch)

**Analog:** `src/docker/test/python/Dockerfile` (self — in-place edits)

**Full current file for reference (lines 1-51) — key sections that change:**

**DOCKSEC-01 — replace root group with dedicated group (lines 35-35):**
```dockerfile
# Before (line 35):
RUN usermod -a -G root seedsyncarrtest

# After:
RUN groupadd testgroup && \
    usermod -a -G testgroup seedsyncarrtest && \
    usermod -a -G testgroup root
```

**DOCKSEC-03 — disable password auth (replace lines 28-30):**
```dockerfile
# Before (lines 28-30):
RUN echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "KbdInteractiveAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "UsePAM yes" >> /etc/ssh/sshd_config

# After — use sed to replace (avoids Pitfall 3):
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?UsePAM.*/UsePAM no/' /etc/ssh/sshd_config
# Lock the user password to prevent any password-based login
RUN passwd -l seedsyncarrtest
```

**DOCKSEC-04 — non-root sshd using setcap (add after apt-get block, before user setup):**
```dockerfile
# Add libcap2-bin + gosu to the existing apt-get install line:
RUN apt-get update && \
    apt-get install -y openssh-server unrar libcap2-bin gosu && \
    ...

# Create dedicated sshd runner (after apt-get, before ssh-keygen):
RUN useradd -r -s /usr/sbin/nologin -d /nonexistent sshdaemon

# Allow sshdaemon to bind port 22 (apply AFTER all openssh-server installs — Pitfall 4):
RUN setcap cap_net_bind_service=+ep /usr/sbin/sshd

# Transfer sshd runtime ownership (after ssh-keygen -A style key generation):
RUN chown sshdaemon /var/run/sshd && \
    chown sshdaemon:sshdaemon /etc/ssh/ssh_host_* && \
    chmod 700 /etc/ssh/ssh_host_*
```

**DOCKSEC-05 — python container already compliant (lines 22-23 — DO NOT CHANGE):**
```dockerfile
# Already generates ephemeral key at build time — no change needed:
RUN ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa && \
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
```

**DOCKSEC-06 — accept-new instead of no (line 25):**
```dockerfile
# Before (line 25):
RUN echo "StrictHostKeyChecking no\nUserKnownHostsFile /dev/null\nLogLevel=quiet" > /root/.ssh/config

# After:
RUN printf "StrictHostKeyChecking accept-new\nUserKnownHostsFile /dev/null\nLogLevel=quiet\n" > /root/.ssh/config
```

---

### `src/docker/test/python/entrypoint.sh` (config/entrypoint, event-driven)

**Analog:** `src/docker/test/python/entrypoint.sh` (self — one-line change)

**Current file (lines 1-11) — only line 7 changes (DOCKSEC-04):**
```bash
# Before (line 7):
/usr/sbin/sshd -D &

# After — run as sshdaemon via gosu:
gosu sshdaemon /usr/sbin/sshd -D &
```

Full context showing where the change fits:
```bash
#!/bin/bash
set -e
echo "Running sshd"
gosu sshdaemon /usr/sbin/sshd -D &   # DOCKSEC-04: was /usr/sbin/sshd -D &
echo "Continuing entrypoint"
echo "$@"
exec $@
```

---

### `src/docker/test/e2e/remote/Dockerfile` (config/container, batch)

**Analog:** `src/docker/test/e2e/remote/Dockerfile` (self) + `src/docker/test/python/Dockerfile` (role-match for sshd patterns)

**Full current file for reference (lines 1-36).**

**DOCKSEC-02 — disable password auth + lock remoteuser password:**
```dockerfile
# Add after the openssh-server install block (after line 31):
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config && \
    echo "UsePAM no" >> /etc/ssh/sshd_config
RUN passwd -l remoteuser
```

**DOCKSEC-04 — run sshd as remoteuser (port 1234 is non-privileged — no setcap needed):**
```dockerfile
# Add after host key generation + ownership transfer:
RUN ssh-keygen -A && \
    chown remoteuser:remoteuser /etc/ssh/ssh_host_* && \
    chmod 700 /etc/ssh/ssh_host_* && \
    chown remoteuser:remoteuser /var/run/sshd

# Non-root sshd needs writable PidFile location:
RUN echo "PidFile /tmp/sshd.pid" >> /etc/ssh/sshd_config

USER remoteuser

# Replace current CMD (line 36):
# Before:
CMD ["/usr/sbin/sshd", "-D"]
# After:
CMD ["/usr/sbin/sshd", "-D", "-e"]
```

**DOCKSEC-05 — ephemeral SSH key via build-arg (replaces static ADD of id_rsa.pub):**
```dockerfile
# Remove entirely (lines 19-21):
USER remoteuser
ADD --chown=remoteuser:remoteuser src/docker/test/e2e/remote/id_rsa.pub /home/remoteuser/user_id_rsa.pub
RUN  mkdir -p /home/remoteuser/.ssh && \
    cat /home/remoteuser/user_id_rsa.pub >> /home/remoteuser/.ssh/authorized_keys
USER root

# Replace with ARG-based ephemeral key injection:
ARG SSH_PUBKEY
RUN mkdir -p /home/remoteuser/.ssh && \
    echo "${SSH_PUBKEY}" >> /home/remoteuser/.ssh/authorized_keys && \
    chown -R remoteuser:remoteuser /home/remoteuser/.ssh && \
    chmod 700 /home/remoteuser/.ssh && \
    chmod 600 /home/remoteuser/.ssh/authorized_keys
```

**Also remove the static file:** `src/docker/test/e2e/remote/id_rsa.pub` must be deleted from the repo.

---

### `Makefile` (config/build, batch)

**Analog:** `Makefile` itself — specifically the `docker-image` target (lines 30-49) which already uses `--cache-from/--cache-to type=registry` pattern.

**Existing cache pattern from `docker-image` target (lines 45-46) — copy this pattern for python test build:**
```makefile
--cache-to=type=registry,ref=$${STAGING_REGISTRY}:cache,mode=max \
--cache-from=type=registry,ref=$${STAGING_REGISTRY}:cache \
```

**CISEC-04 — add cache support to `tests-python` target (lines 79-85):**
```makefile
# Before (lines 79-85):
tests-python:
	# python run
	$(DOCKER) build \
		-f ${SOURCEDIR}/docker/build/docker-image/Dockerfile \
		--target seedsyncarr_run_python_devenv \
		--tag seedsyncarr/run/python/devenv \
		${ROOTDIR}

# After — add conditional cache flags:
tests-python:
	# python run
	$(DOCKER) build \
		-f ${SOURCEDIR}/docker/build/docker-image/Dockerfile \
		--target seedsyncarr_run_python_devenv \
		--tag seedsyncarr/run/python/devenv \
		$(if $(PYTHON_TEST_CACHE_REGISTRY),--cache-from type=registry$(,)ref=$(PYTHON_TEST_CACHE_REGISTRY):cache-python-test) \
		$(if $(PYTHON_TEST_CACHE_REGISTRY),--cache-to type=registry$(,)ref=$(PYTHON_TEST_CACHE_REGISTRY):cache-python-test$(,)mode=max) \
		${ROOTDIR}
```

Note: Makefile comma escaping — define `,` as a variable: `comma := ,` then use `$(comma)` in the cache flags. Alternative: use a shell conditional inside the recipe:

```makefile
tests-python:
	# python run
	@CACHE_FLAGS=""; \
	if [ -n "$(PYTHON_TEST_CACHE_REGISTRY)" ]; then \
		CACHE_FLAGS="--cache-from type=registry,ref=$(PYTHON_TEST_CACHE_REGISTRY):cache-python-test --cache-to type=registry,ref=$(PYTHON_TEST_CACHE_REGISTRY):cache-python-test,mode=max"; \
	fi; \
	$(DOCKER) build \
		-f ${SOURCEDIR}/docker/build/docker-image/Dockerfile \
		--target seedsyncarr_run_python_devenv \
		--tag seedsyncarr/run/python/devenv \
		$$CACHE_FLAGS \
		${ROOTDIR}
```

**DOCKSEC-05 — add ephemeral key generation to `run-tests-e2e` target (before the `docker buildx build` for remote, around line 131):**
```makefile
# Before current remote container build:
ssh-keygen -t ed25519 -N "" -f /tmp/e2e_test_key
E2E_SSH_PUBKEY=$$(cat /tmp/e2e_test_key.pub)
$(DOCKER) buildx build \
	--platform $${SEEDSYNCARR_PLATFORM} \
	--load \
	-t seedsyncarr/test/e2e/remote \
	--build-arg SSH_PUBKEY="$${E2E_SSH_PUBKEY}" \
	-f ${SOURCEDIR}/docker/test/e2e/remote/Dockerfile \
	.
```

---

### `src/docker/test/e2e/compose.yml` (config/compose, event-driven)

**Analog:** `src/docker/stage/docker-image/compose.yml` (compose volume mount pattern) + `src/docker/test/e2e/compose-dev.yml` (override pattern)

**DOCKSEC-05 + DOCKSEC-02 — mount ephemeral private key into myapp container and switch from password to key auth:**

The configure service currently passes `REMOTE_PASSWORD` (line 53-54). After switching to key auth, the approach is:

1. Mount the private key generated in Makefile (`/tmp/e2e_test_key`) into the myapp service.
2. Update `setup_seedsyncarr.sh` to set `use_ssh_key` instead of `remote_password`.

**Volume mount pattern (copy from how compose overrides work — see compose-dev.yml):**
```yaml
# In src/docker/test/e2e/compose.yml — add volume to myapp service:
myapp:
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:8800/server/status"]
    interval: 5s
    timeout: 5s
    retries: 12
    start_period: 10s
  volumes:
    - type: bind
      source: /tmp/e2e_test_key
      target: /home/seedsync/.ssh/id_ed25519
      read_only: true
```

**configure service env update (DOCKSEC-02 — remove REMOTE_PASSWORD, add SSH_KEY_PATH):**
```yaml
configure:
  environment:
    - REMOTE_USERNAME=${REMOTE_USERNAME:-remoteuser}
    # Remove: - REMOTE_PASSWORD=${REMOTE_PASSWORD:-remotepass}
    # SSH key auth replaces password auth
```

---

### `src/docker/test/e2e/configure/setup_seedsyncarr.sh` (config/script, request-response)

**Analog:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh` (self)

**DOCKSEC-02/05 — replace password config with SSH key config (lines 19-20):**
```bash
# Before (line 19-20):
curl -sSf "http://myapp:8800/server/config/set/lftp/remote_password/${REMOTE_PASSWORD:?REMOTE_PASSWORD must be set}" \
  || { echo "ERROR: failed to set lftp/remote_password" >&2; exit 1; }

# After — switch to SSH key-based auth:
curl -sSf "http://myapp:8800/server/config/set/lftp/use_ssh_key/true" \
  || { echo "ERROR: failed to set lftp/use_ssh_key" >&2; exit 1; }
```

**Existing curl config pattern (lines 8-28) to continue following:**
```bash
curl -sSf "http://myapp:8800/server/config/set/<section>/<key>/<value>" \
  || { echo "ERROR: failed to set <section>/<key>" >&2; exit 1; }
```

---

### `src/python/tests/unittests/test_ssh/test_sshcp.py` (test, request-response)

**Analog:** `src/python/tests/unittests/test_ssh/test_sshcp.py` (self — removals/modifications)

**DOCKSEC-03 — password auth tests to remove or adapt:**

1. `_PARAMS` list (lines 21-24) — remove the password tuple:
```python
# Before:
_PARAMS = [
    ("password", _TEST_PASSWORD),
    ("keyauth", None)
]

# After (remove password variant):
_PARAMS = [
    ("keyauth", None)
]
```

2. `test_copy_error_bad_password` (lines 78-82) — remove entirely:
```python
# Remove this entire test method:
@timeout_decorator.timeout(5)
def test_copy_error_bad_password(self):
    sshcp = Sshcp(host=self.host, port=self.port, user=self.user, password="wrong password")
    with self.assertRaises(SshcpError) as ctx:
        sshcp.copy(local_path=self.local_file, remote_path=self.remote_file)
    self.assertEqual("Incorrect password", str(ctx.exception))
```

3. `test_shell_error_bad_password` (lines 176-180) — remove entirely:
```python
# Remove this entire test method:
@timeout_decorator.timeout(5)
def test_shell_error_bad_password(self):
    sshcp = Sshcp(host=self.host, port=self.port, user=self.user, password="wrong password")
    with self.assertRaises(SshcpError) as ctx:
        sshcp.shell("cd {}; pwd".format(self.local_dir))
    self.assertEqual("Incorrect password", str(ctx.exception))
```

4. `_TEST_PASSWORD` constant (line 20) — remove once no tests reference it:
```python
# Remove after all password-using tests are removed:
_TEST_PASSWORD = "seedsyncarrpass"
```

**Parameterized tests that are expanded via `_PARAMS` — these automatically drop the password variant once `_PARAMS` is updated:**
- `test_copy` (parameterized)
- `test_copy_error_missing_local_file` (parameterized)
- `test_copy_error_missing_remote_dir` (parameterized)
- `test_copy_error_bad_host` (parameterized)
- `test_copy_error_bad_port` (parameterized)
- `test_shell` (parameterized)
- `test_shell_with_escape_characters` (parameterized)
- `test_shell_error_bad_host` (parameterized)
- `test_shell_error_bad_port` (parameterized)
- `test_shell_error_bad_command` (parameterized)

---

### `src/python/tests/integration/test_lftp/test_lftp_protocol.py` (test, request-response)

**Analog:** `src/python/tests/integration/test_lftp/test_lftp_protocol.py` (self — removals)

**DOCKSEC-03 — password auth tests to remove:**

1. `test_password_auth` (lines 721-756) — remove entirely:
```python
# Remove this entire test method (lines 721-756):
@timeout_decorator.timeout(5)
def test_password_auth(self):
    # exit the default instance
    self.lftp.exit()
    self.lftp = Lftp(address=self.host, port=self.port, user=self.user, password=self.password)
    ...
```

2. `test_error_bad_password` (lines 758-794) — remove entirely:
```python
# Remove this entire test method (lines 758-794):
@timeout_decorator.timeout(15)
def test_error_bad_password(self):
    ...
    self.assertTrue("Login failed: Login incorrect" in str(ctx.exception))
```

3. `_TEST_PASSWORD` constant (line 18) and `self.password` assignment (line 106) — remove after tests removed:
```python
# Line 18 — remove:
_TEST_PASSWORD = "seedsyncarrpass"

# Line 106 — remove:
self.password = _TEST_PASSWORD
```

Note: The `setUp` method default instance already uses `password=None` (key auth) at line 109. Only the two password-specific test methods above need removing.

---

### `src/python/tests/integration/test_controller/test_controller.py` (test, request-response)

**Analog:** `src/python/tests/integration/test_controller/test_controller.py` (self)

**DOCKSEC-03 — password auth test to remove (lines 2380-2424):**
```python
# Remove this entire test method:
@timeout_decorator.timeout(20)
def test_password_auth(self):
    # Test password-based auth by downloading a file to completion
    self.context.config.lftp.use_ssh_key = False
    ...
    self.assertTrue(fcmp)
```

Also check line 326 — `remote_password` config in test setup:
```python
"remote_password": "seedsyncarrpass",  # Test credentials for Docker-based test container — not a real secret
```
This is in `setUp` context config and feeds into the key-auth default instance. After removing password auth, this line should be removed or set to `None`/empty. Verify whether `remote_password=None` is safe by checking the `Config` model — only the password-specific test method uses `use_ssh_key = False`, so once that test is removed, the setUp config value becomes dead code.

---

## Shared Patterns

### GHCR Login Pattern
**Source:** `.github/workflows/ci.yml` lines 100-104 (build-docker-image job)
**Apply to:** `unittests-python` job (CISEC-04 addition)
```yaml
- name: Log into GitHub Container Registry
  run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login https://ghcr.io -u ${{ github.actor }} --password-stdin
- name: Set staging registry env variable
  run: echo "staging_registry=ghcr.io/${GITHUB_REPOSITORY,,}" >> $GITHUB_ENV
```

### sshd_config Password Disable Pattern
**Source:** RESEARCH.md Pattern 7 (verified against actual Dockerfiles)
**Apply to:** `src/docker/test/python/Dockerfile` (DOCKSEC-03), `src/docker/test/e2e/remote/Dockerfile` (DOCKSEC-02)
```dockerfile
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?UsePAM.*/UsePAM no/' /etc/ssh/sshd_config
```
Use `sed -i` (not `echo >>`) to replace existing lines — Pitfall 3: the python Dockerfile currently appends `PasswordAuthentication yes`, so appending `no` would conflict.

### passwd -l User Lock Pattern
**Source:** RESEARCH.md Pattern 7
**Apply to:** Both Dockerfiles after disabling PasswordAuthentication
```dockerfile
RUN passwd -l <username>   # python: seedsyncarrtest, e2e: remoteuser
```

### SSH Host Key Ownership Transfer Pattern
**Source:** RESEARCH.md Patterns 4 and 5 (Pitfalls 1 and 2)
**Apply to:** Both Dockerfiles before switching to non-root sshd
```dockerfile
# After ssh-keygen -A or existing key generation:
RUN chown <sshdaemon_user>:<sshdaemon_user> /etc/ssh/ssh_host_* && \
    chmod 700 /etc/ssh/ssh_host_* && \
    chown <sshdaemon_user> /var/run/sshd
```
For python container: `sshdaemon`; for e2e remote: `remoteuser`.

### Docker Build Cache Registry Pattern
**Source:** `Makefile` lines 45-46 (docker-image target — already uses this)
**Apply to:** `Makefile` tests-python target (CISEC-04), `.github/workflows/ci.yml` unittests-python job
```makefile
--cache-from=type=registry,ref=$${CACHE_REGISTRY}:cache-python-test \
--cache-to=type=registry,ref=$${CACHE_REGISTRY}:cache-python-test,mode=max \
```

---

## No Analog Found

No files require patterns that do not exist anywhere in the codebase. All changes are:
1. Mechanical YAML edits in ci.yml (patterns already present in other jobs in same file)
2. Dockerfile security hardening (patterns are single-command `sed`/`passwd -l`/`setcap` additions)
3. Test removals (no new test patterns needed — deletions only)

---

## Critical Sequencing Constraints

These are NOT ordering preferences — they are hard dependencies that will cause CI failure if violated:

| Constraint | Rule |
|-----------|------|
| DOCKSEC-03 + test cleanup | Must commit test removals in SAME commit as `PasswordAuthentication no` Dockerfile change. Do NOT split across commits. |
| DOCKSEC-04 setcap placement | `setcap` must be the LAST step that touches `/usr/sbin/sshd` (after all `apt-get install` runs). Pitfall 4. |
| CISEC-01 per-job overrides | Must add `permissions: contents: write` to `publish-github-release` and `publish-docs` in the SAME commit as setting workflow-level `contents: read`. |
| DOCKSEC-05 static key removal | Must remove `ADD src/docker/test/e2e/remote/id_rsa.pub` line AND delete the file in the same commit as adding `ARG SSH_PUBKEY`. |

---

## Metadata

**Analog search scope:** `.github/workflows/`, `src/docker/test/`, `Makefile`, `src/python/tests/`
**Files read:** 12 source files
**Pattern extraction date:** 2026-04-27
