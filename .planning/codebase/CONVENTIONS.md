# Coding Conventions

**Analysis Date:** 2026-05-26

SeedSyncarr is a polyglot codebase with two distinct stacks, each with its own conventions:

- **Angular/TypeScript** frontend (`src/angular/`)
- **Python** backend (`src/python/`)
- **Playwright/TypeScript** e2e tests (`src/e2e/`)

Conventions differ per stack — always confirm which stack you are editing before applying a rule.

## Naming Patterns

**Files:**
- TypeScript components: `kebab-case.component.ts` (e.g., `bulk-actions-bar.component.ts`, `transfer-row.component.ts`)
- TypeScript services: `kebab-case.service.ts` (e.g., `file-selection.service.ts`, `rest.service.ts`)
- TypeScript pipes/directives: `kebab-case.pipe.ts`, `kebab-case.directive.ts`
- TypeScript model classes/utilities: `kebab-case.ts` (e.g., `view-file.ts`, `localization.ts`)
- Test specs (Angular): `<source>.spec.ts` mirroring source name
- Test specs (Playwright): `<page>.page.spec.ts` and `<page>.page.ts` for page objects
- Python modules: `snake_case.py` (e.g., `auto_queue.py`, `job_status_parser.py`)
- Python test modules: `test_<subject>.py` placed under `tests/unittests/test_<module>/` or `tests/integration/`

**Directories:**
- Angular feature areas: `src/app/pages/<feature>/`, `src/app/services/<area>/`
- Python module package directories: lowercase singular (`common/`, `controller/`, `model/`, `lftp/`)

**Functions / methods:**
- TypeScript: `camelCase` (e.g., `selectMultiple`, `getSelectedFiles`, `onQueueClick`)
- Python: `snake_case` (e.g., `add_pattern`, `from_str`, `set_base_logger`)
- Python "dunder-private" methods use leading double underscore for name-mangling
  (e.g., `__notify_listeners`, `__listeners_lock` in `src/python/controller/auto_queue.py`)

**Variables:**
- TypeScript: `camelCase` for locals/fields; private fields commonly prefixed with underscore
  (e.g., `_cachedSelectedViewFiles` in `src/angular/src/app/pages/files/bulk-actions-bar.component.ts`)
- Python: `snake_case`; private with single leading underscore `_` or double `__` for mangled
- Module-level constants: `UPPER_SNAKE_CASE` in both Python (`MAX_CONSECUTIVE_STATUS_ERRORS` in `src/python/lftp/lftp.py:12`)
  and TypeScript (`SEGMENTS`, `SEGMENT_STATUSES` in `src/angular/src/app/pages/files/transfer-table.component.ts`)

**Types / Classes:**
- TypeScript classes/interfaces/enums: `PascalCase` (e.g., `BulkActionsBarComponent`, `BulkActionCounts`, `OptionType`)
- Python classes: `PascalCase` (e.g., `AutoQueuePattern`, `LftpJobStatusParser`, `Controller`)
- Angular interfaces are NOT prefixed with `I` (uses plain `RouteInfo`, `FileInfo`, `BulkActionCounts`)
- Python abstract base classes ARE prefixed with `I` for listener/handler interfaces
  (`IModelListener`, `IAutoQueuePersistListener`, `IHandler`, `IStreamHandler`)
- Custom exception classes end in `Error` and extend `AppError` (e.g., `ControllerError`, `ModelError`, `LftpError`, `ConfigError`)

## Code Style

**Formatting (TypeScript):**
- Indent: 4 spaces (set via `src/angular/.editorconfig`)
- Quotes: double quotes enforced by ESLint rule `"quotes": ["error", "double", { "allowTemplateLiterals": true }]`
- Semicolons: required (`"semi": ["error", "always"]`)
- Line length: max 140 chars (`"max-len": ["error", { "code": 140 }]`)
- Trailing newline required; no trailing whitespace
- Final newline on every file (`"eol-last": "error"`)

