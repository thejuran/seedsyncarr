---
phase: 122-safety-acceptance-and-logging-fixes
reviewed: 2026-10-25T15:55:00Z
depth: standard
review_type: re-review (gap cycle 2, plans 122-13 and 122-14)
diff_base: 85bdc01
files_reviewed: 13
files_reviewed_list:
  - src/python/controller/controller.py
  - src/python/web/handler/config.py
  - src/python/web/handler/status.py
  - src/python/web/rate_limit.py
  - src/python/web/web_app_builder.py
  - src/python/tests/unittests/test_controller/test_controller.py
  - src/python/tests/unittests/test_controller/test_import_credit.py
  - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
  - src/python/tests/unittests/test_web/test_handler/test_controller_handler.py
  - src/python/tests/unittests/test_web/test_handler/test_status_handler.py
  - src/python/tests/unittests/test_web/test_rate_limit.py
  - src/python/tests/unittests/test_web/test_web_app_builder_logging.py
  - src/python/controller/arr_queue.py
findings:
  critical: 0
  warning: 1
  info: 2
  convention: 0
  total: 3
status: issues_found
---

# Phase 122: Code Review Report (re-review after gap cycle 2)

**Reviewed:** 2026-10-25
**Depth:** standard
**Files Reviewed:** 13 (12 in the diff, plus `controller/arr_queue.py` read to check the other outbound use of the API key)
**Status:** issues_found (no blockers)

## Narrative Findings (AI reviewer)

## Summary

Scope: `git diff 85bdc01..HEAD -- src`, covering plans 122-13 (WR-02, WR-03) and 122-14 (CR-01, WR-01). The affected unit tests pass (417 passed: `test_import_credit`, `test_controller`, `tests/unittests/test_web`), and `ruff check` passes on the whole Python tree.

All four prior findings are fixed in code and covered by tests. I found no remaining way for the Arr API key to reach a log:
- `web/` now has no `logger.exception` or `exc_info` call, and no log call that interpolates exception text.
- The only other outbound request that carries the key (`controller/arr_queue.py:277-289`) logs only `type(e).__name__`.
- `StreamQueue` (`web/utils.py:31`) is the only detached logger left under `web/`. Its messages never contain request data, and keeping it detached avoids the log stream logging about itself.

The fixes introduce one new warning: the CR-01 fix strips whitespace from the key only inside Test Connection, so Test Connection can now report success for a stored key that the runtime queue check cannot use (WR-04). They also add two minor robustness gaps in the WR-02 grace window (IN-04, IN-05). Neither gap can authorize a deletion: a credit still never arms auto-delete (D-14), and both gaps fail closed.

## Prior findings

| ID | Status | Evidence |
|----|--------|----------|
| CR-01 (API key in log via `logger.exception`) | **Resolved** | `config.py:150-155`: the key is stripped and must match `[\x21-\x7e]+` before any request is made, so `InvalidHeader` can no longer be triggered by CR/LF or leading whitespace. `config.py:208-216`: the catch-all logs `type(e).__name__` only, with no traceback and no message. Tests: `test_config_key_with_newline_never_reaches_requests_or_log` captures every record under `seedsyncarr` and checks both the plain-formatted and SSE-serialized forms; `test_config_unexpected_error_with_real_invalid_header_logs_type_only` uses a real `InvalidHeader` that carries the key and asserts `exc_info is None`. |
| WR-01 (StatusHandler rate-limit logger detached) | **Resolved** | `status.py:9-17` uses `context.logger.getChild("StatusHandler")`. `web_app_builder.py:35` passes `context`. `rate_limit.py:17-30`: `logger` is now a required keyword-only argument, and passing `None` raises `TypeError`. The module-level logger has been removed. All 7 production call sites pass `logger=self.logger` (config x3, webhook x2, controller x1, status x1). Tests: `TestRateLimitRequiresLogger`, `test_status_rate_limit_warning_under_app_logger`. |
| WR-02 (post-transfer window not limited) | **Resolved** (see IN-04 and IN-05 for leftover gaps) | `controller.py:832-840`: post-transfer keep/credit now requires a local copy and a DOWNLOADING/QUEUED sighting less than 120 s ago (`_POST_TRANSFER_GRACE_SECS`). `controller.py:859-876` discards a pending notice once the root is outside that window. `controller.py:1505-1508` discards on a successful STOP or DELETE_LOCAL. `__last_transferring_at` is pruned against the model on every cycle (`:735-739`) and cleared in `_discard_pending_notices` (`:1166`). Tests: `TestPostTransferWindowBounds` covers the 119/121 s boundary, refresh while transferring, local copy gone, STOP, and DELETE_LOCAL. |
| WR-03 (credit line says "root still transferring") | **Resolved** | `controller.py:895-901` and `:1022-1025`: the reason is passed through, and the default wording is unchanged so existing greps still match. Test: `test_post_transfer_credit_line_says_transfer_finished`. |
| IN-01 (duplicate "Keeping" DEBUG line) | Open, out of scope by owner decision | `controller.py:888-894` is still present. |
| IN-02 (`globals()["logger"]` shadowing) | Resolved as a side effect of WR-01 | The module logger and the `globals()` lookup were both removed. |
| IN-03 (handlers take `config` and `context`) | Open, out of scope by owner decision | `ConfigHandler(context.config, context)` is unchanged. `StatusHandler` now also takes `context` alongside `context.status`. |
| CV-01 (import-relativity flag) | Unchanged, advisory only | Likely a false positive. |

