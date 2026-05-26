# Codebase Structure

**Analysis Date:** 2026-05-26

## Directory Layout

```
seedsyncarr/
├── src/                                 # All product source code
│   ├── python/                          # Python backend (the service)
│   │   ├── seedsyncarr.py               # Service entry point (`main()`)
│   │   ├── scan_fs.py                   # Standalone scanner script (frozen as `scanfs`)
│   │   ├── pyproject.toml               # Package config (hatch + poetry, deps, pytest, coverage)
│   │   ├── poetry.lock                  # Poetry lockfile
│   │   ├── mkdocs.yml                   # User docs site config
│   │   ├── common/                      # Cross-cutting primitives (Job, Context, Config, Persist, etc.)
│   │   ├── controller/                  # Domain core (Controller, AutoQueue, managers, scanners, extract, delete)
│   │   │   ├── controller.py            # Top-level orchestrator
│   │   │   ├── controller_job.py        # Job-thread wrapper
│   │   │   ├── controller_persist.py    # On-disk state for tracked/downloaded/extracted files
│   │   │   ├── auto_queue.py            # Pattern-driven auto-queue
│   │   │   ├── model_builder.py         # Builds new Model from inputs
│   │   │   ├── scan_manager.py          # Owns remote/local/active scanner processes
│   │   │   ├── lftp_manager.py          # Wraps Lftp (pexpect)
│   │   │   ├── file_operation_manager.py# Spawns extract/delete one-shot processes
│   │   │   ├── webhook_manager.py       # Cross-thread import-event queue
│   │   │   ├── memory_monitor.py        # Periodic memory/eviction stats
│   │   │   ├── scan/                    # Scanner implementations + ScannerProcess
│   │   │   ├── extract/                 # ExtractProcess + ExtractDispatch (patool)
│   │   │   └── delete/                  # DeleteLocalProcess / DeleteRemoteProcess
│   │   ├── model/                       # ModelFile / Model / ModelDiff
│   │   ├── lftp/                        # Lftp pexpect wrapper + status parser
│   │   ├── ssh/                         # sshcp helper (used by remote scan dispatch)
│   │   ├── system/                      # Local filesystem scanner + SystemFile
│   │   ├── web/                         # Bottle web app, REST + SSE
│   │   │   ├── web_app.py               # WebApp (Bottle subclass), auth/host/CSP hooks
│   │   │   ├── web_app_builder.py       # Wires handlers + streams into a WebApp
│   │   │   ├── web_app_job.py           # Job-thread wrapper around Paste/Bottle
│   │   │   ├── rate_limit.py            # Decorator
│   │   │   ├── utils.py                 # StreamQueue + helpers
│   │   │   ├── handler/                 # One file per REST/SSE handler group
│   │   │   └── serialize/               # JSON serializers (Model/Config/Status/AutoQueue/LogRecord)
│   │   ├── tests/                       # Pytest tests (unit + integration + helpers)
│   │   └── docs/                        # mkdocs source (arr-setup, configuration, faq, install, …)
│   ├── angular/                         # Angular SPA (the UI)
│   │   ├── angular.json                 # Angular CLI workspace config
│   │   ├── package.json                 # npm scripts + deps
│   │   ├── playwright.config.ts         # Playwright (angular e2e subset)
│   │   ├── eslint.config.js             # ESLint flat config
│   │   ├── karma.conf.js                # Karma runner for unit tests
│   │   ├── tsconfig.json                # TS root config
│   │   ├── src/
│   │   │   ├── main.ts                  # Bootstraps AppComponent
│   │   │   ├── index.html               # Shell HTML (served by Bottle with meta token)
│   │   │   ├── styles.scss              # Global styles (Bootstrap + custom)
│   │   │   ├── polyfills.ts, test.ts, typings.d.ts
│   │   │   ├── environments/            # environment.ts + environment.prod.ts
│   │   │   ├── assets/                  # Static assets bundled into dist
│   │   │   └── app/
│   │   │       ├── app.config.ts        # DI providers (routes, services, interceptors)
│   │   │       ├── routes.ts            # Router config + ROUTE_INFOS
│   │   │       ├── pages/               # Route-level components
│   │   │       │   ├── main/            # AppComponent, HeaderComponent, NotificationBell
│   │   │       │   ├── files/           # Dashboard: files-page, transfer-table/-row, stats-strip,
│   │   │       │   │                       bulk-actions-bar, dashboard-log-pane
│   │   │       │   ├── settings/        # settings-page + option list
│   │   │       │   ├── logs/            # logs-page
│   │   │       │   └── about/           # about-page
│   │   │       ├── services/            # Singleton stores + REST/SSE clients
│   │   │       │   ├── base/            # BaseStreamService, BaseWebService, StreamDispatchService registry
│   │   │       │   ├── files/           # ModelFile types, ModelFileService, view filters/sort/options,
│   │   │       │   │                       dashboard-stats, bulk-action-dispatcher, file-selection
│   │   │       │   ├── server/          # ServerStatusService, ServerCommandService, BulkCommandService
│   │   │       │   ├── settings/        # ConfigService + Config type
│   │   │       │   ├── logs/            # LogService + LogRecord type
│   │   │       │   ├── autoqueue/       # AutoQueueService + AutoQueuePattern type
│   │   │       │   └── utils/           # RestService, LoggerService, NotificationService, ToastService,
│   │   │       │                          DomService, VersionCheckService, ConnectedService,
│   │   │       │                          LocalStorageService, ConfirmModalService, auth.interceptor
│   │   │       ├── common/              # Pipes, directives, shared SCSS, route-reuse, version constant
│   │   │       └── tests/               # Shared test fixtures
│   │   ├── e2e/                         # Legacy Angular Playwright tests (app.po.ts pattern)
│   │   └── dist/                        # Built SPA (consumed by Docker stage)
│   ├── e2e/                             # Cross-stack Playwright tests (run against Docker stack)
│   │   ├── playwright.config.ts
│   │   ├── package.json, tsconfig.json, README.md
│   │   ├── urls.ts                      # Endpoint constants
│   │   └── tests/                       # *.page.ts + *.spec.ts page-object pattern, plus fixtures/ + helpers.ts
│   ├── docker/                          # Docker build + test harnesses
│   │   ├── build/docker-image/          # Production Dockerfile (multi-stage, multi-arch)
│   │   ├── stage/docker-image/          # Staging compose
│   │   ├── test/{python,angular,e2e}/   # Test compose files invoked from Makefile
│   │   └── wait-for-it.sh
│   └── pyinstaller_hooks/               # Custom PyInstaller hooks
│       └── hook-patoolib.py
├── scripts/                             # Repo-level helper scripts
│   ├── verify-release-metadata.mjs
│   └── verify-release-metadata.test.mjs
├── docs/                                # Repo-level docs (architecture, configuration, dev, testing)
│   ├── ARCHITECTURE.md
│   ├── CONFIGURATION.md
│   ├── DEVELOPMENT.md
│   ├── GETTING-STARTED.md
│   ├── TESTING.md
│   └── superpowers/
├── doc/                                 # Brand assets + images for README
├── shield-claude-skill/                 # Vendored Claude skill bundle (separate tool, not the app)
├── reports/                             # Generated reports (CI artifacts)
├── .planning/                           # GSD planning artifacts (this directory)
│   └── codebase/                        # Codebase analysis docs (ARCHITECTURE.md, STRUCTURE.md, …)
├── .agents/skills/aidesigner-frontend/  # AIDesigner skill bundle
├── .claude/                             # Claude Code config, commands, skills, worktrees
├── .github/                             # GitHub Actions workflows + Dependabot + issue templates
├── .aidesigner/                         # AIDesigner local runs / artifacts
├── .gsd, .gsd-id, .mcp.json             # GSD + MCP config
├── .gitleaks.toml                       # Secret-scan config
├── package.json, package-lock.json      # Root-level dev tooling (puppeteer for AIDesigner QA)
├── Makefile                             # Docker build + test entry points
├── CHANGELOG.md, README.md, LICENSE.txt # Project metadata
├── ACKNOWLEDGMENTS.md, CONTRIBUTING.md, SECURITY.md, release-notes.md
```

