# Codebase Structure

**Analysis Date:** 2026-06-09

## Directory Layout

```
seedsyncarr/
├── src/
│   ├── python/                 # Backend daemon (flat package layout, PYTHONPATH root)
│   │   ├── seedsyncarr.py      # Service entry point (main())
│   │   ├── scan_fs.py          # Standalone scanner CLI (frozen to `scanfs` binary)
│   │   ├── common/             # Config, Context, Persist, Job, AppProcess, encryption, status
│   │   ├── model/              # Model, ModelFile, ModelDiff (+ listener interfaces)
│   │   ├── system/             # SystemFile, SystemScanner (filesystem tree scan)
│   │   ├── lftp/               # lftp driver + job status parser
│   │   ├── ssh/                # Sshcp (ssh/scp wrapper)
│   │   ├── controller/         # Business logic: managers, pipeline, autoqueue, webhooks
│   │   │   ├── scan/           # Scanner processes (local/remote/active)
│   │   │   ├── extract/        # Archive extraction (dispatch + process)
│   │   │   └── delete/         # Delete process
│   │   ├── web/                # Bottle web app
│   │   │   ├── handler/        # Route handlers (one IHandler per API surface)
│   │   │   └── serialize/      # SSE/JSON serializers
│   │   ├── tests/
│   │   │   ├── unittests/      # Mirrors package layout (test_common/, test_controller/, …)
│   │   │   ├── integration/    # test_controller/, test_lftp/, test_web/
│   │   │   └── helpers/
│   │   ├── site/               # Project documentation site content
│   │   └── pyproject.toml      # Poetry project (+ poetry.lock)
│   ├── angular/                # Frontend SPA
│   │   ├── src/
│   │   │   ├── main.ts         # bootstrapApplication entry
│   │   │   ├── app/
│   │   │   │   ├── app.config.ts   # Providers, interceptors, APP_INITIALIZERs
│   │   │   │   ├── routes.ts       # ROUTE_INFOS + ROUTES (dashboard/settings/logs/about)
│   │   │   │   ├── pages/          # Page + child components (files, settings, logs, about, main)
│   │   │   │   ├── services/       # State/IO services by domain
│   │   │   │   ├── common/         # Pipes, directives, SCSS partials, constants
│   │   │   │   └── tests/          # fixtures/, mocks/, unittests/
│   │   │   └── environments/
│   │   └── package.json
│   ├── e2e/                    # Playwright E2E suite (own package.json)
│   │   ├── playwright.config.ts
│   │   ├── urls.ts
│   │   └── tests/              # *.page.ts page objects + *.spec.ts specs + fixtures/
│   ├── docker/
│   │   ├── build/docker-image/ # Dockerfile, entrypoint.sh, run_as_user, ssh/scp shims
│   │   ├── stage/              # Staging compose files
│   │   └── test/               # Docker-based test harness
│   └── pyinstaller_hooks/      # hook-patoolib.py
├── scripts/                    # verify-release-metadata.mjs (+ its test)
├── .github/workflows/ci.yml    # CI: node tests, python tests (docker), angular tests, ruff lint
├── Makefile                    # Docker image build, tests, coverage targets
├── doc/                        # Images, brand assets
├── docs/                       # superpowers/ plans and specs
├── .planning/                  # GSD planning state (milestones, phases, debug, codebase)
├── .claude/ & .agents/         # Skills (aidesigner-frontend), agents, commands
└── reports/                    # Generated comparison/analysis reports
```

## Directory Purposes

**`src/python/` (backend root):**
- Purpose: All backend code; this directory is the import root (`from common import ...`)
- Contains: flat top-level packages, two entry scripts, Poetry config
- Key files: `seedsyncarr.py`, `scan_fs.py`, `pyproject.toml`

**`src/python/common/`:**
- Purpose: Shared infrastructure used by every layer
- Key files: `config.py` (661 lines — Config sections incl. sonarr/radarr/autodelete/encryption), `context.py`, `persist.py`, `job.py`, `app_process.py`, `encryption.py`, `status.py`, `bounded_ordered_set.py`, `multiprocessing_logger.py`

**`src/python/controller/`:**
- Purpose: Business logic; `controller.py` (757 lines) is the composition root
- Contains: one manager per concern (`scan_manager.py`, `lftp_manager.py`, `file_operation_manager.py`, `auto_delete_manager.py`, `webhook_manager.py`, `memory_monitor.py`), pipeline (`model_pipeline.py`, `model_builder.py`), command execution (`command_processor.py`), persistence (`controller_persist.py`), thread wrapper (`controller_job.py`)
- Sub-packages hold process-isolated work: `scan/` (`scanner_process.py`, `local_scanner.py`, `remote_scanner.py`, `active_scanner.py`), `extract/` (`dispatch.py`, `extract.py`, `extract_process.py`), `delete/` (`delete_process.py`)

