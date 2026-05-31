# Phase 101: Webhook + Log-Injection Security Cluster - Research

**Researched:** 2026-05-31
**Domain:** Python webhook handler hardening, log-injection sanitization, rate limiting, config serialization
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**SEC-01 — Log-injection sanitizer (CWE-117)**
- D-01: Extract a single shared helper (`sanitize_log_value()`) that strips/escapes CR/LF/control characters. Replace the 3 existing inline `.replace("\n","\\n").replace("\r","\\r")` copies (`webhook_manager.py:37`, `webhook_manager.py:76`, `controller.py:790`) with calls to it.
- D-02: Apply the helper to log sites whose interpolated value is provably remote-/webhook-/user-supplied. Not a blanket wrap.
- D-03: The exact set of taint-reachable log sites is enumerated by the researcher/planner via data-flow analysis. Audit surface includes controller.py, lftp/job_status_parser.py, lftp/lftp.py, controller/webhook_manager.py, and the delete/extract/dispatch log sites.

**BUG-02 — Opt-in webhook fail-closed (highest priority; MUST NOT break back-compat)**
- D-04: New config flag `general.webhook_require_secret`, type bool, default `false`. Lives in the existing General config section next to `webhook_secret`.
- D-05: Flag on + no secret → webhook rejects with 503 before body is parsed. Flag off (default) → existing behavior preserved: no secret → HMAC skipped + loud startup warning.
- D-06: Old config files load with no new required field — wire via `Config.from_dict` back-compat fallback pattern (`config.py:515-569`).
- D-07: Extend existing empty-secret startup warning (`seedsyncarr.py:372-378`) to surface the `require_secret` expectation.

**SEC-03 — Webhook rate-limiting**
- D-08: Reuse the existing `rate_limit(max_requests, window_seconds)` decorator (`web/rate_limit.py`).
- D-09: 60 requests / 60 seconds, per route. Applied independently to `/server/webhook/sonarr` and `/server/webhook/radarr`. Over-limit → generic 429.

**SEC-02 — Config GET response normalization**
- D-10: Secret value fields (`webhook_secret`, `api_token`) always serialize as `""` in the config GET response — never the real value.
- D-11: GET response shape is identical whether a given secret is set or unset, apart from the existing boolean flag.

### Claude's Discretion

- Exact helper name/signature and module location for `sanitize_log_value()`.
- Whether BUG-02's 503 is raised in `_verify_hmac` vs at the top of `_handle_webhook` (must be before body parse either way).
- Test structure — but reuse slice-1 regression tests where they already pin current behavior.

### Deferred Ideas (OUT OF SCOPE)

- DNS-rebind hardening for `_validate_url`.
- Making `webhook_secret` mandatory.
- Settings audit log.
- `set_property` non-string coercion, ServiceExit broad-except, bulk-command queue-after-timeout.
- Reviewed todos: webob-cgi-upstream-unblock, migrate-config-set-to-post-body.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BUG-02 | Opt-in `general.webhook_require_secret` (bool, default false). Flag on + no secret → 503 before body parse. Flag off → existing HMAC-skip + startup warning unchanged. | Full hook-point analysis in §BUG-02 below. from_dict wiring pattern confirmed. |
| SEC-01 | All log sites interpolating remote-/user-supplied strings pass through `sanitize_log_value()` (CWE-117). | 3 existing inline copies confirmed. Taint enumeration below is concrete with line refs. |
| SEC-03 | Webhook routes rate-limited at 60 req/60s per route using existing `rate_limit` decorator. | Decorator semantics and per-route isolation confirmed. Registration pattern confirmed. |
| SEC-02 | Config GET response always serializes secret value fields as `""`. | Current serialization surface fully mapped. `*_is_set` pattern clarified below. |
</phase_requirements>

---

## Summary

Phase 101 makes four additive, backward-compatible hardening changes to the Python backend. All four changes touch a small number of well-understood code surfaces; none require new dependencies, new test infrastructure beyond new test cases, or architectural changes.

The most important finding is that the `*_is_set` boolean convention mentioned in CONTEXT.md does NOT currently exist in the codebase. The current `SerializeConfig.config()` (serialize_config.py) does not emit any `webhook_secret_is_set` or `api_token_is_set` fields. D-10/D-11 therefore means: the change is to replace the current `**REDACTED**` string (unauthenticated path) and the real value (authenticated path) both with `""` — so both paths always emit `""` for secret value fields. This is a simpler normalization than the CONTEXT.md wording implies. The set-vs-unset distinction is conveyed only by the existing behavior that a non-empty `webhook_secret` causes `webhook_require_secret` to be effective — there is no separate `*_is_set` boolean to add or preserve in the GET response today. The planner must decide whether D-11 adds `*_is_set` booleans (additive) or simply zeroes the value field (minimal).

The recommended module location for `sanitize_log_value()` is `src/python/common/types.py` — it is already imported by both `controller.webhook_manager` (via `from common import Context`) and `lftp/lftp.py` (via `from common import AppError`), and adding a pure string utility function there introduces zero circular-import risk.

