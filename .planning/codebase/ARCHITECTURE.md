<!-- refreshed: 2026-06-02 -->
# Architecture

**Analysis Date:** 2026-06-02

## System Overview

SeedSyncarr is a self-hosted file-syncing daemon (an LFTP-driven download manager
with Sonarr/Radarr webhook integration). It is a **two-part application**: a
multi-threaded/multi-process **Python backend** (`src/python/`) that drives LFTP,
scanning, extraction, and auto-delete, and a standalone **Angular SPA frontend**
(`src/angular/`) served as static HTML by the backend's embedded Bottle web server.
The two halves communicate over a REST + Server-Sent-Events (SSE) HTTP API.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                       Angular SPA  (browser)                              │
│  Pages: dashboard / settings / logs / about                              │
│  `src/angular/src/app/pages/*`   Services: `src/angular/src/app/services/*`│
└──────────────┬──────────────────────────────────────┬─────────────────────┘
       REST (GET/POST)                         SSE streams (model/status/log)
               │                                        │
               ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  Web Layer — Bottle app (single process, threaded)        │
│  `src/python/web/web_app.py`  built by `web/web_app_builder.py`           │
│  Handlers: `web/handler/*`     Serializers: `web/serialize/*`             │
└──────────────┬────────────────────────────────────────────────────────────┘
               │ Controller.Command queue  +  IModelListener registration
               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│        Controller (coordinator)  `src/python/controller/controller.py`    │
│  Owns: command queue · Model + model_lock · auto-delete timers · persist  │
│  Delegates to collaborators (post-decomposition, Phase 109):              │
│   ├─ ModelPipeline        `controller/model_pipeline.py`  (scan→build→diff)│
│   ├─ CommandProcessor     `controller/command_processor.py` (QUEUE/STOP…) │
│   ├─ AutoDeleteManager    `controller/auto_delete_manager.py` (BFS+cover)  │
│   ├─ ScanManager          `controller/scan_manager.py`                    │
│   ├─ LftpManager          `controller/lftp_manager.py`                    │
│   ├─ FileOperationManager `controller/file_operation_manager.py`          │
│   ├─ WebhookManager       `controller/webhook_manager.py`                 │
│   ├─ ModelBuilder         `controller/model_builder.py`                   │
│   └─ MemoryMonitor        `controller/memory_monitor.py`                  │
└──────┬───────────────┬──────────────────┬───────────────┬─────────────────┘
       │               │                  │               │
       ▼               ▼                  ▼               ▼
┌────────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐
│ LFTP child │  │ Scanner      │  │ Extract       │  │ Persist (on disk)  │
│ process    │  │ processes    │  │ process       │  │ controller.persist │
│ `lftp/`    │  │ `controller/ │  │ `controller/  │  │ autoqueue.persist  │
│            │  │  scan/`      │  │  extract/`    │  │ settings.cfg       │
└────────────┘  └──────────────┘  └───────────────┘  └────────────────────┘
        Remote NAS  ◀── SSH/SFTP ──▶  Local filesystem
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `Seedsyncarr` (entry) | Parse args, load config/persists, wire objects, run main thread loop, handle signals/restart | `src/python/seedsyncarr.py` |
| `Controller` | Top-level coordinator: owns command queue, `Model`, `model_lock`, auto-delete timers; orchestrates collaborators | `src/python/controller/controller.py` |
| `ControllerJob` | Thread wrapper that calls `controller.process()` + `auto_queue.process()` each tick | `src/python/controller/controller_job.py` |
| `ModelPipeline` | collect → feed → build → diff → apply model-update pipeline | `src/python/controller/model_pipeline.py` |
| `ModelBuilder` | Reconcile scan/LFTP/extract results into `ModelFile` tree | `src/python/controller/model_builder.py` |
| `CommandProcessor` | Execute QUEUE/STOP/EXTRACT/DELETE_LOCAL/DELETE_REMOTE actions | `src/python/controller/command_processor.py` |
| `AutoDeleteManager` | BFS over pack children + coverage guard for safe auto-delete | `src/python/controller/auto_delete_manager.py` |
| `ScanManager` | Owns remote/local/active scanner processes; forced-scan callbacks | `src/python/controller/scan_manager.py` |
| `LftpManager` | Wraps LFTP, queue/stop, job status polling | `src/python/controller/lftp_manager.py` |
| `FileOperationManager` | Spawn/track delete + extract child processes | `src/python/controller/file_operation_manager.py` |
| `WebhookManager` | Process Sonarr/Radarr import events into name→root matches | `src/python/controller/webhook_manager.py` |
| `AutoQueue` | Pattern-based auto-queue of newly discovered files | `src/python/controller/auto_queue.py` |
| `MemoryMonitor` | Periodic stats logging for bounded collections / leak detection | `src/python/controller/memory_monitor.py` |
| `WebApp` / `WebAppBuilder` | Bottle app, route registration, SSE streaming, auth | `src/python/web/web_app.py`, `web/web_app_builder.py` |
| `Model` | Authoritative in-memory file-state tree + listener fan-out | `src/python/model/model.py` |
| `Context` | App-wide config/logger/status/args container | `src/python/common/context.py` |
| Angular `AppComponent` | SPA shell, header, routing outlet | `src/angular/src/app/pages/main/app.component.ts` |
| Angular stream services | Consume SSE, maintain reactive client model | `src/angular/src/app/services/files/`, `services/base/` |

