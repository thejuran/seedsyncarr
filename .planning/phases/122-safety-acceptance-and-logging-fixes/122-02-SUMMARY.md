---
phase: 122-safety-acceptance-and-logging-fixes
plan: 02
subsystem: api
tags: [logging, web-handler, tdd, regression, secrets-review]

# Dependency graph
requires:
  - phase: 120-sonarr-5-compatibility
    provides: existing web handler test suite and ServerHandler's context.logger.getChild(...) pattern
provides:
  - "Webhook, controller and config handlers (and rate_limit) now log under the app's seedsyncarr logger tree instead of a detached module logger"
  - "A regression (test_web_app_builder_logging.py) that fails before and passes after the fix, proving the webhook Test-event INFO line reaches the app log"
  - "D-14 secret-safety review table covering every log call site in the four touched modules"
affects: [122-03, SAFE-01 evidence capture]

# Tech tracking
tech-stack:
  added: []
  patterns: ["context.logger.getChild(ClassName) for web handlers (already established by ServerHandler, now applied to WebhookHandler/ControllerHandler/ConfigHandler)", "optional logger= kwarg on a shared decorator, falling back to a module default"]

key-files:
  created:
    - src/python/tests/unittests/test_web/test_web_app_builder_logging.py
  modified:
    - src/python/web/handler/webhook.py
    - src/python/web/handler/controller.py
    - src/python/web/handler/config.py
    - src/python/web/rate_limit.py
    - src/python/web/web_app_builder.py
    - src/python/tests/unittests/test_web/test_rate_limit.py
    - src/python/tests/unittests/test_web/test_webhook_handler.py
    - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
    - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py
    - src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py

key-decisions:
  - "WebhookHandler/ConfigHandler/ControllerHandler take context: Context (required, never defaulted) and set self.logger = context.logger.getChild(ClassName) as the first __init__ statement, copying ServerHandler's existing pattern exactly"
  - "rate_limit() gained an optional logger: Optional[logging.Logger] = None third parameter, resolved once per decorator call and falling back to the module logger via globals()[\"logger\"], so status.py's unmodified call site keeps using the old module logger unchanged"

requirements-completed: [LOG-01]

# Metrics
duration: ~5h28m (dominated by a hung full-suite pytest run outside the critical path — see Deviations/Issues)
completed: 2026-10-22
---

# Phase 122 Plan 02: Web Handler Logger-Tree Fix (LOG-01) Summary

**Webhook/controller/config handlers and rate_limit now log through `context.logger.getChild(ClassName)` under the app's `seedsyncarr` logger, proven by a regression that failed before the fix and passes after it.**

## Performance

- **Duration:** ~5h28m wall clock; actual coding/verification work was ~15 minutes (RED+GREEN) plus a D-14 review; the remainder was an unplanned hang in a full-suite pytest invocation that the orchestrator killed (see Deviations)
- **Started:** 2026-10-22T13:49:17Z (phase execution start commit `ef31c87`)
- **Completed:** 2026-10-22T19:17:34Z
- **Tasks:** 3 (RED, GREEN, D-14 review) — all completed
- **Files modified:** 10 (1 created, 9 modified)

## Accomplishments
- `WebhookHandler`, `ControllerHandler`, `ConfigHandler` now construct with the app `Context` and log through `self.logger = context.logger.getChild("<ClassName>")`, the exact pattern `ServerHandler` already used — their previous `logging.getLogger(__name__)` module loggers (`web.handler.webhook`, etc., with no ancestor relationship to `seedsyncarr`) are gone.
- `rate_limit()` gained an optional `logger` kwarg; the three in-scope handlers pass `logger=self.logger` at their six call sites, so "Rate limit exceeded" now also reaches the app log for those routes. `status.py`'s unmodified call site and all pre-existing `rate_limit(...)` calls without a `logger=` kwarg are untouched and still pass.
- A new builder-level regression file (`test_web_app_builder_logging.py`) proves, via `unittest.assertLogs("seedsyncarr", ...)` against a real `logging.getLogger("seedsyncarr")`, that: a Sonarr/Radarr webhook Test event produces exactly one INFO record `"<Source> webhook test event received"` on logger `seedsyncarr.WebhookHandler`; a path-traversal rejection logs a WARNING on `seedsyncarr.ControllerHandler`; and a Test Connection `logger.exception` logs an ERROR on `seedsyncarr.ConfigHandler` without ever surfacing a test API key in the formatted record (including the traceback).
- D-14 secret-safety review: all 13 log call sites across the four modules were enumerated and reviewed; none interpolates a secret, token, auth header, or raw webhook body.

