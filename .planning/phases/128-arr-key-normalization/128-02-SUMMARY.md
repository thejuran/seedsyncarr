---
phase: 128-arr-key-normalization
plan: 02
subsystem: web
tags: [sonarr, radarr, api-key, config, secrets, tdd]
requires:
  - "128-01: common.normalize_arr_api_key / is_valid_arr_api_key"
provides:
  - "POST /server/config/set trims Sonarr/Radarr keys, refuses empty-after-trim (Invalid request body) and invalid keys (<Svc> API key contains invalid characters)"
  - "Secret-free save responses: '<section>.<key> updated' and 'Invalid value for <section>.<key>' for every Config.secret_fields() property"
  - "Test Connection on the shared key rule (private _API_KEY_CHARS removed)"
affects: [128-03, 128-04]
tech-stack:
  added: []
  patterns: ["module-level (section, key) -> label map selects props that get save-time normalization", "secret set built per request from Config.secret_fields() on the class (works with a MagicMock config)"]
key-files:
  created: []
  modified:
    - src/python/web/handler/config.py
    - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
    - src/python/tests/integration/test_web/test_handler/test_config.py
decisions:
  - "Refused saves of any secret property answer the fixed text 'Invalid value for <section>.<key>' and log only section, key and the exception class name (D-07)"
  - "Save-time trimming applies only to sonarr.sonarr_api_key and radarr.radarr_api_key; other properties are stored verbatim"
metrics:
  duration: "~5 min"
  completed: 2026-11-19
  tasks: 2
  files: 3
---

# Phase 128 Plan 02: Arr-key normalization on save and secret-free save responses Summary

Saving a Sonarr or Radarr API key now applies the shared rule from plan 01. Surrounding whitespace is trimmed. A key that is empty after trimming is refused with "Invalid request body". A key that still contains invalid characters is refused with the same "<Svc> API key contains invalid characters" text that Test Connection uses. The save response for any secret setting no longer repeats the value.

## RED (Task 1, commit 3b94082f)

Tests were added to `test_config_handler.py` (unit, MagicMock config) and `test_config.py` (integration, real Config). Pinned literals `SONARR_KEY_INVALID_MSG`, `RADARR_KEY_INVALID_MSG` and `INVALID_BODY_MSG` were added.

Observed RED run (`-k "arr_key or secret"`): 27 failed, 10 passed. Every failure was an assertion failure (wrong status, wrong body, set_property called with the untrimmed value). There were no import or harness errors.

Failing tests:
- unit: `test_set_arr_key_sonarr_padded_is_trimmed`, `test_set_arr_key_radarr_padded_is_trimmed`, `test_set_arr_key_whitespace_only_refused` (sonarr and radarr subtests), `test_set_arr_key_invalid_refused_with_test_connection_wording` (all 6 subtests), `test_set_arr_key_non_string_value_is_stringified`, `test_set_secret_success_does_not_echo_value`, `test_set_secret_config_error_does_not_echo_value`
- integration: `test_set_arr_key_trimmed_and_not_echoed`, `test_set_arr_key_radarr_trimmed_and_not_echoed`, `test_set_arr_key_whitespace_only_refused_keeps_stored_key` (both subtests), `test_set_arr_key_invalid_refused_keeps_stored_key` (all 4 subtests), `test_set_secret_fields_never_echo_value` (all 5 secret subtests), `test_set_secret_refusal_does_not_echo_value`

Lock tests that passed before the change, as intended: `test_set_non_secret_still_echoes_value` (unit and integration), `test_set_non_secret_config_error_text_unchanged`, `test_set_arr_key_trim_applies_only_to_arr_keys`.

The pre-existing tests in both files (`-k "not arr_key and not test_set_secret and not test_set_non_secret"`) gave 161 passed and 29 subtests passed. `ruff check src/python/` reported "All checks passed!". The commit touched only the two test files.

## GREEN (Task 2, commit 6bb9928e)

