---
phase: 128-arr-key-normalization
plan: 04
subsystem: testing
tags: [sonarr, radarr, api-key, parity, integration, phase-gate]
requires:
  - "128-01: RULE_CASES shared rule table, normalize_arr_api_key / is_valid_arr_api_key"
  - "128-02: Save trims and validates arr keys; secrets not echoed"
  - "128-03: queue client trims on read and skips a missing/invalid key"
provides:
  - "Cross-path parity tests over one real Config: Save, Test Connection and the queue check agree on every non-empty string row of RULE_CASES and send the same trimmed key"
  - "Per-path boundary pins for null, empty and numeric input"
  - "Filled and signed-off 128-VALIDATION.md"
affects: [128-verification, 130-release-smoke]
tech-stack:
  added: []
  patterns: ["one real Config shared by the WebTest app, a directly built ConfigHandler and ArrQueueClient", "parity claimed for string input only; boundary guards pinned separately"]
key-files:
  created:
    - src/python/tests/integration/test_web/test_handler/test_arr_key_parity.py
  modified:
    - .planning/phases/128-arr-key-normalization/128-VALIDATION.md
decisions:
  - "Local coverage below 88 (86.47%) is recorded as an environment limit, not a passed gate; Linux CI coverage is the authoritative gate result"
metrics:
  duration: "~20 min"
  completed: 2026-11-19
  tasks: 2
  files: 2
---

# Phase 128 Plan 04: Cross-Path Arr Key Parity and Phase Gate Summary

A padded Sonarr or Radarr key now has an end-to-end test. It is saved trimmed, Test Connection sends it trimmed, and the queue check reading the same live Config sends it trimmed. All three paths give the same accept/reject verdict for every non-empty string row of the shared rule table. Lint, the verification map and the single-definition check pass locally. The coverage floor of 88 could not be reproduced on this Mac: the result was 86.47%, with modules that only run on CI excluded.

## Task 1: Parity tests (commit 0b9d4e31)

`tests/integration/test_web/test_handler/test_arr_key_parity.py`, class `TestArrKeyParity(BaseTestWebApp)`, 6 tests:

- `test_padded_key_saved_then_same_key_on_all_three_paths` (Sonarr) and `..._radarr`: Save returns 200 and `<code>.<code>_api_key updated`, and the stored value equals K. Test Connection returns `success: True` with version 4.0.2 and the header it sends equals K. The queue check gives `enabled_targets` api_key K, a fetch id, a settled worker, `records == []` and a header equal to K.
- `test_padded_key_in_live_config_agrees_between_test_connection_and_queue` (D-05): the key is written directly to the config. Both paths succeed and send K.
- `test_rule_table_verdicts_agree_on_all_three_paths`: 15 rows, with the row count asserted. Each row checks Save (status, stored value, exact refusal wording), Test Connection (success or the exact error, and no request on a reject) and the queue check (a fetch with empty records, or None and no request).
- `test_boundary_specific_inputs_are_handled_by_each_path`: Save refuses None and "" with 400 `Invalid request body` and saves 12345 as "12345". Test Connection returns `API key is required` for None and "". The queue check skips None, "" and 123 with api_key "".
- `test_no_key_material_in_parity_logs_or_responses`: a recording handler on the root logger, removed through addCleanup. No message or save response body contains `LEAKPROBE`. The test also asserts that at least one message was logged, so an empty log can't pass it.

Verify run: `pytest -q -p no:cacheprovider tests/integration/test_web/test_handler/test_arr_key_parity.py tests/unittests/test_common/test_arr_api_key.py` gave **12 passed, 58 subtests passed in 0.19s**. `ruff check src/python/` printed **All checks passed!**. No production code changed, and none of the parity assertions found a defect.

## Task 2: Phase gate (commit cab0a182)

All gate runs were made on commit 0b9d4e31. Nothing under `src/python` changed after them; the only later change is 128-VALIDATION.md.

**Whole-tree ruff** (repo root): `ruff check src/python/` printed `All checks passed!`

**Coverage run (this is also the full-suite run):**
The first attempt failed with `unrecognized arguments: --cov` because the Poetry venv was empty and `poetry run` fell through to a global pipx pytest. I ran `poetry install --with dev --no-root`, which installed only the versions pinned in poetry.lock and left poetry.lock and pyproject.toml unchanged, then reran:

```
cd src/python && poetry run pytest --cov -q -p no:cacheprovider \
  --ignore=tests/unittests/test_controller/test_extract \
  --ignore=tests/unittests/test_controller/test_scan \
  --ignore=tests/integration/test_lftp
TOTAL                                    7111    882   1986    139    86%
FAIL Required test coverage of 88.0% not reached. Total coverage: 86.47%
12 failed, 1952 passed, 62 skipped, 2 warnings, 196 subtests passed in 29.83s
```

