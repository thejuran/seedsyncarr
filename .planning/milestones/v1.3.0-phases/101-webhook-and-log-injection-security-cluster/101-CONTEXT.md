# Phase 101: Webhook + Log-Injection Security Cluster - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden the webhook endpoint and the backend log surface. Four scoped changes, all additive and opt-in where behavior could change:

1. **BUG-02** — opt-in webhook fail-closed (new config flag, default off) that rejects unauthenticated webhook calls with 503 when no secret is configured.
2. **SEC-01** — sanitize every remote-/user-supplied string before it reaches a log line (CWE-117 log injection).
3. **SEC-03** — rate-limit the webhook routes with the existing v1.2.0 middleware.
4. **SEC-02** — normalize the config GET response so secret-set vs secret-unset is indistinguishable beyond the existing explicit boolean flag.

Scope anchor from ROADMAP.md (Phase 101) — fixed. Phases 102 (controller concurrency + test infra) and 103 (Angular defects) are out of scope here.

**Cross-cutting (locked by REQUIREMENTS.md):** no breaking change on upgrade — existing config files load unchanged, no new *required* fields, status codes/response shapes for already-supported paths unchanged; CI green amd64+arm64; Python `fail_under` ≥ 88 holds or rises; security fixes log no sensitive data and return generic client errors with detail logged server-side; **no release/tag/version work**.
</domain>

<decisions>
## Implementation Decisions

### SEC-01 — Log-injection sanitizer (CWE-117)
- **D-01:** Extract a single shared helper (e.g. `sanitize_log_value()`) that strips/escapes CR/LF/control characters. Replace the 3 existing inline `.replace("\n","\\n").replace("\r","\\r")` copies (`webhook_manager.py:37`, `webhook_manager.py:76`, `controller.py:790`) with calls to it — one definition, no copy-paste drift.
- **D-02:** Apply the helper to log sites whose interpolated value is **provably remote-/webhook-/user-supplied** (filenames/titles from *arr callbacks, scanned remote names) — NOT to internal-only strings. Targeted to the CWE-117 threat model, not a blanket wrap.
- **D-03:** The exact set of taint-reachable log sites is enumerated by the researcher/planner via data-flow analysis (which `name`/`file_name`/`title` interpolations trace back to a remote source). Audit surface includes controller.py, lftp/job_status_parser.py, lftp/lftp.py, controller/webhook_manager.py, and the delete/extract/dispatch log sites — researcher confirms which are taint-reachable.

### BUG-02 — Opt-in webhook fail-closed (highest priority; MUST NOT break back-compat)
- **D-04:** New config flag **`general.webhook_require_secret`**, type bool, **default `false`**. Lives in the existing General config section next to `webhook_secret`.
- **D-05:** Flag **on** + no secret configured → webhook endpoint rejects with **503 before the body is parsed**. Flag **off** (default) → existing behavior preserved exactly: no secret → HMAC skipped + loud startup warning (honors the locked `Empty webhook_secret skips HMAC` contract). Secret configured → valid-HMAC requests succeed unchanged.
- **D-06:** Old config files load with no new required field — wire the default via the existing `Config.from_dict` back-compat fallback pattern (`config.py:515-569`, the same shape used for webhook_secret/api_token/rate_limit). No new *required* field.
- **D-07:** The flag + required-secret expectation are surfaced to the operator — extend the existing empty-secret startup warning (`seedsyncarr.py:372-378`) and document the flag.

### SEC-03 — Webhook rate-limiting
- **D-08:** Reuse the existing `rate_limit(max_requests, window_seconds)` decorator (`src/python/web/rate_limit.py`) — the same middleware applied to bulk/config/status handlers. No new mechanism.
- **D-09:** Limit = **60 requests / 60 seconds, per route** (matches config/status endpoints). Applied independently to `/server/webhook/sonarr` and `/server/webhook/radarr` so the two don't share a budget. Over-limit → generic **429**.

### SEC-02 — Config GET response normalization
- **D-10:** Secret value fields (`webhook_secret`, `api_token`, and any other secret field surfaced in the GET response) always serialize as **`""`** in the config GET response — never the real value, never a length-revealing mask. Presence is carried only by the already-present explicit boolean (`*_is_set`).
- **D-11:** Result: the GET response shape is **identical whether a given secret is set or unset**, apart from the existing boolean flag — no length, key-presence, or value-shape difference. Researcher confirms the exact current `__handle_get_config` serialization (`config.py:87`) and applies the minimal normalization that satisfies this.

### Claude's Discretion
- Exact helper name/signature and module location for `sanitize_log_value()`.
- Whether BUG-02's 503 is raised in `_verify_hmac` vs at the top of `_handle_webhook` (must be before body parse either way).
- Test structure — but reuse slice-1 regression tests where they already pin current behavior (REQUIREMENTS.md notes several slice-1 tests cover these paths).
</decisions>

<specifics>
## Specific Ideas

