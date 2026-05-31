# Phase 101: Webhook + Log-Injection Security Cluster - Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 9 (4 new/modified production files + 5 test files)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/common/types.py` (add helper) | utility | transform | `src/python/common/types.py` itself (existing `overrides()`) | exact — same module, same pure-function style |
| `src/python/web/handler/webhook.py` (BUG-02 + SEC-03) | middleware/handler | request-response | `src/python/web/handler/status.py` (rate_limit), `src/python/web/handler/config.py` (rate_limit + auth guard) | exact |
| `src/python/common/config.py` (new PROP + from_dict) | config | CRUD | same file — existing `webhook_secret`/`api_token`/`allowed_hostname` PROP declarations (lines 231–233) and `from_dict` block (lines 514–522) | exact |
| `src/python/web/serialize/serialize_config.py` (SEC-02) | serializer | transform | same file — existing `_SENSITIVE_FIELDS`/`_REDACTED` block (lines 8–36) | exact |
| `src/python/controller/webhook_manager.py` (SEC-01 × 2) | service | event-driven | same file — existing inline escapes at lines 37, 76 being replaced | exact |
| `src/python/controller/controller.py` (SEC-01 × 3) | service | event-driven | same file — existing inline escape at line 790; new sites at lines 760, 975 | exact |
| `src/python/seedsyncarr.py` (BUG-02 warning) | config/startup | request-response | same file — existing `_emit_startup_warnings` block (lines 371–392) | exact |
| `tests/unittests/test_common/test_types.py` (new class) | test | — | same file — `TestOverrides` class (lines 20–78) | exact |
| `tests/integration/test_web/test_handler/test_webhook.py` (new classes) | test | — | `TestWebhookIntegration` (lines 4–60) + `tests/unittests/test_web/test_rate_limit.py` `TestRateLimitOverLimit` | exact |
| `tests/integration/test_web/test_handler/test_config.py` (new cases) | test | — | `TestConfigHandler.test_get` (lines 8–20) + `tests/unittests/test_web/test_serialize/test_serialize_config.py` | exact |
| `tests/unittests/test_common/test_config.py` (new cases) | test | — | `TestGeneralConfig.test_general` (lines 281–325) | exact |

---

## Pattern Assignments

---

### `src/python/common/types.py` — add `sanitize_log_value()` (SEC-01)

**Analog:** same file — existing `overrides()` function (lines 1–14)

**Existing module structure** (lines 1–14 — full file, small):
```python
import inspect

def overrides(interface_class):
    """
    Decorator to check that decorated method is a valid override
    Source: https://stackoverflow.com/a/8313042
    :param interface_class: The super class
    """
    assert(inspect.isclass(interface_class)), "Overrides parameter must be a class type"

    def overrider(method):
        assert(method.__name__ in dir(interface_class)), "Method does not override super class"
        return method
    return overrider
```

**Pattern to replicate:** module-level pure function, Google-style docstring with Args/Returns sections, no class wrapper, imports only stdlib. Append after `overrides()`.

**New function signature/docstring shape** (matches research recommendation exactly):
```python
def sanitize_log_value(value: str) -> str:
    """Escape CR/LF control characters from a string before logging.

    Prevents log injection (CWE-117) by replacing newlines with their literal
    escape sequences so crafted payloads cannot split log entries.

    Args:
        value: Potentially untrusted string to sanitize.

    Returns:
        Sanitized string safe for log interpolation.
    """
    return value.replace("\r", "\\r").replace("\n", "\\n")
```

**Export in `src/python/common/__init__.py`** (line 1 pattern — add alongside `overrides`):
```python
# current line 1:
from .types import overrides as overrides
# becomes:
from .types import overrides as overrides, sanitize_log_value as sanitize_log_value
```

---

### `src/python/web/handler/webhook.py` — BUG-02 + SEC-03

**Analog:** `src/python/web/handler/status.py` (rate_limit import + usage, lines 6–17) and `src/python/web/handler/config.py` (rate_limit import at line 14, mixed limits at lines 26–37)

