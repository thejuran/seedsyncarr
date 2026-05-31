---
phase: 101-webhook-and-log-injection-security-cluster
plan: "03"
subsystem: web-serialization
tags: [security, sec-02, config-api, information-disclosure, tdd]
dependency_graph:
  requires: []
  provides:
    - always-blank serialization for webhook_secret and api_token on all GET paths
  affects:
    - src/python/web/serialize/serialize_config.py
    - src/python/tests/unittests/test_web/test_serialize/test_serialize_config.py
    - src/python/tests/integration/test_web/test_handler/test_config.py
tech_stack:
  added: []
  patterns:
    - _ALWAYS_BLANK_FIELDS module-level constant + post-redaction loop in SerializeConfig.config()
    - TDD RED/GREEN with unit and integration layers
key_files:
  created: []
  modified:
    - src/python/web/serialize/serialize_config.py
    - src/python/tests/unittests/test_web/test_serialize/test_serialize_config.py
    - src/python/tests/integration/test_web/test_handler/test_config.py
decisions:
  - "D-10 implemented: webhook_secret and api_token always serialize as \"\" on both auth paths; no *_is_set keys added (Option A)"
  - "D-11 confirmed: GET response shape identical set vs unset; SET path and on-disk persist format untouched (COMPAT)"
  - "Deviation: integration test uses Bearer token header to exercise authenticated path, because setting api_token in config enables auth middleware requiring Bearer auth"
metrics:
  duration_minutes: 18
  completed_date: "2026-05-31"
  tasks_completed: 2
  files_modified: 3
---

# Phase 101 Plan 03: Always-Blank Config Secret Fields (SEC-02) Summary

Always-blank serialization for `general.webhook_secret` and `general.api_token` in the config GET response — `_ALWAYS_BLANK_FIELDS` post-redaction loop in `serialize_config.py` zeros both fields on every auth path, eliminating secret-presence oracle and value-leak vectors (D-10/D-11, Option A).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for always-blank secret fields | a98b584 | test_serialize_config.py |
| 1 (GREEN) | _ALWAYS_BLANK_FIELDS implementation in serialize_config.py | 5704537 | serialize_config.py |
| 2 | Handler-level GET integration test for blank secret fields | 5633d8e | test_config.py (integration) |

## What Was Built

### serialize_config.py — _ALWAYS_BLANK_FIELDS constant + loop

Added after `_REDACTED`:

```python
_ALWAYS_BLANK_FIELDS = {
    "general": ["webhook_secret", "api_token"],
}
```

And inside `SerializeConfig.config()`, after the `_SENSITIVE_FIELDS` redaction loop, before `return json.dumps(...)`:

```python
# SEC-02: secret value fields always serialize as "" (D-10/D-11).
for section, fields in _ALWAYS_BLANK_FIELDS.items():
    if section in config_dict_lowercase:
        for field in fields:
            if field in config_dict_lowercase[section]:
                config_dict_lowercase[section][field] = ""
```

This runs on BOTH paths: on unauthenticated it overwrites `**REDACTED**` with `""`; on authenticated it zeroes the real value before `json.dumps`.

### Test coverage added (serializer unit layer)

- `test_config_blanks_webhook_secret` — unauthenticated, webhook_secret set → `""`
- `test_config_blanks_api_token_unauthenticated` — unauthenticated, api_token set → `""`
- `test_config_blanks_secrets_authenticated` — authenticated=True, both set → both `""`
- `test_config_secret_value_absent_from_payload` — sentinel values absent from JSON string on both auth paths
- `test_config_blanks_api_token_legacy` — renamed from `test_config_redacts_api_token`, updated assertion from `"**REDACTED**"` to `""`

### Test coverage added (handler integration layer)

- `test_get_secret_fields_always_blank` in `TestConfigHandler` — sets webhook_secret and api_token to sentinels, GETs `/server/config/get` with correct Bearer token, asserts both fields `""` and neither sentinel in response body

## Verification

All automated checks from plan passed:

- 17 serializer unit tests green
- 7 integration handler tests green (24 total)
- Both auth paths confirmed blank via inline Python verification
- No `_is_set` keys added (`grep -c "_is_set" serialize_config.py` = 0)
- lftp/sonarr/radarr `**REDACTED**` behavior unchanged
- SET path (`test_set_good`) and on-disk persist tests green
- No sentinel value leak on either auth path

## Deviations from Plan

### Auto-adjusted: Integration test Bearer token header

**Found during:** Task 2
**Issue:** The PATTERNS.md integration test template called `self.test_app.get("/server/config/get")` without a Bearer token, but setting `self.context.config.general.api_token = "super-token-value"` on the shared `Config` object enables the `before_request` auth middleware (web_app.py lines 123-132), causing the request to return 401 instead of 200.
**Fix:** Added `headers={"Authorization": "Bearer super-token-value"}` to the integration test `GET` call so the request authenticates correctly. This correctly exercises the **authenticated** path (auth_valid=True) — exactly the branch that D-10 changes (previously returned the real value; now returns `""`).
**Files modified:** `tests/integration/test_web/test_handler/test_config.py`
**Classification:** Rule 3 (auto-fix blocking issue — test couldn't pass without this adjustment)

### Updated test_config_redacts_api_token (renamed to test_config_blanks_api_token_legacy)

**Found during:** Task 1 — pre-existing test asserted `"**REDACTED**"` for api_token on the unauthenticated path. After `_ALWAYS_BLANK_FIELDS` is applied, the value is `""`. Updated assertion to match the new expected behavior (D-10). This is an intentional behavior change documented in the plan.

## Known Stubs

None — all serializer changes are fully wired. The `_ALWAYS_BLANK_FIELDS` loop executes on every `SerializeConfig.config()` call with no conditional stub logic.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. The only change is narrowing the information surface of an existing endpoint.

## Self-Check: PASSED

- `src/python/web/serialize/serialize_config.py` exists with `_ALWAYS_BLANK_FIELDS` ✓
- `tests/unittests/test_web/test_serialize/test_serialize_config.py` has `test_config_blanks_webhook_secret` ✓
- `tests/integration/test_web/test_handler/test_config.py` has `test_get_secret_fields_always_blank` ✓
- Commit a98b584 exists (RED tests) ✓
- Commit 5704537 exists (GREEN implementation) ✓
- Commit 5633d8e exists (integration test) ✓
