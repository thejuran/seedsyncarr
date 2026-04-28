# Phase 96: Rate Limiting & Tooling - Research

**Researched:** 2026-04-28
**Domain:** Python HTTP handler decorators (Bottle/Paste), Semgrep rule authoring
**Confidence:** HIGH

## Summary

Phase 96 has two independent workstreams: (1) adding a reusable sliding-window rate-limiting decorator to three HTTP endpoints in the Python web layer, and (2) tightening two Semgrep rules in `shield-claude-skill` to eliminate 628 false positives.

The rate-limiting work is a pure extraction-and-apply task. The existing `ControllerHandler._check_bulk_rate_limit()` in `controller.py` (lines 229-251) is a complete, tested, thread-safe implementation using Python's `threading.Lock` and a list-based sliding window. The new `rate_limit.py` module must extract this pattern into a standalone decorator factory — no new algorithm is needed, only a generalization of proven code. The decorator must preserve the original handler's signature so Bottle's routing (which passes path variables as keyword args) continues to work; `functools.wraps` is required.

The Semgrep work is two surgical YAML edits to `shield-claude-skill/configs/semgrep-rules/javascript.yaml`. TOOL-01 converts the `js-nosql-injection-where` rule from a free-variable `pattern:` to a `patterns:` block that adds a `metavariable-regex` constraint restricting `$WHERE` to the literal string `$where`. TOOL-02 adds `pattern-not` entries for arrow-function and named-function callbacks in `setTimeout`/`setInterval` patterns, matching the style of the existing `pattern-not: eval("...")` entry. No other files in `shield-claude-skill` require changes. The `metavariable-regex` syntax is already used in other rule files in the same repo (`go.yaml`, `java.yaml`, `csharp.yaml`, `ruby.yaml`, `rust.yaml`), so the syntax is validated and consistent.

**Primary recommendation:** Extract the sliding-window logic into `src/python/web/rate_limit.py` as a decorator factory, apply it at `add_routes()` call sites in ConfigHandler and StatusHandler, refactor ControllerHandler to use it for the bulk endpoint, and make the two YAML edits to the Semgrep rules. Both workstreams are isolated — they can be planned as separate tasks with no ordering dependency between them.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Two-tier threshold model: 60 req/60s for `/server/config/set` and `/server/status`; 5 req/60s for `/server/config/test/*`.
- **D-02:** Higher tier (60/60s) accommodates per-field config saves and frontend status polling. Lower tier (5/60s) constrains expensive outbound HTTP calls to Sonarr/Radarr.
- **D-03:** Existing bulk endpoint rate limit (10/60s in `ControllerHandler`) must be refactored to use the new decorator but keep its threshold unchanged.
- **D-04:** Create a standalone decorator function in a new `src/python/web/rate_limit.py` module. Sliding-window algorithm matching the existing pattern in `controller.py:229-251`. State per-instance via closure.
- **D-05:** Refactor `ControllerHandler._check_bulk_rate_limit()` to use the new decorator, eliminating duplicated sliding-window logic.
- **D-06:** Decorator accepts `max_requests` and `window_seconds` parameters. Returns HTTP 429 with JSON body `{"error": "Rate limit exceeded. Please try again later."}` and `content_type: application/json`.
- **D-07:** TOOL-01 (`js-nosql-injection-where`, 617 FPs): Add `metavariable-regex` constraint on `$WHERE` matching `^\$where$`. ~3 lines added.
- **D-08:** TOOL-02 (`js-xss-eval-user-input`, 11 FPs): Add `pattern-not` exclusions for arrow-function and named-function callbacks in `setTimeout`/`setInterval`.
- **D-09:** Both Semgrep changes confined to `shield-claude-skill/configs/semgrep-rules/javascript.yaml`. Validate with `semgrep --test` if fixture files exist.

### Claude's Discretion

No specific requirements — open to standard approaches within the decisions above.

### Deferred Ideas (OUT OF SCOPE)

