<!-- refreshed: 2026-06-09 -->
# Architecture

**Analysis Date:** 2026-06-09

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        Angular SPA (browser)                         │
├──────────────────────┬──────────────────────┬───────────────────────┤
│   Page Components    │   Domain Services    │   Stream Dispatch     │
│ `src/angular/src/app │ `src/angular/src/app │ `src/angular/src/app/ │
│  /pages/`            │  /services/`         │  services/base/`      │
└──────────┬───────────┴──────────┬───────────┴──────────┬────────────┘
           │  REST (Bearer token) │                      │ SSE /server/stream
           ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Bottle Web Layer (WebAppJob thread)                     │
│  `src/python/web/` — WebApp + IHandler routes + IStreamHandler SSE   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Controller.Command queue / shared Model
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│            Controller (ControllerJob thread)                         │
│  `src/python/controller/` — managers, model pipeline, auto queue,    │
│  webhook import matching, auto-delete                                │
└───────┬──────────────────┬──────────────────┬───────────────────────┘
        │ multiprocessing  │ subprocess       │ Queue (web→controller)
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌──────────────────────────────┐
│ ScannerProcess│  │ lftp / sshcp  │  │ WebhookManager               │
│ `controller/  │  │ `src/python/  │  │ `controller/                 │
│  scan/`       │  │  lftp/`,`ssh/`│  │  webhook_manager.py`         │
└───────┬───────┘  └───────┬───────┘  └──────────────────────────────┘
        │ SSH + scanfs     │ SFTP mirror
        ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│       Remote seedbox (scanfs binary pushed over SSH) + local disk    │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `Seedsyncarr` | Service bootstrap, config/persist loading, main-thread supervision loop, restart/exit handling | `src/python/seedsyncarr.py` |
| `Controller` | Top-level orchestration: command queue, model ownership, manager coordination | `src/python/controller/controller.py` |
| `ModelPipeline` | scan→build→diff→apply model update pipeline | `src/python/controller/model_pipeline.py` |
| `ModelBuilder` | Combines scan results + lftp status + extract status into ModelFiles | `src/python/controller/model_builder.py` |
| `ScanManager` | Owns local/remote/active `ScannerProcess` instances | `src/python/controller/scan_manager.py` |
| `LftpManager` | Wraps the `Lftp` client used for downloads | `src/python/controller/lftp_manager.py` |
| `FileOperationManager` | Extract and delete operations (dispatch to processes) | `src/python/controller/file_operation_manager.py` |
| `CommandProcessor` | Executes queued `Controller.Command` actions | `src/python/controller/command_processor.py` |
| `AutoQueue` | Auto-queues newly discovered remote files (pattern support) | `src/python/controller/auto_queue.py` |
| `WebhookManager` | Thread-safe queue bridging webhook POSTs (web thread) to import matching (controller thread) | `src/python/controller/webhook_manager.py` |
| `AutoDeleteManager` | Schedules safe-delete of imported files after delay (dry-run support) | `src/python/controller/auto_delete_manager.py` |
| `MemoryMonitor` | Tracks process memory usage | `src/python/controller/memory_monitor.py` |
| `Model` / `ModelFile` / `ModelDiff` | In-memory file-state store with listener pattern and diffing | `src/python/model/model.py`, `src/python/model/file.py`, `src/python/model/diff.py` |
| `Lftp` / `LftpJobStatusParser` | lftp process driver and status-output parser | `src/python/lftp/lftp.py`, `src/python/lftp/job_status_parser.py` |
| `Sshcp` | SSH/SCP wrapper used by remote scanner | `src/python/ssh/sshcp.py` |
| `SystemScanner` | Filesystem tree scanner (shared by local scan and `scan_fs.py`) | `src/python/system/scanner.py` |
| `WebApp` / `WebAppBuilder` | Bottle app, route registration, Bearer auth, SSE multiplexing | `src/python/web/web_app.py`, `src/python/web/web_app_builder.py` |
| Handlers | One `IHandler` per API surface (controller, config, autoqueue, server, status, webhook) | `src/python/web/handler/` |
| Serializers | Convert model/config/status/log to SSE/JSON payloads | `src/python/web/serialize/` |
| `StreamDispatchService` | Single SSE connection, dispatches events to registered Angular stream services | `src/angular/src/app/services/base/stream-service.registry.ts` |
| `ViewFileService` | Frontend store: transforms `ModelFile` → sorted/filtered `ViewFile` list | `src/angular/src/app/services/files/view-file.service.ts` |
| `scan_fs.py` | Standalone scanner CLI, frozen with PyInstaller and pushed to the remote host | `src/python/scan_fs.py` |

