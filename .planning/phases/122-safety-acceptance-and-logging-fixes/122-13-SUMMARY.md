---
phase: 122-safety-acceptance-and-logging-fixes
plan: 13
subsystem: infra
tags: [gap-closure, tdd, webhook-import, pending-notice, d-06c, wr-02, wr-03]
gap_closure: true

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes (plan 10)
    provides: "The post-transfer pending-notice keep/credit exception (D-06c) that this plan narrows"
  - phase: 122-safety-acceptance-and-logging-fixes (plan 12)
    provides: "Live D-06(c) rerun evidence confirming the pre-narrowing fix worked for the intended race"
provides:
  - "post_transfer_pending bounded to _POST_TRANSFER_GRACE_SECS (120 s) since the root was last seen DOWNLOADING/QUEUED, and only while the root still has a local copy"
  - "A new WARNING that discards a tracked notice once the grace window expires or the local copy is gone, naming the reason, never crediting it"
  - "A successful STOP or DELETE_LOCAL discards the root's pending notices at once (_discard_pending_notices)"
  - "__credit_early_child takes a reason parameter; the post-transfer credit line says '(transfer finished, awaiting commit)' instead of the always-false '(root still transferring)'"
affects: ["122-15 (gates both 122-13 and 122-14, pushes to PR #134)", "122-16 (live LOG-01/D-06(c) rerun on the resulting build)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-root last-seen-transferring timestamp (monotonic), pruned to the current model every cycle, used to bound an evidence-gate exception to a short grace window instead of the full pending-notice TTL"

key-files:
  modified:
    - src/python/controller/controller.py
    - src/python/tests/unittests/test_controller/test_import_credit.py
    - src/python/tests/unittests/test_controller/test_controller.py

key-decisions:
  - "Grace window fixed at 120 s (constant _POST_TRANSFER_GRACE_SECS), measured on time.monotonic() from the last controller cycle that saw the root DOWNLOADING or QUEUED with a remote copy. See 'Grace Window Choice' below for the full justification carried over from the plan."
  - "requirements-completed left empty: SAFE-01 is only closed by 122-16/17's live rerun, not by this unit-level fix landing"

patterns-established: []

requirements-completed: []

# Metrics
duration: ~20min
completed: 2026-10-23
---

# Phase 122 Plan 13: D-06(c) Post-Transfer Window Narrowing and Credit-Reason Accuracy Summary

**Bounded the 122-10 post-transfer pending-notice exception to a 120 s grace window with a local-copy requirement, added a STOP/DELETE_LOCAL discard path, and made the import-credit log line name the real reason instead of always claiming "(root still transferring)" — closing WR-02 and WR-03 from 122-REVIEW.md.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-10-23T23:17:24Z
- **Tasks:** 2 of 2 completed
- **Files modified:** 3 (`controller.py`, `test_import_credit.py`, `test_controller.py`)

## Accomplishments

- Narrowed `post_transfer_pending` (122-10, D-06c) so a pending notice can only be kept or credited after its root stops transferring when: the root was last seen DOWNLOADING/QUEUED less than 120 s ago, AND it still has a remote copy, AND it still has a local copy. Past the window, or once the local copy is gone, the notice is discarded with a new WARNING and is never credited.
- Added a per-root `__last_transferring_at` timestamp (monotonic), set in Window 1 of `__check_webhook_imports` while a root is DOWNLOADING/QUEUED with a remote copy, and pruned to the current model's names every cycle (bounds its growth, closing threat T-122-62) and on `_discard_pending_notices`.
- Added `_POST_TRANSFER_GRACE_SECS = 120` with the evidence trail from the plan's grace-window analysis (122-05 and 122-12 live logs, default local-scan interval).
- Wired a successful STOP or DELETE_LOCAL command to discard the root's pending notices at once (`_discard_pending_notices(command.filename, "user stop" | "local copy deleted")` in `__process_commands`, which runs before `__check_webhook_imports` in the same `process()` call) — closing the gap where a stopped or user-deleted transfer could still have an old notice credited against a later re-transfer.
- Gave `__credit_early_child` a `reason` keyword (default `"root still transferring"`, matching the existing `__keep_pending_notice` pattern) so its INFO line says `"(transfer finished, awaiting commit)"` on the post-transfer path instead of the previously hardcoded, always-false `"(root still transferring)"`.
- Confirmed the 122-10 race fix and all other evidence-gate protections are byte-for-byte unchanged: the `"not downloaded by SeedSyncarr (no transfer evidence)"` WARNING, `_PENDING_NOTICE_MAX`, `_PENDING_NOTICE_TTL_SECS`, and all five pre-existing `TestPostTransferWindow` tests pass unmodified.

## Grace Window Choice (carried over from the plan)

Chosen value: `_POST_TRANSFER_GRACE_SECS = 120` (seconds, measured on `time.monotonic()` from the last controller cycle that saw the root DOWNLOADING or QUEUED with a remote copy).

**Why it is long enough.** The window being protected lasts from the lftp job ending until the local scan catches up and the commit pass runs. The app does not log transfer end at INFO, so this can only be bounded from existing evidence:
- 122-05 live log (2026-10-22, SSA122.Alpha2.S01): the post-transfer drop at 16:51:38,396 was followed by `Import credit ... applied on commit` at 16:51:40,916. The root committed about 2.5 s after the first cycle that saw it not transferring.
- 122-12 live log (2026-10-23): E04 was accepted 62 s after its post (SSA122.Echo.S01) and Foxtrot E03 104 s after its post. Each span includes the rest of that child's transfer, so the post-transfer part of it is smaller. 120 s is longer than either full span.
- The default local scan interval is 10 s (`seedsyncarr.py`: `interval_ms_local_scan = 10000`). The window ends at most one local scan after the job ends, so 120 s covers 12 default scan intervals.

**Why it is short enough.** 120 s is 1/180 of the old 6 h TTL. A stopped or failed transfer keeps a notice for at most 2 minutes. Even then the notice can be credited only if the child is already complete on disk, and credit alone never arms deletion (D-14). A user STOP or DELETE_LOCAL discards the notice at once, and a missing local copy discards it on the next cycle.

**Residual risk (unresolved, documented not fixed):** if an operator sets `interval_ms_local_scan` above about 100 s, the scan-lag window can outlast the grace window. The notice is then discarded with the new "no transfer seen for over 120 s without commit" WARNING, which matches the behaviour before 122-10 and is visible to the operator. It is not a silent credit.

## Task Commits

1. **Task 1 (RED): Regression tests** — `166c3e5` (test) — `_local_gone_pack` helper; `TestPostTransferWindowBounds` class with 6 tests (5 RED, 1 guard)
2. **Task 2 (GREEN): Evidence-gate fix** — `43c8c57` (fix) — `_POST_TRANSFER_GRACE_SECS`, `__last_transferring_at`, narrowed `post_transfer_pending`, new discard WARNING, STOP/DELETE_LOCAL discard wiring, `__credit_early_child` reason parameter
3. **Supplementary (Rule 3): Test-double fix** — `848a41d` (test) — seeded `__last_transferring_at = {}` in `TestCheckWebhookImportsSanitization`'s hand-rolled `Controller.__new__()` test double, which the GREEN fix's unconditional pruning line now reads on every call

**Plan metadata:** this commit (docs: record WR-02/WR-03 fix and local gates)

## Test Status (RED -> GREEN)

| Test | Pre-fix (commit `166c3e5`) | Post-fix (commit `43c8c57`) |
|---|---|---|
| `test_post_transfer_notice_discarded_after_grace_window` | RED — notice stayed pending past 120 s, no discard warning | GREEN |
| `test_post_transfer_grace_refreshes_while_root_transfers` | PASS (guard) — no time bound existed yet, so nothing to break | PASS |
| `test_post_transfer_notice_discarded_when_local_copy_gone` | RED — notice stayed pending with `local_size is None` | GREEN |
| `test_user_stop_discards_pending_notice` | RED — no "Discarded 1 pending import notice(s)" line on STOP | GREEN |
| `test_user_delete_local_discards_pending_notice` | RED — no discard line on DELETE_LOCAL | GREEN |
| `test_post_transfer_credit_line_says_transfer_finished` | RED — credit line said "(root still transferring)" on the post-transfer path | GREEN |

`-k TestPostTransferWindowBounds` on the RED commit: `5 failed, 1 passed` (all five failed on the behavioral assertion, none on a setup/TypeError/Command-failed error). On the GREEN commit: all 6 pass.

## Files Created/Modified

- `src/python/tests/unittests/test_controller/test_import_credit.py` — `_local_gone_pack` helper; `TestPostTransferWindowBounds` class (6 tests)
- `src/python/controller/controller.py` — `_POST_TRANSFER_GRACE_SECS` constant; `__last_transferring_at` dict (set, pruned, popped on discard); narrowed `post_transfer_pending`; new discard branch with reason-specific WARNING; STOP/DELETE_LOCAL discard wiring in `__process_commands`; `reason` keyword on `__credit_early_child`; docstring updates on `__check_webhook_imports`, `_discard_pending_notices` and `__credit_early_child`
- `src/python/tests/unittests/test_controller/test_controller.py` — seeded `__last_transferring_at = {}` in `TestCheckWebhookImportsSanitization._make_controller()`

## Decisions Made

See `key-decisions` in frontmatter and the "Grace Window Choice" section above. In summary: 120 s was chosen as long enough to cover the largest observed live post-transfer-to-accept span with margin (12x the default local-scan interval) while short enough to make the window the old 6 h TTL opened (WR-02) negligible in practice, with STOP/DELETE_LOCAL closing the rest of that gap immediately rather than waiting out the window.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `TestCheckWebhookImportsSanitization`'s hand-rolled test double crashed with `AttributeError` after the GREEN fix**
- **Found during:** Task 2 (GREEN fix), running the whole `tests/unittests/test_controller` suite per the verify command
- **Issue:** `TestCheckWebhookImportsSanitization._make_controller()` builds a `Controller` via `Controller.__new__(Controller)` and sets only the private attributes `__check_webhook_imports` needs, bypassing `__init__`. The GREEN fix's model-bounding line (`set(self.__last_transferring_at) - model_names_now`) runs unconditionally at the end of Window 1, even when the model has zero file names, so both of this class's tests (`test_recorded_import_log_is_sanitized`, `test_recorded_import_persist_value_is_raw`) crashed with `AttributeError: 'Controller' object has no attribute '_Controller__last_transferring_at'` instead of running their intended CWE-117 sanitization assertions.
- **Fix:** Added `c._Controller__last_transferring_at = {}` to `_make_controller()`, matching the existing pattern already used there for `__pending_child_notices` and `__root_lifecycle_generation` (both added for the same reason by 122-10).
- **Files modified:** `src/python/tests/unittests/test_controller/test_controller.py`
- **Verification:** `pytest tests/unittests/test_controller/test_controller.py -q` — 33 passed (was 2 failed before this fix)
- **Committed in:** `848a41d` (separate commit, kept out of the GREEN `fix(122-13)` commit so that commit's diff stays scoped to `controller.py` per the plan's acceptance criteria)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to keep the whole-suite gate green; a one-line addition to an existing test double's setup, not a behavioral or architectural change. No scope creep into product code.

## Issues Encountered

One `Edit` tool call on the docstring/Window-1 region of `controller.py` failed on its first attempt with "String to replace not found" despite the `Read`-displayed content appearing identical; splitting the edit into two smaller, more targeted replacements succeeded immediately. No behavioral impact — purely a tooling retry.

## Verify Output (observed, not paraphrased)

`cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_import_credit.py -p no:cacheprovider -q -k TestPostTransferWindowBounds` (pre-fix, commit `166c3e5`):
```
5 failed, 1 passed, 23 deselected, 1 warning in 0.33s
```

`cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_import_credit.py -p no:cacheprovider -q` (post-fix):
```
29 passed, 1 warning in 0.29s
```

`cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller/test_import_credit.py tests/unittests/test_controller/test_import_ambiguity.py tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_auto_delete_rearm.py tests/unittests/test_controller/test_completion_gate.py tests/unittests/test_controller/test_webhook_manager.py -p no:cacheprovider -q`:
```
285 passed, 1 warning, 15 subtests passed in 2.56s
```

`cd src/python && timeout 600 poetry run pytest tests/unittests/test_controller -p no:cacheprovider -q` (whole directory, post both fixes):
```
9 failed, 921 passed, 1 warning, 3 errors, 19 subtests passed in 73.80s (0:01:13)
```
All 9 failures + 3 errors are the pre-existing environment baseline (`test_extract_process.py` x6, `test_scanner_process.py` x3 FAILED + 3 ERROR — multiprocessing-spawn pickling of `MagicMock`, unrelated to this plan).

`cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q` (whole-tree baseline comparison):
```
21 failed, 1798 passed, 2 warnings, 3 errors, 77 subtests passed in 84.43s (0:01:24)
```
The 21 failures match the documented 122-03/122-10/122-14 environment baseline exactly in file/test identity (`test_sshcp.py` x10, `test_extract_process.py` x6, `test_scanner_process.py` x3+3 errors, `test_scanner.py::test_scan_file_with_latin_chars` x1) — none touched by this plan's two files.

`cd src/python && poetry run ruff check .`:
```
All checks passed!
```

Acceptance-criteria greps (all as specified by the plan, run after the GREEN commit):
```
grep -c "class TestPostTransferWindowBounds" test_import_credit.py        -> 1
grep -c "def _local_gone_pack" test_import_credit.py                      -> 1
grep -c "_POST_TRANSFER_GRACE_SECS = 120" controller.py                   -> 1
grep -c "_PENDING_NOTICE_TTL_SECS = 6 \* 3600" controller.py              -> 1
grep -c "_PENDING_NOTICE_MAX = 1000" controller.py                       -> 1
grep -c "__last_transferring_at" controller.py                           -> 8  (>= 4 required)
grep -c "Credited early import of '{}' in '{}' ({})" controller.py       -> 1
grep -c "in '{}' (root still transferring)" controller.py                -> 0
grep -c "by SeedSyncarr (no transfer evidence)" controller.py            -> 1  (unchanged)
grep -c "\"user stop\"" controller.py                                     -> 1
grep -c "\"local copy deleted\"" controller.py                            -> 1
```

One acceptance-criteria grep note, same class of issue 122-10-SUMMARY.md already documented for a different line: `grep -c "Discarding pending webhook import '{}' for '{}': {}; no import credit recorded" controller.py` prints `0`, not `1`, because that exact phrase is split across two adjacent string literals on two source lines (`"Discarding pending webhook import '{}' for '{}': {}; "` / `"no import credit recorded".format(...)`), and `grep` is line-based. The underlying string is correct when the literals concatenate at runtime — confirmed by reading the source directly and by the passing `test_post_transfer_notice_discarded_after_grace_window` / `test_post_transfer_notice_discarded_when_local_copy_gone` tests, which assert on the live-rendered message text, not on source layout.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Nothing pushed; 122-15 gates both 122-13 and 122-14 together and pushes to PR #134.
- 122-16 should rerun 122-05/122-12's D-06(c) scenario live on the build containing this fix (the narrowing is unit-verified here, not yet re-validated live), alongside the LOG-01 rerun.
- Branch `gsd/phase-122-safety-acceptance-and-logging-fixes` is clean and ready for 122-15.

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-23*

## Self-Check: PASSED

- FOUND: `src/python/controller/controller.py`
- FOUND: `src/python/tests/unittests/test_controller/test_import_credit.py`
- FOUND: `src/python/tests/unittests/test_controller/test_controller.py`
- FOUND: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-13-SUMMARY.md`
- FOUND commit `166c3e5` (`git log --oneline --all | grep 166c3e5`)
- FOUND commit `43c8c57` (`git log --oneline --all | grep 43c8c57`)
- FOUND commit `848a41d` (`git log --oneline --all | grep 848a41d`)
- All verify-output lines quoted above were captured directly from this run's own command output, not inferred.