## Pattern Overview

**Overall:** Layered, event-driven coordinator with process isolation for heavy/blocking work.

**Key Characteristics:**
- **Single-coordinator, many-collaborators** — `Controller` is a thin coordinator that holds shared state (model, locks, queues) and delegates logic to injected collaborator objects (post-Phase-109 decomposition).
- **Dependency injection by construction** — `Controller.__init__` constructs all managers, then passes the *same instances* into `CommandProcessor`, `AutoDeleteManager`, and `ModelPipeline`. Collaborators construct no managers themselves (preserves `mock.patch` targets bound to `controller.controller`).
- **Process isolation for blocking work** — scanning, LFTP transfer, and archive extraction each run in separate OS processes (`AppProcess`/`AppOneShotProcess`); the coordinator stays responsive on its own thread.
- **Builder pattern for the web app** — `WebAppBuilder.build()` assembles handlers + stream handlers onto a `WebApp`.
- **Server-Sent Events for push** — the SPA receives model/status/log updates via long-lived SSE streams rather than polling.
- **Frozen immutable model files** — `ModelFile` is frozen after insertion, so reads can return direct references without deep-copying (reduces memory churn on API requests).

## Layers

**Frontend (Angular SPA):**
- Purpose: User-facing dashboard, settings, logs, about.
- Location: `src/angular/src/app/`
- Contains: standalone components (`pages/`), services (`services/`), pipes/directives (`common/`).
- Depends on: backend REST + SSE API only.
- Used by: end users via browser.

**Web Layer (Bottle):**
- Purpose: HTTP boundary — REST endpoints, SSE streams, static HTML serving, Bearer/HMAC auth, rate limiting.
- Location: `src/python/web/`
- Contains: `WebApp` (Bottle subclass), per-feature handlers (`web/handler/`), serializers (`web/serialize/`), `rate_limit.py`.
- Depends on: `Controller` (commands + model listeners), `Context.status`, `Config`.
- Used by: Angular SPA, Sonarr/Radarr webhooks.

**Controller Layer (coordination + domain logic):**
- Purpose: Orchestrate the sync lifecycle and own shared mutable state.
- Location: `src/python/controller/`
- Contains: `Controller` coordinator + collaborator managers + `scan/` and `extract/` sub-packages.
- Depends on: `model`, `lftp`, `system`, `ssh`, `common`.
- Used by: `ControllerJob` thread, `AutoQueue`, web handlers.

