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

All runs below are at the fix commit `d208acb` (branch `safety-patch-1.7.4`), from `src/python` with the main checkout's Poetry interpreter, `-p no:cacheprovider`.

### Fix commits

| Plan | Fix | SHA |
|------|-----|-----|
| 118-02 | `Persist.to_file` serializes first, writes a 0600 `mkstemp` temp file in the target's real directory, fsyncs it, commits with `os.replace`, removes the temp and re-raises the original exception on any failure before the commit, then fsyncs the directory best-effort (warning on `seedsyncarr.Persist`, path and error only) | `d208acb` |

```
$ git diff --stat 62aa868 d208acb -- src/python/common ':!src/python/tests'
 src/python/common/persist.py | 58 +++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 55 insertions(+), 3 deletions(-)
```

Exactly one production file changed. `from_file`, `Serializable`, `PersistError` and the on-disk format are unchanged. `PersistError` is never raised from `to_file`, so `_load_persist`'s corrupt-file backup-and-reset path is not reachable from a save failure.

### Targeted regressions

```
$ poetry run pytest tests/unittests/test_common/test_persist.py -v -k "TestPersistAtomicWrite" -p no:cacheprovider
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_directory_fsync_failure_is_logged_not_raised_and_file_committed PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_failure_with_no_existing_target_leaves_directory_empty PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_file_fsync_failure_leaves_original_and_no_temp PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_interrupt_mid_write_cleans_up_and_preserves_original PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_no_temp_after_success PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_replace_failure_leaves_original_and_no_temp PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_serialization_failure_leaves_original_and_no_temp PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_temp_creation_failure_leaves_original_and_no_temp PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_temp_file_created_in_same_directory_as_target PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_write_failure_leaves_original_and_no_temp PASSED
================= 10 passed, 7 deselected, 1 warning in 0.02s ==================
```

### Phase quick run

```
$ poetry run pytest tests/unittests/test_common/test_persist.py tests/unittests/test_common/test_config.py tests/unittests/test_seedsyncarr.py -q -p no:cacheprovider
91 passed, 1 warning in 0.12s
```

**Delta vs RED.** RED at `99de178`: `9 failed, 82 passed` (91 tests). GREEN at `d208acb`: `0 failed, 91 passed`. 82 + 9 = 91: the nine RED failures (8 spec regressions plus `test_temp_file_created_in_same_directory_as_target`) are now passing, no previously passing test regressed, and no test file changed between the two SHAs (`git diff --stat 99de178 d208acb -- src/python/tests` is empty).

### New-contract tests

- `test_temp_file_created_in_same_directory_as_target`: failed pre-fix (`mkstemp` never called), passes now. The temp file is created in `os.path.dirname(os.path.realpath(target))`.
- `test_no_temp_after_success`: passed pre-fix, still passes. Correct content, mode `0600`, no temp file left.

### Preservation re-run

All pass in the quick run above (verified by name in the `-v` output of the same three files):

- `test_persist.py::TestPersist` (all 7): `test_from_file`, `test_from_file_non_existing`, `test_from_file_tightens_permissive_permissions`, `test_to_file_non_existing`, `test_to_file_overwrite`, `test_to_file_sets_0600_permissions`, `test_to_file_overwrite_preserves_0600_permissions`
- `test_config.py::TestConfig::test_to_file`
- `test_config.py::TestConfig::test_enable_new_install_encrypts_on_write`
- `test_seedsyncarr.py::TestSeedsyncarrReencrypt::test_enable_existing_plaintext_reencrypts`

### Full host suite

- Part 1, every file except the four baseline files (`--ignore` on each of `test_ssh/test_sshcp.py`, `test_controller/test_scan/test_scanner_process.py`, `test_system/test_scanner.py`, `test_controller/test_extract/test_extract_process.py`): `1481 passed, 2 warnings in 40.53s`. 0 failed, 0 errors. The Phase 117 figure was 1471; the 10 extra are `TestPersistAtomicWrite`.
- Part 2, the baseline files run one at a time under `perl -e 'alarm 60; exec @ARGV' poetry run pytest <file> -q -p no:cacheprovider`:
  - `test_ssh/test_sshcp.py`: `11 failed`
  - `test_controller/test_scan/test_scanner_process.py`: `3 failed, 1 passed, 3 errors`
  - `test_system/test_scanner.py`: `1 failed, 19 passed`
  - `test_controller/test_extract/test_extract_process.py`: `6 failed in 33.97s` (pytest-timeout)
- Total: **21 failed / 3 errors**, all in the four pre-existing baseline files. This equals the Phase 116/117 baseline: unchanged, no new failures.
- Cross-check: an unfiltered `pytest tests/unittests -q` at the same SHA (the `--ignore` flags were accidentally collapsed into one argument by zsh, so nothing was ignored) gave `21 failed, 1501 passed, 3 errors`. 1481 + 20 baseline passes (1 + 19) = 1501, and 21 failed / 3 errors is the same baseline.

### Ruff (whole tree)

- `poetry run ruff check src/python/` (ruff 0.15.9, local Poetry env): `All checks passed!`
- `uvx ruff@0.15.22 check src/python/` (CI-pinned version): `All checks passed!`

### Coverage (informational, not a CI gate)

```
$ poetry run pytest tests/unittests --cov=. --cov-report=term -q -p no:cacheprovider <same four --ignore flags>
common/persist.py                          64      6      2      0    91%   82-84, 94-97
TOTAL                                    5973    754   1584    127    86%
FAIL Required test coverage of 88.0% not reached. Total coverage: 86.36%
1481 passed, 2 warnings in 44.29s
```

TOTAL is **86.36%**, below `fail_under = 88` in `pyproject.toml`. This is informational only: CI's `unittests-python` job runs pytest without `--cov` (RESEARCH F5), so `fail_under` is not enforced anywhere, and this host run excludes the four baseline files, whose modules (ssh, scanner, extract process) are therefore under-counted here. No earlier phase recorded a coverage figure, so there is no baseline to compare against. Surfaced to the owner at the Plan 118-04 checkpoint. The uncovered `persist.py` lines are the `fdopen`-failure `os.close` path (82-84) and the temp-unlink error branches (94-97).