**SEC-03 — import addition** (mirror `status.py:6` and `config.py:14`):
```python
# current imports (lines 1–13):
import hmac
import hashlib
import json
import os
import logging
from typing import Optional

from bottle import HTTPResponse, request

from common import overrides
from common.config import Config
from controller.webhook_manager import WebhookManager
from ..web_app import IHandler, WebApp

# add:
from ..rate_limit import rate_limit
```

**SEC-03 — route registration pattern** (mirror `status.py:13–17` and `config.py:23–29`):
```python
# current add_routes (lines 30–33):
@overrides(IHandler)
def add_routes(self, web_app: WebApp):
    """Register webhook endpoints."""
    web_app.add_post_handler("/server/webhook/sonarr", self.__handle_sonarr_webhook)
    web_app.add_post_handler("/server/webhook/radarr", self.__handle_radarr_webhook)

# becomes:
@overrides(IHandler)
def add_routes(self, web_app: WebApp):
    """Register webhook endpoints."""
    web_app.add_post_handler(
        "/server/webhook/sonarr",
        rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_sonarr_webhook)
    )
    web_app.add_post_handler(
        "/server/webhook/radarr",
        rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_radarr_webhook)
    )
```

**BUG-02 — `_verify_hmac` fail-closed branch** (add inside existing `_verify_hmac` at lines 43–77, modifying the `if not secret:` block at lines 55–57):
```python
# current (lines 54–57):
secret = self.__config.general.webhook_secret
if not secret:
    # No secret configured — skip verification for backward compatibility
    return None

# becomes:
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
```

**Key constraint:** the 503 return is at line ~57, before `request.body.read()` at line 60 — "before body parse" is satisfied by staying in `_verify_hmac`.

---

### `src/python/common/config.py` — new `webhook_require_secret` PROP (BUG-02, D-04/D-06)

**Analog:** same file — 3-step PROP pattern for `webhook_secret` / `api_token` / `allowed_hostname` (lines 231–241) and `from_dict` fallback block (lines 514–522)

**Step 1 — class-level PROP declaration** (lines 228–233, insert after `allowed_hostname`):
```python
class General(IC):
    debug = PROP("debug", Checkers.null, Converters.bool)
    verbose = PROP("verbose", Checkers.null, Converters.bool)
    webhook_secret = PROP("webhook_secret", Checkers.null, Converters.null)
    api_token = PROP("api_token", Checkers.null, Converters.null)
    allowed_hostname = PROP("allowed_hostname", Checkers.null, Converters.null)
    webhook_require_secret = PROP("webhook_require_secret", Checkers.null, Converters.bool)  # BUG-02
```

**Step 2 — `__init__` initialization** (lines 235–241, add after `self.allowed_hostname = None`):
```python
def __init__(self):
    super().__init__()
    self.debug = None
    self.verbose = None
    self.webhook_secret = None
    self.api_token = None
    self.allowed_hostname = None
    self.webhook_require_secret = None  # BUG-02
```

**Step 3 — `from_dict` back-compat fallback** (lines 514–523, add after `allowed_hostname` fallback):
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
# BUG-02: webhook_require_secret — default False (preserve existing behavior on upgrade)
if "webhook_require_secret" not in general_dict:
    general_dict["webhook_require_secret"] = "False"
```

**Critical:** inject the string `"False"` (not Python `False`) — `Converters.bool` calls `_strtobool` which operates on strings. Compare: `lftp_dict["rate_limit"] = "0"` at line 527 — same string-injection pattern.

**Do NOT add to `_SECRET_FIELD_PATHS`** (lines 19–25) — `webhook_require_secret` is a behavior flag, not an encrypted credential.

---

### `src/python/web/serialize/serialize_config.py` — SEC-02 always-blank secret fields

**Analog:** same file — existing `_SENSITIVE_FIELDS` / `_REDACTED` pattern (lines 6–38)

**Current full file** (lines 1–38):
```python
import json
import collections

