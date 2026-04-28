# Phase 96: Rate Limiting & Tooling - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add rate limiting to three mutable/pollable HTTP endpoints (`/server/config/set`, `/server/config/test/*`, `/server/status`) via a reusable decorator, and tighten two Semgrep rules in Shield to eliminate 628 false positives.

</domain>

<decisions>
## Implementation Decisions

### Rate Limit Thresholds
- **D-01:** Use a **two-tier threshold** model: **60 req/60s** for `/server/config/set` and `/server/status`, **5 req/60s** for `/server/config/test/*` (test-connection endpoints). Two constants only.
- **D-02:** The higher tier (60/60s) accommodates per-field config saves (settings form fires rapid sequential calls) and frontend status polling without false 429s. The lower tier (5/60s) tightly constrains test-connection endpoints that make expensive outbound HTTP calls to Sonarr/Radarr.
- **D-03:** The existing bulk endpoint rate limit (10 req/60s in `ControllerHandler`) should be refactored to use the new decorator but keep its current threshold unchanged.

### Decorator Design
- **D-04:** Create a **standalone decorator function** in a new `src/python/web/rate_limit.py` module. Sliding-window algorithm (matching the existing pattern in `controller.py:229-251`). State per-instance via closure.
- **D-05:** Refactor `ControllerHandler._check_bulk_rate_limit()` to use the new decorator, eliminating the duplicated sliding-window logic.
- **D-06:** The decorator should accept `max_requests` and `window_seconds` parameters. It returns HTTP 429 with JSON body `{"error": "Rate limit exceeded. Please try again later."}` and `content_type: application/json`.

### Semgrep Rule Fixes
- **D-07:** **TOOL-01** (`js-nosql-injection-where`, 617 FPs): Add a `metavariable-regex` constraint on `$WHERE` to match only the literal `$where` method name (`^\$where$`). ~3 lines added, eliminates all false positives while preserving the rule for future MongoDB scanning.
- **D-08:** **TOOL-02** (`js-xss-eval-user-input`, 11 FPs): Add `pattern-not` exclusions for arrow-function and named-function callbacks in `setTimeout`/`setInterval` patterns. Matches the existing `pattern-not: eval("...")` style already in the rule.
- **D-09:** Both changes confined to `shield-claude-skill/configs/semgrep-rules/javascript.yaml`. Validate with `semgrep --test` if fixture files exist.

### Folded Todos
- **rate-limiting-all-endpoints** (2026-04-14): Add rate limiting to all HTTP endpoints. Problem: only bulk endpoint had rate limiting; config/set, test-connection, and status had none. Directly maps to RATE-01 through RATE-04.
- **tighten-shield-semgrep-rules** (2026-04-23): Tighten Shield Semgrep rules to reduce false positives. Problem: 628 false positives drowning real findings. Directly maps to TOOL-01, TOOL-02.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rate Limiting
- `src/python/web/handler/controller.py` lines 229-283 -- Existing sliding-window rate limiter and HTTP 429 response pattern to extract and reuse
- `src/python/web/handler/config.py` lines 19-25 -- Routes for config/set and test-connection endpoints that need rate limiting
- `src/python/web/handler/status.py` lines 12-13 -- Route for /server/status endpoint that needs rate limiting
- `src/python/web/web_app.py` lines 184-191 -- `add_handler`/`add_post_handler` API that routes are registered through

### Semgrep Rules
- `shield-claude-skill/configs/semgrep-rules/javascript.yaml` lines 87-108 -- `js-xss-eval-user-input` rule (TOOL-02 target)
- `shield-claude-skill/configs/semgrep-rules/javascript.yaml` lines 267-280 -- `js-nosql-injection-where` rule (TOOL-01 target)

### Requirements
- `.planning/REQUIREMENTS.md` -- RATE-01 through RATE-04, TOOL-01, TOOL-02 requirement definitions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ControllerHandler._check_bulk_rate_limit()` (controller.py:229-251): Proven sliding-window implementation with thread-safe lock. Extract this into the new decorator module.
- `ControllerHandler.__handle_bulk_command()` 429 response pattern (controller.py:277-283): JSON error body with `application/json` content type. Reuse as the decorator's response format.

### Established Patterns
- Route registration via `web_app.add_handler(path, handler_method)` -- the decorator wraps the handler method before (or at) registration
- Thread safety via `threading.Lock()` -- paste httpserver is multithreaded, all shared state needs locks
- Handler classes implement `IHandler` with `add_routes()` -- decorator applied at the handler level, not as Bottle middleware

### Integration Points
- `ConfigHandler.add_routes()` -- wrap `__handle_set_config` and both `__handle_test_*_connection` methods
- `StatusHandler.add_routes()` -- wrap `__handle_get_status`
- `ControllerHandler._check_bulk_rate_limit()` -- refactor to use new decorator, remove duplicated logic

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches within the decisions captured above.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
- **e2e-csp-violation-detection** (2026-02-24) -- Already addressed by PLAT-01 in Phase 91 (complete)
- **arm64-unicode-sort-e2e-failures** (2026-04-24) -- Already addressed by PLAT-02 in Phase 91 (complete)
- **webob-cgi-upstream-unblock** -- Blocked on upstream webob 2.0, out of scope
- **migrate-config-set-to-post-body** -- Backend API contract change, explicitly out of scope for this milestone

</deferred>

---

*Phase: 96-Rate Limiting & Tooling*
*Context gathered: 2026-04-28*