**Domain Model:**
- Purpose: Canonical file-state representation and diffing.
- Location: `src/python/model/`
- Contains: `Model`, `ModelFile`, `ModelDiff`/`ModelDiffUtil`.
- Depends on: `common`.
- Used by: `Controller`, `ModelPipeline`, `ModelBuilder`, web serializers.

**Infrastructure / Adapters:**
- Purpose: External-system integration.
- Location: `src/python/lftp/` (LFTP CLI wrapper + status parser), `src/python/ssh/` (SCP/SFTP), `src/python/system/` (local filesystem scanning), `src/python/scan_fs.py` (standalone remote scan executable).
- Depends on: `common`, external binaries (`lftp`, `ssh`).
- Used by: managers in the controller layer.

**Common / Cross-cutting:**
- Purpose: Config, status, context, logging, persistence, encryption, errors, bounded collections.
- Location: `src/python/common/`
- Used by: every layer.

## Data Flow

### Primary Request Path — user queues a download

1. SPA issues `POST /server/command/queue/<filename>` → `RestService` (`src/angular/src/app/services/utils/rest.service.ts`).
2. `ControllerHandler` receives the route, builds a `WebResponseActionCallback`, and enqueues a `Controller.Command` (`src/python/web/handler/controller.py`).
3. `Controller.queue_command()` puts the command on `__command_queue` (`controller.py:349`).
4. On the next tick, `ControllerJob.execute()` calls `Controller.process()` (`controller_job.py:24`).
5. `Controller.__process_commands()` pops the command, resolves the `ModelFile` under `__model_lock`, then delegates to `CommandProcessor.handle(file, command)` outside the lock (`controller.py:719`).
6. `CommandProcessor` invokes `LftpManager.queue()` (subprocess work) and reports success/failure back through the callback.

### Model-update pipeline (every controller tick)

1. `Controller.process()` → `__update_model()` (`controller.py:495`).
2. `ModelPipeline.update_model()` runs collect → feed → build (`model_pipeline.py`):
   - collect scan results, LFTP statuses, extract results,
   - feed them to `ModelBuilder`,
   - build a new model, diff against current, apply diffs under `model_lock`.
3. `Controller` retains two coordinator-only stages: `_update_active_file_tracking()` (owns `__active_downloading_file_names`) and `_update_controller_status()` (capacity write gating).
4. Applied diffs fire `IModelListener` events; SSE stream handlers push them to connected browsers (`web/handler/stream_model.py`).

### Webhook import + auto-delete flow

1. Sonarr/Radarr `POST /server/webhook/<...>` → `WebhookHandler` (HMAC-verified) → `WebhookManager` queue.
2. `Controller.__check_webhook_imports()` builds a name→root BFS lookup under `__model_lock`, processes the queue, records imports in persist (`controller.py:512`).
3. If `config.autodelete.enabled`, `__schedule_auto_delete()` arms a daemon `threading.Timer` per root (`controller.py:590`).
4. On fire, `__execute_auto_delete()` re-checks shutdown/config/state, calls `AutoDeleteManager.run_bfs_and_coverage()` (pack guard + coverage), then `FileOperationManager.delete_local()` outside the model lock (`controller.py:607`).

**State Management:**
- Authoritative state lives in the in-memory `Model` (guarded by `Controller.__model_lock`) plus on-disk persists (`controller.persist`, `autoqueue.persist`) and `settings.cfg`.
- `Context.status` holds live status surfaced over SSE.
- Frontend mirrors model/status reactively from SSE streams.

## Key Abstractions

**Command (`Controller.Command`):**
- Purpose: Client-requested action (QUEUE/STOP/EXTRACT/DELETE_LOCAL/DELETE_REMOTE) with success/failure callbacks executed on the controller thread.
- Examples: `src/python/controller/controller.py:35`, `src/python/web/handler/controller.py`.

**IModelListener / Model events:**
- Purpose: Push file_added/removed/updated events to subscribers (SSE handlers).
- Examples: `src/python/model/model.py:15`, `src/python/web/handler/stream_model.py`.

