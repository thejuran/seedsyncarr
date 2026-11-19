---
phase: 128-arr-key-normalization
reviewed: 2026-11-19T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/python/common/__init__.py
  - src/python/common/arr_api_key.py
  - src/python/controller/arr_queue.py
  - src/python/web/handler/config.py
  - src/python/tests/integration/test_web/test_handler/test_arr_key_parity.py
  - src/python/tests/integration/test_web/test_handler/test_config.py
  - src/python/tests/unittests/test_common/test_arr_api_key.py
  - src/python/tests/unittests/test_controller/test_arr_queue.py
  - src/python/tests/unittests/test_controller/test_completion_gate.py
  - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 128: Code Review Report

**Reviewed:** 2026-11-19
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the phase diff `2f2b1576..HEAD`: the new shared rule (`common/arr_api_key.py`), its use on Save (`ConfigHandler.__handle_set_config`), Test Connection (`_test_arr_connection`) and the queue client (`ArrQueueClient.enabled_targets` / `start_fetch`), the D-07 secret non-echo change, and the new tests. I also traced the queue skip into `controller/completion_gate.py` to check the fail-safe.

Checked against the three focus areas:

- **Secrets never logged or echoed.** Met. The queue skip logs only the arr label. The secret refusal path logs `type(e).__name__` only. Secret confirmations say `"<section>.<key> updated"`. Neither arr-key refusal message contains the value. `web_app.py` does not log request or response bodies. Test Connection and the queue client are still the only places that send `X-Api-Key`, and both now get the normalized key.
- **One identical rule on all three paths.** Met for string input. Test Connection reads the stored key, so all three paths apply `is_valid_arr_api_key(normalize_arr_api_key(raw))` to the same value. Python `str.strip()` also removes NBSP, `\x1c`-`\x1f` and `\x85`, but it does so the same way on every path, so they still agree. The one gap is non-string input on Save (WR-01).
- **Fail-safe on a missing or invalid key.** Met. `start_fetch` returns `None` before any thread or request. `CompletionGate._run` then calls `_record_failure`, which sets the snapshot to `None`, so `_classify` returns `_UNAVAILABLE` and the item is held as `<code>_unavailable`. A key change also changes `ArrTarget.identity`, which triggers `_reset_integration_state`, so no cached proof from the earlier valid key survives (`test_bad_key_after_valid_key_discards_cached_evidence` covers this). I found no path that gives a false all-clear.

Verification: the six phase test modules pass (300 passed, 138 subtests), and whole-tree `ruff check` is clean. The ARR-02 regression (`test_padded_in_memory_key_is_sent_normalized` and the live-config parity test) asserts the exact `X-Api-Key` header, so it would have failed against the old code, which sent the padded key. Convention rule packs found nothing.

## Warnings

### WR-01: Save turns any non-string JSON value into a stored Arr key and overwrites the good key