## Directory Purposes

**`src/python/`**
- Purpose: the SeedSyncarr backend service.
- Contains: Python packages (`common`, `controller`, `model`, `lftp`, `ssh`, `system`, `web`), entry point, `scan_fs.py` helper, tests, and mkdocs sources.
- Key files: `seedsyncarr.py`, `pyproject.toml`, `controller/controller.py`, `web/web_app_builder.py`.

**`src/python/common/`**
- Purpose: cross-cutting primitives reused by every other package.
- Contains: threading + multiprocessing abstractions (`Job`, `AppProcess`), application context (`Context`, `Args`), configuration (`Config`), persistence base (`Persist`, `Serializable`), encryption (`encryption.py`), `Status`, `Localization`, `Constants`, `BoundedOrderedSet`, error hierarchy.
- Key files: `job.py`, `app_process.py`, `context.py`, `config.py`, `persist.py`, `status.py`.

**`src/python/controller/`**
- Purpose: domain core — orchestrates scanning, transfers, extraction, deletion, and webhook-driven imports.
- Contains: `Controller` and its managers, `AutoQueue`, `ModelBuilder`, scanner / extract / delete subpackages.
- Key files: `controller.py`, `controller_job.py`, `auto_queue.py`, `scan_manager.py`, `lftp_manager.py`, `file_operation_manager.py`, `webhook_manager.py`.

