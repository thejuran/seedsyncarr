# Coding Conventions

**Analysis Date:** 2026-06-02

This is a polyglot repo with two production languages plus a separate E2E layer. Conventions differ per language — follow the conventions of the directory you are editing.

| Layer | Language | Location | Lint/Style gate |
|-------|----------|----------|-----------------|
| Backend | Python 3.11–3.12 | `src/python/` | `ruff check src/python/` |
| Frontend | TypeScript / Angular 21 | `src/angular/` | `eslint "src/**/*.ts" --max-warnings 0` |
| E2E | TypeScript / Playwright | `src/e2e/` | not linted (excluded by Angular eslint `ignores`) |

---

## Naming Patterns

### Python (`src/python/`)

**Files:**
- `snake_case.py` for modules: `auto_queue_manager.py`, `model_builder.py`, `scan_manager.py`
- Test files prefixed `test_`: `test_auto_queue.py`, `test_controller.py`

**Classes:**
- `PascalCase`: `AutoQueuePattern`, `AutoQueuePersist`, `Controller`, `WebApp`
- Interface/listener classes use an `I` prefix: `IHandler`, `IModelListener`, `IAutoQueuePersistListener`, `IStatusListener`
- Custom exceptions inherit `AppError` and use `Error` suffix: `ConfigError`, `PersistError`, `DecryptionError`, `ServiceExit`, `ServiceRestart` (see `src/python/common/error.py`)

**Functions / methods:**
- `snake_case`: `add_pattern`, `sanitize_log_value`, `create_mock_context`
- Private methods use name-mangling double-underscore prefix: `__handle_get_autoqueue`, `__handle_add_autoqueue` (see `src/python/web/handler/auto_queue.py`)
- "Private but subclass-visible" attributes use single underscore: `self._logger`

**Variables / constants:**
- `snake_case` for locals, `UPPER_SNAKE` for module constants
- Type aliases are `PascalCase`: `InnerConfigType`, `OuterConfigType` (`src/python/common/config.py`)

### TypeScript (`src/angular/`)

**Files:**
- `kebab-case` with role suffix: `rest.service.ts`, `view-file.service.ts`, `logger.service.ts`, `eta.pipe.ts`, `click-stop-propagation.directive.ts`, `auth.interceptor.ts`
- Components: `*.component.ts` / `*.component.html` / `*.component.scss`
- Tests mirror source name with `.spec.ts` suffix: `rest.service.spec.ts`

**Classes / interfaces:**
- `PascalCase`: `RestService`, `WebReaction`, `LoggerService`, `AutoQueuePattern`
- Enums nested in a `namespace` matching the class: `LoggerService.Level` (`src/angular/src/app/services/utils/logger.service.ts`)

**Functions / methods:**
- `camelCase`: `sendRequest`, `handleSuccess`, `buildViewFromModelFiles`

**Variables:**
- `camelCase` for locals/fields, `UPPER_SNAKE` for module constants and fixtures: `MOCK_MODEL_FILES`, `SCREENSHOT_MODEL_FILES`
- Private instance fields use a leading underscore: `_logger`, `_http`, `_viewFileService` (constructor-injected via `private _logger: LoggerService`)

### E2E (`src/e2e/`)

- Page objects: `*.page.ts` (`dashboard.page.ts`, `settings.page.ts`); specs: `*.page.spec.ts` or `*.spec.ts`
- Fixtures in `src/e2e/tests/fixtures/` (`seed-state.ts`, `csp-listener.ts`)
- Module-scope constants `UPPER_SNAKE`: `TEST_FILE`, `STOPPED_SEED_RATE_LIMIT`

---

## Code Style

### Python

**Formatting:**
- 4-space indentation, no enforced line length (ruff defaults — there is **no** `[tool.ruff]` section in `src/python/pyproject.toml`, so the ruff default rule set `E`/`F` applies)
- String formatting uses `.format()` consistently, **not** f-strings: `"Bad config: {}.{} is empty".format(cls.__name__, name)` (`src/python/common/config.py`). Match this style in `common/`, `web/`, `controller/`.

