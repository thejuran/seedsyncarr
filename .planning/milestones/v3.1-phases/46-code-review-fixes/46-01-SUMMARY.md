---
phase: 46-code-review-fixes
plan: 01
subsystem: api
tags: [python, security, serialization, logging, config, redaction]

# Dependency graph
requires:
  - phase: 44-code-quality
    provides: "serialize_config.py redaction framework with _SENSITIVE_FIELDS dict"
  - phase: 40-credential-endpoint-security
    provides: "SerializeLogRecord._redact_sensitive() log scrubbing"
provides:
  - "webhook_secret redacted in GET /api/config responses (CR-01)"
  - "Log redaction covers interpolated messages via getMessage() (CR-03)"
affects: [config-api, sse-log-stream, security]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_SENSITIVE_FIELDS dict extended with general section for webhook_secret"
    - "record.getMessage() over record.msg for interpolated log message redaction"

key-files:
  created: []
  modified:
    - src/python/web/serialize/serialize_config.py
    - src/python/tests/unittests/test_web/test_serialize/test_serialize_config.py
    - src/python/web/serialize/serialize_log_record.py
    - src/python/tests/unittests/test_web/test_handler/test_stream_log.py

key-decisions:
  - "webhook_secret redacted at serialization layer (not storage) — consistent with existing pattern for remote_password, sonarr_api_key, radarr_api_key"
  - "getMessage() replaces record.msg — returns fully interpolated string so format-arg passwords (logger.info('%s', password)) are caught by regex scrubbers"

patterns-established:
  - "All credential fields on any Config section belong in _SENSITIVE_FIELDS: add section key (lowercase) + field name"
  - "Log message redaction must use record.getMessage() not record.msg to handle positional format args"

requirements-completed: [CR-01, CR-03]

# Metrics
duration: 1min
completed: 2026-02-24
---

# Phase 46 Plan 01: Code Review Fixes Summary

**webhook_secret added to config API redaction and log serializer switched to getMessage() to catch passwords passed as format arguments**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-24T03:46:59Z
- **Completed:** 2026-02-24T03:47:43Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- CR-01: `"general": ["webhook_secret"]` added to `_SENSITIVE_FIELDS` — GET /api/config now returns `**REDACTED**` instead of the real webhook secret
- CR-03: `record.getMessage()` replaces `record.msg` in `SerializeLogRecord.record()` — log redaction now operates on the fully interpolated message, catching passwords passed as positional format arguments (e.g., `logger.info("connecting with -u user,%s", password)`)
- Two new regression tests added: `test_config_redacts_webhook_secret` and `test_redacts_password_in_format_args`
- All 19 targeted tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Redact webhook_secret in config API and fix log redaction to use getMessage()** - `9048377` (fix)

**Plan metadata:** (committed with SUMMARY.md)

## Files Created/Modified
- `src/python/web/serialize/serialize_config.py` - Added `"general": ["webhook_secret"]` to `_SENSITIVE_FIELDS`
- `src/python/web/serialize/serialize_log_record.py` - Changed `record.msg` to `record.getMessage()` at line 58
- `src/python/tests/unittests/test_web/test_serialize/test_serialize_config.py` - Added `test_config_redacts_webhook_secret`
- `src/python/tests/unittests/test_web/test_handler/test_stream_log.py` - Added `test_redacts_password_in_format_args`

## Decisions Made
- webhook_secret redacted at serialization layer, not storage — consistent with existing pattern; internal code still reads the real value for HMAC-SHA256 verification
- getMessage() used over record.msg so that passwords supplied as format arguments are interpolated before the regex scrubber runs, closing the gap where `record.msg = "connecting with %s"` would pass through unredacted

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - `test_serialize_model.py` has a pre-existing `ModuleNotFoundError: No module named 'pytz'` unrelated to our changes; only the two directly modified test files were run, and all 19 tests in those files pass.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both code review findings (CR-01, CR-03) fully resolved with tests
- Config API is now safe against leaking webhook_secret to frontend clients
- Log SSE stream redaction is now robust against format-argument credential injection

---
*Phase: 46-code-review-fixes*
*Completed: 2026-02-24*
