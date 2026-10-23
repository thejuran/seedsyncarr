---
phase: 122-safety-acceptance-and-logging-fixes
plan: 14
subsystem: api
tags: [gap-closure, tdd, security, secret-leak, cr-01, wr-01, logging, rate-limit]
gap_closure: true

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes
    plan: 02
    provides: context.logger.getChild(ClassName) pattern for web handlers; the LOG-01 wiring that made ConfigHandler's and StatusHandler's loggers reachable
provides:
  - "ConfigHandler._test_arr_connection strips and validates the stored Arr API key before it ever reaches requests, so requests cannot raise InvalidHeader (which embeds the raw key) for a stored key"
  - "ConfigHandler's unexpected-error path logs only the exception type, never the message or a traceback, closing the CR-01 secret-leak path"
  - "rate_limit() requires a keyword-only logger argument (no default, no module fallback), so a future call site cannot silently log to a detached logger"
  - "StatusHandler logs under seedsyncarr.StatusHandler and passes that logger to rate_limit, closing WR-01"
affects: [122-16, 122-17]

# Tech tracking
tech-stack:
  added: []
  patterns: ["printable-ASCII-without-space fullmatch gate before building an outbound auth header", "keyword-only required logger= parameter instead of an optional/defaulted one, to make a detached-logger regression impossible to reintroduce silently"]

key-files:
  created: []
  modified:
    - src/python/web/handler/config.py
    - src/python/web/rate_limit.py
    - src/python/web/handler/status.py
    - src/python/web/web_app_builder.py
    - src/python/tests/unittests/test_web/test_web_app_builder_logging.py
    - src/python/tests/unittests/test_web/test_rate_limit.py
    - src/python/tests/unittests/test_web/test_handler/test_status_handler.py
    - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
    - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py

key-decisions:
  - "Key validation rule is printable ASCII without space (0x21-0x7E), not alphanumeric-only: looser than real Sonarr/Radarr's 32-hex-char keys so a proxy-style key with hyphens/underscores still works, but strict enough that requests/http.client can never raise InvalidHeader or a latin-1 encode error for an accepted key"
  - "No new redaction pattern added to SerializeLogRecord._redact_sensitive — a bare key has no recognisable shape, so the fix is to never log exception text at this boundary rather than try to pattern-match a key after the fact"
  - "rate_limit's logger parameter made required and keyword-only (not just given a non-None default) specifically so a future call site that forgets logger= fails at import/registration time with TypeError, not silently at runtime"
  - "No live CR-01 check run on the NAS this plan: reproducing it live would require writing an invalid key into the sandbox config and restoring the real key afterward, which means reading the real key — that conflicts with the absolute 'never print API keys' rule and the owner's standing decision not to touch the sandbox Sonarr key. The unit regression exercises a real requests.exceptions.InvalidHeader through the real ConfigHandler and both real output formatters (plain Formatter and SerializeLogRecord), which is the same code path the phase verifier reproduced"

requirements-completed: []

# Metrics
duration: ~5m
completed: 2026-10-23
---

# Phase 122 Plan 14: API-Key Leak and Status Rate-Limit Logger Gap Closure (CR-01, WR-01) Summary

**A stored Sonarr/Radarr API key is now stripped and character-validated before it ever reaches `requests`, so a real `requests.exceptions.InvalidHeader` can no longer embed the key in a logged traceback; `rate_limit()`'s logger is now a required keyword-only argument, closing the detached-logger gap on `/server/status`.**

## Performance

- **Duration:** ~5 minutes (start 2026-10-23T22:49:30Z, end 2026-10-23T22:54:27Z)
- **Tasks:** 3 (RED, GREEN CR-01, GREEN WR-01) — all completed
- **Files modified:** 9 (5 test, 4 source)

## Accomplishments

