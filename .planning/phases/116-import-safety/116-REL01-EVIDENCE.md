# Phase 116 REL-01 gate-1 evidence (fail-before / pass-after)

RED run executed against pre-fix code at `c734c10` (branch `safety-patch-1.7.4`, before the RED test commit). No file under `src/python/controller/` was modified.

## RED (pre-fix) — Plan 116-01

**Command** (phase quick run, plus `-rf --tb=line`; per-test messages taken from `--junitxml` of the same command):

```
cd src/python && poetry run pytest \
  tests/unittests/test_controller/test_webhook_manager.py \
  tests/unittests/test_controller/test_auto_delete.py \
  tests/unittests/test_controller/test_auto_delete_rearm.py \
  tests/unittests/test_controller/test_controller_unit.py \
  tests/unittests/test_controller/test_controller.py \
  tests/unittests/test_controller/test_import_ambiguity.py \
  -q -p no:cacheprovider -rf --tb=line
```

**Failures** (8, every one an `AssertionError`; no ImportError/TypeError/AttributeError):

```
FAILED tests.unittests.test_controller.test_auto_delete.TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_block_delete_despite_legacy_full_coverage - AssertionError: Expected 'delete_local' to not have been called. Called 1 times.
FAILED tests.unittests.test_controller.test_auto_delete.TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_block_delete_without_imported_children_entry - AssertionError: Expected 'delete_local' to not have been called. Called 1 times.
FAILED tests.unittests.test_controller.test_auto_delete.TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_case_insensitive - AssertionError: Expected 'delete_local' to not have been called. Called 1 times.
FAILED tests.unittests.test_controller.test_auto_delete_rearm.TestAutoDeleteTerminalSkipsDoNotRearm::test_duplicate_basename_is_terminal_and_does_not_rearm - AssertionError: Expected 'delete_local' to not have been called. Called 1 times.
FAILED tests.unittests.test_controller.test_import_ambiguity.TestAmbiguousWebhookImport::test_duplicate_basename_within_one_pack_is_rejected - AssertionError: '{\n [385 chars]d": [],\n    "imported_children": {},\n    "ab[14 chars]}\n}' != '{\n [385 chars]d": [\n        "Pack"\n    ],\n    "imported_c[97 chars]}
FAILED tests.unittests.test_controller.test_import_ambiguity.TestAmbiguousWebhookImport::test_root_name_equal_to_child_basename_elsewhere_is_rejected - AssertionError: '{\n [409 chars]d": [],\n    "imported_children": {},\n    "ab[14 chars]}\n}' != '{\n [409 chars]d": [\n        "Rel.A"\n    ],\n    "imported_[100 chars]
FAILED tests.unittests.test_controller.test_import_ambiguity.TestAmbiguousWebhookImport::test_roots_differing_only_by_case_are_rejected - AssertionError: '{\n [412 chars]d": [],\n    "imported_children": {},\n    "ab[14 chars]}\n}' != '{\n [412 chars]d": [\n        "Movie.mkv"\n    ],\n    "impor[41 chars]}
FAILED tests.unittests.test_controller.test_import_ambiguity.TestAmbiguousWebhookImport::test_two_releases_sharing_sample_mkv_are_untouched - AssertionError: '{\n [404 chars]d": [],\n    "imported_children": {},\n    "ab[14 chars]}\n}' != '{\n [404 chars]d": [\n        "Rel.B"\n    ],\n    "imported_[100 chars]
```

The import-side diffs show the pre-fix code writing a release into the persisted `imported` list (and `imported_children`) for an ambiguous webhook name. Which root wins varies between runs (the `-rf --tb=line` run credited `Rel.A`/`sample.mkv` where the junit run credited `Rel.B`/`Rel.A`) because the last-writer-wins lookup depends on model iteration order; either way a release is credited, which is the defect.

**Summary line:** `8 failed, 323 passed, 12 warnings in 1.91s`

**Ruff** (`poetry run ruff check <worktree>/src/python/`, whole tree): `All checks passed!`

**Preservation tests passing on pre-fix code** (part of the 323 passed):
`test_unique_child_name_imports_and_arms_exactly_as_before`, `test_same_path_referenced_twice_is_one_match`, `test_duplicate_non_video_basenames_do_not_block_delete`.

| # | Failing test | Requirement | Decision |
|---|--------------|-------------|----------|
| 1 | `test_two_releases_sharing_sample_mkv_are_untouched` | IMPORT-01 | D-03 (criterion 1) |
| 2 | `test_roots_differing_only_by_case_are_rejected` | IMPORT-01 | D-01, D-03 (criterion 2) |
| 3 | `test_root_name_equal_to_child_basename_elsewhere_is_rejected` | IMPORT-01 | D-03 (criterion 3) |
| 4 | `test_duplicate_basename_within_one_pack_is_rejected` | IMPORT-01 | D-03, D-04, D-08 (criterion 4) |
| 5 | `test_duplicate_video_basenames_block_delete_despite_legacy_full_coverage` | IMPORT-01 | D-05, D-07 |
| 6 | `test_duplicate_video_basenames_block_delete_without_imported_children_entry` | IMPORT-01 | D-05, D-14 grandfather |
| 7 | `test_duplicate_video_basenames_case_insensitive` | IMPORT-01 | D-05 |
| 8 | `test_duplicate_basename_is_terminal_and_does_not_rearm` | IMPORT-01 | D-06 (terminal) |

## GREEN (post-fix) — Plan 116-03

pending
