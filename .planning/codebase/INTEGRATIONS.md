# External Integrations

**Analysis Date:** 2026-02-03

## APIs & External Services

**File Transfer Protocol:**
- **LFTP** - Primary file syncing engine via SFTP/FTP
  - Client: `src/python/lftp/lftp.py`
  - Process spawning: pexpect-based interactive command wrapper
  - Auth: Username/password via LFTP arguments
  - Configuration: Remote path, port, parallel jobs, rate limiting
  - Integration point: `src/python/controller/lftp_manager.py`

**Remote Server Access:**
- **SSH/SCP** - Remote file operations (copy, delete) and discovery
  - Client: `src/python/ssh/sshcp.py`
  - Process spawning: pexpect for interactive SSH/SCP
  - Auth: Username/password or key-based (configurable)
  - SSH options: StrictHostKeyChecking disabled, auto-add to known_hosts
  - Integration point: `src/python/controller/file_operation_manager.py`

**Archive/Compression:**
- **patool** ^4.0.3 - Archive handling (extract, list contents)
  - Used for automatic extraction of downloads
  - Supports multiple archive formats
  - Integration: `src/python/controller/file_operation_manager.py`

## Data Storage

**Databases:**
- Not used - stateless API design
- Configuration persisted to local file system only

**File Storage:**
- **Local filesystem** - All file operations use local directory paths
  - Base paths configured in settings.cfg
  - Remote files synced to local directory
  - Temp files for LFTP transfers (configurable)

**Caching:**
- None - Real-time scanning and transfer status

**Persistence:**
- **File-based configuration:** `settings.cfg` (INI format)
- **Persisted state:** Pickle-based persistence files
  - Controller state: `controller.persist`
  - AutoQueue state: `autoqueue.persist`

## Authentication & Identity

**Auth Provider:**
- **Custom** - No centralized auth system
- SSH/SFTP authentication handled directly by pexpect-spawned processes
- Remote server credentials stored in `settings.cfg` under `[Lftp]` section
  - Username: `address`, `user`
  - Password: `password` (optional, can be empty)
  - Port: `port` (default 22)

**No Web API Authentication:**
- Web API is unauthenticated (designed for private/trusted networks)
- HTTP server listens on `0.0.0.0:port` (configurable port)

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracking service
- All errors logged locally

**Logs:**
- **File-based logging:** Rotating file handler
  - Main service log: `seedsync.log` (in `--logdir`)
  - Web access log: `seedsync_web_access.log`
  - Log level: Configurable via `[General]` debug setting
  - Format: Timestamp, level, module, message
- **Console logging:** Limited to important messages (errors, startup)
- **Structured data:**
  - LFTP command output parsed in `src/python/lftp/job_status_parser.py`
  - Transfer status tracked via LFTP job status polling

## CI/CD & Deployment

**Hosting:**
- **GitHub Container Registry (GHCR):** ghcr.io/thejuran/seedsync
- **Docker Hub Alternative:** Not configured
- **Local registry:** Optional staging registry (localhost:5000 by default)

**CI Pipeline:**
- **GitHub Actions** (`.github/workflows/`)
  - Trigger: Push to master, pull requests, git tags v*
  - Python unit tests: `pytest` via Docker
  - Angular unit tests: `npm test` via Docker
  - E2E tests: `playwright test` via Docker
  - Build artifacts: Deb packages (amd64, arm64)
  - Container build: Docker Buildx (multi-arch)

**Docker Image Publishing:**
- **docker-publish.yml** - Automatic image push to GHCR
  - On master push: Tag `:dev`
  - On git tag `vX.Y.Z`: Tags `:X.Y.Z` and `:latest`
  - Authentication: GITHUB_TOKEN (built-in GitHub secret)
  - Registry login: `docker/login-action@v3`

**Release Artifacts:**
- Deb packages: Uploaded to GitHub Artifacts
- GitHub Releases: Created for git tags (action: softprops/action-gh-release)
- Version files updated before release:
  - `src/angular/package.json`
  - `src/python/pyproject.toml`
  - `src/debian/changelog`
  - `src/e2e/tests/about.page.spec.ts`

## Environment Configuration

**Required env vars:**
- `STAGING_REGISTRY` - Docker registry for staging (default: localhost:5000)
- `STAGING_VERSION` - Docker image version
- `RELEASE_REGISTRY` - Production registry (required for releases)
- `RELEASE_VERSION` - Release version tag (required for releases)
- `SEEDSYNC_DEB` - Path to deb package for E2E tests
- `SEEDSYNC_OS` - Target OS for deb tests (ubu2204, ubu2404)
- `SEEDSYNC_ARCH` - Target architecture (amd64, arm64)
- `APP_BASE_URL` - E2E test baseURL (default: http://myapp:8800)
- `CHROME_BIN` - Path to Chrome executable for Playwright

**Secrets location:**
- GitHub Secrets (CI/CD):
  - `GITHUB_TOKEN` - Built-in, for GHCR authentication
- Local configuration file: `settings.cfg`
  - Remote server credentials: `[Lftp]` section

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- LFTP at-exit commands: Configurable shell commands executed when LFTP job completes
  - Default: `kill all` (cleanup background jobs)
  - Configurable via LFTP settings

## Remote Server Communication

**SSH/SFTP Connection Details:**
- **Protocol:** SFTP over SSH (via lftp)
- **Connection settings:** Configured in `settings.cfg`
  - Host: `address` parameter
  - Port: `port` parameter (default 22)
  - User: `user` parameter
  - Password: `password` parameter
  - Base path: `remote_path` parameter
- **File operations:** SCP via SSH (in `src/python/ssh/sshcp.py`)
  - Delete operations via SSH rm
  - Copy operations via SCP
  - Host key verification: Disabled (auto-add to known hosts)

## Build & Deployment Integration

**Docker Multi-Architecture Build:**
- **Buildx driver:** docker-buildx (with network=host)
- **Platform support:** linux/amd64, linux/arm64
- **Build stages:**
  - `seedsync_build_scanfs_export` - Compile scanfs binary
  - `seedsync_build_angular_export` - Build Angular frontend
  - `seedsync_run_python_devenv` - Python development environment
  - `seedsync_run` - Final runtime image
  - `seedsync_test_e2e` - E2E test environment

**Registry Caching:**
- Docker layer caching via registry (BuildKit cache-from/cache-to)
- Cache location: `{REGISTRY}-build-scanfs:cache`, etc.
- Cache strategy: mode=max

**Base Images (from Dockerfiles):**
- Ubuntu-based for compilation and runtime
- Node.js image for frontend builds
- Python 3.11+ base images

---

*Integration audit: 2026-02-03*
