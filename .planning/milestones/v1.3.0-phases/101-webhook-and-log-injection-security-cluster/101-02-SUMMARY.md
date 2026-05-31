---
phase: 101-webhook-and-log-injection-security-cluster
plan: "02"
subsystem: web/security
tags: [security, webhook, rate-limiting, fail-closed, config, boolprop]
dependency_graph:
  requires: []
  provides:
    - webhook_require_secret config flag (bool, default false, back-compat via from_dict fallback)
    - fail-closed 503 guard outer wrapper on both webhook routes
    - independent rate_limit(60, 60.0) closures on sonarr + radarr routes
    - startup warning for require_secret-without-secret misconfiguration
  affects:
    - src/python/common/config.py
    - src/python/web/handler/webhook.py
    - src/python/seedsyncarr.py
    - test_config.py (unittests/test_common)
    - test_webhook_handler.py (unittests/test_web)
    - test_webhook.py (integration/test_web/test_handler)
    - test_seedsyncarr.py (unittests)
tech_stack:
  added: []
  patterns:
    - 3-step PROP declaration pattern (class PROP, __init__ None, from_dict fallback)
    - from_dict .get(...) is None to handle both absent and explicit None keys
    - functools.wraps outer guard wrapper (outside rate_limit, before any body read)
    - Two independent rate_limit(60, 60.0) closures per route (per-callable isolation)
key_files:
  created: []
  modified:
    - src/python/common/config.py
    - src/python/seedsyncarr.py
    - src/python/web/handler/webhook.py
    - src/python/tests/unittests/test_common/test_config.py
    - src/python/tests/unittests/test_web/test_webhook_handler.py
    - src/python/tests/integration/test_web/test_handler/test_webhook.py
    - src/python/tests/unittests/test_seedsyncarr.py
decisions:
  - "D-04: general.webhook_require_secret PROP bool default False — operator opt-in fail-closed"
  - "D-05: flag ON + no secret -> 503 before body AND before rate-limit; flag OFF byte-identical to before"
  - "D-06: from_dict uses .get(...) is None (not just key-not-in) so explicit None also collapses to string 'False'"
  - "D-07: startup warning fires when require_secret=True and webhook_secret empty"
  - "D-08: reuse existing rate_limit decorator — no new mechanism"
  - "D-09: two separate rate_limit() calls → independent per-route closures (sonarr/radarr do not share budget)"
metrics:
  duration: ~35 minutes
  completed: "2026-05-31"
  tasks_completed: 3
  files_changed: 7
---

# Phase 101 Plan 02: Webhook Fail-Closed Guard + Rate-Limit Summary

## One-Liner

Opt-in `webhook_require_secret` bool flag with 503 fail-closed outer guard ahead of rate_limit + independent 60/60s rate-limit closures on both webhook routes, preserving byte-identical backward compatibility when the flag is off.

## What Was Built

### Task 1: webhook_require_secret Config Flag (TDD — RED 7ee23e8 / GREEN same commit)

Applied the 3-step PROP pattern to `Config.General`:

1. Class-level: `webhook_require_secret = PROP("webhook_require_secret", Checkers.null, Converters.bool)` — placed after `allowed_hostname` (declaration order per Pitfall 2)
2. `__init__`: `self.webhook_require_secret = None`
3. `from_dict` back-compat: `if general_dict.get("webhook_require_secret") is None: general_dict["webhook_require_secret"] = "False"` — uses `.get(...) is None` to handle BOTH absent keys AND explicit `None` values (codex medium variant: a present-but-None value would otherwise slip past Converters.bool, serialize as the string "None", and crash the next reload)

First-run default: added `config.general.webhook_require_secret = False` to `_create_default_config()` so freshly-generated configs round-trip through `to_str()` → `from_dict()` without a ConfigError (BLOCKER-1).

Flag is NOT in `_SECRET_FIELD_PATHS` — it is a behavior flag, not an encrypted credential.

