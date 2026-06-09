# External Integrations

**Analysis Date:** 2026-06-09

## APIs & External Services

**Media managers (*arr ecosystem):**
- Sonarr - Inbound webhook source + outbound connection test
  - Inbound: `POST /server/webhook/sonarr` handled by `src/python/web/handler/webhook.py` (`WebhookHandler`)
  - Outbound: `GET {sonarr_url}/api/v3/system/status` with `X-Api-Key` header for connection testing (`src/python/web/handler/config.py` `_test_arr_connection`, 10s timeout, redirects disabled, SSRF URL validation)
  - Auth: `sonarr.sonarr_api_key` config field (secret, Fernet-encrypted at rest)
- Radarr - Same pattern as Sonarr
  - Inbound: `POST /server/webhook/radarr` (`src/python/web/handler/webhook.py`)
  - Outbound: `GET {radarr_url}/api/v3/system/status` (`src/python/web/handler/config.py`)
  - Auth: `radarr.radarr_api_key` config field (secret)

**Remote seedbox/server (core integration):**
- SSH/SCP - Remote file scanning transport
  - Client: `pexpect`-driven `ssh`/`scp` (`src/python/ssh/sshcp.py`, 180s timeout, transient vs permanent error classification)
  - The `scanfs` PyInstaller binary (`src/python/scan_fs.py`) is copied to the remote host and executed over SSH to enumerate remote files
  - Auth: password (`lftp.remote_password`, encrypted at rest) or SSH key (`lftp.use_ssh_key`); host keys `StrictHostKeyChecking accept-new` seeded by `src/docker/build/docker-image/entrypoint.sh` and Dockerfile
- LFTP - File transfer engine
  - Client: `pexpect` wrapper around system `lftp` binary (`src/python/lftp/lftp.py`, status parsing in `src/python/lftp/job_status_parser.py`)
  - Config: `lftp.*` section in `settings.cfg` (remote_address, remote_port, parallelism/connection limits, rate_limit)

**GitHub Releases API (frontend, client-side):**
- `https://api.github.com/repos/thejuran/seedsyncarr/releases/latest` - New-version check from the browser (`src/angular/src/app/services/utils/version-check.service.ts`, compared with `compare-versions`)
- Auth: none (public API)

## Data Storage

**Databases:**
- None. No SQL/NoSQL database.
- State persistence is flat-file under the config dir (default `/config`):
  - `settings.cfg` - config (`src/python/common/config.py` via `src/python/common/persist.py`)
  - `controller.persist` - downloaded/extracted file sets (`src/python/controller/controller_persist.py`)
  - `autoqueue.persist` - auto-queue patterns (`src/python/controller/auto_queue.py`)
  - `secrets.key` - Fernet key, 0600 perms (`src/python/common/encryption.py`)

**File Storage:**
- Local filesystem only: `/downloads` (synced files) and optional extract path (`controller.extract_path`); remote filesystem reached via SSH/LFTP

**Caching:**
- None (in-process memory only; `src/python/controller/memory_monitor.py` watches process memory)

## Authentication & Identity

**Auth Provider:**
- Custom, config-driven (no external IdP):
  - Optional Bearer token on `/server/*` API routes: `general.api_token`, constant-time compare via `hmac.compare_digest` (`src/python/web/web_app.py`)
  - Exempt paths: `/server/stream` (SSE cannot send headers), `/server/status` (health check), `/server/webhook/*` (HMAC instead) — listed in `src/python/web/web_app.py`
  - Optional Host-header allowlist: `general.allowed_hostname` (DNS-rebinding defense, `src/python/web/web_app.py`)
  - Webhook HMAC-SHA256: `general.webhook_secret` verified against `X-Webhook-Signature` header, constant-time compare (`src/python/web/handler/webhook.py` `_verify_hmac`); `general.webhook_require_secret` fail-closed mode returns 503 when on with no secret set
  - Rate limiting: in-process token budget per route, e.g. 60 req/60s on webhooks and config set, 5 req/60s on *arr connection tests (`src/python/web/rate_limit.py`)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry or similar)