One earlier coverage run at the same SHA reported `1 failed, 1480 passed`: `test_common/test_app_process.py::TestAppProcess::test_exception_propagates_with_traceback`. That test starts a spawned process, sleeps a fixed 0.2 s and expects the child's exception to have arrived; it does not touch persist. It passed in the plain part 1 run, passed 3/3 when run alone (twice with `--cov`, once without), and passed in the re-run above. It is recorded as a timing flake under coverage instrumentation, not a regression.

## REL-01 gate 1 — combined regression run (Phases 116-118)

One invocation at fix SHA `d208acb` covering every targeted RED regression from the three phases. The `-k` expression is the 42 test-function names extracted from the `FAILED` lines of `116-REL01-EVIDENCE.md` (8), `117-REL01-EVIDENCE.md` (26) and this file's RED section (8, excluding the new-contract `test_temp_file_created_in_same_directory_as_target`). All 42 names are unique across the nine files, and the run selected exactly those 42 (no name missing, no extra name matched).

```
$ cd src/python && poetry run pytest -v -p no:cacheprovider \
    tests/unittests/test_controller/test_auto_delete.py \
    tests/unittests/test_controller/test_auto_delete_rearm.py \
    tests/unittests/test_controller/test_import_ambiguity.py \
    tests/unittests/test_lftp/test_job_status_parser.py \
    tests/unittests/test_lftp/test_lftp_status_contract.py \
    tests/unittests/test_controller/test_auto_queue.py \
    tests/unittests/test_controller/test_transfer_state_safety.py \
    tests/unittests/test_controller/test_scan_clock_safety.py \
    tests/unittests/test_common/test_persist.py \
    -k "<the 42 test names joined with ' or '>"
tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_block_delete_despite_legacy_full_coverage PASSED
tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_block_delete_without_imported_children_entry PASSED
tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_case_insensitive PASSED
tests/unittests/test_controller/test_auto_delete_rearm.py::TestAutoDeleteTerminalSkipsDoNotRearm::test_duplicate_basename_is_terminal_and_does_not_rearm PASSED
tests/unittests/test_controller/test_import_ambiguity.py::TestAmbiguousWebhookImport::test_duplicate_basename_within_one_pack_is_rejected PASSED
tests/unittests/test_controller/test_import_ambiguity.py::TestAmbiguousWebhookImport::test_root_name_equal_to_child_basename_elsewhere_is_rejected PASSED
tests/unittests/test_controller/test_import_ambiguity.py::TestAmbiguousWebhookImport::test_roots_differing_only_by_case_are_rejected PASSED
tests/unittests/test_controller/test_import_ambiguity.py::TestAmbiguousWebhookImport::test_two_releases_sharing_sample_mkv_are_untouched PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_chunk_without_data_line_followed_by_chunk PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_chunk_without_data_line_followed_by_mirror_header PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_mirror_empty_followed_by_header_containing_getting_file_list PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_pget_no_data_line_followed_by_mirror_header PASSED
tests/unittests/test_lftp/test_job_status_parser.py::TestLftpJobStatusParser::test_jobs_pget_no_data_line_followed_by_pget_header PASSED
tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_boundary_sequence_pinned_exactly PASSED
tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_timed_out_status_with_empty_buffer_is_unavailable PASSED
tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_timed_out_status_with_partial_parseable_buffer_is_unavailable PASSED
tests/unittests/test_lftp/test_lftp_status_contract.py::TestLftpStatusBoundary::test_tolerated_parse_failures_report_unavailable_not_empty PASSED
tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_changed_size_after_remote_outage_restarts_window PASSED
tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueStabilityAndSweep::test_failed_remote_scans_spanning_window_do_not_establish_stability PASSED
tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_changed_local_size_after_outage_restarts_window PASSED
tests/unittests/test_controller/test_auto_queue.py::TestAutoQueueLocalStabilityGate::test_failed_local_scans_spanning_window_do_not_establish_local_idle PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_timed_out_status_with_empty_buffer_keeps_protection PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestStatusUnavailableKeepsTransferProtection::test_timed_out_status_with_partial_parseable_buffer_keeps_protection PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestControllerActiveListFrozenWhileStatusUnavailable::test_active_downloading_list_and_scanner_feed_unchanged_on_parse_failure PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_delete_local_in_one_process_does_not_delete PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_delete_remote_in_one_process_does_not_delete PASSED
tests/unittests/test_controller/test_transfer_state_safety.py::TestSameCycleCommandOrderingProtectsSubmittedTransfers::test_queue_then_extract_in_one_process_does_not_extract PASSED
tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_failed_local_scans_spanning_window_do_not_queue PASSED
tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_failed_remote_scans_spanning_window_do_not_queue PASSED
tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_local_recovery_with_changed_size_restarts_window PASSED
tests/unittests/test_controller/test_scan_clock_safety.py::TestStabilityOnSuccessfulScanClock::test_remote_recovery_with_changed_size_restarts_window PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_directory_fsync_failure_is_logged_not_raised_and_file_committed PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_failure_with_no_existing_target_leaves_directory_empty PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_file_fsync_failure_leaves_original_and_no_temp PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_interrupt_mid_write_cleans_up_and_preserves_original PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_replace_failure_leaves_original_and_no_temp PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_serialization_failure_leaves_original_and_no_temp PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_temp_creation_failure_leaves_original_and_no_temp PASSED
tests/unittests/test_common/test_persist.py::TestPersistAtomicWrite::test_write_failure_leaves_original_and_no_temp PASSED
================ 42 passed, 288 deselected, 1 warning in 0.21s =================
```

