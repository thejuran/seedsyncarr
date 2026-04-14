# Codebase Structure

**Analysis Date:** 2026-02-03

## Directory Layout

```
seedsync/
├── src/
│   ├── angular/                    # Angular 19 frontend application
│   │   ├── src/
│   │   │   ├── app/                # Main application code
│   │   │   │   ├── pages/          # Page components (dashboard, settings, etc.)
│   │   │   │   ├── services/       # Business logic services
│   │   │   │   ├── common/         # Shared utilities and components
│   │   │   │   ├── tests/          # Unit tests and mocks
│   │   │   │   ├── app.config.ts   # Application configuration and DI setup
│   │   │   │   └── routes.ts       # Route definitions
│   │   │   ├── main.ts             # Angular bootstrap entry point
│   │   │   ├── styles.scss         # Global styles
│   │   │   └── assets/             # Images, icons, static files
│   │   ├── e2e/                    # E2E tests (Playwright)
│   │   ├── package.json            # npm dependencies
│   │   └── angular.json            # Angular CLI configuration
│   │
│   ├── python/                     # Python backend application
│   │   ├── seedsync.py             # Main entry point - service bootstrapper
│   │   ├── controller/             # Orchestration layer
│   │   │   ├── controller.py       # Main controller - orchestrates all operations
│   │   │   ├── controller_job.py   # ControllerJob wrapper for threading
│   │   │   ├── scan_manager.py     # Manages scanner processes
│   │   │   ├── lftp_manager.py     # Manages LFTP download process
│   │   │   ├── file_operation_manager.py  # Manages extract/delete operations
│   │   │   ├── model_builder.py    # Constructs ModelFile from scanner output
│   │   │   ├── controller_persist.py     # Persistence for downloaded/extracted/stopped files
│   │   │   ├── memory_monitor.py   # Memory leak detection
│   │   │   ├── auto_queue.py       # Auto-queue pattern matching logic
│   │   │   ├── scan/               # Scanner implementations (remote, local, active)
│   │   │   ├── extract/            # Extract operation helpers
│   │   │   └── delete/             # Delete operation helpers
│   │   │
│   │   ├── model/                  # Data models
│   │   │   ├── model.py            # Model container with listener pattern
│   │   │   ├── file.py             # ModelFile - immutable file representation
│   │   │   └── diff.py             # ModelDiff - change tracking
│   │   │
│   │   ├── web/                    # Web server layer (Bottle)
│   │   │   ├── web_app.py          # Bottle app with SSE streaming
│   │   │   ├── web_app_builder.py  # Web app factory
│   │   │   ├── web_app_job.py      # WebAppJob wrapper for threading
│   │   │   ├── handler/            # Request handlers
│   │   │   │   ├── server.py       # Server status endpoint
│   │   │   │   ├── controller.py   # Controller command endpoint
│   │   │   │   ├── config.py       # Configuration endpoint
│   │   │   │   ├── status.py       # Status endpoint
│   │   │   │   ├── auto_queue.py   # AutoQueue endpoint
│   │   │   │   └── stream_*.py     # Streaming handlers (model, log, status, heartbeat)
│   │   │   │
│   │   │   ├── serialize/          # Response serializers
│   │   │   │   ├── serialize.py    # Base serializer
│   │   │   │   ├── serialize_model.py     # ModelFile serialization
│   │   │   │   ├── serialize_status.py    # Status serialization
│   │   │   │   └── serialize_*.py  # Other domain serializers
│   │   │   │
│   │   │   └── utils.py            # Web utilities (StreamQueue, etc.)
│   │   │
│   │   ├── common/                 # Shared utilities
│   │   │   ├── config.py           # Configuration management
│   │   │   ├── context.py          # Application context (logger, config, status)
│   │   │   ├── status.py           # Application status model
│   │   │   ├── bounded_ordered_set.py  # LRU-evicting set implementation
│   │   │   ├── job.py              # Base Job class for threading
│   │   │   ├── app_process.py      # Subprocess wrapper
│   │   │   ├── multiprocessing_logger.py # Multiprocess logging
│   │   │   └── persist.py          # Persistence base class
│   │   │
│   │   ├── lftp/                   # LFTP integration
│   │   │   └── lftp.py             # LFTP process wrapper and status parser
│   │   │
│   │   ├── ssh/                    # SSH integration
│   │   │   └── ssh.py              # SSH connection handling
│   │   │
│   │   ├── system/                 # System utilities
│   │   │   └── system.py           # System information and utilities
│   │   │
│   │   ├── tests/                  # Test suite
│   │   │   ├── unittests/          # Unit tests (mocked dependencies)
│   │   │   └── integration/        # Integration tests (with fixtures)
│   │   │
│   │   ├── pyproject.toml          # Poetry dependencies
│   │   └── poetry.lock             # Locked dependency versions
│   │
│   ├── e2e/                        # End-to-end tests (Playwright)
│   │   ├── tests/                  # E2E test specs
│   │   ├── playwright.config.ts    # Playwright configuration
│   │   └── package.json            # npm dependencies for E2E
│   │
│   ├── docker/                     # Docker build and test configurations
│   │   ├── build/                  # Build image configurations
│   │   │   ├── deb/                # Debian package build
│   │   │   └── docker-image/       # Docker image build
│   │   ├── stage/                  # Runtime staging images
│   │   └── test/                   # Test image configurations
│   │
│   └── debian/                     # Debian package configuration
│       └── source/                 # .deb source files (control, postinst, etc.)
│
├── doc/                            # User documentation
│   ├── images/                     # Documentation images
│   └── licenses/                   # Third-party license files
│
├── planning docs/                  # Development planning documents
│   └── [session-based plans]
│
├── Makefile                        # Build orchestration (deb, docker, tests)
├── README.md                       # Project overview
└── SECURITY.md                     # Security guidelines
```