Tests added: `test_general` (extended with new field), `test_general_webhook_require_secret_back_compat`, `test_general_webhook_require_secret_true`, `test_default_config_roundtrips_require_secret`, `test_general_webhook_require_secret_explicit_none_defaults_false`.

Also updated `_build_plaintext_config()` and `test_to_file` golden string to include the new field.

### Task 2: Fail-Closed Guard + Rate-Limit Webhook Routes (TDD — RED → GREEN 6766e09)

Added to `webhook.py`:

- `import functools` and `from ..rate_limit import rate_limit`
- `_make_require_secret_guard(handler)` — `@functools.wraps` wrapper: checks `webhook_require_secret AND NOT webhook_secret` → logs warning → returns `HTTPResponse(status=503)`; reads no body, consults no counter; otherwise delegates to `handler()` unchanged
- Routes registered as `_make_require_secret_guard(rate_limit(60, 60.0)(handler))` on a single line each (gate-formatting requirement: `grep -cE` pattern matches per-line)
- Two **separate** `rate_limit(60, 60.0)` calls → independent per-route closures (D-09, Pitfall 4)
- `_verify_hmac` left completely unchanged (its no-secret-skip path still `return None`)

Tests added:
- Unit: `TestWebhookFailClosedGuard` — proves 503 + body.read not called + sentinel inner not called (mirroring size-limit test line 274 pattern)
- Integration: `TestWebhookFailClosed` — COMPAT, 503, HMAC-path (401), and `test_503_precedes_429_when_window_exhausted` (61 fail-closed requests → all 503, never 429, BLOCKER 2 proof)
- Integration: `TestWebhookRateLimit` — 61st request → 429, independent counters

### Task 3: Startup Warning Extension (340567e)

Added an independent `if config.general.webhook_require_secret and not config.general.webhook_secret:` block in `_emit_startup_warnings`, placed after the existing webhook_secret warning and before the api_token block. Both warnings can fire together when `require_secret=True` and no secret is set (two distinct concerns: "endpoint accepts any caller" vs "endpoint will reject all callers with 503").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _build_plaintext_config test fixture missing webhook_require_secret**
- **Found during:** Task 1 GREEN phase (test_disable_restores_plaintext failed)
- **Issue:** `_build_plaintext_config()` in test_config.py built a `Config()` without setting `webhook_require_secret`, so `to_str()` serialized it as "None". When `from_str()` reloaded it, `Converters.bool("None")` raised ConfigError
- **Fix:** Added `c.general.webhook_require_secret = False` to the fixture; also updated `test_to_file` golden string to include `webhook_require_secret = False`
- **Files modified:** `src/python/tests/unittests/test_common/test_config.py`
- **Commit:** 7ee23e8

**2. [Rule 1 - Bug] Fixed _make_mock_config in test_seedsyncarr.py missing webhook_require_secret**
- **Found during:** Task 3 (test_startup_warns_both_when_both_empty expected 3 warnings, got 4)
- **Issue:** `_make_mock_config()` didn't set `webhook_require_secret`; `MagicMock()` returns truthy for unset attribute access, triggering the new require_secret warning even in tests that expect the old warning count
- **Fix:** Added `webhook_require_secret=False` parameter to `_make_mock_config()` and set it on the mock
- **Files modified:** `src/python/tests/unittests/test_seedsyncarr.py`
- **Commit:** 340567e

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes beyond those already in the plan's threat model.

## Self-Check

All 3 tasks committed individually (7ee23e8, 6766e09, 340567e). Files verified:

- `src/python/common/config.py` — webhook_require_secret PROP declared
- `src/python/seedsyncarr.py` — first-run default + startup warning
- `src/python/web/handler/webhook.py` — guard + rate-limit imports + add_routes + _make_require_secret_guard
- Test files — 4 new test_config cases, 3 unit guard cases, 6 integration cases (TestWebhookFailClosed + TestWebhookRateLimit)

## Self-Check: PASSED