## Task Commits

1. **Task 1: RED — builder-level regressions on the `seedsyncarr` logger tree plus a rate_limit logger-kwarg test** - `4bd0a28` (test)
2. **Task 2: GREEN — attach the three handlers and rate_limit to the app logger; update WebAppBuilder and existing test constructors** - `220a2ac` (fix)
3. **Task 3: D-14 secret review of every newly visible line, plus full unit suite baseline comparison** - no code commit (review-only task; findings recorded below); this docs commit records it

_TDD plan: RED (`test(122-02)`) precedes GREEN (`fix(122-02)`), confirmed by `git log --format=%s -2`._

## RED Evidence (Task 1, before the fix)

Command: `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_builder_logging.py tests/unittests/test_web/test_rate_limit.py -p no:cacheprovider -q`

Result: **5 failed, 15 passed** (all 15 pre-existing `test_rate_limit.py` tests still passed; the 5 new tests failed for the expected reasons, not setup errors):

- `test_webhook_test_event_logged_under_app_logger` → `AssertionError: no logs of level INFO or higher triggered on seedsyncarr`
- `test_radarr_webhook_test_event_logged_under_app_logger` → `AssertionError: no logs of level INFO or higher triggered on seedsyncarr`
- `test_controller_traversal_warning_under_app_logger` → `AssertionError: no logs of level WARNING or higher triggered on seedsyncarr` (captured log call showed the real line going to `web.handler.controller`, not `seedsyncarr`)
- `test_config_unexpected_error_logged_without_api_key` → `AssertionError: no logs of level ERROR or higher triggered on seedsyncarr`
- `test_rate_limit_uses_supplied_logger` → `TypeError: rate_limit() got an unexpected keyword argument 'logger'`

