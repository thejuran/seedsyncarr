# External Integrations

**Analysis Date:** 2026-05-26

SeedSyncarr is a self-hosted homelab tool. Its integrations are: (1) a remote SSH/SFTP seedbox it pulls files from, (2) optional Sonarr/Radarr media managers it both posts to (test connection) and receives webhooks from, and (3) a periodic GitHub releases poll from the Angular UI for update notifications. There are no third-party SaaS dependencies, no cloud databases, and no telemetry.

## APIs & External Services

**Media managers (outbound + inbound):**
- **Sonarr** — TV show automation
  - Outbound: connection test via `GET <sonarr_url>/api/v3/system/status` with `X-Api-Key` header. `src/python/web/handler/config.py:131-144`
  - Inbound: receives webhooks at `POST /server/webhook/sonarr`. Handler extracts file name from `episodeFile.sourcePath` → `release.releaseTitle` → `series.title` (fallback chain). `src/python/web/handler/webhook.py:131-161`
  - SDK/Client: plain `requests` library, no Sonarr SDK.
  - Auth (outbound): `X-Api-Key` header — value stored in `[Sonarr] sonarr_api_key` (Fernet-encrypted when encryption is enabled).
  - Event types accepted (inbound): `Test`, `Download` (others are 200-OK no-op).

- **Radarr** — movie automation
  - Outbound: connection test via `GET <radarr_url>/api/v3/system/status` with `X-Api-Key` header. `src/python/web/handler/config.py:185-189`
  - Inbound: receives webhooks at `POST /server/webhook/radarr`. Handler extracts file name from `movieFile.sourcePath` → `release.releaseTitle` → `movie.title`. `src/python/web/handler/webhook.py:163-193`
  - Auth: `X-Api-Key` header — value stored in `[Radarr] radarr_api_key` (Fernet-encrypted when encryption is enabled).

- **GitHub releases API** — update notifications
  - Outbound: `GET https://api.github.com/repos/thejuran/seedsyncarr/releases/latest`. `src/angular/src/app/services/utils/version-check.service.ts:23`
  - Called from the Angular SPA on startup via `VersionCheckService`; compares `tag_name` against `APP_VERSION` from `src/angular/src/app/common/version.ts` using `compare-versions`.
  - No auth; unauthenticated public endpoint.
  - CSP whitelist: `connect-src 'self' https://api.github.com` in `src/python/web/web_app.py:158`.

**SSRF protection on outbound calls:** `ConfigHandler._validate_url` in `src/python/web/handler/config.py:56-85` resolves hostnames via `socket.getaddrinfo` and rejects private/loopback/reserved/link-local IPs before any `requests.get` call. Known TOCTOU gap on DNS rebinding is documented in code.

## Data Storage

**Databases:**
- None. There is no SQL/NoSQL database.

**File Storage:**
- Local filesystem only. Two key locations:
  - `<config_dir>` (default `/config` in Docker, `~/.seedsyncarr` outside) — INI config + `.persist` state files + Fernet keyfile.
  - `<local_path>` — destination for synced files (configurable in `[Lftp] local_path`; mounted at `/downloads` in Docker).
- Remote SFTP seedbox — read-only source for files (plus uploading the `scanfs` binary via SCP).

**Persist format:** Hand-rolled `Persist` base class in `src/python/common/persist.py` serializing to INI / JSON-ish on disk. Each persist class implements `from_str`/`to_str`.

**Caching:**
- In-process only: `WebApp._index_html_template` caches the HTML shell, Angular HTTP `shareReplay(1)` caches REST responses per-call.
- LFTP-side: `mirror -c` and `pget -c` use LFTP's own resume/segment cache.

## Authentication & Identity

**Auth Provider:**
- No external identity provider (no OAuth, no LDAP). Single-tenant, single-user homelab tool.

**API authentication (outbound to seedbox):**
- SSH password or SSH key (`use_ssh_key` flag in `[Lftp]`). `src/python/ssh/sshcp.py:60-67` switches between `PasswordAuthentication=no` (key) and `PubkeyAuthentication=no` (password). `StrictHostKeyChecking=accept-new` is enforced — changed host keys cause an explicit error suggesting MITM.