- e2e-csp-violation-detection — already complete in Phase 91
- arm64-unicode-sort-e2e-failures — already complete in Phase 91
- webob-cgi-upstream-unblock — blocked on upstream webob 2.0
- migrate-config-set-to-post-body — backend API contract change, explicitly out of scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RATE-01 | Add reusable rate-limiting decorator for HTTP endpoints | Extract `_check_bulk_rate_limit` into `rate_limit.py` decorator factory with closure-based state |
| RATE-02 | Apply rate limiting to `/server/config/set` endpoint | Wrap `__handle_set_config` in `ConfigHandler.add_routes()` at 60/60s tier |
| RATE-03 | Apply rate limiting to `/server/config/test/*` endpoints | Wrap `__handle_test_sonarr_connection` and `__handle_test_radarr_connection` at 5/60s tier |
| RATE-04 | Apply rate limiting to `/server/status` endpoint | Wrap `__handle_get_status` in `StatusHandler.add_routes()` at 60/60s tier |
| TOOL-01 | Tighten `js-nosql-injection-where` — add MongoDB context constraint | Convert to `patterns:` block, add `metavariable-regex` on `$WHERE` matching `^\$where$` |
| TOOL-02 | Tighten `js-xss-eval-user-input` — exclude arrow/named function callbacks | Add `pattern-not` entries for `setTimeout($X => ..., ...)` and `setTimeout(function $F(...) {...}, ...)` |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Rate limiting enforcement | API / Backend | — | Bottle/Paste handles HTTP; rate state lives in handler instances |
| Rate limit state storage | API / Backend (in-process) | — | Sliding window list + Lock per handler instance; no external cache needed |
| Semgrep rule authoring | Tooling (shield-claude-skill) | — | YAML rule config; no runtime tier involvement |
| HTTP 429 response format | API / Backend | — | JSON body, `application/json` content-type, returned by decorator |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `threading.Lock` | stdlib | Thread-safe rate state | Already used in `ControllerHandler` — Paste httpserver is multithreaded [VERIFIED: codebase grep] |
| `functools.wraps` | stdlib | Preserve wrapped function metadata | Required so Bottle can inspect handler signature for path variable injection [VERIFIED: codebase grep + Python docs] |
| `time.time()` | stdlib | Sliding-window timestamp | Already used in `controller.py:239` [VERIFIED: codebase grep] |
| `bottle.HTTPResponse` | project dependency | 429 response object | Consistent with existing 429 pattern in `controller.py:279-283` [VERIFIED: codebase grep] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `semgrep` | 1.x (installed at `/Users/julianamacbook/Library/Python/3.9/bin/semgrep`) | Rule validation | Use `semgrep --validate` on modified YAML before commit [VERIFIED: `command -v semgrep`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-process sliding window | Redis / external rate limiter | External store adds a network dependency; homelab tool has no Redis; in-process is correct scope |
| Closure-based state | Class-based decorator | Both work; closure is simpler for a function-only module as specified in D-04 |

**Installation:** No new packages required. All dependencies are Python stdlib or existing project dependencies. [VERIFIED: pyproject.toml]

---

## Architecture Patterns

### System Architecture Diagram

```
HTTP request
    |
    v
Bottle router (WebApp.add_handler / add_post_handler)
    |
    v
rate_limit decorator (closure wraps original handler)
    |-- sliding window check (Lock + list of timestamps)
    |     |-- OVER LIMIT --> HTTPResponse(429, JSON)
    |     |-- UNDER LIMIT --> record timestamp, call original handler
    |
    v
Original handler method (__handle_set_config, __handle_get_status, etc.)
    |
    v
HTTPResponse
```

**Decorator application point:** At `add_routes()` call time, the handler method is wrapped before being passed to `web_app.add_handler(path, decorated_handler)`. Each endpoint gets its own decorator instance (its own closure state), so rate limit state is isolated per endpoint.

### Recommended Project Structure

```
src/python/web/
├── rate_limit.py          # NEW: sliding-window decorator factory
├── handler/
│   ├── controller.py      # MODIFIED: remove _check_bulk_rate_limit, use decorator
│   ├── config.py          # MODIFIED: wrap set_config + test_* in add_routes()
│   └── status.py          # MODIFIED: wrap __handle_get_status in add_routes()
tests/unittests/test_web/
├── test_rate_limit.py     # NEW: unit tests for decorator module
└── test_handler/
    ├── test_config_handler.py     # MODIFIED: add rate limit tests
    ├── test_status_handler.py     # MODIFIED: add rate limit tests
    └── test_controller_handler.py # MODIFIED: update to use new decorator (tests already pass)
shield-claude-skill/configs/semgrep-rules/
└── javascript.yaml        # MODIFIED: TOOL-01 + TOOL-02 fixes
```

### Pattern 1: Sliding-Window Rate-Limit Decorator Factory

**What:** A function `rate_limit(max_requests, window_seconds)` that returns a decorator. The decorator uses a closure to store `request_times: List[float]` and a `Lock`. Each call checks and updates the list.

**When to use:** Applied once per endpoint at `add_routes()` time.

```python
# Source: extracted and generalized from controller.py:229-251
import time
import json
import logging
import functools
from threading import Lock
from typing import List, Callable

from bottle import HTTPResponse

logger = logging.getLogger(__name__)

def rate_limit(max_requests: int, window_seconds: float) -> Callable:
    """
    Returns a decorator that enforces a sliding-window rate limit.

    Args:
        max_requests: Maximum number of requests allowed within the window.
        window_seconds: Duration of the sliding window in seconds.

    Returns:
        A decorator that wraps a Bottle handler method.
    """
    def decorator(func: Callable) -> Callable:
        request_times: List[float] = []
        lock = Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            with lock:
                # Evict timestamps outside the window
                request_times[:] = [t for t in request_times if now - t < window_seconds]
                if len(request_times) >= max_requests:
                    logger.warning("Rate limit exceeded for %s", func.__name__)
                    return HTTPResponse(
                        body=json.dumps({"error": "Rate limit exceeded. Please try again later."}),
                        status=429,
                        content_type="application/json"
                    )
                request_times.append(now)
            return func(*args, **kwargs)

        return wrapper
    return decorator
```

**Critical detail:** `functools.wraps(func)` is non-optional. Bottle inspects the wrapped callable's signature to extract path variables (e.g., `section`, `key`, `value` in `/server/config/set/<section>/<key>/<value:re:.+>`). Without `wraps`, Bottle sees `wrapper(*args, **kwargs)` and cannot match path variables — routes with path variables will break. [VERIFIED: Bottle source pattern + `functools.wraps` docs — ASSUMED: Bottle's exact inspection mechanism, but `wraps` is the standard fix and used universally]