**Linting:**
- `ruff check src/python/` runs as a dedicated CI gate (`.github/workflows/ci.yml` job `lint-python`, Python 3.12), **separate** from the pytest gate. A change that passes tests can still fail CI on ruff — run ruff over the whole `src/python/` tree (not just changed files) before declaring a Python phase done.
- Local: `ruff` is pinned in the dev extras (`ruff>=0.4.0`).

### TypeScript (Angular)

**Formatting:**
- 4-space indentation, double quotes (`"@typescript-eslint/quotes": double`, template literals allowed)
- Semicolons required (`semi: always`)
- `max-len` 140 chars
- `eol-last`, `no-trailing-spaces` enforced

**Linting (`src/angular/eslint.config.js`, flat config):**
- `eqeqeq: ["error", "always", { "null": "ignore" }]` — use `===`, but `== null` is permitted for null/undefined checks
- `no-var`, `prefer-const`, `curly` (always brace blocks), `radix`, `no-eval`, `no-bitwise`
- `no-console: ["error", { allow: ["warn", "error", "debug"] }]` — never use bare `console.log`; route logging through `LoggerService` or use `console.warn/error/debug`
- `@typescript-eslint/no-explicit-any: warn` and `explicit-function-return-type: warn` — annotate return types; avoid `any`
- `@typescript-eslint/no-unused-vars: ["error", { argsIgnorePattern: "^_" }]` — prefix intentionally unused args with `_`
- `@typescript-eslint/no-non-null-assertion: off` — the `!` assertion is *allowed* by lint, but per repo null-safety guidance prefer a guard or narrowing before asserting
- Lint runs with `--max-warnings 0`: warnings fail CI. Treat `any`/missing-return-type warnings as errors.

---

## Import Organization

### Python

Imports are grouped stdlib → third-party → first-party, blank-line separated:
```python
import configparser
import os
from typing import Dict, Optional

from .encryption import load_or_create_key, is_ciphertext
from .error import AppError
```
First-party packages are imported by their package facade, **not** deep module paths. `src/python/common/__init__.py` re-exports every public symbol with explicit `as` aliasing (`from .types import overrides as overrides`), so consumers write `from common import overrides, Config, PersistError`. Add new public symbols to the package `__init__.py` re-export list when introducing them.

### TypeScript

- **No path aliases** — the project uses relative imports exclusively (confirmed: `main.ts` uses `./environments/environment`, `app.config.ts` uses `../environments/environment`). Compute relative depth from the editing file's own location.
- Order: Angular/third-party first, then local, blank-line separated:
```typescript
import {Injectable} from "@angular/core";
import {HttpClient, HttpErrorResponse} from "@angular/common/http";
import {Observable, of} from "rxjs";

import {LoggerService} from "./logger.service";
```
- Brace imports have **no inner spaces**: `import {Injectable}` not `import { Injectable }` (Angular layer). Note the E2E layer (`src/e2e/`) uses spaced braces `import { test, expect }` — match the local file's surrounding style.

---

## Error Handling

### Python

- All domain exceptions derive from `AppError` (`src/python/common/error.py`). Add new error types as `AppError` subclasses, never bare `Exception`.
- Catch **specific** exceptions, never bare `except:`. Example in `web/handler/auto_queue.py`:
  ```python
  try:
      self.__auto_queue_persist.add_pattern(aqp)
      return HTTPResponse(body="Added auto-queue pattern '{}'.".format(pattern))
  except ValueError as e:
      return HTTPResponse(body=str(e), status=400)
  ```
- Web handlers translate errors into `bottle.HTTPResponse` with explicit status codes (`409`, `400`, `404`) — business logic raises, the handler layer maps to HTTP. Keep this separation: do not return raw HTTP objects from `controller/` or `model/`.
- Log sanitization is mandatory before interpolating untrusted strings (filenames, patterns) into log lines: use `sanitize_log_value()` from `common` (`src/python/common/types.py`) to neutralize CR/LF and control chars (CWE-117).

