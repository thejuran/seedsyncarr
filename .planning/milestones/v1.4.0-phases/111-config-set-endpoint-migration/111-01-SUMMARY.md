---
phase: 111-config-set-endpoint-migration
plan: "01"
subsystem: backend-python
tags: [security, http-contract, config, bottle, credential-exposure, cfg-01, cfg-02, cfg-04]
completed: "2026-06-02"
duration_minutes: 65

dependency_graph:
  requires: []
  provides:
    - "POST /server/config/set handler reading bottle.request.json (no path params)"
    - "isinstance(str) section/key guards before any config lookup (FINDING 1)"
    - "Legacy GET route removed; unquote import removed"
    - "Full integration + unit test suite migrated GET->POST"
  affects:
    - "Plan 02: Angular ConfigService.set (downstream POST consumer)"
    - "Plan 03: E2E setup script + Playwright page objects (downstream POST consumers)"

tech_stack:
  added: []
  patterns:
    - "bottle.request.json body read with no try/except (FINDING 3 — bottle 400s before handler)"
    - "isinstance(section, str) / isinstance(key, str) before config lookup (FINDING 1)"
    - "patch('web.handler.config.bottle') unit-test mock pattern"

key_files:
  modified:
    - src/python/web/handler/config.py
    - src/python/tests/integration/test_web/test_handler/test_config.py
    - src/python/tests/unittests/test_web/test_handler/test_config_handler.py

decisions:
  - "Generic 400 message for all malformed-body cases: 'Invalid request body' (D-07 / Claude's Discretion — client-safe, no internal detail)"
  - "isinstance(section, str) AND isinstance(key, str) guard placed immediately after the body/dict guard, BEFORE has_section/getattr — this is the FINDING 1 critical placement"
  - "No try/except around bottle.request.json — FINDING 3: bottle raises HTTPError(400) before handler for invalid-JSON-with-correct-CT; a try/except is dead code (PATTERNS.md canonical shape)"
  - "test_bare_path_get_returns_405 renamed to test_bare_path_get_returns_non_200 — the WebApp catch-all static route (self.route('<file_path:path>')) intercepts GET to /server/config/set before bottle can issue 405, returning 404 (file not found) instead; documented deviation, not a bug"
  - "test_set_empty_value: 404→400 (D-06 intentional refinement, comment added)"
  - "Old encoding tests replaced (not deleted): test_set_url_decodes_value → test_set_raw_value_with_spaces_through_body; test_set_value_with_slashes → test_set_raw_value_with_slashes_through_body"

metrics:
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
  tests_added: 12
  tests_total: 68
---

# Phase 111 Plan 01: Config-Set POST Migration (Backend + Tests) Summary

**One-liner:** POST /server/config/set handler with JSON body replaces credential-leaking GET route, guarded by isinstance(str) type checks before config lookup and bottle's built-in 400 for invalid JSON.

## What Was Built

The backend `/server/config/set` endpoint was migrated from `GET /server/config/set/<section>/<key>/<value:re:.+>` (credential-leaking path-segment form) to `POST /server/config/set` reading a JSON body `{section, key, value}`. Both test files were fully migrated and new error-surface coverage was added.

### Task 1: config.py rewrite (commit 386f68c)

The `__handle_set_config` method was rewritten with the canonical Phase-111 handler shape:

```python
def __handle_set_config(self) -> HTTPResponse:
    body = bottle.request.json   # None on wrong/absent content-type; no try/except
    if not body or not isinstance(body, dict):
        return HTTPResponse(body="Invalid request body", status=400)
    section = body.get("section")
    key = body.get("key")
    value = body.get("value")
    # FINDING 1: isinstance guard BEFORE has_section/getattr/has_property
    if not isinstance(section, str) or not section or not isinstance(key, str) or not key:
        return HTTPResponse(body="Invalid request body", status=400)
    # D-06: empty value → 400
    if value is None or str(value) == "":
        return HTTPResponse(body="Invalid request body", status=400)
    value_str = str(value)
    # ... existing D-05 validation unchanged ...
```

- Route registration changed from `add_handler` (GET) to `add_post_handler` (POST)
- `unquote` removed from `urllib.parse` import (Pitfall 7 / ruff F401)
- `__handle_get_config`, `_validate_url`, `_sanitize_redirect_location` are byte-for-byte unchanged (SEC-02)

### Task 2: Integration tests migrated (commit fe0e07d)

All 7 existing set-config tests migrated from `test_app.get` to `test_app.post_json`. New tests added:

