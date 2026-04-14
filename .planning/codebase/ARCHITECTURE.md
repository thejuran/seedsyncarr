# Architecture

**Analysis Date:** 2026-02-03

## Pattern Overview

**Overall:** Client-Server with Manager Pattern (Backend) + Component-Services (Frontend)

The architecture follows a classic separation between a Python backend implementing file synchronization logic and an Angular frontend providing the user interface. The backend uses a manager pattern to delegate responsibility for different concerns (scanning, LFTP operations, file operations) to specialized managers, while the frontend uses Angular services to abstract HTTP communication and state management.

**Key Characteristics:**
- Asynchronous bidirectional communication via Server-Sent Events (SSE) streaming
- Immutable model objects enable lock-free reads on the frontend
- Thread-safe listeners pattern with copy-under-lock for concurrent access
- Bounded collections with LRU eviction for memory management
- Multiprocess scanning with shared memory logging

## Layers

**Frontend (Angular 19.x):**
- Purpose: User interface and client-side state management
- Location: `src/angular/src/app`
- Contains: Pages (components), Services (business logic), Common (shared utilities)
- Depends on: Backend REST/SSE API
- Used by: Web browsers

**Web Server (Bottle):**
- Purpose: HTTP API and Server-Sent Events stream endpoint
- Location: `src/python/web`
- Contains: Request handlers, response serializers, streaming handlers
- Depends on: Controller (business logic)
- Used by: Frontend via REST endpoints and SSE `/server/stream`

**Controller (Orchestration):**
- Purpose: Central orchestrator of all operations
- Location: `src/python/controller/controller.py`
- Contains: Command processing, model management, state transitions
- Depends on: ScanManager, LftpManager, FileOperationManager, ModelBuilder
- Used by: Web handlers, AutoQueue

**Manager Layer (Concurrent Operations):**
- **ScanManager** (`src/python/controller/scan_manager.py`): Manages scanner processes (Active, Local, Remote) for discovering files on remote server and local disk
- **LftpManager** (`src/python/controller/lftp_manager.py`): Manages LFTP process for download operations (queue, kill, status polling)
- **FileOperationManager** (`src/python/controller/file_operation_manager.py`): Manages extract and delete operations via subprocess

**Model Layer:**
- Purpose: Data representation and change notification
- Location: `src/python/model`
- Contains: ModelFile (immutable), Model (listener-based), ModelDiff (change tracking)
- Pattern: Listener observers notify all subscribers of model changes

**Common/Shared:**
- Location: `src/python/common`
- Contains: Configuration, Context, Status, Bounded collections, Logging utilities
- Critical: `bounded_ordered_set.py` - LRU-evicting set for bounded collections

## Data Flow

**Real-Time File Sync Flow:**

1. **Scanner Process**: Remote/Local scanner discovers files and outputs results to stdout
2. **ScanManager**: Parses scanner output, processes results
3. **ModelBuilder**: Constructs ModelFile objects with metadata (size, status, timestamps)
4. **Model Update**: Controller updates central Model with new/changed files
5. **Listener Notification**: Model notifies all listeners of changes (added/updated/removed)
6. **Web Stream**: WebResponseModelListener captures events and enqueues them
7. **SSE Stream**: `/server/stream` yields serialized update events
8. **Frontend Stream**: StreamDispatchService receives SSE events, dispatches to ModelFileService
9. **UI Update**: Angular components render updated file list in real-time

**Download Command Flow:**

1. **Frontend**: User clicks "Queue" on a file
2. **REST POST**: `/server/controller` with queue action to ServerCommandService
3. **Web Handler**: Validates request, creates Command object with callbacks
4. **Controller**: Processes command in command queue (FIFO)
5. **LftpManager**: Enqueues file for download with LFTP
6. **Polling**: Controller polls LFTP status every cycle
7. **Status Updates**: Model updated with download progress
8. **SSE Stream**: ModelFile status changes streamed to frontend in real-time
9. **Callback**: Command callback invoked on success/failure, response sent to frontend

**State Persistence:**

1. **ControllerPersist**: Tracks downloaded, extracted, stopped files using BoundedOrderedSet
2. **Periodic Save**: Controller persists state every ~5 seconds
3. **On Shutdown**: Final persist written before process exit
4. **On Restart**: State reloaded to resume tracking

## Key Abstractions

**ModelFile (Immutable):**
- Purpose: Represents a single file with all metadata
- Examples: `src/python/model/file.py`, `src/angular/src/app/services/files/model-file.ts`
- Pattern: Freeze-on-add immutability - becomes immutable after Model.add_file() to eliminate need for deep copying on API responses
- Reduces GC pressure and enables safe concurrent reads

