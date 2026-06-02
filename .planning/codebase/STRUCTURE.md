# Codebase Structure

**Analysis Date:** 2026-06-02

## Directory Layout

```
seedsyncarr/
├── src/
│   ├── python/                  # Python backend daemon (the application core)
│   │   ├── seedsyncarr.py       # Daemon entry point (main(), Seedsyncarr service class)
│   │   ├── scan_fs.py           # Standalone remote-scan executable (run over SSH)
│   │   ├── common/              # Cross-cutting: context, config, status, logging, persist, encryption
│   │   ├── controller/          # Coordinator + collaborator managers (post-Phase-109 decomposition)
│   │   │   ├── controller.py    # Thin coordinator: command queue, model+lock, auto-delete timers
│   │   │   ├── model_pipeline.py     # scan→build→diff→apply pipeline collaborator
│   │   │   ├── model_builder.py      # Reconcile scan/LFTP/extract → ModelFile tree
│   │   │   ├── command_processor.py  # Execute QUEUE/STOP/EXTRACT/DELETE actions
│   │   │   ├── auto_delete_manager.py # BFS pack-guard + coverage for safe auto-delete
│   │   │   ├── scan_manager.py       # Owns scanner processes
│   │   │   ├── lftp_manager.py       # LFTP queue/stop/status wrapper
│   │   │   ├── file_operation_manager.py # Spawn/track delete + extract processes
│   │   │   ├── webhook_manager.py    # Sonarr/Radarr import matching
│   │   │   ├── auto_queue.py         # Pattern-based auto-queue
│   │   │   ├── memory_monitor.py     # Bounded-collection stats logging
│   │   │   ├── controller_job.py     # Thread wrapper calling process() each tick
│   │   │   ├── controller_persist.py # On-disk controller state
│   │   │   ├── scan/                 # Remote/local/active scanner processes
│   │   │   ├── extract/              # Archive extraction process + dispatch
│   │   │   └── delete/               # Delete subprocess
│   │   ├── model/               # Domain model: Model, ModelFile, ModelDiff
│   │   ├── lftp/                # LFTP CLI wrapper + job-status parser
│   │   ├── ssh/                 # SCP/SFTP helper (sshcp.py)
│   │   ├── system/             # Local filesystem scanning (SystemScanner, SystemFile)
│   │   ├── web/                # Bottle web app: handlers, serializers, auth, rate limit
│   │   │   ├── web_app.py            # WebApp (Bottle subclass), IHandler/IStreamHandler
│   │   │   ├── web_app_builder.py    # Assembles handlers + stream handlers
│   │   │   ├── web_app_job.py        # Thread wrapper for the server
│   │   │   ├── handler/              # Per-feature REST + SSE handlers
│   │   │   ├── serialize/            # JSON serializers for model/status/config/etc.
│   │   │   └── rate_limit.py
│   │   ├── tests/             # pytest suite (unittests/ + integration/)
│   │   └── docs/
│   ├── angular/                # Angular SPA frontend
│   │   └── src/app/
│   │       ├── pages/               # Route components (files/settings/logs/about/main)
│   │       ├── services/            # Feature + util + stream services
│   │       ├── common/              # Pipes, directives, scss partials, helpers
│   │       └── tests/               # Frontend mocks + fixtures
│   ├── e2e/                    # Playwright end-to-end tests (top-level)
│   ├── docker/                # Dockerfiles + build/stage/test image contexts
│   └── pyinstaller_hooks/     # PyInstaller hooks (frozen-package build)
├── scripts/                   # Release-metadata verification (Node .mjs)
├── docs/  doc/                # Project + image/brand docs
├── reports/                   # Generated reports
├── Makefile                   # Build/test/lint orchestration
├── package.json               # Root (release-metadata scripts, puppeteer dev dep)
└── .planning/                 # GSD planning, milestones, codebase maps
```

## Directory Purposes