**State isolation note:** Each call to `rate_limit(...)` creates a new closure with its own `request_times` list and `Lock`. Calling it twice (e.g., once for sonarr-test, once for radarr-test) gives two independent rate limit counters — which is the correct behaviour: each endpoint has its own budget.

**Thread-safety note:** `request_times[:] = [...]` (in-place slice assignment) mutates the existing list rather than rebinding the name, which is safe within the `with lock:` block. [VERIFIED: controller.py:242-244 uses list comprehension reassignment under lock — same pattern]

### Pattern 2: Decorator Application in `add_routes()`

**What:** Wrap the private handler method with the decorator before passing to `web_app.add_handler`.

**When to use:** Applied once in `add_routes()` for each endpoint that needs rate limiting.

```python
# Source: pattern derived from config.py:19-25 + controller.py:67-72 [VERIFIED: codebase read]
from web.rate_limit import rate_limit

_RATE_HIGH = rate_limit(max_requests=60, window_seconds=60.0)   # config/set, status
_RATE_LOW  = rate_limit(max_requests=5,  window_seconds=60.0)   # test-connection

class ConfigHandler(IHandler):
    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_handler("/server/config/get", self.__handle_get_config)
        web_app.add_handler(
            "/server/config/set/<section>/<key>/<value:re:.+>",
            _RATE_HIGH(self.__handle_set_config)
        )
        web_app.add_handler(
            "/server/config/sonarr/test-connection",
            _RATE_LOW(self.__handle_test_sonarr_connection)
        )
        web_app.add_handler(
            "/server/config/radarr/test-connection",
            _RATE_LOW(self.__handle_test_radarr_connection)
        )
```

**Alternative (module-level constants):** Rather than creating decorators inline in `add_routes()`, declare `_RATE_HIGH` and `_RATE_LOW` as module-level closures created once at import time. This is cleaner because each constant represents one shared budget for all handlers at that tier — but as specified in D-01, config/set and status are conceptually independent endpoints. The planner should evaluate whether to give each endpoint its own closure (most isolation) or share a closure per tier (shared budget). Given D-01 says "60 req/60s for `/server/config/set` and `/server/status`" as two separate endpoints, each should get its own closure.

### Pattern 3: ControllerHandler Refactor (D-05)

**What:** Replace the inline `_check_bulk_rate_limit()` call with a decorator-wrapped method.

**When to use:** At `add_routes()` time for the bulk endpoint only.