**API authentication (inbound, `/server/*`):**
- Bearer token. Set via `[General] api_token`; clients must send `Authorization: Bearer <token>`. Constant-time compare via `hmac.compare_digest` in `src/python/web/web_app.py:136`.
- Token surfaced to the SPA via a server-injected `<meta name="api-token" content="...">` tag in `index.html`; `src/angular/src/app/services/utils/auth.interceptor.ts:24-32` reads it once and adds the header to every `HttpClient` request.
- Backward-compat: empty `api_token` = unauthenticated access (logged as a `WARNING` on startup).
- Exempt paths: `/server/stream` (SSE — EventSource can't send custom headers), `/server/status` (health probe), and `/server/webhook/*` (use HMAC instead). `src/python/web/web_app.py:59-65`

**Webhook authentication (inbound):**
- HMAC-SHA256 over the raw request body, signature delivered in `X-Webhook-Signature` header. Compared with `hmac.compare_digest`. `src/python/web/handler/webhook.py:43-77`
- Secret stored in `[General] webhook_secret` (Fernet-encrypted when encryption is enabled). Empty secret skips verification (logged as a startup WARNING).

**Host header validation:**
- Optional Host allowlist via `[General] allowed_hostname`. When set, only `localhost`, `127.0.0.1`, `[::1]`, and the configured hostname are accepted on `/server/*`. `src/python/web/web_app.py:97-110`

**Secrets-at-rest encryption:**
- Fernet (`cryptography` library) symmetric encryption of 5 fields (`webhook_secret`, `api_token`, `lftp.remote_password`, `sonarr.sonarr_api_key`, `radarr.radarr_api_key`) when `[Encryption] enabled = true`. Keyfile auto-created at `<config_dir>/secrets.key` with `O_EXCL | 0600`. `src/python/common/encryption.py:48-80`

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry / Rollbar / Datadog / etc. Errors are logged locally only.

**Logs:**
- Python `logging` module. Main service log = `seedsyncarr.log`, web access log = `web_access.log`. Rotating file handler when `--logdir` is set; otherwise stdout. `src/python/seedsyncarr.py:278-302`
- Rotation: `MAX_LOG_SIZE_IN_BYTES = 10 MB`, `LOG_BACKUP_COUNT = 10`. `src/python/common/constants.py:7-8`
- Log injection mitigation: webhook-supplied strings have `\n` / `\r` escaped before being logged. `src/python/controller/webhook_manager.py:37`
- Browser logs streamed live to the UI via SSE (`LogStreamHandler` on `/server/stream`).

**Health check:**
- `GET /server/status` is auth-exempt and returns a JSON status payload (`src/python/web/handler/status.py`). Used by Docker healthchecks and Playwright e2e harness.

**Metrics / tracing:**
- None.

## CI/CD & Deployment

**Hosting:**
- Self-hosted (user runs their own Docker container or pip-installed daemon). No managed hosting.

**Container Registry:**
- GitHub Container Registry: `ghcr.io/thejuran/seedsyncarr`. Image label `org.opencontainers.image.source` set in `src/docker/build/docker-image/Dockerfile:122`.
- Tags: `latest`, `v<x.y.z>` (semver releases), `dev` (head of `main`).

**Python Package:**
- PyPI: `seedsyncarr` package, published from `src/python/` via `pypa/gh-action-pypi-publish@v1` with OIDC trusted publishing (`id-token: write`). `.github/workflows/ci.yml:303-331`

**CI Pipeline:**
- GitHub Actions, `.github/workflows/ci.yml`. Jobs:
  - `unittests-release-metadata` (Node 22, `npm run test:release-metadata`)
  - `unittests-python` (Docker-based, via `make run-tests-python`)
  - `unittests-angular` (Docker-based, via `make run-tests-angular`)
  - `lint-python` (`ruff check src/python/`)
  - `lint-angular` (`npm run lint`)
  - `build-docker-image` (multi-arch buildx, push to GHCR cache)
  - `e2etests-docker-image` (matrix: amd64 always, arm64 only on main/tag pushes; Playwright e2e)
  - `verify-release-metadata` (tag-only)
  - `publish-docker-image`, `publish-github-release`, `publish-pypi`, `publish-docker-image-dev`, `publish-docs`
- Action versions are pinned by SHA (security best practice).
- GitHub Pages docs site published from `src/python/site/` via `peaceiris/actions-gh-pages@v4`.

**Dependabot:**
- Configured in `.github/dependabot.yml` (auto PR opens for npm, pip, GitHub Actions updates).

**Secret scanning:**
- `.gitleaks.toml` present at repo root.

## Environment Configuration

**Required env vars:**
- None at runtime. All configuration lives in `settings.cfg`.
- CI uses repo secrets: `GITHUB_TOKEN` (auto-provisioned by Actions) — for GHCR push, Pages deploy, and release creation.
- PyPI publish uses OIDC trusted publishing (no token secret).

**Secrets location:**
- On disk: `<config_dir>/settings.cfg` (Fernet-encrypted fields when `[Encryption] enabled = true`), with key at `<config_dir>/secrets.key` (0600).
- In CI: GitHub Actions Secrets / Repository OIDC.
- Repository never contains plaintext secrets (`.gitleaks.toml` guards against accidental commits).

## Webhooks & Callbacks

**Incoming:**
- `POST /server/webhook/sonarr` — Sonarr "On Import" connect events. Body: standard Sonarr webhook JSON. Handled by `WebhookHandler.__handle_sonarr_webhook` in `src/python/web/handler/webhook.py:35-37`.
- `POST /server/webhook/radarr` — Radarr "On Import" connect events. Body: standard Radarr webhook JSON. Handled by `WebhookHandler.__handle_radarr_webhook` in `src/python/web/handler/webhook.py:39-41`.
- Both endpoints:
  - Require HMAC-SHA256 in `X-Webhook-Signature` when `[General] webhook_secret` is set.
  - Cap body at 1 MB (`_WEBHOOK_MAX_BODY_BYTES = 1_048_576`) — returns 413 above limit. `src/python/web/handler/webhook.py:17`
  - Accept event types `Test` and `Download`; everything else returns 200 no-op.
  - Are auth-exempt from the Bearer-token middleware (HMAC is the auth path).

**Outgoing:**
- None. SeedSyncarr does not call Sonarr/Radarr to trigger imports — Sonarr/Radarr poll their own libraries after webhook receipt, or pull state. The only outbound HTTP to Sonarr/Radarr is the user-initiated "Test connection" button (`/server/config/sonarr/test-connection`, `/server/config/radarr/test-connection`).

## Server-Sent Events (SSE)

**Stream endpoint:** `GET /server/stream` (auth-exempt, EventSource limitation).
- Implemented in `src/python/web/web_app.py:248-297` as a generator yielding multiple multiplexed channels.
- Heartbeat ping every 15 s (`_HEARTBEAT_INTERVAL_IN_MS = 15000`).
- Channels registered via `IStreamHandler.register`:
  - `StatusStreamHandler` — server status JSON
  - `LogStreamHandler` — log records
  - `ModelStreamHandler` — file-model diffs
  - `HeartbeatStreamHandler` — connection keepalive
- Angular side: `StreamDispatchService` + `StreamServiceRegistry` in `src/angular/src/app/services/base/` consume the EventSource.

## Internal REST Endpoints (`/server/*`)

All require Bearer auth (when `api_token` is set) unless explicitly noted.

| Method | Path | Handler |
|--------|------|---------|
| GET | `/server/status` | `StatusHandler` (auth-exempt) |
| GET | `/server/config/get` | `ConfigHandler` |
| GET | `/server/config/set/<section>/<key>/<value>` | `ConfigHandler` (rate-limited 60/min) |
| GET | `/server/config/sonarr/test-connection` | `ConfigHandler` (rate-limited 5/min) |
| GET | `/server/config/radarr/test-connection` | `ConfigHandler` (rate-limited 5/min) |
| GET | `/server/autoqueue/get` | `AutoQueueHandler` |
| GET | `/server/autoqueue/add/<pattern>` | `AutoQueueHandler` |
| GET | `/server/autoqueue/remove/<pattern>` | `AutoQueueHandler` |
| POST | `/server/command/restart` | `ServerHandler` |
| POST | `/server/command/queue/<file_name>` | `ControllerHandler` |
| POST | `/server/command/stop/<file_name>` | `ControllerHandler` |
| POST | `/server/command/extract/<file_name>` | `ControllerHandler` |
| DELETE | `/server/command/delete_local/<file_name>` | `ControllerHandler` |
| DELETE | `/server/command/delete_remote/<file_name>` | `ControllerHandler` |
| POST | `/server/command/bulk` | `ControllerHandler` (rate-limited 10/min, max 1000 files) |
| POST | `/server/webhook/sonarr` | `WebhookHandler` (HMAC auth) |
| POST | `/server/webhook/radarr` | `WebhookHandler` (HMAC auth) |
| GET | `/server/stream` | SSE multiplex (auth-exempt) |

Route registration is centralized in `src/python/web/web_app_builder.py:37-62`.

## System Tool Dependencies

These are not Python/npm libraries but external binaries the app shells out to via `pexpect`/`subprocess`:

- `lftp` — `/usr/bin/lftp`, called by `src/python/lftp/lftp.py:62` via `pexpect.spawn`. Configured for SFTP.
- `ssh`, `scp` — OpenSSH client; called by `src/python/ssh/sshcp.py` via `pexpect.spawn`.
- `7z` / `7za` / `unrar` / `bzip2` — invoked by `patool` for archive extraction.
- `scanfs` — PyInstaller-bundled Python script (built from `src/python/scan_fs.py`) that runs on the remote seedbox to enumerate files; copied over via SCP before each scan.

---

*Integration audit: 2026-05-26*
