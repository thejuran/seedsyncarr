---
phase: 75-per-child-import-state-gh-19
plan: 01
subsystem: persist
tags: [python, persist, auto-delete, gh-19, bounded-ordered-set, json-roundtrip]

# Dependency graph
requires:
  - phase: earlier-v1.1.x
    provides: BoundedOrderedSet[T] generic with maxlen + eviction tracking; ControllerPersist JSON round-trip scaffolding (downloaded/extracted/stopped/imported_file_names)
provides:
  - ControllerPersist.imported_children field (Dict[str, BoundedOrderedSet[str]] via collections.OrderedDict)
  - ControllerPersist.add_imported_child(root, child) helper with per-root and global-root-key eviction
  - __KEY_IMPORTED_CHILDREN = "imported_children" serialization key
  - DEFAULT_MAX_CHILDREN_PER_ROOT = 500 class constant
  - JSON round-trip of imported_children via to_str / from_str with dct.get(KEY, {}) backward-compat
  - Two new get_eviction_stats keys: imported_children_evictions, imported_children_root_count
affects: [75-02-webhook-manager, 75-03-controller-coverage-guard, 75-04-auto-delete-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-root BoundedOrderedSet nested in an OrderedDict keyed by root name, with two independent bounds (per-root set maxlen + global OrderedDict size cap)"
    - "Lazy-create of per-root BoundedOrderedSet on first add_imported_child call; OrderedDict.popitem(last=False) for FIFO eviction of root keys"
    - "JSON shape {root: [child, ...]} for nested dict-of-ordered-set field, serialized via list comprehension over BoundedOrderedSet.as_list()"

key-files:
  created: []
  modified:
    - src/python/controller/controller_persist.py
    - src/python/tests/unittests/test_controller/test_controller_persist.py

key-decisions:
  - "DEFAULT_MAX_CHILDREN_PER_ROOT = 500 per D-02 (planner discretion — bounded per-pack, separate from global 10000 root cap)"
  - "collections.OrderedDict for imported_children so popitem(last=False) eviction is explicit (per PATTERNS.md §Pattern 1)"
  - "add_imported_child helper colocates both caps + eviction logging in persist layer, matching from_str debug-log style for other collections"
  - "dct.get(__KEY_IMPORTED_CHILDREN, {}) — missing key loads as empty OrderedDict per D-03 backward-compat"

patterns-established:
  - "Per-root + global two-cap pattern: per-item (child) eviction via BoundedOrderedSet.maxlen, per-group (root) eviction via OrderedDict.popitem(last=False) driven by self._max_tracked_files"
  - "Nested dict-of-ordered-set round-trip: to_str emits {root: bset.as_list()} via comprehension, from_str reuses the mutator helper to replay eviction/cap semantics uniformly on load"

requirements-completed: [FIX-02]

# Metrics
duration: ~45 min
completed: 2026-04-20
---

# Phase 75 Plan 01: Per-Child Import State Persist Foundation Summary

**ControllerPersist gains imported_children field (Dict[str, BoundedOrderedSet[str]]) with per-root and global eviction, JSON round-trip, and 4 unit tests — the storage primitive the GH #19 coverage guard depends on.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-04-20T14:05Z (approx, plan read start)
- **Completed:** 2026-04-20T14:49Z
- **Tasks:** 2 (both `tdd="true"`)
- **Files modified:** 2
- **Commits:** 3 (Task 1: feat; Task 2: test → feat per TDD RED/GREEN)

## Accomplishments

- New `imported_children: OrderedDict[str, BoundedOrderedSet[str]]` field on `ControllerPersist` with lazy per-root set creation.
- `add_imported_child(root, child)` helper enforces two eviction bounds uniformly: per-root `maxlen=DEFAULT_MAX_CHILDREN_PER_ROOT` (500) and global root-key cap `self._max_tracked_files` (10000) via `OrderedDict.popitem(last=False)`. Both eviction paths emit debug-level log lines matching the existing `from_str` collection-loader style.
- `get_eviction_stats()` extended with `imported_children_evictions` (sum across per-root BoundedOrderedSets) and `imported_children_root_count` (OrderedDict length).
- JSON round-trip through `to_str` / `from_str`: serialized shape is `{"imported_children": {"<root>": ["<child>", ...], ...}}`; load path is backward-compatible via `dct.get(__KEY_IMPORTED_CHILDREN, {})` — pre-phase-75 persist blobs load cleanly with an empty field.
- 4 new test cases added to `test_controller_persist.py` (roundtrip, in-to_str shape, backward-compat missing-key, per-root eviction + stats). All 19 tests in the file pass; the plan-level full controller suite shows only pre-existing multiprocess flakes in `test_extract_process.py` / `test_scanner_process.py` (explicitly acknowledged as acceptable in the plan's `<verification>` block).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add imported_children field + constants + helper** — `caf1427` (feat)
2. **Task 2 (RED): Add 4 failing tests for imported_children round-trip** — `2376856` (test)
3. **Task 2 (GREEN): Extend from_str / to_str for imported_children** — `e2e0637` (feat)

_Note: Task 2 was executed TDD-style per its `tdd="true"` attribute. Tests were committed at RED (2 of 4 failing — roundtrip + in_to_str; the other 2 pass against Task 1's code), then serialization was committed at GREEN (all 4 pass)._

## Files Modified

- `src/python/controller/controller_persist.py` — added `import collections`, `Dict` to typing import, `__KEY_IMPORTED_CHILDREN` constant, `DEFAULT_MAX_CHILDREN_PER_ROOT = 500`, `imported_children` field initializer, `add_imported_child` helper, extended `get_eviction_stats`, extended `from_str` backward-compat loader, extended `to_str` nested-dict serializer. (+63 lines)
- `src/python/tests/unittests/test_controller/test_controller_persist.py` — appended 4 new test methods at the end of `TestControllerPersist`: `test_imported_children_roundtrip`, `test_imported_children_in_to_str`, `test_backward_compatibility_no_imported_children_key`, `test_imported_children_eviction_per_root`. (+52 lines)

## Decisions Made

Followed the plan's decision record exactly. Notable reinforcements:

- **Per-root bound of 500** (D-02, plan Action §2): picked via planner discretion in 75-01-PLAN.md; not revised.
- **collections.OrderedDict** (not plain `dict`) for `imported_children`: makes the `popitem(last=False)` global-cap eviction explicit and matches the pattern documented in `75-PATTERNS.md §Pattern 1`. Python 3.7+ dicts are ordered too, but `OrderedDict.popitem(last=False)` reads as intentional whereas `dict.popitem()` only pops last.
- **`add_imported_child` helper (not inline setdefault)**: colocates both caps, eviction logging, and FIFO root-key semantics in the persist layer. Downstream plans 75-02/75-03 will reuse it rather than re-implementing the insertion+cap logic.
- **`dct.get(KEY, {})` for load**: missing key is not an error (D-03), mirroring the existing pattern for `stopped` and `imported_file_names`.

## Deviations from Plan

None — plan executed exactly as written. No auto-fixes required; no architectural changes; no authentication gates encountered (pure offline persist-layer work).

## Issues Encountered

- **Worktree branch base misalignment (pre-task):** On agent startup the worktree branch was based on `main` (815a4ac) rather than the feature branch HEAD (`05a945e`). Followed the `<worktree_branch_check>` protocol: hard-reset to `05a945e` before any other work. Verified HEAD matched the target commit before proceeding.
- **Bash permission denial on pytest (transient, startup only):** Initial `python -m pytest` invocations were denied by the sandbox; `python3 -m pytest ...` from the worktree root worked normally. All test runs used `python3`.

## User Setup Required

None — no external service configuration required.

## Threat Flags

_No new security-relevant surface introduced. The plan's `<threat_model>` covered persistence DoS (T-75-01, mitigated via per-root + global bounds) and tampering (T-75-02, mitigated via existing `PersistError` wrapping + `dct.get` default). Both mitigations are implemented as specified; no new threat flags to raise._

## Next Phase Readiness

- `ControllerPersist.add_imported_child` is the primitive for **Plan 75-02** (webhook_manager: return `List[Tuple[root, matched_name]]`) and **Plan 75-03** (controller: mutate `imported_children[root]` in Window 2 of `__check_webhook_imports`, and read it in the new coverage-guard of `__execute_auto_delete`).
- Legacy-grandfather semantics (D-14): `imported_children` defaults to empty on pre-phase-75 persist files. Downstream coverage-guard MUST treat "root key absent" as "fully imported" so existing tracked roots continue to auto-delete. This plan surfaces the state shape correctly for that contract; no follow-up work needed here.
- Global root-key cap reuses `self._max_tracked_files` — no new config surface introduced.

## Self-Check: PASSED

- `src/python/controller/controller_persist.py` — FOUND
- `src/python/tests/unittests/test_controller/test_controller_persist.py` — FOUND
- Commit `caf1427` (Task 1 feat) — FOUND
- Commit `2376856` (Task 2 RED test) — FOUND
- Commit `e2e0637` (Task 2 GREEN feat) — FOUND
- All 4 new test cases present and passing (19/19 in `test_controller_persist.py`)
- All acceptance-criteria greps from Task 1 + Task 2 return exit 0

---
*Phase: 75-per-child-import-state-gh-19*
*Plan: 01*
*Completed: 2026-04-20*