## Warnings

### WR-04: Test Connection strips the API key, but the runtime queue check sends the raw stored key

**File:** `src/python/web/handler/config.py:150`; `src/python/controller/arr_queue.py:171,175,278`
**Issue:** The CR-01 fix runs `api_key = api_key.strip()` inside `_test_arr_connection` only, and `test_config_key_whitespace_stripped_before_header` locks that behaviour in. The stored value is never normalized: the config property uses `Checkers.null`/`Converters.null`, and the Angular settings form does not trim. `ArrQueueClient` builds `ArrTarget(..., config.sonarr.sonarr_api_key or "")` and sends that raw value in `X-Api-Key`. So for a key pasted with surrounding whitespace:
- Test Connection reports **success**, because it sent the stripped key.
- Every runtime queue check fails. A leading space or a newline makes `requests` raise `InvalidHeader`, logged as `Sonarr queue check failed: InvalidHeader`. A trailing space gets HTTP 401 from Sonarr.
- The completion gate then holds every completion as "Sonarr unavailable".

This fails closed, so nothing is deleted wrongly. But the user's tool for diagnosing a bad key now gives a false all-clear for exactly the key shapes that break the safety gate. Before the fix, Test Connection at least failed for those keys.
**Fix:** Make validation match what is sent at runtime. Either:
- reject instead of strip in Test Connection (`if api_key != api_key.strip() or not _API_KEY_CHARS.fullmatch(api_key): return "...contains invalid characters"`), or, preferably,
- normalize where the key is stored: strip and validate in `ConfigHandler.__handle_set_config` for `sonarr_api_key`/`radarr_api_key` (or add a stripping converter on the PROP). Also strip in `ArrQueueClient` target construction so keys already stored with whitespace keep working:
```python
targets.append(ArrTarget("Sonarr", "sonarr",
                         config.sonarr.sonarr_url or "",
                         (config.sonarr.sonarr_api_key or "").strip()))
```
Then add a test that a whitespace-padded stored key produces the same outcome in Test Connection and in `ArrQueueClient`.

## Info

### IN-04: After STOP, the same cycle re-stamps `__last_transferring_at` from the not-yet-updated model state

**File:** `src/python/controller/controller.py:718-720`, `:1505-1506`, `:360-365`
**Issue:** `process()` runs `__process_commands()` (STOP, then `_discard_pending_notices`, which pops `__last_transferring_at[root]` and bumps the generation) and then `__check_webhook_imports()` in the same call. At that point the model usually still shows the root as DOWNLOADING, because lftp status has not caught up yet. Window 1 therefore stamps `__last_transferring_at[root] = now` again straight away. A fresh webhook notice that arrives in that short gap is kept pending under the new generation. Once the root shows DEFAULT with a partial local copy, that notice is eligible for post-transfer credit for 120 s, on a root the user just stopped. The impact is small: credit still needs the child to be complete (`local_size == remote_size`) and never arms deletion (D-14). Still, the docstring's claim that a stopped transfer "must not be covered" only holds for notices received before the STOP.
**Fix:** Keep a short per-root "stopped/deleted at" fence that `_discard_pending_notices` sets for the STOP and DELETE_LOCAL causes. Skip the Window 1 stamp (or the `post_transfer_pending` grant) while the fence is newer than the last real state transition. Or simply skip stamping for a root whose STOP was handled in the current `process()` call. Add a test: STOP, then a fresh notice in the same cycle while the model still shows DOWNLOADING, then DEFAULT with the child complete, and assert no credit.

### IN-05: `local_size is None` treats "not scanned yet" as "local copy gone", and the 120 s cap is a hard cliff for slow local scans

**File:** `src/python/controller/controller.py:832-840`, `:859-876`
**Issue:** (a) `post_transfer_pending` requires `root_file.local_size is not None`, and the discard branch logs `"local copy gone"` whenever it is `None`. A root whose lftp job ends before the local scanner has ever seen its directory is a real scan-lag case, which is exactly what D-06(c) targets. That notice is discarded with a misleading reason. (b) The window is measured from the last DOWNLOADING/QUEUED sighting, so if the local scan takes longer than 120 s on a large staging directory, the notice is lost even though the transfer finished normally. Both cases fail closed (no credit, so no deletion), but they bring back the missed-import symptom D-06(c) fixed, and only a WARNING line shows it. The 2.5 s transfer-end-to-commit evidence supports 120 s on the sandbox, but nothing guards the larger-library case.
**Fix:** (a) Word the reason as `"no local copy seen"`. Optionally, apply the `local_size is None` test only after at least one local scan has finished since the transfer ended. (b) Optionally measure the grace from the first local-scan completion after the last transferring sighting, or log the elapsed scan duration in the discard line so the cliff can be diagnosed from NAS logs. No change is needed if the owner accepts fail-closed loss here.

---

_Reviewed: 2026-10-25T15:55:00Z_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_