from common import Config

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
        config_dict = config.as_dict()

        # Make the section names lower case
        keys = list(config_dict.keys())
        config_dict_lowercase = collections.OrderedDict()
        for key in keys:
            config_dict_lowercase[key.lower()] = config_dict[key]

        # Redact sensitive fields before serializing.
        # Skip redaction for authenticated requests (CONF-04 fix).
        if not authenticated:
            for section, fields in _SENSITIVE_FIELDS.items():
                if section in config_dict_lowercase:
                    section_dict = config_dict_lowercase[section]
                    for field in fields:
                        if field in section_dict:
                            section_dict[field] = _REDACTED

        return json.dumps(config_dict_lowercase)
```

**SEC-02 change — add module-level constant and always-blank loop** (add after `_REDACTED`, and extend `config()` before the `return`):
```python
# Fields whose value ALWAYS serializes as "" regardless of auth or whether set.
# SEC-02 (D-10/D-11): prevents distinguishing set vs unset via value or length.
_ALWAYS_BLANK_FIELDS = {
    "general": ["webhook_secret", "api_token"],
}

# ... inside config(), before return json.dumps(...):
        # SEC-02: secret value fields always serialize as "" (D-10/D-11).
        # Applies on both authenticated and unauthenticated paths.
        for section, fields in _ALWAYS_BLANK_FIELDS.items():
            if section in config_dict_lowercase:
                for field in fields:
                    if field in config_dict_lowercase[section]:
                        config_dict_lowercase[section][field] = ""

        return json.dumps(config_dict_lowercase)
```

**Note:** `general.webhook_secret` and `general.api_token` remain in `_SENSITIVE_FIELDS` so unauthenticated non-general fields still get `_REDACTED`. The `_ALWAYS_BLANK_FIELDS` loop runs after the `_SENSITIVE_FIELDS` loop, overwriting `_REDACTED` with `""` for those two fields on the unauthenticated path, and zeroing the real value on the authenticated path.

---

### `src/python/controller/webhook_manager.py` — replace inline escapes with `sanitize_log_value` (SEC-01)

**Analog:** same file — the two existing inline escape calls at lines 37 and 76

**Line 37 replacement** (in `enqueue_import`):
```python
# before:
safe_file_name = file_name.replace("\n", "\\n").replace("\r", "\\r")

# after:
safe_file_name = sanitize_log_value(file_name)
```

**Line 76 replacement** (in `process` drain loop):
```python
# before:
safe_file_name = file_name.replace("\n", "\\n").replace("\r", "\\r")

# after:
safe_file_name = sanitize_log_value(file_name)
```

**Import addition** (line 4 area — add `sanitize_log_value` alongside `Context`):
```python
# current:
from common import Context

# becomes:
from common import Context, sanitize_log_value
```

Queue value (`file_name` passed to `name_to_root.get()`) remains untouched — only the log variable is sanitized. The matched `root_name` in the log at line 80 is a model-internal value and does not need sanitization.

---

### `src/python/controller/controller.py` — replace + add `sanitize_log_value` calls (SEC-01)

**Analog:** same file — existing inline escape at line 790 (confirmed D-01 target)

**Line 790 replacement** (in `__check_webhook_imports`):
```python
# before:
safe_matched = matched_name.replace("\n", "\\n").replace("\r", "\\r")

# after:
safe_matched = sanitize_log_value(matched_name)
```

**Line 760 addition** (D-03 borderline site — `root_name` from `__check_webhook_imports` model lookup, log at line 760):
```python
# current (line 760):
self.logger.debug("ModelError looking up '{}' for webhook mapping".format(root_name))

# becomes:
self.logger.debug("ModelError looking up '{}' for webhook mapping".format(
    sanitize_log_value(root_name)
))
```

**Line 975 addition** (D-03 borderline site — auto-deleted local file name, remote-scanner-sourced):
```python
# current (line 975):
self.logger.info("Auto-deleted local file '{}'".format(file_name))

