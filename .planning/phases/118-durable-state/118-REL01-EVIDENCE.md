# Phase 118 REL-01 gate-1 evidence (fail-before / pass-after)

RED run executed against pre-fix code at `99de178` (branch `safety-patch-1.7.4`, the Plan 118-01 test-only commit, before any fix plan). The production tree at that SHA is byte-identical to `62aa868`, the last commit before this plan:

```
$ git diff --stat 62aa868 99de178 -- src/python/common ':!src/python/tests'
(empty)
```

```
$ git log --oneline -1 -- src/python/common/persist.py
9a3d8a6 Strip AI artifact signals and verbose comments from Python source
```

`src/python/common/persist.py` was last touched long before Phase 118, and `99de178` changes only `src/python/tests/unittests/test_common/test_persist.py` (`git show --stat 99de178`: 1 file changed). Every failure below is therefore a fail-before against the unfixed `Persist.to_file`, which opens the target with `open(file_path, "w")` (truncating it) before `to_str()` runs.

## RED (pre-fix) — Plan 118-01

**Command** (per-test exception types taken from the `--junitxml` of the same invocation):

```
cd src/python && poetry run pytest \
  tests/unittests/test_common/test_persist.py \
  tests/unittests/test_common/test_config.py \
  tests/unittests/test_seedsyncarr.py \
  -q -p no:cacheprovider -rf --tb=line --junitxml=<scratchpad>/118-red.xml
```

Executed in the main checkout at HEAD = `99de178`.

**Failures** (9). The node IDs are verbatim from the `-rf` short summary. This pytest version's `-rf --tb=line` summary prints no exception text, so the ` - <exception>` suffix is the first line of the `<failure message>` of the same test in the junit XML of the same run:

```
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_directory_fsync_failure_is_logged_not_raised_and_file_committed - AssertionError: no logs of level WARNING or higher triggered on seedsyncarr.Persist
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_failure_with_no_existing_target_leaves_directory_empty - AssertionError: OSError not raised
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_file_fsync_failure_leaves_original_and_no_temp - AssertionError: OSError not raised
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_interrupt_mid_write_cleans_up_and_preserves_original - AssertionError: ServiceExit not raised
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_replace_failure_leaves_original_and_no_temp - AssertionError: OSError not raised
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_serialization_failure_leaves_original_and_no_temp - AssertionError: b'ORIGINAL' != b'' : original file must be intact byte-for-byte
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_temp_creation_failure_leaves_original_and_no_temp - AssertionError: OSError not raised
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_temp_file_created_in_same_directory_as_target - AssertionError: Expected 'mkstemp' to have been called once. Called 0 times.
FAILED tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_write_failure_leaves_original_and_no_temp - AssertionError: b'ORIGINAL' != b'' : original file must be intact byte-for-byte
```

Breakdown: 8 spec regressions (7 PERSIST-01 failure points + 1 PERSIST-02 directory-fsync) plus 1 new-contract test (`test_temp_file_created_in_same_directory_as_target`, listed separately below). 8 + 1 = 9, matching the expected count from Plan 118-01.

**Failure types** (from the junit XML: 9 `AssertionError`, 0 errors). All nine failures are `AssertionError` raised by a behavioral assertion: two show the pre-fix truncation directly (`b'ORIGINAL' != b''`, the serialization and write cases), five show that the unfixed code never reaches the injected failure point (`OSError not raised` / `ServiceExit not raised`, because it never calls `tempfile.mkstemp`, `os.fsync` or `os.replace`), one shows that no directory-fsync warning is ever logged, and one shows `mkstemp` is never called. None of the nine is an ImportError, AttributeError, ModuleNotFoundError or TypeError. This holds by construction: every injection patches the global module attributes `os.fsync`, `os.replace` and `tempfile.mkstemp`, which exist on both old and new code and are the same objects `persist.py` resolves at call time. Targets such as `common.persist.tempfile.mkstemp` or `common.persist._fsync_directory` were deliberately not used because they do not exist before the fix and would produce a harness error instead of a behavioral RED.