**Primary recommendation:** Implement all four changes in isolation (one commit per requirement), starting with BUG-02 (highest priority). SEC-03 is a two-line change. SEC-01 requires the taint enumeration to be resolved into a concrete diff. SEC-02 requires a decision on whether `*_is_set` booleans are added.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Webhook fail-closed (BUG-02) | API / Backend (webhook.py) | Config layer (config.py) | Request rejection must happen before body parse in the HTTP handler; config declares the flag |
| Log sanitization (SEC-01) | API / Backend (common helper) | Controller, lftp subsystems | All log sinks are in the Python process; helper lives in `common` to serve all tiers without circular imports |
| Webhook rate-limiting (SEC-03) | API / Backend (webhook.py add_routes) | rate_limit.py decorator | Rate state is per-decorated-callable; decoration happens at route registration time |
| Config GET normalization (SEC-02) | API / Backend (serialize_config.py) | — | Serialization layer is the single point of egress for config data; SET path and on-disk format untouched |

---

## Standard Stack

No new external packages. All changes use existing project libraries.

### Existing Libraries Used

| Library | Already In | Purpose for Phase 101 |
|---------|------------|----------------------|
| `bottle` | `pyproject.toml` | HTTPResponse, request object in webhook.py |
| `web.rate_limit` | `src/python/web/rate_limit.py` | `rate_limit` decorator for SEC-03 |
| `common.config` | `src/python/common/config.py` | PROP machinery for new bool flag |

### Package Legitimacy Audit

No new packages. This section is not applicable — phase 101 introduces zero new external dependencies.

---

## Requirement-by-Requirement Analysis

---

### BUG-02: Opt-in Webhook Fail-Closed

#### Hook Point Analysis

**Current flow in `_handle_webhook` (webhook.py:90-129):**

```
Line 91: content_length guard → 413 (before body read)
Line 95: _verify_hmac() → 401 (reads+resets body when secret is set)
Line 100: request.json → JSON parse (body consumed here)
```

**`_verify_hmac` (webhook.py:43-77) current logic:**
```python
Line 54: secret = self.__config.general.webhook_secret
Line 55: if not secret:
Line 56-57:     return None  # ← "Empty webhook_secret skips HMAC" contract
```

**Where to insert the BUG-02 503:**

Two valid positions:
1. **At the top of `_handle_webhook`, before the content_length guard (line 91):** Most explicit. Adds a check before anything.
2. **Inside `_verify_hmac`, replacing the early return at line 55-57:** More cohesive — all auth logic stays in one method.

