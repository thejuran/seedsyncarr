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
