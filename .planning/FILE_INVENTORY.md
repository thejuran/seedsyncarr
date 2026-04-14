# SeedSync Complete File Inventory

## Python Backend Files

### Entry Points
- `src/python/seedsync.py` - Main application entry point
- `src/python/scan_fs.py` - Standalone filesystem scanner utility

### Common Module (13 files)
Foundation layer - utilities used by all other modules.

```
common/
├── __init__.py              [Exports all common utilities]
├── app_process.py           [Application process management]
├── bounded_ordered_set.py   [Custom ordered set data structure]
├── config.py                [Configuration file parsing & validation]
├── constants.py             [Application constants]
├── context.py               [Application context holder]
├── error.py                 [Custom exception hierarchy]
├── job.py                   [Base job/task abstraction]
├── localization.py          [i18n localization support]
├── multiprocessing_logger.py [Cross-process logging]
├── persist.py               [Persistence utilities]
├── status.py                [Status tracking system]
└── types.py                 [Type definitions & enums]
```

### Controller Module (22 files)
Core business logic and orchestration.

**Main Coordinator:**
```
controller/
├── __init__.py              [Module exports]
├── controller.py            [Main orchestrator - calls all managers]
├── controller_job.py        [Job wrapper for async execution]
├── controller_persist.py    [State persistence]
├── auto_queue.py            [Auto-queueing logic]
├── memory_monitor.py        [Memory usage monitoring]
├── model_builder.py         [Builds file model from scan results]
├── scan_manager.py          [Manages scanning operations]
├── lftp_manager.py          [Manages LFTP transfers]
├── file_operation_manager.py [Handles copy/delete operations]
└── webhook_manager.py       [Webhook event handling]
```

**Scanning Sub-Module:**
```
controller/scan/
├── __init__.py              [Exports scanner classes]
├── scanner_process.py       [Base scanner process]
├── active_scanner.py        [Active polling scanner]
├── local_scanner.py         [Local filesystem scanner]
└── remote_scanner.py        [Remote SFTP/SSH scanner]
```

**File Extraction Sub-Module:**
```
controller/extract/
├── __init__.py              [Exports extract classes]
├── extract.py               [Archive extraction logic]
├── extract_process.py       [Extraction process wrapper]
└── dispatch.py              [Dispatch extraction jobs]
```

**File Deletion Sub-Module:**
```
controller/delete/
├── __init__.py
└── delete_process.py        [Delete process implementation]
```

### Model Module (4 files)
Data models for file/folder representation.

```
model/
├── __init__.py              [Module exports]
├── model.py                 [Main file hierarchy model]
├── file.py                  [File/folder abstraction]
└── diff.py                  [Model diffing for change detection]
```

### Web Module (23 files)
REST API and WebSocket handlers.

**Core Web Application:**
```
web/
├── __init__.py
├── web_app.py               [Main Flask application]
├── web_app_builder.py       [Builder pattern for app construction]
├── web_app_job.py           [Web job execution wrapper]
├── auth.py                  [Authentication handling]
└── utils.py                 [Web utilities]
```

**Request Handlers:**
```
web/handler/
├── __init__.py              [Handler exports]
├── server.py                [Server info endpoints]
├── controller.py            [Controller status endpoints]
├── status.py                [Status information endpoint]
├── stream_status.py         [WebSocket status streaming]
├── stream_log.py            [WebSocket log streaming]
├── stream_model.py          [WebSocket model update streaming]
├── stream_heartbeat.py      [WebSocket heartbeat]
├── config.py                [Configuration endpoints]
├── auto_queue.py            [Auto-queue status endpoints]
└── webhook.py               [Webhook receiver]
```

**Serialization (Response Formatting):**
```
web/serialize/
├── __init__.py              [Serialization exports]
├── serialize.py             [Main serialization dispatcher]
├── serialize_status.py      [Status serialization]
├── serialize_config.py      [Configuration serialization]
├── serialize_model.py       [File model serialization]
├── serialize_auto_queue.py  [Auto-queue serialization]
└── serialize_log_record.py  [Log record serialization]
```

### LFTP Module (4 files)
File transfer protocol handling.

```
lftp/
├── __init__.py              [Module exports]
├── lftp.py                  [LFTP protocol implementation]
├── job_status.py            [Job status data class]
└── job_status_parser.py     [Parse LFTP output]
```

### System Module (3 files)
OS-level file operations.

```
system/
├── __init__.py              [Module exports]
├── scanner.py               [Filesystem scanner]
└── file.py                  [File abstraction]
```

### SSH Module (2 files)
Remote access via SSH/SFTP.

```
ssh/
├── __init__.py              [Module exports]
└── sshcp.py                 [SSH copy implementation]
```

---

## TypeScript/Angular Frontend Files

