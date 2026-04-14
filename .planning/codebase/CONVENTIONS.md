# Coding Conventions

**Analysis Date:** 2026-02-03

## Naming Patterns

**Files:**
- **Components**: kebab-case for Angular components - `file.component.ts`, `file-list.component.ts`
- **Services**: kebab-case with `.service.ts` suffix - `server-status.service.ts`, `file-selection.service.ts`
- **Pipes**: kebab-case with `.pipe.ts` suffix - `eta.pipe.ts`, `file-size.pipe.ts`
- **Models**: CamelCase with intent - `ModelFile`, `ViewFile`
- **Interfaces**: PascalCase, often with prefix convention for private members
- **Test files**: Match source file with `.spec.ts` suffix - `file.component.spec.ts`
- **Python**: snake_case for modules and functions - `model.py`, `server.py`, `scan_manager.py`
- **Python classes**: PascalCase - `Controller`, `ModelFile`, `LftpManager`

**Functions:**
- **JavaScript/TypeScript**: camelCase for all functions and methods
- **Angular**: Methods prefixed with `on` for event handlers: `onCheckboxClick()`, `onInit()`
- **Angular pipes**: `transform()` for pipe implementation methods
- **Private methods**: Single underscore prefix in Python, `private` keyword or `#` in TypeScript

**Variables:**
- **JavaScript/TypeScript**: camelCase for all variables and parameters
- **Python**: snake_case for local variables and parameters
- **Constants**: UPPER_SNAKE_CASE when truly constant
- **Unused parameters**: Prefix with underscore to satisfy ESLint rule: `_param: Type`
- **TypeScript private fields**: Use `#` prefix for true privacy: `#listeners: IModelListener[]` or double underscore prefix: `__listeners = []`

**Types:**
- **TypeScript interfaces**: PascalCase prefixed with `I` for interfaces - `IHandler`, `IModelListener`
- **Enums**: PascalCase with UPPER_SNAKE_CASE values - `Action.QUEUE`, `Level.DEBUG`
- **Type aliases**: PascalCase - `ServerStatusJson`, `WebReaction`

## Code Style

**Formatting:**
- **Tool**: No external formatter configured (not using Prettier)
- **Indentation**: 2 spaces (observed in Angular code)
- **Line length**: Maximum 140 characters (ESLint rule: `max-len`)
- **Trailing spaces**: Not allowed (ESLint enforced)
- **End of file**: Must end with newline (ESLint: `eol-last`)

**Linting:**
- **Angular/TypeScript**: ESLint 9.x with TypeScript support (flat config format)
- **Config location**: `/Users/julianamacbook/seedsync/src/angular/eslint.config.js`
- **Key rules enforced**:
  - Double quotes for strings (`:` `"allowTemplateLiterals": true`)
  - Semicolons required at end of statements
  - `no-var` - must use `const` or `let`
  - `prefer-const` - prefer `const` over `let` when variable not reassigned
  - `no-console` - console allowed only for: `log`, `warn`, `error`, `debug`
  - `no-shadow` - inner scopes cannot redefine outer scope variables
  - `no-unused-vars` - parameters starting with `_` are exempt from unused warnings
  - `@typescript-eslint/explicit-function-return-type` - warn (preferred but not enforced)
  - `@typescript-eslint/no-explicit-any` - warn level
  - `@typescript-eslint/no-non-null-assertion` - error (use optional chaining)
- **Python**: pytest with standard linting (no explicit linter config found)

## Import Organization

**Order (TypeScript/Angular):**
1. Angular core imports (`@angular/core`, `@angular/common`, etc.)
2. Angular CDK/third-party library imports
3. Local application imports (relative paths with `./`)

Example from `/Users/julianamacbook/seedsync/src/angular/src/app/pages/files/file.component.ts`:
```typescript
import {
    Component, Input, Output, ChangeDetectionStrategy,
    EventEmitter, OnChanges, SimpleChanges, ViewChild, ElementRef,
    inject, computed, AfterViewInit
} from "@angular/core";
import {NgIf, DatePipe} from "@angular/common";

import {CapitalizePipe} from "../../common/capitalize.pipe";
import {EtaPipe} from "../../common/eta.pipe";
import {FileSizePipe} from "../../common/file-size.pipe";
import {ViewFile} from "../../services/files/view-file";
```

**Path Aliases:**
- No TypeScript path aliases detected in `tsconfig.json`
- All imports use relative paths

**Python imports:**
- Standard library imports first
- Then third-party imports (`bottle`, `pexpect`, etc.)
- Then local application imports (`from common import`, `from model import`)

Example from `/Users/julianamacbook/seedsync/src/python/web/handler/server.py`:
```python
from threading import Lock
from bottle import HTTPResponse

from common import Context, overrides
from ..web_app import IHandler, WebApp
```

## Error Handling

**Patterns (TypeScript/Angular):**
- **No try/catch blocks** in component code - errors are handled at the service level
- **Observable error handling**: Services use RxJS operators to handle HTTP errors
- **WebReaction pattern**: Services return a `WebReaction` object with `success: boolean`, `data: string`, `errorMessage: string`

Example from rest.service.ts:
```typescript
(err: HttpErrorResponse) => {
    let errorMessage = null;
    if (err.error instanceof Event) {
        errorMessage = err.error.type;
    } else {
        errorMessage = err.error;
    }
    observer.next(new WebReaction(false, null, errorMessage));
}
```

**Patterns (Python):**
- **Custom exceptions**: Inherit from `AppError` base class
- **Thread-safe operations**: Document thread-safety in docstrings when needed
- **Callbacks**: Used for async operations (Command pattern with ICallback interface)