- `ConfigHandler._test_arr_connection` strips the stored API key and rejects it with `"{Service} API key contains invalid characters"` before any outbound request if it contains anything other than printable ASCII without space (`[\x21-\x7e]+` fullmatch). A key that would make `requests` raise `InvalidHeader` (embedded CR/LF, other whitespace, control or non-ASCII characters) is now rejected before `requests` ever sees it.
- The `except Exception` branch in `_test_arr_connection` now logs `self.logger.error("Unexpected error testing %s connection (%s)", service_name, type(e).__name__)` with no `exc_info` — never the exception message or a traceback — because `requests`/`urllib3` can embed header or URL values in other exception types too, not just `InvalidHeader`.
- `rate_limit()`'s signature is now `rate_limit(max_requests: int, window_seconds: float, *, logger: logging.Logger)`. The module-level fallback logger and the `globals()["logger"]` lookup are gone; an explicit `logger=None` raises `TypeError("rate_limit requires a logger")`, and a missing or positional `logger` argument raises `TypeError` at the call site (keyword-only, no default).
- `StatusHandler` now takes `(status, context)`, sets `self.logger = context.logger.getChild("StatusHandler")`, and passes `logger=self.logger` to `rate_limit`, so the `/server/status` rate-limit warning now reaches the persisted app log and the UI log stream under `seedsyncarr.StatusHandler` instead of the detached `web.rate_limit` module logger.
- `WebAppBuilder` constructs `StatusHandler(context.status, context)`.

## Task Commits

1. **Task 1 (RED): CR-01/WR-01 regressions, adapted call sites** — `56ffced` (test)
2. **Task 2 (GREEN, CR-01): strip and validate the key; log exception type only** — `b4081ac` (fix)
3. **Task 3 (GREEN, WR-01): required rate_limit logger; StatusHandler on the app logger; D-14 re-audit** — `5400cc0` (fix)

_TDD plan: RED (`test(122-14)`) precedes both GREEN commits, confirmed by `git log -3 --format=%s`:_
```
fix(122-14): route status rate-limit warning to app logger; make rate_limit logger required (WR-01)
fix(122-14): never log Arr API key from Test Connection; validate key before request (CR-01)
test(122-14): reproduce API key leak via InvalidHeader and detached status rate-limit logger (CR-01, WR-01)
```

## RED Evidence (Task 1, before any fix)

Command: `cd src/python && poetry run pytest tests/unittests/test_web -p no:cacheprovider -q`

Result: **10 failed, 345 passed, 2 warnings** — every failure is one of the intended RED tests, failing for the intended reason:

| Test | Failure reason on pre-fix code |
|---|---|
| `test_web_app_builder_logging.py::test_config_key_with_newline_never_reaches_requests_or_log` | On current code, `requests` raises a real `InvalidHeader` during header prep for the CR/LF key, `logger.exception` logs the key, assertions fail |
| `test_web_app_builder_logging.py::test_config_unexpected_error_with_real_invalid_header_logs_type_only` | Message is `"Unexpected error testing Sonarr connection"` (no `(InvalidHeader)` suffix) and `exc_info` is set (the traceback), not `None` |
| `test_web_app_builder_logging.py::test_config_unexpected_error_logged_without_api_key` | Same: message lacks the `(RuntimeError)` suffix, `exc_info` is not `None` |
| `test_config_handler.py::test_config_key_whitespace_stripped_before_header` | `mock_requests.get` is called with the unstripped key `"  testapikey123\t"`, not `"testapikey123"` |
| `test_web_app_builder_logging.py::test_status_rate_limit_warning_under_app_logger` | `AssertionError: no logs of level WARNING or higher triggered on seedsyncarr` — captured log shows `WARNING web.rate_limit:rate_limit.py:44 Rate limit exceeded for __handle_get_status` (detached module logger) |
| `test_rate_limit.py::test_rate_limit_requires_logger` | `AssertionError: TypeError not raised` — `rate_limit(3, 60.0)` succeeds on current code because `logger` defaults to `None` |
| `test_status_handler.py::TestStatusHandler::test_get_status_returns_200` | `TypeError: StatusHandler.__init__() takes 2 positional arguments but 3 were given` |
| `test_status_handler.py::TestStatusHandler::test_get_status_body_is_serialized` | Same constructor `TypeError` |
| `test_status_handler.py::TestStatusHandler::test_get_status_calls_serializer_with_status` | Same constructor `TypeError` |
| `test_status_handler.py::TestStatusHandlerRateLimit::test_status_rate_limited_at_60_per_60s` | Same constructor `TypeError` |