**IModelListener:**
- Purpose: Observer pattern for model changes
- Examples: `src/python/web/handler/stream_model.py` (WebResponseModelListener)
- Pattern: Notified of file_added, file_removed, file_updated events
- Thread-safe: Copy listener list under lock, iterate outside lock

**IStreamHandler:**
- Purpose: Multiplexed streaming data provider
- Examples: Stream handlers in `src/python/web/handler/stream_*.py` (status, log, model, etc.)
- Pattern: setup() → get_value() (called repeatedly) → cleanup()
- Fair interleaving: Web server polls all handlers in round-robin to prevent one from starving others

**BoundedOrderedSet:**
- Purpose: Set with fixed maximum size and LRU eviction
- Location: `src/python/common/bounded_ordered_set.py`
- Pattern: Maintains insertion order, evicts oldest when limit reached
- Used for: downloaded_file_names, extracted_file_names, stopped_file_names (configurable max_tracked_files)

**Command Pattern (Controller):**
- Purpose: Decouple clients from operations
- Location: `src/python/controller/controller.py` (Command, ICallback)
- Pattern: Clients create Command with action and filename, add callback for success/failure
- Executed FIFO in Controller.process(), callbacks invoked in controller thread

## Entry Points

**Backend Entry:**
- Location: `src/python/seedsync.py`
- Triggers: SystemD service start, Docker entrypoint, manual execution
- Responsibilities:
  - Parse arguments (config dir, log dir, HTML path)
  - Initialize Context (logger, config, status)
  - Load persisted state
  - Create and start Controller, WebApp, and AutoQueue
  - Run main loop with signal handling and periodic persistence

**Frontend Entry:**
- Location: `src/angular/src/main.ts`
- Triggers: Browser page load
- Responsibilities:
  - Bootstrap Angular AppComponent with appConfig providers
  - Initialize all services (logging, stream dispatch, etc.)
  - Load routes and render initial component

**Web Server Entry:**
- Location: `src/python/web/web_app_builder.py`
- Triggers: Called from Seedsync.run()
- Responsibilities:
  - Register all handler routes (config, controller, status, etc.)
  - Register all stream handlers (model, log, status, heartbeat)
  - Configure Bottle app for static file serving
  - Start HTTP server on configured port

## Error Handling

**Strategy:** Three-tiered error response with HTTP status codes

**Pattern 1 - Validation (400):**
- Used when: Request validation fails, file already in state
- Example: Queue request for already-queued file returns 400 Bad Request
- Response: ICallback.on_failure(error, 400)

**Pattern 2 - Not Found (404):**
- Used when: Resource doesn't exist
- Example: Delete action on non-existent file
- Response: ICallback.on_failure(error, 404)

**Pattern 3 - Conflict (409):**
- Used when: Resource in wrong state for operation
- Example: Extract command on still-downloading file
- Response: ICallback.on_failure(error, 409)

**Pattern 4 - Server Error (500):**
- Used when: Internal operation fails (LFTP error, subprocess failure)
- Example: LFTP connection refused, extract process error
- Response: ICallback.on_failure(error, 500)

**Backend Exception Handling:**
- Controller catches AppError but continues running (notifies web server of error state)
- ControllerJob catches and propagates exceptions to main thread
- Main thread logs exceptions, terminates cleanly on fatal errors
- Signal handlers (SIGTERM, SIGINT) raise ServiceExit for graceful shutdown

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging module, Angular LoggerService
- Pattern: Hierarchical loggers with child contexts (parent.getChild("name"))
- Levels: DEBUG (verbose), INFO (normal), WARNING, ERROR
- Output: File-based with rotation (10MB max, 3 backups)
- Multiprocess: MultiprocessingLogger queues messages from scanner/extract/delete subprocesses

**Validation:**
- Request validation: Web handlers validate HTTP request parameters
- State validation: Controller checks file state before actions (e.g., not queued before queueing)
- Config validation: On startup, detects incomplete settings (returns placeholder values)

**Authentication:**
- Strategy: SSH credentials for remote server (username, password, or SSH key)
- No built-in auth: SeedSync assumes local network trust, no authentication for web UI
- SSH handled by: `src/python/ssh` layer (subprocess-based SFTP/SSH)

**Thread Safety:**
- Model access: Protected by `__model_lock` (threading.Lock)
- Listener collections: Copy under lock, iterate outside (prevents deadlock)
- Multiprocessing: Scanner/extract/delete run in separate processes, share results via queues
- Immutability: ModelFile objects frozen after add to Model, safe for concurrent reads

---

*Architecture analysis: 2026-02-03*
