---
phase: 128-arr-key-normalization
plan: 03
subsystem: controller
tags: [sonarr, radarr, api-key, completion-gate, queue, logging, tdd]
requires:
  - "128-01: common.normalize_arr_api_key / is_valid_arr_api_key"
provides:
  - "ArrQueueClient.enabled_targets trims the stored Sonarr/Radarr key on read (ARR-02); padded and trimmed keys share one ArrTarget.identity"
  - "ArrQueueClient.start_fetch skips a missing/invalid key before any worker or request exists, returns None, and logs '<Label> queue check skipped: API key is missing or invalid' (WARNING once per key value per arr, DEBUG on repeats) (ARR-03)"
affects: [128-04]
tech-stack:
  added: []
  patterns: ["normalize where the config is read, validate at the single outbound choke point", "warn-once memory keyed by arr code holding only the opaque _key_token value"]
key-files:
  created: []
  modified:
    - src/python/controller/arr_queue.py
    - src/python/tests/unittests/test_controller/test_arr_queue.py
    - src/python/tests/unittests/test_controller/test_completion_gate.py
decisions:
  - "Queue checks trim the stored arr key on read; the trimmed key is kept in the target even when invalid so each distinct invalid value keeps its own token"
  - "An invalid/missing key makes start_fetch return None after the URL check and before the in-flight check; completion_gate.py is unchanged and holds as <code>_unavailable"
  - "Warn-once state resets when a valid key is seen, so a key broken again after working warns again (research open question 1)"
metrics:
  duration: "~8 min"
  completed: 2026-11-19
  tasks: 2
  files: 3
---

# Phase 128 Plan 03: Queue Check Key Normalization and Fail-Safe Skip Summary

Live Sonarr/Radarr queue checks now trim the stored key on read, so a key saved with padding earlier in the session is sent as a clean `X-Api-Key`. A key that is missing or invalid makes the check skip without starting a thread or request, and the completion stays held as unavailable. The skip logs a fixed message that never includes the key.

## RED (commit ff58eb7e)

Tests added:

- `test_arr_queue.py` / `TestArrQueueTargets`: `test_padded_key_and_trimmed_key_share_identity`, `test_enabled_targets_non_string_key_becomes_empty`
- `test_arr_queue.py` / `TestArrQueueFetch`: `test_padded_in_memory_key_is_sent_normalized`, `test_invalid_key_skips_request_and_starts_no_thread`, `test_missing_key_skips_request`, `test_invalid_key_warns_once_per_key_then_debug`, `test_invalid_key_warns_again_after_valid_key_seen`, `test_invalid_key_warning_is_tracked_per_arr`, `test_invalid_key_never_appears_in_logs`, `test_invalid_key_check_runs_after_url_check`
- `test_completion_gate.py` / new `TestBadKeyFailsSafe` (real `ArrQueueClient` + `CompletionGate`, Radarr URL `http://radarr.internal.example:7878` set in setUp): `test_bad_key_whitespace_only_holds_unavailable`, `test_bad_key_invalid_characters_holds_unavailable`, `test_bad_key_radarr_holds_unavailable`, `test_bad_key_logs_reason_without_key`, `test_bad_key_after_valid_key_discards_cached_evidence`

The skip tests patch `controller.arr_queue.threading.Thread` and build a fresh client for each row. None of them uses `threading.active_count` (grep count 0).

Observed RED run (`-k "padded or invalid_key or missing_key or bad_key or non_string_key or identity"`): **22 failed, 5 passed**. Every failure came from behaviour, not from test setup: a padded header was sent, `start_fetch` returned a fetch id (`1 is not None`), `get` was called, or no skip warning was logged. The run that excludes the new tests passed: **95 passed**. `ruff check src/python/`: All checks passed.

The padded key ARR-02 failure before the fix (`test_padded_in_memory_key_is_sent_normalized`):

```
E           AssertionError: expected call not found.
E           Expected: get('http://sonarr.internal.example:8989/api/v3/queue/details', headers={'X-Api-Key': 's3cr3t-api-key-0123456789abcdef'}, timeout=(3.05, 10), allow_redirects=False, stream=True)
E             Actual: get('http://sonarr.internal.example:8989/api/v3/queue/details', headers={'X-Api-Key': '  s3cr3t-api-key-0123456789abcdef\n'}, timeout=(3.05, 10), allow_redirects=False, stream=True)
FAILED tests/unittests/test_controller/test_arr_queue.py::TestArrQueueFetch::test_padded_in_memory_key_is_sent_normalized
1 failed, 37 deselected
```

`test_invalid_key_check_runs_after_url_check` passed before the fix, as planned. It confirms the URL check still runs first.

