---
phase: 122-safety-acceptance-and-logging-fixes
plan: 10
subsystem: infra
tags: [gap-closure, tdd, webhook-import, pending-notice, evidence-gate, d-06c]
gap_closure: true

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes (plan 05)
    provides: "Live D-06(c) FAIL evidence and diagnosis: a deferred child webhook notice dropped between transfer end and commit"
provides:
  - "Narrow fix: a revalidated pending child notice is credited or kept (not dropped) once its root's transfer has ended but before it commits, as long as the root still has a remote copy"
  - "Five regression tests (2 RED reproducing the drop, 3 guards for fresh-notice/TTL/remote-copy-loss narrowness) in test_import_credit.py::TestPostTransferWindow"
affects: ["122-11 (push to PR #134)", "122-05's re-run of its D-06(c) scenario on the fixed build"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Evidence-gate exception keyed off __pending_child_notices membership after the per-cycle revalidation pass, used as a stronger known-tracked-root signal than a defaultdict lifecycle-generation lookup"

key-files:
  modified:
    - src/python/controller/controller.py
    - src/python/tests/unittests/test_controller/test_import_credit.py

key-decisions:
  - "Chosen fix (narrow variant of 122-05's rejected option 1): in Window 2's not-has_evidence branch, treat a notice whose key is still present in __pending_child_notices after this cycle's _revalidate_pending_notice pass as a known-tracked root; if that root still has a remote copy (remote_size is not None), credit or keep it through the post-transfer window via the same credit-or-keep path used while transferring. Rejected 122-05's option 2 (recompute directory sizes from children) as changing every size consumer with a larger blast radius, and option 3 (trust on-disk completeness over a webhook notice) as loosening the import-proof requirement for deletion."
  - "requirements-completed left empty for this plan: SAFE-01 is only closed by live sandbox evidence (122-05's re-run), not by this unit-level fix landing"

patterns-established: []

requirements-completed: []

# Metrics
duration: ~20min
completed: 2026-10-22
---

# Phase 122 Plan 10: D-06(c) Post-Transfer Pending-Notice Gap Closure Summary

**A revalidated pending child import notice is now credited or kept through the window between a root's transfer ending and its commit, instead of being permanently dropped with "no transfer evidence" — closing the exact SSA122.Alpha2.S01E04 drop found live in 122-05, with the 2026-08-21 foreign-dir protection and TTL/path/generation/ambiguity discards all unchanged.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-10-22T23:23:00Z
- **Tasks:** 3 of 3 completed
- **Files modified:** 2 (`controller.py`, `test_import_credit.py`)

## Accomplishments

- Reproduced the exact 122-05 live failure shape at the unit level: a notice kept pending while a root was DOWNLOADING, then dropped once the root's lftp job ended (state DEFAULT, local scan lagging) but before it committed
- Also covered the orchestrator-described unit-test-only shape: a DOWNLOADED root with every child individually complete but a stale root-level size aggregate, reachable only because these tests inject the model directly and skip `ModelPipeline._commit_downloaded_membership` (a live build commits a DOWNLOADED root in the same cycle, before the webhook check ever runs — see Diagnosis Refinement below)
- Fixed narrowly: Window 2's evidence gate now also accepts a notice whose key is still present in `__pending_child_notices` after that cycle's revalidation pass (proof it was kept while the root was transferring, in the current lifecycle, with a unique resolved path), provided the root still has a remote copy
- Confirmed the fix does not widen the gate for anything else: a FRESH notice (never pending) for a non-transferring, uncommitted root is still dropped exactly as before; a previously-pending notice whose root has since lost its remote copy (`remote_size` None) is still dropped; TTL expiry, path-change and generation-change discards in `_revalidate_pending_notice` are untouched and still fire before this exception can apply
- `__keep_pending_notice` takes a `reason` keyword (default `"root still transferring"`) so its DEBUG line is accurate when a notice is kept for the new "transfer finished, awaiting commit" reason

## Diagnosis Refinement (confirmed against the code, this plan)

- `Controller.process()` runs `__update_model()` (which ends with `ModelPipeline._commit_downloaded_membership()`) **before** `__check_webhook_imports()`. A root that reaches DOWNLOADED/EXTRACTED in the model is therefore already committed to `downloaded_file_names` by the time the webhook check runs — so on a live build the DOWNLOADED-with-stale-aggregate shape described in 122-05's diagnosis is not actually reachable; it is a unit-test-only shape (these tests inject the model directly via `_put` and never run the pipeline's commit pass).
- The reachable live shape is instead: the root's lftp job has ended (no `LftpJobStatus`, so `_set_initial_state` leaves it `DEFAULT` rather than `DOWNLOADING`), while the local scan is still lagging, so at least one child still shows local < remote with no transfer state, `_are_all_children_downloaded` is False, and the root stays `DEFAULT` with `local_size < remote_size`. `has_evidence` is False and `transferring` is False — exactly what the live log showed (drop at 16:51:38, commit at 16:51:40, two seconds later).
- Both shapes are covered by separate RED tests (`test_pending_notice_survives_post_transfer_scan_lag_default_root` for the live shape, `test_pending_notice_survives_post_transfer_scan_lag_downloaded_root` for the unit-test-only shape), both fixed by the same `post_transfer_pending` check since neither depends on which non-transferring state the root is in.

## Task Commits

1. **Task 1 (RED): Regression tests** — `f51e55f` (test) — added `_post_transfer_pack` helper and `TestPostTransferWindow` (5 tests: 2 RED, 3 guards)
2. **Task 2 (GREEN): Evidence-gate fix** — `73bd599` (fix) — `post_transfer_pending` exception in `__check_webhook_imports`, `reason` keyword on `__keep_pending_notice`, docstring updates
3. **Task 3: Local gates and SUMMARY** — this commit (docs)