**`src/python/web/`:**
- Purpose: HTTP/SSE interface
- Key files: `web_app.py` (Bottle app, auth, SSE loop, default routes), `web_app_builder.py` (registers all handlers — add new handlers here), `web_app_job.py`, `rate_limit.py`, `utils.py`
- `handler/`: `controller.py` (`/server/command/*`), `config.py` (`/server/config/*`), `auto_queue.py` (`/server/autoqueue/*`), `server.py` (`/server/command/restart`), `status.py` (`/server/status`), `webhook.py` (`/server/webhook/{sonarr,radarr}`), `stream_*.py` (SSE providers)
- `serialize/`: `serialize_model.py`, `serialize_status.py`, `serialize_config.py`, `serialize_auto_queue.py`, `serialize_log_record.py`, base `serialize.py`

**`src/angular/src/app/pages/`:**
- Purpose: Standalone components grouped by page
- Contains: `main/` (app shell, header, notification bell), `files/` (dashboard: files-page, transfer-table, transfer-row, stats-strip, bulk-actions-bar, dashboard-log-pane), `settings/` (settings-page, option component, `options-list.ts`), `logs/`, `about/`
- Each component: `.ts` + `.html` + `.scss` triplet (some with co-located `.spec.ts`)

**`src/angular/src/app/services/`:**
- Purpose: All state and IO, grouped by domain
- Contains: `base/` (SSE plumbing: `stream-service.registry.ts`, `base-stream.service.ts`, `base-web.service.ts`), `files/` (model-file, view-file store + filter/sort/options/selection, `bulk-action-dispatcher.service.ts`, `dashboard-stats.service.ts`), `server/` (`server-command.service.ts`, `bulk-command.service.ts`, `server-status.service.ts`), `settings/` (`config.service.ts`, `config.ts`), `logs/`, `autoqueue/`, `utils/` (`rest.service.ts`, `auth.interceptor.ts`, `notification.service.ts`, `toast.service.ts`, `local-storage.service.ts`, `logger.service.ts`, `confirm-modal.service.ts`, `connected.service.ts`, `dom.service.ts`, `version-check.service.ts`)

**`src/e2e/`:**
- Purpose: Playwright E2E tests, independent npm package
- Key files: `playwright.config.ts`, `tests/dashboard.page.ts` + `tests/dashboard.page.spec.ts` (page-object pattern per page), `tests/fixtures/seed-state.ts`, `tests/helpers.ts`, `tests/csp-canary.spec.ts`

**`src/docker/build/docker-image/`:**
- Purpose: Multi-stage image build — Angular build (node:22-slim) + scanfs PyInstaller build + python:3.11-slim runtime
- Key files: `Dockerfile`, `entrypoint.sh` (PUID/PGID), `run_as_user`, `ssh`/`scp` shims, `setup_default_config.sh`

## Key File Locations

**Entry Points:**
- `src/python/seedsyncarr.py`: backend daemon `main()`
- `src/python/scan_fs.py`: standalone scanner CLI
- `src/angular/src/main.ts`: SPA bootstrap
- `src/docker/build/docker-image/entrypoint.sh`: container start

**Configuration:**
- `src/python/pyproject.toml` + `poetry.lock`: Python deps (Poetry)
- `src/angular/package.json`, `src/angular/src/tsconfig.app.json`, `tsconfig.spec.json`: frontend build/test
- `src/e2e/playwright.config.ts`: E2E runner
- `Makefile`: docker-image build, test targets, `coverage-python`
- `.github/workflows/ci.yml`: CI jobs (release-metadata tests, Python unit tests in Docker, Angular unit tests, `ruff check src/python/`)
- Runtime config lives outside the repo: `settings.cfg`, `controller.persist`, `autoqueue.persist`, `secrets.key` in the `--config_dir`

**Core Logic:**
- `src/python/controller/controller.py`: orchestration hub
- `src/python/controller/model_pipeline.py` + `model_builder.py`: model update pipeline
- `src/python/web/web_app_builder.py`: route/handler wiring
- `src/angular/src/app/services/files/view-file.service.ts`: frontend file store

**Testing:**
- `src/python/tests/unittests/`: mirrors package layout (`test_controller/`, `test_web/`, `test_common/`, `test_lftp/`, `test_model/`, `test_ssh/`, `test_system/`, `test_seedsyncarr.py`)
- `src/python/tests/integration/`: `test_controller/`, `test_lftp/`, `test_web/`
- `src/angular/src/app/tests/`: `unittests/` (by area: common/pages/services), `fixtures/` (`mock-model-files.ts`), `mocks/` (mock services incl. `mock-stream-service.registry.ts`, `mock-event-source.ts`)
- `src/e2e/tests/`: Playwright specs + page objects
- `scripts/verify-release-metadata.test.mjs`: node test for release tooling

