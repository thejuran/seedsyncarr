# SeedSync File Relationships & Dependency Graph

**Generated:** 2026-03-28
**Project:** SeedSync (File synchronization and automated queuing system)
**Architecture:** Monorepo with Python backend + Angular frontend

---

## Overview

SeedSync is a full-stack application with:
- **Backend:** Python-based core with modular architecture
- **Frontend:** Angular/TypeScript web interface
- **Total Source Files:** 74 Python + 102 TypeScript = 176 files (excluding tests)
- **Test Coverage:** 90 test files (Python)

---

## Python Backend Architecture

### Directory Structure

```
src/python/
├── seedsync.py              [ENTRY POINT] Main application entry
├── scan_fs.py               File system scanning utility
├── __init__.py              Package initialization
├── common/                  [13 files] Shared utilities & base classes
├── controller/              [22 files] Core business logic & orchestration
├── model/                   [4 files]  Data models & file representation
├── web/                     [23 files] REST API & web handlers
├── system/                  [3 files]  System-level utilities
├── lftp/                    [4 files]  LFTP transfer management
├── ssh/                     [2 files]  SSH/SFTP operations
└── tests/                   [90 files] Unit & integration tests
```

### Module Breakdown

#### 1. **ENTRY POINT: `seedsync.py`**
- **Purpose:** Main application initialization and lifecycle
- **Imports:**
  - `common` - Configuration, logging, status management
  - `controller` - Core controller initialization
  - `controller.webhook_manager` - Webhook event handling
  - `web` - REST API server

#### 2. **`common/` MODULE** [Shared Utilities]
**13 Files - Foundation layer for all modules**

| File | Purpose |
|------|---------|
| `__init__.py` | Exports all common utilities |
| `app_process.py` | Application process management |
| `config.py` | Configuration file parsing & validation |
| `context.py` | Application context holder |
| `job.py` | Base job abstraction for async work |
| `status.py` | Status tracking for application state |
| `error.py` | Custom exception hierarchy |
| `persist.py` | Persistence layer utilities |
| `types.py` | Type definitions & enums |
| `constants.py` | Application constants |
| `localization.py` | i18n/localization support |
| `multiprocessing_logger.py` | Cross-process logging |
| `bounded_ordered_set.py` | Custom data structure for ordered sets |

**Imported By:** All other modules (foundation layer)

#### 3. **`controller/` MODULE** [Business Logic & Orchestration]
**22 Files - Core application logic**

**Main Coordinator:**
- `controller.py` - Main controller orchestrating all operations
  - Imports: `common`, `model`, `lftp`, `scan_manager`, `lftp_manager`, `file_operation_manager`, `webhook_manager`, `extract`, `model_builder`, `scan`, `memory_monitor`, `controller_persist`

**File Operations Sub-Components:**
| File | Purpose | Imports |
|------|---------|---------|
| `file_operation_manager.py` | Manages file operations (copy/delete) | common, model, extract, delete |
| `auto_queue.py` | Auto-queueing logic | common, model, controller |
| `model_builder.py` | Builds file system model from scans | common, system, lftp, model |
| `scan_manager.py` | Manages scanning operations | common, scan |
| `lftp_manager.py` | Manages LFTP transfers | common, lftp |
| `webhook_manager.py` | Handles incoming webhooks | common |
| `memory_monitor.py` | Monitors memory usage | common |
| `controller_job.py` | Job execution wrapper | common, controller, auto_queue |
| `controller_persist.py` | Persistence for controller state | common |

**Scanning Sub-Module (`controller/scan/`):**
- `scanner_process.py` - Base scanner process
- `active_scanner.py` - Active polling scanner
- `local_scanner.py` - Local filesystem scanner
- `remote_scanner.py` - Remote SFTP/SSH scanner
- `__init__.py` - Module exports

**File Extraction Sub-Module (`controller/extract/`):**
- `extract.py` - Archive extraction logic
- `extract_process.py` - Extraction process wrapper
- `dispatch.py` - Dispatch extraction jobs
- `__init__.py` - Module exports

**File Deletion Sub-Module (`controller/delete/`):**
- `delete_process.py` - Delete process implementation