**`src/python/controller/scan/`, `extract/`, `delete/`**
- Purpose: child-process workers managed by the controller.
- Contains: process classes (`ScannerProcess`, `ExtractProcess`, `DeleteLocalProcess`, `DeleteRemoteProcess`) plus their backing implementations (`RemoteScanner`, `LocalScanner`, `ActiveScanner`, `ExtractDispatch`).

**`src/python/model/`**
- Purpose: in-memory immutable file tree shared between controller and web tier.
- Contains: `ModelFile` (frozen value object), `Model` (listener container), `ModelDiff` + `ModelDiffUtil`.

**`src/python/lftp/`, `ssh/`, `system/`**
- Purpose: thin external-process adapters.
- `lftp/`: `Lftp` pexpect wrapper + `LftpJobStatus`/parser.
- `ssh/`: `sshcp` helper used by `RemoteScanner` to dispatch the scan script.
- `system/`: local `Scanner` and `SystemFile`.

**`src/python/web/`**
- Purpose: HTTP/SSE adapter on top of Bottle + Paste.
- Contains: `WebApp` (Bottle subclass with security hooks), `WebAppBuilder`, `WebAppJob`, rate-limit decorator, `handler/` (one file per endpoint group), `serialize/` (JSON serializers).

**`src/python/web/handler/`**
- Purpose: REST and SSE handler implementations registered by `WebAppBuilder`.
- Contains: `controller.py`, `config.py`, `auto_queue.py`, `status.py`, `server.py`, `webhook.py`, `stream_model.py`, `stream_status.py`, `stream_log.py`, `stream_heartbeat.py`.

**`src/python/web/serialize/`**
- Purpose: convert domain objects to/from JSON SSE/REST payloads.
- Contains: `serialize_model.py`, `serialize_config.py`, `serialize_status.py`, `serialize_auto_queue.py`, `serialize_log_record.py`, `serialize.py` (base).

**`src/python/tests/`**
- Purpose: pytest suite.
- Subdirs: `unittests/` (mirrors source tree: `test_common/`, `test_controller/`, `test_model/`, `test_lftp/`, `test_ssh/`, `test_system/`, `test_web/`, plus `test_seedsyncarr.py`), `integration/` (`test_controller/`, `test_lftp/`, `test_web/`), `helpers/` (`wsgi_stream.py`), `conftest.py`, `utils.py`.