**Count check:** Phase 116: `test_auto_delete.py` 3 + `test_auto_delete_rearm.py` 1 + `test_import_ambiguity.py` 4 = 8. Phase 117: `test_job_status_parser.py` 5 + `test_lftp_status_contract.py` 4 + `test_auto_queue.py` 4 + `test_transfer_state_safety.py` 9 + `test_scan_clock_safety.py` 4 = 26. Phase 118: `TestPersistAtomicWrite` 8. **8 + 26 + 8 = 42**, 42 PASSED, 0 failed.

Each of the 42 has a recorded fail-before: the 8 Phase 116 tests in `116-REL01-EVIDENCE.md`, the 26 Phase 117 tests in `117-REL01-EVIDENCE.md`, and the 8 Phase 118 tests in this file's RED section.

Plan 118-03's release commit changes no file under `src/python` outside tests, so this run stands for the release SHA. Plan 118-03 proves that with `git diff --stat`.

## Release commit (Plan 118-03)

**Release commit:** `9398e7b` — `chore(release): v1.7.4 — safety patch (import, transfer-state, durable-state)` (branch `safety-patch-1.7.4`, not pushed, not tagged).

Files in the release commit (`git show --stat 9398e7b`): `CHANGELOG.md`, `package.json`, `release-notes.md`, `src/angular/package-lock.json`, `src/angular/package.json`, `src/python/pyproject.toml`.

### Release-metadata gate

```
$ npm run verify:release-metadata -- 1.7.4

> verify:release-metadata
> node scripts/verify-release-metadata.mjs 1.7.4

Release metadata matches 1.7.4:
- CHANGELOG.md has release section [1.7.4]
- release-notes.md links to CHANGELOG.md through the {{VERSION}} tag placeholder
- package.json version is 1.7.4
- src/angular/package.json version is 1.7.4
- src/angular/package-lock.json version is 1.7.4
- src/angular/package-lock.json packages[""].version is 1.7.4
(exit 0)
```

`npm run test:release-metadata` (`node --test scripts/verify-release-metadata.test.mjs`): `tests 21`, `pass 21`, `fail 0`.

### Production tree unchanged since the 118-02 fix

```
$ git diff --stat d208acb 9398e7b -- src/python ':!src/python/tests'
 src/python/pyproject.toml | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
```

The only production-tree change between the 118-02 fix commit and the release commit is the two version lines in `pyproject.toml`, so the combined REL-01 gate-1 regression run above stands for the release SHA.

### Owner decision: public backup check dropped (2026-10-09)

The owner decided the public release notes stay plain English for non-engineer self-hosters: stop the app, copy `settings.cfg`, `controller.persist` and `autoqueue.persist`, upgrade; a short rollback that puts the copies back, makes sure `[AutoDelete]` reads `enabled = False` in the restored `settings.cfg`, starts 1.7.2, and keeps auto-delete off until imports are reconciled. The `docker run --entrypoint python3 … from_str` loader-check command, its FAILED/do-not-start block and `sha256sum` steps are NOT in `release-notes.md`. The rigorous loader-based backup check remains in Plan 118-05 (NAS deploy) only.

### NAS scratch proof of the loader check (run before the owner decision; informational)

The proof had already run when the decision arrived. It is kept here because it validates the same loader approach Plan 118-05 uses, but the command is no longer published. Image `ghcr.io/thejuran/seedsyncarr:1.7.2`; scratch dir `/volume1/docker/seedsync-relnotes-check` (no production path or container touched); fixtures generated inside that image (`good` = `Seedsyncarr._create_default_config().to_str()`, `ControllerPersist().to_str()`, `AutoQueuePersist().to_str()`; `bad` = default INI cut immediately before its second section header, `{}`, `{"not_patterns": []}`). Command run:

```
sudo /usr/local/bin/docker run --rm --network none --entrypoint python3 -w /app/python \
  -v "/volume1/docker/seedsync-relnotes-check/<good|bad>:/c:ro" ghcr.io/thejuran/seedsyncarr:1.7.2 -c '
import sys
from common import Config
from controller.controller_persist import ControllerPersist
from controller.auto_queue import AutoQueuePersist
failed = 0
for name, loader in (("settings.cfg.pre-1.7.4", Config),
                     ("controller.persist.pre-1.7.4", ControllerPersist),
                     ("autoqueue.persist.pre-1.7.4", AutoQueuePersist)):
    try:
        with open("/c/" + name, encoding="utf-8") as f:
            loader.from_str(f.read())
        print("OK      " + name)
    except Exception as e:
        failed = 1
        print("FAILED  " + name + " (" + type(e).__name__ + ")")
sys.exit(failed)
'
```

Good set:

```
OK      settings.cfg.pre-1.7.4
OK      controller.persist.pre-1.7.4
OK      autoqueue.persist.pre-1.7.4
exit 0
```

Bad set:

```
FAILED  settings.cfg.pre-1.7.4 (ConfigError)
FAILED  controller.persist.pre-1.7.4 (PersistError)
FAILED  autoqueue.persist.pre-1.7.4 (PersistError)
exit 1
```

Scratch dir removed afterwards (`ls -d` → `No such file or directory`).

## Owner approval (Plan 118-04, D-02)

**Recorded:** 2026-10-09, owner reply relayed by the orchestrator (via AskUserQuestion) after the Plan 118-04 decision packet was shown.

**Owner reply (verbatim option):** `approve-as-drafted`

| Item | Decision | Status |
|------|----------|--------|
| (a) Public rollback target in release notes | `ghcr.io/thejuran/seedsyncarr:1.7.2` (plus "re-pin whatever you ran before") | confirmed |
| (b) CHANGELOG fold of the never-tagged `[1.7.3]` block into `[1.7.4]` | keep the fold with the "never tagged" line | confirmed |
| (c) Coverage 86.36% vs `fail_under = 88` | informational only, not blocking (CI does not enforce it) | confirmed |
| (d) wud semver tag filter | apply label `wud.tag.include=^\d+\.\d+\.\d+$` to the seedsyncarr service during the Plan 118-05 deploy, before wud is restarted | confirmed |
| (e) Compose-file edit method | inode-preserving in-place edit (write a copy, `cat` it over the original), `ls -i` verified before/after | confirmed |