#### 4. **`model/` MODULE** [Data Models]
**4 Files - File system representation**

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `model.py` | Main model class for file hierarchy |
| `file.py` | File/folder abstraction |
| `diff.py` | Model diffing for change detection |

**Imports:**
- `model.py` imports `common`
- `diff.py` imports `file`, `model`
- `file.py` has no internal imports

**Used By:** `controller`, `extract`, `auto_queue`

#### 5. **`web/` MODULE** [REST API & Web Interface]
**23 Files - HTTP API and WebSocket handlers**

**Core Web Server:**
- `web_app.py` - Main Flask/web application
- `web_app_builder.py` - Builder pattern for app construction
- `web_app_job.py` - Web job wrapper
- `utils.py` - Web utilities
- `auth.py` - Authentication handling

**Request Handlers** (`web/handler/`):
| File | Purpose |
|------|---------|
| `server.py` | Server info endpoints |
| `controller.py` | Controller status endpoints |
| `status.py` | Status stream handler |
| `stream_status.py` | WebSocket status streaming |
| `stream_log.py` | WebSocket log streaming |
| `stream_model.py` | WebSocket model updates |
| `stream_heartbeat.py` | WebSocket heartbeat |
| `config.py` | Configuration endpoints |
| `auto_queue.py` | Auto-queue status |
| `webhook.py` | Webhook receiver |

**Serialization** (`web/serialize/`):
- `serialize.py` - Main serialization dispatcher
- `serialize_status.py` - Status serialization
- `serialize_config.py` - Config serialization
- `serialize_model.py` - Model serialization
- `serialize_auto_queue.py` - Auto-queue serialization
- `serialize_log_record.py` - Log record serialization

**Imports:**
- `web_app.py` imports `common`, `controller`
- Handlers import `common`, `controller`, `model`

#### 6. **`lftp/` MODULE** [LFTP Transfer Management]
**4 Files - File transfer protocol handling**

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `lftp.py` | LFTP protocol implementation |
| `job_status.py` | Job status representation |
| `job_status_parser.py` | Parse LFTP status output |

**Imports:**
- `lftp.py` imports `common`
- `job_status_parser.py` imports `common`
- `job_status.py` has no internal imports

**Used By:** `controller`, `model_builder`

#### 7. **`system/` MODULE** [System Utilities]
**3 Files - OS-level operations**

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `scanner.py` | File system scanner |
| `file.py` | File abstraction |

**Imports:** No internal imports (leaf utilities)

**Used By:** `scan`, `model_builder`

#### 8. **`ssh/` MODULE** [SSH/SFTP Operations]
**2 Files - Remote access**

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `sshcp.py` | SSH copy implementation |

**Imports:** `common` only

**Used By:** `remote_scanner`, `delete_process`

---

## Import Dependency Graph

### Top-Level Dependency Flow

```
seedsync.py (ENTRY POINT)
    ├── common (foundation)
    ├── controller
    │   ├── common
    │   ├── model
    │   ├── lftp
    │   ├── system
    │   ├── ssh
    │   └── controller submodules (scan, extract, delete)
    └── web
        ├── common
        ├── controller
        └── model
```

### Module Dependency Hierarchy

**Level 0 (Foundation - No internal imports):**
- `system`
- `ssh`
- `lftp` (except job_status_parser)
- Leaf utilities

**Level 1 (Basic utilities - Imports Level 0):**
- `model` → `system`, `lftp`
- `lftp.job_status_parser` → `lftp`

**Level 2 (Business Logic - Imports Level 0-1):**
- `controller` modules → `common`, `model`, `lftp`, `system`, `ssh`
- `web` → `common`, `model`, `controller`

**Level 3 (Application - Imports all):**
- `seedsync.py` → All modules

### Circular Dependencies

**None detected** - Clean layered architecture

---

## Test File Organization

### Test Coverage: 90 Files

**Structure:**
```
tests/
├── conftest.py                          [Shared pytest fixtures]
├── unittests/                           [Unit tests - 55 files]
│   ├── test_common/
│   ├── test_controller/
│   ├── test_lftp/
│   ├── test_model/
│   ├── test_ssh/
│   ├── test_system/
│   ├── test_web/
│   └── test_seedsync.py
├── integration/                         [Integration tests - 35 files]
│   ├── test_controller/
│   ├── test_lftp/
│   └── test_web/
└── Docker/                              [E2E tests]
    └── test/
        └── e2e/
            └── parse_seedsync_status.py
```