# becomes:
self.logger.info("Auto-deleted local file '{}'".format(sanitize_log_value(file_name)))
```

**Import addition** — `sanitize_log_value` must be added to the existing `common` import. Find the existing `from common import ...` line and add it.

---

### `src/python/seedsyncarr.py` — extend startup warning (BUG-02, D-07)

**Analog:** same file — existing `_emit_startup_warnings` block (lines 371–392)

**Current block** (lines 371–392):
```python
@staticmethod
def _emit_startup_warnings(logger: logging.Logger, config: Config) -> None:
    """Emit security warnings for insecure configuration states."""
    if not config.general.webhook_secret:
        logger.warning(
            "Security: webhook_secret is not configured. "
            "Webhook endpoints will accept requests from any caller."
        )
    if not config.general.api_token:
        logger.warning(
            "Security: No API token configured. "
            "All API requests will be accepted without authentication."
        )
        logger.warning(
            "Security: Application is bound to 0.0.0.0 without an API token. "
            "Any host on the network can access the API."
        )
    else:
        logger.info(
            "Security: API token configured — "
            "all /server/* endpoints require Bearer authentication."
        )
```

**Extension** — add a second `if` block after the `if not config.general.webhook_secret:` block, before the `if not config.general.api_token:` block:
```python
    if config.general.webhook_require_secret and not config.general.webhook_secret:
        logger.warning(
            "Security: webhook_require_secret is True but webhook_secret is not set. "
            "All webhook requests will be rejected with 503 until a secret is configured."
        )
```

Both the existing warning and this new warning can fire simultaneously when `require_secret=True` and no secret is set — that is intentional (two different messages, two different concerns).

---

## Test Pattern Assignments

---

### `tests/unittests/test_common/test_types.py` — add `TestSanitizeLogValue` class (SEC-01)

**Analog:** same file — `TestOverrides` class (lines 20–78)

**Class structure to replicate** (lines 1–10 and 20–27 show the template):
```python
import unittest

from common import overrides  # existing import
# add:
from common import sanitize_log_value


class TestSanitizeLogValue(unittest.TestCase):
    """Unit tests for sanitize_log_value (CWE-117 log injection guard)."""

    def test_plain_string_unchanged(self):
        self.assertEqual("hello world", sanitize_log_value("hello world"))

    def test_newline_escaped(self):
        self.assertEqual("line1\\nline2", sanitize_log_value("line1\nline2"))

    def test_carriage_return_escaped(self):
        self.assertEqual("line1\\rline2", sanitize_log_value("line1\rline2"))

    def test_crlf_both_escaped(self):
        self.assertEqual("line1\\r\\nline2", sanitize_log_value("line1\r\nline2"))

    def test_empty_string(self):
        self.assertEqual("", sanitize_log_value(""))

    def test_multiple_newlines(self):
        self.assertEqual("a\\nb\\nc", sanitize_log_value("a\nb\nc"))
```

---

### `tests/integration/test_web/test_handler/test_webhook.py` — add `TestWebhookFailClosed` and `TestWebhookRateLimit` classes (BUG-02, SEC-03)

**Analog:** existing `TestWebhookIntegration` class (lines 4–60) for setUp/tearDown pattern; `tests/unittests/test_web/test_rate_limit.py` `TestRateLimitOverLimit` (lines 35–88) for 429 assertion pattern.

**Class setup pattern** (from `BaseTestWebApp` in `tests/integration/test_web/test_web_app.py`):
```python
from tests.integration.test_web.test_web_app import BaseTestWebApp

class TestWebhookFailClosed(BaseTestWebApp):
    """Integration tests for BUG-02: webhook_require_secret fail-closed behavior."""

    def _set_require_secret(self, require_secret: bool, webhook_secret: str = ""):
        """Helper to configure require_secret flag on the real Config object."""
        self.context.config.general.webhook_require_secret = require_secret
        self.context.config.general.webhook_secret = webhook_secret

    def test_require_secret_off_no_secret_returns_200(self):
        """Default behavior (require_secret=False, no secret) → 200 (COMPAT)."""
        self._set_require_secret(False, "")
        body = {"eventType": "Test"}
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)

    def test_require_secret_on_no_secret_returns_503(self):
        """require_secret=True + no secret → 503 before body parse."""
        self._set_require_secret(True, "")
        body = {"eventType": "Test"}
        resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)
        self.assertEqual(503, resp.status_int)