**AppProcess / AppOneShotProcess:**
- Purpose: Base classes for cross-process work with multiprocessing logging, exception propagation, and safe terminate.
- Examples: `src/python/common/app_process.py:29`, used by `scan/scanner_process.py`, `extract/extract_process.py`.

**Persist / Serializable:**
- Purpose: Versioned JSON persistence with corruption-backup fallback.
- Examples: `src/python/common/persist.py`, `controller/controller_persist.py`, `controller/auto_queue.py`.

**BoundedOrderedSet:**
- Purpose: Memory-bounded tracking of downloaded/extracted/stopped/imported file names with eviction stats.
- Examples: `src/python/common/bounded_ordered_set.py`, registered in `MemoryMonitor`.

**IHandler / IStreamHandler:**
- Purpose: Web handler contracts — REST handlers add routes; stream handlers feed SSE.
- Examples: `src/python/web/web_app.py:14`.

**Stream services (frontend):**
- Purpose: Base classes mapping SSE events to reactive Angular state.
- Examples: `src/angular/src/app/services/base/base-stream.service.ts`, `services/base/stream-service.registry.ts`.

## Entry Points

**Backend daemon:**
- Location: `src/python/seedsyncarr.py` (`main()` / `Seedsyncarr.run()`).
- Triggers: `seedsyncarr` console command / container start.
- Responsibilities: arg parsing, config + persist loading, object wiring, child-thread (`ControllerJob`, `WebAppJob`) lifecycle, restart/exit loop.

**Standalone remote scanner:**
- Location: `src/python/scan_fs.py`.
- Triggers: invoked over SSH on the remote host (and packaged as `scanfs` executable).
- Responsibilities: walk a directory tree and emit JSON file listing for the remote scanner.

**Web app (in-process):**
- Location: `src/python/web/web_app_job.py` → `WebAppJob`.
- Triggers: started by `Seedsyncarr.run()` as a child thread.
- Responsibilities: run the Bottle/Paste multi-threaded server.

**Frontend bootstrap:**
- Location: `src/angular/src/main.ts` → `bootstrapApplication(AppComponent, appConfig)`.
- Triggers: browser load of served `index.html`.
- Responsibilities: provide router (`app/routes.ts`), HTTP client + `authInterceptor`, and all singleton services (`app/app.config.ts`).

## Architectural Constraints

- **Threading model:** The controller and web server run as threads in a single process. Heavy/blocking work (scanning, LFTP transfer, extraction, deletion) is pushed into separate OS processes via `AppProcess`/`AppOneShotProcess`. Scanner processes never touch the in-memory `Model`, which is why a `threading.Lock` (not a multiprocessing lock) is sufficient for `__model_lock`.
- **Shared lock identity:** `Controller.__model_lock` is passed by reference into `ModelPipeline` and stored as `self._model_lock` (single underscore) to preserve object identity. Do not copy or re-create this lock — collaborators must operate on the *same* lock instance.
- **Lock ordering (deadlock avoidance):** When both are taken, the order is `__model_lock` → `__auto_delete_lock`. `exit()` takes **only** `__auto_delete_lock` (never `__model_lock`), so there is no circular wait. The auto-delete callback releases `__model_lock` before re-acquiring `__auto_delete_lock` for its final commit.
- **Shutdown signaling:** `Controller.__shutdown_event` is set under `__auto_delete_lock` inside `exit()` so it is strictly ordered against the auto-delete timer callback's lock-serialized final-commit step. Do not reuse `__started` for this — it flips too late.
- **DI binding for tests:** Managers are constructed only in `Controller.__init__`. Collaborators receive instances; they must not import-and-construct managers themselves, or `mock.patch("controller.controller.X")` in the test suite will stop intercepting.
- **Forwarding wrappers:** Many `Controller._collect_*` / `_feed_*` / `_apply_*` methods are thin forwarders to `ModelPipeline` kept on `Controller` because the test suite pins those names (e.g. `c._set_import_status = MagicMock()`). Keep the wrappers when moving logic.
- **Frozen model files:** `ModelFile` instances are immutable after being added to `Model`; reads return shared references. Never mutate a model file after insertion — build a new one and apply a diff.
- **Auth exemptions:** SSE (`/server/stream`), health (`/server/status`), and webhook prefixes (`/server/webhook/`) are exempt from Bearer auth by design (`web/web_app.py:59`). EventSource cannot send custom headers; webhooks use HMAC instead.