- The `Empty webhook_secret skips HMAC` backward-compat decision is a **hard constraint** — BUG-02's default-off flag exists specifically to preserve it. Any path where an existing install's webhook behavior changes on upgrade is a defect, not a feature.
- CONCERNS.md line 99 suggests auto-requiring the secret when `sonarr.enabled`/`radarr.enabled` — explicitly **rejected** here because it would change behavior for existing *arr-enabled installs (COMPAT violation). The opt-in flag is the chosen path instead.
- Land fixes test-first where a slice-1 regression test already pins the current behavior of the touched path.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & concerns (source of truth)
- `.planning/REQUIREMENTS.md` — BUG-02, SEC-01, SEC-02, SEC-03 full statements + Cross-Cutting Constraints (COMPAT, CI green, coverage floors, safe observability, no-release). MUST read.
- `.planning/codebase/CONCERNS.md` §"Security Considerations" — original audit detail: webhook trust-of-json-parse (lines 95-99), file-rename/log-injection partial mitigation + audit recommendation (lines 101-105), `from_dict` back-compat branches (line 38).
- `.planning/ROADMAP.md` §"Phase 101" (lines 426-439) — phase goal + 5 success criteria + COMPAT cross-cutting criterion.

### Code surfaces (read before implementing)
- `src/python/web/handler/webhook.py` §`_verify_hmac` (lines 43-77) + `_handle_webhook` (lines 79+) + `add_routes` (lines 30-34) — BUG-02 fail-closed hook point and SEC-03 route registration.
- `src/python/web/rate_limit.py` — the `rate_limit` decorator to reuse for SEC-03; see usage in `web/handler/{controller,status,config}.py`.
- `src/python/web/handler/config.py` §`__handle_get_config` (line 87) + `__handle_set_config` — SEC-02 GET response serialization surface.
- `src/python/common/config.py` §`from_dict` back-compat branches (lines 515-569) — BUG-02 flag default wiring (D-06); `_SECRET_FIELD_PATHS` (lines 19-25) — secret-field inventory for SEC-02.
- `src/python/controller/webhook_manager.py:37,76` + `src/python/controller/controller.py:790` — the 3 inline CWE-117 replacements to consolidate (SEC-01 D-01).
- `seedsyncarr.py:372-378` — existing empty-secret startup warning to extend (BUG-02 D-07).

### Backward-compat anchor
- The `Empty webhook_secret skips HMAC` decision is recorded in PROJECT.md Key Decisions — BUG-02 must not break it.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `rate_limit(max_requests, window_seconds)` decorator (`web/rate_limit.py`) — drop-in for SEC-03; already wraps bulk (10/60), config/status (60/60), test-connection (5/60) handlers.
- Inline CWE-117 escape pattern `.replace("\n","\\n").replace("\r","\\r")` already proven in `webhook_manager.py` — promote to the shared `sanitize_log_value()` helper (SEC-01 D-01).
- `Config.from_dict` back-compat fallback pattern (`config.py:515-569`) — established mechanism for adding an optional config field that loads unchanged on old files (BUG-02 D-06).
- Existing `*_is_set` boolean convention in the config GET response — SEC-02 keeps it and zeroes the value field around it.

### Established Patterns
- Webhook auth flow: `_handle_webhook` → body-size cap (413) → `_verify_hmac` (401) → JSON parse (400). BUG-02's 503 must slot in **before** body parse.
- Per-route POST handler registration via `web_app.add_post_handler(path, fn)` — decorate the bound method exactly like other handlers do (`status.py:16`, `config.py:28`).
- Generic client error + server-side detail logging is the house style for security responses (honors safe-observability constraint).

### Integration Points
- BUG-02 flag flows: `config.py` (declare + from_dict default) → `webhook.py` (read `self.__config.general.webhook_require_secret`) → `seedsyncarr.py` startup warning.
- SEC-02 touches only the GET serialization in `config.py` — set path and on-disk format unchanged (COMPAT).
- SEC-01 helper is shared infra — pick a module importable by controller, lftp, and webhook_manager without a circular import.
</code_context>

<deferred>
## Deferred Ideas

- DNS-rebind hardening for `_validate_url` — out of scope (accepted homelab risk per REQUIREMENTS.md Out-of-Scope table).
- Making `webhook_secret` *mandatory* (vs opt-in flag) — rejected as a COMPAT break; the opt-in flag is the in-scope alternative.
- Settings audit log (who/when/what changed config) — CONCERNS bucket 9 missing-feature, not in this slice.
- `set_property` non-string coercion, ServiceExit broad-except, bulk-command queue-after-timeout — other known bugs deferred per REQUIREMENTS.md Out-of-Scope.

### Reviewed Todos (not folded)
- 2 pending todos exist (webob-cgi-upstream-unblock, migrate-config-set-to-post-body) — neither matched phase 101 (todo.match-phase returned 0 matches). The config-set-to-POST-body item is a separate-milestone API contract change per STATE.md deferred items.

</deferred>

---

*Phase: 101-webhook-and-log-injection-security-cluster*
*Context gathered: 2026-05-31*