**Linting (TypeScript):**
- Config: `src/angular/eslint.config.js`
- Run: `cd src/angular && npm run lint` (alias for `eslint "src/**/*.ts" --max-warnings 0`)
- Notable rules:
  - `eqeqeq: ["error", "always", { "null": "ignore" }]` — use `===`, but `== null` is allowed for null/undefined check
  - `"@typescript-eslint/no-explicit-any": "warn"`
  - `"@typescript-eslint/explicit-function-return-type": "warn"` — return types should be explicit
  - `"@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }]` — prefix unused args with `_`
  - `"@typescript-eslint/no-non-null-assertion": "off"` — non-null `!` is allowed (use sparingly with a preceding guard)
  - `"no-console": ["error", { "allow": ["warn", "error", "debug"] }]` — `console.log` is forbidden; use `LoggerService` (`src/angular/src/app/services/utils/logger.service.ts`)
  - `"curly": "error"` — single-line `if` bodies must still use braces
  - `"no-var": "error"`, `"prefer-const": "error"`
- ESLint ignores: `node_modules/`, `dist/`, `e2e/` (Playwright e2e tree has its own tsconfig), and `**/*.js`

**TypeScript compiler (`src/angular/tsconfig.json`):**
- `strict: true`
- `target: "ES2022"`, `module: "ES2022"`, `moduleResolution: "bundler"`
- `emitDecoratorMetadata: true`, `experimentalDecorators: true`
- `useDefineForClassFields: false` (Angular 21 setup)
- Angular: `fullTemplateTypeCheck: true`, `strictInjectionParameters: true`

**Formatting (Python):**
- Indent: 4 spaces
- Strings: mixed (single and double both used) — no enforced quote style
- Type hints: present on most public function signatures (`def __init__(self, pattern: str)`, `def add_pattern(self, pattern: AutoQueuePattern) -> None`)
- Line length: ruff defaults (88), but no explicit override

**Linting (Python):**
- Tool: `ruff` (configured implicitly via defaults; no `[tool.ruff]` section in `src/python/pyproject.toml`)
- Run: `ruff check src/python/` (per `.github/workflows/ci.yml:90`)
- Python version target: `>=3.11,<3.13` per `pyproject.toml`

## Import Organization

**TypeScript (observed pattern):**
1. Angular framework imports (`@angular/core`, `@angular/common/http`, `@angular/router`)
2. Third-party libraries (`rxjs`, `immutable`, `bootstrap`)
3. Blank line
4. Local/relative imports (`../../services/...`, `../../common/...`)

Example from `src/angular/src/app/pages/files/transfer-table.component.ts`:
```typescript
import {Component, ChangeDetectionStrategy, DestroyRef, ...} from "@angular/core";
import {AsyncPipe} from "@angular/common";
import {Observable, BehaviorSubject, Subject, combineLatest} from "rxjs";
import {List} from "immutable";

import {ViewFileService} from "../../services/files/view-file.service";
import {TransferRowComponent} from "./transfer-row.component";
```

**Python (observed pattern):**
1. Stdlib imports (`os`, `sys`, `logging`, `threading`)
2. Blank line
3. Third-party (`pexpect`, `bottle`, `pytest`)
4. Blank line
5. Local package imports (`from common import ...`, `from controller import ...`, `from .scan_manager import ...`)

Example from `src/python/controller/controller.py:1-22`:
```python
from abc import ABC, abstractmethod
import collections
import os
import threading
from typing import Dict, List, Optional, Tuple

from .scan_manager import ScanManager
from common import Context, AppError, MultiprocessingLogger
from model import ModelError, ModelFile, Model
from lftp import LftpError, LftpJobStatus
```

**Path Aliases:**
- TypeScript: none configured — all local imports use relative paths
- Python: project root is on `pythonpath` per `[tool.pytest.ini_options] pythonpath = ["."]` so packages import as `from common import ...`, `from controller import ...`

## Error Handling