No amendments requested; release text stays at `eece2e3` (`npm run verify:release-metadata -- 1.7.4` re-run at the checkpoint: exit 0).

**NAS rollback reference for Plan 118-05:** `ghcr.io/thejuran/seedsyncarr:357` @ `sha256:87ca66959391846d11fa1d0539601f18faba2294d880934041f8fc040a6d4e9f` (staging tag carrying 1.7.3 code; the true pre-upgrade rollback point for the NAS, not published in the public notes).

## wud suspension (Plan 118-04, codex pass-2 finding 1)

Done before any `git push` in Phase 118.

Pre-check (production not yet moved):

```
$ ssh nas "sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Config.Image}} {{.State.Status}}'"
ghcr.io/thejuran/seedsyncarr:357 running
```

WUD_STOP_TIME: `2026-10-09 08:30:13 -0500` (NAS `date`)

```
$ ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose stop wud'
 Container wud  Stopping
 Container wud  Stopped
$ ssh nas "sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}} {{.State.FinishedAt}}'"
exited 2026-10-09T13:30:24.980056336Z
# re-check after 10 s
exited 2026-10-09T13:30:24.980056336Z
```

Production re-checked after the stop: `ghcr.io/thejuran/seedsyncarr:357 running` (untouched).

wud remains stopped until Plan 118-05 restores it after the deploy is verified or a rollback completes; all NAS auto-updates are paused meanwhile.

## Merge and tag (Plan 118-04)

Run after the owner approval and the verified wud suspension above (both committed on `safety-patch-1.7.4` before the first push: `b652e57`, `e86d7df`).

```
$ git fetch origin && git rev-parse origin/main
f8c94e9dfd7057af47300fc7906ac333ea591780        # unchanged since planning
$ git checkout main && git push origin main
   f8c94e9..c734c10  main -> main                # planning commits first (D-05)
$ git merge --no-ff safety-patch-1.7.4 -m "Merge safety-patch-1.7.4: release v1.7.4 (Phases 116-118)"
$ git push origin main
   c734c10..f6ff78a  main -> main
$ git tag -a v1.7.4 -m "v1.7.4 — safety patch: import ambiguity, transfer-state safety, durable state"
$ git push origin v1.7.4
 * [new tag]         v1.7.4 -> v1.7.4
```

| Item | Value |
|------|-------|
| `origin/main` before | `f8c94e9dfd7057af47300fc7906ac333ea591780` |
| `origin/main` after planning push | `c734c10` |
| Merge commit / `origin/main` after | `f6ff78ac5c599d5fb05f567906d56227b1c268f1` |
| `git rev-parse v1.7.4` (tag object) | `8ef7a225034c9b1eda1a0491468d82832d8c8174` |
| `git rev-parse v1.7.4^{}` | `f6ff78ac5c599d5fb05f567906d56227b1c268f1` (== `origin/main`) |
| `git cat-file -t v1.7.4` | `tag` (annotated) |
| `git log --oneline origin/main \| wc -l` | 1427 → 1547 (+120, history preserved, no squash) |
| `git log --oneline f8c94e9..origin/main -- .planning/ \| wc -l` | 87 |

```
$ git log --oneline -3 main
f6ff78a Merge safety-patch-1.7.4: release v1.7.4 (Phases 116-118)
e86d7df docs(118-04): record wud suspension for the release window
b652e57 docs(118-04): record owner approval for 1.7.4
```

wud re-checked after the tag push: `exited`.

## Tag and CI (Plan 118-04)

**Run:** `37937393805`, https://github.com/thejuran/seedsyncarr/actions/runs/37937393805 (`refs/tags/v1.7.4`, event `push`). **Conclusion: `failure`**, in the PyPI publish job only.

| Job | Conclusion |
|-----|------------|
| Release metadata verifier tests | success |
| Python unit tests | success |
| Angular unit tests | success |
| Lint (Python) | success |
| Lint (Angular) | success |
| Build Docker Image | success |
| End-to-end tests on Docker Image (amd64) | success |
| End-to-end tests on Docker Image (arm64) | success |
| Verify release metadata | success |
| Publish Docker Image | success (`:1.7.4` and `:latest` pushed to GHCR) |
| Publish GitHub Release | success |
| Publish Documentation | success |
| **Publish to PyPI** | **failure** |
| Publish Docker Image (:dev) | skipped (tag run) |

GitHub Release: `gh release view v1.7.4` → https://github.com/thejuran/seedsyncarr/releases/tag/v1.7.4, `isDraft=false`, body contains `blob/v1.7.4/CHANGELOG.md`.

### PyPI failure (`gh run view 37937393805 --log-failed`, excerpt)

```
Uploading distributions to https://upload.pypi.org/legacy/
INFO  src/python/dist/seedsyncarr-1.7.4-py3-none-any.whl (772.4 KB)
INFO  src/python/dist/seedsyncarr-1.7.4.tar.gz (693.1 KB)
Uploading seedsyncarr-1.7.4-py3-none-any.whl
INFO  Response from https://upload.pypi.org/legacy/:
      400 Bad Request
      400 Invalid distribution file. Archive member path is not normalized: './.gitignore'
ERROR HTTPError: 400 Bad Request from https://upload.pypi.org/legacy/
```

PyPI rejected the very first file, so nothing for 1.7.4 was accepted: `https://pypi.org/pypi/seedsyncarr/json` still lists releases up to `1.7.2` only. The version number 1.7.4 is therefore not burned on PyPI.