```

**Rate-limit class pattern** (mirror `TestRateLimitOverLimit` structure with `@patch("web.rate_limit.time")`):
```python
from unittest.mock import patch

class TestWebhookRateLimit(BaseTestWebApp):
    """Integration tests for SEC-03: rate-limited webhook routes."""

    @patch("web.rate_limit.time")
    def test_sonarr_61st_request_returns_429(self, mock_time):
        mock_time.time.return_value = 1000.0
        body = {"eventType": "Test"}
        for _ in range(60):
            resp = self.test_app.post_json("/server/webhook/sonarr", body)
            self.assertEqual(200, resp.status_int)
        resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)
        self.assertEqual(429, resp.status_int)

    @patch("web.rate_limit.time")
    def test_sonarr_and_radarr_counters_are_independent(self, mock_time):
        """Exhaust sonarr budget — radarr still accepts requests (D-09)."""
        mock_time.time.return_value = 1000.0
        body = {"eventType": "Test"}
        for _ in range(60):
            self.test_app.post_json("/server/webhook/sonarr", body)
        # radarr should still be under limit
        resp = self.test_app.post_json("/server/webhook/radarr", body)
        self.assertEqual(200, resp.status_int)
```

---

### `tests/integration/test_web/test_handler/test_config.py` — add `test_get_secret_fields_always_blank` (SEC-02)

**Analog:** same file — `TestConfigHandler.test_get` (lines 8–20); `tests/unittests/test_web/test_serialize/test_serialize_config.py` `test_config_redacts_webhook_secret` (lines 116–122)

**Pattern** (same `json.loads(str(resp.html))` decode pattern, same `assertEqual` style):
```python
def test_get_secret_fields_always_blank(self):
    """SEC-02: webhook_secret and api_token always serialize as "" in GET response."""
    self.context.config.general.webhook_secret = "super-secret-value"
    self.context.config.general.api_token = "super-token-value"
    resp = self.test_app.get("/server/config/get")
    self.assertEqual(200, resp.status_int)
    json_dict = json.loads(str(resp.html))
    self.assertEqual("", json_dict["general"]["webhook_secret"])
    self.assertEqual("", json_dict["general"]["api_token"])
    # Values must not appear anywhere in the response body
    self.assertNotIn("super-secret-value", str(resp.html))
    self.assertNotIn("super-token-value", str(resp.html))
```

---

### `tests/unittests/test_common/test_config.py` — extend `test_general` (BUG-02 back-compat)

**Analog:** same file — `test_general` method (lines 281–325) and `__check_missing_error` pattern

**Extension** — add `webhook_require_secret` to `good_dict` in `test_general` and add back-compat case:
```python
# In test_general, extend good_dict to include the new field:
good_dict = {
    "debug": "True",
    "verbose": "False",
    "webhook_secret": "",
    "api_token": "",
    "allowed_hostname": "",
    "webhook_require_secret": "False",   # add this
}
# Assert new field:
self.assertEqual(False, general.webhook_require_secret)

# Add a new test method for from_dict back-compat:
def test_general_webhook_require_secret_back_compat(self):
    """from_dict without webhook_require_secret key loads with default False (D-06)."""
    base_dict = {
        "debug": "True",
        "verbose": "False",
        "webhook_secret": "",
        "api_token": "",
        "allowed_hostname": "",
        # webhook_require_secret intentionally absent
    }
    # Must not raise — from_dict injects the default
    general = Config.General.from_dict(base_dict)
    # The from_dict fallback injects "False" before from_dict is called —
    # this test exercises Config.from_dict (the outer wrapper), not General.from_dict directly.
    # Use a minimal outer config dict:
    config = Config.from_dict({
        "General": base_dict,
        # include minimal required sections ...
    })
    self.assertEqual(False, config.general.webhook_require_secret)

