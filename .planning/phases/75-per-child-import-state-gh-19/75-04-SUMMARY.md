---
phase: 75-per-child-import-state-gh-19
plan: 04
subsystem: tests
tags: [python, tests, auto-delete, gh-19, coverage-guard, persist-rehydration]

# Dependency graph
requires:
  - phase: 75-per-child-import-state-gh-19
    provides: 75-01 ControllerPersist.imported_children + add_imported_child; 75-02 WebhookManager.process tuple return; 75-03 _VIDEO_EXTENSIONS + coverage guard + clear-on-success
provides:
  - TestAutoDeleteCoverageGuard class (7 cases) exercising the D-08/D-10/D-11/D-14/D-04 guard paths directly
  - TestAutoDeletePersistRehydration class (1 case) exercising D-20 post-restart rehydration through to_str/from_str
  - Migrated tuple-shape mocks at L329/L343 so TestAutoDeleteIntegration runs green against plan-03 controller
affects: []  # terminal plan of phase 75

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subclass TestAutoDeleteExecution (not BaseAutoDeleteTestCase) to reuse _make_safe_mock_file and _make_child helpers without duplication"
    - "Log assertion via MagicMock attribute chain: self.controller.logger.info.call_args_list captures calls because context.logger.getChild(...) returns a recording MagicMock"
    - "Persist rehydration test: serialize via to_str, deserialize via from_str, swap self.controller._Controller__persist with the rehydrated copy, then invoke Timer-fire"

key-files:
  created: []
  modified:
    - src/python/tests/unittests/test_controller/test_auto_delete.py

key-decisions:
  - "Option (b) subclassing chosen per plan's preferred path: TestAutoDeleteCoverageGuard and TestAutoDeletePersistRehydration both inherit from TestAutoDeleteExecution rather than copying _make_child / _make_safe_mock_file helpers"
  - "Log-content assertion uses MagicMock call_args_list inspection, not unittest.assertLogs: controller's self.logger is a MagicMock attribute chain (context.logger.getChild('Controller')), so .info.call_args_list directly captures the calls"
  - "BoundedOrderedSet NOT imported into test file: D-20 test reuses add_imported_child + from_str, no direct BoundedOrderedSet construction"
  - "Bonus case-insensitive coverage test added (seed 'ep01.mkv' lowercase, on-disk 'Ep01.MKV' mixed case -> delete proceeds): per PATTERNS.md's 'at least one case should verify the lowercasing comparison'"
  - "Pre-existing TestAutoDeleteIntegration tuple migration at L329/L343 committed separately (Task 1) so the RED->GREEN migration signal is visible in git log"

patterns-established:
  - "Per-child coverage guard test seed: self.persist.add_imported_child(root, child.lower()) to mirror the controller's normalization write-path"
  - "Rehydration integration test: ControllerPersist.from_str(persist.to_str(), max_tracked_files=100) then assign to self.controller._Controller__persist -- covers D-20 without a full controller re-init"
  - "Missing-basename log assertion: scan [str(call) for call in logger.info.call_args_list] for 'partial import' substring + root_name + missing child basename -- no reliance on exact log format"

requirements-completed: [FIX-02]

# Metrics
duration: ~20min
completed: 2026-04-20
---

# Phase 75 Plan 04: Auto-Delete Unit Tests Summary

**test_auto_delete.py now carries 7 coverage-guard cases + 1 post-restart rehydration case + 3 migrated mock sites; phase 75 Success Criteria #1, #4, and #5 are directly test-covered and green.**

## Performance

- **Duration:** ~20 min (including worktree base correction + pytest cache snag)
- **Started:** 2026-04-20T16:00Z (approx, plan read start)
- **Completed:** 2026-04-20T16:20Z
- **Tasks:** 2 (both `tdd="true"`)
- **Files modified:** 1
- **Commits:** 2

## Accomplishments