Cause (diagnosis, not yet fixed): the PyPI job runs `pip install build && python -m build` with no version pins. Nothing in `src/python/pyproject.toml` or `.github/workflows/ci.yml` changed between `v1.7.2` (PyPI publish succeeded, run `34002932571`) and `v1.7.4`, apart from the two version lines. So the `./.gitignore` member comes from a newer unpinned build backend or a newer PyPI upload check, not from Phase 116-118 code. Fixing it needs a commit (packaging exclude or pinned builder). Per the plan the tag was **not** moved or deleted: whether to ship 1.7.5 or re-publish 1.7.4 to PyPI is the owner's call.


### wud status at the failure stop

```
$ ssh nas "sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}}'"
exited
$ ssh nas "sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Config.Image}} {{.State.Status}}'"
ghcr.io/thejuran/seedsyncarr:357 running
```

wud remains stopped. Owner decision on restoring it: keep it stopped (see below).

### Owner decision on the PyPI failure (2026-10-09), accepted deviation

Owner reply relayed by the orchestrator: **option (a)**. Ship 1.7.4 through Docker and GitHub without PyPI. The PyPI packaging fix (`packages = ["."]` in `src/python/pyproject.toml` produces `./`-prefixed archive members, which PyPI now rejects; confirmed by rebuilding the wheel from `v1.7.4` locally: every member is listed as `./…`) ships as follow-up **1.7.5**, together with open Dependabot alert #93 (`source-map-js >= 1.2.2`). Keep wud stopped. Do not move or delete the `v1.7.4` tag, and do not re-run the PyPI job.

Accepted deviation from the Task 3 success criterion "every job green". Every test, e2e, metadata, Docker publish and GitHub Release job is green; only `Publish to PyPI` failed, and nothing was uploaded to PyPI.

The four `docs(118-04)` evidence commits after the merge (`aeac94f` onwards) stay **local on `main`** and are not pushed now. They are `.planning`-only, and every push to `main` publishes a new numbered staging image through CI. They go out with the next push that is needed anyway.

### Published :1.7.4 image on the NAS (pull only; production untouched)

```
$ ssh nas "sudo /usr/local/bin/docker pull ghcr.io/thejuran/seedsyncarr:1.7.4"
Digest: sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595
Status: Downloaded newer image for ghcr.io/thejuran/seedsyncarr:1.7.4
$ ssh nas "sudo /usr/local/bin/docker image inspect ghcr.io/thejuran/seedsyncarr:1.7.4 --format '{{json .RepoDigests}}'"
["ghcr.io/thejuran/seedsyncarr@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595"]
$ ssh nas "sudo /usr/local/bin/docker image inspect ghcr.io/thejuran/seedsyncarr:1.7.4 --format '{{.Id}} {{.Architecture}}'"
sha256:0e33b030b41004f077d05742286b5599506f27e171b624b6c5122d59811c6d45 amd64
```

DIGEST=sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595
NAS_IMAGE_ID=sha256:0e33b030b41004f077d05742286b5599506f27e171b624b6c5122d59811c6d45

Plan 118-05 reference: `ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595` (smoke test, compose pin, deploy). The smoke container's `.Image` must equal NAS_IMAGE_ID.

Recorded at NAS time `2026-10-09 08:52:10 -0500`. Checked right after the pull: wud `exited`; production `ghcr.io/thejuran/seedsyncarr:357 running` (not touched).

## Smoke test on NAS (Plan 118-05, REL-01 gate 3)

Run 2026-10-09 08:54 to 09:05 -0500 (NAS `date`). Scratch only: containers `seedsyncarr-smoke` and `seedsyncarr-smoke-remote`, network `seedsyncarr-smoke-net`, dirs under `/volume1/docker/seedsync-smoke-1.7.4`. Nothing touched `/volume1/docker/seedsync`, the compose file, the production `seedsyncarr` container or wud. The scratch sshd password was generated on the NAS (`openssl rand -hex 16`), never printed, and is not in this file.

DIGEST=sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595
IMG=ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595
SMOKE_IMAGE_ID=sha256:0e33b030b41004f077d05742286b5599506f27e171b624b6c5122d59811c6d45

SMOKE_IMAGE_ID equals NAS_IMAGE_ID from §Tag and CI and the step 0 `.Id`.

### Step 0: preconditions

```
$ ssh nas "sudo /usr/local/bin/docker inspect wud --format '{{.State.Status}}'"
exited
$ ssh nas "sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Config.Image}} {{.State.Status}}'"
ghcr.io/thejuran/seedsyncarr:357 running
$ ssh nas id jule1651
uid=1026(jule1651) gid=100(users) groups=100(users),101(administrators)
$ ssh nas "sudo /usr/local/bin/docker image inspect $IMG --format '{{.Id}} {{json .RepoDigests}}'"
sha256:0e33b030b41004f077d05742286b5599506f27e171b624b6c5122d59811c6d45 ["ghcr.io/thejuran/seedsyncarr@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595"]
port 8801 in use: no (grep exit 1); seedsyncarr-smoke* containers/networks: none; scratch dir: absent
```

PUID=1026, PGID=100.

### Steps 1-2: scratch network, dirs, disposable sshd remote

Steps 1-4 ran as one remote script (`ssh nas bash -s < script`, `set -euo pipefail`, no `set -x`).

```
$ sudo /usr/local/bin/docker network create seedsyncarr-smoke-net && mkdir -p /volume1/docker/seedsync-smoke-1.7.4/config /volume1/docker/seedsync-smoke-1.7.4/downloads
b20469d94ff27c5f380bc4a32178737d26b672fb46806552ea08550f52959460
$ sudo /usr/local/bin/docker pull debian:bookworm-slim
docker.io/library/debian:bookworm-slim
$ sudo /usr/local/bin/docker run -d --name seedsyncarr-smoke-remote --label wud.watch=false --network seedsyncarr-smoke-net --env-file <0600 tmpfile with SMOKE_PW, deleted right after> debian:bookworm-slim bash -c '<apt install openssh-server; useradd smokeuser; chpasswd; 1 MiB /dev/urandom file; sha256sum; ssh-keygen -A; exec sshd -D -e>'
REMOTE_NOT_READY      # 120 s poll expired while apt was still installing on the NAS
```