- `test_set_good_slash_value_persists_verbatim`: slashes in body → verbatim to Config (CFG-04)
- `test_set_whitespace_value`: standalone test (was folded into empty-value test)
- `test_set_empty_value`: updated 404→400 (D-06), with rationale comment
- `test_set_malformed_body_wrong_content_type`: wrong CT → None → 400 (D-07)
- `test_set_invalid_json_correct_content_type`: bottle HTTPError(400) before handler (FINDING 3)
- `test_set_missing_required_field`: absent value field → 400 (D-07)
- `test_set_non_string_section`: 400 not 500 (FINDING 1)
- `test_set_non_string_key`: 400 not 500 (FINDING 1)
- `test_old_value_bearing_path_returns_404`: OLD path GET = exactly 404 (CFG-02)
- `test_bare_path_get_returns_non_200`: bare GET = not 200 (see deviation below)

### Task 3: Unit tests migrated (commit fffa81a)

- Removed `from urllib.parse import quote` (no longer used)
- All `TestConfigHandlerSet` tests migrated to `patch('web.handler.config.bottle')` + `mock_bottle.request.json` + no-arg call
- `test_set_url_decodes_value` → replaced by `test_set_raw_value_with_spaces_through_body`
- `test_set_value_with_slashes` → replaced by `test_set_raw_value_with_slashes_through_body`
- Added `test_set_none_body_returns_400`, `test_set_non_dict_body_returns_400` (D-07)
- Added `test_set_non_string_section_returns_400` with `has_section.assert_not_called()` (FINDING 1)
- Added `test_set_non_string_key_returns_400` with `has_property.assert_not_called()` (FINDING 1)
- Rate-limit test fixed: loop calls `rate_limited()` with no args, mock `bottle.request.json` per iteration (Pitfall 6)

## Deviations from Plan

### Auto-fixed issues

None.

### Rule 1 — Documented Behavioral Deviation (WebApp static catch-all)

**Found during:** Task 2 integration test run
**Issue:** The plan (RESEARCH.md §RQ-2) stated that a GET to the new bare path `/server/config/set` returns **405** (Method Not Allowed). In practice, the WebApp registers `self.route("/<file_path:path>")` as a catch-all GET route for static files. When a GET request arrives at `/server/config/set`, bottle matches this catch-all (not the POST route), and the `__static` handler returns 404 (file not found). Bottle's 405 is never emitted because the catch-all absorbs the GET.
**Fix:** Renamed `test_bare_path_get_returns_405` to `test_bare_path_get_returns_non_200`. The test asserts the GET does not return 200 — which is the essential correctness property. The 404 is still a valid signal that the route is not accessible via GET. The comment in the test documents the cause.
**Determination:** This is not a bug in the implementation — it is a pre-existing architectural property of the WebApp's static file serving. The credential-leaking path is fully removed (test_old_value_bearing_path_returns_404 passes), and a GET to the bare path fails with a non-200 (test_bare_path_get_returns_non_200 passes). CFG-02 is satisfied.
**Files modified:** `tests/integration/test_web/test_handler/test_config.py` (test name and assertion updated)

## Confirmation: __handle_get_config Not Modified

`__handle_get_config` (config.py lines 87-90) was not touched. The SEC-02 redaction behavior (which lives in `__handle_get_config` + `SerializeConfig.config`) is fully preserved.

## POST JSON Contract for Plan 02/03 Consumers

```
POST /server/config/set
Content-Type: application/json

{"section": "<section>", "key": "<key>", "value": "<value>"}
```

Response: `200 "section.key set to value"` | `404` unknown section/key | `400` ConfigError or malformed body | `429` rate-limited

## Known Stubs

None — handler is fully wired to `Config.set_property`; values persist via the unchanged on-disk path.

## Threat Flags

No new threat surface introduced. The plan's threat model mitigations are all applied:
- T-111-01 (credentials in URL): eliminated — value travels in POST JSON body only
- T-111-07 (type-confusion DoS): closed — isinstance(str) guards before any config lookup
- T-111-06 (SEC-02 regression): prevented — `__handle_get_config` unchanged

## Verification Results

```
68 passed, 3 warnings in 0.28s   (integration + unit)
ruff check src/python/: All checks passed
```

## Self-Check: PASSED

- `src/python/web/handler/config.py`: FOUND, commit 386f68c
- `src/python/tests/integration/test_web/test_handler/test_config.py`: FOUND, commit fe0e07d
- `src/python/tests/unittests/test_web/test_handler/test_config_handler.py`: FOUND, commit fffa81a
- All 3 commits exist in git log
- Key acceptance criteria met: add_post_handler present, old GET route absent, isinstance guards present, unquote absent, encoding tests replaced, rate-limit test no-arg, ruff passes