**`src/python/docs/`**
- Purpose: mkdocs source for user-facing docs (published from `mkdocs.yml`).
- Contains: `arr-setup.md`, `configuration.md`, `coverage-gaps.md`, `faq.md`, `install.md`, `index.md`, `name-mangling-tradeoff.md`, `images/`.

**`src/angular/`**
- Purpose: Angular SPA served by the Python backend as static assets.
- Contains: Angular CLI workspace, Playwright config (legacy `e2e/` subset), Karma config, ESLint flat config.

**`src/angular/src/app/pages/`**
- Purpose: route-level components, one folder per route.
- Subdirs: `main/` (root `AppComponent` + header + notification bell), `files/` (dashboard), `settings/`, `logs/`, `about/`.

**`src/angular/src/app/services/`**
- Purpose: Angular singleton services split by domain.
- Subdirs:
  - `base/` — `BaseStreamService`, `BaseWebService`, `StreamDispatchService` registry.
  - `files/` — model file store + view options + bulk action dispatcher + dashboard stats.
  - `server/` — status / command / bulk command services.
  - `settings/` — config store and types.
  - `logs/` — log stream service.
  - `autoqueue/` — autoqueue pattern service.
  - `utils/` — REST, logger, notification, toast, DOM, version check, connected, local storage, auth interceptor, confirm modal.

**`src/angular/src/app/common/`**
- Purpose: tiny shared building blocks not tied to a single route or service.
- Contains: `cached-reuse-strategy.ts`, `capitalize.pipe.ts`, `eta.pipe.ts`, `file-size.pipe.ts`, `is-selected.pipe.ts`, `click-stop-propagation.directive.ts`, `localization.ts`, `storage-keys.ts`, `version.ts`, plus Bootstrap SCSS overrides.

**`src/e2e/`**
- Purpose: cross-stack Playwright tests run against a fully assembled Docker stack.
- Contains: Playwright config, `urls.ts` endpoint constants, page objects + spec files following the `*.page.ts` + `*.page.spec.ts` pattern, `helpers.ts`, `fixtures/`.

**`src/docker/`**
- Purpose: container build + test harness.
- `build/docker-image/Dockerfile` is the multi-stage, multi-arch production build (`seedsyncarr_run` final stage).
- `test/{python,angular,e2e}/compose.yml` are docker compose stacks invoked from `Makefile` (`run-tests-python`, `run-tests-angular`, `run-tests-e2e`).
- `wait-for-it.sh` is reused across compose files.

**`src/pyinstaller_hooks/`**
- Purpose: custom PyInstaller collection hooks. Currently only `hook-patoolib.py` so the frozen build can find patool's archive-format modules.

**`scripts/`**
- Purpose: repo-level Node scripts. `verify-release-metadata.mjs` runs in CI to keep `release-notes.md`, `CHANGELOG.md`, and `pyproject.toml` versions consistent.

**`docs/`**
- Purpose: repo-level documentation for contributors (separate from `src/python/docs/` which is the user-facing mkdocs site).

**`shield-claude-skill/`**
- Purpose: vendored standalone Claude skill bundle. Not part of the SeedSyncarr runtime; do not import it from `src/`.

**`reports/`**
- Purpose: CI-generated reports. Treat as outputs, not inputs.

**`.planning/`**
- Purpose: GSD planning artifacts (phases, milestones, codebase analysis). Source-controlled.

**`.aidesigner/`**
- Purpose: AIDesigner local runs / preview artifacts. Generally treat as scratch.

## Key File Locations

**Entry Points:**
- `src/python/seedsyncarr.py`: Python service entry (`main()` exposed as `seedsyncarr` console script).
- `src/python/scan_fs.py`: standalone remote scan helper (frozen as `scanfs`).
- `src/angular/src/main.ts`: Angular SPA bootstrap.
- `src/angular/src/app/app.config.ts`: Angular DI configuration.
- `src/angular/src/app/routes.ts`: SPA route table.
- `src/docker/build/docker-image/Dockerfile`: production container build.

