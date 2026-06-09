# Technology Stack

**Analysis Date:** 2026-06-09

## Languages

**Primary:**
- Python >=3.11,<3.13 - Backend daemon: controller, LFTP wrapper, SSH, web API (`src/python/`)
- TypeScript ~6.0.3 - Angular frontend (`src/angular/src/`) and Playwright E2E tests (`src/e2e/tests/`)

**Secondary:**
- Bash - Docker entrypoint and build scripts (`src/docker/build/docker-image/entrypoint.sh`, `Makefile` targets)
- JavaScript (Node ESM) - Release metadata verifier (`scripts/verify-release-metadata.mjs`)
- SCSS - Angular styles (`src/angular/src/styles.scss`)

## Runtime

**Environment:**
- Python 3.11 in production (Docker base `python:3.11-slim`, Debian 12 Bookworm — `src/docker/build/docker-image/Dockerfile`)
- Python 3.12 used in CI for lint and PyPI build (`.github/workflows/ci.yml`)
- Node.js 22 for Angular build/test and release scripts (Docker stage `node:22-slim`; CI `setup-node` with `node-version: "22"`)
- Docker container is the deployment unit; app served on port 8800

**Package Manager:**
- Python: Poetry (Docker/dev install path) + Hatchling build backend (PyPI publish) — dual config in `src/python/pyproject.toml`
- Lockfile: `src/python/poetry.lock` present
- Node: npm
- Lockfiles: `src/angular/package-lock.json`, `src/e2e/package-lock.json`, root `package-lock.json` all present

## Frameworks

**Core:**
- Bottle >=0.13.4 - WSGI web framework for the REST/SSE API (`src/python/web/web_app.py`)
- Paste >=3.10.1 - Threaded WSGI HTTP server hosting Bottle (`src/python/web/web_app_job.py` uses `paste.httpserver` + `TransLogger`)
- Angular ^22.0.0 - SPA frontend (`src/angular/`), built with `@angular/build:application` (esbuild) per `src/angular/angular.json`
- RxJS ^7.5.0, Immutable.js ^5.1.6, Bootstrap ^5.3.3, @phosphor-icons/web ^2.1.2 - frontend runtime libraries

**Testing:**
- pytest >=9.0.3 with pytest-timeout, pytest-cov - Python tests (`src/python/tests/`); coverage `fail_under = 88` (branch coverage) in `src/python/pyproject.toml`
- testfixtures, WebTest - Python test helpers (WSGI endpoint testing)
- Jasmine ^6.2.0 + Karma ^6.4.4 - Angular unit tests (`src/angular/karma.conf.js`)
- Playwright ^1.60.0 - E2E tests against the Docker image (`src/e2e/`, `src/angular/playwright.config.ts`, `src/e2e/playwright.config.ts`)
- node:test - Release metadata verifier tests (`scripts/verify-release-metadata.test.mjs`)

**Build/Dev:**
- Make - Top-level orchestration (`Makefile`: `docker-image`, `run-tests-python`, `run-tests-angular`, `run-tests-e2e`, `docker-image-release`)
- Docker Buildx multi-stage builds, multi-arch (amd64 + arm64 via QEMU) - `src/docker/build/docker-image/Dockerfile`
- PyInstaller >=6.0.0 - Builds the standalone `scanfs` remote-scan binary from `src/python/scan_fs.py` (hooks in `src/python/pyinstaller_hooks/`)
- Ruff >=0.4.0 - Python linting (CI runs `ruff check src/python/`)
- ESLint ^10 + typescript-eslint ^8 - Angular linting (`src/angular/eslint.config.js`, `npm run lint` with `--max-warnings 0`)
- Sass ^1.100.0 (Dart Sass) - style compilation
- MkDocs >=1.6.1 + mkdocs-material - documentation site (`src/python/mkdocs.yml`, content in `src/python/docs/`)

## Key Dependencies

**Critical (Python runtime):**
- `pexpect` >=4.9.0 - Drives the `lftp` and `ssh`/`scp` subprocesses interactively (`src/python/lftp/lftp.py`, `src/python/ssh/sshcp.py`)
- `cryptography` >=44.0.0,<47 - Fernet encryption of config secrets at rest (`src/python/common/encryption.py`; keyfile `secrets.key` in config dir)
- `requests` >=2.33.0 - Outbound Sonarr/Radarr connection tests (`src/python/web/handler/config.py`)
- `patool` >=4.0.3 - Archive extraction dispatcher (7z/unrar/bzip2 installed in Docker image)
- `tblib` >=3.2.2 - Traceback pickling across multiprocessing boundaries
- `pytz` >=2025.2 - Timezone handling