All ten failures are exactly the set named in the plan's acceptance criteria (the four named CR-01/WR-01 tests, `test_rate_limit_requires_logger`, and every other FAILED line in `test_status_handler.py`). The twelve pre-existing bare `rate_limit(...)` call sites across `test_rate_limit.py`, `test_config_handler.py` and `test_controller_handler.py` were adapted to pass `logger=` in the same commit and all continued to pass.

## GREEN Evidence

**Task 2 (CR-01):** `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_builder_logging.py tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_sonarr5 -p no:cacheprovider -q` → **1 failed (`test_status_rate_limit_warning_under_app_logger`, WR-01, expected — fixed in Task 3), 109 passed, 58 subtests passed.** All four CR-01 tests pass; every `test_config_handler.py` and `test_sonarr5` test passes.

Acceptance-criteria greps on `config.py` (all match):
- `grep -c "logger.exception" web/handler/config.py` → `0`
- `grep -c "type(e).__name__" web/handler/config.py` → `1`
- `grep -c "API key contains invalid characters" web/handler/config.py` → `1`
- `grep -c "api_key = api_key.strip()" web/handler/config.py` → `1`
- `git show --stat --format= HEAD` → `src/python/web/handler/config.py` only

**Task 3 (WR-01):** `cd src/python && poetry run pytest tests/unittests/test_web tests/unittests/test_sonarr5 -p no:cacheprovider -q` → **404 passed, 58 subtests passed, 0 failed, 0 errors.** `grep -rn "logger.exception\|exc_info" web/handler web/rate_limit.py controller/arr_queue.py | wc -l` → `0`.

Acceptance-criteria greps on the three Task 3 files (all match):
- `grep -c "globals()" web/rate_limit.py` → `0`
- `grep -c "getLogger" web/rate_limit.py` → `0`
- `grep -c "requires a logger" web/rate_limit.py` → `1`
- `grep -rn "rate_limit(max_requests" web/handler | grep -v -c "logger="` → `0`
- `grep -c "StatusHandler(context.status, context)" web/web_app_builder.py` → `1`
- `grep -c "getChild(\"StatusHandler\")" web/handler/status.py` → `1`

Whole-tree lint: `cd src/python && poetry run ruff check .` → **All checks passed!** (run after Task 3, covers all nine modified files).

Post-commit deletion check on all three commits (`56ffced`, `b4081ac`, `5400cc0`): `git diff --diff-filter=D --name-only <commit>~1 <commit>` is empty for each — no unexpected file deletions.

## D-14 Re-audit (Task 3)

`grep -n "logger\." src/python/web/handler/webhook.py src/python/web/handler/controller.py src/python/web/handler/config.py src/python/web/handler/status.py src/python/web/rate_limit.py src/python/controller/arr_queue.py`:

```
web/handler/status.py:11:        self.logger = context.logger.getChild("StatusHandler")
web/handler/controller.py:56:        self.logger = context.logger.getChild("ControllerHandler")
web/handler/controller.py:194:            self.logger.warning("Rejected path traversal attempt for: %s", repr(file_name))
web/handler/controller.py:352:        self.logger.info("Bulk {} operation started for {} file(s)".format(action_name, file_count))
web/handler/controller.py:386:        self.logger.debug("Bulk {}: queued {} commands in {:.3f}s".format(
web/handler/controller.py:428:            self.logger.warning(
web/handler/controller.py:434:            self.logger.info(
web/handler/config.py:23:        self.logger = context.logger.getChild("ConfigHandler")
web/handler/config.py:213:            self.logger.error(
web/handler/webhook.py:25:        self.logger = context.logger.getChild("WebhookHandler")
web/handler/webhook.py:54:                self.logger.warning(
web/handler/webhook.py:96:            self.logger.warning("Webhook request missing X-Webhook-Signature header")
web/handler/webhook.py:101:            self.logger.warning("Webhook request has invalid HMAC signature")
web/handler/webhook.py:140:            self.logger.info("{} webhook test event received".format(source))
web/handler/webhook.py:147:            self.logger.info("{} webhook ignored event type: '{}'".format(
web/handler/webhook.py:159:            self.logger.warning(
web/rate_limit.py:49:                    logger.warning("Rate limit exceeded for %s", func.__name__)
controller/arr_queue.py:158:        self.logger = context.logger.getChild("ArrQueueClient")
controller/arr_queue.py:193:            self.logger.warning("%s queue check skipped: URL must use http or https", target.label)
controller/arr_queue.py:198:            self.logger.debug("%s queue fetch from a previous attempt is still in flight; "
controller/arr_queue.py:208:            self.logger.debug("%s queue fetch: discarding stale result", target.label)
controller/arr_queue.py:229:            self.logger.debug("%s discarded late queue result for an abandoned fetch (id %d)",
controller/arr_queue.py:239:            self.logger.warning("%s queue fetch exceeded the %.0f s deadline; treating as unavailable",
controller/arr_queue.py:252:        self.logger.warning("%s queue fetch ended without a result; treating as unavailable", f.label)
controller/arr_queue.py:265:        self.logger.debug("%s queue fetch abandoned (id %d)", f.label, f.fetch_id)
controller/arr_queue.py:287:            self.logger.warning("%s queue check failed: %s", target.label, type(e).__name__)
controller/arr_queue.py:289:            self.logger.warning("%s queue check failed: %s", target.label, type(e).__name__)
controller/arr_queue.py:296:            self.logger.warning("%s queue fetch exceeded the %.0f s deadline; treating as unavailable",
controller/arr_queue.py:306:            self.logger.warning("%s queue check failed: HTTP %d", target.label, response.status_code)
controller/arr_queue.py:313:                self.logger.warning("%s queue response exceeded %d bytes; treating as unavailable",
controller/arr_queue.py:322:            self.logger.warning("%s queue check failed: %s", target.label, type(e).__name__)
controller/arr_queue.py:325:            self.logger.warning("%s queue check failed: unexpected payload type %s",
controller/arr_queue.py:337:            self.logger.warning("%s queue snapshot rejected: unparseable record", target.label)
controller/arr_queue.py:342:                self.logger.debug("%s queue record has defect %s for '%s'", target.label, record.defect,
```

`grep -rn "logger.exception\|exc_info" src/python/web/handler src/python/web/rate_limit.py src/python/controller/arr_queue.py` → **empty (0 matches)**.