def test_general_webhook_require_secret_true(self):
    """from_dict with webhook_require_secret: True loads correctly."""
    good_dict_with_flag = {
        "debug": "True",
        "verbose": "False",
        "webhook_secret": "mysecret",
        "api_token": "",
        "allowed_hostname": "",
        "webhook_require_secret": "True",
    }
    general = Config.General.from_dict(good_dict_with_flag)
    self.assertEqual(True, general.webhook_require_secret)
```

---

## Shared Patterns

### Rate-Limit Decorator Application
**Source:** `src/python/web/handler/status.py` (lines 6, 13–17) and `src/python/web/handler/config.py` (lines 14, 26–29)
**Apply to:** `webhook.py` `add_routes` for both sonarr and radarr routes
```python
from ..rate_limit import rate_limit   # import pattern

# application pattern (one call per route, independent closures):
rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_sonarr_webhook)
rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_radarr_webhook)
```

### PROP Declaration (3-Step Pattern)
**Source:** `src/python/common/config.py` lines 229–241 (General class body + `__init__`)
**Apply to:** `webhook_require_secret` addition in `Config.General`
```python
# Step 1 (class body): webhook_require_secret = PROP("webhook_require_secret", Checkers.null, Converters.bool)
# Step 2 (__init__):   self.webhook_require_secret = None
# Step 3 (from_dict):  if "webhook_require_secret" not in general_dict: general_dict["webhook_require_secret"] = "False"
```

### from_dict String-Injection Convention
**Source:** `src/python/common/config.py` line 527 (`lftp_dict["rate_limit"] = "0"`)
**Apply to:** BUG-02 `from_dict` fallback for `webhook_require_secret`
```python
# Always inject string value, not Python literal — Converters.bool calls _strtobool on strings:
general_dict["webhook_require_secret"] = "False"   # correct
# general_dict["webhook_require_secret"] = False   # wrong — bypasses _strtobool pipeline
```

### Startup Warning Block
**Source:** `src/python/seedsyncarr.py` lines 371–392 (`_emit_startup_warnings`)
**Apply to:** BUG-02 additional warning condition
```python
# Pattern: independent if-blocks, one per security concern, same logger.warning() style
if config.general.webhook_require_secret and not config.general.webhook_secret:
    logger.warning("Security: ...")
```

### Integration Test setUp via BaseTestWebApp
**Source:** `tests/integration/test_web/test_web_app.py` lines 13–58
**Apply to:** all new integration test classes (`TestWebhookFailClosed`, `TestWebhookRateLimit`)
```python
class TestWebhookFailClosed(BaseTestWebApp):
    # setUp/tearDown inherited — no override needed unless extra mocks required
    # Access real Config via: self.context.config.general.webhook_require_secret = ...
    # Access webhook_manager mock via: self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager
```

### Rate-Limit Test with Time Patch
**Source:** `tests/unittests/test_web/test_rate_limit.py` lines 44–52 (`@patch("web.rate_limit.time")`)
**Apply to:** `TestWebhookRateLimit` integration tests
```python
@patch("web.rate_limit.time")
def test_...(self, mock_time):
    mock_time.time.return_value = 1000.0
    # calls at same timestamp are within the window
```

---

## No Analog Found

All files have direct analogs in the codebase. No RESEARCH.md fallback patterns required.

---

## Metadata

**Analog search scope:** `src/python/` (all subdirs), `src/python/tests/`
**Files scanned:** 15 (webhook.py, status.py, config.py handler, common/config.py, common/types.py, common/__init__.py, serialize_config.py, controller.py, webhook_manager.py, seedsyncarr.py, test_types.py, test_webhook.py, test_config.py handler, test_serialize_config.py, test_webhook_manager.py, test_rate_limit.py, test_config.py common)
**Pattern extraction date:** 2026-05-31
