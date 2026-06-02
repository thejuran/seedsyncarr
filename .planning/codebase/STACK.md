# Technology Stack

**Analysis Date:** 2026-06-02

## Languages

**Primary:**
- Python `>=3.11,<3.13` - Backend daemon, controller, web server, LFTP/SSH orchestration. All source under `src/python/`.
- TypeScript `~6.0.3` - Angular SPA frontend. All source under `src/angular/src/`.

**Secondary:**
- Bash - Docker entrypoints and helper scripts (`src/docker/**/*.sh`, `src/docker/wait-for-it.sh`).
- SCSS/Sass `^1.100.0` - Angular component and global styles (`src/angular/src/styles.scss`).
- JavaScript (ESM) - Release-metadata tooling (`scripts/*.mjs`, root `package.json`).

## Runtime

**Environment:**
- Python 3.11 (production runtime container is `python:3.11-slim`; PyInstaller scanfs binary built on `python:3.11-slim-bullseye` for GLIBC 2.31 compat — see `src/docker/build/docker-image/Dockerfile`).
- Node.js 22 (Angular build + CI; `node:22-slim` build stage).
- Browser runtime for the Angular SPA (served as static HTML from the Python container on port 8800).

**Package Managers:**
- Python: Poetry (`src/python/poetry.lock`) — production install via `poetry install --only main`. `pyproject.toml` carries both a PEP 621 `[project]` table (hatchling build backend) and a `[tool.poetry]` table.
- Angular: npm (`src/angular/package-lock.json`).
- Root tooling: npm (`package-lock.json`) for release-metadata verifier scripts only.
- E2E: npm (`src/e2e/package-lock.json`).
- Lockfiles: present for all four manifests.

## Frameworks

**Backend Core:**
- Bottle `>=0.13.4` - WSGI web framework; `WebApp` subclasses `bottle.Bottle` in `src/python/web/web_app.py`.
- Paste `>=3.10.1` - WSGI server / multithreaded HTTP serving for Bottle.

**Frontend Core:**
- Angular `^21.2.14` - SPA framework (`@angular/core`, `@angular/common`, `@angular/router`, `@angular/forms`, `@angular/animations`, `@angular/cdk`, `@angular/platform-browser`).
- RxJS `^7.5.0` - Reactive streams for services and SSE handling.
- zone.js `^0.16.2` - Angular change detection.

**Testing:**
- pytest `>=9.0.3` with `pytest-timeout` `>=2.3.1` and `pytest-cov` `>=7.0.0` - Python unit + integration tests (`src/python/tests/`). `webtest` `>=3.0.7` and `testfixtures` `>=11.0.0` for web handler / fixture tests.
- Karma `^6.4.4` + Jasmine `^6.2.0` - Angular unit tests (`karma.conf.js`, `src/angular/src/app/tests/`).
- Playwright `^1.60.0` (`@playwright/test`) - E2E tests, two suites: `src/e2e/` (primary) and `src/angular/playwright.config.ts`.
- Node built-in test runner (`node --test`) - Release-metadata verifier tests (`scripts/verify-release-metadata.test.mjs`).

**Build/Dev:**
- Angular CLI / `@angular/build` `^21.2.12` - esbuild-based application builder (`ng build --configuration=production`).
- PyInstaller `>=6.0.0` - Freezes `scan_fs.py` into the `scanfs` binary shipped on the remote server (`src/pyinstaller_hooks/hook-patoolib.py`).
- ruff `>=0.4.0` - Python linter (`ruff check src/python/`; ruff cache `src/python/.ruff_cache/0.15.9`).
- ESLint `^10.4.0` + `typescript-eslint` `^8.60.0` - Angular linting (`src/angular/eslint.config.js`).
- mkdocs `>=1.6.1` + mkdocs-material `>=9.7.1` - Documentation site (`src/python/mkdocs.yml`, `src/python/site/`).
- Make - Top-level build/test orchestration (`Makefile`: `docker-image`, `run-tests-python`, `run-tests-angular`, `run-tests-e2e`).

## Key Dependencies