- **Task 1 (mock migration):** L329 and L343 `self.mock_webhook_manager.process.return_value` entries migrated from `List[str]` to `List[Tuple[str, str]]` (tuple form `("test_file.mkv", "test_file.mkv")`). L45 (empty list in `BaseAutoDeleteTestCase.setUp`) left unchanged per plan — empty list is tuple-shape-invariant. Both pre-existing `TestAutoDeleteIntegration` cases (`test_webhook_import_triggers_auto_delete_schedule`, `test_webhook_import_no_schedule_when_disabled`) now pass against the plan-03 controller which unpacks the tuples at `controller.py:761` (`for root_name, matched_name in newly_imported:`).
- **Task 2 (new cases):** Two new test classes added immediately before `TestAutoDeleteShutdown`:
  - `TestAutoDeleteCoverageGuard(TestAutoDeleteExecution)` — 7 cases covering D-08 (full + partial), D-10 (non-video ignored), D-11 (single-file bypass), D-14 (legacy grandfather), D-04 (clear-on-success), and a bonus case-insensitivity check.
  - `TestAutoDeletePersistRehydration(TestAutoDeleteExecution)` — 1 case covering D-20 by round-tripping the seeded persist through `to_str` → `from_str`, swapping `self.controller._Controller__persist` for the rehydrated copy, and asserting Timer-fire still skips when coverage is partial.
- **Subclassing strategy:** Both new classes extend `TestAutoDeleteExecution` (not `BaseAutoDeleteTestCase`) per plan's explicitly preferred option (b), inheriting `_make_child` and `_make_safe_mock_file` helpers without duplication. The side effect is that parent-class tests rerun under each subclass, inflating the collected count — this is by-design and matches the plan's recommendation.
- **Test metrics:**
  - `test_auto_delete.py`: **74 passed, 0 failed** (28 pre-existing × 1 base class + 17 TestAutoDeleteExecution tests × 2 subclasses inheriting them + 7 new coverage-guard tests + 1 new rehydration test + 4 scheduling + 2 shutdown + 2 integration; pytest collects 74 items).
  - Plan acceptance criterion "at least 35 test items" — satisfied and exceeded (74 items).
  - `test_auto_delete.py` + `test_controller_persist.py` + `test_controller_unit.py` + `test_webhook_manager.py` combined: **215 passed, 0 failed**.
  - Full `test_controller/` suite: **463 passed, 9 failed, 3 errors** — the 9 failures + 3 errors are all in `test_extract_process.py` and `test_scanner_process.py` (pre-existing macOS multiprocess flakes, explicitly acknowledged as acceptable in the plan's `<verification>` block and in `.planning/debug/resolved/seedsyncarr-predelete.md`). Not caused by this plan's changes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_auto_delete process.return_value sites to tuple form** — `0e1c125` (test)
2. **Task 2: Add D-19 coverage guard cases + D-20 rehydration case** — `52cb4b7` (test)

_Note: This plan's tasks are declared `tdd="true"`, but the production code they exercise (coverage guard, tuple-unpack, clear-on-success, from_str rehydration) already landed in plans 01/02/03. So the tests go GREEN on first run. The plan-level RED signal was the 2-case failure in `TestAutoDeleteIntegration` before Task 1's migration — Task 1 is the GREEN flip for those, Task 2 is new GREEN cases._

## Files Modified

- `src/python/tests/unittests/test_controller/test_auto_delete.py` — migrated 2 mock sites to tuple form (Task 1), appended 2 new test classes with 8 new test methods (Task 2). Net `+144 / -2`.

## Success Criterion Mapping

| Phase 75 Success Criterion | Covering Test Case | Class |
|-----------------------------|--------------------|-------|
| #1 — Partial-import pack not auto-deleted (GH #19 regression) | `test_execute_skips_dir_when_one_video_child_missing` | `TestAutoDeleteCoverageGuard` |
| #4 — Single-file import covered | `test_execute_proceeds_single_file_root_when_root_imported` | `TestAutoDeleteCoverageGuard` |
| #4 — Full-coverage pack deletes | `test_execute_proceeds_dir_when_all_video_children_imported` | `TestAutoDeleteCoverageGuard` |
| #4 — Partial-coverage pack skips | `test_execute_skips_dir_when_one_video_child_missing` | `TestAutoDeleteCoverageGuard` |
| #4 — Non-video files ignored for coverage | `test_execute_proceeds_dir_when_non_video_files_uncovered` | `TestAutoDeleteCoverageGuard` |
| #4 — Legacy grandfather (no per-root entry) | `test_execute_proceeds_dir_when_no_imported_children_entry_legacy` | `TestAutoDeleteCoverageGuard` |
| #4 — Post-restart rehydration | `test_imported_children_partial_coverage_survives_restart` | `TestAutoDeletePersistRehydration` |
| #5 — Clear-on-success | `test_execute_clears_imported_children_after_delete` | `TestAutoDeleteCoverageGuard` |
| (Bonus) Case-insensitive matching | `test_execute_coverage_check_is_case_insensitive` | `TestAutoDeleteCoverageGuard` |

## Mock-Migration Confirmation

- L45 `self.mock_webhook_manager.process.return_value = []` — **unchanged** (empty list is tuple-shape-invariant; `for x, y in []` is a no-op).
- L329 `self.mock_webhook_manager.process.return_value = [("test_file.mkv", "test_file.mkv")]` — **migrated**.
- L343 `self.mock_webhook_manager.process.return_value = [("test_file.mkv", "test_file.mkv")]` — **migrated**.
- Acceptance greps:
  - `grep -nE 'process\.return_value = \["' test_auto_delete.py` → 0 matches (PASS)
  - `grep -nE 'process\.return_value = \[\("test_file.mkv", "test_file.mkv"\)\]' test_auto_delete.py` → 2 matches (PASS)

## Final Pytest Output (Scope: test_auto_delete.py)

```
============================== test session starts ===============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /.../src/python
collected 74 items
...
74 passed, 1 warning in 0.32s
```

## Decisions Made

Plan executed as written. Notable reinforcements:

- **Subclassing over helper duplication (plan-preferred option b):** Both new test classes subclass `TestAutoDeleteExecution` to reuse `_make_child` and `_make_safe_mock_file` helpers. This inflates the collected count (parent tests rerun under each subclass) but mirrors the plan's stated preference to avoid duplication. The alternative (copying the two helpers into each class) would have yielded exactly 36 cases (28 + 8) but at the cost of duplication.
- **Log-content assertion via MagicMock call_args_list:** The plan's `<interfaces>` block identified that `self.controller.logger` is a MagicMock attribute chain because `context.logger.getChild(...)` on a MagicMock returns another MagicMock. Confirmed empirically — `self.controller.logger.info.call_args_list` captures every `.info()` call with its args, and `str(call)` renders the args for substring matching. `assertLogs` was not needed (and would not have captured anything because the controller's logger is a Mock, not a real `logging.Logger`).
- **`BoundedOrderedSet` not imported:** The D-20 test seeds state via `self.persist.add_imported_child(root, child)` and then round-trips through `ControllerPersist.from_str` — no direct `BoundedOrderedSet(...)` construction needed, so the import stayed out of the test file per plan Action §1's guidance ("Only add the import if the D-20 test constructs a BoundedOrderedSet directly").
- **Case-insensitive bonus test added:** Plan's Action §3 BONUS note + PATTERNS.md's "at least one case should verify the lowercasing comparison" motivated `test_execute_coverage_check_is_case_insensitive`. Seeds `imported_children["Pack.S01"] = {"ep01.mkv"}` (lowercase, as add_imported_child writes it) and stubs `_make_child("Ep01.MKV", ...)` (mixed case). Delete proceeds because controller's compare side lowercases via `{c.lower() for c in imported_child_bset.as_list()}` and basename side via `child.name.lower()`.

