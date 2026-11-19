---
phase: 128-arr-key-normalization
plan: 01
subsystem: common
tags: [sonarr, radarr, api-key, validation, tdd]
requires: []
provides:
  - "common.ARR_API_KEY_CHARS / normalize_arr_api_key / is_valid_arr_api_key (shared key rule, D-01)"
  - "RULE_CASES rule table in tests/unittests/test_common/test_arr_api_key.py (reused by plan 04 parity test)"
affects: [128-02, 128-03, 128-04]
tech-stack:
  added: []
  patterns: ["pure dependency-free helper in common/, re-exported via barrel 'X as X' line"]
key-files:
  created:
    - src/python/common/arr_api_key.py
    - src/python/tests/unittests/test_common/test_arr_api_key.py
  modified:
    - src/python/common/__init__.py
decisions:
  - "Shared arr key rule lives in common/arr_api_key.py; is_valid_arr_api_key does not trim and returns False for non-str (fail-safe, never raises)"
metrics:
  duration: "~1 min wall clock"
  completed: 2026-11-19
  tasks: 2
  files: 3
---

# Phase 128 Plan 01: Shared Sonarr/Radarr API-key rule Summary

One shared rule for Sonarr/Radarr API keys, in `common/arr_api_key.py`: trim surrounding whitespace, then the key must be one or more printable ASCII characters with no spaces (`[\x21-\x7e]+`). An 18-row rule table pins the behaviour.

## RED

Task 1 wrote `tests/unittests/test_common/test_arr_api_key.py`, which has `RULE_CASES` (18 rows, a plain list literal, NBSP rows written as ` ` escapes) and 6 tests in `TestArrApiKeyRule`. Observed failure before the module existed:

```
E   ImportError: cannot import name 'ARR_API_KEY_CHARS' from 'common' (.../src/python/common/__init__.py)
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

Acceptance checks observed: the AST row count is `[18]`, `^RULE_CASES = \[` appears once, `u00a0` appears twice, there are 0 literal NBSP bytes and no raw control bytes, `ruff check src/python/` reports "All checks passed!", and `common/arr_api_key.py` does not exist.

## GREEN

Task 2 added `common/arr_api_key.py`. It imports only `re` and `typing.Any`. It defines `ARR_API_KEY_CHARS`, `normalize_arr_api_key`, which returns `""` for non-str and otherwise `.strip()`, and `is_valid_arr_api_key`, which returns False for non-str and otherwise `fullmatch`. A barrel line was added directly after line 1 of `common/__init__.py`. The comment describes the rule as the application's own policy and states that it is narrower than what `requests` accepts. The old "only characters requests accepts" wording was not copied.

Observed:
- `pytest -q -p no:cacheprovider tests/unittests/test_common` gave 211 passed and 36 subtests passed
- `from common import ARR_API_KEY_CHARS, normalize_arr_api_key, is_valid_arr_api_key` printed `import ok`
- `ruff check src/python/` (whole tree) reported "All checks passed!"
- Grep counts: 3 definitions, 2 import lines, 1 barrel line. The commit touched only `common/arr_api_key.py` and `common/__init__.py`.

## REFACTOR

None needed.

## Commits

- e34d9582: test(128-01): add failing rule-table tests for the shared arr key rule
- e4d3c460: feat(128-01): add shared arr api key normalization rule

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] NBSP escapes written as literal characters by the file-writing tool**
- **Found during:** Task 1
- **Issue:** The Write tool turned the ` ` escapes in the source into literal U+00A0 bytes. The plan forbids this, and the acceptance check showed 0 `u00a0` matches and 2 literal NBSP matches.
- **Fix:** Used `perl` to replace the literal bytes with the ` ` escape text before committing. Rechecked: 2 escapes, 0 literal NBSP bytes, no raw control bytes in the file.
- **Cost if wrong:** If the escapes had been lost, the NBSP rows would only work by accident of the file's encoding. `test_rule_table_pins_nbsp_rows` still guards the semantics.
- **Files modified:** src/python/tests/unittests/test_common/test_arr_api_key.py (before the RED commit)
- **Commit:** e34d9582

**2. [Rule 3 - Environment] Import probe interpreter**
- **Found during:** Task 2 verify
- **Issue:** Bare `python` is not on PATH. Homebrew `python3` lacks the project dependency `cryptography`, so `from common import ...` failed there inside `common/encryption.py`, which this plan does not touch.
- **Fix:** Ran the probe with the interpreter pytest uses (`~/.local/pipx/venvs/pytest/bin/python`). It printed `import ok`. The pytest run also imports through the barrel and passed.
- **Cost if wrong:** None to the code. Only the probe command differs.

## Threat Surface

T-128-01 (CR/LF and control-character injection) is mitigated by the allowlist `fullmatch`. It is pinned by the `abc\ndef`, `abc\r\ndef` and `a\x00b` rows. T-128-02 is mitigated: both functions are pure, never log, and never raise with the key in a message. No new surface outside the threat model.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/python/common/arr_api_key.py
- FOUND: src/python/tests/unittests/test_common/test_arr_api_key.py
- FOUND: e34d9582
- FOUND: e4d3c460