Example from `/Users/julianamacbook/seedsync/src/python/controller/controller.py`:
```python
class ICallback(ABC):
    """Command callback interface"""
    @abstractmethod
    def on_success(self):
        """Called on successful completion of action"""
        pass

    @abstractmethod
    def on_failure(self, error: str, error_code: int = 400):
        """
        Called on action failure.
        Args:
            error: Human-readable error message
            error_code: HTTP status code (400, 404, 409, 500)
        """
        pass
```

## Logging

**Framework (Angular/TypeScript):**
- **LoggerService**: Custom injectable service, NOT Winston or other libraries
- **Location**: `/Users/julianamacbook/seedsync/src/angular/src/app/services/utils/logger.service.ts`
- **Levels**: `LoggerService.Level.ERROR`, `WARN`, `INFO`, `DEBUG`
- **API**: `logger.debug()`, `logger.info()`, `logger.warn()`, `logger.error()`
- **Implementation**: Wraps `console.*` methods, returns no-op function if level not met
- **Usage**: Injected as `@Injectable()`, accessed via constructor injection

```typescript
@Injectable()
export class LoggerService {
    public level: LoggerService.Level;

    get debug() {
        if (this.level >= LoggerService.Level.DEBUG) {
            return console.debug.bind(console);
        } else {
            return () => {};
        }
    }
}
```

**Framework (Python):**
- **Standard library**: `logging` module
- **Pattern**: `logger = logging.getLogger("ModuleName")`
- **Child loggers**: `self.logger = context.logger.getChild("ClassName")`
- **Levels**: Used naturally via `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()`

Example from `/Users/julianamacbook/seedsync/src/python/model/model.py`:
```python
def __init__(self):
    self.logger = logging.getLogger("Model")

def set_base_logger(self, base_logger: logging.Logger):
    self.logger = base_logger.getChild("Model")
```

## Comments

**When to Comment:**
- Document non-obvious design decisions (why, not what)
- Explain complex algorithms or workarounds
- Mark intentional deviations from conventions
- Use JSDoc/TSDoc for public APIs

**JSDoc/TSDoc Usage:**
- Document public methods and classes
- Use `@param`, `@return`, `@throws` for clarity
- Python uses docstring format (triple quotes)

Example from `/Users/julianamacbook/seedsync/src/angular/src/app/pages/files/file.component.ts`:
```typescript
/**
 * FileComponent displays a single file row in the file list.
 *
 * Session 16: Signal-Based Selection Architecture
 * - Injects FileSelectionService directly instead of receiving selection via @Input
 * - Uses computed() signal to derive selection state from the service
 * - This eliminates cascading checkbox updates on select-all
 */
@Component({
    selector: "app-file",
    // ...
})
export class FileComponent implements OnChanges, AfterViewInit {
```

**Code Comments:**
- Prefer self-documenting code over comments
- Use `// noinspection JSUnusedGlobalSymbols` to suppress IDE warnings when intentional

Example:
```typescript
// noinspection JSUnusedGlobalSymbols
get warn() {
    // Implementation...
}
```

## Function Design

**Size:**
- Methods should be focused and under 50 lines where practical
- Large methods extracted into managers (e.g., `ScanManager`, `LftpManager`)

**Parameters:**
- Prefer explicit parameters over options objects for < 3 params
- Use typed parameters (no untyped `any`)
- Document thread-safety in docstrings when relevant

**Return Values:**
- Prefer explicit return types (TypeScript)
- Use `null` for absence of value when appropriate (ESLint: `eqeqeq: ["error", "always", {"null": "ignore"}]`)
- Python: return tuples or custom objects for multiple values

Example signature from controller.py:
```python
def on_failure(self, error: str, error_code: int = 400):
    """
    Called on action failure.

    Args:
        error: Human-readable error message
        error_code: HTTP status code for the error (default 400)
    """
    pass
```

## Module Design

**Exports:**
- **Angular**: Use `exports` array in `@Component` decorator for standalone components
- **Python**: Explicit `__all__` list when relevant
- Services are singletons via Angular DI

Example from file.component.ts:
```typescript
@Component({
    selector: "app-file",
    standalone: true,
    imports: [NgIf, DatePipe, CapitalizePipe, EtaPipe, FileSizePipe, ClickStopPropagationDirective],
    // ...
})
export class FileComponent implements OnChanges, AfterViewInit {
```

**Barrel Files:**
- Not widely used in this codebase
- Most imports are direct paths to components/services

## TypeScript Specifics

**Decorators:**
- Angular 19.x syntax with experimental decorators enabled
- `@Component`, `@Injectable`, `@Pipe` are primary decorators
- `@Input()`, `@Output()`, `@ViewChild()` used for component interaction

**Interfaces:**
- Named with `I` prefix for clarity: `IHandler`, `IModelListener`, `ICallback`
- Abstract methods clearly marked

**Types vs Interfaces:**
- Prefer `interface` for object shapes (contracts)
- Use `type` for unions and complex types

**Generics:**
- Used in services for flexible APIs
- Example: Immutable.List<Pattern> for type-safe collections

**Angular Signals:**
- Modern signal API used: `signal()`, `computed()`, `effect()`
- Replaces older RxJS-heavy patterns
- FileComponent uses `computed()` for signal-based selection

## Async Patterns

**Observables:**
- RxJS streams for async operations
- Services return Observables
- Components subscribe with `.subscribe({next, error, complete})`
- `shareReplay(1)` used for preventing duplicate requests

**Promises:**
- Not primary pattern - Observables preferred
- Used for modal confirmations: `confirmModal.confirm().then()`

**Async/Await:**
- Not widely used in this codebase (RxJS dominant)
- When used in tests with `fakeAsync()` and `tick()`

---

*Convention analysis: 2026-02-03*