## GREEN (commit aec8d8a7)

`src/python/controller/arr_queue.py`:
- The import now also brings in `is_valid_arr_api_key` and `normalize_arr_api_key` from `common`.
- `__init__` adds `self.__key_skip_warned: Dict[str, str]`, which maps an arr code to the opaque key token it last warned about. Only the controller thread uses it, so it has no lock.
- `enabled_targets` now reads both keys with `normalize_arr_api_key(config.<arr>.<arr>_api_key)` and no longer uses `or ""`.
- `start_fetch` checks `is_valid_arr_api_key(target.api_key)` after the URL-scheme skip and before `code = target.code` and the in-flight check. When the key is invalid, it logs a WARNING the first time a key token is seen for that arr code and a DEBUG line on repeats, then returns None. When the key is valid, it clears the warn-once entry with `__key_skip_warned.pop(target.code, None)`. The docstring now lists the missing/invalid key condition.
- `completion_gate.py` is unchanged (the diff stat is empty). Its existing `if fid is None: self._record_failure(...)` branch produces `HOLD("<code>_unavailable")`.

Observed GREEN runs:
- `test_arr_queue.py` + `test_completion_gate.py`: **110 passed, 31 subtests passed**
- `-k padded`: 2 passed
- `test_common/test_arr_api_key.py`: 6 passed
- `tests/unittests/test_sonarr5`: 49 passed
- Each other `test_controller/*.py` module: all passed
- `ruff check src/python/`: All checks passed

Acceptance greps all matched the plan: `normalize_arr_api_key(config.` = 2, `api_key or ""` = 0, skip format string with `target.label` = 2, `__key_skip_warned` = 4, `pop(target.code, None)` = 1, `pop(code` = 0. The validity check is on line 199, after the URL warning (line 197) and before `prior = self.__fetches.get(code)` (line 209).

## REFACTOR

None needed.

## Warn-once reset decision

Seeing a valid key clears the arr's warn-once entry. So if a key works and later breaks again, a new WARNING is logged even when the bad value is the same one as before. This follows D-06: a change from valid to invalid counts as a key change. `test_invalid_key_warns_again_after_valid_key_seen` covers it.

## Gate transition evidence

In `test_bad_key_after_valid_key_discards_cached_evidence`, the real client with an empty queue gives `HOLD("no_queue_entry")`, matching the fake-client tests. When the key changes to `"abc def"`, the identity changes and the gate resets. The skip then sets `_snapshots["sonarr"] = None`, the verdict is `HOLD("sonarr_unavailable")`, and no second request is made (`get.call_count == 1`). The first evaluate, while the fetch is still pending, also returns `HOLD("sonarr_unavailable")`. No step returns an allow or not-required verdict.

## Pre-existing tests given an explicit key

None. No existing test failed after the fix, so none needed a key added to its config.

## Deviations from Plan

None in product code. Two small additions to the tests:
- `test_enabled_targets_non_string_key_becomes_empty` uses subTest to check `None`, an unset `MagicMock`, and the int `12345`, rather than a single value.
- `test_invalid_key_never_appears_in_logs` also checks the full `_log_text` of the logger mock, in addition to the per-level sweep.
- **Cost if wrong:** none. These only add assertions.

## Deferred Issues (out of scope, pre-existing)

- Running `tests/unittests/test_controller` as one directory under the pipx pytest on macOS spun at 100% CPU for several minutes and was stopped. Run module by module with a 60 s timeout, every module that uses the arr code passed. `test_controller/test_scan` fails with multiprocessing errors (`'NoneType' object has no attribute 'terminate'`, `Can't pickle <class 'unittest.mock.MagicMock'>`), and `test_controller/test_extract` reached the 60 s timeout. Neither module imports the arr queue or gate code. At the RED commit ff58eb7e, before any source change, `test_scan` already showed 3 failed and 3 errors. These look like problems with the macOS multiprocessing spawn setup, not with this change. CI on Linux is the authoritative run for those modules.

## Threat Surface

Nothing new. T-128-10 to T-128-15 are mitigated as planned. The skip log uses a fixed format string with only `target.label`. The key is validated before any worker or request exists. Warn-once memory keeps only the opaque `k<n>` token.

## Commits

- ff58eb7e test(128-03): add failing regression for padded arr key and fail-safe skip tests
- aec8d8a7 fix(128-03): normalize arr key on read and skip queue check on a missing or invalid key

## Self-Check: PASSED

- FOUND: src/python/controller/arr_queue.py, test_arr_queue.py, test_completion_gate.py
- FOUND: ff58eb7e, aec8d8a7 in git log