### Configuration Files
- `src/angular/src/main.ts` - Application bootstrap entry point
- `src/angular/src/app.config.ts` - Angular application configuration
- `src/angular/src/routes.ts` - Application routing configuration
- `src/angular/src/index.html` - HTML shell
- `src/angular/src/styles.scss` - Global styles
- `src/angular/src/polyfills.ts` - Browser compatibility

### Page Components (12 files + 12+ sub-components)

**Main Container:**
```
app/pages/main/
├── app.component.ts         [Root application component]
├── app.component.html
├── app.component.scss
├── header.component.ts      [Header/navigation bar]
├── header.component.html
└── header.component.scss
```

**File Management Pages:**
```
app/pages/files/
├── files-page.component.ts  [File management container]
├── files-page.component.html
├── file-list.component.ts   [File list view]
├── file-list.component.html
├── file.component.ts        [Individual file row]
├── file.component.html
├── file-actions-bar.component.ts [File action buttons]
├── file-options.component.ts [Context menu]
├── bulk-actions-bar.component.ts [Bulk operation toolbar]
└── [corresponding .html/.scss files]
```

**Logs Page:**
```
app/pages/logs/
├── logs-page.component.ts   [Log viewer container]
├── logs-page.component.html
└── logs-page.component.scss
```

**Settings Page:**
```
app/pages/settings/
├── settings-page.component.ts [Settings container]
├── settings-page.component.html
├── option.component.ts      [Individual setting option]
└── [corresponding .html/.scss files]
```

**About Page:**
```
app/pages/about/
├── about-page.component.ts  [About page]
└── [corresponding .html/.scss files]
```

### Services (30 files)

**Base/Abstract Services (3 files):**
```
app/services/base/
├── base-web.service.ts      [Base HTTP service]
├── base-stream.service.ts   [Base WebSocket service]
└── stream-service.registry.ts [Registry for stream services]
```

**Server Communication (3 services):**
```
app/services/server/
├── server-status.service.ts     [Fetch server status]
├── server-command.service.ts    [Execute server commands]
└── bulk-command.service.ts      [Bulk command execution]
```

**File Management (6 services):**
```
app/services/files/
├── model-file.service.ts        [File model abstraction]
├── view-file.service.ts         [File view state management]
├── view-file-filter.service.ts  [File filtering logic]
├── view-file-sort.service.ts    [File sorting logic]
├── view-file-options.service.ts [File display options]
└── file-selection.service.ts    [Multi-select tracking]
```

**Logging (1 service):**
```
app/services/logs/
└── log.service.ts           [Log retrieval & caching]
```

**Auto-Queue (1 service):**
```
app/services/autoqueue/
└── autoqueue.service.ts     [Auto-queue management]
```

**Settings (1 service):**
```
app/services/settings/
└── config.service.ts        [Configuration management]
```

**Utilities (14 services):**
```
app/services/utils/
├── rest.service.ts              [REST HTTP client]
├── notification.service.ts      [User notifications]
├── toast.service.ts             [Toast messages]
├── logger.service.ts            [Client-side logging]
├── connected.service.ts         [Connection status]
├── local-storage.service.ts     [LocalStorage wrapper]
├── dom.service.ts               [DOM utilities]
├── confirm-modal.service.ts     [Confirmation dialogs]
└── version-check.service.ts     [Version compatibility check]
```

### Common Module (8 files)

**Shared Components & Utilities:**
```
app/common/
├── [directives/]            [Custom directives]
├── [pipes/]                 [Custom pipes]
├── [models/]                [TypeScript interfaces/classes]
└── [utilities/]             [Shared utility functions]
```

### Tests (30+ files)

**Mock Services:**
```
app/tests/mocks/
├── mock-model-file.service.ts
├── mock-rest.service.ts
├── mock-storage.service.ts
├── mock-stream-service.registry.ts
├── mock-view-file-options.service.ts
└── mock-view-file.service.ts
```

**Spec Files:**
```
Located alongside source files with .spec.ts extension:
├── app.component.spec.ts
├── [page].component.spec.ts
├── [service].service.spec.ts
└── [feature].spec.ts
```

### Static Assets
```
assets/
├── [images/]
├── [icons/]
└── [other static files]
```

### Environment Configuration
```
environments/
├── environment.ts           [Development config]
└── environment.prod.ts      [Production config]
```

---

## Test Files Structure

### Python Tests (90 files)

**Configuration:**
```
tests/
└── conftest.py              [Shared pytest fixtures & configuration]
```

**Unit Tests (55 files):**
```
tests/unittests/
├── test_common/             [Common utilities tests]
├── test_controller/         [Controller tests]
│   ├── test_scan/
│   ├── test_extract/
│   └── [individual manager tests]
├── test_lftp/               [LFTP tests]
├── test_model/              [Model tests]
├── test_ssh/                [SSH tests]
├── test_system/             [System/filesystem tests]
├── test_web/                [Web handler tests]
│   ├── test_handler/
│   └── test_serialize/
└── test_seedsync.py         [Main app tests]
```