**Python:**
- Domain errors subclass `AppError` (defined in `src/python/common/error.py`)
- Each module defines its own `*Error` (`ControllerError`, `ModelError`, `LftpError`, `ConfigError`, `PersistError`, `ScannerProcessDiedError`)
- `ServiceExit` and `ServiceRestart` extend `AppError` to signal clean shutdown / restart from any thread
- Long-running jobs catch broad `Exception` ONLY at the top of the thread loop and propagate via `self.exc_info = sys.exc_info()` then set `shutdown_flag` (see `src/python/common/job.py:38-45`)
- Avoid bare `except:` — always catch a specific exception or `Exception`
- Re-raise with context via tuple-style propagation; `tblib` is a dep so tracebacks can cross process boundaries

**TypeScript:**
- HTTP errors are converted to a `WebReaction { success, data, errorMessage }` envelope in `RestService` (`src/angular/src/app/services/utils/rest.service.ts:86-93`)
- Components do not throw — they return failed `WebReaction` values
- Error UI flows through `NotificationService` (`src/angular/src/app/services/utils/notification.service.ts`) and `ToastService`
- `try/catch` is used sparingly; prefer rxjs `catchError` for streams
- Never re-throw an `HttpErrorResponse` to the template; map it through `WebReaction`

## Logging

**Python:**
- Use `logging` module; obtain loggers via `context.logger.getChild("ComponentName")` (e.g., `Controller`, `WebApp`, `ScanManager`)
- Multi-process logging routed through `MultiprocessingLogger` (`src/python/common/multiprocessing_logger.py`); scanner subprocesses call `mp_logger.get_process_safe_logger()`
- Levels: `.debug()`, `.info()`, `.warning()`, `.error()`, `.exception()` (latter for unhandled exceptions in catch blocks)
- Format string style: `"Thread {} started".format(self.name)` (older `.format()` style is dominant; do NOT mix with f-strings in the same file unless the file already uses f-strings)
- NEVER log full request bodies with auth headers, passwords, tokens, or API keys

**TypeScript:**
- Inject `LoggerService` (`src/angular/src/app/services/utils/logger.service.ts`)
- Call `this._logger.debug(...)`, `.info(...)`, `.warn(...)`, `.error(...)`
- `console.log` is BANNED by ESLint; `console.warn`, `console.error`, `console.debug` are allowed only as a last resort
- Logger uses printf-style: `this._logger.debug("%s http response: %s", url, data)`

## Comments

**When to Comment:**
- Non-obvious design decisions, thread-safety guarantees, and historical context are documented inline
  (see `src/python/controller/auto_queue.py:54-56` describing the "copy-under-lock" listener pattern)
- Reference phase/issue identifiers in comments when the code encodes a fix:
  `// FIX-01 D-09 case 2`, `// See phase 75 (GH #19) D-09, D-10`
- Security-critical configs include a rationale (e.g., the `_AUTH_EXEMPT_PATHS` and `R001-R005` reference codes in `src/python/web/web_app.py:59-65`)

**JSDoc / TSDoc:**
- Public services and components have a leading block comment describing purpose, thread-safety, and architecture
  (see `FileSelectionService` comment in `src/angular/src/app/services/files/file-selection.service.ts:8-28`)
- Public methods have `/** ... */` JSDoc with `@param` for non-obvious parameters
- Older RestService methods use legacy `@returns {Observable<WebReaction>}` form

**Python docstrings:**
- Triple-quoted, line 1 = summary, blank line, then details
- Args / Returns sections use plain text, not Google or NumPy style strictly — but most public methods have at least a one-line description
- Thread-safety notes are common (see `Model` class in `src/python/model/model.py:40-47`)

## Function Design

**Size:**
- Prefer methods under ~50 lines; longer methods exist in `Controller` and `WebApp` but are exceptions
- Extract helpers (e.g., `_recomputeCachedValues` in `BulkActionsBarComponent`) when a method has multiple distinct phases

**Parameters:**
- Python: keyword args for any boolean or optional parameter; required positional args first
  (e.g., `LftpJobStatus(job_id=42, job_type=..., state=..., name="", flags="")`)
- TypeScript: small object parameter when 3+ optional fields (e.g., `new ViewFile({ name, isQueueable, ... })`)
- Avoid mutable default arguments in Python — always use `None` and initialize inside

