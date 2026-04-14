# Technology Stack

**Analysis Date:** 2026-02-03

## Languages

**Primary:**
- **Python** 3.11+ - Backend application server and CLI tools, located in `src/python/`
- **TypeScript** 5.7 - Angular frontend application, located in `src/angular/`
- **HTML/SCSS** - Frontend templates and styling

**Secondary:**
- **Bash** - Makefile-based build orchestration (`Makefile`)
- **YAML** - GitHub Actions CI/CD configuration (`.github/workflows/`)
- **Dockerfile** - Multi-stage Docker build configurations (`src/docker/`)

## Runtime

**Environment:**
- **Python 3.11 - 3.12** - Backend runtime
- **Node.js** (via npm) - Frontend build and test runtime
- **Docker/Buildx** - Containerized deployment

**Package Manager:**
- **Poetry** 1.x - Python dependency management
  - Config: `src/python/pyproject.toml`
  - Lockfile: `src/python/poetry.lock` (present)
- **npm** - JavaScript/TypeScript dependency management
  - Config: `src/angular/package.json`, `src/e2e/package.json`
  - Lockfile: `src/angular/package-lock.json` (present)

## Frameworks

**Core:**
- **Bottle** ^0.13.4 - Lightweight Python web framework for API
  - Server: Custom WSGI adapter in `src/python/web/web_app_job.py`
  - HTTP server: Paste httpserver
- **Angular** ^19.2.18 - Frontend SPA framework
  - CLI: Angular DevKit 19.2.19
  - Build system: Angular-devkit/build-angular

**Testing:**
- **pytest** ^7.4.4 - Python unit testing framework
  - Config: `src/python/pyproject.toml` (timeout: 60s)
  - Test discovery: Tests in `src/python/tests/`
- **Karma** ^6.4.4 - Angular unit test runner
  - Config: `src/angular/karma.conf.js`
  - Browser: Chrome launcher
- **Jasmine** ~5.1.0 - Angular assertion library
- **Playwright** ^1.48.0 - End-to-end testing
  - Angular E2E config: `src/angular/playwright.config.ts` (baseURL: http://localhost:4200)
  - Main E2E config: `src/e2e/playwright.config.ts` (baseURL: http://myapp:8800)
  - Browser: Chromium

**Build/Dev:**
- **Docker** & **Docker Buildx** - Multi-architecture image building
- **Make** - Build orchestration (`Makefile`)
- **Angular CLI** - Frontend development server and build
- **Sass** ^1.32.0 - CSS preprocessing

## Key Dependencies

**Critical:**
- **pexpect** ^4.9.0 - Interactive command-line process spawning (used for LFTP, SSH/SCP)
- **Bottle** ^0.13.4 - Core web framework
- **Paste** ^3.10.1 - WSGI HTTP server implementation
- **RxJS** ^7.5.0 - Reactive programming library for Angular
- **Bootstrap** ^5.3.3 - CSS framework for frontend UI
- **Angular Core** ^19.2.18 - Frontend framework

**Infrastructure:**
- **pytz** ^2025.2 - Timezone support for Python
- **requests** ^2.32.5 - HTTP client library (for potential API calls)
- **parameterized** ^0.9.0 - Parametrized testing for pytest
- **patool** ^4.0.3 - Archive/compression tool wrapper
- **timeout-decorator** ^0.5.0 - Timeout management for long-running operations
- **tblib** ^3.2.2 - Traceback serialization (for error handling)
- **immutable** ^4.3.0 - Immutable collections library for Angular
- **compare-versions** ^6.1.1 - Version comparison utility

**Linting & Code Quality:**
- **ESLint** ^9.18.0 - TypeScript/JavaScript linting
  - Parser: @typescript-eslint/parser ^8.54.0
  - Plugin: @typescript-eslint/eslint-plugin ^8.54.0
  - Config: Flat config format in `src/angular/eslint.config.js`

**Documentation:**
- **MkDocs** ^1.6.1 - Documentation generator
  - Theme: mkdocs-material ^9.7.1
  - Config: `src/python/mkdocs.yml`

## Configuration

**Environment:**
- **Angular dev server:** Runs on http://localhost:4200 (configurable in angular.json)
- **Python web server:** Configurable port (default 8800) via config section `[Web]`
- **E2E tests:** Configurable baseURL via `APP_BASE_URL` environment variable
- **Python logging:** RotatingFileHandler-based logs in configurable directory
- **Config file location:** `settings.cfg` (location set via CLI argument `--config`)

**Build:**
- `src/angular/tsconfig.json` - TypeScript compilation (target: ES2022, module: ES2022)
- `src/angular/angular.json` - Angular build configuration
- `src/angular/eslint.config.js` - ESLint rules and configuration
- `src/angular/karma.conf.js` - Karma test runner configuration
- `src/angular/playwright.config.ts` - E2E Playwright configuration
- `src/e2e/playwright.config.ts` - Integration E2E configuration
- Docker build targets:
  - `seedsync_build_deb_export` - Debian package build
  - `seedsync_build_angular_export` - Angular frontend build
  - `seedsync_build_scanfs_export` - Scanfs binary build
  - `seedsync_run` - Final runtime image

**Deployment:**
- **Debian packages:** Built for amd64 and arm64 architectures
- **Docker images:** Multi-architecture (amd64, arm64) published to GHCR
- **Environment variables:**
  - `STAGING_REGISTRY` - Docker registry for staging builds (default: localhost:5000)
  - `STAGING_VERSION` - Docker image version for staging
  - `RELEASE_REGISTRY` - Docker registry for release builds
  - `RELEASE_VERSION` - Release version
  - `SEEDSYNC_DEB` - Path to deb package for E2E testing
  - `SEEDSYNC_OS` - Target OS for deb E2E tests (ubu2204, ubu2404)
  - `SEEDSYNC_ARCH` - Target architecture (amd64, arm64)

## Platform Requirements

**Development:**
- Node.js/npm (for Angular frontend)
- Python 3.11+
- Docker with Buildx support
- Make
- LFTP command-line tool
- SSH/SCP utilities

**Production:**
- **Container hosting:** Docker-compatible container runtime
- **Deployment target:**
  - Docker containers (amd64, arm64)
  - Linux Debian packages (amd64, arm64, Ubuntu 22.04, Ubuntu 24.04)
  - macOS/Windows via Docker
- **Disk space:** Configurable via settings
- **Network:** SSH/SFTP connectivity to remote servers

**Browser Support:**
- **Chromium/Chrome** - Desktop (tested in E2E)
- Modern browsers supporting ES2022 JavaScript

## CI/CD Stack

**Continuous Integration:**
- **GitHub Actions** - Build and test automation
- **Docker Buildx** - Multi-architecture image building in CI
- **Artifact storage:** GitHub Artifacts (deb packages)
- **Container registry:** GitHub Container Registry (GHCR) at ghcr.io/thejuran/seedsync

**Versioning:**
- Git tags: `vX.Y.Z` for releases
- Branch-based triggers: `master` for `:dev` tag, tags for `:X.Y.Z` releases

---

*Stack analysis: 2026-02-03*