**Configuration:**
- `src/python/pyproject.toml`: Python package metadata, deps, pytest, coverage.
- `src/python/poetry.lock`: Python lockfile.
- `src/angular/package.json`, `src/angular/package-lock.json`: Angular deps + npm scripts.
- `src/angular/angular.json`: Angular workspace config.
- `src/angular/tsconfig.json`, `tsconfig.app.json`, `tsconfig.spec.json`: TypeScript configs.
- `src/angular/eslint.config.js`: ESLint flat config.
- `src/angular/karma.conf.js`: unit test runner config.
- `src/angular/playwright.config.ts`, `src/e2e/playwright.config.ts`: Playwright configs.
- `Makefile`: top-level build/test targets.
- `package.json` (repo root): tooling-only deps (Puppeteer for AIDesigner QA).
- `.gitleaks.toml`: secret scanner config.
- `.github/workflows/`: CI pipelines.
- Runtime config: `$CONFIG_DIR/settings.cfg` (default `~/.seedsyncarr/`), with companion `controller.persist`, `autoqueue.persist`, `secrets.key`.

**Core Logic:**
- `src/python/controller/controller.py`: orchestrator + command processing + auto-delete logic.
- `src/python/controller/controller_job.py`: thread wrapper.
- `src/python/controller/auto_queue.py`: pattern-driven auto-queue.
- `src/python/controller/scan_manager.py`, `src/python/controller/scan/`: scanner subsystem.
- `src/python/controller/lftp_manager.py`, `src/python/lftp/lftp.py`: LFTP subsystem.
- `src/python/controller/file_operation_manager.py`, `src/python/controller/extract/`, `src/python/controller/delete/`: file ops subsystem.
- `src/python/controller/webhook_manager.py`: webhook bridge.
- `src/python/model/model.py`, `src/python/model/file.py`, `src/python/model/diff.py`: in-memory model.
- `src/python/web/web_app.py`, `src/python/web/web_app_builder.py`: web app and DI.
- `src/python/web/handler/*.py`: REST + SSE endpoints.
- `src/python/web/serialize/*.py`: JSON payload serializers.
- `src/angular/src/app/services/files/model-file.service.ts`: SPA model store.
- `src/angular/src/app/services/base/stream-service.registry.ts`: SSE dispatcher.

**Testing:**
- `src/python/tests/unittests/`: pytest unit tests, mirrors source tree.
- `src/python/tests/integration/`: integration tests (`test_controller`, `test_lftp`, `test_web`).
- `src/python/tests/conftest.py`, `src/python/tests/utils.py`, `src/python/tests/helpers/`: shared fixtures.
- `src/angular/src/app/**/*.spec.ts`: Angular unit tests (Jasmine + Karma) co-located with source.
- `src/angular/e2e/`: legacy Angular Playwright tests.
- `src/e2e/tests/`: cross-stack Playwright tests with `*.page.ts` page objects.
- `src/docker/test/{python,angular,e2e}/compose.yml`: dockerized test runners.

## Naming Conventions

**Files (Python):**
- `lowercase_snake_case.py` for modules: `web_app_builder.py`, `auto_queue.py`, `file_operation_manager.py`.
- One primary class per module; classmodule pairing common (e.g. `Controller` in `controller.py`, `ControllerJob` in `controller_job.py`, `ControllerPersist` in `controller_persist.py`).
- `__init__.py` re-exports the package's public API with `as`-aliasing (see `src/python/common/__init__.py`, `src/python/controller/__init__.py`).
- Test files: `test_<module>.py` mirroring the source path (e.g., `tests/unittests/test_controller/test_controller.py`).

