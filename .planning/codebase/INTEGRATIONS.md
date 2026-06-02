# External Integrations

**Analysis Date:** 2026-06-02

## APIs & External Services

**Media managers (*arr):**
- Sonarr - TV import detection and connection health checks.
  - SDK/Client: `requests` (`src/python/web/handler/config.py`).
  - Endpoint called: `GET {sonarr_url}/api/v3/system/status` with 10s timeout, `allow_redirects=False`.
  - Auth: `X-Api-Key` header; key from `config.sonarr.sonarr_api_key` (secret, encryptable at rest).
  - Config: `[Sonarr] enabled / sonarr_url / sonarr_api_key` in `settings.cfg`.
  - Test route: `POST /server/config/sonarr/test-connection` (rate-limited 5/60s).
- Radarr - Movie import detection and connection health checks.
  - Same client/endpoint shape as Sonarr (`_test_arr_connection` in `src/python/web/handler/config.py`).
  - Auth: `X-Api-Key` header; key from `config.radarr.radarr_api_key` (secret).
  - Config: `[Radarr] enabled / radarr_url / radarr_api_key`.
  - Test route: `POST /server/config/radarr/test-connection` (rate-limited 5/60s).
- SSRF protection: `ConfigHandler._validate_url()` rejects non-http(s) schemes and URLs resolving to private/loopback/reserved/link-local IPs before any outbound request. Known limitation documented in code: DNS-rebinding (TOCTOU) not mitigated (out of scope for a homelab tool).

**Remote seedbox (SSH/SFTP via CLI):**
- `lftp` - Primary file mirroring engine, driven via `pexpect` (`src/python/lftp/lftp.py`). Uses SFTP transport, configurable parallelism, connection limits, rate limiting, and temp-file usage.
- `ssh`/`scp` (`openssh-client`) - Deploys/invokes the remote `scanfs` script and transfers status (`src/python/ssh/sshcp.py`). Distinguishes transient (`Timed out`, `Connection refused`) vs permanent (`Incorrect password`, `Remote host key has changed`, `Bad hostname`) error classes for retry decisions.
- Connection config: `[Lftp] remote_address / remote_port (default 22) / remote_username / remote_password (secret) / use_ssh_key / remote_path / local_path`.

## Data Storage

**Databases:**
- None. No SQL/NoSQL database, ORM, or DB client present.

**File Storage:**
- Local filesystem only. State persisted as flat files in the config directory:
  - `settings.cfg` - INI config (`src/python/common/config.py`).
  - `controller.persist`, `autoqueue.persist` - Custom-serialized app state (`src/python/common/persist.py`).
  - `secrets.key` - Fernet encryption key (0600).
  - Corrupt persist/config files are auto-backed-up to `*.N.bak`.
- Downloaded files land in `config.lftp.local_path`; archives extracted to `config.controller.extract_path` (or local path) by `patool`.

**Caching:**
- None at the application layer. (pytest cache redirected to `/tmp/.pytest_cache`; Angular build cache under `src/angular/.angular/cache/`.)

## Authentication & Identity

**API auth (inbound):**
- Custom Bearer-token scheme. All `/server/*` endpoints require `Authorization: Bearer <api_token>` when `config.general.api_token` is set; validated in the `before_request` hook of `src/python/web/web_app.py`.
  - Exempt paths: `/server/stream` (SSE — EventSource cannot send headers), `/server/status` (health check).
  - Exempt prefixes: `/server/webhook/` (uses HMAC instead).
- Host-header validation against `config.general.allowed_hostname` in the same hook (anti-DNS-rebinding for the UI).
- If no API token is configured, all requests are accepted — startup emits explicit security warnings (`Seedsyncarr._emit_startup_warnings` in `src/python/seedsyncarr.py`).

**Webhook auth (inbound):**
- HMAC-SHA256 over the raw request body, compared constant-time against the `X-Webhook-Signature` header (`WebhookHandler._verify_hmac` in `src/python/web/handler/webhook.py`).
- Secret: `config.general.webhook_secret`. When empty, verification is skipped (backward compat). When `config.general.webhook_require_secret` is true but no secret is set, webhooks fail closed with HTTP 503.

