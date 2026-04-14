---
phase: 40-credential-endpoint-security
plan: 01
subsystem: api
tags: [security, serialization, sse, credential-redaction, lftp]

# Dependency graph
requires: []
provides:
  - Config GET API never returns remote_password, sonarr_api_key, or radarr_api_key values
  - SSE log stream scrubs LFTP -u user,password patterns before reaching browser
  - _SENSITIVE_FIELDS constant centralizes which config fields require redaction
  - _redact_sensitive() utility handles both LFTP -u and generic password= patterns
affects:
  - config-handler
  - lftp-verbose-logging
  - frontend-settings-ui

# Tech tracking
tech-stack:
  added: [re (regex, stdlib)]
  patterns:
    - Redact-before-serialize: sensitive fields replaced with **REDACTED** string after lowercasing but before json.dumps
    - Scrub-before-emit: log record messages sanitized at SSE serialization layer rather than at log source

key-files:
  created: []
  modified:
    - src/python/web/serialize/serialize_config.py
    - src/python/web/serialize/serialize_log_record.py
    - src/python/tests/unittests/test_web/test_serialize/test_serialize_config.py
    - src/python/tests/unittests/test_web/test_handler/test_stream_log.py

key-decisions:
  - "Redact at serialization layer (not config storage) so internal code can still read real values; only the HTTP response is sanitized"
  - "Preserve field keys in JSON response (**REDACTED** value) so frontend knows fields exist and can display edit controls"
  - "Scrub in SerializeLogRecord rather than at log source to cover all code paths including cached history replayed on stream connect"

patterns-established:
  - "_SENSITIVE_FIELDS dict pattern: section->field mapping for centralised redaction maintenance"
  - "_redact_sensitive() static method pattern: pure function on str, easy to unit test and reuse"

requirements-completed:
  - SEC-04
  - SEC-05

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 40 Plan 01: Credential Endpoint Security Summary

**Credential leakage closed on two vectors: config GET API redacts remote_password/sonarr_api_key/radarr_api_key with `**REDACTED**`, and SSE log stream strips LFTP `-u user,password` patterns before reaching the browser**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T01:18:06Z
- **Completed:** 2026-02-24T01:20:29Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Config GET response now always returns `**REDACTED**` for `remote_password`, `sonarr_api_key`, and `radarr_api_key` while preserving all other fields
- SSE log stream scrubs LFTP `-u username,password` and generic `password=value` patterns before emitting to browser clients
- Exception tracebacks in log stream are also scrubbed (covers the case where a password appears in a caught exception message)
- 8 new tests (4 per task) proving both redaction paths

## Task Commits

Each task was committed atomically:

1. **Task 1: Redact sensitive fields from config GET response** - `0a4a410` (feat)
2. **Task 2: Scrub passwords from SSE log stream records** - `b9a3220` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `src/python/web/serialize/serialize_config.py` - Added `_SENSITIVE_FIELDS` constant and redaction loop before `json.dumps`
- `src/python/web/serialize/serialize_log_record.py` - Added `_redact_sensitive()` static method using regex; applied to `record.msg` and `exc_text`
- `src/python/tests/unittests/test_web/test_serialize/test_serialize_config.py` - Added 4 redaction tests
- `src/python/tests/unittests/test_web/test_handler/test_stream_log.py` - Added `TestSerializeLogRecordRedaction` class with 4 tests

## Decisions Made

- Redaction happens at the serialization layer rather than at the config storage layer. This means internal Python code can still read actual values (needed by LFTP to connect); only the HTTP/SSE output path sanitizes them.
- Field keys are preserved in the response with value `**REDACTED**` so the UI can still render edit fields — otherwise the frontend would not know these fields exist.
- Log stream scrubbing is applied in `SerializeLogRecord.record()` rather than in `LogStreamHandler` or at the LFTP log source, ensuring cached history replayed to new SSE clients is also scrubbed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both credential leakage vectors (SEC-04, SEC-05) closed
- All 9 serialize_config tests pass; all 8 stream_log tests pass; all 31 config_handler regression tests pass
- Ready for remaining Phase 40 plans

## Self-Check: PASSED

- FOUND: src/python/web/serialize/serialize_config.py
- FOUND: src/python/web/serialize/serialize_log_record.py
- FOUND: src/python/tests/unittests/test_web/test_serialize/test_serialize_config.py
- FOUND: src/python/tests/unittests/test_web/test_handler/test_stream_log.py
- FOUND: .planning/phases/40-credential-endpoint-security/40-01-SUMMARY.md
- FOUND commit: 0a4a410
- FOUND commit: b9a3220

---
*Phase: 40-credential-endpoint-security*
*Completed: 2026-02-24*