## Pattern Overview

**Overall:** Threaded daemon with a central in-memory Model (observer pattern), process-isolated scanners, and a Bottle REST + SSE web layer serving an Angular SPA. Frontend mirrors the backend model via an SSE-driven observable-store pattern.

**Key Characteristics:**
- Single source of truth: the `Model` in `src/python/model/model.py`, guarded by one `threading.Lock` owned by `Controller`
- Listener/observer pattern everywhere: `IModelListener` (backend), `IStreamService` (frontend), `ExtractListener`
- Command pattern for UI actions: `Controller.Command` with `ICallback` success/failure callbacks executed in the controller thread
- Heavy work isolated in `multiprocessing` processes (`AppProcess` base, `src/python/common/app_process.py`) with exception propagation via `ExceptionWrapper`
- Collaborator injection: `Controller.__init__` constructs all managers and passes them into `ModelPipeline` (do NOT construct managers inside collaborators)

## Layers

**Common layer:**
- Purpose: Shared infrastructure — config, context, persistence, status, jobs, processes, encryption, logging
- Location: `src/python/common/`
- Contains: `Config` (INI-backed with encrypted secret fields), `Context` (DI container: logger, config, args, status), `Persist` base class, `Job` (thread base), `AppProcess` (process base), `MultiprocessingLogger`, `BoundedOrderedSet`
- Depends on: stdlib only (plus `tblib`)
- Used by: every other Python package

**Domain layer (model/system/lftp/ssh):**
- Purpose: Pure domain types and external-tool drivers
- Location: `src/python/model/`, `src/python/system/`, `src/python/lftp/`, `src/python/ssh/`
- Contains: `Model`/`ModelFile`/`ModelDiff`, `SystemFile`/`SystemScanner`, `Lftp` + status parser, `Sshcp`
- Depends on: `common`
- Used by: `controller`, `web`, `scan_fs.py`

**Controller layer:**
- Purpose: Business logic and orchestration; owns the model and all background work
- Location: `src/python/controller/` (sub-packages `scan/`, `extract/`, `delete/`)
- Depends on: `common`, `model`, `lftp`, `ssh`, `system`
- Used by: `web` (via `Controller` public API), entry point

**Web layer:**
- Purpose: HTTP/SSE interface; no business logic — translates requests to `Controller.Command`s and model state to serialized streams
- Location: `src/python/web/` (`handler/` routes, `serialize/` payload builders)
- Depends on: `common`, `controller`, `model`
- Used by: entry point (via `WebAppBuilder`)

**Frontend layer:**
- Purpose: Angular SPA (standalone components, no NgModules)
- Location: `src/angular/src/app/` — `pages/` (components), `services/` (state + IO), `common/` (pipes, directives, constants)
- Depends on: backend REST + SSE API only

## Data Flow

### Primary Sync Flow (remote file → local disk)

1. `RemoteScannerProcess` copies the frozen `scanfs` binary to the seedbox over SSH and runs it (`src/python/controller/scan/remote_scanner.py`, `src/python/ssh/sshcp.py`)
2. `ScanManager` collects `ScannerResult`s from process queues (`src/python/controller/scan_manager.py`)
3. `ModelPipeline.build_and_apply_model` merges remote scan + local scan + lftp status + extract results via `ModelBuilder`, diffs against current `Model`, applies diff under `model_lock` (`src/python/controller/model_pipeline.py`)
4. `Model` notifies `IModelListener`s (`src/python/model/model.py`)
5. `AutoQueue` (a model listener) queues new remote files for download (`src/python/controller/auto_queue.py`)
6. `CommandProcessor` executes QUEUE → `LftpManager` starts an lftp mirror job (`src/python/controller/lftp_manager.py`, `src/python/lftp/lftp.py`)
7. `ActiveScannerProcess` + lftp status feed download progress back into the model each controller cycle (`src/python/controller/scan/active_scanner.py`, `Controller.process()` at `src/python/controller/controller.py:236`)