The remote kept starting and logged `Server listening` about 2 minutes later. Because the first script had exited, its password variable was gone. A resume script generated a fresh password on the NAS and set it via stdin, so it never appeared on a command line:

```
$ printf 'smokeuser:<redacted>' | sudo /usr/local/bin/docker exec -i seedsyncarr-smoke-remote chpasswd
CHPASSWD_OK
$ sudo /usr/local/bin/docker logs seedsyncarr-smoke-remote 2>&1 | grep 'Server listening'
Server listening on 0.0.0.0 port 22.
Server listening on :: port 22.
REMOTE_SHA=94bb4071069cffe028c77e5645eaab36e67bcd878819a85bec9fe88d557c249c
```

No port was published for the remote. It was reachable only on the scratch bridge network.

### Step 3: app on the published digest (BEFORE state)

```
$ sudo /usr/local/bin/docker run -d --name seedsyncarr-smoke --label wud.watch=false --network seedsyncarr-smoke-net -e PUID=1026 -e PGID=100 -p 8801:8800 -v /volume1/docker/seedsync-smoke-1.7.4/config:/config -v /volume1/docker/seedsync-smoke-1.7.4/downloads:/downloads ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595
6307d01c47b3fca773c0d39f91acb4a48e2d1402ed2676331eca485cf20ac86d
$ sudo /usr/local/bin/docker inspect seedsyncarr-smoke --format '{{.Image}}'
sha256:0e33b030b41004f077d05742286b5599506f27e171b624b6c5122d59811c6d45
$ sudo /usr/local/bin/docker inspect seedsyncarr-smoke --format '{{.State.Status}}'
running
$ curl -fsS -m 5 http://localhost:8801/server/status   # BEFORE (default config)
{"server": {"up": false, "error_msg": "The settings are not fully configured."}, "controller": {"latest_local_scan_time": null, "latest_remote_scan_time": null, "latest_remote_scan_failed": null, "latest_remote_scan_error": null}, "storage": {"local_total": null, "local_used": null, "remote_total": null, "remote_used": null}}
```

This is the BEFORE state, not a pass: `up: false` on the incomplete default config.

### Step 4: complete config

```
set lftp/remote_address=seedsyncarr-smoke-remote -> HTTP 200
set lftp/remote_username=smokeuser -> HTTP 200
set lftp/remote_password=<redacted> -> HTTP 200      # body built on the NAS with printf from the shell variable
set lftp/remote_port=22 -> HTTP 200
set lftp/remote_path=/home/smokeuser/files -> HTTP 200
set lftp/local_path=/downloads -> HTTP 200
set lftp/use_ssh_key=false -> HTTP 200
set autoqueue/remote_stability_seconds=0 -> HTTP 200
set autoqueue/local_stability_seconds=0 -> HTTP 200
set sonarr/sonarr_url=http://smoke-test.invalid:8989 -> HTTP 200
$ sudo /usr/local/bin/docker restart seedsyncarr-smoke
seedsyncarr-smoke
```

### Step 5: startup (AFTER state)

```
$ curl -fsS -m 5 http://localhost:8801/server/status | jq -e '.server.up == true'    # polled, passed
STARTUP: server.up == true
$ curl -fsS -m 5 http://localhost:8801/server/status   # AFTER complete config
{"server": {"up": true, "error_msg": null}, "controller": {"latest_local_scan_time": "1791554354.941289", "latest_remote_scan_time": "1791554344.948798", "latest_remote_scan_failed": false, "latest_remote_scan_error": null}, "storage": {"local_total": 76780498186240, "local_used": 36172160024576, "remote_total": 76780498186240, "remote_used": 36172160126976}}
$ sudo /usr/local/bin/docker logs --tail 60 seedsyncarr-smoke 2>&1 | grep -cE 'Traceback|Backing up'
0
```

Verdict, startup: **PASS**.

### Step 6: transfer status (real controller, real LFTP transfer)

```
# 6a: remote scan (scanfs copied to and run on the remote over ssh)
SCAN_OK=1
$ curl -fsS -m 5 http://localhost:8801/server/status | jq -c .controller
{"latest_local_scan_time":"1791554354.941289","latest_remote_scan_time":"1791554344.948798","latest_remote_scan_failed":false,"latest_remote_scan_error":null}

# 6b: model stream
$ curl -sN -m 90 http://localhost:8801/server/stream | grep -m1 -oE '"name": *"smoke-1MiB.bin"[^}]*"state": *"downloaded"'
"name": "smoke-1MiB.bin", "is_dir": false, "state": "downloaded"
states seen for smoke-1MiB.bin: downloaded
# By the time the stream was opened, the transfer had already finished, so the
# model-init event carried the file as downloaded. No queued/downloading lines were captured.

# 6c: bytes
$ ls -l /volume1/docker/seedsync-smoke-1.7.4/downloads/smoke-1MiB.bin
-rwxrwxrwx+ 1 jule1651 users 1048576 Oct  9 08:58 /volume1/docker/seedsync-smoke-1.7.4/downloads/smoke-1MiB.bin
$ sha256sum /volume1/docker/seedsync-smoke-1.7.4/downloads/smoke-1MiB.bin | cut -d' ' -f1
94bb4071069cffe028c77e5645eaab36e67bcd878819a85bec9fe88d557c249c
remote (REMOTE_SHA): 94bb4071069cffe028c77e5645eaab36e67bcd878819a85bec9fe88d557c249c
```

Verdict, transfer status: **PASS**. The remote scan succeeded, the model reached `downloaded`, the size is 1048576 bytes, and the sha256 matches.

### Step 7: settings persistence

