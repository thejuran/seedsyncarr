# Technology Stack

**Analysis Date:** 2026-05-26

SeedSyncarr is a multi-language monorepo. The Python backend daemon hosts a Bottle web server, drives LFTP/SSH to a remote seedbox, and serves a compiled Angular SPA. End-to-end and unit tests use Playwright and Karma respectively. The final artifact is a multi-arch Docker image published to GHCR.

## Languages

**Primary:**
- Python 3.11–3.12 — backend daemon, web API, LFTP/SSH orchestration. `src/python/`
- TypeScript ~6.0.3 — Angular SPA web UI. `src/angular/src/`

**Secondary:**
- Bash — Docker entrypoints, CI helper scripts. `src/docker/build/docker-image/setup_default_config.sh`, `src/docker/wait-for-it.sh`, `src/docker/test/e2e/run_make_target.sh`
- SCSS (Dart Sass ^1.99.0) — Angular component styles. `src/angular/src/styles.scss`
- JavaScript (ES) — root release-metadata scripts only. `scripts/verify-release-metadata.mjs`

## Runtime

**Environment:**
- Python 3.11 (production Docker image — `python:3.11-slim`). See `src/docker/build/docker-image/Dockerfile:75`
- Python 3.11 or 3.12 supported for pip-installed builds (`requires-python = ">=3.11,<3.13"` in `src/python/pyproject.toml`)
- Node.js 22 (build/test/CI) — `src/docker/build/docker-image/Dockerfile:8` uses `node:22-slim`; CI uses `actions/setup-node@v6.4.0` with `node-version: "22"`
- Browser runtime: Chromium-based (Karma + Playwright tests)

**Package Manager:**
- Python: Poetry (`src/python/poetry.lock`, lockfile present) — backend builds also install via Poetry inside Docker. PyPI publishes use `python -m build` against `src/python/pyproject.toml` (Hatchling build backend).
- Node.js (Angular): npm — `src/angular/package-lock.json` (lockfile present, 375 KB)
- Node.js (e2e): npm — `src/e2e/package-lock.json`
- Node.js (root): npm — `package-lock.json` (release-metadata verifier only)

## Frameworks

**Core (Backend):**
- bottle ^0.13.4 — WSGI web micro-framework. `src/python/web/web_app.py:50` subclasses `bottle.Bottle`.
- paste ^3.10.1 — WSGI server (`paste.httpserver`) and TransLogger access logging. `src/python/web/web_app_job.py:5`
- pexpect ^4.9.0 — drives the interactive `lftp` and `ssh`/`scp` child processes. `src/python/lftp/lftp.py:62`, `src/python/ssh/sshcp.py:74`
- patool ^4.0.3 — archive extraction (7z, RAR, ZIP, etc.). `src/python/controller/extract/`
- cryptography >=44.0.0,<47 — Fernet symmetric encryption of secrets in `settings.cfg`. `src/python/common/encryption.py:6`
- requests ^2.33.0 — Sonarr/Radarr API connection tests. `src/python/web/handler/config.py:7`
- tblib ^3.2.2 — propagates child-thread tracebacks across `Job` boundaries.
- pytz >=2025.2,<2027.0 — timezone-aware timestamp formatting.

**Core (Frontend):**
- Angular ^21.2.13 — full framework: `@angular/core`, `@angular/router`, `@angular/forms`, `@angular/common/http`, `@angular/animations`, `@angular/cdk`, `@angular/platform-browser`. `src/angular/package.json:14-23`
- RxJS ^7.5.0 — Observables for HTTP, SSE streams, and reactive state. Used everywhere in `src/angular/src/app/services/`
- Zone.js ^0.16.2 — Angular change detection.
- Bootstrap ^5.3.3 + `@popperjs/core` ^2.11.8 — CSS framework and tooltip engine.
- `@phosphor-icons/web` ^2.1.2 and `font-awesome` ^4.7.0 — icon fonts.
- Immutable ^5.1.5 — `Immutable.List` for route metadata, etc. `src/angular/src/app/routes.ts:3`
- compare-versions ^6.1.1 — semver comparison for update-check notifications. `src/angular/src/app/services/utils/version-check.service.ts:5`
- jquery ^4.0.0 — legacy DOM utility.
- css-element-queries ^1.1.1 — element resize observation.