**`src/python/` — backend daemon:**
- Purpose: The entire server-side application; runs as the `seedsyncarr` daemon.
- Contains: entry point, controller coordination layer, domain model, infrastructure adapters, web layer, tests.
- Key files: `seedsyncarr.py`, `controller/controller.py`, `web/web_app.py`.

**`src/python/controller/` — coordination layer (decomposed):**
- Purpose: Orchestrate the sync lifecycle. `Controller` is a thin coordinator; logic lives in collaborator managers.
- Contains: coordinator + managers + `scan/`, `extract/`, `delete/` sub-packages.
- Key files: `controller.py` (coordinator), `model_pipeline.py`, `command_processor.py`, `auto_delete_manager.py`.

**`src/python/common/` — cross-cutting:**
- Purpose: Shared infrastructure used by every layer.
- Contains: `context.py`, `config.py`, `status.py`, `persist.py`, `encryption.py`, `error.py`, `app_process.py`, `bounded_ordered_set.py`, `multiprocessing_logger.py`, `localization.py`, `constants.py`, `types.py`.
- Key files: `context.py`, `config.py`, `app_process.py`.

**`src/python/web/` — HTTP boundary:**
- Purpose: REST + SSE API, static HTML serving, auth, rate limiting.
- Contains: `web_app.py`, `web_app_builder.py`, `handler/` (one file per feature), `serialize/` (one serializer per resource), `rate_limit.py`.
- Key files: `web_app_builder.py`, `handler/controller.py`, `handler/webhook.py`.

**`src/python/model/` — domain model:**
- Purpose: Canonical file-state tree + diffing + listener events.
- Key files: `model.py`, `file.py`, `diff.py`.

**`src/angular/src/app/` — SPA:**
- Purpose: Browser UI.
- Contains: `pages/` (standalone route components, each with `.ts`/`.html`/`.scss`/`.spec.ts`), `services/` (grouped by domain: `files/`, `server/`, `settings/`, `logs/`, `autoqueue/`, `utils/`, `base/`), `common/` (pipes, directives, styles).
- Key files: `app.config.ts`, `routes.ts`, `pages/main/app.component.ts`.

**`src/python/tests/` — backend tests:**
- Purpose: pytest suite.
- Contains: `unittests/` (mirrors source tree) and `integration/` (`test_controller/`, `test_lftp/`, `test_web/`), plus `conftest.py`, `helpers/`, `utils.py`.

## Key File Locations

**Entry Points:**
- `src/python/seedsyncarr.py`: Daemon `main()` + `Seedsyncarr` service class.
- `src/python/scan_fs.py`: Standalone remote scanner executable.
- `src/python/web/web_app_job.py`: Web server thread.
- `src/python/controller/controller_job.py`: Controller thread.
- `src/angular/src/main.ts`: Frontend bootstrap.

**Configuration:**
- `src/python/common/config.py`: Config schema + (de)serialization.
- `src/python/common/constants.py`: App-wide constants/intervals.
- `src/angular/src/app/app.config.ts`: Angular providers/DI.
- `src/angular/src/app/routes.ts`: Frontend routes.
- `src/angular/angular.json`, `angular/package.json`, `angular/tsconfig.json`: Build config.
- `Makefile`, root `package.json`: Top-level build/test orchestration.

**Core Logic:**
- `src/python/controller/controller.py`: Coordinator.
- `src/python/controller/model_pipeline.py`: Model-update pipeline.
- `src/python/controller/model_builder.py`: Model reconciliation.
- `src/python/model/model.py`: Domain model.

**Testing:**
- `src/python/tests/`: Backend pytest (unit + integration).
- `src/angular/src/app/**/*.spec.ts`: Frontend Karma/Jasmine specs (co-located).
- `src/e2e/tests/`: Playwright E2E.

## Naming Conventions