**Encryption at rest:**
- Fernet (symmetric) encryption of secret config fields when `[Encryption] enabled = true` (`src/python/common/encryption.py`). Plaintext secrets are transparently re-encrypted in place on startup.

**No third-party identity provider** (no OAuth/OIDC/SSO for the app itself).

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry/Rollbar/Datadog integration.

**Logs:**
- Python `logging` with `RotatingFileHandler` (max size + backup count from `Constants`) when `--logdir` is set, else stdout (`Seedsyncarr._create_logger`). Separate main log and web-access log.
- Log-injection (CWE-117) defense: webhook-supplied values sanitized via `sanitize_log_value` before logging (`src/python/controller/webhook_manager.py`).
- Frontend log stream surfaced to the UI via SSE (`/server/stream`, `LogStreamHandler`).

**Health/status:**
- `GET /server/status` (auth-exempt) and SSE status stream (`StatusStreamHandler`, `HeartbeatStreamHandler` pinging every 15s).

## CI/CD & Deployment

**Hosting:**
- Self-hosted Docker container. Image published to GitHub Container Registry (`ghcr.io/<repo>`).

**CI Pipeline:**
- GitHub Actions, single workflow `.github/workflows/ci.yml`. Triggers: push to `main`, semver tags `v[0-9]+.[0-9]+.[0-9]+`, PRs to `main`, manual dispatch.
- Jobs: release-metadata verifier tests (`npm run test:release-metadata`), Python unit tests (`make run-tests-python`), Angular unit tests (`make run-tests-angular`), Python lint (`ruff check src/python/`), Angular lint (`npm run lint`), Docker image build (`make docker-image`), and matrix E2E tests on the built image per arch (`make run-tests-e2e`).
- Registry auth: `docker login ghcr.io` using `secrets.GITHUB_TOKEN`. Multi-arch via QEMU + Buildx.
- Note: CI runs `ruff` as a separate gate from pytest — Python phases must pass whole-tree ruff.

## Environment Configuration

**Required app config (in `settings.cfg`, not env vars):**
- `[Lftp]` remote connection: `remote_address`, `remote_port`, `remote_username`, `remote_password` (or `use_ssh_key`), `remote_path`, `local_path`.
- `[Web] port` (default 8800).
- Optional integrations: `[Sonarr]`, `[Radarr]`, `[AutoDelete]`, `[AutoQueue]`, `[Encryption]`.

**CI/deploy env vars:**
- `GITHUB_TOKEN`, `STAGING_REGISTRY`, `STAGING_VERSION` (GitHub Actions).

**Secrets location:**
- App secrets live in `settings.cfg` (Fernet-encrypted when enabled, key in `secrets.key`).
- No `.env` file in repo. `.gitleaks.toml` configures secret scanning.
- AIDesigner design tooling (dev-only, not app runtime) references `AIDESIGNER_API_KEY` / `AIDESIGNER_MCP_ACCESS_TOKEN`; the `aidesigner` MCP server is configured in `.mcp.json` (http transport, OAuth-backed).

## Webhooks & Callbacks

**Incoming:**
- `POST /server/webhook/sonarr` - Sonarr import events; extracts file title, enqueues via `WebhookManager.enqueue_import` (`src/python/web/handler/webhook.py`).
- `POST /server/webhook/radarr` - Radarr import events; same flow.
- Both: HMAC-verified (when secret set), rate-limited 60/60s, 1 MB max body, JSON-parsed. Imported names matched case-insensitively against the SeedSyncarr model in the controller thread (`WebhookManager.process`).

**Outgoing:**
- Only the Sonarr/Radarr `/api/v3/system/status` connection-test calls (no event push-out, no other outbound callbacks).

**Server-Sent Events (streaming, outbound to UI):**
- `GET /server/stream` - Multiplexed SSE for model, status, log, and heartbeat streams (`src/python/web/web_app.py`, `src/python/web/handler/stream_*.py`). Consumed via `EventSource` in `src/angular/src/app/services/base/stream-service.registry.ts`.

---

*Integration audit: 2026-06-02*