**Testing:**
- pytest ^9.0.3 — Python unit tests. `pyproject.toml:[tool.pytest.ini_options]` sets `timeout = 60`, `cache_dir = "/tmp/.pytest_cache"`.
- pytest-cov ^7.1.0 — coverage; `fail_under = 84`, branch coverage on. `src/python/pyproject.toml:79-95`
- pytest-timeout ^2.3.1 — per-test timeout enforcement.
- testfixtures ^11.0.0, webtest ^3.0.7 — fixture helpers and WSGI test client.
- Karma ^6.4.4 + Jasmine ^6.2.0 — Angular unit tests. `src/angular/karma.conf.js`
- Playwright ^1.58.2 / `@playwright/test` ^1.60.0 — e2e tests in both `src/angular/e2e/` (component-level) and `src/e2e/tests/` (Dockerized end-to-end against the running image).
- puppeteer ^25.0.4 — root-level dev dep used by `scripts/verify-release-metadata.test.mjs`.

**Build/Dev:**
- `@angular/build` ^21.2.11 (`@angular/build:application` esbuild-based builder, AOT, `autoCsp: true`). `src/angular/angular.json:21`
- `@angular/cli` ^21.2.11
- TypeScript ~6.0.3, `module: ES2022`, `target: ES2022`, `moduleResolution: bundler`, `strict: true`. `src/angular/tsconfig.json`
- ESLint ^10.4.0 + `typescript-eslint` ^8.59.4 — `src/angular/eslint.config.js` (flat config)
- ruff >=0.4.0 (lint) — Python linting; CI installs ruff via pip and runs `ruff check src/python/`.
- PyInstaller ^6.19.0 — bundles `scan_fs.py` into a single-file `scanfs` binary used over SCP. `src/python/scan_fs.py`, `src/pyinstaller_hooks/`
- mkdocs ^1.6.1 + mkdocs-material ^9.7.6 — documentation site. `src/python/mkdocs.yml`
- Docker + Buildx + QEMU — multi-arch (linux/amd64, linux/arm64) image builds via `Makefile`.

## Key Dependencies

**Critical:**
- bottle — entire HTTP API surface depends on it; SSE streaming is implemented as a generator endpoint on this WSGI server.
- pexpect — only mechanism for talking to LFTP/SSH; tightly coupled to `lftp` CLI prompts and `ssh` interactive output.
- patool — required for archive auto-extract; transitively shells out to system `7z`, `unrar`, `bzip2`, `unzip`.
- cryptography (Fernet) — encrypts the 5 secret fields (`webhook_secret`, `api_token`, `lftp.remote_password`, `sonarr.sonarr_api_key`, `radarr.sonarr_api_key`) when `[Encryption].enabled = true`. Keyfile at `<config_dir>/secrets.key`, 0600 permissions enforced. `src/python/common/encryption.py`

**Infrastructure:**
- LFTP (system binary, `/usr/bin/lftp`) — SFTP transfers; installed in the Docker image via `apt-get install lftp`. Required by `Lftp.__init__` via `pexpect.spawn`.
- OpenSSH client (`ssh`, `scp`) — used to push the `scanfs` binary to the remote box and run remote shell commands. Installed via `apt-get install openssh-client`.
- p7zip / p7zip-full / unrar / bzip2 — archive extractors invoked by patool.
- libnss-wrapper — installed in image for non-root user juggling.

**Frontend ecosystem overrides (security pins):**
- `src/angular/package.json:63-70` pins: `ip-address ^10.2.0`, `undici ^7.24.0`, `lodash ^4.18.0`, `vite ^7.3.2`, `hono ^4.12.18`, `@hono/node-server ^1.19.13`.
- Root `package.json:10-12` pins `basic-ftp ^5.3.0` (transitive override).

## Configuration