This is the fail-before evidence: the webhook/controller/config lines were reaching a detached module logger (visible in pytest's "Captured log call" output under names like `web.handler.controller`), never the `seedsyncarr` logger tree that owns the app's real handlers.

## GREEN Evidence (Task 2, after the fix)

Command: `cd src/python && poetry run pytest tests/unittests/test_web tests/unittests/test_sonarr5/test_sonarr5_system_status.py -p no:cacheprovider -q && cd ../.. && ruff check src/python/`

Result: **355 passed** (includes all 5 Task 1 regressions now green, every pre-existing test in `test_webhook_handler.py`, `test_config_handler.py`, `test_controller_handler.py`, `test_rate_limit.py`, `test_server_handler.py`, `test_sonarr5_system_status.py`, and the rest of `tests/unittests/test_web`). `ruff check src/python/` → **All checks passed!**

Acceptance-criteria greps (all match the plan exactly):
- `grep -n "logging.getLogger(__name__)" web/handler/{webhook,controller,config}.py` → empty
- `grep -c "context.logger.getChild(" web/handler/{webhook,controller,config}.py` → 1 for each file
- bare `logger.` calls (excluding comments) in those three files → 0
- `grep -c "logger=self.logger" webhook.py config.py controller.py` → 2, 3, 1 respectively
- `git diff HEAD~1 -- web/handler/status.py` → empty (untouched, as required — it has no logger of its own and is out of D-13's scope)
- `grep -c "WebhookHandler(webhook_manager, context.config, context)" web_app_builder.py` → 1
- `git log --format=%s -2` → `fix(122-02)` on top of `test(122-02)`

Post-commit deletion check on both commits: no unexpected file deletions.

## Final Constructor / Function Signatures

```python
WebhookHandler(webhook_manager: WebhookManager, config: Config, context: Context)
ConfigHandler(config: Config, context: Context)
ControllerHandler(controller: Controller, context: Context, local_path: str = "")
rate_limit(max_requests: int, window_seconds: float, logger: Optional[logging.Logger] = None)
```

`context` is required (never defaulted) on all three handlers, so a handler can never silently fall back to a detached logger.

## D-14 Secret-Safety Review (Task 3)

Every `self.logger.`/`_logger.` call site in the four modules, grep-verified complete (`grep -c` against each file: webhook.py 6, controller.py 5, config.py 1, rate_limit.py 1 = 13 total, matching 100% of the call-site inventory named in 122-PATTERNS.md/122-RESEARCH.md):

| File:Line | Level | Message template | Interpolated value(s) | Source of value | Secret risk |
|---|---|---|---|---|---|
| `webhook.py:54` | WARNING | "Webhook request rejected: webhook_require_secret is enabled but no webhook_secret is configured." | none | — | None — no values interpolated |
| `webhook.py:96` | WARNING | "Webhook request missing X-Webhook-Signature header" | none | — | None — names the header only, never its value |
| `webhook.py:101` | WARNING | "Webhook request has invalid HMAC signature" | none | — | None — never logs the signature or the secret |
| `webhook.py:140` | INFO | "{} webhook test event received" | `source` | literal `"Sonarr"`/`"Radarr"` constant | None |
| `webhook.py:147` | INFO | "{} webhook ignored event type: '{}'" | `source`, `event_type` | literal constant; `sanitize_log_value(str(event_type))` | None — short enum-like string, already sanitized (CWE-117) |
| `webhook.py:159` | WARNING | "{} webhook Download event has no source file path; NOT marking an import (release.releaseTitle: '{}')" | `source`, `release_title` | literal constant; `sanitize_log_value(release_title)` | None — a release/episode title, not a credential; already sanitized |
| `controller.py:194` | WARNING | "Rejected path traversal attempt for: %s" | `repr(file_name)` | user-supplied file name | None — file name only, no credential. Pre-existing use of `repr()` instead of `sanitize_log_value` is inconsistent with the rest of the codebase; noted per 122-PATTERNS.md as out of this phase's scope to change |
| `controller.py:352` | INFO | "Bulk {} operation started for {} file(s)" | `action_name`, `file_count` | literal action name from a fixed set; integer count | None |
| `controller.py:386` | DEBUG | "Bulk {}: queued {} commands in {:.3f}s" | `action_name`, `file_count`, duration | literal; count; timing | None |
| `controller.py:428` | WARNING | "Bulk {} completed: {}/{} succeeded, {} failed, {} timed out in {:.3f}s" | `action_name`, counts, duration | literal; counts; timing | None |
| `controller.py:434` | INFO | "Bulk {} completed: {}/{} succeeded in {:.3f}s ({:.1f} files/sec)" | `action_name`, counts, duration, rate | literal; counts; timing | None |
| `config.py:196` | ERROR (`logger.exception`) | "Unexpected error testing %s connection" | `service_name` | literal `"Sonarr"`/`"Radarr"` constant | None — `api_key` travels only via the `X-Api-Key` HTTP header, never the URL or an f-string; Python's default traceback formatter prints frames/lines, not local variable values. Pinned by `test_config_unexpected_error_logged_without_api_key`, which forces this exact path with a literal test key (`test-api-key-122-PIN`) and asserts it is absent from the fully formatted record (`logging.Formatter().format(record)`, including the traceback text) |
| `rate_limit.py:44` | WARNING | "Rate limit exceeded for %s" | `func.__name__` | the wrapped handler's Python function name (e.g. a name-mangled private method name) | None — not user input |

**Conclusion: no secret-leak risk found in any of the four modules.** No row required a fix; the review and the pinning test above satisfy D-14.

## Full Unit Suite Baseline Comparison — Not Completed (see Deviations)

The plan's Task 3 verification also calls for running the full `tests/unittests` suite at HEAD and at the plan's base commit (`ef31c87`) and confirming the failure sets are identical apart from the 5 new passing tests. Both runs were started but **hung** in this sandboxed environment (CPU-pegged for 5h20m / ~5 CPU-hours each with no progress past ~40% of collected tests) and were killed by the orchestrator rather than left running further. See Deviations below for the full account and the deferred follow-up.

## Decisions Made

- Followed the plan's Claude's-Discretion signature choice (`WebhookHandler(webhook_manager, config, context)`, `ConfigHandler(config, context)`, `ControllerHandler(controller, context, local_path="")`) exactly as specified in the plan's interfaces block — no deviation.
- `rate_limit()`'s `logger` parameter resolves via `globals()["logger"]` rather than a differently-named module attribute, so the parameter can be named `logger` (shadowing the module-level `logger` binding inside the function body) while still falling back to the original module logger by explicit global lookup — matches 122-PATTERNS.md's recommended shape exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test's own mock for `requests.ConnectionError`/`requests.Timeout` needed to use the real exception classes**
- **Found during:** Task 1 (RED), while first running `test_config_unexpected_error_logged_without_api_key`
- **Issue:** `@patch('web.handler.config.requests')` replaces the whole `requests` module with a `MagicMock`, so `requests.ConnectionError`/`requests.Timeout` inside `config.py`'s `except` clauses became `MagicMock` attributes rather than real exception classes, and `except requests.ConnectionError:` raised `TypeError: catching classes that do not inherit from BaseException is not allowed` instead of the intended `AssertionError` RED signal.
- **Fix:** Set `mock_requests.ConnectionError = requests.ConnectionError` and `mock_requests.Timeout = requests.Timeout` on the mock before raising `RuntimeError("boom")`, mirroring the exact pattern already used throughout `test_config_handler.py`.
- **Files modified:** `src/python/tests/unittests/test_web/test_web_app_builder_logging.py` (test-only, part of the RED commit)
- **Verification:** Re-ran the RED suite; all 5 new tests then failed for the intended reason (4× `AssertionError: no logs ... triggered on seedsyncarr`, 1× `TypeError: unexpected keyword argument 'logger'`).
- **Committed in:** `4bd0a28` (Task 1 RED commit)

---

**Total deviations:** 1 auto-fixed (1 bug, test-only, fixed before the RED commit was made — no impact on shipped behavior).
**Impact on plan:** None on production code; the fix only corrected my own new test's mocking so the RED evidence was for the right reason.

## Issues Encountered

**Full local `tests/unittests` suite hangs in this sandboxed macOS environment; both the HEAD run and a base-commit (`ef31c87`) comparison run were killed by the orchestrator after ~5h20m (~5 CPU-hours each) with no forward progress past roughly 40% of the 1802 collected tests.** This environment's ad-hoc `pytest` invocations do not actually enforce the project's configured `timeout`/`timeout_func_only` pytest-timeout options (`PytestConfigWarning: Unknown config option: timeout` appears on every run, confirming the plugin isn't active here), so any test relying on that marker for a bound (e.g. real-socket/SSH/subprocess-spawn tests called out in 122-CONTEXT.md and prior-phase evidence as "known macOS-environment-bound failures — multiprocessing spawn, sshcp, APFS latin-1") can run far longer than intended, up to effectively unbounded in this sandbox. Phase 120's own evidence (`120-06-SUMMARY.md`) shows the full suite *can* complete (1823 passed / 62 skipped / 21 failed / 43 errors, all attributed to the same host-only causes) but apparently not reliably inside this execution environment on this run.

**Resolution:** Per the orchestrator's explicit direction, the full-suite base/head comparison for Task 3 is **deferred** — it did not block this plan's GREEN evidence (which is scoped and complete: `tests/unittests/test_web` + `tests/unittests/test_sonarr5/test_sonarr5_system_status.py`, 355 passed; whole-tree `ruff check src/python/`, clean) and does not change any production code in this plan. The base/head full-suite comparison will instead be covered by CI (which runs in Docker, not this sandbox, and is where Phase 120's equivalent comparison was actually green) at the Plan 03 gate / PR review for this phase.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LOG-01 is fully implemented and verified at the scoped level (`test_web` + `test_sonarr5_system_status`, 355 passed; ruff clean); SAFE-01 evidence later in this phase can rely on the webhook Test-event INFO line actually reaching the app log.
- The full-suite base/head comparison is an open item carried to the PR/CI gate (per orchestrator direction) rather than a blocker on this plan — CI runs in Docker and is not subject to this sandbox's apparent hang.
- No blockers for Plan 03 (LOG-02).

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-22*

## Self-Check: PASSED

- All 10 modified/created source and test files found on disk.
- `122-02-SUMMARY.md` found on disk.
- Both task commits (`4bd0a28`, `220a2ac`) found in `git log --oneline --all`.