```
$ grep -c smoke-test.invalid /volume1/docker/seedsync-smoke-1.7.4/config/settings.cfg
1
$ grep -c seedsyncarr-smoke-remote /volume1/docker/seedsync-smoke-1.7.4/config/settings.cfg
1
$ ls -la /volume1/docker/seedsync-smoke-1.7.4/config
total 12
drwxrwxrwx+ 1 jule1651 users  100 Oct  9 08:59 .
drwxrwxrwx+ 1 jule1651 users   30 Oct  9 08:54 ..
-rw-------  1 jule1651 users   22 Oct  9 08:59 autoqueue.persist
-rw-------  1 jule1651 users  137 Oct  9 08:59 controller.persist
drwxrwxrwx+ 1 jule1651 users   58 Oct  9 08:58 log
-rw-------  1 jule1651 users 1181 Oct  9 08:59 settings.cfg
$ ls -a /volume1/docker/seedsync-smoke-1.7.4/config | grep -c '\.tmp$'
0
```

Verdict, settings persistence: **PASS**.

### Step 8: restart

```
$ sudo /usr/local/bin/docker restart seedsyncarr-smoke
seedsyncarr-smoke
RESTART: server.up == true
{"server": {"up": true, "error_msg": null}, "controller": {"latest_local_scan_time": null, "latest_remote_scan_time": null, "latest_remote_scan_failed": null, "latest_remote_scan_error": null}, "storage": {"local_total": null, "local_used": null, "remote_total": null, "remote_used": null}}
$ curl -fsS -m 5 http://localhost:8801/server/config/get | grep -o smoke-test.invalid
smoke-test.invalid
# after the first post-restart scans (about 30 s later):
$ curl -fsS -m 5 http://localhost:8801/server/status | jq -c .controller
{"latest_local_scan_time":"1791554418.990393","latest_remote_scan_time":"1791554408.991557","latest_remote_scan_failed":false,"latest_remote_scan_error":null}
$ curl -sN -m 8 http://localhost:8801/server/stream   # first model-init event
"name": "smoke-1MiB.bin", "is_dir": false, "state": "downloaded"
```

The first `model-init` read, taken immediately after the restart and before any scan, did not list the file. After the first scans it lists `smoke-1MiB.bin` as `downloaded`.

Container log over the whole run: `grep -cE 'Traceback|Backing up'` = 1. The single hit is a shutdown-time traceback, not a startup one:

```
2026-10-09 13:59:21,455 - INFO - seedsyncarr (MainProcess/MainThread) - Exiting Seedsyncarr
2026-10-09 13:59:21,558 - ERROR - seedsyncarr.ScanManager (MainProcess/ControllerJob) - Scanner process(es) died unexpectedly: RemoteScanner, LocalScanner, ActiveScanner
2026-10-09 13:59:21,558 - ERROR - seedsyncarr.ControllerJob (MainProcess/ControllerJob) - Caught exception in job ControllerJob
Traceback (most recent call last):
  ... controller/scan_manager.py, line 201, in _check_process_health
    raise ScannerProcessDiedError(
```

This is the same shutdown race that production `:357` already logs on every stop. Read-only grep of the production log (`/volume1/docker/seedsync/log/seedsyncarr.log*`) shows it on 2026-09-06, 2026-09-16 and 2026-10-05, each about 100-350 ms after `Exiting Seedsyncarr`. It is not new in 1.7.4. There is no `Backing up` line.

Verdict, restart: **PASS**.

### Step 8b: backup checker self-test (codex pass-4)

The script is `parse_check.py`, committed byte-identical as `.planning/phases/118-durable-state/118-05-parse_check.py`. The fixture generator is `118-05-gen_fixtures.py` (sha256 `984228092f9a8e672c24d7ede0b0dbb4f5ef5a8ef7c291c2a4a9abd10c2060e9`).

PARSE_CHECK_SHA=920363ac3693d1528ece37114e870cf00cb8b75b718663bc2ef5d446b3f5dd53

**Flag change, recorded and carried into Task 3.** The first full run used the planned flags (`--rm -i --read-only --network none --cap-drop ALL`). All good, bad, mixed and cross outputs matched expectations. The real-file run on the smoke app's own `-rw-------` files, however, printed:

```
FAIL settings.cfg PermissionError
FAIL controller.persist PermissionError
FAIL autoqueue.persist PermissionError
PARSE_FAIL
EXIT=1
```

`--cap-drop ALL` removes `CAP_DAC_OVERRIDE`, so the in-container root user cannot read 0600 files owned by uid 1026. The checker failed closed, as it should. The fix is `--user 1026:100`, which reads as the file owner and keeps every other restriction. The production files have the same owner and mode, so Task 3 must use the same flag. The whole self-test was then re-run with the final flags. Everything below is that re-run.

Final checker flags: `--rm -i --read-only --user 1026:100 --network none --cap-drop ALL --entrypoint python3 -w /app/python -v <dir>:/c:ro`