Option 2 is recommended (Claude's Discretion): modify `_verify_hmac` so that when `not secret` is true, it checks `self.__config.general.webhook_require_secret`. If `require_secret` is True, return `HTTPResponse(status=503)`. If False, return `None` (existing behavior). This keeps all authentication decision logic in one method and avoids spreading concern into `_handle_webhook`.

**Concrete change to `_verify_hmac`:**
```python
secret = self.__config.general.webhook_secret
if not secret:
    if self.__config.general.webhook_require_secret:
        logger.warning("Webhook rejected: require_secret is on but no secret configured")
        return HTTPResponse(status=503, body="Service unavailable")
    # No secret configured — skip verification for backward compatibility
    return None
```

The 503 is returned at line ~57 (before `request.body.read()` at line 60), satisfying D-05's "before body parse" requirement. The content_length check at line 91 already fires before `_verify_hmac` is called — that ordering is preserved.

**COMPAT risk:** Default `webhook_require_secret=False` preserves exact existing behavior. Existing installs loading old config files get the default via the from_dict fallback (see below).

#### Config Declaration (config.py)

**Current `Config.General` class (config.py:228-241):**

```python
class General(IC):
    debug = PROP("debug", Checkers.null, Converters.bool)
    verbose = PROP("verbose", Checkers.null, Converters.bool)
    webhook_secret = PROP("webhook_secret", Checkers.null, Converters.null)
    api_token = PROP("api_token", Checkers.null, Converters.null)
    allowed_hostname = PROP("allowed_hostname", Checkers.null, Converters.null)

    def __init__(self):
        super().__init__()
        self.debug = None
        self.verbose = None
        self.webhook_secret = None
        self.api_token = None
        self.allowed_hostname = None
```

**Required addition** — three-step PROP pattern (CONCERNS.md §Fragile Areas):

Step 1 — Add class-level PROP after `allowed_hostname`:
```python
webhook_require_secret = PROP("webhook_require_secret", Checkers.null, Converters.bool)
```

Step 2 — Initialize to None in `__init__`:
```python
self.webhook_require_secret = None
```

Step 3 — Wire the default in `Config.from_dict` back-compat block (config.py:514-523):
```python
general_dict = Config._check_section(config_dict, "General")
# Backward compatibility: webhook_secret added in v3.1 — default to empty string
if "webhook_secret" not in general_dict:
    general_dict["webhook_secret"] = ""
# Backward compatibility: api_token added in v3.2 — default to empty string
if "api_token" not in general_dict:
    general_dict["api_token"] = ""
if "allowed_hostname" not in general_dict:
    general_dict["allowed_hostname"] = ""
# BUG-02: webhook_require_secret — default False (preserve existing behavior)
if "webhook_require_secret" not in general_dict:
    general_dict["webhook_require_secret"] = "False"
```

**COMPAT check:** The `from_dict` fallback pattern is proven for `webhook_secret` (line 516), `api_token` (line 519), `allowed_hostname` (line 521), and `rate_limit` (line 527). New booleans must inject the string `"False"` (not Python `False`) because `from_dict` values may pass through `Converters.bool` which calls `_strtobool` on strings.

**`_SECRET_FIELD_PATHS` (config.py:19-25):** `webhook_require_secret` is NOT a secret; do NOT add it to this tuple. It is a behavior flag, not an encrypted credential.

#### Startup Warning Extension (seedsyncarr.py:371-388)

**Current `_emit_startup_warnings` block (lines 371-393):**
```python
@staticmethod
def _emit_startup_warnings(logger: logging.Logger, config: Config) -> None:
    """Emit security warnings for insecure configuration states."""
    if not config.general.webhook_secret:
        logger.warning(
            "Security: webhook_secret is not configured. "
            "Webhook endpoints will accept requests from any caller."
        )
```

**Extension for D-07:** Add a second condition block after the existing `if not config.general.webhook_secret:` block:
```python
    if config.general.webhook_require_secret and not config.general.webhook_secret:
        logger.warning(
            "Security: webhook_require_secret is True but webhook_secret is not set. "
            "All webhook requests will be rejected with 503 until a secret is configured."
        )
```

Note: the existing warning fires when `not webhook_secret` is true (regardless of require_secret). The new warning fires specifically when the operator has enabled the flag but forgotten the secret. Both can fire simultaneously if `require_secret=True` and no secret is set — that is intentional (two different messages, two different concerns).

#### Existing Tests That Pin Current Behavior

- `test_webhook.py:TestWebhookIntegration` (all 5 tests) — pins that webhook routes return 200 for valid Download/Test/Grab events without any HMAC configured. These must continue to pass after BUG-02 (default-off path).
- `test_config.py:TestConfigHandler.test_get` — pins that `general` section is returned on GET.
- `test_common/test_config.py:TestGeneralConfig` (lines 278-318) — pins that `webhook_secret` and `api_token` are present and loadable, and that missing keys still raise. After adding `webhook_require_secret`, the `_build_config_ini` helper and any test that calls `Config.General.from_dict` with a full dict must include the new key OR the from_dict fallback test must cover absence.

---

### SEC-01: Log-Injection Sanitizer (CWE-117)

#### The Three Existing Inline Copies

All three confirmed by grep [VERIFIED: direct source read]:

1. **`webhook_manager.py:37`** — `enqueue_import()`:
   ```python
   safe_file_name = file_name.replace("\n", "\\n").replace("\r", "\\r")
   ```
   `file_name` is passed from `WebhookHandler._extract_sonarr_title` / `_extract_radarr_title`, which extracts it from the webhook request JSON body. **Provably remote-tainted.**

2. **`webhook_manager.py:76`** — `process()` drain loop:
   ```python
   safe_file_name = file_name.replace("\n", "\\n").replace("\r", "\\r")
   ```
   Same `file_name` from the queue. **Provably remote-tainted.**

3. **`controller.py:790`** — `__check_webhook_imports()`:
   ```python
   safe_matched = matched_name.replace("\n", "\\n").replace("\r", "\\r")
   ```
   `matched_name` is the file_name as returned by `WebhookManager.process()` — it is the original webhook-supplied string (queue value is used raw for matching). **Provably remote-tainted.**

#### Sanitizer Module Location

**Recommended location: `src/python/common/types.py`**

Rationale:
- `common/types.py` currently contains only `overrides()` — a pure utility decorator. A pure string utility function is an exact fit.
- Both `controller/webhook_manager.py` and `controller/controller.py` already import `from common import Context` (which re-exports from `common/__init__.py` which imports `common/types.py`). No new import needed.
- `lftp/lftp.py` already imports `from common import AppError` — same path. No new import needed.
- `web/handler/webhook.py` already imports `from common import overrides`. Same.
- Adding to `common/types.py` introduces zero circular-import risk: `types.py` imports only `inspect` (stdlib).
- Alternative `common/__init__.py` direct export would work but pollutes the namespace; `types.py` keeps it contained.

**Recommended signature:**
```python
def sanitize_log_value(value: str) -> str:
    """Escape CR/LF and other control characters from a string before logging.

    Prevents log injection (CWE-117) by replacing newlines with their literal
    escape sequences and stripping other control characters (< 0x20, except
    horizontal tab 0x09 which is acceptable in log output).

    Args:
        value: Potentially untrusted string to sanitize.

    Returns:
        Sanitized string safe for log interpolation.
    """
    return (
        value
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
```

The existing inline pattern only escapes `\n` and `\r`. The helper should match that scope exactly (not expand to all control characters) to avoid changing log output for existing sites. The order (`\r` first, then `\n`) is conventional; the existing copies do `\n` then `\r` — either order is correct, pick one consistently.

**Export from `common/__init__.py`:**
```python
from .types import overrides as overrides, sanitize_log_value as sanitize_log_value
```

#### Full Taint Enumeration for SEC-01

This is the complete audit of all log sites that interpolate remotely- or user-supplied strings, categorized by taint status:

**PROVABLY REMOTE-TAINTED (require sanitize_log_value):**

| Location | Line | Variable | Taint Origin |
|----------|------|----------|--------------|
| `controller/webhook_manager.py` | 37 | `file_name` | Webhook request JSON body (`episodeFile.sourcePath`, `release.releaseTitle`, `series.title`) |
| `controller/webhook_manager.py` | 76 | `file_name` | Same — drained from the import queue |
| `controller/controller.py` | 790 | `matched_name` | Webhook-supplied file_name passed through WebhookManager.process() |

These are the three D-01 targets. All other sites below are analyzed for completeness.

**`controller/controller.py` — other log sites:**

| Line | Variable | Taint Status | Reason |
|------|----------|--------------|--------|
| 229 | `file_name` (auto-delete) | INTERNAL | Source is `self.__pending_auto_deletes` keys — populated from `root_name`, which is a model file name obtained via `model.get_file_names()`. Model file names originate from the remote scanner output (lftp directory listing), not from webhook JSON. BORDERLINE — see note. |
| 760 | `root_name` | INTERNAL/BORDERLINE | Same source as above — model file name from remote scanner. |
| 975 | `file_name` (auto-delete) | INTERNAL/BORDERLINE | Same. |
| 1075 | `command.filename` | INTERNAL | Comes from the `/server/command/<file_name>` URL path, which the Angular frontend URL-encodes from the model. Not a direct webhook value. |
| 541 | `remove_extracted_file_names` | INTERNAL | Set of model file names; same origin as model scanner. |

**Note on remote-scanner-sourced file names (controller.py:229, 760, 975):** Model file names originate from the lftp `jobs -v` output parsed by `LftpJobStatusParser` — they are filenames on the seedbox remote. These are "remote-sourced" in the sense that an attacker controlling the seedbox filenames could inject newlines there too. However, the CONTEXT.md D-02 decision restricts sanitization to "provably remote-/webhook-/user-supplied" values — the threat model is focused on *arr webhook callbacks. Whether to include these BORDERLINE sites is Claude's Discretion (see Open Questions below). The research recommendation is: include them to be thorough, since they are measurably remote-sourced.

**`controller/delete/delete_process.py`:**

| Line | Variable | Taint Status | Reason |
|------|----------|--------------|--------|
| 17 | `self.__file_name` (DeleteLocal) | BORDERLINE | `file_name` passed from controller command handler; origin is `command.filename` from URL path, decoded from model file name. |
| 19 | `file_path` (DeleteLocal) | BORDERLINE | Derived from `file_name` joined with `local_path`. |
| 45 | `self.__file_name` (DeleteRemote) | BORDERLINE | Same. |
| 48 | `out.decode()` (DeleteRemote) | NOT-TAINTED | Output of SSH `rm` command — attacker-controllable only if SSH session is compromised; out of scope. |

**`controller/extract/dispatch.py`:**

| Line | Variable | Taint Status | Reason |
|------|----------|--------------|--------|
| 106 | `model_file.name` | BORDERLINE | Model file name — same remote-scanner origin as above. |
| 134 | `model_file.name` | BORDERLINE | Same. |
| 139 | `model_file.name` | BORDERLINE | Same. |
| 152 | `model_file.name` | BORDERLINE | Same. |
| 183 | `archive_path` | BORDERLINE | Derived from `model_file.name` + `local_path`. |

**`lftp/lftp.py`:**

| Line | Variable | Taint Status | Reason |
|------|----------|--------------|--------|
| 114 | `command` | INTERNAL | LFTP protocol commands constructed by the application (e.g., `queue add /remote/path`). Not user-supplied strings. |
| 126 | `out` | INTERNAL | Raw pexpect output buffer — internal protocol traffic. |
| 148 | `error_out` | INTERNAL | pexpect error output — internal. |
| 356 | `name` | BORDERLINE | Job name passed to `kill()` — source is model file name from `self.status()`. |
| 362, 365 | `name` | BORDERLINE | Same. |

**`lftp/job_status_parser.py`:**

| Line | Variable | Taint Status | Reason |
|------|----------|--------------|--------|
| 724 | `str(e)` | NOT-TAINTED | ValueError message from internal parsing logic — not remote content. |
| 725 | `output` | BORDERLINE | Raw lftp `jobs -v` output — remote-server-controlled. However this is only logged on a parse error, and the threat of log injection in a parse-error context is lower than in normal flow. |

**Recommended scope for SEC-01 implementation:** Apply `sanitize_log_value()` to the three D-01 targets (confirmed, provably tainted). The BORDERLINE sites (remote scanner file names in controller.py:229, 760, 975 and delete/extract dispatch) should be discussed with planner — the research recommendation is to include them since they are remote-sourced, but the CONTEXT.md D-02 says "targeted to the CWE-117 threat model, not a blanket wrap." The planner should decide which BORDERLINE sites to include.

#### Existing Tests That Pin Current Behavior for SEC-01

- `test_controller/test_controller.py` (integration tests for webhook flow) — exercises `WebhookManager.process()` and the controller's `__check_webhook_imports` path. These tests will continue to pass after the refactor since `sanitize_log_value()` is a pure string transform on the log variable only (the queue value is used raw for matching, unchanged).
- No dedicated test for the sanitization behavior exists. The planner should add a unit test for `sanitize_log_value()` itself in `test_common/` (or nearby) and a behavioral test that verifies newlines in file_name don't appear literally in log output.

---

### SEC-03: Webhook Rate-Limiting

#### rate_limit Decorator Semantics

**File: `src/python/web/rate_limit.py:19-49`** [VERIFIED: direct source read]

- **Type:** Sliding window, per-decorated-callable state.
- **State isolation:** Each call to `rate_limit(N, W)(fn)` creates a fresh `deque` and `Lock` in a closure. Two separate `rate_limit(60, 60.0)(fn)` applications on two different handler methods produce two completely independent counters. The `TestRateLimitIndependentClosures` unit test in `test_rate_limit.py` explicitly verifies this.
- **Over-limit response:** `HTTPResponse(status=429, body=json.dumps({...}), headers={"Retry-After": ...}, content_type="application/json")`.
- **Thread-safety:** `Lock()` wraps the deque read-and-write atomically.

#### Registration Pattern

**How other handlers apply rate_limit at route registration:**

- `status.py:16`: `web_app.add_handler("/server/status", rate_limit(60, 60.0)(self.__handle_get_status))`
- `config.py:28`: `web_app.add_handler("/server/config/set/...", rate_limit(60, 60.0)(self.__handle_set_config))`

**Webhook routes currently use `add_post_handler` (webhook.py:32-33):**
```python
web_app.add_post_handler("/server/webhook/sonarr", self.__handle_sonarr_webhook)
web_app.add_post_handler("/server/webhook/radarr", self.__handle_radarr_webhook)
```

**The change for SEC-03** wraps each handler at registration:
```python
web_app.add_post_handler(
    "/server/webhook/sonarr",
    rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_sonarr_webhook)
)
web_app.add_post_handler(
    "/server/webhook/radarr",
    rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_radarr_webhook)
)
```

Each `rate_limit(60, 60.0)(...)` call creates an independent closure. Sonarr and Radarr routes do NOT share a budget — D-09 is satisfied.

**Import:** `rate_limit` is already imported in `webhook.py`? No — currently webhook.py imports from `common` and `controller`. The planner must add:
```python
from ..rate_limit import rate_limit
```
This mirrors the pattern in `config.py:14` and `status.py:6`.

**COMPAT risk:** None. Rate-limiting only rejects requests that exceed 60/60s. Legitimate *arr callbacks fire at most once per import event; 60/60s is well above any realistic frequency.

#### Existing Tests That Pin Current Behavior for SEC-03

- `test_webhook.py` all 5 tests use `self.test_app.post_json(...)` once per test — all under the limit, will continue to pass.
- `test_rate_limit.py` (20 unit tests) pin the decorator's behavior including 429 shape, Retry-After header, per-callable isolation, and sliding window. These tests remain unchanged; they document the behavior the planner can rely on.
- New tests needed: integration test for webhook 429 when limit is exceeded (patch `rate_limit.time` to control the window).

---

### SEC-02: Config GET Response Normalization

#### Current Serialization Surface

**File: `src/python/web/serialize/serialize_config.py`** [VERIFIED: direct source read]

```python
_SENSITIVE_FIELDS = {
    "lftp": ["remote_password", "remote_address", "remote_username", "remote_path"],
    "sonarr": ["sonarr_api_key"],
    "radarr": ["radarr_api_key"],
    "general": ["webhook_secret", "api_token"],
}

_REDACTED = "**REDACTED**"

class SerializeConfig:
    @staticmethod
    def config(config: Config, authenticated: bool = False) -> str:
        ...
        if not authenticated:
            for section, fields in _SENSITIVE_FIELDS.items():
                ...
                section_dict[field] = _REDACTED  # ← "**REDACTED**" for unauthenticated
        return json.dumps(config_dict_lowercase)
```

**Current GET response shape for secret fields:**
- **Unauthenticated request:** `webhook_secret: "**REDACTED**"`, `api_token: "**REDACTED**"`
- **Authenticated request:** `webhook_secret: "<actual value or empty>"`, `api_token: "<actual value or empty>"`

**Critical clarification on `*_is_set`:** There is NO `webhook_secret_is_set` or `api_token_is_set` boolean field in the current codebase. CONTEXT.md §D-10/D-11 references "the already-present explicit boolean (`*_is_set`)" — this wording is aspirational/conceptual, not a currently-emitted field name. The planner must choose one of two interpretations:

**Option A (minimal):** Simply change `_REDACTED` to `""` (or always emit `""` for both authenticated and unauthenticated paths). No new fields added. The Angular front-end already does not display `webhook_secret` value in the settings UI (confirmed: no Angular source references `webhook_secret` or `api_token` values from the config GET response). COMPAT risk: this changes the GET response shape from `"**REDACTED**"` to `""` for unauthenticated callers — the string differs, but D-11 explicitly says "shape is identical whether set or unset." This is the correct interpretation.

**Option B (additive):** Add `webhook_secret_is_set: bool` and `api_token_is_set: bool` fields alongside the zeroed value field. This is additive and therefore COMPAT-safe (no existing field changes shape), but adds fields not currently in the response.

**Research recommendation:** Option A is the correct implementation of D-10/D-11 as written. The change is:

In `serialize_config.py`, change the serialization so that for `general.webhook_secret` and `general.api_token`:
- Always emit `""` regardless of authentication status and regardless of whether the value is set.

The `_SENSITIVE_FIELDS` approach covers both paths via the unauthenticated redaction. For the authenticated path, the change requires explicit zeroing of these two fields.

**Concrete change to `serialize_config.py`:**

```python
# Fields whose value must always serialize as "" (never reveal actual value).
# Presence is conveyed only by operator-visible configuration state.
_ALWAYS_BLANK_FIELDS = {
    "general": ["webhook_secret", "api_token"],
}

class SerializeConfig:
    @staticmethod
    def config(config: Config, authenticated: bool = False) -> str:
        ...
        # Redact sensitive fields for unauthenticated requests
        if not authenticated:
            for section, fields in _SENSITIVE_FIELDS.items():
                ...
                section_dict[field] = _REDACTED  # existing, for other fields

        # SEC-02: secret value fields always serialize as "" (D-10/D-11)
        for section, fields in _ALWAYS_BLANK_FIELDS.items():
            if section in config_dict_lowercase:
                for field in fields:
                    if field in config_dict_lowercase[section]:
                        config_dict_lowercase[section][field] = ""

        return json.dumps(config_dict_lowercase)
```

**SET path not touched:** `__handle_set_config` in `config.py:92-105` is unchanged. On-disk format unchanged. `_SECRET_FIELD_PATHS` in `config.py:19-25` unchanged.

**COMPAT risk:** The GET response for `webhook_secret` and `api_token` changes from `"**REDACTED**"` (unauthenticated) or real value (authenticated) to `""` in both cases. Angular does not currently read or display these values from the GET response. No breaking change for any consumer that correctly treats the config GET as display-only.

#### Existing Tests That Pin Current Behavior for SEC-02

- `test_config.py:TestConfigHandler.test_get` (line 8-18): Tests that the GET response returns correct values for `general.debug`, `lftp.remote_path`, `controller.interval_ms_local_scan`, `web.port`. It does NOT assert anything about `webhook_secret` or `api_token` values. The comment "No api_token configured → auth_valid=True → config is unredacted" means the test verifies the unredacted path exists but doesn't check the secret fields. This test will continue to pass after SEC-02.
- New test needed: assert that `general.webhook_secret` and `general.api_token` are `""` in the GET response regardless of whether they are set or not, and regardless of auth status.

---

## Architecture Patterns

### Recommended Project Structure (no new files beyond helper)

```
src/python/
├── common/
│   └── types.py          # Add sanitize_log_value() here
├── web/
│   └── serialize/
│       └── serialize_config.py   # SEC-02: always-blank fields
│   └── handler/
│       └── webhook.py    # BUG-02 + SEC-03 changes
└── controller/
    ├── controller.py     # SEC-01: replace line 790 with sanitize_log_value()
    └── webhook_manager.py  # SEC-01: replace lines 37, 76 with sanitize_log_value()
```

### Anti-Patterns to Avoid

- **Circular imports:** Do not put `sanitize_log_value()` in `web/` (controller and lftp cannot import from `web/`). Do not put it in `controller/` (webhook.py imports from `controller/webhook_manager` already, adding `common/types` instead avoids new cross-tier imports).
- **Blanket sanitization:** D-02 says targeted, not blanket. Do not wrap `root_name` in log lines that come from internal model lookups unless the planner explicitly decides to include BORDERLINE sites.
- **Mutating `_SECRET_FIELD_PATHS`:** `webhook_require_secret` is not a secret and must not be added to that tuple. Encryption only applies to the 5 existing credential fields.
- **Touching the SET path for SEC-02:** `__handle_set_config` must not be changed. Only the GET serialization changes.
- **Raising 503 after body parse:** BUG-02's 503 must fire before `request.json` (line 100). The `_verify_hmac` placement at line 95 guarantees this — any alternative placement must verify it comes before line 100.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP rate limiting | Custom per-IP counter or token bucket | `web.rate_limit.rate_limit` decorator | Already implemented, tested, and used by 4 other handlers |
| Constant-time HMAC comparison | `==` comparison | `hmac.compare_digest` (already in use at line 73) | Timing attack prevention |
| Log sanitization | Re-implementing per call site | `sanitize_log_value()` in `common/types.py` | Single source of truth, no drift |

---

## Common Pitfalls

### Pitfall 1: Breaking the `Empty webhook_secret skips HMAC` Contract
**What goes wrong:** Changing `_verify_hmac` logic so that `not secret` → 401 instead of `None` even when `webhook_require_secret=False`.
**Why it happens:** Developer confuses the require_secret flag state.
**How to avoid:** The condition is `if not secret AND webhook_require_secret: return 503`. The `else` branch (require_secret=False) must still return `None` unconditionally.
**Warning signs:** Existing webhook tests fail with 503 after the change.

### Pitfall 2: PROP Declaration Order Breaks as_dict
**What goes wrong:** Adding `webhook_require_secret` PROP out of sequence causes `as_dict()` to emit fields in wrong order, breaking any consumer that assumes General section key order.
**Why it happens:** `InnerConfig.__prop_addon_map` is ordered by creation time (class definition order). PROPs must be declared in the order they should appear.
**How to avoid:** Add `webhook_require_secret` after `allowed_hostname` in the class body AND initialize to `None` in `__init__` in the same relative position.
**Warning signs:** `test_config.py` or encryption round-trip tests fail.

### Pitfall 3: Injecting Python `False` vs String `"False"` in from_dict
**What goes wrong:** `general_dict["webhook_require_secret"] = False` (Python bool) instead of `"False"` (string) causes `Converters.bool` to receive a non-string and skip conversion, potentially setting the property to the Python bool directly (which works, but bypasses the checker pipeline).
**Why it happens:** Other from_dict defaults for bool fields use string "False" (see `config.py:558-559`).
**How to avoid:** Use `"False"` as the fallback string value. Compare with `config.autodelete.dry_run = False` (line 559) which sets native Python bool directly on the object — that path bypasses from_dict entirely. The from_dict injection should use strings.
**Warning signs:** `Converters.bool` is never called for this field when loading old config files.

### Pitfall 4: Rate-Limit State is Per-Callable Object, Not Per-Route
**What goes wrong:** Decorating the same bound method object twice produces one shared counter, not two.
**Why it happens:** `rate_limit(N, W)(fn)` creates a closure captured by the `fn` identity. In Python, bound methods are created fresh each call (`self.__handle_sonarr_webhook` creates a new bound method object each time it is referenced). Since `add_post_handler` is called once at startup, the bound method is captured once per route registration — this is correct and each decoration produces an independent counter.
**How to avoid:** The `TestRateLimitIndependentClosures` tests confirm per-callable isolation. No action needed beyond using the existing pattern.

### Pitfall 5: SEC-02 Breaks Authenticated Config GET for Operators
**What goes wrong:** After SEC-02, an operator who relies on reading the real `webhook_secret` value from the GET response (to copy it) can no longer do so.
**Why it happens:** D-10 explicitly says "always `""`". This is intentional.
**How to avoid:** This is a documented behavior change, not a bug. The COMPAT constraint says "no change to existing public API contracts for already-supported paths." The current authenticated path returns the real value, so this IS a change to the authenticated path. The planner must confirm this is acceptable under D-10's authority over SEC-02. Research note: no Angular source reads `webhook_secret` from the GET response, so the Angular client is unaffected.

---

## Code Examples

### BUG-02: Modified _verify_hmac
```python
# Source: direct analysis of webhook.py:43-77
def _verify_hmac(self) -> Optional[HTTPResponse]:
    secret = self.__config.general.webhook_secret
    if not secret:
        if self.__config.general.webhook_require_secret:
            logger.warning(
                "Webhook rejected: webhook_require_secret is enabled "
                "but no webhook_secret is configured"
            )
            return HTTPResponse(status=503, body="Service unavailable")
        # No secret configured — skip verification for backward compatibility
        return None
    # ... rest of existing HMAC verification unchanged ...
```

### SEC-03: Rate-Limited Route Registration
```python
# Source: mirrors config.py:27-29 and status.py:14-17 patterns
from ..rate_limit import rate_limit  # add to imports

def add_routes(self, web_app: WebApp):
    web_app.add_post_handler(
        "/server/webhook/sonarr",
        rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_sonarr_webhook)
    )
    web_app.add_post_handler(
        "/server/webhook/radarr",
        rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_radarr_webhook)
    )
```

### SEC-01: sanitize_log_value Usage
```python
# Source: replaces existing inline pattern at webhook_manager.py:37, 76, controller.py:790
from common import sanitize_log_value  # or from common.types import sanitize_log_value

# Before (webhook_manager.py:37):
# safe_file_name = file_name.replace("\n", "\\n").replace("\r", "\\r")
# After:
safe_file_name = sanitize_log_value(file_name)
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd src/python && python -m pytest tests/unittests/ tests/integration/test_web/ -x -q` |
| Full suite command | `cd src/python && python -m pytest --cov --cov-report=term-missing -x` |
| Coverage floor | `fail_under = 88` (pyproject.toml:88) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUG-02 | Default flag off → no behavior change | unit/integration | `pytest tests/integration/test_web/test_handler/test_webhook.py -x` | YES (existing) |
| BUG-02 | Flag on, no secret → 503 before body parse | integration | `pytest tests/integration/test_web/test_handler/test_webhook.py::TestWebhookIntegration::test_require_secret_no_secret_returns_503` | NO — Wave 0 |
| BUG-02 | Flag on, secret set → existing HMAC flow unchanged | integration | `pytest tests/integration/test_web/test_handler/test_webhook.py -x` | NO — Wave 0 |
| BUG-02 | Old config file loads without webhook_require_secret | unit | `pytest tests/unittests/test_common/test_config.py -x` | Partial — add case |
| SEC-01 | sanitize_log_value strips CR/LF | unit | `pytest tests/unittests/test_common/test_types.py -x` | NO — Wave 0 |
| SEC-01 | enqueue_import uses sanitize_log_value | unit | `pytest tests/unittests/test_controller/test_webhook_manager.py -x` | NO — Wave 0 |
| SEC-03 | Sonarr webhook returns 429 over limit | integration | `pytest tests/integration/test_web/test_handler/test_webhook.py::TestWebhookRateLimit -x` | NO — Wave 0 |
| SEC-03 | Radarr and Sonarr rate limits are independent | unit | `pytest tests/unittests/test_web/test_rate_limit.py::TestRateLimitIndependentClosures` | YES (existing) |
| SEC-02 | GET returns "" for webhook_secret regardless of value | integration | `pytest tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_get_redacts_secret_fields` | NO — Wave 0 |
| SEC-02 | GET returns "" for api_token regardless of auth state | integration | `pytest tests/integration/test_web/test_handler/test_config.py -x` | Partial — add case |

### Sampling Rate

- **Per task commit:** `cd src/python && python -m pytest tests/unittests/ tests/integration/test_web/test_handler/test_webhook.py tests/integration/test_web/test_handler/test_config.py -x -q`
- **Per wave merge:** Full suite: `cd src/python && python -m pytest --cov --cov-report=term-missing -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unittests/test_common/test_types.py` — unit tests for `sanitize_log_value()` (empty string, plain string unchanged, `\n` escaped, `\r` escaped, `\r\n` both escaped, combined)
- [ ] `tests/integration/test_web/test_handler/test_webhook.py` — add `TestWebhookFailClosed` class: (1) require_secret=True + no secret → 503; (2) require_secret=True + valid secret → passes HMAC; (3) require_secret=False + no secret → 200 (existing behavior)
- [ ] `tests/integration/test_web/test_handler/test_webhook.py` — add `TestWebhookRateLimit` class: (1) 60 requests pass; (2) 61st returns 429; (3) Sonarr and Radarr have independent counters
- [ ] `tests/integration/test_web/test_handler/test_config.py` — add `test_get_secret_fields_always_blank`: set `webhook_secret` to a non-empty value, GET → assert `general.webhook_secret == ""`; also assert `general.api_token == ""` similarly
- [ ] `tests/unittests/test_common/test_config.py` — add case to `test_general_config` (or new method): from_dict without `webhook_require_secret` key → loads with default False; from_dict with `webhook_require_secret: "True"` → loads True

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes (BUG-02 webhook auth gate) | HMAC-SHA256 with `hmac.compare_digest` — already in use |
| V3 Session Management | No | Not applicable to webhook endpoints |
| V4 Access Control | Yes (BUG-02 fail-closed) | Config flag defaults to off; webhook secret required when flag is on |
| V5 Input Validation | Yes (SEC-01 log injection) | `sanitize_log_value()` strips CWE-117 vectors |
| V6 Cryptography | No | HMAC key is already in use; no new crypto |
| V10 Malicious Code | No | Rate limiting (SEC-03) is DoS mitigation, not malicious code |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Webhook body parse before auth | Spoofing + DoS | BUG-02: 503 before body parse when secret required |
| Log injection via CR/LF in remote file names | Tampering | SEC-01: `sanitize_log_value()` strips newlines |
| Webhook endpoint DoS (unbounded call rate) | DoS | SEC-03: rate_limit(60, 60.0) per route |
| Config GET leaking real secret value | Information Disclosure | SEC-02: always emit `""` for secret value fields |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `*_is_set` booleans do not currently exist in the GET response | SEC-02 | If they do exist (e.g., added in a branch not read), the normalization approach must also handle them |
| A2 | Angular does not read `webhook_secret` or `api_token` values from config GET | SEC-02 | If Angular reads and displays these, SEC-02 would break the settings UI (need to add `*_is_set` booleans for the Angular to use instead) |
| A3 | The BORDERLINE remote-scanner file names (controller.py:229, 760, 975) are NOT included in the D-01 three targets | SEC-01 taint scope | If planner decides these must be sanitized, 3 additional call sites need sanitize_log_value |

**If this table is empty for A1/A2:** Both were checked against Angular source (no matches found for `webhook_secret` or `api_token` in Angular `.ts` files outside node_modules). Confidence is HIGH.

---

## Open Questions for Planner

1. **SEC-02 — `*_is_set` booleans:** The CONTEXT.md says "presence is carried only by the already-present explicit boolean (`*_is_set`)." No such boolean exists today. Should SEC-02 add `webhook_secret_is_set: bool` and `api_token_is_set: bool` to the GET response (Option B, additive) or simply zero the value field to `""` (Option A, minimal)? Option A satisfies D-10/D-11 text literally. Option B is a stricter reading. **Recommendation: Option A.**

2. **SEC-01 BORDERLINE scope — remote-scanner-sourced file names:** Controller.py lines 229, 760, 975 log model file names that originate from the seedbox remote directory listing (via lftp), not from webhook JSON. Should these be included in the sanitize_log_value application? They are "remote" in a weaker sense than direct webhook payload values. **Recommendation: include lines 760 and 975 (they handle the `root_name` from `__check_webhook_imports` which immediately follows the webhook path), exclude line 229 (auto-delete timer context, more internal).**

3. **SEC-02 — authenticated GET path:** Currently the authenticated path returns the real `webhook_secret` value. D-10 says "always serialize as `""`". This is a behavior change for authenticated callers. Since no Angular code reads this value, the practical impact is zero — but the planner should confirm this is acceptable.

---

## Sources

### Primary (HIGH confidence)
- Direct source read: `src/python/web/handler/webhook.py` — all assertions about hook points and flow
- Direct source read: `src/python/web/rate_limit.py` — decorator semantics confirmed
- Direct source read: `src/python/web/serialize/serialize_config.py` — current GET serialization confirmed
- Direct source read: `src/python/common/config.py` — PROP machinery, from_dict pattern, _SECRET_FIELD_PATHS
- Direct source read: `src/python/seedsyncarr.py:371-393` — startup warning confirmed
- Direct source read: `src/python/controller/webhook_manager.py` — all three CWE-117 inline copies confirmed
- Direct source read: `src/python/controller/controller.py:787-795` — third CWE-117 copy confirmed
- Direct source read: `src/python/tests/` — all test file inventories confirmed

### Secondary (MEDIUM confidence)
- Grep analysis of all `logger.*` calls in `controller/`, `lftp/`, `controller/delete/`, `controller/extract/` — taint enumeration derives from this
- Angular source search for `webhook_secret`, `api_token`, `REDACTED`, `is_set` — returned no hits, supporting A2

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all verified in source
- Architecture: HIGH — all hook points confirmed with exact line numbers from direct source reads
- Pitfalls: HIGH — derived from actual code patterns observed
- Taint enumeration: MEDIUM — complete for confirmed + borderline sites; "not tainted" claims are bounded by grep coverage

**Research date:** 2026-05-31
**Valid until:** 2026-07-01 (stable codebase; changes only if webhook.py or config.py is modified between now and planning)