**Critical:**
- pexpect `>=4.9.0` - Drives the external `lftp` and `ssh`/`scp` CLIs via spawned pseudo-terminals (`src/python/lftp/lftp.py`, `src/python/ssh/sshcp.py`). Core to the sync engine.
- patool `>=4.0.3` - Archive extraction (rar/zip/etc.) in the extract controller (`src/python/controller/extract/`). Custom PyInstaller hook at `src/pyinstaller_hooks/hook-patoolib.py`.
- cryptography `>=44.0.0,<47` - Fernet symmetric encryption of secret config fields (`src/python/common/encryption.py`).
- requests `>=2.33.0` - Outbound HTTP to Sonarr/Radarr `/api/v3/system/status` for connection testing (`src/python/web/handler/config.py`).
- immutable `^5.1.5` (frontend) - Immutable.js data structures for model/file state in Angular services.

**Infrastructure:**
- pytz `>=2025.2` - Timezone handling.
- tblib `>=3.2.2` - Traceback serialization across process boundaries (multiprocessing logger).
- bootstrap `^5.3.3` + `@popperjs/core` `^2.11.8` - Frontend CSS framework and positioning.
- `@phosphor-icons/web` `^2.1.2` - Icon set.
- compare-versions `^6.1.1` - Frontend version comparison (update checks / about page).

**External CLI tools (not pip/npm — installed in runtime container):**
- `lftp` - File mirroring engine (apt-installed in `seedsyncarr_run_python_env` stage).
- `openssh-client` (`ssh`/`scp`) - Remote scan-script invocation and key auth.

## Configuration

**Application config:**
- INI-format `settings.cfg` in the config directory, parsed by `configparser` via `Config` (`src/python/common/config.py`). Sections: `General`, `Lftp`, `Controller`, `Web`, `AutoQueue`, `Sonarr`, `Radarr`, `AutoDelete`, `Encryption`.
- Secret fields (`webhook_secret`, `api_token`, `lftp.remote_password`, `sonarr.sonarr_api_key`, `radarr.radarr_api_key`) are Fernet-encrypted at rest when `[Encryption] enabled = true`. Key stored in `secrets.key` (0600, atomic create) alongside the config.
- Persisted state files in the config dir: `controller.persist`, `autoqueue.persist` (custom `Persist` serialization; corrupt files auto-backed-up to `*.bak`).
- CLI args (`src/python/seedsyncarr.py`): `-c/--config_dir` (required), `--logdir`, `-d/--debug`, `--exit`, `--html`, `--scanfs`. Legacy fallback to `~/.seedsync` if config dir missing.

**Frontend environment:**
- Angular environment files: `src/angular/src/environments/environment.ts`, `environment.prod.ts`, `environment.test.ts`.
- API calls and SSE use same-origin relative paths (`/server/...`); no separate API base URL is configured (`src/angular/src/app/services/base/stream-service.registry.ts`).

**Build config:**
- `src/python/pyproject.toml` - Python deps, pytest options (`timeout=60`, `cache_dir=/tmp/.pytest_cache`), coverage gate (`fail_under = 88`, branch coverage).
- `src/angular/angular.json`, `src/angular/tsconfig.json` - Angular build/TS config.
- `src/angular/eslint.config.js`, `src/angular/karma.conf.js`, `src/angular/playwright.config.ts` - Lint/test config.
- `src/docker/build/docker-image/Dockerfile` - Multi-stage build (Angular → scanfs PyInstaller → Python runtime).

**Secrets / env (existence only — contents never read):**
- `.gitleaks.toml` - Secret-scan config at repo root.
- AIDesigner skill references `AIDESIGNER_API_KEY` / `AIDESIGNER_MCP_ACCESS_TOKEN` env vars for the design tooling MCP server (not part of the app runtime).
- No `.env` file present in the repo.

## Platform Requirements

**Development:**
- Docker + Docker Buildx (all test targets run inside containers via `make`; `src/docker/test/`).
- Make, Node 22, Python 3.11–3.12, Poetry for local non-containerized work.
- QEMU for multi-arch builds (amd64 + arm64); note: local NAS deploy build env is blocked on QEMU per project memory.

**Production:**
- Single Docker image (published to `ghcr.io/<repo>`), `EXPOSE 8800`, runs `python /app/python/seedsyncarr.py` as entrypoint.
- Requires a reachable remote seedbox over SSH/SFTP (port 22 default) with the `scanfs` binary deployable there.
- Linux host assumed (POSIX file-permission semantics relied upon for `secrets.key`).

---

*Stack analysis: 2026-06-02*