**File:** `src/python/web/handler/config.py:330-356`
**Issue:** Before the arr-key rule runs, `value_str = str(value)` converts any JSON type to text. Several non-string values pass the rule after that conversion: `true` becomes `"True"`, `[]` becomes `"[]"`, `{}` becomes `"{}"`, `["abc"]` becomes `"['abc']"`, and `1e999` becomes `"inf"`. Save stores the result, answers `200 "sonarr.sonarr_api_key updated"`, and the previously stored working key is gone. Real Sonarr or Radarr rejects the garbage key with a 401, so every queue check fails and completions stay held as "Sonarr unavailable" until someone notices and re-enters the key. This is the same "looks saved, nothing works" symptom the phase set out to remove. It also breaks the parity claim: the queue client treats a non-string key as missing (`normalize_arr_api_key` returns `""`), while Save treats the same input as a valid key. The Angular client always sends strings, so the trigger is a direct API caller or script, but the loss of the stored key is real. Today the test suite explicitly accepts `12345` (`test_set_arr_key_non_string_value_is_stringified`, and the parity test's boundary case), and nothing tests bool, list or dict input.
**Fix:** For the arr-key properties, accept only `str` input. Accept `int` only if numeric keys are a deliberate decision. Reject everything else with the D-04 response, before `str()` is applied:
```python
arr_service = _ARR_KEY_PROPS.get((section, key))
if arr_service is not None:
    if not isinstance(value, str):
        return HTTPResponse(body="Invalid request body", status=400)
    value_str = normalize_arr_api_key(value)
    ...
```
Then update the `12345` assertions, and add bool, list and dict cases that check the stored key is unchanged.

## Info

### IN-01: Only `enabled_targets` trims the key, so the queue client's agreement with Save depends on one caller

**File:** `src/python/controller/arr_queue.py:172-178, 199`
**Issue:** `enabled_targets` trims the key, and `start_fetch` only validates it. An `ArrTarget` built anywhere else with a raw padded key is refused (skipped) rather than trimmed. That is still fail-safe, but it would bring back the Test-Connection-passes / queue-fails mismatch for that caller. Today `enabled_targets` is the only production constructor, so this is a maintenance trap, not a live bug.
**Fix:** Move the trim into one place that every caller goes through. For example, have `start_fetch` call `normalize_arr_api_key(target.api_key)` before validating and before building the worker args. Or note on `ArrTarget` that `api_key` must already be normalized.

### IN-02: A refused secret now gives a generic message even when the reason contains nothing sensitive

**File:** `src/python/web/handler/config.py:363-370`
**Issue:** Every `ConfigError` on a `secret=True` property now returns `"Invalid value for <section>.<key>"`. For `lftp.remote_password` the only checker is `Checkers.string_nonempty`, whose message (`"Bad config: Lftp.remote_password is empty"`) never contains the value. The user loses the actual reason ("is empty") for no security benefit. This is a small usability regression on the settings page.
**Fix:** This is optional. Keep the generic text, but append a fixed reason when one is known (for example `"... is empty"` for whitespace-only input), or add a checker-supplied reason that is guaranteed not to contain the value. The current behaviour is acceptable under D-07.

## Set aside (needs ruling)

### SA-01: After saving a padded key, the frontend's local config still holds the untrimmed value

**Where:** `src/angular/src/app/services/settings/config.service.ts:69`
**Why excluded:** The phase scope excludes UI changes. The server-side behaviour is correct.
**Effect if left as is:** After a successful save, `ConfigService` puts the value the user typed (padded) into its local copy, while the server stores the trimmed key. An authenticated user, whose config GET is not redacted, sees the padded value on the settings page until the next config reload. This is cosmetic only: Test Connection and the queue check both use the server's trimmed copy.
**Needs:** Owner ruling. Accept as is, or defer a follow-up so the frontend re-reads config (or applies the same trim) after a save.

### SA-02: Save confirmations still echo fields that are redacted on GET but not marked `secret=True`

**Where:** `src/python/web/handler/config.py:374` with `src/python/web/serialize/serialize_config.py:8-13`
**Why excluded:** D-07 covers only properties marked `secret=True`.
**Effect if left as is:** `lftp.remote_address`, `remote_username` and `remote_path` are hidden from unauthenticated GET responses, but a successful save still answers `"lftp.remote_address set to <value>"`. The value goes back only to the client that just sent it, so exposure is limited to proxies or logs that capture response bodies.
**Needs:** Owner ruling. Accept, or extend the non-echo rule to the `_SENSITIVE_FIELDS` set in a later phase.

---

_Reviewed: 2026-11-19_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_

## Resolution (orchestrator, 2026-11-19)

- **WR-01: fixed.** Save now refuses non-text Sonarr/Radarr key values with 400 "Invalid request body" and keeps the stored key (ebb52e1f test, 31d013e0 fix). This supersedes the plan's "stringify 12345" behaviour.
- **IN-01, IN-02: accepted as-is** (no live bug; informational).
- **Set-aside items: open for the owner's ruling** (UI shows untrimmed key until reload; save echoes non-secret hidden fields).