**Environment:**
- The app is configured via an INI file at `<config_dir>/settings.cfg` (default `/config` inside Docker, `~/.seedsyncarr` outside). Parsed by `configparser` in `src/python/common/config.py:404`.
- No `.env` is read by the Python code. `os.environ`/`os.getenv` is not used in `src/python/` outside of test/CI scripts.
- Frontend reads a runtime API token from `<meta name="api-token" content="...">` injected server-side at `src/python/web/web_app.py:219-224`; the Angular `authInterceptor` reads it from the DOM. `src/angular/src/app/services/utils/auth.interceptor.ts:11-16`

**Config sections (in `settings.cfg`):**
- `[General]` — `debug`, `verbose`, `webhook_secret`, `api_token`, `allowed_hostname`
- `[Lftp]` — `remote_address`, `remote_username`, `remote_password`, `remote_port`, `remote_path`, `local_path`, `remote_path_to_scan_script`, `use_ssh_key`, parallelism knobs, `rate_limit`
- `[Controller]` — scan intervals, `extract_path`, `use_local_path_as_extract_path`, `max_tracked_files`
- `[Web]` — `port` (default 8800)
- `[AutoQueue]` — `enabled`, `patterns_only`, `auto_extract`
- `[Sonarr]` — `enabled`, `sonarr_url`, `sonarr_api_key`
- `[Radarr]` — `enabled`, `radarr_url`, `radarr_api_key`
- `[AutoDelete]` — `enabled`, `dry_run`, `delay_seconds`
- `[Encryption]` — `enabled`

**Persist files** (in `<config_dir>`):
- `settings.cfg` — main config
- `secrets.key` — Fernet keyfile (auto-created 0600)
- `controller.persist` — in-flight transfer state
- `autoqueue.persist` — pattern history
- `*.<n>.bak` — automatic backups on corruption

**CLI arguments** (`src/python/seedsyncarr.py:238-264`):
- `-c/--config_dir` (required), `--logdir`, `-d/--debug`, `--exit`, `--html`, `--scanfs`
- For PyInstaller-frozen builds, `--html` and `--scanfs` default to `sys._MEIPASS` paths.

**Build:**
- Python build: `src/python/pyproject.toml` (Hatchling backend; Poetry used for dev/lock management).
- Angular build: `src/angular/angular.json`, `src/angular/tsconfig.json`, `src/angular/tsconfig.app.json`, `src/angular/tsconfig.spec.json`.
- Test: `src/angular/karma.conf.js`, `src/angular/playwright.config.ts`, `src/e2e/playwright.config.ts`.
- Docker: `src/docker/build/docker-image/Dockerfile` (multi-stage: `seedsyncarr_build_angular_env` → `seedsyncarr_build_angular` → `seedsyncarr_build_pyinstaller_env` → `seedsyncarr_build_scanfs` → `seedsyncarr_run_python_env` → `seedsyncarr_run`).
- Root orchestration: `Makefile` targets (`docker-image`, `tests-python`, `tests-angular`, `run-tests-e2e`, `coverage-python`).
- Dockerignore: `src/docker/build/docker-image/Dockerfile.dockerignore`.

## Platform Requirements

**Development:**
- Python 3.11 or 3.12, Poetry for backend dev.
- Node.js 22 + npm for Angular dev (`npm run start` runs `ng serve` on port 4200).
- Docker + Buildx (with QEMU for cross-arch) for image builds and e2e harness.
- System tools (Debian/Ubuntu): `lftp`, `openssh-client`, `p7zip-full`, `unrar`, `bzip2`.
- macOS host noted in repo metadata; tests primarily run inside Linux containers.

**Production:**
- Linux container (`python:3.11-slim`, Debian 12 Bookworm base).
- Multi-arch: `linux/amd64` and `linux/arm64`.
- Image published to `ghcr.io/thejuran/seedsyncarr` (tags: `latest`, `v<x.y.z>`, `dev`).
- Exposes TCP port 8800 (`EXPOSE 8800` in Dockerfile).
- Runs as non-root user `seedsyncarr` (uid/gid 1000) — `Dockerfile:141-149`.
- Required volumes: `/config` (settings + persist files), `/downloads` (local sync target).
- Also published to PyPI as `seedsyncarr` (sdist + wheel built via `python -m build`).

---

*Stack analysis: 2026-05-26*