## Naming Conventions

**Files:**
- Python: `snake_case.py`; one main class per file named after it (`scan_manager.py` → `ScanManager`); processes end `_process.py`; managers end `_manager.py`; persist classes end `_persist.py`
- Python tests: `test_<module>.py` inside `test_<package>/` directories mirroring source
- Angular: `kebab-case` with role suffixes — `*.component.ts/html/scss`, `*.service.ts`, `*.pipe.ts`, `*.directive.ts`, `*.interceptor.ts`; plain domain models have no suffix (`view-file.ts`, `model-file.ts`, `config.ts`)
- E2E: `<page>.page.ts` (page object) + `<page>.page.spec.ts` (spec)
- Web handlers: noun of the API surface (`webhook.py`, `config.py`); SSE handlers prefixed `stream_`
- Serializers prefixed `serialize_`

**Directories:**
- Python packages: short lowercase nouns (`common`, `model`, `lftp`, `ssh`, `web`, `controller`)
- Angular: `pages/<page-name>/`, `services/<domain>/`

## Where to Add New Code

**New backend API endpoint:**
- Handler: new or existing `IHandler` in `src/python/web/handler/` with `add_routes()` using `web_app.add_handler/add_post_handler/add_delete_handler`
- Wire it in `src/python/web/web_app_builder.py` (constructor + `build()`)
- Serializer (if streaming/JSON payload): `src/python/web/serialize/serialize_<thing>.py`
- Remember auth: `/server/*` paths are Bearer-protected unless added to exemptions in `src/python/web/web_app.py`
- Tests: `src/python/tests/unittests/test_web/`, integration in `src/python/tests/integration/test_web/`

**New controller behavior/manager:**
- Implementation: `src/python/controller/<name>_manager.py`; construct it in `Controller.__init__` and inject into collaborators (do not construct inside `ModelPipeline` etc.)
- Long-running/blocking work: subclass `AppProcess` in a sub-package (`scan/`, `extract/`, `delete/` pattern)
- Tests: `src/python/tests/unittests/test_controller/test_<name>.py`

**New config option:**
- Add to the relevant section class in `src/python/common/config.py`; set defaults in `Seedsyncarr._create_default_config` (`src/python/seedsyncarr.py:306`); expose via `src/python/web/handler/config.py` + `serialize_config.py`; surface in UI via `src/angular/src/app/services/settings/config.ts` and `src/angular/src/app/pages/settings/options-list.ts`

**New frontend page:**
- Component triplet in `src/angular/src/app/pages/<page>/`
- Register in `src/angular/src/app/routes.ts` (both `ROUTE_INFOS` and `ROUTES`)
- Add matching backend SPA route in `WebApp.add_default_routes` (`src/python/web/web_app.py:174-182`)

**New frontend service:**
- `src/angular/src/app/services/<domain>/<name>.service.ts`; provide in `src/angular/src/app/app.config.ts`
- SSE consumers: extend `BaseStreamService` and register through `StreamServiceRegistry` (`src/angular/src/app/services/base/`)
- Tests: `src/angular/src/app/tests/unittests/services/`; shared mocks in `src/angular/src/app/tests/mocks/`

**New E2E test:**
- Page object `src/e2e/tests/<page>.page.ts` + spec `<page>.page.spec.ts`; seed data via `src/e2e/tests/fixtures/seed-state.ts`

**Utilities:**
- Backend shared helpers: `src/python/common/`
- Frontend shared pipes/directives/constants: `src/angular/src/app/common/`

## Special Directories

**`.planning/`:**
- Purpose: GSD planning state (milestones, phases, debug notes, codebase maps)
- Generated: By GSD commands — Committed: Yes

**`src/angular/dist/`, `src/angular/.angular/`, `src/angular/node_modules/`, `src/e2e/node_modules/`, `src/e2e/playwright-report/`, `src/e2e/test-results/`:**
- Purpose: Build output, caches, deps — Generated: Yes — Committed: No

**`src/python/htmlcov/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`:**
- Purpose: Python coverage/test/lint caches — Generated: Yes — Committed: No

**`src/python/site/`:**
- Purpose: Documentation site content (install, configuration, arr-setup, faq) — Generated: No — Committed: Yes

**`.claude/skills/aidesigner-frontend/`, `.agents/skills/aidesigner-frontend/`:**
- Purpose: AIDesigner frontend skill (design-artifact → repo-native porting rules) — Committed: Yes

**`.aidesigner/runs/`, `.turingmind/`, `.playwright-mcp/`, `.bg-shell/`:**
- Purpose: Tool-generated artifacts (design runs, review state, browser sessions) — Generated: Yes

**`shield-claude-skill/`:**
- Purpose: Embedded separate project (own `.git`) — not part of the SeedSyncarr application

---

*Structure analysis: 2026-06-09*
