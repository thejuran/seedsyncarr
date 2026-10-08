---
phase: 116-import-safety
plan: 01
subsystem: controller (webhook import + auto-delete)
tags: [python, pytest, webhook, auto-delete, regression, red-first]
requires: []
provides:
  - RED regression tests for IMPORT-01 (ambiguous webhook import, duplicate video basename delete guard)
  - IMPORT-02 preservation tests (unique child import, same path twice, non-video duplicates)
  - 116-REL01-EVIDENCE.md RED section for Phase 118 REL-01 gate 1
affects: [116-02, 116-03]
tech-stack:
  added: []
  patterns:
    - "End-to-end controller tests with a real WebhookManager and real ModelFile trees (shape-independent)"
    - "Legacy persist fixture via ControllerPersist.from_str, swapped into both Controller and AutoDeleteManager"
key-files:
  created:
    - src/python/tests/unittests/test_controller/test_import_ambiguity.py
    - .planning/phases/116-import-safety/116-REL01-EVIDENCE.md
  modified:
    - src/python/tests/unittests/test_controller/test_auto_delete.py
    - src/python/tests/unittests/test_controller/test_auto_delete_rearm.py
decisions:
  - "Rejection tests assert persist/timer state first, then filter the shared logger mock by the substring 'ambiguous' (wording aligned with Plan 02's suggested warning)"
  - "Terminal-skip test matches warnings starting \"Auto-delete skipped for 'Pack.S01'\" and containing 'more than one path' (wording aligned with Plan 03)"
metrics:
  duration: ~20 min
  completed: 2026-10-08
  tasks: 3
  files: 4
---

# Phase 116 Plan 01: RED regressions for import safety Summary

Eight shape-independent regression tests that each fail on the pre-fix code with an AssertionError. They prove two defects: a wrong-release webhook import credit, and a delete that goes ahead when two discs share one video basename. Three preservation tests pin today's unambiguous behavior and pass. All of it is recorded as REL-01 RED evidence.

## What was built

- `test_import_ambiguity.py` (new, 6 tests): `TestAmbiguousWebhookImport(BaseAutoDeleteTestCase)` uses a real `WebhookManager(self.mock_context)` injected into `Controller`, real `ModelFile` trees (`_leaf`/`_pack`) and `enqueue_import` followed by `controller.process()`. It never references the lookup shape (`name_to_root`/`name_to_paths`/`process.call_args`), so Plans 02/03 need no edits to it.
- `test_auto_delete.py`: new `TestAutoDeleteDuplicateBasenameGuard(TestAutoDeleteExecution)`, which covers D-07 legacy full coverage (persist swapped on both `_Controller__persist` and `_Controller__auto_delete_mgr._persist`), the D-14 grandfather path, case-insensitive duplicates, and the D-05a non-video preservation case.
- `test_auto_delete_rearm.py`: `test_duplicate_basename_is_terminal_and_does_not_rearm` in `TestAutoDeleteTerminalSkipsDoNotRearm`.
- `116-REL01-EVIDENCE.md`: RED section with the command, 8 FAILED lines, summary line, ruff result and requirement/decision table. The GREEN heading is marked `pending` for Plan 03.

## RED run (observed, pre-fix code at c734c10)

Phase quick run (6 controller test files) with `-q -p no:cacheprovider -rf`:

```
FAILED tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_block_delete_despite_legacy_full_coverage
FAILED tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_block_delete_without_imported_children_entry
FAILED tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_case_insensitive
FAILED tests/unittests/test_controller/test_auto_delete_rearm.py::TestAutoDeleteTerminalSkipsDoNotRearm::test_duplicate_basename_is_terminal_and_does_not_rearm
FAILED tests/unittests/test_controller/test_import_ambiguity.py::TestAmbiguousWebhookImport::test_duplicate_basename_within_one_pack_is_rejected
FAILED tests/unittests/test_controller/test_import_ambiguity.py::TestAmbiguousWebhookImport::test_root_name_equal_to_child_basename_elsewhere_is_rejected
FAILED tests/unittests/test_controller/test_import_ambiguity.py::TestAmbiguousWebhookImport::test_roots_differing_only_by_case_are_rejected
FAILED tests/unittests/test_controller/test_import_ambiguity.py::TestAmbiguousWebhookImport::test_two_releases_sharing_sample_mkv_are_untouched
8 failed, 323 passed, 12 warnings in 1.91s
```

All 8 failures are `AssertionError`: the delete-side failures are `Expected 'delete_local' to not have been called. Called 1 times.` and the import-side failures are persist `to_str()` diffs that show a release written into `imported`. Per-test messages are in the evidence file. Whole-tree ruff: `All checks passed!`. All pre-existing tests in the six files passed.

**The quick run is intentionally RED until Plans 02 and 03 land.** Plan 02 turns the 4 `test_import_ambiguity.py` failures green. Plan 03 turns the 4 delete-side failures green. A red quick run in the next wave is expected and is not a regression.

## Deviations from Plan

- **Commit granularity:** Task 3 of the plan specifies a single RED commit containing all three test files plus the evidence file, and its acceptance criteria check that exact file set. So Tasks 1 to 3 landed as one commit (`00fb62f`) instead of one commit per task.
- **Evidence message source:** with this pytest configuration the `-rf` short-summary lines print no exception message. So the evidence file pairs each FAILED test with its exception message from `--junitxml` output of the same command. The `--tb=line` output agreed: 8 `E   AssertionError` lines.

## Observations

- Which root the pre-fix code credits for an ambiguous name varies between runs (`Rel.A` vs `Rel.B`), because last-writer-wins follows model iteration order. The tests assert that persist is unchanged, so they fail whichever root wins.
- The local poetry venv reports `PytestUnknownMarkWarning: Unknown pytest.mark.timeout` (pytest-timeout plugin not loaded on this host). This was pre-existing, is out of scope, and did not affect results.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/python/tests/unittests/test_controller/test_import_ambiguity.py
- FOUND: .planning/phases/116-import-safety/116-REL01-EVIDENCE.md
- FOUND: commit 00fb62f (`test(116-01): ...`), touches exactly the 4 planned files; `git diff --quiet HEAD~1 HEAD -- src/python/controller/` exit 0