**Files (Angular/TypeScript):**
- Components: `<feature>.component.ts` + matching `.html` + `.scss` + `.spec.ts` (e.g., `transfer-table.component.ts`).
- Services: `<feature>.service.ts` (e.g., `model-file.service.ts`, `view-file-filter.service.ts`).
- Interfaces / types: `<feature>.ts` (e.g., `model-file.ts`, `view-file.ts`, `notification.ts`).
- Pipes: `<feature>.pipe.ts` (e.g., `file-size.pipe.ts`).
- Directives: `<feature>.directive.ts` (e.g., `click-stop-propagation.directive.ts`).
- Interceptors: `<feature>.interceptor.ts` (e.g., `auth.interceptor.ts`).
- Test files: co-located `<file>.spec.ts`.
- E2E: `<page>.page.ts` (page object) + `<page>.page.spec.ts` or `<topic>.spec.ts` (spec).

**Directories:**
- Python: `lowercase` single-word packages (`common`, `controller`, `model`, `web`, `lftp`, `ssh`, `system`). Subpackages also lowercase (`controller/scan`, `controller/extract`, `controller/delete`, `web/handler`, `web/serialize`).
- Angular: `kebab-case` only when needed; mostly single-word (`pages/files`, `pages/settings`, `services/base`, `services/files`, `services/server`). The `aidesigner-frontend` skill folder uses kebab-case.
- Test mirroring: each `controller/scan` source has a `tests/unittests/test_controller/test_scan/` directory.

**Class / Symbol names:**
- Python classes `PascalCase`, methods `snake_case`, private with leading `_` or `__`. Abstract interfaces use `I` prefix only for cross-process / cross-module contracts (`IHandler`, `IStreamHandler`, `IModelListener`, `IAutoQueuePersistListener`, `IScanner`, `IStatusListener`). Domain errors end in `Error` (`ControllerError`, `LftpError`, `ScannerError`, `ConfigError`).
- TypeScript classes `PascalCase`, members `camelCase` with `_` prefix for private fields (`_logger`, `_files`). Constants `UPPER_SNAKE_CASE`. Observable accessors named after the data (`files`, `connected$`).

## Where to Add New Code

**New REST endpoint (Python):**
- Implementation: add or extend a handler in `src/python/web/handler/<group>.py` (or create a new file there).
- Wire it: instantiate in `src/python/web/web_app_builder.py` and call its `add_routes(web_app)`.
- Serialization: add a serializer in `src/python/web/serialize/` if a new payload type is needed.
- Tests: `src/python/tests/unittests/test_web/test_handler/` + integration in `src/python/tests/integration/test_web/`.
- If the endpoint mutates controller state, do not call domain methods directly — submit a `Controller.Command` via `controller.queue_command(...)`.

**New SSE event stream (Python):**
- Implementation: add a class implementing `IStreamHandler` in `src/python/web/handler/stream_<name>.py`.
- Register it: call `<Class>.register(web_app=web_app, **kwargs)` from `WebAppBuilder.build()` so it joins the multiplexed `/server/stream`.
- Frontend: subclass `BaseStreamService` in `src/angular/src/app/services/<domain>/`, `registerEventName(...)` for each event, and add it to `StreamServiceRegistryProvider` (`src/angular/src/app/services/base/stream-service.registry.ts`).

**New controller subsystem (Python):**
- If it owns an external process: subclass `AppProcess` / `AppOneShotProcess` in a new subpackage of `src/python/controller/` (mirroring `scan/`, `extract/`, `delete/`).
- Wire it up in `Controller.__init__`, drive it from `Controller.process()`, and expose status via `Status` updates.
- Persistent state: add fields to `ControllerPersist` (`src/python/controller/controller_persist.py`) — they will be automatically rotated/backed-up on corruption.

**New config field (Python):**
- Add the attribute to the relevant section class in `src/python/common/config.py` and add a default in `Seedsyncarr._create_default_config()` (`src/python/seedsyncarr.py`).
- If the field is a secret, add it to `_SECRET_FIELD_PATHS` in `src/python/common/config.py` so it is encrypted on disk.
- Expose it to the UI: add a serialization step in `src/python/web/serialize/serialize_config.py`, then add the field to `Config` (`src/angular/src/app/services/settings/config.ts`) and an `OptionComponent` entry in `src/angular/src/app/pages/settings/options-list.ts`.
- If sensitive, also list it in `Context._REDACTED_KEYS` (`src/python/common/context.py`).