## Anti-Patterns

### Holding the model lock across blocking subprocess calls

**What happens:** Code resolves a `ModelFile` under `__model_lock`, then performs a subprocess-spawning operation (`delete_local`, LFTP queue) while still holding the lock.
**Why it's wrong:** Blocking subprocess calls under the lock starve all model updates running on the controller thread, freezing the UI.
**Do this instead:** Capture the (frozen) `ModelFile` reference under the lock, release the lock, then perform the subprocess work. See `Controller.__execute_auto_delete` (`controller.py:713`) and `Controller.__process_commands` (`controller.py:737`).

### Constructing managers inside a collaborator

**What happens:** A collaborator (`ModelPipeline`, `CommandProcessor`, `AutoDeleteManager`) instantiates its own `LftpManager`/`ScanManager`/etc.
**Why it's wrong:** It breaks the single-instance invariant and unbinds `mock.patch("controller.controller.*")` targets, silently disabling test interception; it can also create duplicate child processes.
**Do this instead:** Construct all managers once in `Controller.__init__` and inject the instances (`controller.py:187-221`).

### Re-creating or copying the model lock

**What happens:** A collaborator stores a copy of the lock or creates a new `Lock()`.
**Why it's wrong:** Two different lock objects provide no mutual exclusion; concurrent model mutation races.
**Do this instead:** Pass and store the same lock object (`model_lock` → `self._model_lock`, `model_pipeline.py:42`).

### Polling instead of streaming on the frontend

**What happens:** A component calls REST on an interval to refresh model/status.
**Why it's wrong:** The backend already pushes via SSE; polling adds latency and load and bypasses the reactive stream services.
**Do this instead:** Subscribe to the relevant stream service (`services/base/base-stream.service.ts`, `services/files/model-file.service.ts`).

## Error Handling

**Strategy:** Typed exception hierarchy rooted at `common.AppError`; cross-process exceptions are pickled and re-raised on the owner thread.

**Patterns:**
- Domain errors subclass `AppError` (`ControllerError`, `ModelError`, `ScannerError`, `ExtractError`, `PersistError`, `ConfigError`, `EncryptionError`).
- Child-process exceptions are wrapped (`ExceptionWrapper`, `tblib`) and propagated via `propagate_exception()` / `raise_pending_error()` calls in `Controller.__propagate_exceptions()` (`controller.py:750`).
- The main thread loop catches controller `AppError`, surfaces it to `status.server.error_msg`, and keeps the web server alive (`seedsyncarr.py:180`).
- `ServiceExit` / `ServiceRestart` flow up to `main()` to drive graceful shutdown vs. restart.
- Corrupt persist/config files are backed up (`*.N.bak`) and replaced with defaults rather than crashing (`seedsyncarr.py:_load_persist`).

## Cross-Cutting Concerns

**Logging:** Python `logging` with a shared root logger from `Context`; child loggers via `logger.getChild(...)`. Cross-process logging routed through `MultiprocessingLogger` (`common/multiprocessing_logger.py`). All user/remote-sourced values are passed through `sanitize_log_value()` before logging to prevent log injection (CWE-117). Web access has a separate logger.

**Validation:** Config validation in `common/config.py`; incomplete-config detection blocks controller startup. Webhook payloads HMAC-verified; command filenames URL-decoded and existence-checked against the model.

**Authentication:** Optional Bearer token on `/server/*` endpoints (`web/web_app.py`), with explicit exempt paths/prefixes; webhooks authenticated by HMAC secret; rate limiting via `web/rate_limit.py`. Secrets encrypted at rest via `common/encryption.py` (Fernet-style keyfile `secrets.key`).

---

*Architecture analysis: 2026-06-02*