Per-line verdict (every line above is constant text, a counted/sanitized value, or an exception's type name — none can carry an API key, webhook secret, HMAC signature, Authorization/X-Api-Key header value, or webhook body):

| File:Line | Can contain |
|---|---|
| `status.py:11`, `controller.py:56`, `config.py:23`, `webhook.py:25`, `arr_queue.py:158` | Nothing (constructor assignment, not a log call) |
| `controller.py:194` | `repr()` of a rejected file/path name (user-supplied path, not a credential) |
| `controller.py:352`, `:386`, `:428`, `:434` | A literal action name from a fixed set, integer file/success/failure counts, and float timings/rates |
| `config.py:213` | A literal service name (`"Sonarr"`/`"Radarr"`) and `type(e).__name__` (an exception class name, e.g. `InvalidHeader`) — the fix for CR-01: never the exception message, never `exc_info` |
| `webhook.py:54`, `:96`, `:101` | Constant text only; `:96`/`:101` name the header/signature check by type, never log the header or signature value |
| `webhook.py:140` | A literal source constant (`"Sonarr"`/`"Radarr"`) |
| `webhook.py:147` | A literal source constant and `sanitize_log_value(str(event_type))` (a short enum-like webhook event type string) |
| `webhook.py:159` | A literal source constant and `sanitize_log_value(release_title)` (a release/episode title, not a credential) |
| `rate_limit.py:49` | `func.__name__` — the wrapped handler's Python function name, not user input |
| `arr_queue.py:193`, `:239`, `:252`, `:296`, `:306`, `:313`, `:325`, `:337` | A service label (`target.label`/`f.label`, e.g. `"Sonarr"`), plus integers/floats (deadlines, byte counts, HTTP status codes) or a Python type name |
| `arr_queue.py:198`, `:208`, `:229`, `:265` | A service label and integer fetch IDs (DEBUG, internal bookkeeping) |
| `arr_queue.py:287`, `:289`, `:322` | A service label and `type(e).__name__` only — the exception message is never logged here either |
| `arr_queue.py:342` | A service label, `record.defect` (an internal validity-check name) and `sanitize_log_value(record.basename or "")` (a sanitized filename) |

**Conclusion: no log call site in the D-14 audit scope can expose a secret.** The only change from the 122-02 D-14 table is `config.py:213` (now `logger.error` with `type(e).__name__` only, no `exc_info`, replacing the leaking `logger.exception`) and the addition of `status.py`/`rate_limit.py`'s now-wired warning, which carries only `func.__name__`.

## No Live CR-01 Check (by design)

Per the plan's `<design_choices>`: a live CR-01 check on the NAS would require writing an invalid key into the sandbox config and then restoring the real key afterward, which means reading the real key at some point — that conflicts with the absolute "never print API keys" rule and the owner's standing decision not to touch the sandbox Sonarr key. The unit regression (`test_config_key_with_newline_never_reaches_requests_or_log` and `test_config_unexpected_error_with_real_invalid_header_logs_type_only`) exercises a real `requests.exceptions.InvalidHeader` through the real `ConfigHandler._test_arr_connection` method and both real output formatters (`logging.Formatter().format(...)` for the RotatingFileHandler path, `SerializeLogRecord().record(...)` for the SSE UI log path) — the same code path the phase verifier (122-VERIFICATION.md) independently reproduced to find CR-01 in the first place. LOG-01 is re-confirmed live in 122-16 and SAFE-01/LOG-01 close in 122-17; `requirements-completed` is intentionally empty here.

## Decisions Made

- Followed the plan's design choice exactly: `_API_KEY_CHARS = re.compile(r"[\x21-\x7e]+")`, fullmatch after `.strip()`, placed after the existing empty/whitespace-only check and before the SSRF `_validate_url` call and any outbound request.
- `rate_limit`'s `logger` parameter made keyword-only (`*, logger: logging.Logger`) with no default, rather than merely removing the `Optional` type hint, so Python itself raises `TypeError` for a missing or positional logger before the function body runs; the explicit `if logger is None: raise TypeError(...)` inside the body only covers the `logger=None` case.

## Deviations from Plan

None — plan executed exactly as written. The RED commit's failure set matched the plan's acceptance criteria exactly (the four named CR-01/WR-01 tests, `test_rate_limit_requires_logger`, and every other failure confined to `test_status_handler.py`'s constructor `TypeError`s), and every acceptance-criteria grep in Tasks 2 and 3 matched on the first run with no rework.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CR-01 and WR-01 are closed in source and covered by regressions that fail before and pass after the fix.
- Nothing is pushed by this plan (122-15 pushes to PR #134 per the phase's one-PR-per-phase policy).
- LOG-01 is re-confirmed live and SAFE-01/LOG-01 are formally closed later in the gap-closure sequence (122-16/122-17), consistent with `requirements-completed: []` here.

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-23*

## Self-Check: PASSED

- All 9 modified files found on disk (verified below).
- `122-14-SUMMARY.md` found on disk.
- All three task commits (`56ffced`, `b4081ac`, `5400cc0`) found in `git log --oneline --all`.
