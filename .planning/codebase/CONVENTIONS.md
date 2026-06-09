# Coding Conventions

**Analysis Date:** 2026-06-09

This is a polyglot codebase: Python backend (`src/python/`), Angular frontend (`src/angular/`), Playwright e2e suite (`src/e2e/`). Conventions differ per language — follow the section matching the code you are touching.

## Naming Patterns

**Files:**
- Python: `snake_case.py` modules (`auto_queue.py`, `webhook_manager.py`, `rate_limit.py`). Packages have curated `__init__.py` re-exports.
- Angular: kebab-case with role suffix — `transfer-row.component.ts`, `rest.service.ts`, `file-size.pipe.ts`, `click-stop-propagation.directive.ts`, `auth.interceptor.ts`. Templates/styles co-located (`*.component.html`, `*.component.scss`).
- E2E: page objects as `<name>.page.ts`, specs as `<name>.page.spec.ts` or `<name>.spec.ts` in `src/e2e/tests/`.

**Functions:**
- Python: `snake_case` (`add_pattern`, `sanitize_log_value`). Type hints on public signatures (`def from_str(cls, content: str) -> "AutoQueuePattern":`).
- TypeScript: `camelCase` (`sendRequest`, `getRowCheckbox`, `waitForAtLeastFileCount`). Component event handlers prefixed `on` (`onCheckboxClick`).

**Variables:**
- Python: `snake_case` locals; class-level constants are double-underscore-mangled UPPER keys (`__KEY_PATTERN = "pattern"`); private instance attributes use double-underscore name mangling (`self.__patterns`, `self.__listeners_lock`) — see `src/python/controller/auto_queue.py`.
- TypeScript: `camelCase`; constructor-injected services use `_` prefix in older code (`private _logger`, `private _http` in `src/angular/src/app/services/utils/rest.service.ts`); class-level lookup tables are `private static readonly` UPPER_SNAKE `Record`s (`BADGE_LABELS` in `transfer-row.component.ts`). Module constants in e2e specs are UPPER_SNAKE (`TEST_FILE`, `STOPPED_SEED_RATE_LIMIT`).

**Types:**
- Python: `PascalCase` classes. Listener/interface abstractions are ABCs prefixed `I` (`IModelListener`, `IStatusListener`, `IAutoQueuePersistListener`). Custom errors end in `Error` (`AppError`, `ConfigError`, `PersistError` in `src/python/common/error.py`, `src/python/common/persist.py`).
- TypeScript: `PascalCase` classes/interfaces, no `I` prefix (`FileInfo`, `WebReaction`, `ViewFile`). Enums nested in namespaces (`ViewFile.Status`).

## Code Style

**Formatting:**
- Python: `ruff format` — verify with `ruff format --check src/python` (per `CONTRIBUTING.md`). 4-space indent.
- TypeScript (app): 4-space indent, double quotes, semicolons required, max line 140 — enforced by ESLint, not Prettier (no Prettier config exists).
- TypeScript (e2e + Playwright configs): single quotes, 4-space indent. The `src/angular/e2e/` and `src/e2e/` trees are excluded from ESLint (`ignores: ["e2e/"]`).

**Linting:**
- Python: `ruff check src/python/` (CI gate `lint-python` in `.github/workflows/ci.yml:73-90`). No `[tool.ruff]` section exists in `src/python/pyproject.toml` — ruff runs with default rules. Run it on the whole `src/python/` tree, not just changed files.
- Angular: ESLint flat config at `src/angular/eslint.config.js`; run `cd src/angular && npm run lint` — note `--max-warnings 0`, so warnings fail CI. Key rules:
  - `quotes: double` (template literals allowed), `semi: always`, `max-len: 140`
  - `eqeqeq: always` with `null: ignore` (`== null` checks permitted)
  - `no-console` except `warn`/`error`/`debug` — use `LoggerService` (`src/angular/src/app/services/utils/logger.service.ts`) instead
  - `curly: error`, `prefer-const`, `no-var`
  - `@typescript-eslint/explicit-function-return-type: warn`, `no-explicit-any: warn` (both fail the build via max-warnings 0)
  - `no-unused-vars` with `argsIgnorePattern: "^_"` — prefix intentionally unused params with `_`
  - `no-non-null-assertion` is OFF; `@Input({ required: true }) file!: ViewFile;` is an accepted pattern
- TypeScript strict mode is on (`src/angular/tsconfig.json`: `"strict": true`, `fullTemplateTypeCheck`, `strictInjectionParameters`).

## Import Organization

**Order (Python):**
1. Standard library (`import json`, `import threading`)
2. Third-party (`import pytest`, `from unittest.mock import MagicMock`)
3. First-party packages (`from common import overrides, Constants, Context`)
4. Relative within package (`from .controller import Controller`)

Packages re-export their public API in `__init__.py` using explicit `from .x import X as X` form (see `src/python/common/__init__.py`). Import from the package (`from common import Config`), not the submodule.