**Backend (Python) files:**
- `snake_case.py` modules: `model_pipeline.py`, `auto_delete_manager.py`.
- Manager collaborators end in `_manager.py`; process classes in `_process.py`; persisted state in `_persist.py`; thread wrappers in `_job.py`.
- One primary class per module, `PascalCase` class names (`ModelPipeline`, `CommandProcessor`).
- Tests mirror source: `test_<module>.py` under `tests/unittests/test_<package>/`.

**Frontend (Angular) files:**
- Components: `<name>.component.ts` + `.html` + `.scss` + `.spec.ts` (co-located quad).
- Services: `<name>.service.ts`; plain models: `<name>.ts`; pipes: `<name>.pipe.ts`; directives: `<name>.directive.ts`.
- `PascalCase` classes (`FilesPageComponent`, `ModelFileService`); `kebab-case` filenames.

**Directories:**
- Python: `snake_case`, grouped by responsibility (`controller/scan/`, `web/handler/`).
- Angular: `kebab-case`, grouped by feature/domain under `pages/` and `services/`.

## Where to Add New Code

**New backend controller behavior (e.g., a new background activity):**
- Implement as a new collaborator manager in `src/python/controller/<name>_manager.py`.
- Construct it once in `Controller.__init__` (`src/python/controller/controller.py`) and inject instances — do NOT construct managers inside other collaborators (preserves test `mock.patch` binding).
- Export it from `src/python/controller/__init__.py`.
- Tests: `src/python/tests/unittests/test_controller/test_<name>_manager.py`.

**New REST/SSE endpoint:**
- Add or extend a handler in `src/python/web/handler/<feature>.py` (implement `IHandler.add_routes` or `IStreamHandler`).
- Register it in `src/python/web/web_app_builder.py` (`__init__` + `build()`).
- Add a serializer in `src/python/web/serialize/serialize_<resource>.py` if returning a new resource shape.
- Tests: `src/python/tests/unittests/test_web/test_handler/` and `tests/integration/test_web/`.

**New domain model field/behavior:**
- Modify `src/python/model/file.py` / `model.py`; remember `ModelFile` is frozen after insertion (build-new + diff, never mutate in place).
- Update `ModelBuilder` (`controller/model_builder.py`) and the matching serializer in `web/serialize/`.

**New frontend page:**
- Component quad under `src/angular/src/app/pages/<name>/<name>-page.component.{ts,html,scss,spec.ts}`.
- Register route in `src/angular/src/app/routes.ts` (both `ROUTE_INFOS` for nav and `ROUTES`).

**New frontend service:**
- `src/angular/src/app/services/<domain>/<name>.service.ts`; for SSE-backed services extend the base in `services/base/`.
- Provide it in `src/angular/src/app/app.config.ts`.

**Shared utilities:**
- Backend cross-cutting helpers: `src/python/common/` (export via `common/__init__.py`).
- Frontend pipes/directives/helpers: `src/angular/src/app/common/`.

## Special Directories

**`src/angular/dist/` and `src/angular/.angular/`:**
- Purpose: Angular build output / build cache.
- Generated: Yes. Committed: No (gitignored).

**`.planning/`:**
- Purpose: GSD planning artifacts, milestones, and these codebase maps.
- Generated: Partially (codebase maps generated). Committed: Yes.

**`src/docker/build/`, `src/docker/stage/`, `src/docker/test/`:**
- Purpose: Image build contexts for build/stage/test variants.
- Generated: No (source). Committed: Yes.

**`src/pyinstaller_hooks/`:**
- Purpose: PyInstaller hooks for the frozen single-binary package (`hook-patoolib.py`).
- Committed: Yes.

**`shield-claude-skill/`, `.aidesigner/`, `.turingmind/`, `.bg-shell/`:**
- Purpose: Tooling/skill subprojects and agent state (not part of the shipped app).
- Committed: Mixed (`shield-claude-skill/` is a nested git repo; agent-state dirs largely gitignored).

**`node_modules/` (root, `src/angular/`, `src/e2e/`):**
- Purpose: npm dependencies.
- Generated: Yes. Committed: No.

---

*Structure analysis: 2026-06-02*