**Integration Tests (35 files):**
```
tests/integration/
├── test_controller/         [Controller integration tests]
├── test_lftp/               [LFTP integration tests]
└── test_web/                [Web server integration tests]
```

**E2E Tests:**
```
src/docker/test/e2e/
└── parse_seedsync_status.py [End-to-end tests in Docker]
```

### TypeScript Tests (30+ files)
- Located alongside source files as `*.spec.ts`
- Organized by module mirroring source structure

---

## Configuration & Build Files

### Project Configuration
```
ROOT/
├── Makefile                 [Build targets & development commands]
├── .gitignore               [Git ignore rules]
├── README.md                [Project overview]
├── LICENSE.txt              [License]
├── SECURITY.md              [Security policy]
└── ACKNOWLEDGMENTS.md       [Acknowledgments]
```

### Documentation
```
doc/                         [Project documentation]
.planning/                   [GSD project planning]
.gsd/                        [GSD workflow state]
```

### Backend Build/Config
```
src/docker/                  [Docker configuration]
src/pyinstaller_hooks/       [PyInstaller hooks]
build/                       [Build artifacts]
```

### Frontend Build/Config
```
src/angular/
├── angular.json             [Angular build config]
├── tsconfig.json            [TypeScript configuration]
├── karma.conf.js            [Test runner config]
├── eslint.config.js         [Linting rules]
├── playwright.config.ts     [E2E test config]
├── package.json             [npm dependencies]
├── package-lock.json        [Locked versions]
└── .angular/                [Angular cache]
```

---

## Quick File Reference by Purpose

### "I need to add a REST endpoint"
Edit: `src/python/web/handler/{feature}.py`
Then: Register in `src/python/web/web_app_builder.py`

### "I need to add business logic"
Edit: `src/python/controller/{manager}.py` (choose appropriate manager)
Or: Create new manager following existing pattern

### "I need to handle a new file operation"
Edit: `src/python/controller/file_operation_manager.py`
Add extraction: `src/python/controller/extract/extract.py`
Add deletion: `src/python/controller/delete/delete_process.py`

### "I need to add scanning capability"
Edit: `src/python/controller/scan/{scanner_type}.py`
Register in: `src/python/controller/scan_manager.py`

### "I need to add a new page"
Create: `src/angular/src/app/pages/{name}/{name}-page.component.ts`
Register in: `src/angular/src/app/routes.ts`
Create service: `src/angular/src/app/services/{category}/new.service.ts`

### "I need to add a new service"
Create: `src/angular/src/app/services/{category}/new.service.ts`
Extend: `BaseWebService` or `BaseStreamService`
Inject in: Components that need it

### "I need to test something"
Python unit test: `tests/unittests/test_{module}/test_{feature}.py`
Python integration: `tests/integration/test_{module}/test_{feature}.py`
TypeScript test: `src/angular/src/app/{path}/{file}.spec.ts`

---

## Total File Count

| Category | Count |
|----------|-------|
| Python source files | 74 |
| Python test files | 90 |
| TypeScript source files | 102 |
| TypeScript test files | 30+ |
| Configuration files | 10+ |
| Documentation files | 5+ |
| Total | 300+ |

---

## Key File Relationships

### Data Flow: File Scan
```
1. controller/scan_manager.py (initiates)
2. controller/scan/{scanner}.py (runs scan)
3. system/scanner.py (performs scan)
4. controller/model_builder.py (builds model)
5. model/model.py (stores result)
6. web/serialize/serialize_model.py (formats)
7. web/stream_model.py (sends to client)
```

### Data Flow: File Transfer
```
1. web/handler/controller.py (receives request)
2. controller/file_operation_manager.py (decides action)
3. controller/lftp_manager.py (manages transfer)
4. lftp/lftp.py (executes transfer)
5. lftp/job_status_parser.py (parses output)
6. web/stream_status.py (sends updates)
```

### Data Flow: Archive Extraction
```
1. web/handler/controller.py (receives request)
2. controller/file_operation_manager.py (initiates)
3. controller/extract/dispatch.py (dispatches)
4. controller/extract/extract_process.py (runs process)
5. controller/extract/extract.py (extracts)
6. model/model.py (updates)
7. web/stream_model.py (notifies client)
```

---

## Dependency Summary by File

### Most Connected Files
1. `controller/controller.py` - Imports 10+ modules, imported by: seedsync, web, tests
2. `common/__init__.py` - Imported by all modules (foundation)
3. `web/web_app.py` - Imports controller, model, common
4. `model/model.py` - Imports common, file, diff

### Hub Files (imported by many)
- `common/status.py` - Status tracking
- `model/model.py` - Data representation
- `controller/controller.py` - Orchestration
- `web/serialize/serialize.py` - Response formatting

### Leaf Files (import nothing internal)
- `system/file.py`
- `system/scanner.py`
- `ssh/sshcp.py`
- `lftp/job_status.py`
- `model/file.py`

---

Generated: 2026-03-28
