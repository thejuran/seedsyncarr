---
phase: 40-credential-endpoint-security
plan: 03
subsystem: security
tags: [hmac, webhook, csp, security-headers, bottle, config]

requires:
  - phase: 40-credential-endpoint-security
    provides: "Webhook handler and config infrastructure from plans 01-02"

provides:
  - "HMAC-SHA256 signature verification on all webhook POST endpoints"
  - "Backward-compatible webhook_secret config field in Config.General"
  - "Content-Security-Policy, X-Frame-Options, X-Content-Type-Options on all API responses"
  - "after_request Bottle hook for zero-touch security header injection"

affects:
  - webhook-configuration
  - api-responses
  - security-headers

tech-stack:
  added: []
  patterns:
    - "HMAC verification with empty-secret bypass for backward compat"
    - "Bottle after_request hook for cross-cutting response decoration"
    - "Constant-time HMAC comparison via hmac.compare_digest"

key-files:
  created:
    - src/python/tests/unittests/test_web/test_web_app.py
  modified:
    - src/python/common/config.py
    - src/python/seedsync.py
    - src/python/web/handler/webhook.py
    - src/python/web/web_app.py
    - src/python/web/web_app_builder.py
    - src/python/tests/unittests/test_web/test_webhook_handler.py
    - src/python/tests/unittests/test_common/test_config.py

key-decisions:
  - "webhook_secret lives in Config.General (shared across Sonarr/Radarr) — simpler than per-service secrets"
  - "Empty webhook_secret skips verification entirely — backward compat for existing installs"
  - "X-Webhook-Signature header used for HMAC (generic, matches Sonarr/Radarr custom header support)"
  - "CSP allows unsafe-inline on style-src and Google Fonts CDN for Bootstrap compatibility"
  - "Config test golden string updated to include webhook_secret field"

patterns-established:
  - "Security headers via Bottle after_request hook: zero-touch, applies to all routes automatically"
  - "HMAC secret config pattern: null checker + empty-string default for backward compat"

requirements-completed:
  - SEC-03
  - SEC-09

duration: 25min
completed: 2026-02-24
---

# Phase 40 Plan 03: Credential Endpoint Security (HMAC + Headers) Summary

**HMAC-SHA256 webhook authentication with backward-compat bypass and CSP/X-Frame-Options/X-Content-Type-Options injected on all Bottle responses via after_request hook**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-02-24T01:00:00Z
- **Completed:** 2026-02-24T01:25:03Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Webhook endpoints now verify HMAC-SHA256 signatures when `webhook_secret` is configured; missing or invalid `X-Webhook-Signature` returns 401
- Empty `webhook_secret` (default for existing installs) skips verification — full backward compatibility
- All API responses automatically include `Content-Security-Policy`, `X-Frame-Options: DENY`, and `X-Content-Type-Options: nosniff` via a single Bottle `after_request` hook
- 45 tests pass across webhook handler, web app security headers, and config tests

## Task Commits

Each task was committed atomically:

1. **Task 1: HMAC authentication on webhook endpoints** - `a92af56` (feat)
2. **Task 2: Security headers on all API responses** - `4c485d9` (feat)

**Plan metadata:** (this summary commit)

## Files Created/Modified

- `src/python/common/config.py` - Added `webhook_secret` to `Config.General`, backward-compat default in `from_dict`
- `src/python/seedsync.py` - Set `webhook_secret = ""` in `_create_default_config`
- `src/python/web/handler/webhook.py` - Added `hmac`/`hashlib` imports, `Config` parameter, `_verify_hmac()` method called at top of `_handle_webhook()`
- `src/python/web/web_app.py` - Added `after_request` hook setting CSP, X-Frame-Options, X-Content-Type-Options headers
- `src/python/web/web_app_builder.py` - Pass `context.config` to `WebhookHandler`
- `src/python/tests/unittests/test_web/test_webhook_handler.py` - Updated `setUp` for new constructor signature; added `TestWebhookHandlerHmacVerification` class with 6 tests
- `src/python/tests/unittests/test_web/test_web_app.py` - New file: `TestWebAppSecurityHeaders` with 5 tests using `webtest.TestApp`
- `src/python/tests/unittests/test_common/test_config.py` - Updated `test_general` and `test_to_file` for new `webhook_secret` field

## Decisions Made

- `webhook_secret` placed on `Config.General` (shared secret for all webhooks) rather than per-service on `Config.Sonarr`/`Config.Radarr` — simpler, sufficient for both services
- Empty secret skips HMAC entirely — backward compat for users without webhook authentication configured
- `X-Webhook-Signature` header name matches Sonarr/Radarr's custom webhook header support
- CSP includes `'unsafe-inline'` for style-src and Google Fonts CDN references — Bootstrap CSS requires this
- `hmac.compare_digest` used for constant-time comparison to prevent timing attacks

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated config test golden string and general dict for webhook_secret**
- **Found during:** Task 1 (webhook HMAC authentication)
- **Issue:** `test_general` in `test_config.py` calls `Config.General.from_dict` directly without the outer `Config.from_dict` backward-compat injection — so the test dict needed `webhook_secret` explicitly. `test_to_file` golden string didn't include the new field.
- **Fix:** Added `webhook_secret` to `good_dict` in `test_general`, excluded it from `check_common` set (uses `Checkers.null` so empty string is valid), added explicit missing-key test. Updated `test_to_file` golden string and added `config.general.webhook_secret = ""` to setup.
- **Files modified:** `src/python/tests/unittests/test_common/test_config.py`
- **Verification:** All 15 config tests pass
- **Committed in:** `a92af56` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug: test expectations out of sync with new field)
**Impact on plan:** Necessary fix to maintain test suite accuracy. No scope creep.

## Issues Encountered

Pre-existing test failures (out of scope, not introduced by this plan):
- `test_app_process.py::test_process_with_long_running_thread_terminates_properly` — macOS multiprocessing pickle issue with `_thread.lock`
- `test_serialize_log_record.py` (5 tests) — `re.sub` called with `None` message
- `test_lftp.py` (many tests) — Latin-1 byte sequence not allowed on HFS+/APFS filesystem

These were confirmed pre-existing by running with `git stash` before my changes.

## User Setup Required

To enable webhook HMAC authentication, users add to their seedsync config file:

```ini
[General]
webhook_secret = <a-random-secret-string>
```

Then configure the same value as the webhook secret in Sonarr/Radarr → Settings → Connect → Webhook → "Custom Headers: X-Webhook-Signature: <hmac-hex-digest>". Note: Sonarr/Radarr must be configured to send the HMAC signature header for the verification to work. If `webhook_secret` is empty (default), all webhook requests are accepted without verification.

## Next Phase Readiness

- SEC-03 (webhook HMAC) and SEC-09 (security headers) requirements fulfilled
- All webhook endpoint tests and security header tests passing
- Phase 40 (credential endpoint security) plans 01-03 now complete

## Self-Check: PASSED

- `src/python/web/handler/webhook.py` — FOUND
- `src/python/web/web_app.py` — FOUND
- `src/python/common/config.py` — FOUND
- `src/python/tests/unittests/test_web/test_webhook_handler.py` — FOUND
- `src/python/tests/unittests/test_web/test_web_app.py` — FOUND
- Task 1 commit `a92af56` — FOUND
- Task 2 commit `4c485d9` — FOUND

---
*Phase: 40-credential-endpoint-security*
*Completed: 2026-02-24*
