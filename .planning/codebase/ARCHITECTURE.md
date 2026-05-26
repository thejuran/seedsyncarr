<!-- refreshed: 2026-05-26 -->
# Architecture

**Analysis Date:** 2026-05-26

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                          Browser (Angular SPA)                           │
│  `src/angular/src/app/pages/*`     `src/angular/src/app/services/*`      │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐     │
│  │ Files page  │  │ Settings    │  │ Logs page    │  │ About page  │     │
│  │ (dashboard) │  │ page        │  │              │  │             │     │
│  └─────────────┘  └─────────────┘  └──────────────┘  └─────────────┘     │
│         │                │                  │                            │
│         └────────────────┴──────────────────┘                            │
│                          │                                               │
│         ┌────────────────┴───────────────────┐                           │
│         │  Services (HTTP + SSE consumers)   │                           │
│         │  ModelFileService, ConfigService,  │                           │
│         │  LogService, ServerStatusService,  │                           │
│         │  StreamDispatchService             │                           │
│         └────────────────┬───────────────────┘                           │
└──────────────────────────┼───────────────────────────────────────────────┘
                           │  HTTP/REST + SSE on /server/*
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     Web Server (Bottle + Paste WSGI)                     │
│  `src/python/web/web_app.py`  `src/python/web/web_app_builder.py`        │
│                                                                          │
│  Handlers (REST):                Stream handlers (SSE multiplex):        │
│  - ControllerHandler             - ModelStreamHandler                    │
│  - ConfigHandler                 - StatusStreamHandler                   │
│  - AutoQueueHandler              - LogStreamHandler                      │
│  - ServerHandler                 - HeartbeatStreamHandler                │
│  - StatusHandler                                                         │
│  - WebhookHandler (Sonarr/Radarr in)                                     │
│                                                                          │
│  Cross-cutting: Bearer auth, Host allowlist, CSP/security headers,       │
│  rate limiting, HMAC verification on webhooks.                           │
└──────────┬───────────────────────────────────────────────────────────────┘
           │  command_queue.put / model listener / status reads
           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      Controller (main worker thread)                     │
│  `src/python/controller/controller.py`                                   │
│                                                                          │
│  Owns:                                                                   │
│  - Model (`src/python/model/model.py`)  + ModelBuilder                   │
│  - ScanManager   → RemoteScanner / LocalScanner / ActiveScanner          │
│  - LftpManager   → Lftp pexpect process                                  │
│  - FileOperationManager → ExtractProcess + Delete[Local|Remote]Process   │
│  - WebhookManager (import event queue)                                   │
│  - AutoQueue (pattern-driven auto-queueing)                              │
│  - MemoryMonitor, ControllerPersist                                      │
└─────┬───────────────────┬──────────────────┬─────────────────────────────┘
      │ multiprocessing   │ pexpect          │ subprocess (patool)
      ▼                   ▼                  ▼
┌──────────────┐    ┌──────────────┐    ┌────────────────────────────────┐
│ Scanner      │    │ LFTP process │    │ Extract / Delete one-shot      │
│ processes    │    │ (transfers)  │    │ processes                      │
│ (remote/local│    │              │    │                                │
│  /active)    │    │              │    │                                │
└──────┬───────┘    └──────┬───────┘    └──────────────┬─────────────────┘
       │                   │                           │
       ▼                   ▼                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│      Filesystems and remote services (SSH host, Sonarr, Radarr)          │
│      Persist files in $CONFIG_DIR (settings.cfg, *.persist, secrets.key) │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `Seedsyncarr` | Top-level service: arg parsing, config load/restore, context build, signal handling, thread orchestration | `src/python/seedsyncarr.py` |
| `Context` / `Args` | Shared application state (logger, config, status, CLI args) passed to all components | `src/python/common/context.py` |
| `Config` | Sectioned settings persisted to `settings.cfg`, with secret-field encryption | `src/python/common/config.py` |
| `Status` | Mutable runtime status (server up flag, scan times, storage capacity) consumed by stream/REST handlers | `src/python/common/status.py` |
| `Job` (abstract) | Thread with `setup` / `execute` / `cleanup` lifecycle and exception propagation back to main | `src/python/common/job.py` |
| `ControllerJob` | Thread wrapper around `Controller.process()` + `AutoQueue.process()` | `src/python/controller/controller_job.py` |
| `Controller` | Orchestrator that owns the model, drains a command queue, and updates state from scanner / LFTP / extract managers | `src/python/controller/controller.py` |
| `Model` / `ModelFile` / `ModelDiff` | Immutable file tree (frozen after add) with listener notifications and diff utility | `src/python/model/model.py`, `src/python/model/file.py`, `src/python/model/diff.py` |
| `ModelBuilder` | Builds a new immutable `Model` by merging remote/local/active scan results, LFTP statuses, and extract statuses | `src/python/controller/model_builder.py` |
| `ScanManager` | Owns the three scanner processes (remote / local / active) and exposes results | `src/python/controller/scan_manager.py` |
| `RemoteScanner` / `LocalScanner` / `ActiveScanner` | Concrete scanners run inside `ScannerProcess` | `src/python/controller/scan/*.py` |
| `LftpManager` / `Lftp` | Wraps a long-running `lftp` shell over pexpect; exposes queue / kill / status | `src/python/controller/lftp_manager.py`, `src/python/lftp/lftp.py` |
| `FileOperationManager` | Spawns one-shot extract / delete-local / delete-remote processes and tracks their progress | `src/python/controller/file_operation_manager.py` |
| `ExtractProcess` / `ExtractDispatch` | Long-lived child process that runs `patool` extractions | `src/python/controller/extract/extract_process.py`, `extract/dispatch.py` |
| `Delete[Local|Remote]Process` | One-shot subprocesses that delete files locally or over SSH | `src/python/controller/delete/delete_process.py` |
| `WebhookManager` | Thread-safe queue between web webhook handlers and controller; matches imported names back to model files | `src/python/controller/webhook_manager.py` |
| `AutoQueue` | Listens to `Model` events and queues newly seen remote files for download (with optional glob patterns) | `src/python/controller/auto_queue.py` |
| `WebAppBuilder` | Wires REST handlers + SSE handlers into a single `WebApp` (Bottle) | `src/python/web/web_app_builder.py` |
| `WebApp` | Bottle subclass with auth/host/CSP hooks, SSE multiplex (`/server/stream`), static SPA serving | `src/python/web/web_app.py` |
| `WebAppJob` | Hosts Bottle on Paste WSGI in a background thread; supports clean stop | `src/python/web/web_app_job.py` |
| `MultiprocessingLogger` | Aggregates log records from child processes into the main logger | `src/python/common/multiprocessing_logger.py` |
| `MemoryMonitor` | Periodic logging of bounded-set sizes / eviction counts for leak detection | `src/python/controller/memory_monitor.py` |
| `BoundedOrderedSet` | LRU-bounded set used for `downloaded_file_names`, `extracted_file_names`, `stopped_file_names`, `imported_file_names` | `src/python/common/bounded_ordered_set.py` |
| `AppComponent` | Angular root: router outlet, header, toasts, connection indicator | `src/angular/src/app/pages/main/app.component.ts` |
| `StreamDispatchService` | Single `EventSource` on `/server/stream`; demultiplexes events to subscribed services | `src/angular/src/app/services/base/stream-service.registry.ts` |
| `ModelFileService` | Holds the SPA's `Immutable.Map<string, ModelFile>` and issues REST commands (queue/stop/extract/delete) | `src/angular/src/app/services/files/model-file.service.ts` |
| `ConfigService` / `AutoQueueService` / `LogService` / `ServerStatusService` | Domain stores for settings, autoqueue patterns, log records, and status (each subscribes via SSE + REST) | `src/angular/src/app/services/*` |

## Pattern Overview

**Overall:** Layered service with a single long-running controller thread, dedicated child *processes* for I/O-heavy work (scans, LFTP, extract, delete), and a Bottle/Paste web tier feeding an Angular SPA through REST + a multiplexed Server-Sent-Events stream.

**Key Characteristics:**
- Single-process main app (`Seedsyncarr.run`) that supervises two `threading.Thread` jobs: `ControllerJob` and `WebAppJob`.
- CPU/IO-heavy concerns are isolated in `multiprocessing.Process` children with their own queues (`AppProcess`, `AppOneShotProcess`); only the controller thread touches the in-memory `Model`.
- The `Model` is rebuilt by `ModelBuilder` from independent input streams (remote scan, local scan, active scan, LFTP statuses, extract statuses) and a `ModelDiff` is applied under `__model_lock`; once added, `ModelFile` instances are *frozen* (immutable) so they can be shared across threads/SSE listeners without deep copies.
- Web tier is stateless w.r.t. file transfer — it submits `Controller.Command` objects to a thread-safe `Queue` and waits on per-command callbacks (with timeouts).
- SSE is multiplexed: every `/server/stream` connection runs all registered `IStreamHandler` instances (model / status / log / heartbeat) on a single response generator with fair interleaving.
- Frontend mirrors this: one `EventSource` in `StreamDispatchService` fans events out to registered `IStreamService` consumers (`ModelFileService`, `ServerStatusService`, `LogService`, `ConnectedService`).

## Layers

**Entry / Supervision (Python):**
- Purpose: parse args, load config, build context, supervise jobs, persist state.
- Location: `src/python/seedsyncarr.py`
- Contains: `Seedsyncarr` class, `main()`, ServiceExit/ServiceRestart loop.
- Depends on: `common`, `controller`, `web`.
- Used by: `pyproject.toml [project.scripts] seedsyncarr` + PyInstaller frozen entry.

**Common / Cross-cutting:**
- Purpose: shared primitives (`Job`, `AppProcess`, `Context`, `Config`, `Status`, `Persist`, `Localization`, encryption, bounded LRU set).
- Location: `src/python/common/`
- Used by: every other Python package.

**Controller (domain core):**
- Purpose: orchestrates scanning, LFTP transfers, extract/delete, model state, webhook imports, auto-delete, auto-queue.
- Location: `src/python/controller/`
- Depends on: `model`, `lftp`, `ssh`, `system`, `common`.
- Used by: `web` (read-only model access + command queue), `seedsyncarr.py`.

**Model:**
- Purpose: immutable file tree with listener notifications and diff utility.
- Location: `src/python/model/`
- Depends on: `common`.
- Used by: `controller`, `web` (via stream handlers).

**LFTP / SSH / System adapters:**
- Purpose: external-process wrappers (lftp via pexpect, SSH copy, host filesystem scans).
- Location: `src/python/lftp/`, `src/python/ssh/`, `src/python/system/`, `src/python/scan_fs.py`
- Used by: `controller`.

**Web (HTTP/SSE adapter):**
- Purpose: Bottle app, security hooks, REST handlers, SSE stream handlers, payload serialization.
- Location: `src/python/web/`
- Subdivisions: `web/handler/` (one file per endpoint group), `web/serialize/` (JSON serializers for Model/Config/Status/AutoQueue/LogRecord).
- Depends on: `controller`, `common`.

**Angular SPA (UI):**
- Purpose: dashboard, settings, logs, about pages; consumes `/server/*` REST + SSE.
- Location: `src/angular/src/app/`
- Sublayers:
  - `pages/` — route-level components (`files`, `settings`, `logs`, `about`, `main`).
  - `services/` — singleton stores (split by domain: `files`, `server`, `settings`, `logs`, `autoqueue`, `utils`, `base`).
  - `common/` — shared pipes, directives, styles, route-reuse strategy, version constant.
- Bootstrapped by: `src/angular/src/main.ts` → `bootstrapApplication(AppComponent, appConfig)`.

**E2E / Tests:**
- Python unit + integration tests: `src/python/tests/unittests/`, `src/python/tests/integration/`.
- Angular unit tests: `*.spec.ts` co-located with components and services.
- Angular Playwright tests: `src/angular/e2e/`.
- Cross-stack Playwright e2e: `src/e2e/tests/` (page-object pattern with `*.page.ts` + `*.spec.ts`).
- Docker test harnesses: `src/docker/test/{python,angular,e2e}/`.

## Data Flow

### Primary Request Path — User clicks "Queue" on a file

1. Browser: `TransferRowComponent` → `ModelFileService.queue(file)` (`src/angular/src/app/services/files/model-file.service.ts`).
2. `RestService` issues `POST /server/command/queue/<file_name>` (`src/angular/src/app/services/utils/rest.service.ts`); `authInterceptor` attaches the Bearer token read from `<meta name="api-token">`.
3. `WebApp` `before_request` hook validates Host + Bearer (`src/python/web/web_app.py:83`).
4. `ControllerHandler.__handle_action_queue` builds a `Controller.Command(QUEUE, file)` and a `WebResponseActionCallback` (`src/python/web/handler/controller.py:76`).
5. `Controller.queue_command(command)` puts it on `__command_queue` (`src/python/controller/controller.py:307`).
6. `ControllerJob.execute()` runs `Controller.process()` → `__process_commands()` drains the queue under `__model_lock` and calls `__handle_queue_command` → `LftpManager.queue` (`src/python/controller/controller.py:977`, `src/python/controller/lftp_manager.py`).
7. Callback fires `on_success()`; the handler returns HTTP 200; UI is updated by the next SSE model diff (not by the response body).

### Secondary Flow — Model update propagation (SSE)

1. Scanner processes write `ScannerResult` to their `multiprocessing.Queue` (`src/python/controller/scan/scanner_process.py`).
2. `Controller.__update_model()` (`src/python/controller/controller.py:689`) pulls scan/LFTP/extract results and feeds `ModelBuilder`.
3. `_build_and_apply_model` diffs old vs new model, applies the diff under `__model_lock`, and notifies registered `IModelListener`s (`src/python/model/model.py:add_file/remove_file/update_file`).
4. Each connected SSE client has its own `WebResponseModelListener` whose listener callbacks push `SerializeModel.UpdateEvent` into a `StreamQueue` (`src/python/web/handler/stream_model.py:10`).
5. `WebApp.__web_stream` interleaves `get_value()` from all stream handlers and yields `event: model-{added,updated,removed}` SSE frames (`src/python/web/web_app.py:248`).
6. `StreamDispatchService` (`src/angular/src/app/services/base/stream-service.registry.ts`) receives the event and dispatches it to `ModelFileService.notifyEvent`, which updates its `BehaviorSubject<Immutable.Map<string, ModelFile>>`.
7. `TransferTableComponent` (`src/angular/src/app/pages/files/transfer-table.component.ts`) re-renders via async pipe.

### Tertiary Flow — Sonarr/Radarr webhook → auto-delete

1. Sonarr posts to `POST /server/webhook/sonarr` (`src/python/web/handler/webhook.py`).
2. `WebhookHandler._verify_hmac` checks `X-Webhook-Signature` against `general.webhook_secret`.
3. Title is extracted and `WebhookManager.enqueue_import(source, file_name)` puts it on the shared queue (`src/python/controller/webhook_manager.py:25`).
4. On the controller thread, `Controller.__check_webhook_imports` builds a `name_to_root` lookup (root + child names), calls `webhook_manager.process(...)`, and records imports in `ControllerPersist` (`src/python/controller/controller.py:726`).
5. If `config.autodelete.enabled`, `__schedule_auto_delete` arms a `threading.Timer` for `delay_seconds`.
6. `__execute_auto_delete` re-checks model state, runs the pack-guard + coverage BFS (capped at 10,000 nodes), and dispatches `FileOperationManager.delete_local(file)` — which spawns a one-shot `DeleteLocalProcess`.

**State Management:**
- Authoritative state lives in `Controller.__model` (Python) and is rebuilt on every controller tick.
- Persisted state lives in `$CONFIG_DIR/{settings.cfg, controller.persist, autoqueue.persist, secrets.key}` and is rewritten every `MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS` plus on shutdown.
- Frontend state is a derived `Immutable.Map` rebuilt from SSE events; on reconnect, `notifyConnected()` resets stores and re-subscribes.

## Key Abstractions

**`Job` (threading abstraction):**
- Purpose: long-running thread with deterministic setup / execute-loop / cleanup and exception capture for the supervisor.
- Examples: `src/python/controller/controller_job.py`, `src/python/web/web_app_job.py`.
- Pattern: subclass `Job`, implement `setup/execute/cleanup`; the main thread polls `propagate_exception()`.

**`AppProcess` / `AppOneShotProcess` (multiprocessing abstraction):**
- Purpose: child processes with cross-process exception propagation (`tblib`) and a multiprocessing logger.
- Examples: `src/python/controller/scan/scanner_process.py`, `src/python/controller/extract/extract_process.py`, `src/python/controller/delete/delete_process.py`.
- Pattern: subclass `AppProcess`, override `run_init` / `run_cycle` (or `run_once` for one-shots); communicate via `multiprocessing.Queue`.

**`Controller.Command` + `Controller.Command.ICallback`:**
- Purpose: every state-changing user action is a queued command with success/failure callbacks; this is the only mutation entry point into the controller.
- Pattern: see `WebResponseActionCallback` in `src/python/web/handler/controller.py:19` — uses `threading.Event` to bridge the web request thread and the controller thread.

**`IHandler` / `IStreamHandler` (web extension points):**
- Purpose: pluggable REST/SSE handlers. `WebAppBuilder` instantiates and wires them.
- Examples: `src/python/web/handler/controller.py`, `src/python/web/handler/stream_model.py`.
- Pattern: implement `add_routes(web_app)` for REST or `setup/get_value/cleanup` for streams.

**`Model` + `IModelListener` + `ModelDiff`:**
- Purpose: observable immutable file tree. Listeners receive ADDED/REMOVED/UPDATED events; diffs are used to compute SSE payloads and persist updates.
- Files: `src/python/model/model.py`, `src/python/model/diff.py`, `src/python/model/file.py`.
- Pattern: `ModelFile._unfreeze()` is intentional protected access — only the controller (which owns the freeze lifecycle) calls it.

**`Persist` / `Serializable`:**
- Purpose: file-backed JSON persistence with corruption-aware loading (`from_file` falls back to `.bak` rotation).
- Examples: `src/python/common/persist.py`, `src/python/controller/controller_persist.py`, `src/python/controller/auto_queue.py` (`AutoQueuePersist`).

**`BaseStreamService` / `BaseWebService` / `IStreamService` (Angular):**
- Purpose: common base for SSE-driven and REST-driven services, registered via DI tokens.
- Files: `src/angular/src/app/services/base/base-stream.service.ts`, `src/angular/src/app/services/base/base-web.service.ts`, `src/angular/src/app/services/base/stream-service.registry.ts`.

## Entry Points

**Python service:**
- Location: `src/python/seedsyncarr.py` (`main()` exposed as the `seedsyncarr` console script in `src/python/pyproject.toml`).
- Triggers: `pip install seedsyncarr` then `seedsyncarr -c <config_dir>`; Docker `CMD` runs this. PyInstaller frozen builds use `sys._MEIPASS` defaults for `--html` and `--scanfs`.
- Responsibilities: parse args, load/repair config, build `Context`, start `ControllerJob` + `WebAppJob`, loop on persist + exception propagation + restart detection.

**Angular SPA bootstrap:**
- Location: `src/angular/src/main.ts`.
- Triggers: any browser hit to `/`, `/dashboard`, `/settings`, `/autoqueue`, `/logs`, `/about` (Bottle serves `index.html` with an injected `<meta name="api-token">` tag, then the SPA takes over).
- Responsibilities: bootstrap `AppComponent` with `appConfig` (`src/angular/src/app/app.config.ts`), install router (`src/angular/src/app/routes.ts`), inject services declared in `providers[]`.

**HTTP/SSE surface:**
- Streaming: `GET /server/stream` (multiplexed SSE; auth-exempt because `EventSource` cannot send custom headers).
- Status: `GET /server/status` (health, auth-exempt).
- Commands: `POST/DELETE /server/command/{queue,stop,extract,delete_local,delete_remote}/<file>`, `POST /server/command/bulk`.
- Config: `GET /server/config/get`, `GET /server/config/set/<section>/<key>/<value>`, `GET /server/config/{sonarr,radarr}/test-connection`.
- AutoQueue: handled by `AutoQueueHandler` in `src/python/web/handler/auto_queue.py`.
- Webhooks: `POST /server/webhook/{sonarr,radarr}` (HMAC-authenticated, Bearer-exempt).
- Server admin: `ServerHandler` in `src/python/web/handler/server.py` (restart, version info).
- SPA routes: `/`, `/dashboard`, `/settings`, `/autoqueue`, `/logs`, `/about` all return the SPA shell; everything else under `/<path>` is served as a static file from `--html`.

**Scanner script (frozen helper):**
- `src/python/scan_fs.py` is packaged as a standalone `scanfs` executable via PyInstaller (`--scanfs`) and invoked on the remote host over SSH by `RemoteScanner`.

## Architectural Constraints

- **Threading model:** Main process runs three threads — main supervisor, `ControllerJob`, `WebAppJob` (which itself spawns Paste's WSGI thread pool). Heavy work runs in `multiprocessing.Process` children (scanners, extract, delete-local/remote, LFTP via pexpect).
- **Model mutation rule:** the `Model` is only mutated on the controller thread under `__model_lock`. `ModelFile` instances are frozen after `add_file`; `_unfreeze()` is intentional protected access owned by `Controller` (see `src/python/controller/controller.py:355`).
- **Web → controller mutations:** must go through `Controller.queue_command(...)`. Web handlers MUST NOT touch model fields directly.
- **Controller → scanners:** scanner processes never read the model; they only push `ScannerResult` and consume `force_*_scan` triggers via `ScanManager`.
- **Webhook payloads are untrusted:** all log lines that include webhook-supplied strings must be sanitized (replace `\n`, `\r`) to prevent CWE-117 log injection. See `src/python/controller/webhook_manager.py:36`, `src/python/controller/controller.py:790`.
- **Path safety:** every destructive REST command (`extract`, `delete_local`, `delete_remote`) goes through `ControllerHandler._check_path_safe` which `realpath()`-resolves the candidate and enforces containment under `config.lftp.local_path`.
- **Auth surface:** all `/server/*` paths require a Bearer token equal to `general.api_token`, except `/server/stream` (R003), `/server/status`, and `/server/webhook/*` (HMAC-authed). Empty `api_token` disables Bearer auth for backward compatibility but logs a startup warning.
- **CSP:** layered — HTTP header in `WebApp._add_security_headers` plus Angular's `autoCsp`-generated meta tag. Both policies must allow Angular's inline bootstrap.
- **Bounded growth:** `downloaded_file_names`, `extracted_file_names`, `stopped_file_names`, `imported_file_names` are `BoundedOrderedSet` with LRU eviction (default 10,000 — `config.controller.max_tracked_files`). Auto-delete BFS is capped at `_AUTO_DELETE_BFS_NODE_LIMIT = 10_000` nodes.
- **Encryption:** secret fields listed in `_SECRET_FIELD_PATHS` are encrypted in-place on disk when `encryption.enabled = true`; the keyfile is `$CONFIG_DIR/secrets.key`. Plaintext-on-disk values are silently re-encrypted at startup.
- **Frontend Zone:** uses zone.js with `eventCoalescing: true` (`src/angular/src/app/app.config.ts:41`); all `EventSource` callbacks run inside `NgZone` via `StreamDispatchService`.

## Anti-Patterns

### Bypassing the command queue

**What happens:** A handler or background task calls `LftpManager.queue` / `FileOperationManager.delete_local` / model mutation directly instead of submitting a `Controller.Command`.
**Why it's wrong:** breaks the "controller thread owns the model" invariant — concurrent scans or other commands can interleave and produce torn state; per-command callbacks (and HTTP error reporting) are lost.
**Do this instead:** build a `Controller.Command(Action, file_name)`, attach a `WebResponseActionCallback`, call `controller.queue_command(command)`, and wait on the callback (`src/python/web/handler/controller.py:76`).

### Touching `ModelFile` mutably outside the controller

**What happens:** Code outside `Controller` copies a `ModelFile`, calls `_unfreeze()`, mutates fields, and re-inserts it.
**Why it's wrong:** `_unfreeze` is a protected hook owned by `Controller`'s freeze lifecycle. Mutation on a model file that other threads/SSE listeners still hold causes data races, and replays through `ModelDiffUtil` produce duplicate or missed SSE events.
**Do this instead:** rebuild via `ModelBuilder` inputs (`set_remote_files` / `set_local_files` / `set_*`); let `_build_and_apply_model` produce a new `Model` and diff it under the lock (`src/python/controller/controller.py:597`).

### Reading webhook-supplied strings into logs unsanitized

**What happens:** `logger.info("import: " + payload["file"])` is written verbatim.
**Why it's wrong:** webhook payloads are untrusted. Embedded `\n` lets attackers forge log entries (CWE-117).
**Do this instead:** strip newlines/CRs before logging — see the `safe_file_name = file_name.replace("\n", "\\n").replace("\r", "\\r")` pattern in `src/python/controller/webhook_manager.py:36` and `src/python/controller/controller.py:790`.

### Adding a second `EventSource` from the frontend

**What happens:** A new service opens its own `new EventSource("/server/stream")`.
**Why it's wrong:** the stream is multiplexed by design. Extra connections double SSE load on the WSGI thread pool, and the per-connection `before_request` Host/Bearer check still runs against `EventSource`'s header limitations.
**Do this instead:** subclass `BaseStreamService`, `registerEventName(...)` for the events you care about, and register the service in `StreamServiceRegistryProvider` (`src/angular/src/app/services/base/stream-service.registry.ts`).

### Long blocking work inside a `Job.execute()`

**What happens:** A `Job` subclass blocks for seconds inside `execute()`.
**Why it's wrong:** `Job` is a single-threaded loop; long blocks delay `terminate()` (the supervisor cannot stop the thread cleanly) and starve subsequent ticks (model updates, command processing).
**Do this instead:** offload to an `AppProcess` (scanner/extract/delete pattern) or a `threading.Timer` (auto-delete pattern), and keep `execute()` returning promptly.

## Error Handling

**Strategy:** errors are surfaced *across* thread/process boundaries with explicit propagation primitives, never swallowed in worker threads.

**Patterns:**
- `AppError` hierarchy in `src/python/common/error.py` (`AppError`, `ServiceExit`, `ServiceRestart`); domain modules add specifics (`ControllerError`, `LftpError`, `ScannerError`, `ModelError`, `ConfigError`, `PersistError`, `EncryptionError`).
- `Job.run` catches every `Exception` in the loop, stores `sys.exc_info()`, sets the shutdown flag, and runs `cleanup()`; main thread calls `Job.propagate_exception()` to re-raise (`src/python/common/job.py:36`).
- `AppProcess` uses `tblib.pickling_support` to round-trip cross-process tracebacks through `ExceptionWrapper` (`src/python/common/app_process.py:17`).
- Controller-thread exceptions are caught in `Seedsyncarr.run` so the web tier can keep serving an error page (`status.server.up = False`, `error_msg`); fatal errors only escape when `--exit` is passed (`src/python/seedsyncarr.py:181`).
- REST handlers translate domain failures into HTTP status codes via `(success, error_msg, error_code)` tuples from `Controller.__handle_*` methods (400/404/409/500/504).
- Frontend: `RestService` wraps responses in `WebReaction` (success/failure + message); `ToastService` surfaces them via `notification-bell.component.ts` and toast strip in `app.component.ts`.

## Cross-Cutting Concerns

**Logging:**
- Two named loggers (main service + web access) configured in `Seedsyncarr._create_logger` with `RotatingFileHandler` when `--logdir` is set, else stdout.
- Child processes use `MultiprocessingLogger` (`src/python/common/multiprocessing_logger.py`) which forwards records to the main logger.
- Sensitive keys redacted by `Context._REDACTED_KEYS` when `print_to_log()` dumps config at startup.
- Webhook / user-supplied strings are newline-stripped before logging.

**Validation:**
- Config: `Config.from_file` uses per-field converters; missing or malformed configs trigger a `.bak` rotation and default config regeneration.
- Webhook payloads: capped at `_WEBHOOK_MAX_BODY_BYTES = 1 MB`, HMAC-verified, JSON-parsed.
- Bulk commands: capped at `_MAX_BULK_FILES = 1000`, deduplicated, individually path-checked for destructive actions.
- Frontend forms: Angular reactive validation in `settings-page.component.ts`.

**Authentication:**
- Host allowlist (`general.allowed_hostname`) and Bearer token both enforced in `WebApp` `before_request`.
- HMAC-SHA256 for webhooks via `general.webhook_secret`.
- Frontend reads the token from `<meta name="api-token">` injected by `WebApp._inject_meta_tag` and attaches it via `authInterceptor` (`src/angular/src/app/services/utils/auth.interceptor.ts`).

**Rate Limiting:**
- `web/rate_limit.py` decorator applied to `config/set`, Sonarr/Radarr connection tests, and `command/bulk`.

**Persistence:**
- `Persist` base class (`src/python/common/persist.py`) and the corruption-rotating `Seedsyncarr.__backup_file` ensure a bad persist file never blocks startup.

---

*Architecture analysis: 2026-05-26*