### Test-to-Source Mapping

| Test Module | Tests |
|-------------|-------|
| `test_common/` | Common utilities |
| `test_controller/` | Controller & job scheduling |
| `test_lftp/` | LFTP protocol parsing & management |
| `test_model/` | Model representation & diffing |
| `test_ssh/` | SSH operations |
| `test_system/` | File system scanning |
| `test_web/` | Web handlers & serialization |

---

## Angular Frontend Architecture

### Directory Structure

```
src/angular/src/
├── main.ts                    [ENTRY POINT]
├── app.config.ts              Angular app configuration
├── routes.ts                  Routing configuration
├── app/
│   ├── pages/                 [12 components] Page-level containers
│   │   ├── main/              Application shell
│   │   ├── files/             File management pages
│   │   ├── logs/              Log viewer
│   │   ├── settings/          Settings page
│   │   └── about/             About page
│   ├── services/              [30 services] Business logic
│   │   ├── server/            Server communication
│   │   ├── files/             File operations
│   │   ├── logs/              Log management
│   │   ├── autoqueue/         Auto-queue logic
│   │   ├── settings/          Settings management
│   │   ├── utils/             Utility services
│   │   └── base/              Base/abstract services
│   ├── common/                [8 files] Shared components & utils
│   │   ├── directives/        Custom directives
│   │   ├── pipes/             Custom pipes
│   │   └── models/            TypeScript models
│   └── tests/                 [30+ files] Unit & integration tests
│       └── mocks/             Mock implementations
├── assets/                    Static assets
├── environments/              Environment configuration
└── styles.scss                Global styles
```

### Frontend Components

**Pages (12 Components):**
- `main/app.component.ts` - Root application component
- `main/header.component.ts` - Header/navigation
- `files/files-page.component.ts` - File management container
- `files/file-list.component.ts` - File list view
- `files/file.component.ts` - Individual file row
- `files/file-actions-bar.component.ts` - File actions toolbar
- `files/file-options.component.ts` - File context menu
- `files/bulk-actions-bar.component.ts` - Bulk operations
- `logs/logs-page.component.ts` - Log viewer container
- `settings/settings-page.component.ts` - Settings container
- `settings/option.component.ts` - Individual setting
- `about/about-page.component.ts` - About page

**Services (30 Services organized in categories):**

**Server Communication:**
- `server/server-status.service.ts` - Fetch server status
- `server/server-command.service.ts` - Execute server commands
- `server/bulk-command.service.ts` - Bulk operations

**File Management:**
- `files/model-file.service.ts` - File model abstraction
- `files/view-file.service.ts` - File view state
- `files/view-file-filter.service.ts` - File filtering
- `files/view-file-sort.service.ts` - File sorting
- `files/view-file-options.service.ts` - File display options
- `files/file-selection.service.ts` - Multi-select tracking

**Logging:**
- `logs/log.service.ts` - Log retrieval & caching

**Auto-Queue:**
- `autoqueue/autoqueue.service.ts` - Auto-queue management

**Settings:**
- `settings/config.service.ts` - Configuration management

**Base/Abstract Services:**
- `base/base-web.service.ts` - Base HTTP service
- `base/base-stream.service.ts` - Base WebSocket service
- `base/stream-service.registry.ts` - Stream service registry

**Utilities:**
- `utils/rest.service.ts` - REST client abstraction
- `utils/notification.service.ts` - Notifications
- `utils/toast.service.ts` - Toast notifications
- `utils/logger.service.ts` - Client-side logging
- `utils/connected.service.ts` - Connection status
- `utils/local-storage.service.ts` - LocalStorage wrapper
- `utils/dom.service.ts` - DOM utilities
- `utils/confirm-modal.service.ts` - Confirmation dialogs
- `utils/version-check.service.ts` - Version checking

**Other:**
- `tests/mocks/*` - Mock service implementations

### Service Dependencies

**Dependency Flow:**