### Webhook Import → Safe-Delete Flow (the *arr differentiator)

1. Sonarr/Radarr POST to `/server/webhook/sonarr` or `/server/webhook/radarr` — HMAC-verified, rate-limited 60/60s (`src/python/web/handler/webhook.py:40-41`)
2. `WebhookManager.enqueue_import()` puts `(source, file_name)` on a thread-safe `Queue` from the web thread (`src/python/controller/webhook_manager.py`)
3. Controller thread calls `WebhookManager.process()` each cycle with a lowercased name→root lookup; matches child or root file names case-insensitively (`__check_webhook_imports` at `src/python/controller/controller.py:512`)
4. Matched files get import status set and `AutoDeleteManager` schedules deletion after `config.autodelete.delay_seconds` (`__schedule_auto_delete` at `src/python/controller/controller.py:590`, `src/python/controller/auto_delete_manager.py`)
5. Delete executes via `FileOperationManager`/`DeleteProcess` (`src/python/controller/delete/delete_process.py`)

### UI Command Flow

1. Angular `ServerCommandService` POSTs e.g. `/server/command/queue/<file_name>` (`src/angular/src/app/services/server/server-command.service.ts`)
2. `authInterceptor` attaches Bearer token (`src/angular/src/app/services/utils/auth.interceptor.ts`)
3. `ControllerHandler` wraps it in a `Controller.Command` with an HTTP callback and queues it (`src/python/web/handler/controller.py:66-71`)
4. Controller thread `__process_commands()` executes and fires `on_success`/`on_failure(error, error_code)` (`src/python/controller/controller.py:719`)

### SSE Push Flow (backend → frontend)

1. `WebApp.__web_stream` serves `GET /server/stream`, polling registered `IStreamHandler`s every 100 ms, heartbeat ping every 15 s (`src/python/web/web_app.py`)
2. Stream handlers serialize model diffs, status, and log records (`src/python/web/handler/stream_model.py`, `stream_status.py`, `stream_log.py`, `stream_heartbeat.py`; serializers in `src/python/web/serialize/`)
3. Frontend `StreamDispatchService` holds the single `EventSource`, reconnects on 30 s idle (2x the 15 s server heartbeat), dispatches events by name to `IStreamService` implementations via `StreamServiceRegistry` (`src/angular/src/app/services/base/stream-service.registry.ts`)
4. `ModelFileService` → `ViewFileService` (sort/filter/select) → page components render (`src/angular/src/app/services/files/`)

**State Management:**
- Backend: `Model` (in-memory) + `Persist` files written periodically by the main thread (`persist()` at `src/python/seedsyncarr.py:226`); `ControllerPersist` uses `BoundedOrderedSet` with `max_tracked_files` cap (`src/python/controller/controller_persist.py`, `src/python/common/bounded_ordered_set.py`)
- Frontend: observable-store services with RxJS `BehaviorSubject` + Immutable.js collections; UI options persisted via `LocalStorageService` (keys in `src/angular/src/app/common/storage-keys.ts`)

## Key Abstractions

**`Job` (thread) and `AppProcess` (process):**
- Purpose: Uniform lifecycle (start/terminate/join) with cross-thread/process exception propagation
- Examples: `ControllerJob` (`src/python/controller/controller_job.py`), `WebAppJob` (`src/python/web/web_app_job.py`), `ScannerProcess` (`src/python/controller/scan/scanner_process.py`)
- Pattern: subclass, implement run loop; owner calls `propagate_exception()` each main-loop tick

**`IHandler` / `IStreamHandler`:**
- Purpose: Pluggable web routes and SSE data providers
- Examples: all files in `src/python/web/handler/`
- Pattern: `IHandler.add_routes(web_app)` registers via `web_app.add_handler/add_post_handler/add_delete_handler`; `IStreamHandler.register(web_app, **kwargs)` for streams; wired together in `WebAppBuilder.build()` (`src/python/web/web_app_builder.py`)