```python
# controller.py refactor sketch
# Remove: _BULK_RATE_LIMIT, _BULK_RATE_WINDOW, _bulk_request_times, _bulk_rate_lock, _check_bulk_rate_limit()
# Add in add_routes():
web_app.add_post_handler(
    "/server/command/bulk",
    rate_limit(max_requests=10, window_seconds=60.0)(self.__handle_bulk_command)
)
# Remove the rate limit check block from __handle_bulk_command body (lines 276-283)
```

**Test impact:** Existing rate limit tests in `test_controller_handler.py` (lines 610-702) currently access `ControllerHandler._BULK_RATE_LIMIT` and `ControllerHandler._BULK_RATE_WINDOW` as class constants. After refactoring, these constants no longer exist on the class. Tests must be updated to use the decorator's closure constants directly (import from `rate_limit.py`) or use numeric literals. [VERIFIED: test_controller_handler.py lines 615, 627, 652-653, 657, 688]

### Pattern 4: Semgrep Rule Fix — TOOL-01 (js-nosql-injection-where)

**What:** Convert the single `pattern:` rule to `patterns:` with an added `metavariable-regex` filter.

**Current rule (lines 267-280 of javascript.yaml):**
```yaml
  - id: js-nosql-injection-where
    pattern: |
      $COLLECTION.$WHERE($INPUT)
```

**Fixed rule:**
```yaml
  - id: js-nosql-injection-where
    patterns:
      - pattern: |
          $COLLECTION.$WHERE($INPUT)
      - metavariable-regex:
          metavariable: $WHERE
          regex: '^\$where$'
```

**Why it works:** The `metavariable-regex` filter requires that the code matched by `$WHERE` is literally the string `$where` (dollar sign + "where") — the MongoDB operator. All generic `.where()` method calls (Lodash, Knex, TypeORM, etc.) use `.where` without a dollar sign, so `$WHERE` captures `where` (no dollar), which does not match `^\$where$`. The regex `\$` escapes the dollar sign in the regex; the YAML single-quote wrapper prevents YAML from interpreting `$where` as a variable reference. [VERIFIED: metavariable-regex syntax from go.yaml in same repo; regex semantics — ASSUMED: Semgrep's exact metavariable capture behavior for method names, but this is the standard documented approach]

### Pattern 5: Semgrep Rule Fix — TOOL-02 (js-xss-eval-user-input)

**What:** Add `pattern-not` exclusions for callback-shaped arguments to `setTimeout`/`setInterval`.

**Current false positives (11 cases):** Code like:
```javascript
setTimeout(() => doSomething(), 1000)       // arrow function — safe
setInterval(function tick() { ... }, 500)   // named function — safe
```

**Fixed rule additions:**
```yaml
      - pattern-not: |
          setTimeout(($ARGS) => $BODY, ...)
      - pattern-not: |
          setTimeout(function $NAME($PARAMS) { $BODY }, ...)
      - pattern-not: |
          setInterval(($ARGS) => $BODY, ...)
      - pattern-not: |
          setInterval(function $NAME($PARAMS) { $BODY }, ...)
```

**Style match:** These follow the `pattern-not: eval("...")` style already in the rule (line 98-99). Each `pattern-not` is a sibling under `patterns:` alongside the existing `pattern-either` and `pattern-not`. [VERIFIED: existing rule structure at javascript.yaml lines 87-110]

**Note on zero-parameter arrow functions:** `() => $BODY` vs `($ARGS) => $BODY` — Semgrep treats these as distinct patterns. The planner should include both forms or verify via `semgrep --validate` / `semgrep scan` that the pattern covers them. [ASSUMED: Semgrep metavariable matching for zero-arg arrow functions; verify during implementation]

### Anti-Patterns to Avoid

- **Shared rate limit state across endpoints via a class variable:** If `_bulk_request_times` is a class variable (not instance), all handler instances share rate limit state. The existing code correctly uses instance variables initialized in `__init__`. The new decorator uses closure state, which is inherently per-decorator-call, avoiding this problem.
- **Rebinding `request_times` inside the lock:** `request_times = [t for t in ...]` rebinds the closure variable; `request_times[:] = [...]` mutates in place. Rebinding does not affect the list object the name originally referred to — the existing controller.py code uses reassignment inside a lock which is safe, but the cleaner pattern for closure variables is in-place mutation. Either works within the lock.
- **Missing `functools.wraps`:** Without it, Bottle cannot extract path variables from the wrapper's signature. Routes with path variables (`/server/config/set/<section>/<key>/<value:re:.+>`) will silently fail to pass arguments to the handler. [ASSUMED: Bottle's route variable injection relies on `inspect.signature` of the callable]
- **Creating the decorator once and reusing the same closure across multiple endpoints:** Each endpoint needs its own `rate_limit(...)` call to get its own `request_times` list and `Lock`. Creating `decorator = rate_limit(60, 60)` and applying it to both config/set and status would give them a shared budget.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe list mutation | Custom mutex class | `threading.Lock` (stdlib) | Already proven in codebase |
| HTTP 429 response | Custom response class | `bottle.HTTPResponse(status=429)` | Consistent with existing pattern |
| Semgrep pattern filtering | Custom regex pre-processor | `metavariable-regex` (Semgrep built-in) | Already used in other rules in the same repo |