```
### image ghcr.io/thejuran/seedsyncarr:357 (fixtures .../parsecheck-selftest/357)
$ sudo /usr/local/bin/docker run --rm -i --network none --cap-drop ALL --entrypoint python3 -w /app/python -v /volume1/docker/seedsync-smoke-1.7.4/parsecheck-selftest/357:/c ghcr.io/thejuran/seedsyncarr:357 - < gen_fixtures.py
/c/good/settings.cfg 1117
/c/good/controller.persist 137
/c/good/autoqueue.persist 22
/c/bad/settings.cfg 123
/c/bad/controller.persist 2
/c/bad/autoqueue.persist 20
/c/mixed/settings.cfg 1117
/c/mixed/controller.persist 137
/c/mixed/autoqueue.persist 20
$ sudo /usr/local/bin/docker run --rm -i --read-only --user 1026:100 --network none --cap-drop ALL --entrypoint python3 -w /app/python -v /volume1/docker/seedsync-smoke-1.7.4/parsecheck-selftest/357:/c:ro ghcr.io/thejuran/seedsyncarr:357 - good/settings.cfg good/controller.persist good/autoqueue.persist < parse_check.py
PASS settings.cfg loader=Config
AutoDelete.enabled=False
PASS controller.persist loader=ControllerPersist
PASS autoqueue.persist loader=AutoQueuePersist
PARSE_OK
EXIT=0
$ ... :357 - bad/settings.cfg bad/controller.persist bad/autoqueue.persist < parse_check.py
FAIL settings.cfg ConfigError
FAIL controller.persist PersistError
FAIL autoqueue.persist PersistError
PARSE_FAIL
EXIT=1
$ ... :357 - mixed/settings.cfg mixed/controller.persist mixed/autoqueue.persist < parse_check.py
PASS settings.cfg loader=Config
AutoDelete.enabled=False
PASS controller.persist loader=ControllerPersist
FAIL autoqueue.persist PersistError
PARSE_FAIL
EXIT=1

### image ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595 (fixtures .../parsecheck-selftest/174)
$ sudo /usr/local/bin/docker run --rm -i --network none --cap-drop ALL --entrypoint python3 -w /app/python -v /volume1/docker/seedsync-smoke-1.7.4/parsecheck-selftest/174:/c ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595 - < gen_fixtures.py
/c/good/settings.cfg 1117
/c/good/controller.persist 137
/c/good/autoqueue.persist 22
/c/bad/settings.cfg 123
/c/bad/controller.persist 2
/c/bad/autoqueue.persist 20
/c/mixed/settings.cfg 1117
/c/mixed/controller.persist 137
/c/mixed/autoqueue.persist 20
$ sudo /usr/local/bin/docker run --rm -i --read-only --user 1026:100 --network none --cap-drop ALL --entrypoint python3 -w /app/python -v /volume1/docker/seedsync-smoke-1.7.4/parsecheck-selftest/174:/c:ro ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595 - good/settings.cfg good/controller.persist good/autoqueue.persist < parse_check.py
PASS settings.cfg loader=Config
AutoDelete.enabled=False
PASS controller.persist loader=ControllerPersist
PASS autoqueue.persist loader=AutoQueuePersist
PARSE_OK
EXIT=0
$ ... :1.7.4@DIGEST - bad/settings.cfg bad/controller.persist bad/autoqueue.persist < parse_check.py
FAIL settings.cfg ConfigError
FAIL controller.persist PersistError
FAIL autoqueue.persist PersistError
PARSE_FAIL
EXIT=1
$ ... :1.7.4@DIGEST - mixed/settings.cfg mixed/controller.persist mixed/autoqueue.persist < parse_check.py
PASS settings.cfg loader=Config
AutoDelete.enabled=False
PASS controller.persist loader=ControllerPersist
FAIL autoqueue.persist PersistError
PARSE_FAIL
EXIT=1

### cross: :357-generated good set checked by :1.7.4@DIGEST (what the deploy relies on)
PASS settings.cfg loader=Config
AutoDelete.enabled=False
PASS controller.persist loader=ControllerPersist
PASS autoqueue.persist loader=AutoQueuePersist
PARSE_OK
EXIT=0

### cross (informative): 1.7.4-generated good set checked by :357 (rollback caveat)
PASS settings.cfg loader=Config
AutoDelete.enabled=False
PASS controller.persist loader=ControllerPersist
PASS autoqueue.persist loader=AutoQueuePersist
PARSE_OK
EXIT=0

### real files: smoke app config (written and loaded by 1.7.4 in steps 4-8) checked by :1.7.4@DIGEST
$ sudo /usr/local/bin/docker run --rm -i --read-only --user 1026:100 --network none --cap-drop ALL --entrypoint python3 -w /app/python -v /volume1/docker/seedsync-smoke-1.7.4/config:/c:ro ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129ddfe0da97bd739efe7044ff3cfc30577976550933cbc3b68bb1801595 - settings.cfg controller.persist autoqueue.persist < parse_check.py
PASS settings.cfg loader=Config
AutoDelete.enabled=False
PASS controller.persist loader=ControllerPersist
PASS autoqueue.persist loader=AutoQueuePersist
PARSE_OK
EXIT=0
```

The `ConfigError` on the bad `settings.cfg` (123 bytes, cut right before the second section header) proves `configparser` accepted the file and `Config.from_dict` rejected it. A syntax-only check would have passed it. The rollback caveat is clear: `:357` reads 1.7.4-written default files.

SELFTEST_OK

Verdict, checker self-test: **PASS**.

### Step 9: cleanup

```
$ sudo /usr/local/bin/docker rm -f seedsyncarr-smoke seedsyncarr-smoke-remote
seedsyncarr-smoke
seedsyncarr-smoke-remote
$ sudo /usr/local/bin/docker network rm seedsyncarr-smoke-net
seedsyncarr-smoke-net
$ rm -rf /volume1/docker/seedsync-smoke-1.7.4
scratch dir removed
$ sudo /usr/local/bin/docker ps -a --format '{{.Names}}' | grep -c seedsyncarr-smoke
0
$ sudo /usr/local/bin/docker network ls --format '{{.Name}}' | grep -c seedsyncarr-smoke-net
0
```

`debian:bookworm-slim` is left cached on the NAS. It is unused and harmless. The password variable ended with each remote shell session (the first session also ran `unset PW`).

End state at 2026-10-09 09:05:39 -0500: wud `exited`; production `ghcr.io/thejuran/seedsyncarr:357 running` (unchanged).

### Verdicts

| Sub-gate | Verdict |
|----------|---------|
| Startup (`server.up` true after the complete config) | PASS |
| Transfer status (scan ok, `downloaded`, sha256 match) | PASS |
| Settings persistence (values in `settings.cfg`, `-rw-------`, 0 `.tmp`) | PASS |
| Restart (value survives, `server.up` true, model restored) | PASS |
| Checker self-test (both images, SELFTEST_OK) | PASS |

**Overall: PASS** on `:1.7.4@sha256:682d129d…1595`, platform image `sha256:0e33b030…6d45`.