**`Persist`:**
- Purpose: File-backed state with corruption backup-and-reset (`Seedsyncarr._load_persist` at `src/python/seedsyncarr.py:446`)
- Examples: `ControllerPersist`, `AutoQueuePersist` (`src/python/controller/auto_queue.py`), `Config` (`src/python/common/config.py`)

**`Context`:**
- Purpose: Dependency container (logger, web_access_logger, config, args, status) passed into every component; `create_child_context(name)` namespaces loggers
- Examples: `src/python/common/context.py`

**`IStreamService` + `BaseStreamService` (frontend):**
- Purpose: Services consuming named SSE events from the single multiplexed stream
- Examples: `ModelFileService`, `ServerStatusService`, `LogService`, `ConnectedService`
- Pattern: register event names, implement `onEvent/onConnected/onDisconnected`; obtain via `StreamServiceRegistry`, never instantiate directly (`src/angular/src/app/services/base/base-stream.service.ts`)

**`ModelFile` → `ViewFile` (frontend view-model split):**
- Purpose: `ModelFile` mirrors backend state; `ViewFile` adds UI state (selection, display status)
- Examples: `src/angular/src/app/services/files/model-file.ts`, `view-file.ts`, transformation in `view-file.service.ts`

## Entry Points

**`src/python/seedsyncarr.py` — `main()`:**
- Triggers: `python seedsyncarr.py -c <config_dir> --html <path> --scanfs <path>`; Docker entrypoint runs this; PyInstaller-frozen builds default `--html`/`--scanfs` from `sys._MEIPASS`
- Responsibilities: config/persist load with backup-on-corruption, logger setup, startup security warnings, secret re-encryption, builds `WebhookManager` → `Controller` → `AutoQueue` → `WebApp`, starts `ControllerJob` + `WebAppJob`, supervises restart/exit loop (`ServiceExit`/`ServiceRestart`)

**`src/python/scan_fs.py`:**
- Triggers: built as standalone `scanfs` binary (PyInstaller, `src/docker/build/docker-image/Dockerfile:57-60`); run locally and pushed to remote host for remote scans
- Responsibilities: scan a directory tree with `SystemScanner`, emit `SystemFile` list to stdout

**`src/angular/src/main.ts`:**
- Triggers: browser load of `index.html` (served by `WebApp.__index` with meta-tag injection; SPA routes `/dashboard`, `/settings`, `/logs`, `/about` all serve index — `src/python/web/web_app.py:174-182`)
- Responsibilities: `bootstrapApplication(AppComponent, appConfig)`; providers and `APP_INITIALIZER`s in `src/angular/src/app/app.config.ts`

**`src/docker/build/docker-image/entrypoint.sh`:**
- Triggers: container start
- Responsibilities: PUID/PGID remap, SSH home setup, default config (`setup_default_config.sh`), launches the Python service

## Architectural Constraints

- **Threading:** Main thread supervises; `ControllerJob` and `WebAppJob` are threads (bottle+paste is multi-threaded). Scanners, extract, and delete run as separate `multiprocessing` processes and NEVER touch the `Model` — they communicate via queues. A plain `threading.Lock` therefore suffices for the model (`src/python/controller/controller.py:95-101`).
- **Single model lock:** `ModelPipeline` stores Controller's lock as `self._model_lock` with a single underscore specifically to preserve object identity (no name mangling; documented as D-03/Pitfall 3 in `src/python/controller/model_pipeline.py`). Never create a second lock for the model.
- **Web→controller handoff:** The web layer must not mutate the model. UI actions go through `Controller.queue_command()`; webhook imports through `WebhookManager.enqueue_import()`. Both are thread-safe queues drained in the controller thread.
- **Global state:** `Seedsyncarr.logger` (class attribute set at startup); `Config.set_keyfile_path()` class-level keyfile for secret encryption. Python imports use a flat layout rooted at `src/python` (`from common import ...`), so PYTHONPATH/cwd must include `src/python`.
- **Auth model:** All `/server/*` routes require Bearer token when `general.api_token` is set, EXCEPT `/server/stream` (EventSource cannot send headers), `/server/status` (health check), and `/server/webhook/*` (HMAC instead) — `WebApp._AUTH_EXEMPT_PATHS` / `_AUTH_EXEMPT_PREFIXES` (`src/python/web/web_app.py:58-64`).
- **Bottle quirk:** `WebApp` must use `object.__setattr__` for instance flags because Bottle intercepts `__setattr__` (`src/python/web/web_app.py`).