**Plan metadata:** this commit (docs: record D-06c fix and local gates)

## Files Created/Modified

- `src/python/tests/unittests/test_controller/test_import_credit.py` — `_post_transfer_pack` helper; `TestPostTransferWindow` class with 5 tests (2 RED reproducing the drop, 3 guards: fresh-notice-still-ignored, TTL-expiry-unaffected, remote-copy-loss-still-drops)
- `src/python/controller/controller.py` — `post_transfer_pending` computed in `__check_webhook_imports` Window 2; drop condition changed from `not transferring` to `not transferring and not post_transfer_pending`; `root_level_dir` now also true under `post_transfer_pending`; `__keep_pending_notice` gained a `reason` keyword; docstrings on `__check_webhook_imports`, the Window 2 comment block, `__credit_early_child` and `__keep_pending_notice` updated to describe the post-transfer window

## Decisions Made

See `key-decisions` in frontmatter. In summary: the narrow "known-tracked root via pending-notice membership" exception was chosen over 122-05's rejected wider options (recomputing directory sizes, or trusting on-disk completeness), because it reaches exactly the roots already proven to have been transferring this lifecycle, with no broader blast radius.

## Deviations from Plan

None — plan executed exactly as written. Both RED tests failed on the pre-fix code for the expected reason (the "Ignoring webhook import ... no transfer evidence" drop / missing pending-notice-and-credit assertions), all three guards and all 21 pre-existing tests in the file passed unmodified throughout, and the fix made all 5 new tests pass without touching any other file.

One plan acceptance-criteria note (not a deviation in behavior, just the verification command itself): the plan's acceptance criterion `grep -c "not downloaded by SeedSyncarr (no transfer evidence)" src/python/controller/controller.py` is expected to print `1`; it prints `0` both before and after this plan's changes, because that exact string is split across two adjacent string-literal lines in the source (`"...not downloaded "` / `"by SeedSyncarr (no transfer evidence)"`) and `grep` is line-based. The underlying requirement — the warning string itself is unchanged, still one call site — holds: confirmed by reading the single occurrence directly and by `grep -c "no transfer evidence" src/python/controller/controller.py` printing `1`.

## Issues Encountered

None.

## Residual Risk (documented, not in scope)

A FRESH notice (one that was never kept pending) that first arrives inside the same post-transfer window — after the root's transfer has ended but before it commits — is still ignored with "no transfer evidence", exactly as before this phase. This is the pre-existing evidence-gate behavior for any notice without prior transferring-state evidence, not the D-06(c) deferral contract (which only covers a notice that was already being tracked while the root was actively transferring). Guarded explicitly by `test_fresh_notice_for_uncommitted_non_transferring_root_still_ignored`.

## Local Gates (Task 3)

**Gate 1 — Full unit suite vs. 122-03 environment baseline**

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q`

Result (verbatim summary line): `21 failed, 1787 passed, 2 warnings, 3 errors, 77 subtests passed in 81.16s (0:01:21)`

The sorted 24-line FAILED/ERROR list (test_extract_process.py x6, test_scanner_process.py x3 FAILED + 3 ERROR, test_sshcp.py x10, test_scanner.py::test_scan_file_with_latin_chars x1) is, after stripping pytest's truncated inline reason suffix (`-q`'s `- KeyErro...` etc., a cosmetic formatting difference only), **byte-identical** to the 122-03-SUMMARY.md Gate 1 baseline list (`comm`/`diff` both empty). All failures remain the pre-existing environment-bound set (multiprocessing spawn, local SSH test host, macOS APFS Latin-1 path handling). **Gate 1: PASS.**

**Gate 2 — Whole-tree ruff**

Command: `poetry run ruff check src/python/` (repo-root equivalent; standalone/poetry-venv ruff here is 0.15.9, not the CI-pinned 0.15.22 — a pre-existing local environment/lock drift unrelated to this plan's two files, noted for transparency, not fixed as out of scope)

Result: `All checks passed!` **Gate 2: PASS.**

**Gate 3 — RED-before-GREEN**

`git log --format=%s -3` → `fix(122-10): ...` / `test(122-10): ...` / `docs(122): ...` — `test(122-10)` (`f51e55f`) precedes `fix(122-10)` (`73bd599`); `git show --stat f51e55f` lists only `test_import_credit.py`. **Gate 3: PASS.**

**Gate 4 — Scope diff**

`git diff <commit before test(122-10)>..HEAD --stat -- src/` lists exactly `src/python/controller/controller.py` and `src/python/tests/unittests/test_controller/test_import_credit.py`. **Gate 4: PASS.**

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Nothing pushed; 122-11 pushes to PR #134.
- 122-05's D-06(c) scenario (`SSA122.Alpha2.S01`) should be re-run against the build containing this fix before SAFE-01 is marked passed; the fix is unit-verified here but not yet re-validated live.
- Branch `gsd/phase-122-safety-acceptance-and-logging-fixes` is clean and ready for 122-11.

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-22*

## Self-Check: PASSED

- FOUND: `src/python/controller/controller.py` (modified, `post_transfer_pending` present 4x)
- FOUND: `src/python/tests/unittests/test_controller/test_import_credit.py` (modified, `TestPostTransferWindow` and `_post_transfer_pack` present)
- FOUND commit `f51e55f` (`git log --oneline --all | grep f51e55f`)
- FOUND commit `73bd599` (`git log --oneline --all | grep 73bd599`)
- Full-suite summary line and ruff output quoted above were captured directly from this run's own command output, not inferred.