**Summary line:** `9 failed, 82 passed, 1 warning in 0.16s`

**Ruff** (whole tree):
- `poetry run ruff check src/python/` (ruff 0.15.9, local Poetry env): `All checks passed!`
- `uvx ruff@0.15.22 check src/python/` (CI-pinned version): `All checks passed!`

**Preservation tests passing on pre-fix code** (part of the 82 passed; each must stay green through the fix):

- `test_persist.py::TestPersist::test_from_file`
- `test_persist.py::TestPersist::test_from_file_non_existing`
- `test_persist.py::TestPersist::test_from_file_tightens_permissive_permissions`
- `test_persist.py::TestPersist::test_to_file_non_existing`
- `test_persist.py::TestPersist::test_to_file_overwrite`
- `test_persist.py::TestPersist::test_to_file_sets_0600_permissions`
- `test_persist.py::TestPersist::test_to_file_overwrite_preserves_0600_permissions`
- `test_config.py::TestConfig::test_to_file` (settings.cfg write through `Persist.to_file`)
- `test_config.py::TestConfig::test_enable_new_install_encrypts_on_write`
- `test_seedsyncarr.py::TestSeedsyncarrReencrypt::test_enable_existing_plaintext_reencrypts` (startup re-encrypt hook, which rewrites settings.cfg via `to_file`)

| # | Failing test | Requirement | Decision |
|---|--------------|-------------|----------|
| 1 | `test_serialization_failure_leaves_original_and_no_temp` | PERSIST-01 | fix in 118-02 (serialize before touching the filesystem) |
| 2 | `test_write_failure_leaves_original_and_no_temp` | PERSIST-01 | fix in 118-02 (write goes to temp file, original untouched) |
| 3 | `test_file_fsync_failure_leaves_original_and_no_temp` | PERSIST-01 | fix in 118-02 (fsync temp before replace; cleanup + re-raise) |
| 4 | `test_replace_failure_leaves_original_and_no_temp` | PERSIST-01 | fix in 118-02 (`os.replace` commit point; cleanup + re-raise) |
| 5 | `test_temp_creation_failure_leaves_original_and_no_temp` | PERSIST-01 | fix in 118-02 (`tempfile.mkstemp` in target dir; error propagates unwrapped) |
| 6 | `test_failure_with_no_existing_target_leaves_directory_empty` | PERSIST-01 | fix in 118-02 (failed first save leaves nothing behind) |
| 7 | `test_interrupt_mid_write_cleans_up_and_preserves_original` | PERSIST-01 | fix in 118-02 (`except BaseException` cleanup covers `ServiceExit`) |
| 8 | `test_directory_fsync_failure_is_logged_not_raised_and_file_committed` | PERSIST-02 | fix in 118-02 (best-effort dir fsync, warning on `seedsyncarr.Persist`, no content in log) |

### New-contract tests (added with the fixes; not regressions)

These pin details of the new implementation rather than the spec failure contract, so they are not part of the RED evidence:

- `test_temp_file_created_in_same_directory_as_target`: fails pre-fix for a non-spec reason (`mkstemp` is never called, `Called 0 times`). Pins the temp file being created in the target's real directory so `os.replace` is a same-filesystem rename (no `EXDEV` on the Docker `/config` bind mount).
- `test_no_temp_after_success`: passes pre-fix. Pins that a successful save leaves the correct content, mode `0600`, and no temp file.

Sanity probe (not part of the record of code under test): the full `test_persist.py` was also run in a scratch copy of `src/python` with the RESEARCH Code Example 1 `to_file` substituted, and all 17 tests passed. This confirms the RED set is satisfiable by the planned fix without test edits; the production file in the repo was not changed.

## GREEN (post-fix) — Plan 118-02

_(recorded by Plan 118-02)_