**Key insight:** Both workstreams are refinements of code already in the repo. The rate limiter is an extraction of working logic; the Semgrep fixes are surgical YAML edits using syntax already present in the same config directory.

---

## Common Pitfalls

### Pitfall 1: Bottle Path Variable Injection Broken by Missing `functools.wraps`
**What goes wrong:** `/server/config/set/<section>/<key>/<value:re:.+>` stops receiving `section`, `key`, `value` as keyword arguments — handler gets called with no args, crashes with TypeError.
**Why it happens:** Bottle uses `inspect.signature` (or similar introspection) to map path variables to function parameters. A bare `wrapper(*args, **kwargs)` has no named parameters — Bottle cannot match.
**How to avoid:** Always apply `@functools.wraps(func)` to the inner wrapper function.
**Warning signs:** 500 errors on config/set routes immediately after applying decorator; TypeError in logs about unexpected arguments.

### Pitfall 2: Shared Rate Limit Budget Between Endpoints
**What goes wrong:** If the same decorator closure is applied to multiple endpoints, they share a rate limit counter. Hitting the limit on config/set also blocks status.
**Why it happens:** Decorator factory called once, result reused; closure state is the same object.
**How to avoid:** Call `rate_limit(max_requests, window_seconds)` separately for each endpoint, or create per-endpoint decorator instances.
**Warning signs:** Tests for one endpoint's rate limit bleed into tests for another.

### Pitfall 3: Existing Controller Rate Limit Tests Break After Refactor
**What goes wrong:** Tests reference `ControllerHandler._BULK_RATE_LIMIT` and `ControllerHandler._BULK_RATE_WINDOW` — attributes removed in the refactor.
**Why it happens:** Tests were written against the old class-constant design.
**How to avoid:** Update tests to use numeric literals or import the constants from `rate_limit.py`.
**Warning signs:** `AttributeError: type object 'ControllerHandler' has no attribute '_BULK_RATE_LIMIT'` in existing tests.

### Pitfall 4: Semgrep `metavariable-regex` regex escaping
**What goes wrong:** YAML interprets `$where` in the regex value as a YAML alias or variable.
**Why it happens:** YAML double-quoted strings interpret backslashes; unquoted `$` can be ambiguous.
**How to avoid:** Use single-quoted YAML string for the regex value: `regex: '^\$where$'`.
**Warning signs:** `semgrep --validate` reports YAML parse error or regex compile error.

### Pitfall 5: Arrow-Function Pattern Missing Zero-Arg Form
**What goes wrong:** `setTimeout(() => foo(), 1000)` still triggers the rule because `() => $BODY` doesn't match `($ARGS) => $BODY` if Semgrep requires at least one arg for `$ARGS`.
**Why it happens:** Semgrep metavariable ellipsis behavior for empty param lists may vary.
**How to avoid:** Test with `semgrep scan --config javascript.yaml` against a fixture file containing `() => expr`. Add `- pattern-not: setTimeout(() => $BODY, ...)` if needed.
**Warning signs:** `semgrep --test` still reports false positives on zero-arg arrow function fixtures.

---

## Code Examples