### TypeScript

- HTTP errors are normalized into a `WebReaction(success, data, errorMessage)` value object inside `RestService` rather than thrown — callers branch on `reaction.success` (`src/angular/src/app/services/utils/rest.service.ts`). Follow this pattern for new REST calls instead of letting `HttpErrorResponse` propagate.
- RxJS error flows use `catchError` returning `of(...)` so streams stay alive.
- Never expose raw error objects/stack traces to the UI; map to a user-facing message.

---

## Logging

### Python

- Standard library `logging`, obtained per-class: `logging.getLogger(ClassName.__name__)`. A multiprocessing-safe wrapper exists (`common/multiprocessing_logger.py`, `MultiprocessingLogger`).
- Always sanitize untrusted values before logging (`sanitize_log_value`). There is dedicated test coverage for this (`tests/unittests/test_lftp/test_lftp_log_sanitization.py`) — do not regress it.

### TypeScript

- Inject `LoggerService` (`src/angular/src/app/services/utils/logger.service.ts`); call `this._logger.debug(...)` / `.info` / `.warn` / `.error`. Levels are gated by `LoggerService.Level` and configured via `environment.logger.level` (DEBUG in dev, WARN in prod).
- Do not call `console.log` directly (eslint `no-console` forbids it; only `warn`/`error`/`debug` are allowed and those should still prefer the service).

---

## Comments

**When to comment:**
- Comments explain *why*, not *what* — heavily used for non-obvious decisions, cross-arch concerns, and security rationale. Examples: the `shareReplay(1)` rationale in `rest.service.ts`, the locale-determinism note in `playwright.config.ts`, the CWE-117 docstring in `types.py`.
- Phase/decision provenance is frequently referenced inline (e.g. `// FIX-01 anchor`, `# Reviewer feedback reversed Phase 79 D-02`). When touching such code, preserve the provenance comment.

**Docstrings (Python):**
- Triple-quoted docstrings on public functions/classes, often including `Args:` / `Returns:` sections (`src/python/tests/helpers/__init__.py`, `common/types.py`). Add type-hinted signatures plus a docstring for new public functions.

**JSDoc (TypeScript):**
- `/** ... */` blocks on public services/methods with `@param` / `@returns` (`rest.service.ts`). Not universally enforced, but match the file you are in.

---

## Function & Module Design

### Python

- **Type hints** on public signatures (`def sanitize_log_value(value: str) -> str:`). Avoid `Any` when a concrete type is known.
- Interface conformance is checked at decoration time with the custom `@overrides(InterfaceClass)` decorator (`common/types.py`) — apply `@overrides(IHandler)` etc. when implementing an interface method so a typo'd override fails fast.
- Dependency injection by constructor: handlers/managers receive their collaborators (`def __init__(self, auto_queue_persist: AutoQueuePersist)`), they do not reach for globals.
- Keep HTTP/bottle concerns in `web/`, orchestration in `controller/`, data in `model/`, shared primitives in `common/`. Do not mix layers.

### TypeScript

- Services are `@Injectable()` classes with constructor DI (`constructor(private _logger: LoggerService, private _http: HttpClient)`).
- Value objects use `readonly` fields set in the constructor (`WebReaction`).
- Prefer returning small factory closures for handler logic (`handleSuccess(url)` returns a mapper) rather than inline arrow functions in render paths.
- Immutable data uses the `immutable` library (`Immutable.Map<string, ModelFile>`).

---

## Module Exports

**Python:** Each package's `__init__.py` is a curated facade with explicit `X as X` re-exports (`common/__init__.py`). New public symbols must be added there to be importable as `from common import X`.

**TypeScript:** No barrel files — each symbol is imported from its own relative module path. Keep one primary export per file matching the filename role.

---

*Convention analysis: 2026-06-02*