**New page / route (Angular):**
- Implementation: create `src/angular/src/app/pages/<name>/<name>-page.component.{ts,html,scss}` (+ `.spec.ts`).
- Route: add the route entry to both `ROUTE_INFOS` (header nav) and `ROUTES` (router) in `src/angular/src/app/routes.ts`.
- Server route: add the path to the SPA-shell list in `WebApp.add_default_routes` (`src/python/web/web_app.py:166`) so deep links return `index.html`.

**New shared Angular component / pipe / directive:**
- Component used by multiple pages: place under the most relevant page folder (e.g., `pages/files/transfer-row.component.ts`) and import it directly; there is no global `shared/` module — components are `standalone: true`.
- Pipe / directive / route-reuse helper: `src/angular/src/app/common/`.
- Imports in `app.config.ts` providers when a service must be global.

**New Angular service:**
- Place under `src/angular/src/app/services/<domain>/`. Domain folders: `files`, `server`, `settings`, `logs`, `autoqueue`, `utils`, `base`.
- If singleton: add to `providers[]` in `src/angular/src/app/app.config.ts`.
- If SSE-backed: subclass `BaseStreamService`. If REST-only: depend on `RestService` directly.

**New tests:**
- Python unit: `src/python/tests/unittests/test_<package>/test_<module>.py`.
- Python integration: `src/python/tests/integration/test_<area>/`.
- Angular unit: co-located `*.spec.ts` next to the source file.
- Cross-stack e2e: `src/e2e/tests/<feature>.page.ts` + `<feature>.spec.ts` (page-object pattern).
- Run via `make run-tests-python` / `make run-tests-angular` / `make run-tests-e2e`.

**Utilities / shared helpers:**
- Python: `src/python/common/` for primitives reused across packages. Resist adding domain logic here — `common` is intentionally infrastructure-only.
- Angular: `src/angular/src/app/services/utils/` for technical services, `src/angular/src/app/common/` for pipes/directives/constants.

## Special Directories

**`src/angular/dist/`**
- Purpose: built SPA artifacts.
- Generated: yes (by `ng build`).
- Committed: no (`.gitignore`).
- Consumed by: Dockerfile `seedsyncarr_run` stage, which copies into `--html` path.

**`src/python/site/`**
- Purpose: built mkdocs output.
- Generated: yes (by `mkdocs build`).
- Committed: typically no.

**`reports/`**
- Purpose: CI-generated coverage / lint reports.
- Generated: yes.
- Committed: yes (historical artifacts).

**`.planning/`**
- Purpose: GSD planning artifacts (this file lives here).
- Generated: yes (by GSD commands).
- Committed: yes.

**`.aidesigner/`**
- Purpose: AIDesigner local runs / previews.
- Generated: yes (by `@aidesigner/agent-skills`).
- Committed: selectively (design briefs yes; run artifacts often no).

**`shield-claude-skill/`**
- Purpose: vendored standalone Claude skill bundle. Do not import from `src/`.
- Generated: no.
- Committed: yes.

**`.agents/skills/aidesigner-frontend/`, `.claude/skills/aidesigner-frontend/`**
- Purpose: skill definitions for the AIDesigner frontend workflow. Indexed by the Claude agent harness.
- Generated: regenerated by `npx -y @aidesigner/agent-skills upgrade`.
- Committed: yes.

**`.github/`**
- Purpose: CI workflows (`.github/workflows/`), Dependabot config, PR/issue templates.
- Committed: yes.

**`.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `__pycache__/`**
- Purpose: tool caches and installed deps.
- Generated: yes.
- Committed: no (`.gitignore`).

---

*Structure analysis: 2026-05-26*