## Anti-Patterns

### Constructing managers inside collaborators

**What happens:** A collaborator (e.g., a new pipeline/manager class) instantiates `ScanManager`, `LftpManager`, etc. itself.
**Why it's wrong:** Breaks `mock.patch` binding in tests and duplicates lifecycle ownership — `Controller.__init__` is the single composition root (documented as D-05 in `src/python/controller/model_pipeline.py`).
**Do this instead:** Construct all managers in `Controller.__init__` and inject instances, as `ModelPipeline.__init__` does.

### Touching the Model from a process or without the lock

**What happens:** Code in `controller/scan/`, `controller/extract/`, or `controller/delete/` reads/writes `Model`, or controller code accesses the model without `model_lock`.
**Why it's wrong:** Scanner/extract/delete code runs in separate OS processes (stale copies); in-thread access without the lock races with the web layer's `get_model_files_and_add_listener` (`src/python/controller/controller.py:333`).
**Do this instead:** Processes return results via queues; controller-thread code acquires the lock; web code uses `Controller`'s public API.

### Instantiating frontend stream services directly

**What happens:** A component or test news up `ModelFileService`/`ServerStatusService` outside the registry.
**Why it's wrong:** They only receive data when registered with `StreamDispatchService`'s single multiplexed `EventSource`; direct instances silently never connect (documented in `src/angular/src/app/services/base/base-stream.service.ts`).
**Do this instead:** Provide via `StreamServiceRegistryProvider` in `app.config.ts`; in tests use `MockStreamServiceRegistry` (`src/angular/src/app/tests/mocks/mock-stream-service.registry.ts`).

### Logging webhook-supplied values raw

**What happens:** Logging `file_name` or other request fields directly.
**Why it's wrong:** Log injection (CWE-117) — webhook bodies are attacker-controllable.
**Do this instead:** Wrap with `sanitize_log_value()` from `common`, as in `src/python/controller/webhook_manager.py:36-38`.

## Error Handling

**Strategy:** Exceptions derive from `AppError` (`src/python/common/error.py`); child threads/processes capture and re-raise into the owner via `propagate_exception()`. Controller failures degrade gracefully (server marked down with error message) instead of killing the web app (`src/python/seedsyncarr.py:181-190`).

**Patterns:**
- `ServiceExit` / `ServiceRestart` sentinel exceptions drive the supervision loop in `main()` (`src/python/seedsyncarr.py:507-523`)
- Corrupted config/persist files are backed up (`*.N.bak`) and replaced with defaults, never fatal (`Seedsyncarr.__backup_file`)
- `Controller.Command.ICallback.on_failure(error, error_code)` maps domain failures to HTTP status codes (400/404/409/500)
- `ScannerError(recoverable=True)` lets scan failures retry without crashing the controller (`src/python/controller/scan/scanner_process.py`)
- Cross-process tracebacks preserved with `tblib` + `ExceptionWrapper` (`src/python/common/app_process.py`)

## Cross-Cutting Concerns

**Logging:** Hierarchical loggers via `Context.create_child_context` / `logger.getChild`; separate main and web-access logs; rotating file handlers (`src/python/seedsyncarr.py:280`); `MultiprocessingLogger` bridges process logs (`src/python/common/multiprocessing_logger.py`). Frontend: `LoggerService` with environment-configured level.
**Validation:** Config typed/validated in `Config` (`src/python/common/config.py`); incomplete config (`<replace me>` dummy values) blocks controller start but keeps the web UI up for setup (`src/python/seedsyncarr.py:154-161`).
**Authentication:** Bearer token middleware in `WebApp` with exempt paths; HMAC verification + 60/60s rate limit for webhooks (`src/python/web/handler/webhook.py`, `src/python/web/rate_limit.py`); secrets optionally encrypted at rest with `secrets.key` (`src/python/common/encryption.py`); startup re-encryption and decrypt-failure warnings (`src/python/seedsyncarr.py:402-443`).

---

*Architecture analysis: 2026-06-09*
