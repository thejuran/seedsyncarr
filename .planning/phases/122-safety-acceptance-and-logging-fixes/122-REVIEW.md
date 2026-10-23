---
phase: 122-safety-acceptance-and-logging-fixes
reviewed: 2026-10-23T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/python/controller/completion_gate.py
  - src/python/controller/controller.py
  - src/python/web/handler/config.py
  - src/python/web/handler/controller.py
  - src/python/web/handler/webhook.py
  - src/python/web/rate_limit.py
  - src/python/web/web_app_builder.py
  - src/python/tests/unittests/test_controller/test_completion_gate.py
  - src/python/tests/unittests/test_controller/test_import_credit.py
  - src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py
  - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
  - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py
  - src/python/tests/unittests/test_web/test_rate_limit.py
  - src/python/tests/unittests/test_web/test_web_app_builder_logging.py
  - src/python/tests/unittests/test_web/test_webhook_handler.py
findings:
  critical: 1
  warning: 3
  info: 3
  convention: 1
  total: 8
status: issues_found
---

# Phase 122: Code Review Report

**Reviewed:** 2026-10-23
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

Scope: `git diff origin/main...HEAD` for phase 122. That covers LOG-01 (web handler loggers moved under the `seedsyncarr` app logger, plus injecting a logger into `rate_limit`), LOG-02 (completion hold "cleared" vs "dropped" wording) and D-06(c) (a revalidated pending import notice is kept or credited between transfer end and commit).

LOG-02 is correct and well tested. The proof-based release still logs "cleared" with the exact old wording. Prune paths and the no-integration path log "dropped (<module literal>)", and the root name is sanitized.