## Directory Purposes

**`src/angular/`:**
- Purpose: Single Page Application (SPA) frontend
- Contains: Angular components, services, routing, styles, tests
- Key files: `package.json` (version 1.0.0), `angular.json` (build config)

**`src/python/`:**
- Purpose: Backend service logic
- Contains: Controllers, models, web handlers, external integrations
- Key files: `seedsync.py` (main entry), `pyproject.toml` (Poetry config)

**`src/python/controller/`:**
- Purpose: Application orchestration and concurrency management
- Contains: State machines (scan/lftp/file ops), model updates, persistence
- Core logic for file syncing operations

**`src/python/web/`:**
- Purpose: HTTP API and real-time communication
- Contains: Request handlers, response serialization, SSE streaming
- All client communication happens through this layer

**`src/python/model/`:**
- Purpose: Data representation and change notification
- Contains: Immutable file objects, central model, diff tracking
- Enables listener-based real-time UI updates

**`src/python/common/`:**
- Purpose: Shared utilities and cross-cutting concerns
- Contains: Config, Context, Status, Logging, LRU collections
- Used by: All other backend modules

**`src/e2e/`:**
- Purpose: End-to-end testing (Playwright)
- Contains: Full application flow tests
- Tests entire system: frontend + backend + file operations

**`src/docker/`:**
- Purpose: Container and packaging
- Contains: Build stages for deb package and Docker image
- Used by: CI/CD to build and test releases

## Key File Locations

**Entry Points:**
- `src/python/seedsync.py`: Python backend entry point - initializes and runs the service
- `src/angular/src/main.ts`: Angular frontend entry point - bootstraps the app
- `src/angular/src/app/pages/main/app.component.ts`: Root Angular component

**Configuration:**
- `src/python/common/config.py`: Config class and schema
- `src/angular/src/app/app.config.ts`: Angular DI and provider setup
- `src/angular/angular.json`: Build and development configuration

**Core Logic:**
- `src/python/controller/controller.py`: Main orchestrator (1000+ lines)
- `src/python/controller/model_builder.py`: Transforms scanner output to ModelFile
- `src/python/model/model.py`: Central Model with listener pattern

**Testing:**
- `src/python/tests/unittests/`: Unit tests with mocked dependencies
- `src/python/tests/integration/`: Integration tests with real fixtures
- `src/angular/src/app/tests/`: Angular unit tests and mocks
- `src/e2e/tests/`: E2E test specifications

**Web API:**
- `src/python/web/handler/`: HTTP request handlers (config, controller, status, etc.)
- `src/python/web/serialize/`: Response serialization (JSON formatting)
- `src/python/web/web_app.py`: Bottle app with SSE streaming

**Frontend Services:**
- `src/angular/src/app/services/server/`: Backend communication (command, status)
- `src/angular/src/app/services/files/`: File model and filtering
- `src/angular/src/app/services/base/stream-service.registry.ts`: SSE stream handling

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `scan_manager.py`, `model_builder.py`)
- Angular components: `kebab-case.component.ts` (e.g., `file-list.component.ts`)
- Angular services: `kebab-case.service.ts` (e.g., `model-file.service.ts`)
- Test files: `[name].spec.ts` (Angular), `test_[name].py` (Python)
- Config files: `[name].config.ts` or `[name].config.js` (Angular)