### New `rate_limit.py` Module
```python
# Source: generalized from controller.py:229-251 [VERIFIED: codebase read]
import json
import logging
import time
import functools
from threading import Lock
from typing import Callable, List

from bottle import HTTPResponse

logger = logging.getLogger(__name__)


def rate_limit(max_requests: int, window_seconds: float) -> Callable:
    """
    Sliding-window rate limiter decorator factory.

    Args:
        max_requests: Maximum allowed requests within the window.
        window_seconds: Window duration in seconds.

    Returns:
        A decorator that wraps a Bottle handler. Returns HTTP 429 when
        the limit is exceeded.
    """
    def decorator(func: Callable) -> Callable:
        request_times: List[float] = []
        lock = Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            with lock:
                request_times[:] = [t for t in request_times if now - t < window_seconds]
                if len(request_times) >= max_requests:
                    logger.warning("Rate limit exceeded for %s", func.__name__)
                    return HTTPResponse(
                        body=json.dumps({"error": "Rate limit exceeded. Please try again later."}),
                        status=429,
                        content_type="application/json"
                    )
                request_times.append(now)
            return func(*args, **kwargs)

        return wrapper
    return decorator
```

### ConfigHandler.add_routes() After Change
```python
# Source: config.py:19-25 [VERIFIED: codebase read] + D-01 thresholds
from web.rate_limit import rate_limit

class ConfigHandler(IHandler):
    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_handler("/server/config/get", self.__handle_get_config)
        web_app.add_handler(
            "/server/config/set/<section>/<key>/<value:re:.+>",
            rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_set_config)
        )
        web_app.add_handler(
            "/server/config/sonarr/test-connection",
            rate_limit(max_requests=5, window_seconds=60.0)(self.__handle_test_sonarr_connection)
        )
        web_app.add_handler(
            "/server/config/radarr/test-connection",
            rate_limit(max_requests=5, window_seconds=60.0)(self.__handle_test_radarr_connection)
        )
```

### StatusHandler.add_routes() After Change
```python
# Source: status.py:12-13 [VERIFIED: codebase read] + D-01 threshold
from web.rate_limit import rate_limit

class StatusHandler(IHandler):
    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_handler(
            "/server/status",
            rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_get_status)
        )
```

### TOOL-01 Fixed Rule (full rule block)
```yaml
  - id: js-nosql-injection-where
    patterns:
      - pattern: |
          $COLLECTION.$WHERE($INPUT)
      - metavariable-regex:
          metavariable: $WHERE
          regex: '^\$where$'
    message: >
      The $where operator evaluates JavaScript on the server. Never pass
      user-controlled data to $where. Use standard query operators instead.
    severity: ERROR
    languages: [javascript, typescript]
    metadata:
      cwe: "CWE-943"
      owasp: "A03:2021 Injection"
      confidence: HIGH
      impact: CRITICAL
      category: security
```

### TOOL-02 Added pattern-not entries (within the existing `patterns:` block)
```yaml
      - pattern-not: |
          setTimeout(($ARGS) => $BODY, ...)
      - pattern-not: |
          setTimeout(() => $BODY, ...)
      - pattern-not: |
          setTimeout(function $NAME($PARAMS) { $BODY }, ...)
      - pattern-not: |
          setInterval(($ARGS) => $BODY, ...)
      - pattern-not: |
          setInterval(() => $BODY, ...)
      - pattern-not: |
          setInterval(function $NAME($PARAMS) { $BODY }, ...)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rate limit logic inline in handler | Decorator factory in separate module | This phase | Eliminates duplication; consistent 429 response across all endpoints |
| `pattern:` rule (catches all `.where()`) | `patterns:` + `metavariable-regex` | This phase | Eliminates 617 false positives; preserves MongoDB-specific detection |
| No exclusion for function callbacks in eval rule | `pattern-not` for arrow/named functions | This phase | Eliminates 11 false positives; rule still fires on `setTimeout(userInput, ...)` |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Bottle uses `inspect.signature` (or equivalent) to extract path variables and requires `functools.wraps` on wrapped callables | Architecture Patterns — Pitfall 1 | Routes with path variables silently break; mitigate by testing config/set with section/key/value args after wrapping |
| A2 | Semgrep `metavariable-regex` matches the method name in `$COLLECTION.$WHERE($INPUT)` as the string the method resolves to (e.g., `where` not `$where`) | Architecture Patterns — Pattern 4 | Regex `^\$where$` might never match if Semgrep captures `where` (without `$`); implementation must validate with `semgrep scan` |
| A3 | Zero-arg arrow function `() => $BODY` is distinct from `($ARGS) => $BODY` in Semgrep metavariable matching | Common Pitfalls — Pitfall 5 | TOOL-02 still has FPs for `setTimeout(() => fn(), t)`; add the zero-arg form pattern-not |
| A4 | `semgrep --test` requires co-located fixture files with `# ruleid:` annotations; none exist for the javascript.yaml rules | Validation Architecture | Cannot run automated rule tests without creating fixtures; D-09 already acknowledges this condition |