LOG-01 does what it set out to do, but it has a security side effect. Lines that used to go nowhere useful (a detached module logger, so only Python's last-resort stderr handler saw them) now go to the rotating app log file and to the web UI log stream (SSE). One of those lines is `logger.exception` in the Sonarr/Radarr test-connection path. I confirmed by running it that this line can contain the configured API key in plain text (CR-01). The new test that claims to prove "no API key in the log" only uses a `RuntimeError("boom")`, so it does not exercise the failure that leaks the key. LOG-01 also misses one call site: the `StatusHandler` rate-limit logger is still detached (WR-01).

D-06(c) does fix the 2026-10-22 sandbox drop. The new window is wider than its comments say, though. It is not limited to "between transfer end and commit": it applies to any root that still has a remote copy and is not transferring, for up to the 6 h TTL (WR-02). The credit log line on the new path also says "(root still transferring)", which is false there (WR-03).

## Critical Issues

### CR-01: Arr API key written to the app log file and web UI log stream via the test-connection exception log

**File:** `src/python/web/handler/config.py:195` (with `:131-160`)
**Issue:** `_test_arr_connection` sends the stored API key with `headers={"X-Api-Key": api_key}`. It only rejects a key that is empty or all whitespace (line 138); the key is never stripped or validated, and the config uses `Checkers.null` / `Converters.null`. requests checks header values before sending. If the key has leading whitespace or any `\r`/`\n` (for example a value pasted with a leading space or a trailing newline), requests raises `requests.exceptions.InvalidHeader` with this message: `"Invalid leading whitespace, reserved character(s), or return character(s) in header value: ' <APIKEY>\n'"`. That exception is neither `ConnectionError` nor `Timeout`, so it falls into `except Exception:` and `self.logger.exception(...)` logs the full traceback, which includes the key.

Before this phase that logger was detached. Phase 122 attaches it to `seedsyncarr.ConfigHandler`, so the key now goes to:
- the RotatingFileHandler (`/volume1/docker/seedsync/log/seedsyncarr.log`, which is persisted and kept by log forensics);
- the web UI log stream. `SerializeLogRecord._redact_sensitive` only covers lftp `-u`, `password=`, and `user@host` patterns. It does nothing for an `X-Api-Key` header value.

Reproduced locally: `_test_arr_connection("Sonarr", url, " SECRETKEY123\n")` with `_validate_url` patched produced a captured `seedsyncarr` log containing `SECRETKEY123`. This breaks the absolute rule "Never log sensitive data (… tokens …, auth headers)". The regression test `test_config_unexpected_error_logged_without_api_key` passes only because a `RuntimeError("boom")` never contains the key.

**Fix:** Do not log exception text or a traceback from this boundary. Log the exception type only, and handle the key-shape error before the request:
```python
        api_key = api_key.strip()
        if not re.fullmatch(r"[A-Za-z0-9]+", api_key):
            return HTTPResponse(body=json.dumps({"success": False,
                    "error": "{} API key contains invalid characters".format(service_name)}),
                content_type="application/json")
        ...
        except Exception as e:
            # Never log the message/traceback: requests embeds header values
            # (the API key) in InvalidHeader and similar errors.
            self.logger.error("Unexpected error testing %s connection (%s)",
                              service_name, type(e).__name__)
```
Also add a regression test that leaves `requests` unmocked (or raises a real `requests.exceptions.InvalidHeader` that carries the key) and asserts the key does not appear in the formatted record or the SSE-serialized record. Audit other `logger.exception` sites that are now under the app logger and touch outbound arr requests (`sonarr5`/`arr_queue` clients) for the same pattern.

## Warnings

### WR-01: LOG-01 incomplete: StatusHandler rate-limit warning still goes to the detached module logger

**File:** `src/python/web/handler/status.py:16`, `src/python/web/rate_limit.py:16,29`
**Issue:** `StatusHandler` still calls `rate_limit(max_requests=60, window_seconds=60.0)` without `logger=`. The phase leaves the module-level fallback `logging.getLogger("web.rate_limit")` in place, so the status endpoint's "Rate limit exceeded" warning is still not routed to the app log or the UI. This is the exact class of loss LOG-01 was meant to fix. Because the parameter is optional, any future caller will repeat this silently.
**Fix:** Give `StatusHandler` the context logger (`StatusHandler(context.status, context)` and `logger=self.logger`). Better still, make `logger` a required keyword argument of `rate_limit` so a detached fallback cannot happen again. Then drop the module-level `logger`.

### WR-02: Post-transfer notice retention is not limited to "transfer ended, awaiting commit"

**File:** `src/python/controller/controller.py:806-835`
**Issue:** `post_transfer_pending` only requires that the key is already pending and that `root_file.remote_size is not None`. It does not check the root's state or how long ago it left DOWNLOADING/QUEUED. The comments and the docstring (lines 683-685, 786-804) say the notice is kept "after the root's transfer ends and until it commits". In practice, a pending notice now survives and can be credited for up to `_PENDING_NOTICE_TTL_SECS` (6 h) in states that have nothing to do with scan lag:
- the user stops the transfer, or the lftp job fails, leaving the root DEFAULT with a partial copy;
- the user deletes the local copy while the remote remains. This is not a "root removed from model" lifecycle reset, and a delete-local does not bump the generation.
The notice can then be credited if a later, non-USER (auto-queue) re-transfer completes that child within the same generation. Before this change, any of these states dropped the notice on the next cycle. A credit does not arm deletion by itself (D-14), but it does count toward coverage when the root later commits. So in these off-path cases, the change widens what an old notice can authorize. The new tests only cover DEFAULT-with-scan-lag and remote loss.
**Fix:** Limit the window explicitly. Record when the root was last seen transferring (for example, a per-root `last_transferring_at` set while DOWNLOADING/QUEUED). Allow `post_transfer_pending` only when `now - last_transferring_at` is below a short grace period (a few scan intervals, not 6 h). Also discard pending notices for a root on delete-local and when the user stops it. Add tests for stopped-root and local-deleted-root shapes.

### WR-03: Credit INFO line says "(root still transferring)" on the post-transfer path

**File:** `src/python/controller/controller.py:958-963`
**Issue:** `__credit_early_child` is now also reached when the root is not transferring (`post_transfer_only`). Its docstring was updated, but the INFO line it emits still says `"Credited early import of '{}' in '{}' (root still transferring)"`. In the 122-10 case this is false. Phase 122 (LOG-02) exists to make log wording match what actually happened, and these lines are used directly in NAS log forensics and Phase 120 evidence greps.
**Fix:** Pass the reason through, as was already done for `__keep_pending_notice`:
```python
def __credit_early_child(self, root_file, root_name, matched_name, reason="root still transferring"):
    ...
    self.logger.info("Credited early import of '{}' in '{}' ({})".format(
        sanitize_log_value(matched_name), sanitize_log_value(root_name), reason))
```
and call it with `reason="transfer finished, awaiting commit"` when `post_transfer_only`. Keep the default string unchanged so existing greps still match.

## Info

### IN-01: Duplicate and misleading DEBUG lines on the post-transfer path

**File:** `src/python/controller/controller.py:831-848`
**Issue:** When `post_transfer_only` is true, the code logs "Keeping webhook notice ... transfer finished, awaiting commit" before it tries to credit. If the credit succeeds, the "Keeping" line was wrong. If it fails, `__keep_pending_notice` then logs "Deferring webhook notice ... transfer finished, awaiting commit", which says the same thing again. That is two DEBUG lines per pending notice per cycle.
**Fix:** Remove the "Keeping" block at lines 831-838. The `reason` passed to `__keep_pending_notice` already covers it.

### IN-02: `rate_limit` parameter shadows the module logger; `globals()["logger"]` workaround

**File:** `src/python/web/rate_limit.py:22,29`
**Issue:** The new `logger` parameter has the same name as the module-level `logger`, so the code has to use `globals()["logger"]` to reach the default. This is fragile: renaming the module variable breaks it at runtime, not at import time.
**Fix:** Rename the module variable (`_default_logger = logging.getLogger(__name__)`) and use `logger or _default_logger`. Or remove the fallback entirely (see WR-01).

### IN-03: Handlers take both `config` and `context` (redundant constructor arguments)

**File:** `src/python/web/web_app_builder.py:33,36`; `src/python/web/handler/config.py:16`; `src/python/web/handler/webhook.py:24`
**Issue:** `ConfigHandler(context.config, context)` and `WebhookHandler(webhook_manager, context.config, context)` receive the config twice. `ServerHandler(context)` already reads everything from `context`. The two can drift apart in tests (mocks pass an unrelated `MagicMock()` context).
**Fix:** Optional cleanup: take `context` only and read `context.config` inside. Or pass `logger` instead of the whole context.

## Conventions

### CV-01: Import-relativity flag on `rate_limit.py` (likely false positive)

**File:** `src/python/web/rate_limit.py:1`
**Deviation:** The checker reports absolute imports, while its dominant axis is relative. The only absolute imports in this file are stdlib and the third-party `bottle`, which cannot be relative.
**Convention:** py-import-relativity (relative imports for intra-package modules).
**Fix:** No action needed for the current imports. Use relative imports if intra-package imports are added later. Advisory only; does not block.

---

_Reviewed: 2026-10-23_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_