**Directories:**
- Feature directories: `kebab-case/` or `snake_case/` (matching file naming)
- Test directories: `tests/`, `test/`, or co-located with source
- Shared utilities: `common/`, `utils/`, `shared/`

**Python Classes:**
- Controllers/Managers: `PascalCase` (e.g., `Controller`, `ScanManager`)
- Errors: `PascalCase` with "Error" suffix (e.g., `ControllerError`, `ConfigError`)
- Persistence: `PascalCase` with "Persist" suffix (e.g., `ControllerPersist`)
- Private members: `__double_underscore` prefix (e.g., `__model_lock`)

**TypeScript Classes:**
- Components: `PascalCase` with "Component" suffix (e.g., `FileListComponent`)
- Services: `PascalCase` with "Service" suffix (e.g., `ModelFileService`)
- Interfaces: `PascalCase` with "I" prefix (e.g., `IStreamService`)
- Types: `PascalCase` (e.g., `ModelFile`, `ServerStatus`)

## Where to Add New Code

**New HTTP Endpoint:**
1. Create handler in `src/python/web/handler/[name].py`
   - Inherit from `IHandler` or define handler function
   - Implement response logic
2. Register in `src/python/web/web_app_builder.py`
   - Call `builder.add_handler()` or `builder.add_post_handler()`
3. Add serializer in `src/python/web/serialize/serialize_[name].py` if needed
4. Test in `src/python/tests/integration/test_web/test_handler/test_[name].py`

**New Angular Page:**
1. Create page component in `src/angular/src/app/pages/[name]/[name]-page.component.ts`
   - Inherit from component base if needed
2. Register route in `src/angular/src/app/routes.ts`
   - Add RouteInfo to ROUTE_INFOS
   - Add route to ROUTES array
3. Create service in `src/angular/src/app/services/[category]/[name].service.ts` for logic
4. Add template in `[name]-page.component.html`
5. Add tests in `src/angular/src/app/tests/unittests/pages/[name]/`

**New Python Controller Command:**
1. Add Action to `Controller.Command.Action` enum in `src/python/controller/controller.py`
2. Implement command processing in `__process_command()` method
3. Handle state transition and callback in manager (ScanManager, LftpManager, FileOperationManager)
4. Add HTTP handler in `src/python/web/handler/[endpoint].py` to expose command
5. Test in `src/python/tests/integration/test_controller/test_[feature].py`

**New Utility/Helper:**
- General utilities: `src/python/common/[name].py` or `src/angular/src/app/services/utils/[name].ts`
- Domain-specific: Create in relevant module (e.g., `src/python/lftp/[name].py`)

**New Test:**
- Unit tests: `src/python/tests/unittests/test_[module]/` or `src/angular/src/app/tests/unittests/`
  - Mock external dependencies
  - Test single class/function in isolation
- Integration tests: `src/python/tests/integration/test_[module]/`
  - Use real fixtures, test with actual dependencies
- E2E tests: `src/e2e/tests/[feature].spec.ts`
  - Test complete user workflows through UI

## Special Directories

**`src/python/tests/unittests/`:**
- Purpose: Fast unit tests with mocked dependencies
- Generated: No (committed to git)
- Committed: Yes
- Run via: `pytest` or Make target `make run-tests-python`

**`src/python/tests/integration/`:**
- Purpose: Tests with real fixtures and dependencies
- Generated: No
- Committed: Yes
- Run via: `pytest` with integration marker

**`src/angular/src/app/tests/unittests/`:**
- Purpose: Angular unit tests using Jasmine/Karma
- Generated: No
- Committed: Yes
- Run via: `ng test` or `npm test`

**`src/angular/e2e/`:**
- Purpose: Angular E2E tests using Playwright
- Generated: No
- Committed: Yes
- Run via: `npm run e2e`

**`src/angular/.angular/cache/`:**
- Purpose: Angular CLI build cache
- Generated: Yes
- Committed: No (.gitignore)

**`src/docker/build/`:**
- Purpose: Docker build image configurations for creating artifacts
- Generated: No
- Committed: Yes

**`src/docker/stage/`:**
- Purpose: Docker staging images for runtime environments
- Generated: No
- Committed: Yes

**`src/docker/test/`:**
- Purpose: Docker test image configurations and test fixtures
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-02-03*