**Order (TypeScript):**
1. `@angular/*` core imports
2. `rxjs` / third-party
3. Local relative imports (services, then components/pipes)

**Path Aliases:**
- None. All TypeScript imports are relative (`../../../../services/utils/rest.service` from deep test paths). Python uses `pythonpath = ["."]` rooted at `src/python/` (set in `pyproject.toml [tool.pytest.ini_options]`).

## Error Handling

**Python:**
- Custom exception hierarchy in `src/python/common/error.py`: `AppError`, `ServiceExit`, `ServiceRestart`; domain errors `ConfigError`, `PersistError`, `EncryptionError`/`DecryptionError`. Raise specific errors, catch specific errors.
- Validate inputs and raise `ValueError` with a message (`raise ValueError("Cannot add blank pattern")` in `controller/auto_queue.py`).
- Web layer returns HTTP status codes (e.g., 429 from `web/rate_limit.py`) rather than leaking exceptions to clients.

**TypeScript:**
- Services wrap HTTP outcomes into result objects rather than throwing: `WebReaction {success, data, errorMessage}` via `catchError` in `src/angular/src/app/services/utils/rest.service.ts`. Follow this pattern for new backend calls — subscribe handlers branch on `reaction.success`.
- E2E helpers throw `Error` with full context (`Seed call ${method} ${url} failed: ${status} ${body}` in `src/e2e/tests/fixtures/seed-state.ts`).

## Logging

**Framework:**
- Python: stdlib `logging`, passed down via `Context` (`context.logger`); multiprocess-safe via `src/python/common/multiprocessing_logger.py`.
- Angular: `LoggerService` (`src/angular/src/app/services/utils/logger.service.ts`); direct `console.log` is lint-blocked.

**Patterns:**
- ALWAYS sanitize untrusted values (filenames, remote paths) before logging with `sanitize_log_value` from `common/types.py` — this is a CWE-117 log-injection guard covering CR/LF, C0 controls, and DEL. Tests exist at `tests/unittests/test_lftp/test_lftp_log_sanitization.py`.
- Angular debug logging uses printf-style args: `this._logger.debug("%s http response: %s", url, data)`.

## Comments

**When to Comment:**
- Explain WHY, often with traceability references to planning artifacts and review decisions (e.g., `pyproject.toml` cache_dir comment referencing "Phase 79 D-02"; e2e specs referencing "E2EFIX-07", "RESEARCH Pitfall 2"). This codebase heavily cross-references GSD phase decisions in comments — preserve that habit.
- Document thread-safety contracts in class docstrings ("Thread-safety: Listener operations are protected by __listeners_lock. The copy-under-lock pattern is used..." in `controller/auto_queue.py`).

**Docstrings/JSDoc:**
- Python: triple-quoted docstrings on classes and non-trivial functions. Two styles coexist — Sphinx `:param x:` (older code, `tests/utils.py`) and Google-style `Args:/Returns:` (newer code, `common/types.py`, `tests/helpers/__init__.py`). Prefer Google-style for new code.
- TypeScript: JSDoc on public service methods with `@param {type}` and `@returns` (see `rest.service.ts`).

## Function Design

**Size:** Small, single-purpose methods. Components keep logic in getters/computed signals; lookup data lives in `static readonly` Records, not switch statements.

**Parameters:**
- Python: keyword arguments at call sites for clarity (`AutoQueuePattern(pattern="file.one")`).
- TypeScript: optional params via `?` with `??` fallback (`post(url: string, body?: object)` sends `body ?? null`).

**Return Values:**
- Python: explicit return type hints; `@property` for read access to private state, returning defensive copies (`return set(self.__patterns)`).
- Angular services: return `Observable<WebReaction>` with `shareReplay(1)` to dedupe HTTP requests.

## Module Design

**Exports:**
- Python: package `__init__.py` is the public API surface (`from .types import overrides as overrides`). Don't reach into another package's submodules.
- Angular: standalone components with explicit `imports: [...]` arrays and `ChangeDetectionStrategy.OnPush` (`transfer-row.component.ts`). DI via constructor injection in services and via `inject()` in newer component code — both patterns are present; match the file you're editing.

**Barrel Files:**
- Python: yes (`__init__.py` re-exports per package: `common`, `controller`, `model`, `lftp`, `ssh`, `system`, `web`).
- Angular: no barrel files; import directly from the file.

**Layering (Python):**
- `web/handler/*` — HTTP endpoints only (Bottle); `controller/*` — business logic; `common/*` — shared infrastructure (config, persistence, logging, encryption); `lftp/`, `ssh/`, `system/` — external process integration; `model/` — domain model with listener interfaces. Keep HTTP concerns out of `controller/`.

**Interface/listener pattern (Python):**
- Define an ABC named `IXxxListener` with `@abstractmethod`s; implementers mark methods with `@overrides(IXxxListener)` (decorator in `common/types.py` asserts the override is valid). Notify listeners using copy-under-lock.

---

*Convention analysis: 2026-06-09*