**Return Values:**
- TypeScript: explicit return types required by lint (warn-level)
- Python: type-hint the return where the type is non-trivial (`-> Tuple[List[...], List[...]]`)
- `null` / `None` returns must always be guarded at call sites — never dereference without a check

## Module Design

**Exports (TypeScript):**
- One component / service per file, exported by name
- Re-exports happen at `src/app/...` boundaries; no barrel `index.ts` files in the Angular tree
- Components are `standalone: true` (Angular 21) — no NgModules; imports listed inline on the `@Component` decorator

**Exports (Python):**
- Each package has an `__init__.py` that re-exports the public API
  (e.g., `from controller import Controller, ControllerJob, ControllerPersist, AutoQueue, AutoQueuePersist`)
- Underscore-prefixed names (`_SECRET_FIELD_PATHS`, `_VIDEO_EXTENSIONS`) are module-private and not re-exported

**Barrel Files:**
- Python uses `__init__.py` as the package barrel
- Angular does NOT use barrel files — imports always reach into the specific file

## Angular-Specific Patterns

- **Standalone components:** Every component declares `standalone: true` and lists its `imports` inline on `@Component`
- **Change detection:** Default to `ChangeDetectionStrategy.OnPush` for any component handling lists or signal-driven state
  (`BulkActionsBarComponent`, `TransferRowComponent`, `TransferTableComponent`, `OptionComponent`)
- **Signals over BehaviorSubjects:** New state should use `signal()` + `computed()` (see `FileSelectionService`). Keep an Observable view via `toObservable()` only for backwards compatibility
- **Cleanup:** Components subscribing manually use `takeUntilDestroyed(this.destroyRef)` (preferred) or a `destroy$ = new Subject<void>()` + `takeUntil(this.destroy$)` pair completed in `ngOnDestroy`
- **Inputs / Outputs:** Use `@Input()` / `@Output() = new EventEmitter<T>()`. Required inputs use `@Input({ required: true }) file!: ViewFile`
- **Immutable.js:** `immutable` (`List`, `Map`) is used for collections in services; never mutate in place
- **DI:** `inject(Service)` is preferred over constructor injection for new code, but both patterns coexist

## Python-Specific Patterns

- **`@overrides(BaseClass)` decorator:** Defined in `src/python/common/types.py:3-14`; applied to any method that overrides a base class — runtime assertion that the method name exists on the parent
- **`Persist` / `Serializable`** ABCs in `src/python/common/persist.py` define `from_str` / `to_str` contract for any state class persisted to disk; `to_file` chmods the file to `0o600` after write
- **Thread safety / "copy-under-lock":** When notifying listeners, copy the listener list inside the lock and iterate outside the lock (see `AutoQueuePersist.add_pattern` in `src/python/controller/auto_queue.py:75-81`)
- **Listener interfaces:** Abstract base classes with `@abstractmethod` (e.g., `IModelListener`, `IAutoQueuePersistListener`)
- **Process boundaries:** `MultiprocessingLogger`, `Queue`, and `tblib` are used to bridge processes; never share Python locks across processes
- **Context object:** `common.Context` carries `config`, `args`, `logger`, `status`; passed down through `Controller(context, persist, webhook_manager)` rather than module-global state

## Security Conventions

- Never interpolate user input into shell commands — use `pexpect.spawn` with an args list or use `subprocess` with `shell=False`
- Bearer token auth on `/server/*` paths; exemptions enumerated explicitly in `_AUTH_EXEMPT_PATHS` / `_AUTH_EXEMPT_PREFIXES` (`src/python/web/web_app.py:58-65`)
- Webhooks authenticate via HMAC (R004), not Bearer tokens
- Secrets (`webhook_secret`, `api_token`, `remote_password`, Sonarr/Radarr API keys) are encrypted at rest via `src/python/common/encryption.py`; the list of secret paths is the single source of truth in `_SECRET_FIELD_PATHS`
- Persist files chmod to `0o600` (owner read/write only)
- `gitleaks` is configured at `.gitleaks.toml`

---

*Convention analysis: 2026-05-26*