Changes in `src/python/web/handler/config.py`:
- The import now pulls in `normalize_arr_api_key` and `is_valid_arr_api_key` from `common`. The private `_API_KEY_CHARS` and its comment were deleted. `_URL_CHARS` and `_HOSTNAME_RE` are unchanged.
- A new `_ARR_KEY_PROPS` maps `("sonarr", "sonarr_api_key")` to "Sonarr" and `("radarr", "radarr_api_key")` to "Radarr".
- `__handle_set_config` keeps its existing guards in the same order. After the has_property check, the two Arr keys are normalized. Empty gives 400 "Invalid request body". Invalid gives 400 "<Svc> API key contains invalid characters". Neither refusal calls set_property.
- Membership in `Config.secret_fields()` is checked with the lowercase attr. A secret answers "<section>.<key> updated". A refused secret answers 400 "Invalid value for <section>.<key>" and logs one warning, `"Config set refused for %s.%s: %s"`, with section, key and `type(e).__name__`. Non-secrets behave as before.
- In `_test_arr_connection`, `.strip()` and the regex are replaced by the shared helpers. Both error strings are byte-identical.

Observed:
- `pytest -q -p no:cacheprovider tests/unittests/test_web tests/integration/test_web/test_handler/test_config.py tests/unittests/test_sonarr5` gave 546 passed and 107 subtests passed. This includes the unchanged Test Connection pins.
- `ruff check src/python/` (whole tree) reported "All checks passed!"
- Grep counts in config.py:

| Pattern | Count |
|---|---|
| `_API_KEY_CHARS` | 0 |
| `normalize_arr_api_key` | 3 |
| `"{}.{} updated"` | 1 |
| `"{}.{} set to {}"` | 1 |
| `Config.secret_fields()` | 1 |
| `"{} API key contains invalid characters"` | 2 |
| `"{} API key is required"` | 1 |

- `git diff HEAD~1 HEAD --stat -- src/python/common/config.py src/angular src/e2e src/python/tests` printed nothing.

### "set to" grep

`grep -rn "set to" src/python/tests src/e2e --include="*.py" --include="*.ts"` found:
- `tests/integration/test_lftp/test_lftp_protocol.py:827`, a comment that is not about config
- `tests/integration/test_web/test_handler/test_config.py:315`, a new non-secret lock test
- `tests/unittests/test_seedsyncarr.py:893`, a docstring that is not about config
- `tests/unittests/test_web/test_handler/test_config_handler.py:300`, a new non-secret lock test

None of these assert the old confirmation text for a secret property, so no existing test needed a change.

## REFACTOR

None needed.

## Deviations from Plan

**1. [Structure] Success returns moved after the try/except instead of inside the try block**
- **Found during:** Task 2
- **Issue:** The plan placed the success return inside the try block. Moving it after the try/except leaves only `set_property` in the try. The behaviour and the grep counts are the same.
- **Cost if wrong:** None functionally. It is a cosmetic difference from the plan's wording.
- **Commit:** 6bb9928e

Apart from this, the plan was executed as written.

## Notes for the owner

- **The settings page shows the key as typed until the next reload.** If you paste a key with a stray space or line break, the server stores the trimmed key, but the settings field keeps showing what you typed until the settings reload. This is cosmetic. UI changes are out of scope for this phase.
- **One error message changes wording.** Saving a remote password that is only spaces used to show "Bad config: Lftp.remote_password is empty". It now shows "Invalid value for lftp.remote_password". The save is still refused and the stored password is unchanged; only the text differs. This applies to every secret setting (remote password, API token, webhook secret, both Arr keys): a refused save now answers a fixed message, so the value can never be repeated back in an error.

## Threat Flags

None. The only new surface is the warning line on refused secret saves. It is covered by T-128-06 and logs no value or exception message.

## Known Stubs

None.

## Commits

- 3b94082f: test(128-02): add failing tests for arr key save normalization and secret-free responses
- 6bb9928e: feat(128-02): normalize arr keys on save and stop echoing secrets

## Self-Check: PASSED

SUMMARY.md and config.py exist; commits 3b94082f and 6bb9928e are in git log.