The 12 failures are all environment failures: 11 in `tests/unittests/test_ssh/test_sshcp.py` (needs the CI `testgroup` account) and `test_system/test_scanner.py::test_scan_file_with_latin_chars` (APFS illegal byte sequence). None of them involves arr code.

**Baseline comparison:** I ran the same command at the phase base b79b06fb in a temporary worktree, since removed. It gave `Total coverage: 86.39%`, the same 882 missed lines and the same 12 failures. The phase raised local coverage by 0.08 points. The shortfall comes from modules whose tests can't run here: controller/extract (21 to 45%), controller/scan (21 to 44%), lftp/lftp.py (78%) and ssh/sshcp.py (15%). Phase files: common/arr_api_key.py 100%, controller/arr_queue.py 98%, web/handler/config.py 97%.

**Verdict:** the coverage gate was **not** reproduced locally and is not marked as passed. Linux CI has to confirm 88 or more. Lint, every verification map row and all parity tests pass.

**Verification map:** I ran all 14 Automated Command rows from src/python. Each one selected at least one test and passed (counts range from 1 to 8 tests). I marked every row ✅ green, ticked Wave 0 and the sign-off items, set the front matter to `status: complete`, `nyquist_compliant: true` and `wave_0_complete: true`, and filled in the Approval line with the coverage caveat.

**Other acceptance checks:**
- `grep -rl 'API_KEY_CHARS' src/python --include='*.py' | grep -v '/tests/'` lists exactly `src/python/common/__init__.py` and `src/python/common/arr_api_key.py`
- `git diff b79b06fb..HEAD -- src/python/pyproject.toml`: empty, so fail_under and the ruff config are unchanged
- No `noqa` was added under src/python during the phase
- `git diff --stat b79b06fb..HEAD -- completion_gate.py common/config.py src/angular src/e2e`: empty

## ARR-02 fail-before / pass-after

- **Before the fix:** 128-03-SUMMARY.md quotes the RED failure at ff58eb7e from `test_padded_in_memory_key_is_sent_normalized`: `Expected: ... headers={'X-Api-Key': 's3cr3t-api-key-0123456789abcdef'} ... Actual: ... headers={'X-Api-Key': '  s3cr3t-api-key-0123456789abcdef\n'}`.
- **After the fix:** in this task, `pytest ... test_arr_queue.py -k padded` gave 2 passed. `test_arr_key_parity.py -k "all_three_paths or live_config"` gave 4 passed with 15 subtests, including the D-05 live-config padded key sent as the trimmed K by both Test Connection and the queue check.

## Deviations from Plan

**1. [Rule 3 - Blocking] Installed the locked dev dependencies into the empty Poetry venv**
- **Found during:** Task 2
- **Issue:** `poetry run pytest --cov` failed with `unrecognized arguments: --cov`. The venv held only pip, so the call resolved to a global pipx pytest.
- **Fix:** ran `poetry install --with dev --no-root`, as the plan's action allows. It installed only versions from the committed lock, and poetry.lock and pyproject.toml are unchanged.
- **Cost if wrong:** none for the repo; this changes only the local venv.
- **Commit:** none (environment only)

**2. [Environment] Local gate run excludes modules that only run on CI**
- **Found during:** Task 2
- **Issue:** test_extract hangs, test_scan fails on macOS spawn, and test_lftp and test_sshcp need the `testgroup` account. With those excluded, total coverage is 86.47%, below fail_under 88.
- **Handling:** fail_under was not lowered and no test was skipped or deleted. I measured the phase base under the same conditions (86.39%) to show the phase did not cause the shortfall. The result is recorded in 128-VALIDATION.md and here as not reproduced locally.
- **Cost if wrong:** if Linux CI also reports under 88, the shortfall is still not from this phase, since the base was lower, but it would block the CI gate and need a separate fix.

## Assumption Drift (advisory)

- **Found during:** Task 2. **Planned:** the coverage run reproduces the CI gate locally and passes at 88 or more. **Actual:** it can't on macOS; the local total is 86.47% with CI-only modules excluded. **Why:** environment limits in modules unrelated to arr code. **Cost if wrong:** the phase verifier must take the coverage result from CI, not from this summary.

## Known Stubs

None.

## Threat Flags

None. The change is test-only, and every key in the tests is an obvious fake.

## Self-Check: PASSED

- FOUND: src/python/tests/integration/test_web/test_handler/test_arr_key_parity.py
- FOUND: .planning/phases/128-arr-key-normalization/128-VALIDATION.md (nyquist_compliant: true)
- FOUND: commit 0b9d4e31
- FOUND: commit cab0a182