**Critical (frontend):**
- `immutable` ^5.1.6 - Immutable model/view state records
- `compare-versions` ^6.1.1 - New-release comparison in `src/angular/src/app/services/utils/version-check.service.ts`
- `zone.js` ^0.16.2 - Angular change detection

**Infrastructure (system binaries inside Docker image):**
- `lftp` - Core transfer engine (the product's whole purpose)
- `openssh-client` - Remote scan transport (`scp`/`ssh` shims in `/usr/local/sbin`)
- `gosu` - Privilege drop in entrypoint after PUID/PGID remap
- `libnss-wrapper` - Run-as-arbitrary-uid SSH fix (`src/docker/build/docker-image/run_as_user`)
- `p7zip`, `p7zip-full`, `unrar`, `bzip2` - Extraction backends for patool

**Security overrides (npm `overrides` blocks):**
- `src/angular/package.json`: `ip-address`, `undici`, `lodash`, `vite`, `hono`, `@hono/node-server`
- Root `package.json`: `basic-ftp` ^5.3.0

## Configuration

**Environment:**
- App config is file-based, not env-based: `settings.cfg` in the config dir (default `/config` in Docker), loaded by `src/python/common/config.py` via `src/python/common/persist.py`
- Config sections: General, Lftp, Controller, Web, AutoQueue, Sonarr, Radarr, AutoDelete (`src/python/common/config.py` `Config` class)
- Secret-marked config fields (webhook_secret, api_token, remote_password, sonarr_api_key, radarr_api_key) encrypted at rest with Fernet; key auto-generated at `<config>/secrets.key` with 0600 perms (`src/python/common/encryption.py`)
- Persisted state files: `autoqueue.persist`, `controller.persist` (`src/python/seedsyncarr.py`)
- Docker env vars: `PUID`, `PGID` (user remap), `ENTRYPOINT_CHOWN_RECURSIVE` (deep chown opt-in) — `src/docker/build/docker-image/entrypoint.sh`
- CLI args: `-c <config_dir>`, `--html <path>`, `--scanfs <path>` (`src/python/seedsyncarr.py`)

**Build:**
- `src/python/pyproject.toml` - Python deps, pytest, coverage, hatch/poetry config
- `src/angular/angular.json` - Angular application builder config
- `src/angular/tsconfig.json`, `src/e2e/tsconfig.json` - TypeScript configs
- `src/angular/eslint.config.js` - flat ESLint config
- `src/angular/karma.conf.js` - Karma config
- `src/angular/playwright.config.ts`, `src/e2e/playwright.config.ts` - Playwright configs
- `Makefile` - build/test entry points; Docker test images under `src/docker/test/`
- `src/python/mkdocs.yml` - docs site config

## Platform Requirements

**Development:**
- Docker + Buildx (Python tests run inside Docker via `make run-tests-python`)
- Node 22 + npm for Angular work
- Python 3.11/3.12 + Poetry for local Python work

**Production:**
- Docker (Linux, amd64 or arm64). Image published to `ghcr.io/thejuran/seedsyncarr` (`:latest`, `:dev`, `:vX.Y.Z`)
- Also published to PyPI as `seedsyncarr` (console script `seedsyncarr`) via CI on version tags
- Container mounts: `/config` (settings + state), `/downloads` (synced files); exposes port 8800
- Remote side requires SSH access; `scanfs` PyInstaller binary built against GLIBC 2.31 (Debian bullseye) for older remote-host compatibility

## Project Skills

- `.claude/skills/aidesigner-frontend/SKILL.md` (mirrored at `.agents/skills/aidesigner-frontend/`) - AIDesigner design-to-frontend workflow skill. Mandates porting AIDesigner HTML artifacts into the repo's real Angular primitives/tokens rather than shipping raw HTML; root devDependency `puppeteer` ^25.1.0 supports its clone-QA screenshot loop.

---

*Stack analysis: 2026-06-09*