**Logs:**
- Python `logging` with `RotatingFileHandler` to the config/log dir (`src/python/seedsyncarr.py`); multiprocessing-aware logger in `src/python/common/multiprocessing_logger.py`
- HTTP access logs via Paste `TransLogger` (`src/python/web/web_app_job.py`)
- Log streaming to the UI over SSE: `/server/stream` aggregate stream plus handlers in `src/python/web/handler/stream_log.py`, `stream_model.py`, `stream_status.py`, `stream_heartbeat.py`
- Webhook-supplied values sanitized before logging (CWE-117 guard, `src/python/controller/webhook_manager.py`)

## CI/CD & Deployment

**Hosting:**
- Self-hosted Docker (user's NAS or any Docker host). Image: `ghcr.io/thejuran/seedsyncarr`
- Docs site on GitHub Pages (mkdocs-material build, deployed by `peaceiris/actions-gh-pages` in CI)

**CI Pipeline:**
- GitHub Actions: `.github/workflows/ci.yml`
  - Gates: Node release-metadata tests, Python unit tests (in Docker, with GHCR build cache), Angular unit tests, `ruff check src/python/` (separate lint gate), Angular ESLint
  - Build: multi-arch Docker image via Buildx/QEMU, staged to `ghcr.io/<repo>` with run-number tags
  - E2E: Playwright against the built image; amd64 on PRs, amd64+arm64 on main/tags (arm64 on `ubuntu-24.04-arm` runner)
  - Publish on `v*` tags: GHCR `:vX.Y.Z` + `:latest`, GitHub Release (gh CLI + `release-notes.md`), PyPI (trusted publishing via `id-token: write`, `pypa/gh-action-pypi-publish`)
  - Publish on main: GHCR `:dev` tag, docs to GitHub Pages
  - Release metadata guard: `scripts/verify-release-metadata.mjs` checks version consistency against the tag

## Environment Configuration

**Required env vars:**
- None required by the Python app itself (config is file-based in `/config/settings.cfg`)
- Docker runtime (optional): `PUID`, `PGID` (default 1000/1000), `ENTRYPOINT_CHOWN_RECURSIVE` (`src/docker/build/docker-image/entrypoint.sh`)
- CI: `GITHUB_TOKEN` (GHCR login, release creation); PyPI uses OIDC trusted publishing (no stored token)

**Secrets location:**
- App secrets live in `/config/settings.cfg`, encrypted with the Fernet key at `/config/secrets.key` (`src/python/common/encryption.py`). Secret fields: `general.webhook_secret`, `general.api_token`, `lftp.remote_password`, `sonarr.sonarr_api_key`, `radarr.radarr_api_key` (marked `secret=True` in `src/python/common/config.py`)
- No `.env` files in the repo

## Webhooks & Callbacks

**Incoming:**
- `POST /server/webhook/sonarr` and `POST /server/webhook/radarr` (`src/python/web/handler/webhook.py`)
  - Processes `eventType: Download` (import) events; responds 200 to `Test` events
  - Title extraction fallback chain: `episodeFile.sourcePath`/`movieFile.sourcePath` basename → `release.releaseTitle` → `series.title`/`movie.title`
  - Protections: 1 MB body cap (413), optional HMAC-SHA256 signature (401), fail-closed 503 mode, 60 req/60s rate limit (429)
  - Downstream: `WebhookManager.enqueue_import` queues the title; controller thread matches it against the model and feeds the auto-delete lifecycle (`src/python/controller/webhook_manager.py`, `src/python/controller/auto_delete_manager.py` — pack-guard BFS + coverage checks, `dry_run` and `delay_seconds` config in `autodelete` section)

**Outgoing:**
- None. SeedSyncarr does not push webhooks; outbound HTTP is limited to the Sonarr/Radarr connection-test endpoint above.

**Server-push to UI:**
- SSE stream at `GET /server/stream` (model, status, log records, heartbeat) consumed by Angular `EventSource` services (`src/angular/src/app/services/base/stream-service.registry.ts`)

---

*Integration audit: 2026-06-09*
