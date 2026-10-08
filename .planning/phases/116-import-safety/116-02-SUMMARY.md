---
phase: 116-import-safety
plan: 02
subsystem: controller (webhook import)
tags: [python, webhook, controller, ambiguity, sanitize-log, cwe-117]
requires: [116-01]
provides:
  - Multi-path webhook lookup (lowercased basename -> {case-preserving path -> root})
  - WebhookManager.process rejects names resolving to 2+ distinct model paths
  - One sanitized, capped ambiguity WARNING per rejected event
affects: [116-03]
tech-stack:
  added: []
  patterns:
    - "Basename lookup keeps every path per name (setdefault dict-of-dicts); only the key is lowercased"
    - "_format_capped helper: sanitize each element + 10-item cap with ' (+N more)'"
key-files:
  created: []
  modified:
    - src/python/controller/controller.py
    - src/python/controller/webhook_manager.py
    - src/python/tests/unittests/test_controller/test_webhook_manager.py
    - src/python/tests/unittests/test_controller/test_controller_unit.py
decisions:
  - "Ambiguity warning wording: \"{source} webhook import '{name}' is ambiguous: matches {N} distinct SeedSyncarr paths in release(s) [roots] ([paths]); no import credit or automatic cleanup authorized ({provenance})\""
  - "Child paths are '/'-joined name chains built during BFS (identity keys, not filesystem paths); ModelFile.full_path and os.path.join are not used"
metrics:
  duration: ~15 min
  completed: 2026-10-08
  tasks: 2
  files: 4
---

# Phase 116 Plan 02: Reject ambiguous webhook imports Summary

The controller used to keep one root per webhook basename, and the last one written won. It now records every model path that carries each basename. `WebhookManager.process` credits a webhook name only when it resolves to exactly one distinct path. A name that matches two or more paths (across releases, within one pack, or between a root and a child elsewhere) gets one sanitized warning and is never returned. That means no import credit, no badge and no auto-delete timer for it. Unambiguous names return the same `(root_name, matched_name)` tuple as before, so Window 2 of `__check_webhook_imports` was not edited.

## What was built

- **controller.py, Window 1 only:** `name_to_paths: Dict[str, Dict[str, str]]`. Root entries are `{root: root}`. The BFS carries `(child, parent_path)` and stores `{"Root/sub/child": root}`. `process(name_to_paths)` is still called outside `__model_lock`. The docstring is updated. The diff has no hunks after the `process(` call.
- **webhook_manager.py:** `process()` has three branches:
  - Not found: the existing WARNING is kept byte-identical and counts `len(name_to_paths)`.
  - One path: the existing INFO line, now with `sanitize_log_value(root_name)`.
  - Two or more paths: one WARNING.

  A module-private `_format_capped()` sanitizes each root and path and caps the list at 10 with `(+N more)`.
- **Final warning wording:**
  `Sonarr webhook import 'sample.mkv' is ambiguous: matches 2 distinct SeedSyncarr paths in release(s) ['Rel.A', 'Rel.B'] (['Rel.A/sample.mkv', 'Rel.B/sample.mkv']); no import credit or automatic cleanup authorized (<provenance>)`
- **Tests:**
  - The 16 existing WebhookManager tests were migrated to the nested shape through a `_lookup((basename, path, root), ...)` helper. All assertion strings are unchanged, including `checked 3 names including children` and the exact `import detected` INFO strings.
  - The 3 `test_webhook_name_lookup_*` controller tests were migrated to the nested dict.
  - 6 new WebhookManager tests cover: ambiguity across roots, ambiguity within one root, single-path dedup, CRLF sanitization of name/roots/paths/provenance, the 10-item cap with `(+2 more)`, and root-name sanitization on the INFO line.

## Verification (observed)

Task 1 verify: `test_import_ambiguity.py` plus `TestControllerWebhookThreadSafety` gave `8 passed`. Whole-tree ruff: `All checks passed!`.

Task 2 quick run (6 controller test files, `-q -p no:cacheprovider -rf`):

```
FAILED tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_block_delete_despite_legacy_full_coverage
FAILED tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_block_delete_without_imported_children_entry
FAILED tests/unittests/test_controller/test_auto_delete.py::TestAutoDeleteDuplicateBasenameGuard::test_duplicate_video_basenames_case_insensitive
FAILED tests/unittests/test_controller/test_auto_delete_rearm.py::TestAutoDeleteTerminalSkipsDoNotRearm::test_duplicate_basename_is_terminal_and_does_not_rearm
4 failed, 333 passed, 12 warnings in 1.97s
```

The four remaining failures are exactly the delete-side RED tests that Plan 03 owns. All 6 `test_import_ambiguity.py` tests pass, which covers the 4 former RED import tests and the 2 preservation tests. Whole-tree ruff after Task 2: `All checks passed!`.

Wider checks:
- `tests/unittests/test_web -k webhook` gave `35 passed`.
- A grep for `webhook_manager.process` callers found no production caller other than `controller.py`. Every other test mocks `process.return_value` with the unchanged `[(root, name)]` shape.
- **Not verified:** the full `tests/unittests` run. Two attempts exceeded the 10-minute tool limit, which points to slow integration tests in the tree. The first reached about 40% with no failures and was stopped by its timeout. The second (the `test_controller` + `test_web` directories) had produced no output after more than 10 minutes when it was stopped. CI should be treated as the full-suite gate.

Acceptance greps:
- `name_to_root` appears 0 times in all 4 modified files.
- `no import credit or automatic cleanup authorized` appears once in webhook_manager.py.
- `full_path` / `os.path.join` appear 0 times in the `__check_webhook_imports` Window 1 block.

## Deviations from Plan

1. **[Rule 3 - Count mismatch] Test count is 22, not 20.** The plan assumed 14 existing tests in test_webhook_manager.py, but the file had 16 (it includes the three CWE-117 tests). 16 migrated plus 6 new gives 22 `def test_`.
2. **[Rule 3 - Acceptance grep] One docstring changed in TestControllerWebhookThreadSafety.** The plan said to leave that class untouched, but its docstring at L1156 named `name_to_root`, and the acceptance criteria require 0 occurrences in the file. Only that docstring word changed. The test logic is untouched.
3. **[Rule 3 - Acceptance grep] Warning phrase kept on one source line.** The first version split `no import credit or automatic cleanup authorized` across two string literals, so the acceptance grep returned 0. The literals were re-split so the phrase sits on one line. The runtime message is unchanged. Folded into commit 604aba8.
4. **Worktree base reset:** the worktree started at f8c94e9, not the expected base 166eb26. It was hard-reset to 166eb26 before any work, as the worktree_branch_check instructs.
5. **Verify paths:** the plan's verify commands name `/Users/julianamacbook/seedsyncarr/src/python`, which is the main checkout. All runs used the worktree's own `src/python`, so the changes being tested were the ones in this worktree.

## Known Stubs

None.

## Threat Flags

None. All new log output goes through `sanitize_log_value`, as T-116-02/T-116-03 require. No new endpoints or file access.

## Commits

- 604aba8 feat(116-02): reject ambiguous webhook imports via multi-path lookup
- 843db57 test(116-02): migrate webhook lookup tests to multi-path shape and cover ambiguity rejection

## Self-Check: PASSED

- FOUND: commits 604aba8, 843db57
- FOUND: all 4 modified files