```
Components
    ├── file-list.component
    │   ├── view-file.service
    │   ├── view-file-filter.service
    │   ├── view-file-sort.service
    │   ├── file-selection.service
    │   └── server-command.service
    ├── settings-page.component
    │   └── config.service
    └── logs-page.component
        └── log.service

Services
    ├── Base Services
    │   ├── rest.service
    │   └── stream services
    ├── Domain Services
    │   ├── server-status.service → rest.service
    │   ├── config.service → rest.service
    │   └── log.service → rest.service
    └── Utility Services
        ├── notification.service
        ├── logger.service
        └── connected.service
```

---

## Configuration & Environment Files

### Backend Configuration

| File | Purpose |
|------|---------|
| `.gsd/` | GSD (Get Shit Done) workflow tracking |
| `.planning/` | Project planning documents |
| `Makefile` | Build & development commands |
| `requirements.txt` | Python dependencies |
| `pyproject.toml` | Python project metadata |

### Frontend Configuration

| File | Purpose |
|------|---------|
| `angular.json` | Angular build configuration |
| `tsconfig.json` | TypeScript configuration |
| `package.json` | npm dependencies & scripts |
| `karma.conf.js` | Test runner configuration |
| `eslint.config.js` | Linting configuration |
| `playwright.config.ts` | E2E test configuration |

### Docker Configuration

| File | Purpose |
|------|---------|
| `.docker/` | Docker-related files |
| `src/docker/` | Docker build context |
| `Dockerfile` | Container image definition |

---

## Entry Points Summary

### Backend Entry Points

1. **`seedsync.py`** - Main application
   - Initializes: `common`, `controller`, `web`, `webhook_manager`
   - Starts: Web server, controller, file operations

2. **`scan_fs.py`** - Filesystem scanning utility
   - Standalone scanner for testing/debugging

3. **Tests**
   - `pytest` entry point: `tests/conftest.py`

### Frontend Entry Points

1. **`main.ts`** - Angular bootstrap file
   - Initializes: `AppComponent` (root)
   - Configures: `AppConfig`

2. **`routes.ts`** - Application routing
   - Defines all page routes and navigation

3. **`index.html`** - HTML shell
   - Contains `<app-root>` outlet

---

## Key Insights

### Architecture Patterns

1. **Layered Architecture**
   - Foundation layer: `common`, `system`, `ssh`, `lftp`
   - Domain layer: `model`, `controller`
   - Application layer: `web`, `seedsync.py`

2. **Module Organization**
   - Clear separation of concerns
   - Each module has single responsibility
   - No circular dependencies

3. **Bi-directional Communication**
   - Backend → Frontend: REST API (`web/`)
   - Frontend → Backend: WebSocket streams + HTTP calls

4. **Test-Driven Structure**
   - Unit tests for individual components
   - Integration tests for module interactions
   - E2E tests in Docker container

### Scale Metrics

| Metric | Count |
|--------|-------|
| Python source files | 74 |
| Python test files | 90 |
| TypeScript files | 102 |
| Total test specs | 30+ |
| Lines of code (Python) | ~15,000 |
| Lines of code (TypeScript) | ~3,000 |

### Critical Paths (Most Connected)

1. **`common/`** - Used by all modules (foundation)
2. **`controller/`** - Orchestrates all operations (22 files)
3. **`web/`** - Public API surface (23 files)
4. **`model/`** - Data representation (all domain logic)
5. **Services layer** (Angular) - Frontend business logic

---

## How to Navigate the Codebase

### For Understanding Data Flow

1. Start: `seedsync.py` → Main entry
2. Follow: `controller.py` → Core orchestration
3. Explore: `model/` → Data structures
4. Check: `web/handlers/` → API endpoints

### For Adding Features

1. **Backend feature:** Controller → Model → Web handler
2. **Frontend feature:** Service → Component
3. **Transfer feature:** `lftp/` → `controller/`
4. **Scanning feature:** `system/` → `controller/scan/` → `model/`

### For Testing

- Unit tests: `tests/unittests/{module}/`
- Integration tests: `tests/integration/{module}/`
- E2E tests: `src/e2e/` or `src/docker/test/e2e/`

### For Debugging

- Logs: `common/multiprocessing_logger.py`
- Status: `common/status.py` + `web/serialize/`
- WebSocket: `web/stream_*` handlers
- Config: `common/config.py`