---

## Open Questions (RESOLVED)

1. **Does Semgrep `$WHERE` capture `where` (the identifier) or `$where` (the string with dollar)?**
   - What we know: In MongoDB `db.collection.$where(fn)`, the method name as written in source is `$where`.
   - What's unclear: Whether Semgrep captures the dollar sign as part of the metavariable value or strips it.
   - Recommendation: The implementer should validate by running `semgrep scan --config javascript.yaml` against a one-line test file containing `db.users.$where(userInput)` and confirming it fires, then against `db.users.where(userInput)` and confirming it does not.
   - **RESOLVED:** Plan 02 includes inline TP/FP scan validation against temp test files during implementation. The regex `^\$where$` is the standard documented approach for metavariable filtering. Empirical validation during execution will confirm capture behavior.

2. **Bottle path variable injection with wrapped handlers**
   - What we know: `web_app.add_handler(path, handler)` calls `self.get(path)(handler)` which is Bottle's standard route decorator.
   - What's unclear: Whether Bottle's routing uses `inspect.signature` (which `functools.wraps` populates) or `inspect.getfullargspec` (which also works with `wraps`).
   - Recommendation: Include a quick smoke test in the plan that calls `__handle_set_config` via the wrapped interface with path variable kwargs to confirm they pass through.
   - **RESOLVED:** `functools.wraps` is the universal standard fix for preserving function metadata across decorators. Plan 01 includes `functools.wraps` in the implementation and Plan 03 test suite verifies path-variable passthrough for config/set routes with section/key/value kwargs.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| semgrep | TOOL-01, TOOL-02 validation | Yes | installed at `/Users/julianamacbook/Library/Python/3.9/bin/semgrep` | Run `semgrep --validate` only; skip `--test` if no fixture files |
| Docker | Python unit tests (Makefile target) | Yes | 29.4.1 | — |
| python3.12 | Decorator unit tests (manual) | Yes | via Homebrew | — |
| pytest | Unit tests | Yes (via Docker / project test infra) | ^9.0.3 | Docker-based test runner |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** No project-level venv detected at `/Users/julianamacbook/seedsyncarr/src/python/`. Python unit tests run via Docker (`make run-tests-python`). Local `python3.12` is available but lacks pytest — use Docker for test runs.

---

## Validation Architecture

**nyquist_validation:** Enabled (key absent from config.json).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `make run-tests-python` (Docker) |
| Full suite command | `make run-tests-python` |

**Local quick run (for individual files, requires Docker or compatible env):**
```
docker compose -f src/docker/test/python/compose.yml run tests pytest tests/unittests/test_web/ -q
```

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RATE-01 | Decorator returns 429 after exceeding limit; allows under limit; resets after window | unit | `pytest tests/unittests/test_web/test_rate_limit.py -x` | No — Wave 0 gap |
| RATE-01 | Decorator preserves wrapped function return value when under limit | unit | `pytest tests/unittests/test_web/test_rate_limit.py -x` | No — Wave 0 gap |
| RATE-01 | Thread safety: concurrent requests correctly bounded | unit | `pytest tests/unittests/test_web/test_rate_limit.py -x` | No — Wave 0 gap |
| RATE-02 | config/set returns 429 after 60 requests in 60s | unit | `pytest tests/unittests/test_web/test_handler/test_config_handler.py -k rate` | No — Wave 0 gap |
| RATE-03 | test-connection returns 429 after 5 requests in 60s | unit | `pytest tests/unittests/test_web/test_handler/test_config_handler.py -k rate` | No — Wave 0 gap |
| RATE-04 | status returns 429 after 60 requests in 60s | unit | `pytest tests/unittests/test_web/test_handler/test_status_handler.py -k rate` | No — Wave 0 gap |
| RATE-01 (D-05) | ControllerHandler bulk still rate-limits at 10/60s after refactor | unit | `pytest tests/unittests/test_web/test_handler/test_controller_handler.py -k rate` | Yes — existing tests need update |
| TOOL-01 | Semgrep rule does not fire on `db.users.where(input)` | manual / semgrep scan | `semgrep scan --config javascript.yaml test_nosql_fp.js` | No fixture |
| TOOL-01 | Semgrep rule still fires on `db.users.$where(input)` | manual / semgrep scan | `semgrep scan --config javascript.yaml test_nosql_tp.js` | No fixture |
| TOOL-02 | Semgrep rule does not fire on `setTimeout(() => fn(), 1000)` | manual / semgrep scan | `semgrep scan --config javascript.yaml test_eval_fp.js` | No fixture |
| TOOL-02 | Semgrep rule still fires on `setTimeout(userInput, 1000)` | manual / semgrep scan | `semgrep scan --config javascript.yaml test_eval_tp.js` | No fixture |