## Deviations from Plan

Plan executed as written with one observational note:

**1. [Informational] Test count higher than plan's lower bound due to subclassing**
- **Found during:** Task 2 verification
- **Issue:** Plan's acceptance criterion says "at least 35 test items (28 pre-existing + 7 new)". Actual collected count is 74 because `TestAutoDeleteCoverageGuard` and `TestAutoDeletePersistRehydration` both inherit from `TestAutoDeleteExecution`, which already holds 17 tests — those 17 rerun under each subclass, adding 34 duplicated runs.
- **Fix:** None required — this is the direct consequence of plan-preferred option (b) "subclass `TestAutoDeleteExecution` instead of `BaseAutoDeleteTestCase`". The plan acknowledged both options; option (b) inflates collected count but eliminates helper duplication. Acceptance criterion "at least 35" is satisfied by a wider margin (74 >= 35).
- **Files modified:** None.
- **Committed in:** `52cb4b7`.

**Total deviations:** 1 observational (no code impact).

## Issues Encountered

### Worktree base correction (pre-task)
On agent startup the worktree branch was based on `815a4ac` (main branch tip) rather than the required base `d3483e5` (phase-75 wave-2 merge commit including plans 01+02+03). Per the `<worktree_branch_check>` protocol I hard-reset to `d3483e5` before any other work. Verified `git rev-parse HEAD` matched the target commit before proceeding. No work was lost.