### Sampling Rate
- **Per task commit:** `pytest tests/unittests/test_web/ -q --tb=short` (via Docker)
- **Per wave merge:** Full `make run-tests-python`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/python/tests/unittests/test_web/test_rate_limit.py` — covers RATE-01 (decorator unit tests)
- [ ] `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` rate limit tests — covers RATE-02, RATE-03
- [ ] `src/python/tests/unittests/test_web/test_handler/test_status_handler.py` rate limit test — covers RATE-04
- [ ] Update `test_controller_handler.py` rate limit tests — remove references to `_BULK_RATE_LIMIT` / `_BULK_RATE_WINDOW` class constants (covers D-05 refactor)

No fixture files needed for Semgrep `--test` (D-09 says "if fixture files exist"). Manual validation with `semgrep scan` is sufficient.

---

## Security Domain

**security_enforcement:** Enabled (key absent from config.json).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | Yes (partial) | Rate limiting prevents brute-force/abuse of config endpoints |
| V5 Input Validation | No | Not introducing new inputs |
| V6 Cryptography | No | — |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Abuse of `/server/config/test/*` to trigger repeated outbound HTTP calls to arbitrary hosts | Denial-of-Service | 5 req/60s rate limit (RATE-03) |
| Rapid config changes via `/server/config/set` flooding | Tampering | 60 req/60s rate limit (RATE-02) |
| False positives hiding real Semgrep findings | Information Disclosure (tool blind spot) | Fix Semgrep rules (TOOL-01, TOOL-02) |
| `setTimeout(userInput, delay)` — dynamic code execution | Tampering/Elevation | `js-xss-eval-user-input` rule (preserved after TOOL-02 fix) |

**Note:** The rate limiter is in-process. A sufficiently motivated attacker with multiple source IPs can bypass it. For a homelab tool this is the appropriate scope — the CONTEXT.md decisions explicitly do not require IP-based or distributed rate limiting.

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase read] `src/python/web/handler/controller.py` lines 229-283 — sliding-window implementation and 429 response pattern
- [VERIFIED: codebase read] `src/python/web/handler/config.py` — full file; routes, handler methods, test connection logic
- [VERIFIED: codebase read] `src/python/web/handler/status.py` — full file
- [VERIFIED: codebase read] `src/python/web/web_app.py` lines 184-191 — `add_handler` / `add_post_handler` API
- [VERIFIED: codebase read] `shield-claude-skill/configs/semgrep-rules/javascript.yaml` lines 87-108, 267-280 — target rules
- [VERIFIED: codebase grep] `shield-claude-skill/configs/semgrep-rules/go.yaml` — `metavariable-regex` syntax reference
- [VERIFIED: codebase read] `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` lines 607-702 — existing rate limit tests
- [VERIFIED: codebase read] `src/python/pyproject.toml` — pytest config, test framework versions, no new deps needed

### Secondary (MEDIUM confidence)
- [VERIFIED: `command -v semgrep`] semgrep installed at `/Users/julianamacbook/Library/Python/3.9/bin/semgrep`
- [CITED: Python stdlib] `functools.wraps` preserves `__name__`, `__doc__`, `__wrapped__`, and `__signature__` on wrapper

### Tertiary (LOW confidence)
- [ASSUMED] Bottle's route variable injection mechanism requires `functools.wraps` for correct signature inspection — flagged as A1 in Assumptions Log

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in codebase or pyproject.toml
- Architecture: HIGH — pattern extracted directly from existing working code
- Pitfalls: HIGH (pitfalls 1, 3, 4) / MEDIUM (pitfalls 2, 5) — mostly verified from codebase, Bottle introspection behavior assumed
- Semgrep fixes: HIGH — syntax verified from sibling rule files in same repo

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable domain — no external dependencies change)