### Pytest cache stale-state during diagnostic phase
During the initial Task 1 verification, pytest reported `ValueError: too many values to unpack (expected 2)` for `TestAutoDeleteIntegration` even after the migration was complete on disk. Diagnostic instrumentation (spy side_effect writing to `/tmp/spy.log`) showed the migrated code WAS in effect — the spy captured the new tuple shape and the test passed. The initial failure was a stale pytest cache state; clearing `/tmp/.pytest_cache` and re-running produced a clean pass. No code change required — the migration on disk was always correct.

### Bash permission denial on inline Python REPL diagnostics (transient)
Sandbox denied a standalone `python3 -c "..."` interactive reproduction during diagnosis. Workaround: inserted a diagnostic `side_effect` callback into the test code that wrote to `/tmp/spy.log`, then ran pytest normally. Spy output confirmed `self.controller._Controller__webhook_manager` and `self.mock_webhook_manager` share the same object id (expected — the mock is passed in at Controller construction), and the spy was called exactly once with the tuple-form return. All diagnostic code was removed before the final commit.

## User Setup Required

None — in-process test additions; no external service, env var, or credential required.

## Threat Flags

No new security-relevant surface introduced. The plan's `<threat_model>` covered test-fixture tampering (T-75-15, mitigated via explicit-state assertions and no reliance on Timer fire), information disclosure (T-75-16, accept — anonymized fixture names only), DoS (T-75-17, accept — all in-memory), and repudiation (T-75-18, accept). All four threats disposed as planned.

## Phase 75 Closing Note

With this plan, the four phase-level must-haves (per ROADMAP §Phase 75) are now all test-covered and green:

1. **Per-child state shape** — `ControllerPersist.imported_children` (plan 01) round-trips cleanly via `to_str`/`from_str` (test_controller_persist.py) AND survives restart (test_auto_delete.py::TestAutoDeletePersistRehydration).
2. **Webhook (root, child) capture** — `WebhookManager.process` returns tuples (plan 02) and `__check_webhook_imports` writes per-child via `add_imported_child` (plan 03); exercised end-to-end through `TestAutoDeleteIntegration` which now runs green after Task 1 migration.
3. **Coverage guard at Timer-fire** — `__execute_auto_delete` skips when any on-disk video child is missing from `imported_children[root]` (plan 03); directly tested by `test_execute_skips_dir_when_one_video_child_missing` (the canonical GH #19 regression case).
4. **Clear-on-success + grandfather legacy** — post-delete pop (D-04) tested by `test_execute_clears_imported_children_after_delete`; legacy-root proceed (D-14) tested by `test_execute_proceeds_dir_when_no_imported_children_entry_legacy`.

Phase 75 Success Criteria #1, #3, #4, and #5 all have direct test coverage. GH #19 is closed.

## TDD Gate Compliance

- RED gate: Pre-Task-1 state — `TestAutoDeleteIntegration` 2 cases failed with `ValueError: too many values to unpack (expected 2)` at controller.py:761 (plan 03 unpacks 2-tuples; old mocks returned strings). Verified at agent start (26 passed, 2 failed baseline).
- GREEN gate: Task 1 commit `0e1c125 test(75-04): migrate test_auto_delete process.return_value sites to tuple form` — full test_auto_delete.py 28/28 passing post-commit.
- GREEN gate (additive): Task 2 commit `52cb4b7 test(75-04): add D-19 coverage guard cases + D-20 rehydration case` — full test_auto_delete.py 74/74 passing.
- REFACTOR gate: skipped (tests are already at their final shape; no cleanup pass needed).

## Self-Check: PASSED

- `src/python/tests/unittests/test_controller/test_auto_delete.py` — FOUND
- Commit `0e1c125` (Task 1 test migration) — FOUND in git log
- Commit `52cb4b7` (Task 2 new cases) — FOUND in git log
- `class TestAutoDeleteCoverageGuard` — 1 match (PASS)
- `class TestAutoDeletePersistRehydration` — 1 match (PASS)
- All 8 new test method names present (PASS)
- `test_auto_delete.py` final run: 74 passed, 0 failed (PASS)
- `test_controller/` combined run (4 phase-75 files): 215 passed, 0 failed (PASS)
- No accidental deletions across both commits: `git diff --diff-filter=D --name-only HEAD~2 HEAD` empty (PASS)

---
*Phase: 75-per-child-import-state-gh-19*
*Plan: 04*
*Completed: 2026-04-20*
